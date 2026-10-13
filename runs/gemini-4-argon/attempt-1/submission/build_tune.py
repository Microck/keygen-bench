"""
Build the complete 12-channel, 12-pattern (48-bar) original keygen XM module
and render it to WAV for analysis.
"""
from __future__ import annotations
import base64
import sys
import time
import numpy as np

sys.path.insert(0, "/opt/keygen")
sys.path.insert(0, "/workspace")
from bridge import exchange
from synth_instruments import build_all_instruments


def ft2_call(tool_name: str, **kwargs) -> dict:
    res = exchange({"op": "call", "name": tool_name, "arguments": kwargs})
    if res.get("isError"):
        raise RuntimeError(f"FT2 error in {tool_name}({kwargs}): {res}")
    return res


def v_set(vol_0_64: int) -> int:
    """Convert linear tracker volume 0..64 to XM volume column byte 0x10..0x50."""
    return 0x10 + max(0, min(64, int(round(vol_0_64))))


# Semitone helper for computing 0xy arpeggio nibbles and transpositions
NOTE_NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]


def midi_to_xm(midi_note: int) -> str:
    """Convert MIDI-style note (where C-4 = 60 -> FT2 'C-4') to FT2 note string."""
    octv = (midi_note // 12) - 1
    semi = midi_note % 12
    return f"{NOTE_NAMES[semi]}{octv}"


def xm_to_midi(note_str: str) -> int:
    """Convert FT2 note string like 'D-4' or 'C#5' to integer (C-4 = 60)."""
    s = note_str.strip()
    if len(s) == 3 and s[1] in ("-", "#"):
        prefix = s[:2]
        octv = int(s[2])
    else:
        raise ValueError(f"Bad note string: {note_str}")
    semi = NOTE_NAMES.index(prefix)
    return (octv + 1) * 12 + semi


class PatternGrid:
    """In-memory representation of a 64-row, 12-channel pattern before flushing to FT2."""
    def __init__(self, pat_idx: int, rows: int = 64, channels: int = 12):
        self.pat_idx = pat_idx
        self.rows = rows
        self.channels = channels
        self.cells: dict[tuple[int, int], dict] = {}

    def set(
        self,
        row: int,
        ch: int,
        note: str | int | None = None,
        inst: int | None = None,
        vol: int | None = None,
        fx: int | None = None,
        param: int | None = None,
    ) -> None:
        if not (0 <= row < self.rows and 0 <= ch < self.channels):
            return
        cell = self.cells.get((row, ch), {})
        if note is not None:
            cell["note"] = note
        if inst is not None:
            cell["instrument"] = inst
        if vol is not None:
            cell["volume"] = vol
        if fx is not None:
            cell["effect"] = fx
        if param is not None:
            cell["effect_param"] = param
        self.cells[(row, ch)] = cell

    def flush(self) -> int:
        ft2_call("pattern_clear", pattern=self.pat_idx)
        ft2_call("pattern_set_length", pattern=self.pat_idx, rows=self.rows)
        count = 0
        for (row, ch), cell in sorted(self.cells.items()):
            ft2_call("pattern_set_cell", pattern=self.pat_idx, row=row, channel=ch, **cell)
            count += 1
        return count


# ==============================================================================
# Reusable Groove, Bass, Arp, Pad & Echo Builders
# ==============================================================================

def add_drums_standard(
    p: PatternGrid,
    crash_rows: list[int] | None = None,
    fill_type: str = "tom_desc",
    half_time: bool = False,
) -> None:
    """
    Populate Ch 0 (Kick), Ch 1 (Snare/Tom), Ch 2 (Closed/Open Hats & Crash).
    """
    crash_set = set(crash_rows or [])
    for r in range(64):
        in_fill = r >= 56 and fill_type != "none"

        # --- CH 0: KICK (Inst 11) ---
        if half_time:
            # Atmospheric half-time groove for Baroque breakdown (Pattern 6)
            if r % 16 in (0, 6, 10):
                vol = 58 if (r % 16 == 0) else 48
                p.set(r, 0, note="C-4", inst=11, vol=v_set(vol))
        else:
            if not in_fill:
                # Driving keygen 4-on-the-floor + syncopated ghost kicks on 16th pickups
                if r % 4 == 0:
                    p.set(r, 0, note="C-4", inst=11, vol=v_set(64))
                elif r % 16 in (11, 14):
                    p.set(r, 0, note="C-4", inst=11, vol=v_set(46))
            else:
                if r in (56, 60):
                    p.set(r, 0, note="C-4", inst=11, vol=v_set(62))

        # --- CH 1: SNARE (Inst 12) & SYNTH TOM (Inst 13) ---
        if not in_fill:
            if half_time:
                if r % 16 == 8:
                    p.set(r, 1, note="C-4", inst=12, vol=v_set(58))
                elif r % 16 == 15:
                    p.set(r, 1, note="C-4", inst=12, vol=v_set(34))
            else:
                if r % 8 == 4:
                    p.set(r, 1, note="C-4", inst=12, vol=v_set(63))
                elif r % 16 in (7, 15):
                    # Subtle ghost snare
                    p.set(r, 1, note="C-4", inst=12, vol=v_set(30))
        else:
            # 2-beat turnaround fill (rows 56..63)
            if fill_type == "tom_desc":
                fill_map = {
                    56: ("C-4", 12, 58),
                    57: ("C-4", 12, 44),
                    58: ("G-4", 13, 60),
                    59: ("F-4", 13, 56),
                    60: ("D-4", 13, 62),
                    61: ("C-4", 13, 58),
                    62: ("A-3", 13, 64),
                    63: ("C-4", 12, 64),
                }
                if r in fill_map:
                    nt, ins, vl = fill_map[r]
                    pan_val = 48 + (r - 56) * 24
                    p.set(r, 1, note=nt, inst=ins, vol=v_set(vl), fx=8, param=min(224, pan_val))
            elif fill_type == "snare_roll":
                vols = [44, 48, 52, 55, 58, 60, 62, 64]
                idx = r - 56
                # Classic tracker E93 retrigger on the climax of the snare roll (rows 62-63)!
                if r in (62, 63):
                    p.set(r, 1, note="C-4", inst=12, vol=v_set(vols[idx]), fx=14, param=0x93)
                else:
                    p.set(r, 1, note="C-4", inst=12, vol=v_set(vols[idx]))
            elif fill_type == "loop_pickup":
                # Clean, tight pickup in rows 56..63 that resolves cleanly into Pattern 0 Row 0
                fill_map = {
                    56: ("F-4", 13, 56),
                    58: ("D-4", 13, 58),
                    60: ("C-4", 12, 62),
                    62: ("A-3", 13, 60),
                    63: ("C-4", 12, 54),
                }
                if r in fill_map:
                    nt, ins, vl = fill_map[r]
                    p.set(r, 1, note=nt, inst=ins, vol=v_set(vl))

        # --- CH 2: HI-HATS (Inst 14 Closed, Inst 15 Open) & CRASH (Inst 16) ---
        if r in crash_set:
            p.set(r, 2, note="C-4", inst=16, vol=v_set(58))
        elif half_time:
            if r % 2 == 0:
                p.set(r, 2, note="C-4", inst=14, vol=v_set(42 if r % 4 == 0 else 32))
            elif r % 8 == 6:
                p.set(r, 2, note="C-4", inst=15, vol=v_set(44))
        else:
            if r % 4 == 2:
                # Off-beat open hi-hat!
                p.set(r, 2, note="C-4", inst=15, vol=v_set(50))
            elif r % 2 == 0:
                p.set(r, 2, note="C-4", inst=14, vol=v_set(44))
            else:
                p.set(r, 2, note="C-4", inst=14, vol=v_set(32))


def add_bass_line(
    p: PatternGrid,
    bar_roots: list[tuple[str, str, str]],
    style: str = "driving",
) -> None:
    """
    Populate Ch 3 (Bass).
    bar_roots: list of 4 tuples (root_low, root_high, fifth_or_passing) for the 4 bars.
    style: 'driving' (16th octave bounce), 'anthem' (gallop + slap), 'major_groove' (FM slap + acid), 'baroque' (pedal + walk)
    """
    for bar_idx in range(4):
        base_r = bar_idx * 16
        r_lo, r_hi, r_5th = bar_roots[bar_idx]
        for step in range(16):
            r = base_r + step
            if style == "driving":
                # Classic keygen octave-bouncing 16th bass
                if step in (0, 6, 8, 12):
                    p.set(r, 3, note=r_lo, inst=5, vol=v_set(62 if step in (0, 8) else 56))
                elif step in (2, 4, 10):
                    p.set(r, 3, note=r_hi, inst=5, vol=v_set(54))
                elif step == 14:
                    p.set(r, 3, note=r_5th, inst=6, vol=v_set(58))
                else:
                    p.set(r, 3, note=r_hi if step % 2 == 1 else r_lo, inst=5, vol=v_set(42))
            elif style == "anthem":
                # High-energy gallop mixing Acid Bass (5) and FM Slap Bass (6)
                if step in (0, 3, 6, 8, 11, 12):
                    p.set(r, 3, note=r_lo, inst=5, vol=v_set(63 if step in (0, 8) else 56))
                elif step in (2, 4, 10):
                    p.set(r, 3, note=r_hi, inst=6, vol=v_set(58))
                elif step == 14:
                    p.set(r, 3, note=r_5th, inst=6, vol=v_set(60))
                else:
                    p.set(r, 3, note=r_hi, inst=5, vol=v_set(44))
            elif style == "major_groove":
                # Funky, bouncy F-major slap + acid groove
                if step in (0, 8):
                    p.set(r, 3, note=r_lo, inst=6, vol=v_set(64))
                elif step in (3, 6, 11):
                    p.set(r, 3, note=r_lo, inst=5, vol=v_set(56))
                elif step in (2, 4, 10, 12):
                    p.set(r, 3, note=r_hi, inst=6, vol=v_set(56))
                elif step in (14, 15):
                    p.set(r, 3, note=r_5th if step == 14 else r_hi, inst=5, vol=v_set(54))
                else:
                    p.set(r, 3, note=r_lo, inst=5, vol=v_set(38))
            elif style == "baroque":
                # Noble 8th-note baroque continuo bass
                if step % 4 == 0:
                    p.set(r, 3, note=r_lo, inst=5, vol=v_set(58))
                elif step % 4 == 2:
                    p.set(r, 3, note=r_hi if step < 12 else r_5th, inst=6, vol=v_set(50))
                elif step % 4 == 3:
                    # Slight volume taper before next 8th note
                    p.set(r, 3, vol=v_set(30))


def add_stereo_arps(
    p: PatternGrid,
    bar_chords: list[tuple[str, str, str, str]],
    mode: str = "full",
) -> None:
    """
    Populate Ch 4 (03:ChipSqArp with 0xy + 16th pattern arp)
    and Ch 5 (04:SIDPluck interlocking counter-arp).
    bar_chords: list of 4 4-note chord voicings (n0, n1, n2, n3) in ascending order.
    """
    for bar_idx in range(4):
        base_r = bar_idx * 16
        n0, n1, n2, n3 = bar_chords[bar_idx]
        m0, m1, m2 = xm_to_midi(n0), xm_to_midi(n1), xm_to_midi(n2)
        d1 = max(0, min(15, m1 - m0))
        d2 = max(0, min(15, m2 - m0))
        arp_param = (d1 << 4) | d2

        notes_cycle = [n0, n1, n2, n3, n2, n1, n0, n2]
        counter_cycle = [n3, n2, n1, n0, n2, n3, n1, n2]

        for step in range(16):
            r = base_r + step
            if mode == "full":
                # Ch 4: Rapid 16th-note chip arpeggio with 0xy warble on even steps
                nt = notes_cycle[step % 8]
                vol = 48 if (step % 4 == 0) else 40
                if step % 2 == 0:
                    p.set(r, 4, note=nt, inst=3, vol=v_set(vol), fx=0, param=arp_param)
                else:
                    p.set(r, 4, note=nt, inst=3, vol=v_set(vol - 4))
                # Ch 5: Interlocking SID Pluck on off-16ths & syncopated accents
                if step % 2 == 1 or step in (0, 6, 12):
                    cnt_nt = counter_cycle[step % 8]
                    c_vol = 46 if (step in (0, 6, 12)) else 38
                    p.set(r, 5, note=cnt_nt, inst=4, vol=v_set(c_vol))
            elif mode == "sparkle":
                # Lighter, airy arpeggio for breakdowns / major lift
                if step % 2 == 0:
                    nt = notes_cycle[(step // 2) % 8]
                    p.set(r, 4, note=nt, inst=3, vol=v_set(42), fx=0, param=arp_param)
                if step % 2 == 1:
                    cnt_nt = counter_cycle[(step // 2) % 8]
                    p.set(r, 5, note=cnt_nt, inst=4, vol=v_set(42))


def add_pads(
    p: PatternGrid,
    bar_dyads: list[tuple[str, str]],
    vol_base: int = 44,
) -> None:
    """
    Populate Ch 8 (Pad Lo-Mid, pan left) and Ch 9 (Pad Hi-Mid, pan right)
    with smooth fade-out on rows 14..15 of each bar so chord changes are 100% click-free.
    """
    for bar_idx in range(4):
        base_r = bar_idx * 16
        nt_lo, nt_hi = bar_dyads[bar_idx]
        p.set(base_r, 8, note=nt_lo, inst=7, vol=v_set(vol_base), fx=8, param=16)
        p.set(base_r, 9, note=nt_hi, inst=7, vol=v_set(vol_base), fx=8, param=240)
        # Gentle swell on row 4, smooth taper on rows 13, 14, 15 before next bar's chord
        p.set(base_r + 4, 8, vol=v_set(vol_base + 4))
        p.set(base_r + 4, 9, vol=v_set(vol_base + 4))
        p.set(base_r + 13, 8, vol=v_set(max(12, vol_base - 12)))
        p.set(base_r + 13, 9, vol=v_set(max(12, vol_base - 12)))
        p.set(base_r + 14, 8, vol=v_set(max(8, vol_base - 22)))
        p.set(base_r + 14, 9, vol=v_set(max(8, vol_base - 22)))
        p.set(base_r + 15, 8, vol=v_set(4))
        p.set(base_r + 15, 9, vol=v_set(4))


def write_melody_with_echo(
    p: PatternGrid,
    events: list[tuple[int, str, int, int, int | None, int | None]],
    lead_ch: int = 6,
    echo_ch: int | None = 11,
    echo_delay: int = 3,
    echo_atten: int = 24,
) -> None:
    """
    Write a list of melody events (row, note, inst, vol_0_64, fx, param) to lead_ch.
    Automatically tapers sustained lead notes 1 row before the next note or rest,
    and writes a 3-row delayed stereo echo on echo_ch!
    """
    sorted_ev = sorted(events, key=lambda x: x[0])
    for idx, (row, note, inst, vol, fx, param) in enumerate(sorted_ev):
        if note == "off":
            # Smooth fade instead of abrupt cut
            if row > 0:
                p.set(row - 1, lead_ch, vol=v_set(16))
            p.set(row, lead_ch, vol=v_set(0))
            continue

        p.set(row, lead_ch, note=note, inst=inst, vol=v_set(vol), fx=fx, param=param)

        # Add expressive vibrato on sustained notes (>= 4 rows long)
        next_row = sorted_ev[idx + 1][0] if idx + 1 < len(sorted_ev) else 64
        dur = next_row - row
        if dur >= 4 and inst in (1, 2):
            for vr in range(row + 2, min(63, next_row - 1)):
                if (vr, lead_ch) not in p.cells:
                    p.set(vr, lead_ch, fx=4, param=0x53)  # Vibrato speed 5, depth 3
            # Smooth micro-taper on the row right before the next note
            if next_row <= 63 and (next_row - 1, lead_ch) not in p.cells:
                p.set(next_row - 1, lead_ch, vol=v_set(max(24, vol - 14)))

        # Write stereo echo on echo_ch if slot is free
        if echo_ch is not None:
            er = row + echo_delay
            if er < 62 and (er, echo_ch) not in p.cells:
                evol = max(14, vol - echo_atten)
                p.set(er, echo_ch, note=note, inst=inst, vol=v_set(evol), fx=8, param=216)


# ==============================================================================
# Pattern Composition (12 Patterns = 48 Bars in D Minor / F Major)
# ==============================================================================

def build_all_patterns() -> list[PatternGrid]:
    patterns: list[PatternGrid] = []

    # Common chord & bass definitions
    # Progression A1: Dm | BbMaj7 | Gm7 | Asus4 -> A7
    roots_dm_bb_gm_a = [
        ("D-2", "D-3", "A-2"),
        ("A#1", "A#2", "F-2"),
        ("G-1", "G-2", "D-2"),
        ("A-1", "A-2", "E-2"),
    ]
    chords_dm_bb_gm_a = [
        ("D-4", "F-4", "A-4", "D-5"),
        ("A#3", "D-4", "F-4", "A-4"),
        ("G-3", "A#3", "D-4", "F-4"),
        ("A-3", "C#4", "E-4", "G-4"),
    ]
    pads_dm_bb_gm_a = [
        ("F-3", "A-4"),
        ("D-3", "A-4"),
        ("G-3", "A#4"),
        ("E-3", "C#5"),
    ]

    # --------------------------------------------------------------------------
    # PATTERN 0 (Bars 1-4): "The Razor Hook" (Also loop_start = 0 target!)
    # Harmony: Dm | BbMaj7 | Gm7 | Asus4 -> A7
    # --------------------------------------------------------------------------
    p0 = PatternGrid(0)
    add_drums_standard(p0, crash_rows=[0], fill_type="tom_desc")
    add_bass_line(p0, roots_dm_bb_gm_a, style="driving")
    add_stereo_arps(p0, chords_dm_bb_gm_a, mode="full")
    add_pads(p0, pads_dm_bb_gm_a, vol_base=42)

    # Hero Lead 1 (Ch 6) - Iconic opening keygen hook
    mel_p0 = [
        # Bar 1 (Dm): D5 - F5 - A5 -> G5 - F5 - E5 - D5
        (0, "D-5", 1, 62, None, None),
        (3, "F-5", 1, 58, None, None),
        (6, "A-5", 1, 64, 3, 0x38),
        (10, "G-5", 1, 58, None, None),
        (12, "F-5", 1, 56, None, None),
        (14, "E-5", 1, 54, None, None),
        # Bar 2 (BbMaj7): F5 -> D5 -> A4 - Bb4 - C5 - D5
        (16, "F-5", 1, 62, None, None),
        (20, "D-5", 1, 58, None, None),
        (24, "A-4", 1, 54, None, None),
        (26, "A#4", 1, 56, None, None),
        (28, "C-5", 1, 58, None, None),
        (30, "D-5", 1, 60, None, None),
        # Bar 3 (Gm7): G5 - F5 - D5 - Bb4 - G4 - Bb4 - D5 - G5
        (32, "G-5", 1, 63, None, None),
        (35, "F-5", 1, 58, None, None),
        (38, "D-5", 1, 60, None, None),
        (42, "A#4", 1, 56, None, None),
        (44, "C-5", 1, 58, None, None),
        (46, "D-5", 1, 60, None, None),
        # Bar 4 (Asus4 -> A7): E5 (sus4 resolve) -> C#5 -> A4 -> B4 -> C#5 pickup
        (48, "E-5", 1, 63, None, None),
        (52, "C#5", 1, 60, None, None),
        (56, "A-4", 1, 56, None, None),
        (60, "B-4", 1, 58, None, None),
        (62, "C#5", 1, 62, None, None),
    ]
    write_melody_with_echo(p0, mel_p0, lead_ch=6, echo_ch=11)

    # Ch 7: Sync/FM Lead 2 answers on Bar 2 & Bar 4
    p0.set(16, 7, note="A-4", inst=2, vol=v_set(50))
    p0.set(20, 7, note="F-4", inst=2, vol=v_set(48))
    p0.set(24, 7, note="D-4", inst=2, vol=v_set(42))
    p0.set(32, 7, note="A#4", inst=2, vol=v_set(50))
    p0.set(38, 7, note="G-4", inst=2, vol=v_set(48))
    p0.set(48, 7, note="A-4", inst=2, vol=v_set(52))
    p0.set(52, 7, note="G-4", inst=2, vol=v_set(50))
    p0.set(56, 7, note="E-4", inst=2, vol=v_set(46))
    p0.set(62, 7, vol=v_set(16))

    # Ch 10: Crystal Bell (Inst 8) & Brass Stab (Inst 9) accents
    for r, nt in [(0, "A-5"), (6, "D-6"), (16, "A-5"), (22, "F-5"), (32, "A#5"), (38, "G-5"), (48, "A-5"), (52, "G-5")]:
        p0.set(r, 10, note=nt, inst=8, vol=v_set(50))
    patterns.append(p0)

    # --------------------------------------------------------------------------
    # PATTERN 1 (Bars 5-8): Full Dual-Lead Answer & Lift
    # Harmony: Dm | BbMaj7 | C7 | FMaj7 -> A7
    # --------------------------------------------------------------------------
    p1 = PatternGrid(1)
    roots_p1 = [
        ("D-2", "D-3", "A-2"),
        ("A#1", "A#2", "F-2"),
        ("C-2", "C-3", "G-2"),
        ("F-1", "F-2", "A-1"),
    ]
    chords_p1 = [
        ("D-4", "F-4", "A-4", "D-5"),
        ("A#3", "D-4", "F-4", "A-4"),
        ("C-4", "E-4", "G-4", "A#4"),
        ("F-3", "A-3", "C#4", "E-4"),
    ]
    pads_p1 = [
        ("F-3", "A-4"),
        ("D-3", "A-4"),
        ("E-3", "A#4"),
        ("F-3", "C#5"),
    ]
    add_drums_standard(p1, crash_rows=[0], fill_type="snare_roll")
    add_bass_line(p1, roots_p1, style="anthem")
    add_stereo_arps(p1, chords_p1, mode="full")
    add_pads(p1, pads_p1, vol_base=44)

    mel_p1_lead1 = [
        # Bar 5 (Dm): High energetic variant D5 - F5 - A5 - Bb5 - A5 - G5 - F5
        (0, "D-5", 1, 63, None, None),
        (2, "E-5", 1, 56, None, None),
        (4, "F-5", 1, 60, None, None),
        (6, "A-5", 1, 64, 3, 0x38),
        (10, "A#5", 1, 62, None, None),
        (12, "A-5", 1, 60, None, None),
        (14, "G-5", 1, 58, None, None),
        # Bar 6 (BbMaj7): F5 - D5 - C5 - Bb4 - D5 - F5
        (16, "F-5", 1, 62, None, None),
        (20, "D-5", 1, 58, None, None),
        (24, "C-5", 1, 56, None, None),
        (26, "D-5", 1, 58, None, None),
        (28, "F-5", 1, 60, None, None),
        (30, "G-5", 1, 62, None, None),
        # Bar 7 (C7): G5 - E5 - C5 -> E5 - G5 - A5 - Bb5
        (32, "G-5", 1, 64, None, None),
        (36, "E-5", 1, 58, None, None),
        (40, "C-5", 1, 56, None, None),
        (42, "E-5", 1, 58, None, None),
        (44, "G-5", 1, 60, None, None),
        (46, "A-5", 1, 62, None, None),
        # Bar 8 (FMaj7 -> A7): A5 -> F5 -> E5 -> C#5 -> D5 -> E5
        (48, "A-5", 1, 64, None, None),
        (52, "F-5", 1, 60, None, None),
        (56, "E-5", 1, 62, None, None),
        (60, "C#5", 1, 60, None, None),
        (62, "E-5", 1, 62, None, None),
    ]
    write_melody_with_echo(p1, mel_p1_lead1, lead_ch=6, echo_ch=11)

    # Ch 7: Sync/FM Lead 2 harmonizes in 3rds/6ths!
    mel_p1_lead2 = [
        (0, "F-4", 2, 52, None, None),
        (4, "A-4", 2, 52, None, None),
        (6, "D-5", 2, 56, None, None),
        (10, "D-5", 2, 54, None, None),
        (12, "C-5", 2, 52, None, None),
        (16, "D-5", 2, 54, None, None),
        (20, "A#4", 2, 50, None, None),
        (28, "A#4", 2, 52, None, None),
        (32, "E-5", 2, 56, None, None),
        (36, "C-5", 2, 52, None, None),
        (44, "E-5", 2, 54, None, None),
        (48, "F-5", 2, 56, None, None),
        (52, "C-5", 2, 52, None, None),
        (56, "C#5", 2, 56, None, None),
        (60, "A-4", 2, 54, None, None),
    ]
    write_melody_with_echo(p1, mel_p1_lead2, lead_ch=7, echo_ch=None)

    # Ch 10: Brass Synth Stabs on syncopated chord hits
    for r, nt in [(0, "D-5"), (6, "F-5"), (16, "D-5"), (22, "F-5"), (32, "E-5"), (38, "G-5"), (48, "F-5"), (56, "E-5")]:
        p1.set(r, 10, note=nt, inst=9, vol=v_set(52))
    patterns.append(p1)

    # --------------------------------------------------------------------------
    # PATTERN 2 (Bars 9-12): Main Theme A1 — Circle of Fifths Keygen Anthem
    # Harmony: Dm | Gm7 | C7 | FMaj7 -> A7
    # --------------------------------------------------------------------------
    p2 = PatternGrid(2)
    roots_p2 = [
        ("D-2", "D-3", "A-2"),
        ("G-1", "G-2", "D-2"),
        ("C-2", "C-3", "G-2"),
        ("F-1", "F-2", "A-1"),
    ]
    chords_p2 = [
        ("D-4", "F-4", "A-4", "D-5"),
        ("G-3", "A#3", "D-4", "G-4"),
        ("C-4", "E-4", "G-4", "A#4"),
        ("F-3", "A-3", "C#4", "E-4"),
    ]
    pads_p2 = [
        ("F-3", "A-4"),
        ("G-3", "A#4"),
        ("E-3", "A#4"),
        ("F-3", "C#5"),
    ]
    add_drums_standard(p2, crash_rows=[0], fill_type="tom_desc")
    add_bass_line(p2, roots_p2, style="anthem")
    add_stereo_arps(p2, chords_p2, mode="full")
    add_pads(p2, pads_p2, vol_base=45)

    mel_p2 = [
        # Bar 9 (Dm): Soaring A5 hook -> A5 - G5 - F5 - E5 - D5 - F5 - A5
        (0, "A-5", 1, 64, None, None),
        (4, "G-5", 1, 58, None, None),
        (6, "F-5", 1, 60, None, None),
        (8, "E-5", 1, 56, None, None),
        (10, "D-5", 1, 60, None, None),
        (12, "F-5", 1, 60, None, None),
        (14, "A-5", 1, 62, None, None),
        # Bar 10 (Gm7): Bb5 - A5 - G5 - F5 - D5 - G5
        (16, "A#5", 1, 64, None, None),
        (20, "A-5", 1, 58, None, None),
        (22, "G-5", 1, 60, None, None),
        (24, "F-5", 1, 56, None, None),
        (26, "D-5", 1, 58, None, None),
        (30, "G-5", 1, 62, None, None),
        # Bar 11 (C7): G5 - F5 - E5 - D5 - C5 - E5 - G5
        (32, "G-5", 1, 63, None, None),
        (36, "F-5", 1, 58, None, None),
        (38, "E-5", 1, 60, None, None),
        (40, "D-5", 1, 56, None, None),
        (42, "C-5", 1, 58, None, None),
        (44, "E-5", 1, 60, None, None),
        (46, "G-5", 1, 62, None, None),
        # Bar 12 (FMaj7 -> A7): F5 - G5 - A5 -> E5 - F5 - G5
        (48, "F-5", 1, 62, None, None),
        (52, "G-5", 1, 58, None, None),
        (54, "A-5", 1, 62, None, None),
        (56, "E-5", 1, 60, None, None),
        (60, "F-5", 1, 58, None, None),
        (62, "G-5", 1, 62, None, None),
    ]
    write_melody_with_echo(p2, mel_p2, lead_ch=6, echo_ch=11)

    # Counter-melody on Ch 7 (Inst 2)
    mel_p2_c = [
        (0, "F-5", 2, 54, None, None),
        (6, "D-5", 2, 52, None, None),
        (10, "A-4", 2, 50, None, None),
        (16, "G-5", 2, 54, None, None),
        (22, "D-5", 2, 52, None, None),
        (26, "A#4", 2, 50, None, None),
        (32, "E-5", 2, 54, None, None),
        (38, "C-5", 2, 52, None, None),
        (42, "G-4", 2, 50, None, None),
        (48, "C-5", 2, 52, None, None),
        (56, "C#5", 2, 56, None, None),
        (62, "E-5", 2, 54, None, None),
    ]
    write_melody_with_echo(p2, mel_p2_c, lead_ch=7, echo_ch=None)

    for r, nt in [(0, "A-5"), (12, "F-5"), (16, "G-5"), (28, "D-5"), (32, "E-5"), (44, "C-5"), (48, "F-5"), (56, "C#5")]:
        p2.set(r, 10, note=nt, inst=8 if r % 16 == 0 else 9, vol=v_set(52))
    patterns.append(p2)

    # --------------------------------------------------------------------------
    # PATTERN 3 (Bars 13-16): Main Theme A2 — High Climax & Pivot to F Major
    # Harmony: BbMaj7 | Gm7 | Asus4 | A7 -> C7 (preparing F Major in Pat 4!)
    # --------------------------------------------------------------------------
    p3 = PatternGrid(3)
    roots_p3 = [
        ("A#1", "A#2", "F-2"),
        ("G-1", "G-2", "D-2"),
        ("A-1", "A-2", "E-2"),
        ("A-1", "C-2", "G-2"),
    ]
    chords_p3 = [
        ("A#3", "D-4", "F-4", "A-4"),
        ("G-3", "A#3", "D-4", "F-4"),
        ("A-3", "D-4", "E-4", "A-4"),
        ("A-3", "C#4", "E-4", "G-4"),
    ]
    pads_p3 = [
        ("D-3", "A-4"),
        ("G-3", "A#4"),
        ("E-3", "D-5"),
        ("E-3", "C#5"),
    ]
    add_drums_standard(p3, crash_rows=[0, 48], fill_type="snare_roll")
    add_bass_line(p3, roots_p3, style="anthem")
    add_stereo_arps(p3, chords_p3, mode="full")
    add_pads(p3, pads_p3, vol_base=46)

    mel_p3 = [
        # Bar 13 (BbMaj7): F5 - G5 - A5 - Bb5 - A5 - G5 - F5
        (0, "F-5", 1, 62, None, None),
        (4, "G-5", 1, 60, None, None),
        (6, "A-5", 1, 64, 3, 0x38),
        (10, "A#5", 1, 64, None, None),
        (12, "A-5", 1, 60, None, None),
        (14, "G-5", 1, 58, None, None),
        # Bar 14 (Gm7): G5 - A5 - Bb5 - D6 - C6 - Bb5 - A5
        (16, "G-5", 1, 62, None, None),
        (20, "A-5", 1, 60, None, None),
        (22, "A#5", 1, 63, None, None),
        (26, "D-6", 1, 64, 3, 0x40),
        (28, "C-6", 1, 60, None, None),
        (30, "A#5", 1, 58, None, None),
        # Bar 15 (Asus4): A5 held + 16th ornamental turn
        (32, "A-5", 1, 64, None, None),
        (38, "G-5", 1, 58, None, None),
        (40, "F-5", 1, 58, None, None),
        (42, "E-5", 1, 60, None, None),
        (44, "F-5", 1, 60, None, None),
        (46, "G-5", 1, 62, None, None),
        # Bar 16 (A7 -> C7 pivot): A5 -> E5 -> C5 -> G5 (leading to F5 in Pat 4!)
        (48, "A-5", 1, 64, None, None),
        (52, "E-5", 1, 60, None, None),
        (56, "C-5", 1, 58, None, None),
        (58, "D-5", 1, 60, None, None),
        (60, "E-5", 1, 62, None, None),
        (62, "G-5", 1, 64, None, None),
    ]
    write_melody_with_echo(p3, mel_p3, lead_ch=6, echo_ch=11)

    mel_p3_c = [
        (0, "D-5", 2, 54, None, None),
        (6, "F-5", 2, 56, None, None),
        (10, "F-5", 2, 56, None, None),
        (16, "D-5", 2, 54, None, None),
        (22, "G-5", 2, 56, None, None),
        (26, "A#5", 2, 58, None, None),
        (32, "E-5", 2, 56, None, None),
        (42, "C#5", 2, 54, None, None),
        (48, "C#5", 2, 56, None, None),
        (56, "G-4", 2, 52, None, None),
        (60, "C-5", 2, 56, None, None),
        (62, "E-5", 2, 58, None, None),
    ]
    write_melody_with_echo(p3, mel_p3_c, lead_ch=7, echo_ch=None)

    for r, nt in [(0, "A#5"), (16, "G-5"), (26, "D-6"), (32, "A-5"), (48, "A-5"), (56, "G-5")]:
        p3.set(r, 10, note=nt, inst=8, vol=v_set(54))
    patterns.append(p3)

    # --------------------------------------------------------------------------
    # PATTERN 4 (Bars 17-20): Section III — Relative Major Lift (F Major!)
    # Harmony: FMaj7 | C/E | Dm7 | BbMaj7 -> C7
    # Spotlight on Sync/FM Lead 2 (Ch 7) + Crystal Bell (Ch 10) + FM Slap Bass!
    # --------------------------------------------------------------------------
    p4 = PatternGrid(4)
    roots_p4 = [
        ("F-2", "F-3", "C-3"),
        ("E-2", "C-3", "G-2"),
        ("D-2", "D-3", "A-2"),
        ("A#1", "C-2", "G-2"),
    ]
    chords_p4 = [
        ("F-4", "A-4", "C-5", "E-5"),
        ("E-4", "G-4", "C-5", "E-5"),
        ("D-4", "F-4", "A-4", "C-5"),
        ("A#3", "D-4", "F-4", "G-4"),
    ]
    pads_p4 = [
        ("F-3", "A-4"),
        ("E-3", "G-4"),
        ("D-3", "A-4"),
        ("D-3", "G-4"),
    ]
    add_drums_standard(p4, crash_rows=[0], fill_type="tom_desc")
    add_bass_line(p4, roots_p4, style="major_groove")
    add_stereo_arps(p4, chords_p4, mode="sparkle")
    add_pads(p4, pads_p4, vol_base=44)

    # Sync/FM Lead 2 (Ch 7) takes main euphoric melody in F Major!
    mel_p4_lead2 = [
        # Bar 17 (FMaj7): A5 - G5 - F5 - C5 - D5 - F5 - A5
        (0, "A-5", 2, 64, None, None),
        (4, "G-5", 2, 58, None, None),
        (6, "F-5", 2, 62, None, None),
        (10, "C-5", 2, 56, None, None),
        (12, "D-5", 2, 58, None, None),
        (14, "F-5", 2, 60, None, None),
        # Bar 18 (C/E): G5 - F5 - E5 - C5 - G5 - E5
        (16, "G-5", 2, 63, None, None),
        (20, "F-5", 2, 58, None, None),
        (22, "E-5", 2, 60, None, None),
        (26, "C-5", 2, 56, None, None),
        (28, "E-5", 2, 58, None, None),
        (30, "G-5", 2, 62, None, None),
        # Bar 19 (Dm7): F5 - E5 - D5 - A4 - C5 - D5 - F5
        (32, "F-5", 2, 62, None, None),
        (36, "E-5", 2, 58, None, None),
        (38, "D-5", 2, 60, None, None),
        (42, "A-4", 2, 54, None, None),
        (44, "C-5", 2, 58, None, None),
        (46, "D-5", 2, 60, None, None),
        # Bar 20 (BbMaj7 -> C7): D5 - F5 - G5 - A5 - G5
        (48, "D-5", 2, 60, None, None),
        (52, "F-5", 2, 62, None, None),
        (56, "G-5", 2, 64, None, None),
        (60, "A-5", 2, 60, None, None),
        (62, "G-5", 2, 62, None, None),
    ]
    write_melody_with_echo(p4, mel_p4_lead2, lead_ch=7, echo_ch=11)

    # Ch 6 (Hero Lead 1) & Ch 10 (Crystal Bell) play sparkling call-and-response counter-phrases
    for r, nt in [(0, "C-5"), (8, "A-5"), (16, "C-5"), (24, "G-5"), (32, "A-4"), (40, "F-5"), (48, "A#4"), (56, "E-5")]:
        p4.set(r, 6, note=nt, inst=1, vol=v_set(50))
        p4.set(r + 2, 10, note=nt, inst=8, vol=v_set(52))
    p4.set(62, 6, vol=v_set(16))
    patterns.append(p4)

    # --------------------------------------------------------------------------
    # PATTERN 5 (Bars 21-24): Euphoric Canon & Pivot Back to D Minor
    # Harmony: FMaj7 | Gm7 | BbMaj7 | Asus4 -> A7
    # --------------------------------------------------------------------------
    p5 = PatternGrid(5)
    roots_p5 = [
        ("F-2", "F-3", "C-3"),
        ("G-1", "G-2", "D-2"),
        ("A#1", "A#2", "F-2"),
        ("A-1", "A-2", "E-2"),
    ]
    chords_p5 = [
        ("F-4", "A-4", "C-5", "E-5"),
        ("G-3", "A#3", "D-4", "F-4"),
        ("A#3", "D-4", "F-4", "A-4"),
        ("A-3", "C#4", "E-4", "G-4"),
    ]
    pads_p5 = [
        ("F-3", "C-5"),
        ("G-3", "A#4"),
        ("D-3", "A-4"),
        ("E-3", "C#5"),
    ]
    add_drums_standard(p5, crash_rows=[0], fill_type="snare_roll")
    add_bass_line(p5, roots_p5, style="major_groove")
    add_stereo_arps(p5, chords_p5, mode="full")
    add_pads(p5, pads_p5, vol_base=45)

    # Hero Lead 1 (Ch 6) and Sync/FM Lead 2 (Ch 7) in triumphant canon!
    mel_p5_1 = [
        (0, "C-6", 1, 64, None, None),
        (4, "A-5", 1, 60, None, None),
        (6, "F-5", 1, 60, None, None),
        (10, "G-5", 1, 58, None, None),
        (12, "A-5", 1, 62, None, None),
        (16, "A#5", 1, 64, None, None),
        (20, "G-5", 1, 60, None, None),
        (22, "D-5", 1, 58, None, None),
        (26, "F-5", 1, 60, None, None),
        (28, "G-5", 1, 62, None, None),
        (32, "A-5", 1, 64, None, None),
        (36, "F-5", 1, 60, None, None),
        (40, "D-5", 1, 58, None, None),
        (44, "F-5", 1, 60, None, None),
        (46, "G-5", 1, 62, None, None),
        (48, "A-5", 1, 64, None, None),
        (54, "G-5", 1, 60, None, None),
        (56, "E-5", 1, 60, None, None),
        (60, "C#5", 1, 62, None, None),
    ]
    write_melody_with_echo(p5, mel_p5_1, lead_ch=6, echo_ch=11)

    mel_p5_2 = [
        (4, "F-5", 2, 56, None, None),
        (8, "C-5", 2, 54, None, None),
        (12, "F-5", 2, 56, None, None),
        (20, "D-5", 2, 56, None, None),
        (24, "A#4", 2, 54, None, None),
        (28, "D-5", 2, 56, None, None),
        (36, "D-5", 2, 56, None, None),
        (40, "A#4", 2, 54, None, None),
        (44, "D-5", 2, 56, None, None),
        (48, "E-5", 2, 58, None, None),
        (54, "C#5", 2, 56, None, None),
        (58, "A-4", 2, 54, None, None),
    ]
    write_melody_with_echo(p5, mel_p5_2, lead_ch=7, echo_ch=None)

    for r, nt in [(0, "C-6"), (16, "A#5"), (32, "A-5"), (48, "A-5"), (56, "E-5")]:
        p5.set(r, 10, note=nt, inst=9, vol=v_set(52))
    patterns.append(p5)

    # --------------------------------------------------------------------------
    # PATTERN 6 (Bars 25-28): Section IV — Baroque Neoclassical Breakdown
    # Harmony: Dm | Dm/C | BbMaj7 | Gm6 -> A7
    # Spotlight on 10:HarpsiClav (Ch 6) & 08:CrystalBell (Ch 7/10) over Lush Pads!
    # --------------------------------------------------------------------------
    p6 = PatternGrid(6)
    roots_p6 = [
        ("D-2", "D-3", "A-2"),
        ("C-2", "C-3", "A-2"),
        ("A#1", "A#2", "F-2"),
        ("G-1", "A-1", "E-2"),
    ]
    chords_p6 = [
        ("D-4", "F-4", "A-4", "D-5"),
        ("C-4", "F-4", "A-4", "D-5"),
        ("A#3", "D-4", "F-4", "A-4"),
        ("G-3", "C#4", "E-4", "A-4"),
    ]
    pads_p6 = [
        ("D-3", "A-4"),
        ("C-3", "A-4"),
        ("A#2", "F-4"),
        ("A-2", "C#5"),
    ]
    add_drums_standard(p6, crash_rows=[0], fill_type="none", half_time=True)
    add_bass_line(p6, roots_p6, style="baroque")
    add_stereo_arps(p6, chords_p6, mode="sparkle")
    add_pads(p6, pads_p6, vol_base=48)

    # Dazzling 16th-note baroque harpsichord sequence (Inst 10 on Ch 6, echoed on Ch 11)
    baroque_notes = [
        # Bar 25 (Dm): D5 A4 F4 A4 D5 F5 A5 F5 | E5 A4 G4 A4 F5 D5 A4 F4
        "D-5", "A-4", "F-4", "A-4", "D-5", "F-5", "A-5", "F-5",
        "E-5", "A-4", "G-4", "A-4", "F-5", "D-5", "A-4", "F-4",
        # Bar 26 (Dm/C): C5 A4 F4 A4 C5 F5 A5 F5 | E5 C5 G4 C5 F5 E5 D5 C5
        "C-5", "A-4", "F-4", "A-4", "C-5", "F-5", "A-5", "F-5",
        "E-5", "C-5", "G-4", "C-5", "F-5", "E-5", "D-5", "C-5",
        # Bar 27 (BbMaj7): Bb4 F4 D4 F4 Bb4 D5 F5 D5 | G5 D5 Bb4 D5 F5 E5 D5 C#5
        "A#4", "F-4", "D-4", "F-4", "A#4", "D-5", "F-5", "D-5",
        "G-5", "D-5", "A#4", "D-5", "F-5", "E-5", "D-5", "C#5",
        # Bar 28 (Gm6 -> A7): G4Bb4D5G5 E5C#5A4E5 | C#5A4E5G5 A5G5F5E5
        "G-4", "A#4", "D-5", "G-5", "E-5", "C#5", "A-4", "E-5",
        "C#5", "A-4", "E-5", "G-5", "A-5", "G-5", "F-5", "E-5",
    ]
    for r, nt in enumerate(baroque_notes):
        vol = 60 if (r % 4 == 0) else (52 if r % 2 == 0 else 46)
        p6.set(r, 6, note=nt, inst=10, vol=v_set(vol))
        if r % 2 == 0 and r + 3 < 64:
            p6.set(r + 3, 11, note=nt, inst=10, vol=v_set(32), fx=8, param=216)

    # Crystal Bell (Inst 8 on Ch 7 & Ch 10) plays poised lyrical counter-melody above Harpsichord
    bell_counter = [
        (0, "A-5"), (6, "F-5"), (12, "D-5"),
        (16, "A-5"), (22, "F-5"), (28, "E-5"),
        (32, "F-5"), (38, "D-5"), (44, "A#4"),
        (48, "A#5"), (52, "A-5"), (56, "G-5"), (60, "E-5"),
    ]
    for r, nt in bell_counter:
        p6.set(r, 7, note=nt, inst=8, vol=v_set(56))
        p6.set(r, 10, note=nt, inst=2, vol=v_set(40))
    p6.set(63, 10, vol=v_set(12))
    patterns.append(p6)

    # --------------------------------------------------------------------------
    # PATTERN 7 (Bars 29-32): The Demoscene Riser & Ascending Build to Final Drop
    # Harmony: Gm7 | A7 | BbMaj7 -> Bdim7 | Asus4 -> A7/C#
    # --------------------------------------------------------------------------
    p7 = PatternGrid(7)
    roots_p7 = [
        ("G-1", "G-2", "D-2"),
        ("A-1", "A-2", "E-2"),
        ("A#1", "B-1", "F-2"),
        ("A-1", "C#2", "E-2"),
    ]
    chords_p7 = [
        ("G-3", "A#3", "D-4", "G-4"),
        ("A-3", "C#4", "E-4", "A-4"),
        ("A#3", "D-4", "F-4", "G#4"),
        ("A-3", "C#4", "E-4", "G-4"),
    ]
    pads_p7 = [
        ("G-3", "D-5"),
        ("A-3", "C#5"),
        ("A#3", "F-5"),
        ("A-3", "E-5"),
    ]
    add_drums_standard(p7, crash_rows=[0, 32, 48], fill_type="snare_roll")
    add_bass_line(p7, roots_p7, style="driving")
    add_stereo_arps(p7, chords_p7, mode="full")
    add_pads(p7, pads_p7, vol_base=46)

    # Ascending sequential trade between Hero Lead 1 (Ch 6) and Harpsichord/FM Lead (Ch 7/10)
    mel_p7 = [
        # Bar 29 (Gm7): G4 - A4 - Bb4 - D5 - G5 - F5 - D5
        (0, "G-4", 1, 58, None, None),
        (2, "A-4", 1, 56, None, None),
        (4, "A#4", 1, 60, None, None),
        (6, "D-5", 1, 62, None, None),
        (8, "G-5", 1, 64, None, None),
        (12, "F-5", 1, 60, None, None),
        (14, "D-5", 1, 58, None, None),
        # Bar 30 (A7): A4 - B4 - C#5 - E5 - A5 - G5 - E5
        (16, "A-4", 1, 60, None, None),
        (18, "B-4", 1, 58, None, None),
        (20, "C#5", 1, 62, None, None),
        (22, "E-5", 1, 62, None, None),
        (24, "A-5", 1, 64, None, None),
        (28, "G-5", 1, 60, None, None),
        (30, "E-5", 1, 58, None, None),
        # Bar 31 (Bb -> Bdim7): Bb4 - D5 - F5 - Bb5 -> B5 - Ab5 - F5 - D5
        (32, "A#4", 1, 60, None, None),
        (34, "D-5", 1, 60, None, None),
        (36, "F-5", 1, 62, None, None),
        (38, "A#5", 1, 64, None, None),
        (40, "B-5", 1, 64, None, None),
        (42, "G#5", 1, 60, None, None),
        (44, "F-5", 1, 60, None, None),
        (46, "D-5", 1, 58, None, None),
        # Bar 32 (Asus4 -> A7 climax build): E5 - F5 - G5 - A5 - Bb5 - B5 - C#6!
        (48, "E-5", 1, 62, None, None),
        (50, "F-5", 1, 62, None, None),
        (52, "G-5", 1, 62, None, None),
        (54, "A-5", 1, 63, None, None),
        (56, "A#5", 1, 63, None, None),
        (58, "B-5", 1, 64, None, None),
        (60, "C#6", 1, 64, 3, 0x38),
        (62, "A-5", 1, 64, None, None),
    ]
    write_melody_with_echo(p7, mel_p7, lead_ch=6, echo_ch=11)

    # Ch 7 & Ch 10 double the ascending build in lower 3rds/octaves!
    for r, nt in [(0, "D-4"), (8, "A#4"), (16, "E-4"), (24, "C#5"), (32, "F-4"), (40, "D-5"), (48, "A-4"), (52, "C#5"), (56, "E-5"), (60, "G-5")]:
        p7.set(r, 7, note=nt, inst=2, vol=v_set(56))
        p7.set(r, 10, note=nt, inst=10, vol=v_set(56))
    p7.set(63, 7, vol=v_set(20))
    patterns.append(p7)

    # --------------------------------------------------------------------------
    # PATTERN 8 (Bars 33-36): Section V — Virtuoso Keygen Solo Drop!
    # Harmony: Dm | BbMaj7 | C7 | Asus4 -> A7
    # Blistering melodic 16th-note keygen lead solo on Ch 6!
    # --------------------------------------------------------------------------
    p8 = PatternGrid(8)
    roots_p8 = [
        ("D-2", "D-3", "A-2"),
        ("A#1", "A#2", "F-2"),
        ("C-2", "C-3", "G-2"),
        ("A-1", "A-2", "E-2"),
    ]
    chords_p8 = [
        ("D-4", "F-4", "A-4", "D-5"),
        ("A#3", "D-4", "F-4", "A-4"),
        ("C-4", "E-4", "G-4", "A#4"),
        ("A-3", "C#4", "E-4", "G-4"),
    ]
    pads_p8 = [
        ("F-3", "A-4"),
        ("D-3", "A-4"),
        ("E-3", "A#4"),
        ("E-3", "C#5"),
    ]
    add_drums_standard(p8, crash_rows=[0], fill_type="tom_desc")
    add_bass_line(p8, roots_p8, style="anthem")
    add_stereo_arps(p8, chords_p8, mode="full")
    add_pads(p8, pads_p8, vol_base=46)

    # Virtuoso keygen solo on Ch 6 (Inst 1)
    solo_p8 = [
        # Bar 33 (Dm): Rapid pedal-point + Dorian shred
        (0, "D-6", 1, 64, None, None),
        (2, "A-5", 1, 58, None, None),
        (3, "F-5", 1, 56, None, None),
        (4, "A-5", 1, 60, None, None),
        (6, "D-6", 1, 64, None, None),
        (8, "C-6", 1, 62, None, None),
        (10, "A-5", 1, 58, None, None),
        (11, "G-5", 1, 56, None, None),
        (12, "F-5", 1, 60, None, None),
        (14, "E-5", 1, 58, None, None),
        (15, "D-5", 1, 56, None, None),
        # Bar 34 (BbMaj7): Lydian/Major arpeggio sweep
        (16, "F-5", 1, 62, None, None),
        (18, "D-5", 1, 56, None, None),
        (19, "A#4", 1, 56, None, None),
        (20, "D-5", 1, 60, None, None),
        (22, "F-5", 1, 62, None, None),
        (24, "A-5", 1, 64, None, None),
        (26, "A#5", 1, 62, None, None),
        (28, "A-5", 1, 60, None, None),
        (30, "F-5", 1, 58, None, None),
        (31, "D-5", 1, 56, None, None),
        # Bar 35 (C7): Ascending mixolydian run
        (32, "E-5", 1, 62, None, None),
        (34, "G-5", 1, 60, None, None),
        (36, "C-6", 1, 64, 3, 0x40),
        (38, "A#5", 1, 62, None, None),
        (40, "A-5", 1, 60, None, None),
        (42, "G-5", 1, 62, None, None),
        (44, "E-5", 1, 58, None, None),
        (46, "G-5", 1, 60, None, None),
        # Bar 36 (Asus4 -> A7): Harmonic minorneo-classical cadence
        (48, "A-5", 1, 64, None, None),
        (50, "G-5", 1, 58, None, None),
        (51, "F-5", 1, 58, None, None),
        (52, "E-5", 1, 62, None, None),
        (54, "G-5", 1, 60, None, None),
        (56, "F-5", 1, 60, None, None),
        (58, "E-5", 1, 58, None, None),
        (60, "C#5", 1, 62, None, None),
        (62, "E-5", 1, 62, None, None),
    ]
    write_melody_with_echo(p8, solo_p8, lead_ch=6, echo_ch=11, echo_delay=2, echo_atten=26)

    # Ch 7 & Ch 10: Punchy syncopated Brass Stabs & FM Lead answers
    for r, nt in [(0, "A-4"), (6, "F-5"), (16, "A#4"), (24, "D-5"), (32, "C-5"), (40, "E-5"), (48, "D-5"), (52, "C#5"), (60, "A-4")]:
        p8.set(r, 7, note=nt, inst=2, vol=v_set(52))
        p8.set(r, 10, note=nt, inst=9, vol=v_set(54))
    p8.set(63, 7, vol=v_set(16))
    patterns.append(p8)

    # --------------------------------------------------------------------------
    # PATTERN 9 (Bars 37-40): Supercharged Dual-Lead Reprise of Theme A
    # Harmony: Dm | Gm7 | C7 | FMaj7 -> A7
    # Hero Lead 1 (Ch 6) + Sync/FM Lead 2 (Ch 7) + HarpsiClav (Ch 10)
    # --------------------------------------------------------------------------
    p9 = PatternGrid(9)
    add_drums_standard(p9, crash_rows=[0], fill_type="tom_desc")
    add_bass_line(p9, roots_p2, style="anthem")
    add_stereo_arps(p9, chords_p2, mode="full")
    add_pads(p9, pads_p2, vol_base=46)

    write_melody_with_echo(p9, mel_p2, lead_ch=6, echo_ch=11)
    write_melody_with_echo(p9, mel_p2_c, lead_ch=7, echo_ch=None)

    # Harpsichord (Inst 10 on Ch 10) doubles the main anthem hook for extra keygen bite!
    for row, note, _inst, vol, _fx, _param in mel_p2:
        p9.set(row, 10, note=note, inst=10, vol=v_set(max(36, vol - 10)))
    patterns.append(p9)

    # --------------------------------------------------------------------------
    # PATTERN 10 (Bars 41-44): Peak Emotional Climax (VI - VII - i - iv/V7)
    # Harmony: BbMaj7 | C7 | Dm7 | Gm7 -> A7
    # --------------------------------------------------------------------------
    p10 = PatternGrid(10)
    roots_p10 = [
        ("A#1", "A#2", "F-2"),
        ("C-2", "C-3", "G-2"),
        ("D-2", "D-3", "A-2"),
        ("G-1", "A-1", "E-2"),
    ]
    chords_p10 = [
        ("A#3", "D-4", "F-4", "A-4"),
        ("C-4", "E-4", "G-4", "A#4"),
        ("D-4", "F-4", "A-4", "C-5"),
        ("G-3", "C#4", "E-4", "G-4"),
    ]
    pads_p10 = [
        ("D-3", "A-4"),
        ("E-3", "A#4"),
        ("F-3", "C-5"),
        ("E-3", "C#5"),
    ]
    add_drums_standard(p10, crash_rows=[0, 32], fill_type="snare_roll")
    add_bass_line(p10, roots_p10, style="anthem")
    add_stereo_arps(p10, chords_p10, mode="full")
    add_pads(p10, pads_p10, vol_base=46)

    mel_p10 = [
        # Bar 41 (BbMaj7): Soaring D6 -> C6 -> A5 -> F5 -> D5 -> F5 -> A5
        (0, "D-6", 1, 64, None, None),
        (4, "C-6", 1, 60, None, None),
        (6, "A-5", 1, 62, None, None),
        (10, "F-5", 1, 58, None, None),
        (12, "D-5", 1, 58, None, None),
        (14, "A-5", 1, 62, None, None),
        # Bar 42 (C7): C6 -> Bb5 -> G5 -> E5 -> C5 -> E5 -> G5
        (16, "C-6", 1, 64, None, None),
        (20, "A#5", 1, 60, None, None),
        (22, "G-5", 1, 62, None, None),
        (26, "E-5", 1, 58, None, None),
        (28, "G-5", 1, 60, None, None),
        (30, "C-6", 1, 62, None, None),
        # Bar 43 (Dm7): A5 -> G5 -> F5 -> D5 -> F5 -> A5 -> D6
        (32, "A-5", 1, 64, None, None),
        (36, "G-5", 1, 58, None, None),
        (38, "F-5", 1, 62, None, None),
        (42, "D-5", 1, 58, None, None),
        (44, "F-5", 1, 60, None, None),
        (46, "A-5", 1, 62, None, None),
        # Bar 44 (Gm7 -> A7): Bb5 -> A5 -> G5 -> F5 -> E5 -> C#5 -> E5
        (48, "A#5", 1, 64, None, None),
        (52, "A-5", 1, 60, None, None),
        (54, "G-5", 1, 60, None, None),
        (56, "E-5", 1, 62, None, None),
        (60, "C#5", 1, 60, None, None),
        (62, "E-5", 1, 62, None, None),
    ]
    write_melody_with_echo(p10, mel_p10, lead_ch=6, echo_ch=11)

    mel_p10_2 = [
        (0, "F-5", 2, 56, None, None),
        (6, "D-5", 2, 54, None, None),
        (16, "E-5", 2, 56, None, None),
        (22, "C-5", 2, 54, None, None),
        (32, "F-5", 2, 56, None, None),
        (38, "D-5", 2, 54, None, None),
        (48, "D-5", 2, 56, None, None),
        (56, "C#5", 2, 56, None, None),
        (62, "A-4", 2, 54, None, None),
    ]
    write_melody_with_echo(p10, mel_p10_2, lead_ch=7, echo_ch=None)

    for r, nt in [(0, "D-6"), (16, "C-6"), (32, "A-5"), (48, "A#5"), (56, "A-5")]:
        p10.set(r, 10, note=nt, inst=8, vol=v_set(54))
    patterns.append(p10)

    # --------------------------------------------------------------------------
    # PATTERN 11 (Bars 45-48): Section VI — Outrun Coda & Seamless Loop Turnaround
    # Harmony: Dm | BbMaj7 | Gm7 | Asus4 -> A7 (resolving seamlessly into Pattern 0 Row 0!)
    # --------------------------------------------------------------------------
    p11 = PatternGrid(11)
    add_drums_standard(p11, crash_rows=[0], fill_type="loop_pickup")
    add_bass_line(p11, roots_dm_bb_gm_a, style="driving")
    add_stereo_arps(p11, chords_dm_bb_gm_a, mode="full")
    add_pads(p11, pads_dm_bb_gm_a, vol_base=42)

    mel_p11 = [
        # Bar 45 (Dm): Triumphant tonic resolution D5 - F5 - A5 - D6 - A5 - F5
        (0, "D-5", 1, 63, None, None),
        (2, "F-5", 1, 58, None, None),
        (4, "A-5", 1, 62, None, None),
        (6, "D-6", 1, 64, None, None),
        (10, "A-5", 1, 60, None, None),
        (12, "F-5", 1, 58, None, None),
        (14, "E-5", 1, 56, None, None),
        # Bar 46 (BbMaj7): D5 - F5 - A5 - G5 - F5 - D5
        (16, "D-5", 1, 62, None, None),
        (20, "F-5", 1, 60, None, None),
        (24, "A-5", 1, 62, None, None),
        (28, "G-5", 1, 58, None, None),
        (30, "F-5", 1, 56, None, None),
        # Bar 47 (Gm7): G5 - F5 - D5 - Bb4 - C5 - D5
        (32, "G-5", 1, 62, None, None),
        (35, "F-5", 1, 58, None, None),
        (38, "D-5", 1, 60, None, None),
        (42, "A#4", 1, 56, None, None),
        (44, "C-5", 1, 58, None, None),
        (46, "D-5", 1, 60, None, None),
        # Bar 48 (Asus4 -> A7): E5 -> C#5 -> A4 -> B4 -> C#5 (resolves directly into D5 on Pat 0 Row 0!)
        (48, "E-5", 1, 62, None, None),
        (52, "C#5", 1, 60, None, None),
        (56, "A-4", 1, 56, None, None),
        (60, "B-4", 1, 58, None, None),
        (62, "C#5", 1, 60, None, None),
    ]
    write_melody_with_echo(p11, mel_p11, lead_ch=6, echo_ch=11)
    # Clean 16th-note pickup caesura on Row 63 across all channels right before Pattern 0 Row 0 downbeat!
    # This guarantees a punchy breath into the loop downbeat AND exact [0, 0] last_frame continuity.
    for ch_idx in range(12):
        p11.cells.pop((62, ch_idx), None) if ch_idx in (0, 1, 2, 4, 5) else None
        p11.cells.pop((63, ch_idx), None)
        p11.set(62, ch_idx, vol=v_set(18))
        p11.set(63, ch_idx, note="off", vol=v_set(0))

    # Ch 7: Harmony Lead 2 plays in Bars 45-47 and fades cleanly by Row 56 so Pattern 0 Row 0 starts fresh
    p11.set(0, 7, note="F-4", inst=2, vol=v_set(52))
    p11.set(6, 7, note="A-5", inst=2, vol=v_set(54))
    p11.set(16, 7, note="A#4", inst=2, vol=v_set(50))
    p11.set(24, 7, note="F-5", inst=2, vol=v_set(52))
    p11.set(32, 7, note="A#4", inst=2, vol=v_set(50))
    p11.set(38, 7, note="G-4", inst=2, vol=v_set(48))
    p11.set(48, 7, note="A-4", inst=2, vol=v_set(48))
    p11.set(52, 7, note="G-4", inst=2, vol=v_set(42))
    p11.set(56, 7, vol=v_set(24))
    p11.set(58, 7, vol=v_set(10))
    p11.set(60, 7, vol=v_set(0))

    for r, nt in [(0, "A-5"), (6, "D-6"), (16, "A-5"), (32, "A#5"), (48, "A-5"), (52, "G-5")]:
        p11.set(r, 10, note=nt, inst=8, vol=v_set(50))
    patterns.append(p11)

    return patterns


def main() -> None:
    t0 = time.time()
    print("1. Creating new 12-channel module...")
    ft2_call("module_new", channels=12, name="RAZORLIGHT KEYGEN")
    ft2_call("song_set", name="RAZORLIGHT KEYGEN", bpm=138, speed=6, length=12, loop_start=0, channels=12)

    print("2. Synthesizing and loading 16 custom instruments...")
    insts = build_all_instruments()
    for ins in insts:
        iid = ins["id"]
        ft2_call("instrument_set", instrument=iid, name=ins["name"])
        b64_pcm = base64.b64encode(ins["pcm"].tobytes()).decode("ascii")
        ft2_call("sample_create_from_pcm", instrument=iid, sample=0, pcm=b64_pcm, encoding="int16", name=ins["name"])
        ft2_call(
            "sample_set",
            instrument=iid,
            sample=0,
            name=ins["name"],
            volume=ins["volume"],
            panning=ins["panning"],
            finetune=ins["finetune"],
            relative_note=ins["rel_note"],
            loop_start=ins["loop_start"],
            loop_length=ins["loop_length"],
            flags=ins["flags"],
        )

    print("3. Building and flushing 12 patterns (768 rows across 12 channels)...")
    patterns = build_all_patterns()
    total_cells = 0
    for pat in patterns:
        total_cells += pat.flush()
        ft2_call("order_set", position=pat.pat_idx, pattern=pat.pat_idx)

    print(f"   Flushed {total_cells} pattern cells in {time.time() - t0:.2f}s.")

    print("4. Saving XM to /workspace/submission/tune.xm and rendering WAV preview...")
    ft2_call("module_save", path="/workspace/submission/tune.xm", format="xm")
    render_res = ft2_call("module_render", path="/workspace/submission/preview.wav", rate=44100, bits=16)
    print("   Render result:", render_res)

    # Also render a 13-pattern seam verification WAV (Order 0..11 + Order 0 at pos 12)
    # so we can inspect the exact live tracker transition from Pattern 11 Row 63 -> Pattern 0 Row 0!
    ft2_call("song_set", length=13, loop_start=0)
    ft2_call("order_set", position=12, pattern=0)
    ft2_call("module_render", path="/tmp/seam_check.wav", rate=44100, bits=16)

    # Restore exact 12-pattern song length and re-save final tune.xm
    ft2_call("song_set", length=12, loop_start=0)
    ft2_call("module_save", path="/workspace/submission/tune.xm", format="xm")
    print("Done!")


if __name__ == "__main__":
    main()
