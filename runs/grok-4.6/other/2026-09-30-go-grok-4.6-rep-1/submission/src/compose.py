#!/usr/bin/env python3
"""Compose CRC SUNRISE — original keygen XM."""
import json
import os
import subprocess

SAMP = "/workspace/samples"
BATCH = "/tmp/ft2_batch.json"

calls = []


def ft(tool, **kwargs):
    calls.append({"name": tool, "arguments": kwargs})


def put(p, r, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    args = {"pattern": p, "row": r, "channel": ch}
    if note is not None:
        args["note"] = note
    if ins is not None:
        args["instrument"] = ins
    if vol is not None:
        args["volume"] = vol
    if fx is not None:
        args["effect"] = fx
    if fp is not None:
        args["effect_param"] = fp
    ft("pattern_set_cell", **args)


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------
KICK, SNARE, CLAP, CHAT, OHAT, CRASH, TOM = 1, 2, 3, 4, 5, 6, 7
BASS, PULSE, SAW, SQUARE, TRI, PAD, PLUCK, BELL, RISER = 8, 9, 10, 11, 12, 13, 14, 15, 16

SAMPLES = [
    (KICK, "kick.wav", "kick", 64, 128, 0, 0, 16),
    (SNARE, "snare.wav", "snare", 64, 160, 0, 0, 16),
    (CLAP, "clap.wav", "clap", 48, 80, 0, 0, 16),
    (CHAT, "chat.wav", "chat", 48, 28, 0, 0, 16),
    (OHAT, "ohat.wav", "ohat", 44, 230, 0, 0, 16),
    (CRASH, "crash.wav", "crash", 48, 128, 0, 0, 16),
    (TOM, "tom.wav", "tom", 52, 96, 0, 0, 16),
    (BASS, "bass.wav", "bass", 44, 128, 0, 32, 17),
    (PULSE, "pulse.wav", "pulse", 64, 190, 0, 32, 17),
    (SAW, "leadsaw.wav", "saw", 40, 48, 0, 32, 17),
    (SQUARE, "square.wav", "square", 24, 16, 0, 32, 17),
    (TRI, "tri.wav", "tri", 40, 210, 0, 32, 17),
    (PAD, "pad.wav", "pad", 20, 128, 0, 256, 17),
    (PLUCK, "pluck.wav", "pluck", 44, 30, 0, 0, 16),
    (BELL, "bell.wav", "bell", 42, 230, 0, 0, 16),
    (RISER, "riser.wav", "riser", 42, 128, 0, 0, 16),
]

NAMES = {
    KICK: "kick",
    SNARE: "snare",
    CLAP: "clap",
    CHAT: "closed hat",
    OHAT: "open hat",
    CRASH: "crash",
    TOM: "tom",
    BASS: "acid bass",
    PULSE: "pulse lead",
    SAW: "saw lead",
    SQUARE: "chip square",
    TRI: "soft tri",
    PAD: "organ pad",
    PLUCK: "arp pluck",
    BELL: "fm bell",
    RISER: "riser",
}

# ---------------------------------------------------------------------------
# Module setup
# ---------------------------------------------------------------------------
ft("module_new", channels=10, name="CRC SUNRISE")
ft("song_set", name="CRC SUNRISE", bpm=144, speed=4, length=12, loop_start=2)

for pos, pat in enumerate([0, 1, 2, 3, 4, 5, 2, 3, 4, 5, 6, 7]):
    ft("order_set", position=pos, pattern=pat)

for p in range(8):
    ft("pattern_set_length", pattern=p, rows=64)

for ins, fname, sname, vol, pan, lstart, llen, flags in SAMPLES:
    ft("instrument_set", instrument=ins, name=NAMES[ins])
    ft("sample_load", path=os.path.join(SAMP, fname), instrument=ins, sample=0)
    kw = dict(
        instrument=ins,
        sample=0,
        name=sname,
        volume=vol,
        panning=pan,
        finetune=0,
        relative_note=0,
        flags=flags,
    )
    if flags & 1:
        kw["loop_start"] = lstart
        kw["loop_length"] = llen
    ft("sample_set", **kw)

# ---------------------------------------------------------------------------
# Musical helpers
# ---------------------------------------------------------------------------

def hats_8th(p, bars=4, vol=32, start=0, delay_offbeats=False):
    for bar in range(bars):
        b = start + bar * 16
        for i in range(8):
            row = b + i * 2
            v = vol + 8 if i % 2 == 0 else vol - 4
            v = max(10, min(64, v))
            fx = fp = None
            if delay_offbeats and i % 2 == 1:
                fx, fp = 14, 0xD1  # ED1 note delay 1 tick — slight shuffle
            put(p, row, 2, "F-5", CHAT, v, fx, fp)


def hats_16th(p, bars=4, vol=26, start=0):
    for bar in range(bars):
        b = start + bar * 16
        for i in range(16):
            v = vol
            if i % 4 == 0:
                v = vol + 10
            elif i % 2 == 0:
                v = vol + 4
            else:
                v = vol - 4
            put(p, b + i, 2, "F-5", CHAT, max(8, min(64, v)))


def kicks(p, rows, note="C-4", vol=64):
    for r in rows:
        put(p, r, 0, note, KICK, vol)


def snares(p, rows, vol=56, ins=None):
    ins = ins or SNARE
    for r in rows:
        put(p, r, 1, "C-4", ins, vol)


def open_hats(p, rows, vol=34):
    for r in rows:
        put(p, r, 3, "C-5", OHAT, vol)


def crash(p, row, vol=48, note="C-5"):
    put(p, row, 3, note, CRASH, vol)


# bass line: list of (offset_in_bar, note, vol)
def bass_bar(p, bar_row, events):
    for off, note, vol in events:
        put(p, bar_row + off, 4, note, BASS, vol)


def pad_chord(p, row, note, vol=30):
    put(p, row, 8, note, PAD, vol)


def arp_pattern(p, bar_row, notes4, vol=38, ch=7):
    """4-note cell as 16ths x4 = 16 rows, ping-pong panned."""
    for i in range(16):
        n = notes4[i % 4]
        v = vol + (6 if i % 4 == 0 else 0)
        pan = 0x30 if (i % 2 == 0) else 0xD0
        put(p, bar_row + i, ch, n, PLUCK, min(64, v), 8, pan)


def lead(p, row, note, ins=PULSE, vol=60, fx=None, fp=None, ch=5):
    put(p, row, ch, note, ins, vol, fx, fp)


def harm(p, row, note, ins=SAW, vol=32, fx=None, fp=None, ch=6):
    put(p, row, ch, note, ins, vol, fx, fp)


def bell(p, row, note, vol=40, ch=9):
    put(p, row, ch, note, BELL, vol)


def off(p, row, ch):
    put(p, row, ch, "OFF")


# Groove templates per bar (16 rows)
KICK_VERSE = [0, 4, 8, 12]
KICK_DRIVE = [0, 4, 6, 8, 12, 14]
KICK_CHORUS = [0, 3, 4, 8, 11, 12]
KICK_HALF = [0, 8]
KICK_BUILD = [0, 4, 8, 10, 12, 14]
SNARE_STD = [4, 12]
SNARE_GHOST_EXTRA = [4, 10, 12]  # 10 ghost handled separately
OHAT_STD = [2, 6, 10, 14]
OHAT_SPARSE = [6, 14]


def groove_verse(p, start=0, bars=4, extra_kick=False):
    for bar in range(bars):
        b = start + bar * 16
        ks = KICK_DRIVE if extra_kick else KICK_VERSE
        for k in ks:
            put(p, b + k, 0, "C-4", KICK, 64 if k % 4 == 0 else 50)
        put(p, b + 4, 1, "C-4", SNARE, 54)
        put(p, b + 12, 1, "C-4", SNARE, 58)
        # ghost
        put(p, b + 10, 1, "C-4", SNARE, 22)
        for h in OHAT_STD:
            put(p, b + h, 3, "C-5", OHAT, 26)


def groove_chorus(p, start=0, bars=4):
    for bar in range(bars):
        b = start + bar * 16
        for k in KICK_CHORUS:
            put(p, b + k, 0, "C-4", KICK, 64 if k in (0, 8) else 48)
        put(p, b + 4, 1, "C-4", SNARE, 58)
        put(p, b + 12, 1, "C-4", SNARE, 60)
        put(p, b + 10, 1, "C-4", SNARE, 24)
        # clap layered on snare beats via ch 3 would fight ohats; put clap on snare channel? can't.
        # use ch 9 sometimes... bells live there. Clap on ch 3 at 4 and 12, ohats on 2,6,10,14.
        put(p, b + 4, 3, "C-4", CLAP, 42)
        put(p, b + 12, 3, "C-4", CLAP, 46)
        put(p, b + 2, 3, "C-5", OHAT, 28)
        put(p, b + 6, 3, "C-5", OHAT, 24)
        put(p, b + 10, 3, "C-5", OHAT, 24)
        put(p, b + 14, 3, "C-5", OHAT, 26)


def fill_toms(p, start_row=60):
    """Last 4 rows tom/snare fill. Overwrites ch 0,1,3."""
    put(p, start_row + 0, 0, "C-4", KICK, 50)
    put(p, start_row + 0, 3, "A-4", TOM, 48)
    put(p, start_row + 1, 3, "F-4", TOM, 50)
    put(p, start_row + 2, 1, "C-4", SNARE, 40)
    put(p, start_row + 2, 3, "D-4", TOM, 52)
    put(p, start_row + 3, 0, "C-4", KICK, 64)
    put(p, start_row + 3, 1, "C-4", SNARE, 60)
    put(p, start_row + 3, 3, "C-5", CRASH, 40)


# Bass riffs (8th notes) for each chord
def bass_Am(p, b, drive=True):
    if drive:
        seq = [(0, "A-2", 46), (2, "A-3", 36), (4, "A-2", 42), (6, "E-3", 34),
               (8, "A-2", 46), (10, "A-3", 38), (12, "G-2", 40), (14, "A-2", 42)]
    else:
        seq = [(0, "A-2", 34), (4, "A-3", 38), (8, "A-2", 42), (12, "E-3", 36)]
    bass_bar(p, b, seq)


def bass_F(p, b, drive=True):
    if drive:
        seq = [(0, "F-2", 46), (2, "F-3", 36), (4, "F-2", 42), (6, "C-3", 34),
               (8, "F-2", 46), (10, "F-3", 38), (12, "E-2", 40), (14, "F-2", 42)]
    else:
        seq = [(0, "F-2", 34), (4, "F-3", 38), (8, "F-2", 42), (12, "C-3", 36)]
    bass_bar(p, b, seq)


def bass_C(p, b, drive=True):
    if drive:
        seq = [(0, "C-3", 46), (2, "C-4", 36), (4, "C-3", 42), (6, "G-3", 34),
               (8, "C-3", 46), (10, "E-3", 38), (12, "G-3", 40), (14, "C-4", 42)]
    else:
        seq = [(0, "C-3", 34), (4, "C-4", 38), (8, "G-3", 42), (12, "C-3", 36)]
    bass_bar(p, b, seq)


def bass_G(p, b, drive=True):
    if drive:
        seq = [(0, "G-2", 46), (2, "G-3", 36), (4, "G-2", 42), (6, "D-3", 34),
               (8, "G-2", 46), (10, "B-2", 38), (12, "D-3", 40), (14, "G-3", 42)]
    else:
        seq = [(0, "G-2", 34), (4, "G-3", 38), (8, "D-3", 42), (12, "G-2", 36)]
    bass_bar(p, b, seq)


def bass_Dm(p, b, drive=True):
    if drive:
        seq = [(0, "D-3", 46), (2, "D-4", 36), (4, "D-3", 42), (6, "A-3", 34),
               (8, "D-3", 46), (10, "D-4", 38), (12, "C-3", 40), (14, "D-3", 42)]
    else:
        seq = [(0, "D-3", 34), (4, "D-4", 38), (8, "A-3", 42), (12, "D-3", 36)]
    bass_bar(p, b, seq)


def bass_E(p, b, drive=True):
    if drive:
        seq = [(0, "E-2", 46), (2, "E-3", 36), (4, "E-2", 42), (6, "B-2", 34),
               (8, "E-2", 36), (10, "E-3", 40), (12, "G#2", 40), (14, "B-2", 42)]
    else:
        seq = [(0, "E-2", 34), (4, "E-3", 38), (8, "B-2", 42), (12, "E-2", 36)]
    bass_bar(p, b, seq)


# G# note naming: G#1
# FT2 uses G#1 or G#1 — test used C-4 and C#4 style. G#1 it is.

ARP_Am = ["A-4", "E-5", "A-5", "E-5"]
ARP_F = ["F-4", "C-5", "F-5", "C-5"]
ARP_C = ["C-5", "G-5", "C-6", "G-5"]
ARP_G = ["G-4", "D-5", "G-5", "D-5"]
ARP_Dm = ["D-4", "A-4", "D-5", "A-4"]
ARP_E = ["E-4", "B-4", "E-5", "B-4"]

# Square bubble arp (effect 0) on long notes — used sparingly on ch 6 during intro/break


# ===========================================================================
# PATTERN 0 — INTRO
# ===========================================================================
# Bar 0: crash + kick + pad + hats + hook bells — start immediately
pad_chord(0, 0, "A-3", 24)
hats_8th(0, bars=1, vol=28, start=0)
kicks(0, [0, 8], vol=54)
crash(0, 0, 40)
open_hats(0, [6, 14], 28)
bell(0, 0, "E-5", 48)
bell(0, 4, "A-5", 40)
bell(0, 8, "G-5", 44)
bell(0, 12, "E-5", 36)
bass_Am(0, 0, drive=False)
# quiet pulse hint
lead(0, 0, "E-5", PULSE, 28)
lead(0, 8, "A-5", PULSE, 30)

# Bar 1: more kick, ohats, pad F
pad_chord(0, 16, "F-3", 24)
hats_8th(0, bars=1, vol=30, start=16)
kicks(0, [16, 20, 24, 28], vol=56)
open_hats(0, [18, 22, 26, 30], 28)
bell(0, 16, "F-5", 44)
bell(0, 20, "A-5", 38)
bell(0, 24, "C-6", 46)
bell(0, 28, "A-5", 36)
bass_F(0, 16, drive=False)
lead(0, 16, "F-5", PULSE, 32)
lead(0, 24, "A-5", PULSE, 36)

# Bar 2: snare in, bass drive, pad C
pad_chord(0, 32, "C-3", 24)
hats_8th(0, bars=1, vol=32, start=32)
kicks(0, [32, 36, 40, 44], vol=60)
snares(0, [36, 44], vol=50)
open_hats(0, [34, 38, 42, 46], 30)
bass_C(0, 32, drive=True)
bell(0, 32, "G-5", 44)
bell(0, 40, "C-6", 48)
lead(0, 32, "G-5", PULSE, 40)
lead(0, 36, "C-6", PULSE, 44)
lead(0, 40, "E-6", PULSE, 48)
lead(0, 44, "D-6", PULSE, 42)

# Bar 3: full-ish, pad G, fill at end
pad_chord(0, 48, "G-3", 24)
hats_8th(0, bars=1, vol=34, start=48)
kicks(0, [48, 52, 56, 60, 62], vol=62)
snares(0, [52], vol=54)
put(0, 48, 3, "C-5", CRASH, 42)
bass_G(0, 48, drive=True)
# snare roll 60-63
put(0, 60, 1, "C-4", SNARE, 40)
put(0, 61, 1, "C-4", SNARE, 48)
put(0, 62, 1, "C-4", SNARE, 54)
put(0, 63, 1, "C-4", SNARE, 62)
put(0, 63, 0, "C-4", KICK, 64)
lead(0, 48, "B-5", PULSE, 50)
lead(0, 52, "D-6", PULSE, 54)
lead(0, 56, "G-6", PULSE, 58)
lead(0, 60, "B-6", PULSE, 60)
off(0, 63, 5)

# ===========================================================================
# PATTERN 1 — BUILD (groove + bass + arp, no main lead)
# ===========================================================================
groove_verse(1, 0, 4, extra_kick=False)
hats_8th(1, bars=4, vol=30, start=0, delay_offbeats=True)
crash(1, 0, 48)

bass_Am(1, 0, True)
bass_F(1, 16, True)
bass_C(1, 32, True)
bass_G(1, 48, True)

pad_chord(1, 0, "A-3", 24)
pad_chord(1, 16, "F-3", 24)
pad_chord(1, 32, "C-3", 24)
pad_chord(1, 48, "G-3", 24)

arp_pattern(1, 0, ARP_Am, vol=32)
arp_pattern(1, 16, ARP_F, vol=32)
arp_pattern(1, 32, ARP_C, vol=34)
arp_pattern(1, 48, ARP_G, vol=34)

# square bubble under pad (ch 6) with arpeggio effect
put(1, 0, 6, "A-4", SQUARE, 20, 0, 0x37)   # minor
put(1, 16, 6, "F-4", SQUARE, 20, 0, 0x47)   # major
put(1, 32, 6, "C-5", SQUARE, 20, 0, 0x47)
put(1, 48, 6, "G-4", SQUARE, 20, 0, 0x47)
off(1, 63, 6)

# rising bells
bell(1, 0, "A-5", 22)
bell(1, 16, "C-6", 24)
bell(1, 32, "E-6", 28)
bell(1, 48, "G-6", 32)
bell(1, 56, "A-6", 30)

fill_toms(1, 60)
# overwrite crash on 63 already in fill

# ===========================================================================
# PATTERN 2 — VERSE A  (Am F C G) main melody
# ===========================================================================
groove_verse(2, 0, 4, extra_kick=False)
hats_8th(2, bars=4, vol=34, start=0)
crash(2, 0, 40)

bass_Am(2, 0, True)
bass_F(2, 16, True)
bass_C(2, 32, True)
bass_G(2, 48, True)

pad_chord(2, 0, "A-3", 22)
pad_chord(2, 16, "F-3", 22)
pad_chord(2, 32, "C-3", 22)
pad_chord(2, 48, "G-3", 22)

arp_pattern(2, 0, ARP_Am, 28)
arp_pattern(2, 16, ARP_F, 28)
arp_pattern(2, 32, ARP_C, 30)
arp_pattern(2, 48, ARP_G, 28)

# LEAD verse 1
# Am
lead(2, 0, "E-5", PULSE, 56)
lead(2, 4, "A-5", PULSE, 58)
lead(2, 8, "G-5", PULSE, 50)
lead(2, 10, "E-5", PULSE, 48)
lead(2, 12, "D-5", PULSE, 44)
lead(2, 14, "E-5", PULSE, 50)
# F
lead(2, 16, "F-5", PULSE, 56)
lead(2, 20, "A-5", PULSE, 58)
lead(2, 24, "C-6", PULSE, 60, 4, 0x43)  # vibrato
lead(2, 28, "B-5", PULSE, 50)
lead(2, 30, "A-5", PULSE, 46)
# C
lead(2, 32, "G-5", PULSE, 56)
lead(2, 36, "C-6", PULSE, 58)
lead(2, 40, "E-6", PULSE, 60, 4, 0x54)
lead(2, 44, "D-6", PULSE, 52)
lead(2, 46, "C-6", PULSE, 48)
# G
lead(2, 48, "B-5", PULSE, 56)
lead(2, 50, "D-6", PULSE, 52)
lead(2, 52, "G-5", PULSE, 44)
lead(2, 54, "B-5", PULSE, 50)
lead(2, 56, "C-6", PULSE, 58)
lead(2, 58, "B-5", PULSE, 50)
lead(2, 60, "A-5", PULSE, 46)
lead(2, 62, "G-5", PULSE, 50)

# quiet harmony (thirds)
harm(2, 0, "C-5", SAW, 22)
harm(2, 4, "E-5", SAW, 24)
harm(2, 8, "E-5", SAW, 20)
harm(2, 10, "C-5", SAW, 20)
harm(2, 16, "C-5", SAW, 22)
harm(2, 20, "F-5", SAW, 24)
harm(2, 24, "A-5", SAW, 26)
harm(2, 32, "E-5", SAW, 22)
harm(2, 36, "G-5", SAW, 24)
harm(2, 40, "C-6", SAW, 26, 4, 0x42)
harm(2, 48, "G-5", SAW, 22)
harm(2, 52, "D-5", SAW, 20)
harm(2, 56, "A-5", SAW, 24)
off(2, 63, 6)

# sparse bells answering
bell(2, 8, "A-6", 20)
bell(2, 24, "C-7", 22)
bell(2, 40, "E-6", 24)
bell(2, 56, "G-6", 22)

# ===========================================================================
# PATTERN 3 — VERSE A2  (same harmony, busier, harmony full)
# ===========================================================================
groove_verse(3, 0, 4, extra_kick=True)
hats_16th(3, bars=4, vol=28, start=0)
crash(3, 0, 38)

bass_Am(3, 0, True)
bass_F(3, 16, True)
bass_C(3, 32, True)
bass_G(3, 48, True)

pad_chord(3, 0, "A-3", 24)
pad_chord(3, 16, "F-3", 24)
pad_chord(3, 32, "C-3", 24)
pad_chord(3, 48, "G-3", 24)

arp_pattern(3, 0, ARP_Am, 30)
arp_pattern(3, 16, ARP_F, 30)
arp_pattern(3, 32, ARP_C, 32)
arp_pattern(3, 48, ARP_G, 30)

# lead with extra 16th ornaments
lead(3, 0, "E-5", PULSE, 56)
lead(3, 2, "G-5", PULSE, 40)  # grace
lead(3, 4, "A-5", PULSE, 58)
lead(3, 6, "C-6", PULSE, 44)
lead(3, 8, "B-5", PULSE, 52)
lead(3, 10, "A-5", PULSE, 46)
lead(3, 12, "G-5", PULSE, 48)
lead(3, 14, "E-5", PULSE, 50)

lead(3, 16, "F-5", PULSE, 56)
lead(3, 18, "A-5", PULSE, 42)
lead(3, 20, "C-6", PULSE, 58)
lead(3, 22, "E-6", PULSE, 46)
lead(3, 24, "D-6", PULSE, 54, 4, 0x43)
lead(3, 28, "C-6", PULSE, 50)
lead(3, 30, "A-5", PULSE, 46)

lead(3, 32, "G-5", PULSE, 56)
lead(3, 34, "C-6", PULSE, 42)
lead(3, 36, "E-6", PULSE, 58)
lead(3, 38, "G-6", PULSE, 50)
lead(3, 40, "F-6", PULSE, 54)
lead(3, 42, "E-6", PULSE, 50)
lead(3, 44, "D-6", PULSE, 48)
lead(3, 46, "C-6", PULSE, 46)

lead(3, 48, "D-6", PULSE, 56)
lead(3, 50, "B-5", PULSE, 50)
lead(3, 52, "G-6", PULSE, 58)
lead(3, 54, "F-6", PULSE, 50)
lead(3, 56, "E-6", PULSE, 54)
lead(3, 58, "D-6", PULSE, 48)
lead(3, 60, "C-6", PULSE, 50)
lead(3, 62, "B-5", PULSE, 52)

# harmony thirds / sixths fuller
harm(3, 0, "C-5", SAW, 26)
harm(3, 4, "E-5", SAW, 28)
harm(3, 8, "G-5", SAW, 24)
harm(3, 12, "E-5", SAW, 24)
harm(3, 16, "C-5", SAW, 26)
harm(3, 20, "F-5", SAW, 28)
harm(3, 24, "A-5", SAW, 30, 4, 0x42)
harm(3, 32, "E-5", SAW, 26)
harm(3, 36, "G-5", SAW, 28)
harm(3, 40, "C-6", SAW, 30)
harm(3, 44, "B-5", SAW, 26)
harm(3, 48, "B-5", SAW, 26)
harm(3, 52, "D-6", SAW, 28)
harm(3, 56, "C-6", SAW, 26)
harm(3, 60, "A-5", SAW, 24)

# echo bells 2 rows later (8th delay)
for r, n, v in [
    (2, "E-6", 18), (6, "A-6", 20), (10, "B-6", 16),
    (18, "F-6", 18), (22, "C-7", 20), (26, "D-7", 16),
    (34, "G-6", 18), (38, "E-7", 22), (42, "F-6", 16),
    (50, "D-6", 18), (54, "G-6", 20), (58, "E-6", 16),
]:
    bell(3, r, n, v)

fill_toms(3, 60)

# ===========================================================================
# PATTERN 4 — CHORUS  (C G Am F)
# ===========================================================================
groove_chorus(4, 0, 4)
hats_16th(4, bars=4, vol=30, start=0)
crash(4, 0, 50)
# extra crash mid
put(4, 32, 3, "G-4", CRASH, 32)  # fights clap? row 32 is bar 3 row 0, clap not on 0. ch3 row 32 empty. OK.

bass_C(4, 0, True)
bass_G(4, 16, True)
bass_Am(4, 32, True)
bass_F(4, 48, True)

pad_chord(4, 0, "C-3", 26)
pad_chord(4, 16, "G-3", 26)
pad_chord(4, 32, "A-3", 26)
pad_chord(4, 48, "F-3", 26)

arp_pattern(4, 0, ARP_C, 32)
arp_pattern(4, 16, ARP_G, 32)
arp_pattern(4, 32, ARP_Am, 32)
arp_pattern(4, 48, ARP_F, 32)

# Chorus lead — anthemic, saw+pulse: pulse on 5, saw doubles on 6 an octave or third
# C
lead(4, 0, "E-6", PULSE, 60)
lead(4, 4, "D-6", PULSE, 52)
lead(4, 6, "C-6", PULSE, 50)
lead(4, 8, "G-5", PULSE, 48)
lead(4, 12, "A-5", PULSE, 54)
lead(4, 14, "C-6", PULSE, 56)
# G
lead(4, 16, "D-6", PULSE, 60)
lead(4, 20, "G-6", PULSE, 62, 4, 0x54)
lead(4, 24, "F-6", PULSE, 54)
lead(4, 26, "E-6", PULSE, 50)
lead(4, 28, "D-6", PULSE, 48)
lead(4, 30, "B-5", PULSE, 46)
# Am
lead(4, 32, "C-6", PULSE, 60)
lead(4, 36, "E-6", PULSE, 58)
lead(4, 40, "A-6", PULSE, 62, 4, 0x55)
lead(4, 44, "G-6", PULSE, 54)
lead(4, 46, "E-6", PULSE, 50)
# F
lead(4, 48, "F-6", PULSE, 60)
lead(4, 52, "E-6", PULSE, 54)
lead(4, 54, "D-6", PULSE, 50)
lead(4, 56, "C-6", PULSE, 56)
lead(4, 58, "A-5", PULSE, 48)
lead(4, 60, "B-5", PULSE, 50)
lead(4, 62, "C-6", PULSE, 54)

# saw harmony a third below / unison octave
harm(4, 0, "C-6", SAW, 30)
harm(4, 4, "B-5", SAW, 26)
harm(4, 8, "E-5", SAW, 24)
harm(4, 12, "F-5", SAW, 26)
harm(4, 16, "B-5", SAW, 30)
harm(4, 20, "D-6", SAW, 32, 4, 0x43)
harm(4, 24, "D-6", SAW, 26)
harm(4, 32, "A-5", SAW, 30)
harm(4, 36, "C-6", SAW, 28)
harm(4, 40, "E-6", SAW, 32, 4, 0x44)
harm(4, 48, "C-6", SAW, 30)
harm(4, 52, "C-6", SAW, 26)
harm(4, 56, "A-5", SAW, 28)
harm(4, 60, "G-5", SAW, 26)

bell(4, 0, "E-6", 28)
bell(4, 16, "G-6", 30)
bell(4, 32, "A-6", 32)
bell(4, 40, "E-7", 26)
bell(4, 48, "F-6", 28)

# ===========================================================================
# PATTERN 5 — CHORUS 2 (call/response, max energy)
# ===========================================================================
groove_chorus(5, 0, 4)
hats_16th(5, bars=4, vol=32, start=0)
crash(5, 0, 50)
put(5, 16, 3, "C-5", CRASH, 28)  # wait ch3 row 16 is start of bar2, clap not there. But ohats 2,6,10,14 only. OK.

bass_C(5, 0, True)
bass_G(5, 16, True)
bass_Am(5, 32, True)
bass_F(5, 48, True)

pad_chord(5, 0, "C-3", 26)
pad_chord(5, 16, "G-3", 26)
pad_chord(5, 32, "A-3", 26)
pad_chord(5, 48, "F-3", 26)

arp_pattern(5, 0, ARP_C, 34)
arp_pattern(5, 16, ARP_G, 34)
arp_pattern(5, 32, ARP_Am, 34)
arp_pattern(5, 48, ARP_F, 34)

# lead variation — more runs
lead(5, 0, "G-6", PULSE, 60)
lead(5, 2, "E-6", PULSE, 44)
lead(5, 4, "C-6", PULSE, 50)
lead(5, 6, "D-6", PULSE, 48)
lead(5, 8, "E-6", PULSE, 58, 4, 0x43)
lead(5, 12, "G-6", PULSE, 56)
lead(5, 14, "A-6", PULSE, 58)

lead(5, 16, "B-6", PULSE, 62)
lead(5, 20, "G-6", PULSE, 54)
lead(5, 22, "D-6", PULSE, 46)
lead(5, 24, "G-6", PULSE, 56)
lead(5, 28, "F-6", PULSE, 52)
lead(5, 30, "D-6", PULSE, 48)

lead(5, 32, "E-6", PULSE, 60)
lead(5, 34, "C-6", PULSE, 44)
lead(5, 36, "A-6", PULSE, 58)
lead(5, 38, "C-7", PULSE, 50)
lead(5, 40, "B-6", PULSE, 56, 4, 0x54)
lead(5, 44, "A-6", PULSE, 52)
lead(5, 46, "E-6", PULSE, 48)

lead(5, 48, "F-6", PULSE, 60)
lead(5, 50, "A-6", PULSE, 50)
lead(5, 52, "C-7", PULSE, 58)
lead(5, 54, "A-6", PULSE, 48)
lead(5, 56, "G-6", PULSE, 54)
lead(5, 58, "F-6", PULSE, 48)
lead(5, 60, "E-6", PULSE, 50)
lead(5, 62, "D-6", PULSE, 52)

# saw counter-melody
harm(5, 0, "E-6", SAW, 28)
harm(5, 8, "C-6", SAW, 26)
harm(5, 16, "D-6", SAW, 30)
harm(5, 24, "B-5", SAW, 26)
harm(5, 32, "C-6", SAW, 28)
harm(5, 40, "E-6", SAW, 30, 4, 0x43)
harm(5, 48, "C-6", SAW, 28)
harm(5, 56, "A-5", SAW, 26)

# bell call-response (on the off phrases)
bell(5, 4, "G-6", 30)
bell(5, 12, "E-6", 26)
bell(5, 20, "B-6", 32)
bell(5, 28, "G-6", 26)
bell(5, 36, "A-6", 30)
bell(5, 44, "E-7", 28)
bell(5, 52, "F-6", 30)
bell(5, 60, "C-6", 26)

fill_toms(5, 60)

# ===========================================================================
# PATTERN 6 — BREAK  (Dm G C E)  half-time then build
# ===========================================================================
# bars 0-1 half time, bars 2-3 build

# bar 0 Dm half
kicks(6, [0, 8], 58)
snares(6, [8], 40)
hats_8th(6, bars=1, vol=22, start=0)
pad_chord(6, 0, "D-3", 20)
bass_Dm(6, 0, drive=False)
# arp featured, higher
arp_pattern(6, 0, ["D-5", "A-5", "D-6", "A-5"], 36)
# tri soft melody
put(6, 0, 5, "A-5", TRI, 40)
put(6, 4, 5, "D-6", TRI, 36)
put(6, 8, 5, "F-6", TRI, 42, 4, 0x53)
put(6, 12, 5, "E-6", TRI, 36)
bell(6, 0, "D-6", 24)

# bar 1 G half
kicks(6, [16, 24], 58)
snares(6, [24], 42)
hats_8th(6, bars=1, vol=24, start=16)
pad_chord(6, 16, "G-3", 22)
bass_G(6, 16, drive=False)
arp_pattern(6, 16, ["G-4", "D-5", "G-5", "B-5"], 36)
put(6, 16, 5, "D-6", TRI, 40)
put(6, 20, 5, "G-6", TRI, 38)
put(6, 24, 5, "B-6", TRI, 44, 4, 0x53)
put(6, 28, 5, "A-6", TRI, 38)
bell(6, 16, "G-6", 26)

# bar 2 C — drums return, riser starts
kicks(6, [32, 36, 40, 44], 60)
snares(6, [36, 44], 50)
hats_8th(6, bars=1, vol=30, start=32)
open_hats(6, [34, 38, 42, 46], 26)
pad_chord(6, 32, "C-3", 24)
bass_C(6, 32, True)
arp_pattern(6, 32, ARP_C, 32)
put(6, 32, 5, "E-6", PULSE, 48)
put(6, 36, 5, "G-6", PULSE, 52)
put(6, 40, 5, "C-7", PULSE, 56, 4, 0x54)
put(6, 44, 5, "B-6", PULSE, 50)
# riser on ch 9 (bells) — long sample
put(6, 32, 9, "C-4", RISER, 44)
# saw drone
put(6, 32, 6, "C-5", SAW, 24, 4, 0x62)

# bar 3 E major — dominant build, snare roll
kicks(6, [48, 52, 56, 58, 60, 62], 62)
hats_16th(6, bars=1, vol=30, start=48)
pad_chord(6, 48, "E-3", 26)
bass_E(6, 48, True)
arp_pattern(6, 48, ARP_E, 34)
put(6, 48, 5, "E-6", PULSE, 56)
put(6, 50, 5, "G#6", PULSE, 52)
put(6, 52, 5, "B-6", PULSE, 58)
put(6, 54, 5, "E-7", PULSE, 60)
put(6, 56, 5, "D-7", PULSE, 54)
put(6, 58, 5, "B-6", PULSE, 52)
put(6, 60, 5, "G#6", PULSE, 56)
put(6, 62, 5, "E-6", PULSE, 58)
# snare roll
for i, v in enumerate([28, 32, 36, 40, 44, 48, 52, 58]):
    put(6, 56 + i, 1, "C-4", SNARE, v)
put(6, 48, 3, "C-5", CRASH, 30)
put(6, 63, 0, "C-4", KICK, 64)
put(6, 63, 3, "C-5", CRASH, 50)
# harmony E major
put(6, 48, 6, "G#5", SAW, 28, 4, 0x54)
put(6, 56, 6, "B-5", SAW, 30)

# ===========================================================================
# PATTERN 7 — FINALE  Am F C E   (resolves E -> Am of pattern 2)
# ===========================================================================
groove_chorus(7, 0, 3)  # first 3 bars chorus groove
hats_16th(7, bars=3, vol=32, start=0)
crash(7, 0, 52)

bass_Am(7, 0, True)
bass_F(7, 16, True)
bass_C(7, 32, True)

pad_chord(7, 0, "A-3", 26)
pad_chord(7, 16, "F-3", 26)
pad_chord(7, 32, "C-3", 26)

arp_pattern(7, 0, ARP_Am, 34)
arp_pattern(7, 16, ARP_F, 34)
arp_pattern(7, 32, ARP_C, 34)

# finale lead — verse hook an octave up then into E
lead(7, 0, "E-6", PULSE, 62)
lead(7, 2, "A-6", PULSE, 48)
lead(7, 4, "C-7", PULSE, 58)
lead(7, 8, "B-6", PULSE, 54)
lead(7, 10, "A-6", PULSE, 50)
lead(7, 12, "G-6", PULSE, 52)
lead(7, 14, "E-6", PULSE, 50)

lead(7, 16, "F-6", PULSE, 60)
lead(7, 20, "A-6", PULSE, 58)
lead(7, 24, "C-7", PULSE, 62, 4, 0x54)
lead(7, 28, "D-7", PULSE, 54)
lead(7, 30, "C-7", PULSE, 50)

lead(7, 32, "G-6", PULSE, 60)
lead(7, 36, "C-7", PULSE, 58)
lead(7, 40, "E-7", PULSE, 64, 4, 0x55)
lead(7, 44, "D-7", PULSE, 54)
lead(7, 46, "C-7", PULSE, 50)

harm(7, 0, "C-6", SAW, 30)
harm(7, 4, "E-6", SAW, 32)
harm(7, 8, "G-6", SAW, 28)
harm(7, 16, "C-6", SAW, 30)
harm(7, 24, "A-6", SAW, 32, 4, 0x43)
harm(7, 32, "E-6", SAW, 30)
harm(7, 40, "G-6", SAW, 34, 4, 0x44)

bell(7, 0, "A-6", 28)
bell(7, 8, "E-7", 24)
bell(7, 16, "F-6", 26)
bell(7, 24, "C-7", 30)
bell(7, 32, "G-6", 26)
bell(7, 40, "E-7", 32)

# last bar: E major dominant, setup loop to Am (pattern 2)
# drums: driving into the downbeat
kicks(7, [48, 52, 56, 58, 60, 62], 64)
put(7, 52, 1, "C-4", SNARE, 50)
put(7, 56, 1, "C-4", SNARE, 36)
put(7, 58, 1, "C-4", SNARE, 44)
put(7, 60, 1, "C-4", SNARE, 52)
put(7, 62, 1, "C-4", SNARE, 58)
put(7, 63, 1, "C-4", SNARE, 62)
hats_8th(7, bars=1, vol=32, start=48)
put(7, 48, 3, "C-5", CRASH, 46)
pad_chord(7, 48, "E-3", 28)
bass_E(7, 48, True)
arp_pattern(7, 48, ARP_E, 36)

# lead: G# run that wants to resolve to A/E of verse
lead(7, 48, "E-6", PULSE, 60)
lead(7, 50, "G#6", PULSE, 54)
lead(7, 52, "B-6", PULSE, 58)
lead(7, 54, "E-7", PULSE, 62)
lead(7, 56, "D#7", PULSE, 50)
lead(7, 58, "B-6", PULSE, 52)
lead(7, 60, "G#6", PULSE, 56)
lead(7, 62, "E-6", PULSE, 58)  # resolves to E-5 of verse an octave down — still E, verse starts E-5. Nice.

harm(7, 48, "G#5", SAW, 30, 4, 0x54)
harm(7, 56, "B-5", SAW, 28)
bell(7, 48, "E-6", 32)
bell(7, 56, "B-6", 28)

# note: looping samples (lead, bass, pad, arp pluck is one-shot) will continue
# across the loop. Pattern 2 retriggers everything on row 0 so we should be clean.
# Cut looping square/saw/pulse/pad by retriggering on P2 row 0 which we do.

# ===========================================================================
# Save batch and execute
# ===========================================================================
print(f"Prepared {len(calls)} FT2 calls")
with open(BATCH, "w") as f:
    json.dump(calls, f)
print(f"Wrote {BATCH} ({os.path.getsize(BATCH)} bytes)")

r = subprocess.run(["ft2", "batch", BATCH], capture_output=True, text=True)
print("batch return", r.returncode)
# print last part of output
out = r.stdout
print("stdout tail:", out[-1500:] if out else "(empty)")
if r.stderr:
    print("stderr:", r.stderr[-1000:])

# save module
r2 = subprocess.run(
    ["ft2", "call", "module_save", json.dumps({"path": "/workspace/submission/tune.xm", "format": "xm"})],
    capture_output=True, text=True,
)
print("save", r2.stdout[-400:] if r2.stdout else r2.stderr)

r3 = subprocess.run(["ft2", "call", "module_info", "{}"], capture_output=True, text=True)
print("info", r3.stdout[-400:])
