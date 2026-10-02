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

    def test_devin_qualification_requires_matching_bridge_executable(self):
        spec = pilot_spec()
        spec["model"].update(provider="devin", api="chat", model="devin/exact-model",
                             response_model="exact-model", base_url="http://127.0.0.1:8417/v1",
                             generation={"max_tokens": 64000, "reasoning_effort": "max"},
                             tier={"level": "max", "reasoning": {"reasoning_effort": "max"},
                                   "spec_sha256": "0" * 64})
        with self.assertRaisesRegex(ValueError, "executable provenance"):
            readiness.normalize_spec(spec, None)
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "bridge"
            executable.write_bytes(b"synthetic bridge executable")
            spec["model"]["backend_provenance"]["bridge"] = {
                "implementation": "CLIProxyAPI", "version": "synthetic",
                "executable_sha256": readiness.campaign.file_digest(executable)}
            with self.assertRaisesRegex(ValueError, "does not match"):
                readiness.normalize_spec(spec, None)
            normalized = readiness.normalize_spec(spec, executable)
            self.assertEqual(normalized["model"]["effective_settings"]["expected_transmitted_generation"],
                             {"max_tokens": 64000, "reasoning_effort": "max"})
            executable.write_bytes(b"changed executable")
            with self.assertRaisesRegex(ValueError, "does not match"):
                readiness.normalize_spec(spec, executable)


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


if __name__ == "__main__":
    unittest.main()
