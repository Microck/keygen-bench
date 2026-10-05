#!/usr/bin/env python3
"""Neon Cipher — 12-ch keygen XM. Loops from order 2."""
import json, os

CH_KICK, CH_SNR, CH_HAT, CH_BASS, CH_SUB, CH_LEAD = 0, 1, 2, 3, 4, 5
CH_ECHO, CH_ARP, CH_PAD, CH_PLK, CH_FX, CH_AUX = 6, 7, 8, 9, 10, 11

I_BASS, I_SUB, I_DIST = 1, 2, 3
I_SAW, I_PULSE, I_TRI, I_SQR, I_ARP = 4, 5, 6, 7, 8
I_PAD, I_PAD2 = 9, 10
I_KICK, I_SNR, I_CLAP, I_CHH, I_OHH = 11, 12, 13, 14, 15
I_RIDE, I_CRASH, I_TOM, I_BLIP = 16, 17, 18, 19
I_RISER, I_BELL, I_PLUCK, I_CHIP = 20, 21, 22, 23

ops = []

def xv(v):
    return 16 + int(max(0, min(64, round(v))))

def cell(p, r, ch, note=None, ins=None, vol=None, eff=None, ep=None):
    if r < 0 or r > 63:
        return
    d = {"pattern": int(p), "row": int(r), "channel": int(ch)}
    if note is not None:
        d["note"] = note
    if ins is not None:
        d["instrument"] = int(ins)
    if vol is not None:
        d["volume"] = xv(vol) if vol <= 64 else int(vol)
    if eff is not None:
        d["effect"] = int(eff)
    if ep is not None:
        d["effect_param"] = int(ep)
    ops.append({"name": "pattern_set_cell", "arguments": d})

def off(p, r, ch):
    cell(p, r, ch, note="OFF")

def octn(name, k):
    if name[1] == "#":
        let = name[:2]
        rest = name[2:]
        if rest[:1] == "-":
            rest = rest[1:]
        return f"{let}-{int(rest) + k}"
    return f"{name[0]}-{int(name.split('-')[1]) + k}"


def drums(p, extra=(), claps=False, ghost=True, fill=False, kv=64, sv=58):
    kicks, snares = [], []
    for bar in range(4):
        b = bar * 16
        kicks += [b + 0, b + 8]
        snares += [b + 4, b + 12]
    for r in kicks + list(extra):
        cell(p, r, CH_KICK, "C-4", I_KICK, vol=kv)
    for r in snares:
        if fill and r >= 56:
            continue
        if claps and (r % 16 == 12):
            cell(p, r, CH_SNR, "D-4", I_CLAP, vol=sv - 4, eff=8, ep=0xA8)
        else:
            cell(p, r, CH_SNR, "C-4", I_SNR, vol=sv, eff=8, ep=0x90)
    if ghost:
        for r in (10, 26, 42):
            if not (fill and r >= 56):
                cell(p, r, CH_SNR, "C-4", I_SNR, vol=16, eff=8, ep=0x78)
    if fill:
        cell(p, 56, CH_SNR, "A-3", I_TOM, vol=48, eff=8, ep=0x50)
        cell(p, 58, CH_SNR, "A-3", I_TOM, vol=40, eff=8, ep=0x48)
        cell(p, 60, CH_SNR, "F-3", I_TOM, vol=52, eff=8, ep=0x70)
        cell(p, 61, CH_SNR, "F-3", I_TOM, vol=36, eff=8, ep=0x80)
        cell(p, 62, CH_SNR, "C-3", I_TOM, vol=56, eff=8, ep=0x98)
        cell(p, 63, CH_KICK, "C-4", I_KICK, vol=52)


