#!/usr/bin/env python3
"""Keygen Sunrise — balanced rebuild."""
import json, subprocess

def ft2_call(name, args):
    r = subprocess.run(["ft2", "call", name, json.dumps(args)], capture_output=True, text=True)
    if r.returncode != 0:
        print("ERR", name, args, r.stdout, r.stderr)
        raise SystemExit(1)
    out = r.stdout.strip()
    if out:
        try: return json.loads(out)
        except Exception: return out
    return None

def ft2_batch(calls):
    CHUNK = 350
    for i in range(0, len(calls), CHUNK):
        chunk = calls[i:i+CHUNK]
        path = f"/tmp/ft2b_{i}.json"
        with open(path, "w") as f:
            json.dump(chunk, f)
        r = subprocess.run(["ft2", "batch", path], capture_output=True, text=True)
        if r.returncode != 0:
            print("BATCH ERR", i, r.stdout[-800:], (r.stderr or "")[-800:])
            raise SystemExit(1)
        print(f"  batch {i//CHUNK}: {len(chunk)} ok")

NOTE = ["C-","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-"]
def ns(midi):
    return f"{NOTE[midi%12]}{midi//12 - 1}"

BASS, BPL, LEAD, LEAD2, ARP, PAD = 1, 2, 3, 4, 5, 6
KICK, SNARE, HAT, HATO, TOM, FX = 7, 8, 9, 10, 11, 12

print("New module...")
ft2_call("module_new", {"channels": 10, "name": "Keygen Sunrise"})
ft2_call("song_set", {
    "name": "Keygen Sunrise",
    "bpm": 142,
    "speed": 3,
    "length": 12,
    "loop_start": 0,
})

# Better balance: quieter bass, louder leads/arps, pan spread
# channels: 0 kick/snare, 1 hats, 2 bass, 3 arp, 4 lead, 5 harm, 6 pad, 7 fx/tom, 8 lead octave/echo, 9 arp2
samples = [
    (1, "bass.wav", "Bass Saw", 32, 128),
    (2, "bass_pluck.wav", "Bass Pluck", 28, 128),
    (3, "lead.wav", "Lead Pulse", 62, 180),
    (4, "lead2.wav", "Lead Soft", 52, 60),
    (5, "arp.wav", "Arp Pluck", 54, 35),
    (6, "pad.wav", "Pad Soft", 28, 128),
    (7, "kick.wav", "Kick", 50, 128),
    (8, "snare.wav", "Snare", 48, 128),
    (9, "hat.wav", "Hat Closed", 40, 210),
    (10, "hat_open.wav", "Hat Open", 34, 35),
    (11, "tom.wav", "Tom", 40, 90),
    (12, "fx_up.wav", "FX Riser", 36, 128),
]

for inst, fname, name, vol, pan in samples:
    path = f"/workspace/samples/{fname}"
    ft2_call("sample_load", {"path": path, "instrument": inst, "sample": 0})
    ft2_call("instrument_set", {"instrument": inst, "name": name})
    ft2_call("sample_set", {
        "instrument": inst, "sample": 0, "name": name[:22],
        "volume": vol, "panning": pan,
    })

A2,B2,C3,D3,E3,F3,G3 = 45,47,48,50,52,53,55
A3,B3,C4,D4,E4,F4,G4 = 57,59,60,62,64,65,67
A4,B4,C5,D5,E5,F5,G5 = 69,71,72,74,76,77,79
A5,B5,C6 = 81,83,84
G2,E2,F2 = 43,40,41

PROG_A = [(0, A2), (16, F2), (32, C3), (48, G2)]
PROG_B = [(0, A2), (16, G2), (32, F2), (48, E2)]
PROG_C = [(0, A2), (16, C3), (32, F2), (48, G2)]

CHORDS_A = [(0,'Am'),(16,'F'),(32,'C'),(48,'G')]
CHORDS_B = [(0,'Am'),(16,'G'),(32,'F'),(48,'E')]
CHORDS_C = [(0,'Am'),(16,'C'),(32,'F'),(48,'G')]
CHORDS_BR = [(0,'Am'),(16,'Am'),(32,'F'),(48,'G')]

