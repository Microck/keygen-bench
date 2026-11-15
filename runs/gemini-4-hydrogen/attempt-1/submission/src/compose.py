import os
from xm_builder import XMModule, XMPattern, parse_note
from synth import build_all_instruments

# Instrument IDs (1-based)
I_PWM_LEAD   = 1
I_ARP_P25    = 2
I_ARP_P12    = 3
I_SAW_LEAD   = 4
I_BASS_PUNCH = 5
I_BASS_SUB   = 6
I_FM_BELL    = 7
I_STAB       = 8
I_PAD        = 9
I_TRI        = 10
I_KICK       = 11
I_SNARE      = 12
I_CLAP_RIM   = 13
I_HAT        = 14
I_FX         = 15
I_TOM_ZAP    = 16
I_PWM_TWIN   = 17
I_SAW_TWIN   = 18

# Channels (12)
CH_KICK  = 0
CH_SNARE = 1
CH_HAT   = 2
CH_BASS  = 3
CH_ARP1  = 4
CH_ARP2  = 5
CH_LEAD  = 6
CH_ECHO  = 7
CH_BELL  = 8
CH_PAD   = 9
CH_FX    = 10
CH_BELL2 = 11

CH_PANS = {
    CH_KICK:  0x80,
    CH_SNARE: 0x68,
    CH_HAT:   0xCA,
    CH_BASS:  0x80,
    CH_ARP1:  0x22,
    CH_ARP2:  0xDE,
    CH_LEAD:  0xA2,
    CH_ECHO:  0x44,
    CH_BELL:  0x38,
    CH_PAD:   0x9C,
    CH_FX:    0x80,
    CH_BELL2: 0xC8,
}

def set_init_pans_and_gvol(pat: XMPattern, row: int = 0, gvol: int = 0x35):
    for ch, pan in CH_PANS.items():
        n, i, v, e, p = pat.get_cell(row, ch)
        if e == 0 and p == 0:
            pat.set_cell(row, ch, note=n, inst=i, vol=v, eff=0x08, param=pan)
    n, i, v, e, p = pat.get_cell(row, CH_FX)
    if e == 0 or e == 0x08:
        pat.set_cell(row, CH_FX, note=n, inst=i, vol=v, eff=0x10, param=gvol)

NOTE_LIST = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
def transpose_note(note_str: str, semis: int) -> str:
    v = parse_note(note_str)
    if v == 0 or v == 97:
        return note_str
    nv = max(1, min(96, v + semis)) - 1
    return f"{NOTE_LIST[nv % 12]}{nv // 12}"

# -----------------------------------------------------------------------------
# Drum Groove Generators (per 16-row bar)
# -----------------------------------------------------------------------------
def write_drum_bar(pat: XMPattern, bar_idx: int, mode: str = "full", fill: str = "none"):
    r0 = bar_idx * 16
    if mode in ("full", "driving"):
        for r in [0, 4, 8, 12]:
            pat.set_cell(r0 + r, CH_KICK, note="C-4", inst=I_KICK, vol=0x46)
        if mode == "driving" or (bar_idx % 2 == 1):
            pat.set_cell(r0 + 14, CH_KICK, note="C-4", inst=I_KICK, vol=0x34)
        for r in [4, 12]:
            pat.set_cell(r0 + r, CH_SNARE, note="C-4", inst=I_SNARE, vol=0x4A)
            n_fx, _, _, _, _ = pat.get_cell(r0 + r, CH_FX)
            if n_fx == 0:
                pat.set_cell(r0 + r, CH_FX, note="C-4", inst=I_CLAP_RIM, vol=0x36)
        if mode == "driving" and bar_idx % 2 == 1 and fill == "none":
            pat.set_cell(r0 + 15, CH_SNARE, note="C-4", inst=I_SNARE, vol=0x28)
        for step in range(16):
            if step in (2, 6, 10, 14):
                pat.set_cell(r0 + step, CH_HAT, note="F#4", inst=I_HAT, vol=0x42)
            elif step % 4 == 0:
                pat.set_cell(r0 + step, CH_HAT, note="C-4", inst=I_HAT, vol=0x3C)
            elif step % 2 == 1:
                vol = 0x2C if mode == "full" else 0x36
                pat.set_cell(r0 + step, CH_HAT, note="C-3", inst=I_HAT, vol=vol)

    elif mode == "halftime":
        pat.set_cell(r0 + 0, CH_KICK, note="C-4", inst=I_KICK, vol=0x44)
        pat.set_cell(r0 + 10, CH_KICK, note="C-4", inst=I_KICK, vol=0x3C)
        pat.set_cell(r0 + 8, CH_SNARE, note="C-4", inst=I_SNARE, vol=0x48)
        for step in range(16):
            if step % 2 == 0:
                pat.set_cell(r0 + step, CH_HAT, note="C-4" if step % 4 == 0 else "F#4", inst=I_HAT, vol=0x36)
            else:
                pat.set_cell(r0 + step, CH_HAT, note="C-3", inst=I_HAT, vol=0x26)

    elif mode == "breakdown":
        for step in range(16):
            if step in (0, 4, 8, 12):
                pat.set_cell(r0 + step, CH_HAT, note="C-4", inst=I_HAT, vol=0x2A)
            elif step % 2 == 1:
                pat.set_cell(r0 + step, CH_HAT, note="C-3", inst=I_HAT, vol=0x20)
        pat.set_cell(r0 + 4, CH_SNARE, note="C-3", inst=I_CLAP_RIM, vol=0x30)
        pat.set_cell(r0 + 12, CH_SNARE, note="C-3", inst=I_CLAP_RIM, vol=0x34)
        if bar_idx % 2 == 1:
            pat.set_cell(r0 + 14, CH_SNARE, note="C-3", inst=I_CLAP_RIM, vol=0x26)

    elif mode == "intro_tick":
        for step in range(16):
            if step % 4 == 0:
                pat.set_cell(r0 + step, CH_HAT, note="C-4", inst=I_HAT, vol=0x32)
            elif step % 4 == 2:
                pat.set_cell(r0 + step, CH_HAT, note="F#4" if bar_idx >= 1 else "C-3", inst=I_HAT, vol=0x2C)
            else:
                pat.set_cell(r0 + step, CH_HAT, note="C-3", inst=I_HAT, vol=0x22)

    if fill == "snare_build":
        for idx, r in enumerate([8, 10, 12, 13, 14, 15]):
            v = 0x2E + idx * 5
            pat.set_cell(r0 + r, CH_SNARE, note="C-4", inst=I_SNARE, vol=min(0x4E, v))
        pat.set_cell(r0 + 15, CH_HAT, note="C-4", inst=I_SNARE, vol=0x44, eff=0x0E, param=0xD3)

    elif fill == "tom_cascade":
        tom_seq = [(10, "G-3", 0x46), (11, "F-3", 0x44), (12, "D-3", 0x48), (13, "C-3", 0x46), (14, "C-4", 0x4C)]
        for r, n, v in tom_seq:
            if n in ("G-3", "F-3", "D-3", "C-3"):
                pat.set_cell(r0 + r, CH_FX, note=n, inst=I_TOM_ZAP, vol=v)
            else:
                pat.set_cell(r0 + r, CH_SNARE, note="C-4", inst=I_SNARE, vol=v)
        pat.set_cell(r0 + 15, CH_SNARE, note="C-4", inst=I_CLAP_RIM, vol=0x46, eff=0x0E, param=0xD3)

    elif fill == "snare_32_drop":
        for r, v in [(0,0x40),(2,0x38),(4,0x42),(6,0x3A),(8,0x44),(9,0x3A),(10,0x46),(11,0x3C),(12,0x48),(13,0x44),(14,0x4A),(15,0x4E)]:
            pat.set_cell(r0 + r, CH_SNARE, note="C-4", inst=I_SNARE, vol=v)
        pat.set_cell(r0 + 14, CH_HAT, note="C-4", inst=I_SNARE, vol=0x40, eff=0x0E, param=0xD3)
        pat.set_cell(r0 + 15, CH_HAT, note="C-4", inst=I_SNARE, vol=0x46, eff=0x0E, param=0xD3)

    elif fill == "turnaround":
        pat.set_cell(r0 + 8,  CH_SNARE, note="C-4", inst=I_SNARE, vol=0x4A)
        pat.set_cell(r0 + 9,  CH_FX, note="G-3", inst=I_TOM_ZAP, vol=0x44)
        pat.set_cell(r0 + 10, CH_FX, note="F-3", inst=I_TOM_ZAP, vol=0x46)
        pat.set_cell(r0 + 11, CH_FX, note="D-3", inst=I_TOM_ZAP, vol=0x46)
        pat.set_cell(r0 + 12, CH_SNARE, note="C-4", inst=I_SNARE, vol=0x4E)
        pat.set_cell(r0 + 12, CH_FX, note="C-4", inst=I_CLAP_RIM, vol=0x44)
        pat.set_cell(r0 + 14, CH_FX, note="C-3", inst=I_TOM_ZAP, vol=0x48)
        pat.set_cell(r0 + 14, CH_SNARE, note="C-4", inst=I_SNARE, vol=0x48, eff=0x0E, param=0xD3)

