"""A Chat Completions Model adapter for mini-swe-agent's DefaultAgent.

Speaks mini's default action protocol: one declared `bash` function tool, the model
answers with tool calls, observations go back as `tool` messages. No LiteLLM router,
native CLI, config discovery, extra tools, or skill loader. Credentials never enter
messages or serialized model configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from types import SimpleNamespace

Reply = SimpleNamespace  # request() result: .json, .headers, .seconds, .bytes
from typing import Any

from minisweagent.models.utils.actions_toolcall import (
    BASH_TOOL, format_toolcall_observation_messages, parse_toolcall_actions)

MAX_RESPONSE = 16 * 1024 * 1024
# Response headers kept per request for quota accounting; anything else is dropped unread.
RATE_LIMIT_HEADERS = ("retry-after", "anthropic-ratelimit-", "x-ratelimit-", "x-codex-", "openai-processing-ms")
# mini's stock LitellmModel defaults, so every model gets the same wording and observation shape.
# DefaultAgent feeds a FormatError back as a user message and ends the run after three in a row.
FORMAT_ERROR = "{{ error }}"
OBSERVATION = ("{% if output.exception_info %}<exception>{{output.exception_info}}</exception>\n{% endif %}"
               "<returncode>{{output.returncode}}</returncode>\n<output>\n{{output.output}}</output>"
               "{% if output.time_left %}\n<time_left>{{output.time_left}}</time_left>{% endif %}")
# One client-side retry after this pause, only for upstream 5xx and transport failures. 4xx (auth, quota,
# rate limit) end the attempt at once: they are the provider's answer, not a transient. The proxy itself
# is configured with request-retry 0 so every upstream request appears in the audit exactly once.
RETRY_PAUSE_SECONDS = 5
TRANSIENT = ("Proxy HTTP 5", "Proxy transport failed")
# Keep provider reasoning state across tool turns; mini's local metadata stays local.
REASONING_FIELDS = ("reasoning_content", "reasoning", "reasoning_details")
FORWARDED = {"system": ("content",), "user": ("content",),
             "assistant": ("content", "tool_calls", *REASONING_FIELDS),
             "tool": ("content", "tool_call_id")}


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


def request(base: str, key: str, path: str, payload=None, timeout: float = 180) -> Reply:
    """Exactly one HTTP request, no ambient HTTP_PROXY or redirects. Retrying is the caller's decision.

    Returns .json (the decoded object), .headers (rate-limit subset), .seconds (wall time).
    """
    body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    req = urllib.request.Request(validate_url(base) + path, data=body,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
            headers = {k.lower(): v for k, v in response.headers.items() if k.lower().startswith(RATE_LIMIT_HEADERS)}
    except urllib.error.HTTPError as exc:
        # Do not persist upstream error bodies/headers: they can contain credentials.
        raise RuntimeError(f"Proxy HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("Proxy transport failed") from None
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Proxy response exceeded byte limit")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Proxy response must be an object")
    return Reply(json=result, headers=headers, seconds=time.monotonic() - started, bytes=len(raw))


def forward(message: dict) -> dict:
    """The upstream view of one conversation message: role plus the keys the API needs."""
    return {"role": message["role"], **{k: message[k] for k in FORWARDED[message["role"]] if k in message}}


class ProxyModel:
    def __init__(self, config: dict, model: dict, audit: Path):
        self.config, self.model, self.audit = config, model, audit
        self.key = os.environ[config["api_key_env"]]

    def query(self, messages: list[dict], **kwargs) -> dict:
        payload = {**self.config["generation"], "model": self.model["model"],
                   "messages": [forward(m) for m in messages], "tools": [BASH_TOOL],
                   "stream": False, "n": 1}
        for attempt in (1, 2):
            started_at = time.time()
            try:
                reply = request(self.config["base_url"], self.key, "/chat/completions", payload,
                                self.config["limits"]["request_seconds"])
                break
            except (RuntimeError, ValueError) as exc:
                # A failed request still cost time; record it so totals do not read as zero. A transient
                # upstream failure gets one more try; the audit line says so, and both requests count.
                retry = attempt == 1 and str(exc).startswith(TRANSIENT)
                failed = {"request_sha256": digest(payload), "requested_model": self.model["model"], "started_at": started_at,
                          "latency_seconds": time.time() - started_at, "prompt_messages": len(payload["messages"]),
                          "error": type(exc).__name__ + ": " + str(exc), "retried": retry}
                with self.audit.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(failed, allow_nan=False) + "\n")
                if not retry:
                    raise
                time.sleep(RETRY_PAUSE_SECONDS)
        response = reply.json
        returned_model = response.get("model")
        record = {"request_sha256": digest(payload), "requested_model": self.model["model"],
                  "returned_model": returned_model, "id": response.get("id"),
                  "usage": response.get("usage"), "system_fingerprint": response.get("system_fingerprint"),
                  "started_at": started_at, "latency_seconds": reply.seconds, "response_bytes": reply.bytes,
                  "prompt_messages": len(payload["messages"]), "rate_limit": reply.headers}
        with self.audit.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, allow_nan=False) + "\n")
        # Whole upstream body (reasoning fields included) beside the audit line, one JSON per turn.
        with self.audit.with_name("responses.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(response, allow_nan=False) + "\n")
        if returned_model != self.model["response_model"]:
            raise ValueError("Unexpected response model; possible alias or fallback")
        choices = response.get("choices", [])
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("Expected exactly one completion")
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        if not isinstance(tool_calls, list) or not all(isinstance(t, dict) for t in tool_calls):
            raise ValueError("Malformed tool_calls in completion")
        # mini's parser reads attribute-style objects (LiteLLM's); the audit line above is already
        # written, so a FormatError here still records the turn.
        actions = parse_toolcall_actions(
            [SimpleNamespace(id=t.get("id"), function=SimpleNamespace(
                name=(t.get("function") or {}).get("name"), arguments=(t.get("function") or {}).get("arguments", "")))
             for t in tool_calls],
            format_error_template=FORMAT_ERROR, template_kwargs={"finish_reason": choices[0].get("finish_reason")})
        content = message.get("content")
        return {"role": "assistant", "content": content if isinstance(content, str) else "",
                "tool_calls": tool_calls,
                **{key: message[key] for key in REASONING_FIELDS if key in message},
                "extra": {"actions": actions, "cost": 0.0, "cost_status": "not_measured", **record,
                          "timestamp": time.time(), "finish_reason": choices[0].get("finish_reason")}}

    def format_message(self, **kwargs) -> dict:
        return kwargs

    def format_observation_messages(self, message: dict, outputs: list[dict], template_vars=None) -> list[dict]:
        # Only 20 KB of any observation reaches the model; the container already capped the log.
        bounded = []
        for output in outputs:
            text = output.get("output", "")
            if len(text) > 20000:
                text = text[:10000] + "\n[observation truncated]\n" + text[-10000:]
            # mini's template reads exception_info (the sandbox only reports it on failure) and time_left
            # (set below on the last output) with strict undefined checking, so both keys always exist.
            bounded.append({"exception_info": "", "time_left": "", **output, "output": text})
        # The step's last observation ends with the minutes left, so a model can pace itself against the
        # wall clock instead of discovering the limit when the run ends. mini supplies both numbers.
        limit = (template_vars or {}).get("wall_time_limit_seconds") or 0
        if bounded and limit > 0:
            left = max(0, limit - int(template_vars.get("elapsed_seconds", 0)))
            bounded[-1]["time_left"] = f"{left // 60} min"
        return format_toolcall_observation_messages(
            actions=message["extra"]["actions"], outputs=bounded, observation_template=OBSERVATION)

    def get_template_vars(self, **kwargs) -> dict:
        return {}

    def serialize(self) -> dict:
        return {"info": {"transport": "cliproxyapi_chat_completions_retry_transient_once", "tools": ["bash"],
                         "requested_model": self.model["model"],
                         "generation": self.config["generation"], "cost_status": "not_measured"}}