calls = []

def cell(p, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    d = {"pattern": p, "row": row, "channel": ch}
    if note is not None:
        d["note"] = note if isinstance(note, str) else ns(note)
    if ins is not None: d["instrument"] = ins
    if vol is not None: d["volume"] = vol
    if fx is not None: d["effect"] = fx
    if fp is not None: d["effect_param"] = fp
    calls.append({"name": "pattern_set_cell", "arguments": d})

def set_len(p, rows):
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": rows}})

def clear(p):
    calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})

def drums_basic(p, rows=64, open_hats=False, fill_at=None, ghost=False):
    for r in range(0, rows, 4):
        if (r % 8) == 4:
            cell(p, r, 0, note="C-4", ins=SNARE, vol=52)
        else:
            cell(p, r, 0, note="C-4", ins=KICK, vol=58)
    for r in range(0, rows, 16):
        if r+6 < rows:
            cell(p, r+6, 0, note="C-4", ins=KICK, vol=44)
        if r+10 < rows:
            cell(p, r+10, 0, note="C-4", ins=KICK, vol=40)
    for r in range(0, rows, 2):
        if r % 8 == 6 and open_hats:
            cell(p, r, 1, note="C-4", ins=HATO, vol=30)
        else:
            v = 32 if r % 4 == 0 else 20
            # swing-ish alternate pan via volume?
            cell(p, r, 1, note="C-4", ins=HAT, vol=v)
    if ghost:
        for r in range(0, rows, 16):
            if r+11 < rows: cell(p, r+11, 0, note="C-4", ins=SNARE, vol=18)
            if r+13 < rows: cell(p, r+13, 0, note="C-4", ins=SNARE, vol=12)
    if fill_at is not None:
        r0 = fill_at
        for off, nmidi, v in [(0, 64, 48), (1, 60, 42), (2, 57, 46), (3, 53, 50)]:
            if r0+off < rows:
                cell(p, r0+off, 7, note=ns(nmidi), ins=TOM, vol=v)
        if r0+4 < rows:
            cell(p, r0+4, 0, note="C-4", ins=SNARE, vol=58)

def drums_half(p, rows=64):
    for r in range(0, rows, 8):
        cell(p, r, 0, note="C-4", ins=KICK, vol=44)
    for r in range(4, rows, 8):
        cell(p, r, 0, note="C-4", ins=SNARE, vol=34)
    for r in range(0, rows, 4):
        cell(p, r, 1, note="C-4", ins=HAT, vol=18)

def drums_break(p, rows=64):
    for r in [0, 24, 32, 48]:
        cell(p, r, 0, note="C-4", ins=KICK, vol=48)
    for r in [16, 40, 56]:
        cell(p, r, 0, note="C-4", ins=SNARE, vol=38)
    for r in range(0, rows, 8):
        cell(p, r+6, 1, note="C-4", ins=HATO, vol=24)

def place_bass(p, prog, style="drive"):
    for i, (start, note) in enumerate(prog):
        end = prog[i+1][0] if i+1 < len(prog) else 64
        if style == "drive":
            # classic keygen gallop-ish
            offs = [0, 3, 6, 8, 11, 12, 14]
            for base in range(start, end, 16):
                for off in offs:
                    r = base + off
                    if r >= end: break
                    n = note + (12 if off in (8, 14) else 0)
                    ins = BASS if off in (0, 8) else BPL
                    v = 44 if off == 0 else (36 if off in (6, 8) else 28)
                    cell(p, r, 2, note=ns(n), ins=ins, vol=v)
        elif style == "simple":
            for r in range(start, end, 4):
                cell(p, r, 2, note=ns(note), ins=BASS, vol=36)
        elif style == "walk":
            walk = [0, 0, 7, 5, 0, -2, 0, 3]
            for j, r in enumerate(range(start, end, 2)):
                n = note + walk[j % len(walk)]
                cell(p, r, 2, note=ns(n), ins=BPL if j%2 else BASS, vol=30 if j%2 else 40)

