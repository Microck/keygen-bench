import os, sys, json, base64, subprocess, wave
import numpy as np

sys.path.insert(0, "/workspace/scripts")
from build_samples import make_samples

NOTE_MAP = {"C-": 0, "C#": 1, "D-": 2, "D#": 3, "E-": 4, "F-": 5,
            "F#": 6, "G-": 7, "G#": 8, "A-": 9, "A#": 10, "B-": 11}
OFF = 97

def N(s):
    if s == "OFF":
        return OFF
    pitch, octv = s[:-1], int(s[-1])
    return 1 + octv * 12 + NOTE_MAP[pitch]

# Instrument IDs
KICK = 1
SNARE = 2
HAT_C = 3
HAT_O = 4
CRASH = 5
TOM = 6
CLAP = 7
BASS_RESO = 8
BASS_FM = 9
BASS_TRI = 10
ARP_25 = 11
ARP_12 = 12
STAB = 13
PAD = 14
LEAD_HERO = 15
LEAD_SYNC = 16
BELL = 17
LEAD_FLUTE = 18
LEAD_PWR = 19
FX_RISER = 20
FX_LASER = 21
FX_REV = 22

# Channels (12)
CH_KICK = 0
CH_SNARE = 1
CH_HAT = 2
CH_PERC = 3
CH_BASS = 4
CH_ARP1 = 5
CH_ARP2 = 6
CH_LEAD = 7
CH_ECHO = 8
CH_SOLO = 9
CH_STAB = 10
CH_FX = 11

def vol_v(v):
    return 0x10 + max(0, min(64, int(v)))

