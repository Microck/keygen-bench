"""Consumer-visible cache-only adaptive campaign publication contracts."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from benchmark import report


class ReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.model = {"id": "claude", "model": "claude-exact", "response_model": "claude-exact",
                      "provider": "anthropic", "api": "anthropic", "base_url": "https://api.anthropic.com",
                      "effective_settings": {"reasoning": "maximum", "output_limit": 8192}}
        self.config = {"schema": "keygen-native-campaign-2", "campaign_id": "fixture-cohort",
                       "max_attempts": 3, "models": [self.model],
                       "policies": {"attempt_selection": "first_success_up_to_three_attempts"},
                       "prompts": {"system": "frozen", "task": "create"}}
        self.snapshot = self.envelope(self.config)
        self.write(self.root / "campaign.lock.json", self.snapshot)

    @staticmethod
    def envelope(config):
        snapshot = {"campaign": config, "config_sha256": report.digest(config), "image_id": "sha256:fixture"}
        return {"snapshot": snapshot, "sha256": report.digest(snapshot)}

    @staticmethod
    def write(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def attempt(self, repetition, score, *, name=None, config=None, category=None,
                model_failure=False, retry_of=None, exhibition=False, evaluator="fixture",
                status_updates=None, profile_updates=None):
        config = config or self.config
        model = config["models"][0]
        name = name or f"claude-rep-{repetition}"
        directory = self.root / name
        status = {"attempt_id": name, "repetition": repetition, "model": model,
                  "status": "RENDERED_UNSCORED" if score is not None else "INFRA_ERROR",
                  "render": "ok" if score is not None else "not_attempted", "eligible": score is not None,
                  "failure_category": category, "model_failure": model_failure,
                  "retry_of": retry_of, "exhibition": exhibition,
                  "totals": {"requests": 2, "usage_unknown": 0}, "started_at": repetition}
        status.update(status_updates or {})
        self.write(directory / "status.json", status)
        self.write(directory / "campaign.json", self.envelope(config))
        inputs = {"artifacts": {"status.json": hashlib.sha256((directory / "status.json").read_bytes()).hexdigest()},
                  "scorer": {"score.py": evaluator}, "numerical": {"version": "fixture"}}
        profile = {"model": model["model"], "score_version": "craft-v7", "evaluation_schema": 2,
                   "status": status["status"], "cacheable": True,
                   "evaluation_location": "evaluations/fixture", "inputs": inputs, "eligible": score is not None,
                   "evaluation_status": "evaluated" if score is not None else "ineligible",
                   "run_failure_category": category, "model_failure": model_failure,
                   "craft": {"craft_score": score, "auxiliary": True}}
        if score is None:
            profile["evaluation_error"] = {"category": category or "MISSING_ARTIFACT", "reason": "fixture"}
        profile.update(profile_updates or {})
        self.write(directory / "profile.json", profile)
        return directory

    def skip(self, repetition, selected="claude-rep-2"):
        name = f"claude-rep-{repetition}"
        directory = self.root / name
        self.write(directory / "campaign.json", self.snapshot)
        self.write(directory / "status.json", {"attempt_id": name, "repetition": repetition,
                   "model": self.model, "status": "SKIPPED_AFTER_SUCCESS", "eligible": False,
                   "selected_attempt_id": selected, "quality_score": None, "totals": None})

    def publish(self):
        return report.build_report(self.root, self.root / "campaign.lock.json")

    def test_failure_success_skip_preserves_outcomes_and_null_unused_slot(self):
        self.attempt(1, None, category="MODEL", model_failure=True)
        self.attempt(2, 30)
        self.skip(3)
        result = self.publish()
        group = result["groups"][0]
        self.assertEqual(group["state"], "success")
        self.assertEqual(group["selected_attempt_id"], "claude-rep-2")
        self.assertEqual(group["selected_craft"], 30)
        self.assertEqual(group["attempted_count"], 2)
        self.assertEqual(result["counts"]["attempts"], 2)
        self.assertEqual(result["counts"]["slots"], 3)
        self.assertEqual(result["counts"]["model_failure_denominator"], 2)
        self.assertEqual(result["counts"]["model_failures"], 1)
        self.assertEqual(result["counts"]["unknown_model_outcomes"], 0)
        skipped = next(row for row in result["rows"] if row["repetition"] == 3)
        self.assertFalse(skipped["attempted"])
        self.assertFalse(skipped["eligible"])
        self.assertTrue(skipped["skip_link_valid"])
        self.assertIsNone(skipped["craft"])
        self.assertIsNone(skipped["totals"])
        self.assertIsNone(skipped["cost"])
        self.assertEqual(skipped["error"], "")
        self.assertEqual(group["policy_errors"], [])
        self.assertNotIn("diagnostic_median", group)
        self.assertNotIn("diagnostic_range", group)

    def test_earliest_success_is_not_replaced_by_later_or_extra_success(self):
        self.attempt(1, 0)
        self.attempt(2, 90)
        self.attempt(3, 99, evaluator="different-scorer")
        self.attempt(1, 100, name="late-retry", retry_of="claude-rep-1")
        result = self.publish()
        self.assertEqual({row["attempt_id"] for row in result["rows"]},
                         {"claude-rep-1", "claude-rep-2", "claude-rep-3", "late-retry"})
        group = result["groups"][0]
        self.assertEqual(group["selected_attempt_id"], "claude-rep-1")
        self.assertEqual(group["selected_craft"], 0)
        self.assertEqual(group["extra_attempts"], 1)
        self.assertEqual(len(group["policy_errors"]), 2)
        self.assertEqual([row["attempt_id"] for row in result["rows"] if row["selected"]], ["claude-rep-1"])
        selected = next(row for row in result["rows"] if row["selected"])
        self.assertEqual(group["selected_evaluation_fingerprint"], selected["evaluation_fingerprint"])
        self.assertNotEqual(selected["evaluation_fingerprint"], next(row["evaluation_fingerprint"] for row in result["rows"] if row["repetition"] == 3))

    def test_cached_score_cannot_override_status_or_evaluation_faults(self):
        faults = [({"failure_category": "AUTH"}, {}),
                  ({"failure_category": "PROTOCOL"}, {}),
                  ({"eligible": False}, {}), ({"render": "error"}, {}),
                  ({"error": "transport failed"}, {}),
                  ({"cleanup_error": "cleanup failed"}, {}),
                  ({"trajectory_recovery_error": "recovery failed"}, {}),
                  ({"termination": {"failure_category": "PROTOCOL"}}, {}),
                  ({"totals": {"identity_mismatch": True}}, {}),
                  ({"finalization_error": {"failure_category": "EVAL"}}, {}),
                  ({}, {"evaluation_error": {"category": "EVAL"}}),
                  ({}, {"evaluation_status": "ineligible"}),
                  ({}, {"run_failure_category": "INFRA"}),
                  ({}, {"cacheable": False}), ({}, {"status": "INFRA_ERROR"})]
        for status_updates, profile_updates in faults:
            with self.subTest(status=status_updates, profile=profile_updates):
                self.attempt(1, 80, status_updates=status_updates, profile_updates=profile_updates)
                self.attempt(2, 20)
                self.skip(3)
                result = self.publish()
                first = next(row for row in result["rows"] if row["repetition"] == 1)
                self.assertFalse(first["eligible"])
                self.assertIsNone(first["craft"])
                self.assertEqual(result["groups"][0]["selected_attempt_id"], "claude-rep-2")

    def test_finalization_sidecar_excludes_otherwise_valid_success(self):
        directory = self.attempt(1, 90)
        self.write(directory / "finalization-error.json", {"failure_category": "EVAL", "error": "archive failed"})
        self.attempt(2, 20)
        self.skip(3)
        result = self.publish()
        self.assertEqual(result["groups"][0]["selected_attempt_id"], "claude-rep-2")
        self.assertEqual(result["counts"]["evaluation_failures"], 1)
        self.assertEqual(result["counts"]["infrastructure_failures"], 1)

    def test_missing_slots_remain_pending_and_not_success(self):
        result = self.publish()
        self.assertEqual(result["groups"][0]["state"], "pending")
        self.assertEqual(result["groups"][0]["attempted_count"], 0)
        self.assertIsNone(result["groups"][0]["selected_attempt_id"])
        self.assertEqual(result["declared_counts"]["null_scores"], 3)
        self.assertTrue(all(row["status"] == "MISSING" and row["outcome"] == "UNKNOWN" for row in result["rows"]))
        self.attempt(1, 50)
        result = self.publish()
        self.assertEqual(result["groups"][0]["selected_attempt_id"], "claude-rep-1")
        self.assertEqual([row["status"] for row in result["rows"]], ["RENDERED_UNSCORED", "MISSING", "MISSING"])

    def test_rendered_status_without_actual_cached_evaluation_is_unknown(self):
        directory = self.attempt(1, 90)
        (directory / "profile.json").unlink()
        result = self.publish()
        self.assertEqual(result["groups"][0]["state"], "pending")
        self.assertEqual(result["groups"][0]["attempted_count"], 1)
        self.assertIsNone(result["groups"][0]["selected_attempt_id"])
        first = next(row for row in result["rows"] if row["repetition"] == 1)
        self.assertEqual(first["outcome"], "UNKNOWN")
        self.assertIsNone(first["craft"])
        self.attempt(2, 20)
        self.skip(3)
        self.assertEqual(self.publish()["groups"][0]["selected_attempt_id"], "claude-rep-2")

    def test_exhausted_failures_and_interrupted_attempts_are_distinct(self):
        self.attempt(1, None, category="MODEL", model_failure=True)
        self.attempt(2, None, category="PROTOCOL", model_failure=False)
        self.attempt(3, None, model_failure=None)
        result = self.publish()
        self.assertEqual(result["groups"][0]["state"], "exhausted")
        self.assertEqual(result["groups"][0]["attempted_count"], 3)
        totals = result["counts"]
        self.assertEqual(totals["model_failures"], 1)
        self.assertEqual(totals["infrastructure_failures"], 1)
        self.assertEqual(totals["unknown_model_outcomes"], 1)
        self.assertEqual(totals["null_scores"], 3)
        self.attempt(3, None, category="INFRA", status_updates={"status": "INTERRUPTED"})
        self.assertEqual(self.publish()["groups"][0]["state"], "interrupted")

    def test_skip_without_earlier_matching_success_is_not_inferred_success(self):
        self.skip(3, selected="claude-rep-1")
        result = self.publish()
        self.assertEqual(result["groups"][0]["state"], "pending")
        self.assertIsNone(result["groups"][0]["selected_attempt_id"])
        self.assertFalse(result["rows"][2]["skip_link_valid"])
        self.assertEqual(result["counts"]["attempts"], 0)
        self.assertEqual(len(result["groups"][0]["policy_errors"]), 1)

    def test_routes_settings_prompts_and_exhibitions_never_merge(self):
        self.attempt(1, 40)
        for name, field in [("other-route", "route"), ("other-settings", "settings"), ("other-prompt", "prompt")]:
            config = copy.deepcopy(self.config)
            if field == "route":
                config["models"][0].update(provider="devin", api="responses", base_url="https://devin.invalid")
            elif field == "settings":
                config["models"][0]["effective_settings"]["output_limit"] = 4096
            else:
                config["prompts"]["task"] = "changed prompt"
            self.attempt(1, 80, name=name, config=config)
        self.attempt(1, 90, name="exhibition", exhibition=True)
        result = self.publish()
        self.assertEqual(len(result["groups"]), 5)
        self.assertEqual({group["kind"] for group in result["groups"]}, {"native", "exhibition"})
        self.assertEqual([group["selected_attempt_id"] for group in result["groups"] if group["selected_attempt_id"]], ["claude-rep-1"])

    def test_exact_roster_keeps_identical_routes_with_distinct_configuration_ids(self):
        second = copy.deepcopy(self.model)
        second["id"] = "claude-other"
        self.config["models"].append(second)
        self.snapshot = self.envelope(self.config)
        self.write(self.root / "campaign.lock.json", self.snapshot)
        result = self.publish()
        self.assertEqual({group["model_id"] for group in result["groups"]}, {"claude", "claude-other"})
        self.assertEqual({row["attempt_id"] for row in result["rows"]},
                         {f"{model_id}-rep-{ordinal}" for model_id in ("claude", "claude-other") for ordinal in (1, 2, 3)})

    def test_changed_status_invalidates_retained_numeric_profile(self):
        directory = self.attempt(1, 60)
        status = json.loads((directory / "status.json").read_text())
        status.update(status="AUTH_ERROR", failure_category="AUTH", model_failure=False)
        self.write(directory / "status.json", status)
        row = next(row for row in self.publish()["rows"] if row["attempt_id"] == "claude-rep-1")
        self.assertFalse(row["eligible"])
        self.assertIsNone(row["craft"])
        self.assertEqual(row["failure_category"], "AUTH")

    def test_evicted_artifacts_keep_cached_score_without_fake_links(self):
        directory = self.attempt(1, 10)
        self.write(directory / "archive.json", {"verified": True, "remote": "cloud:private/bundle.tar.gz",
                   "files": {"canonical/canonical.wav": {"sha256": "unavailable"},
                             "visualizer/visualizer.mp4": {"sha256": "unavailable"}}})
        self.skip(2, selected="claude-rep-1")
        self.skip(3, selected="claude-rep-1")
        result = self.publish()
        self.assertEqual(result["groups"][0]["selected_craft"], 10)
        rows = report.page_rows(result, self.root / "index.html")
        self.assertNotIn("original WAV", rows[0]["files"])
        self.assertNotIn("video", rows[0]["files"])
        self.assertIn("canonical/canonical.wav", rows[0]["archived_artifacts"])
        self.assertTrue(rows[0]["cost_unknown"])
        self.assertIsNone(rows[0]["cost"])
        self.assertIsNone(rows[1]["steps"])
        self.assertEqual(rows[1]["attempts"], 0)

    def test_wrong_cohort_or_modified_manifest_is_rejected(self):
        different = copy.deepcopy(self.config)
        different["prompts"]["task"] = "other cohort"
        self.write(self.root / "other.json", {"campaign": different, "sha256": report.digest(different)})
        with self.assertRaisesRegex(ValueError, "different frozen cohort"):
            report.build_report(self.root, self.root / "other.json")
        changed = copy.deepcopy(self.snapshot)
        changed["snapshot"]["campaign"]["prompts"]["task"] = "tampered"
        self.write(self.root / "campaign.lock.json", changed)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.publish()

    def max_tier_config(self, version="prompt-v2"):
        config = copy.deepcopy(self.config)
        config.update(schema="keygen-native-campaign-3", campaign_id="next-max-tier-fixture")
        config["prompts"]["version"] = version
        config["models"][0]["tier"] = {"level": "max", "reasoning": {"output_config": {"effort": "max"}}, "spec_sha256": "0" * 64}
        config["models"][0]["effective_settings"]["output_limit"] = 128000
        return config

    def test_cohort_labels_distinguish_provider_default_from_highest_declared_tier(self):
        self.attempt(1, 40)
        default = self.publish()
        self.assertEqual(default["cohort"], {"key": "provider-default/prompt-v1", "condition": "provider-default",
                                             "prompt_version": "prompt-v1", "label": "provider default effort, prompt-v1"})
        row = default["rows"][0]
        self.assertEqual(row["tier"], "provider default effort, 8k output")
        self.assertEqual(row["effective_settings"], {"reasoning": "maximum", "output_limit": 8192})
        self.assertEqual(report.page_rows(default, self.root / "index.html")[0]["tier"], row["tier"])

        self.config = self.max_tier_config()
        self.model = self.config["models"][0]
        self.snapshot = self.envelope(self.config)
        self.write(self.root / "campaign.lock.json", self.snapshot)
        self.attempt(1, 40)
        self.skip(2, selected="claude-rep-1")
        result = self.publish()
        self.assertEqual(result["cohort"]["key"], "highest-declared-tier/prompt-v2")
        self.assertEqual(result["cohort"]["label"], "highest declared tier per exact route, prompt-v2")
        self.assertEqual({row["tier"] for row in result["rows"]}, {"highest declared tier: max, 128k output"})
        self.assertIn("not equal compute", result["tier_note"])
        self.assertIn("one quality sample", result["sample_note"])

    def test_schema_three_without_max_tier_prefix_is_not_labeled_highest(self):
        config = self.max_tier_config(version=None)
        config["campaign_id"] = "fixture-declared"
        del config["prompts"]["version"]
        cohort = report.campaign_cohort(config)
        self.assertEqual(cohort["key"], "declared-tier/prompt-v1")
        self.assertEqual(report.tier_label(config["models"][0], cohort["condition"]), "declared tier: max, 128k output")

    def test_each_cohort_gets_its_own_table(self):
        self.attempt(1, 40)
        self.attempt(1, 95, name="max-tier-stray", config=self.max_tier_config())
        result = self.publish()
        tables = result["cohort_tables"]
        self.assertEqual([table["cohort"]["key"] for table in tables],
                         ["provider-default/prompt-v1", "highest-declared-tier/prompt-v2"])
        groups = {group["group_id"]: group for group in result["groups"]}
        for table in tables:
            self.assertTrue(table["group_ids"])
            self.assertEqual({groups[group_id]["cohort"]["key"] for group_id in table["group_ids"]}, {table["cohort"]["key"]})
        self.assertEqual(sorted(group_id for table in tables for group_id in table["group_ids"]), sorted(groups))
        # The higher max-tier score never becomes the default cohort's selection.
        self.assertEqual([group["selected_attempt_id"] for group in result["groups"] if group["selected_attempt_id"]], ["claude-rep-1"])

    def test_quota_stop_is_infrastructure_and_reserved_slots_stay_pending(self):
        self.attempt(1, None, category="QUOTA", status_updates={"status": "QUOTA_ERROR"})
        for repetition in (2, 3):
            name = f"claude-rep-{repetition}"
            self.write(self.root / name / "campaign.json", self.snapshot)
            self.write(self.root / name / "status.json", {"status": "RESERVED", "attempt_id": name, "model": self.model,
                       "repetition": repetition, "retry_of": None, "eligible": False, "quality_score": None,
                       "totals": {"in_flight_usage_unknown": False}})
        result = self.publish()
        counts = result["counts"]
        self.assertEqual(counts["infrastructure_failures"], 1)
        self.assertEqual(counts["model_failures"], 0)
        self.assertEqual(counts["model_failure_denominator"], 0)
        self.assertEqual(counts["attempts"], 1)
        self.assertEqual(counts["unattempted_slots"], 2)
        self.assertEqual(result["groups"][0]["state"], "pending")
        reserved = [row for row in result["rows"] if row["status"] == "RESERVED"]
        self.assertEqual(len(reserved), 2)
        self.assertTrue(all(not row["attempted"] and row["outcome"] == "UNKNOWN" and row["model_failure"] is None for row in reserved))


if __name__ == "__main__":
    unittest.main()
