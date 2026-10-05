#!/usr/bin/env python3
"""Copy every benchmark run into the private data root and lay it out by model.

Layout (user 2026-10-05), ~/keygen-data/ on this laptop, not a git checkout:
  runs/<model>/attempt-1/ attempt-2/ attempt-3/   the three attempts the leaderboard ranks (best of 3)
  runs/<model>/other/<date>-<attempt>/             everything else: failed, retried, quota, legacy, other services
  runs/index.json                                  every attempt: model, slot, status, score, source
  _store/<host>/<path>/                            verified mirror of each source run root (audit copy)

Each run root found on a host (a directory with campaign.lock.json) is mirrored into _store with rsync and
every file's SHA-256 is checked against the source; sources are never modified. Laptop sources are mirrored
as hard links (no extra disk). runs/ is rebuilt from _store as hard links on every invocation, so a later
retry that becomes ranked simply moves into its attempt slot. Run roots with a RUNNING attempt are not
re-mirrored (their previous mirror, if any, is used). Credentials, private logs and isolated homes are never
copied.

  organize.py --dry-run      list run roots, sizes and the per-model layout; copies nothing
  organize.py                mirror, verify, rebuild runs/
"""
import argparse
import collections
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

DATA = Path.home() / "keygen-data"
STORE = DATA / "_store"
HOSTS = {
    "ashburn": ("ubuntu@100.92.22.120", "/home/ubuntu/keygen-full.OGHjBAkO"),
    "paris": ("oracle-paris", "/home/ubuntu/keygen-full.eALj54bh"),
    "laptop": (None, str(Path.home() / "workspace")),
}
# Directories whose run roots are copies of other roots (release sources, checkouts), never originals.
SKIP_PARTS = ("/repo", "/web-release-", "/sources/", "/.jj/", "/.git/", "/node_modules/")
# Extra non-run directories mirrored with their host: proofs a ranked attempt depends on.
EXTRA = {"ashburn": ["google-20261003/rescore-3-flash-rep-1"]}
# A rescored attempt is ranked from its rescore staging copy; the original stays under other/.
RESCORES = {("ashburn", "google-20261003/results/next-max-tier-prompt-v2-google-20261003/google-gemini-3-flash-rep-1"):
            "google-20261003/rescore-3-flash-rep-1/attempt/google-gemini-3-flash-rep-1"}
EXCLUDE = ["*.private.log", ".private/", "*.env.json", "isolated-host-home/", "__pycache__/", "*.lock"]
SHOWCASE = "next-max-tier-prompt-v2"
PLACEHOLDER = {"RESERVED", "SKIPPED_AFTER_SUCCESS"}
# Several routes served one model; plain folder names merge them. Ranked route order: vendor, Devin, Go, Vercel.
ROUTES = [("anthropic_oauth-", "anthropic"), ("codex_oauth-", "codex"), ("google-", "google"),
          ("devin-", "devin"), ("go-", "go"), ("vercel-", "vercel")]
ROUTE_ORDER = [name for _, name in ROUTES] + ["unknown"]
ALIASES = {"gemini-3-flash-preview": "gemini-3-flash", "claude-5-fable": "claude-fable-5",
           "nemotron-3-ultra": "nemotron-3-ultra-550b-a55b", "claude-opus-4.5-20251101": "claude-opus-4.5"}

FIND_ROOTS = r"""import json,os,sys
base=sys.argv[1];skip=json.loads(sys.argv[2]);out=[]
for d,ds,fs in os.walk(base):
    ds[:]=[x for x in ds if not any(p in os.path.join(d,x)+'/' for p in skip) and x not in ('isolated-host-home','submission')]
    if 'campaign.lock.json' in fs:
        busy=0;size=0
        for a,_,names in os.walk(d):
            for n in names:
                p=os.path.join(a,n)
                if not os.path.islink(p): size+=os.path.getsize(p)
                if n=='status.json' and os.path.dirname(a)==d:
                    try: busy+=json.load(open(p)).get('status')=='RUNNING'
                    except Exception: pass
        out.append({'path':os.path.relpath(d,base),'busy':busy,'bytes':size});ds[:]=[]
print(json.dumps(out))"""
LISTING = r"""import fnmatch,hashlib,json,os,sys
root=sys.argv[1];skip=json.loads(sys.argv[2]);out={}
for d,ds,fs in os.walk(root):
    rel=os.path.relpath(d,root)
    ds[:]=[x for x in ds if not any(fnmatch.fnmatch(x+'/',p) for p in skip)]
    for f in fs:
        p=os.path.join(d,f)
        if any(fnmatch.fnmatch(f,p_) for p_ in skip) or os.path.islink(p): continue
        h=hashlib.sha256()
        with open(p,'rb') as s:
            for b in iter(lambda:s.read(1<<20),b''): h.update(b)
        out[os.path.normpath(os.path.join(rel,f))]=h.hexdigest()
print(json.dumps(out))"""


