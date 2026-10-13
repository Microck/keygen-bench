import json
import socket
import base64

SOCKET = "/tmp/keygen-ft2.sock"
LIMIT = 240 * 1024

class FT2Client:
    def __init__(self):
        pass

    def call(self, name: str, arguments: dict = None):
        if arguments is None:
            arguments = {}
        msg = {"op": "call", "name": name, "arguments": arguments}
        raw = json.dumps(msg).encode("utf-8") + b"\n"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(60)
            sock.connect(SOCKET)
            sock.sendall(raw)
            with sock.makefile("rb") as reader:
                line = reader.readline(LIMIT + 1)
        reply = json.loads(line)
        if "error" in reply:
            raise RuntimeError(f"FT2 error in {name}: {reply['error']}")
        res = reply["result"]
        if res.get("isError"):
            raise RuntimeError(f"FT2 tool error in {name}: {res}")
        return res

    def load_sample_pcm(self, idx: int, sdict: dict):
        pcm_b64 = base64.b64encode(sdict['pcm'].tobytes()).decode('ascii')
        self.call("instrument_set", {"instrument": idx, "name": sdict['name']})
        self.call("sample_create_from_pcm", {
            "instrument": idx,
            "sample": 0,
            "pcm": pcm_b64,
            "encoding": "int16",
            "name": sdict['name']
        })
        self.call("sample_set", {
            "instrument": idx,
            "sample": 0,
            "name": sdict['name'],
            "volume": sdict['volume'],
            "panning": sdict['panning'],
            "relative_note": sdict['relative_note'],
            "finetune": sdict['finetune'],
            "loop_start": sdict['loop_start'],
            "loop_length": sdict['loop_length'],
            "flags": sdict['flags']
        })