def hats_8(p, base=20):
    for r in range(0, 64, 2):
        acc = 10 if r % 8 == 0 else (4 if r % 4 == 0 else 0)
        pan = 0xC0 if (r // 2) % 2 == 0 else 0x40
        cell(p, r, CH_HAT, "F-4", I_CHH, vol=base + acc, eff=8, ep=pan)


def hats_16(p, base=26, open_on=(14, 30, 46, 62)):
    for r in range(64):
        if r in open_on:
            cell(p, r, CH_HAT, "G-4", I_OHH, vol=base + 10, eff=8, ep=0xE0)
            continue
        acc = 12 if r % 8 == 0 else (7 if r % 4 == 0 else (3 if r % 2 == 0 else -2))
        pan = 0xC8 if r % 4 < 2 else 0x38
        cell(p, r, CH_HAT, "F-4", I_CHH, vol=max(8, base + acc), eff=8, ep=pan)


def ride4(p, vol=18):
    pans = (0xE0, 0xC0, 0xA0, 0xE8)
    for r, pan in zip((0, 16, 32, 48), pans):
        cell(p, r, CH_AUX, "C-5", I_RIDE, vol=vol, eff=8, ep=pan)


# walking-ish bass: root, root, 5th, octave, passing, root, octave
BASS_WALK = {
    "A-2": [(0, "A-2"), (4, "A-2"), (6, "E-2"), (8, "A-3"), (10, "G-2"), (12, "A-2"), (14, "A-3")],
    "F-2": [(0, "F-2"), (4, "F-2"), (6, "C-2"), (8, "F-3"), (10, "E-2"), (12, "F-2"), (14, "F-3")],
    "C-2": [(0, "C-2"), (4, "C-2"), (6, "G-2"), (8, "C-3"), (10, "B-1"), (12, "C-2"), (14, "C-3")],
    "G-2": [(0, "G-2"), (4, "G-2"), (6, "D-2"), (8, "G-3"), (10, "F-2"), (12, "G-2"), (14, "G-3")],
    "D-2": [(0, "D-2"), (4, "D-2"), (6, "A-2"), (8, "D-3"), (10, "C-2"), (12, "D-2"), (14, "D-3")],
    "E-2": [(0, "E-2"), (4, "E-2"), (6, "B-1"), (8, "E-3"), (10, "D-2"), (12, "E-2"), (14, "G#2")],
}


def bass(p, roots, dist=False, v=52, sub=True, walk=True):
    ins = I_DIST if dist else I_BASS
    for bar, root in enumerate(roots):
        b = bar * 16
        seq = BASS_WALK.get(root) if walk else [
            (0, root), (4, root), (6, root), (8, octn(root, 1)),
            (10, root), (12, root), (14, octn(root, 1)),
        ]
        for i, (off_, n) in enumerate(seq):
            vv = v if off_ in (0, 8) else (v - 8 if off_ in (4, 12) else v - 14)
            cell(p, b + off_, CH_BASS, n, ins, vol=max(16, vv))
        if sub:
            cell(p, b + 0, CH_SUB, octn(root, -1), I_SUB, vol=26)
            cell(p, b + 8, CH_SUB, octn(root, -1), I_SUB, vol=18)


def bass_half(p, roots, v=34):
    for bar, root in enumerate(roots):
        b = bar * 16
        cell(p, b + 0, CH_BASS, root, I_BASS, vol=v)
        cell(p, b + 8, CH_BASS, octn(root, 1), I_BASS, vol=v - 8)
        cell(p, b + 0, CH_SUB, octn(root, -1), I_SUB, vol=20)


AM, Fmaj, Cmaj, Gmaj = ("A-4", 0x37), ("F-4", 0x47), ("C-5", 0x47), ("G-4", 0x47)
Dm, Emaj = ("D-4", 0x37), ("E-4", 0x47)


def arps(p, chords, vol=32, every=4):
    pans = (0x28, 0x40, 0x20, 0x38)
    for bar, (n, ap) in enumerate(chords):
        b = bar * 16
        for i, off_ in enumerate(range(0, 16, every)):
            cell(p, b + off_, CH_ARP, n, I_ARP, vol=vol, eff=0, ep=ap)
            # overlay pan on next row so arpeggio keeps running
            if off_ + 1 < 16:
                cell(p, b + off_ + 1, CH_ARP, eff=8, ep=pans[(bar + i) % 4])


def pads(p, notes, vol=22, ins=I_PAD):
    pans = (0x70, 0x90, 0x60, 0xA0)
    for bar, n in enumerate(notes):
        cell(p, bar * 16, CH_PAD, n, ins, vol=vol, eff=8, ep=pans[bar])
        # slow vol fade near bar end so retrigger is clean
        cell(p, bar * 16 + 12, CH_PAD, eff=0xA, ep=0x02)


def pluck_off(p, groups, vol=34):
    for bar, notes in enumerate(groups):
        b = bar * 16
        for i, n in enumerate(notes):
            pan = 0x30 + i * 40
            cell(p, b + 2 + i * 4, CH_PLK, n, I_PLUCK, vol=vol if i == 0 else vol - 6,
                 eff=8, ep=min(0xF0, pan))


def crash(p, r=0, vol=40, ch=CH_FX):
    cell(p, r, ch, "C-4", I_CRASH, vol=vol)


def lead(p, events, delay=3, echo_ins=I_PULSE, echo_div=2.2):
    for ev in events:
        r, n, v = ev[0], ev[1], ev[2]
        e = ev[3] if len(ev) > 3 else 8
        ep = ev[4] if len(ev) > 4 else 0x48  # slightly left
        if len(ev) <= 3:
            e, ep = 8, 0x48
        cell(p, r, CH_LEAD, n, I_SAW, vol=v, eff=e, ep=ep)
        if n in (None, "OFF", 97):
            continue
        rr = r + delay
        if 0 <= rr < 64:
            cell(p, rr, CH_ECHO, n, echo_ins, vol=max(10, int(v / echo_div)),
                 eff=8, ep=0xD8)


def cut_lead(p, r=63):
    off(p, r, CH_LEAD)
    off(p, r, CH_ECHO)


def bells(p, seq, ch=CH_FX):
    for r, n, v in seq:
        cell(p, r, ch, n, I_BELL, vol=v, eff=8, ep=0x40)


def chips(p, start, notes, vol0=24, ch=CH_PLK):
    for i, n in enumerate(notes):
        cell(p, start + i, ch, n, I_CHIP, vol=vol0 + i * 2, eff=8, ep=0x20 + i * 16)


# ============================================================
def pat0():
    p = 0
    pads(p, ["A-4", "A-4", "F-4", "G-4"], vol=20)
    arps(p, [AM, AM, Fmaj, Gmaj], vol=20, every=8)
    hats_8(p, base=14)
    cell(p, 0, CH_SUB, "A-1", I_SUB, vol=18)
    cell(p, 32, CH_SUB, "F-1", I_SUB, vol=16)
    cell(p, 48, CH_SUB, "G-1", I_SUB, vol=16)
    for r, v in ((32, 36), (48, 48), (56, 40)):
        cell(p, r, CH_KICK, "C-4", I_KICK, vol=v)
    bells(p, [
        (0, "A-5", 40), (8, "E-5", 26), (16, "C-6", 34), (24, "B-5", 24),
        (32, "A-5", 38), (40, "E-5", 24), (48, "G-5", 34), (56, "A-5", 42),
    ])
    ride4(p, vol=14)
    # sparkle
    chips(p, 0, ["A-5", "E-5", "C-6", "A-5"], vol0=14, ch=CH_PLK)
    chips(p, 32, ["F-5", "A-5", "C-6", "E-6"], vol0=16, ch=CH_PLK)
    lead(p, [(48, "E-5", 24), (56, "A-5", 28)], delay=4)
    cut_lead(p, 63)


def pat1():
    p = 1
    pads(p, ["A-4", "F-4", "C-5", "G-4"], vol=22)
    bass(p, ["A-2", "F-2", "C-2", "G-2"], v=44, walk=True)
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=24, every=4)
    hats_8(p, base=18)
    for r in (0, 16, 24, 32, 36, 40, 44, 48, 50, 52, 54, 56, 58, 60, 62):
        cell(p, r, CH_KICK, "C-4", I_KICK, vol=50 if r < 48 else 62)
    for r, v in ((36, 34), (44, 42), (52, 52), (56, 48), (60, 56)):
        cell(p, r, CH_SNR, "C-4", I_SNR, vol=v, eff=8, ep=0x90)
    cell(p, 62, CH_SNR, "D-4", I_CLAP, vol=52)
    cell(p, 34, CH_FX, "C-4", I_RISER, vol=38)
    crash(p, 0, vol=22, ch=CH_AUX)
    chips(p, 56, ["A-4", "C-5", "E-5", "A-5", "C-5", "E-5", "A-5", "C-6"], vol0=22)
    lead(p, [
        (0, "A-5", 22), (16, "C-6", 26), (32, "E-5", 28), (40, "A-5", 32),
        (48, "C-6", 36),
    ], delay=4)
    cut_lead(p, 63)


