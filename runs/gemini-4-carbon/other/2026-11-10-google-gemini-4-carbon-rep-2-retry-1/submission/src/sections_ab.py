"""
Patterns 00..09 of 'CYBERNETIC FUGUE // KEYGEN'
  Pos 00..01: Intro Fanfare ("Cracktro Boot Sequence")
  Pos 02..05: Section A - Main Keygen Hook ("Neon Cipher", loop_start = 2!)
  Pos 06..09: Section B - Euphoric Chorus ("Skyline Overdrive")
"""
from xm_builder import Pattern
from tracker_helpers import (
    I_KICK, I_SNARE, I_CLAP, I_RIM, I_HATC, I_HATO, I_CRASH, I_TOM,
    I_BASS, I_ACID, I_LEAD1, I_LEAD2, I_CHIP, I_BELL, I_PAD, I_STAB, I_RISER,
    CH_KICK, CH_SNARE, CH_HAT, CH_BASS, CH_LEAD1, CH_LEAD2, CH_CHIP, CH_BELL,
    CH_PAD1, CH_PAD2, CH_PAD3, CH_PAD4,
    CHORDS, tr, write_lead_phrase, fill_drums_driving, fill_drum_turnaround,
    fill_bass_gallop, fill_bass_styled, write_stereo_delay_echo, fill_chip_arp_bar, place_pad_chord, place_brass_stabs,
)