def arp_notes(chord):
    return {
        'Am': [A3, C4, E4, A4],
        'F':  [F3, A3, C4, F4],
        'C':  [C4, E4, G4, C5],
        'G':  [G3, B3, D4, G4],
        'Em': [E3, G3, B3, E4],
        'E':  [E3, 56, B3, E4],
        'Dm': [D3, F3, A3, D4],
    }[chord]

def place_arp(p, chords, rows=64, rate=1, vol=42, oct_up=False, ch=3):
    for i, (start, chname) in enumerate(chords):
        end = chords[i+1][0] if i+1 < len(chords) else rows
        notes = arp_notes(chname)
        if oct_up:
            notes = [n+12 for n in notes]
        base = notes + [notes[1], notes[2], notes[3], notes[2]]
        idx = 0
        for r in range(start, end, rate):
            n = base[idx % len(base)]
            if (idx % 16) == 8:
                n = notes[-1] + (0 if oct_up else 12)
            v = vol + (6 if (r % 4 == 0) else 0)
            cell(p, r, ch, note=ns(n), ins=ARP, vol=min(v, 60))
            idx += 1

def place_arp_mirror(p, chords, rows=64, rate=2, vol=28, ch=9):
    """Second arp channel, offset inverted for width"""
    for i, (start, chname) in enumerate(chords):
        end = chords[i+1][0] if i+1 < len(chords) else rows
        notes = list(reversed(arp_notes(chname)))
        idx = 0
        for r in range(start + 1, end, rate):  # offset by 1
            n = notes[idx % len(notes)] + 12
            cell(p, r, ch, note=ns(n), ins=ARP, vol=vol)
            idx += 1

def place_pad(p, chords, rows=64, vol=28):
    tones = {
        'Am': (A3, C4, E4),
        'F': (F3, A3, C4),
        'C': (C4, E4, G4),
        'G': (G3, B3, D4),
        'E': (E3, 56, B3),
        'Em': (E3, G3, B3),
        'Dm': (D3, F3, A3),
    }
    for i, (start, chname) in enumerate(chords):
        t = tones[chname]
        cell(p, start, 6, note=ns(t[1]), ins=PAD, vol=vol)
        if start + 8 < rows:
            cell(p, start + 8, 6, note=ns(t[0] + 12), ins=PAD, vol=max(vol - 6, 12))

def melody_a(p, ch=4, ins=LEAD, vol=52):
    ph = []
    ph += [(0, A4), (2, C5), (4, E5), (6, C5), (8, B4), (10, A4), (12, E4), (14, A4)]
    ph += [(16, A4), (18, C5), (20, F5), (22, E5), (24, D5), (26, C5), (28, A4), (30, F4)]
    ph += [(32, G4), (34, C5), (36, E5), (38, G5), (40, E5), (42, D5), (44, C5), (46, E4)]
    ph += [(48, D5), (50, B4), (52, G4), (54, B4), (56, D5), (58, E5), (60, D5), (62, B4)]
    for r, n in ph:
        cell(p, r, ch, note=ns(n), ins=ins, vol=vol)

def melody_a_harm(p, ch=5, ins=LEAD2, vol=36):
    ph = []
    ph += [(0, E4), (2, A4), (4, C5), (6, A4), (8, G4), (10, E4), (12, C4), (14, E4)]
    ph += [(16, F4), (18, A4), (20, C5), (22, C5), (24, A4), (26, A4), (28, F4), (30, C4)]
    ph += [(32, E4), (34, G4), (36, C5), (38, E5), (40, C5), (42, B4), (44, G4), (46, C4)]
    ph += [(48, B4), (50, G4), (52, D4), (54, G4), (56, B4), (58, C5), (60, B4), (62, G4)]
    for r, n in ph:
        cell(p, r, ch, note=ns(n), ins=ins, vol=vol)

