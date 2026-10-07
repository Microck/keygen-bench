import sys, json, socket
sys.path.insert(0, "/opt/keygen")
LIMIT = 240*1024
SOCKET = "/tmp/keygen-ft2.sock"

def call(_tool, **arguments):
    raw = json.dumps({"op":"call","name":_tool,"arguments":arguments}).encode()+b"\n"
    if len(raw) > LIMIT: raise ValueError("too large")
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(600)
        s.connect(SOCKET)
        s.sendall(raw)
        with s.makefile("rb") as r:
            line = r.readline(LIMIT*2)
    rep = json.loads(line)
    if "error" in rep: raise RuntimeError(rep["error"])
    res = rep["result"]
    txt = "\n".join(c.get("text","") for c in res.get("content",[]) if c.get("type")=="text")
    if res.get("isError"): raise RuntimeError(txt)
    return txt
