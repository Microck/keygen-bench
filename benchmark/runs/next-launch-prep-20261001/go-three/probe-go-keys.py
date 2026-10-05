#!/usr/bin/env python3
"""Send exactly ONE tiny Chat request per named OpenCode Go key and record whether it is usable.

usage: probe-go-keys.py ENV_JSON OUT_JSON KEY_NAME [KEY_NAME ...]

Runs on the controller that holds the private environment file. Each key gets a single
non-streaming request (8 output tokens) and is never retried: a key that answers with a usage
limit (GoUsageLimitError / usage limit / 429) must not receive further requests. Records only
key names, HTTP status, error type and a scrubbed error excerpt; never key values.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

URL = "https://opencode.ai/zen/go/v1/chat/completions"
MODEL = "deepseek-v4.1-flash"
SECRET = re.compile(r"(?:oc_sk_|sk-ant-|sk-proj-|sk-)[A-Za-z0-9_-]{8,}")


def probe(key: str) -> dict:
    body = json.dumps({"model": MODEL, "max_tokens": 8,
                       "messages": [{"role": "user", "content": "Reply with the single word OK."}]}).encode()
    request = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
        "User-Agent": "keygen-benchmark/go-key-probe-1.0",
        # Go rejects unrouted requests (MissingSessionID); the harness sends a per-run digest too.
        "x-opencode-session": hashlib.sha256(uuid.uuid4().bytes).hexdigest()})
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read())
            return {"http_status": response.status, "usable": True, "category": "ok",
                    "response_model": payload.get("model"), "usage": payload.get("usage"),
                    "seconds": round(time.time() - started, 2)}
    except urllib.error.HTTPError as exc:
        text = SECRET.sub("[redacted]", exc.read().decode("utf-8", "replace"))[:400]
        limited = exc.code == 429 or re.search(r"GoUsageLimitError|usage limit|rate limit|insufficient", text, re.I)
        return {"http_status": exc.code, "usable": False, "category": "usage_limit" if limited else "error",
                "error_excerpt": text, "seconds": round(time.time() - started, 2)}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"http_status": None, "usable": False, "category": "transport", "error": type(exc).__name__,
                "seconds": round(time.time() - started, 2)}


def main():
    env_path, out_path, names = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    if env_path.stat().st_mode & 0o077:
        raise SystemExit("private environment file permissions too broad")
    env = json.loads(env_path.read_text())
    results = []
    for name in names:
        if not re.fullmatch(r"OPENCODE_GO_API_KEY(?:_[0-9])?", name) or not env.get(name):
            raise SystemExit(f"{name}: not an approved Go key name present in the controller environment")
        results.append({"key": name, "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": MODEL,
                        "requests_sent": 1, **probe(env[name])})
        print(json.dumps(results[-1]), flush=True)
    previous = json.loads(out_path.read_text()) if out_path.exists() else {"probes": []}
    previous["probes"].extend(results)
    out_path.write_text(json.dumps(previous, indent=2) + "\n")


if __name__ == "__main__":
    main()