def melody_a_echo(p, ch=8, ins=LEAD2, vol=22, delay=3):
    ph = []
    ph += [(0, A4), (2, C5), (4, E5), (6, C5), (8, B4), (10, A4), (12, E4), (14, A4)]
    ph += [(16, A4), (18, C5), (20, F5), (22, E5), (24, D5), (26, C5), (28, A4), (30, F4)]
    ph += [(32, G4), (34, C5), (36, E5), (38, G5), (40, E5), (42, D5), (44, C5), (46, E4)]
    ph += [(48, D5), (50, B4), (52, G4), (54, B4), (56, D5), (58, E5), (60, D5), (62, B4)]
    for r, n in ph:
        rr = r + delay
        if rr < 64:
            cell(p, rr, ch, note=ns(n), ins=ins, vol=vol)

def melody_b(p, ch=4, ins=LEAD, vol=54):
    ph = []
    ph += [(0, A4), (2, B4), (4, C5), (6, E5), (8, A5), (10, E5), (12, C5), (14, A4)]
    ph += [(16, G4), (18, B4), (20, D5), (22, G5), (24, D5), (26, B4), (28, G4), (30, D4)]
    ph += [(32, F5), (34, E5), (36, D5), (38, C5), (40, A4), (42, F4), (44, A4), (46, C5)]
    ph += [(48, B4), (50, E5), (52, G5), (54, F5), (56, E5), (58, D5), (60, B4), (62, E4)]
    for r, n in ph:
        cell(p, r, ch, note=ns(n), ins=ins, vol=vol)

def melody_b_harm(p, ch=5, ins=LEAD2, vol=38):
    ph = []
    ph += [(0, E4), (2, G4), (4, A4), (6, C5), (8, E5), (10, C5), (12, A4), (14, E4)]
    ph += [(16, D4), (18, G4), (20, B4), (22, D5), (24, B4), (26, G4), (28, D4), (30, B3)]
    ph += [(32, C5), (34, C5), (36, A4), (38, A4), (40, F4), (42, C4), (44, F4), (46, A4)]
    ph += [(48, G4), (50, B4), (52, E5), (54, D5), (56, B4), (58, B4), (60, G4), (62, B3)]
    for r, n in ph:
        cell(p, r, ch, note=ns(n), ins=ins, vol=vol)

def melody_b_echo(p, ch=8, ins=LEAD, vol=20, delay=2):
    ph = [(0,A4),(4,C5),(8,A5),(12,C5),(16,G4),(20,D5),(24,D5),(28,G4),
          (32,F5),(36,D5),(40,A4),(44,A4),(48,B4),(52,G5),(56,E5),(60,B4)]
    for r, n in ph:
        rr = r + delay
        if rr < 64:
            cell(p, rr, ch, note=ns(n + 12), ins=ins, vol=vol)

def melody_bridge(p):
    ph = [
        (0, A4), (4, A4), (8, C5), (12, E5),
        (16, E5), (20, D5), (24, C5), (28, B4),
        (32, A4), (36, F4), (40, A4), (44, C5),
        (48, B4), (52, G4), (56, B4), (60, D5),
    ]
    for r, n in ph:
        cell(p, r, 4, note=ns(n), ins=LEAD, vol=48)
        if r + 2 < 64:
            cell(p, r + 2, 5, note=ns(n - 12), ins=LEAD2, vol=30)
        if r + 4 < 64:
            cell(p, r + 4, 8, note=ns(n), ins=LEAD2, vol=18)

def lead_intro(p):
    ph = [(8, A4), (16, C5), (24, E5), (32, A4), (40, G4), (48, E4), (56, A4)]
    for r, n in ph:
        cell(p, r, 4, note=ns(n), ins=LEAD2, vol=40)
        if r + 2 < 64:
            cell(p, r + 2, 8, note=ns(n), ins=LEAD2, vol=18)

# Patterns
for p in range(12):
    clear(p)
    set_len(p, 64)

