"""CLI privacy and authorization regressions. No paid inference or Docker builds."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

CONTRIB = Path(__file__).resolve().parents[1] / "contrib"
SPEC = importlib.util.spec_from_file_location("contrib_cli", CONTRIB / "cli.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class ContributionCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="keygen-cli-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = self.root / "private/contrib.json"
        self.environment = dict(os.environ)
        for key in list(self.environment):
            if "KEY" in key or "TOKEN" in key or "SECRET" in key:
                self.environment.pop(key)
        self.environment["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
        self.environment["LITELLM_MODE"] = "PRODUCTION"
        self.environment["KEYGEN_CONTRIB_API_KEY"] = "FAKE_CLI_CREDENTIAL_DO_NOT_ECHO"

    def command(self, *arguments, environment=None):
        return subprocess.run([sys.executable, str(CONTRIB / "cli.py"), *map(str, arguments)],
                              env=environment or self.environment, input="", text=True,
                              capture_output=True, timeout=60)

    def configure_arguments(self, **overrides):
        values = {"config": self.config, "provider": "openai", "model": "gpt-5.2",
                  "api": "responses", "reasoning-tier": "high",
                  "tier-source": "https://platform.openai.com/docs/guides/reasoning",
                  "generation": '{"max_output_tokens":64,"reasoning":{"effort":"high"}}',
                  "handle": "synthetic-fixture"}
        values.update(overrides)
        arguments = ["configure", "--no-input"]
        for key, value in values.items():
            arguments.extend(["--" + key, str(value)])
        return arguments

    def create_config(self):
        result = self.command(*self.configure_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.config.read_text())

    def test_noninteractive_configuration_preserves_exact_settings_without_secret(self):
        value = self.create_config()
        self.assertEqual(value["model"], "gpt-5.2")
        self.assertEqual(value["api"], "responses")
        self.assertEqual(value["generation"], {"max_output_tokens": 64, "reasoning": {"effort": "high"}})
        self.assertEqual(value["reasoning_tier"], "high")
        self.assertEqual(value["base_url"], "https://api.openai.com/v1")
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.config.parent.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(self.environment["KEYGEN_CONTRIB_API_KEY"], self.config.read_text())
        self.assertNotIn("api_key", value)

    def test_no_input_never_invents_missing_model_or_output_settings(self):
        result = self.command("configure", "--no-input", "--provider", "openai", "--config", self.config)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing --model", result.stderr)
        self.assertFalse(self.config.exists())
        result = self.command(*self.configure_arguments(generation='{"reasoning":{"effort":"high"}}'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("documented output limit", result.stderr)
        self.assertFalse(self.config.exists())

    def test_credential_flags_and_accidental_secret_settings_are_not_echoed_or_saved(self):
        secret = self.environment["KEYGEN_CONTRIB_API_KEY"]
        result = self.command("configure", "--api-key", secret)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertIn("environment or a hidden prompt", result.stderr)
        result = self.command(*self.configure_arguments(model=secret))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertFalse(self.config.exists())

    def test_configuration_never_clobbers_without_explicit_replace(self):
        self.create_config()
        original = self.config.read_bytes()
        result = self.command(*self.configure_arguments(model="gpt-5"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--replace", result.stderr)
        self.assertEqual(self.config.read_bytes(), original)
        result = self.command(*self.configure_arguments(model="gpt-5"), "--replace")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.config.read_text())["model"], "gpt-5")

    def test_run_and_smoke_require_explicit_spending_consent_before_creating_work(self):
        self.create_config()
        for command in ("run", "smoke"):
            with self.subTest(command=command):
                work = self.root / (command + "-work")
                arguments = [command, "--config", self.config, "--work", work, "--no-input"]
                if command == "run":
                    arguments.extend(["--out", self.root / "bundle"])
                result = self.command(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Spending is not authorized", result.stderr)
                self.assertFalse(work.exists())
                self.assertFalse((self.root / "bundle").exists())
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn(self.environment["KEYGEN_CONTRIB_API_KEY"], result.stderr)

    def test_no_input_consent_without_credential_still_makes_no_attempt(self):
        self.create_config()
        environment = dict(self.environment)
        environment.pop("KEYGEN_CONTRIB_API_KEY")
        work = self.root / "credential-missing"
        result = self.command("smoke", "--config", self.config, "--work", work, "--yes", "--no-input", environment=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Set KEYGEN_CONTRIB_API_KEY", result.stderr)
        self.assertFalse(work.exists())

    def test_unsafe_private_paths_and_insecure_saved_config_are_rejected(self):
        self.create_config()
        os.chmod(self.config, 0o644)
        result = self.command("smoke", "--config", self.config, "--work", self.root / "unsafe", "--yes", "--no-input")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("modes 0600 and 0700", result.stderr)
        self.assertFalse((self.root / "unsafe").exists())
        os.chmod(self.config, 0o600)
        link = self.root / "link"
        link.symlink_to(self.config.parent, target_is_directory=True)
        result = self.command(*self.configure_arguments(config=link / "other.json"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlinks", result.stderr)
        self.assertFalse((self.config.parent / "other.json").exists())
        result = self.command(*self.configure_arguments(config=CONTRIB / "private-test.json"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the checkout", result.stderr)
        self.assertFalse((CONTRIB / "private-test.json").exists())

    def test_private_custom_url_and_secret_generation_fail_without_traceback(self):
        for endpoint in ("http://127.0.0.1:1234/v1", "https://10.0.0.1/v1", "https://example.com/v1?token=FAKEONLY"):
            with self.subTest(endpoint=endpoint):
                result = self.command(*self.configure_arguments(provider="custom", **{"base-url": endpoint}))
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.config.exists())
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("FAKEONLY", result.stderr)
        result = self.command(*self.configure_arguments(generation='{"max_output_tokens":64,"api_key":"FAKEONLY"}'))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("FAKEONLY", result.stderr)
        self.assertFalse(self.config.exists())

    def test_oauth_configuration_requires_external_bridge_and_exact_endpoint(self):
        arguments = self.configure_arguments(provider="codex_oauth", **{"base-url": "http://127.0.0.1:54321/v1"})
        result = self.command(*arguments)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authorized", result.stderr)
        self.assertIn("bridge", result.stderr)
        self.assertFalse(self.config.exists())
        result = self.command(*arguments, "--bridge-binary", sys.executable)
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(self.config.read_text())
        self.assertEqual(values["base_url"], "http://127.0.0.1:54321/v1")
        self.assertEqual(values["bridge_binary"], str(Path(sys.executable).resolve()))
        self.assertIn("no account tokens are extracted", result.stderr)

    def test_bridge_doctor_uses_tcp_only_and_reports_closed_listener(self):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(5)
        received = []

        def serve():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(5)
                received.append(connection.recv(4096))

        server = threading.Thread(target=serve)
        server.start()
        settings = argparse.Namespace(provider="codex_oauth", bridge_binary=Path(sys.executable),
                                      base_url=f"http://127.0.0.1:{listener.getsockname()[1]}/v1")
        digest = cli.bridge_check(settings)
        server.join(timeout=6)
        self.assertFalse(server.is_alive())
        self.assertEqual(received, [b""])
        self.assertEqual(digest, cli.runner.sha(Path(sys.executable)))
        listener.close()
        with self.assertRaisesRegex(cli.CLIError, "not listening"):
            cli.bridge_check(settings)

    def test_setup_missing_prerequisites_is_actionable_and_has_no_partial_home(self):
        environment = dict(self.environment, PATH="")
        home = self.root / "setup-home"
        result = self.command("setup", "--home", home, "--no-input", environment=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sudo apt-get", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(home.exists())

    def test_new_private_work_can_be_created_under_shared_temporary_parent(self):
        path = self.root / "new-smoke-work"
        work = cli.new_work(path)
        self.assertEqual(work.stat().st_mode & 0o777, 0o700)
        with self.assertRaisesRegex(cli.CLIError, "new private work"):
            cli.new_work(path)

    def test_official_disk_reserve_is_not_reduced_for_small_available_space(self):
        capacity = type("Capacity", (), {"free": 512 * 1024**2})()
        with mock.patch.object(cli.shutil, "disk_usage", return_value=capacity):
            with self.assertRaisesRegex(RuntimeError, "Insufficient local artifact space"):
                cli.admit_artifact_disk(self.root)

    def test_synthetic_disk_admission_preserves_input_size_and_renderer_reserve(self):
        source = self.root / "large-synthetic.xm"
        with source.open("wb") as stream:
            stream.truncate(64 * 1024**2)
        capacity = type("Capacity", (), {"free": 480 * 1024**2})()
        with mock.patch.object(cli.shutil, "disk_usage", return_value=capacity):
            with self.assertRaisesRegex(RuntimeError, "insufficient evaluation disk"):
                cli.admit_artifact_disk(self.root, source)


if __name__ == "__main__":
    unittest.main()
