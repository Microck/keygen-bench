#!/usr/bin/env python3
"""Compose a looping keygen-style XM via ft2 tracker tools."""
import json, os

SAMP = "/workspace/samples"

def b64(name):
    with open(f"{SAMP}/{name}.b64") as f:
        return f.read()

CH_KICK, CH_SNR, CH_HAT, CH_BASS = 0, 1, 2, 3
CH_ARP, CH_LEAD, CH_PAD, CH_ECHO = 4, 5, 6, 7
CH_HARM, CH_CRASH = 8, 9

I_KICK, I_SNR, I_HATC, I_HATO, I_CLAP = 1, 2, 3, 4, 5
I_TOM, I_CRASH, I_BASS, I_LEAD, I_LEAD2 = 6, 7, 8, 9, 10
I_PAD, I_PLUCK, I_BELL, I_SHAK = 11, 12, 13, 14

calls = []

def add(tool, **kw):
    calls.append({"name": tool, "arguments": kw})

def cell(p, r, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    a = {"pattern": int(p), "row": int(r), "channel": int(ch)}
    if note is not None:
        a["note"] = note
    if ins is not None:
        a["instrument"] = int(ins)
    if vol is not None:
        a["volume"] = int(vol)
    if fx is not None:
        a["effect"] = int(fx)
    if fp is not None:
        a["effect_param"] = int(fp)
    calls.append({"name": "pattern_set_cell", "arguments": a})

add("module_new", channels=10, name="until next patch")

# sample default pan 128 = center. We'll pan in the pattern.
drums = [
    (I_KICK, "kick", 64, 128, False, 0),
    (I_SNR, "snare", 54, 128, False, 0),
    (I_HATC, "hatc", 64, 128, False, 0),
    (I_HATO, "hato", 52, 128, False, 0),
    (I_CLAP, "clap", 50, 128, False, 0),
    (I_TOM, "tom", 50, 128, False, 0),
    (I_CRASH, "crash", 36, 128, False, 0),
]
# 128-sample @ 8363 Hz ≈ C2 at C-4.
# bass rel+12 => C3 at C-4; lead rel+24 => C4 at C-4.
tonal = [
    (I_BASS, "bass", 44, 128, True, 12),
    (I_LEAD, "lead", 40, 118, True, 24),   # slightly left
    (I_LEAD2, "lead2", 32, 138, True, 24),  # slightly right
    (I_PAD, "pad", 28, 128, True, 12),
    (I_PLUCK, "pluck", 46, 128, False, 0),
    (I_BELL, "bell", 30, 128, False, 12),
    (I_SHAK, "shaker", 40, 128, False, 0),
]

for ins, name, vol, pan, loop, rel in drums + tonal:
    add("sample_create_from_pcm", instrument=ins, sample=0, pcm=b64(name),
        encoding="int16", name=name)
    flags = 17 if loop else 16
    add("sample_set", instrument=ins, sample=0, name=name, volume=vol,
        panning=pan, finetune=0, relative_note=rel, flags=flags,
        loop_start=0, loop_length=(128 if loop else 0))
    add("instrument_set", instrument=ins, name=name)

N_PAT = 8
add("song_set", name="until next patch", bpm=140, speed=6,
    length=N_PAT, loop_start=1, channels=10)
for i in range(N_PAT):
    add("order_set", position=i, pattern=i)
    add("pattern_set_length", pattern=i, rows=64)

ANDALUSIAN = [
    ("A-3", "A-4", ["A-4", "C-5", "E-5", "A-5"], "A-4", 0x37),
    ("G-3", "G-4", ["G-4", "B-4", "D-5", "G-5"], "G-4", 0x47),
    ("F-3", "F-4", ["F-4", "A-4", "C-5", "F-5"], "F-4", 0x47),
    ("E-3", "E-4", ["E-4", "G#4", "B-4", "E-5"], "E-4", 0x47),
]
CHORUS = [
    ("A-3", "A-4", ["A-4", "C-5", "E-5", "A-5"], "A-4", 0x37),
    ("F-3", "F-4", ["F-4", "A-4", "C-5", "F-5"], "F-4", 0x47),
    ("C-3", "C-4", ["C-5", "E-5", "G-5", "C-6"], "C-4", 0x47),
    ("G-3", "G-4", ["G-4", "B-4", "D-5", "G-5"], "G-4", 0x47),
]
HOLD_AM = [
    ("A-3", "A-4", ["A-4", "C-5", "E-5", "A-5"], "A-4", 0x37),
    ("A-3", "E-4", ["A-4", "C-5", "E-5", "G-5"], "A-4", 0x37),
    ("F-3", "F-4", ["F-4", "A-4", "C-5", "E-5"], "F-4", 0x47),
    ("G-3", "G-4", ["G-4", "B-4", "D-5", "F-5"], "G-4", 0x47),
]
FIFTH = {
    "A-3": "E-4", "G-3": "D-4", "F-3": "C-4", "E-3": "B-3", "C-3": "G-3",
}


def drums_groove(p, variant="verse"):
    for r in range(64):
        beat = r % 16
        bar = r // 16

        kick_hits = set()
        if variant == "sparse":
            if beat == 0:
                kick_hits.add(0)
            if beat == 8 and bar % 2 == 0:
                kick_hits.add(8)
        elif variant == "break":
            if bar < 3:
                kick_hits |= {0, 8}
            else:
                kick_hits |= {0, 4, 8, 10, 12, 14}
        elif variant == "build":
            if bar < 2:
                kick_hits |= {0, 8}
            elif bar == 2:
                kick_hits |= {0, 4, 8, 12, 14}
            else:
                kick_hits |= {0, 2, 4, 6, 8, 10, 12, 14}
        else:
            kick_hits |= {0, 8}
            if beat == 6:
                kick_hits.add(6)
            if beat == 14 and bar % 2 == 1:
                kick_hits.add(14)

        if beat in kick_hits:
            vol = 64 if beat in (0, 8) else 46
            if variant == "build" and bar == 3:
                vol = 52
            cell(p, r, CH_KICK, note="C-4", ins=I_KICK, vol=vol)

        filling = False
        if variant in ("verse", "chorus") and r in (60, 61, 62, 63):
            filling = True
        if variant == "climax" and r in (56, 58, 60, 61, 62, 63):
            filling = True
        if variant == "build" and r in (60, 61, 62, 63):
            filling = True

        if not filling:
            if variant == "break" and bar >= 2:
                if beat in (4, 12):
                    cell(p, r, CH_SNR, note="C-4", ins=I_SNR, vol=40, fx=8, fp=0x90)
            elif variant == "build" and bar == 3:
                if beat % 2 == 0:
                    cell(p, r, CH_SNR, note="C-4", ins=I_SNR, vol=22 + beat, fx=8, fp=0x98)
            else:
                if beat == 4:
                    cell(p, r, CH_SNR, note="C-4", ins=I_SNR, vol=52, fx=8, fp=0x88)
                elif beat == 12:
                    cell(p, r, CH_SNR, note="C-4", ins=I_CLAP, vol=46, fx=8, fp=0xB8)
                elif variant in ("verse", "chorus", "climax") and beat == 10 and bar % 2 == 1:
                    cell(p, r, CH_SNR, note="C-4", ins=I_SNR, vol=16, fx=8, fp=0x70)
                elif variant in ("chorus", "climax") and beat == 7 and bar == 1:
                    cell(p, r, CH_SNR, note="C-4", ins=I_SNR, vol=14, fx=8, fp=0x60)

        # hats: play a fifth up for extra brightness
        if variant == "sparse":
            if beat % 8 == 4:
                cell(p, r, CH_HAT, note="C-5", ins=I_HATC, vol=32, fx=8,
                     fp=0x28 + (r * 5) % 0xB0)
        elif variant == "break":
            if r % 2 == 0:
                pan = 0x20 if (r // 2) % 2 == 0 else 0xD0
                cell(p, r, CH_HAT, note="C-5", ins=I_HATC, vol=30 + (r % 8),
                     fx=8, fp=pan)
            if beat == 14:
                cell(p, r, CH_HAT, note="C-5", ins=I_HATO, vol=38, fx=8, fp=0xC0)
        else:
            if r % 2 == 0:
                pan = 0x24 if (r // 2) % 2 == 0 else 0xCC
                v = 40 if beat % 4 == 2 else 34
                if beat % 4 == 2:
                    # swing the off-beat 8th by 1 tick
                    cell(p, r, CH_HAT, note="C-5", ins=I_HATC, vol=v, fx=0xE, fp=0xD1)
                else:
                    cell(p, r, CH_HAT, note="C-5", ins=I_HATC, vol=v, fx=8, fp=pan)
            if beat == 6:
                cell(p, r, CH_HAT, note="C-5", ins=I_HATO, vol=36, fx=8, fp=0xC4)
            if beat == 14 and bar % 2 == 0:
                cell(p, r, CH_HAT, note="C-5", ins=I_HATO, vol=38, fx=8, fp=0x2C)
            if variant in ("chorus", "climax") and r % 2 == 1:
                cell(p, r, CH_HAT, note="G-5", ins=I_SHAK, vol=26, fx=8,
                     fp=0x18 if r % 4 == 1 else 0xE8)

    if variant in ("verse", "chorus"):
        cell(p, 60, CH_SNR, note="A-4", ins=I_TOM, vol=38, fx=8, fp=0x40)
        cell(p, 61, CH_SNR, note="A-4", ins=I_TOM, vol=26, fx=8, fp=0x50)
        cell(p, 62, CH_SNR, note="F-4", ins=I_TOM, vol=44, fx=8, fp=0x30)
        cell(p, 63, CH_SNR, note="C-4", ins=I_SNR, vol=34, fx=8, fp=0x90)
    if variant == "climax":
        cell(p, 56, CH_SNR, note="C-5", ins=I_TOM, vol=32, fx=8, fp=0x60)
        cell(p, 58, CH_SNR, note="A-4", ins=I_TOM, vol=38, fx=8, fp=0x48)
        cell(p, 60, CH_SNR, note="F-4", ins=I_TOM, vol=44, fx=8, fp=0x30)
        cell(p, 61, CH_SNR, note="C-4", ins=I_SNR, vol=28)
        cell(p, 62, CH_SNR, note="C-4", ins=I_SNR, vol=44)
        cell(p, 63, CH_SNR, note="C-4", ins=I_CLAP, vol=50, fx=8, fp=0xC0)
    if variant == "build":
        cell(p, 60, CH_SNR, note="C-4", ins=I_SNR, vol=34, fx=0xE, fp=0x93)
        cell(p, 62, CH_SNR, note="C-4", ins=I_CLAP, vol=48)
        cell(p, 63, CH_SNR, note="C-4", ins=I_SNR, vol=38)

    crash_rows = set()
    if variant in ("chorus", "climax", "build"):
        cell(p, 0, CH_CRASH, note="C-4", ins=I_CRASH, vol=30)
        crash_rows.add(0)
    if variant == "build":
        cell(p, 32, CH_CRASH, note="C-4", ins=I_CRASH, vol=18)
        crash_rows.add(32)
    if variant == "sparse":
        cell(p, 0, CH_CRASH, note="C-4", ins=I_CRASH, vol=16)
        crash_rows.add(0)
    if variant == "verse" and p == 1:
        cell(p, 0, CH_CRASH, note="C-4", ins=I_CRASH, vol=14)
        crash_rows.add(0)

    # extra bright hat ticks on free crash-channel slots
    if variant not in ("sparse",):
        for r in range(64):
            if r in crash_rows:
                continue
            if r % 4 == 2:
                pan = 0x30 if (r // 4) % 2 == 0 else 0xC8
                cell(p, r, CH_CRASH, note="C-6", ins=I_HATC, vol=28, fx=8, fp=pan)


def bass_line(p, chords, extra="drive"):
    for bi, chd in enumerate(chords):
        base = bi * 16
        root, octu = chd[0], chd[1]
        fifth = FIFTH.get(root, octu)
        if extra == "syncop":
            seq = [
                (0, root, 54),
                (3, root, 28),
                (4, octu, 46),
                (6, fifth, 38),
                (8, root, 50),
                (11, root, 26),
                (12, octu, 44),
                (14, fifth, 40),
            ]
        elif extra == "minimal":
            seq = [(0, root, 42), (8, fifth, 32)]
        else:
            seq = [
                (0, root, 52),
                (2, root, 36),
                (4, octu, 48),
                (6, root, 32),
                (8, fifth, 46),
                (10, root, 32),
                (12, root, 42),
                (14, octu, 44),
            ]
        for off, note, vol in seq:
            fx = fp = None
            if extra == "drive" and off in (0, 8):
                fx, fp = 0xA, 0x01
            cell(p, base + off, CH_BASS, note=note, ins=I_BASS, vol=vol, fx=fx, fp=fp)
        if extra == "minimal":
            cell(p, base + 14, CH_BASS, note="off")


def arp_line(p, chords, density="full", vol_base=30):
    for bi, chd in enumerate(chords):
        notes = chd[2]
        base = bi * 16
        if density == "none":
            continue
        step = 1 if density == "full" else 2
        fade = [vol_base, vol_base - 8, vol_base - 2, vol_base - 10]
        for i in range(0, 16, step):
            n = notes[i % 4]
            v = fade[i % 4]
            if density == "half":
                v = max(12, v - 4)
            pan = 0x20 + ((i * 19) % 0xB8)
            cell(p, base + i, CH_ARP, note=n, ins=I_PLUCK, vol=max(12, v), fx=8, fp=pan)


def pad_line(p, chords, vol=22):
    for bi, chd in enumerate(chords):
        padn = chd[3]
        arpe = chd[4]
        base = bi * 16
        # slow pan around + arpeggio
        cell(p, base, CH_PAD, note=padn, ins=I_PAD, vol=vol, fx=0, fp=arpe)
        cell(p, base + 4, CH_PAD, fx=8, fp=0x40)
        cell(p, base + 10, CH_PAD, fx=8, fp=0xC0)
        cell(p, base + 15, CH_PAD, note="off")


# lead register: C-5 ≈ C5 sounding
THEME_A = {
    0:  ("E-5", 46, None, None),
    2:  ("A-5", 42, None, None),
    4:  ("C-6", 48, None, None),
    6:  ("B-5", 38, None, None),
    8:  ("A-5", 42, 4, 0x52),
    12: ("E-5", 34, None, None),
    14: ("G-5", 38, None, None),
    16: ("D-5", 42, None, None),
    18: ("G-5", 40, None, None),
    20: ("B-5", 48, None, None),
    22: ("A-5", 36, None, None),
    24: ("G-5", 40, 4, 0x52),
    28: ("D-5", 32, None, None),
    30: ("F-5", 38, None, None),
    32: ("C-5", 42, None, None),
    34: ("F-5", 40, None, None),
    36: ("A-5", 48, None, None),
    38: ("G-5", 36, None, None),
    40: ("F-5", 40, None, None),
    42: ("A-5", 36, None, None),
    44: ("C-6", 46, None, None),
    46: ("A-5", 34, None, None),
    48: ("G#5", 48, None, None),
    50: ("B-5", 42, None, None),
    52: ("E-6", 50, None, None),
    54: ("D-6", 38, None, None),
    56: ("B-5", 42, 4, 0x63),
    60: ("G#5", 36, None, None),
    62: ("E-5", 32, None, None),
}
HARM_A = {
    0: "C-5", 8: "C-5", 16: "B-4", 24: "B-4",
    32: "A-4", 40: "C-5", 48: "B-4", 56: "E-5",
}

THEME_A2 = {
    0:  ("A-5", 42, None, None),
    1:  ("B-5", 22, None, None),
    2:  ("C-6", 46, None, None),
    4:  ("E-6", 48, None, None),
    6:  ("C-6", 34, None, None),
    8:  ("B-5", 40, None, None),
    10: ("A-5", 34, None, None),
    12: ("G-5", 38, None, None),
    14: ("A-5", 42, 4, 0x51),
    16: ("B-5", 42, None, None),
    18: ("D-6", 46, None, None),
    20: ("G-6", 48, None, None),
    22: ("D-6", 34, None, None),
    24: ("B-5", 38, None, None),
    26: ("G-5", 32, None, None),
    28: ("A-5", 40, None, None),
    30: ("B-5", 36, None, None),
    32: ("C-6", 46, None, None),
    34: ("A-5", 34, None, None),
    36: ("F-5", 38, None, None),
    38: ("A-5", 42, None, None),
    40: ("C-6", 48, None, None),
    42: ("D-6", 38, None, None),
    44: ("C-6", 36, None, None),
    46: ("A-5", 32, None, None),
    48: ("B-5", 46, None, None),
    50: ("G#5", 36, None, None),
    52: ("E-5", 34, None, None),
    54: ("G#5", 40, None, None),
    56: ("B-5", 48, 4, 0x62),
    60: ("D-6", 38, None, None),
    62: ("E-6", 48, None, None),
}
HARM_A2 = {
    0: "E-5", 8: "E-5", 16: "D-5", 24: "D-5",
    32: "C-5", 40: "F-5", 48: "E-5", 56: "G#5",
}

THEME_B = {
    0:  ("E-6", 48, None, None),
    2:  ("C-6", 36, None, None),
    4:  ("A-5", 34, None, None),
    6:  ("C-6", 40, None, None),
    8:  ("E-6", 48, 4, 0x52),
    12: ("G-6", 44, None, None),
    14: ("E-6", 34, None, None),
    16: ("F-6", 48, None, None),
    18: ("C-6", 34, None, None),
    20: ("A-5", 36, None, None),
    22: ("C-6", 40, None, None),
    24: ("F-6", 44, None, None),
    26: ("E-6", 36, None, None),
    28: ("D-6", 38, None, None),
    30: ("C-6", 34, None, None),
    32: ("G-5", 38, None, None),
    34: ("C-6", 40, None, None),
    36: ("E-6", 48, None, None),
    38: ("G-6", 44, None, None),
    40: ("E-6", 38, 4, 0x52),
    44: ("C-6", 36, None, None),
    46: ("D-6", 40, None, None),
    48: ("B-5", 44, None, None),
    50: ("D-6", 38, None, None),
    52: ("G-6", 48, None, None),
    54: ("F-6", 38, None, None),
    56: ("D-6", 40, None, None),
    58: ("B-5", 34, None, None),
    60: ("G-5", 36, None, None),
    62: ("A-5", 46, None, None),
}
HARM_B = {
    0: "A-5", 8: "C-6", 16: "A-5", 24: "C-6",
    32: "E-5", 40: "G-5", 48: "D-5", 56: "G-5",
}

THEME_B2 = {
    0:  ("A-5", 42, None, None),
    2:  ("C-6", 38, None, None),
    4:  ("E-6", 46, None, None),
    6:  ("A-6", 50, None, None),
    8:  ("G-6", 42, None, None),
    10: ("E-6", 34, None, None),
    12: ("C-6", 36, None, None),
    14: ("E-6", 44, None, None),
    16: ("F-6", 46, None, None),
    18: ("A-6", 44, None, None),
    20: ("C-6", 38, None, None),
    22: ("A-6", 48, None, None),
    24: ("G-6", 40, 4, 0x52),
    28: ("F-6", 34, None, None),
    30: ("E-6", 38, None, None),
    32: ("E-6", 44, None, None),
    34: ("G-6", 42, None, None),
    36: ("C-6", 36, None, None),
    38: ("G-6", 46, None, None),
    40: ("E-6", 38, None, None),
    42: ("C-6", 32, None, None),
    44: ("D-6", 38, None, None),
    46: ("E-6", 40, None, None),
    48: ("G-6", 46, None, None),
    50: ("D-6", 34, None, None),
    52: ("B-5", 36, None, None),
    54: ("D-6", 40, None, None),
    56: ("G-6", 48, 4, 0x63),
    60: ("A-6", 42, None, None),
    62: ("G#6", 38, None, None),
}
HARM_B2 = {
    0: "E-5", 8: "C-6", 16: "C-6", 24: "A-5",
    32: "G-5", 40: "C-6", 48: "D-6", 56: "B-5",
}

THEME_BREAK = {
    0:  ("A-4", 30, 4, 0x62),
    8:  ("C-5", 26, 4, 0x62),
    16: ("E-5", 28, 4, 0x62),
    24: ("C-5", 24, 4, 0x62),
    32: ("F-4", 28, 4, 0x62),
    40: ("A-4", 24, None, None),
    48: ("G-4", 30, 4, 0x63),
    56: ("B-4", 28, None, None),
    60: ("D-5", 32, None, None),
    62: ("E-5", 38, None, None),
}

# quiet ostinato for groove-only patterns
def ostinato(p, chords, vol=20):
    for bi, chd in enumerate(chords):
        notes = chd[2]
        base = bi * 16
        # slower rising figure
        seq = [0, 4, 8, 12]
        for i, off in enumerate(seq):
            n = notes[i % 4]
            pan = 0x38 if i % 2 == 0 else 0xC0
            cell(p, base + off, CH_HARM, note=n, ins=I_LEAD2, vol=vol, fx=8, fp=pan)


def lead_line(p, theme, echo=True, echo_vol=12):
    occupied = set(theme.keys())
    for r, spec in theme.items():
        note, vol, fx, fp = spec
        cell(p, r, CH_LEAD, note=note, ins=I_LEAD, vol=vol, fx=fx, fp=fp)
        if echo:
            er = r + 3
            if er < 64 and er not in occupied:
                occupied.add(er)
                # milder right pan than before
                cell(p, er, CH_ECHO, note=note, ins=I_LEAD2, vol=echo_vol, fx=8, fp=0xB0)


def harm_line(p, mapping, vol=18):
    for r, note in mapping.items():
        cell(p, r, CH_HARM, note=note, ins=I_LEAD2, vol=vol, fx=4, fp=0x41)


def bells(p, items):
    for r, note, vol in items:
        cell(p, r, CH_ECHO, note=note, ins=I_BELL, vol=vol, fx=8, fp=0x30)


def cut_sustains(p, channels):
    for ch in channels:
        cell(p, 63, ch, note="off")


# ---------- patterns ----------
# P0 intro
drums_groove(0, "sparse")
bass_line(0, ANDALUSIAN, extra="minimal")
arp_line(0, ANDALUSIAN, density="half", vol_base=20)
pad_line(0, ANDALUSIAN, vol=18)
bells(0, [(0, "A-5", 20), (16, "E-5", 14), (32, "C-5", 16), (48, "G#5", 18)])
# lock BPM/speed on first row without wiping the kick
cell(0, 0, CH_KICK, note="C-4", ins=I_KICK, vol=64, fx=0xF, fp=0x8C)
cell(0, 1, CH_KICK, fx=0xF, fp=0x06)
cut_sustains(0, [CH_LEAD, CH_ECHO, CH_HARM, CH_PAD, CH_BASS])

THEME_WAIT = {
    0:  ("E-5", 24, 4, 0x62),
    16: ("D-5", 22, 4, 0x62),
    32: ("C-5", 22, 4, 0x62),
    48: ("B-4", 24, 4, 0x62),
    56: ("E-5", 26, None, None),
    60: ("A-4", 20, None, None),
}

# P1 groove (loop restart)
drums_groove(1, "verse")
bass_line(1, ANDALUSIAN, extra="drive")
arp_line(1, ANDALUSIAN, density="full", vol_base=32)
pad_line(1, ANDALUSIAN, vol=20)
ostinato(1, ANDALUSIAN, vol=16)
lead_line(1, THEME_WAIT, echo=False)
bells(1, [(8, "A-5", 16), (24, "G-5", 12), (40, "F-5", 14), (52, "E-5", 18)])

# P2 theme A
drums_groove(2, "verse")
bass_line(2, ANDALUSIAN, extra="drive")
arp_line(2, ANDALUSIAN, density="full", vol_base=26)
pad_line(2, ANDALUSIAN, vol=18)
lead_line(2, THEME_A, echo=True, echo_vol=12)
harm_line(2, HARM_A, vol=16)

# P3 theme A2
drums_groove(3, "verse")
bass_line(3, ANDALUSIAN, extra="syncop")
arp_line(3, ANDALUSIAN, density="full", vol_base=24)
pad_line(3, ANDALUSIAN, vol=16)
lead_line(3, THEME_A2, echo=True, echo_vol=12)
harm_line(3, HARM_A2, vol=16)

# P4 chorus
drums_groove(4, "chorus")
bass_line(4, CHORUS, extra="drive")
arp_line(4, CHORUS, density="full", vol_base=28)
pad_line(4, CHORUS, vol=22)
lead_line(4, THEME_B, echo=True, echo_vol=13)
harm_line(4, HARM_B, vol=18)

# P5 climax
drums_groove(5, "climax")
bass_line(5, CHORUS, extra="syncop")
arp_line(5, CHORUS, density="full", vol_base=26)
pad_line(5, CHORUS, vol=20)
lead_line(5, THEME_B2, echo=True, echo_vol=12)
harm_line(5, HARM_B2, vol=18)
cut_sustains(5, [CH_LEAD, CH_ECHO, CH_HARM])

# P6 break
drums_groove(6, "break")
bass_line(6, HOLD_AM, extra="minimal")
arp_line(6, HOLD_AM, density="half", vol_base=16)
pad_line(6, HOLD_AM, vol=14)
lead_line(6, THEME_BREAK, echo=False)
bells(6, [(4, "E-5", 22), (20, "A-5", 18), (36, "C-5", 16), (52, "B-4", 20)])
cell(6, 0, CH_HARM, note="A-4", ins=I_LEAD2, vol=14, fx=4, fp=0x61)
cell(6, 32, CH_HARM, note="F-4", ins=I_LEAD2, vol=12, fx=4, fp=0x61)
cell(6, 48, CH_HARM, note="G-4", ins=I_LEAD2, vol=14, fx=4, fp=0x61)
cut_sustains(6, [CH_LEAD, CH_ECHO, CH_HARM])

# P7 build, then loop to P1
drums_groove(7, "build")
bass_line(7, ANDALUSIAN, extra="drive")
arp_line(7, ANDALUSIAN, density="full", vol_base=30)
pad_line(7, ANDALUSIAN, vol=22)
lead_line(7, THEME_A, echo=True, echo_vol=10)
harm_line(7, HARM_A, vol=14)
cell(7, 56, CH_BASS, note="E-3", ins=I_BASS, vol=44)
cell(7, 57, CH_BASS, note="G-3", ins=I_BASS, vol=38)
cell(7, 58, CH_BASS, note="G#3", ins=I_BASS, vol=42)
cell(7, 59, CH_BASS, note="B-3", ins=I_BASS, vol=44)
cell(7, 60, CH_BASS, note="A-3", ins=I_BASS, vol=52)
cell(7, 62, CH_BASS, note="E-4", ins=I_BASS, vol=40)
cell(7, 63, CH_BASS, note="G-3", ins=I_BASS, vol=34)
cut_sustains(7, [CH_LEAD, CH_ECHO, CH_HARM, CH_PAD])

add("module_save", path="/workspace/submission/tune.xm", format="xm")
add("module_info")

out = "/workspace/src/batch_all.json"
with open(out, "w") as f:
    json.dump(calls, f)
print("calls", len(calls), "bytes", os.path.getsize(out))