# -----------------------------------------------------------------------------
# Bassline Generator
# -----------------------------------------------------------------------------
def write_bass_bar(pat: XMPattern, bar_idx: int, root_note: str, style: str = "octave", walk: list = None):
    r0 = bar_idx * 16
    hi = transpose_note(root_note, 12)
    fifth = transpose_note(root_note, 7)

    if style == "octave":
        seq = [
            (0, root_note, 0x48), (2, hi, 0x3E), (3, root_note, 0x3A),
            (4, root_note, 0x46), (6, hi, 0x3E), (7, fifth, 0x36),
            (8, root_note, 0x48), (10, hi, 0x40), (11, root_note, 0x3A),
            (12, root_note, 0x46), (14, hi, 0x40), (15, hi, 0x38),
        ]
        for step, n, v in seq:
            pat.set_cell(r0 + step, CH_BASS, note=n, inst=I_BASS_PUNCH, vol=v)
    elif style == "bounce":
        seq = [
            (0, root_note, 0x48), (2, hi, 0x3E), (3, root_note, 0x3A),
            (6, hi, 0x40), (8, root_note, 0x48), (10, hi, 0x3E),
            (11, root_note, 0x3C), (12, root_note, 0x46), (14, fifth, 0x3C), (15, hi, 0x3E),
        ]
        for step, n, v in seq:
            pat.set_cell(r0 + step, CH_BASS, note=n, inst=I_BASS_PUNCH, vol=v)
    elif style == "sub":
        pat.set_cell(r0 + 0, CH_BASS, note=root_note, inst=I_BASS_SUB, vol=0x26)
        pat.set_cell(r0 + 15, CH_BASS, note="OFF")
    elif style == "walk" and walk:
        for step, n, v in walk:
            pat.set_cell(r0 + step, CH_BASS, note=n, inst=I_BASS_PUNCH, vol=v)

# -----------------------------------------------------------------------------
# Chip Arp Generator
# -----------------------------------------------------------------------------
def write_arp_segment(pat: XMPattern, row_start: int, row_len: int, root_note: str, arp_hex: int,
                      inst1: int = I_ARP_P25, inst2: int = I_ARP_P12, vol1: int = 0x40, vol2: int = 0x3C,
                      mode: str = "pulse"):
    hi_root = transpose_note(root_note, 12)
    if mode == "pulse":
        for off in range(row_len):
            r = row_start + off
            if off % 4 == 0:
                pat.set_cell(r, CH_ARP1, note=root_note, inst=inst1, vol=vol1, eff=0x00, param=arp_hex)
                pat.set_cell(r, CH_ARP2, note=hi_root, inst=inst2, vol=vol2, eff=0x00, param=arp_hex)
            else:
                pat.set_cell(r, CH_ARP1, eff=0x00, param=arp_hex)
                pat.set_cell(r, CH_ARP2, eff=0x00, param=arp_hex)
    elif mode == "gated":
        for off in range(row_len):
            r = row_start + off
            if off % 2 == 0:
                pat.set_cell(r, CH_ARP1, note=root_note, inst=inst1, vol=vol1, eff=0x00, param=arp_hex)
                pat.set_cell(r, CH_ARP2, note=hi_root, inst=inst2, vol=vol2, eff=0x00, param=arp_hex)
            else:
                pat.set_cell(r, CH_ARP1, vol=max(0x18, vol1 - 10), eff=0x00, param=arp_hex)
                pat.set_cell(r, CH_ARP2, vol=max(0x16, vol2 - 10), eff=0x00, param=arp_hex)