def python(host, script, *args):
    """Run a stdlib Python snippet on a host (local when host is None) and parse its JSON output."""
    command = ["python3", "-c", script, *args]
    if host:
        command = ["ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=auto", "-o", "ControlPersist=120",
                   "-o", "ControlPath=/tmp/keygen-organize-%C", host,
                   " ".join("'" + a.replace("'", "'\\''") + "'" for a in command)]
    return json.loads(subprocess.run(command, capture_output=True, text=True, check=True, timeout=3600).stdout)


def mirror(name, rel, dry):
    host, base = HOSTS[name]
    source, target = f"{base}/{rel}", STORE / name / rel
    if dry:
        return
    target.mkdir(parents=True, exist_ok=True)
    command = ["rsync", "-a", "--delete", "--delete-excluded"] + [f"--exclude={p}" for p in EXCLUDE]
    if host:
        command += ["-e", "ssh -o BatchMode=yes -o ControlMaster=auto -o ControlPersist=120 "
                          "-o ControlPath=/tmp/keygen-organize-%C", f"{host}:{source}/", f"{target}/"]
    else:
        command += [f"--link-dest={source}", f"{source}/", f"{target}/"]
    subprocess.run(command, check=True, timeout=7200)
    expected = python(host, LISTING, source, json.dumps(EXCLUDE))
    actual = python(None, LISTING, str(target), json.dumps(EXCLUDE))
    if expected != actual:
        missing = sorted(set(expected) - set(actual))[:5]
        changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])[:5]
        raise SystemExit(f"checksum mismatch for {name}:{source}: missing {missing} changed {changed}")
    print(f"  verified {len(actual):6d} files  {name}:{rel}")


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def attempts_in_store():
    """Every attempt directory in the mirrored run roots, with the fields the layout needs."""
    out = []
    for lock in STORE.glob("*/**/campaign.lock.json"):
        root = lock.parent
        host = root.relative_to(STORE).parts[0]
        rel_root = str(root.relative_to(STORE / host))
        snapshot = (load(lock) or {}).get("snapshot") or {}
        campaign = snapshot.get("campaign") or snapshot.get("config") or {}
        models = {m["id"]: m for m in campaign.get("models") or []}
        for status_path in root.glob("*/status.json"):
            status = load(status_path)
            if not status:
                continue
            model_id = status.get("model")
            model_id = model_id.get("id") if isinstance(model_id, dict) else model_id
            directory = status_path.parent
            ranked_dir = RESCORES.get((host, f"{rel_root}/{directory.name}"))
            scored_dir = STORE / host / ranked_dir if ranked_dir else directory
            craft = ((load(scored_dir / "profile.json") or {}).get("craft"))
            out.append({"host": host, "dir": directory, "ranked_dir": scored_dir, "campaign_id": campaign.get("campaign_id"),
                        "attempt_id": status.get("attempt_id") or directory.name, "rep": status.get("repetition"),
                        "model_id": model_id, "model": (models.get(model_id) or {}).get("model"),
                        "status": status.get("status"), "category": status.get("failure_category"),
                        "score": craft.get("craft_score") if isinstance(craft, dict) else None,
                        "rescored": bool(ranked_dir), "started": status.get("started_at"),
                        "finished": status.get("finished_at")})
    return out


def route(attempt):
    model_id, model = attempt["model_id"] or "", attempt["model"] or ""
    for prefix, name in ROUTES:
        if model_id.startswith(prefix):
            return name
    if model.startswith("vercel-") or "/" in model:
        return "vercel"
    return {"claude": "anthropic", "gpt": "codex"}.get(model.split("-")[0], "unknown")


def plain_name(attempt):
    name = (attempt["model"] or attempt["model_id"] or attempt["dir"].name).split("/")[-1]
    name = re.sub(r"^(vercel-|go-)", "", name)
    name = re.sub(r"-(messages|chat-final|chat)$", "", name)
    # Devin writes versions with dashes (glm-5-3); every other route uses dots (glm-5.3).
    name = re.sub(r"(\d)-(\d+)(?![\w.])|(\d)-(\d+)(?=-)", lambda m: f"{m[1] or m[3]}.{m[2] or m[4]}", name, count=1)
    return ALIASES.get(name, name)


