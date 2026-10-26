"""Offline integration tests: synthetic publication and three local bare remotes."""
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "deploy_site.py"
spec = importlib.util.spec_from_file_location("deploy_site", SCRIPT)
deploy_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy_site)


class DeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pub = self.root / "publication"
        (self.pub / "dist/media").mkdir(parents=True)
        (self.pub / "dist/og").mkdir()
        (self.pub / "dist/evaluations").mkdir()
        (self.pub / "dist/evaluations/private.json").write_text("not public")
        (self.pub / "index.html").write_text("<html><head></head><body>\n</body></html>\n")
        run = {"name": "model (attempt 1)", "model_key": "model", "slug": "model-a1",
               "maker": "maker", "score": 75.0, "ranked": True, "rank": 1,
               "provenance": {"attempt_ordinal": 1}, "trace": {"rows": []},
               "media": {"audio": "media/model-a1.mp3", "xm": "media/model-a1.xm",
                         "wav": "media/model-a1.wav", "evaluation": "evaluations/private.json"}}
        (self.pub / "dist/data.json").write_text(json.dumps(
            {"generated": "2026-10-14T00:00:00Z", "runs": [run]}))
        info = {"title": "Test leaderboard", "description": "Synthetic publication",
                "image": "home.png"}
        (self.pub / "dist/og/meta.json").write_text(json.dumps(
            {"/": info, "/rankings": info, "/tracker/model": info}))
        for extension in ("mp3", "xm", "flac"):
            (self.pub / f"dist/media/model-a1.{extension}").write_bytes(extension.encode() * 7)
        self.seed = self.root / "seed.json"
        self.seed.write_text(json.dumps({"model-a1.flac": deploy_site.BASES[1] + "model-a1.flac"}))
        self.remotes = tuple(str(self.root / f"{name}.git") for name in ("site", "media", "media2"))
        for remote in self.remotes:
            self.run_git("init", "--bare", "--quiet", "--initial-branch=main", remote)
        self.out_count = 0

    @staticmethod
    def run_git(*args):
        return subprocess.run(["git", *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def head(self, index):
        return self.run_git("--git-dir", self.remotes[index], "rev-parse", "refs/heads/main")

    def deploy(self, dry_run=False, **kwargs):
        self.out_count += 1
        out = self.root / f"deployment-{self.out_count}"
        report = deploy_site.deploy(self.pub, out, self.remotes, self.seed,
                                    "https://keygen.micr.dev", dry_run, **kwargs)
        return out, report

    def test_workflow_sparse_checkout_preserves_bundle_contract_inputs(self):
        repository = SCRIPT.parents[1]
        workflow = (repository / ".github/workflows/deploy-site.yml").read_text()
        patterns = workflow.split("<<'PATTERNS'\n", 1)[1].split("PATTERNS", 1)[0]
        patterns = "\n".join(line.strip() for line in patterns.splitlines()) + "\n"
        fixture = self.root / "source"
        fixture.mkdir()
        shutil.copytree(repository / "benchmark", fixture / "benchmark",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (fixture / "scripts").mkdir()
        shutil.copyfile(repository / "scripts/build-ft2-linux.sh",
                        fixture / "scripts/build-ft2-linux.sh")
        self.run_git("init", "--quiet", str(fixture))
        self.run_git("-C", str(fixture), "add", ".")
        self.run_git("-C", str(fixture), "-c", "user.name=Fixture",
                     "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                     "commit", "--quiet", "-m", "synthetic contract inputs")
        sparse = self.root / "sparse"
        self.run_git("clone", "--quiet", "--no-checkout", str(fixture), str(sparse))
        subprocess.run(["git", "-C", str(sparse), "sparse-checkout", "set", "--no-cone", "--stdin"],
                       input=patterns, text=True, check=True, capture_output=True)
        self.run_git("-C", str(sparse), "checkout", "--quiet")
        subprocess.run([sys.executable, "-c",
                        "import sys; sys.path.insert(0, 'benchmark/contrib'); "
                        "from validate_bundle import contract; contract()"],
                       cwd=sparse, check=True, capture_output=True)

    def test_export_local_push_and_unchanged_skip(self):
        out, report = self.deploy()
        self.assertTrue(all(row["pushed"] for row in report["repositories"]))
        self.assertEqual([row["name"] for row in report["repositories"]],
                         [deploy_site.REPOS[1], deploy_site.REPOS[2], deploy_site.REPOS[0]])
        before = [self.head(i) for i in range(3)]
        mapping = json.loads((out / "media-map.json").read_text())
        self.assertEqual(mapping["model-a1.flac"], deploy_site.BASES[1] + "model-a1.flac")
        data = json.loads((out / "static/dist/data.json").read_text())
        self.assertEqual(data["runs"][0]["media"]["wav"], mapping["model-a1.flac"])
        self.assertNotIn("evaluation", data["runs"][0]["media"])
        self.assertNotIn("trace", data["runs"][0])
        self.assertTrue((out / "static/dist/traces/model-a1.json").is_file())
        self.assertFalse((out / "static/dist/evaluations").exists())
        self.assertFalse((out / "static/dist/media").exists())
        self.assertFalse((out / "static/.git").exists())
        self.assertTrue((out / "static/404.html").is_file())
        for name in ("CNAME", ".nojekyll", "README.md", deploy_site.MAP_FILE):
            self.assertTrue((out / "static" / name).is_file())
        _, second = self.deploy()
        self.assertFalse(any(row["changed"] or row["pushed"] for row in second["repositories"]))
        self.assertEqual(before, [self.head(i) for i in range(3)])
        for remote in self.remotes:
            self.assertEqual(self.run_git("--git-dir", remote, "rev-list", "--count", "main"), "1")

    def test_dry_run_never_pushes_and_cli_works(self):
        out = self.root / "cli-deployment"
        subprocess.run([os.sys.executable, str(SCRIPT), "--publication", str(self.pub),
                        "--out", str(out), "--seed-map", str(self.seed), "--dry-run",
                        "--site-repo", self.remotes[0], "--media-repo", self.remotes[1],
                        "--media2-repo", self.remotes[2]], check=True, capture_output=True, text=True)
        report = json.loads((out / "report.json").read_text())
        self.assertTrue(report["dry_run"])
        self.assertTrue(all(row["changed"] and not row["pushed"] for row in report["repositories"]))
        for remote in self.remotes:
            self.assertEqual(self.run_git("--git-dir", remote, "for-each-ref", "refs/heads"), "")

    def test_deployed_map_overrides_seed_and_preserves_site_files(self):
        self.deploy()
        repo, _ = deploy_site.open_remote(self.root / "edit.git", self.remotes[0])
        tree = self.root / "metadata"
        tree.mkdir()
        originals = {"CNAME": "keygen.micr.dev\n", ".nojekyll": "",
                     "README.md": "  Maintained README\n\n"}
        for name, content in originals.items():
            (tree / name).write_text(content)
        # Keep the deployed map in this synthetic maintainer edit.
        stored = self.run_git("--git-dir", self.remotes[0], "show", f"main:{deploy_site.MAP_FILE}")
        (tree / deploy_site.MAP_FILE).write_text(stored + "\n")
        deploy_site.git(repo, "add", "--all", worktree=tree)
        oid = deploy_site.git(repo, "write-tree")
        env = os.environ | {"GIT_AUTHOR_NAME": "Tester", "GIT_COMMITTER_NAME": "Tester",
                            "GIT_AUTHOR_EMAIL": "test@example.org", "GIT_COMMITTER_EMAIL": "test@example.org"}
        commit = deploy_site.git(repo, "commit-tree", oid, input="Metadata\n", env=env)
        deploy_site.git(repo, "push", "--force", self.remotes[0], f"{commit}:refs/heads/main")
        self.seed.write_text("{}")
        out, _ = self.deploy()
        mapping = json.loads((out / "media-map.json").read_text())
        self.assertEqual(mapping["model-a1.flac"], deploy_site.BASES[1] + "model-a1.flac")
        for name, content in originals.items():
            self.assertEqual((out / "static" / name).read_text(), content)

    def test_media_change_pushes_only_affected_repo(self):
        self.deploy()
        before = [self.head(i) for i in range(3)]
        (self.pub / "dist/media/model-a1.flac").write_bytes(b"new audio")
        _, report = self.deploy()
        self.assertEqual([row["name"] for row in report["repositories"] if row["pushed"]],
                         [deploy_site.REPOS[2]])
        self.assertEqual(before[:2], [self.head(i) for i in range(2)])
        self.assertNotEqual(before[2], self.head(2))

    def test_capacity_and_stable_placement(self):
        media = self.root / "capacity"
        media.mkdir()
        (media / "old.flac").write_bytes(b"x" * 8)
        (media / "new.mp3").write_bytes(b"x" * 5)
        (media / "new.flac").write_bytes(b"x" * 6)
        existing = {"old.flac": deploy_site.BASES[0] + "old.flac"}
        mapping, sizes = deploy_site.assign_media(media, existing, 12)
        self.assertEqual(sizes, [8, 11])
        self.assertEqual(mapping["old.flac"], existing["old.flac"])
        self.assertEqual(mapping["new.mp3"], deploy_site.BASES[1] + "new.mp3")
        with self.assertRaisesRegex(ValueError, "No media repository has room"):
            deploy_site.assign_media(media, existing, 10)
        with self.assertRaisesRegex(ValueError, "Existing media assignments exceed"):
            deploy_site.assign_media(media, existing, 7)

    def test_failures_happen_before_any_push(self):
        self.deploy()
        before = [self.head(i) for i in range(3)]
        (self.pub / "dist/media/oversized.flac").write_bytes(b"x" * 10000)
        with self.assertRaisesRegex(ValueError, "No media repository has room"):
            self.deploy(limit=100)
        self.assertEqual(before, [self.head(i) for i in range(3)])

    def test_unsafe_media_and_unknown_host_rejected(self):
        media = self.pub / "dist/media"
        with self.assertRaisesRegex(ValueError, "Unknown media URL"):
            deploy_site.assign_media(media, {"model-a1.mp3": "https://example.org/wrong"}, 10000)
        (media / "symlink.mp3").symlink_to(media / "model-a1.mp3")
        with self.assertRaisesRegex(ValueError, "Unexpected media file"):
            deploy_site.assign_media(media, {}, 10000)

    def test_force_with_lease_rejects_intervening_push(self):
        self.deploy()
        before = [self.head(i) for i in range(3)]
        (self.pub / "dist/media/model-a1.flac").write_bytes(b"updated")
        original_git = deploy_site.git

        def race(repo, *args, **kwargs):
            if args and args[0] == "push":
                # Simulate an outside maintainer replacing the target after fetch.
                remote = self.remotes[2]
                tree = self.run_git("--git-dir", remote, "rev-parse", "main^{tree}")
                env = os.environ | {"GIT_AUTHOR_NAME": "Other", "GIT_COMMITTER_NAME": "Other",
                                    "GIT_AUTHOR_EMAIL": "other@example.org", "GIT_COMMITTER_EMAIL": "other@example.org"}
                commit = self.run_git_with_env(remote, tree, env)
                self.run_git("--git-dir", remote, "update-ref", "refs/heads/main", commit)
            return original_git(repo, *args, **kwargs)

        with patch.object(deploy_site, "git", side_effect=race):
            with self.assertRaises(subprocess.CalledProcessError):
                self.deploy()
        self.assertEqual(before[:2], [self.head(i) for i in range(2)])

    @staticmethod
    def run_git_with_env(remote, tree, env):
        return subprocess.run(["git", "--git-dir", remote, "commit-tree", tree],
                              env=env, input="External change\n", check=True,
                              text=True, capture_output=True).stdout.strip()


if __name__ == "__main__":
    unittest.main()