# -----------------------------------------------------------------------------
# Melody Writer (with Stereo Twin Harmony or Stereo Delay Echo)
# -----------------------------------------------------------------------------
def write_melody_events(pat: XMPattern, events: list, inst: int = I_PWM_LEAD, vol: int = 0x4E,
                        add_echo: bool = True, echo_delay: int = 3, echo_vol: int = 0x2A,
                        twin_inst: int = None, harmony_semis: list = None):
    if twin_inst is None:
        twin_inst = I_SAW_TWIN if inst == I_SAW_LEAD else I_PWM_TWIN
    for idx, ev in enumerate(events):
        row, note_str, dur = ev[0], ev[1], ev[2]
        fx = ev[3] if len(ev) > 3 else None
        ev_vol = vol
        eff, param = 0, 0
        if fx:
            kind, val = fx
            if kind == "vib":
                eff, param = 0x04, val
            elif kind == "porta":
                eff, param = 0x03, val
            elif kind == "vol":
                ev_vol = val
        pat.set_cell(row, CH_LEAD, note=note_str, inst=inst, vol=ev_vol, eff=eff, param=param)
        if dur >= 6 and (fx is None or fx[0] != "porta"):
            for vr in range(row + 2, min(pat.rows, row + dur)):
                pat.set_cell(vr, CH_LEAD, eff=0x04, param=0x42)
        next_row = events[idx + 1][0] if idx + 1 < len(events) else pat.rows
        off_row = row + dur
        if off_row < next_row and off_row < pat.rows:
            pat.set_cell(off_row, CH_LEAD, note="OFF")

        # Twin harmony on CH_ECHO using dedicated Left-panned twin instrument!
        if harmony_semis is not None and idx < len(harmony_semis) and harmony_semis[idx] is not None:
            h_note = transpose_note(note_str, harmony_semis[idx])
            pat.set_cell(row, CH_ECHO, note=h_note, inst=twin_inst, vol=max(0x24, ev_vol - 8), eff=eff, param=param)
            if dur >= 6 and (fx is None or fx[0] != "porta"):
                for vr in range(row + 2, min(pat.rows, row + dur)):
                    pat.set_cell(vr, CH_ECHO, eff=0x04, param=0x42)
            if off_row < next_row and off_row < pat.rows:
                pat.set_cell(off_row, CH_ECHO, note="OFF")
        elif add_echo:
            er = row + echo_delay
            if er < pat.rows - 1:
                n_cur, _, _, _, _ = pat.get_cell(er, CH_ECHO)
                if n_cur == 0:
                    pat.set_cell(er, CH_ECHO, note=note_str, inst=twin_inst, vol=echo_vol)
                    e_off = min(pat.rows - 1, er + min(dur, 4))
                    if e_off < pat.rows - 1:
                        pat.set_cell(e_off, CH_ECHO, note="OFF")

def write_pad_chords(pat: XMPattern, chords: list, vol: int = 0x26):
    for r, n, off_r in chords:
        pat.set_cell(r, CH_PAD, note=n, inst=I_PAD, vol=vol)
        if off_r is not None and off_r < pat.rows:
            pat.set_cell(off_r, CH_PAD, note="OFF")

# -----------------------------------------------------------------------------
# Main Hook Melodies & Verified Diatonic Harmonies (F# Minor / Harmonic Minor)
# -----------------------------------------------------------------------------
MELODY_A1 = [
    (0,  "F#5", 3), (3,  "E-5", 2), (5,  "F#5", 2), (7,  "A-5", 3),
    (10, "G#5", 2), (12, "F#5", 2), (14, "C#5", 2),
    (16, "E-5", 2), (18, "D-5", 4), (22, "F#5", 2), (24, "A-5", 4),
    (28, "F#5", 2), (30, "E-5", 2),
    (32, "E-5", 3), (35, "F#5", 2), (37, "G#5", 3), (40, "B-5", 4),
    (44, "A-5", 2), (46, "G#5", 2),
    (48, "G#5", 3), (51, "F#5", 2), (53, "E#5", 3), (56, "G#5", 4),
    (60, "C#6", 2), (62, "B-5", 2),
]
HARM_NOTES_A1 = [
    -5, -3, -5, -3, -4, -5, -4,
    -3, -5, -4, -3, -4, -3,
    -5, -2, -4, -3, -5, -4,
    -4, -5, -4, -3, -5, -3,
]

# Climax A1 elevation: bright high variation in bars 3..4!
MELODY_A1_CLIMAX = MELODY_A1[:13] + [
    (32, "E-5", 3), (35, "G#5", 2), (37, "B-5", 3), (40, "E-6", 4, ("vib", 0x42)),
    (44, "C#6", 2), (46, "B-5", 2),
    (48, "G#5", 3), (51, "A-5", 2), (53, "B-5", 3), (56, "C#6", 4, ("vib", 0x42)),
    (60, "E#6", 2), (62, "C#6", 2),
]
HARM_A1_CLIMAX = HARM_NOTES_A1[:13] + [
    -5, -4, -4, -5, -4, -3,   # E: B4, E5, G#5, B5, A5, G#5
    -4, -5, -3, -4, -4, -5,   # C#7: E5, E5, G#5, A5(or E#5: -8)-> wait C#6-4=A5, use -8=E#5 or -5=G#5!
]
# Let's keep Bar 4 of climax strictly inside C#m7->C#7: G#5(-4=E5), A5(-5=E5), B5(-3=G#5), C#6(-5=G#5), E#6(-4=C#6), C#6(-5=G#5)
HARM_A1_CLIMAX[19:] = [-4, -5, -3, -5, -4, -5]

