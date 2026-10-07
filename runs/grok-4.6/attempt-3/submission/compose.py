#!/usr/bin/env python3
"""CRACKINTRO.NFO — looping keygen XM. Builds a cell batch for ft2."""
import json
from collections import defaultdict

# Instruments
KICK, SNARE, HAT, OHAT, CLAP, TOM, CRASH, RIDE = 1, 2, 3, 4, 5, 6, 7, 8
BASS, SUB, LEAD, LEADSOFT, ARP, CHIP, PAD, ORGAN = 9, 10, 11, 12, 13, 14, 15, 16
TRI, PLUCK, BELL, ZAP, RISE, SQUARE, TICK = 17, 18, 19, 20, 21, 22, 23

# Channels
CH_KICK, CH_SNARE, CH_HAT, CH_BASS, CH_SUB = 0, 1, 2, 3, 4
CH_ARP, CH_LEAD, CH_PAD, CH_CHIP, CH_FX = 5, 6, 7, 8, 9
CH_SPARK, CH_ECHO = 10, 11  # pluck/bell/organ  |  clap/tick/harmony

OFF = "off"

# Arpeggio params
A037 = 0x37  # min
A047 = 0x47  # maj
A038 = 0x38  # min add8
A07A = 0x7A  # 5 + m7  (min7-ish)
A04B = 0x4B  # maj7-ish (4 + 11)

PROG = {
    "verse": [
        dict(root="A-2", oct="A-3", fifth="E-2", pad="A-4", arp="A-4", chip="E-5",
             pluck="A-5", bell="E-6", param=A037, kind="min"),
        dict(root="F-2", oct="F-3", fifth="C-3", pad="F-4", arp="F-4", chip="C-5",
             pluck="F-5", bell="A-5", param=A047, kind="maj"),
        dict(root="C-2", oct="C-3", fifth="G-2", pad="C-5", arp="C-5", chip="G-5",
             pluck="C-6", bell="E-6", param=A047, kind="maj"),
        dict(root="G-2", oct="G-3", fifth="D-3", pad="G-4", arp="G-4", chip="D-5",
             pluck="G-5", bell="B-5", param=A047, kind="maj"),
    ],
    "chorus": [
        dict(root="F-2", oct="F-3", fifth="C-3", pad="F-4", arp="F-4", chip="C-5",
             pluck="F-5", bell="A-5", param=A047, kind="maj"),
        dict(root="G-2", oct="G-3", fifth="D-3", pad="G-4", arp="G-4", chip="D-5",
             pluck="G-5", bell="B-5", param=A047, kind="maj"),
        dict(root="A-2", oct="A-3", fifth="E-2", pad="A-4", arp="A-4", chip="E-5",
             pluck="A-5", bell="C-6", param=A037, kind="min"),
        dict(root="C-2", oct="C-3", fifth="G-2", pad="C-5", arp="C-5", chip="G-5",
             pluck="C-6", bell="E-6", param=A047, kind="maj"),
    ],
    "dom": [
        dict(root="F-2", oct="F-3", fifth="C-3", pad="F-4", arp="F-4", chip="A-5",
             pluck="F-5", bell="E-6", param=A04B, kind="maj"),
        dict(root="G-2", oct="G-3", fifth="D-3", pad="G-4", arp="G-4", chip="B-5",
             pluck="G-5", bell="D-6", param=A047, kind="maj"),
        dict(root="E-2", oct="E-3", fifth="B-2", pad="E-4", arp="E-4", chip="G-5",
             pluck="E-5", bell="B-5", param=A037, kind="min"),
        dict(root="E-2", oct="E-3", fifth="B-2", pad="E-4", arp="E-4", chip="G#5",
             pluck="E-5", bell="G#5", param=A047, kind="maj"),
    ],
    "bridge": [
        dict(root="F-2", oct="F-3", fifth="C-3", pad="F-4", arp="F-4", chip="A-5",
             pluck="F-5", bell="A-5", param=A04B, kind="maj"),
        dict(root="E-2", oct="E-3", fifth="B-2", pad="E-4", arp="E-4", chip="G#5",
             pluck="E-5", bell="G#5", param=A047, kind="maj"),
        dict(root="A-2", oct="A-3", fifth="E-2", pad="A-4", arp="A-4", chip="E-5",
             pluck="A-5", bell="C-6", param=A037, kind="min"),
        dict(root="G-2", oct="G-3", fifth="D-3", pad="G-4", arp="G-4", chip="D-5",
             pluck="G-5", bell="B-5", param=A047, kind="maj"),
    ],
}

RUNS = {
    "A-4": ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "E-4",
            "A-4", "C-5", "E-5", "G-5", "A-5", "E-5", "C-5", "A-4"],
    "F-4": ["F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "C-4",
            "F-4", "A-4", "C-5", "E-5", "F-5", "C-5", "A-4", "F-4"],
    "C-5": ["C-5", "E-5", "G-5", "C-6", "G-5", "E-5", "C-5", "G-4",
            "C-5", "E-5", "G-5", "B-5", "C-6", "G-5", "E-5", "C-5"],
    "G-4": ["G-4", "B-4", "D-5", "G-5", "D-5", "B-4", "G-4", "D-4",
            "G-4", "B-4", "D-5", "F-5", "G-5", "D-5", "B-4", "G-4"],
    "E-4": ["E-4", "G-4", "B-4", "E-5", "B-4", "G-4", "E-4", "B-3",
            "E-4", "G#4", "B-4", "E-5", "B-4", "G#4", "E-5", "B-4"],
}


