"""
Canonical XM 1.04 writer + FT2 verification/save/render pipeline.
Every module written here is loaded into FT2 via `ft2 call module_load`,
re-saved via `ft2 call module_save`, and rendered via `ft2 call module_render`.
"""
import struct
import subprocess
import json
import numpy as np

NOTE_NAMES = {
    "C-": 0, "C#": 1, "Db": 1,
    "D-": 2, "D#": 3, "Eb": 3,
    "E-": 4, "E#": 5, "Fb": 4,
    "F-": 5, "F#": 6, "Gb": 6,
    "G-": 7, "G#": 8, "Ab": 8,
    "A-": 9, "A#": 10, "Bb": 10,
    "B-": 11, "Cb": 11,
}


def parse_note(note) -> int:
    """Convert note string ('C-4' -> 49, 'F#2' -> 31, '===' / 'off' -> 97, None/''/'...' -> 0) or int."""
    if note is None or note == "" or note == "...":
        return 0
    if isinstance(note, int):
        return note
    s = note.strip()
    if s.lower() in ("off", "===", "^^"):
        return 97
    if len(s) == 2 and s[0] in "ABCDEFG" and s[1].isdigit():
        prefix = s[0] + "-"
        octv = int(s[1])
    elif len(s) == 3:
        prefix = s[:2]
        octv = int(s[2])
    else:
        raise ValueError(f"Cannot parse note: {note!r}")
    semi = NOTE_NAMES[prefix]
    val = octv * 12 + semi + 1  # C-0 = 1, C-4 = 49
    if not (1 <= val <= 96):
        raise ValueError(f"Note out of XM range 1..96: {note!r} -> {val}")
    return val


def vol_byte(vol) -> int:
    """
    Convert volume specification:
      None -> 0x00 (empty)
      int 0..64 -> 0x10 + vol (standard set volume)
      tuple ('raw', byte) -> raw XM volume column byte (e.g. volume slide, vibrato, pan)
    """
    if vol is None:
        return 0
    if isinstance(vol, tuple) and vol[0] == "raw":
        return int(vol[1]) & 0xFF
    v = max(0, min(64, int(vol)))
    return 0x10 + v


class Pattern:
    def __init__(self, rows: int = 64, channels: int = 12):
        self.rows = rows
        self.channels = channels
        # Grid of [row][ch] = [note, inst, vol_col, eff, param]
        self.cells = [[[0, 0, 0, 0, 0] for _ in range(channels)] for _ in range(rows)]

    def set(self, row: int, ch: int, note=None, inst: int = None, vol=None, eff: int = None, param: int = None):
        if not (0 <= row < self.rows) or not (0 <= ch < self.channels):
            return
        c = self.cells[row][ch]
        if note is not None:
            c[0] = parse_note(note)
        if inst is not None:
            c[1] = int(inst)
        if vol is not None:
            c[2] = vol_byte(vol)
        if eff is not None:
            c[3] = int(eff) & 0xFF
        if param is not None:
            c[4] = int(param) & 0xFF

    def pack_xm(self) -> bytes:
        packed = bytearray()
        for r in range(self.rows):
            for ch in range(self.channels):
                n, ins, v, ef, pr = self.cells[r][ch]
                if n == 0 and ins == 0 and v == 0 and ef == 0 and pr == 0:
                    packed.append(0x80)
                elif n != 0 and ins != 0 and v != 0 and ef != 0 and pr != 0:
                    packed.extend((n, ins, v, ef, pr))
                else:
                    flags = 0x80
                    body = bytearray()
                    if n != 0:
                        flags |= 0x01
                        body.append(n)
                    if ins != 0:
                        flags |= 0x02
                        body.append(ins)
                    if v != 0:
                        flags |= 0x04
                        body.append(v)
                    if ef != 0:
                        flags |= 0x08
                        body.append(ef)
                    if pr != 0:
                        flags |= 0x10
                        body.append(pr)
                    packed.append(flags)
                    packed.extend(body)
        hdr = struct.pack("<IBHH", 9, 0, self.rows, len(packed))
        return hdr + bytes(packed)


def delta_encode_int16(pcm: np.ndarray) -> bytes:
    """XM 16-bit sample data is stored as signed 16-bit delta values (mod 65536)."""
    arr = np.asarray(pcm, dtype=np.int16).astype(np.int32)
    deltas = np.empty_like(arr, dtype=np.int16)
    if len(arr) > 0:
        deltas[0] = np.int16(arr[0])
        if len(arr) > 1:
            diff = (arr[1:] - arr[:-1]) & 0xFFFF
            deltas[1:] = diff.astype(np.uint16).view(np.int16)
    return deltas.tobytes()


