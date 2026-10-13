"""Compose the complete 12-pattern (48-bar) HYPERION KEYGEN tracker module."""
from __future__ import annotations
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/keygen")
sys.path.insert(0, "/workspace")
from bridge import exchange
from src.instruments import build_all_instruments


def call(tool_name: str, **kwargs):
    res = exchange({"op": "call", "name": tool_name, "arguments": kwargs})
    if res.get("isError"):
        raise RuntimeError(f"{tool_name} failed: {res}")
    return res


def v(vol_0_64: int) -> int:
    """XM volume column byte for set volume 0..64."""
    return 0x10 + max(0, min(64, int(vol_0_64)))


def vs_down(speed_1_15: int) -> int:
    """XM volume column byte for volume slide down."""
    return 0x60 + max(1, min(15, int(speed_1_15)))


def vs_up(speed_1_15: int) -> int:
    """XM volume column byte for volume slide up."""
    return 0x70 + max(1, min(15, int(speed_1_15)))


class PatternBuilder:
    def __init__(self, num_patterns: int = 12, channels: int = 12, rows: int = 64):
        self.num_patterns = num_patterns
        self.channels = channels
        self.rows = rows
        # grid[pat][(row, ch)] = dict of cell args
        self.grid: list[dict[tuple[int, int], dict]] = [{} for _ in range(num_patterns)]

    def set(
        self,
        pat: int,
        row: int,
        ch: int,
        note: str | int | None = None,
        inst: int | None = None,
        vol: int | None = None,
        fx: int | None = None,
        param: int | None = None,
    ):
        if not (0 <= pat < self.num_patterns and 0 <= row < self.rows and 0 <= ch < self.channels):
            return
        cell = self.grid[pat].get((row, ch), {"pattern": pat, "row": row, "channel": ch})
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
        self.grid[pat][(row, ch)] = cell

    def off(self, pat: int, row: int, ch: int):
        self.set(pat, row, ch, note="===")

    def add_phrase(self, pat: int, default_inst: int, events: list[tuple], ch: int | None = None):
        inst_to_ch = {10: 4, 11: 5, 12: 6, 13: 7, 14: 8, 15: 10, 16: 11}
        if ch is None:
            ch = inst_to_ch[default_inst]
        """
        events: list of tuples:
          (row, note, vol_0_64) or
          (row, note, vol_0_64, fx, param) or
          (row, note, vol_0_64, fx, param, inst_override)
        """
        for ev in events:
            row = ev[0]
            note = ev[1]
            vol = ev[2] if len(ev) > 2 else None
            fx = ev[3] if len(ev) > 3 else None
            param = ev[4] if len(ev) > 4 else None
            inst_ov = ev[5] if len(ev) > 5 else default_inst
            if note == "===":
                self.set(pat, row, ch, note="===", fx=fx, param=param)
            elif note is None:
                self.set(pat, row, ch, vol=(v(vol) if vol is not None else None), fx=fx, param=param)
            else:
                self.set(
                    pat,
                    row,
                    ch,
                    note=note,
                    inst=inst_ov,
                    vol=(v(vol) if vol is not None else None),
                    fx=fx,
                    param=param,
                )
        if default_inst == 15 and ch == 10:
            occupied = {ev[0] for ev in events}
            for ev in events:
                r, nt = ev[0], ev[1]
                vl = ev[2] if len(ev) > 2 else 50
                if isinstance(nt, str) and nt != "===" and (r + 2) < 62 and (r + 2) not in occupied:
                    self.set(pat, r + 2, 10, note=nt, inst=15, vol=v(max(18, int(vl * 0.42))), fx=8, param=240)


# ==============================================================================
# DRUM & PERCUSSION HELPERS (Ch 0: Kick/Tom, Ch 1: Snare/Clap, Ch 2: Hats/Crash)
# ==============================================================================

