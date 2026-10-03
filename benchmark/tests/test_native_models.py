"""Synthetic HTTP peers exercise the original native SDK/model history paths."""
from __future__ import annotations

import ipaddress
import json
import os
import subprocess
import tempfile
import threading
import unittest
from contextlib import contextmanager, nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from benchmark import native_models as native
from benchmark import run

CONFIG = {"native": {"timeout_seconds": 5, "retries": 0}}
RETRYING = {"native": {"timeout_seconds": 5, "retries": native.MAX_TRANSPORT_RETRIES}}


def model_spec(api="responses", provider="codex_oauth", base="http://127.0.0.1:8417/v1"):
    name = "claude-sonnet-4-5" if api == "messages" else "gpt-5.5"
    return {"id": "native-test", "model": name, "response_model": name,
            "provider": provider, "api": api, "base_url": base,
            "api_key_env": "BENCHMARK_TEST_KEY",
            "generation": {"max_tokens": 4096} if api != "responses" else {"max_output_tokens": 4096},
            "tier": {"level": "none-available", "reasoning": {}, "spec_sha256": "0" * 64},
            "readiness": {"status": "qualification", "evidence": None, "verified_at": None}}


def tiered(spec, level, **reasoning):
    """Declare a tier and its exact reasoning wire fields, as a tier-spec entry would."""
    spec["generation"].update(reasoning)
    spec["tier"] = {"level": level, "reasoning": reasoning, "spec_sha256": "0" * 64}
    return spec


MAX_TIER = {
    "chat": ("max", {"reasoning_effort": "max"}),
    "responses": ("xhigh", {"reasoning": {"effort": "xhigh"}}),
    "messages": ("max", {"thinking": {"type": "adaptive"}, "output_config": {"effort": "max"}}),
}


