"""A no-retry Chat Completions Model adapter for mini-swe-agent's DefaultAgent.

No LiteLLM router, native CLI, config discovery, tool injection, or skill loader.
Credentials never enter messages or serialized model configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ACTION = re.compile(r"```mswea_bash_command\s*\n(.*?)\n```", re.DOTALL)
MAX_RESPONSE = 16 * 1024 * 1024


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def validate_url(url: str) -> str:
    u = urllib.parse.urlsplit(url)
    if (u.scheme != "http" or u.hostname != "127.0.0.1" or not u.port
            or u.path.rstrip("/") != "/v1" or u.username or u.password or u.query or u.fragment):
        raise ValueError("Use an explicit http://127.0.0.1:PORT/v1 proxy URL")
    return url.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Proxy redirect refused")


def request(base: str, key: str, path: str, payload=None, timeout: float = 180) -> dict:
    """Exactly one HTTP request, no ambient HTTP_PROXY, redirects, or retries."""
    body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    req = urllib.request.Request(validate_url(base) + path, data=body,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as exc:
        # Do not persist upstream error bodies/headers: they can contain credentials.
        raise RuntimeError(f"Proxy HTTP {exc.code}; request not retried") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("Proxy transport failed; request not retried") from None
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Proxy response exceeded byte limit")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Proxy response must be an object")
    return result


class ProxyModel:
    def __init__(self, config: dict, model: dict, audit: Path):
        self.config, self.model, self.audit = config, model, audit
        self.key = os.environ[config["api_key_env"]]

    def query(self, messages: list[dict], **kwargs) -> dict:
        clean = [{"role": m["role"], "content": m["content"]} for m in messages]
        payload = {**self.config["generation"], "model": self.model["model"],
                   "messages": clean, "stream": False, "n": 1}
        response = request(self.config["base_url"], self.key, "/chat/completions", payload,
                           self.config["limits"]["request_seconds"])
        returned_model = response.get("model")
        record = {"request_sha256": digest(payload), "requested_model": self.model["model"],
                  "returned_model": returned_model, "id": response.get("id"),
                  "usage": response.get("usage"), "system_fingerprint": response.get("system_fingerprint")}
        with self.audit.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, allow_nan=False) + "\n")
        if returned_model != self.model["response_model"]:
            raise ValueError("Unexpected response model; possible alias or fallback")
        choices = response.get("choices", [])
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("Expected exactly one completion")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ValueError("Expected a text completion")
        actions = ACTION.findall(content)
        if len(actions) != 1 or not actions[0].strip():
            raise ValueError("Expected exactly one nonempty mswea_bash_command block")
        return {"role": "assistant", "content": content,
                "extra": {"actions": [{"command": actions[0]}], "cost": 0.0,
                          "cost_status": "not_measured", **record,
                          "finish_reason": choices[0].get("finish_reason")}}

    def format_message(self, **kwargs) -> dict:
        return kwargs

    def format_observation_messages(self, message, outputs, template_vars=None) -> list[dict]:
        result = []
        for output in outputs:
            text = output.get("output", "")
            if len(text) > 20000:
                text = text[:10000] + "\n[observation truncated]\n" + text[-10000:]
            result.append({"role": "user", "content":
                           f"<returncode>{output['returncode']}</returncode>\n<output>\n{text}\n</output>"})
        return result

    def get_template_vars(self, **kwargs) -> dict:
        return {}

    def serialize(self) -> dict:
        return {"info": {"transport": "cliproxyapi_chat_completions_no_retry",
                         "requested_model": self.model["model"],
                         "generation": self.config["generation"], "cost_status": "not_measured"}}