MELODY_A2 = [
    (0,  "A-5", 3), (3,  "G#5", 2), (5,  "F#5", 3), (8,  "C#5", 3),
    (11, "E-5", 2), (13, "F#5", 3),
    (16, "D-5", 3), (19, "F#5", 2), (21, "B-5", 3), (24, "A-5", 3),
    (27, "F#5", 2), (29, "D-5", 3),
    (32, "D-5", 2), (34, "F#5", 2), (36, "A-5", 4), (40, "E-5", 2),
    (42, "G#5", 2), (44, "B-5", 4),
    (48, "A-5", 3), (51, "F#5", 3), (54, "G#5", 2), (56, "E#5", 4),
    (60, "C#5", 2), (62, "E#5", 2),
]
HARM_NOTES_A2 = [
    -3, -4, -5, -4, -3, -5,
    -3, -4, -5, -3, -4, -3,
    -5, -4, -3, -5, -4, -3,
    -3, -5, -4, -4, -5, -4,
]

# Climax A2 soaring finale octave peak in bar 7
MELODY_A2_FINALE = MELODY_A2[:12] + [
    (32, "D-5", 2), (34, "F#5", 2), (36, "A-5", 2), (38, "D-6", 2),
    (40, "E-6", 2), (42, "B-5", 2), (44, "G#5", 4, ("vib", 0x42)),
    (48, "A-5", 3), (51, "F#5", 3), (54, "G#5", 2), (56, "E#5", 4),
    (60, "C#5", 2), (61, "E#5", 2), # ends cleanly by row 63!
]
HARM_A2_FINALE = HARM_NOTES_A2[:12] + [
    -5, -4, -3, -5,   # D: A4, D5, F#5, A5
    -5, -3, -4,       # E: B5, G#5, E5
    -3, -5, -4, -4, -5, -4,
]

def build_pattern_A1(variant: str = "base") -> XMPattern:
    pat = XMPattern(64, 12)
    write_bass_bar(pat, 0, "F#2", "octave")
    write_bass_bar(pat, 1, "D-2", "octave")
    write_bass_bar(pat, 2, "E-2", "octave")
    write_bass_bar(pat, 3, "C#2", "walk", [
        (0,"C#2",0x48),(2,"C#3",0x3E),(4,"C#2",0x46),(6,"G#2",0x3C),
        (8,"C#2",0x48),(10,"E#2",0x40),(12,"G#2",0x42),(14,"B-2",0x40),
    ])

    write_arp_segment(pat, 0,  16, "F#4", 0x73, mode="pulse")
    write_arp_segment(pat, 16, 16, "D-4", 0xB4, mode="pulse")
    write_arp_segment(pat, 32, 16, "E-4", 0x74, mode="pulse")
    write_arp_segment(pat, 48, 8,  "C#4", 0x73, mode="pulse")
    write_arp_segment(pat, 56, 8,  "C#4", 0xA4, mode="gated")

    drum_mode = "full" if variant == "base" else "driving"
    for b in range(4):
        write_drum_bar(pat, b, mode=drum_mode)

    if variant == "base":
        write_melody_events(pat, MELODY_A1, inst=I_PWM_LEAD, vol=0x4E, add_echo=True, echo_vol=0x2C)
    elif variant == "harm":
        write_melody_events(pat, MELODY_A1, inst=I_PWM_LEAD, vol=0x4E, add_echo=False, harmony_semis=HARM_NOTES_A1)
        for r, n in [(8,"C#6"),(10,"A-5"),(24,"F#5"),(26,"A-5"),(40,"G#5"),(42,"B-5"),(56,"G#5"),(58,"E#5")]:
            pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x34)
            pat.set_cell(r+2, CH_BELL2, note=n, inst=I_FM_BELL, vol=0x26, eff=0x08, param=0xC6)
        write_pad_chords(pat, [(0,"F#4",None),(16,"D-4",None),(32,"E-4",None),(48,"C#4",63)], vol=0x24)
    elif variant == "climax":
        pat.set_cell(0, CH_FX, note="C-4", inst=I_FX, vol=0x44)
        write_melody_events(pat, MELODY_A1_CLIMAX, inst=I_PWM_LEAD, vol=0x50, add_echo=False, harmony_semis=HARM_A1_CLIMAX)
        for b, rn in [(0,"F#4"),(1,"D-4"),(2,"E-4"),(3,"C#4")]:
            for st in [0, 6, 12]:
                pat.set_cell(b*16 + st, CH_BELL2, note=rn, inst=I_STAB, vol=0x30)
        for r, n in [(2,"C#6"),(6,"A-5"),(18,"A-5"),(22,"D-6"),(34,"B-5"),(38,"G#5"),(50,"G#5"),(54,"C#6")]:
            pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x36)
        write_pad_chords(pat, [(0,"F#4",None),(16,"D-4",None),(32,"E-4",None),(48,"C#4",63)], vol=0x26)
    elif variant == "finale":
        pat.set_cell(0, CH_FX, note="C-4", inst=I_FX, vol=0x44)
        write_melody_events(pat, MELODY_A1, inst=I_PWM_LEAD, vol=0x50, add_echo=False, harmony_semis=HARM_NOTES_A1)
        for b, rn in [(0,"F#4"),(1,"D-4"),(2,"E-4"),(3,"C#4")]:
            for st in [0, 6, 12]:
                pat.set_cell(b*16 + st, CH_BELL2, note=rn, inst=I_STAB, vol=0x30)
        for r, n in [(2,"C#6"),(6,"A-5"),(18,"A-5"),(22,"D-6"),(34,"B-5"),(38,"G#5"),(50,"G#5"),(54,"C#6")]:
            pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x36)
        write_pad_chords(pat, [(0,"F#4",None),(16,"D-4",None),(32,"E-4",None),(48,"C#4",63)], vol=0x26)

    return pat