def classify(attempts):
    """Per model: the ranked route is the first in ROUTE_ORDER with three showcase ordinals; each ordinal's
    ranked attempt is its latest-started attempt in that route. Everything else is other/."""
    models = collections.defaultdict(list)
    for attempt in attempts:
        if attempt["status"] in PLACEHOLDER:
            continue
        attempt["route"], attempt["name"] = route(attempt), plain_name(attempt)
        attempt["slot"] = "other"
        models[attempt["name"]].append(attempt)
    for name, xs in models.items():
        showcase = [x for x in xs if (x["campaign_id"] or "").startswith(SHOWCASE)]
        best = {}
        for r in sorted({x["route"] for x in showcase}, key=ROUTE_ORDER.index):
            per_rep = {}
            for x in sorted((x for x in showcase if x["route"] == r), key=lambda x: x["started"] or 0):
                per_rep[x["rep"]] = x
            if len(per_rep) > len(best):
                best = per_rep
            if len(best) == 3:
                break
        for rep, x in best.items():
            x["slot"] = f"attempt-{rep}"
    return models


def other_label(attempt, taken):
    when = attempt["started"] or attempt["finished"]
    date = datetime.datetime.fromtimestamp(when, datetime.timezone.utc).strftime("%Y-%m-%d") if when else "undated"
    label = f"{date}-{attempt['dir'].name}"
    n = 1
    while label + ("" if n == 1 else f"-{n}") in taken:
        n += 1
    label += "" if n == 1 else f"-{n}"
    taken.add(label)
    return label


def build(models, dry):
    index, staging = {}, DATA / "runs.new"
    if not dry:
        shutil.rmtree(staging, ignore_errors=True)
    for name in sorted(models):
        taken, rows = set(), []
        for x in sorted(models[name], key=lambda x: (x["slot"], x["started"] or 0)):
            target = x["slot"] if x["slot"] != "other" else f"other/{other_label(x, taken)}"
            source = x["ranked_dir"] if x["slot"] != "other" else x["dir"]
            row = {"slot": x["slot"], "path": target, "attempt_id": x["attempt_id"], "status": x["status"],
                   "failure_category": x["category"], "score": x["score"] if x["slot"] != "other" or not x["rescored"] else None,
                   "route": x["route"], "campaign_id": x["campaign_id"], "rescored": x["rescored"] and x["slot"] != "other",
                   "source": f"{x['host']}:{source.relative_to(STORE / x['host'])}"}
            rows.append(row)
            if dry:
                continue
            destination = staging / name / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["cp", "-al", str(source), str(destination)], check=True)
            (destination / "ATTEMPT.json").write_text(json.dumps(row, indent=2) + "\n")
        ranked = [r for r in rows if r["slot"] != "other"]
        index[name] = {"route": ranked[0]["route"] if ranked else None, "ranked": len(ranked),
                       "best": max((r["score"] for r in ranked if r["score"] is not None), default=None), "attempts": rows}
        print(f"  {name:28s} {str(index[name]['route']):9s} {len(ranked)} ranked {len(rows) - len(ranked):3d} other  "
              + " · ".join(str(r["score"] if r["score"] is not None else r["status"]) for r in ranked))
    if dry:
        return
    (staging / "index.json").write_text(json.dumps(
        {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ranking": "best of 3", "models": index},
        indent=2) + "\n")
    old = DATA / "runs.old"
    shutil.rmtree(old, ignore_errors=True)
    if (DATA / "runs").exists():
        os.rename(DATA / "runs", old)
    os.rename(staging, DATA / "runs")
    shutil.rmtree(old, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for name, (host, base) in HOSTS.items():
        roots = python(host, FIND_ROOTS, base, json.dumps(SKIP_PARTS))
        print(f"{name}: {len(roots)} run roots, {sum(r['bytes'] for r in roots) / 1e9:.2f} GB")
        for r in roots + [{"path": p, "busy": 0, "bytes": 0} for p in EXTRA.get(name, [])]:
            if r["busy"]:
                print(f"  in flight ({r['busy']} RUNNING), previous mirror kept: {r['path']}")
                continue
            mirror(name, r["path"], args.dry_run)
    if not STORE.exists():
        print("no mirror yet; run without --dry-run first")
        return
    build(classify(attempts_in_store()), args.dry_run)


if __name__ == "__main__":
    main()
