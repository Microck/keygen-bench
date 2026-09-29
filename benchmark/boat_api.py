"""Finite controller-only Boat metadata requests, with credentials passed on stdin.

The parent enforces a whole-process deadline. A killed create/fork HTTP request
is ambiguous, so only the same idempotency key can recover it. This helper never
runs remote commands or transports artifact bytes.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    payload = json.loads(sys.stdin.buffer.read(128 * 1024))
    url = payload["url"]
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in {"boat.dev", "ascii.dev"}:
        raise ValueError("untrusted Boat API origin")
    headers = {"Authorization": "Bearer " + payload["token"], "Content-Type": "application/json"}
    if payload.get("key"):
        headers["Idempotency-Key"] = payload["key"]
    body = payload.get("body")
    request = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=payload["method"])
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=payload["timeout"]) as response:
            data = json.loads(response.read(2 * 1024 * 1024))
        if not isinstance(data, dict) or data.get("ok") is False:
            raise ValueError("unsuccessful Boat response")
        result = {"result": data}
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read(64 * 1024))
            error = data.get("error")
            code = data.get("code") or (error.get("code") if isinstance(error, dict) else None) or "http_error"
            if not isinstance(code, str) or not code.replace("_", "").isalnum():
                code = "http_error"
        except (ValueError, AttributeError):
            code = "http_error"
        result = {"error": {"code": code, "status": exc.code}}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        result = {"error": {"code": "connection_error", "status": 0}}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never dump requests, credentials, response URLs, or tracebacks.
        sys.stdout.write(json.dumps({"error": {"code": "connection_error", "status": 0}}))