def build_pattern_A2(variant: str = "base") -> XMPattern:
    pat = XMPattern(64, 12)
    write_bass_bar(pat, 0, "F#2", "octave")
    write_bass_bar(pat, 1, "B-1", "octave")
    write_bass_bar(pat, 2, "D-2", "walk", [
        (0,"D-2",0x48),(2,"D-3",0x3E),(4,"D-2",0x46),(6,"A-2",0x3C),
        (8,"E-2",0x48),(10,"E-3",0x3E),(12,"E-2",0x46),(14,"B-2",0x40),
    ])
    write_bass_bar(pat, 3, "F#2", "walk", [
        (0,"F#2",0x48),(2,"F#3",0x3E),(4,"F#2",0x46),(6,"A-2",0x3C),
        (8,"C#2",0x48),(10,"E#2",0x40),(12,"G#2",0x42),(14,"B-2",0x42),
    ])

    write_arp_segment(pat, 0,  16, "F#4", 0x73, mode="pulse")
    write_arp_segment(pat, 16, 16, "B-3", 0xA3, mode="pulse")
    write_arp_segment(pat, 32, 8,  "D-4", 0x74, mode="pulse")
    write_arp_segment(pat, 40, 8,  "E-4", 0x74, mode="pulse")
    write_arp_segment(pat, 48, 8,  "F#4", 0x73, mode="pulse")
    write_arp_segment(pat, 56, 8,  "C#4", 0xA4, mode="gated")

    drum_mode = "full" if variant == "base" else "driving"
    for b in range(3):
        write_drum_bar(pat, b, mode=drum_mode)
    if variant == "harm":
        write_drum_bar(pat, 3, mode=drum_mode, fill="tom_cascade")
    elif variant == "turnaround":
        write_drum_bar(pat, 3, mode=drum_mode, fill="turnaround")
    else:
        write_drum_bar(pat, 3, mode=drum_mode, fill="snare_build")

    if variant == "base":
        write_melody_events(pat, MELODY_A2, inst=I_PWM_LEAD, vol=0x4E, add_echo=True, echo_vol=0x2C)
    elif variant in ("harm", "climax", "turnaround"):
        mel = MELODY_A2_FINALE if variant == "turnaround" else MELODY_A2
        hrm = HARM_A2_FINALE if variant == "turnaround" else HARM_NOTES_A2
        write_melody_events(pat, mel, inst=I_PWM_LEAD, vol=0x50, add_echo=False, harmony_semis=hrm)
        for r, n in [(8,"A-5"),(10,"F#5"),(24,"D-6"),(26,"B-5"),(40,"E-6"),(42,"B-5")]:
            pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x36)
            if r + 2 < 60:
                pat.set_cell(r+2, CH_BELL2, note=n, inst=I_FM_BELL, vol=0x26, eff=0x08, param=0xC6)
        pad_end = 56 if variant == "turnaround" else 63
        write_pad_chords(pat, [(0,"F#4",None),(16,"B-3",None),(32,"D-4",None),(40,"E-4",None),(48,"C#4",pad_end)], vol=0x24)
        if variant == "turnaround":
            for ch_off in (CH_BELL, CH_BELL2, CH_ARP1, CH_ARP2, CH_ECHO, CH_PAD, CH_LEAD):
                pat.set_cell(63, ch_off, note="OFF")

    return pat

# -----------------------------------------------------------------------------
# Order 0: Intro — "Boot Sequence"
# -----------------------------------------------------------------------------
def build_intro() -> XMPattern:
    pat = XMPattern(64, 12)
    set_init_pans_and_gvol(pat, row=0, gvol=0x35)

    write_arp_segment(pat, 0,  16, "F#4", 0x73, vol1=0x24, vol2=0x20, mode="pulse")
    write_arp_segment(pat, 16, 16, "D-4", 0xB4, vol1=0x2C, vol2=0x28, mode="pulse")
    write_arp_segment(pat, 32, 16, "B-3", 0xA3, vol1=0x36, vol2=0x32, mode="gated")
    write_arp_segment(pat, 48, 16, "C#4", 0xA4, vol1=0x40, vol2=0x3A, mode="gated")

    intro_bells = [
        (0,"F#5"),(3,"C#5"),(6,"A-4"),(8,"E-5"),(11,"C#5"),(14,"A-4"),
        (16,"F#5"),(19,"D-5"),(22,"A-4"),(24,"A-5"),(27,"F#5"),(30,"D-5"),
        (32,"B-5"),(35,"F#5"),(38,"D-5"),(40,"A-5"),(43,"F#5"),(46,"D-5"),
        (48,"G#5"),(51,"E#5"),(54,"C#5"),(56,"C#6"),(59,"B-5"),(61,"G#5"),
    ]
    for r, n in intro_bells:
        pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x30)
        if r + 2 < 63:
            pat.set_cell(r + 2, CH_BELL2, note=n, inst=I_FM_BELL, vol=0x2A, eff=0x08, param=0xC6)

    # Subtle PWM Lead teaser motif on bars 3..4 rising into the drop!
    teaser = [
        (32, "B-4", 4), (36, "D-5", 4), (40, "F#5", 4), (44, "A-5", 4),
        (48, "G#5", 4), (52, "B-5", 4), (56, "C#6", 6, ("vib", 0x42)),
    ]
    write_melody_events(pat, teaser, inst=I_PWM_LEAD, vol=0x34, add_echo=True, echo_vol=0x1E)

    write_drum_bar(pat, 0, mode="intro_tick")
    write_drum_bar(pat, 1, mode="intro_tick")
    write_drum_bar(pat, 2, mode="intro_tick")
    for r in [32, 40, 48, 52]:
        pat.set_cell(r, CH_KICK, note="C-4", inst=I_KICK, vol=0x40)
    write_drum_bar(pat, 3, mode="intro_tick", fill="snare_build")

    write_bass_bar(pat, 2, "B-1", "octave")
    write_bass_bar(pat, 3, "C#2", "walk", [
        (0,"C#2",0x42),(2,"C#3",0x3A),(4,"C#2",0x44),(6,"C#3",0x3C),
        (8,"C#2",0x46),(10,"E#2",0x3E),(12,"G#2",0x42),(14,"B-2",0x44),
    ])

    pat.set_cell(48, CH_FX, note="F#4", inst=I_FX, vol=0x3E)
    write_pad_chords(pat, [(32,"B-3",None),(48,"C#4",63)], vol=0x20)
    return pat

