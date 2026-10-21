"""Explicit, local CLIProxyAPI OAuth orchestration; never extracts provider tokens.

Login completion and benchmark route qualification are separate states. No
provider requests are made by this module; the user-selected bridge owns OAuth.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

FLOWS = {"codex": "-codex-device-login", "anthropic": "-claude-login", "xai": "-xai-login"}
ROUTES = {"codex": "codex_oauth", "anthropic": "anthropic_oauth", "xai": "xai_oauth"}
ALIASES = {"openai": "codex"}


def provider(name):
    name = ALIASES.get(name, name)
    if name not in FLOWS:
        raise ValueError("No reviewed OAuth login flow for this provider. Gemini CLI and Antigravity are not interchangeable. Use --method api-key explicitly if desired.")
    return name


def config_path(directory, name):
    return directory / "oauth" / provider(name) / "bridge.json"


def resolve_binary(value):
    path = Path(value).expanduser() if value else Path(shutil.which("cli-proxy-api") or "")
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("Install a reviewed CLIProxyAPI v8 release and select its executable with --bridge-binary; nothing is downloaded automatically")
    return path.resolve()


def create_config(directory, name, binary, port, private_directory):
    if not 1024 <= port <= 65535:
        raise ValueError("Bridge port must be between 1024 and 65535")
    name = provider(name)
    path = config_path(directory, name)
    private_directory(path.parent)
    if path.exists() or path.is_symlink():
        raise ValueError("OAuth bridge configuration already exists; reuse it instead of overwriting credentials")
    token_dir = private_directory(path.parent / "provider-tokens")
    config = {"config-version": 8, "server": {"host": "127.0.0.1", "port": port},
              "access": {"api-keys": [secrets.token_urlsafe(32)]},
              "management": {"secret-key": ""}, "oauth": {"auth-dir": str(token_dir)},
              "upstream": {"claude": {"disable-claude-cloak-mode": True, "disable-cloaking-model-list": True},
                           "codex": {"disable-codex-cloaking": True}, "xai": {"inject-x-search": False}},
              "multimedia": {"disable-image-generation": True}, "plugins": {"enabled": False}}
    # JSON is a YAML subset supported by CLIProxyAPI. Do not interpolate YAML paths/keys.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump(config, output, indent=2)
        output.write("\n")
    metadata = path.parent / "client.json"
    fd = os.open(metadata, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump({"binary": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "login_verified": False}, output)
    return path


def load_config(directory, name, outside_path, check_owner):
    path = outside_path(config_path(directory, name))
    check_owner(path.parent, directory=True)
    check_owner(path)
    if path.stat().st_size > 32768:
        raise ValueError("OAuth configuration exceeds size limit")
    value = json.loads(path.read_text())
    # This is a dedicated generated profile, not an arbitrary account config.
    if value.get("config-version") != 8 or value.get("server", {}).get("host") != "127.0.0.1":
        raise ValueError("OAuth bridge must use the generated v8 loopback configuration")
    port = value["server"].get("port")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Invalid OAuth bridge port")
    if value.get("upstream") != {"claude": {"disable-claude-cloak-mode": True, "disable-cloaking-model-list": True}, "codex": {"disable-codex-cloaking": True}, "xai": {"inject-x-search": False}} or value.get("plugins") != {"enabled": False} or value.get("multimedia") != {"disable-image-generation": True}:
        raise ValueError("OAuth bridge no-cloak profile was changed; do not silently alter the benchmark")
    if set(value) != {"config-version", "server", "access", "management", "oauth", "upstream", "multimedia", "plugins"} or value.get("management") != {"secret-key": ""}:
        raise ValueError("Unexpected OAuth bridge settings; aliases, fallbacks and management access are not allowed")
    if set(value["server"]) != {"host", "port"} or set(value.get("access", {})) != {"api-keys"} or set(value.get("oauth", {})) != {"auth-dir"}:
        raise ValueError("Unexpected nested OAuth bridge settings")
    token_dir = outside_path(Path(value.get("oauth", {}).get("auth-dir", "")))
    if token_dir != path.parent / "provider-tokens":
        raise ValueError("OAuth credential directory must remain isolated in this profile")
    check_owner(token_dir, directory=True)
    keys = value.get("access", {}).get("api-keys")
    if not isinstance(keys, list) or len(keys) != 1 or not isinstance(keys[0], str) or len(keys[0]) < 32:
        raise ValueError("Invalid local bridge bearer")
    metadata = outside_path(path.parent / "client.json")
    check_owner(metadata)
    if metadata.stat().st_size > 8192:
        raise ValueError("Invalid OAuth client metadata")
    client = json.loads(metadata.read_text())
    binary = resolve_binary(client.get("binary"))
    if client.get("sha256") != hashlib.sha256(binary.read_bytes()).hexdigest():
        raise ValueError("Selected bridge binary changed; review the update before reusing this OAuth profile")
    return path, binary, value


def command(binary, path, name, *, no_browser=False, serve=False):
    result = [str(binary), "--config", str(path)]
    if not serve:
        result.append(FLOWS[provider(name)])
        if no_browser:
            result.append("-no-browser")
    return result


def invoke(arguments):
    # Inherit the local terminal, never capture OAuth codes/URLs into run artifacts.
    # A zero exit code is NOT proof of login: some upstream helpers swallow errors.
    environment = {key: value for key, value in os.environ.items()
                   if not any(part in key.upper() for part in ("TOKEN", "SECRET", "PASSWORD", "API_KEY"))}
    return subprocess.run(arguments, env=environment, check=False).returncode