def make_pat00_intro_a() -> Pattern:
    """Pos 00 (Bars 1-4): Sparkling neo-baroque CrystalDX bell arpeggio + warm pad + teasing motif."""
    p = Pattern(64, 12)
    prog = [(0, 16, "F#m9"), (16, 16, "Dmaj7"), (32, 8, "Bm7"), (40, 8, "E"), (48, 8, "C#m7"), (56, 8, "F#m")]
    for r0, ln, chd in prog:
        place_pad_chord(p, r0, ln, chd, vol=32)

    # Delicate ticking clock hats & rim
    for r in range(64):
        if r % 4 == 0:
            p.set(r, CH_HAT, "C-4", I_HATC, 30)
        elif r % 2 == 1:
            p.set(r, CH_HAT, "C-4", I_HATC, 18)
        if r in (12, 28, 44, 60):
            p.set(r, CH_SNARE, "C-4", I_RIM, 30)

    # Sparkling harpsichord-bell 16th figure (Ch 7)
    bell_bars = [
        # Bar 1: F#m9
        ["F#5", "C#5", "A-4", "C#5", "G#5", "C#5", "A-4", "C#5", "A-5", "F#5", "C#5", "A-4", "G#5", "F#5", "C#5", "A-4"],
        # Bar 2: Dmaj7
        ["F#5", "D-5", "A-4", "D-5", "G#5", "D-5", "A-4", "D-5", "A-5", "F#5", "D-5", "A-4", "E-5", "C#5", "A-4", "E-5"],
        # Bar 3: Bm7 -> E
        ["F#5", "D-5", "B-4", "D-5", "A-5", "F#5", "D-5", "B-4", "G#5", "E-5", "B-4", "E-5", "B-5", "G#5", "E-5", "B-4"],
        # Bar 4: C#m7 -> F#m
        ["G#5", "E-5", "C#5", "E-5", "B-5", "G#5", "E-5", "C#5", "A-5", "F#5", "C#5", "A-4", "F#5", "C#5", "A-4", "C#5"],
    ]
    for b_idx, notes in enumerate(bell_bars):
        for s_idx, nt in enumerate(notes):
            r = b_idx * 16 + s_idx
            vel = 52 if s_idx % 4 == 0 else (40 if s_idx % 2 == 0 else 32)
            p.set(r, CH_BELL, nt, I_BELL, vel)

    # Offbeat subtle 0xy chip-pulses answering the bell
    for r0, _, chd in prog:
        _, c_root, xy, _ = CHORDS[chd]
        p.set(r0 + 2, CH_CHIP, c_root, I_CHIP, 32, 0, xy)
        p.set(r0 + 4, CH_CHIP, "off")
        p.set(r0 + 6, CH_CHIP, tr(c_root, 12), I_CHIP, 28, 0, xy)
        p.set(r0 + 8, CH_CHIP, "off")

    # Teasing lyrical HeroPWM lead enters in Bar 2!
    lead = [
        (16, 6, "C#5", "soft"),
        (22, 2, "E-5", "slide"),
        (24, 6, "F#5", "norm"),
        (30, 2, "E-5", "grace"),
        (32, 6, "D-5", "norm"),
        (38, 2, "C#5", "norm"),
        (40, 8, "B-4", "norm"),
        (48, 4, "C#5", "norm"),
        (52, 4, "E-5", "slide"),
        (56, 7, "F#5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, lead, base_vol=50, pan=64)
    write_stereo_delay_echo(p, CH_LEAD2, I_LEAD1, lead, delay_rows=3, echo_vol=20, pan=204, max_row=64)
    return p


def make_pat01_intro_b() -> Pattern:
    """Pos 01 (Bars 5-8): Twin-lead neo-classical fanfare + pulsing bass + Bar-8 Riser & Fill into Drop!"""
    p = Pattern(64, 12)
    prog = [(0, 16, "F#m"), (16, 8, "Dmaj7"), (24, 8, "Bm7"), (32, 8, "G#m7b5"), (40, 8, "C#7sus4"), (48, 8, "C#7"), (56, 8, "C#7b9")]
    for r0, ln, chd in prog:
        # Leave Ch 11 free in Bar 8 (row 48..63) for CyberRiser!
        place_pad_chord(p, r0, ln, chd, vol=36, include_ch11=(r0 < 48))

    # Pulsing 8th-note sub-bass awakening in Bars 5-7, accelerating to 16ths in Bar 8!
    for r0, ln, chd in prog:
        root = CHORDS[chd][0]
        step_sz = 1 if r0 >= 48 else 2
        for st in range(0, ln, step_sz):
            v = 56 if st % 4 == 0 else 44
            nt = tr(root, 12) if (r0 >= 48 and st % 2 == 1) else root
            p.set(r0 + st, CH_BASS, nt, I_BASS, v)

    # Four-on-the-floor kick pulse Bars 5-7 -> full explosive turnaround fill in Bar 8!
    for b in range(3):
        r0 = b * 16
        for st in (0, 4, 8, 12):
            p.set(r0 + st, CH_KICK, "C-4", I_KICK, 56 + b * 3)
        for st in range(16):
            p.set(r0 + st, CH_HAT, "C-4", I_HATO if st in (6, 14) else I_HATC, 36 + b * 3)
        p.set(r0 + 12, CH_SNARE, "C-4", I_SNARE, 48 + b * 4)
    fill_drum_turnaround(p, start_row=48, intense=True)
    # 1-bar CyberRiser on Ch 11!
    p.set(48, CH_PAD4, "C#4", I_RISER, 58, 8, 148)

    # Chip arp builds energy
    for r0, ln, chd in prog:
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=38 if r0 < 48 else 46)

    # Rising Twin-Lead Baroque Fanfare (Ch 4 + Ch 5 in 3rds!)
    lead1 = [
        (0, 4, "F#4", "norm"), (4, 2, "G#4", "norm"), (6, 2, "A-4", "norm"),
        (8, 6, "C#5", "accent"), (14, 2, "B-4", "grace"),
        (16, 4, "A-4", "norm"), (20, 4, "F#5", "slide"),
        (24, 6, "D-5", "norm"), (30, 2, "C#5", "norm"),
        (32, 4, "B-4", "norm"), (36, 4, "D-5", "norm"),
        (40, 6, "C#5", "accent"), (46, 2, "B-4", "norm"),
        # Bar 8 dominant C#7 harmonic-minor climb!
        (48, 2, "C#5", "norm"), (50, 2, "D-5", "norm"), (52, 2, "F-5", "norm"), (54, 2, "G#5", "norm"),
        (56, 2, "B-5", "accent"), (58, 2, "G#5", "norm"), (60, 2, "F-5", "norm"), (62, 2, "G#5", "accent"),
    ]
    lead2 = [
        (0, 4, "A-4", "soft"), (4, 2, "B-4", "soft"), (6, 2, "C#5", "soft"),
        (8, 6, "F#5", "norm"), (14, 2, "D-5", "grace"),
        (16, 4, "C#5", "norm"), (20, 4, "A-5", "slide"),
        (24, 6, "F#5", "norm"), (30, 2, "E-5", "norm"),
        (32, 4, "D-5", "norm"), (36, 4, "F#5", "norm"),
        (40, 6, "F#5", "norm"), (46, 2, "D-5", "norm"),
        (48, 2, "F-5", "norm"), (50, 2, "F#5", "norm"), (52, 2, "G#5", "norm"), (54, 2, "B-5", "norm"),
        (56, 2, "D-6", "accent"), (58, 2, "B-5", "norm"), (60, 2, "G#5", "norm"), (62, 2, "B-5", "accent"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, lead1, base_vol=56, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, lead2, base_vol=48, pan=176)
    return p


def make_pat02_sec_a1a() -> Pattern:
    """
    Pos 02 (Bars 9-12) — LOOP START!
    Main Keygen Hook 'Neon Cipher' Part 1: F#m | Dmaj7 | E | C#m7 -> F#m
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=False, crash_bar0=True, energy=1)

    prog = [(0, 16, "F#m", None), (16, 16, "Dmaj7", None), (32, 16, "E", None), (48, 8, "C#m7", "E-2"), (56, 8, "F#m", "A-2")]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'gallop', I_BASS, vol=61, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=44)
        if ln == 16:
            place_brass_stabs(p, r0, chd, steps=(0, 6, 12), vol=42)
        else:
            place_brass_stabs(p, r0, chd, steps=(0, 6), vol=42)

    # Iconic Main Keygen Hook on Ch 4 (HeroPWM)!
    hook = [
        # Bar 9 (F#m): Heroic leap F#4 -> C#5, nimble 16th turn, syncopated bounce
        (0, 2, "F#4", "accent"), (2, 4, "C#5", "slide"),
        (6, 1, "B-4", "norm"), (7, 1, "C#5", "norm"), (8, 2, "D-5", "norm"), (10, 2, "C#5", "norm"),
        (12, 2, "A-4", "stacc"), (14, 2, "C#5", "norm"),
        # Bar 10 (Dmaj7): Expressive slide to F#5 -> cascading lydian/major7 sparkle
        (16, 2, "E-5", "norm"), (18, 4, "F#5", "slide"),
        (22, 2, "E-5", "norm"), (24, 4, "C#5", "norm"),
        (28, 2, "A-4", "stacc"), (30, 2, "B-4", "grace"),
        # Bar 11 (E): Soaring lift to G#5!
        (32, 4, "E-5", "accent"), (36, 2, "F#5", "norm"), (38, 4, "G#5", "slide"),
        (42, 2, "F#5", "norm"), (44, 2, "E-5", "norm"), (46, 2, "B-4", "stacc"),
        # Bar 12 (C#m7 -> F#m): Virtuoso cascade landing on F#5!
        (48, 2, "A-5", "accent"), (50, 2, "G#5", "norm"), (52, 2, "F#5", "norm"), (54, 2, "E-5", "norm"),
        (56, 2, "C#5", "norm"), (58, 6, "F#5", "slide"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, hook, base_vol=58, pan=64)
    write_stereo_delay_echo(p, CH_LEAD2, I_LEAD1, hook, delay_rows=3, echo_vol=22, pan=208, max_row=64)

    # Sparkling CrystalDX Bell answer accents in phrase gaps!
    for r, nt, v in [
        (12, "F#5", 46), (14, "A-5", 48),
        (28, "D-5", 46), (30, "F#5", 50),
        (44, "G#5", 46), (46, "B-5", 50),
        (60, "C#6", 48), (62, "A-5", 44),
    ]:
        p.set(r, CH_BELL, nt, I_BELL, v)
    return p


def make_pat03_sec_a1b() -> Pattern:
    """Pos 03 (Bars 13-16) — Main Hook Part 2: Bm7 | G#m7b5 -> C#7 | F#m -> E/G# -> A | Bm7 -> C#7"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=False, crash_bar0=False, energy=1)
    fill_drum_turnaround(p, start_row=56, intense=False)

    prog = [
        (0, 16, "Bm7", None),
        (16, 8, "G#m7b5", None), (24, 8, "C#7", "F-2"),
        (32, 8, "F#m", "G#1"), (40, 8, "A", None),
        (48, 8, "Bm7", None), (56, 8, "C#7", "F-2"),
    ]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'gallop', I_BASS, vol=61, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=44)
        place_brass_stabs(p, r0, chd, steps=(0, 6) if ln == 8 else (0, 6, 12), vol=42)

    hook_b = [
        # Bar 13 (Bm7): Rising Dorian/Aeolian arpeggio sweep
        (0, 2, "B-4", "norm"), (2, 2, "D-5", "norm"), (4, 4, "F#5", "accent"),
        (8, 2, "A-5", "slide"), (10, 2, "G#5", "norm"), (12, 4, "F#5", "norm"),
        # Bar 14 (G#m7b5 -> C#7): Dramatic harmonic-minor tension (F-5 = E#5!)
        (16, 4, "G#5", "accent"), (20, 2, "F#5", "norm"), (22, 2, "D-5", "norm"),
        (24, 6, "F-5", "slide"), (30, 2, "C#5", "stacc"),
        # Bar 15 (F#m -> A): Heroic sequence climbing upward
        (32, 3, "F#5", "norm"), (35, 1, "G#5", "grace"), (36, 4, "A-5", "accent"),
        (40, 4, "E-5", "norm"), (44, 4, "C#5", "norm"),
        # Bar 16 (Bm7 -> C#7): Snappy turnaround motif setting up Twin-Lead repeat!
        (48, 2, "D-5", "norm"), (50, 2, "E-5", "norm"), (52, 2, "F#5", "accent"), (54, 2, "D-5", "norm"),
        (56, 4, "F-5", "accent"), (60, 2, "G#5", "norm"), (62, 2, "F-5", "stacc"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, hook_b, base_vol=58, pan=64)
    write_stereo_delay_echo(p, CH_LEAD2, I_LEAD1, [e for e in hook_b if e[0] < 28], delay_rows=3, echo_vol=21, pan=208, max_row=32)

    # Subtle Lead 2 harmony enters in Bars 15-16 to anticipate Section A2!
    harm_tail = [
        (32, 4, "A-4", "soft"), (36, 4, "C#5", "norm"),
        (40, 4, "A-4", "soft"), (44, 4, "E-4", "soft"),
        (48, 2, "F#4", "norm"), (50, 2, "G#4", "norm"), (52, 2, "A-4", "norm"), (54, 2, "F#4", "norm"),
        (56, 4, "G#4", "norm"), (60, 2, "B-4", "norm"), (62, 2, "C#5", "stacc"),
    ]
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, harm_tail, base_vol=48, pan=176)

    for r, nt in [(6, "B-5"), (14, "D-5"), (28, "G#5"), (30, "B-5"), (44, "A-5"), (46, "C#6")]:
        p.set(r, CH_BELL, nt, I_BELL, 48)
    return p


def make_pat04_sec_a2a() -> Pattern:
    """Pos 04 (Bars 17-20) — Main Hook Variation with Glorious Twin-Lead Harmonies in 3rds/6ths!"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=2)

    prog = [(0, 16, "F#m", None), (16, 16, "Dmaj7", None), (32, 16, "E", None), (48, 8, "A", "G#1"), (56, 8, "E/G#", None)]
    for r0, ln, chd, wlk in prog:
        fill_bass_gallop(p, r0, ln, chd, I_BASS, vol=62, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=45)
        place_pad_chord(p, r0, ln, chd, vol=33)

    lead1 = [
        (0, 2, "F#4", "accent"), (2, 4, "C#5", "slide"),
        (6, 1, "B-4", "norm"), (7, 1, "C#5", "norm"), (8, 2, "D-5", "norm"), (10, 2, "C#5", "norm"),
        (12, 2, "F#5", "accent"), (14, 2, "E-5", "norm"),
        (16, 2, "E-5", "norm"), (18, 4, "F#5", "slide"),
        (22, 2, "A-5", "accent"), (24, 4, "F#5", "norm"),
        (28, 2, "E-5", "norm"), (30, 2, "F#5", "grace"),
        (32, 4, "G#5", "accent"), (36, 2, "F#5", "norm"), (38, 4, "E-5", "norm"),
        (42, 2, "F#5", "norm"), (44, 2, "G#5", "norm"), (46, 2, "B-5", "accent"),
        # Bar 20 (A -> E/G#): Radiant major lift!
        (48, 4, "A-5", "accent"), (52, 2, "G#5", "norm"), (54, 2, "E-5", "norm"),
        (56, 4, "G#5", "slide"), (60, 4, "B-5", "accent"),
    ]
    # Twin Harmony Lead 2 in diatonic 3rds below/above!
    lead2 = [
        (0, 2, "A-4", "norm"), (2, 4, "F#5", "slide"),
        (6, 1, "D-5", "norm"), (7, 1, "E-5", "norm"), (8, 2, "F#5", "norm"), (10, 2, "E-5", "norm"),
        (12, 2, "A-5", "norm"), (14, 2, "G#5", "norm"),
        (16, 2, "C#5", "norm"), (18, 4, "D-5", "slide"),
        (22, 2, "F#5", "norm"), (24, 4, "D-5", "norm"),
        (28, 2, "C#5", "norm"), (30, 2, "D-5", "grace"),
        (32, 4, "B-4", "norm"), (36, 2, "D-5", "norm"), (38, 4, "B-4", "norm"),
        (42, 2, "D-5", "norm"), (44, 2, "E-5", "norm"), (46, 2, "G#5", "norm"),
        (48, 4, "C#5", "norm"), (52, 2, "E-5", "norm"), (54, 2, "C#5", "norm"),
        (56, 4, "E-5", "slide"), (60, 4, "G#5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, lead1, base_vol=58, pan=76)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, lead2, base_vol=50, pan=180)

    # Sparkling offbeat CrystalDX Bell arpeggios
    for bar_i, notes in enumerate([
        ["A-5", "F#5", "C#6", "A-5"],
        ["F#5", "A-5", "D-6", "A-5"],
        ["G#5", "B-5", "E-6", "B-5"],
        ["A-5", "C#6", "B-5", "G#5"],
    ]):
        for j, nt in enumerate(notes):
            p.set(bar_i * 16 + j * 4 + 2, CH_BELL, nt, I_BELL, 42)
    return p


def make_pat05_sec_a2b() -> Pattern:
    """Pos 05 (Bars 21-24) — Pivot to Chorus: Bm7 | C#7 | F#m -> E | Dmaj7 -> E7 + Riser!"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 3, clap=True, crash_bar0=False, energy=2)
    fill_drum_turnaround(p, start_row=48, intense=True)
    p.set(48, CH_PAD4, "E-4", I_RISER, 56, 8, 148)

    prog = [
        (0, 16, "Bm7", None),
        (16, 16, "C#7", "F-2"),
        (32, 8, "F#m", None), (40, 8, "E", None),
        (48, 8, "Dmaj7", None), (56, 8, "E7", "G#2"),
    ]
    for r0, ln, chd, wlk in prog:
        fill_bass_gallop(p, r0, ln, chd, I_BASS, vol=62, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=45)
        place_pad_chord(p, r0, ln, chd, vol=35, include_ch11=(r0 < 48))

    lead1 = [
        (0, 4, "F#5", "accent"), (4, 2, "E-5", "norm"), (6, 4, "D-5", "norm"),
        (10, 2, "E-5", "norm"), (12, 4, "F#5", "slide"),
        (16, 6, "F-5", "accent"), (22, 2, "F#5", "norm"), (24, 4, "G#5", "slide"), (28, 4, "C#5", "norm"),
        (32, 6, "F#5", "accent"), (38, 2, "G#5", "grace"), (40, 6, "G#5", "norm"), (46, 2, "A-5", "norm"),
        # Bar 24: Dominant E7 lift into Dmaj7 Chorus!
        (48, 4, "F#5", "norm"), (52, 4, "A-5", "slide"),
        (56, 4, "G#5", "accent"), (60, 2, "B-5", "norm"), (62, 2, "G#5", "accent"),
    ]
    lead2 = [
        (0, 4, "D-5", "norm"), (4, 2, "C#5", "norm"), (6, 4, "B-4", "norm"),
        (10, 2, "C#5", "norm"), (12, 4, "D-5", "slide"),
        (16, 6, "C#5", "norm"), (22, 2, "D-5", "norm"), (24, 4, "F-5", "slide"), (28, 4, "G#4", "norm"),
        (32, 6, "A-4", "norm"), (38, 2, "B-4", "grace"), (40, 6, "B-4", "norm"), (46, 2, "C#5", "norm"),
        (48, 4, "D-5", "norm"), (52, 4, "F#5", "slide"),
        (56, 4, "E-5", "norm"), (60, 2, "G#5", "norm"), (62, 2, "E-5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, lead1, base_vol=58, pan=76)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, lead2, base_vol=50, pan=180)
    return p


def make_pat06_chorus_b1a() -> Pattern:
    """
    Pos 06 (Bars 25-28) — Euphoric Chorus 'Skyline Overdrive' Part 1:
    Dmaj7 | E | C#m7 | F#m7 -> F#7 (secondary dominant pull!)
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=2)

    prog = [(0, 16, "Dmaj7", None), (16, 16, "E", None), (32, 16, "C#m7", None), (48, 8, "F#m7", None), (56, 8, "F#7", "A#2")]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'chorus_drive', I_BASS, vol=62, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=44)
        place_pad_chord(p, r0, ln, chd, vol=38)

    # Soaring, unforgettable Chorus Anthem on Ch 4!
    chorus_mel = [
        # Bar 25 (Dmaj7): Radiant A5 peak!
        (0, 6, "A-5", "accent"), (6, 2, "G#5", "norm"), (8, 4, "F#5", "norm"), (12, 4, "E-5", "slide"),
        # Bar 26 (E): Uplifting G#5 -> B5 arc
        (16, 4, "G#5", "accent"), (20, 2, "F#5", "norm"), (22, 2, "E-5", "norm"), (24, 6, "B-5", "slide"), (30, 2, "A-5", "grace"),
        # Bar 27 (C#m7): Emotional yearning phrase
        (32, 6, "G#5", "accent"), (38, 2, "F#5", "norm"), (40, 4, "E-5", "norm"), (44, 4, "C#5", "norm"),
        # Bar 28 (F#m7 -> F#7): Goosebump A#5 (maj3 of F#7!) leading into Bm7!
        (48, 4, "F#5", "norm"), (52, 4, "E-5", "norm"),
        (56, 6, "A#5", "accent"), (62, 2, "C#6", "slide"),
    ]
    # True contrapuntal answer line on Ch 5 (moves when Ch 4 holds!)
    counter_mel = [
        (4, 2, "C#5", "soft"), (6, 2, "D-5", "soft"), (10, 2, "A-4", "soft"), (12, 4, "C#5", "norm"),
        (16, 4, "B-4", "soft"), (24, 2, "E-5", "norm"), (26, 2, "F#5", "norm"), (28, 2, "G#5", "norm"), (30, 2, "F#5", "norm"),
        (36, 2, "B-4", "soft"), (38, 2, "C#5", "soft"), (42, 2, "G#4", "soft"), (44, 4, "B-4", "norm"),
        (48, 4, "A-4", "soft"), (52, 4, "C#5", "norm"), (56, 4, "C#5", "norm"), (60, 4, "E-5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, chorus_mel, base_vol=60, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, counter_mel, base_vol=48, pan=176)

    # Shimmering bell sparkles on beat-1 & beat-3-and
    for r, nt in [(0, "C#6"), (10, "A-5"), (16, "B-5"), (26, "G#5"), (32, "B-5"), (42, "G#5"), (48, "A-5"), (56, "C#6")]:
        p.set(r, CH_BELL, nt, I_BELL, 44)
    return p


def make_pat07_chorus_b1b() -> Pattern:
    """Pos 07 (Bars 29-32) — Chorus Part 2: Bm7 | E7 | Amaj7 -> Dmaj7 | G#m7b5 -> C#7"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=False, energy=2)
    fill_drum_turnaround(p, start_row=56, intense=False)

    prog = [
        (0, 16, "Bm7", None),
        (16, 16, "E7", "G#2"),
        (32, 8, "Amaj7", None), (40, 8, "Dmaj7", None),
        (48, 8, "G#m7b5", None), (56, 8, "C#7", "F-2"),
    ]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'chorus_drive', I_BASS, vol=62, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=44)
        place_pad_chord(p, r0, ln, chd, vol=38)

    chorus_b = [
        # Bar 29 (Bm7): Resolves C#6 -> B5 -> F#5 -> D5
        (0, 6, "B-5", "accent"), (6, 2, "A-5", "norm"), (8, 4, "F#5", "norm"), (12, 4, "D-5", "norm"),
        # Bar 30 (E7): Joyful syncopated climb
        (16, 4, "E-5", "norm"), (20, 2, "F#5", "norm"), (22, 4, "G#5", "slide"), (26, 2, "A-5", "norm"), (28, 4, "B-5", "accent"),
        # Bar 31 (Amaj7 -> Dmaj7): Sunlit A Major warmth
        (32, 4, "A-5", "accent"), (36, 2, "G#5", "norm"), (38, 2, "E-5", "norm"),
        (40, 4, "F#5", "slide"), (44, 4, "A-5", "norm"),
        # Bar 32 (G#m7b5 -> C#7): Pull back to F#m / Dmaj7!
        (48, 4, "G#5", "norm"), (52, 4, "F#5", "norm"),
        (56, 4, "F-5", "accent"), (60, 4, "G#5", "slide"),
    ]
    counter_b = [
        (0, 6, "D-5", "norm"), (8, 4, "B-4", "soft"), (12, 4, "A-4", "soft"),
        (16, 4, "B-4", "soft"), (22, 4, "D-5", "norm"), (28, 4, "E-5", "norm"),
        (32, 4, "C#5", "norm"), (36, 4, "E-5", "soft"), (40, 4, "D-5", "norm"), (44, 4, "F#5", "norm"),
        (48, 4, "D-5", "norm"), (52, 4, "B-4", "norm"), (56, 4, "C#5", "norm"), (60, 4, "F-5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, chorus_b, base_vol=60, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, counter_b, base_vol=48, pan=184)
    for b_r, notes in [(0, ["D-5", "F#5", "A-5", "D-6"]), (16, ["E-5", "G#5", "B-5", "D-6"]), (32, ["E-5", "A-5", "C#6", "A-5"]), (48, ["D-5", "G#5", "B-5", "F-5"])]:
        for j, nt in enumerate(notes):
            p.set(b_r + j * 2, CH_BELL, nt, I_BELL, 44 - j * 3)
    return p


def make_pat08_chorus_b2a() -> Pattern:
    """Pos 08 (Bars 33-36) — Chorus High-Octane Variation with 2-Octave Sweeping Chip Arps!"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=3)

    prog = [(0, 16, "Dmaj7", None), (16, 16, "E/D", None), (32, 16, "C#m7", None), (48, 8, "F#m7", "G#1"), (56, 8, "A", None)]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'chorus_drive', I_BASS, vol=63, walk_end=wlk)
        # Switch Ch 6 to dazzling 16th-note 2-octave sweeping arpeggios!
        fill_chip_arp_bar(p, r0, ln, chd, mode="sweep", vol=44)
        place_brass_stabs(p, r0, chd, steps=(0, 6, 12) if ln == 16 else (0, 6), vol=42)

    mel_var = [
        (0, 4, "A-5", "accent"), (4, 2, "B-5", "norm"), (6, 4, "C#6", "slide"), (10, 2, "B-5", "norm"), (12, 4, "A-5", "norm"),
        (16, 4, "G#5", "accent"), (20, 2, "A-5", "norm"), (22, 4, "B-5", "slide"), (26, 2, "G#5", "norm"), (28, 4, "E-5", "norm"),
        (32, 4, "G#5", "accent"), (36, 2, "A-5", "norm"), (38, 2, "G#5", "norm"), (40, 4, "F#5", "norm"), (44, 4, "E-5", "norm"),
        (48, 4, "F#5", "accent"), (52, 2, "G#5", "norm"), (54, 2, "A-5", "norm"), (56, 6, "C#6", "slide"), (62, 2, "B-5", "grace"),
    ]
    harm_var = [
        (0, 4, "F#5", "norm"), (4, 2, "G#5", "norm"), (6, 4, "A-5", "slide"), (10, 2, "G#5", "norm"), (12, 4, "F#5", "norm"),
        (16, 4, "E-5", "norm"), (20, 2, "F#5", "norm"), (22, 4, "G#5", "slide"), (26, 2, "E-5", "norm"), (28, 4, "B-4", "norm"),
        (32, 4, "E-5", "norm"), (36, 2, "F#5", "norm"), (38, 2, "E-5", "norm"), (40, 4, "C#5", "norm"), (44, 4, "B-4", "norm"),
        (48, 4, "C#5", "norm"), (52, 2, "E-5", "norm"), (54, 2, "F#5", "norm"), (56, 6, "A-5", "slide"), (62, 2, "G#5", "grace"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, mel_var, base_vol=60, pan=76)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, harm_var, base_vol=51, pan=180)
    return p


def make_pat09_chorus_b2b() -> Pattern:
    """Pos 09 (Bars 37-40) — Dramatic Chorus Resolution into Breakdown: Bm7 | C#7 | F#m -> Dmaj7 | G#m7b5 -> C#7"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 3, clap=True, crash_bar0=False, energy=2)
    # Bar 40 tapers drums cleanly with a crisp snare/rim decrescendo into the intimate Section C Breakdown!
    for st, v in [(0, 58), (4, 52), (8, 46)]:
        p.set(48 + st, CH_KICK, "C-4", I_KICK, v)
    p.set(52, CH_SNARE, "C-4", I_SNARE, 54)
    p.set(58, CH_SNARE, "C-4", I_RIM, 44)
    p.set(60, CH_SNARE, "C-4", I_RIM, 38)
    p.set(62, CH_SNARE, "C-4", I_RIM, 30)
    for st in range(0, 16, 2):
        p.set(48 + st, CH_HAT, "C-4", I_HATC, max(20, 44 - st * 2))

    prog = [
        (0, 16, "Bm7", None),
        (16, 16, "C#7", "F-2"),
        (32, 8, "F#m", None), (40, 8, "Dmaj7", None),
        (48, 8, "G#m7b5", None), (56, 8, "C#7", None),
    ]
    for r0, ln, chd, wlk in prog:
        if r0 < 48:
            fill_bass_styled(p, r0, ln, chd, 'chorus_drive', I_BASS, vol=61, walk_end=wlk)
            fill_chip_arp_bar(p, r0, ln, chd, mode="sweep", vol=42)
        else:
            # Sustained decrescendo bass & soft 0xy shimmer in Bar 40
            p.set(r0, CH_BASS, CHORDS[chd][0], I_BASS, 50 if r0 == 48 else 44)
            p.set(r0 + 6, CH_BASS, vol=("raw", 0x62))
            fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=34)
        place_pad_chord(p, r0, ln, chd, vol=36)

    mel_end = [
        (0, 4, "A-5", "accent"), (4, 2, "G#5", "norm"), (6, 4, "F#5", "norm"), (10, 2, "E-5", "norm"), (12, 4, "D-5", "norm"),
        (16, 6, "F-5", "accent"), (22, 2, "G#5", "norm"), (24, 4, "C#6", "slide"), (28, 4, "B-5", "norm"),
        (32, 6, "A-5", "norm"), (38, 2, "G#5", "norm"), (40, 6, "F#5", "norm"), (46, 2, "E-5", "soft"),
        (48, 6, "D-5", "soft"), (54, 2, "B-4", "soft"), (56, 7, "F-5", "soft"),
    ]
    harm_end = [
        (0, 4, "F#5", "norm"), (4, 2, "E-5", "norm"), (6, 4, "D-5", "norm"), (10, 2, "C#5", "norm"), (12, 4, "B-4", "norm"),
        (16, 6, "C#5", "norm"), (22, 2, "F-5", "norm"), (24, 4, "G#5", "slide"), (28, 4, "F-5", "norm"),
        (32, 6, "F#5", "soft"), (40, 6, "D-5", "soft"), (48, 6, "B-4", "soft"), (56, 4, "C#5", "soft"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, mel_end, base_vol=58, pan=84)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, harm_end, base_vol=47, pan=172)
    p.set(60, CH_LEAD2, "off")
    return p


def build_patterns_00_to_09() -> list:
    return [
        make_pat00_intro_a(),
        make_pat01_intro_b(),
        make_pat02_sec_a1a(),
        make_pat03_sec_a1b(),
        make_pat04_sec_a2a(),
        make_pat05_sec_a2b(),
        make_pat06_chorus_b1a(),
        make_pat07_chorus_b1b(),
        make_pat08_chorus_b2a(),
        make_pat09_chorus_b2b(),
    ]