# -----------------------------------------------------------------------------
# Orders 5 & 6: Section B — "Euphoric Major Lift"
# -----------------------------------------------------------------------------
MELODY_B1 = [
    (0,  "A-5", 4, ("vib", 0x42)), (4,  "F#5", 2), (6,  "A-5", 2), (8,  "C#6", 4, ("vib", 0x42)),
    (12, "B-5", 2), (14, "A-5", 2),
    (16, "G#5", 4), (20, "E-5", 2), (22, "G#5", 2), (24, "B-5", 4, ("vib", 0x42)),
    (28, "C#6", 2), (30, "B-5", 2),
    (32, "G#5", 3), (35, "E-5", 3), (38, "G#5", 2), (40, "B-5", 4, ("vib", 0x42)),
    (44, "A-5", 2), (46, "G#5", 2),
    (48, "F#5", 4, ("porta", 0x20)), (52, "A-5", 4), (56, "C#6", 4, ("vib", 0x42)),
    (60, "A-5", 2), (62, "F#5", 2),
]
MELODY_B2 = [
    (0,  "D-5", 3), (3,  "F#5", 3), (6,  "A-5", 2), (8,  "B-5", 4, ("vib", 0x42)),
    (12, "A-5", 2), (14, "F#5", 2),
    (16, "G#5", 3), (19, "B-5", 3), (22, "E-6", 2), (24, "D-6", 2),
    (26, "B-5", 2), (28, "G#5", 4),
    (32, "A-5", 3), (35, "C#6", 3), (38, "E-6", 2), (40, "D#6", 4, ("vib", 0x42)),
    (44, "C-6", 2), (46, "G#5", 2),
    (48, "F#5", 4), (52, "E#5", 4), (56, "G#5", 4, ("vib", 0x42)),
    (60, "C#6", 4),
]

def build_pattern_B1() -> XMPattern:
    pat = XMPattern(64, 12)
    pat.set_cell(0, CH_FX, note="C-4", inst=I_FX, vol=0x40)
    write_bass_bar(pat, 0, "D-2", "bounce")
    write_bass_bar(pat, 1, "E-2", "bounce")
    write_bass_bar(pat, 2, "C#2", "bounce")
    write_bass_bar(pat, 3, "F#2", "bounce")

    # I_ARP_P25 is Left (34), I_TRI is Right (206) -> clean L/R stereo balance!
    write_arp_segment(pat, 0,  16, "D-4", 0xB4, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x3E, vol2=0x30, mode="pulse")
    write_arp_segment(pat, 16, 16, "E-4", 0x94, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x3E, vol2=0x30, mode="pulse")
    write_arp_segment(pat, 32, 16, "C#4", 0xA3, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x3E, vol2=0x30, mode="pulse")
    write_arp_segment(pat, 48, 16, "F#4", 0xA3, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x3E, vol2=0x30, mode="pulse")

    for b in range(4):
        write_drum_bar(pat, b, mode="driving")
    write_melody_events(pat, MELODY_B1, inst=I_PWM_LEAD, vol=0x4E, add_echo=True, echo_vol=0x2A)

    for b, rn in [(0,"D-4"),(1,"E-4"),(2,"C#4"),(3,"F#4")]:
        for st in [0, 3, 6, 10, 12]:
            pat.set_cell(b*16 + st, CH_BELL2, note=rn, inst=I_STAB, vol=0x28)
            pat.set_cell(b*16 + st + 2, CH_BELL2, note="OFF")
    for r, n in [(8,"A-5"),(10,"E-5"),(24,"B-5"),(26,"G#5"),(40,"E-6"),(42,"B-5"),(56,"F#6"),(58,"C#6")]:
        pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x34)
    write_pad_chords(pat, [(0,"D-4",None),(16,"E-4",None),(32,"C#4",None),(48,"F#4",63)], vol=0x26)
    return pat

def build_pattern_B2() -> XMPattern:
    pat = XMPattern(64, 12)
    write_bass_bar(pat, 0, "B-1", "bounce")
    write_bass_bar(pat, 1, "E-2", "bounce")
    write_bass_bar(pat, 2, "A-1", "walk", [
        (0,"A-1",0x48),(2,"A-2",0x3E),(4,"A-1",0x46),(6,"E-2",0x3E),
        (8,"G#1",0x48),(10,"G#2",0x3E),(12,"G#1",0x46),(14,"D#2",0x40),
    ])
    write_bass_bar(pat, 3, "C#2", "walk", [
        (0,"C#2",0x48),(2,"C#3",0x3E),(4,"C#2",0x46),(6,"F#2",0x3E),
        (8,"C#2",0x48),(10,"E#2",0x40),(12,"G#2",0x42),(14,"B-2",0x44),
    ])

    write_arp_segment(pat, 0,  16, "B-3", 0xA3, mode="pulse")
    write_arp_segment(pat, 16, 16, "E-4", 0x74, mode="pulse")
    write_arp_segment(pat, 32, 8,  "A-3", 0xB4, mode="pulse")
    write_arp_segment(pat, 40, 8,  "G#3", 0xA4, mode="pulse")
    write_arp_segment(pat, 48, 8,  "C#4", 0x75, mode="gated")
    write_arp_segment(pat, 56, 8,  "C#4", 0xA4, mode="gated")

    for b in range(3):
        write_drum_bar(pat, b, mode="driving")
    write_drum_bar(pat, 3, mode="driving", fill="snare_build")
    write_melody_events(pat, MELODY_B2, inst=I_PWM_LEAD, vol=0x4E, add_echo=True, echo_vol=0x2A)

    for b, rn in [(0,"B-3"),(1,"E-4"),(2,"A-3"),(3,"C#4")]:
        for st in [0, 3, 6, 10, 12]:
            pat.set_cell(b*16 + st, CH_BELL2, note=rn, inst=I_STAB, vol=0x28)
    write_pad_chords(pat, [(0,"B-3",None),(16,"E-4",None),(32,"A-3",None),(48,"C#4",62)], vol=0x26)
    return pat