@contextmanager
def peer(api, error=False, failures=(), truncated=False, refused=0, response_model=None, base_prefix=""):
    """failures: (status, message) replies sent before the normal reply, one per request.

    refused: Messages replies after the failures that Anthropic's content filter blocked
    (stop_reason refusal, no content)."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append((self.path, payload))
            expected_path = base_prefix + {"chat": "/v1/chat/completions", "messages": "/v1/messages",
                                           "responses": "/v1/responses"}[api]
            if self.path != expected_path:
                self.send_error(404, "Incorrect native protocol endpoint")
                return
            if len(seen) <= len(failures):
                status, message = failures[len(seen) - 1]
                raw = json.dumps({"error": {"type": "error", "message": message}}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if error:
                response = {"error": {"type": "gateway_error", "message": "BENCHMARK_SYNTHETIC_SECRET"}}
            elif len(seen) <= len(failures) + refused:
                response = {"id": f"msg-{len(seen)}", "type": "message", "role": "assistant",
                            "model": payload["model"], "stop_reason": "refusal", "stop_sequence": None,
                            "content": [], "usage": {"input_tokens": 11, "output_tokens": 0}}
            elif truncated:
                response = {"id": "chatcmpl-cut", "object": "chat.completion", "created": 1,
                            "model": payload["model"], "choices": [{"index": 0, "finish_reason": "length",
                            "message": {"role": "assistant", "content": "I will now write the whole mod"}}],
                            "usage": {"prompt_tokens": 11, "completion_tokens": 4096, "total_tokens": 4107}}
            elif api == "chat":
                response = {"id": f"chatcmpl-{len(seen)}", "object": "chat.completion", "created": 1,
                            "model": payload["model"], "choices": [{"index": 0, "finish_reason": "tool_calls",
                            "message": {"role": "assistant", "content": None,
                            "reasoning_content": "preserved reasoning",
                            "tool_calls": [{"id": f"call-{len(seen)}", "type": "function",
                            "function": {"name": "bash", "arguments": '{"command":"echo ready"}'}}]}}],
                            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}
            elif api == "messages":
                response = {"id": f"msg-{len(seen)}", "type": "message", "role": "assistant",
                            "model": payload["model"], "stop_reason": "tool_use", "stop_sequence": None,
                            "content": [{"type": "thinking", "thinking": "preserved thinking", "signature": "signed"},
                            {"type": "tool_use", "id": f"call-{len(seen)}", "name": "bash",
                             "input": {"command": "echo ready"}}],
                            "usage": {"input_tokens": 11, "output_tokens": 7}}
            else:
                response = {"id": f"resp-{len(seen)}", "object": "response", "created_at": 1,
                            "model": payload["model"], "status": "completed", "error": None,
                            "incomplete_details": None, "parallel_tool_calls": True,
                            "output": [{"id": f"rs-{len(seen)}", "type": "reasoning",
                                        "summary": [], "encrypted_content": "preserved-encrypted-state"},
                                       {"id": f"fc-{len(seen)}", "type": "function_call",
                                        "call_id": f"call-{len(seen)}", "name": "bash",
                                        "arguments": '{"command":"echo ready"}', "status": "completed"}],
                            "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
                            "tool_choice": "auto", "tools": payload["tools"]}
            if response_model is not None and "model" in response:
                response["model"] = response_model
            raw = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}{base_prefix}/v1", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextmanager
def worker_env(root, spec):
    home = root / "home"
    mini = home / "mini-config"
    mini.mkdir(parents=True)
    with patch.dict(os.environ, {"BENCHMARK_TEST_KEY": "BENCHMARK_SYNTHETIC_SECRET"}, clear=True):
        env = native.credential_env(CONFIG, spec)
        env.update(HOME=str(home), MSWEA_GLOBAL_CONFIG_DIR=str(mini), MSWEA_SILENT_STARTUP="1")
        with patch.dict(os.environ, env):
            yield


class LocalShell:
    def __init__(self, root):
        self.root = root

    def execute(self, action):
        result = subprocess.run(["/bin/sh", "-c", action["command"]], cwd=self.root,
                                capture_output=True, text=True, timeout=5)
        return {"output": result.stdout + result.stderr, "returncode": result.returncode}

    def get_template_vars(self):
        return {}

    def serialize(self):
        return {}


class NativeProtocolTests(unittest.TestCase):
    def roundtrip(self, api, provider=None, name=None, tier=None, output_limit=4096, response_name=None, cap_key=None,
                  base_prefix=""):
        provider = provider or {"chat": "go", "messages": "anthropic_oauth", "responses": "codex_oauth"}[api]
        with tempfile.TemporaryDirectory() as temporary, peer(api, response_model=response_name, base_prefix=base_prefix) as (base, seen):
            root = Path(temporary)
            spec = model_spec(api, provider, base)
            name = name or {"chat": "kimi-k3", "messages": "claude-opus-4-8"}.get(api)
            if name:
                spec["model"] = spec["response_model"] = name
            if response_name is not None:
                spec["response_model"] = response_name
            default_cap = "max_output_tokens" if api == "responses" else "max_tokens"
            cap_key = cap_key or default_cap
            spec["generation"].pop(default_cap)
            spec["generation"][cap_key] = output_limit
            level, reasoning = tier or MAX_TIER[api]
            tiered(spec, level, **reasoning)
            wire = native.transmitted_reasoning(spec)
            # Public endpoints use the synthetic peer; Devin exercises its real loopback URL
            # validation too. SDK, model, parser, serialization and history all execute.
            route = nullcontext() if provider == "devin" else patch.object(native, "validate_url", return_value=base)
            with route, patch.object(native, "check_custom_destination"), worker_env(root, spec):
                model = native.build_probe_model(CONFIG, spec, root)
                from minisweagent.agents.default import DefaultAgent
                agent = DefaultAgent(model, LocalShell(root), system_template="Frozen system",
                                     instance_template="{{task}}", step_limit=2, cost_limit=0,
                                     wall_time_limit_seconds=120, output_path=None)
                outcome = agent.run("Frozen task")
                self.assertEqual(outcome["exit_status"], "LimitsExceeded")
                messages = agent.messages
                observations = [message for message in messages if message.get("role") == "tool"
                                or message.get("type") == "function_call_output"]
                self.assertEqual([m["extra"]["returncode"] for m in observations], [0, 0])
                audits = native.audit_messages(messages, spec)
                self.assertEqual([a["identity_status"] for a in audits], ["identity_match", "identity_match"])
                self.assertEqual(audits[0]["usage"]["total_tokens"], 18)
                self.assertNotIn("BENCHMARK_SYNTHETIC_SECRET", json.dumps(model.serialize()))
                requests = [json.loads(line) for line in (root / "transport.jsonl").read_text().splitlines()]
                self.assertNotIn("BENCHMARK_SYNTHETIC_SECRET", json.dumps(requests))
                expected_wire = native.validate_model(CONFIG, spec)["expected_transmitted_generation"]
                for request_record in requests:
                    if request_record["event"] == "request":
                        actual_settings = request_record["settings"]
                        self.assertEqual({k: actual_settings[k] for k in expected_wire}, expected_wire)
                        self.assertEqual({k: actual_settings.get(k) for k in wire}, wire)
                # The declared tier's reasoning control reaches the endpoint on every request,
                # with any SDK extra_body envelope expanded into the HTTP body.
                self.assertEqual(len(seen), 2)
                for _, payload in seen:
                    self.assertEqual({k: payload.get(k) for k in wire}, wire)
                    self.assertEqual(payload[cap_key], output_limit)
                    self.assertNotIn("extra_body", payload)
                    if api == "chat":
                        self.assertEqual(payload["messages"][0]["role"], "system")
                if api == "responses":
                    self.assertEqual(seen[1][0], base_prefix + "/v1/responses")
                    history = seen[1][1]["input"]
                    self.assertTrue(any(item.get("encrypted_content") == "preserved-encrypted-state" for item in history))
                    self.assertTrue(any(item.get("type") == "function_call_output"
                                        and item.get("call_id") == "call-1" and "ready" in item["output"]
                                        for item in history))
                    self.assertEqual(seen[0][1]["max_output_tokens"], output_limit)
                elif api == "messages":
                    self.assertEqual(seen[1][0], base_prefix + "/v1/messages")
                    blocks = [block for item in seen[1][1]["messages"] for block in item["content"]]
                    self.assertTrue(any(block.get("signature") == "signed" for block in blocks))
                    self.assertTrue(any(block.get("type") == "tool_result"
                                        and block.get("tool_use_id") == "call-1" for block in blocks))
                else:
                    self.assertEqual(seen[1][0], base_prefix + "/v1/chat/completions")
                    history = seen[1][1]["messages"]
                    self.assertEqual(history[-1]["tool_call_id"], "call-1")
                    self.assertIn("<time_left>", history[-1]["content"])
                    self.assertEqual(history[-2]["reasoning_content"], "preserved reasoning")
                return messages, seen, model.serialize()

    def test_chat_native_history(self):
        self.roundtrip("chat")

    def test_devin_chat_native_max_effort_and_default_history(self):
        for name, tier in (("gpt-oss-120b", ("max", {"reasoning_effort": "max"})),
                           ("kimi-k2.7", ("none-available", {}))):
            with self.subTest(name=name, tier=tier[0]):
                _, seen, _ = self.roundtrip("chat", "devin", f"devin/{name}", tier,
                                            output_limit=64000, response_name=name)
                if tier[0] == "none-available":
                    for _, payload in seen:
                        self.assertNotIn("reasoning_effort", payload)
                        self.assertNotIn("reasoning", payload)

    def test_devin_gpt_catalog_xhigh_reaches_chat_without_rerouting(self):
        for name in ("gpt-5-4", "gpt-5-4-mini", "gpt-5-3-codex"):
            with self.subTest(name=name):
                self.roundtrip("chat", "devin", f"devin/{name}",
                               ("xhigh", {"reasoning_effort": "xhigh"}), output_limit=64000,
                               response_name=name, cap_key="max_completion_tokens")

    def test_devin_gpt_capability_is_exact_route_and_effort(self):
        for provider, base, effort in (("devin", "http://127.0.0.1:8417/v1", "high"),
                                       ("go", "https://opencode.ai/zen/go/v1", "xhigh")):
            spec = tiered(model_spec("chat", provider, base), effort, reasoning_effort=effort)
            spec["model"] = spec["response_model"] = "devin/gpt-5-4"
            spec["generation"]["max_completion_tokens"] = spec["generation"].pop("max_tokens")
            with self.subTest(provider=provider, effort=effort), self.assertRaises(ValueError):
                native.validate_model(CONFIG, spec)

    def test_devin_response_identity_is_not_inferred_from_request(self):
        with tempfile.TemporaryDirectory() as temporary, peer("chat", response_model="other-model") as (base, seen):
            root = Path(temporary)
            spec = tiered(model_spec("chat", "devin", base), "max", reasoning_effort="max")
            spec["model"] = "devin/exact-model"
            spec["response_model"] = "exact-model"
            with worker_env(root, spec):
                model = native.build_probe_model(CONFIG, spec, root)
                message = model.query([{"role": "user", "content": "Use bash"}])
            self.assertEqual(native.audit_messages([message], spec)[0]["identity_status"], "identity_mismatch")
            transport = [json.loads(line) for line in (root / "transport.jsonl").read_text().splitlines()]
            self.assertEqual(transport[-1]["response_model"], "other-model")
            self.assertEqual(transport[-1]["identity_status"], "identity_mismatch")
            self.assertEqual(seen[0][1]["model"], "devin/exact-model")

    def test_direct_and_custom_routes_use_native_protocols(self):
        for provider, api, name, tier in (
                ("openai", "chat", "gpt-4.1", ("none-available", {})),
                ("openai", "responses", None, None),
                ("anthropic", "messages", None, None),
                ("custom", "chat", "compatible-model", ("none-available", {})),
                ("custom", "responses", None, None),
                ("custom", "messages", "compatible-model",
                 ("thinking-budget", {"thinking": {"type": "enabled", "budget_tokens": 1024}}))):
            with self.subTest(provider=provider, api=api):
                self.roundtrip(api, provider, name, tier, base_prefix="/service" if provider == "custom" else "")

    def test_go_glm_chat_drops_only_the_sdk_synthesized_assistant_key(self):
        # The SDK wraps its own refusal=None as provider_specific_fields; Go's GLM upstream rejects
        # that key, so only its declared routes omit it from the outgoing assistant message.
        sent = {}
        for name in ("glm-5.2", "glm-5.3", "kimi-k3", "glm-5.3-flash"):
            with self.subTest(name=name):
                messages, seen, serialized = self.roundtrip("chat", "go", name)
                assistant = seen[1][1]["messages"][2]
                self.assertEqual(assistant["role"], "assistant")
                self.assertEqual(assistant["tool_calls"][0]["id"], "call-1")
                # Native history itself is unchanged on every route.
                self.assertEqual(messages[2]["provider_specific_fields"], {"refusal": None})
                sent[name] = assistant
                declared = name in {"glm-5.2", "glm-5.3"}
                self.assertEqual("provider_specific_fields" not in assistant, declared)
                self.assertEqual(serialized["info"]["config"]["model_type"],
                                 "native_models.GoStrictHistoryLitellmModel" if declared
                                 else "minisweagent.models.litellm_model.LitellmModel")
        other = {k: v for k, v in sent["kimi-k3"].items() if k != "provider_specific_fields"}
        self.assertEqual(sent["kimi-k3"]["provider_specific_fields"], {"refusal": None})
        for name in ("glm-5.2", "glm-5.3"):
            self.assertEqual(sent[name], other)

    def test_history_key_removal_is_route_scoped_and_value_exact(self):
        def spec(provider, api, base):
            level, reasoning = MAX_TIER[api] if api == "chat" else ("none-available", {})
            value = tiered(model_spec(api, provider, base), level, **reasoning)
            value["model"] = value["response_model"] = "glm-5.2"
            return value

        go = native.validate_model(CONFIG, spec("go", "chat", "https://opencode.ai/zen/go/v1"))
        self.assertEqual(go["history_key_removal"]["key"], "provider_specific_fields")
        for provider, api, base in (("nim", "chat", "https://integrate.api.nvidia.com/v1"),
                                    ("go", "messages", "https://opencode.ai/zen/go/v1")):
            with self.subTest(provider=provider, api=api):
                self.assertNotIn("history_key_removal", native.validate_model(CONFIG, spec(provider, api, base)))
        removal = native.HISTORY_KEY_REMOVALS[("go", "chat", "glm-5.2")]
        endpoint_data = {"role": "assistant", "content": "", "provider_specific_fields": {"refusal": "no"}}
        with self.assertRaisesRegex(ValueError, "beyond the SDK-synthesized value"):
            native.remove_synthesized_key(endpoint_data, removal)
        tool = {"role": "tool", "content": "ok", "provider_specific_fields": {"refusal": None}}
        self.assertIs(native.remove_synthesized_key(tool, removal), tool)

    def test_responses_native_reasoning_history(self):
        self.roundtrip("responses")

    def test_messages_native_signed_thinking_history(self):
        self.roundtrip("messages")

    def test_nim_chat_template_thinking_reaches_endpoint(self):
        self.roundtrip("chat", "nim", "moonshotai/kimi-k3",
                       ("thinking-on", {"extra_body": {"chat_template_kwargs": {"thinking": True}}}))

    def test_go_messages_budget_thinking_reaches_endpoint_for_non_claude_name(self):
        self.roundtrip("messages", "go", "qwen3.7-plus",
                       ("thinking-budget", {"thinking": {"type": "enabled", "budget_tokens": 2048}}))

    def test_go_messages_approved_xhigh_override_reaches_endpoint(self):
        # The user-approved capability declaration lets the real SDK send effort xhigh.
        for name in ("qwen3.8-flash", "qwen3.8-max"):
            with self.subTest(name=name):
                self.roundtrip("messages", "go", name, ("xhigh", {"output_config": {"effort": "xhigh"}}))

    def test_go_messages_effort_the_sdk_cannot_send_fails_closed(self):
        # The pinned SDK gates output_config xhigh/max to Claude names at request time; an
        # approved override must not open the gate for any other name, route or effort.
        def spec(name, level, provider="go", base="https://opencode.ai/zen/go/v1"):
            value = tiered(model_spec("messages", provider, base), level, output_config={"effort": level})
            value["model"] = value["response_model"] = name
            return value

        native.validate_model(CONFIG, spec("qwen3.8-max", "xhigh"))  # registers the approved name
        for name, level, provider in (("qwen3.7-plus", "xhigh", "go"), ("qwen3.8-max", "max", "go"),
                                      ("qwen3.8-flash", "low", "go"),
                                      ("qwen3.8-max", "xhigh", "anthropic_oauth")):
            with self.subTest(name=name, level=level, provider=provider):
                base = "http://127.0.0.1:8417/v1" if provider == "anthropic_oauth" else "https://opencode.ai/zen/go/v1"
                with self.assertRaisesRegex(ValueError, "output_config|Capability override"):
                    native.validate_model(CONFIG, spec(name, level, provider, base))

    def test_http_200_error_is_gateway_error_not_identity_fallback(self):
        with tempfile.TemporaryDirectory() as temporary, peer("responses", error=True) as (base, seen):
            root = Path(temporary)
            spec = model_spec(base=base)
            with worker_env(root, spec):
                model = native.build_probe_model(CONFIG, spec, root)
                try:
                    message = model.query([{"role": "user", "content": "Use bash"}])
                except Exception as error:
                    self.assertEqual(native.classify_error(error, root), "gateway_error")
                else:
                    self.assertEqual(native.audit_messages([message], spec)[0]["identity_status"], "gateway_error")
                self.assertEqual(len(seen), 1)
                audit = (root / "transport.jsonl").read_text()
                self.assertNotIn("BENCHMARK_SYNTHETIC_SECRET", audit)
                self.assertIn("gateway_error", audit)

    def query_once(self, config, failures=(), truncated=False, api="chat", refused=0, bound=False, provider=None):
        """One real SDK query against the peer; returns (outcome, seen, transport events).

        bound applies the production content-filter bound (run.bound_content_filter)."""
        with tempfile.TemporaryDirectory() as temporary, \
                peer(api, failures=failures, truncated=truncated, refused=refused) as (base, seen):
            root = Path(temporary)
            provider = provider or {"chat": "go", "messages": "anthropic_oauth", "responses": "codex_oauth"}[api]
            spec = model_spec(api, provider, base)
            if api == "chat":
                spec["model"] = spec["response_model"] = "kimi-k3"
            with patch.object(native, "validate_url", return_value=base), worker_env(root, spec):
                model = native.build_probe_model(config, spec, root)
                if bound:
                    model = run.bound_content_filter(model, spec, root)
                try:
                    outcome = model.query([{"role": "user", "content": "Use bash"}])
                except Exception as error:  # noqa: BLE001 - the classified failure is the outcome
                    outcome = error
                events = [json.loads(line)["event"] for line in (root / "transport.jsonl").read_text().splitlines()]
                self.totals = run.summarize(root, spec)
                return outcome, seen, events

    def test_content_filter_block_is_resent_up_to_three_sends(self):
        blocked = (400, "Output blocked by content filtering policy")
        for form, kwargs, events in (
                ("stop_reason", {"refused": 2}, ["request", "response", "content_filter_block"]),
                ("error", {"failures": [blocked] * 2}, ["request", "content_filter_block"])):
            with self.subTest(form=form):
                outcome, seen, recorded = self.query_once(RETRYING, api="messages", bound=True, **kwargs)
                self.assertIsInstance(outcome, dict)
                self.assertEqual(outcome["extra"]["actions"][0]["command"], "echo ready")
                # Every send is identical: a blocked reply never enters native history.
                self.assertEqual(len(seen), 3)
                self.assertEqual(len({json.dumps(payload, sort_keys=True) for _, payload in seen}), 1)
                self.assertEqual(recorded, events * 2 + ["request", "response"])
                self.assertEqual((self.totals["content_filter_blocks"], self.totals["transport_retries"]), (2, 0))

    def test_third_content_filter_block_fails_as_content_filter(self):
        blocked = (400, "Output blocked by content filtering policy")
        for kwargs in ({"refused": 3}, {"failures": [blocked] * 3}, {"failures": [blocked], "refused": 2}):
            with self.subTest(**{key: len(value) if isinstance(value, list) else value for key, value in kwargs.items()}):
                outcome, seen, recorded = self.query_once(RETRYING, api="messages", bound=True, **kwargs)
                self.assertIsInstance(outcome, run.ContentFilterBlocked)
                self.assertEqual(len(seen), run.CONTENT_FILTER_SENDS)
                self.assertEqual(recorded.count("content_filter_block"), 3)
                self.assertEqual(run.failure_category(outcome), "CONTENT_FILTER")
                self.assertIn("CONTENT_FILTER", run.SEQUENCE_STOPPING_FAILURES)

    def test_direct_anthropic_content_filter_classification(self):
        outcome, seen, events = self.query_once(
            RETRYING, api="messages", provider="anthropic", refused=3, bound=True)
        self.assertEqual(run.failure_category(outcome), "CONTENT_FILTER")
        self.assertEqual(len(seen), run.CONTENT_FILTER_SENDS)
        self.assertEqual(events.count("content_filter_block"), 3)

    def test_content_filter_bound_resends_nothing_else(self):
        outcome, seen, _ = self.query_once(RETRYING, [(400, "prompt is too long")], api="messages", bound=True)
        self.assertEqual(run.failure_category(outcome), "PROTOCOL")
        self.assertEqual(len(seen), 1)
        # The bound covers Anthropic routes; other providers send once, unclassified as a block.
        outcome, seen, _ = self.query_once(RETRYING, failures=[(400, "Output blocked by content filtering policy")],
                                           api="responses", bound=True)
        self.assertNotEqual(run.failure_category(outcome), "CONTENT_FILTER")
        self.assertEqual(len(seen), 1)

    def test_transport_failures_are_retried_within_bound_on_every_protocol(self):
        for api in ("chat", "messages", "responses"):
            with self.subTest(api=api):
                outcome, seen, events = self.query_once(RETRYING, [(503, "overloaded"), (500, "reset")], api=api)
                self.assertIsInstance(outcome, dict)
                self.assertEqual(len(seen), 3)
                self.assertEqual(events, ["request", "request", "request", "response"])
                outcome, seen, _ = self.query_once(RETRYING, [(500, "down")] * 3, api=api)
                self.assertEqual(native.classify_error(outcome), "transport_error")
                self.assertEqual(len(seen), 1 + native.MAX_TRANSPORT_RETRIES)

    def test_client_errors_and_quota_are_never_retried(self):
        for status, message, category in ((400, "context too long", "provider_request_error"),
                                          (429, "Go usage limit exceeded", "quota_or_rate_limit"),
                                          (402, "Upstream request failed: Insufficient account funds", "quota_or_rate_limit"),
                                          (401, "denied", "authentication_error")):
            with self.subTest(status=status):
                outcome, seen, events = self.query_once(RETRYING, [(status, message)])
                self.assertEqual(native.classify_error(outcome), category)
                self.assertEqual((len(seen), events), (1, ["request"]))

    def test_zero_retries_sends_one_request(self):
        outcome, seen, _ = self.query_once(CONFIG, [(503, "overloaded")])
        self.assertEqual(native.classify_error(outcome), "transport_error")
        self.assertEqual(len(seen), 1)

    def test_format_error_says_when_the_output_cap_cut_the_reply(self):
        from minisweagent.exceptions import FormatError
        outcome, _, _ = self.query_once(CONFIG, truncated=True)
        self.assertIsInstance(outcome, FormatError)
        self.assertIn("cut off at the output token limit", outcome.messages[0]["content"])
        self.assertIn("No tool calls found", outcome.messages[0]["content"])


class NativePolicyTests(unittest.TestCase):
    def test_direct_provider_route_and_protocol_restrictions(self):
        routes = (("openai", "https://api.openai.com/v1", {"chat", "responses"}),
                  ("anthropic", "https://api.anthropic.com/v1", {"messages"}))
        for provider, base, allowed in routes:
            for api in ("chat", "responses", "messages"):
                with self.subTest(provider=provider, api=api):
                    spec = model_spec(api, provider, base)
                    if provider == "openai" and api == "chat":
                        spec.update(model="gpt-4o", response_model="gpt-4o")
                    if api in allowed:
                        effective = native.validate_model(CONFIG, spec)
                        sdk_base = base.removesuffix("/v1") if api == "messages" else base
                        self.assertEqual(effective["model_kwargs"]["api_base"], sdk_base)
                    else:
                        with self.assertRaisesRegex(ValueError, "native protocol"):
                            native.validate_model(CONFIG, spec)
            with self.assertRaises(ValueError):
                native.validate_url("https://different.example.com/v1", provider)

    def test_custom_public_url_policy(self):
        for url in ("https://api.example.com/v1", "https://api.example.com/service/v1",
                    "https://api.example.com:8443/v1", "https://8.8.8.8/v1"):
            with self.subTest(url=url):
                self.assertEqual(native.validate_url(url, "custom", "messages"), url)
        for url in (
                "http://api.example.com/v1", "https://localhost/v1", "https://127.0.0.1/v1",
                "https://10.0.0.1/v1", "https://172.16.0.1/v1", "https://192.168.1.1/v1",
                "https://169.254.169.254/v1", "https://100.64.0.1/v1", "https://0.0.0.0/v1",
                "https://[::1]/v1", "https://[fd00::1]/v1", "https://[::ffff:127.0.0.1]/v1",
                "https://224.0.0.1/v1", "https://2130706433/v1", "https://127.1/v1",
                "https://api.local/v1", "https://api.internal/v1", "https://api.localhost/v1",
                "https://api.test/v1", "https://api.invalid/v1", "https://intranet/v1",
                "https://user:password@api.example.com/v1", "https://@api.example.com/v1",
                "https://api.example.com/v1?key=value", "https://api.example.com/v1?",
                "https://api.example.com/v1#", "https://api.example.com/v1#fragment",
                "https://api.example.com/%73k-FAKEONLYFAKEONLY/v1",
                "https://api.example.com/sk-FAKEONLYFAKEONLY/v1",
                "https://api.example.com\\@localhost/v1", "https://api.example.com/\nv1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                native.validate_url(url, "custom", "messages")
        with self.assertRaisesRegex(ValueError, "end in /v1"):
            native.validate_url("https://api.example.com/service", "custom", "messages")

    def test_custom_dns_guard_rejects_every_nonpublic_answer(self):
        spec = model_spec("responses", "custom", "https://api.example.com/v1")
        def answers(*addresses):
            return [(0, 0, 0, "", (address, 443)) for address in addresses]
        with patch.object(native.socket, "getaddrinfo", return_value=answers("8.8.8.8", "1.1.1.1")):
            native.check_custom_destination(spec)
        for addresses in ((), ("127.0.0.1",), ("8.8.8.8", "10.0.0.1"), ("::ffff:192.168.0.1",)):
            with (self.subTest(addresses=addresses),
                  patch.object(native.socket, "getaddrinfo", return_value=answers(*addresses)),
                  self.assertRaisesRegex(ValueError, "nonpublic")):
                native.check_custom_destination(spec)
        with (patch.object(native.socket, "getaddrinfo", side_effect=OSError("synthetic DNS failure")),
              self.assertRaisesRegex(ValueError, "DNS resolution failed")):
            native.check_custom_destination(spec)
        self.assertFalse(native.public_address(ipaddress.ip_address("::ffff:10.0.0.1")))

    def test_custom_worker_blocks_private_dns_before_any_request(self):
        spec = model_spec("responses", "custom", "https://api.example.com/v1")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (worker_env(root, spec),
                  patch.object(native.socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("10.0.0.1", 443))]),
                  self.assertRaisesRegex(ValueError, "nonpublic")):
                native.build_probe_model(CONFIG, spec, root)
            self.assertFalse((root / "transport.jsonl").exists())

    def test_custom_key_probe_blocks_private_dns_before_sending(self):
        spec = model_spec("responses", "custom", "https://api.example.com/v1")
        with (patch.object(native.socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("127.0.0.1", 443))]),
              patch("urllib.request.urlopen") as request,
              self.assertRaisesRegex(ValueError, "nonpublic")):
            run.probe_provider(spec, "synthetic-only")
        request.assert_not_called()

    def test_production_rejects_unqualified_model(self):
        for status in (None, "pending", "qualification", "blocked"):
            spec = model_spec()
            spec["readiness"] = None if status is None else {"status": status}
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaisesRegex(ValueError, "verified native protocol readiness"):
                    native.build_model(CONFIG, spec, Path(temporary))

    def test_unknown_cost_is_not_free(self):
        spec = model_spec()
        rows = native.audit_messages([
            {"object": "response", "model": spec["model"], "extra": {"cost": 0}},
            {"object": "response", "model": spec["model"], "extra": {"cost": 0.125}},
        ], spec)
        self.assertEqual([(r["cost"], r["cost_status"]) for r in rows],
                         [(None, "unknown"), (0.125, "native_estimate")])

    def test_missing_identity_is_not_mismatch_and_error_takes_precedence(self):
        spec = model_spec()
        rows = native.audit_messages([
            {"extra": {"response": {"error": {}}}},
            {"extra": {"response": {"choices": []}}},
            {"extra": {"response": {"model": "other"}}},
        ], spec)
        self.assertEqual([row["identity_status"] for row in rows],
                         ["gateway_error", "identity_unverified", "identity_mismatch"])

    def test_new_auth_failure_is_not_masked_by_previous_gateway_envelope(self):
        error = native._litellm().AuthenticationError(message="denied", llm_provider="openai", model="x")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "transport.jsonl").write_text(
                json.dumps({"event": "response", "identity_status": "gateway_error"}) + "\n"
                + json.dumps({"event": "request"}) + "\n")
            self.assertEqual(native.classify_error(error, root), "authentication_error")

    def test_quota_bodies_are_quota_under_any_error_class(self):
        llm = native._litellm()
        errors = [
            llm.APIError(status_code=500, message="Upstream request failed: Insufficient account funds", llm_provider="openai", model="x"),
            llm.RateLimitError(message='{"type":"GoUsageLimitError","message":"Go usage limit exceeded"}', llm_provider="openai", model="x"),
            llm.APIError(status_code=402, message="A positive credit balance is required for all requests", llm_provider="openai", model="x"),
            llm.BadRequestError(message="Go usage limit exceeded", llm_provider="anthropic", model="x"),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # A quota body wins even over an earlier gateway envelope in the same exchange.
            (root / "transport.jsonl").write_text(json.dumps({"event": "response", "identity_status": "gateway_error"}) + "\n")
            for error in errors:
                with self.subTest(error=type(error).__name__):
                    self.assertEqual(native.classify_error(error, root), "quota_or_rate_limit")
        plain = llm.BadRequestError(message="prompt is too long", llm_provider="openai", model="x")
        self.assertEqual(native.classify_error(plain), "provider_request_error")

    def test_subminimum_response_limit_is_rejected_not_raised_silently(self):
        spec = model_spec()
        spec["generation"]["max_output_tokens"] = 1
        with self.assertRaises(ValueError):
            native.validate_model(CONFIG, spec)

    def test_thinking_budget_must_fit_output_limit(self):
        spec = model_spec("messages", "anthropic_oauth")
        spec["generation"]["thinking"] = {"type": "enabled", "budget_tokens": 4096}
        with self.assertRaises(ValueError):
            native.validate_model(CONFIG, spec)

    def test_unsupported_parameters_are_not_dropped(self):
        spec = model_spec()
        spec["generation"]["seed"] = 42
        with self.assertRaises(ValueError):
            native.validate_model(CONFIG, spec)

    def test_keys_and_unapproved_routes_are_rejected(self):
        for provider in ("zen", "kimi_pool", "gemini_bridge", "unknown"):
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                native.validate_model(CONFIG, model_spec(provider=provider))
        spec = model_spec()
        spec["api_key"] = "must-not-serialize"
        with self.assertRaises(ValueError):
            native.validate_model(CONFIG, spec)
        for url in ("http://localhost:8417/v1", "http://127.0.0.1:8417/v1?key=secret",
                    "http://secret@127.0.0.1:8417/v1", "https://opencode.ai/zen/v1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                native.validate_url(url, "codex_oauth")

    def test_devin_credential_route_rejects_nonloopback_and_wrong_protocols(self):
        spec = model_spec("chat", "devin")
        spec["model"] = spec["response_model"] = "devin/exact-model"
        for base in ("https://devin.ai/v1", "http://localhost:8417/v1", "http://100.92.22.120:8417/v1",
                     "http://127.0.0.1/v1", "http://127.0.0.1:8417", "http://127.0.0.1:8417/v1?key=secret",
                     "http://secret@127.0.0.1:8417/v1", "http://127.0.0.1:8417/v1#key"):
            with (self.subTest(base=base), patch.dict(os.environ, {"BENCHMARK_TEST_KEY": "synthetic-only"}),
                  self.assertRaises(ValueError)):
                native.credential_env(CONFIG, {**spec, "base_url": base})
        for api in ("messages", "responses"):
            with self.subTest(api=api), self.assertRaisesRegex(ValueError, "protocol"):
                native.validate_model(CONFIG, {**spec, "api": api})

    def test_redaction_covers_nested_exception_and_response_echoes(self):
        value = {"messages": [{"extra": {"traceback": "token=secret"}}], "secret": "secret"}
        self.assertEqual(native.redact_credentials(value, ["secret"]),
                         {"messages": [{"extra": {"traceback": "token=[REDACTED]"}}], "[REDACTED]": "[REDACTED]"})

    def test_declared_tier_admits_maximum_effort_absent_from_capability_map(self):
        spec = tiered(model_spec("chat", "go", "https://opencode.ai/zen/go/v1"), "max", reasoning_effort="max")
        spec["model"] = spec["response_model"] = "kimi-k3"
        effective = native.validate_model(CONFIG, spec)
        self.assertEqual(effective["declared_tier"], "max")
        self.assertEqual(effective["expected_transmitted_generation"]["reasoning_effort"], "max")

    def test_undeclared_or_mismatched_tier_is_rejected(self):
        undeclared = tiered(model_spec(), "xhigh", reasoning={"effort": "xhigh"})
        del undeclared["tier"]
        lower = tiered(model_spec(), "high", reasoning={"effort": "xhigh"})  # spec says high, sends xhigh
        silent = model_spec()
        silent["generation"]["reasoning"] = {"effort": "max"}  # tier still says none-available
        claimed = tiered(model_spec(), "max")  # claims max with no reasoning control
        for name, spec in (("undeclared", undeclared), ("mismatched", lower), ("silent", silent), ("claimed", claimed)):
            with self.subTest(name), self.assertRaisesRegex(ValueError, "tier"):
                native.validate_model(CONFIG, spec)

    def test_chat_route_that_sdk_would_reroute_to_responses_is_rejected(self):
        for provider, base in (("vercel", "https://ai-gateway.vercel.sh/v1"),
                               ("devin", "http://127.0.0.1:8417/v1")):
            spec = tiered(model_spec("chat", provider, base), "xhigh", reasoning_effort="xhigh")
            spec["model"] = spec["response_model"] = "openai/gpt-5.4"
            spec["generation"]["max_completion_tokens"] = spec["generation"].pop("max_tokens")
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                native.validate_model(CONFIG, spec)

    def test_anthropic_effort_rejected_where_native_sdk_would_refuse_it(self):
        spec = tiered(model_spec("messages", "anthropic_oauth"), "max", output_config={"effort": "max"})
        spec["model"] = spec["response_model"] = "claude-opus-4-5-20251101"
        with self.assertRaisesRegex(ValueError, "output_config"):
            native.validate_model(CONFIG, spec)


if __name__ == "__main__":
    unittest.main()