class Song:
    def __init__(self):
        self.cells = {}  # (p,r,ch) -> dict

    def put(self, p, r, ch, note=None, ins=None, vol=None, fx=None, fp=None):
        if r < 0 or r > 63:
            return
        key = (p, r, ch)
        cur = self.cells.get(key, {"pattern": p, "row": r, "channel": ch})
        if note is not None:
            cur["note"] = note
        if ins is not None:
            cur["instrument"] = ins
        if vol is not None:
            cur["volume"] = vol
        if fx is not None:
            cur["effect"] = fx
        if fp is not None:
            cur["effect_param"] = fp
        self.cells[key] = cur

    def dump(self):
        return sorted(self.cells.values(), key=lambda d: (d["pattern"], d["row"], d["channel"]))


S = Song()


def drums(p, kind="verse"):
    """kind: intro, verse, chorus, climax, break, fill"""
    for bar in range(4):
        b = bar * 16
        last = bar == 3
        # --- hats / ride ---
        if kind == "intro":
            if bar >= 1:
                step = 4 if bar == 1 else 2
                for off in range(0, 16, step):
                    v = 20 if off % 4 == 0 else 12
                    if bar >= 2:
                        v += 6
                    S.put(p, b + off, CH_HAT, "F#5", HAT, vol=v)
                if bar == 3:
                    S.put(p, b + 12, CH_HAT, "A#5", OHAT, vol=26)
        elif kind == "drop":
            # ride + light hats, kick only on 1, snare on 3 of last two bars
            for beat in range(4):
                S.put(p, b + beat * 4, CH_HAT, "G#4", RIDE, vol=24 if beat == 0 else 16)
            for off in range(0, 16, 2):
                S.put(p, b + off, CH_HAT, "F#5", HAT, vol=10 if off % 4 else 16)
            S.put(p, b + 0, CH_KICK, "C-3", KICK, vol=50)
            if bar >= 2:
                S.put(p, b + 8, CH_KICK, "C-3", KICK, vol=44)
                S.put(p, b + 4, CH_SNARE, "D-3", SNARE, vol=36)
                S.put(p, b + 12, CH_SNARE, "D-3", SNARE, vol=32)
            if last:
                S.put(p, b + 10, CH_KICK, "A-3", TOM, vol=40)
                S.put(p, b + 12, CH_KICK, "F-3", TOM, vol=44)
                S.put(p, b + 14, CH_KICK, "C-3", TOM, vol=50)
                S.put(p, b + 13, CH_SNARE, "D-3", SNARE, vol=30)
                S.put(p, b + 15, CH_SNARE, "D-3", SNARE, vol=42)
        elif kind == "break":
            for beat in range(4):
                S.put(p, b + beat * 4, CH_HAT, "G#4", RIDE, vol=26 if beat == 0 else 18)
            for off in (6, 14):
                S.put(p, b + off, CH_HAT, "F#5", HAT, vol=16)
        else:
            # 8th hats
            for off in range(0, 16, 2):
                accent = off in (0, 8)
                v = 36 if accent else 22
                if kind == "climax":
                    v += 2
                S.put(p, b + off, CH_HAT, "F#5", HAT, vol=v)
            # 16th ghosts
            if kind in ("verse", "chorus", "climax"):
                gv = 14 if kind == "climax" else (12 if kind == "chorus" else 9)
                for off in (1, 3, 5, 7, 9, 11, 13, 15):
                    # slight delay on some 16ths (classic tracker swing)
                    # EDx note delay for light swing on the last 16th of a beat
                    nd = 0xD1 if (off % 4 == 3 and bar % 2 == 1) else None
                    S.put(p, b + off, CH_HAT, "F#5", HAT, vol=gv, fx=0xE if nd else None, fp=nd)
            # open hat
            if kind == "climax":
                S.put(p, b + 6, CH_HAT, "A#5", OHAT, vol=28)
                if not last:
                    S.put(p, b + 14, CH_HAT, "A#5", OHAT, vol=18)
            elif last:
                S.put(p, b + 14, CH_HAT, "A#5", OHAT, vol=20)
            elif bar % 2 == 1:
                S.put(p, b + 14, CH_HAT, "A#5", OHAT, vol=18)

        # --- kick ---
        if kind in ("drop",):
            pass  # already placed in hat block
        elif kind == "intro":
            if bar == 3:
                S.put(p, b + 0, CH_KICK, "C-3", KICK, vol=62)
                S.put(p, b + 8, CH_KICK, "C-3", KICK, vol=56)
                S.put(p, b + 12, CH_KICK, "C-3", KICK, vol=48)
        elif kind == "break":
            S.put(p, b + 0, CH_KICK, "C-3", KICK, vol=56)
            if bar in (1, 3):
                S.put(p, b + 8, CH_KICK, "C-3", KICK, vol=48)
            if last:
                S.put(p, b + 10, CH_KICK, "A-3", TOM, vol=46)
                S.put(p, b + 12, CH_KICK, "F-3", TOM, vol=50)
                S.put(p, b + 14, CH_KICK, "C-3", TOM, vol=54)
        else:
            S.put(p, b + 0, CH_KICK, "C-3", KICK, vol=64)
            S.put(p, b + 8, CH_KICK, "C-3", KICK, vol=60)
            if kind in ("chorus", "climax"):
                S.put(p, b + 6, CH_KICK, "C-3", KICK, vol=46)
                if bar % 2 == 0:
                    S.put(p, b + 11, CH_KICK, "C-3", KICK, vol=38)
            else:
                if bar in (1, 3):
                    S.put(p, b + 10, CH_KICK, "C-3", KICK, vol=40)
            if kind == "climax" and bar == 1:
                S.put(p, b + 3, CH_KICK, "C-3", KICK, vol=36)

        # --- snare ---
        if kind in ("drop",):
            pass
        elif kind == "intro":
            if bar == 3:
                S.put(p, b + 4, CH_SNARE, "D-3", SNARE, vol=42)
                S.put(p, b + 12, CH_SNARE, "D-3", SNARE, vol=38)
        elif kind == "break":
            S.put(p, b + 4, CH_SNARE, "D-3", SNARE, vol=34)
            S.put(p, b + 12, CH_SNARE, "D-3", SNARE, vol=30)
            if last:
                S.put(p, b + 8, CH_SNARE, "D-3", SNARE, vol=28)
                S.put(p, b + 10, CH_SNARE, "D-3", SNARE, vol=36)
                S.put(p, b + 13, CH_SNARE, "D-3", SNARE, vol=44)
                S.put(p, b + 15, CH_SNARE, "D-3", SNARE, vol=50)
        else:
            sv = 54 if kind == "climax" else 50
            S.put(p, b + 4, CH_SNARE, "D-3", SNARE, vol=sv)
            S.put(p, b + 12, CH_SNARE, "D-3", SNARE, vol=sv - 2)
            S.put(p, b + 7, CH_SNARE, "D-3", SNARE, vol=16)
            if kind in ("chorus", "climax"):
                S.put(p, b + 15, CH_SNARE, "D-3", SNARE, vol=14)
            # clap layer on echo channel
            if kind in ("chorus", "climax"):
                S.put(p, b + 4, CH_ECHO, "D-3", CLAP, vol=36)
                S.put(p, b + 12, CH_ECHO, "D-3", CLAP, vol=32)

        # ticks in climax
        if kind == "climax":
            for off in (1, 3, 5, 9, 11, 13):
                # ticks on spark channel? spark used for pluck. Use echo if clap not there
                if off not in (4, 12):
                    S.put(p, b + off, CH_ECHO, "C-6", TICK, vol=20)

    # end fill on last 4 rows of verse/chorus/climax
    if kind in ("verse", "chorus"):
        pass  # optional, caller can request fill
    if kind == "climax":
        # overwrite last 4 rows of last bar with fill
        for r, n, v in [(60, "A-3", 44), (61, "G-3", 48), (62, "E-3", 52), (63, "C-3", 56)]:
            S.put(p, r, CH_KICK, n, TOM, vol=v)
        S.put(p, 60, CH_SNARE, "D-3", SNARE, vol=30)
        S.put(p, 62, CH_SNARE, "D-3", SNARE, vol=42)
        S.put(p, 63, CH_SNARE, "D-3", SNARE, vol=52)