# -----------------------------------------------------------------------------
# Orders 7 & 8: Section C — "Cyber Breakdown & Bell Cascade"
# -----------------------------------------------------------------------------
def build_pattern_C1() -> XMPattern:
    pat = XMPattern(64, 12)
    pat.set_cell(0, CH_FX, note="C-3", inst=I_FX, vol=0x40)
    write_bass_bar(pat, 0, "F#2", "sub")
    write_bass_bar(pat, 1, "D-2", "sub")
    write_bass_bar(pat, 2, "B-1", "sub")
    write_bass_bar(pat, 3, "C#2", "sub")

    for b in range(4):
        write_drum_bar(pat, b, mode="breakdown")

    bar_arps = [
        ["F#4","A-4","C#5","F#5","A-5","F#5","C#5","A-4", "F#4","C#5","E-5","A-5","C#6","A-5","E-5","C#5"],
        ["D-4","F#4","A-4","D-5","F#5","D-5","A-4","F#4", "D-4","A-4","C#5","F#5","A-5","F#5","C#5","A-4"],
        ["B-3","D-4","F#4","B-4","D-5","B-4","F#4","D-4", "B-3","F#4","A-4","D-5","F#5","D-5","A-4","F#4"],
        ["C#4","E#4","G#4","C#5","E#5","C#5","G#4","E#4", "C#4","G#4","B-4","E#5","G#5","E#5","B-4","G#4"],
    ]
    for b, notes in enumerate(bar_arps):
        for s_idx, n in enumerate(notes):
            r = b * 16 + s_idx
            pat.set_cell(r, CH_BELL, note=n, inst=I_FM_BELL, vol=0x2A if s_idx % 4 == 0 else 0x1E)
            if r + 3 < 64:
                pat.set_cell(r + 3, CH_BELL2, note=n, inst=I_FM_BELL, vol=0x24, eff=0x08, param=0xC6)

    # Balanced soft stereo arps underneath (Left P25, Right Tri)
    write_arp_segment(pat, 0,  16, "F#4", 0x73, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x28, vol2=0x1E, mode="pulse")
    write_arp_segment(pat, 16, 16, "D-4", 0xB4, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x28, vol2=0x1E, mode="pulse")
    write_arp_segment(pat, 32, 16, "B-3", 0xA3, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x28, vol2=0x1E, mode="pulse")
    write_arp_segment(pat, 48, 16, "C#4", 0xA4, inst1=I_ARP_P25, inst2=I_TRI, vol1=0x28, vol2=0x1E, mode="pulse")
    write_pad_chords(pat, [(0,"F#4",None),(16,"D-4",None),(32,"B-3",None),(48,"C#4",63)], vol=0x22)
    return pat

def build_pattern_C2() -> XMPattern:
    pat = XMPattern(64, 12)
    write_bass_bar(pat, 0, "F#2", "sub")
    write_bass_bar(pat, 1, "D-2", "sub")
    write_bass_bar(pat, 2, "B-1", "octave")
    write_bass_bar(pat, 3, "C#2", "walk", [
        (0,"C#2",0x46),(2,"C#3",0x40),(4,"C#2",0x46),(6,"C#3",0x40),
        (8,"C#2",0x48),(10,"C#3",0x42),(12,"C#2",0x48),(14,"C#3",0x46),
    ])

    write_drum_bar(pat, 0, mode="halftime")
    write_drum_bar(pat, 1, mode="halftime")
    write_drum_bar(pat, 2, mode="full")
    write_drum_bar(pat, 3, mode="full", fill="snare_32_drop")

    write_arp_segment(pat, 0,  16, "F#4", 0x73, vol1=0x2C, vol2=0x28, mode="pulse")
    write_arp_segment(pat, 16, 16, "D-4", 0xB4, vol1=0x32, vol2=0x2E, mode="pulse")
    write_arp_segment(pat, 32, 16, "B-3", 0xA3, vol1=0x38, vol2=0x34, mode="gated")
    write_arp_segment(pat, 48, 16, "C#4", 0xA4, vol1=0x40, vol2=0x3C, mode="gated")

    pat.set_cell(32, CH_LEAD, note="C#5", inst=I_PWM_LEAD, vol=0x38)
    pat.set_cell(48, CH_LEAD, note="C#6", inst=I_PWM_LEAD, vol=0x4E, eff=0x03, param=0x16)
    for r in range(49, 63):
        pat.set_cell(r, CH_LEAD, eff=0x03, param=0x16)
    pat.set_cell(63, CH_LEAD, note="OFF")

    pat.set_cell(48, CH_FX, note="F#4", inst=I_FX, vol=0x44)
    write_pad_chords(pat, [(0,"F#4",None),(16,"D-4",None),(32,"B-3",None),(48,"C#4",63)], vol=0x24)
    return pat

# -----------------------------------------------------------------------------
# Orders 11 & 12: Section E — "Virtuoso Razor-Saw Chip Solo"
# -----------------------------------------------------------------------------
SOLO_E1 = [
    (0,"F#5",2),(2,"A-5",2),(4,"C#6",2),(6,"B-5",2),
    (8,"A-5",2),(10,"G#5",2),(12,"F#5",2),(14,"E-5",2),
    (16,"E-5",2),(18,"G#5",2),(20,"B-5",2),(22,"A-5",2),
    (24,"G#5",2),(26,"F#5",2),(28,"E-5",2),(30,"D-5",2),
    (32,"D-5",2),(34,"F#5",2),(36,"A-5",2),(38,"D-6",2),
    (40,"C#6",2),(42,"B-5",2),(44,"A-5",2),(46,"F#5",2),
    (48,"E#5",2),(50,"G#5",2),(52,"B-5",2),(54,"D-6",2),
    (56,"C#6",2),(58,"B-5",2),(60,"G#5",2),(62,"E#5",2),
]

SOLO_E2 = [
    (0,"F#5",2),(2,"G#5",1),(3,"A-5",1),(4,"C#6",4,("vib",0x42)),
    (8,"F#6",2),(10,"E-6",2),(12,"C#6",2),(14,"A-5",2),
    (16,"B-5",3),(19,"G#5",3),(22,"E-5",2),(24,"G#5",2),
    (26,"B-5",2),(28,"E-6",4,("vib",0x42)),
    (32,"D-6",2),(34,"A-5",2),(36,"F#5",2),(38,"A-5",2),
    (40,"E-6",2),(42,"B-5",2),(44,"G#5",2),(46,"B-5",2),
    (48,"E#6",2),(50,"C#6",2),(52,"G#5",2),(54,"B-5",2),
    (56,"C#6",2),(58,"E#6",2),(60,"G#6",4),
]

