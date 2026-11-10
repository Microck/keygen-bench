"""
Patterns 10..19 of 'CYBERNETIC FUGUE // KEYGEN'
  Pos 10..11: Section C1 - Neo-Baroque Sanctuary Breakdown & Acid Pulse Awakening
  Pos 12..13: Section C2 - Virtuoso Stereo Shred Duel & Mega Build
  Pos 14..17: Section D  - Grand Climax Reprise (Hook + Descant + Climax Chorus)
  Pos 18..19: Coda & Seamless Loop Turnaround -> resolves into Pos 02 (loop_start = 2)
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


def make_pat10_breakdown_canon() -> Pattern:
    """
    Pos 10 (Bars 41-44) — 'Ring0 Sanctuary':
    Intimate dynamic drop! Kick & heavy bass drop out in Bars 41-42;
    2-voice Neo-Baroque Canon between CrystalDX Bell (Ch 7) & SyncShred Lead (Ch 5)
    over line-cliche harmony: F#m | F#m/E | Dmaj7 | C#7sus4 -> C#7.
    """
    p = Pattern(64, 12)
    # Ensure Lead 1 & Chip from Pos 09 release cleanly at row 0
    p.set(0, CH_LEAD1, "off")
    p.set(0, CH_CHIP, "off")
    p.set(0, CH_BASS, "off")

    prog = [(0, 16, "F#m"), (16, 16, "F#m/E"), (32, 16, "Dmaj7"), (48, 8, "C#7sus4"), (56, 8, "C#7")]
    for r0, ln, chd in prog:
        place_pad_chord(p, r0, ln, chd, vol=31)

    # Sparse crystalline percussion: soft rim & delicate 8th hats
    for b in range(4):
        r0 = b * 16
        for st in range(0, 16, 2):
            p.set(r0 + st, CH_HAT, "C-4", I_HATC, 24 if st % 4 == 0 else 16)
        p.set(r0 + 12, CH_SNARE, "C-4", I_RIM, 28)
        if b >= 2:
            p.set(r0 + 6, CH_SNARE, "C-4", I_RIM, 22)

    # Gentle AcidSync bass enters in Bar 43 (row 32) with warm pulsing eighths
    for r0, ln, chd in [(32, 16, "Dmaj7"), (48, 8, "C#7sus4"), (56, 8, "C#7")]:
        root = CHORDS[chd][0]
        for st in range(0, ln, 4):
            p.set(r0 + st, CH_BASS, root, I_ACID, 44)
            p.set(r0 + st + 2, CH_BASS, tr(root, 12), I_ACID, 36, 14, 0xC4)

    # Baroque Canon Voice 1: CrystalDX Bell (states theme in Bar 41, weaves 16th counterpoint!)
    bell_events = [
        # Bar 41: Subject statement
        (0, "F#5", 50), (2, "G#5", 42), (4, "A-5", 52), (6, "F#5", 40),
        (8, "C#6", 54), (12, "B-5", 46), (14, "A-5", 42),
        # Bar 42 (F#m/E): Flowing counterpoint while Lead 2 answers!
        (16, "G#5", 48), (18, "A-5", 40), (20, "C#6", 50), (22, "A-5", 40),
        (24, "F#5", 48), (26, "E-5", 40), (28, "A-5", 46), (30, "G#5", 40),
        # Bar 43 (Dmaj7): Sequential subject
        (32, "F#5", 50), (34, "A-5", 42), (36, "D-6", 54), (38, "C#6", 44),
        (40, "B-5", 48), (42, "A-5", 42), (44, "F#5", 46), (46, "E-5", 40),
        # Bar 44 (C#7sus4 -> C#7): Harmonic minor resolution ornament
        (48, "F#5", 50), (50, "G#5", 44), (52, "B-5", 48), (54, "F#5", 42),
        (56, "F-5", 52), (58, "G#5", 46), (60, "C#6", 54), (62, "B-5", 44),
    ]
    for r, nt, v in bell_events:
        p.set(r, CH_BELL, nt, I_BELL, v)

    # Baroque Canon Voice 2: SyncShred Lead (enters 8 rows later in imitation!)
    canon_lead2 = [
        (8, 2, "F#4", "soft"), (10, 2, "G#4", "soft"), (12, 2, "A-4", "norm"), (14, 2, "F#4", "soft"),
        (16, 4, "C#5", "slide"), (20, 2, "B-4", "norm"), (22, 2, "A-4", "soft"),
        (24, 6, "C#5", "norm"), (30, 2, "B-4", "soft"),
        (32, 4, "A-4", "norm"), (36, 4, "F#5", "slide"),
        (40, 4, "E-5", "norm"), (44, 4, "D-5", "norm"),
        (48, 6, "C#5", "norm"), (54, 2, "B-4", "soft"),
        (56, 6, "F-5", "slide"), (62, 2, "G#5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, canon_lead2, base_vol=44, pan=100)
    return p


def make_pat11_acid_awakening() -> Pattern:
    """
    Pos 11 (Bars 45-48) — 'Acid Pulse Awakening':
    Hypnotic 16th-note AcidSync Bass + heartbeat kick + 3-part rising harmonic sequence
    igniting into the Virtuoso Stereo Shred Duel!
    """
    p = Pattern(64, 12)
    prog = [(0, 16, "Bm7"), (16, 16, "E7"), (32, 8, "Amaj7"), (40, 8, "Dmaj7"), (48, 8, "G#dim7"), (56, 8, "C#7")]
    for r0, ln, chd in prog:
        place_pad_chord(p, r0, ln, chd, vol=34, include_ch11=(r0 < 48))
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=36 if r0 < 32 else 42)

    # Squelchy syncopated 16th AcidSync Bass line!
    for r0, ln, chd in prog:
        root = CHORDS[chd][0]
        r_hi = tr(root, 12)
        fifth = tr(root, 6 if ("dim" in chd or "b5" in chd) else 7)
        seq = [root, r_hi, root, fifth, root, r_hi, tr(root, 10 if "7" in chd else 12), fifth]
        for st in range(ln):
            nt = seq[st % 8]
            vel = 55 if st % 4 == 0 else (48 if st % 2 == 1 else 42)
            if st % 4 == 3:
                p.set(r0 + st, CH_BASS, nt, I_ACID, vel, 14, 0xC3)
            else:
                p.set(r0 + st, CH_BASS, nt, I_ACID, vel)

    # Heartbeat kick in Bars 45-47 -> Full turnaround fill + CyberRiser in Bar 48!
    for b in range(3):
        r0 = b * 16
        for st in (0, 6, 8, 14):
            p.set(r0 + st, CH_KICK, "C-4", I_KICK, 54 + b * 4)
        p.set(r0 + 12, CH_SNARE, "C-4", I_SNARE if b == 2 else I_RIM, 48 + b * 5)
        for st in range(16):
            p.set(r0 + st, CH_HAT, "C-4", I_HATO if st in (6, 14) else I_HATC, 34 + b * 4)
    fill_drum_turnaround(p, start_row=48, intense=True)
    p.set(48, CH_PAD4, "C#4", I_RISER, 58, 8, 148)

    # HeroPWM Lead re-enters in rising 3-part dialogue with SyncShred!
    lead1 = [
        (0, 6, "D-5", "norm"), (6, 2, "E-5", "norm"), (8, 6, "F#5", "slide"), (14, 2, "D-5", "norm"),
        (16, 6, "E-5", "norm"), (22, 2, "F#5", "norm"), (24, 6, "G#5", "slide"), (30, 2, "E-5", "norm"),
        (32, 4, "A-5", "accent"), (36, 4, "E-5", "norm"), (40, 4, "F#5", "accent"), (44, 4, "A-5", "slide"),
        (48, 2, "G#5", "accent"), (50, 2, "B-5", "norm"), (52, 2, "D-6", "accent"), (54, 2, "B-5", "norm"),
        (56, 4, "C#6", "accent"), (60, 4, "F-5", "slide"),
    ]
    lead2 = [
        (0, 6, "B-4", "soft"), (8, 6, "D-5", "norm"),
        (16, 6, "B-4", "soft"), (24, 6, "D-5", "norm"),
        (32, 4, "C#5", "norm"), (36, 4, "A-4", "soft"), (40, 4, "D-5", "norm"), (44, 4, "F#5", "slide"),
        (48, 2, "F-5", "norm"), (50, 2, "G#5", "norm"), (52, 2, "B-5", "accent"), (54, 2, "G#5", "norm"),
        (56, 4, "G#5", "accent"), (60, 4, "C#5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, lead1, base_vol=56, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, lead2, base_vol=48, pan=176)
    return p


def make_pat12_shred_duel_a() -> Pattern:
    """
    Pos 12 (Bars 49-52) — 'Virtuoso Stereo Shred Duel' Part 1!
    Hard-Left HeroPWM (pan=76) & Hard-Right SyncShred (pan=180) trade blazing
    1-bar neo-classical 16th-note solos over full driving drums & RazorFM Bass!
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=2)

    prog = [(0, 16, "F#m", None), (16, 16, "Bm7", None), (32, 8, "E7", None), (40, 8, "Amaj7", None), (48, 8, "Dmaj7", None), (56, 8, "C#7", "F-2")]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'baroque_pedal', I_BASS, vol=62, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=42)
        place_brass_stabs(p, r0, chd, steps=(0, 8), vol=40)

    p.set(0, CH_LEAD2, "off")             # Silence Ch 5 cleanly during Ch 4 Left solo!
    p.set(0, CH_LEAD1, eff=8, param=28)
    p.set(16, CH_LEAD2, eff=8, param=228)

    # Bar 49 (rows 0..15): Ch 4 Left Bach/Malmsteen pedal-point shred on F#m!
    bar49_l1 = ["F#5", "A-4", "G#5", "A-4", "A-5", "A-4", "G#5", "A-4", "F#5", "C#5", "E-5", "C#5", "D-5", "C#5", "B-4", "A-4"]
    for i, nt in enumerate(bar49_l1):
        p.set(i, CH_LEAD1, nt, I_LEAD1, 60 if i % 2 == 0 else 50, 8, 28)
    p.set(16, CH_LEAD1, "B-4", I_LEAD1, 58, 4, 0x64)  # Rings out on downbeat of Bar 50 while Right answers!
    p.set(20, CH_LEAD1, "off")

    # Bar 50 (rows 16..31): Ch 5 Right answers with sweeping Bm7 arpeggio & scalar run!
    bar50_l2 = ["B-4", "D-5", "F#5", "A-5", "B-5", "A-5", "F#5", "D-5", "E-5", "F#5", "G#5", "A-5", "B-5", "A-5", "G#5", "F#5"]
    for i, nt in enumerate(bar50_l2):
        p.set(16 + i, CH_LEAD2, nt, I_LEAD2, 60 if i % 2 == 0 else 52, 8, 228)
    p.set(32, CH_LEAD2, "G#5", I_LEAD2, 58, 4, 0x64)
    p.set(36, CH_LEAD2, "off")

    # Bar 51 (rows 32..47): Ch 4 Left rapid sequence over E7 -> Amaj7!
    bar51_l1 = ["E-5", "G#5", "B-5", "D-6", "C#6", "B-5", "A-5", "G#5", "A-5", "E-5", "C#5", "E-5", "A-5", "B-5", "C#6", "A-5"]
    for i, nt in enumerate(bar51_l1):
        p.set(32 + i, CH_LEAD1, nt, I_LEAD1, 61 if i % 2 == 0 else 52, 8, 28)
    p.set(48, CH_LEAD1, "F#5", I_LEAD1, 58, 4, 0x64)
    p.set(52, CH_LEAD1, "off")

    # Bar 52 (rows 48..63): Ch 5 Right blazing Dmaj7 -> F-dim7 (C#7b9) sweep!
    bar52_l2 = ["D-5", "F#5", "A-5", "C#6", "B-5", "A-5", "G#5", "F#5", "F-5", "G#5", "B-5", "D-6", "C#6", "B-5", "G#5", "F-5"]
    for i, nt in enumerate(bar52_l2):
        p.set(48 + i, CH_LEAD2, nt, I_LEAD2, 62 if i % 2 == 0 else 54, 8, 228)
    return p


