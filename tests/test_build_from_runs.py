"""Offline publication tests with small synthetic ranked attempts."""
import errno
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "web/classic"), str(ROOT), str(ROOT / "benchmark")]
import build_from_runs as builder
from benchmark.report import digest
from benchmark.score import benchmark_score
from collect_public import response_usage, sha256
from build import estimate_request_cost
from check_runs_parity import compare
from benchmark.tests.test_contrib import make_bundle


class RunsBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runs = self.root / "runs"
        self.site = self.root / "site"
        self.site.mkdir()
        self.scores = self.root / "scores.json"
        self.model = {"id": "test-model", "model": "test-model", "tier": {"level": "high"},
                      "effective_settings": {"output_limit": 64000}}
        self.config = {"schema": "keygen-native-campaign-3", "campaign_id": "next-max-tier-test",
                       "models": [self.model], "prompts": {"version": "prompt-v2"}}
        self.evidence = []
        self.identities = {}
        self.make_attempt(1, 7.0)
        self.make_attempt(2, 8.0)
        self.write_site()

    def test_response_receipts_recover_cached_usage_and_price_each_context(self):
        directory = self.root / "receipts"
        directory.mkdir()
        receipts = [
            {"usage": {"input_tokens": 100000, "output_tokens": 1000,
                       "input_tokens_details": {"cached_tokens": 90000, "cache_write_tokens": 0}}},
            {"usage": {"input_tokens": 300000, "output_tokens": 2000,
                       "input_tokens_details": {"cached_tokens": 280000, "cache_write_tokens": 0}}},
        ]
        (directory / "transport.jsonl").write_text("\n".join(json.dumps(row) for row in receipts))
        totals = {"requests": 2, "prompt_tokens": 400000, "completion_tokens": 3000, "cached_tokens": 0}
        requests = response_usage(directory, totals)
        self.assertEqual(sum(row["cached_tokens"] for row in requests), 370000)
        price = {"input_usd_per_m": 1, "cached_input_usd_per_m": .05, "output_usd_per_m": 5,
                 "tiers": [{"min_prompt_tokens": 272001, "input_usd_per_m": 2,
                            "cached_input_usd_per_m": .1, "output_usd_per_m": 7.5}]}
        self.assertAlmostEqual(sum(estimate_request_cost(row, price) for row in requests), .1025)
        self.assertIsNone(response_usage(directory, {**totals, "requests": 3}))
        self.assertIsNone(response_usage(directory, {**totals, "prompt_tokens": 400001}))

    def tearDown(self):
        self.temporary.cleanup()

    def dump(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n")

    def make_attempt(self, ordinal, enjoyment, *, directory=None, status=None, identity=None, xm=None):
        """Write one scored slot: a maintainer campaign slot of test-model unless `identity` is given."""
        directory = directory or self.runs / "test-model" / f"attempt-{ordinal}"
        directory.mkdir(parents=True)
        attempt_id = (status or {}).get("attempt_id", f"test-model-rep-{ordinal}")
        status = {"attempt_id": attempt_id, "repetition": ordinal, "model": self.model,
                  "status": "RENDERED_UNSCORED", "render": "ok", "eligible": True, "failure_category": None,
                  "totals": {"requests": 2, "prompt_tokens": 100, "completion_tokens": 200},
                  "wall_seconds": 90, "module": {"name": f"Synthetic {ordinal}", "channels": 4}, **(status or {})}
        self.dump(directory / "status.json", status)
        self.dump(directory / "ATTEMPT.json", identity or {"attempt_id": attempt_id, "slot": directory.name})
        if identity is None:
            self.dump(directory / "campaign.json", {"campaign": self.config, "sha256": digest(self.config)})
        wav = directory / "canonical/canonical.wav"
        wav.parent.mkdir()
        with wave.open(str(wav), "wb") as stream:
            stream.setnchannels(2)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            stream.writeframes(b"\x01\x00\x01\x00" * 4410)
        target = directory / "submission/tune.xm"
        target.parent.mkdir()
        if xm:
            shutil.copyfile(xm, target)
        else:
            target.write_bytes(f"synthetic xm {directory.parent.name} {ordinal}".encode())
        xm = target
        structure = {"arrangement_score": 1.0, "sequence_coverage": 1.0, "used_longest_sample_seconds": 1.0,
                     "used_sample_seconds_total": 5.0, "instruments_used": 4, "channels_used": 4, "note_ons": 600}
        audio = {"duration_seconds": 0.1, "clip_fraction": 0.0, "dc_offset": 0.0, "true_peak_dbtp": -2.0,
                 "lufs_integrated": -18.0, "silent_fraction": 0.0, "longest_silence_seconds": 0.0,
                 "tail_silence_seconds": 0.0, "block_rms_range_db": 8.0, "phrase_rms_range_db": 3.0,
                 "spectral": {"tonal_organization": 1.0, "sustained_noise_fraction": 0.0}}
        loop = {"quality_score": 1.0, "analysis_duration_seconds": 0.1, "first_pass_audible_seconds": 0.1}
        craft = benchmark_score(structure, audio, loop, {"ratings": {"content_enjoyment": enjoyment,
            "production_quality": 7.0, "content_usefulness": 6.0, "production_complexity": 5.0}, "analyzed_seconds": 0.1})
        profile = {"score_version": "listener-v1", "evaluation_schema": 2, "eligible": True,
            "evaluation_status": "evaluated", "cacheable": True, "model": self.model["model"], "status": status["status"],
            "craft": craft, "audio": audio, "structure": structure, "loop": loop, "flags": [], "process": {},
            "mix": {"clarity_score": 1.0, "masking_fraction": 0.0}, "inputs": {"artifacts": {
                "status.json": sha256(directory / "status.json"), "submission/tune.xm": sha256(xm),
                "canonical/canonical.wav": sha256(wav)}}}
        self.dump(directory / "profile.json", profile)
        self.evidence.append({"eligible": True, "xm_sha256": sha256(xm), "canonical_wav_sha256": sha256(wav),
                              "new_score": craft["craft_score"], "craft": craft, "spectral": audio["spectral"]})
        if identity is None:
            self.identities[sha256(xm)] = {"slug": f"historic-attempt-{ordinal}", "model_key": self.model["model"],
                                          "name": f"{self.model['model']} (max-tier, attempt {ordinal})", "attempt_ordinal": ordinal}
        return directory

    def write_site(self):
        self.dump(self.scores, {"score_version": "listener-v1", "attempts": self.evidence, "listener": {"model": "fake"}})
        models = {"test-model", self.model["model"]}
        self.dump(self.site / "model-metadata.json", {model: {"release_date": "2026-01-01"} for model in models})
        self.dump(self.site / "prices.json", {"models": [{"id": model, "maker": "Test maker",
            "input_usd_per_m": 1, "cached_input_usd_per_m": 0, "output_usd_per_m": 2,
            "source_url": "https://openai.com/pricing"} for model in sorted(models)]})
        self.dump(self.site / "spend.json", {"total_usd": 0})
        self.dump(self.site / "published-identities.json", self.identities)
        self.dump(self.site / "publication-policy.json", {"excluded_models": {}})

    def build(self, out="publication", **kwargs):
        return builder.build_from_runs(self.runs, self.root / out, self.scores,
                                       site=self.site, cards=False, submissions=self.root / "submissions", **kwargs)

    def make_community(self, model_dir, name="2026-01-02-fixture"):
        """Seal a synthetic bundle and retain reviewed slots as validate_bundle --publication-out does."""
        bundle = self.root / "submissions" / model_dir / name
        bundle.parent.mkdir(parents=True, exist_ok=True)
        make_bundle(bundle)
        environment = json.loads((bundle / "manifest.json").read_text())["environment"]
        frozen = environment["contract"]
        self.model = environment["model"]
        spec = {"model": self.model, "config": {"schema": "keygen-native-campaign-3", "models": [self.model],
                "image": environment["images"]["agent"], "visualizer_image": environment["images"]["visualizer"],
                "prompts": frozen["prompt"], "limits": frozen["limits"], "native": frozen["native"],
                "policies": {"attempt_selection": frozen["attempt_selection"]}}}
        bundle_sha256 = sha256(bundle / "manifest.json")
        publication = {"kind": "community-submitted", "bundle_sha256": bundle_sha256,
                       "note": "Community-submitted; maintainer re-scored. Not comparatively ranked."}
        for ordinal in range(1, 4):
            source, directory = bundle / f"attempt-{ordinal}", self.runs / model_dir / "community" / name / f"attempt-{ordinal}"
            status = json.loads((source / "status.json").read_text())
            identity = {"attempt_id": status["attempt_id"], "slot": directory.name,
                        "campaign_id": "community-" + bundle_sha256, "publication": publication}
            if (source / "tune.xm").is_file():
                # The synthetic bundle repeats one module, so its listener evidence must agree.
                self.make_attempt(ordinal, 6.0, directory=directory, status=status, identity=identity, xm=source / "tune.xm")
            else:
                self.dump(directory / "status.json", status)
                self.dump(directory / "ATTEMPT.json", identity)
                self.dump(directory / "profile.json", {"score_version": "listener-v1", "evaluation_schema": 2,
                    "eligible": False, "evaluation_status": "ineligible", "cacheable": True, "status": status["status"],
                    "model": self.model["model"], "craft": {"craft_score": None}, "inputs": {"artifacts": {
                        "status.json": sha256(directory / "status.json"), "submission/tune.xm": None,
                        "canonical/canonical.wav": None}}})
            self.dump(directory / "spec.json", spec)
            for filename in ("trajectory.json", "transport.jsonl"):
                shutil.copyfile(source / filename, directory / filename)
        self.write_site()
        return bundle

    def test_best_of_three_links_and_other_ignored(self):
        self.dump(self.runs / "test-model/other/bad/status.json", {"unexpected": "never read"})
        data = self.build(no_media=True)
        self.assertEqual(data["eligible_attempts"], 2)
        group = data["repetition_groups"][0]
        self.assertEqual(group["ranked_slug"], "historic-attempt-2")
        self.assertEqual(group["best_ordinal"], 2)
        self.assertEqual(group["attempts"][2]["status"], "RESERVED")
        self.assertEqual(data["runs"][0]["attempt_of"], "historic-attempt-2")
        self.assertEqual(data["runs"][1]["rank"], 1)
        self.assertTrue((self.root / "publication/index.html").is_file())
        self.assertEqual(group["pending"], 1)
        self.assertFalse((self.root / "publication/dist/.verified").exists())
        self.assertNotIn("results", data["runs"][0]["cohort"])
        self.assertNotEqual(data["runs"][0]["provenance"]["evaluation_fingerprint"],
                            data["runs"][0]["provenance"]["source_evaluation"]["evaluation_fingerprint"])

    def test_verified_stage_moves_across_filesystems(self):
        with patch("os.rename", side_effect=OSError(errno.EXDEV, "Invalid cross-device link")) as rename:
            data = self.build(no_media=True)
        self.assertEqual(rename.call_count, 2)
        self.assertEqual(data["eligible_attempts"], 2)
        self.assertTrue((self.root / "publication/dist/data.json").is_file())
        self.assertFalse((self.root / "publication/dist/.verified").exists())

    def test_display_names_drop_route_free_and_contributor_tags(self):
        self.assertEqual(builder.display_name("meta/muse-spark-1.13-contributor:free"), "muse-spark-1.13")
        self.assertEqual(builder.display_name("stepfun/step-3.7-flash:free"), "step-3.7-flash")
        self.assertEqual(builder.display_name("longcat-2.5-preview-free"), "longcat-2.5-preview")

    def test_minimax_free_route_uses_maker_api_list_price(self):
        route_id = "minimax/minimax-m3.1-flash:free"
        source_url = "https://www.minimax.io/blog/minimax-m31f"
        model_key = builder.display_name(builder.price_id(route_id))
        price = {"id": model_key, "maker": "MiniMax", "source_url": source_url,
                 "input_usd_per_m": 0.15, "cached_input_usd_per_m": 0.015,
                 "output_usd_per_m": 0.6}
        published = builder.public_price(price)

        self.assertEqual(model_key, "minimax-m3.1-flash")
        self.assertEqual(published, {
            "input_usd_per_m": 0.15,
            "cached_input_usd_per_m": 0.015,
            "output_usd_per_m": 0.6,
            "source_url": source_url,
        })
        self.assertAlmostEqual(builder.estimate_cost({
            "prompt_tokens": 957, "cached_tokens": 186, "completion_tokens": 100,
        }, published, round_digits=None), 0.00017844)

    def test_new_attempt_uses_existing_model_metadata(self):
        self.identities.clear()
        self.write_site()
        data = self.build(no_media=True)
        self.assertTrue(data["runs"][0]["slug"].startswith("test-model-a1-"))
        self.assertEqual(data["runs"][0]["model_key"], "test-model")

    @unittest.skipUnless(shutil.which("ffmpeg"), "requires MP3 encoder")
    def test_campaign_collector_keeps_default_wav_layout(self):
        directory = self.runs / "test-model/attempt-1"
        report_root = self.root / "report"
        report_root.mkdir()
        row, _, campaign_hash = builder.load_attempt(directory, report_root)
        output = self.root / "legacy-snapshot"
        output.mkdir()
        run = builder.public_run(row, {"attempted_count": 2}, directory, output,
                                 {"campaign_sha256": campaign_hash}, "repetitions", {})
        self.assertEqual(run["media"]["wav"], "media/test-model-a1.wav")
        self.assertEqual(run["provenance"]["public_media_sha256"]["wav"],
                         row["profile"]["inputs"]["artifacts"]["canonical/canonical.wav"])

    def test_parity_checks_links_and_listener_best_scores(self):
        data = self.build(no_media=True)
        baseline = json.loads(json.dumps(data))
        self.assertEqual(compare(data, baseline, baseline)["failures"], [])
        data["runs"][0]["slug"] = "changed-link"
        data["runs"][1]["score"] = 0
        failures = compare(data, baseline, baseline)["failures"]
        self.assertTrue(any(item["field"] == "slug" for item in failures))
        self.assertTrue(any(item["field"] == "listener_best_score" for item in failures))

    def test_registry_slug_cannot_escape_publication(self):
        next(iter(self.identities.values()))["slug"] = "../../outside"
        self.write_site()
        with self.assertRaisesRegex(ValueError, "Invalid public slug"):
            self.build(no_media=True)
        self.assertFalse((self.root / "outside").exists())

    def test_ranked_slots_cannot_mix_models(self):
        self.model = dict(self.model, id="other-model", model="other-model")
        self.config = dict(self.config, models=[self.model])
        directory = self.make_attempt(3, 9.0)
        profile = json.loads((directory / "profile.json").read_text())
        profile["model"] = "other-model"
        self.dump(directory / "profile.json", profile)
        self.write_site()
        with self.assertRaisesRegex(ValueError, "ranked slots mix model identities"):
            self.build(no_media=True)

    def test_missing_evidence_lists_attempt(self):
        self.evidence.pop()
        self.write_site()
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "test-model/attempt-2"):
            self.build(no_media=True)

    def test_changed_xm_fails_integrity(self):
        (self.runs / "test-model/attempt-1/submission/tune.xm").write_bytes(b"changed")
        with patch.dict(os.environ, {"KEYGEN_LISTENER_PYTHON": "unused"}), self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.build(no_media=True)

    def test_canonical_evidence_binding(self):
        self.evidence[0]["canonical_wav_sha256"] = "0" * 64
        self.write_site()
        with self.assertRaisesRegex(ValueError, "canonical WAV mismatch"):
            self.build(no_media=True)

    def test_reviewed_withheld_model_is_not_read(self):
        self.dump(self.runs / "withheld/attempt-1/ATTEMPT.json", {"malformed": True})
        self.dump(self.site / "publication-policy.json", {"excluded_models": {"withheld": "reviewed exclusion"}})
        data = self.build(no_media=True)
        self.assertEqual(data["eligible_attempts"], 2)
        self.assertEqual(data["excluded_models"][0]["model_key"], "withheld")

    def test_unknown_metadata_fails(self):
        self.dump(self.site / "model-metadata.json", {})
        with self.assertRaisesRegex(ValueError, "Unknown model metadata"):
            self.build(no_media=True)

    def test_explicit_unknown_release_date_is_not_fabricated(self):
        self.dump(self.site / "model-metadata.json", {"test-model": {
            "release_date": None, "release_date_note": "No verified maker announcement."}})
        data = self.build(no_media=True)
        self.assertEqual(len(data["runs"]), 2)
        metadata = json.loads((self.root / "publication/dist/model-metadata.json").read_text())
        self.assertIsNone(metadata["test-model"]["release_date"])

    def maintainer_slots(self, model_dir, ordinals=(1, 2), enjoyment=8.0):
        """Unregistered maintainer slots, so their slugs come from the builder's own formula."""
        for ordinal in ordinals:
            directory = self.make_attempt(ordinal, enjoyment + ordinal, directory=self.runs / model_dir / f"attempt-{ordinal}",
                                          status={"attempt_id": f"{model_dir}-rep-{ordinal}"})
            self.identities.pop(sha256(directory / "submission/tune.xm"))
        self.write_site()

    def test_community_set_publishes_beside_existing_maintainer_slots(self):
        bundle = self.make_community("synthetic-fixture")
        self.config = dict(self.config, models=[self.model])
        self.maintainer_slots("synthetic-fixture")
        community = self.runs / "synthetic-fixture/community"
        shutil.move(community, self.root / "held")
        before = {run["slug"]: run["rank"] for run in self.build("before", no_media=True)["runs"]}
        shutil.move(self.root / "held", community)
        data = self.build("after", no_media=True)
        groups = {group["model_key"]: group for group in data["repetition_groups"]}
        community_key = "synthetic-fixture-community-2026-01-02-fixture"
        self.assertEqual(set(groups), {"test-model", "synthetic-fixture", community_key})
        maintainer, community = groups["synthetic-fixture"], groups[community_key]
        # Maintainer slots keep their public URLs and ranks and stay in the ranked condition.
        self.assertEqual({run["slug"]: run["rank"] for run in data["runs"] if not run["exhibition"]}, before)
        self.assertEqual(maintainer["best_ordinal"], 2)
        self.assertEqual(maintainer["cohort_key"], "highest-declared-tier/prompt-v2")
        # Every contributor attempt stays visible in its own unranked cohort, including the failure.
        self.assertEqual([a["ordinal"] for a in community["attempts"]], [1, 2, 3])
        self.assertEqual([a["eligible"] for a in community["attempts"]], [True, True, False])
        self.assertEqual(community["attempts"][2]["failure_category"], "INFRA")
        self.assertEqual(community["cohort_key"], "community/" + sha256(bundle / "manifest.json"))
        runs = [run for run in data["runs"] if run["model_key"] == community_key]
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertTrue(run["exhibition"])
            self.assertIsNone(run["rank"])
            self.assertFalse(run["ranked"])
            self.assertEqual(run["release_date"], "2026-01-01")
            self.assertEqual(run["provenance"]["kind"], "community-submitted")
        self.assertEqual(sorted(run["rank"] for run in data["runs"] if run["rank"]), [1, 2])
        self.assertEqual(data["ranked_results"], 2)
        self.assertTrue(all(run["slug"].startswith("synthetic-fixture-community-2026-01-02-fixture-a") for run in runs))

    def test_community_set_may_be_the_only_set_of_a_model(self):
        self.make_community("synthetic-fixture")
        data = self.build(no_media=True)
        self.assertEqual({group["model_key"] for group in data["repetition_groups"]},
                         {"test-model", "synthetic-fixture-community-2026-01-02-fixture"})
        self.assertEqual(data["ranked_results"], 1)

    def test_community_receipts_only_publish_from_their_submission_directory(self):
        self.make_community("synthetic-fixture")
        community = self.runs / "synthetic-fixture/community/2026-01-02-fixture"
        # A receipt in a maintainer slot would replace maintainer evidence and is rejected.
        shutil.move(community / "attempt-1", self.runs / "synthetic-fixture/attempt-1")
        with self.assertRaisesRegex(ValueError, "community receipts belong only under"):
            self.build(no_media=True)
        shutil.move(self.runs / "synthetic-fixture/attempt-1", community / "attempt-1")
        # A receipt must name the submission directory it was reviewed from.
        community.rename(community.with_name("2026-01-03-fixture"))
        with self.assertRaisesRegex(ValueError, "missing reviewed community bundle"):
            self.build(no_media=True)

    def test_maintainer_slots_ignore_campaign_naming(self):
        """A maintainer campaign named without the max-tier prefix stays in the ranked condition."""
        self.config = dict(self.config, campaign_id="terra-like-20261026")
        for ordinal in (1, 2):
            directory = self.runs / "test-model" / f"attempt-{ordinal}"
            self.dump(directory / "campaign.json", {"campaign": self.config, "sha256": digest(self.config)})
        data = self.build(no_media=True)
        self.assertEqual({run["cohort"]["key"] for run in data["runs"]}, {"highest-declared-tier/prompt-v2"})
        self.assertEqual([run["rank"] for run in data["runs"] if run["rank"]], [1])
        self.assertFalse(any(run["exhibition"] for run in data["runs"]))

    def test_publication_out_must_be_a_community_directory(self):
        bundle = make_bundle(self.root / "2026-01-02-fixture")
        for target in (self.runs / "test-model", self.runs / "test-model/community/other-name"):
            completed = subprocess.run([sys.executable, str(ROOT / "benchmark/contrib/validate_bundle.py"), str(bundle),
                "--rescore", "--trusted-agent-image", "unused", "--rescore-out", str(self.root / "review"),
                "--publication-out", str(target)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("runs/<model>/community/<bundle directory name>", completed.stderr)
        self.assertEqual(sorted(path.name for path in (self.runs / "test-model").iterdir()), ["attempt-1", "attempt-2"])

    @unittest.skipUnless(shutil.which("flac"), "requires lossless encoder")
    def test_public_review_preserves_hashes_and_removes_home_prefixes(self):
        from benchmark.contrib.validate_bundle import publish_review
        bundle, review = self.root / "bundle", self.root / "review"
        self.dump(bundle / "manifest.json", {"sealed": "synthetic fixture"})
        self.dump(review / "verification.json", {"bundle_sha256": sha256(bundle / "manifest.json")})
        for ordinal in range(1, 4):
            directory = review / f"attempt-{ordinal}"
            for name in ("status.json", "trajectory.json", "environment.json", "spec.json"):
                self.dump(directory / name, {})
            self.dump(directory / "ATTEMPT.json", {"publication": {"kind": "community-submitted"}})
            self.dump(directory / "profile.json", {"inputs": {"binary_sha256": "a" * 64,
                "path": "/home/private-user/venv/bin/python"}, "craft": {"craft_score": 70}})
            (directory / "transport.jsonl").write_text("")
        published = self.root / "published-review"
        publish_review(bundle, review, published)
        for ordinal in range(1, 4):
            directory = published / f"attempt-{ordinal}"
            profile = json.loads((directory / "profile.json").read_text())
            self.assertEqual(profile["inputs"]["path"], "HOME/venv/bin/python")
            self.assertEqual(profile["inputs"]["binary_sha256"], "a" * 64)
            self.assertEqual(profile["craft"]["craft_score"], 70)
            identity = json.loads((directory / "ATTEMPT.json").read_text())
            self.assertEqual(identity["publication"]["raw_profile_sha256"],
                             sha256(review / f"attempt-{ordinal}/profile.json"))
        self.assertIn("/home/private-user", (review / "attempt-1/profile.json").read_text())

    @unittest.skipUnless(importlib.util.find_spec("PIL") and importlib.util.find_spec("fontTools"),
                         "requires OG image dependencies")
    def test_community_og_has_routes_but_no_comparative_rank(self):
        dist = self.root / "community-cards"
        self.dump(dist / "data.json", {"generated": "2026-01-01", "runs": [{
            "model_key": "test-model", "slug": "test-model-a1", "name": "test-model (attempt 1)",
            "maker": "OpenAI", "score": 70.0, "exhibition": True,
            "publication_note": "Community-submitted, not comparatively ranked.",
            "provenance": {"attempt_ordinal": 1}, "listener": {
                "content_enjoyment": 7.0, "production_quality": 8.0, "production_complexity": 5.0}}]})
        subprocess.run([sys.executable, str(ROOT / "web/classic/build_og.py"),
                        "--dist", str(dist)], check=True, capture_output=True)
        metadata = json.loads((dist / "og/meta.json").read_text())
        description = metadata["/tracker/test-model"]["description"]
        self.assertIn("not comparatively ranked", description)
        self.assertNotIn("Rank 1", description)
        self.assertTrue((dist / "og/test-model.png").is_file())

    def test_missing_release_date_fails(self):
        self.dump(self.site / "model-metadata.json", {"test-model": {}})
        with self.assertRaisesRegex(ValueError, "Missing release_date"):
            self.build(no_media=True)

    def test_hash_proven_post_evaluation_error_is_recovered(self):
        path = self.runs / "test-model/attempt-1/status.json"
        status = json.loads(path.read_text())
        status.update(status="FINALIZATION_ERROR", finalization_error={"message": "archive upload failed"})
        self.dump(path, status)
        data = self.build(no_media=True)
        self.assertEqual(data["runs"][0]["score"], 70)
        self.assertEqual(data["runs"][0]["status"], "RENDERED_UNSCORED")

    def test_changed_status_fails_integrity(self):
        path = self.runs / "test-model/attempt-1/status.json"
        status = json.loads(path.read_text())
        status["wall_seconds"] = 100
        self.dump(path, status)
        with self.assertRaisesRegex(ValueError, "does not match current status"):
            self.build(no_media=True)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("flac"), "requires media encoders")
    def test_media_and_compressed_canonical(self):
        wav = self.runs / "test-model/attempt-1/canonical/canonical.wav"
        subprocess.run(["flac", "--silent", "--keep-foreign-metadata",
                        "-o", str(wav) + ".flac", str(wav)], check=True)
        wav.unlink()
        data = self.build()
        for run in data["runs"]:
            for extension in ("mp3", "xm", "flac"):
                path = self.root / "publication/dist/media" / f"{run['slug']}.{extension}"
                self.assertTrue(path.is_file())
                self.assertEqual(sha256(path), run["provenance"]["public_media_sha256"][extension])
                if extension == "flac":
                    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path),
                                          "-f", "s16le", "-"], check=True, capture_output=True).stdout
                    self.assertEqual(pcm, b"\x01\x00\x01\x00" * 4410)
        self.assertFalse(list((self.root / "publication/dist/media").glob("*.wav")))

    def test_standalone_configuration_adapter(self):
        for directory in (self.runs / "test-model").glob("attempt-*"):
            (directory / "campaign.json").unlink()
            self.dump(directory / "spec.json", {"config": self.config, "model": self.model})
            identity = json.loads((directory / "ATTEMPT.json").read_text())
            identity["campaign_id"] = "standalone-test"
            self.dump(directory / "ATTEMPT.json", identity)
        data = self.build(no_media=True)
        self.assertEqual(data["eligible_attempts"], 2)
        self.assertEqual(data["runs"][0]["cohort"]["key"], "highest-declared-tier/prompt-v2")

    def test_listener_fallback_uses_real_subprocess_protocol(self):
        self.evidence.clear()
        self.write_site()
        with patch.dict(os.environ, {"KEYGEN_LISTENER_PYTHON": str(ROOT / "benchmark/tests/fake_listener.py")}):
            data = self.build(no_media=True)
        self.assertEqual([r["score"] for r in data["runs"]], [65.4, 65.4])
        self.assertEqual(data["repetition_groups"][0]["best_ordinal"], 1)


if __name__ == "__main__":
    unittest.main()
