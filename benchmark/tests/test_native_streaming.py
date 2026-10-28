"""Real HTTP/SSE conformance tests for the pinned native Responses transport."""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from benchmark import campaign, native_models as native, run

CONFIG = {"native": {"timeout_seconds": 3, "retries": 2}}
MESSAGES = [{"role": "user", "content": "Use both tools"}]


def response(payload, status="completed"):
    return {"id": "resp-fixture", "created_at": 1, "object": "response", "model": payload["model"],
            "status": status, "error": None, "incomplete_details": None,
            "output": [{"id": "rs-1", "type": "reasoning", "summary": [],
                        "encrypted_content": "opaque-original-state",
                        "content": [{"type": "reasoning_text", "text": "Synthetic original reasoning"}]},
                       *[{"id": f"fc-{n}", "type": "function_call", "call_id": f"call-{n}",
                          "name": "bash", "arguments": json.dumps({"command": f"printf '{n}\\n' >> executed"}),
                          "status": "completed", "provider_extension": {"null": None, "false": False}} for n in (1, 2)]],
            "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18,
                      "input_tokens_details": {"cached_tokens": 5, "cache_write_tokens": 3},
                      "output_tokens_details": {"reasoning_tokens": 4}},
            "provider_metadata": {"gateway": {"cost": "0.0123"}}, "tools": payload["tools"]}


def event(kind, **fields):
    return ("data: " + json.dumps({"type": kind, "sequence_number": 0, **fields}) + "\n\n").encode()


