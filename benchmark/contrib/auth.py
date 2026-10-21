"""Provider-key setup only. No network calls, OAuth-token discovery or inference."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

# name: (runner provider, exact destination, environment variable, key-management URL)
PROFILES = {
    "openai": ("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
    "anthropic": ("anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "https://platform.claude.com/settings/keys"),
    "xai": ("custom", "https://api.x.ai/v1", "XAI_API_KEY", "https://console.x.ai/"),
    "google": ("google", "https://generativelanguage.googleapis.com/v1beta", "GEMINI_API_KEY", "https://aistudio.google.com/apikey"),
    "openrouter": ("custom", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "https://openrouter.ai/settings/keys"),
    "deepseek": ("custom", "https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "https://platform.deepseek.com/api_keys"),
    "groq": ("custom", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "https://console.groq.com/keys"),
    "mistral": ("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "https://console.mistral.ai/"),
    "cohere": ("cohere", "https://api.cohere.ai/compatibility/v1", "COHERE_API_KEY", "https://dashboard.cohere.com/api-keys"),
}
ALIASES = {"codex": "openai", "gemini": "google"}
NAMES = sorted(set(PROFILES) | set(ALIASES) | {"custom"})


def canonical(name):
    name = ALIASES.get(name, name)
    if name not in PROFILES and name != "custom":
        raise ValueError("Unsupported login provider")
    return name


def matching_profile(settings):
    for name, (provider, endpoint, _, _) in PROFILES.items():
        if settings.provider == provider and settings.base_url.rstrip("/") == endpoint:
            return name
    return None


def validate_key(value):
    if not isinstance(value, str) or not value or len(value) > 16384 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("API key must be a nonempty single-line value without whitespace")
    return value


def identity(name, endpoint=None):
    name = canonical(name)
    if name == "custom":
        if not endpoint:
            raise ValueError("Custom credentials require an explicit destination")
        return "custom-" + hashlib.sha256(endpoint.encode()).hexdigest(), endpoint
    return name, PROFILES[name][1]


def read_key(directory, name, endpoint=None):
    """Caller verifies private directory; refuse symlink/nonregular/wrong-owner files."""
    stem, destination = identity(name, endpoint)
    path = directory / (stem + ".json")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "r", encoding="utf-8") as source:
        details = os.fstat(source.fileno())
        if not stat.S_ISREG(details.st_mode) or details.st_uid != os.getuid() or details.st_mode & 0o077 or details.st_size > 32768:
            raise ValueError("Credential file must be an owner-only regular file (0600), at most 32 KiB")
        try:
            record = json.load(source)
        except (ValueError, UnicodeError):
            raise ValueError("Credential file is invalid; use login --replace to repair it") from None
    name = canonical(name)
    if not isinstance(record, dict) or set(record) != {"schema", "provider", "endpoint", "key"} or record.get("schema") != "keygen-api-key-1" or record.get("provider") != name or record.get("endpoint") != destination:
        raise ValueError("Credential destination does not match this provider")
    return validate_key(record["key"])


def save_key(directory, name, key, *, replace=False, endpoint=None):
    name = canonical(name)
    stem, destination = identity(name, endpoint)
    record = {"schema": "keygen-api-key-1", "provider": name, "endpoint": destination, "key": validate_key(key)}
    path = directory / (stem + ".json")
    if path.is_symlink():
        raise ValueError("Credential symlinks are forbidden")
    if path.exists():
        details = path.lstat()
        if not stat.S_ISREG(details.st_mode) or details.st_uid != os.getuid() or details.st_mode & 0o077:
            raise ValueError("Existing credential must be an owner-only regular file")
        if not replace:
            raise ValueError("Credential already exists; use --replace deliberately")
    fd, pending = tempfile.mkstemp(prefix=".login-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            json.dump(record, target)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        if replace:
            os.replace(pending, path)
        else:
            os.link(pending, path, follow_symlinks=False)
    finally:
        Path(pending).unlink(missing_ok=True)


def oauth_unavailable(name):
    name = canonical(name)
    if name == "openai":
        return "Official ChatGPT OAuth does not support the frozen output-token cap/sampling controls. Use an OpenAI API key; OAuth needs a separately disclosed compatible condition, not silent parameter removal."
    if name == "anthropic":
        return "Anthropic does not support third-party Claude subscription login here. Use an Anthropic API key; running Claude Code is a different agent harness."
    return "No compatible official subscription OAuth flow is implemented for this provider. Use its API key; provider CLI credentials are never extracted."