# P0 Intro — soft, airy
place_pad(0, CHORDS_A, vol=24)
place_arp(0, CHORDS_A, rate=2, vol=24)
place_arp_mirror(0, CHORDS_A, rate=2, vol=16)
lead_intro(0)
for start, note in PROG_A:
    cell(0, start, 2, note=ns(note), ins=BASS, vol=24)
    cell(0, start + 8, 2, note=ns(note), ins=BPL, vol=16)

# P1 build-in
drums_half(1)
place_pad(1, CHORDS_A, vol=26)
place_arp(1, CHORDS_A, rate=2, vol=32)
place_arp_mirror(1, CHORDS_A, rate=2, vol=18)
place_bass(1, PROG_A, style="simple")
for r, n in [(0, A4), (8, E5), (16, A4), (24, F5), (32, G5), (40, E5), (48, D5), (56, B4)]:
    cell(1, r, 4, note=ns(n), ins=LEAD, vol=44)
    cell(1, r + 2, 8, note=ns(n), ins=LEAD2, vol=20)
cell(1, 56, 7, note="C-5", ins=FX, vol=40)

# P2 Main A
drums_basic(2, open_hats=True, ghost=True)
place_bass(2, PROG_A, style="drive")
place_arp(2, CHORDS_A, rate=1, vol=40)
place_arp_mirror(2, CHORDS_A, rate=2, vol=24)
place_pad(2, CHORDS_A, vol=24)
melody_a(2, vol=52)
melody_a_harm(2, vol=34)
melody_a_echo(2, vol=20)

# P3 Main A var — higher arp
drums_basic(3, open_hats=True, ghost=True, fill_at=60)
place_bass(3, PROG_A, style="drive")
place_arp(3, CHORDS_A, rate=1, vol=42, oct_up=True)
place_arp_mirror(3, CHORDS_A, rate=1, vol=22)
place_pad(3, CHORDS_A, vol=22)
melody_a(3, vol=54)
melody_a_harm(3, vol=36)
melody_a_echo(3, vol=22, delay=2)
for r, n in [(15, A5), (31, A5), (47, G5)]:
    cell(3, r, 8, note=ns(n), ins=LEAD, vol=32)
cell(3, 58, 7, note="C-5", ins=FX, vol=36)

# P4 Main B
drums_basic(4, open_hats=True, ghost=True)
place_bass(4, PROG_B, style="drive")
place_arp(4, CHORDS_B, rate=1, vol=42)
place_arp_mirror(4, CHORDS_B, rate=2, vol=24)
place_pad(4, CHORDS_B, vol=24)
melody_b(4, vol=54)
melody_b_harm(4, vol=36)
melody_b_echo(4, vol=20)

# P5 Main B big
drums_basic(5, open_hats=True, ghost=True, fill_at=56)
place_bass(5, PROG_B, style="walk")
place_arp(5, CHORDS_B, rate=1, vol=44, oct_up=True)
place_arp_mirror(5, CHORDS_B, rate=1, vol=26)
place_pad(5, CHORDS_B, vol=26)
melody_b(5, vol=56)
melody_b_harm(5, vol=38)
melody_b_echo(5, vol=24)
for r in [0, 16, 32, 48]:
    cell(5, r + 7, 7, note="D-4", ins=TOM, vol=28)

# P6 Break
drums_break(6)
place_pad(6, CHORDS_BR, vol=30)
place_arp(6, CHORDS_BR, rate=2, vol=28)
for start, note in [(0, A2), (16, A2), (32, F2), (48, G2)]:
    cell(6, start, 2, note=ns(note), ins=BASS, vol=34)
melody_bridge(6)
cell(6, 48, 7, note="G-4", ins=FX, vol=44)

# P7 Build
drums_basic(7, open_hats=False)
for r in range(32, 64):
    cell(7, r, 1, note="C-4", ins=HAT, vol=min(42, 12 + (r - 32)))
place_bass(7, PROG_A, style="drive")
place_arp(7, CHORDS_A, rate=1, vol=34)
place_pad(7, CHORDS_A, vol=20)
stabs = [(0,A4),(4,A4),(8,C5),(12,E5),(16,A4),(18,C5),(20,E5),(22,A5),
         (24,A5),(26,E5),(28,C5),(30,A4),
         (32,C5),(34,E5),(36,G5),(38,A5),(40,C6),(44,A5),(48,G5),(52,E5),(56,D5),(60,E5)]