def write_xm(
    path: str,
    song_name: str,
    channels: int,
    bpm: int,
    speed: int,
    orders: list,
    loop_start: int,
    patterns: list,
    instruments: list,
):
    out = bytearray()
    name_b = song_name.encode("ascii", "replace")[:20].ljust(20, b"\x00")
    tracker_b = b"Fasttracker II clone"
    # Pre-header (60 bytes)
    out.extend(b"Extended Module: ")
    out.extend(name_b)
    out.append(0x1A)
    out.extend(tracker_b)
    out.extend(struct.pack("<H", 0x0104))  # Version 1.04

    # Song header (276 bytes)
    order_table = bytearray(256)
    for idx, pat_idx in enumerate(orders[:256]):
        order_table[idx] = pat_idx
    song_hdr = struct.pack(
        "<IHHHHHHHH",
        276,                # Header size
        len(orders),        # Song length
        loop_start,         # Restart position
        channels,           # Number of channels
        len(patterns),      # Number of patterns
        len(instruments),   # Number of instruments
        1,                  # Flags: 1 = Linear frequency table
        speed,              # Default tempo (ticks/row)
        bpm,                # Default BPM
    ) + bytes(order_table)
    out.extend(song_hdr)

    # Patterns
    for pat in patterns:
        out.extend(pat.pack_xm())

    # Instruments (pure sample-based XM instruments, vol_type=0, pan_type=0)
    for inst in instruments:
        iname = inst["name"].encode("ascii", "replace")[:22].ljust(22, b"\x00")
        pcm = np.asarray(inst["pcm"], dtype=np.int16)
        inst_hdr = bytearray(263)
        struct.pack_into("<I", inst_hdr, 0, 263)
        inst_hdr[4:26] = iname
        inst_hdr[26] = 0
        struct.pack_into("<H", inst_hdr, 27, 1)  # 1 sample
        struct.pack_into("<I", inst_hdr, 29, 40) # Sample header size
        # Default 2-point disabled envelope points just like FT2 default
        struct.pack_into("<HHHH", inst_hdr, 129, 0, 64, 100, 64)
        struct.pack_into("<HHHH", inst_hdr, 177, 0, 32, 100, 32)
        inst_hdr[225] = 2
        inst_hdr[226] = 2
        inst_hdr[233] = 0  # vol_type = 0 (no envelope)
        inst_hdr[234] = 0  # pan_type = 0 (no envelope)
        struct.pack_into("<H", inst_hdr, 239, 128)  # default FT2 fadeout
        out.extend(inst_hdr)

        # Sample header (40 bytes); lengths in BYTES for 16-bit samples!
        slen_bytes = len(pcm) * 2
        lstart_bytes = int(inst.get("loop_start", 0)) * 2
        llen_bytes = int(inst.get("loop_length", 0)) * 2
        vol = int(inst.get("volume", 64))
        fine = int(inst.get("finetune", 0))
        flags = int(inst.get("flags", 16))
        pan = int(inst.get("panning", 128))
        rel = int(inst.get("relative_note", 0))
        sname = inst["name"].encode("ascii", "replace")[:22].ljust(22, b"\x00")
        samp_hdr = struct.pack(
            "<IIIBbBBbB22s",
            slen_bytes, lstart_bytes, llen_bytes,
            vol, fine, flags, pan, rel, 0, sname
        )
        out.extend(samp_hdr)
        out.extend(delta_encode_int16(pcm))

    with open(path, "wb") as f:
        f.write(out)


def ft2_call(tool: str, args: dict) -> dict:
    res = subprocess.run(["ft2", "call", tool, json.dumps(args)], capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    if data.get("isError"):
        raise RuntimeError(f"FT2 error calling {tool}: {data}")
    return data


def build_and_render(
    raw_xm_path: str,
    final_xm_path: str,
    wav_path: str,
    song_name: str,
    channels: int,
    bpm: int,
    speed: int,
    orders: list,
    loop_start: int,
    patterns: list,
    instruments: list,
) -> dict:
    write_xm(raw_xm_path, song_name, channels, bpm, speed, orders, loop_start, patterns, instruments)
    ft2_call("module_load", {"path": raw_xm_path})
    info = ft2_call("module_info", {})
    ft2_call("module_save", {"path": final_xm_path, "format": "xm"})
    render_info = ft2_call("module_render", {"path": wav_path, "rate": 44100, "bits": 16})
    return {"module_info": info, "render_info": render_info}


if __name__ == "__main__":
    from synth import build_all_instruments
    insts = build_all_instruments()
    p0 = Pattern(rows=64, channels=12)
    # Quick pitch & instrument verification test
    p0.set(0, 0, "C-4", 1, 64)
    p0.set(4, 1, "C-4", 2, 64)
    p0.set(8, 2, "C-4", 5, 56)
    p0.set(0, 3, "A-2", 9, 64)
    p0.set(16, 3, "off")
    p0.set(16, 4, "A-4", 11, 64)
    p0.set(32, 4, "off")
    p0.set(32, 5, "A-4", 12, 64)
    p0.set(48, 5, "off")
    p0.set(48, 7, "A-4", 14, 64)

    res = build_and_render(
        "/workspace/build/cal_raw.xm",
        "/workspace/build/cal.xm",
        "/workspace/build/cal.wav",
        "Calibration",
        12, 145, 6, [0], 0, [p0], insts
    )
    print("Calibration build OK:", res["module_info"]["content"][0]["text"])