def drums_fill(p, start=60):
    for i, (n, v) in enumerate([("A-3", 44), ("G-3", 48), ("E-3", 52), ("C-3", 58)]):
        S.put(p, start + i, CH_KICK, n, TOM, vol=v)
    S.put(p, start + 0, CH_SNARE, "D-3", SNARE, vol=26)
    S.put(p, start + 2, CH_SNARE, "D-3", SNARE, vol=40)
    S.put(p, start + 3, CH_SNARE, "D-3", SNARE, vol=52)


def bass_phrase(p, b, chd, kind="verse"):
    root, octu, fifth = chd["root"], chd["oct"], chd["fifth"]
    if kind == "break":
        seq = [(0, root, 34, 4), (8, root, 30, 4)]
    elif kind == "drive":
        seq = [
            (0, root, 42, 2), (2, octu, 30, 1),
            (4, root, 36, 2), (6, fifth, 28, 1),
            (8, root, 40, 2), (10, octu, 30, 1),
            (12, fifth, 34, 2), (14, octu, 26, 1),
        ]
    elif kind == "gallop":
        seq = [
            (0, root, 42, 2), (3, octu, 26, 1),
            (4, root, 34, 2), (6, fifth, 28, 1),
            (8, root, 40, 2), (11, octu, 26, 1),
            (12, fifth, 32, 2), (14, root, 28, 1),
        ]
    else:
        seq = [
            (0, root, 40, 2), (3, octu, 24, 1),
            (4, root, 32, 2), (6, fifth, 26, 1),
            (8, root, 38, 2), (11, octu, 24, 1),
            (12, fifth, 30, 2), (15, octu, 22, 1),
        ]
    for off, n, v, dur in seq:
        S.put(p, b + off, CH_BASS, n, BASS, vol=v)
        S.put(p, b + off, CH_SUB, n, SUB, vol=max(v - 18, 8))
        if off == 0:
            # tiny up-slide next row (keygen analog)
            if 1 not in [s[0] for s in seq]:
                S.put(p, b + 1, CH_BASS, fx=0xE, fp=0x12)
        cut = b + off + dur
        if dur >= 1 and (off + dur) < 16:
            # don't cut if next note lands on cut row
            nxt = [s[0] for s in seq]
            if (off + dur) not in nxt:
                S.put(p, cut, CH_BASS, OFF)
                S.put(p, cut, CH_SUB, OFF)


