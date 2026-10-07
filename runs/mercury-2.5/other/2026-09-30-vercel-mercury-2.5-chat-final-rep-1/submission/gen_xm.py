import struct
import os
import numpy as np

MAGIC = b"Extended Module: FastTracker 2.x\n\x1a\n1.00"
NUM_SAMPLES = 2
NUM_PATTERNS = 4
ORDER_LEN = 32
TEMPO = 140
BPM = 125

def gen_sample(freq, dur=0.3):
    sr = 22050
    n = int(sr * dur)
    t = np.arange(n) / sr
    w = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10)
    return (w * 32767).astype(np.int16).tobytes()

s1 = gen_sample(440)
s2 = gen_sample(220)

def mk_sample_hdr(name, data):
    nb = name.encode("ascii")[:22].ljust(22, b"\x00")
    hdr = struct.pack("<22s", nb)
    hdr += struct.pack("<IHHHH", len(data), 0, 0, 0, 0)
    hdr += b"\x00" * 24
    hdr += b"\x00" * 360
    hdr += struct.pack("<" + "H"*64, *([0]*64))
    hdr += struct.pack("<HHHHH", 0,0,0,0,0)
    hdr += struct.pack("<BBBBB", 1,0,0,0,0)
    hdr += struct.pack("<BBBB", 0,0,0,0)
    hdr += struct.pack("<HHHHHH", *([0]*6))
    return hdr

shdr = mk_sample_hdr("LEAD", s1) + mk_sample_hdr("BASS", s2)

def mk_pattern(row_data, rows=64):
    out = b""
    for i in range(rows):
        rd = row_data[i % len(row_data)]
        for ch in range(4):
            val = rd[ch] if ch < len(rd) else 0
            inst = rd[ch+1] if ch+1 < len(rd) else 1
            out += struct.pack("<BBH", val, inst, 0)
    return out

p0 = mk_pattern([12,1,0,2,24,1,36,2] * 8)
p1 = mk_pattern([24,2] * 16)
p2 = mk_pattern([36,1,12,1,48,1,60,1] * 8)
p3 = mk_pattern([12,1,24,1,36,1,48,1] * 8)

patterns = p0 + p1 + p2 + p3
order = [0,1,2,3] + [0]*28

with open("/workspace/submission/tune.xm", "wb") as f:
    f.write(MAGIC)
    f.write(struct.pack("<H", len(shdr)))
    f.write(struct.pack("<HHHHHHH", NUM_SAMPLES, NUM_PATTERNS, ORDER_LEN, 1, TEMPO, BPM, 0))
    f.write(struct.pack("<H", 0))
    f.write(struct.pack("<H", 0))
    f.write(struct.pack("<BB", 0, 0))
    f.write(struct.pack("<B", 0))
    f.write(struct.pack("<BBB", 0, 0, 0))
    f.write(struct.pack("<H", 0))
    f.write(struct.pack("<HHHH", 0, 0, 0, 0))
    f.write(shdr)
    f.write(struct.pack("<H", NUM_PATTERNS))
    f.write(struct.pack("<H", 0))
    for i in range(NUM_PATTERNS):
        f.write(struct.pack("<HH", 64, 0))
    f.write(patterns)
    f.write(struct.pack("<" + "B" * ORDER_LEN, *order))
print("XM created")