def pat2():
    p = 2
    cut_lead(p, 0)
    drums(p, extra=(26, 42, 54), claps=True, ghost=True)
    hats_16(p, base=26)
    bass(p, ["A-2", "F-2", "C-2", "G-2"])
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=34)
    pads(p, ["A-5", "F-5", "C-5", "G-5"], vol=20)
    pluck_off(p, [
        ["A-4", "C-5", "E-5", "A-5"],
        ["F-4", "A-4", "C-5", "F-5"],
        ["C-5", "E-5", "G-5", "C-6"],
        ["G-4", "B-4", "D-5", "G-5"],
    ])
    crash(p, 0, vol=36)
    ride4(p, vol=16)


def pat3():
    p = 3
    drums(p, extra=(26, 38, 54), claps=False, ghost=True)
    hats_16(p, base=26, open_on=(14, 30, 46))
    bass(p, ["A-2", "F-2", "C-2", "G-2"])
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=28)
    pads(p, ["A-4", "F-4", "C-5", "G-4"], vol=18)
    lead(p, [
        (0, "E-5", 50), (4, "A-5", 54), (8, "C-6", 58), (10, "B-5", 46),
        (12, "A-5", 44), (14, "G-5", 36),
        (16, "A-5", 52), (20, "G-5", 46), (24, "F-5", 48), (26, "E-5", 38),
        (28, "D-5", 36), (30, "C-5", 32),
        (32, "E-5", 52), (36, "G-5", 54), (40, "C-6", 58), (44, "D-6", 48),
        (46, "C-6", 42),
        (48, "B-5", 54), (52, "A-5", 48), (56, "G-5", 46), (58, "F-5", 36),
        (60, "E-5", 44, 4, 0x43),
    ], delay=3)
    for r, pan in ((15, 0xE8), (31, 0x18), (47, 0xE0)):
        cell(p, r, CH_AUX, "C-5", I_BLIP, vol=22, eff=8, ep=pan)


