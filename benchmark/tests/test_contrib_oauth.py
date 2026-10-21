"""OAuth orchestration against a synthetic local executable, never a provider."""
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

SPEC = importlib.util.spec_from_file_location("oauth_cli", Path(__file__).resolve().parents[1] / "contrib/cli.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "credentials"
        self.binary = self.root / "synthetic-bridge"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o700)

    def args(self, provider="codex", **overrides):
        values = dict(command="login", provider=provider, method=None, auth_dir=self.directory,
                      no_input=False, accept_community_auth=True, bridge_binary=self.binary,
                      bridge_port=None, no_browser=True)
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_allowlisted_commands_device_flow_and_no_shell(self):
        for name, flag in {"codex": "-codex-device-login", "anthropic": "-claude-login", "xai": "-xai-login"}.items():
            result = cli.oauth_bridge.command(self.binary, self.root / "config with spaces", name, no_browser=True)
            self.assertEqual(result, [str(self.binary), "--config", str(self.root / "config with spaces"), flag, "-no-browser"])
        with self.assertRaises(ValueError):
            cli.oauth_bridge.provider("gemini")

    def test_new_profile_never_discovers_binary_from_path(self):
        with mock.patch.dict(os.environ, {"PATH": str(self.root)}):
            with self.assertRaisesRegex(ValueError, "explicitly"):
                cli.oauth_bridge.resolve_binary(None)
        self.assertEqual(cli.oauth_bridge.resolve_binary(self.binary), self.binary)

    def test_missing_profile_cannot_report_server_started(self):
        with mock.patch.object(cli.oauth_bridge, "invoke") as invoke:
            with self.assertRaisesRegex(ValueError, "No bridge was started"):
                cli.provider_auth(self.args(command="bridge-serve"))
            invoke.assert_not_called()
        with redirect_stdout(io.StringIO()):
            cli.provider_auth(self.args(command="auth-status"))
        self.assertFalse(self.directory.exists())

    def test_oauth_rejection_never_invokes_bridge_or_network(self):
        with mock.patch.object(cli, "interactive", return_value=False), mock.patch.object(cli.oauth_bridge, "invoke") as invoke, mock.patch.object(cli, "urlopen") as network:
            for name in cli.auth.NAMES:
                with self.assertRaisesRegex(ValueError, "OAuth requires an interactive|No reviewed OAuth login"):
                    cli.provider_auth(self.args(name, method="oauth", no_input=True))
            invoke.assert_not_called()
            network.assert_not_called()
        self.assertFalse(self.directory.exists())

    def test_generated_config_is_private_isolated_and_no_cloak(self):
        path = cli.oauth_bridge.create_config(self.directory, "xai", self.binary, 8319, cli.private_directory)
        loaded_path, binary, config = cli.oauth_bridge.load_config(self.directory, "xai", cli.outside_path, cli.check_owner)
        self.assertEqual(loaded_path, path)
        self.assertEqual(binary, self.binary)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(config["server"]["host"], "127.0.0.1")
        self.assertFalse(config["upstream"]["xai"]["inject-x-search"])
        self.assertEqual(Path(config["oauth"]["auth-dir"]), path.parent / "provider-tokens")
        self.assertGreaterEqual(len(config["access"]["api-keys"][0]), 32)
        config["upstream"]["claude"]["disable-claude-cloak-mode"] = False
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            cli.oauth_bridge.load_config(self.directory, "xai", cli.outside_path, cli.check_owner)

    def test_zero_exit_without_credentials_is_not_login_success(self):
        with mock.patch.object(cli, "interactive", return_value=True), mock.patch.object(cli.subprocess, "run", return_value=argparse.Namespace(stdout="-codex-device-login", stderr="")), mock.patch.object(cli.oauth_bridge, "invoke", return_value=0), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "unverified"):
                cli.provider_auth(self.args())

    def test_login_observes_only_persistence_never_reads_provider_token(self):
        def fake_invoke(command):
            config = json.loads(Path(command[2]).read_text())
            path = Path(config["oauth"]["auth-dir"]) / "fixture.json"
            path.write_text("SYNTHETIC_PROVIDER_TOKEN_DO_NOT_PRINT")
            path.chmod(0o600)
            return 0
        out = io.StringIO()
        with mock.patch.object(cli, "interactive", return_value=True), mock.patch.object(cli.subprocess, "run", return_value=argparse.Namespace(stdout="-xai-login", stderr="")), mock.patch.object(cli.oauth_bridge, "invoke", side_effect=fake_invoke), redirect_stdout(out):
            cli.provider_auth(self.args("xai"))
        self.assertIn("remote validity is unverified", out.getvalue())
        self.assertNotIn("SYNTHETIC_PROVIDER_TOKEN", out.getvalue())

    def test_no_input_and_cancel_do_not_launch_login_or_save(self):
        with mock.patch.object(cli, "interactive", return_value=False), mock.patch.object(cli.oauth_bridge, "invoke") as invoke:
            with self.assertRaisesRegex(ValueError, "interactive"):
                cli.provider_auth(self.args(no_input=True))
            invoke.assert_not_called()
        self.assertFalse(self.directory.exists())
        with mock.patch.object(cli, "interactive", return_value=True), mock.patch("builtins.input", return_value="n"), mock.patch.object(cli.oauth_bridge, "invoke") as invoke, redirect_stdout(io.StringIO()):
            cli.provider_auth(self.args(accept_community_auth=False))
            invoke.assert_not_called()
        self.assertFalse(self.directory.exists())

    def test_local_bearer_only_matches_its_bridge_and_endpoint(self):
        cli.oauth_bridge.create_config(self.directory, "xai", self.binary, 8319, cli.private_directory)
        settings = argparse.Namespace(provider="xai_oauth", base_url="http://127.0.0.1:8319/v1", bridge_binary=self.binary)
        bearer = cli.saved_credential(settings, self.directory)
        self.assertGreaterEqual(len(bearer), 32)
        settings.base_url = "http://127.0.0.1:9999/v1"
        self.assertIsNone(cli.saved_credential(settings, self.directory))

    def test_catalog_http_errors_report_status_without_response_or_credentials(self):
        from urllib.error import HTTPError
        settings = argparse.Namespace(provider="xai_oauth", api="responses", base_url="http://127.0.0.1:8319/v1", model="fixture")
        for code in (401, 404, 500):
            error = HTTPError(settings.base_url + "/models", code, "SYNTHETIC_SECRET", {}, io.BytesIO(b"PRIVATE_RESPONSE"))
            with mock.patch.dict(os.environ, {"KEYGEN_CONTRIB_API_KEY": "SYNTHETIC_BEARER"}), mock.patch.object(cli, "urlopen", side_effect=error):
                with self.assertRaisesRegex(ValueError, f"HTTP {code}; no inference") as caught:
                    cli.verify_model_catalog(settings)
                self.assertNotIn("SYNTHETIC", str(caught.exception))
                self.assertNotIn("PRIVATE", str(caught.exception))

    def test_custom_key_is_bound_to_exact_endpoint(self):
        cli.private_directory(self.directory)
        cli.auth.save_key(self.directory, "custom", "SYNTHETIC_CUSTOM_KEY", endpoint="https://models.example/v1")
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = argparse.Namespace(provider="custom", base_url="https://models.example/v1")
            self.assertEqual(cli.saved_credential(settings, self.directory), "SYNTHETIC_CUSTOM_KEY")
            settings.base_url = "https://other.example/v1"
            self.assertIsNone(cli.saved_credential(settings, self.directory))


if __name__ == "__main__":
    unittest.main()
