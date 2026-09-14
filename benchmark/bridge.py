"""Shell client for one persistent FT2 stdio MCP process, inside the sandbox."""
from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

SOCKET = "/tmp/keygen-ft2.sock"
LIMIT = 240 * 1024


def exchange(message: dict) -> dict:
    raw = json.dumps(message).encode() + b"\n"
    if len(raw) > LIMIT:
        raise ValueError("FT2 request too large; use sample_load for large PCM")
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(600)
        sock.connect(SOCKET)
        sock.sendall(raw)
        with sock.makefile("rb") as reader:
            result = reader.readline(LIMIT + 1)
    if len(result) > LIMIT:
        raise ValueError("FT2 response too large")
    reply = json.loads(result)
    if "error" in reply:
        raise RuntimeError(reply["error"])
    return reply["result"]


def serve(binary: str) -> None:
    # The Docker image includes only the existing transport, not repository prompts.
    sys.path.insert(0, "/opt/keygen")
    from tools.ft2_transport import StdioMCP

    client = StdioMCP([binary, "--mcp"], Path("/workspace"), timeout=600)
    try:
        client.initialize()
        tools = client.request("tools/list", {})
        with socket.socket(socket.AF_UNIX) as server:
            server.bind(SOCKET)
            server.listen(8)
            while True:
                with server.accept()[0] as connection:
                    connection.settimeout(30)
                    try:
                        with connection.makefile("rb") as reader:
                            raw = reader.readline(LIMIT + 1)
                        if len(raw) > LIMIT:
                            raise ValueError("request too large")
                        message = json.loads(raw)
                        if message.get("op") == "list":
                            result = tools
                        elif message.get("op") == "call":
                            result = client.request("tools/call", {
                                "name": message["name"], "arguments": message.get("arguments", {})})
                        else:
                            raise ValueError("unknown bridge operation")
                        reply = {"result": result}
                    except Exception as exc:
                        reply = {"error": str(exc)}
                    try:
                        connection.sendall(json.dumps(reply).encode() + b"\n")
                    except (BrokenPipeError, OSError):
                        pass
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)
    sub.add_parser("list")
    call = sub.add_parser("call")
    call.add_argument("name")
    call.add_argument("arguments", nargs="?", default="{}")
    batch = sub.add_parser("batch")
    batch.add_argument("file", type=Path)
    service = sub.add_parser("serve")
    service.add_argument("binary")
    args = parser.parse_args()
    if args.op == "serve":
        serve(args.binary)
        return
    if args.op == "list":
        print(json.dumps(exchange({"op": "list"}), indent=2))
        return
    calls = json.loads(args.file.read_text()) if args.op == "batch" else [
        {"name": args.name, "arguments": json.loads(args.arguments)}]
    if not isinstance(calls, list):
        raise ValueError("batch must be a JSON list")
    for item in calls:
        reply = exchange({"op": "call", "name": item["name"], "arguments": item.get("arguments", {})})
        print(json.dumps(reply), flush=True)
        if reply.get("isError"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