def pat4():
    p = 4
    drums(p, extra=(10, 26, 42, 54), claps=True, ghost=True, fill=True)
    hats_16(p, base=28, open_on=(14, 30, 46, 54))
    bass(p, ["A-2", "F-2", "C-2", "G-2"])
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=30)
    pads(p, ["C-5", "A-4", "G-4", "B-4"], vol=18, ins=I_PAD2)
    lead(p, [
        (0, "A-5", 52), (2, "C-6", 38), (4, "E-6", 56), (6, "C-6", 36),
        (8, "B-5", 48), (10, "C-6", 38), (12, "A-5", 44), (14, "E-5", 34),
        (16, "F-5", 52), (18, "A-5", 38), (20, "C-6", 54), (22, "A-5", 36),
        (24, "G-5", 48), (26, "A-5", 38), (28, "F-5", 42), (30, "C-5", 32),
        (32, "G-5", 52), (34, "C-6", 40), (36, "E-6", 58), (38, "D-6", 38),
        (40, "C-6", 52), (42, "B-5", 38), (44, "C-6", 46), (46, "G-5", 34),
        (48, "D-5", 50), (50, "G-5", 40), (52, "B-5", 54), (54, "A-5", 38),
        (56, "G-5", 44), (58, "F-5", 36), (60, "E-5", 40), (62, "D-5", 32),
    ], delay=2)
    cell(p, 0, CH_FX, "E-5", I_BELL, vol=28, eff=8, ep=0x38)


