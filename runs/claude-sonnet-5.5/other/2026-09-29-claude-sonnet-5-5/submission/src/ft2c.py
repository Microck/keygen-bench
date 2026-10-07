import json, socket
SOCK = "/tmp/keygen-ft2.sock"
def call(tool, **args):
    raw = json.dumps({"op": "call", "name": tool, "arguments": args}).encode() + b"\n"
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(600)
        s.connect(SOCK)
        s.sendall(raw)
        with s.makefile("rb") as r:
            line = r.readline(1 << 24)
    rep = json.loads(line)
    if "error" in rep:
        raise RuntimeError(rep["error"])
    res = rep["result"]
    txt = "\n".join(c.get("text", "") for c in res.get("content", []))
    if res.get("isError"):
        raise RuntimeError(tool + ": " + txt)
    return txt
