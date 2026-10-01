#!/usr/bin/env python3
"""Summarize qualification output directories without credential values or error bodies.

Usage: qualification-collect.py <out-root> <label> [<label> ...]  -> JSON on stdout.
"""
import json
from pathlib import Path
import re
import sys

KEYLIKE = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|nvapi-[A-Za-z0-9_-]{8,}|Bearer\s+\S+|[A-Za-z0-9_-]{40,})")


def load(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def records(root):
    path = root / "transport.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def last_error_line(root):
    """The final exception line of the redacted worker log, scrubbed of key-like tokens."""
    path = root / "worker.log"
    if not path.exists():
        return None
    lines = [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]
    for line in reversed(lines):
        if re.match(r"^[A-Za-z_.]+(Error|Exception|Exceeded)\b", line) or "Error:" in line:
            return KEYLIKE.sub("[REDACTED]", line)[:300]
    return None


def summarize(root, probe):
    transport = records(root)
    requests = [r for r in transport if r.get("event") == "request"]
    responses = [r for r in transport if r.get("event") == "response"]
    row = {
        "dir": root.name,
        "request_settings": [r.get("settings") for r in requests],
        "requested_models": sorted({r.get("model") for r in requests if r.get("model")}),
        "returned_models": sorted({r.get("response_model") for r in responses if r.get("response_model")}),
        "identity_statuses": [r.get("identity_status") for r in responses],
        "responses": [{"latency_seconds": r.get("latency_seconds"), "usage": r.get("usage")} for r in responses],
        "worker_result": load(root / "worker-result.json"),
        "cleanup": load(root / "cleanup.json"),
        "last_error_line": last_error_line(root),
    }
    if probe:
        payload = load(root / "probe.json") or {}
        row.update({key: payload.get(key) for key in (
            "outcome", "max_output_tokens_observed", "max_latency_seconds", "failure_category",
            "settings_match", "exchanges", "blocker")})
    else:
        readiness = load(root / "readiness.json") or {}
        row["status"] = readiness.get("status")
        row["blocker"] = readiness.get("blocker")
        row["proof_sha256"] = (readiness.get("evidence") or {}).get("artifact_sha256")
    return row


def main():
    out = Path(sys.argv[1])
    result = {}
    for label in sys.argv[2:]:
        for root in sorted((out / label).iterdir()):
            if root.is_dir():
                result.setdefault(label, {})[root.name] = summarize(root, (root / "probe.json").exists())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