for r, n in stabs:
    cell(7, r, 4, note=ns(n), ins=LEAD, vol=46 if r < 32 else 54)
    if r + 1 < 64:
        cell(7, r + 1, 8, note=ns(n), ins=LEAD2, vol=22)
cell(7, 60, 7, note="C-5", ins=FX, vol=50)
for r in range(60, 64):
    cell(7, r, 0, note="C-4", ins=SNARE, vol=30 + (r - 60) * 8)

# P8 Main A peak
drums_basic(8, open_hats=True, ghost=True)
place_bass(8, PROG_A, style="drive")
place_arp(8, CHORDS_A, rate=1, vol=44, oct_up=True)
place_arp_mirror(8, CHORDS_A, rate=1, vol=26)
place_pad(8, CHORDS_A, vol=26)
melody_a(8, vol=56)
melody_a_harm(8, vol=40)
melody_a_echo(8, vol=24)
for r in [0, 16, 32, 48]:
    cell(8, r, 7, note=ns(A5), ins=LEAD, vol=28)

# P9 Main B peak
drums_basic(9, open_hats=True, ghost=True, fill_at=60)
place_bass(9, PROG_B, style="drive")
place_arp(9, CHORDS_B, rate=1, vol=46, oct_up=True)
place_arp_mirror(9, CHORDS_B, rate=1, vol=28)
place_pad(9, CHORDS_B, vol=26)
melody_b(9, vol=58)
melody_b_harm(9, vol=42)
melody_b_echo(9, vol=26)

# P10 Cool down
drums_basic(10, open_hats=True)
place_bass(10, PROG_C, style="drive")
place_arp(10, CHORDS_C, rate=1, vol=36)
place_arp_mirror(10, CHORDS_C, rate=2, vol=20)
place_pad(10, CHORDS_C, vol=24)
melody_a(10, vol=44, ins=LEAD2)
melody_a_harm(10, vol=30, ins=LEAD2)
melody_a_echo(10, vol=16, delay=4)

# P11 Turnaround — settle into intro energy for clean loop
drums_basic(11, open_hats=False, fill_at=44)
# fade drum intensity after fill by quiet hats only
for r in range(52, 64, 2):
    cell(11, r, 1, note="C-4", ins=HAT, vol=12)
cell(11, 56, 0, note="C-4", ins=KICK, vol=28)
place_bass(11, PROG_A, style="simple")
# quieter bass late
for r in range(48, 64, 4):
    cell(11, r, 2, note=ns(A2), ins=BASS, vol=22)
place_arp(11, CHORDS_A, rate=2, vol=28)
place_pad(11, CHORDS_A, vol=22)
close = [(0,A5),(4,E5),(8,C5),(12,A4),(16,G4),(20,E4),(24,A4),(28,C5),
         (32,E5),(36,D5),(40,C5),(44,B4),(48,A4),(52,E4),(56,A3)]
for r, n in close:
    cell(11, r, 4, note=ns(n), ins=LEAD, vol=46 if r < 44 else 28)
    if r + 3 < 64 and r < 48:
        cell(11, r + 3, 8, note=ns(n), ins=LEAD2, vol=16)
cell(11, 56, 6, note=ns(A3), ins=PAD, vol=18)
cell(11, 58, 1, note="C-4", ins=HATO, vol=14)

for pos in range(12):
    calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pos}})

calls.append({"name": "song_set", "arguments": {
    "name": "Keygen Sunrise",
    "bpm": 142,
    "speed": 3,
    "length": 12,
    "loop_start": 0,
}})

print(f"calls={len(calls)}")
ft2_batch(calls)
print(ft2_call("module_info", {}))
ft2_call("module_save", {"path": "/workspace/submission/tune.xm", "format": "xm"})
print("saved")
