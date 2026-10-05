"""Direct Python client for the persistent FT2 MCP bridge socket."""
import json
import socket

SOCKET = "/tmp/keygen-ft2.sock"
LIMIT = 240 * 1024


def call(tool, **arguments):
    msg = {"op": "call", "name": tool, "arguments": arguments}
    raw = json.dumps(msg).encode() + b"\n"
    if len(raw) > LIMIT:
        raise ValueError(f"request too large: {len(raw)} bytes")
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(600)
        sock.connect(SOCKET)
        sock.sendall(raw)
        chunks = []
        with sock.makefile("rb") as reader:
            line = reader.readline(LIMIT + 1)
    reply = json.loads(line)
    if "error" in reply:
        raise RuntimeError(reply["error"])
    result = reply["result"]
    if result.get("isError"):
        raise RuntimeError(result)
    return result


def text_of(result):
    for item in result.get("content", []):
        if item.get("type") == "text":
            return item["text"]
    return None


def jcall(tool, **arguments):
    """Call and parse JSON text response."""
    res = call(tool, **arguments)
    t = text_of(res)
    try:
        return json.loads(t)
    except Exception:
        return t


if __name__ == "__main__":
    print(jcall("module_info"))
