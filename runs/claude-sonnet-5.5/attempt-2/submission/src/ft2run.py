import json, subprocess, wave
import numpy as np


def ft2(name, args=None):
    p = subprocess.run(["ft2", "call", name, json.dumps(args or {})], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stdout + p.stderr)
    r = json.loads(p.stdout.strip().splitlines()[-1])
    if r.get("isError"):
        raise RuntimeError(str(r))
    return r["content"][0]["text"]


def render(xm, wav, bits=16, amp=None, start=None, stop=None):
    ft2("module_load", {"path": xm})
    a = {"path": wav, "bits": bits}
    if amp is not None:
        a["amp"] = amp
    if start is not None:
        a["start"] = start
    if stop is not None:
        a["stop"] = stop
    return ft2("module_render", a)


def read_wav(path):
    """returns float array (frames, 2) in [-1, 1] (or beyond for float wavs) and sample rate"""
    import struct
    d = open(path, "rb").read()
    assert d[:4] == b"RIFF"
    pos = 12
    fmt = None
    data = None
    while pos < len(d):
        cid = d[pos:pos + 4]
        sz = struct.unpack_from("<I", d, pos + 4)[0]
        if cid == b"fmt ":
            fmt = struct.unpack_from("<HHIIHH", d, pos + 8)
        elif cid == b"data":
            data = d[pos + 8: pos + 8 + sz]
        pos += 8 + sz + (sz & 1)
    tag, ch, sr, _, _, bits = fmt
    if tag == 3:
        x = np.frombuffer(data, dtype="<f4").astype(np.float64)
    elif bits == 16:
        x = np.frombuffer(data, dtype="<i2").astype(np.float64) / 32768.0
    elif bits == 32:
        x = np.frombuffer(data, dtype="<i4").astype(np.float64) / 2147483648.0
    elif bits == 24:
        b = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
        v = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float64) / (1 << 23)
    else:
        raise ValueError(bits)
    return x.reshape(-1, ch), sr