def make_pat13_shred_duel_b() -> Pattern:
    """
    Pos 13 (Bars 53-56) — 'Virtuoso Shred Duel' Part 2 -> Mega Build!
    Both leads lock together in synchronized parallel 3rds for 2 bars, then ignite
    a thrilling harmonic-minor climb + CyberRiser + 32nd-note snare/tom fill into Climax!
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 3, clap=True, crash_bar0=False, energy=3)
    fill_drum_turnaround(p, start_row=48, intense=True)
    p.set(48, CH_PAD4, "C#4", I_RISER, 60, 8, 148)

    prog = [
        (0, 16, "F#m", None),
        (16, 16, "Dmaj7", None),
        (32, 8, "Bm7", None), (40, 8, "G#dim7", None),
        (48, 8, "C#7sus4", None), (56, 8, "C#7b9", None),
    ]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'baroque_pedal', I_BASS, vol=63, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="sweep" if r0 < 32 else "0xy", vol=44)
        place_pad_chord(p, r0, ln, chd, vol=36, include_ch11=(r0 < 48))

    p.set(0, CH_LEAD1, eff=8, param=92)
    p.set(0, CH_LEAD2, eff=8, param=164)

    # Bars 53-54 (rows 0..31): Synchronized Twin-Lead 16th Baroque Harmony Run!
    run_l1 = [
        # Bar 53 (F#m)
        "F#5", "G#5", "A-5", "F#5", "G#5", "A-5", "B-5", "G#5", "A-5", "B-5", "C#6", "A-5", "B-5", "A-5", "G#5", "F#5",
        # Bar 54 (Dmaj7)
        "F#5", "E-5", "D-5", "F#5", "A-5", "F#5", "A-5", "C#6", "D-6", "C#6", "B-5", "A-5", "G#5", "A-5", "B-5", "C#6",
    ]
    run_l2 = [
        # Parallel diatonic 3rds below!
        "C#5", "E-5", "F#5", "C#5", "E-5", "F#5", "G#5", "E-5", "F#5", "G#5", "A-5", "F#5", "G#5", "F#5", "E-5", "C#5",
        "D-5", "C#5", "A-4", "D-5", "F#5", "D-5", "F#5", "A-5", "B-5", "A-5", "G#5", "F#5", "E-5", "F#5", "G#5", "A-5",
    ]
    for i in range(32):
        p.set(i, CH_LEAD1, run_l1[i], I_LEAD1, 60 if i % 2 == 0 else 52, 8, 60)
        p.set(i, CH_LEAD2, run_l2[i], I_LEAD2, 52 if i % 2 == 0 else 45, 8, 196)

    # Bars 55-56 (rows 32..63): Epic Heroic Climb to Dominant Climax!
    climb1 = [
        (32, 4, "B-5", "accent"), (36, 4, "A-5", "norm"),
        (40, 4, "G#5", "accent"), (44, 4, "B-5", "slide"),
        (48, 4, "C#6", "accent"), (52, 4, "B-5", "norm"),
        (56, 2, "G#5", "accent"), (58, 2, "B-5", "norm"), (60, 2, "D-6", "accent"), (62, 2, "C#6", "accent"),
    ]
    climb2 = [
        (32, 4, "F#5", "norm"), (36, 4, "F#5", "norm"),
        (40, 4, "F-5", "norm"), (44, 4, "G#5", "slide"),
        (48, 4, "F#5", "norm"), (52, 4, "G#5", "norm"),
        (56, 2, "F-5", "norm"), (58, 2, "G#5", "norm"), (60, 2, "B-5", "accent"), (62, 2, "G#5", "accent"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, climb1, base_vol=60, pan=76)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, climb2, base_vol=52, pan=180)
    return p


def make_pat14_climax_hook_a() -> Pattern:
    """
    Pos 14 (Bars 57-60) — GRAND CLIMAX REPRISE!
    Main Keygen Hook 'Neon Cipher' returns at maximum intensity + High Descant Counter-Melody!
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=3)

    prog = [(0, 16, "F#m", None), (16, 16, "Dmaj7", None), (32, 16, "E", None), (48, 8, "C#m7", "E-2"), (56, 8, "F#m", "A-2")]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'climax_funk', I_BASS, vol=63, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="sweep", vol=44)
        place_pad_chord(p, r0, ln, chd, vol=37)

    # Main Hook on Ch 4 (with extra climax grace ornaments!)
    hook = [
        (0, 2, "F#4", "accent"), (2, 4, "C#5", "slide"),
        (6, 1, "B-4", "norm"), (7, 1, "C#5", "norm"), (8, 2, "D-5", "norm"), (10, 2, "C#5", "norm"),
        (12, 2, "F#5", "accent"), (14, 2, "C#5", "norm"),
        (16, 2, "E-5", "norm"), (18, 4, "F#5", "slide"),
        (22, 2, "E-5", "norm"), (24, 4, "C#5", "norm"),
        (28, 2, "A-4", "stacc"), (30, 2, "C#5", "grace"),
        (32, 4, "E-5", "accent"), (36, 2, "F#5", "norm"), (38, 4, "G#5", "slide"),
        (42, 2, "F#5", "norm"), (44, 2, "E-5", "norm"), (46, 2, "G#5", "norm"),
        (48, 2, "A-5", "accent"), (50, 2, "G#5", "norm"), (52, 2, "F#5", "norm"), (54, 2, "E-5", "norm"),
        (56, 2, "C#5", "norm"), (58, 6, "F#5", "slide"),
    ]
    # Soaring High Descant Counter-Melody on Ch 5!
    descant = [
        (0, 6, "A-5", "norm"), (6, 2, "G#5", "norm"), (8, 4, "F#5", "norm"), (12, 4, "A-5", "slide"),
        (16, 6, "A-5", "accent"), (22, 2, "G#5", "norm"), (24, 4, "F#5", "norm"), (28, 4, "E-5", "norm"),
        (32, 4, "G#5", "accent"), (36, 2, "A-5", "norm"), (38, 4, "B-5", "slide"), (42, 2, "A-5", "norm"), (44, 4, "G#5", "norm"),
        (48, 4, "C#6", "accent"), (52, 4, "B-5", "norm"), (56, 8, "A-5", "slide"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, hook, base_vol=60, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, descant, base_vol=50, pan=176)

    for r, nt in [(0, "C#6"), (8, "A-5"), (16, "D-6"), (24, "A-5"), (32, "B-5"), (40, "G#5"), (48, "C#6"), (56, "F#5")]:
        p.set(r, CH_BELL, nt, I_BELL, 48)
    return p


def make_pat15_climax_hook_b() -> Pattern:
    """Pos 15 (Bars 61-64) — Climax Hook Part 2 pivoting into Grand Chorus Finale!"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 3, clap=True, crash_bar0=False, energy=3)
    fill_drum_turnaround(p, start_row=56, intense=False)

    prog = [
        (0, 16, "Bm7", None),
        (16, 8, "G#m7b5", None), (24, 8, "C#7", "F-2"),
        (32, 8, "F#m", "G#1"), (40, 8, "A", None),
        (48, 8, "Bm7", None), (56, 8, "E7", "G#2"),
    ]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'climax_funk', I_BASS, vol=63, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="sweep", vol=44)
        place_pad_chord(p, r0, ln, chd, vol=37)

    hook_b = [
        (0, 2, "B-4", "norm"), (2, 2, "D-5", "norm"), (4, 4, "F#5", "accent"),
        (8, 2, "A-5", "slide"), (10, 2, "G#5", "norm"), (12, 4, "F#5", "norm"),
        (16, 4, "G#5", "accent"), (20, 2, "F#5", "norm"), (22, 2, "D-5", "norm"),
        (24, 6, "F-5", "slide"), (30, 2, "G#5", "norm"),
        (32, 4, "A-5", "accent"), (36, 4, "G#5", "norm"), (40, 4, "A-5", "accent"), (44, 4, "C#6", "slide"),
        (48, 4, "B-5", "accent"), (52, 4, "A-5", "norm"), (56, 4, "G#5", "accent"), (60, 4, "B-5", "slide"),
    ]
    descant_b = [
        (0, 4, "D-5", "norm"), (4, 4, "A-5", "norm"), (8, 4, "F#5", "norm"), (12, 4, "D-5", "norm"),
        (16, 4, "B-4", "norm"), (20, 4, "D-5", "norm"), (24, 8, "C#5", "norm"),
        (32, 4, "C#5", "norm"), (36, 4, "E-5", "norm"), (40, 4, "E-5", "norm"), (44, 4, "A-5", "slide"),
        (48, 4, "F#5", "norm"), (52, 4, "F#5", "norm"), (56, 4, "E-5", "norm"), (60, 4, "G#5", "slide"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, hook_b, base_vol=60, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, descant_b, base_vol=50, pan=176)
    return p


def make_pat16_climax_chorus_a() -> Pattern:
    """Pos 16 (Bars 65-68) — Euphoric Climax Chorus Finale Part 1: Dmaj7 | E | F#m -> E/G# | Amaj7"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=3)

    prog = [(0, 16, "Dmaj7", None), (16, 16, "E", None), (32, 8, "F#m", None), (40, 8, "E/G#", None), (48, 16, "Amaj7", None)]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'climax_funk', I_BASS, vol=63, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=46)
        place_brass_stabs(p, r0, chd, steps=(0, 6, 12) if ln == 16 else (0, 6), vol=44)

    climax_a = [
        (0, 6, "A-5", "accent"), (6, 2, "B-5", "norm"), (8, 4, "C#6", "slide"), (12, 4, "A-5", "norm"),
        (16, 6, "B-5", "accent"), (22, 2, "A-5", "norm"), (24, 4, "G#5", "norm"), (28, 4, "E-5", "norm"),
        (32, 4, "F#5", "accent"), (36, 4, "A-5", "slide"), (40, 4, "G#5", "accent"), (44, 4, "B-5", "slide"),
        (48, 6, "C#6", "accent"), (54, 2, "B-5", "norm"), (56, 4, "A-5", "norm"), (60, 4, "E-5", "norm"),
    ]
    climax_a2 = [
        (0, 6, "F#5", "norm"), (6, 2, "G#5", "norm"), (8, 4, "A-5", "slide"), (12, 4, "F#5", "norm"),
        (16, 6, "G#5", "norm"), (22, 2, "F#5", "norm"), (24, 4, "E-5", "norm"), (28, 4, "B-4", "norm"),
        (32, 4, "C#5", "norm"), (36, 4, "F#5", "slide"), (40, 4, "E-5", "norm"), (44, 4, "G#5", "slide"),
        (48, 6, "A-5", "norm"), (54, 2, "G#5", "norm"), (56, 4, "E-5", "norm"), (60, 4, "C#5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, climax_a, base_vol=61, pan=76)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, climax_a2, base_vol=52, pan=188)
    for b_r, notes in [(0, ["F#5", "A-5", "C#6", "D-6"]), (16, ["G#5", "B-5", "E-5", "B-5"]), (32, ["F#5", "A-5", "G#5", "B-5"]), (48, ["E-5", "A-5", "C#6", "E-5"])]:
        for j, nt in enumerate(notes):
            p.set(b_r + j * 4 + 2, CH_BELL, nt, I_BELL, 44)
    return p


def make_pat17_climax_chorus_b() -> Pattern:
    """Pos 17 (Bars 69-72) — Climax Chorus Finale Part 2: Bm7 | C#7 | Dmaj7 -> Bm7 | C#7sus4 -> C#7"""
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=False, energy=3)
    fill_drum_turnaround(p, start_row=56, intense=False)

    prog = [
        (0, 16, "Bm7", None),
        (16, 16, "C#7", "F-2"),
        (32, 8, "Dmaj7", None), (40, 8, "Bm7", None),
        (48, 8, "C#7sus4", None), (56, 8, "C#7", "F-2"),
    ]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'climax_funk', I_BASS, vol=63, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=46)
        place_pad_chord(p, r0, ln, chd, vol=38)

    climax_b = [
        (0, 4, "D-6", "accent"), (4, 2, "C#6", "norm"), (6, 4, "B-5", "norm"), (10, 2, "A-5", "norm"), (12, 4, "F#5", "norm"),
        (16, 6, "G#5", "accent"), (22, 2, "A-5", "norm"), (24, 4, "B-5", "slide"), (28, 4, "F-5", "norm"),
        (32, 4, "A-5", "accent"), (36, 4, "F#5", "norm"), (40, 4, "B-5", "accent"), (44, 4, "A-5", "norm"),
        (48, 6, "G#5", "accent"), (54, 2, "F#5", "norm"), (56, 6, "F-5", "accent"), (62, 2, "G#5", "norm"),
    ]
    climax_b2 = [
        (0, 4, "B-5", "norm"), (4, 2, "A-5", "norm"), (6, 4, "F#5", "norm"), (10, 2, "F#5", "norm"), (12, 4, "D-5", "norm"),
        (16, 6, "F-5", "norm"), (22, 2, "F#5", "norm"), (24, 4, "G#5", "slide"), (28, 4, "C#5", "norm"),
        (32, 4, "F#5", "norm"), (36, 4, "D-5", "norm"), (40, 4, "F#5", "norm"), (44, 4, "F#5", "norm"),
        (48, 6, "C#5", "norm"), (56, 6, "C#5", "norm"), (62, 2, "F-5", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, climax_b, base_vol=61, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, climax_b2, base_vol=52, pan=176)
    return p


def make_pat18_coda_riff() -> Pattern:
    """
    Pos 18 (Bars 73-76) — High-Octane Keygen Coda Riff:
    Punchy rhythmic call-and-response over F#m | E | Dmaj7 | C#m7 -> Bm7!
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 4, clap=True, crash_bar0=True, energy=2)

    prog = [(0, 16, "F#m", None), (16, 16, "E", None), (32, 16, "Dmaj7", None), (48, 8, "C#m7", None), (56, 8, "Bm7", None)]
    for r0, ln, chd, wlk in prog:
        fill_bass_styled(p, r0, ln, chd, 'gallop', I_BASS, vol=62, walk_end=wlk)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=44)
        place_brass_stabs(p, r0, chd, steps=(0, 3, 6) if ln == 8 else (0, 3, 6, 12), vol=44)

    # Tight syncopated riff trading between Twin Leads & CrystalDX Bell!
    riff1 = [
        (0, 3, "F#5", "accent"), (3, 3, "A-5", "stacc"), (6, 4, "F#5", "norm"), (12, 2, "E-5", "norm"), (14, 2, "F#5", "norm"),
        (16, 3, "G#5", "accent"), (19, 3, "B-5", "stacc"), (22, 4, "G#5", "norm"), (28, 2, "F#5", "norm"), (30, 2, "E-5", "norm"),
        (32, 3, "F#5", "accent"), (35, 3, "A-5", "stacc"), (38, 4, "F#5", "norm"), (44, 2, "E-5", "norm"), (46, 2, "C#5", "norm"),
        (48, 4, "E-5", "accent"), (52, 4, "C#5", "norm"), (56, 4, "D-5", "accent"), (60, 4, "B-4", "norm"),
    ]
    riff2 = [
        (0, 3, "C#5", "norm"), (3, 3, "F#5", "stacc"), (6, 4, "C#5", "norm"),
        (16, 3, "E-5", "norm"), (19, 3, "G#5", "stacc"), (22, 4, "E-5", "norm"),
        (32, 3, "D-5", "norm"), (35, 3, "F#5", "stacc"), (38, 4, "D-5", "norm"),
        (48, 4, "G#4", "norm"), (52, 4, "A-4", "norm"), (56, 4, "B-4", "norm"), (60, 4, "F#4", "norm"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, riff1, base_vol=58, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, riff2, base_vol=50, pan=176)

    for r, nt in [(8, "C#6"), (10, "A-5"), (24, "B-5"), (26, "G#5"), (40, "A-5"), (42, "F#5"), (54, "G#5"), (62, "F#5")]:
        p.set(r, CH_BELL, nt, I_BELL, 48)
    return p


def make_pat19_loop_turnaround() -> Pattern:
    """
    Pos 19 (Bars 77-80) — SEAMLESS LOOP TURNAROUND INTO POS 02 (loop_start = 2)!
    Harmony: F#m -> E/G# | A -> Dmaj7 | Bm7 -> G#m7b5 | C#7 -> C#7b9 + Riser + Stereo Tom/Snare Fill!
    Engineered so Row 63 resolves with 100% harmonic, rhythmic, and channel-state perfection
    directly into Pos 02, Row 0 (F#m Main Keygen Hook Drop)!
    """
    p = Pattern(64, 12)
    fill_drums_driving(p, 0, 3, clap=True, crash_bar0=False, energy=2)
    fill_drum_turnaround(p, start_row=48, intense=True)
    # 1-bar CyberRiser on Ch 11 in Bar 80 (rows 48..63) — identical launch energy to Pos 01!
    p.set(48, CH_PAD4, "C#4", I_RISER, 58, 8, 148)

    prog = [
        (0, 8, "F#m", "G#1"), (8, 8, "E/G#", None),
        (16, 8, "A", None), (24, 8, "Dmaj7", None),
        (32, 8, "Bm7", None), (40, 8, "G#m7b5", None),
        (48, 8, "C#7", None), (56, 8, "C#7b9", None),
    ]
    for r0, ln, chd, wlk in prog:
        if r0 < 48:
            fill_bass_styled(p, r0, ln, chd, 'gallop', I_BASS, vol=62, walk_end=wlk)
        else:
            # Driving 16th octave dominant C# pedal building tension into F#m!
            root = CHORDS[chd][0]
            for st in range(ln):
                nt = tr(root, 12) if st % 2 == 1 else root
                p.set(r0 + st, CH_BASS, nt, I_BASS, 58 if st % 2 == 0 else 50)
        fill_chip_arp_bar(p, r0, ln, chd, mode="0xy", vol=44 if r0 < 48 else 46)
        place_pad_chord(p, r0, ln, chd, vol=36, include_ch11=(r0 < 48))

    # Rising Turnaround Fanfare leading directly to Pos 02 Row 0 ('F#4' on Lead 1)!
    turn1 = [
        (0, 4, "F#4", "norm"), (4, 4, "A-4", "norm"), (8, 4, "B-4", "norm"), (12, 4, "G#4", "norm"),
        (16, 4, "A-4", "accent"), (20, 4, "C#5", "norm"), (24, 4, "D-5", "accent"), (28, 4, "F#5", "slide"),
        (32, 4, "D-5", "norm"), (36, 4, "B-4", "norm"), (40, 4, "D-5", "norm"), (44, 4, "F-5", "slide"),
        # Bar 80 (C#7 -> C#7b9): Dominant tension resolving down/up cleanly into F#4 / C#5 at Pos 02!
        (48, 2, "C#5", "norm"), (50, 2, "D-5", "norm"), (52, 2, "F-5", "norm"), (54, 2, "G#5", "norm"),
        (56, 2, "B-5", "accent"), (58, 2, "G#5", "norm"), (60, 2, "F-5", "norm"), (62, 2, "G#5", "accent"),
    ]
    turn2 = [
        (0, 4, "A-4", "soft"), (4, 4, "C#5", "soft"), (8, 4, "E-5", "soft"), (12, 4, "B-4", "soft"),
        (16, 4, "C#5", "norm"), (20, 4, "E-5", "norm"), (24, 4, "F#5", "norm"), (28, 4, "A-5", "slide"),
        (32, 4, "F#5", "norm"), (36, 4, "D-5", "norm"), (40, 4, "F#5", "norm"), (44, 4, "G#5", "slide"),
        (48, 2, "F-5", "norm"), (50, 2, "F#5", "norm"), (52, 2, "G#5", "norm"), (54, 2, "B-5", "norm"),
        (56, 2, "D-6", "accent"), (58, 2, "B-5", "norm"), (60, 2, "G#5", "norm"), (62, 1, "B-5", "stacc"),
    ]
    write_lead_phrase(p, CH_LEAD1, I_LEAD1, turn1, base_vol=58, pan=80)
    write_lead_phrase(p, CH_LEAD2, I_LEAD2, turn2, base_vol=50, pan=176)
    # Explicit clean note-off on Lead 2 at Row 63 so Ch 5 is 100% silent entering Pos 02!
    p.set(63, CH_LEAD2, "off")
    return p


def build_patterns_10_to_19() -> list:
    return [
        make_pat10_breakdown_canon(),
        make_pat11_acid_awakening(),
        make_pat12_shred_duel_a(),
        make_pat13_shred_duel_b(),
        make_pat14_climax_hook_a(),
        make_pat15_climax_hook_b(),
        make_pat16_climax_chorus_a(),
        make_pat17_climax_chorus_b(),
        make_pat18_coda_riff(),
        make_pat19_loop_turnaround(),
    ]
