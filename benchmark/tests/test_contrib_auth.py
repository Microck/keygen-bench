"""Synthetic local login lifecycle: no accounts, network requests or model calls."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("auth_cli", Path(__file__).resolve().parents[1] / "contrib/cli.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class LoginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "credentials"
        self.secret = "SYNTHETIC_TEST_ONLY_NOT_A_REAL_KEY"
        self.env = {k: v for k, v in os.environ.items() if not any(x in k for x in ("KEY", "TOKEN", "SECRET"))}

    def command(self, action, provider, *extra, env=None):
        return subprocess.run([sys.executable, str(SPEC.origin), action, provider,
                               "--auth-dir", str(self.directory), "--no-input", "--method", "api-key", *extra],
                              env=env or self.env, capture_output=True, text=True, timeout=20)

    def test_all_provider_login_status_logout_without_secret_output(self):
        for name in (n for n in cli.auth.NAMES if n != "custom"):
            canonical = cli.auth.canonical(name)
            variable = cli.auth.PROFILES[canonical][2]
            result = self.command("login", name, "--save", env={**self.env, variable: self.secret})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(self.secret, result.stdout + result.stderr)
            path = self.directory / (canonical + ".json")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
            self.assertIn("unverified", self.command("auth-status", name).stdout)
            result = self.command("logout", name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(path.exists())
            self.assertIn("remains active", result.stdout)

    def test_save_is_explicit_and_replace_is_explicit(self):
        env = {**self.env, "OPENAI_API_KEY": self.secret}
        self.assertNotEqual(self.command("login", "openai", env=env).returncode, 0)
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.command("login", "openai", "--save", env=env).returncode, 0)
        self.assertNotEqual(self.command("login", "openai", "--save", env=env).returncode, 0)
        self.assertEqual(self.command("login", "openai", "--save", "--replace", env=env).returncode, 0)

    def test_noninteractive_oauth_rejects_for_the_expected_reason(self):
        for name in cli.auth.NAMES:
            result = self.command("login", name, "--method", "oauth", "--save")
            self.assertNotEqual(result.returncode, 0)
            expected = ("OAuth requires an interactive local terminal" if name in {"openai", "codex", "anthropic", "xai"}
                        else "No reviewed OAuth login flow for this provider")
            self.assertIn(expected, result.stderr)
            self.assertNotIn("_API_KEY", result.stderr)
            self.assertFalse(self.directory.exists())

    def test_saved_key_never_follows_custom_destination(self):
        cli.private_directory(self.directory)
        cli.auth.save_key(self.directory, "openai", self.secret)
        settings = argparse.Namespace(provider="openai", base_url="https://api.openai.com/v1")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cli.saved_credential(settings, self.directory), self.secret)
            for provider, url in [("custom", "https://attacker.example/v1"), ("openai", "https://api.openai.com.evil.example/v1"), ("codex_oauth", "http://127.0.0.1:8888/v1")]:
                settings.provider, settings.base_url = provider, url
                self.assertIsNone(cli.saved_credential(settings, self.directory))

    def test_symlinks_permissions_and_tampered_destination_fail(self):
        cli.private_directory(self.directory)
        cli.auth.save_key(self.directory, "openai", self.secret)
        path = self.directory / "openai.json"
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            cli.auth.read_key(self.directory, "openai")
        path.chmod(0o600)
        data = json.loads(path.read_text())
        data["endpoint"] = "https://attacker.example/v1"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            cli.auth.read_key(self.directory, "openai")
        path.unlink()
        path.symlink_to(Path(self.temp.name) / "elsewhere")
        with self.assertRaises((ValueError, OSError)):
            cli.auth.save_key(self.directory, "openai", self.secret, replace=True)
        with self.assertRaises(OSError):
            cli.auth.read_key(self.directory, "openai")

    def test_invalid_secrets_and_secret_flags_never_echo(self):
        result = self.command("login", "openai", "--save", "--api-key", self.secret)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(self.secret, result.stdout + result.stderr)
        result = self.command("login", "openai", "--save", env={**self.env, "OPENAI_API_KEY": self.secret + "\nBAD"})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(self.secret, result.stdout + result.stderr)

    def test_direct_run_and_guided_run_block_incompatible_bridges_before_spend(self):
        for provider in ("codex_oauth", "anthropic_oauth"):
            with self.assertRaisesRegex(ValueError, "not eligible"):
                cli.runner.execute(argparse.Namespace(provider=provider))
        cli.runner.require_contributor_route(argparse.Namespace(provider="openai"))

    def test_no_input_does_not_prompt_or_save_without_key(self):
        result = self.command("login", "xai", "--save")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("XAI_API_KEY", result.stderr)
        self.assertFalse(self.directory.exists())

    def test_help_states_login_defaults_to_oauth_with_explicit_api_key_option(self):
        result = subprocess.run([sys.executable, str(SPEC.origin), "--help"], env={**self.env, "COLUMNS": "400"},
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        login = next(line for line in result.stdout.splitlines() if line.split()[:1] == ["login"])
        self.assertIn("OAuth", login)
        self.assertIn("--method api-key", login)


if __name__ == "__main__":
    unittest.main()