@contextmanager
def endpoint(modes):
    """A real SSE endpoint, including real broken chunked framing and cancellation."""
    seen, closed = [], threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(payload)
            mode = modes[min(len(seen) - 1, len(modes) - 1)]
            if mode == "disconnect":
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            raw = response(payload)
            prefix = event("response.created", response={**raw, "status": "in_progress", "output": []})
            prefix += event("response.function_call_arguments.delta", item_id="fc-1", output_index=1,
                            delta='{"command":"do not execute partial')
            terminal = "response.completed"
            if mode == "explicitnull":
                raw["output"][0]["encrypted_content"] = None
                raw["output"][1].update(namespace=None, caller=None)
                raw["metadata"] = None
                raw["unknown_provider_field"] = {"empty": [], "zero": 0, "false": False, "text": "", "nested": [None, False, 0, "", {"null": None}]}
            if mode == "aliased":
                raw["text"] = {"format": {"type": "json_schema", "name": "payload", "schema": {"type": "object", "properties": {"x": {"type": "string"}}}, "strict": False, "description": None}}
            if mode in {"http503", "http502", "httpquota500"}:
                body = json.dumps({"error": {"message": "insufficient account funds" if mode == "httpquota500" else "temporary unavailable",
                                             "type": "server_error"}}).encode()
                self.send_response({"http503": 503, "http502": 502, "httpquota500": 500}[mode])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if mode in {"failed429", "failed500", "failedquota500", "failed400"}:
                raw.update(status="failed", output=[], error={"code": "rate_limit_exceeded" if mode == "failed429" else "invalid_prompt" if mode == "failed400" else "server_error",
                                                             "message": "usage limit exceeded" if mode in {"failed429", "failedquota500"} else "server failed"})
                terminal = "response.failed"
            elif mode == "incomplete":
                raw.update(status="incomplete", output=[], incomplete_details={"reason": "max_output_tokens"})
                terminal = "response.incomplete"
            elif mode == "cancelled":
                raw.update(status="cancelled", output=[])
                terminal = "response.incomplete"
            elif mode == "mismatch":
                raw["model"] = "different-model"
            body = prefix + event(terminal, response=raw) + b"data: [DONE]\n\n"
            if mode == "eof":
                body = prefix
            elif mode == "empty":
                body = b""
            elif mode == "error429":
                body = prefix + event("error", code="rate_limit_exceeded", message="usage limit exceeded", param=None)
            elif mode == "errorquota":
                body = prefix + event("error", code="insufficient_quota", message="Quota exhausted", param=None)
            elif mode == "nested429":
                body = prefix + event("error", error={"code": "rate_limit_exceeded", "message": "usage limit exceeded"})
            elif mode == "json":
                body = json.dumps(raw).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json" if mode == "json" else "text/event-stream")
            if mode in {"broken", "wait", "tail", "timeout"}:
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            if mode == "broken":
                self.wfile.write(f"{len(prefix):x}\r\n".encode() + prefix + b"\r\n")
                self.wfile.flush()
                self.close_connection = True  # No final zero chunk: real RemoteProtocolError.
            elif mode in {"wait", "tail", "timeout"}:
                initial = body if mode == "tail" else prefix
                try:
                    self.wfile.write(f"{len(initial):x}\r\n".encode() + initial + b"\r\n")
                    self.wfile.flush()
                    if mode == "wait":
                        # Arm the real cancellation only after the request entered SSE.
                        signal.setitimer(signal.ITIMER_REAL, .1)
                    if mode == "timeout":
                        time.sleep(4)
                    for _ in range(50):
                        time.sleep(.05)
                        heartbeat = b": heartbeat\n\n"
                        self.wfile.write(f"{len(heartbeat):x}\r\n".encode() + heartbeat + b"\r\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    closed.set()
                self.close_connection = True
            else:
                self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", seen, closed
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@contextmanager
def worker(root, base):
    """Use the production credential boundary and a genuinely isolated environment."""
    saved = dict(os.environ)
    home = root / "home"
    mini = home / "mini"
    mini.mkdir(parents=True)
    spec = {"id": "stream-test", "model": "gpt-5.5", "response_model": "gpt-5.5",
            "provider": "codex_oauth", "api": "responses", "base_url": base,
            "api_key_env": "SYNTHETIC_KEY", "generation": {"max_output_tokens": 4096},
            "tier": {"level": "none-available", "reasoning": {}, "spec_sha256": "0" * 64}}
    try:
        os.environ.clear()
        os.environ["SYNTHETIC_KEY"] = "fixture-credential"
        os.environ.update(native.credential_env(CONFIG, spec))
        os.environ.update(HOME=str(home), MSWEA_GLOBAL_CONFIG_DIR=str(mini), MSWEA_SILENT_STARTUP="1")
        model = native.build_probe_model(CONFIG, spec, root)
        yield model, spec
    finally:
        os.environ.clear()
        os.environ.update(saved)


class NativeStreamingTests(unittest.TestCase):
    def records(self, root):
        return [json.loads(line) for line in (root / "transport.jsonl").read_text().splitlines()]

    def test_all_responses_routes_share_fixed_native_transport(self):
        bases = {"go": "https://opencode.ai/zen/go/v1", "vercel": "https://ai-gateway.vercel.sh/v1",
                 "openai": "https://api.openai.com/v1", "custom": "https://api.example.com/v1",
                 "codex_oauth": "http://127.0.0.1:9999/v1", "xai_oauth": "http://127.0.0.1:9999/v1"}
        self.assertEqual(set(bases), {provider for provider, apis in native.PROTOCOLS.items() if "responses" in apis})
        for provider, base in bases.items():
            with self.subTest(provider=provider):
                spec = {"id": "routes-test", "model": "gpt-5.5", "response_model": "gpt-5.5",
                        "provider": provider, "api": "responses", "base_url": base, "api_key_env": "SYNTHETIC_KEY",
                        "generation": {"max_output_tokens": 4096},
                        "tier": {"level": "none-available", "reasoning": {}, "spec_sha256": "0" * 64}}
                effective = native.validate_model(CONFIG, spec)
                self.assertEqual(effective["model_class"], "StreamingOpenAIResponseModel")
                for key, value in native.responses_options(spec).items():
                    self.assertEqual(effective["model_kwargs"][key], value)
                self.assertEqual(effective["model_kwargs"]["max_retries"], 0)
                self.assertEqual(effective["model_kwargs"]["api_base"], base)

    def test_native_sdk_base_classes_do_not_broaden_legacy_retry_classes(self):
        import litellm
        class FailingLegacyModel:
            calls = 0
            def _query(self, messages):
                self.calls += 1
                raise litellm.APIConnectionError(message="unmapped legacy error", model="fixture", llm_provider="openai")
        model, waits = FailingLegacyModel(), []
        run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
        with self.assertRaises(litellm.APIConnectionError):
            model._query(MESSAGES)
        self.assertEqual((model.calls, waits), (1, []))

    def test_transient_then_semantic_quota_stops_before_another_send(self):
        with tempfile.TemporaryDirectory() as temporary, endpoint(["http503", "httpquota500", "complete"]) as (base, seen, _):
            root = Path(temporary)
            with worker(root, base) as (model, spec):
                waits = []
                run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
                with self.assertRaises(Exception) as caught:
                    model.query(MESSAGES)
                self.assertEqual(native.classify_error(caught.exception), "quota_or_rate_limit")
                self.assertEqual((len(seen), waits), (2, [15]))

    def test_opening_502_and_funds_500_are_not_retried(self):
        for mode in ("http502", "httpquota500"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary, endpoint([mode]) as (base, seen, _):
                root = Path(temporary)
                with worker(root, base) as (model, spec):
                    waits = []
                    run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
                    with self.assertRaises(Exception) as caught:
                        model.query(MESSAGES)
                    self.assertEqual((len(seen), waits), (1, []))
                    if mode == "httpquota500":
                        self.assertEqual(native.classify_error(caught.exception, root), "quota_or_rate_limit")

    def test_received_fields_and_values_round_trip_without_sdk_defaults(self):
        for mode in ("complete", "explicitnull", "aliased"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary, endpoint([mode]) as (base, seen, _):
                root = Path(temporary)
                with worker(root, base) as (model, spec):
                    message = model.query(MESSAGES)
                    expected = response(seen[0])
                    if mode == "explicitnull":
                        expected["output"][0]["encrypted_content"] = None
                        expected["output"][1].update(namespace=None, caller=None)
                        expected["metadata"] = None
                        expected["unknown_provider_field"] = {"empty": [], "zero": 0, "false": False, "text": "", "nested": [None, False, 0, "", {"null": None}]}
                    if mode == "aliased":
                        expected["text"] = {"format": {"type": "json_schema", "name": "payload", "schema": {"type": "object", "properties": {"x": {"type": "string"}}}, "strict": False, "description": None}}
                    self.assertEqual({key: value for key, value in message.items() if key != "extra"}, expected)
                    model.query([*MESSAGES, message])
                    self.assertEqual(seen[1]["input"][1:], expected["output"])
                    if mode == "complete":
                        self.assertNotIn("namespace", message["output"][1])
                        self.assertNotIn("caller", message["output"][1])
                        self.assertNotIn("status", message["output"][0])
                    elif mode == "explicitnull":
                        self.assertIsNone(message["output"][1]["namespace"])
                        self.assertIsNone(message["output"][0]["encrypted_content"])
                    receipts = [row for row in self.records(root) if row["event"] == "response"]
                    self.assertEqual(receipts[0]["provider_receipt"]["usage"], expected["usage"])
                    self.assertEqual(receipts[0]["provider_receipt"]["provider_metadata"], expected["provider_metadata"])

    def test_terminal_tools_history_usage_and_cost_have_one_owner(self):
        with tempfile.TemporaryDirectory() as temporary, endpoint(["complete"]) as (base, seen, _):
            root = Path(temporary)
            with worker(root, base) as (model, spec):
                first = model.query(MESSAGES)
                actions = first["extra"]["actions"]
                self.assertEqual(len(actions), 2)
                outputs = []
                for action in actions:
                    command = subprocess.run(["/bin/sh", "-c", action["command"]], cwd=root,
                                             text=True, capture_output=True, check=True)
                    outputs.append({"output": command.stdout, "returncode": command.returncode})
                observations = model.format_observation_messages(first, outputs, {"wall_time_limit_seconds": 0})
                model.query([*MESSAGES, first, *observations])
                self.assertEqual((root / "executed").read_text(), "1\n2\n")
                self.assertEqual(first["output"][0]["encrypted_content"], "opaque-original-state")
                self.assertEqual(first["provider_metadata"]["gateway"]["cost"], "0.0123")
                self.assertEqual([item["call_id"] for item in seen[1]["input"] if item.get("type") == "function_call_output"],
                                 ["call-1", "call-2"])
                self.assertIn(first["output"][0], seen[1]["input"])
                self.assertTrue(all(payload["stream"] is True for payload in seen))
                receipts = [row for row in self.records(root) if row["event"] == "response"]
                self.assertEqual(len(receipts), 2)
                self.assertEqual([row["provider_receipt"]["provider_metadata"]["gateway"]["cost"] for row in receipts],
                                 ["0.0123", "0.0123"])
                self.assertEqual(receipts[0]["provider_receipt"]["usage"]["input_tokens_details"]["cache_write_tokens"], 3)
                self.assertAlmostEqual(first["extra"]["cost"], .0002425)
                self.assertEqual(sum(row["usage"]["total_tokens"] for row in receipts), 36)
                totals = run.summarize(root, spec)
                self.assertEqual((totals["requests"], totals["cached_tokens"], totals["reasoning_tokens"], totals["usage_unknown"]),
                                 (2, 10, 8, 0))

    def test_interrupted_streams_retry_identical_request_without_partial_tools(self):
        for mode in ("empty", "eof", "broken", "disconnect", "http503", "timeout"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary, endpoint([mode, "complete"]) as (base, seen, _):
                root = Path(temporary)
                with worker(root, base) as (model, spec):
                    waits = []
                    run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
                    message = model.query(MESSAGES)
                    self.assertEqual(waits, [15])
                    self.assertEqual(seen[0], seen[1])
                    self.assertEqual(len(message["extra"]["actions"]), 2)
                    self.assertFalse((root / "executed").exists())
                    totals = run.summarize(root, spec)
                    self.assertEqual((totals["requests"], totals["transport_retries"], totals["usage_unknown"]), (2, 1, 1))
                    exchanges = campaign.unblocked_exchanges(self.records(root))
                    self.assertEqual([row["event"] for row in exchanges], ["request", "response"])

    def test_missing_terminal_exhausts_only_bounded_transport_budget(self):
        import httpx
        with tempfile.TemporaryDirectory() as temporary, endpoint(["eof"]) as (base, seen, _):
            root = Path(temporary)
            with worker(root, base) as (model, spec):
                waits = []
                run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
                with self.assertRaises(httpx.RemoteProtocolError):
                    model.query(MESSAGES)
                self.assertEqual(waits, [15, 30])
                self.assertEqual(len(seen), 3)
                self.assertEqual(run.summarize(root, spec)["usage_unknown"], 3)

    def test_quota_and_terminal_failures_do_not_retry(self):
        for mode, category in (("failed429", "quota_or_rate_limit"), ("error429", "quota_or_rate_limit"),
                               ("nested429", "quota_or_rate_limit"), ("errorquota", "quota_or_rate_limit"),
                               ("failed500", "gateway_error"), ("failedquota500", "quota_or_rate_limit"),
                               ("failed400", "gateway_error"), ("cancelled", "gateway_error")):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary, endpoint([mode]) as (base, seen, _):
                root = Path(temporary)
                with worker(root, base) as (model, spec):
                    waits = []
                    run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
                    with self.assertRaises(Exception) as caught:
                        model.query(MESSAGES)
                    self.assertEqual(native.classify_error(caught.exception, root), category)
                    self.assertEqual((len(seen), waits), (1, []))
                    self.assertEqual(run.summarize(root, spec)["failed_requests"], 1)
                    if mode not in {"error429", "nested429", "errorquota"}:
                        receipts = [row for row in self.records(root) if row["event"] == "response"]
                        self.assertEqual(len(receipts), 1)
                        self.assertEqual(receipts[0]["provider_receipt"]["provider_metadata"]["gateway"]["cost"], "0.0123")
                    self.assertFalse((root / "executed").exists())

    def test_output_limit_keeps_native_format_error_and_terminal_usage(self):
        from minisweagent.exceptions import FormatError
        with tempfile.TemporaryDirectory() as temporary, endpoint(["incomplete"]) as (base, seen, _):
            root = Path(temporary)
            with worker(root, base) as (model, spec):
                with self.assertRaises(FormatError) as caught:
                    model.query(MESSAGES)
                self.assertIn("cut off at the output token limit", str(caught.exception.messages))
                self.assertEqual(len(seen), 1)
                self.assertEqual(run.summarize(root, spec)["usage_unknown"], 0)

    def test_no_nonstream_fallback_or_identity_substitution(self):
        for mode in ("json", "mismatch"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary, endpoint([mode]) as (base, seen, _):
                root = Path(temporary)
                with worker(root, base) as (model, spec):
                    if mode == "json":
                        with self.assertRaisesRegex(ValueError, "text/event-stream"):
                            model.query(MESSAGES)
                    else:
                        message = model.query(MESSAGES)
                        self.assertEqual(message["model"], "different-model")
                        self.assertTrue(run.summarize(root, spec)["identity_mismatch"])
                    self.assertEqual(len(seen), 1)

    def test_terminal_closes_without_waiting_for_trailing_connection(self):
        with tempfile.TemporaryDirectory() as temporary, endpoint(["tail"]) as (base, seen, closed):
            root = Path(temporary)
            with worker(root, base) as (model, spec):
                model.query(MESSAGES)
                self.assertTrue(closed.wait(2), "terminal consumer must close the HTTP stream")
                self.assertEqual(len(seen), 1)
                self.assertEqual(len([row for row in self.records(root) if row["event"] == "response"]), 1)

    def test_client_cancellation_closes_stream_and_never_retries(self):
        # SIGINT may interrupt the SDK's lazy type initialization. A real worker
        # exits after cancellation, so test this in an equally isolated process.
        child = subprocess.run([sys.executable, "-c",
                                "from benchmark.tests.test_native_streaming import cancellation_check; cancellation_check()"],
                               cwd=Path(__file__).resolve().parents[2], text=True,
                               capture_output=True, timeout=15)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)


def cancellation_check():
    with tempfile.TemporaryDirectory() as temporary, endpoint(["wait"]) as (base, seen, closed):
        root = Path(temporary)
        with worker(root, base) as (model, spec):
            waits = []
            run.backoff_transport_errors(model, CONFIG, sleep=waits.append)
            previous = signal.getsignal(signal.SIGALRM)
            def cancel(signum, frame):
                raise KeyboardInterrupt
            signal.signal(signal.SIGALRM, cancel)
            signal.setitimer(signal.ITIMER_REAL, 5)
            try:
                with unittest.TestCase().assertRaises(KeyboardInterrupt):
                    model.query(MESSAGES)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous)
            assert closed.wait(2)
            assert (len(seen), waits) == (1, [])
            assert json.loads((root / "transport.jsonl").read_text().splitlines()[-1])["reason"] == "cancelled"


if __name__ == "__main__":
    unittest.main()
