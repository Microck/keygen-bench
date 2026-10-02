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
                      "tier": {"level": "max", "reasoning": {"output_config": {"effort": "max"}}, "spec_sha256": "0" * 64},
                      "effective_settings": {"reasoning": "maximum", "output_limit": 8192}}
        self.config = {"schema": "keygen-native-campaign-3", "campaign_id": "fixture-cohort",
                       "max_attempts": 3, "models": [self.model],
                       "policies": {"attempt_selection": "first_success_up_to_three_attempts"},
                       "prompts": {"version": "fixture-v1", "system": "frozen", "task": "create"}}
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
                status_updates=None, profile_updates=None, root=None):
        config = config or self.config
        model = config["models"][0]
        name = name or f"claude-rep-{repetition}"
        directory = (root or self.root) / name
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
        self.write(directory / "finalization-error.json", {"failure_category": "EVAL", "error": "scorer failed"})
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

    def test_missing_artifacts_keep_cached_score_without_fake_links(self):
        self.attempt(1, 10)
        self.skip(2, selected="claude-rep-1")
        self.skip(3, selected="claude-rep-1")
        result = self.publish()
        self.assertEqual(result["groups"][0]["selected_craft"], 10)
        rows = report.page_rows(result, self.root / "index.html")
        self.assertNotIn("original WAV", rows[0]["files"])
        self.assertNotIn("video", rows[0]["files"])
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

    def alternate_config(self):
        config = copy.deepcopy(self.config)
        config["campaign_id"] = "fixture-alternate"
        config["prompts"]["version"] = "fixture-v2"
        config["models"][0]["effective_settings"]["output_limit"] = 128000
        return config

    def test_campaign_name_does_not_infer_condition(self):
        config = self.alternate_config()
        expected = report.campaign_cohort(config)
        self.assertEqual(expected["condition"], "declared-tier")
        for name in ("max-effort", "default-effort", "another-campaign"):
            with self.subTest(name=name):
                config["campaign_id"] = name
                self.assertEqual(report.campaign_cohort(config), expected)

    def test_each_cohort_gets_its_own_table(self):
        self.attempt(1, 40)
        self.attempt(1, 95, name="other-prompt-stray", config=self.alternate_config())
        result = self.publish()
        tables = result["cohort_tables"]
        self.assertEqual([table["cohort"]["key"] for table in tables],
                         ["declared-tier/fixture-v1", "declared-tier/fixture-v2"])
        groups = {group["group_id"]: group for group in result["groups"]}
        for table in tables:
            self.assertTrue(table["group_ids"])
            self.assertEqual({groups[group_id]["cohort"]["key"] for group_id in table["group_ids"]}, {table["cohort"]["key"]})
        self.assertEqual(sorted(group_id for table in tables for group_id in table["group_ids"]), sorted(groups))
        # The higher score from another prompt never replaces the selected cohort's sample.
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

    def repeats(self, config=None, suffix="repeats"):
        """A companion campaign declaring repetitions 2-3 of the fixture cohort's condition."""
        config = copy.deepcopy(config or self.config)
        model = config["models"][0]
        repeats = {**config, "campaign_id": "fixture-repeats",
                   "policies": {"attempt_selection": "independent_repetitions", "repetitions": [2, 3],
                                "linked_condition": {"campaign_id": "fixture-cohort", "config_sha256": report.digest(self.config),
                                                     "repetitions": [1], "condition_fingerprints": {
                                                         "claude": report.condition_fingerprint(config, model)}}}}
        temporary = tempfile.TemporaryDirectory(suffix=suffix)
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.write(root / "campaign.lock.json", self.envelope(repeats))
        return repeats, root

    def test_linked_repetitions_keep_failed_outside_slots_out_of_statistics(self):
        self.attempt(1, 65)
        self.attempt(2, None, category="AUTH", status_updates={"status": "AUTH_ERROR"})
        repeats, root = self.repeats()
        self.attempt(2, 40, config=repeats, root=root)
        self.attempt(3, None, config=repeats, root=root, category="MODEL", model_failure=True)
        result = report.build_report(root, root / "campaign.lock.json", [(self.root, self.root / "campaign.lock.json")])
        group, = result["groups"]
        self.assertEqual([(rep["repetition"], rep["source_campaign_id"], rep["craft"]) for rep in group["repetitions"]],
                         [(1, "fixture-cohort", 65), (2, "fixture-repeats", 40), (3, "fixture-repeats", None)])
        self.assertEqual((group["eligible_repetitions"], group["median_craft"], group["min_craft"], group["max_craft"], group["craft_range"]),
                         (2, 52.5, 40, 65, 25))
        self.assertEqual(group["state"], "complete_with_failures")
        self.assertEqual([(row["attempt_id"], row["status"], row["failure_category"]) for row in group["outside_condition_attempts"]],
                         [("claude-rep-2", "AUTH_ERROR", "AUTH")])
        self.assertEqual(result["declared_counts"]["attempts"], 3)
        self.assertFalse(any(row["selected"] for row in result["rows"]))

    def test_repetitions_need_the_linked_root_and_an_identical_condition(self):
        self.attempt(1, 65)
        repeats, root = self.repeats()
        self.attempt(2, 40, config=repeats, root=root)
        with self.assertRaisesRegex(ValueError, "linked campaign's root"):
            report.build_report(root, root / "campaign.lock.json")
        changed = copy.deepcopy(self.config)
        changed["prompts"]["task"] = "different"
        _, other = self.repeats(changed, "changed")
        with self.assertRaisesRegex(ValueError, "condition differs"):
            report.build_report(other, other / "campaign.lock.json", [(self.root, self.root / "campaign.lock.json")])

    def queue(self, repeats, plan_rows, cap=3):
        """A rerun queue over the fixture cohort (rep 1) and its repeats campaign (reps 2-3)."""
        origins = {"fixture-cohort": self.root, "fixture-repeats": None}
        plan = []
        for repetition, campaign_id, outcome, category, root in plan_rows:
            origin = None
            if campaign_id:
                attempt_id = f"claude-rep-{repetition}"
                status = (root / attempt_id / "status.json").read_bytes()
                origin = {"campaign_id": campaign_id, "attempt_id": attempt_id, "status": json.loads(status)["status"],
                          "status_sha256": hashlib.sha256(status).hexdigest(), "outcome": outcome, "failure_category": category}
            plan.append({"repetition": repetition, "origin": origin})
        model = self.config["models"][0]
        fingerprint = report.condition_fingerprint(self.config, model)
        queue = {**self.config, "campaign_id": "fixture-queue",
                 "policies": {"attempt_selection": report.QUEUE_SELECTION, "repetitions": [1, 2, 3],
                              "max_queue_attempts": cap, "plan": {"claude": plan},
                              "linked_campaigns": [
                                  {"campaign_id": "fixture-cohort", "config_sha256": report.digest(self.config),
                                   "condition_fingerprints": {"claude": fingerprint}},
                                  {"campaign_id": "fixture-repeats", "config_sha256": report.digest(repeats),
                                   "condition_fingerprints": {"claude": fingerprint}}]}}
        temporary = tempfile.TemporaryDirectory(suffix="queue")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.write(root / "campaign.lock.json", self.envelope(queue))
        return queue, root

    def rerun(self, queue, root, repetition, index, score, previous, previous_campaign, **kwargs):
        name = f"claude-rep-{repetition}-retry-{index}"
        self.write(root / f"retry-{name}.json", {"campaign_sha256": report.digest(queue), "attempt_id": name,
                                                 "retry_of": previous, "retry_of_campaign_id": previous_campaign})
        return self.attempt(repetition, score, name=name, config=queue, root=root, retry_of=previous, **kwargs)

    def test_queue_reruns_only_infrastructure_failures_and_unstarted_slots(self):
        self.attempt(1, 65)
        repeats, repeats_root = self.repeats()
        self.attempt(2, None, config=repeats, root=repeats_root, category="QUOTA", status_updates={"status": "QUOTA_ERROR"})
        self.write(repeats_root / "claude-rep-3" / "status.json", {"attempt_id": "claude-rep-3", "repetition": 3,
                   "model": self.model, "status": "RESERVED", "retry_of": None, "eligible": False})
        queue, root = self.queue(repeats, [(1, "fixture-cohort", "SUCCESS", None, self.root),
                                           (2, "fixture-repeats", "FAILURE", "QUOTA", repeats_root),
                                           (3, "fixture-repeats", "UNATTEMPTED", None, repeats_root)])
        self.rerun(queue, root, 2, 1, None, "claude-rep-2", "fixture-repeats", category="TRANSPORT",
                   status_updates={"status": "TRANSPORT_ERROR"})
        self.rerun(queue, root, 2, 2, 40, "claude-rep-2-retry-1", "fixture-queue")
        self.rerun(queue, root, 3, 1, None, "claude-rep-3", "fixture-repeats", category="MODEL", model_failure=True)
        linked = [(self.root, self.root / "campaign.lock.json"), (repeats_root, repeats_root / "campaign.lock.json")]
        result = report.build_report(root, root / "campaign.lock.json", linked)
        group, = result["groups"]
        self.assertEqual([(rep["repetition"], rep["attempt_id"], rep["source_campaign_id"], rep["craft"], rep["outcome"])
                          for rep in group["repetitions"]],
                         [(1, "claude-rep-1", "fixture-cohort", 65, "SUCCESS"),
                          (2, "claude-rep-2-retry-2", "fixture-queue", 40, "SUCCESS"),
                          (3, "claude-rep-3-retry-1", "fixture-queue", None, "FAILURE")])
        self.assertEqual([[row["attempt_id"] for row in rep["superseded_attempts"]] for rep in group["repetitions"]],
                         [[], ["claude-rep-2", "claude-rep-2-retry-1"], ["claude-rep-3"]])
        self.assertEqual((group["state"], group["eligible_repetitions"], group["median_craft"]), ("complete_with_failures", 2, 52.5))
        self.assertEqual(result["declared_counts"]["attempts"], 3)
        # A rerun that cannot prove its link to the attempt it reruns is not a sample.
        (root / "retry-claude-rep-2-retry-2.json").unlink()
        group, = report.build_report(root, root / "campaign.lock.json", linked)["groups"]
        self.assertEqual((group["repetitions"][1]["eligible"], group["eligible_repetitions"]), (False, 1))

    def test_queue_never_reruns_a_scored_outcome_and_pins_the_origin_record(self):
        self.attempt(1, 65)
        repeats, repeats_root = self.repeats()
        self.attempt(2, 40, config=repeats, root=repeats_root)
        self.attempt(3, None, config=repeats, root=repeats_root, category="INFRA")
        # The plan claims the scored rep 2 failed; its rerun must not replace the score.
        queue, root = self.queue(repeats, [(1, "fixture-cohort", "SUCCESS", None, self.root),
                                           (2, "fixture-repeats", "FAILURE", "INFRA", repeats_root),
                                           (3, "fixture-repeats", "FAILURE", "INFRA", repeats_root)])
        linked = [(self.root, self.root / "campaign.lock.json"), (repeats_root, repeats_root / "campaign.lock.json")]
        group, = report.build_report(root, root / "campaign.lock.json", linked)["groups"]
        # Only the truly unscored rep 3 awaits a rerun; the report trusts the slot, not the plan's claim.
        self.assertEqual(group["pending_repetitions"], ["claude-rep-3"])
        self.rerun(queue, root, 2, 1, 90, "claude-rep-2", "fixture-repeats")
        with self.assertRaisesRegex(ValueError, "neither unstarted nor a non-model failure"):
            report.build_report(root, root / "campaign.lock.json", linked)
        (root / "claude-rep-2-retry-1" / "status.json").unlink()
        (root / "claude-rep-2-retry-1" / "profile.json").unlink()
        (root / "claude-rep-2-retry-1" / "campaign.json").unlink()
        (root / "claude-rep-2-retry-1").rmdir()
        self.attempt(3, 70, config=repeats, root=repeats_root)  # origin rewritten after the queue froze it
        with self.assertRaisesRegex(ValueError, "frozen record"):
            report.build_report(root, root / "campaign.lock.json", linked)

    def test_follow_up_queue_continues_an_earlier_queues_rerun_chain(self):
        self.attempt(1, 65)
        repeats, repeats_root = self.repeats()
        self.attempt(2, None, config=repeats, root=repeats_root, category="QUOTA", status_updates={"status": "QUOTA_ERROR"})
        self.attempt(3, 30, config=repeats, root=repeats_root)
        first, first_root = self.queue(repeats, [(1, "fixture-cohort", "SUCCESS", None, self.root),
                                                 (2, "fixture-repeats", "FAILURE", "QUOTA", repeats_root),
                                                 (3, "fixture-repeats", "SUCCESS", None, repeats_root)])
        self.rerun(first, first_root, 2, 1, None, "claude-rep-2", "fixture-repeats", category="INFRA",
                   status_updates={"status": "INTERRUPTED"})
        follow = copy.deepcopy(first)
        follow["campaign_id"] = "fixture-queue-2"
        interrupted = (first_root / "claude-rep-2-retry-1" / "status.json").read_bytes()
        follow["policies"]["plan"]["claude"][1]["reruns"] = [{
            "campaign_id": "fixture-queue", "attempt_id": "claude-rep-2-retry-1", "status": "INTERRUPTED",
            "status_sha256": hashlib.sha256(interrupted).hexdigest(), "outcome": "FAILURE", "failure_category": "INFRA"}]
        follow["policies"]["linked_campaigns"].append({"campaign_id": "fixture-queue", "config_sha256": report.digest(first),
                                                       "condition_fingerprints": {"claude": report.condition_fingerprint(self.config, self.model)}})
        temporary = tempfile.TemporaryDirectory(suffix="queue-2")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.write(root / "campaign.lock.json", self.envelope(follow))
        self.rerun(follow, root, 2, 2, 55, "claude-rep-2-retry-1", "fixture-queue")
        linked = [(self.root, self.root / "campaign.lock.json"), (repeats_root, repeats_root / "campaign.lock.json"),
                  (first_root, first_root / "campaign.lock.json")]
        group, = report.build_report(root, root / "campaign.lock.json", linked)["groups"]
        rep = group["repetitions"][1]
        self.assertEqual((rep["attempt_id"], rep["source_campaign_id"], rep["craft"]), ("claude-rep-2-retry-2", "fixture-queue-2", 55))
        self.assertEqual([(row["attempt_id"], row["source_campaign_id"]) for row in rep["superseded_attempts"]],
                         [("claude-rep-2", "fixture-repeats"), ("claude-rep-2-retry-1", "fixture-queue")])
        self.assertEqual((group["state"], group["scores"]), ("complete", [65, 55, 30]))


if __name__ == "__main__":
    unittest.main()
