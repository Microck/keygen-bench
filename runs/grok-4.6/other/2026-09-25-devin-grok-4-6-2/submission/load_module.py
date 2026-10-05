#!/usr/bin/env python3
"""Create module, load instruments, set sample params. Patterns later."""
import json, os, subprocess, sys

def ft2(tool, args):
    cmd = ["ft2", "call", tool, json.dumps(args)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or '"isError": true' in r.stdout:
        print("ERR", tool, args.get("instrument", args), r.stdout[-400:], r.stderr[-200:])
        raise SystemExit(1)
    return r.stdout

index = json.load(open("/workspace/src/samples/index.json"))

# 12 channels
print(ft2("module_new", {"channels": 12, "name": "Neon Cipher"}))
print(ft2("song_set", {
    "name": "Neon Cipher",
    "bpm": 150,
    "speed": 6,
    "length": 12,
    "loop_start": 2,
    "channels": 12,
}))

for meta in index:
    payload = json.load(open(meta["json"]))
    # force instrument number
    payload["instrument"] = meta["instrument"]
    payload["sample"] = 0
    print("load", meta["instrument"], meta["name"], "...", end=" ", flush=True)
    out = ft2("sample_create_from_pcm", payload)
    print("ok")
    ft2("instrument_set", {"instrument": meta["instrument"], "name": meta["name"][:22]})
    flags = 17 if meta["loop"] else 16
    sset = {
        "instrument": meta["instrument"],
        "sample": 0,
        "name": meta["name"][:22],
        "volume": meta["volume"],
        "panning": meta["panning"],
        "finetune": meta["finetune"],
        "relative_note": meta["relative_note"],
        "flags": flags,
    }
    if meta["loop"]:
        sset["loop_start"] = 0
        sset["loop_length"] = meta["n"]
    else:
        sset["loop_start"] = 0
        sset["loop_length"] = 0
    ft2("sample_set", sset)

print(ft2("module_save", {"path": "/workspace/src/base.xm", "format": "xm"}))
print("saved base")
