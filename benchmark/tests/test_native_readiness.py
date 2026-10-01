"""Qualification never turns configuration or setup failures into a live proof."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark import native_readiness as readiness


def pilot_spec():
    return {
        "model": {
            "id": "readiness-test", "model": "grok-4.7", "response_model": "grok-4.7",
            "provider": "go", "api": "responses", "base_url": "https://opencode.ai/zen/go/v1",
            "api_key_env": "BENCHMARK_READINESS_TEST_KEY",
            "generation": {"max_output_tokens": 1024, "reasoning": {"effort": "xhigh"}},
            "tier": {"level": "xhigh", "reasoning": {"reasoning": {"effort": "xhigh"}}, "spec_sha256": "0" * 64},
            "backend_provenance": {"service_revision": None, "bridge": None},
        },
        "config": {"native": {"timeout_seconds": 3600, "retries": 0}},
        "image": "sha256:" + "a" * 64,
        "limits": {"steps": 5, "wall_seconds": 180, "command_seconds": 15},
    }


def chat_reply(*calls):
    return {"role": "assistant", "tool_calls": [{"id": call} for call in calls],
            "extra": {"actions": [{"command": "true", "tool_call_id": call} for call in calls]}}


def chat_result(call, returncode=0):
    return {"role": "tool", "tool_call_id": call, "content": "", "extra": {"returncode": returncode}}


def responses_reply(*calls):
    return {"object": "response", "output": [{"type": "function_call", "call_id": call} for call in calls],
            "extra": {"actions": [{"command": "true", "tool_call_id": call} for call in calls]}}


def responses_result(call, returncode=0):
    return {"type": "function_call_output", "call_id": call, "output": "", "extra": {"returncode": returncode}}


def request(settings=None):
    return {"event": "request", "settings": {"reasoning_effort": "xhigh"} if settings is None else settings}


def response(usage=None, latency=1.0, identity="identity_match"):
    return {"event": "response", "identity_status": identity, "usage": usage or {}, "latency_seconds": latency}


EXPECTED = {"reasoning_effort": "xhigh"}


class QualificationBoundaryTests(unittest.TestCase):
    def test_outer_deadline_does_not_change_declared_native_timeout(self):
        spec = pilot_spec()
        spec["model"]["readiness"] = {"status": "verified", "evidence": "old proof"}
        normalized = readiness.normalize_spec(spec, None)
        self.assertEqual(normalized["model"]["readiness"]["status"], "qualification")
        self.assertEqual(normalized["model"]["effective_settings"]["model_kwargs"]["timeout"], 3600)
        self.assertEqual(normalized["limits"]["wall_seconds"], 180)

    def test_missing_credentials_emits_blocker_without_allocating_sandbox(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            source = root / "input.json"
            source.write_text(json.dumps(pilot_spec()))
            out = root / "proof"
            result = readiness.qualify(source, out)
            self.assertEqual(result["status"], "blocked")
            self.assertIsNone(result["evidence"])
            payload = json.loads((out / "proof.json").read_text())
            self.assertEqual(payload["cleanup"]["status"], "not_allocated")
            self.assertEqual(payload["transport"], [])
            self.assertEqual(payload["trajectory"]["messages"], [])

    def test_invalid_native_settings_cannot_publish_verified_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = pilot_spec()
            spec["model"]["generation"]["max_output_tokens"] = 1
            source = root / "input.json"
            source.write_text(json.dumps(spec))
            result = readiness.qualify(source, root / "proof")
            self.assertEqual(result["status"], "blocked")
            self.assertIsNone(result["verified_at"])
            self.assertIsNone(result["evidence"])

    def test_previous_proof_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "proof.json"
            original.write_text("original outcome")
            with self.assertRaises(FileExistsError):
                readiness.qualify(root / "absent-input.json", root)
            self.assertEqual(original.read_text(), "original outcome")

    def test_bounded_transport_retries_are_accepted_and_larger_counts_rejected(self):
        spec = pilot_spec()
        spec["config"]["native"]["retries"] = readiness.MAX_TRANSPORT_RETRIES
        self.assertEqual(readiness.normalize_spec(spec, None)["config"]["native"]["retries"], 2)
        spec["config"]["native"]["retries"] = readiness.MAX_TRANSPORT_RETRIES + 1
        with self.assertRaises(ValueError):
            readiness.normalize_spec(spec, None)


class ExecutedCallTests(unittest.TestCase):
    def test_one_call_and_multi_call_replies_both_count(self):
        single = [{"role": "system"}, {"role": "user"}, chat_reply("a"), chat_result("a"),
                  chat_reply("b"), chat_result("b"), chat_reply("c"), chat_result("c"), chat_reply("d")]
        self.assertEqual(readiness.executed_calls(single), ["a", "b", "c"])
        multi = [{"role": "system"}, {"role": "user"}, responses_reply("a"), responses_result("a"),
                 responses_reply("b", "c"), responses_result("b"), responses_result("c")]
        self.assertEqual(readiness.executed_calls(multi), ["a", "b", "c"])

    def test_failed_or_unexecuted_call_does_not_count(self):
        failed = [chat_reply("b", "c"), chat_result("b"), chat_result("c", 1)]
        # mini pads calls that never ran with returncode -1; a missing result is no proof either.
        missing = [responses_reply("b", "c"), responses_result("b")]
        # A result answering a later reply cannot vouch for an earlier one.
        misplaced = [chat_reply("b", "c"), chat_result("b"), chat_reply("d"), chat_result("c")]
        for messages in (failed, missing, misplaced):
            self.assertEqual(readiness.executed_calls(messages), [])

    def pilot(self, root, messages, artifact="other\n"):
        (root / "worker-result.json").write_text(json.dumps({"exit_status": "Submitted"}))
        (root / "trajectory.json").write_text(json.dumps({"messages": messages}))
        (root / "submission").mkdir()
        (root / "submission/readiness.txt").write_text(artifact)
        readiness.verify_pilot({"model": pilot_spec()["model"]}, root, "marker")

    def test_single_call_turns_pass_the_turn_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            messages = [{"role": "system"}, {"role": "user"}, chat_reply("a"), chat_result("a"),
                        chat_reply("b"), chat_result("b"), chat_reply("c"), chat_result("c")]
            # Rejected only later, by the deliberately wrong artifact.
            with self.assertRaisesRegex(ValueError, "artifact did not match"):
                self.pilot(Path(temporary), messages)

    def test_pilot_needs_three_calls_answered_by_their_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            messages = [{"role": "system"}, {"role": "user"}, chat_reply("a"), chat_result("a"),
                        chat_reply("b", "c"), chat_result("b"), chat_reply("d"), chat_result("c")]
            with self.assertRaisesRegex(ValueError, "three native tool calls"):
                self.pilot(Path(temporary), messages, "marker\n")


class LongGenerationProbeTests(unittest.TestCase):
    def classify(self, records, worker=None, controller=None, expected=EXPECTED):
        return readiness.classify_long_generation(records, worker, controller, expected)

    def test_long_output_or_latency_passes(self):
        tokens = self.classify([request(), response({"output_tokens": 40000}, latency=300)])
        self.assertEqual((tokens["outcome"], tokens["max_output_tokens_observed"]), ("pass", 40000))
        latency = self.classify([request(), response({"completion_tokens": 9000}, latency=700.5)])
        self.assertEqual((latency["outcome"], latency["max_latency_seconds"]), ("pass", 700.5))

    def test_thresholds_are_strict(self):
        result = self.classify([request(), response({"output_tokens": 32768}, latency=600)])
        self.assertEqual((result["outcome"], result["failure_category"]), ("inconclusive", None))

    def test_short_model_shortcut_is_inconclusive(self):
        result = self.classify([request(), response({"output_tokens": 900}, latency=12),
                                request(), response({"output_tokens": 40}, latency=2)])
        self.assertEqual((result["outcome"], result["failure_category"]), ("inconclusive", None))

    def test_dropped_request_fails_even_when_retry_completed_long(self):
        result = self.classify([request(), request(), response({"output_tokens": 50000}, latency=900)])
        self.assertEqual((result["outcome"], result["failure_category"]), ("fail", "transport_retry"))

    def test_transport_error_and_outer_deadline_fail(self):
        error = self.classify([request(), response({"output_tokens": 10}), request()], worker="transport_error")
        self.assertEqual((error["outcome"], error["failure_category"]), ("fail", "transport_error"))
        deadline = self.classify([request()], controller="wall_time_exceeded")
        self.assertEqual((deadline["outcome"], deadline["failure_category"]), ("fail", "request_timeout"))
        gateway = self.classify([request(), response(identity="gateway_error")], worker="gateway_error")
        self.assertEqual((gateway["outcome"], gateway["failure_category"]), ("fail", "gateway_error"))

    def test_quota_after_long_response_is_inconclusive(self):
        result = self.classify([request(), response({"output_tokens": 50000}), request()],
                               worker="quota_or_rate_limit")
        self.assertEqual((result["outcome"], result["failure_category"]), ("inconclusive", "quota_or_rate_limit"))

    def test_content_filter_resend_is_not_a_transport_retry(self):
        block = {"event": "content_filter_block", "send": 1, "form": "error"}
        resent = self.classify([request(), block, request(), response({"output_tokens": 50000})])
        self.assertEqual((resent["outcome"], resent["failure_category"]), ("pass", None))
        exhausted = self.classify([request(), block, request(), block, request(), block], worker="content_filter")
        self.assertEqual((exhausted["outcome"], exhausted["failure_category"]), ("inconclusive", "content_filter"))

    def test_long_response_on_other_settings_is_not_a_pass(self):
        result = self.classify([request({"reasoning_effort": "low"}), response({"output_tokens": 50000})])
        self.assertEqual((result["outcome"], result["failure_category"]), ("inconclusive", "settings_mismatch"))

    def test_probe_writes_probe_record_but_never_readiness_evidence(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True):
            root = Path(temporary)
            spec = pilot_spec()
            spec["limits"] = dict(readiness.PROBE_LIMITS)
            source = root / "input.json"
            source.write_text(json.dumps(spec))
            out = root / "probe"
            result = readiness.long_generation_probe(source, out)
            self.assertEqual((result["outcome"], result["failure_category"]), ("inconclusive", "credentials_error"))
            self.assertEqual(json.loads((out / "probe.json").read_text())["schema"], readiness.PROBE_SCHEMA)
            self.assertFalse((out / "readiness.json").exists() or (out / "proof.json").exists())

    def test_probe_rejects_pilot_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.json"
            source.write_text(json.dumps(pilot_spec()))
            result = readiness.long_generation_probe(source, root / "probe")
            self.assertEqual((result["outcome"], result["failure_category"]), ("inconclusive", "configuration_error"))


if __name__ == "__main__":
    unittest.main()