class ModuleBuilder:
    def __init__(self, name="HYPERION KEYGEN", channels=12, bpm=138, speed=3):
        self.calls = []
        self.calls.append({"name": "module_new", "arguments": {"channels": channels, "name": name}})
        self.bpm = bpm
        self.speed = speed
        self.patterns = {}
        self.order = []
        self.loop_start = 2

    def load_samples(self):
        for s in make_samples():
            inst = s["instrument"]
            b64 = base64.b64encode(s["pcm"].tobytes()).decode("ascii")
            self.calls.append({"name": "instrument_set", "arguments": {"instrument": inst, "name": s["name"]}})
            self.calls.append({"name": "sample_create_from_pcm", "arguments": {
                "instrument": inst, "sample": 0, "pcm": b64, "encoding": "int16", "name": s["name"]
            }})
            self.calls.append({"name": "sample_set", "arguments": {
                "instrument": inst, "sample": 0,
                "volume": s["volume"], "panning": s["panning"],
                "finetune": s["finetune"], "relative_note": s["relative_note"],
                "loop_start": s["loop_start"], "loop_length": s["loop_length"],
                "flags": s["flags"]
            }})

    def cell(self, pat, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
        if pat not in self.patterns:
            self.patterns[pat] = {}
        d = self.patterns[pat].get((row, ch), {})
        if note is not None:
            d["note"] = N(note) if isinstance(note, str) else int(note)
        if inst is not None:
            d["instrument"] = int(inst)
        if vol is not None:
            d["volume"] = int(vol)
        if eff is not None:
            d["effect"] = int(eff)
        if param is not None:
            d["effect_param"] = int(param)
        self.patterns[pat][(row, ch)] = d

    def put_melody(self, pat, ch, inst, events, vol=56, vib=None, echo_ch=None, echo_delay=6, echo_vol=22, echo_pan=13, off_at_end=True, porta_rows=None):
        """
        events: list of (row, note_str, length_rows) or (row, note_str, length_rows, eff, param)
        porta_rows: set of rows that should glide cleanly with 3xx portamento
        """
        porta_rows = porta_rows or set()
        for idx, ev in enumerate(events):
            row, note_s, length = ev[0], ev[1], ev[2]
            eff = ev[3] if len(ev) > 3 else None
            param = ev[4] if len(ev) > 4 else None
            if row in porta_rows and eff is None:
                eff, param = 3, 0x38
                self.cell(pat, row, ch, note=note_s, vol=vol_v(vol), eff=eff, param=param)
            else:
                if eff is None and vib is not None and length >= 8:
                    eff, param = 4, vib
                self.cell(pat, row, ch, note=note_s, inst=inst, vol=vol_v(vol), eff=eff, param=param)
            if off_at_end:
                end_row = row + length
                next_row = events[idx + 1][0] if idx + 1 < len(events) else 64
                if end_row < next_row and end_row < 64:
                    self.cell(pat, end_row, ch, note=OFF)

            if echo_ch is not None:
                erow = row + echo_delay
                if erow < 64:
                    self.cell(pat, erow, echo_ch, note=note_s, inst=inst, vol=vol_v(echo_vol), eff=8, param=echo_pan * 16)
                    e_end = erow + max(2, length - 1)
                    next_erow = (events[idx + 1][0] + echo_delay) if idx + 1 < len(events) else 64
                    if e_end < next_erow and e_end < 64:
                        self.cell(pat, e_end, echo_ch, note=OFF)

    def put_arp_bar(self, pat, ch, inst, row_start, root_note, arp_param, vol=40, step=4, rows=32):
        rn = N(root_note) if isinstance(root_note, str) else root_note
        for r in range(row_start, row_start + rows, step):
            v = vol if (r % 8 == 0) else max(16, vol - 8)
            self.cell(pat, r, ch, note=rn, inst=inst, vol=vol_v(v), eff=0, param=arp_param)
            for sub in range(1, step):
                if r + sub < row_start + rows:
                    self.cell(pat, r + sub, ch, eff=0, param=arp_param)

    def put_drums_standard(self, pat, style="main", fill=None):
        if style in ("main", "chorus", "solo"):
            kick_rows = [0, 8, 16, 24, 32, 40, 48, 56]
            if style == "main":
                kick_rows += [14, 46]
            elif style in ("chorus", "solo"):
                kick_rows += [6, 22, 38, 54]
            for r in sorted(set(kick_rows)):
                if fill == "roll_last_bar" and r >= 48:
                    continue
                v = 56 if r % 8 == 0 else 44
                self.cell(pat, r, CH_KICK, note="C-4", inst=KICK, vol=vol_v(v))

            for r in [8, 24, 40, 56]:
                if fill == "roll_last_bar" and r >= 48:
                    continue
                self.cell(pat, r, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(54))
                if style == "chorus":
                    self.cell(pat, r, CH_PERC, note="C-4", inst=CLAP, vol=vol_v(38))

            if style == "main":
                for r in range(0, 64, 2):
                    if fill == "roll_last_bar" and r >= 52:
                        continue
                    if r % 8 == 4:
                        self.cell(pat, r, CH_HAT, note="C-4", inst=HAT_O, vol=vol_v(42))
                    elif r % 4 == 0:
                        self.cell(pat, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(44))
                    else:
                        self.cell(pat, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(26))
            elif style in ("chorus", "solo"):
                for r in range(0, 64, 2):
                    if fill == "roll_last_bar" and r >= 52:
                        continue
                    if r % 8 == 4:
                        self.cell(pat, r, CH_HAT, note="C-4", inst=HAT_O, vol=vol_v(52))
                    elif r % 4 == 0:
                        self.cell(pat, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(46))
                    else:
                        self.cell(pat, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(32))

        if fill == "tom_end":
            toms = [(48, "E-4", 48), (52, "D-4", 48), (56, "C-4", 52), (58, "A-3", 52), (60, "G-3", 56), (62, "C-4", 54)]
            for r, nt, v in toms:
                self.cell(pat, r, CH_PERC, note=nt, inst=TOM, vol=vol_v(v))
        elif fill == "snare_turnaround":
            for idx, r in enumerate(range(48, 64, 2)):
                v = 30 + idx * 4
                self.cell(pat, r, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(min(58, v)))
        elif fill == "roll_last_bar":
            roll = [(48, 32), (50, 36), (52, 40), (54, 44), (56, 48), (58, 50), (60, 54), (61, 50), (62, 56), (63, 58)]
            for r, v in roll:
                self.cell(pat, r, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(v))

    def put_bass_bar(self, pat, row_start, root, inst=BASS_FM, pattern="octave", vol=50):
        r0 = N(root)
        r_oct = r0 + 12
        r_5th = r0 + 7
        if pattern == "octave":
            seq = [
                (0, r0, vol), (4, r_oct, vol - 5), (8, r0, vol), (12, r_oct, vol - 5),
                (14, r_oct, vol - 12), (16, r0, vol), (20, r_oct, vol - 5),
                (24, r0, vol), (28, r_5th, vol - 7), (30, r_oct, vol - 8)
            ]
        elif pattern == "driving":
            seq = []
            for r in range(0, 32, 2):
                if r % 8 == 4:
                    seq.append((r, r_oct, vol - 2))
                elif r % 8 == 0:
                    seq.append((r, r0, vol))
                elif r % 4 == 2:
                    seq.append((r, r0, vol - 12))
                else:
                    seq.append((r, r_oct, vol - 8))
        elif pattern == "half":
            seq = [
                (0, r0, vol), (6, r0, vol - 10), (8, r_5th, vol - 6), (12, r_oct, vol - 6),
                (16, r0, vol), (24, r_5th, vol - 6), (28, r_oct, vol - 8)
            ]
        for off, nt, v in seq:
            self.cell(pat, row_start + off, CH_BASS, note=nt, inst=inst, vol=vol_v(v))

    def build_tune(self):
        self.load_samples()

        # =====================================================================
        # PAT 0: INTRO PART 1 (F#m | D)
        # =====================================================================
        p = 0
        self.cell(p, 0, CH_FX, eff=16, param=56)
        bell_p0 = [
            (0, "F#4", 4), (4, "A-4", 4), (8, "C#5", 4), (12, "F#5", 8),
            (20, "C#5", 4), (24, "A-4", 4), (28, "C#5", 4),
            (32, "D-4", 4), (36, "F#4", 4), (40, "A-4", 4), (44, "D-5", 8),
            (52, "A-4", 4), (56, "F#4", 4), (60, "A-4", 4),
        ]
        self.put_melody(p, CH_SOLO, BELL, bell_p0, vol=52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=22, echo_pan=3, off_at_end=False)
        for r in range(0, 32, 4):
            v = 18 + (r // 4) * 3
            self.cell(p, r, CH_ARP2, note="F#4", inst=ARP_12, vol=vol_v(v), eff=0, param=0x37)
            for s in range(1, 4):
                self.cell(p, r + s, CH_ARP2, eff=0, param=0x37)
        for r in range(32, 64, 4):
            v = 24 + ((r - 32) // 4) * 3
            self.cell(p, r, CH_ARP2, note="D-4", inst=ARP_12, vol=vol_v(v), eff=0, param=0x47)
            for s in range(1, 4):
                self.cell(p, r + s, CH_ARP2, eff=0, param=0x47)
        for r in range(0, 64, 4):
            self.cell(p, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(18 + (r // 4)))
        # Airy upper-octave Pad foundation
        self.cell(p, 0, CH_STAB, note="F#4", inst=PAD, vol=vol_v(26))
        self.cell(p, 32, CH_STAB, note="D-4", inst=PAD, vol=vol_v(28))

        # =====================================================================
        # PAT 1: INTRO PART 2 (E | C#7)
        # =====================================================================
        p = 1
        bell_p1 = [
            (0, "E-4", 4), (4, "G#4", 4), (8, "B-4", 4), (12, "E-5", 8),
            (20, "B-4", 4), (24, "G#4", 4), (28, "B-4", 4),
            (32, "C#4", 4), (36, "F-4", 4), (40, "G#4", 4), (44, "C#5", 6),
            (50, "F-5", 4), (54, "G#5", 4), (58, "C#6", 6),
        ]
        self.put_melody(p, CH_SOLO, BELL, bell_p1, vol=54, echo_ch=CH_ECHO, echo_delay=6, echo_vol=24, echo_pan=3, off_at_end=False)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 0, "E-4", 0x47, vol=38, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 32, "C#4", 0x47, vol=42, step=4, rows=32)
        self.put_bass_bar(p, 0, "E-2", inst=BASS_TRI, pattern="octave", vol=46)
        self.put_bass_bar(p, 32, "C#2", inst=BASS_TRI, pattern="octave", vol=50)
        self.cell(p, 0, CH_STAB, note="E-4", inst=PAD, vol=vol_v(28))
        self.cell(p, 32, CH_STAB, note="C#4", inst=PAD, vol=vol_v(30))
        self.cell(p, 62, CH_STAB, note=OFF)
        for r in range(0, 32, 8):
            self.cell(p, r + 4, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(24 + r // 2))
        for idx, r in enumerate(range(32, 48, 4)):
            self.cell(p, r, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(30 + idx * 4))
        for idx, r in enumerate(range(48, 64, 2)):
            self.cell(p, r, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(38 + idx * 2))
        self.cell(p, 32, CH_FX, note="C-4", inst=FX_RISER, vol=vol_v(44))
        self.cell(p, 40, CH_PERC, note="C-4", inst=FX_REV, vol=vol_v(44))

        # =====================================================================
        # THEME A (PAT 2..5): Main Groove (F#m | D | E | C#m7 / C#7)
        # =====================================================================
        def fill_theme_a_groove(pat, ch1, arp1, ch2, arp2, bass1, bass2, fill=None, crash=False):
            self.put_drums_standard(pat, style="main", fill=fill)
            if crash:
                self.cell(pat, 0, CH_PERC, note="C-4", inst=CRASH, vol=vol_v(44))
            self.put_bass_bar(pat, 0, bass1, inst=BASS_FM, pattern="octave", vol=48)
            self.put_bass_bar(pat, 32, bass2, inst=BASS_FM, pattern="octave", vol=48)
            self.put_arp_bar(pat, CH_ARP1, ARP_25, 0, ch1, arp1, vol=36, step=4, rows=32)
            self.put_arp_bar(pat, CH_ARP1, ARP_25, 32, ch2, arp2, vol=36, step=4, rows=32)
            self.put_arp_bar(pat, CH_ARP2, ARP_12, 0, ch1, arp1, vol=24, step=8, rows=32)
            self.put_arp_bar(pat, CH_ARP2, ARP_12, 32, ch2, arp2, vol=24, step=8, rows=32)

        # PAT 2: F#m | D
        self.cell(2, 0, CH_FX, eff=16, param=56)
        fill_theme_a_groove(2, "F#4", 0x37, "D-4", 0x47, "F#2", "D-2", crash=True)
        lead_a1 = [
            (0, "F#5", 6), (6, "G#5", 2), (8, "A-5", 4), (12, "C#6", 4),
            (16, "B-5", 4), (20, "A-5", 4), (24, "G#5", 4), (28, "F#5", 4),
            (32, "A-5", 6), (38, "F#5", 2), (40, "D-5", 8),
            (48, "E-5", 4), (52, "F#5", 4), (56, "A-5", 4), (60, "G#5", 4, 14, 0xC2),
        ]
        self.put_melody(2, CH_LEAD, LEAD_HERO, lead_a1, vol=54, vib=0x52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=13, porta_rows={6})
        self.cell(2, 0, CH_STAB, note="F#4", inst=STAB, vol=vol_v(36))
        self.cell(2, 32, CH_STAB, note="D-4", inst=STAB, vol=vol_v(36))

        # PAT 3: E | C#m7
        fill_theme_a_groove(3, "E-4", 0x47, "C#4", 0x3A, "E-2", "C#2", fill="tom_end")
        lead_a2 = [
            (0, "G#5", 6), (6, "A-5", 2), (8, "B-5", 4), (12, "E-6", 4),
            (16, "D-6", 4), (20, "C#6", 4), (24, "B-5", 4), (28, "A-5", 4),
            (32, "G#5", 12), (44, "E-5", 4),
            (48, "G#5", 4), (52, "F#5", 4), (56, "E-5", 4), (60, "C#5", 4, 14, 0xC2),
        ]
        self.put_melody(3, CH_LEAD, LEAD_HERO, lead_a2, vol=54, vib=0x52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=13, porta_rows={6})
        self.cell(3, 0, CH_STAB, note="E-4", inst=STAB, vol=vol_v(36))
        self.cell(3, 32, CH_STAB, note="C#4", inst=STAB, vol=vol_v(36))

        # PAT 4: F#m | D (High Peak Variation!)
        fill_theme_a_groove(4, "F#4", 0x37, "D-4", 0x47, "F#2", "D-2")
        lead_a3 = [
            (0, "F#5", 6), (6, "G#5", 2), (8, "A-5", 4), (12, "C#6", 4),
            (16, "F#6", 6), (22, "E-6", 2), (24, "C#6", 4), (28, "A-5", 4),
            (32, "D-6", 6), (38, "C#6", 2), (40, "B-5", 4), (44, "A-5", 4),
            (48, "F#5", 4), (52, "A-5", 4), (56, "B-5", 4), (60, "A-5", 4),
        ]
        self.put_melody(4, CH_LEAD, LEAD_HERO, lead_a3, vol=56, vib=0x53, echo_ch=CH_ECHO, echo_delay=6, echo_vol=22, echo_pan=13, porta_rows={16})
        for r, nt in [(16, "A-5"), (32, "F#5"), (48, "D-5")]:
            self.cell(4, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(36))

        # PAT 5: E | C#7 (Turnaround into Chorus!)
        fill_theme_a_groove(5, "E-4", 0x47, "C#4", 0x4A, "E-2", "C#2", fill="snare_turnaround")
        lead_a4 = [
            (0, "G#5", 6), (6, "A-5", 2), (8, "B-5", 8),
            (16, "E-5", 4), (20, "G#5", 4), (24, "B-5", 4), (28, "D-6", 4),
            (32, "C#6", 8), (40, "B-5", 4), (44, "G#5", 4),
            (48, "F-5", 4), (52, "G#5", 4), (56, "B-5", 4), (60, "C#6", 4),
        ]
        self.put_melody(5, CH_LEAD, LEAD_HERO, lead_a4, vol=56, vib=0x63, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=13)
        self.cell(5, 32, CH_FX, note="C-4", inst=FX_RISER, vol=vol_v(34))

        # =====================================================================
        # SECTION B (PAT 6..9, + PAT 18 climax): ANTHEMIC CHORUS
        # =====================================================================
        def fill_chorus_base(pat, ch1, arp1, ch2, arp2, b1, b2, fill=None, crash=False):
            self.put_drums_standard(pat, style="chorus", fill=fill)
            if crash:
                self.cell(pat, 0, CH_PERC, note="C-4", inst=CRASH, vol=vol_v(50))
            self.put_bass_bar(pat, 0, b1, inst=BASS_RESO, pattern="driving", vol=52)
            self.put_bass_bar(pat, 32, b2, inst=BASS_RESO, pattern="driving", vol=52)
            self.put_arp_bar(pat, CH_ARP1, ARP_25, 0, ch1, arp1, vol=40, step=4, rows=32)
            self.put_arp_bar(pat, CH_ARP1, ARP_25, 32, ch2, arp2, vol=40, step=4, rows=32)
            self.put_arp_bar(pat, CH_ARP2, ARP_12, 0, N(ch1) + 12, arp1, vol=36, step=4, rows=32)
            self.put_arp_bar(pat, CH_ARP2, ARP_12, 32, N(ch2) + 12, arp2, vol=36, step=4, rows=32)
            for bar_off, chord_root in [(0, ch1), (32, ch2)]:
                for r_off in [0, 6, 12, 20, 28]:
                    self.cell(pat, bar_off + r_off, CH_STAB, note=chord_root, inst=STAB, vol=vol_v(42))

        # PAT 6: D | E
        fill_chorus_base(6, "D-4", 0x47, "E-4", 0x47, "D-2", "E-2", crash=True)
        c6_lead = [
            (0, "F#5", 12), (12, "A-5", 4), (16, "D-6", 8), (24, "C#6", 4), (28, "B-5", 4),
            (32, "B-5", 12), (44, "G#5", 4), (48, "E-5", 8), (56, "G#5", 4), (60, "B-5", 4),
        ]
        c6_harm = [
            (0, "D-5", 12), (12, "F#5", 4), (16, "A-5", 8), (24, "A-5", 4), (28, "G#5", 4),
            (32, "G#5", 12), (44, "E-5", 4), (48, "B-4", 8), (56, "E-5", 4), (60, "G#5", 4),
        ]
        self.put_melody(6, CH_LEAD, LEAD_PWR, c6_lead, vol=58, vib=0x52)
        self.put_melody(6, CH_ECHO, LEAD_HERO, c6_harm, vol=42, vib=0x52)
        for r, nt in [(0, "A-5"), (16, "F#6"), (32, "E-6"), (48, "B-5")]:
            self.cell(6, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(36))

        # PAT 7: F#m | A
        fill_chorus_base(7, "F#4", 0x37, "A-4", 0x47, "F#2", "A-2", fill="tom_end")
        c7_lead = [
            (0, "A-5", 6), (6, "B-5", 2), (8, "C#6", 8), (16, "A-5", 4), (20, "F#5", 4), (24, "C#6", 4), (28, "D-6", 4),
            (32, "E-6", 12), (44, "C#6", 4), (48, "A-5", 8), (56, "B-5", 4), (60, "C#6", 4),
        ]
        c7_harm = [
            (0, "F#5", 6), (6, "G#5", 2), (8, "A-5", 8), (16, "F#5", 4), (20, "C#5", 4), (24, "A-5", 4), (28, "B-5", 4),
            (32, "C#6", 12), (44, "A-5", 4), (48, "E-5", 8), (56, "G#5", 4), (60, "A-5", 4),
        ]
        self.put_melody(7, CH_LEAD, LEAD_PWR, c7_lead, vol=58, vib=0x52)
        self.put_melody(7, CH_ECHO, LEAD_HERO, c7_harm, vol=42, vib=0x52)
        for r, nt in [(0, "C#6"), (16, "F#5"), (32, "A-6"), (48, "E-6")]:
            self.cell(7, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(36))

        # PAT 8: D | E (Chorus Peak!)
        fill_chorus_base(8, "D-4", 0x47, "E-4", 0x47, "D-2", "E-2")
        c8_lead = [
            (0, "D-6", 6), (6, "E-6", 2), (8, "F#6", 8), (16, "D-6", 4), (20, "A-5", 4), (24, "D-6", 4), (28, "C#6", 4),
            (32, "B-5", 6), (38, "C#6", 2), (40, "D-6", 8), (48, "E-6", 8), (56, "D-6", 4), (60, "B-5", 4),
        ]
        c8_harm = [
            (0, "A-5", 6), (6, "C#6", 2), (8, "D-6", 8), (16, "A-5", 4), (20, "F#5", 4), (24, "A-5", 4), (28, "A-5", 4),
            (32, "G#5", 6), (38, "A-5", 2), (40, "B-5", 8), (48, "B-5", 8), (56, "B-5", 4), (60, "G#5", 4),
        ]
        self.put_melody(8, CH_LEAD, LEAD_PWR, c8_lead, vol=60, vib=0x53)
        self.put_melody(8, CH_ECHO, LEAD_HERO, c8_harm, vol=44, vib=0x53)
        for r, nt in [(0, "F#6"), (16, "A-5"), (32, "G#6"), (48, "B-6")]:
            self.cell(8, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(36))

        # PAT 9: C#7 | F#m
        fill_chorus_base(9, "C#4", 0x4A, "F#4", 0x37, "C#2", "F#2")
        c9_lead = [
            (0, "C#6", 8), (8, "G#5", 4), (12, "F-5", 4), (16, "G#5", 6), (22, "B-5", 2), (24, "C#6", 4), (28, "F-5", 4),
            (32, "F#5", 16), (48, "C#6", 4), (52, "A-5", 4), (56, "F#5", 8),
        ]
        c9_harm = [
            (0, "G#5", 8), (8, "F-5", 4), (12, "C#5", 4), (16, "F-5", 6), (22, "G#5", 2), (24, "G#5", 4), (28, "C#5", 4),
            (32, "C#5", 16), (48, "A-5", 4), (52, "F#5", 4), (56, "C#5", 8),
        ]
        self.put_melody(9, CH_LEAD, LEAD_PWR, c9_lead, vol=58, vib=0x63)
        self.put_melody(9, CH_ECHO, LEAD_HERO, c9_harm, vol=42, vib=0x63)
        self.cell(9, 56, CH_FX, note="C-4", inst=FX_LASER, vol=vol_v(40))

        # =====================================================================
        # SECTION C (PAT 10..13): INTIMATE AIRY BREAKDOWN & BUILD
        # =====================================================================
        # PAT 10: Bm7 | E
        p = 10
        self.cell(p, 0, CH_PERC, note="C-4", inst=CRASH, vol=vol_v(38))
        self.cell(p, 0, CH_STAB, note="B-4", inst=PAD, vol=vol_v(20))
        self.cell(p, 32, CH_STAB, note="E-4", inst=PAD, vol=vol_v(20))
        self.put_bass_bar(p, 0, "B-1", inst=BASS_TRI, pattern="half", vol=38)
        self.put_bass_bar(p, 32, "E-2", inst=BASS_TRI, pattern="half", vol=38)
        for r in [8, 24, 40, 56]:
            self.cell(p, r, CH_SNARE, note="C-4", inst=CLAP, vol=vol_v(28))
        for r in range(0, 64, 4):
            self.cell(p, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(32 if r % 8 == 4 else 20))
        self.put_arp_bar(p, CH_ARP2, ARP_12, 0, "B-5", 0x3A, vol=26, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 32, "E-5", 0x47, vol=26, step=4, rows=32)
        flute_10 = [
            (0, "D-5", 10), (10, "C#5", 2), (12, "B-4", 4), (16, "F#5", 12), (28, "E-5", 4),
            (32, "G#5", 8), (40, "E-5", 8), (48, "B-4", 8), (56, "E-5", 8),
        ]
        self.put_melody(p, CH_LEAD, LEAD_FLUTE, flute_10, vol=38, vib=0x42, echo_ch=CH_ECHO, echo_delay=6, echo_vol=14, echo_pan=13)
        for r, nt in [(16, "F#5"), (20, "A-5"), (24, "D-6"), (48, "G#5"), (52, "B-5"), (56, "E-6")]:
            self.cell(p, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(46))

        # PAT 11: A | D
        p = 11
        self.cell(p, 0, CH_STAB, note="A-4", inst=PAD, vol=vol_v(20))
        self.cell(p, 32, CH_STAB, note="D-4", inst=PAD, vol=vol_v(20))
        self.put_bass_bar(p, 0, "A-1", inst=BASS_TRI, pattern="half", vol=38)
        self.put_bass_bar(p, 32, "D-2", inst=BASS_TRI, pattern="half", vol=38)
        for r in [8, 24, 40, 56]:
            self.cell(p, r, CH_SNARE, note="C-4", inst=CLAP, vol=vol_v(30))
        for r in range(0, 64, 4):
            self.cell(p, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(34 if r % 8 == 4 else 22))
        flute_11 = [
            (0, "C#5", 8), (8, "E-5", 8), (16, "A-5", 10), (26, "G#5", 2), (28, "E-5", 4),
            (32, "F#5", 12), (44, "D-5", 4), (48, "A-5", 8), (56, "F#5", 8),
        ]
        self.put_melody(p, CH_LEAD, LEAD_FLUTE, flute_11, vol=40, vib=0x42, echo_ch=CH_ECHO, echo_delay=6, echo_vol=15, echo_pan=13)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 0, "A-5", 0x47, vol=28, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 32, "D-5", 0x47, vol=30, step=4, rows=32)
        for r, nt in [(16, "C#6"), (24, "E-6"), (48, "F#5"), (56, "A-5")]:
            self.cell(p, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(46))

        # PAT 12: Bm7 | C#7
        p = 12
        self.cell(p, 0, CH_STAB, note="B-4", inst=PAD, vol=vol_v(30))
        self.cell(p, 32, CH_STAB, note="C#4", inst=PAD, vol=vol_v(32))
        self.put_bass_bar(p, 0, "B-1", inst=BASS_RESO, pattern="octave", vol=46)
        self.put_bass_bar(p, 32, "C#2", inst=BASS_RESO, pattern="octave", vol=48)
        for r in [0, 16, 32, 40, 48, 56]:
            self.cell(p, r, CH_KICK, note="C-4", inst=KICK, vol=vol_v(50))
        for r in [16, 40, 56]:
            self.cell(p, r, CH_SNARE, note="C-4", inst=SNARE, vol=vol_v(46))
        for r in range(0, 64, 4):
            self.cell(p, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(30))
        self.put_arp_bar(p, CH_ARP1, ARP_25, 0, "B-4", 0x3A, vol=32, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP1, ARP_25, 32, "C#4", 0x4A, vol=36, step=4, rows=32)
        flute_12 = [
            (0, "D-5", 8), (8, "F#5", 8), (16, "B-5", 12), (28, "A-5", 4),
            (32, "G#5", 8), (40, "F-5", 8), (48, "G#5", 8), (56, "C#6", 8),
        ]
        self.put_melody(p, CH_LEAD, LEAD_HERO, flute_12, vol=50, vib=0x52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=13)

        # PAT 13: F#m | C#7 (Pre-Solo Snare Roll & Riser Drop!)
        p = 13
        self.put_drums_standard(p, style="main", fill="roll_last_bar")
        self.put_bass_bar(p, 0, "F#2", inst=BASS_RESO, pattern="driving", vol=50)
        self.put_bass_bar(p, 32, "C#2", inst=BASS_RESO, pattern="driving", vol=52)
        self.put_arp_bar(p, CH_ARP1, ARP_25, 0, "F#4", 0x37, vol=38, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP1, ARP_25, 32, "C#4", 0x47, vol=40, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 0, "F#5", 0x37, vol=30, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP2, ARP_12, 32, "C#5", 0x47, vol=34, step=4, rows=32)
        lead_13 = [
            (0, "F#5", 8), (8, "A-5", 8), (16, "C#6", 8), (24, "F#6", 8),
            (32, "F-6", 6), (38, "C#6", 2), (40, "G#5", 4), (44, "B-5", 4),
            (48, "C#6", 4), (52, "F-6", 4), (56, "G#6", 8),
        ]
        self.put_melody(p, CH_LEAD, LEAD_HERO, lead_13, vol=54, vib=0x63)
        self.cell(p, 32, CH_FX, note="C-4", inst=FX_RISER, vol=vol_v(42))
        self.cell(p, 40, CH_PERC, note="C-4", inst=FX_REV, vol=vol_v(44))

        # =====================================================================
        # SECTION D (PAT 14..17): VIRTUOSO C64 CHIP SOLO
        # =====================================================================
        def fill_solo_base(pat, ch1, arp1, ch2, arp2, b1, b2, fill=None, crash=False):
            self.put_drums_standard(pat, style="solo", fill=fill)
            if crash:
                self.cell(pat, 0, CH_PERC, note="C-4", inst=CRASH, vol=vol_v(48))
            self.put_bass_bar(pat, 0, b1, inst=BASS_FM, pattern="octave", vol=50)
            self.put_bass_bar(pat, 32, b2, inst=BASS_FM, pattern="octave", vol=50)
            self.put_arp_bar(pat, CH_ARP1, ARP_25, 0, ch1, arp1, vol=36, step=4, rows=32)
            self.put_arp_bar(pat, CH_ARP1, ARP_25, 32, ch2, arp2, vol=36, step=4, rows=32)

        # PAT 14: F#m | D
        fill_solo_base(14, "F#4", 0x37, "D-4", 0x47, "F#2", "D-2", crash=True)
        solo_14 = [
            (0, "F#5", 2), (2, "A-5", 2), (4, "C#6", 2), (6, "F#6", 2),
            (8, "F-6", 2), (10, "C#6", 2), (12, "B-5", 2), (14, "A-5", 2),
            (16, "G#5", 2), (18, "A-5", 2), (20, "B-5", 2), (22, "C#6", 2),
            (24, "A-5", 4), (28, "F#5", 4, 14, 0xC2),
            (32, "D-6", 2), (34, "F#6", 2), (36, "A-6", 4), (40, "G#6", 2), (42, "F#6", 2),
            (44, "E-6", 2), (46, "D-6", 2), (48, "C#6", 4), (52, "B-5", 4),
            (56, "A-5", 4), (60, "F#5", 4),
        ]
        self.put_melody(14, CH_LEAD, LEAD_SYNC, solo_14, vol=54, vib=0x52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=14, porta_rows={6, 36})

        # PAT 15: Bm | C#7
        fill_solo_base(15, "B-4", 0x37, "C#4", 0x47, "B-1", "C#2", fill="tom_end")
        solo_15 = [
            (0, "B-5", 2), (2, "D-6", 2), (4, "F#6", 4), (8, "E-6", 2), (10, "D-6", 2), (12, "C#6", 4),
            (16, "B-5", 6), (22, "A-5", 2), (24, "G#5", 4), (28, "F#5", 4),
            (32, "F-5", 2), (34, "G#5", 2), (36, "C#6", 2), (38, "F-6", 2),
            (40, "G#6", 8), (48, "F-6", 4), (52, "C#6", 4), (56, "B-5", 4), (60, "G#5", 4),
        ]
        self.put_melody(15, CH_LEAD, LEAD_SYNC, solo_15, vol=54, vib=0x63)
        for r, nt in [(16, "D-6"), (20, "F#6"), (24, "B-6"), (48, "G#5"), (52, "C#6")]:
            self.cell(15, r, CH_SOLO, note=nt, inst=BELL, vol=vol_v(42))

        # PAT 16: F#m | D
        fill_solo_base(16, "F#4", 0x37, "D-4", 0x47, "F#2", "D-2")
        solo_16 = [
            (0, "F#6", 1), (1, "G#6", 1), (2, "F#6", 1), (3, "E-6", 1), (4, "C#6", 4),
            (8, "E-6", 1), (9, "F#6", 1), (10, "E-6", 1), (11, "D-6", 1), (12, "B-5", 4),
            (16, "C#6", 2), (18, "A-5", 2), (20, "F#5", 2), (22, "A-5", 2),
            (24, "C#6", 4), (28, "F#6", 4),
            (32, "D-6", 4), (36, "A-5", 2), (38, "D-6", 2), (40, "F#6", 4), (44, "A-6", 4),
            (48, "F#6", 4), (52, "D-6", 4), (56, "E-6", 4), (60, "F#6", 4),
        ]
        self.put_melody(16, CH_LEAD, LEAD_SYNC, solo_16, vol=56, vib=0x52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=14)

        # PAT 17: E | C#7
        fill_solo_base(17, "E-4", 0x47, "C#4", 0x4A, "E-2", "C#2", fill="snare_turnaround")
        solo_17 = [
            (0, "G#6", 6), (6, "F#6", 2), (8, "E-6", 4), (12, "B-5", 4),
            (16, "E-6", 4), (20, "G#6", 4), (24, "B-6", 8),
            (32, "G#6", 4), (36, "F-6", 4), (40, "C#6", 4), (44, "G#5", 4),
            (48, "C#6", 2), (50, "F-6", 2), (52, "G#6", 2), (54, "B-6", 2),
            (56, "C#7", 8),
        ]
        self.put_melody(17, CH_LEAD, LEAD_SYNC, solo_17, vol=56, vib=0x63)
        self.cell(17, 32, CH_FX, note="C-4", inst=FX_RISER, vol=vol_v(38))
        self.cell(17, 40, CH_PERC, note="C-4", inst=FX_REV, vol=vol_v(42))

        # =====================================================================
        # PAT 18: DOUBLE CHORUS CLIMAX ENDING (C#7 | F#m)
        # =====================================================================
        fill_chorus_base(18, "C#4", 0x4A, "F#4", 0x37, "C#2", "F#2", fill="tom_end")
        c18_lead = [
            (0, "G#6", 8), (8, "F-6", 4), (12, "C#6", 4), (16, "F-6", 4), (20, "G#6", 4), (24, "B-6", 4), (28, "G#6", 4),
            (32, "F#6", 16), (48, "C#6", 4), (52, "A-5", 4), (56, "F#5", 8),
        ]
        c18_harm = [
            (0, "C#6", 8), (8, "G#5", 4), (12, "F-5", 4), (16, "G#5", 4), (20, "C#6", 4), (24, "F-6", 4), (28, "C#6", 4),
            (32, "C#6", 16), (48, "A-5", 4), (52, "F#5", 4), (56, "C#5", 8),
        ]
        self.put_melody(18, CH_LEAD, LEAD_PWR, c18_lead, vol=60, vib=0x63)
        self.put_melody(18, CH_ECHO, LEAD_HERO, c18_harm, vol=44, vib=0x63)

        # =====================================================================
        # SECTION A2 (PAT 19..22): OUTRO GROOVE & SEAMLESS TURNAROUND TO POS 2
        # =====================================================================
        # PAT 19: F#m | D
        p = 19
        self.cell(p, 0, CH_PERC, note="C-4", inst=CRASH, vol=vol_v(46))
        for r in [0, 16, 32, 48]:
            self.cell(p, r, CH_KICK, note="C-4", inst=KICK, vol=vol_v(52))
        for r in [8, 24, 40, 56]:
            self.cell(p, r, CH_SNARE, note="C-4", inst=CLAP, vol=vol_v(38))
        for r in range(0, 64, 4):
            self.cell(p, r, CH_HAT, note="C-4", inst=HAT_C, vol=vol_v(34 if r % 8 == 4 else 22))
        self.put_bass_bar(p, 0, "F#2", inst=BASS_FM, pattern="octave", vol=48)
        self.put_bass_bar(p, 32, "D-2", inst=BASS_FM, pattern="octave", vol=48)
        self.put_arp_bar(p, CH_ARP1, ARP_25, 0, "F#4", 0x37, vol=34, step=4, rows=32)
        self.put_arp_bar(p, CH_ARP1, ARP_25, 32, "D-4", 0x47, vol=34, step=4, rows=32)
        self.put_melody(p, CH_SOLO, BELL, lead_a1, vol=50, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=13, off_at_end=False)

        # PAT 20: E | C#m7
        fill_theme_a_groove(20, "E-4", 0x47, "C#4", 0x3A, "E-2", "C#2", fill="tom_end")
        self.put_melody(20, CH_LEAD, LEAD_HERO, lead_a2, vol=54, vib=0x52, echo_ch=CH_ECHO, echo_delay=6, echo_vol=20, echo_pan=13)

        # PAT 21: F#m | D
        fill_theme_a_groove(21, "F#4", 0x37, "D-4", 0x47, "F#2", "D-2")
        self.put_melody(21, CH_LEAD, LEAD_HERO, lead_a3, vol=56, vib=0x53, echo_ch=CH_ECHO, echo_delay=6, echo_vol=22, echo_pan=13)
        for r, nt in [(0, "F#4"), (16, "F#4"), (32, "D-4"), (48, "D-4")]:
            self.cell(21, r, CH_STAB, note=nt, inst=STAB, vol=vol_v(38))

        # PAT 22: E | C#7 -> seamless turnaround into PAT 2 (F#m)
        fill_theme_a_groove(22, "E-4", 0x47, "C#4", 0x4A, "E-2", "C#2", fill="roll_last_bar")
        lead_22 = [
            (0, "G#5", 6), (6, "A-5", 2), (8, "B-5", 8),
            (16, "E-6", 6), (22, "D-6", 2), (24, "C#6", 4), (28, "B-5", 4),
            (32, "C#6", 8), (40, "G#5", 4), (44, "F-5", 4),
            (48, "G#5", 4), (52, "B-5", 4), (56, "C#6", 4), (60, "F-6", 4),
        ]
        self.put_melody(22, CH_LEAD, LEAD_HERO, lead_22, vol=56, vib=0x63)
        self.cell(22, 32, CH_FX, note="C-4", inst=FX_RISER, vol=vol_v(42))
        self.cell(22, 40, CH_PERC, note="C-4", inst=FX_REV, vol=vol_v(42))

        self.order = [
            0, 1,           # Intro
            2, 3, 4, 5,     # Theme A  <-- loop_start = 2
            6, 7, 8, 9,     # Chorus B1
            10, 11, 12, 13, # Breakdown & Build C
            14, 15, 16, 17, # Chip Solo D
            6, 7, 8, 18,    # Double Chorus B2
            19, 20, 21, 22  # Outro & Turnaround A2
        ]
        self.loop_start = 2

        self.calls.append({"name": "song_set", "arguments": {
            "name": "HYPERION KEYGEN",
            "bpm": self.bpm,
            "speed": self.speed,
            "length": len(self.order),
            "loop_start": self.loop_start
        }})
        for pos, pat in enumerate(self.order):
            self.calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

        for pat, cells in sorted(self.patterns.items()):
            self.calls.append({"name": "pattern_set_length", "arguments": {"pattern": pat, "rows": 64}})
            for (row, ch), d in sorted(cells.items()):
                args = {"pattern": pat, "row": row, "channel": ch}
                args.update(d)
                self.calls.append({"name": "pattern_set_cell", "arguments": args})

        self.calls.append({"name": "module_save", "arguments": {"path": "/workspace/submission/tune.xm", "format": "xm"}})
        return self.calls

if __name__ == "__main__":
    mb = ModuleBuilder()
    calls = mb.build_tune()
    batch_path = "/tmp/build_batch.json"
    with open(batch_path, "w") as f:
        json.dump(calls, f)
    p = subprocess.run(["ft2", "batch", batch_path], capture_output=True, text=True)
    if p.returncode != 0:
        print("BATCH ERROR:", p.returncode, p.stderr, p.stdout[-2000:])
        sys.exit(1)

    r1 = subprocess.run(["ft2", "call", "module_render", json.dumps({
        "path": "/tmp/tune_v2.wav", "rate": 44100, "bits": 16
    })], capture_output=True, text=True)
    print("Render v2:", r1.stdout.strip())

    # Analyze v2
    with wave.open("/tmp/tune_v2.wav", "rb") as w:
        sr = w.getframerate()
        d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(np.float64)

    clipped = np.sum(np.abs(d) >= 32767)
    print(f"Peak: {np.max(np.abs(d)):.0f} / 32768 | Total clipped samples: {clipped} ({100.0 * clipped / d.size:.4f}%)")
    pat_s = 64 * 3 * 2.5 / 138.0
    def band_energies(seg):
        mono = 0.5 * (seg[:, 0] + seg[:, 1])
        spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono))))**2
        freqs = np.fft.rfftfreq(len(mono), 1/sr)
        bands = [(20, 80, "sub"), (80, 250, "bass"), (250, 1000, "lmid"), (1000, 4000, "pres"), (4000, 16000, "air")]
        tot = np.sum(spec) + 1e-12
        return {name: 100.0 * np.sum(spec[(freqs >= f0) & (freqs < f1)]) / tot for f0, f1, name in bands}

    sections = [
        ("Intro (0-1)", 0, 2),
        ("Theme A (2-5)", 2, 6),
        ("Chorus B1 (6-9)", 6, 10),
        ("Break C1 (10-11)", 10, 12),
        ("Build C2 (12-13)", 12, 14),
        ("Solo D (14-17)", 14, 18),
        ("Chorus B2 (18-21)", 18, 22),
        ("Outro A2 (22-25)", 22, 26),
    ]
    for name, p0, p1 in sections:
        s0, s1 = int(p0 * pat_s * sr), min(len(d), int(p1 * pat_s * sr))
        seg = d[s0:s1]
        rmsL = np.sqrt(np.mean(seg[:, 0]**2))
        rmsR = np.sqrt(np.mean(seg[:, 1]**2))
        pk = np.max(np.abs(seg))
        clip_pct = 100.0 * np.sum(np.abs(seg) >= 32767) / seg.size
        be = band_energies(seg)
        bstr = " ".join(f"{k}:{v:4.1f}%" for k, v in be.items())
        print(f"{name:18s} rms=({rmsL:5.0f},{rmsR:5.0f}) pk={pk:5.0f} clip={clip_pct:4.2f}% | {bstr}")