def pat5():
    p = 5
    drums(p, extra=(6, 22, 26, 38, 42, 54), claps=True, ghost=True)
    hats_16(p, base=28, open_on=(6, 14, 22, 30, 38, 46, 54, 62))
    bass(p, ["A-2", "F-2", "C-2", "G-2"], v=54)
    for bar, n in enumerate(["A-1", "F-1", "C-2", "G-1"]):
        cell(p, bar * 16, CH_AUX, n, I_DIST, vol=22, eff=8, ep=0x60)
        cell(p, bar * 16 + 8, CH_AUX, n, I_DIST, vol=16, eff=8, ep=0xA0)
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=36)
    pads(p, ["A-5", "F-5", "E-5", "G-5"], vol=22)
    lead(p, [
        (0, "A-5", 56), (4, "C-6", 50), (8, "E-6", 60, 4, 0x54), (12, "C-6", 46),
        (16, "A-5", 54), (20, "F-5", 48), (24, "A-5", 56), (28, "C-6", 50),
        (32, "G-5", 54), (36, "E-5", 48), (40, "G-5", 56), (44, "C-6", 52),
        (48, "B-5", 58), (52, "D-6", 52), (56, "B-5", 50), (60, "G-5", 46, 4, 0x43),
    ], delay=3, echo_ins=I_TRI)
    for r, n, v, pan in [
        (0, "C-6", 24, 0x20), (8, "A-5", 26, 0x30), (16, "C-6", 24, 0x28),
        (24, "A-5", 24, 0x38), (32, "E-6", 26, 0x18), (40, "E-6", 26, 0x40),
        (48, "D-6", 24, 0x24), (56, "B-5", 24, 0x48),
    ]:
        cell(p, r, CH_PLK, n, I_TRI, vol=v, eff=8, ep=pan)
    crash(p, 0, vol=42)


def pat6():
    p = 6
    for bar in range(4):
        b = bar * 16
        cell(p, b, CH_KICK, "C-4", I_KICK, vol=46)
        cell(p, b + 12, CH_SNR, "D-4", I_CLAP, vol=36, eff=8, ep=0xB0)
        if bar >= 2:
            cell(p, b + 8, CH_KICK, "C-4", I_KICK, vol=40)
    hats_8(p, base=14)
    cell(p, 60, CH_HAT, "G-4", I_OHH, vol=28, eff=8, ep=0xD0)
    bass_half(p, ["A-2", "G-2", "F-2", "E-2"], v=36)
    arps(p, [AM, Gmaj, Fmaj, Emaj], vol=20, every=8)
    pads(p, ["A-4", "G-4", "F-4", "E-4"], vol=16)
    bells(p, [
        (0, "E-6", 40), (8, "A-5", 24), (16, "D-6", 36), (24, "G-5", 22),
        (32, "C-6", 38), (40, "F-5", 22), (48, "B-5", 40), (56, "E-5", 28),
        (60, "G#5", 34),
    ])
    lead(p, [
        (4, "A-5", 30), (12, "E-5", 24), (20, "G-5", 28), (28, "D-5", 22),
        (36, "F-5", 28), (44, "C-5", 22), (52, "E-5", 34), (58, "G#5", 32),
        (62, "B-5", 28),
    ], delay=4, echo_ins=I_TRI, echo_div=2.0)
    chips(p, 56, ["E-4", "F-4", "G#4", "A-4", "B-4", "C-5", "D-5", "E-5"], vol0=20)