def pad_phrase(p, b, chd, vol=20, vib=True):
    S.put(p, b + 0, CH_PAD, chd["pad"], PAD, vol=vol, fx=4 if vib else None, fp=0x31 if vib else None)
    # slight fade
    S.put(p, b + 8, CH_PAD, fx=4, fp=0x31)


def arp_classic(p, b, chd, vol=44, pan_swing=True):
    note = chd["arp"]
    prm = chd["param"]
    for off in range(16):
        if off % 4 == 0:
            v = vol if off == 0 else vol - 4
            S.put(p, b + off, CH_ARP, note, ARP, vol=v, fx=0, fp=prm)
        else:
            S.put(p, b + off, CH_ARP, fx=0, fp=prm)


def arp_run(p, b, chd, vol=44):
    run = RUNS.get(chd["arp"])
    if not run:
        return arp_classic(p, b, chd, vol)
    for off, n in enumerate(run):
        v = vol if off % 4 == 0 else vol - 8
        # ping-pong pan (effect 8) — the keygen stereo shimmer
        pan = 0x20 + (off % 8) * 0x18
        if pan > 0xF0:
            pan = 0xF0
        S.put(p, b + off, CH_ARP, n, ARP, vol=v, fx=8, fp=pan)


def arp_stacc(p, b, chd, vol=44):
    prm = chd["param"]
    note = chd["arp"]
    for off in range(0, 16, 2):
        v = vol if off % 4 == 0 else vol - 8
        S.put(p, b + off, CH_ARP, note, ARP, vol=v, fx=0, fp=prm)
        S.put(p, b + off + 1, CH_ARP, OFF)


def chip_echo(p, b, chd, kind="delay"):
    note = chd["chip"]
    prm = chd["param"]
    if kind == "delay":
        for off in range(2, 16, 4):
            S.put(p, b + off, CH_CHIP, note, CHIP, vol=28, fx=0, fp=prm)
            S.put(p, b + off + 1, CH_CHIP, fx=0, fp=prm)
            if off + 2 < 16:
                S.put(p, b + off + 2, CH_CHIP, fx=0, fp=prm)
        S.put(p, b + 0, CH_CHIP, OFF)
    elif kind == "unison":
        for off in range(16):
            if off % 4 == 0:
                S.put(p, b + off, CH_CHIP, note, CHIP, vol=30, fx=0, fp=prm)
            else:
                S.put(p, b + off, CH_CHIP, fx=0, fp=prm)
    elif kind == "offbeat":
        for off in range(0, 16, 2):
            S.put(p, b + off, CH_CHIP, note, CHIP, vol=22 if off % 4 else 32, fx=0, fp=prm)
            S.put(p, b + off + 1, CH_CHIP, OFF)
    elif kind == "drive":
        for off in range(16):
            if off % 2 == 0:
                S.put(p, b + off, CH_CHIP, note, CHIP, vol=28, fx=0, fp=prm)
            else:
                # retrig every tick on the off 16ths for extra chatter
                S.put(p, b + off, CH_CHIP, fx=0xE, fp=0x93)


def sparkle(p, b, chd, kind="pluck"):
    if kind == "pluck":
        S.put(p, b + 0, CH_SPARK, chd["pluck"], PLUCK, vol=44)
        S.put(p, b + 8, CH_SPARK, chd["pluck"], PLUCK, vol=28)
    elif kind == "bell":
        S.put(p, b + 0, CH_SPARK, chd["bell"], BELL, vol=40)
    elif kind == "organ":
        S.put(p, b + 0, CH_SPARK, chd["pad"], ORGAN, vol=30)
        S.put(p, b + 8, CH_SPARK, chd["pad"], ORGAN, vol=24)
    elif kind == "none":
        pass


def square_pulse(p, b, note, vol=22):
    """Sparse square stabs answering the harmony."""
    S.put(p, b + 4, CH_ECHO, note, SQUARE, vol=vol)
    S.put(p, b + 12, CH_ECHO, note, SQUARE, vol=vol - 6)