def write_drums_standard(
    pb: PatternBuilder,
    pat: int,
    crash_rows: tuple[int, ...] = (0,),
    style: str = "driving",
    fill_type: str = "snare_tom",
):
    for bar in range(4):
        b0 = bar * 16
        is_fill_bar = (bar == 3)
        for step in range(16):
            r = b0 + step
            # Crash cymbals on requested rows
            if r in crash_rows:
                pb.set(pat, r, 2, note="C-4", inst=6, vol=v(54))
            else:
                # Hi-Hat pattern
                if style == "breakdown" and bar < 2:
                    if step % 2 == 0:
                        pb.set(pat, r, 2, note="C-4", inst=4, vol=v(38 if step % 4 == 0 else 28))
                elif style == "halftime":
                    if step % 4 == 2:
                        pb.set(pat, r, 2, note="C-4", inst=5, vol=v(46))
                    else:
                        pb.set(pat, r, 2, note="C-4", inst=4, vol=v(40 if step % 2 == 0 else 26))
                else:
                    # Driving 16th hats with open hat on offbeats (2, 6, 10, 14)
                    if step % 4 == 2:
                        pb.set(pat, r, 2, note="C-4", inst=5, vol=v(50))
                    else:
                        vel = 44 if step % 4 == 0 else (34 if step % 2 == 0 else 26)
                        pb.set(pat, r, 2, note="C-4", inst=4, vol=v(vel))

            if is_fill_bar and step >= 8:
                # Bar 4 Fill (rows 56..63) handled below
                continue

            if style == "intro" and bar < 2:
                # Punchy syncopated intro kick + light rim/snare
                if step in (0, 6, 8, 14):
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(62 if step in (0, 8) else 52))
                if step in (4, 12):
                    pb.set(pat, r, 1, note="C-4", inst=3, vol=v(48))
                elif step == 15:
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(34))
            elif style == "breakdown":
                if bar < 2:
                    if step in (0, 8):
                        pb.set(pat, r, 0, note="C-4", inst=1, vol=v(56))
                    if step in (4, 12):
                        pb.set(pat, r, 1, note="C-4", inst=3, vol=v(46))
                else:
                    if step in (0, 4, 8, 12):
                        pb.set(pat, r, 0, note="C-4", inst=1, vol=v(60))
                    if step in (4, 12):
                        pb.set(pat, r, 1, note="C-4", inst=2, vol=v(56))
            elif style == "halftime":
                # Atmospheric half-time groove (Kick on 0, 6, 10; Big Snare/Clap on 8)
                if step in (0, 6, 10):
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(64 if step == 0 else 54))
                if step == 8:
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(64))
                elif step in (11, 14):
                    pb.set(pat, r, 1, note="C-4", inst=3, vol=v(36))
            else:
                # Driving four-on-the-floor + syncopated double-kick pickups
                if step in (0, 4, 8, 12):
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(64))
                elif step == 14 and bar % 2 == 1:
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(52))
                elif step == 7 and bar == 1:
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(48))

                # Snare + Clap backbeat on 4 & 12 + ghost notes
                if step == 4:
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(62))
                elif step == 12:
                    pb.set(pat, r, 1, note="C-4", inst=3 if bar % 2 == 0 else 2, vol=v(64))
                elif step in (7, 15) and style == "climax":
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(34))
                elif step == 15 and bar % 2 == 0:
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(32))

    # Write Bar 4 Fill on rows 56..63
    if fill_type == "snare_tom":
        pb.set(pat, 56, 0, note="C-4", inst=1, vol=v(64))
        pb.set(pat, 56, 1, note="C-4", inst=2, vol=v(56))
        pb.set(pat, 57, 1, note="C-4", inst=2, vol=v(44))
        pb.set(pat, 58, 0, note="F-4", inst=7, vol=v(60))
        pb.set(pat, 59, 0, note="D-4", inst=7, vol=v(58))
        pb.set(pat, 60, 1, note="C-4", inst=2, vol=v(62))
        pb.set(pat, 60, 0, note="C-4", inst=7, vol=v(60))
        pb.set(pat, 61, 0, note="A-3", inst=7, vol=v(60))
        pb.set(pat, 62, 1, note="C-4", inst=3, vol=v(64))
        pb.set(pat, 62, 0, note="G-3", inst=7, vol=v(62))
        pb.set(pat, 63, 1, note="C-4", inst=2, vol=v(64), fx=14, param=0x93)  # E93 retrig!
    elif fill_type == "buildup_roll":
        # Pattern 8 accelerator snare roll across the whole pattern!
        for r in range(64):
            if r < 16:
                if r % 4 == 0:
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(60))
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(46 + r // 2))
            elif r < 32:
                if r % 2 == 0:
                    pb.set(pat, r, 0, note="C-4", inst=1, vol=v(60))
                    pb.set(pat, r, 1, note="C-4", inst=2, vol=v(48 + (r - 16) // 2))
            elif r < 56:
                pb.set(pat, r, 0, note="C-4", inst=1 if r % 2 == 0 else 7, vol=v(58))
                pb.set(pat, r, 1, note="C-4", inst=2, vol=v(44 + (r - 32) // 2))
            elif r < 62:
                # Blistering 32nd-note tracker snare roll (E93 / E92)
                pb.set(pat, r, 1, note="C-4", inst=2, vol=v(64), fx=14, param=(0x93 if r < 60 else 0x92))
                pb.set(pat, r, 0, note="D-4" if r < 59 else "F-4", inst=7, vol=v(62))
            elif r == 62:
                pb.set(pat, r, 1, note="C-4", inst=3, vol=v(64))
                pb.set(pat, r, 0, note="C-4", inst=1, vol=v(64))
            elif r == 63:
                # Dramatic 1-row breath before the Climax crash!
                pb.off(pat, r, 0)
                pb.off(pat, r, 1)
                pb.off(pat, r, 2)
    elif fill_type == "turnaround":
        # Pattern 11 final bar turnaround leading seamlessly back to Pattern 0 Row 0!
        pb.set(pat, 56, 0, note="C-4", inst=1, vol=v(64))
        pb.set(pat, 56, 1, note="C-4", inst=2, vol=v(58))
        pb.set(pat, 58, 0, note="E-4", inst=7, vol=v(60))
        pb.set(pat, 59, 1, note="C-4", inst=2, vol=v(52))
        pb.set(pat, 60, 0, note="C#4", inst=7, vol=v(62))
        pb.set(pat, 60, 1, note="C-4", inst=3, vol=v(62))
        pb.set(pat, 61, 0, note="A-3", inst=7, vol=v(62))
        pb.set(pat, 62, 0, note="C-4", inst=1, vol=v(64))
        pb.set(pat, 62, 1, note="C-4", inst=2, vol=v(64))
        pb.set(pat, 63, 1, note="C-4", inst=2, vol=v(58), fx=14, param=0xD3)  # ED3 flam pickup into Pat 0 Row 0!


# ==============================================================================
# BASSLINE HELPER (Ch 3: Inst 8 Punch Bass & Inst 9 Acid Sub)
# ==============================================================================

def write_bass_bars(
    pb: PatternBuilder,
    pat: int,
    bar_roots: list[tuple[str, str, str, str]],
    pattern_style: str = "octave_16th",
):
    """
    bar_roots: list of 4 tuples (one per bar), each tuple has 4 root pairs (low_oct, high_oct, fifth, passing)
    or we pass explicit 4-beat roots per bar.
    """
    for bar_idx, beats in enumerate(bar_roots):
        b0 = bar_idx * 16
        for beat_idx, root in enumerate(beats):
            r0 = b0 + beat_idx * 4
            # Parse root note name e.g. "D-2" -> high octave "D-3"
            if root.endswith("-1"):
                hi = root[:-2] + "-2"
            elif root.endswith("-2"):
                hi = root[:-2] + "-3"
            else:
                hi = root

            if pattern_style == "octave_16th":
                # Classic driving demoscene octave bass: Root (Inst 8) - Hi (Inst 9) - Root (Inst 9) - Hi (Inst 9)
                pb.set(pat, r0 + 0, 3, note=root, inst=8, vol=v(62))
                pb.set(pat, r0 + 1, 3, note=hi, inst=9, vol=v(48), fx=14, param=0xC4)
                pb.set(pat, r0 + 2, 3, note=root, inst=9, vol=v(54))
                pb.set(pat, r0 + 3, 3, note=hi, inst=9, vol=v(52), fx=14, param=0xC4)
            elif pattern_style == "intro_pulse":
                if bar_idx == 0:
                    if beat_idx == 0:
                        pb.set(pat, r0 + 0, 3, note=root, inst=8, vol=v(58))
                    else:
                        pb.set(pat, r0 + 0, 3, note=hi, inst=9, vol=v(38))
                        pb.set(pat, r0 + 2, 3, note=hi, inst=9, vol=v(34), fx=14, param=0xC3)
                elif bar_idx == 1:
                    pb.set(pat, r0 + 0, 3, note=root, inst=8, vol=v(48))
                    pb.set(pat, r0 + 2, 3, note=hi, inst=9, vol=v(42))
                else:
                    pb.set(pat, r0 + 0, 3, note=root, inst=8, vol=v(60))
                    pb.set(pat, r0 + 2, 3, note=hi, inst=9, vol=v(50))
                    pb.set(pat, r0 + 3, 3, note=root, inst=9, vol=v(46), fx=14, param=0xC3)
            elif pattern_style == "baroque_16th":
                scale = 0.76 if bar_idx < 2 else 1.0
                pb.set(pat, r0 + 0, 3, note=root, inst=9, vol=v(int(58 * scale)))
                pb.set(pat, r0 + 1, 3, note=hi, inst=9, vol=v(int(46 * scale)))
                pb.set(pat, r0 + 2, 3, note=hi, inst=9, vol=v(int(52 * scale)))
                pb.set(pat, r0 + 3, 3, note=root, inst=9, vol=v(int(48 * scale)))
            elif pattern_style == "halftime":
                if beat_idx in (0, 2):
                    pb.set(pat, r0 + 0, 3, note=root, inst=8, vol=v(62))
                    pb.set(pat, r0 + 3, 3, note=hi, inst=9, vol=v(48))
                else:
                    pb.set(pat, r0 + 2, 3, note=root, inst=8, vol=v(56))
                    pb.set(pat, r0 + 3, 3, note=hi, inst=9, vol=v(50))


# ==============================================================================
# PAD & HARMONY HELPERS (Ch 8 Left Pad, Ch 9 Right Pad, Ch 6 Arp, Ch 7 Pluck)
# ==============================================================================

def write_pad_chords(pb: PatternBuilder, pat: int, chords: list[tuple[int, str, str, int]]):
    """
    chords: list of (start_row, left_note, right_note, vol_0_64)
    """
    for row, n_left, n_right, vol in chords:
        if n_left == "===":
            pb.off(pat, row, 8)
            pb.off(pat, row, 9)
        else:
            pb.set(pat, row, 8, note=n_left, inst=14, vol=v(vol), fx=8, param=4)
            pb.set(pat, row, 9, note=n_right, inst=14, vol=v(vol), fx=8, param=252)


def write_arp_and_pluck_bars(
    pb: PatternBuilder,
    pat: int,
    bar_chords: list[tuple[list[str], int, list[str]]],
    arp_vol: int = 44,
    pluck_vol: int = 46,
    mode: str = "full",
):
    """
    bar_chords: list of 8 half-bar (8-row) entries per pattern:
      (arp_notes_4, arp_fx_param, pluck_notes_4)
    """
    for hb_idx, (arp_n, arp_fx, pluck_n) in enumerate(bar_chords):
        r0 = hb_idx * 8
        for s in range(8):
            r = r0 + s
            an = arp_n[s % len(arp_n)]
            pn = pluck_n[s % len(pluck_n)]
            # Alternate stereo pan slightly on Ch 6 for extra sparkle
            vel_a = arp_vol if s % 2 == 0 else max(24, arp_vol - 8)
            if mode != "pluck_only":
                pb.set(pat, r, 6, note=an, inst=12, vol=v(vel_a), fx=0, param=arp_fx)
            if mode == "full" or mode == "pluck_only":
                vel_p = pluck_vol if s % 2 == 0 else max(24, pluck_vol - 10)
                pb.set(pat, r, 7, note=pn, inst=13, vol=v(vel_p))
            elif mode == "sparse_pluck" and s in (0, 3, 6):
                pb.set(pat, r, 7, note=pn, inst=13, vol=v(pluck_vol))


def build_song() -> PatternBuilder:
    pb = PatternBuilder(num_patterns=12, channels=12, rows=64)

    # Common chord tables (8 half-bars = 64 rows per pattern)
    # Progression A1 (Dm | Bb | Gm7 -> C7 | Asus4 -> A7)
    chords_A1 = [
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["A-4", "F-4", "D-4", "A-3"]),
        (["D-4", "A-4", "D-5", "F-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["A#3", "D-4", "F-4", "A#4"], 0x47, ["F-4", "D-4", "A#3", "F-3"]),
        (["A#3", "F-4", "A#4", "D-5"], 0x47, ["A#4", "F-4", "D-4", "A#3"]),
        (["G-3", "A#3", "D-4", "F-4"], 0x37, ["D-4", "A#3", "G-3", "D-4"]),
        (["C-4", "E-4", "G-4", "A#4"], 0x47, ["G-4", "E-4", "C-4", "G-3"]),
        (["A-3", "D-4", "E-4", "A-4"], 0x57, ["E-4", "D-4", "A-3", "E-4"]),
        (["A-3", "C#4", "E-4", "G-4"], 0x47, ["G-4", "E-4", "C#4", "A-3"]),
    ]

    # Progression A2 (Dm | Bb -> G/B | C -> A7/C# | Dm -> C/E)
    chords_A2 = [
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["A-4", "F-4", "D-4", "A-3"]),
        (["F-4", "A-4", "D-5", "F-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["A#3", "D-4", "F-4", "A#4"], 0x47, ["F-4", "D-4", "A#3", "D-4"]),
        (["B-3", "D-4", "G-4", "B-4"], 0x38, ["G-4", "D-4", "B-3", "G-3"]),
        (["C-4", "E-4", "G-4", "C-5"], 0x47, ["G-4", "E-4", "C-4", "E-4"]),
        (["C#4", "E-4", "G-4", "A-4"], 0x36, ["A-4", "G-4", "E-4", "C#4"]),
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["A-4", "F-4", "D-4", "F-4"]),
        (["E-4", "G-4", "C-5", "E-5"], 0x38, ["C-5", "G-4", "E-4", "C-4"]),
    ]

    # Progression B1 (Fmaj7 | C/E -> C | Dm7 -> Bbmaj7 | Gm7 -> C7)
    chords_B1 = [
        (["F-4", "A-4", "C-5", "E-5"], 0x47, ["C-5", "A-4", "F-4", "C-4"]),
        (["F-4", "C-5", "E-5", "A-5"], 0x47, ["E-5", "C-5", "A-4", "F-4"]),
        (["E-4", "G-4", "C-5", "E-5"], 0x38, ["C-5", "G-4", "E-4", "C-4"]),
        (["C-4", "E-4", "G-4", "C-5"], 0x47, ["G-4", "E-4", "C-4", "G-3"]),
        (["D-4", "F-4", "A-4", "C-5"], 0x37, ["A-4", "F-4", "D-4", "A-3"]),
        (["A#3", "D-4", "F-4", "A-4"], 0x47, ["F-4", "D-4", "A#3", "F-3"]),
        (["G-3", "A#3", "D-4", "F-4"], 0x37, ["D-4", "A#3", "G-3", "D-4"]),
        (["C-4", "E-4", "G-4", "A#4"], 0x47, ["A#4", "G-4", "E-4", "C-4"]),
    ]

    # Progression B2 (F | Am7 -> D7/F# | Gm7 -> Bbm6 | F/A -> A7)
    chords_B2 = [
        (["F-4", "A-4", "C-5", "F-5"], 0x47, ["C-5", "A-4", "F-4", "C-4"]),
        (["A-4", "C-5", "F-5", "A-5"], 0x38, ["F-5", "C-5", "A-4", "F-4"]),
        (["A-3", "C-4", "E-4", "G-4"], 0x37, ["E-4", "C-4", "A-3", "E-4"]),
        (["D-4", "F#4", "A-4", "C-5"], 0x47, ["A-4", "F#4", "D-4", "A-3"]),
        (["G-3", "A#3", "D-4", "F-4"], 0x37, ["D-4", "A#3", "G-3", "D-4"]),
        (["A#3", "C#4", "F-4", "G-4"], 0x37, ["F-4", "C#4", "A#3", "G-3"]),
        (["A-3", "C-4", "F-4", "A-4"], 0x38, ["F-4", "C-4", "A-3", "F-3"]),
        (["A-3", "C#4", "E-4", "G-4"], 0x47, ["G-4", "E-4", "C#4", "A-3"]),
    ]

    # Progression C1/C2 Baroque Circle of Fifths (Dm -> Gm | C7 -> Fmaj7 | Bbmaj7 -> Em7b5 | Asus4 -> A7)
    chords_C = [
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["G-3", "A#3", "D-4", "G-4"], 0x37, ["G-4", "D-4", "A#3", "G-3"]),
        (["C-4", "E-4", "G-4", "A#4"], 0x47, ["A#4", "G-4", "E-4", "C-4"]),
        (["F-4", "A-4", "C-5", "E-5"], 0x47, ["E-5", "C-5", "A-4", "F-4"]),
        (["A#3", "D-4", "F-4", "A-4"], 0x47, ["A-4", "F-4", "D-4", "A#3"]),
        (["E-4", "G-4", "A#4", "D-5"], 0x36, ["D-5", "A#4", "G-4", "E-4"]),
        (["A-3", "D-4", "E-4", "A-4"], 0x57, ["A-4", "E-4", "D-4", "A-3"]),
        (["A-3", "C#4", "E-4", "G-4"], 0x47, ["G-4", "E-4", "C#4", "A-3"]),
    ]

    # ==========================================================================
    # PATTERN 0: CYBER AWAKENING (Hook Intro & Groove Drop)
    # ==========================================================================
    write_drums_standard(pb, 0, crash_rows=(0, 32), style="intro", fill_type="snare_tom")
    write_bass_bars(
        pb, 0,
        [
            ("D-2", "D-2", "F-2", "A-2"),
            ("A#1", "A#1", "C-2", "A-1"),
            ("D-2", "D-2", "F-2", "G-2"),
            ("A#1", "C-2", "A-1", "A-1"),
        ],
        pattern_style="intro_pulse",
    )
    write_pad_chords(
        pb, 0,
        [
            (0, "D-4", "A-4", 44),
            (16, "A#3", "F-4", 44),
            (24, "C-4", "G-4", 46),
            (32, "D-4", "A-4", 48),
            (48, "A#3", "F-4", 48),
            (56, "A-3", "C#4", 50),
        ],
    )
    write_arp_and_pluck_bars(pb, 0, chords_A1, arp_vol=44, pluck_vol=48, mode="full")

    # Crystal Bell plays the signature HYPERION motif in Bars 1-3
    pb.add_phrase(
        0, 15,
        [
            (0, "D-5", 58), (3, "F-5", 52), (6, "A-5", 56), (8, "G-5", 52), (12, "F-5", 50), (14, "E-5", 48),
            (16, "D-5", 56), (19, "A#4", 50), (22, "D-5", 54), (24, "E-5", 54), (28, "C#5", 52),
            (32, "D-5", 60), (35, "F-5", 54), (38, "A-5", 58), (40, "G-5", 54), (44, "F-5", 52),
            (48, "A#5", 58), (52, "A-5", 54), (56, "G-5", 52), (60, "E-5", 54),
        ],
    )
    # Heroic Lead 1 enters at Bar 3 (row 32) with an electrifying call & pickup into Pattern 1!
    pb.add_phrase(
        0, 10,
        [
            (0, "===", None),  # Ensure clean loop entry if Lead 1 was held at end of Pat 11
            (32, "D-5", 56), (36, "F-5", 58, 4, 0x63), (40, "E-5", 56), (44, "D-5", 54),
            (48, "A#4", 56), (52, "C-5", 58), (56, "A-4", 60, 4, 0x64),
            (60, "A-4", 58), (61, "B-4", 60), (62, "C-5", 62), (63, "C#5", 64),
        ],
    )
    pb.off(0, 0, 5)
    pb.off(0, 0, 11)
    # Brass stabs on Bar 3 & 4 accents
    pb.add_phrase(
        0, 16,
        [
            (32, "D-4", 52, 0, 0x37), (38, "F-4", 48, 0, 0x37),
            (48, "A#3", 52, 0, 0x47), (56, "A-3", 56, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 1: MAIN THEME A1 (The Keygen Anthem)
    # ==========================================================================
    write_drums_standard(pb, 1, crash_rows=(0,), style="driving", fill_type="snare_tom")
    write_bass_bars(
        pb, 1,
        [
            ("D-2", "D-2", "F-2", "A-2"),
            ("A#1", "A#1", "D-2", "F-2"),
            ("G-1", "A#1", "C-2", "E-2"),
            ("A-1", "A-1", "G-1", "E-1"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 1,
        [
            (0, "D-4", "A-4", 46),
            (16, "A#3", "F-4", 46),
            (32, "G-3", "D-4", 46),
            (40, "C-4", "G-4", 48),
            (48, "A-3", "D-4", 48),
            (56, "A-3", "C#4", 50),
        ],
    )
    write_arp_and_pluck_bars(pb, 1, chords_A1, arp_vol=46, pluck_vol=48, mode="full")

    # Heroic Lead 1 (Ch 4): Iconic 4-bar D-minor Anthem
    pb.add_phrase(
        1, 10,
        [
            # Bar 5 (Dm)
            (0, "D-5", 64), (2, None, None, 4, 0x63), (4, "A-4", 58), (6, "D-5", 62),
            (8, "F-5", 64), (10, "E-5", 60), (12, "D-5", 62), (14, "C-5", 58),
            # Bar 6 (Bb)
            (16, "A#4", 64), (18, None, None, 4, 0x64), (20, "F-4", 56), (22, "A#4", 60),
            (24, "D-5", 64), (26, "F-5", 62, 3, 0x20), (28, "E-5", 60), (30, "D-5", 58),
            # Bar 7 (Gm7 -> C7)
            (32, "G-5", 64), (34, "F-5", 60), (36, "D-5", 62), (38, "A#4", 58),
            (40, "E-5", 64), (42, "F-5", 60), (44, "E-5", 62, 4, 0x63), (46, "C-5", 56),
            # Bar 8 (Asus4 -> A7)
            (48, "D-5", 64), (50, "E-5", 62), (51, "D-5", 58), (52, "C#5", 64),
            (54, None, None, 4, 0x74), (58, "A-4", 58), (60, "B-4", 60), (62, "C#5", 62),
        ],
    )
    # Harmony / Counter-Lead 2 (Ch 5): Call-and-response & 3rd harmonies
    pb.add_phrase(
        1, 11,
        [
            (0, "F-4", 46), (4, "F-4", 42), (8, "A-4", 50), (10, "G-4", 46), (12, "F-4", 48), (14, "===", None),
            (16, "D-4", 46), (22, "F-4", 46), (24, "A#4", 50), (28, "G-4", 48), (30, "===", None),
            (32, "A#4", 50), (36, "G-4", 48), (40, "G-4", 50), (44, "A#4", 50, 4, 0x63),
            (48, "A-4", 52), (52, "A-4", 52, 4, 0x63), (58, "===", None),
        ],
    )
    # Bells & Brass Stabs
    pb.add_phrase(
        1, 15,
        [
            (0, "D-6", 50), (8, "F-5", 46), (16, "A#5", 50), (24, "D-5", 46),
            (32, "G-5", 50), (40, "E-5", 50), (48, "D-5", 48), (52, "C#5", 52),
        ],
    )
    pb.add_phrase(
        1, 16,
        [
            (0, "D-4", 52, 0, 0x37), (6, "D-4", 46, 0, 0x37),
            (16, "A#3", 52, 0, 0x47), (22, "A#3", 46, 0, 0x47),
            (32, "G-3", 52, 0, 0x37), (40, "C-4", 52, 0, 0x47),
            (48, "A-3", 54, 0, 0x57), (52, "A-3", 56, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 2: MAIN THEME A2 (Twin-Lead Harmony & Lift to Chorus)
    # ==========================================================================
    write_drums_standard(pb, 2, crash_rows=(0,), style="driving", fill_type="snare_tom")
    write_bass_bars(
        pb, 2,
        [
            ("D-2", "D-2", "F-2", "A-2"),
            ("A#1", "A#1", "B-1", "G-1"),
            ("C-2", "C-2", "C#2", "A-1"),
            ("D-2", "C-2", "A#1", "C-2"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 2,
        [
            (0, "D-4", "A-4", 48),
            (16, "A#3", "F-4", 48),
            (24, "B-3", "G-4", 48),
            (32, "C-4", "G-4", 50),
            (40, "C#4", "A-4", 50),
            (48, "D-4", "A-4", 52),
            (56, "E-4", "C-5", 54),
        ],
    )
    write_arp_and_pluck_bars(pb, 2, chords_A2, arp_vol=48, pluck_vol=50, mode="full")

    # Lead 1 (Ch 4) & Lead 2 (Ch 5) in tight 3rd/6th twin harmony!
    pb.add_phrase(
        2, 10,
        [
            # Bar 9 (Dm)
            (0, "D-5", 64), (4, "E-5", 60), (6, "F-5", 62), (8, "A-5", 64, 4, 0x64),
            (12, "G-5", 60), (14, "F-5", 58),
            # Bar 10 (Bb -> G/B)
            (16, "F-5", 64), (18, "E-5", 58), (20, "D-5", 62), (22, "C-5", 58),
            (24, "D-5", 64), (26, "G-5", 62), (28, "F-5", 60), (30, "D-5", 58),
            # Bar 11 (C -> A7/C#)
            (32, "E-5", 64), (36, "G-5", 62), (38, "F-5", 60), (40, "E-5", 64),
            (42, "G-5", 62), (44, "A-5", 64, 4, 0x64), (46, "G-5", 60),
            # Bar 12 (Dm -> C/E pickup to F major Chorus!)
            (48, "F-5", 64), (50, "E-5", 60), (52, "D-5", 64, 4, 0x64),
            (56, "C-5", 60), (58, "D-5", 62), (60, "E-5", 64), (62, "G-5", 64),
        ],
    )
    pb.add_phrase(
        2, 11,
        [
            # Harmonizing a 3rd below Lead 1
            (0, "A-4", 54), (4, "C-5", 50), (6, "D-5", 52), (8, "F-5", 56, 4, 0x64),
            (12, "E-5", 50), (14, "D-5", 48),
            (16, "D-5", 54), (18, "C-5", 48), (20, "A#4", 52), (22, "A-4", 48),
            (24, "B-4", 54), (26, "D-5", 52), (28, "B-4", 50), (30, "G-4", 48),
            (32, "C-5", 54), (36, "E-5", 52), (38, "D-5", 50), (40, "C#5", 54),
            (42, "E-5", 52), (44, "F-5", 56, 4, 0x64), (46, "E-5", 50),
            (48, "D-5", 54), (50, "C-5", 50), (52, "A-4", 54, 4, 0x64),
            (56, "G-4", 52), (58, "A#4", 52), (60, "C-5", 56), (62, "E-5", 58),
        ],
    )
    pb.add_phrase(
        2, 15,
        [
            (0, "A-5", 52), (8, "D-6", 54), (16, "F-5", 50), (24, "G-5", 52),
            (32, "C-6", 54), (40, "A-5", 54), (48, "D-6", 56), (56, "C-6", 56),
        ],
    )
    pb.add_phrase(
        2, 16,
        [
            (0, "D-4", 54, 0, 0x37), (16, "A#3", 52, 0, 0x47), (24, "G-3", 54, 0, 0x47),
            (32, "C-4", 54, 0, 0x47), (40, "A-3", 56, 0, 0x47), (48, "D-4", 56, 0, 0x37),
            (56, "C-4", 58, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 3: CHORUS B1 (Relative Major Skyward Lift — F Major!)
    # ==========================================================================
    write_drums_standard(pb, 3, crash_rows=(0, 32), style="driving", fill_type="snare_tom")
    write_bass_bars(
        pb, 3,
        [
            ("F-1", "F-1", "A-1", "C-2"),
            ("E-1", "E-1", "C-2", "G-1"),
            ("D-2", "C-2", "A#1", "F-1"),
            ("G-1", "A#1", "C-2", "C-2"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 3,
        [
            (0, "F-4", "C-5", 50),
            (16, "E-4", "C-5", 50),
            (32, "D-4", "A-4", 50),
            (40, "A#3", "F-4", 50),
            (48, "G-3", "D-4", 50),
            (56, "C-4", "A#4", 52),
        ],
    )
    write_arp_and_pluck_bars(pb, 3, chords_B1, arp_vol=48, pluck_vol=50, mode="full")

    # Soaring F-Major Chorus Lead 1 (Ch 4)
    pb.add_phrase(
        3, 10,
        [
            # Bar 13 (Fmaj7)
            (0, "F-5", 64), (2, None, None, 4, 0x64), (6, "G-5", 62), (8, "A-5", 64),
            (10, "C-6", 64, 4, 0x64), (14, "A-5", 60),
            # Bar 14 (C/E -> C)
            (16, "G-5", 64), (18, None, None, 4, 0x63), (20, "E-5", 60), (22, "C-5", 58),
            (24, "G-5", 64), (26, "F-5", 60), (28, "E-5", 62, 4, 0x63), (30, "C-5", 56),
            # Bar 15 (Dm7 -> Bbmaj7)
            (32, "F-5", 64), (34, "E-5", 60), (36, "D-5", 62), (38, "C-5", 58),
            (40, "D-5", 64), (42, "F-5", 62), (44, "A-5", 64, 4, 0x64), (46, "F-5", 58),
            # Bar 16 (Gm7 -> C7)
            (48, "G-5", 64), (50, "F-5", 60), (52, "D-5", 62), (54, "A#4", 58),
            (56, "C-5", 64), (58, "D-5", 62), (60, "E-5", 64, 4, 0x64), (62, "G-5", 62),
        ],
    )
    # Counter-Lead 2 (Ch 5)
    pb.add_phrase(
        3, 11,
        [
            (0, "A-4", 52), (6, "C-5", 50), (8, "C-5", 54), (10, "F-5", 56, 4, 0x63), (14, "C-5", 50),
            (16, "C-5", 54), (20, "G-4", 48), (24, "E-5", 54), (28, "C-5", 52, 4, 0x63),
            (32, "A-4", 52), (36, "F-4", 48), (40, "A#4", 54), (44, "D-5", 56, 4, 0x63),
            (48, "A#4", 52), (52, "G-4", 48), (56, "G-4", 52), (60, "A#4", 56, 4, 0x64),
        ],
    )
    pb.add_phrase(
        3, 15,
        [
            (0, "F-5", 56), (8, "A-5", 54), (10, "C-6", 58),
            (16, "G-5", 54), (24, "E-5", 52),
            (32, "F-5", 54), (40, "D-5", 54), (44, "A-5", 56),
            (48, "G-5", 54), (56, "E-5", 56),
        ],
    )
    pb.add_phrase(
        3, 16,
        [
            (0, "F-4", 56, 0, 0x47), (6, "F-4", 48, 0, 0x47),
            (16, "C-4", 54, 0, 0x47), (32, "D-4", 54, 0, 0x37),
            (40, "A#3", 54, 0, 0x47), (48, "G-3", 54, 0, 0x37),
            (56, "C-4", 58, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 4: CHORUS B2 (Emotional Resolution & Minor Pivot: D7/F# -> Gm -> Bbm6 -> F/A -> A7)
    # ==========================================================================
    write_drums_standard(pb, 4, crash_rows=(0,), style="driving", fill_type="snare_tom")
    write_bass_bars(
        pb, 4,
        [
            ("F-1", "F-1", "A-1", "C-2"),
            ("A-1", "E-1", "F#1", "D-2"),
            ("G-1", "G-1", "A#1", "C#2"),
            ("A-1", "C-2", "A-1", "E-1"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 4,
        [
            (0, "F-4", "C-5", 50),
            (16, "A-3", "E-4", 48),
            (24, "F#3", "C-4", 52),  # D7/F#
            (32, "G-3", "D-4", 52),  # Gm7
            (40, "A#3", "C#4", 54), # Bbm6 (emotional minor iv!)
            (48, "A-3", "F-4", 52),  # F/A
            (56, "A-3", "C#4", 54), # A7 pivot back to D minor!
        ],
    )
    write_arp_and_pluck_bars(pb, 4, chords_B2, arp_vol=48, pluck_vol=50, mode="full")

    pb.add_phrase(
        4, 10,
        [
            # Bar 17 (F)
            (0, "A-5", 64), (2, None, None, 4, 0x64), (6, "G-5", 60), (8, "F-5", 64),
            (12, "C-5", 58), (14, "D-5", 60),
            # Bar 18 (Am7 -> D7/F#)
            (16, "E-5", 64), (18, None, None, 4, 0x63), (20, "C-5", 58), (22, "A-4", 56),
            (24, "F#5", 64), (26, None, None, 4, 0x74), (28, "G-5", 62), (30, "A-5", 64),
            # Bar 19 (Gm7 -> Bbm6!)
            (32, "A#5", 64), (34, "A-5", 60), (36, "G-5", 62), (38, "D-5", 58),
            (40, "G-5", 64), (42, "F-5", 62), (44, "C#5", 64, 4, 0x74), (46, "A#4", 58),
            # Bar 20 (F/A -> Asus4 -> A7)
            (48, "C-5", 62), (50, "F-5", 64), (52, "E-5", 62), (54, "D-5", 60),
            (56, "C#5", 64), (58, None, None, 4, 0x74), (62, "===", None),
        ],
    )
    pb.add_phrase(
        4, 11,
        [
            (0, "C-5", 54), (6, "A#4", 50), (8, "A-4", 54), (12, "A-4", 48),
            (16, "C-5", 52), (20, "A-4", 48), (24, "D-5", 56), (28, "D-5", 52), (30, "F#5", 56),
            (32, "D-5", 56), (36, "A#4", 52), (40, "C#5", 56), (44, "A#4", 54, 4, 0x64),
            (48, "A-4", 54), (50, "C-5", 54), (52, "B-4", 52), (56, "A-4", 56, 4, 0x64), (62, "===", None),
        ],
    )
    pb.add_phrase(
        4, 15,
        [
            (0, "A-5", 54), (8, "F-5", 52), (16, "E-5", 52), (24, "F#5", 58),
            (32, "A#5", 58), (40, "C#5", 56), (48, "F-5", 54), (56, "E-5", 56),
        ],
    )
    pb.add_phrase(
        4, 16,
        [
            (0, "F-4", 54, 0, 0x47), (16, "A-3", 52, 0, 0x37), (24, "D-4", 58, 0, 0x47),
            (32, "G-3", 56, 0, 0x37), (40, "A#3", 58, 0, 0x37), (48, "F-4", 54, 0, 0x47),
            (56, "A-3", 58, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 5: BAROQUE CHIP BREAKDOWN C1 (Circle of Fifths Sequence)
    # ==========================================================================
    write_drums_standard(pb, 5, crash_rows=(0, 32), style="breakdown", fill_type="snare_tom")
    write_bass_bars(
        pb, 5,
        [
            ("D-2", "F-2", "G-1", "A#1"),
            ("C-2", "E-2", "F-1", "A-1"),
            ("A#1", "D-2", "E-1", "G-1"),
            ("A-1", "D-2", "A-1", "C#2"),
        ],
        pattern_style="baroque_16th",
    )
    write_pad_chords(
        pb, 5,
        [
            (0, "D-4", "A-4", 40),
            (8, "G-3", "D-4", 40),
            (16, "C-4", "G-4", 40),
            (24, "F-3", "C-4", 42),
            (32, "A#3", "F-4", 44),
            (40, "E-3", "A#3", 44),
            (48, "A-3", "D-4", 46),
            (56, "A-3", "C#4", 48),
        ],
    )
    write_arp_and_pluck_bars(pb, 5, chords_C, arp_vol=50, pluck_vol=54, mode="full")

    # Lead 1 rests in Bars 21-22 while Lead 2 (Sync/FM) & Harpsi run Vivaldi/Bach sequences, then enters in Bar 23!
    pb.off(5, 0, 4)
    pb.add_phrase(
        5, 11,
        [
            # Baroque 16th-note sequential solo on Ch 5 (Inst 11 Sync/FM)
            # Bar 21 (Dm -> Gm)
            (0, "A-5", 58), (2, "F-5", 52), (4, "D-5", 56), (6, "F-5", 52),
            (8, "G-5", 58), (10, "D-5", 52), (12, "A#4", 56), (14, "D-5", 52),
            # Bar 22 (C7 -> Fmaj7)
            (16, "E-5", 58), (18, "C-5", 52), (20, "G-4", 54), (22, "C-5", 52),
            (24, "F-5", 58), (26, "C-5", 52), (28, "A-4", 56), (30, "C-5", 52),
            # Bar 23 (Bbmaj7 -> Em7b5)
            (32, "D-5", 58), (34, "A#4", 52), (36, "F-4", 54), (38, "A#4", 52),
            (40, "G-5", 58), (42, "E-5", 54), (44, "A#4", 56), (46, "D-5", 54),
            # Bar 24 (Asus4 -> A7)
            (48, "D-5", 60), (50, "E-5", 56), (52, "F-5", 58), (54, "D-5", 54),
            (56, "C#5", 60), (58, "E-5", 58), (60, "A-5", 62, 4, 0x64),
        ],
    )
    pb.add_phrase(
        5, 10,
        [
            # Lead 1 joins in Bar 23-24 with soaring counter-line
            (32, "F-5", 58), (36, "D-5", 56), (40, "A#5", 62, 4, 0x63), (44, "G-5", 58),
            (48, "A-5", 62), (52, "G-5", 58), (56, "E-5", 64, 4, 0x64),
        ],
    )
    pb.add_phrase(
        5, 15,
        [
            (0, "A-5", 48), (8, "G-5", 48), (16, "E-5", 48), (24, "F-5", 48),
            (32, "D-5", 50), (40, "G-5", 50), (48, "A-5", 52), (56, "C#6", 54),
        ],
    )
    pb.off(5, 0, 11)

    # ==========================================================================
    # PATTERN 6: VIRTUOSO DUAL SOLO C2 (High-Speed Counterpoint)
    # ==========================================================================
    write_drums_standard(pb, 6, crash_rows=(0, 32), style="driving", fill_type="snare_tom")
    write_bass_bars(
        pb, 6,
        [
            ("D-2", "D-2", "F#1", "A-1"),
            ("G-1", "A#1", "C-2", "E-2"),
            ("F-1", "A-1", "A#1", "D-2"),
            ("E-1", "G-1", "A-1", "C#2"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 6,
        [
            (0, "D-4", "A-4", 48),
            (8, "F#3", "D-4", 50),
            (16, "G-3", "D-4", 50),
            (24, "C-4", "A#4", 50),
            (32, "F-4", "C-5", 50),
            (40, "A#3", "F-4", 50),
            (48, "E-3", "A#3", 50),
            (56, "A-3", "C#4", 54),
        ],
    )
    write_arp_and_pluck_bars(pb, 6, chords_C, arp_vol=48, pluck_vol=50, mode="full")

    # Dazzling 16th-note call-and-response & harmonized runs between Lead 1 & Lead 2!
    pb.add_phrase(
        6, 10,
        [
            # Bar 25 (Dm -> D7/F#)
            (0, "D-5", 64), (1, "E-5", 58), (2, "F-5", 62), (3, "G-5", 58),
            (4, "A-5", 64), (6, "F-5", 58), (8, "F#5", 64), (10, "A-5", 62),
            (12, "C-6", 64, 4, 0x64), (14, "A-5", 60),
            # Bar 26 (Gm -> C7)
            (16, "A#5", 64), (18, "A-5", 60), (20, "G-5", 62), (22, "F-5", 58),
            (24, "E-5", 64), (25, "F-5", 58), (26, "G-5", 62), (27, "A-5", 60),
            (28, "A#5", 64), (30, "G-5", 60),
            # Bar 27 (Fmaj7 -> Bbmaj7)
            (32, "A-5", 64), (34, "G-5", 60), (36, "F-5", 62), (38, "E-5", 58),
            (40, "F-5", 64), (42, "D-5", 60), (44, "A#4", 62), (46, "D-5", 60),
            # Bar 28 (Em7b5 -> A7)
            (48, "G-5", 64), (49, "F-5", 58), (50, "E-5", 62), (51, "D-5", 58),
            (52, "C#5", 64), (53, "D-5", 58), (54, "E-5", 62), (55, "G-5", 60),
            (56, "A-5", 64, 4, 0x74), (62, "===", None),
        ],
    )
    pb.add_phrase(
        6, 11,
        [
            # Harmonizing a 3rd/6th below every run!
            (0, "F-4", 52), (1, "G-4", 48), (2, "A-4", 50), (3, "A#4", 48),
            (4, "C-5", 54), (6, "A-4", 48), (8, "D-5", 56), (10, "C-5", 52),
            (12, "F#5", 56, 4, 0x64), (14, "D-5", 50),
            (16, "D-5", 56), (18, "C-5", 50), (20, "A#4", 52), (22, "A-4", 48),
            (24, "C-5", 54), (25, "D-5", 48), (26, "E-5", 52), (27, "F-5", 50),
            (28, "G-5", 56), (30, "E-5", 50),
            (32, "C-5", 56), (34, "A#4", 50), (36, "A-4", 52), (38, "G-4", 48),
            (40, "D-5", 54), (42, "A#4", 50), (44, "F-4", 50), (46, "A#4", 50),
            (48, "A#4", 54), (49, "A-4", 48), (50, "G-4", 50), (51, "F-4", 48),
            (52, "E-4", 54), (53, "F-4", 48), (54, "G-4", 50), (55, "A#4", 50),
            (56, "C#5", 58, 4, 0x74), (62, "===", None),
        ],
    )
    pb.add_phrase(
        6, 15,
        [
            (0, "D-6", 54), (8, "F#5", 54), (16, "A#5", 54), (24, "E-5", 54),
            (32, "A-5", 56), (40, "F-5", 54), (48, "G-5", 54), (56, "A-5", 58),
        ],
    )
    pb.add_phrase(
        6, 16,
        [
            (0, "D-4", 54, 0, 0x37), (8, "D-4", 56, 0, 0x47),
            (16, "G-3", 54, 0, 0x37), (24, "C-4", 54, 0, 0x47),
            (32, "F-4", 54, 0, 0x47), (40, "A#3", 54, 0, 0x47),
            (48, "E-4", 54, 0, 0x36), (56, "A-3", 58, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 7: CYBER BRIDGE D1 (Half-Time Atmospheric Wonder: Bbmaj7 | C6 | Dm9 | Bm7b5 -> Bb7 -> A7)
    # ==========================================================================
    write_drums_standard(pb, 7, crash_rows=(0,), style="halftime", fill_type="snare_tom")
    write_bass_bars(
        pb, 7,
        [
            ("A#1", "A#1", "F-1", "A#1"),
            ("C-2", "C-2", "G-1", "C-2"),
            ("D-2", "D-2", "A-1", "D-2"),
            ("B-1", "B-1", "A#1", "A-1"),
        ],
        pattern_style="halftime",
    )
    write_pad_chords(
        pb, 7,
        [
            (0, "A#3", "A-4", 52),
            (16, "C-4", "A-4", 52),
            (32, "D-4", "E-5", 52),
            (48, "B-3", "A-4", 52),
            (56, "A#3", "G#4", 54),
            (60, "A-3", "G-4", 56),
        ],
    )
    chords_D1 = [
        (["A#3", "D-4", "F-4", "A-4"], 0x47, ["A-4", "F-4", "D-4", "A#3"]),
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["C-4", "E-4", "G-4", "A-4"], 0x47, ["A-4", "G-4", "E-4", "C-4"]),
        (["E-4", "G-4", "C-5", "E-5"], 0x38, ["E-5", "C-5", "G-4", "E-4"]),
        (["D-4", "F-4", "A-4", "E-5"], 0x37, ["E-5", "A-4", "F-4", "D-4"]),
        (["F-4", "A-4", "C-5", "E-5"], 0x47, ["E-5", "C-5", "A-4", "F-4"]),
        (["B-3", "D-4", "F-4", "A-4"], 0x36, ["A-4", "F-4", "D-4", "B-3"]),
        (["A#3", "D-4", "F-4", "G#4"], 0x46, ["G-4", "E-4", "C#4", "A-3"]),
    ]
    write_arp_and_pluck_bars(pb, 7, chords_D1, arp_vol=42, pluck_vol=48, mode="sparse_pluck")

    # Singing, expressive lyrical solo on Lead 1 with portamento & lush bell answers
    pb.add_phrase(
        7, 10,
        [
            (0, "F-5", 60), (4, "A-5", 64, 3, 0x18), (6, None, None, 4, 0x64),
            (12, "G-5", 58), (14, "F-5", 56),
            (16, "E-5", 62), (20, "G-5", 64, 3, 0x18), (22, None, None, 4, 0x64),
            (28, "F-5", 58), (30, "E-5", 56),
            (32, "D-5", 60), (36, "A-5", 64, 3, 0x24), (38, None, None, 4, 0x64),
            (44, "G-5", 60), (46, "F-5", 58),
            (48, "F-5", 62), (52, "D-5", 58), (56, "E-5", 62), (60, "C#5", 64, 4, 0x74),
        ],
    )
    pb.add_phrase(
        7, 11,
        [
            (0, "===", None),
            (8, "D-5", 48), (12, "C-5", 46),
            (24, "E-5", 48), (28, "D-5", 46),
            (40, "F-5", 50), (44, "E-5", 48),
            (48, "D-5", 50), (56, "G#4", 52), (60, "A-4", 54, 4, 0x64),
        ],
    )
    pb.add_phrase(
        7, 15,
        [
            (0, "A-5", 56), (6, "F-5", 50), (12, "D-6", 54),
            (16, "G-5", 56), (22, "E-5", 50), (28, "C-6", 54),
            (32, "A-5", 56), (38, "E-6", 56), (44, "C-6", 52),
            (48, "F-5", 54), (56, "G#5", 54), (60, "A-5", 58),
        ],
    )
    pb.off(7, 0, 11)

    # ==========================================================================
    # PATTERN 8: ACCELERATOR BUILDUP D2 (Riser & 32nd-Note Snare Roll into Climax!)
    # ==========================================================================
    write_drums_standard(pb, 8, crash_rows=(0, 32), style="driving", fill_type="buildup_roll")
    write_bass_bars(
        pb, 8,
        [
            ("G-1", "G-1", "G-1", "A-1"),
            ("A-1", "A-1", "A-1", "B-1"),
            ("A#1", "A#1", "B-1", "B-1"),
            ("A-1", "A-1", "A-1", "A-1"),
        ],
        pattern_style="octave_16th",
    )
    # Cut bass cleanly on row 63 for the 1-row dramatic drop silence!
    pb.off(8, 63, 3)

    write_pad_chords(
        pb, 8,
        [
            (0, "G-3", "D-4", 48),
            (16, "A-3", "E-4", 50),
            (32, "A#3", "F-4", 52),
            (40, "B-3", "F-4", 54),
            (48, "A-3", "D-4", 56),
            (56, "A-3", "C#4", 60),
            (63, "===", "===", 0),
        ],
    )
    chords_D2 = [
        (["G-3", "A#3", "D-4", "G-4"], 0x37, ["D-4", "A#3", "G-3", "D-4"]),
        (["G-4", "A#4", "D-5", "G-5"], 0x37, ["G-4", "D-4", "A#3", "G-3"]),
        (["A-3", "C#4", "E-4", "A-4"], 0x47, ["E-4", "C#4", "A-3", "E-4"]),
        (["A-4", "C#5", "E-5", "A-5"], 0x47, ["A-4", "E-4", "C#4", "A-3"]),
        (["A#3", "D-4", "F-4", "A#4"], 0x47, ["F-4", "D-4", "A#3", "F-4"]),
        (["B-3", "D-4", "F-4", "G#4"], 0x36, ["G#4", "F-4", "D-4", "B-3"]),
        (["A-3", "D-4", "E-4", "A-4"], 0x57, ["A-4", "E-4", "D-4", "A-3"]),
        (["A-4", "C#5", "E-5", "A-5"], 0x47, ["C#5", "A-4", "E-4", "C#4"]),
    ]
    write_arp_and_pluck_bars(pb, 8, chords_D2, arp_vol=50, pluck_vol=52, mode="full")
    pb.off(8, 63, 6)
    pb.off(8, 63, 7)

    # Climbing tension motif on Lead 1 & Lead 2
    pb.add_phrase(
        8, 10,
        [
            (0, "A#4", 58), (4, "D-5", 60), (8, "G-5", 62, 4, 0x63), (12, "F-5", 58),
            (16, "C#5", 60), (20, "E-5", 62), (24, "A-5", 64, 4, 0x64), (28, "G-5", 60),
            (32, "D-5", 62), (36, "F-5", 64), (40, "G#5", 64, 4, 0x74), (44, "F-5", 62),
            (48, "A-5", 64), (50, "E-5", 60), (52, "F-5", 62), (54, "G-5", 62),
            (56, "A-5", 64), (58, "A#5", 64), (60, "B-5", 64), (62, "C#6", 64),
            (63, "===", None),
        ],
    )
    pb.add_phrase(
        8, 11,
        [
            (0, "G-4", 50), (4, "A#4", 52), (8, "D-5", 54, 4, 0x63), (12, "D-5", 50),
            (16, "A-4", 52), (20, "C#5", 54), (24, "E-5", 56, 4, 0x64), (28, "E-5", 52),
            (32, "A#4", 54), (36, "D-5", 56), (40, "D-5", 58, 4, 0x74), (44, "D-5", 54),
            (48, "E-5", 58), (52, "D-5", 56), (56, "C#5", 60), (58, "D-5", 60),
            (60, "E-5", 62), (62, "G-5", 64), (63, "===", None),
        ],
    )
    pb.add_phrase(
        8, 15,
        [
            (0, "G-5", 52), (16, "A-5", 54), (32, "A#5", 56), (40, "B-5", 58),
            (48, "A-5", 60), (56, "C#6", 62), (63, "===", None),
        ],
    )
    # Ch 11 Pitch Riser in Bar 35-36 (rows 32..62) using Inst 10/16 + 1xx portamento up!
    pb.set(8, 32, 11, note="A-3", inst=11, vol=v(36), fx=1, param=0x04)
    for r in range(33, 63):
        vel = 36 + (r - 32) * 28 // 30
        pb.set(8, r, 11, vol=v(vel), fx=1, param=0x06 if r < 48 else 0x0A)
    pb.off(8, 63, 11)

    # ==========================================================================
    # PATTERN 9: GRAND CLIMAX A3 (Maximum Keygen Overdrive Part 1)
    # ==========================================================================
    write_drums_standard(pb, 9, crash_rows=(0, 32), style="climax", fill_type="snare_tom")
    write_bass_bars(
        pb, 9,
        [
            ("D-2", "D-2", "F-2", "A-2"),
            ("A#1", "A#1", "D-2", "F-2"),
            ("G-1", "A#1", "C-2", "E-2"),
            ("A-1", "A-1", "G-1", "C#2"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 9,
        [
            (0, "D-4", "A-4", 52),
            (16, "A#3", "F-4", 52),
            (32, "G-3", "D-4", 52),
            (40, "C-4", "G-4", 52),
            (48, "A-3", "D-4", 54),
            (56, "A-3", "C#4", 56),
        ],
    )
    write_arp_and_pluck_bars(pb, 9, chords_A1, arp_vol=50, pluck_vol=52, mode="full")

    # Climax Lead 1 (Ch 4) with upper-octave heroic embellishments!
    pb.add_phrase(
        9, 10,
        [
            # Bar 37 (Dm)
            (0, "D-6", 64), (2, "A-5", 60), (4, "F-5", 62), (6, "D-5", 60),
            (8, "F-5", 64), (10, "G-5", 62), (12, "A-5", 64, 4, 0x64), (14, "F-5", 60),
            # Bar 38 (Bb)
            (16, "A#5", 64), (18, None, None, 4, 0x64), (20, "F-5", 60), (22, "D-5", 58),
            (24, "F-5", 64), (26, "G-5", 62), (28, "A-5", 64, 4, 0x64), (30, "F-5", 60),
            # Bar 39 (Gm7 -> C7)
            (32, "A#5", 64), (34, "A-5", 62), (36, "G-5", 64), (38, "F-5", 60),
            (40, "E-5", 64), (42, "G-5", 62), (44, "C-6", 64, 4, 0x64), (46, "A#5", 62),
            # Bar 40 (Asus4 -> A7)
            (48, "A-5", 64), (50, "G-5", 62), (52, "F-5", 64), (54, "E-5", 62),
            (56, "C#5", 64), (58, "E-5", 62), (60, "A-5", 64, 4, 0x74),
        ],
    )
    # Climax Harmony Lead 2 (Ch 5) in locked 3rds/6ths
    pb.add_phrase(
        9, 11,
        [
            (0, "F-5", 56), (2, "F-5", 52), (4, "D-5", 54), (6, "A-4", 52),
            (8, "D-5", 56), (10, "E-5", 54), (12, "F-5", 58, 4, 0x64), (14, "D-5", 52),
            (16, "D-5", 56), (18, None, None, 4, 0x64), (20, "D-5", 52), (22, "A#4", 50),
            (24, "D-5", 56), (26, "E-5", 54), (28, "F-5", 58, 4, 0x64), (30, "D-5", 52),
            (32, "D-5", 56), (34, "C-5", 54), (36, "A#4", 56), (38, "D-5", 52),
            (40, "C-5", 56), (42, "E-5", 54), (44, "G-5", 58, 4, 0x64), (46, "E-5", 54),
            (48, "F-5", 56), (50, "E-5", 54), (52, "D-5", 56), (54, "C#5", 54),
            (56, "A-4", 56), (58, "C#5", 54), (60, "E-5", 58, 4, 0x74),
        ],
    )
    pb.add_phrase(
        9, 15,
        [
            (0, "D-6", 58), (8, "F-5", 54), (12, "A-5", 56),
            (16, "A#5", 58), (24, "F-5", 54), (28, "A-5", 56),
            (32, "G-5", 56), (40, "C-6", 58),
            (48, "A-5", 58), (56, "C#6", 58),
        ],
    )
    pb.add_phrase(
        9, 16,
        [
            (0, "D-4", 58, 0, 0x37), (6, "D-4", 52, 0, 0x37), (12, "F-4", 54, 0, 0x37),
            (16, "A#3", 58, 0, 0x47), (22, "A#3", 52, 0, 0x47), (28, "D-4", 54, 0, 0x37),
            (32, "G-3", 58, 0, 0x37), (40, "C-4", 58, 0, 0x47),
            (48, "A-3", 58, 0, 0x57), (56, "A-3", 60, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 10: GRAND CLIMAX B3 (Triumphant Finale: Bbmaj7 | C -> A7/C# | Dm -> Gm7 | Dm/A -> A7 -> Dm)
    # ==========================================================================
    write_drums_standard(pb, 10, crash_rows=(0, 32), style="climax", fill_type="snare_tom")
    write_bass_bars(
        pb, 10,
        [
            ("A#1", "A#1", "D-2", "F-2"),
            ("C-2", "C-2", "C#2", "A-1"),
            ("D-2", "C-2", "G-1", "A#1"),
            ("A-1", "A-1", "A-1", "D-2"),
        ],
        pattern_style="octave_16th",
    )
    write_pad_chords(
        pb, 10,
        [
            (0, "A#3", "F-4", 54),
            (16, "C-4", "G-4", 54),
            (24, "C#4", "A-4", 56),
            (32, "D-4", "A-4", 56),
            (40, "G-3", "D-4", 54),
            (48, "A-3", "F-4", 56),
            (56, "A-3", "C#4", 58),
        ],
    )
    chords_B3 = [
        (["A#3", "D-4", "F-4", "A-4"], 0x47, ["A-4", "F-4", "D-4", "A#3"]),
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["C-4", "E-4", "G-4", "C-5"], 0x47, ["G-4", "E-4", "C-4", "G-3"]),
        (["C#4", "E-4", "G-4", "A-4"], 0x36, ["A-4", "G-4", "E-4", "C#4"]),
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["G-3", "A#3", "D-4", "G-4"], 0x37, ["G-4", "D-4", "A#3", "G-3"]),
        (["A-3", "D-4", "F-4", "A-4"], 0x57, ["A-4", "F-4", "D-4", "A-3"]),
        (["A-3", "C#4", "E-4", "G-4"], 0x47, ["G-4", "E-4", "C#4", "A-3"]),
    ]
    write_arp_and_pluck_bars(pb, 10, chords_B3, arp_vol=50, pluck_vol=52, mode="full")

    pb.add_phrase(
        10, 10,
        [
            # Bar 41 (Bbmaj7)
            (0, "F-5", 64), (4, "G-5", 62), (6, "A-5", 64), (8, "A#5", 64, 4, 0x64),
            (12, "A-5", 62), (14, "G-5", 60),
            # Bar 42 (C -> A7/C#)
            (16, "G-5", 64), (18, "F-5", 60), (20, "E-5", 62), (22, "G-5", 62),
            (24, "A-5", 64), (26, "B-5", 62), (28, "C#6", 64, 4, 0x64), (30, "A-5", 62),
            # Bar 43 (Dm -> Gm7)
            (32, "D-6", 64), (34, "A-5", 62), (36, "F-5", 62), (38, "D-5", 60),
            (40, "A#5", 64), (42, "A-5", 62), (44, "G-5", 64, 4, 0x64), (46, "F-5", 60),
            # Bar 44 (Dm/A -> A7 -> Dm)
            (48, "F-5", 64), (50, "E-5", 62), (52, "D-5", 62), (54, "F-5", 62),
            (56, "E-5", 64), (58, "C#5", 62), (60, "D-5", 64, 4, 0x64),
        ],
    )
    pb.add_phrase(
        10, 11,
        [
            (0, "D-5", 56), (4, "E-5", 54), (6, "F-5", 56), (8, "F-5", 58, 4, 0x64),
            (12, "F-5", 54), (14, "E-5", 52),
            (16, "E-5", 56), (18, "D-5", 52), (20, "C-5", 54), (22, "E-5", 54),
            (24, "E-5", 56), (26, "G-5", 54), (28, "A-5", 58, 4, 0x64), (30, "E-5", 54),
            (32, "F-5", 58), (34, "F-5", 54), (36, "D-5", 54), (38, "A-4", 52),
            (40, "D-5", 56), (42, "C-5", 54), (44, "A#4", 56, 4, 0x64), (46, "D-5", 52),
            (48, "D-5", 56), (50, "C-5", 54), (52, "A-4", 54), (54, "D-5", 54),
            (56, "C#5", 56), (58, "A-4", 54), (60, "A-4", 58, 4, 0x64),
        ],
    )
    pb.add_phrase(
        10, 15,
        [
            (0, "A#5", 56), (8, "D-6", 58), (16, "G-5", 56), (24, "A-5", 58),
            (32, "D-6", 60), (40, "A#5", 56), (48, "A-5", 56), (56, "E-5", 56), (60, "D-6", 58),
        ],
    )
    pb.add_phrase(
        10, 16,
        [
            (0, "A#3", 58, 0, 0x47), (16, "C-4", 58, 0, 0x47), (24, "A-3", 58, 0, 0x47),
            (32, "D-4", 60, 0, 0x37), (40, "G-3", 58, 0, 0x37),
            (48, "D-4", 58, 0, 0x37), (56, "A-3", 60, 0, 0x47),
        ],
    )

    # ==========================================================================
    # PATTERN 11: OUTRO CODA & SEAMLESS LOOP TURNAROUND (Dm | Bb -> Gm7 | Em7b5 -> Asus4 | A7 -> Pat 0!)
    # ==========================================================================
    write_drums_standard(pb, 11, crash_rows=(0,), style="driving", fill_type="turnaround")
    write_bass_bars(
        pb, 11,
        [
            ("D-2", "D-2", "F-2", "A-2"),
            ("A#1", "A#1", "G-1", "A#1"),
            ("E-1", "G-1", "A-1", "D-2"),
            ("A-1", "A-1", "B-1", "C#2"),  # Rising bass pickup A-1 -> B-1 -> C#2 into D-2 on Pat 0 Row 0!
        ],
        pattern_style="octave_16th",
    )
    # Explicit bass pickup in last 4 rows (60..63) of Pattern 11:
    pb.set(11, 60, 3, note="A-1", inst=8, vol=v(60))
    pb.set(11, 61, 3, note="B-1", inst=9, vol=v(58))
    pb.set(11, 62, 3, note="C-2", inst=9, vol=v(60))
    pb.set(11, 63, 3, note="C#2", inst=8, vol=v(64))

    write_pad_chords(
        pb, 11,
        [
            (0, "D-4", "A-4", 50),
            (16, "A#3", "F-4", 48),
            (24, "G-3", "D-4", 48),
            (32, "E-3", "A#3", 46),
            (40, "A-3", "D-4", 46),
            (48, "A-3", "C#4", 46),  # Resolves smoothly to D-4 / A-4 at Pat 0 Row 0 (vol 44)!
        ],
    )
    chords_Coda = [
        (["D-4", "F-4", "A-4", "D-5"], 0x37, ["A-4", "F-4", "D-4", "A-3"]),
        (["D-4", "A-4", "D-5", "F-5"], 0x37, ["D-5", "A-4", "F-4", "D-4"]),
        (["A#3", "D-4", "F-4", "A#4"], 0x47, ["F-4", "D-4", "A#3", "F-3"]),
        (["G-3", "A#3", "D-4", "G-4"], 0x37, ["D-4", "A#3", "G-3", "D-4"]),
        (["E-4", "G-4", "A#4", "D-5"], 0x36, ["A#4", "G-4", "E-4", "A#3"]),
        (["A-3", "D-4", "E-4", "A-4"], 0x57, ["E-4", "D-4", "A-3", "E-4"]),
        (["A-3", "C#4", "E-4", "G-4"], 0x47, ["G-4", "E-4", "C#4", "A-3"]),
        (["A-3", "C#4", "E-4", "A-4"], 0x47, ["A-4", "E-4", "C#4", "A-3"]),
    ]
    write_arp_and_pluck_bars(pb, 11, chords_Coda, arp_vol=46, pluck_vol=48, mode="full")

    # Reprise of the HYPERION Bell & Lead Hook, tapering gracefully into the pickup to Pat 0 Row 0!
    pb.add_phrase(
        11, 10,
        [
            (0, "D-5", 62), (3, "F-5", 58), (6, "A-5", 62, 4, 0x64), (8, "G-5", 58), (12, "F-5", 56), (14, "E-5", 54),
            (16, "D-5", 60), (20, "A#4", 56), (24, "G-5", 60, 4, 0x63), (28, "F-5", 56),
            (32, "E-5", 58), (36, "G-5", 58), (40, "F-5", 56), (44, "D-5", 54),
            (48, "C#5", 58, 4, 0x64), (54, "===", None),
        ],
    )
    pb.add_phrase(
        11, 11,
        [
            (0, "A-4", 50), (6, "D-5", 52, 4, 0x64), (8, "C-5", 48), (12, "A-4", 46),
            (16, "F-4", 48), (24, "A#4", 50, 4, 0x63), (28, "A-4", 46),
            (32, "A#4", 48), (40, "A-4", 48), (48, "A-4", 50, 4, 0x63), (54, "===", None),
        ],
    )
    # Crystal Bell plays the exact turnaround pickup (rows 56..63: A-4 -> B-4 -> C-5 -> C#5) -> D-5 on Pat 0 Row 0!
    pb.add_phrase(
        11, 15,
        [
            (0, "D-5", 56), (3, "F-5", 50), (6, "A-5", 54), (8, "G-5", 50), (12, "F-5", 48),
            (16, "D-5", 54), (24, "G-5", 52), (32, "A#5", 52), (40, "A-5", 52),
            (48, "G-5", 50), (52, "E-5", 50),
            (56, "A-4", 52), (58, "B-4", 54), (60, "C-5", 56), (62, "C#5", 58),
        ],
    )
    pb.add_phrase(
        11, 16,
        [
            (0, "D-4", 54, 0, 0x37), (16, "A#3", 52, 0, 0x47), (24, "G-3", 52, 0, 0x37),
            (32, "E-4", 50, 0, 0x36), (40, "A-3", 50, 0, 0x57), (48, "A-3", 52, 0, 0x47),
        ],
    )

    return pb


def apply_to_ft2(pb: PatternBuilder):
    call("module_new", channels=12, name="HYPERION KEYGEN")
    for ins in build_all_instruments():
        idx = ins["instrument"]
        b64 = base64.b64encode(ins["pcm"]).decode("ascii")
        call("instrument_set", instrument=idx, name=ins["name"])
        call("sample_create_from_pcm", instrument=idx, sample=0, pcm=b64, encoding="int16", name=ins["name"])
        call(
            "sample_set",
            instrument=idx,
            sample=0,
            name=ins["name"],
            volume=ins["volume"],
            panning=ins["panning"],
            finetune=ins["finetune"],
            relative_note=ins["relative_note"],
            loop_start=ins["loop_start"],
            loop_length=ins["loop_length"],
            flags=ins["flags"],
        )

    call("song_set", name="HYPERION KEYGEN", bpm=140, speed=6, length=pb.num_patterns, loop_start=0)
    for pat in range(pb.num_patterns):
        call("order_set", position=pat, pattern=pat)
        call("pattern_clear", pattern=pat)
        call("pattern_set_length", pattern=pat, rows=pb.rows)
        for (row, ch), cell in sorted(pb.grid[pat].items()):
            call("pattern_set_cell", **cell)


if __name__ == "__main__":
    pb = build_song()
    total_cells = sum(len(g) for g in pb.grid)
    print(f"Built 12-pattern song with {total_cells} populated tracker cells. Pushing to FT2...")
    apply_to_ft2(pb)
    call("module_save", path="/workspace/submission/tune.xm", format="xm")
    res = call("module_render", path="/workspace/submission/preview.wav", rate=44100, bits=16)
    print("Saved /workspace/submission/tune.xm and rendered /workspace/submission/preview.wav:", res)
