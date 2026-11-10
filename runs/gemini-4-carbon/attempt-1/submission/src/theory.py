"""Tracker music theory, note encoding, and pattern-building helpers for FT2 XM."""

NOTE_MAP = {
    "C": 0, "C#": 1, "DB": 1,
    "D": 2, "D#": 3, "EB": 3,
    "E": 4, "E#": 5, "FB": 4,
    "F": 5, "F#": 6, "GB": 6,
    "G": 7, "G#": 8, "AB": 8,
    "A": 9, "A#": 10, "BB": 10,
    "B": 11, "CB": 11,
}

OFF = 97

def n(note_str):
    """Convert note string like 'F#4', 'C-2', 'E#5', 'OFF' to FT2 note integer 1..97."""
    if note_str is None:
        return None
    if isinstance(note_str, int):
        return note_str
    s = note_str.strip().upper()
    if s in ("OFF", "===", "97"):
        return OFF
    s = s.replace("-", "")
    pitch = s[:-1]
    octv = int(s[-1])
    if pitch == "E#":
        # E#4 is enharmonic to F4 (same octave number in scientific pitch: E4 -> E#4 = F4)
        semi = 5
    elif pitch == "B#":
        semi = 0
        octv += 1
    elif pitch == "CB":
        semi = 11
        octv -= 1
    else:
        semi = NOTE_MAP[pitch]
    val = octv * 12 + semi + 1  # C-0 = 1, C-4 = 49, A-4 = 58
    assert 1 <= val <= 96, f"Note out of XM range: {note_str} -> {val}"
    return val

def v(vol_0_64):
    """Convert 0..64 volume to XM volume column byte 0x10..0x50."""
    if vol_0_64 is None:
        return None
    val = max(0, min(64, int(round(vol_0_64))))
    return 0x10 + val

def arp_xy(semi_high, semi_mid):
    """In FT2 at speed 6, 0xy plays tick0=0, tick1=+y, tick2=+x.
    For ascending root -> 3rd -> 5th on ticks 0,1,2, pass y=3rd, x=5th -> (5th << 4) | 3rd!
    """
    assert 0 <= semi_high <= 15 and 0 <= semi_mid <= 15
    return (semi_high << 4) | semi_mid

class Pattern:
    def __init__(self, pat_idx, rows=64, channels=12):
        self.pat_idx = pat_idx
        self.rows = rows
        self.channels = channels
        self.cells = {}  # (row, ch) -> dict

    def set(self, row, ch, note=None, inst=None, vol=None, fx=None, param=None, raw_vol=None):
        if not (0 <= row < self.rows):
            return
        assert 0 <= ch < self.channels
        cell = self.cells.get((row, ch), {})
        if note is not None:
            cell["note"] = n(note)
        if inst is not None:
            cell["instrument"] = int(inst)
        if raw_vol is not None:
            cell["volume"] = int(raw_vol)
        elif vol is not None:
            cell["volume"] = v(vol)
        if fx is not None:
            cell["effect"] = int(fx)
            cell["effect_param"] = int(param or 0)
        elif param is not None:
            cell["effect_param"] = int(param)
        self.cells[(row, ch)] = cell

    def off(self, row, ch):
        self.set(row, ch, note=OFF)

    def note_len(self, row, ch, note_str, inst, vol=64, length=4, vib=None, slide_down=None, cut_tick=None):
        """Place a phrased note with optional delayed vibrato, tail slide, and clean key-off."""
        self.set(row, ch, note=note_str, inst=inst, vol=vol)
        if vib is not None and length >= 3:
            for r in range(row + 1, min(self.rows, row + length)):
                self.set(r, ch, fx=0x4, param=vib)
        if slide_down is not None and length >= 2:
            r_last = min(self.rows - 1, row + length - 1)
            self.set(r_last, ch, fx=0xA, param=slide_down)
        if cut_tick is not None and row + length - 1 < self.rows:
            self.set(row + length - 1, ch, fx=0xE, param=0xC0 | (cut_tick & 0x0F))
        elif row + length < self.rows:
            # Only place key-off if next cell doesn't already trigger a note (caller can overwrite)
            if (row + length, ch) not in self.cells:
                self.off(row + length, ch)

    def apply_echo(self, src_ch, dst_ch, echo_inst=11, delay_rows=3, vol_scale=0.38, max_row=64):
        """Generate tracker dotted-16th stereo echo on dst_ch where dst_ch is free."""
        for r in range(0, max_row - delay_rows):
            src = self.cells.get((r, src_ch))
            if not src:
                continue
            dst_r = r + delay_rows
            if (dst_r, dst_ch) in self.cells:
                continue
            nt = src.get("note")
            if nt == OFF:
                self.off(dst_r, dst_ch)
            elif nt is not None and 1 <= nt <= 96:
                src_v = (src.get("volume", 0x50) - 0x10) if src.get("volume", 0) >= 0x10 else 56
                echo_v = max(10, int(round(src_v * vol_scale)))
                self.set(dst_r, dst_ch, note=nt, inst=echo_inst, vol=echo_v)

    def to_ft2_ops(self):
        ops = [
            {"name": "pattern_set_length", "arguments": {"pattern": self.pat_idx, "rows": self.rows}},
            {"name": "pattern_clear", "arguments": {"pattern": self.pat_idx}},
        ]
        for (row, ch), cell in sorted(self.cells.items()):
            args = {"pattern": self.pat_idx, "row": row, "channel": ch}
            args.update(cell)
            ops.append({"name": "pattern_set_cell", "arguments": args})
        return ops

if __name__ == "__main__":
    assert n("C-4") == 49
    assert n("A-4") == 58
    assert n("F#2") == 31
    assert n("E#5") == n("F-5")
    print("theory.py self-test OK! F#2=", n("F#2"), "E#5=", n("E#5"), "C#6=", n("C#6"))
