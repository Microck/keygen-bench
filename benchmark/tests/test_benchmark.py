"""Offline consumer-visible campaign, recovery and artifact boundaries."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import copy
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tarfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import wave

from benchmark import campaign, run


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.model = {"id": "verified", "inventory_id": "exact-model", "model": "exact-model", "response_model": "exact-model",
                      "provider": "go", "api": "chat", "base_url": "https://opencode.ai/zen/go/v1", "api_key_env": "TEST_GO_KEY",
                      "generation": {"max_tokens": 4096, "reasoning_effort": "max"},
                      "readiness": {"status": "verified", "evidence": "offline-fixture", "verified_at": "2026-09-30"}}
        self.model["backend_provenance"] = {"service_revision": None, "bridge": None}
        self.tier_spec_path = self.root / "tier-spec.json"
        self.tier_spec_path.write_text(json.dumps({"entries": [
            {"provider": "go", "api": "chat", "model": "exact-model", "tier": "max",
             "reasoning": {"reasoning_effort": "max"}}]}))
        self.model["tier"] = {"level": "max", "reasoning": {"reasoning_effort": "max"},
                              "spec_sha256": campaign.file_digest(self.tier_spec_path)}
        self.selection = json.loads((run.HERE / "config/campaign.example.json").read_text())
        self.selection["models"] = [self.model]
        self.selection["image"] = "sha256:" + "a" * 64
        self.selection["visualizer_image"] = "sha256:" + "b" * 64
        self.selection["storage"] = {"reserve_bytes": 1, "peak_bytes_per_attempt": 1073741824}
        effective = campaign.normalize_native(self.selection, [self.model])[0]
        route = {key: self.model[key] for key in ("provider", "api", "base_url", "model", "response_model", "backend_provenance")}
        # A synthetic native trace exercises proof validation, not provider readiness.
        from minisweagent.models.utils.actions_toolcall import BASH_TOOL
        call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": '{"command":"echo ready"}'}}
        messages = [{"role": "system", "content": "Protocol probe"}, {"role": "user", "content": "Run a tool then submit"},
                    {"role": "assistant", "content": "", "tool_calls": [call],
                     "extra": {"response": {"model": "exact-model", "usage": {"prompt_tokens": 3}},
                               "actions": [{"command": "echo ready", "tool_call_id": "c1"}]}},
                    {"role": "tool", "tool_call_id": "c1", "content": "ready", "extra": {"returncode": 0}},
                    {"role": "assistant", "content": "", "extra": {"response": {"model": "exact-model", "usage": {"prompt_tokens": 4}},
                                                                 "actions": [{"command": run.FINISH, "tool_call_id": "c2"}]}}]
        self.proof = {"schema": "keygen-native-readiness-1", "route": route, "effective_settings": effective,
                      "native_source_sha256": campaign.file_digest(run.HERE / "native_models.py"),
                      "upstream_source_sha256": campaign.upstream_provenance("chat"),
                      "trajectory": {"info": {"config": {"agent_type": "minisweagent.agents.default.DefaultAgent",
                                                        "model_type": "minisweagent.models.litellm_model.LitellmModel"}}, "messages": messages},
                      "transport": [{"event": "request", "input_sha256": campaign.digest(messages[:2]),
                                     "tools_sha256": campaign.digest([BASH_TOOL]), "settings": effective["expected_transmitted_generation"]},
                                    {"event": "response", "identity_status": "identity_match"},
                                    {"event": "request", "input_sha256": campaign.digest(messages[:4]),
                                     "tools_sha256": campaign.digest([BASH_TOOL]), "settings": effective["expected_transmitted_generation"]},
                                    {"event": "response", "identity_status": "identity_match"}]}
        self.proof_path = self.root / "proof.json"
        self.proof_path.write_text(json.dumps(self.proof))
        self.model["readiness"]["evidence"] = {"evidence_path": str(self.proof_path),
                                             "artifact_sha256": campaign.file_digest(self.proof_path),
                                             "provider_received_settings_verified": False}
        self.inventory = {"models": [{"model": "exact-model", "provider": "OpenCode Go", "status": "pending-model-smoke",
                                      "upstream_model": "exact-model", "proxy_request_model": "exact-model"}]}
        self.inventory_path = self.root / "inventory.json"
        self.selection_path = self.root / "selection.json"

    def compile(self):
        self.inventory_path.write_text(json.dumps(self.inventory))
        self.selection_path.write_text(json.dumps(self.selection))
        return campaign.compile_campaign(self.inventory_path, self.selection_path, self.root / "campaign.json", self.tier_spec_path)

    def test_new_selected_provider_requires_bound_without_migrating_legacy_maps(self):
        legacy = set(self.selection["concurrency"]["providers"])
        self.assertEqual(set(self.compile()["concurrency"]["providers"]), legacy)
        for provider, label, base in (("openai", "OpenAI", "https://api.openai.com/v1"),
                                      ("custom", "Custom", "https://api.example.com/v1")):
            with self.subTest(provider=provider):
                (self.root / "campaign.json").unlink()
                self.model.update(provider=provider, base_url=base)
                self.inventory["models"][0]["provider"] = label
                self.tier_spec_path.write_text(json.dumps({"entries": [
                    {"provider": provider, "api": "chat", "model": "exact-model", "tier": "max",
                     "reasoning": {"reasoning_effort": "max"}}]}))
                self.model["tier"]["spec_sha256"] = campaign.file_digest(self.tier_spec_path)
                effective = campaign.normalize_native(self.selection, [self.model])[0]
                self.proof["route"] = {key: self.model[key] for key in
                                       ("provider", "api", "base_url", "model", "response_model", "backend_provenance")}
                self.proof["effective_settings"] = effective
                self.proof_path.write_text(json.dumps(self.proof))
                self.model["readiness"]["evidence"]["artifact_sha256"] = campaign.file_digest(self.proof_path)
                self.selection["concurrency"]["providers"] = {key: 1 for key in legacy}
                with self.assertRaisesRegex(ValueError, "concurrency bounds"):
                    self.compile()
                self.selection["concurrency"]["providers"][provider] = 1
                compiled = self.compile()
                self.assertEqual(compiled["models"][0]["provider"], provider)
                self.assertEqual(set(compiled["concurrency"]["providers"]), legacy | {provider})

    def test_held_and_excluded_routes_rejected_without_credentials(self):
        for provider, status in [("Devin", "held-until-devin-renewal"), ("OpenCode Zen", "ready"), ("OpenCode Go", "blocked-original-checkpoint-unproven")]:
            with self.subTest(provider=provider, status=status):
                self.inventory["models"][0].update(provider=provider, status=status)
                with self.assertRaisesRegex(ValueError, "held|Excluded"):
                    self.compile()
        self.assertFalse((self.root / "campaign.json").exists())

    def test_unverified_native_route_rejected(self):
        self.model["readiness"]["status"] = "pending"
        with self.assertRaisesRegex(ValueError, "readiness"):
            self.compile()

    def test_devin_compilation_freezes_alias_response_identity_bridge_and_concurrency(self):
        self.model.update(provider="devin", model="devin/exact-model",
                          base_url="http://127.0.0.1:8417/v1", api_key_env="DEVIN_BRIDGE_API_KEY")
        self.model["backend_provenance"]["bridge"] = {
            "implementation": "CLIProxyAPI", "version": "synthetic", "executable_sha256": "d" * 64}
        self.inventory["models"][0].update(provider="Devin", proxy_request_model="devin/exact-model")
        self.tier_spec_path.write_text(json.dumps({"entries": [
            {"provider": "devin", "api": "chat", "model": "devin/exact-model", "tier": "max",
             "reasoning": {"reasoning_effort": "max"}}]}))
        self.model["tier"]["spec_sha256"] = campaign.file_digest(self.tier_spec_path)
        self.proof["route"] = {key: self.model[key] for key in
                              ("provider", "api", "base_url", "model", "response_model", "backend_provenance")}
        self.proof["effective_settings"] = campaign.normalize_native(self.selection, [self.model])[0]
        self.proof_path.write_text(json.dumps(self.proof))
        self.model["readiness"]["evidence"]["artifact_sha256"] = campaign.file_digest(self.proof_path)
        compiled = self.compile()
        self.assertEqual(compiled["models"][0]["model"], "devin/exact-model")
        self.assertEqual(compiled["models"][0]["response_model"], "exact-model")
        for mutation in ("bridge", "request_identity", "response_identity", "concurrency"):
            changed = copy.deepcopy(compiled)
            if mutation == "bridge":
                changed["models"][0]["backend_provenance"]["bridge"] = None
                expected = "Bridge route"
            elif mutation == "concurrency":
                del changed["concurrency"]["providers"]["devin"]
                expected = "selected provider concurrency bounds"
            else:
                changed["models"][0]["model" if mutation == "request_identity" else "response_model"] = "other-model"
                expected = "identity differs"
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, expected):
                campaign.validate(changed, check_provenance=False)

    def test_claimed_readiness_without_real_proof_file_rejected(self):
        self.proof_path.unlink()
        with self.assertRaisesRegex(ValueError, "existing bounded"):
            self.compile()

    def test_readiness_hash_single_turn_and_missing_tool_result_rejected(self):
        original = copy.deepcopy(self.proof)
        for mutation in ("hash", "single_turn", "no_tool"):
            self.proof = copy.deepcopy(original)
            if mutation == "single_turn":
                self.proof["trajectory"]["messages"] = self.proof["trajectory"]["messages"][:4]
            elif mutation == "no_tool":
                self.proof["trajectory"]["messages"].pop(3)
            self.proof_path.write_text(json.dumps(self.proof))
            self.model["readiness"]["evidence"]["artifact_sha256"] = (
                "b" * 64 if mutation == "hash" else campaign.file_digest(self.proof_path))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.compile()

    def test_readiness_bound_to_native_source_and_exact_transmitted_settings(self):
        original = copy.deepcopy(self.proof)
        for mutation in ("source", "settings"):
            self.proof = copy.deepcopy(original)
            if mutation == "source":
                self.proof["native_source_sha256"] = "0" * 64
            else:
                self.proof["transport"][0]["settings"] = {"max_tokens": 1}
            self.proof_path.write_text(json.dumps(self.proof))
            self.model["readiness"]["evidence"]["artifact_sha256"] = campaign.file_digest(self.proof_path)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.compile()

    def test_content_filter_blocked_send_is_set_aside_but_its_settings_still_count(self):
        original = copy.deepcopy(self.proof)
        blocked = copy.deepcopy(original["transport"][0])
        # Blocked first send of the first request (HTTP 200 form), then its identical re-send.
        self.proof["transport"] = [blocked, {"event": "response", "identity_status": "identity_match"},
                                   {"event": "content_filter_block", "send": 1, "form": "stop_reason"},
                                   *original["transport"]]
        self.proof_path.write_text(json.dumps(self.proof))
        self.model["readiness"]["evidence"]["artifact_sha256"] = campaign.file_digest(self.proof_path)
        self.compile()
        blocked["settings"] = {"max_tokens": 4096}  # reasoning control missing on the blocked send
        self.proof["transport"][0] = blocked
        self.proof_path.write_text(json.dumps(self.proof))
        self.model["readiness"]["evidence"]["artifact_sha256"] = campaign.file_digest(self.proof_path)
        with self.assertRaisesRegex(ValueError, "transmitted settings|reasoning control"):
            self.compile()

    def test_first_success_contract_preserves_exact_prompts(self):
        config = self.compile()
        self.assertEqual(config["max_attempts"], 3)
        self.assertEqual(config["policies"]["attempt_selection"], "first_success_up_to_three_attempts")
        changed = copy.deepcopy(config)
        changed["max_attempts"] = True
        with self.assertRaises(ValueError):
            campaign.validate(changed)
        changed = copy.deepcopy(config)
        changed["prompts"]["task"] += "Prefer tonal music"
        with self.assertRaisesRegex(ValueError, "Creative prompts"):
            campaign.validate(changed)

    def test_repetitions_link_only_an_identical_condition_and_never_reuse_a_conditional_slot(self):
        primary = self.compile()
        self.selection["campaign_id"] = "fixture-repeats"
        self.selection["concurrency"]["workers"] += 1  # operational, not part of the condition
        self.selection_path.write_text(json.dumps(self.selection))
        compile_repeats = lambda ordinals, out="repeats.json": campaign.compile_campaign(
            self.inventory_path, self.selection_path, self.root / out, self.tier_spec_path,
            ordinals, self.root / "campaign.json")
        repeats = compile_repeats([2, 3])
        link = repeats["policies"]["linked_condition"]
        self.assertEqual(repeats["policies"]["attempt_selection"], "independent_repetitions")
        self.assertEqual((link["campaign_id"], link["config_sha256"], link["repetitions"]),
                         (primary["campaign_id"], campaign.digest(primary), [1]))
        self.assertEqual(campaign.repetitions(repeats), [2, 3])
        # A first-success campaign's later slots ran only after a failure, so they cannot be linked samples.
        with self.assertRaisesRegex(ValueError, "exactly once"):
            compile_repeats([1, 2], "overlap.json")
        continuation = campaign.compile_campaign(self.inventory_path, self.selection_path, self.root / "continuation.json",
                                                 self.tier_spec_path, [2, 3], self.root / "campaign.json", campaign.FIRST_SUCCESS)
        self.assertEqual((continuation["policies"]["attempt_selection"], campaign.repetitions(continuation),
                          continuation["policies"]["linked_condition"]["repetitions"]), (campaign.FIRST_SUCCESS, [2, 3], [1]))
        with self.assertRaisesRegex(ValueError, "after the linked campaign's consumed"):
            campaign.compile_campaign(self.inventory_path, self.selection_path, self.root / "gap.json",
                                      self.tier_spec_path, [1, 3], self.root / "campaign.json", campaign.FIRST_SUCCESS)
        self.selection["limits"]["command_seconds"] += 60
        self.selection_path.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(ValueError, "condition differs"):
            compile_repeats([2, 3], "changed.json")
        forged = copy.deepcopy(repeats)
        forged["prompts"]["task"] += "Prefer tonal music"
        forged["policies"]["linked_condition"]["condition_fingerprints"]["verified"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "condition fingerprint"):
            campaign.validate(forged)

    def test_rerun_queue_freezes_origins_and_runs_only_unscored_ordinals(self):
        primary = self.compile()
        self.selection["campaign_id"] = "fixture-queue"
        self.selection_path.write_text(json.dumps(self.selection))
        origin = lambda n, outcome, category, status: {"campaign_id": primary["campaign_id"], "attempt_id": f"verified-rep-{n}",
                                                       "status": status, "status_sha256": "a" * 64,
                                                       "outcome": outcome, "failure_category": category}
        plan = {"max_queue_attempts": 4, "models": {"verified": [
            {"repetition": 1, "origin": origin(1, "SUCCESS", None, "RENDERED_UNSCORED")},
            {"repetition": 2, "origin": origin(2, "FAILURE", "QUOTA", "QUOTA_ERROR")},
            {"repetition": 3, "origin": origin(3, "UNATTEMPTED", None, "RESERVED")}]}}
        plan_path = self.root / "queue-plan.json"
        compile_queue = lambda out: campaign.compile_campaign(self.inventory_path, self.selection_path, self.root / out,
                                                              self.tier_spec_path, queue_plan=plan_path,
                                                              queue_links=[self.root / "campaign.json"])
        plan_path.write_text(json.dumps(plan))
        queue = compile_queue("queue.json")
        self.assertEqual(queue["policies"]["linked_campaigns"],
                         [{"campaign_id": primary["campaign_id"], "config_sha256": campaign.digest(primary),
                           "condition_fingerprints": {"verified": campaign.condition_fingerprint(queue, queue["models"][0])}}])
        self.assertEqual([campaign.origin_reruns(entry["origin"]) for entry in queue["policies"]["plan"]["verified"]],
                         [False, True, True])
        # An origin must be the ordinal's own slot, and a scored plan has nothing to run.
        plan["models"]["verified"][1]["origin"]["attempt_id"] = "verified-rep-3"
        plan_path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "names its linked slot"):
            compile_queue("wrong-slot.json")
        plan["models"]["verified"][1]["origin"] = origin(2, "FAILURE", "MODEL", "MODEL_FAILED")
        plan["models"]["verified"][2]["origin"] = origin(3, "SUCCESS", None, "RENDERED_UNSCORED")
        plan_path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "at least one"):
            compile_queue("nothing.json")
        self.selection["limits"]["command_seconds"] += 60
        self.selection_path.write_text(json.dumps(self.selection))
        plan["models"]["verified"][2]["origin"] = origin(3, "UNATTEMPTED", None, "RESERVED")
        plan_path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "condition differs"):
            compile_queue("changed.json")

    def test_cross_environment_queue_links_only_when_declared_and_route_unchanged(self):
        primary = self.compile()
        self.selection["campaign_id"] = "fixture-queue"
        # Another sandbox environment: a different agent image (e.g. a local arm64 build).
        self.selection["image"] = "sha256:" + "c" * 64
        self.selection_path.write_text(json.dumps(self.selection))
        plan = {"max_queue_attempts": 4, "models": {"verified": [
            {"repetition": n, "origin": {"campaign_id": primary["campaign_id"], "attempt_id": f"verified-rep-{n}",
                                         "status": "RESERVED", "status_sha256": "a" * 64,
                                         "outcome": "UNATTEMPTED", "failure_category": None}} for n in (1, 2, 3)]}}
        plan_path = self.root / "queue-plan.json"
        compile_queue = lambda out: campaign.compile_campaign(self.inventory_path, self.selection_path, self.root / out,
                                                              self.tier_spec_path, queue_plan=plan_path,
                                                              queue_links=[self.root / "campaign.json"])
        plan_path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "condition differs"):
            compile_queue("undeclared.json")
        plan["cross_environment"] = True
        plan_path.write_text(json.dumps(plan))
        queue = compile_queue("cross.json")
        self.assertTrue(queue["policies"]["cross_environment"])
        self.assertEqual(queue["policies"]["linked_campaigns"][0]["condition_fingerprints"],
                         {"verified": campaign.environment_free_fingerprint(primary, primary["models"][0])})
        # Anything beyond the environment must still match.
        self.selection["limits"]["command_seconds"] += 60
        self.selection_path.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(ValueError, "condition differs"):
            compile_queue("changed.json")

    def test_model_mapping_and_effective_settings_cannot_be_faked(self):
        self.model["response_model"] = "substitute"
        with self.assertRaisesRegex(ValueError, "identity differs"):
            self.compile()
        self.model["response_model"] = "exact-model"
        config = self.compile()
        config["models"][0]["effective_settings"]["output_limit"] = 999999
        evidence = config["models"][0]["readiness"]["evidence"]
        evidence["payload"]["effective_settings"]["output_limit"] = 999999
        evidence["payload_sha256"] = campaign.digest(evidence["payload"])
        with self.assertRaises(ValueError):
            campaign.validate(config)

    def test_inventory_is_not_executable_and_manifest_is_immutable(self):
        with self.assertRaises(ValueError):
            campaign.load(self.inventory_path) if self.inventory_path.exists() else campaign.validate(self.inventory)
        config = self.compile()
        envelope = json.loads((self.root / "campaign.json").read_text())
        envelope["campaign"]["limits"]["steps"] = 1
        (self.root / "campaign.json").write_text(json.dumps(envelope))
        with self.assertRaisesRegex(ValueError, "immutable"):
            campaign.load(self.root / "campaign.json")
        with self.assertRaises(ValueError):
            campaign.publish(self.root / "campaign.json", {"sha256": campaign.digest(config), "campaign": config})

    def test_atomic_lock_publication_under_concurrent_starts(self):
        path = self.root / "lock.json"
        start = threading.Barrier(12)
        def publish():
            start.wait()
            run.lock_campaign(path, {"condition": "fixed"})
            return json.loads(path.read_text())["snapshot"]
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _: publish(), range(12)))
        self.assertEqual(results, [{"condition": "fixed"}] * 12)
        with self.assertRaises(ValueError):
            run.lock_campaign(path, {"condition": "changed"})

    def test_atomic_repeat_reservations_preserve_identity(self):
        def reserve(repetition):
            try:
                run.reserve(self.root, self.model, repetition, f"verified-rep-{repetition}")
                return True
            except FileExistsError:
                return False
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(reserve, [1, 2, 3] * 4))
        self.assertEqual(sum(results), 3)
        rows = [json.loads(path.read_text()) for path in self.root.glob("*/status.json")]
        self.assertEqual({row["repetition"] for row in rows}, {1, 2, 3})
        self.assertEqual({row["model"]["model"] for row in rows}, {"exact-model"})
        self.assertTrue(all(row["status"] == "RESERVED" and row["eligible"] is False for row in rows))

    def test_recovery_finalizes_without_rerun_and_keeps_unknown_usage(self):
        directory = run.reserve(self.root, self.model, 1, "verified-rep-1")
        self.assertEqual(run.recover_attempts(self.root, self.selection, []), ["verified-rep-1"])
        status = json.loads((directory / "status.json").read_text())
        self.assertEqual(status["status"], "INTERRUPTED")
        self.assertEqual(status["model"], self.model)
        self.assertTrue(status["totals"]["in_flight_usage_unknown"])
        self.assertEqual(status["failure_category"], "INFRA")
        with self.assertRaises(FileExistsError):
            run.reserve(self.root, self.model, 1, "verified-rep-1")
        retry = run.reserve(self.root, self.model, 1, "retry-explicit", retry_of="verified-rep-1")
        self.assertEqual(json.loads((retry / "status.json").read_text())["retry_of"], "verified-rep-1")
        self.assertEqual(json.loads((directory / "status.json").read_text())["status"], "INTERRUPTED")

    def test_identity_mismatch_and_native_usage_remain_separate(self):
        trajectory = {"info": {"model_stats": {"api_calls": 2}}, "messages": [
            {"role": "assistant", "extra": {"response": {"model": "different", "usage": {"prompt_tokens": 100, "completion_tokens": 10,
                "completion_tokens_details": {"reasoning_tokens": 3}}}}},
            {"role": "tool", "extra": {"duration_seconds": 2.0}}]}
        (self.root / "trajectory.json").write_text(json.dumps(trajectory))
        totals = run.summarize(self.root, self.model, interrupted=True)
        self.assertTrue(totals["identity_mismatch"])
        self.assertEqual(totals["prompt_tokens"], 100)
        self.assertEqual(totals["reasoning_tokens"], 3)
        self.assertEqual(totals["requests"], 2)
        self.assertEqual(totals["usage_unknown"], 2)
        self.assertEqual(totals["sandbox_seconds"], 2.0)

    def test_environment_does_not_forward_ambient_configuration(self):
        with patch.dict("os.environ", {"BASH_ENV": "/injected", "PYTHONPATH": "/injected", "ANTHROPIC_API_KEY": "private"}):
            env = run.isolated_env(self.root, {"OPENAI_API_KEY": "required"})
        self.assertNotIn("BASH_ENV", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual(env["OPENAI_API_KEY"], "required")
        with self.assertRaises(ValueError):
            run.isolated_env(self.root, {"HOME": "/override"})

    def test_controller_credentials_reject_unapproved_route_or_reserved_identity(self):
        original = {**self.model, "effective_settings": self.proof["effective_settings"]}
        for mutation in ({"provider": "devin"}, {"provider": "go", "api": "messages"},
                         {"api_key_env": "HOME"}, {"base_url": "https://unapproved.example/v1"},
                         {"effective_settings": {"model_name": "anthropic/exact-model"}}):
            with (self.subTest(mutation=mutation), patch.dict("os.environ", {"TEST_GO_KEY": "synthetic-only"}),
                  self.assertRaises(ValueError)):
                run.worker_credentials(self.selection, {**original, **mutation})

    def test_compiler_requires_the_spec_tier_and_its_reasoning_control(self):
        undeclared = copy.deepcopy(self.model)
        del undeclared["tier"]
        silent = copy.deepcopy(self.model)
        del silent["generation"]["reasoning_effort"]  # provider default instead of the spec's max
        silent["tier"] = {**silent["tier"], "level": "none-available", "reasoning": {}}
        lowered = copy.deepcopy(self.model)
        lowered["generation"]["reasoning_effort"] = "high"
        lowered["tier"] = {**lowered["tier"], "level": "high", "reasoning": {"reasoning_effort": "high"}}
        for name, model in (("undeclared", undeclared), ("silent", silent), ("lowered", lowered)):
            self.selection["models"] = [model]
            with self.subTest(name), self.assertRaisesRegex(ValueError, "tier"):
                self.compile()
        self.assertFalse((self.root / "campaign.json").exists())
        blocked = {"entries": [{"provider": "go", "api": "chat", "model": "exact-model", "tier": "blocked-unknown", "reasoning": {}}]}
        self.tier_spec_path.write_text(json.dumps(blocked))
        self.selection["models"] = [self.model]
        with self.assertRaisesRegex(ValueError, "blocked"):
            self.compile()

    def test_key_pool_assigns_least_loaded_key_under_caps_and_records_only_names(self):
        config = {"native": {"timeout_seconds": 1, "retries": 0},
                  "concurrency": {"key_pools": {"TEST_GO_KEY": {"TEST_GO_KEY_1": 2, "TEST_GO_KEY_2": 1}}}}
        model = {**self.model, "effective_settings": self.proof["effective_settings"]}
        with ExitStack() as stack:
            held = [stack.enter_context(run.credential_lease(config, model)) for _ in range(3)]
            # Least loaded first (ties in declared order), never beyond a key's cap.
            self.assertEqual(held, ["TEST_GO_KEY_1", "TEST_GO_KEY_2", "TEST_GO_KEY_1"])
            blocked = threading.Event()
            def fourth():
                with run.credential_lease(config, model):
                    blocked.set()
            waiter = threading.Thread(target=fourth, daemon=True)
            waiter.start()
            self.assertFalse(blocked.wait(0.3))
        waiter.join(2)
        self.assertTrue(blocked.is_set())
        with patch.dict("os.environ", {"TEST_GO_KEY_2": "synthetic-two"}, clear=True):
            self.assertEqual(run.worker_credentials(config, model, "TEST_GO_KEY_2")["OPENAI_API_KEY"], "synthetic-two")
            for key in (None, "TEST_GO_KEY", "OTHER_KEY"):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    run.worker_credentials(config, model, key)

    def test_key_pool_caps_must_cover_provider_bound(self):
        self.selection["concurrency"]["providers"]["go"] = 4
        self.selection["concurrency"]["workers"] = 4
        self.selection["concurrency"]["key_pools"] = {"TEST_GO_KEY": {"TEST_GO_KEY_1": 1, "TEST_GO_KEY_2": 2}}
        with self.assertRaisesRegex(ValueError, "Per-key caps"):
            self.compile()

    def test_global_slot_bounds_concurrent_evaluation(self):
        active = peak = 0
        guard = threading.Lock()
        ready = threading.Barrier(8)
        def work(_):
            nonlocal active, peak
            ready.wait()
            with run.slot(self.root, "render", 2):
                with guard:
                    active += 1
                    peak = max(peak, active)
                threading.Event().wait(0.03)
                with guard:
                    active -= 1
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(work, range(8)))
        self.assertEqual(peak, 2)

    def test_local_artifact_root_rejects_relative_paths(self):
        with self.assertRaises(ValueError):
            run.artifact_root(Path("relative"))

    def test_binary_export_bound_removes_partial_file(self):
        import sys
        output = self.root / "preview.mp4"
        with self.assertRaisesRegex(ValueError, "byte limit"):
            run.bounded_stream([sys.executable, "-I", "-c", "import os;os.write(1,b'x'*4096)"], output, 1024, 5)
        self.assertFalse(output.exists())

    def test_binary_export_deadline_reaps_process_and_removes_partial_file(self):
        import sys
        output = self.root / "preview.mp4"
        with self.assertRaises(TimeoutError):
            run.bounded_stream([sys.executable, "-I", "-c", "import time;time.sleep(30)"], output, 1024, 1)
        self.assertFalse(output.exists())

    def archive(self, name, size=4, kind=tarfile.REGTYPE):
        path = self.root / "artifact.tar"
        with tarfile.open(path, "w") as archive:
            item = tarfile.TarInfo(name)
            item.type, item.size = kind, size if kind == tarfile.REGTYPE else 0
            archive.addfile(item, io.BytesIO(b"a" * size) if kind == tarfile.REGTYPE else None)
        return path

    def test_artifact_paths_links_and_size_rejected(self):
        for name, kind in [("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                run.safe_unpack(self.archive(name, kind=kind), self.root / "out", 100)
        with self.assertRaises(ValueError):
            run.safe_unpack(self.archive("tune.xm", 100), self.root / "out", 20)

    def test_regular_artifact_extracted_without_untrusted_modes(self):
        run.safe_unpack(self.archive("tune.xm"), self.root / "out", 100)
        self.assertEqual((self.root / "out/tune.xm").read_bytes(), b"aaaa")
        self.assertFalse((self.root / "out/tune.xm").stat().st_mode & 0o111)

    def wav(self, values):
        path = self.root / "audio.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            wav.writeframes(struct.pack("<" + "h" * len(values), *values))
        return path

    def test_audio_technical_facts_not_aesthetic_grade(self):
        result = run.wav_info(self.wav([32767, -32768, 1000, -1000] * 50))
        self.assertIsNone(result["quality_score"])
        self.assertEqual(result["full_scale_samples"], 100)
        with self.assertRaisesRegex(ValueError, "silent"):
            run.wav_info(self.wav([0] * 100))


class ModelSequenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.model = {"id": "model", "model": "exact", "provider": "go"}
        self.config = {"max_attempts": 3, "policies": campaign.POLICIES}
        self.invoked = []
        run.STOP.clear()
        self.addCleanup(run.STOP.clear)
        for ordinal in range(1, 4):
            run.reserve(self.root, self.model, ordinal, f"model-rep-{ordinal}")

    def status(self, ordinal):
        return json.loads((self.root / f"model-rep-{ordinal}" / "status.json").read_text())

    def execute(self, outcomes):
        def attempt(root, config, model, docker, image, visualizer, ordinal, attempt_id, store):
            self.invoked.append(ordinal)
            directory = root / attempt_id
            status = self.status(ordinal)
            status.update(status="RENDERED_UNSCORED", render="ok", eligible=True,
                          failure_category=None, totals={"requests": 1, "completion_tokens": ordinal})
            if outcomes[ordinal - 1] == "failure":
                status.update(status="MODEL_FAILED", eligible=False, failure_category="MODEL")
            elif outcomes[ordinal - 1] == "protocol":
                status.update(status="PROTOCOL_ERROR", failure_category="PROTOCOL")
            elif outcomes[ordinal - 1] in {"QUOTA", "AUTH", "CONTENT_FILTER", "TRANSPORT"}:
                status.update(status=outcomes[ordinal - 1] + "_ERROR", eligible=False,
                              failure_category=outcomes[ordinal - 1], model_failure=False)
            run.write_json(directory / "status.json", status)
            run.write_json(directory / "profile.json", {
                "eligible": True, "evaluation_status": "evaluated", "cacheable": True,
                "status": status["status"], "model": model["model"], "craft": {"craft_score": 0}})
            if outcomes[ordinal - 1] == "finalization":
                run.write_json(directory / "finalization-error.json", {"error": "EvaluationFailed"})
                raise RuntimeError("evaluation failed")
        with patch.object(run, "run_one", side_effect=attempt):
            return run.run_model_sequence(self.root, self.config, self.model, None, "image", "video", None)

    def test_first_success_prevents_remaining_invocations_and_preserves_null_slots(self):
        result = self.execute(["success", "failure", "failure"])
        self.assertEqual(self.invoked, [1])
        self.assertEqual(result["selected_attempt_id"], "model-rep-1")
        self.assertEqual(result["skipped"], ["model-rep-2", "model-rep-3"])
        for ordinal in (2, 3):
            status = self.status(ordinal)
            self.assertEqual(status["status"], "SKIPPED_AFTER_SUCCESS")
            self.assertEqual(status["selected_attempt_id"], "model-rep-1")
            self.assertIsNone(status["totals"])
            self.assertIsNone(status["quality_score"])
        self.assertEqual(json.loads((self.root / "model-attempts.json").read_text()), result)

    def test_failure_advances_once_and_retains_original_outcome(self):
        result = self.execute(["failure", "success", "failure"])
        self.assertEqual(self.invoked, [1, 2])
        self.assertEqual(self.status(1)["status"], "MODEL_FAILED")
        self.assertEqual(self.status(1)["totals"]["completion_tokens"], 1)
        self.assertEqual(result["selected_attempt_id"], "model-rep-2")

    def test_protocol_and_finalization_errors_with_rendered_profile_do_not_succeed(self):
        result = self.execute(["protocol", "finalization", "success"])
        self.assertEqual(self.invoked, [1, 2, 3])
        self.assertEqual(result["selected_attempt_id"], "model-rep-3")
        self.assertEqual(result["errors"], [{"attempt_id": "model-rep-2", "error": "RuntimeError"}])
        self.assertEqual(self.status(1)["render"], "ok")
        self.assertTrue((self.root / "model-rep-2/finalization-error.json").exists())

    def test_three_failures_exhaust_slots_without_selecting_or_replacing_any(self):
        result = self.execute(["failure", "failure", "failure"])
        self.assertEqual(self.invoked, [1, 2, 3])
        self.assertIsNone(result["selected_attempt_id"])
        self.assertEqual(result["skipped"], [])
        self.assertEqual([self.status(n)["status"] for n in (1, 2, 3)], ["MODEL_FAILED"] * 3)

    def independent(self, ordinals):
        self.config = {"max_attempts": 3, "policies": {**campaign.POLICIES, "attempt_selection": campaign.INDEPENDENT,
                                                       "repetitions": ordinals, "linked_condition": None}}

    def test_independent_repetitions_run_every_slot_after_success_and_failure(self):
        self.independent([1, 2, 3])
        result = self.execute(["success", "failure", "success"])
        self.assertEqual(self.invoked, [1, 2, 3])
        self.assertIsNone(result["selected_attempt_id"])
        self.assertEqual(result["eligible"], ["model-rep-1", "model-rep-3"])
        self.assertEqual(result["skipped"], [])
        self.assertEqual([self.status(n)["status"] for n in (1, 2, 3)], ["RENDERED_UNSCORED", "MODEL_FAILED", "RENDERED_UNSCORED"])

    def test_declared_repetitions_run_only_their_slots_and_quota_still_stops(self):
        self.independent([2, 3])
        result = self.execute(["success", "QUOTA", "success"])
        self.assertEqual(self.invoked, [2])
        self.assertEqual(result["stopped_after"], {"attempt_id": "model-rep-2", "failure_category": "QUOTA"})
        self.assertEqual(result["reserved"], ["model-rep-3"])
        self.assertEqual((self.status(1)["status"], self.status(3)["status"]), ("RESERVED", "RESERVED"))

    def test_quota_or_content_filter_stops_sequence_and_leaves_later_slots_reserved(self):
        for category in ("QUOTA", "CONTENT_FILTER"):
            with self.subTest(category=category):
                self.setUp()
                result = self.execute(["failure", category, "success"])
                self.assertEqual(self.invoked, [1, 2])
                self.assertEqual(result["stopped_after"], {"attempt_id": "model-rep-2", "failure_category": category})
                self.assertEqual(result["reserved"], ["model-rep-3"])
                self.assertIsNone(result["selected_attempt_id"])
                self.assertEqual(result["skipped"], [])
                self.assertEqual(self.status(2)["model_failure"], False)
                self.assertEqual(self.status(3)["status"], "RESERVED")

    def test_auth_failure_on_first_slot_consumes_only_that_slot(self):
        result = self.execute(["AUTH", "success", "success"])
        self.assertEqual(self.invoked, [1])
        self.assertEqual(result["reserved"], ["model-rep-2", "model-rep-3"])
        self.assertEqual([self.status(n)["status"] for n in (2, 3)], ["RESERVED", "RESERVED"])

    def test_transport_failure_still_advances_to_the_next_slot(self):
        result = self.execute(["TRANSPORT", "success", "failure"])
        self.assertEqual(self.invoked, [1, 2])
        self.assertIsNone(result["stopped_after"])
        self.assertEqual(result["selected_attempt_id"], "model-rep-2")

    def queue_root(self, transport=None):
        model = {"id": "model", "model": "exact", "response_model": "exact", "provider": "go", "api": "chat",
                 "base_url": "https://fixture.invalid/v1", "api_key_env": "TEST_KEY", "effective_settings": {}}
        linked = {"campaign_id": "fixture-linked", "attempt_id": "model-rep-2", "status": "QUOTA_ERROR",
                  "status_sha256": "0" * 64, "outcome": "FAILURE", "failure_category": "QUOTA"}
        scored = {**linked, "attempt_id": "model-rep-3", "status": "RENDERED_UNSCORED", "outcome": "SUCCESS",
                  "failure_category": None}
        config = {"schema": "keygen-native-campaign-3", "campaign_id": "fixture-queue", "max_attempts": 3,
                  "models": [model], "transport": transport or {"backend": "local"},
                  "concurrency": {"workers": 2, "providers": {"go": 1}},
                  "policies": {**campaign.POLICIES, "attempt_selection": campaign.QUEUE, "repetitions": [1, 2, 3],
                               "max_queue_attempts": 3, "linked_campaigns": [],
                               "plan": {"model": [{"repetition": 1, "origin": None}, {"repetition": 2, "origin": linked},
                                                  {"repetition": 3, "origin": scored}]}}}
        root = self.root / "queue"
        root.mkdir()
        snapshot = {"config_sha256": campaign.digest(config), "campaign": config, "image_id": "image", "visualizer_image_id": "video"}
        run.lock_campaign(root / "campaign.lock.json", snapshot)
        return root, config, snapshot

    def queue_attempt(self, outcomes):
        def attempt(root, config, model, docker, image, visualizer, repetition, attempt_id, store, retry_of):
            self.invoked.append(attempt_id)
            directory = root / attempt_id
            status = json.loads((directory / "status.json").read_text())
            if outcomes[attempt_id] == "success":
                status.update(status="RENDERED_UNSCORED", render="ok", eligible=True, failure_category=None, model_failure=False)
            else:
                status.update(status=outcomes[attempt_id] + "_ERROR", eligible=False,
                              failure_category=outcomes[attempt_id], model_failure=False)
            run.write_json(directory / "status.json", status)
            if outcomes[attempt_id] == "success":
                run.write_json(directory / "profile.json", {
                    "eligible": True, "evaluation_status": "evaluated", "cacheable": True, "evaluation_schema": 2,
                    "score_version": "fixture", "status": status["status"], "model": model["model"],
                    "inputs": {"artifacts": {"status.json": campaign.file_digest(directory / "status.json")}},
                    "craft": {"craft_score": 50}})
        return attempt

    def test_rerun_queue_waits_on_probes_and_reruns_only_infrastructure_failures(self):
        root, config, snapshot = self.queue_root()
        probes = iter(["quota", "ok", "ok", "ok"])
        probed = []
        def probe(model, credential):
            probed.append(next(probes))
            return {"category": probed[-1], "http_status": 200 if probed[-1] == "ok" else 429}
        outcomes = {"model-rep-1": "QUOTA", "model-rep-1-retry-1": "success", "model-rep-2-retry-1": "success"}
        with patch.object(run, "run_one", side_effect=self.queue_attempt(outcomes)), patch.object(run.STOP, "wait"):
            result = run.RerunQueue(root, config, None, snapshot, None, probe_interval=0, retry_interval=0,
                                    probe=probe).run()
        # No attempt starts while the probe reports a usage limit; the quota failure re-closes the gate.
        self.assertEqual(probed, ["quota", "ok", "ok"])
        self.assertEqual(self.invoked, ["model-rep-1", "model-rep-1-retry-1", "model-rep-2-retry-1"])
        self.assertEqual(json.loads((root / "model-rep-1/status.json").read_text())["status"], "QUOTA_ERROR")
        records = {name: json.loads((root / f"retry-{name}.json").read_text()) for name in ("model-rep-1-retry-1", "model-rep-2-retry-1")}
        self.assertEqual([(record["retry_of"], record["retry_of_campaign_id"], record["kind"]) for record in records.values()],
                         [("model-rep-1", "fixture-queue", "retry"), ("model-rep-2", "fixture-linked", "retry")])
        self.assertEqual([json.loads((root / name / "status.json").read_text())["retry_of"] for name in records],
                         ["model-rep-1", "model-rep-2"])
        self.assertEqual([(item["repetition"], item["state"], item["attempt_id"]) for item in result["ordinals"]],
                         [(1, "done", "model-rep-1-retry-1"), (2, "done", "model-rep-2-retry-1")])
        self.assertEqual(result["status"], "COMPLETED")

    def test_rerun_queue_gates_each_model_holds_deferred_ones_and_continues_earlier_reruns(self):
        root, config, snapshot = self.queue_root()
        base = config["models"][0]
        config["models"] = [{**base, "id": "fable", "model": "fable-exact", "response_model": "fable-exact"},
                            {**base, "id": "held", "model": "held-exact", "response_model": "held-exact"}, base]
        config["concurrency"] = {"workers": 3, "providers": {"go": 3}}
        from benchmark import report
        link = lambda model_id, n, index, campaign_id, status, outcome, category: {
            "campaign_id": campaign_id, "attempt_id": report.queue_chain_id(model_id, n, index), "status": status,
            "status_sha256": "0" * 64, "outcome": outcome, "failure_category": category}
        scored = lambda model_id, n: {"repetition": n, "origin": link(model_id, n, 0, "fixture-linked", "RENDERED_UNSCORED", "SUCCESS", None)}
        config["policies"]["plan"] = {
            "fable": [{"repetition": 1, "origin": None}, scored("fable", 2), scored("fable", 3)],
            "held": [{"repetition": 1, "origin": None}, scored("held", 2), scored("held", 3)],
            "model": [scored("model", 1),
                      {"repetition": 2, "origin": link("model", 2, 0, "fixture-linked", "QUOTA_ERROR", "FAILURE", "QUOTA"),
                       "reruns": [link("model", 2, 1, "fixture-queue-1", "INTERRUPTED", "FAILURE", "INFRA")]},
                      scored("model", 3)]}
        snapshot = {**snapshot, "config_sha256": campaign.digest(config), "campaign": config}
        (root / "campaign.lock.json").unlink()
        run.lock_campaign(root / "campaign.lock.json", snapshot)
        probed = []
        def probe(model, credential):
            probed.append(model["id"])
            return {"category": "quota" if model["id"] == "fable" else "ok", "http_status": 429 if model["id"] == "fable" else 200}
        waits = []
        def wait(seconds):
            waits.append(seconds)
            if len(waits) >= 4:
                run.STOP.set()
        with patch.object(run, "run_one", side_effect=self.queue_attempt({"model-rep-2-retry-2": "success"})), \
                patch.object(run.STOP, "wait", side_effect=wait), self.assertRaises(KeyboardInterrupt):
            run.RerunQueue(root, config, None, snapshot, None, probe_interval=10 ** 6, retry_interval=10 ** 6,
                           probe=probe, holds=["held"]).run()
        # Fable's usage limit closes only Fable; the held model is never probed or started.
        self.assertEqual((probed, self.invoked), (["fable", "model"], ["model-rep-2-retry-2"]))
        record = json.loads((root / "retry-model-rep-2-retry-2.json").read_text())
        self.assertEqual((record["retry_of"], record["retry_of_campaign_id"], record["kind"]),
                         ("model-rep-2-retry-1", "fixture-queue-1", "retry"))
        state = json.loads((root / "queue-state.json").read_text())
        self.assertEqual({(item["model_id"], item["state"]) for item in state["ordinals"]},
                         {("fable", "next"), ("held", "held"), ("model", "done")})

    def test_pooled_queue_probes_each_key_once_and_a_quota_closes_only_that_key(self):
        root, config, snapshot = self.queue_root()
        config["concurrency"] = {"workers": 2, "providers": {"go": 2}, "key_pools": {"TEST_KEY": {"TEST_KEY_A": 1, "TEST_KEY_B": 1}}}
        snapshot = {**snapshot, "config_sha256": campaign.digest(config), "campaign": config}
        (root / "campaign.lock.json").unlink()
        run.lock_campaign(root / "campaign.lock.json", snapshot)
        probed, keys = [], {}
        def probe(model, credential):
            probed.append(credential)
            return {"category": "ok", "http_status": 200}
        attempt = self.queue_attempt({"model-rep-1": "QUOTA", "model-rep-1-retry-1": "success", "model-rep-2-retry-1": "success"})
        both_started = threading.Event()
        def pooled_attempt(*args, key_lease):
            # The queue, not the attempt, releases the key once it has classified the outcome.
            keys[args[7]] = key_lease.name
            if args[7] == "model-rep-2-retry-1":
                both_started.set()
            elif args[7] == "model-rep-1":
                both_started.wait(5)  # hold key A while the second ordinal is admitted
            attempt(*args)
            if args[7] == "model-rep-1":
                status = json.loads((root / "model-rep-1/status.json").read_text())
                status["error"] = 'GoUsageLimitError "limitName":"weekly"'
                run.write_json(root / "model-rep-1/status.json", status)
        controller = self.root / "controller"
        controller.mkdir()
        with patch.object(run, "run_one", side_effect=pooled_attempt), patch.object(run.STOP, "wait"), \
                patch.object(tempfile, "tempdir", str(controller)), \
                patch.dict("os.environ", {"TEST_KEY_A": "synthetic-a", "TEST_KEY_B": "synthetic-b"}):
            result = run.RerunQueue(root, config, None, snapshot, None, probe_interval=3600, retry_interval=60,
                                    probe=probe).run()
        # One probe per key before its first use, each on its own credential; the QUOTA attempt
        # closes only its key (6 h for a weekly window), so the rerun goes to the other, already
        # verified key without a probe.
        self.assertEqual(probed, ["synthetic-a", "synthetic-b"])
        self.assertEqual(keys, {"model-rep-1": "TEST_KEY_A", "model-rep-2-retry-1": "TEST_KEY_B",
                                "model-rep-1-retry-1": "TEST_KEY_B"})
        gates = result["key_gates"]
        self.assertEqual((gates["TEST_KEY_A"]["open"], gates["TEST_KEY_A"]["closed_by"]), (False, "model-rep-1"))
        self.assertGreater(gates["TEST_KEY_A"]["next_probe_at"], time.time() + 6 * 3600 - 60)
        self.assertTrue(gates["TEST_KEY_B"]["open"])
        self.assertEqual(result["status"], "COMPLETED")

    def test_pooled_queue_with_zero_gate_freshness_probes_the_key_before_every_start(self):
        root, config, snapshot = self.queue_root()
        config["concurrency"] = {"workers": 1, "providers": {"go": 1}, "key_pools": {"TEST_KEY": {"TEST_KEY_A": 1}}}
        snapshot = {**snapshot, "config_sha256": campaign.digest(config), "campaign": config}
        (root / "campaign.lock.json").unlink()
        run.lock_campaign(root / "campaign.lock.json", snapshot)
        events = []
        def probe(model, credential):
            events.append("probe")
            return {"category": "ok", "http_status": 200}
        attempt = self.queue_attempt({"model-rep-1": "success", "model-rep-2-retry-1": "success"})
        def pooled_attempt(*args, key_lease):
            events.append(args[7])
            attempt(*args)
        controller = self.root / "controller"
        controller.mkdir()
        with patch.object(run, "run_one", side_effect=pooled_attempt), patch.object(run.STOP, "wait"), \
                patch.object(tempfile, "tempdir", str(controller)), patch.dict("os.environ", {"TEST_KEY_A": "synthetic-a"}):
            result = run.RerunQueue(root, config, None, snapshot, None, probe_interval=3600, retry_interval=60,
                                    probe=probe, key_gate_fresh=0).run()
        # The finished attempt verified the key, but the second start still sends its own probe first.
        self.assertEqual(events, ["probe", "model-rep-1", "probe", "model-rep-2-retry-1"])
        self.assertEqual(result["status"], "COMPLETED")

    def test_funds_usage_limit_and_rate_limit_errors_are_quota_not_protocol(self):
        import litellm
        for error in (litellm.APIError(status_code=500, message="Upstream request failed: Insufficient account funds",
                                       llm_provider="openai", model="x"),
                      litellm.RateLimitError(message="Go usage limit exceeded", llm_provider="openai", model="x"),
                      litellm.APIError(status_code=402, message="A positive credit balance is required",
                                       llm_provider="openai", model="x")):
            with self.subTest(error=str(error)[:60]):
                self.assertEqual(run.failure_category(error), "QUOTA")
        self.assertEqual(run.failure_category(litellm.BadRequestError(message="bad", llm_provider="openai", model="x")), "PROTOCOL")

    def test_transport_retries_counted_from_unanswered_requests(self):
        directory = self.root / "retried"
        directory.mkdir()
        events = ["request", "request", "response", "request", "response", "request", "request", "request"]
        (directory / "transport.jsonl").write_text("".join(json.dumps({"event": e}) + "\n" for e in events))
        self.assertEqual(run.summarize(directory)["transport_retries"], 3)

    def test_existing_interrupted_or_unknown_slots_are_never_run_or_hidden(self):
        for outcome in ("INTERRUPTED", "UNKNOWN"):
            status = self.status(2)
            status.update(status=outcome, eligible=False)
            run.write_json(self.root / "model-rep-2/status.json", status)
            with patch.object(run, "run_one") as execute, self.assertRaises(ValueError):
                run.run_model_sequence(self.root, self.config, self.model, None, "image", "video", None)
            execute.assert_not_called()
            self.assertEqual(self.status(2)["status"], outcome)

    def test_evaluation_failure_invalidates_run(self):
        directory = self.root / "model-rep-1"
        status = self.status(1)
        status.update(status="RENDERED_UNSCORED", render="ok", eligible=True)
        run.write_json(directory / "status.json", status)
        with patch("score.profile_attempt", side_effect=RuntimeError("scorer failed")), self.assertRaises(RuntimeError):
            run.finalize_attempt(directory)
        failed = self.status(1)
        self.assertEqual(failed["status"], "FINALIZATION_ERROR")
        self.assertFalse(failed["eligible"])
        self.assertEqual(failed["finalization_error"]["failure_category"], "EVAL")

    def test_success_requires_actual_eligible_profile_not_render_or_craft_score_alone(self):
        status = {"status": "RENDERED_UNSCORED", "render": "ok", "eligible": True,
                  "model": self.model}
        profile = {"eligible": True, "evaluation_status": "evaluated", "cacheable": True,
                   "status": status["status"], "model": self.model["model"], "craft": {"craft_score": 0}}
        self.assertTrue(run.attempt_succeeded(status, profile))
        self.assertFalse(run.attempt_succeeded(status, None))
        for mutation in ({"eligible": False}, {"cacheable": False}, {"evaluation_status": "ineligible"},
                         {"evaluation_error": {"category": "EVAL"}}, {"model": "different"}):
            with self.subTest(mutation=mutation):
                self.assertFalse(run.attempt_succeeded(status, {**profile, **mutation}))
        self.assertFalse(run.attempt_succeeded(status, profile, finalization_error=True))


class SubmissionCollectionTests(unittest.TestCase):
    """Real collect()/safe_unpack() over GNU tar of a local stand-in for /workspace."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / "workspace"
        (self.workspace / "submission").mkdir(parents=True)
        self.run_dir = self.root / "attempt"
        self.run_dir.mkdir()
        export_command = run.workspace_export_command
        export = patch.object(run, "workspace_export_command",
                              lambda docker, name, source: [
                                  part.replace("/export", str(self.workspace))
                                  for part in export_command([], name, source)[2:]])
        export.start()
        self.addCleanup(export.stop)

    def write(self, name, size):
        path = self.workspace / "submission" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"Extended Module: " + b"x" * max(0, size - 17))

    def collect(self, limit=4096):
        return run.collect_submission([], "container", self.run_dir, limit)

    def test_oversize_extras_are_dropped_with_a_note_and_tune_is_kept(self):
        self.write("tune.xm", 1000)
        self.write("preview.wav", 8000)
        result = self.collect()
        self.assertEqual(result["status"], "dropped")
        self.assertIn("limit", result["reason"])
        self.assertEqual(sorted(p.name for p in (self.run_dir / "submission").iterdir()), ["tune.xm"])
        self.assertFalse((self.run_dir / ".submission-extras").exists())

    def test_linked_extra_is_dropped_not_a_model_failure(self):
        self.write("tune.xm", 100)
        (self.workspace / "submission/link").symlink_to("/etc/passwd")
        self.assertEqual(self.collect()["status"], "dropped")
        self.assertTrue((self.run_dir / "submission/tune.xm").is_file())

    def test_fitting_extras_are_collected_beside_tune(self):
        self.write("tune.xm", 100)
        self.write("src/make.py", 50)
        self.assertEqual(self.collect(), {"status": "collected", "files": 1})
        self.assertEqual((self.run_dir / "submission/tune.xm").stat().st_size, 100)
        self.assertTrue((self.run_dir / "submission/src/make.py").is_file())

    def test_missing_or_oversize_tune_remains_the_models_failure(self):
        self.write("preview.wav", 100)
        with self.assertRaisesRegex(ValueError, "Submission not found"):
            self.collect()
        shutil.rmtree(self.run_dir / "submission", ignore_errors=True)
        self.write("tune.xm", 8000)
        with self.assertRaisesRegex(ValueError, "limit"):
            self.collect()


if __name__ == "__main__":
    unittest.main()