def pat7():
    p = 7
    drums(p, extra=(6, 10, 22, 26, 38, 42, 50, 54, 58), claps=True, ghost=False)
    hats_16(p, base=28)
    bass(p, ["D-2", "A-2", "F-2", "E-2"])
    arps(p, [Dm, AM, Fmaj, Emaj], vol=32)
    pads(p, ["D-5", "A-4", "F-4", "E-4"], vol=20)
    cell(p, 20, CH_FX, "C-4", I_RISER, vol=40)
    lead(p, [
        (0, "F-5", 48), (4, "A-5", 50), (8, "D-6", 54), (12, "E-6", 52),
        (16, "A-5", 50), (20, "C-6", 52), (24, "E-6", 56), (28, "A-6", 54),
        (32, "A-5", 52), (36, "C-6", 54), (40, "F-6", 58), (44, "G-6", 56),
        (48, "G#5", 54), (50, "B-5", 50), (52, "E-6", 58), (54, "G#6", 52),
        (56, "B-5", 50), (58, "E-6", 56), (60, "G#6", 58), (62, "B-6", 52),
    ], delay=2)
    crash(p, 0, vol=28, ch=CH_AUX)
    cell(p, 60, CH_SNR, "A-3", I_TOM, vol=44, eff=8, ep=0x40)
    cell(p, 62, CH_SNR, "C-3", I_TOM, vol=50, eff=8, ep=0x90)


def pat8():
    p = 8
    drums(p, extra=(6, 14, 22, 26, 38, 46, 54), claps=True, ghost=True)
    hats_16(p, base=30, open_on=(6, 14, 22, 30, 38, 46, 54, 62))
    bass(p, ["A-2", "F-2", "C-2", "G-2"], dist=True, v=50)
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=38)
    pads(p, ["A-5", "F-5", "C-5", "G-5"], vol=24, ins=I_PAD2)
    crash(p, 0, vol=44)
    crash(p, 32, vol=26)
    lead(p, [
        (0, "E-6", 58), (2, "D-6", 36), (4, "E-6", 54), (8, "A-6", 62),
        (12, "G-6", 52), (14, "E-6", 40),
        (16, "F-6", 58), (20, "C-6", 48), (24, "A-5", 52), (28, "C-6", 50),
        (32, "G-6", 60), (34, "E-6", 40), (36, "G-6", 54), (40, "A-6", 62),
        (44, "G-6", 50), (46, "E-6", 42),
        (48, "B-5", 58), (52, "G-6", 50), (56, "D-6", 52), (58, "B-5", 40),
        (60, "G-5", 46, 4, 0x54),
    ], delay=3, echo_ins=I_PULSE)
    for r, n, v in [
        (0, "C-6", 28), (8, "E-6", 30), (16, "A-5", 26), (24, "F-5", 26),
        (32, "E-6", 30), (40, "G-6", 32), (48, "D-6", 28), (56, "B-5", 26),
    ]:
        cell(p, r, CH_PLK, n, I_TRI, vol=v, eff=8, ep=0x28)
    ride4(p, vol=18)


def pat9():
    p = 9
    drums(p, extra=(10, 26, 42, 50, 54), claps=True, ghost=True, fill=True)
    hats_16(p, base=28, open_on=(14, 30, 46))
    bass(p, ["A-2", "G-2", "F-2", "E-2"])
    arps(p, [AM, Gmaj, Fmaj, Emaj], vol=32)
    pads(p, ["A-4", "G-4", "F-4", "G#4"], vol=20)
    lead(p, [
        (0, "A-6", 58), (4, "E-6", 46), (8, "C-6", 50), (12, "A-5", 40),
        (16, "B-5", 54), (20, "D-6", 50), (24, "G-6", 58), (28, "D-6", 42),
        (32, "A-6", 56), (36, "F-6", 50), (40, "C-6", 48), (44, "A-5", 40),
        (48, "G#5", 54), (50, "B-5", 48), (52, "E-6", 58), (54, "G#6", 50),
        (56, "B-6", 52), (58, "A-6", 48), (60, "G#6", 44), (62, "E-6", 40),
    ], delay=2, echo_ins=I_SAW)
    for r, n in [(0, "E-6"), (8, "A-5"), (16, "G-5"), (24, "B-5"),
                 (32, "F-5"), (40, "C-5"), (48, "E-5"), (56, "G#5")]:
        cell(p, r, CH_PLK, n, I_SQR, vol=22, eff=8, ep=0x24)
    crash(p, 0, vol=30)


