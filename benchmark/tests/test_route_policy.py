"""Offline contract checks for the route-policy registry."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_models
import run


class Native:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def _query(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        item = next(self.results)
        if isinstance(item, Exception):
            raise item
        return item


class RoutePolicyTests(unittest.TestCase):
    def test_adapter_registry_preserves_approved_routes(self):
        self.assertEqual(native_models.BRIDGE_PROVIDERS,
                         {"devin", "anthropic_oauth", "codex_oauth", "xai_oauth"})
        self.assertEqual(native_models.PROTOCOLS, {
            "go": {"chat", "responses", "messages"}, "vercel": {"chat", "responses"},
            "nim": {"chat"}, "google": {"chat"}, "mistral": {"chat"}, "cohere": {"chat"},
            "devin": {"chat"}, "anthropic_oauth": {"messages"}, "codex_oauth": {"responses"},
            "xai_oauth": {"responses"}, "openai": {"chat", "responses"},
            "anthropic": {"messages"}, "custom": {"chat", "responses", "messages"},
        })
        fixed = {
            "go": "https://opencode.ai/zen/go/v1", "vercel": "https://ai-gateway.vercel.sh/v1",
            "nim": "https://integrate.api.nvidia.com/v1", "google": "https://generativelanguage.googleapis.com/v1beta",
            "mistral": "https://api.mistral.ai/v1", "cohere": "https://api.cohere.ai/compatibility/v1",
            "openai": "https://api.openai.com/v1", "anthropic": "https://api.anthropic.com/v1",
        }
        for provider, url in fixed.items():
            with self.subTest(provider=provider):
                self.assertEqual(native_models.validate_url(url, provider), url)
                with self.assertRaises(ValueError):
                    native_models.validate_url("https://attacker.example/v1", provider)
        self.assertEqual(native_models.SDK_PREFIX, {"google": "gemini", "mistral": "mistral"})
        self.assertTrue(native_models.ROUTE_ADAPTERS["google"].omit_api_base)
        self.assertTrue(native_models.ROUTE_ADAPTERS["cohere"].strict_tools)
        self.assertEqual(native_models.ROUTE_ADAPTERS["go"].user_agent,
                         "keygen-benchmark/mini-swe-agent-2.4.6")
        self.assertEqual(native_models.responses_options({"provider": "codex_oauth"}),
                         {"store": False, "stream": True, "include": ["reasoning.encrypted_content"]})
        self.assertEqual(native_models.responses_options({"provider": "openai"}),
                         {"store": False, "stream": True})
        self.assertEqual(native_models.route_probe_headers("go", lambda: SimpleNamespace(hex="abc")),
                         {"x-opencode-session": "abc"})
        self.assertEqual(native_models.route_probe_headers("custom", lambda: self.fail("unexpected session")), {})

    def test_registry_preserves_all_known_route_defaults(self):
        expected = {"go": {"upstream_outage"}, "anthropic": {"content_filter"},
                    "anthropic_oauth": {"content_filter"}}
        for provider in native_models.PROVIDERS:
            self.assertEqual(native_models.route_policy(provider), expected.get(provider, set()))
        with self.assertRaisesRegex(ValueError, "Unsupported model provider"):
            native_models.route_policy("unregistered")

    def test_outage_retries_only_go_and_preserves_request_and_audit(self):
        failure = RuntimeError("Upstream request failed: Endpoint is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = Native([failure, "ok"])
            slept = []
            run.wait_out_upstream_outage(native, {"provider": "go"}, root, sleep=slept.append)
            self.assertEqual(native._query(["same"], token=1), "ok")
            self.assertEqual(native.calls, [(["same"], {"token": 1})] * 2)
            self.assertEqual(slept, [15])
            self.assertIn('"event": "upstream_unavailable"', (root / "transport.jsonl").read_text())
            other = Native([failure])
            run.wait_out_upstream_outage(other, {"provider": "custom"}, root, sleep=slept.append)
            with self.assertRaisesRegex(RuntimeError, "Endpoint is unavailable"):
                other._query(["same"])
            self.assertEqual(len(other.calls), 1)

    def test_content_filter_retries_only_declared_routes(self):
        blocked = SimpleNamespace(choices=[SimpleNamespace(finish_reason="content_filter",
                                    message=SimpleNamespace(tool_calls=None, content=None))])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            native = Native([blocked, blocked, blocked])
            run.bound_content_filter(native, {"provider": "anthropic"}, root)
            with self.assertRaises(run.ContentFilterBlocked):
                native._query(["same"])
            self.assertEqual(len(native.calls), 3)
            self.assertEqual((root / "transport.jsonl").read_text().count('"content_filter_block"'), 3)
            other = Native([blocked])
            run.bound_content_filter(other, {"provider": "custom"}, root)
            self.assertIs(other._query(["same"]), blocked)
            self.assertEqual(len(other.calls), 1)


if __name__ == "__main__":
    unittest.main()
