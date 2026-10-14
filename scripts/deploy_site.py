#!/usr/bin/env python3
"""Export a publication and deploy its three GitHub Pages repositories.

Build the publication first with web/classic/build_from_runs.py. Then run:
  python scripts/deploy_site.py --publication PUB --out DEPLOY --dry-run

DEPLOY must not exist. It contains static/, r1/, r2/, media-map.json and
report.json. Dry runs read public repository metadata but never push. For
an entirely offline run, pass local --site-repo, --media-repo and --media2-repo.
Real deployments use KEYGEN_{SITE,MEDIA,MEDIA2}_DEPLOY_KEY_FILE and
KEYGEN_KNOWN_HOSTS_FILE. Each changed repository receives one orphan commit,
with a force-with-lease push to protect against an intervening remote edit.
The deployed site's .keygen-media-map.json carries assignments across builds;
scripts/site-media-map.json bootstraps the first deployment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPOS = ("keygen-bench-site", "keygen-bench-media", "keygen-bench-media-2")
BASES = ("https://microck.github.io/keygen-bench-media/media/",
         "https://microck.github.io/keygen-bench-media-2/media/")
MAP_FILE = ".keygen-media-map.json"
LIMIT = 900_000_000


def git(repo: Path, *args: str, worktree: Path | None = None,
        env: dict | None = None, input: str | None = None, strip: bool = True) -> str:
    command = ["git", "--git-dir", str(repo)]
    if worktree is not None:
        command += ["--work-tree", str(worktree)]
    result = subprocess.run(command + list(args), check=True, text=True,
                            capture_output=True, input=input, env=env)
    return result.stdout.strip() if strip else result.stdout

def open_remote(directory: Path, remote: str) -> tuple[Path, str]:
    """Fetch trees, not media blobs. Public HTTPS reads need no deploy secrets."""
    directory.parent.mkdir(parents=True, exist_ok=True)
    git(directory, "init", "--bare", "--quiet")
    git(directory, "remote", "add", "origin", remote)
    git(directory, "config", "remote.origin.promisor", "true")
    git(directory, "config", "remote.origin.partialclonefilter", "blob:none")
    ref = git(directory, "ls-remote", "origin", "refs/heads/main")
    if not ref:
        return directory, ""
    git(directory, "fetch", "--quiet", "--depth=1", "--filter=blob:none",
        "origin", "refs/heads/main")
    return directory, git(directory, "rev-parse", "FETCH_HEAD")


def remote_file(repo: Path, head: str, name: str) -> str | None:
    if not head or not git(repo, "ls-tree", head, "--", name):
        return None
    return git(repo, "show", f"{head}:{name}", strip=False)


def assign_media(source: Path, existing: dict, limit: int) -> tuple[dict, list[int]]:
    """Keep known assignments, then fit new files without relocating old URLs."""
    if not source.is_dir():
        raise ValueError(f"Missing media directory: {source}")
    files = sorted(source.iterdir())
    plan, sizes = {}, [0, 0]
    pending = []
    for path in files:
        if path.is_symlink() or not path.is_file() or path.suffix not in (".mp3", ".xm", ".flac"):
            raise ValueError(f"Unexpected media file: {path}")
        size = path.stat().st_size
        if path.name in existing:
            url = existing[path.name]
            choices = [i for i, base in enumerate(BASES) if url == base + path.name]
            if not choices:
                raise ValueError(f"Unknown media URL for {path.name}: {url}")
            slot = choices[0]
            plan[path.name] = slot
            sizes[slot] += size
        else:
            pending.append(path)
    if max(sizes) > limit:
        raise ValueError(f"Existing media assignments exceed {limit} bytes: {sizes}")
    # MP3/XM prefer r1, as in the original pipeline. Largest FLACs fit first.
    pending.sort(key=lambda p: (p.suffix == ".flac", -p.stat().st_size, p.name))
    for path in pending:
        size = path.stat().st_size
        slot = next((i for i in (0, 1) if sizes[i] + size <= limit), None)
        if slot is None:
            raise ValueError(f"No media repository has room for {path.name} ({size} bytes); sizes={sizes}")
        plan[path.name] = slot
        sizes[slot] += size
    return {name: BASES[slot] + name for name, slot in sorted(plan.items())}, sizes


def link_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def push_environment(slot: int) -> dict:
    name = ("SITE", "MEDIA", "MEDIA2")[slot]
    key = Path(os.environ[f"KEYGEN_{name}_DEPLOY_KEY_FILE"]).resolve()
    hosts = Path(os.environ["KEYGEN_KNOWN_HOSTS_FILE"]).resolve()
    if not key.is_file() or not hosts.is_file():
        raise ValueError("Missing SSH deploy key or known-hosts file")
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = ("ssh -i " + shlex.quote(str(key))
                              + " -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes"
                              + " -o UserKnownHostsFile=" + shlex.quote(str(hosts)))
    return env


def push_remote(remote: str) -> str:
    # The public read URL and the write URL refer to the same GitHub repository.
    if remote.startswith("https://github.com/"):
        return "git@github.com:" + remote.removeprefix("https://github.com/")
    return remote


def deploy(publication: Path, out: Path, remotes: tuple[str, str, str],
           seed: Path, site_url: str, dry_run: bool, limit: int = LIMIT) -> dict:
    if out.exists():
        raise ValueError("Use a new deployment output directory")
    if urlsplit(site_url).scheme != "https" or not urlsplit(site_url).hostname:
        raise ValueError("site-url must be an HTTPS origin")
    out.mkdir(parents=True)
    repos = [open_remote(out / ".repos" / f"{i}.git", remote)
             for i, remote in enumerate(remotes)]
    deployed = remote_file(*repos[0], MAP_FILE)
    existing = json.loads(deployed) if deployed is not None else json.loads(seed.read_text())
    mapping, sizes = assign_media(publication / "dist/media", existing, limit)
    map_path = out / "media-map.json"
    map_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    trees = [out / "static", out / "r1", out / "r2"]
    subprocess.run([sys.executable, str(ROOT / "web/classic/export_static.py"),
                    "--publication", str(publication), "--out", str(trees[0]),
                    "--site-url", site_url, "--media-map", str(map_path),
                    "--host", "github-pages"], check=True)
    for name in ("CNAME", ".nojekyll", "README.md"):
        old = remote_file(*repos[0], name)
        if old is not None:
            (trees[0] / name).write_text(old)
    if not (trees[0] / "README.md").exists():
        (trees[0] / "README.md").write_text(
            "Generated site for https://github.com/Microck/keygen-bench.\n")
    (trees[0] / MAP_FILE).write_text(map_path.read_text())
    for tree in trees[1:]:
        (tree / "media").mkdir(parents=True)
        (tree / ".nojekyll").write_text("")
        (tree / "README.md").write_text(
            "Media for https://github.com/Microck/keygen-bench, served with GitHub Pages: "
            "MP3 renders, XM modules and lossless FLAC loop sources. "
            "Generated by the site build; do not edit.\n")
    for name, url in mapping.items():
        slot = 0 if url.startswith(BASES[0]) else 1
        link_file(publication / "dist/media" / name, trees[slot + 1] / "media" / name)
    planned = []
    for (repo, head), tree in zip(repos, trees):
        git(repo, "add", "--all", "--", ".", worktree=tree)
        desired = git(repo, "write-tree")
        previous = git(repo, "rev-parse", f"{head}^{{tree}}") if head else ""
        total = sum(p.stat().st_size for p in tree.rglob("*") if p.is_file())
        if total > limit:
            raise ValueError(f"{tree.name} exceeds {limit} bytes including Pages files: {total}")
        planned.append({"repo": repo, "head": head, "tree": desired,
                        "changed": desired != previous, "bytes": total})
    # Preflight every key before any push. Media goes first so the new site URLs exist.
    environments = {}
    if not dry_run:
        environments = {i: push_environment(i) if remotes[i].startswith("https://github.com/")
                        or remotes[i].startswith("git@github.com:") else os.environ.copy()
                        for i, plan in enumerate(planned) if plan["changed"]}
    report = {"dry_run": dry_run, "media_bytes": sizes, "repositories": []}
    for i in (1, 2, 0):
        plan = planned[i]
        pushed = False
        if plan["changed"] and not dry_run:
            env = environments[i] | {"GIT_AUTHOR_NAME": "Microck", "GIT_COMMITTER_NAME": "Microck",
                                     "GIT_AUTHOR_EMAIL": "contact@micr.dev",
                                     "GIT_COMMITTER_EMAIL": "contact@micr.dev"}
            commit = git(plan["repo"], "commit-tree", plan["tree"],
                         input="Rebuild public site from keygen-bench\n", env=env)
            git(plan["repo"], "push", "--quiet",
                f"--force-with-lease=refs/heads/main:{plan['head']}",
                push_remote(remotes[i]), f"{commit}:refs/heads/main", env=env)
            pushed = True
        report["repositories"].append({"name": REPOS[i], "changed": plan["changed"],
                                       "pushed": pushed, "bytes": plan["bytes"]})
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--site-url", default="https://keygen.micr.dev")
    parser.add_argument("--seed-map", type=Path, default=ROOT / "scripts/site-media-map.json")
    for flag, repo in zip(("site", "media", "media2"), REPOS):
        parser.add_argument(f"--{flag}-repo", default=f"https://github.com/Microck/{repo}.git")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        report = deploy(args.publication.resolve(), args.out.resolve(),
                        (args.site_repo, args.media_repo, args.media2_repo),
                        args.seed_map.resolve(), args.site_url, args.dry_run)
    except (ValueError, KeyError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            print(exc.stderr or str(exc), file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