def harmony_thirds(p, events, delay=0, vol_div=2, ins=LEADSOFT):
    """Place delayed quieter copy of note events on CH_ECHO — careful with claps.
    Only use on patterns without chorus claps, or on rows not 4/12 of bars.
    """
    for row, note, ins0, vol, fx, fp in events:
        if not note or note == OFF:
            continue
        rr = row + delay
        if rr >= 64:
            continue
        # skip clap collisions (rows 4,12,20,28,36,44,52,60)
        if rr % 16 in (4, 12):
            continue
        vv = max(12, (vol or 40) // vol_div)
        S.put(p, rr, CH_ECHO, note, ins, vol=vv)


# Melodies: list of (row, note, ins, vol, fx, fp)
def M(row, note, ins=LEAD, vol=48, fx=None, fp=None):
    return (row, note, ins, vol, fx, fp)


def apply_mel(p, events, ch=CH_LEAD):
    for row, note, ins, vol, fx, fp in events:
        S.put(p, row, ch, note, ins, vol, fx, fp)


def lead_verse():
    e = []
    # hook with a classic FT2 porta into A
    e += [M(0, "E-5", vol=52), M(2, "D-5", vol=46), M(4, "C-5", vol=48),
          M(6, "B-4", vol=44), M(8, "A-4", vol=50, fx=4, fp=0x42),
          M(10, None, None, None, 4, 0x42),
          M(12, "C-5", vol=46), M(14, "E-5", vol=54, fx=1, fp=0x08)]  # slight slide up
    e += [M(16, "G-5", vol=52), M(18, "E-5", vol=44), M(20, "F-5", vol=48),
          M(22, "C-5", vol=40), M(24, "D-5", vol=46), M(26, "C-5", vol=40),
          M(28, "A-4", vol=44), M(30, "C-5", vol=48)]
    e += [M(32, "E-5", vol=50), M(34, "G-5", vol=54), M(36, "A-5", vol=52, fx=4, fp=0x43),
          M(38, None, None, None, 4, 0x43),
          M(40, "G-5", vol=50), M(42, "E-5", vol=44), M(44, "D-5", vol=42),
          M(46, "C-5", vol=40)]
    e += [M(48, "B-4", vol=44), M(50, "D-5", vol=46), M(52, "G-5", vol=50),
          M(54, "D-5", vol=42), M(56, "F-5", vol=48), M(58, "E-5", vol=46),
          M(60, "D-5", vol=44), M(62, "B-4", vol=40)]
    return e


def lead_verse_b():
    e = []
    e += [M(0, "A-5", vol=52), M(2, "G-5", vol=46), M(4, "E-5", vol=48),
          M(6, "D-5", vol=42), M(8, "C-5", vol=44), M(10, "E-5", vol=50),
          M(12, "A-5", vol=54), M(14, "C-6", vol=50)]
    e += [M(16, "B-5", vol=52, fx=4, fp=0x42), M(18, None, None, None, 4, 0x42),
          M(20, "A-5", vol=46), M(22, "G-5", vol=42), M(24, "F-5", vol=44),
          M(26, "A-5", vol=48), M(28, "G-5", vol=44), M(30, "E-5", vol=40)]
    e += [M(32, "G-5", vol=50), M(34, "E-5", vol=44), M(36, "C-5", vol=46),
          M(38, "D-5", vol=48), M(40, "E-5", vol=50), M(42, "G-5", vol=52),
          M(44, "A-5", vol=50), M(46, "G-5", vol=44)]
    e += [M(48, "F#5", vol=46), M(50, "G-5", vol=48), M(52, "A-5", vol=52),
          M(54, "B-5", vol=50), M(56, "D-6", vol=54), M(58, "B-5", vol=48),
          M(60, "G-5", vol=44), M(62, "E-5", vol=42)]
    return e


def lead_chorus():
    e = []
    e += [M(0, "A-5", LEADSOFT, vol=52), M(2, "C-6", LEADSOFT, vol=48),
          M(4, "A-5", LEADSOFT, vol=46), M(6, "G-5", LEADSOFT, vol=44),
          M(8, "F-5", LEADSOFT, vol=48, fx=4, fp=0x43),
          M(10, None, None, None, 4, 0x43),
          M(12, "G-5", LEADSOFT, vol=46), M(14, "A-5", LEADSOFT, vol=50)]
    e += [M(16, "B-5", LEADSOFT, vol=52), M(18, "D-6", LEADSOFT, vol=48),
          M(20, "B-5", LEADSOFT, vol=46), M(22, "A-5", LEADSOFT, vol=42),
          M(24, "G-5", LEADSOFT, vol=46), M(26, "B-5", LEADSOFT, vol=48),
          M(28, "D-6", LEADSOFT, vol=50), M(30, "G-5", LEADSOFT, vol=44)]
    e += [M(32, "E-6", LEAD, vol=56, fx=4, fp=0x42),
          M(34, None, None, None, 4, 0x42),
          M(36, "D-6", LEAD, vol=48), M(38, "C-6", LEAD, vol=46),
          M(40, "B-5", LEAD, vol=44), M(42, "A-5", LEAD, vol=46),
          M(44, "C-6", LEAD, vol=50), M(46, "E-6", LEAD, vol=52)]
    e += [M(48, "G-5", LEAD, vol=48), M(50, "C-6", LEAD, vol=50),
          M(52, "E-6", LEAD, vol=52), M(54, "G-6", LEAD, vol=48, fx=4, fp=0x53),
          M(56, None, None, None, 4, 0x53),
          M(58, "E-6", LEAD, vol=46), M(60, "D-6", LEAD, vol=44),
          M(62, "C-6", LEAD, vol=42)]
    return e


def lead_dom():
    e = []
    e += [M(0, "C-6", LEADSOFT, vol=50), M(2, "A-5", vol=44), M(4, "G-5", vol=46),
          M(6, "F-5", vol=42), M(8, "E-5", vol=46, fx=4, fp=0x42),
          M(10, None, None, None, 4, 0x42),
          M(12, "F-5", vol=44), M(14, "A-5", vol=50)]
    e += [M(16, "B-5", vol=52), M(18, "G-5", vol=44), M(20, "D-6", vol=52),
          M(22, "B-5", vol=46), M(24, "A-5", vol=44), M(26, "G-5", vol=42),
          M(28, "F#5", vol=46), M(30, "G-5", vol=48)]
    e += [M(32, "G-5", vol=48), M(34, "B-5", vol=46), M(36, "E-6", vol=52, fx=4, fp=0x43),
          M(38, None, None, None, 4, 0x43),
          M(40, "D-6", vol=48), M(42, "B-5", vol=44), M(44, "A-5", vol=42),
          M(46, "G-5", vol=40)]
    e += [M(48, "G#5", vol=50), M(50, "B-5", vol=52), M(52, "E-6", vol=54),
          M(54, "G#5", vol=46), M(56, "B-5", vol=50), M(58, "E-6", vol=52),
          M(60, "F#6", vol=50), M(62, "G#6", vol=54)]
    return e


def lead_bridge():
    e = []
    e += [M(0, "A-4", TRI, vol=40, fx=4, fp=0x42),
          M(4, None, None, None, 4, 0x42),
          M(8, "C-5", TRI, vol=38, fx=4, fp=0x42),
          M(12, None, None, None, 4, 0x42)]
    e += [M(16, "B-4", TRI, vol=40, fx=4, fp=0x43),
          M(20, None, None, None, 4, 0x43),
          M(24, "G#4", TRI, vol=38),
          M(28, "B-4", TRI, vol=40)]
    e += [M(32, "C-5", TRI, vol=42, fx=4, fp=0x42),
          M(36, None, None, None, 4, 0x42),
          M(40, "E-5", TRI, vol=44),
          M(44, "A-5", TRI, vol=46, fx=4, fp=0x43),
          M(46, None, None, None, 4, 0x43)]
    e += [M(48, "G-5", TRI, vol=44), M(52, "D-5", TRI, vol=40),
          M(56, "B-4", TRI, vol=38), M(60, "G-4", TRI, vol=36)]
    return e


def lead_turn():
    e = []
    e += [M(0, "F-5", vol=48), M(2, "A-5", vol=50), M(4, "C-6", vol=52),
          M(6, "A-5", vol=46), M(8, "G-5", vol=48, fx=4, fp=0x42),
          M(10, None, None, None, 4, 0x42),
          M(12, "F-5", vol=44), M(14, "D-5", vol=42)]
    e += [M(16, "G-5", vol=48), M(18, "B-5", vol=50), M(20, "D-6", vol=52),
          M(22, "B-5", vol=46), M(24, "A-5", vol=48), M(26, "G-5", vol=44),
          M(28, "F-5", vol=42), M(30, "G-5", vol=46)]
    e += [M(32, "G#5", vol=50), M(34, "B-5", vol=48), M(36, "E-6", vol=54, fx=4, fp=0x43),
          M(38, None, None, None, 4, 0x43),
          M(40, "D-6", vol=48), M(42, "C-6", vol=46), M(44, "B-5", vol=48),
          M(46, "G#5", vol=44)]
    e += [M(48, "E-5", vol=50), M(50, "G#5", vol=52), M(52, "B-5", vol=54),
          M(54, "E-6", vol=56), M(56, "G#5", vol=48), M(58, "B-5", vol=52),
          M(60, "E-6", vol=54, fx=1, fp=0x12), M(62, "E-5", vol=44)]
    return e


def apply_prog(p, name, bass_kind, arp_kind, chip_kind, pad_vol, spark_kind):
    prog = PROG[name]
    for i, chd in enumerate(prog):
        b = i * 16
        bass_phrase(p, b, chd, kind=bass_kind)
        pad_phrase(p, b, chd, vol=pad_vol)
        if arp_kind == "classic":
            arp_classic(p, b, chd)
        elif arp_kind == "run":
            arp_run(p, b, chd)
        elif arp_kind == "stacc":
            arp_stacc(p, b, chd)
        chip_echo(p, b, chd, kind=chip_kind)
        sparkle(p, b, chd, kind=spark_kind)


def crash(p, r, vol=44):
    S.put(p, r, CH_FX, "C-5", CRASH, vol=vol)


def rise(p, r, note="A-4", vol=24):
    S.put(p, r, CH_FX, note, RISE, vol=vol)


def zap(p, r, note="E-5", vol=28):
    S.put(p, r, CH_FX, note, ZAP, vol=vol)


# ===================== PATTERNS =====================

# P0 intro
def p0():
    p = 0
    drums(p, "intro")
    # long Am pad, slow swell (vol slide up), keep it alive
    S.put(p, 0, CH_PAD, "A-4", PAD, vol=16, fx=4, fp=0x31)
    S.put(p, 4, CH_PAD, fx=10, fp=0x0C)
    S.put(p, 8, CH_PAD, fx=10, fp=0x0C)
    S.put(p, 12, CH_PAD, fx=4, fp=0x32)
    S.put(p, 16, CH_PAD, "C-5", PAD, vol=16, fx=4, fp=0x32)
    S.put(p, 24, CH_PAD, fx=4, fp=0x32)
    S.put(p, 32, CH_PAD, "E-5", PAD, vol=18, fx=4, fp=0x31)
    S.put(p, 40, CH_PAD, fx=4, fp=0x31)
    S.put(p, 48, CH_PAD, "A-4", PAD, vol=22, fx=4, fp=0x31)
    S.put(p, 56, CH_PAD, fx=4, fp=0x31)
    # bells + triangle motif
    S.put(p, 0, CH_SPARK, "A-5", BELL, vol=42)
    S.put(p, 8, CH_SPARK, "E-5", BELL, vol=28)  # keep hole filled
    S.put(p, 8, CH_ECHO, "E-5", TRI, vol=24, fx=4, fp=0x42)
    S.put(p, 16, CH_SPARK, "C-6", BELL, vol=32)
    S.put(p, 24, CH_SPARK, "C-6", BELL, vol=28)
    S.put(p, 28, CH_ECHO, "A-5", TRI, vol=20)
    S.put(p, 32, CH_SPARK, "A-5", BELL, vol=36)
    S.put(p, 40, CH_SPARK, "E-6", BELL, vol=30)
    S.put(p, 48, CH_SPARK, "A-6", BELL, vol=32)
    rise(p, 0, "G-4", 24)
    # arp from bar 2
    for off in range(16, 32):
        if off % 4 == 0:
            S.put(p, off, CH_ARP, "A-4", ARP, vol=16, fx=0, fp=A037)
        else:
            S.put(p, off, CH_ARP, fx=0, fp=A037)
    for off in range(32, 48):
        if off % 4 == 0:
            S.put(p, off, CH_ARP, "A-4", ARP, vol=24, fx=0, fp=A037)
        else:
            S.put(p, off, CH_ARP, fx=0, fp=A037)
    dummy = PROG["verse"][0]
    for off in range(48, 64):
        if off % 4 == 0:
            S.put(p, off, CH_ARP, "A-4", ARP, vol=34, fx=0, fp=A037)
        else:
            S.put(p, off, CH_ARP, fx=0, fp=A037)
    for off in range(32, 48, 4):
        S.put(p, off, CH_CHIP, "E-5", CHIP, vol=14, fx=0, fp=A037)
        S.put(p, off + 1, CH_CHIP, fx=0, fp=A037)
    for off in range(48, 64, 2):
        S.put(p, off, CH_CHIP, "E-5", CHIP, vol=22, fx=0, fp=A037)
        S.put(p, off + 1, CH_CHIP, fx=0, fp=A037)
    # sub drone from the first beat so the intro isn't a hole
    S.put(p, 0, CH_SUB, "A-2", SUB, vol=14, fx=4, fp=0x31)
    S.put(p, 16, CH_SUB, "A-2", SUB, vol=16, fx=4, fp=0x31)
    S.put(p, 32, CH_SUB, "A-2", SUB, vol=18, fx=4, fp=0x32)
    S.put(p, 0, CH_BASS, "A-2", BASS, vol=10)
    S.put(p, 16, CH_BASS, "E-2", BASS, vol=12)
    S.put(p, 32, CH_BASS, "A-2", BASS, vol=16)
    bass_phrase(p, 48, dummy, kind="verse")
    crash(p, 48, 42)
    apply_mel(p, [M(32, "A-4", TRI, vol=28, fx=4, fp=0x42),
                  M(40, "C-5", TRI, vol=30),
                  M(48, "E-5", vol=40), M(52, "A-5", vol=44),
                  M(56, "C-6", vol=48), M(60, "E-6", vol=46), M(62, "A-5", vol=36)])
    zap(p, 60, "C-5", 22)


def groove(p, prog, drums_kind, bass_kind, arp_kind, chip_kind, pad_vol, spark,
           lead_fn=None, crash_rows=None, rise_row=None, fill=False, zap_row=None,
           echo_lead=False):
    drums(p, drums_kind)
    apply_prog(p, prog, bass_kind, arp_kind, chip_kind, pad_vol, spark)
    if lead_fn:
        ev = lead_fn()
        apply_mel(p, ev)
        if echo_lead:
            # delayed copy on CH_ECHO would fight claps in chorus — only for verse
            for row, note, ins, vol, fx, fp in ev:
                if note and note != OFF:
                    rr = row + 3
                    if rr < 64:
                        S.put(p, rr, CH_ECHO, note, CHIP, vol=max(10, (vol or 40) // 3))
    for r in (crash_rows or []):
        crash(p, r, 42)
    if rise_row is not None:
        rise(p, rise_row, "A-4", 22)
    if zap_row is not None:
        zap(p, zap_row, "G-4", 26)
    if fill:
        drums_fill(p, 60)
        zap(p, 60, "E-4", 24)


# Build
p0()
# 1 verse groove
groove(1, "verse", "verse", "verse", "classic", "delay", 18, "pluck",
       crash_rows=[0])
for i, n in enumerate(["E-5", "C-5", "G-5", "D-5"]):
    S.put(1, i * 16 + 4, CH_ECHO, n, SQUARE, vol=18)
    S.put(1, i * 16 + 12, CH_ECHO, n, SQUARE, vol=14)
    for off in (1, 3, 9, 11):
        S.put(1, i * 16 + off, CH_ECHO, "C-6", TICK, vol=12)
# 2 verse + hook
groove(2, "verse", "verse", "gallop", "classic", "offbeat", 20, "pluck",
       lead_fn=lead_verse, echo_lead=True, fill=True)
# 3 chorus
groove(3, "chorus", "chorus", "drive", "run", "drive", 24, "bell",
       lead_fn=lead_chorus, crash_rows=[0])
for i, n in enumerate(["C-6", "D-6", "E-6", "G-6"]):
    if i == 0:
        continue  # crash on row 0 of FX
    S.put(3, i * 16 + 0, CH_FX, n, SQUARE, vol=18)
    S.put(3, i * 16 + 8, CH_FX, n, SQUARE, vol=14)
# 4 dominant lift
groove(4, "dom", "chorus", "drive", "stacc", "offbeat", 22, "pluck",
       lead_fn=lead_dom, crash_rows=[0], fill=True, rise_row=48)
# 5 rest / drop
groove(5, "verse", "drop", "break", "stacc", "delay", 16, "organ",
       crash_rows=[])
# square answers
for i, n in enumerate(["E-5", "C-5", "G-5", "B-4"]):
    square_pulse(5, i * 16, n, vol=24)
# 6 verse B + lead
groove(6, "verse", "verse", "gallop", "classic", "offbeat", 20, "pluck",
       lead_fn=lead_verse_b, echo_lead=True, fill=True, crash_rows=[0])
# 7 chorus again
groove(7, "chorus", "chorus", "drive", "run", "drive", 24, "bell",
       lead_fn=lead_chorus, crash_rows=[0], fill=True)
for i, n in enumerate(["C-6", "D-6", "E-6", "G-6"]):
    if i == 0:
        continue
    S.put(7, i * 16 + 0, CH_FX, n, SQUARE, vol=18)
    S.put(7, i * 16 + 8, CH_FX, n, SQUARE, vol=14)
# 8 break
groove(8, "bridge", "break", "break", "stacc", "delay", 14, "bell",
       lead_fn=lead_bridge, crash_rows=[], rise_row=48)
crash(8, 0, 30)
crash(8, 60, 40)
# 9 climax
groove(9, "verse", "climax", "drive", "run", "drive", 26, "pluck",
       lead_fn=lead_verse_b, crash_rows=[0], fill=False)
# extra bells / squares riding over the climax
for i, n in enumerate(["A-6", "F-6", "C-6", "G-6"]):
    if i:
        S.put(9, i * 16, CH_FX, n, BELL, vol=30)
    S.put(9, i * 16 + 8, CH_FX, n, SQUARE, vol=18)
crash(9, 32, 38)
# octave-down lead answers (echo rows 0/8 are clap-free)
octs = ["A-4", "G-4", "E-4", "D-4"]
for i, n in enumerate(octs):
    S.put(9, i * 16 + 0, CH_ECHO, n, LEADSOFT, vol=22, fx=4, fp=0x42)
    S.put(9, i * 16 + 8, CH_ECHO, n, LEADSOFT, vol=18)
# 10 turnaround
groove(10, "dom", "climax", "drive", "run", "drive", 24, "pluck",
       lead_fn=lead_turn, crash_rows=[0], fill=True, rise_row=40)
zap(10, 58, "B-4", 20)
crash(10, 32, 34)

# extra crash near loop-back
crash(10, 0, 42)  # already

# Order
order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
loop_start = 1

batch = []
batch.append({"name": "song_set", "arguments": {
    "name": "CRACKINTRO.NFO",
    "bpm": 148,
    "speed": 6,
    "length": len(order),
    "loop_start": loop_start,
    "channels": 12,
}})
for pos, pat in enumerate(order):
    batch.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

pats = sorted(set(order))
for pat in pats:
    batch.append({"name": "pattern_set_length", "arguments": {"pattern": pat, "rows": 64}})
    batch.append({"name": "pattern_clear", "arguments": {"pattern": pat}})

cells = S.dump()
for c in cells:
    batch.append({"name": "pattern_set_cell", "arguments": c})

path = "/tmp/compose_batch.json"
with open(path, "w") as f:
    json.dump(batch, f)

from collections import Counter
cc = Counter(c["pattern"] for c in cells)
print("batch", len(batch), "cells", len(cells), "bytes", __import__("os").path.getsize(path))
print("order", order, "loop", loop_start)
print("cells/pat", dict(sorted(cc.items())))
chc = Counter(c["channel"] for c in cells)
print("cells/ch", dict(sorted(chc.items())))