def pat10():
    p = 10
    drums(p, extra=(26, 42, 54), claps=True, ghost=True)
    hats_16(p, base=26)
    bass(p, ["A-2", "F-2", "C-2", "G-2"])
    arps(p, [AM, Fmaj, Cmaj, Gmaj], vol=30)
    pads(p, ["A-5", "F-5", "C-5", "G-5"], vol=18)
    lead(p, [
        (0, "E-5", 52, 4, 0x42), (8, "A-5", 54), (12, "C-6", 48),
        (16, "D-6", 52), (20, "C-6", 44), (24, "A-5", 46), (28, "F-5", 36),
        (32, "G-5", 52), (36, "C-6", 54), (40, "E-6", 56), (44, "D-6", 44),
        (48, "B-5", 54), (52, "G-5", 46), (56, "A-5", 52), (60, "E-5", 42, 4, 0x43),
    ], delay=3)
    pluck_off(p, [
        ["E-4", "A-4", "C-5", "E-5"],
        ["F-4", "A-4", "C-5", "F-5"],
        ["G-4", "C-5", "E-5", "G-5"],
        ["G-4", "B-4", "D-5", "G-5"],
    ], vol=28)


def pat11():
    p = 11
    drums(p, extra=(6, 22, 38, 50, 54, 58), claps=True, ghost=True, fill=True)
    hats_16(p, base=28)
    bass(p, ["F-2", "G-2", "A-2", "E-2"])
    arps(p, [Fmaj, Gmaj, AM, Emaj], vol=32)
    pads(p, ["F-4", "G-4", "A-4", "E-4"], vol=20)
    lead(p, [
        (0, "C-6", 54), (4, "A-5", 46), (8, "F-5", 48), (12, "A-5", 44),
        (16, "D-6", 56), (20, "B-5", 46), (24, "G-5", 48), (28, "B-5", 44),
        (32, "E-6", 58), (36, "C-6", 48), (40, "A-5", 50), (44, "E-5", 40),
        (48, "G#5", 54), (50, "B-5", 48), (52, "E-6", 58), (56, "D-6", 50),
        (58, "C-6", 44), (60, "B-5", 40),
    ], delay=3, echo_ins=I_PULSE)
    bells(p, [(0, "A-5", 32), (32, "E-5", 22)])
    crash(p, 60, vol=36, ch=CH_AUX)
    # hard cut so the loop into groove is clean
    cut_lead(p, 63)
    off(p, 63, CH_ARP)
    off(p, 63, CH_PAD)
    off(p, 63, CH_PLK)


print("compose...")
pat0(); print(" p0", len(ops))
pat1(); print(" p1", len(ops))
pat2(); print(" p2", len(ops))
pat3(); print(" p3", len(ops))
pat4(); print(" p4", len(ops))
pat5(); print(" p5", len(ops))
pat6(); print(" p6", len(ops))
pat7(); print(" p7", len(ops))
pat8(); print(" p8", len(ops))
pat9(); print(" p9", len(ops))
pat10(); print(" p10", len(ops))
pat11(); print(" p11", len(ops))

head = []
for p in range(12):
    head.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
for i in range(12):
    head.append({"name": "order_set", "arguments": {"position": i, "pattern": i}})
head.append({"name": "song_set", "arguments": {
    "name": "Neon Cipher",
    "bpm": 150,
    "speed": 6,
    "length": 12,
    "loop_start": 2,
}})
ops = head + ops
print("total ops", len(ops))

os.makedirs("/workspace/src/batches", exist_ok=True)
CHUNK = 350
files = []
for i in range(0, len(ops), CHUNK):
    chunk = ops[i:i + CHUNK]
    fn = f"/workspace/src/batches/b{i // CHUNK:03d}.json"
    with open(fn, "w") as f:
        json.dump(chunk, f)
    files.append(fn)
print("chunks", len(files), "ops", len(ops))
with open("/workspace/src/batches/list.txt", "w") as f:
    f.write("\n".join(files))
