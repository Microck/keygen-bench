import os
import json
import base64
import subprocess
import numpy as np
from synth import build_bank

NOTE_NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
ALIAS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}

def note_str(name):
    if name in ("OFF", "off", "==="):
        return "OFF"
    if len(name) == 3 and name[:2] in NOTE_NAMES:
        return name
    if len(name) == 2:
        pitch, octv = name[0] + "-", name[1]
    elif len(name) == 3:
        p = name[:2]
        pitch = ALIAS.get(p, p)
        if len(pitch) == 1:
            pitch += "-"
        octv = name[2]
    else:
        raise ValueError(f"Bad note: {name}")
    assert pitch in NOTE_NAMES, f"Invalid pitch {pitch} from {name}"
    return f"{pitch}{octv}"

def note_to_midi(name):
    s = note_str(name)
    if s == "OFF":
        return None
    p, o = s[:2], int(s[2])
    return (o + 1) * 12 + NOTE_NAMES.index(p)

def midi_to_note(m):
    o = (m // 12) - 1
    p = NOTE_NAMES[m % 12]
    return f"{p}{o}"

def transpose(name, semi):
    return midi_to_note(note_to_midi(name) + semi)

# Instrument IDs
I_KICK     = 1
I_SNARE    = 2
I_HATC     = 3
I_HATO     = 4
I_CRASH    = 5
I_TOM      = 6
I_UPLIFT   = 7
I_BASS_FM  = 8
I_BASS_SQ  = 9
I_LEAD_PWM = 10
I_ARP      = 11
I_LEAD_THN = 12
I_BELL     = 13
I_PAD      = 14

# XM Effect codes
FX_ARP   = 0x00
FX_UP    = 0x01
FX_DN    = 0x02
FX_PORTA = 0x03
FX_VIB   = 0x04
FX_PAN   = 0x08
FX_VSL   = 0x0A
FX_VOL   = 0x0C
FX_EFX   = 0x0E
FX_SPD   = 0x0F

# 12 Channels
CH_KICK  = 0
CH_SNARE = 1
CH_HAT   = 2
CH_BASS  = 3
CH_ARP   = 4
CH_PAD   = 5
CH_LEAD  = 6
CH_HARM  = 7
CH_BELL  = 8
CH_ECHO  = 9
CH_PAD2  = 10
CH_CYM   = 11

class SongBuilder:
    def __init__(self, num_patterns=18, rows=64):
        self.num_patterns = num_patterns
        self.rows = rows
        self.cells = [{} for _ in range(num_patterns)]
        self.echo_counter = 0

    def set(self, pat, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
        if not (0 <= row < self.rows):
            return
        d = self.cells[pat].setdefault((row, ch), {})
        if note is not None:
            d["note"] = note_str(note)
        if inst is not None:
            d["instrument"] = int(inst)
        if vol is not None:
            v = max(0, min(64, int(vol)))
            d["volume"] = 0x10 + v
        if fx is not None:
            d["effect"] = int(fx)
            d["effect_param"] = int(param or 0)

def add_kick_4x4(sb, pat, start_row=0, end_row=64, vol=52, skip_rows=()):
    for r in range(start_row, end_row, 8):
        if r not in skip_rows:
            sb.set(pat, r, CH_KICK, note="C-4", inst=I_KICK, vol=vol)

def add_snare_2_4(sb, pat, start_row=0, end_row=64, vol=48, ghosts=True):
    for r in range(start_row, end_row):
        m = r % 32
        if m in (8, 24):
            sb.set(pat, r, CH_SNARE, note="C-4", inst=I_SNARE, vol=vol)
        elif ghosts and m in (14, 30):
            sb.set(pat, r, CH_SNARE, note="C-4", inst=I_SNARE, vol=19)

def add_hats_driving(sb, pat, start_row=0, end_row=64, base_vol=36, open_every=True):
    for r in range(start_row, end_row, 2):
        m = r % 16
        if open_every and m == 4:
            sb.set(pat, r, CH_HAT, note="C-4", inst=I_HATO, vol=base_vol + 4)
        elif m == 0:
            sb.set(pat, r, CH_HAT, note="C-4", inst=I_HATC, vol=base_vol + 5)
        elif m in (8, 12):
            sb.set(pat, r, CH_HAT, note="C-4", inst=I_HATC, vol=base_vol + 2)
        else:
            sb.set(pat, r, CH_HAT, note="C-4", inst=I_HATC, vol=base_vol - 8)

def add_snare_roll(sb, pat, start_row=48, end_row=64, v_start=24, v_end=54):
    rows = list(range(start_row, end_row, 2))
    if end_row - start_row >= 8:
        rows = list(range(start_row, end_row - 8, 2)) + list(range(end_row - 8, end_row, 1))
    n = max(1, len(rows) - 1)
    for idx, r in enumerate(rows):
        v = int(round(v_start + (v_end - v_start) * (idx / n)))
        sb.set(pat, r, CH_SNARE, note="C-4", inst=I_SNARE, vol=v)

def add_tom_fill(sb, pat, start_row=48):
    hits = [
        (0, "G-4", 42, 70),
        (2, "G-4", 38, 82),
        (4, "F-4", 44, 102),
        (6, "D#4", 44, 128),
        (8, "C-4", 46, 152),
        (10, "C-4", 40, 166),
        (12, "G-3", 48, 180),
        (14, "G-3", 46, 192),
    ]
    for off, nt, vol, pan in hits:
        sb.set(pat, start_row + off, CH_SNARE, note=nt, inst=I_TOM, vol=vol, fx=FX_PAN, param=pan)

def add_bass_pattern(sb, pat, bars_chords, inst=I_BASS_FM, vol=44, style="octave", kick_duck=True, kick_rows=None):
    if kick_rows is None:
        kick_rows = set(range(0, 64, 8))
    for r0, r1, root in bars_chords:
        hi = transpose(root, 12)
        fifth = transpose(root, 7)
        if style == "octave":
            for r in range(r0, r1, 2):
                m = (r - r0) % 16
                if m in (0, 2, 6, 8, 12):
                    nt = root
                    v = vol if m in (0, 8) else vol - 5
                elif m in (4, 10, 14):
                    nt = hi if m != 14 else (fifth if ((r - r0) // 16) % 2 == 1 else hi)
                    v = vol - 3
                else:
                    continue
                if kick_duck and (r in kick_rows):
                    v = max(24, v - 13)
                sb.set(pat, r, CH_BASS, note=nt, inst=inst, vol=v)
                if m == 14 and r + 1 < r1:
                    sb.set(pat, r + 1, CH_BASS, note="OFF")
        elif style == "pumping":
            for r in range(r0, r1, 2):
                m = (r - r0) % 16
                if m in (0, 6, 8):
                    v = vol
                    if kick_duck and (r in kick_rows):
                        v = max(24, v - 13)
                    sb.set(pat, r, CH_BASS, note=root, inst=inst, vol=v)
                elif m in (4, 10, 12, 14):
                    nt = hi if m in (4, 12) else fifth
                    sb.set(pat, r, CH_BASS, note=nt, inst=inst, vol=vol - 4)
        elif style == "sustained":
            sb.set(pat, r0, CH_BASS, note=root, inst=inst, vol=vol - 4)
            if r1 - r0 >= 16:
                sb.set(pat, r0 + 16, CH_BASS, note=hi, inst=inst, vol=vol - 8)
                sb.set(pat, r0 + 24, CH_BASS, note=fifth, inst=inst, vol=vol - 6)

def add_arp_chords(sb, pat, segments, vol=31, gate=True):
    for r0, r1, root, arp in segments:
        step = 4 if gate else 8
        for r in range(r0, r1, step):
            v = vol if (r % 8 == 0) else vol - 5
            sb.set(pat, r, CH_ARP, note=root, inst=I_ARP, vol=v, fx=FX_ARP, param=arp)
            if gate and r + 3 < r1:
                sb.set(pat, r + 3, CH_ARP, note="OFF")
            elif not gate:
                for rr in range(r + 1, min(r + step, r1)):
                    sb.set(pat, rr, CH_ARP, fx=FX_ARP, param=arp)

def add_pad_stereo(sb, pat, segments, vol=19):
    """segments: list of (r0, r1, note_R, note_L)"""
    for r0, r1, nR, nL in segments:
        sb.set(pat, r0, CH_PAD, note=nR, inst=I_PAD, vol=vol, fx=FX_PAN, param=198)
        sb.set(pat, r0, CH_PAD2, note=nL, inst=I_PAD, vol=vol, fx=FX_PAN, param=58)
        if r1 - r0 >= 8:
            sb.set(pat, r1 - 2, CH_PAD, fx=FX_VSL, param=0x05)
            sb.set(pat, r1 - 2, CH_PAD2, fx=FX_VSL, param=0x05)

def add_lead_phrase(sb, pat, events, inst=I_LEAD_PWM, vol=45, ch=CH_LEAD, echo=True, echo_inst=None, echo_vol=18, echo_delay=6):
    if echo_inst is None:
        echo_inst = inst
    for ev in events:
        if len(ev) == 2:
            r, nt = ev
            opts = {}
        else:
            r, nt, opts = ev
        v = opts.get("vol", vol)
        fx = opts.get("fx", None)
        param = opts.get("param", None)
        if nt == "OFF":
            sb.set(pat, r, ch, note="OFF")
            if echo and r + echo_delay < sb.rows:
                sb.set(pat, r + echo_delay, CH_ECHO, note="OFF")
        else:
            use_inst = None if opts.get("slide") else inst
            if opts.get("slide"):
                fx = FX_PORTA
                param = opts.get("slide_spd", 0x28)
            elif opts.get("vib"):
                fx = FX_VIB
                param = opts.get("vib")
            sb.set(pat, r, ch, note=nt, inst=use_inst, vol=v if not opts.get("slide") else None, fx=fx, param=param)
            if echo and not opts.get("no_echo", False):
                er = r + echo_delay
                if er < sb.rows:
                    pan = 34 if (sb.echo_counter % 2 == 0) else 222
                    sb.echo_counter += 1
                    sb.set(pat, er, CH_ECHO, note=nt, inst=echo_inst, vol=echo_vol, fx=FX_PAN, param=pan)
                er2 = r + echo_delay * 2
                if er2 < sb.rows and opts.get("echo2", False):
                    pan2 = 222 if (sb.echo_counter % 2 == 0) else 34
                    sb.echo_counter += 1
                    sb.set(pat, er2, CH_ECHO, note=nt, inst=echo_inst, vol=max(9, echo_vol // 2), fx=FX_PAN, param=pan2)

def build_song():
    sb = SongBuilder(num_patterns=18, rows=64)

    # ==========================================================
    # PAT 0 & 1: INTRO (4 bars: Cm -> Ab -> Bb -> G7)
    # ==========================================================
    add_bass_pattern(sb, 0, [(0, 32, "C-2"), (32, 64, "Ab1")], inst=I_BASS_FM, vol=38, style="pumping", kick_duck=False)
    add_arp_chords(sb, 0, [(0, 32, "C-4", 0x37), (32, 64, "Ab3", 0x47)], vol=30, gate=True)
    add_pad_stereo(sb, 0, [(0, 32, "Eb4", "G-4"), (32, 64, "C-4", "Eb4")], vol=14)
    for r in range(0, 64, 2):
        if r % 16 == 4:
            sb.set(0, r, CH_HAT, note="C-4", inst=I_HATO, vol=28)
        else:
            sb.set(0, r, CH_HAT, note="C-4", inst=I_HATC, vol=24 + (r % 8 == 0) * 10)
    bell_intro = [
        (0, "G-5"), (8, "Eb5"), (16, "D-5"), (24, "C-5"),
        (32, "G-4"), (40, "Ab4"), (48, "C-5"), (56, "Eb5"),
    ]
    for idx, (r, nt) in enumerate(bell_intro):
        sb.set(0, r, CH_BELL, note=nt, inst=I_BELL, vol=36)
        if r + 6 < 64:
            sb.set(0, r + 6, CH_ECHO, note=nt, inst=I_BELL, vol=16, fx=FX_PAN, param=56 if idx % 2 == 0 else 200)

    # Pat 1: Kick enters + Snare build + Uplift riser into the Drop!
    add_kick_4x4(sb, 1, 0, 56, vol=50)
    add_snare_2_4(sb, 1, 0, 48, vol=44, ghosts=False)
    add_snare_roll(sb, 1, 48, 64, v_start=24, v_end=56)
    add_hats_driving(sb, 1, 0, 48, base_vol=33, open_every=True)
    add_bass_pattern(sb, 1, [(0, 32, "Bb1"), (32, 60, "G-1")], inst=I_BASS_FM, vol=43, style="octave", kick_duck=True)
    add_arp_chords(sb, 1, [(0, 32, "Bb3", 0x47), (32, 60, "G-3", 0x47)], vol=31, gate=True)
    add_pad_stereo(sb, 1, [(0, 32, "D-4", "F-4")], vol=16)
    sb.set(1, 32, CH_PAD, note="C-4", inst=I_UPLIFT, vol=38, fx=FX_PAN, param=128)
    sb.set(1, 32, CH_PAD2, note="OFF")
    for r, nt in [(0, "F-5"), (8, "D-5"), (16, "Bb4"), (24, "F-5"), (32, "D-5"), (40, "B-4"), (48, "G-4")]:
        sb.set(1, r, CH_BELL, note=nt, inst=I_BELL, vol=36)

    # ==========================================================
    # PAT 2..5 & 14..17: THEME A — MAIN HOOK
    # ==========================================================
    def populate_theme_a(pats, climax=False):
        p0, p1, p2, p3 = pats
        sb.set(p0, 0, CH_CYM, note="C-4", inst=I_CRASH, vol=44)
        sb.set(p2, 0, CH_CYM, note="C-4", inst=I_CRASH, vol=40)

        for pi, p in enumerate([p0, p1, p2, p3]):
            skip = (56,) if pi == 3 else ()
            add_kick_4x4(sb, p, 0, 64, vol=52, skip_rows=skip)
            if pi == 3:
                add_snare_2_4(sb, p, 0, 48, vol=48, ghosts=True)
                add_tom_fill(sb, p, 48)
                if climax:
                    sb.set(p, 56, CH_SNARE, note="C-4", inst=I_SNARE, vol=48)
                    sb.set(p, 60, CH_SNARE, note="C-4", inst=I_SNARE, vol=52)
            else:
                add_snare_2_4(sb, p, 0, 64, vol=48, ghosts=True)
            add_hats_driving(sb, p, 0, 64 if pi < 3 else 48, base_vol=36, open_every=True)

        krows_normal = set(range(0, 64, 8))
        krows_fill = set(range(0, 56, 8))
        add_bass_pattern(sb, p0, [(0, 32, "C-2"), (32, 64, "Ab1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=krows_normal)
        add_bass_pattern(sb, p1, [(0, 32, "Bb1"), (32, 64, "G-1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=krows_normal)
        add_bass_pattern(sb, p2, [(0, 32, "C-2"), (32, 64, "Ab1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=krows_normal)
        add_bass_pattern(sb, p3, [(0, 32, "F-1"), (32, 64, "G-1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=krows_fill)

        add_arp_chords(sb, p0, [(0, 32, "C-4", 0x37), (32, 64, "Ab3", 0x47)], vol=31, gate=True)
        add_arp_chords(sb, p1, [(0, 32, "Bb3", 0x47), (32, 48, "G-3", 0x37), (48, 64, "G-3", 0x47)], vol=31, gate=True)
        add_arp_chords(sb, p2, [(0, 32, "C-4", 0x37), (32, 64, "Ab3", 0x47)], vol=31, gate=True)
        add_arp_chords(sb, p3, [(0, 32, "F-4", 0x37), (32, 64, "G-3", 0x4A)], vol=31, gate=True)

        pv = 21 if climax else 16
        add_pad_stereo(sb, p0, [(0, 32, "Eb4", "G-4"), (32, 64, "C-4", "Eb4")], vol=pv)
        add_pad_stereo(sb, p1, [(0, 32, "D-4", "F-4"), (32, 64, "B-3", "D-4")], vol=pv)
        add_pad_stereo(sb, p2, [(0, 32, "Eb4", "G-4"), (32, 64, "C-4", "Eb4")], vol=pv)
        add_pad_stereo(sb, p3, [(0, 32, "C-4", "Ab4"), (32, 64, "D-4", "B-4")], vol=pv)

        lead0 = [
            (0,  "G-5"), (6, "Eb5"), (8, "F-5"), (12, "G-5"),
            (16, "C-6", {"vib": 0x43, "echo2": True}), (22, "Bb5"), (24, "G-5"), (28, "Eb5"),
            (32, "F-5"), (38, "Eb5"), (40, "C-5"), (44, "Eb5"),
            (48, "Ab5", {"vib": 0x43}), (56, "G-5"), (60, "Eb5"),
        ]
        lead1 = [
            (0,  "F-5"), (6, "D-5"), (8, "Eb5"), (12, "F-5"),
            (16, "Bb5", {"vib": 0x43, "echo2": True}), (22, "G-5"), (24, "F-5"), (28, "D-5"),
            (32, "Eb5"), (36, "D-5"), (40, "C-5"), (44, "Bb4"),
            (48, "B-4"), (54, "D-5", {"slide": True, "slide_spd": 0x30}), (58, "F-5"),
        ]
        lead2 = [
            (0,  "G-5"), (6, "Eb5"), (8, "F-5"), (12, "G-5"),
            (16, "C-6"), (22, "D-6"), (24, "Eb6", {"vib": 0x44, "echo2": True}), (30, "D-6"),
            (32, "C-6"), (38, "Bb5"), (40, "Ab5"), (44, "G-5"),
            (48, "Ab5", {"vib": 0x43}), (56, "G-5"), (60, "Eb5"),
        ]
        # On climax p3 (Pat 17), end on F-5 so it resolves cleanly up to G-5 on Pat 2!
        end_note = "F-5" if climax else "G-5"
        lead3 = [
            (0,  "F-5"), (6, "G-5"), (8, "Ab5"), (12, "C-6"),
            (16, "Bb5"), (22, "Ab5"), (24, "G-5"), (28, "F-5"),
            (32, "G-5", {"vib": 0x44, "echo2": True}), (40, "F-5"), (44, "D-5"),
            (48, "B-4"), (54, "D-5"), (58, end_note),
        ]
        add_lead_phrase(sb, p0, lead0, inst=I_LEAD_PWM, vol=45, echo=True, echo_vol=18)
        add_lead_phrase(sb, p1, lead1, inst=I_LEAD_PWM, vol=45, echo=True, echo_vol=18)
        add_lead_phrase(sb, p2, lead2, inst=I_LEAD_PWM, vol=46, echo=True, echo_vol=18)
        add_lead_phrase(sb, p3, lead3, inst=I_LEAD_PWM, vol=46, echo=True, echo_vol=18)

        harm_start = 0 if climax else 2
        harm_events = [
            [(0, "Eb5"), (6, "C-5"), (8, "D-5"), (12, "Eb5"), (16, "G-5"), (22, "G-5"), (24, "Eb5"), (28, "C-5"),
             (32, "C-5"), (38, "C-5"), (40, "Ab4"), (44, "C-5"), (48, "Eb5"), (56, "Eb5"), (60, "C-5")],
            [(0, "D-5"), (6, "Bb4"), (8, "C-5"), (12, "D-5"), (16, "F-5"), (22, "Eb5"), (24, "D-5"), (28, "Bb4"),
             (32, "C-5"), (36, "Bb4"), (40, "G-4"), (44, "G-4"), (48, "G-4"), (54, "B-4"), (58, "D-5")],
            [(0, "Eb5"), (6, "C-5"), (8, "D-5"), (12, "Eb5"), (16, "G-5"), (22, "Bb5"), (24, "C-6"), (30, "Bb5"),
             (32, "Ab5"), (38, "G-5"), (40, "Eb5"), (44, "Eb5"), (48, "Eb5"), (56, "Eb5"), (60, "C-5")],
            [(0, "C-5"), (6, "Eb5"), (8, "F-5"), (12, "Ab5"), (16, "G-5"), (22, "F-5"), (24, "Eb5"), (28, "D-5"),
             (32, "D-5"), (40, "D-5"), (44, "B-4"), (48, "G-4"), (54, "B-4"), (58, "D-5")],
        ]
        for idx in range(harm_start, 4):
            add_lead_phrase(sb, pats[idx], harm_events[idx], inst=I_LEAD_THN, vol=30 if not climax else 33, ch=CH_HARM, echo=False)

        bell_spots = [
            (p0, [(48, "C-6"), (52, "Eb6"), (56, "G-6"), (60, "Eb6")]),
            (p1, [(48, "G-5"), (52, "B-5"), (56, "D-6"), (60, "G-6")]),
            (p2, [(16, "G-6"), (20, "Eb6"), (24, "C-6"), (48, "Eb6"), (52, "C-6"), (56, "Ab5")]),
            (p3, [(0, "C-6"), (8, "Ab5"), (16, "F-5"), (32, "D-6"), (40, "B-5"), (48, "G-5")]),
        ]
        for p, spots in bell_spots:
            for r, nt in spots:
                sb.set(p, r, CH_BELL, note=nt, inst=I_BELL, vol=35 if climax else 31)

    populate_theme_a([2, 3, 4, 5], climax=False)

    # ==========================================================
    # PAT 6..9: THEME B — HEROIC RELATIVE MAJOR CHORUS
    # ==========================================================
    sb.set(6, 0, CH_CYM, note="C-4", inst=I_CRASH, vol=44)
    for pi, p in enumerate([6, 7, 8, 9]):
        add_kick_4x4(sb, p, 0, 64 if pi < 3 else 48, vol=52)
        if pi == 3:
            add_snare_2_4(sb, p, 0, 48, vol=48, ghosts=True)
            add_snare_roll(sb, p, 48, 64, v_start=28, v_end=55)
        else:
            add_snare_2_4(sb, p, 0, 64, vol=48, ghosts=True)
        add_hats_driving(sb, p, 0, 64 if pi < 3 else 48, base_vol=36, open_every=True)

    krows_full = set(range(0, 64, 8))
    krows_cut = set(range(0, 48, 8))
    add_bass_pattern(sb, 6, [(0, 32, "Eb2"), (32, 64, "D-2")], inst=I_BASS_FM, vol=45, style="pumping", kick_rows=krows_full)
    add_bass_pattern(sb, 7, [(0, 32, "C-2"), (32, 64, "Bb1")], inst=I_BASS_FM, vol=45, style="pumping", kick_rows=krows_full)
    add_bass_pattern(sb, 8, [(0, 32, "Ab1"), (32, 64, "Bb1")], inst=I_BASS_FM, vol=45, style="pumping", kick_rows=krows_full)
    add_bass_pattern(sb, 9, [(0, 32, "C-2"), (32, 64, "G-1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=krows_cut)

    add_arp_chords(sb, 6, [(0, 32, "Eb4", 0x47), (32, 64, "D-4", 0x38)], vol=29, gate=True)
    add_arp_chords(sb, 7, [(0, 32, "C-4", 0x37), (32, 64, "Bb3", 0x47)], vol=29, gate=True)
    add_arp_chords(sb, 8, [(0, 32, "Ab3", 0x47), (32, 64, "Bb3", 0x47)], vol=29, gate=True)
    add_arp_chords(sb, 9, [(0, 32, "C-4", 0x37), (32, 64, "G-3", 0x4A)], vol=29, gate=True)

    add_pad_stereo(sb, 6, [(0, 32, "G-4", "Bb4"), (32, 64, "F-4", "Bb4")], vol=21)
    add_pad_stereo(sb, 7, [(0, 32, "Eb4", "G-4"), (32, 64, "D-4", "F-4")], vol=21)
    add_pad_stereo(sb, 8, [(0, 32, "C-4", "Eb4"), (32, 64, "D-4", "F-4")], vol=21)
    add_pad_stereo(sb, 9, [(0, 32, "Eb4", "G-4"), (32, 64, "B-3", "F-4")], vol=21)

    chorus_leads = [
        (6, [(0, "Bb5"), (8, "G-5"), (12, "Bb5"), (16, "Eb6", {"vib": 0x44, "echo2": True}), (24, "D-6"), (28, "Bb5"),
             (32, "C-6"), (38, "Bb5"), (40, "F-5"), (48, "G-5"), (54, "F-5"), (56, "D-5")]),
        (7, [(0, "Eb5"), (6, "G-5"), (8, "C-6", {"vib": 0x43}), (16, "Bb5"), (22, "G-5"), (24, "Eb5"),
             (32, "F-5"), (40, "G-5"), (44, "Bb5"), (48, "D-6", {"vib": 0x44, "echo2": True}), (56, "Bb5")]),
        (8, [(0, "C-6"), (8, "Ab5"), (12, "C-6"), (16, "Eb6", {"vib": 0x44}), (24, "C-6"), (28, "Ab5"),
             (32, "Bb5"), (38, "G-5"), (40, "F-5"), (48, "D-5"), (52, "F-5"), (56, "Bb5")]),
        (9, [(0, "C-6"), (8, "G-5"), (12, "Eb5"), (16, "F-5"), (22, "Eb5"), (24, "C-5"),
             (32, "D-5"), (40, "G-5"), (44, "B-5"), (48, "D-6", {"vib": 0x45}), (56, "G-5")]),
    ]
    chorus_harms = [
        (6, [(0, "G-5"), (8, "Eb5"), (12, "G-5"), (16, "Bb5"), (24, "Bb5"), (28, "G-5"),
             (32, "Ab5"), (38, "F-5"), (40, "D-5"), (48, "D-5"), (54, "D-5"), (56, "Bb4")]),
        (7, [(0, "C-5"), (6, "Eb5"), (8, "G-5"), (16, "G-5"), (22, "Eb5"), (24, "C-5"),
             (32, "D-5"), (40, "Eb5"), (44, "F-5"), (48, "Bb5"), (56, "F-5")]),
        (8, [(0, "Ab5"), (8, "Eb5"), (12, "Ab5"), (16, "C-6"), (24, "Ab5"), (28, "Eb5"),
             (32, "G-5"), (38, "Eb5"), (40, "D-5"), (48, "Bb4"), (52, "D-5"), (56, "F-5")]),
        (9, [(0, "G-5"), (8, "Eb5"), (12, "C-5"), (16, "C-5"), (22, "C-5"), (24, "G-4"),
             (32, "B-4"), (40, "D-5"), (44, "G-5"), (48, "B-5"), (56, "D-5")]),
    ]
    for p, evs in chorus_leads:
        add_lead_phrase(sb, p, evs, inst=I_LEAD_PWM, vol=45, echo=True, echo_vol=19)
    for p, evs in chorus_harms:
        add_lead_phrase(sb, p, evs, inst=I_LEAD_THN, vol=31, ch=CH_HARM, echo=False)

    # ==========================================================
    # PAT 10..11: BREAKDOWN & BUILD
    # ==========================================================
    sb.set(10, 0, CH_CYM, note="C-4", inst=I_CRASH, vol=38)
    add_bass_pattern(sb, 10, [(0, 32, "F-1"), (32, 64, "Eb1")], inst=I_BASS_SQ, vol=42, style="sustained", kick_duck=False)
    add_pad_stereo(sb, 10, [(0, 32, "C-4", "Ab4"), (32, 64, "Bb3", "G-4")], vol=22)
    for r in range(0, 64, 4):
        sb.set(10, r, CH_HAT, note="C-4", inst=I_HATC, vol=28 if r % 8 == 0 else 18)
    bell_brk = [
        (0, "C-6"), (4, "Ab5"), (8, "F-5"), (12, "C-5"),
        (16, "Eb6"), (20, "C-6"), (24, "Ab5"), (28, "F-5"),
        (32, "Bb5"), (36, "G-5"), (40, "Eb5"), (44, "Bb4"),
        (48, "Eb6"), (52, "Bb5"), (56, "G-5"), (60, "Eb5"),
    ]
    for idx, (r, nt) in enumerate(bell_brk):
        sb.set(10, r, CH_BELL, note=nt, inst=I_BELL, vol=37)
        if r + 6 < 64:
            sb.set(10, r + 6, CH_ECHO, note=nt, inst=I_BELL, vol=17, fx=FX_PAN, param=52 if idx % 2 == 0 else 204)

    add_bass_pattern(sb, 11, [(0, 32, "D-2"), (32, 60, "G-1")], inst=I_BASS_SQ, vol=43, style="pumping", kick_rows={0, 16, 32, 40, 48, 56})
    add_pad_stereo(sb, 11, [(0, 32, "F-4", "Ab4")], vol=20)
    add_arp_chords(sb, 11, [(0, 32, "D-4", 0x36), (32, 60, "G-3", 0x4A)], vol=30, gate=True)
    for r in (0, 16, 32, 40, 48, 56):
        sb.set(11, r, CH_KICK, note="C-4", inst=I_KICK, vol=50)
    sb.set(11, 8, CH_SNARE, note="C-4", inst=I_SNARE, vol=42)
    sb.set(11, 24, CH_SNARE, note="C-4", inst=I_SNARE, vol=46)
    add_snare_roll(sb, 11, 32, 64, v_start=22, v_end=56)
    sb.set(11, 32, CH_PAD, note="C-4", inst=I_UPLIFT, vol=38, fx=FX_PAN, param=128)
    for r, nt in [(0, "Ab5"), (4, "F-5"), (8, "D-5"), (16, "C-6"), (20, "Ab5"), (24, "F-5"), (32, "G-5"), (40, "B-5"), (48, "D-6")]:
        sb.set(11, r, CH_BELL, note=nt, inst=I_BELL, vol=36)

    # ==========================================================
    # PAT 12..13: CHIPTUNE SOLO / BRIDGE
    # ==========================================================
    sb.set(12, 0, CH_CYM, note="C-4", inst=I_CRASH, vol=44)
    for pi, p in enumerate([12, 13]):
        skip = (56,) if pi == 1 else ()
        add_kick_4x4(sb, p, 0, 64, vol=52, skip_rows=skip)
        if pi == 1:
            add_snare_2_4(sb, p, 0, 48, vol=48, ghosts=True)
            add_tom_fill(sb, p, 48)
        else:
            add_snare_2_4(sb, p, 0, 64, vol=48, ghosts=True)
        add_hats_driving(sb, p, 0, 64 if pi == 0 else 48, base_vol=37, open_every=True)

    add_bass_pattern(sb, 12, [(0, 32, "F-1"), (32, 64, "Bb1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=krows_full)
    add_bass_pattern(sb, 13, [(0, 16, "Eb2"), (16, 32, "Ab1"), (32, 48, "D-2"), (48, 64, "G-1")], inst=I_BASS_FM, vol=45, style="octave", kick_rows=set(range(0, 56, 8)))

    add_arp_chords(sb, 12, [(0, 32, "F-4", 0x37), (32, 64, "Bb3", 0x47)], vol=29, gate=True)
    add_arp_chords(sb, 13, [(0, 16, "Eb4", 0x47), (16, 32, "Ab3", 0x47), (32, 48, "D-4", 0x36), (48, 64, "G-3", 0x4A)], vol=29, gate=True)

    solo_12 = [
        (0, "C-6"), (2, "Ab5"), (4, "F-5"), (6, "G-5"),
        (8, "Ab5"), (10, "C-6"), (12, "Eb6"), (14, "C-6"),
        (16, "F-6", {"vib": 0x33}), (22, "Eb6"), (24, "C-6"), (26, "Ab5"), (28, "F-5"), (30, "Ab5"),
        (32, "Bb5"), (34, "F-5"), (36, "D-5"), (38, "F-5"),
        (40, "Bb5"), (42, "D-6"), (44, "F-6"), (46, "D-6"),
        (48, "G-6"), (50, "F-6"), (52, "D-6"), (54, "Bb5"),
        (56, "F-5"), (58, "G-5"), (60, "Ab5"), (62, "Bb5"),
    ]
    add_lead_phrase(sb, 12, solo_12, inst=I_LEAD_THN, vol=41, ch=CH_LEAD, echo=True, echo_inst=I_LEAD_THN, echo_vol=16)

    solo_13 = [
        (0, "Eb6"), (2, "Bb5"), (4, "G-5"), (6, "Bb5"),
        (8, "Eb6"), (10, "G-6"), (12, "F-6"), (14, "Eb6"),
        (16, "C-6"), (18, "Eb6"), (20, "Ab6"), (22, "G-6"),
        (24, "Eb6"), (26, "C-6"), (28, "Ab5"), (30, "C-6"),
        (32, "D-6"), (34, "C-6"), (36, "Ab5"), (38, "F-5"),
        (40, "Ab5"), (42, "C-6"), (44, "D-6"), (46, "F-6"),
        (48, "G-6", {"vib": 0x45, "echo2": True}), (56, "F-6"), (58, "D-6"), (60, "B-5"), (62, "D-6"),
    ]
    add_lead_phrase(sb, 13, solo_13, inst=I_LEAD_PWM, vol=46, ch=CH_LEAD, echo=True, echo_vol=18)
    for r, nt in [(0, "Eb5"), (16, "C-5"), (32, "D-5"), (48, "G-5"), (56, "F-5"), (60, "B-4")]:
        sb.set(13, r, CH_HARM, note=nt, inst=I_LEAD_THN, vol=31)

    # ==========================================================
    # PAT 14..17: FINAL CLIMAX HOOK (loops cleanly into Pos 2!)
    # ==========================================================
    populate_theme_a([14, 15, 16, 17], climax=True)

    # Build ft2 batch JSON
    calls = [{"name": "module_new", "arguments": {"channels": 12, "name": "PRISM KEYGEN"}}]

    bank = build_bank()
    for inst, name, (pcm, ls, ll, fl, rn, ft, pan) in bank:
        b64 = base64.b64encode(pcm.tobytes()).decode()
        calls.append({"name": "instrument_set", "arguments": {"instrument": inst, "name": name}})
        calls.append({"name": "sample_create_from_pcm", "arguments": {"instrument": inst, "sample": 0, "pcm": b64, "encoding": "int16", "name": name}})
        calls.append({
            "name": "sample_set",
            "arguments": {
                "instrument": inst,
                "sample": 0,
                "volume": 64,
                "panning": pan,
                "relative_note": rn,
                "finetune": ft,
                "loop_start": ls,
                "loop_length": ll,
                "flags": fl,
            }
        })

    for p in range(18):
        calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
        for (row, ch), cell in sorted(sb.cells[p].items()):
            args = {"pattern": p, "row": row, "channel": ch}
            args.update(cell)
            calls.append({"name": "pattern_set_cell", "arguments": args})

    for pos in range(18):
        calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pos}})

    calls.append({
        "name": "song_set",
        "arguments": {"name": "PRISM KEYGEN", "bpm": 138, "speed": 3, "length": 18, "loop_start": 2}
    })
    calls.append({"name": "module_save", "arguments": {"path": "/workspace/submission/tune.xm", "format": "xm"}})
    calls.append({"name": "module_render", "arguments": {"path": "/workspace/submission/preview.wav", "rate": 44100, "bits": 16}})

    batch_path = "/workspace/src/build_tune.json"
    with open(batch_path, "w") as f:
        json.dump(calls, f)
    print(f"Wrote {len(calls)} batch commands")

    res = subprocess.run(["ft2", "batch", batch_path], capture_output=True, text=True)
    if res.returncode != 0:
        print("BATCH ERROR:", res.returncode, res.stderr)
        raise SystemExit(1)
    lines = [l for l in res.stdout.strip().splitlines() if l.strip()]
    errors = [l for l in lines if '"isError": true' in l or '"isError":true' in l]
    print(f"Batch executed {len(lines)} calls, errors={len(errors)}")
    if errors:
        print("Sample errors:", errors[:5])
    print("Last 2 results:", "\n".join(lines[-2:]))

if __name__ == "__main__":
    build_song()