def build_pattern_E1() -> XMPattern:
    pat = XMPattern(64, 12)
    pat.set_cell(0, CH_FX, note="C-4", inst=I_FX, vol=0x40)
    write_bass_bar(pat, 0, "F#2", "octave")
    write_bass_bar(pat, 1, "E-2", "octave")
    write_bass_bar(pat, 2, "D-2", "octave")
    write_bass_bar(pat, 3, "C#2", "octave")

    write_arp_segment(pat, 0,  16, "F#4", 0x73, mode="gated")
    write_arp_segment(pat, 16, 16, "E-4", 0x74, mode="gated")
    write_arp_segment(pat, 32, 16, "D-4", 0x74, mode="gated")
    write_arp_segment(pat, 48, 16, "C#4", 0xA4, mode="gated")

    for b in range(4):
        write_drum_bar(pat, b, mode="driving")
    write_melody_events(pat, SOLO_E1, inst=I_SAW_LEAD, vol=0x4E, add_echo=True, echo_delay=3, echo_vol=0x28, twin_inst=I_SAW_TWIN)

    pat.set_cell(60, CH_BELL, note="C-5", inst=I_TOM_ZAP, vol=0x38)
    write_pad_chords(pat, [(0,"F#4",None),(16,"E-4",None),(32,"D-4",None),(48,"C#4",63)], vol=0x20)
    return pat

def build_pattern_E2() -> XMPattern:
    pat = XMPattern(64, 12)
    write_bass_bar(pat, 0, "F#2", "octave")
    write_bass_bar(pat, 1, "E-2", "octave")
    write_bass_bar(pat, 2, "D-2", "walk", [
        (0,"D-2",0x48),(2,"D-3",0x3E),(4,"D-2",0x46),(6,"A-2",0x3C),
        (8,"E-2",0x48),(10,"E-3",0x3E),(12,"E-2",0x46),(14,"B-2",0x40),
    ])
    write_bass_bar(pat, 3, "C#2", "walk", [
        (0,"C#2",0x48),(2,"C#3",0x3E),(4,"C#2",0x46),(6,"G#2",0x3E),
        (8,"C#2",0x48),(10,"E#2",0x40),(12,"G#2",0x44),(14,"B-2",0x46),
    ])

    write_arp_segment(pat, 0,  16, "F#4", 0x73, mode="gated")
    write_arp_segment(pat, 16, 16, "E-4", 0x74, mode="gated")
    write_arp_segment(pat, 32, 8,  "D-4", 0x74, mode="gated")
    write_arp_segment(pat, 40, 8,  "E-4", 0x74, mode="gated")
    write_arp_segment(pat, 48, 16, "C#4", 0xA4, mode="gated")

    for b in range(3):
        write_drum_bar(pat, b, mode="driving")
    write_drum_bar(pat, 3, mode="driving", fill="snare_build")

    harm_e2 = [None]*14 + [
        -5,-3,-4,-3, -5,-3,-4,-3,
        -4,-5,-3,-3, -5,-4,-3,
    ]
    assert len(harm_e2) == len(SOLO_E2)
    write_melody_events(pat, SOLO_E2, inst=I_SAW_LEAD, vol=0x4E, add_echo=True, echo_delay=3, echo_vol=0x28, twin_inst=I_SAW_TWIN, harmony_semis=harm_e2)
    write_pad_chords(pat, [(0,"F#4",None),(16,"E-4",None),(32,"D-4",None),(48,"C#4",62)], vol=0x22)
    return pat

# -----------------------------------------------------------------------------
# Assemble Full 15-Order Keygen Tune
# -----------------------------------------------------------------------------
def build_song() -> XMModule:
    mod = XMModule(
        name="RAZOR KEYGEN 440",
        channels=12,
        speed=6,
        bpm=142,
        loop_start=1,
    )
    for inst in build_all_instruments():
        mod.add_instrument(inst)

    p0  = build_intro()                    # Order 0: Boot Intro
    p1  = build_pattern_A1("base")         # Order 1: Main Hook A1
    p2  = build_pattern_A2("base")         # Order 2: Main Hook A2
    p3  = build_pattern_A1("harm")         # Order 3: Hook A1 + Twin Harmony & Bell
    p4  = build_pattern_A2("harm")         # Order 4: Hook A2 + Twin Harmony & Tom Fill
    p5  = build_pattern_B1()               # Order 5: Major Lift B1
    p6  = build_pattern_B2()               # Order 6: Major Lift B2
    p7  = build_pattern_C1()               # Order 7: Cyber Breakdown C1
    p8  = build_pattern_C2()               # Order 8: Breakdown Build C2
    p9  = build_pattern_A1("climax")       # Order 9: Overdrive Climax D1
    p10 = build_pattern_A2("climax")       # Order 10: Overdrive Climax D2
    p11 = build_pattern_E1()               # Order 11: Razor-Saw Chip Solo E1
    p12 = build_pattern_E2()               # Order 12: Razor-Saw Chip Solo E2
    p13 = build_pattern_A1("finale")       # Order 13: Final Chorus F1
    p14 = build_pattern_A2("turnaround")   # Order 14: Final Chorus & Turnaround -> Order 1

    # Crash on Order 1 drop + reset global volume/pans cleanly on both Order 0 and Order 1
    p1.set_cell(0, CH_FX, note="C-4", inst=I_FX, vol=0x3E, eff=0x10, param=0x36)
    set_init_pans_and_gvol(p0, row=0, gvol=0x36)
    set_init_pans_and_gvol(p1, row=0, gvol=0x36)

    for p in [p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14]:
        mod.add_pattern(p)

    mod.orders = list(range(15))
    return mod

if __name__ == "__main__":
    os.makedirs("/workspace/submission", exist_ok=True)
    m = build_song()
    out_xm = "/workspace/submission/tune.xm"
    m.save(out_xm)
    print(f"Saved {out_xm} ({os.path.getsize(out_xm)} bytes, {len(m.orders)} orders, {len(m.instruments)} instruments)")
