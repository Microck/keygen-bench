import os
import sys
import json
import subprocess
import numpy as np

sys.path.insert(0, '/workspace/work')
import instruments

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

def note_to_xm(name):
    if name in ('off', '===', 97):
        return 97
    if isinstance(name, int):
        return name
    name = name.strip()
    octave = int(name[-1])
    pitch = name[:-1]
    alias = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
    if pitch in alias:
        pitch = alias[pitch]
    if len(pitch) == 1:
        pitch += '-'
    idx = NOTE_NAMES.index(pitch)
    return octave * 12 + idx + 1

# Instrument IDs matching instruments.py
KICK      = 1
SNARE     = 2
GHOST     = 3
HHC       = 4
HHO       = 5
CRASH     = 6
TOM       = 7
BASS_DRV  = 8
BASS_PLK  = 9
ARP_P25   = 10
ARP_BELL  = 11
LEAD_PWM  = 12
LEAD_SAW  = 13
LEAD_BELL = 14
PAD_TRI   = 15
FX_SWEEP  = 16

class SongBuilder:
    def __init__(self, num_patterns, channels=10, name="Astral Keysmith", bpm=138, speed=3):
        self.num_patterns = num_patterns
        self.channels = channels
        self.name = name
        self.bpm = bpm
        self.speed = speed
        self.patterns = [{} for _ in range(num_patterns)]
        self.pat_rows = [64] * num_patterns
        self.orders = []
        self.loop_start = 0

    def set_cell(self, pat, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
        if row < 0 or row >= self.pat_rows[pat]:
            return
        key = (row, ch)
        cell = self.patterns[pat].get(key, {})
        if note is not None:
            cell['note'] = note_to_xm(note)
        if inst is not None:
            cell['instrument'] = inst
        if vol is not None:
            cell['volume'] = vol
        if fx is not None:
            cell['effect'] = fx
        if param is not None:
            cell['effect_param'] = param
        self.patterns[pat][key] = cell

    def v(self, vol64):
        return 0x10 + max(0, min(64, int(round(vol64))))

    def put_phrase(self, pat, ch, inst, events, vol_scale=0.61, vib=None, echo_ch=None, echo_delay=3, echo_vol=0.38, porta_speed=0x20, pan_override=None, echo_pan=192):
        for i, ev in enumerate(events):
            row = ev[0]
            note = ev[1]
            dur = ev[2]
            vol64 = int(round(ev[3] * vol_scale))
            mode = ev[4] if len(ev) > 4 else None

            if note == 'off':
                self.set_cell(pat, row, ch, note=97)
                continue

            if mode == 'slide':
                self.set_cell(pat, row, ch, note=note, vol=self.v(vol64), fx=3, param=porta_speed)
                if dur >= 4:
                    self.set_cell(pat, row + 1, ch, fx=3, param=porta_speed)
                    self.set_cell(pat, row + 2, ch, fx=3, param=porta_speed)
            else:
                self.set_cell(pat, row, ch, note=note, inst=inst, vol=self.v(vol64))
                if pan_override is not None:
                    self.set_cell(pat, row, ch, fx=8, param=pan_override)

            if vib is not None and dur >= 6:
                start_v = 3 if mode == 'slide' else 2
                for vr in range(row + start_v, min(row + dur - 1, 64)):
                    self.set_cell(pat, vr, ch, fx=4, param=vib)

            end_row = row + dur
            if mode == 'cut' and end_row < 64:
                self.set_cell(pat, end_row, ch, note=97)
            elif i == len(events) - 1 and end_row < 64:
                if dur >= 4:
                    self.set_cell(pat, end_row - 1, ch, fx=10, param=0x0A)
                self.set_cell(pat, end_row, ch, note=97)

            if echo_ch is not None and note != 'off':
                er = row + echo_delay
                if er < 64:
                    ev_vol = max(5, int(round(vol64 * echo_vol)))
                    self.set_cell(pat, er, echo_ch, note=note, inst=inst, vol=self.v(ev_vol), fx=8, param=echo_pan)
                    if er + min(dur, 4) < 64:
                        self.set_cell(pat, er + min(dur, 4), echo_ch, note=97)

    def put_drums_standard(self, pat, style='drive', fill='none'):
        for bar in range(2):
            off = bar * 32
            if style == 'drive':
                kicks = [0, 8, 16, 22, 24] if bar == 0 else [0, 8, 14, 16, 24]
            elif style == 'drive2':
                kicks = [0, 6, 8, 16, 22, 24] if bar == 0 else [0, 8, 14, 16, 22, 24]
            elif style == 'chorus':
                kicks = [0, 6, 8, 16, 22, 24] if bar == 0 else [0, 6, 8, 14, 16, 24]
            elif style == 'solo':
                kicks = [0, 6, 8, 12, 16, 22, 24, 28]
            elif style == 'halftime':
                kicks = [0, 20]
            elif style == 'build':
                kicks = [0, 8, 16, 24]
            else:
                kicks = []

            for r in kicks:
                if bar == 1 and fill == 'tom_run' and r >= 24:
                    continue
                kv = 25 if style == 'halftime' else (38 if r % 8 == 0 else 32)
                self.set_cell(pat, off + r, 0, note='C-4', inst=KICK, vol=self.v(kv))

            if style in ('drive', 'drive2', 'chorus', 'solo'):
                for r in [8, 24]:
                    if bar == 1 and fill in ('snare_roll', 'tom_run') and r == 24:
                        continue
                    self.set_cell(pat, off + r, 1, note='C-4', inst=SNARE, vol=self.v(40))
                for gr, gv in [(14, 22), (18, 19), (30, 24)]:
                    if bar == 1 and fill != 'none' and gr >= 24:
                        continue
                    self.set_cell(pat, off + gr, 1, note='C-4', inst=GHOST, vol=self.v(gv))
            elif style == 'halftime':
                self.set_cell(pat, off + 16, 1, note='C-4', inst=GHOST, vol=self.v(24))

            if style in ('drive', 'drive2', 'chorus', 'solo'):
                for r in range(0, 32, 2):
                    if bar == 1 and fill == 'break_stop' and r >= 24:
                        continue
                    if r % 8 == 4:
                        if r in (12, 28) and style != 'solo':
                            self.set_cell(pat, off + r, 2, note='C-4', inst=HHO, vol=self.v(38 if 'drive' in style else 44))
                        else:
                            self.set_cell(pat, off + r, 2, note='C-4', inst=HHC, vol=self.v(44))
                    elif r % 4 == 0:
                        self.set_cell(pat, off + r, 2, note='C-4', inst=HHC, vol=self.v(34))
                    else:
                        self.set_cell(pat, off + r, 2, note='C-4', inst=HHC, vol=self.v(22 if 'drive' in style else 28))
            elif style == 'halftime':
                for r in range(0, 32, 4):
                    self.set_cell(pat, off + r, 2, note='C-4', inst=HHC, vol=self.v(24 if r % 8 == 0 else 16))
            elif style == 'build':
                for r in range(0, 32, 2):
                    self.set_cell(pat, off + r, 2, note='C-4', inst=HHC, vol=self.v(16 + r // 2))

        if fill == 'snare_roll':
            self.set_cell(pat, 48, 1, note='C-4', inst=SNARE, vol=self.v(42))
            for idx, r in enumerate(range(52, 64, 2)):
                self.set_cell(pat, r, 1, note='C-4', inst=GHOST if idx < 3 else SNARE, vol=self.v(28 + idx * 4))
            self.set_cell(pat, 57, 1, note='C-4', inst=GHOST, vol=self.v(34))
            self.set_cell(pat, 59, 1, note='C-4', inst=GHOST, vol=self.v(38))
            self.set_cell(pat, 61, 1, note='C-4', inst=SNARE, vol=self.v(40))
            self.set_cell(pat, 63, 1, note='C-4', inst=SNARE, vol=self.v(40))
        elif fill == 'tom_run':
            self.set_cell(pat, 52, 1, note='G-4', inst=TOM, vol=self.v(44))
            self.set_cell(pat, 54, 1, note='E-4', inst=TOM, vol=self.v(44))
            self.set_cell(pat, 56, 1, note='D-4', inst=TOM, vol=self.v(46))
            self.set_cell(pat, 58, 1, note='C-4', inst=TOM, vol=self.v(46))
            self.set_cell(pat, 60, 1, note='A-3', inst=TOM, vol=self.v(48))
            self.set_cell(pat, 62, 1, note='C-4', inst=SNARE, vol=self.v(40))
        elif fill == 'snare_pick':
            self.set_cell(pat, 56, 1, note='C-4', inst=SNARE, vol=self.v(46))
            self.set_cell(pat, 60, 1, note='C-4', inst=GHOST, vol=self.v(34))
            self.set_cell(pat, 62, 1, note='C-4', inst=SNARE, vol=self.v(40))

    def put_crash(self, pat, row=0, ch=9, vol64=26):
        self.set_cell(pat, row, ch, note='C-4', inst=CRASH, vol=self.v(vol64))

    def put_bass_groove(self, pat, chords_rows, style='octave_plk', vol_scale=0.77):
        for start, end, root in chords_rows:
            r_xm = note_to_xm(root)
            hi_xm = r_xm + 12
            fifth_xm = r_xm + 7
            if style == 'octave_plk':
                pat8 = [0, 0, 12, 0, 0, 12, 0, 12]
                for r in range(start, end, 2):
                    step = (r // 2) % 8
                    if (r % 32) == 30:
                        n, v = fifth_xm, 38
                    else:
                        n = r_xm + pat8[step]
                        v = 45 if step in (0, 2, 5) else 35
                    self.set_cell(pat, r, 3, note=n, inst=BASS_PLK, vol=self.v(v * vol_scale))
            elif style == 'drive_mix':
                for r in range(start, end, 2):
                    step = (r // 2) % 8
                    if step in (0, 4):
                        self.set_cell(pat, r, 3, note=r_xm, inst=BASS_DRV, vol=self.v(42 * vol_scale))
                    elif step in (2, 6):
                        self.set_cell(pat, r, 3, note=hi_xm, inst=BASS_PLK, vol=self.v(42 * vol_scale))
                    elif step in (3, 7):
                        self.set_cell(pat, r, 3, note=r_xm, inst=BASS_PLK, vol=self.v(35 * vol_scale))
                    elif step == 5:
                        self.set_cell(pat, r, 3, note=hi_xm if (r % 32) < 24 else fifth_xm, inst=BASS_PLK, vol=self.v(38 * vol_scale))
            elif style == 'pulse_8th':
                for r in range(start, end, 4):
                    self.set_cell(pat, r, 3, note=r_xm, inst=BASS_PLK, vol=self.v((32 if (r % 8 == 0) else 24) * vol_scale))

    def put_arp_chord_stream(self, pat, ch, chords, inst=ARP_P25, vol64=26, pulse_every=4):
        for start, end, base, s1, s2 in chords:
            p = ((s2 & 0xF) << 4) | (s1 & 0xF)
            for r in range(start, end):
                if (r - start) % pulse_every == 0:
                    self.set_cell(pat, r, ch, note=base, inst=inst, vol=self.v(vol64), fx=0, param=p)
                else:
                    self.set_cell(pat, r, ch, fx=0, param=p)
            if end < 64:
                self.set_cell(pat, end, ch, note=97)
            else:
                self.set_cell(pat, 63, ch, fx=10, param=0x08)

    def put_broken_harp(self, pat, ch, chords, inst=ARP_BELL, vol64=32, step=2, pan_override=None):
        for start, end, notes in chords:
            idx = 0
            for r in range(start, end, step):
                n = notes[idx % len(notes)]
                acc = 1.0 if (r % 8 == 0) else (0.85 if idx % len(notes) == 0 else 0.72)
                self.set_cell(pat, r, ch, note=n, inst=inst, vol=self.v(vol64 * acc))
                if pan_override is not None:
                    self.set_cell(pat, r, ch, fx=8, param=pan_override)
                idx += 1

    def put_pad(self, pat, ch, chords, vol64=22, pan=None):
        for start, end, note in chords:
            self.set_cell(pat, start, ch, note=note, inst=PAD_TRI, vol=self.v(vol64))
            if pan is not None:
                self.set_cell(pat, start, ch, fx=8, param=pan)
            if end - 2 >= start:
                self.set_cell(pat, end - 2, ch, fx=10, param=0x06)
            if end < 64:
                self.set_cell(pat, end, ch, note=97)
            else:
                self.set_cell(pat, 63, ch, note=97)


def build_song():
    s = SongBuilder(num_patterns=34, channels=10, name="Astral Keysmith", bpm=138, speed=3)

    # Init tempo & clean channel state on Pat 0 AND Pat 2 (loop_start!)
    s.set_cell(0, 0, 0, fx=15, param=3)
    s.set_cell(0, 0, 1, fx=15, param=138)
    s.set_cell(2, 0, 0, fx=15, param=3)
    s.set_cell(2, 0, 1, fx=15, param=138)
    # Silence any lingering Ch 7/Ch 8 voices upon entering Pat 2 (loop_start)
    s.set_cell(2, 0, 7, note=97)
    s.set_cell(2, 0, 8, note=97)

    # =========================================================================
    # INTRO (Pat 0..1)
    # =========================================================================
    s.put_pad(0, 5, [(0, 64, 'D-4')], vol64=22, pan=64)
    s.put_pad(0, 8, [(0, 64, 'A-4')], vol64=22, pan=192)
    s.put_broken_harp(0, 4, [
        (0, 32, ['D-5', 'E-5', 'F-5', 'A-5', 'E-5', 'F-5', 'A-5', 'D-6']),
        (32, 64, ['C-5', 'E-5', 'F-5', 'A-5', 'E-5', 'F-5', 'A-5', 'C-6']),
    ], inst=ARP_BELL, vol64=30, step=4)
    s.put_bass_groove(0, [(0, 32, 'D-2'), (32, 64, 'C-2')], style='pulse_8th', vol_scale=0.85)
    for r in range(0, 64, 4):
        s.set_cell(0, r, 2, note='C-4', inst=HHC, vol=s.v(16 + r // 3))

    s.put_pad(1, 5, [(0, 32, 'Bb3'), (32, 64, 'A-3')], vol64=24, pan=64)
    s.put_pad(1, 8, [(0, 32, 'F-4'), (32, 64, 'E-4')], vol64=24, pan=192)
    s.put_arp_chord_stream(1, 4, [
        (0, 32, 'Bb4', 4, 7),
        (32, 48, 'A-4', 5, 7),
        (48, 64, 'A-4', 4, 7),
    ], inst=ARP_P25, vol64=26, pulse_every=4)
    s.put_broken_harp(1, 9, [
        (0, 32, ['F-5', 'A-5', 'Bb5', 'D-6']),
        (32, 48, ['E-5', 'A-5', 'D-6', 'E-6']),
        (48, 62, ['E-5', 'A-5', 'C#6', 'E-6']),
    ], inst=ARP_BELL, vol64=34, step=2)
    s.put_bass_groove(1, [(0, 32, 'Bb1'), (32, 64, 'A-1')], style='octave_plk', vol_scale=0.9)
    s.put_drums_standard(1, style='build', fill='snare_roll')
    s.set_cell(1, 32, 2, note='C-4', inst=FX_SWEEP, vol=s.v(34))
    s.put_phrase(1, 6, LEAD_PWM, [
        (56, 'A-4', 2, 46),
        (58, 'Bb4', 2, 50),
        (60, 'C#5', 4, 56, 'slide'),
    ], vib=None, echo_ch=7, echo_delay=3, echo_vol=0.36, echo_pan=192)

    # =========================================================================
    # SECTION A1 & A2 — MAIN THEME (Pat 2..9)
    # =========================================================================
    def fill_section_A(pats, with_counter=False):
        p0, p1, p2, p3 = pats
        s.put_crash(p0, 0, ch=9, vol64=26)
        dstyle = 'drive2' if with_counter else 'drive'
        s.put_drums_standard(p0, style=dstyle, fill='none')
        s.put_drums_standard(p1, style=dstyle, fill='snare_pick')
        s.put_drums_standard(p2, style=dstyle, fill='none')
        s.put_drums_standard(p3, style=dstyle, fill='tom_run' if with_counter else 'snare_roll')

        bstyle = 'drive_mix' if with_counter else 'octave_plk'
        s.put_bass_groove(p0, [(0, 32, 'D-2'), (32, 64, 'C-2')], style=bstyle)
        s.put_bass_groove(p1, [(0, 32, 'Bb1'), (32, 48, 'G-2'), (48, 64, 'A-2')], style=bstyle)
        s.put_bass_groove(p2, [(0, 32, 'D-2'), (32, 64, 'C-2')], style=bstyle)
        s.put_bass_groove(p3, [(0, 32, 'Bb1'), (32, 48, 'C-2'), (48, 64, 'A-1' if with_counter else 'D-2')], style=bstyle)

        s.put_arp_chord_stream(p0, 4, [(0, 32, 'D-4', 3, 7), (32, 64, 'F-4', 4, 9)], inst=ARP_P25, vol64=25, pulse_every=4)
        s.put_arp_chord_stream(p1, 4, [(0, 32, 'Bb3', 4, 7), (32, 48, 'G-4', 3, 7), (48, 64, 'A-4', 4, 7)], inst=ARP_P25, vol64=25, pulse_every=4)
        s.put_arp_chord_stream(p2, 4, [(0, 32, 'D-4', 3, 7), (32, 64, 'F-4', 4, 7)], inst=ARP_P25, vol64=25, pulse_every=4)
        s.put_arp_chord_stream(p3, 4, [(0, 32, 'Bb3', 4, 7), (32, 48, 'C-4', 4, 7), (48, 64, 'A-4', 4, 7) if with_counter else (48, 64, 'D-4', 3, 7)], inst=ARP_P25, vol64=26, pulse_every=4)

        s.put_broken_harp(p0, 5, [(0, 32, ['D-5', 'F-5', 'A-5', 'D-6']), (32, 64, ['C-5', 'F-5', 'A-5', 'C-6'])], inst=ARP_BELL, vol64=30, step=4)
        s.put_broken_harp(p1, 5, [(0, 32, ['Bb4', 'D-5', 'F-5', 'Bb5']), (32, 48, ['G-4', 'Bb4', 'D-5', 'G-5']), (48, 64, ['A-4', 'C#5', 'E-5', 'A-5'])], inst=ARP_BELL, vol64=30, step=4)
        s.put_broken_harp(p2, 5, [(0, 32, ['D-5', 'F-5', 'A-5', 'F-5']), (32, 64, ['C-5', 'F-5', 'A-5', 'C-6'])], inst=ARP_BELL, vol64=30, step=4)
        s.put_broken_harp(p3, 5, [(0, 32, ['Bb4', 'D-5', 'F-5', 'D-5']), (32, 48, ['C-5', 'E-5', 'G-5', 'C-6']), (48, 64, ['A-4', 'C#5', 'E-5', 'A-5'] if with_counter else ['D-5', 'F-5', 'A-5', 'D-6'])], inst=ARP_BELL, vol64=32, step=4)

        echo = 7 if not with_counter else None
        s.put_phrase(p0, 6, LEAD_PWM, [
            (0,  'D-5', 10, 58), (10, 'F-5', 4,  54), (14, 'E-5', 8,  56),
            (22, 'C-5', 4,  52), (26, 'D-5', 6,  55), (32, 'A-4', 18, 58),
            (50, 'C-5', 4,  50), (54, 'D-5', 4,  53), (58, 'F-5', 6,  57, 'slide'),
        ], vib=0x53, echo_ch=echo, echo_delay=3, echo_vol=0.38, echo_pan=192)

        s.put_phrase(p1, 6, LEAD_PWM, [
            (0,  'G-5', 8,  60), (8,  'F-5', 4,  54), (12, 'E-5', 4,  54),
            (16, 'D-5', 8,  56), (24, 'Bb4', 8,  55), (32, 'G-4', 4,  50),
            (36, 'A-4', 4,  52), (40, 'Bb4', 4,  54), (44, 'D-5', 4,  56),
            (48, 'C#5', 14, 59), (62, 'D-5', 2,  52),
        ], vib=0x63, echo_ch=echo, echo_delay=3, echo_vol=0.38, echo_pan=192)

        s.put_phrase(p2, 6, LEAD_PWM, [
            (0,  'F-5', 10, 59), (10, 'G-5', 4,  56), (14, 'A-5', 10, 62, 'slide'),
            (24, 'G-5', 4,  56), (28, 'F-5', 4,  54), (32, 'E-5', 16, 58),
            (48, 'C-5', 4,  52), (52, 'D-5', 4,  54), (56, 'E-5', 8,  57),
        ], vib=0x54, echo_ch=echo, echo_delay=3, echo_vol=0.38, echo_pan=192)

        end_note = 'E-5' if with_counter else 'D-5'
        s.put_phrase(p3, 6, LEAD_PWM, [
            (0,  'D-5', 4,  56), (4,  'E-5', 4,  57), (8,  'F-5', 8,  59),
            (16, 'G-5', 8,  60), (24, 'E-5', 8,  57), (32, 'D-5', 12, 58),
            (44, 'C-5', 4,  54), (48, end_note, 12, 58), (60, 'C-5' if with_counter else 'A-4', 4, 52),
        ], vib=0x53, echo_ch=echo, echo_delay=3, echo_vol=0.38, echo_pan=192)

        if with_counter:
            s.put_phrase(p0, 8, LEAD_BELL, [
                (8,  'A-5', 6, 36), (20, 'G-5', 6, 36), (36, 'E-5', 8, 38), (48, 'F-5', 8, 40),
            ])
            s.put_phrase(p1, 8, LEAD_BELL, [
                (4,  'D-6', 6, 38), (16, 'Bb5', 8, 38), (32, 'D-5', 8, 36), (48, 'A-5', 12, 40),
            ])
            s.put_phrase(p2, 7, LEAD_SAW, [
                (0,  'D-5', 10, 44), (10, 'E-5', 4,  42), (14, 'F-5', 10, 48, 'slide'),
                (24, 'E-5', 4,  42), (28, 'D-5', 4,  42), (32, 'C-5', 16, 45),
                (48, 'A-4', 4,  40), (52, 'Bb4', 4,  42), (56, 'C-5', 8,  45),
            ], vib=0x54, pan_override=176)
            s.put_phrase(p3, 7, LEAD_SAW, [
                (0,  'Bb4', 4,  42), (4,  'C-5', 4,  44), (8,  'D-5', 8,  46),
                (16, 'E-5', 8,  48), (24, 'C-5', 8,  44), (32, 'Bb4', 12, 46),
                (44, 'A-4', 4,  42), (48, 'C#5', 12, 48), (60, 'A-4', 4,  42),
            ], vib=0x53, pan_override=176)
            s.set_cell(p3, 48, 2, note='C-4', inst=FX_SWEEP, vol=s.v(34))

    fill_section_A([2, 3, 4, 5], with_counter=False)
    fill_section_A([6, 7, 8, 9], with_counter=True)

    # =========================================================================
    # SECTION B1, B2 & D1 — UPLIFTING F MAJOR CHORUS
    # =========================================================================
    def fill_chorus(pats, pivot_to_minor=False, add_upper_bell=False, climax_variation=False, intro_half_echo=False):
        p0, p1, p2, p3 = pats
        s.put_crash(p0, 0, ch=9, vol64=26)
        s.put_crash(p2, 0, ch=9, vol64=26)

        s.put_drums_standard(p0, style='chorus', fill='none')
        s.put_drums_standard(p1, style='chorus', fill='tom_run' if climax_variation else 'snare_pick')
        s.put_drums_standard(p2, style='chorus', fill='none')
        s.put_drums_standard(p3, style='chorus', fill='snare_roll' if pivot_to_minor else 'tom_run')

        s.put_bass_groove(p0, [(0, 32, 'F-2'), (32, 64, 'E-2')], style='drive_mix')
        s.put_bass_groove(p1, [(0, 32, 'D-2'), (32, 64, 'Bb1')], style='drive_mix')
        s.put_bass_groove(p2, [(0, 32, 'F-2'), (32, 48, 'C-2'), (48, 64, 'D-2')], style='drive_mix')
        if pivot_to_minor:
            s.put_bass_groove(p3, [(0, 24, 'Bb1'), (24, 40, 'C-2'), (40, 64, 'A-1')], style='drive_mix')
        else:
            s.put_bass_groove(p3, [(0, 24, 'Bb1'), (24, 48, 'C-2'), (48, 64, 'F-2')], style='drive_mix')

        s.put_arp_chord_stream(p0, 4, [(0, 32, 'F-4', 4, 7), (32, 64, 'E-4', 3, 8)], inst=ARP_P25, vol64=26, pulse_every=4)
        s.put_arp_chord_stream(p1, 4, [(0, 32, 'D-4', 3, 7), (32, 64, 'Bb3', 4, 7)], inst=ARP_P25, vol64=26, pulse_every=4)
        s.put_arp_chord_stream(p2, 4, [(0, 32, 'F-4', 4, 7), (32, 48, 'C-4', 4, 7), (48, 64, 'D-4', 3, 7)], inst=ARP_P25, vol64=26, pulse_every=4)
        if pivot_to_minor:
            s.put_arp_chord_stream(p3, 4, [(0, 24, 'Bb3', 4, 7), (24, 40, 'C-4', 4, 7), (40, 64, 'A-4', 4, 7)], inst=ARP_P25, vol64=27, pulse_every=4)
        else:
            s.put_arp_chord_stream(p3, 4, [(0, 24, 'Bb3', 4, 7), (24, 48, 'C-4', 4, 7), (48, 64, 'F-4', 4, 7)], inst=ARP_P25, vol64=27, pulse_every=4)

        s.put_broken_harp(p0, 5, [(0, 32, ['F-5', 'A-5', 'C-6', 'A-5']), (32, 64, ['E-5', 'G-5', 'C-6', 'G-5'])], inst=ARP_BELL, vol64=30, step=2)
        s.put_broken_harp(p1, 5, [(0, 32, ['D-5', 'F-5', 'A-5', 'C-6']), (32, 64, ['Bb4', 'D-5', 'F-5', 'C-6'])], inst=ARP_BELL, vol64=30, step=2)
        s.put_broken_harp(p2, 5, [(0, 32, ['F-5', 'A-5', 'C-6', 'F-6']), (32, 48, ['E-5', 'G-5', 'C-6', 'E-6']), (48, 64, ['D-5', 'F-5', 'A-5', 'D-6'])], inst=ARP_BELL, vol64=32, step=2)
        if pivot_to_minor:
            s.put_broken_harp(p3, 5, [(0, 24, ['Bb4', 'D-5', 'F-5', 'Bb5']), (24, 40, ['C-5', 'E-5', 'G-5', 'C-6']), (40, 64, ['A-4', 'C#5', 'E-5', 'A-5'])], inst=ARP_BELL, vol64=34, step=2)
        else:
            s.put_broken_harp(p3, 5, [(0, 24, ['Bb4', 'D-5', 'F-5', 'Bb5']), (24, 48, ['C-5', 'E-5', 'G-5', 'C-6']), (48, 64, ['F-5', 'A-5', 'C-6', 'F-6'])], inst=ARP_BELL, vol64=34, step=2)

        # p0 melody
        s.put_phrase(p0, 6, LEAD_PWM, [
            (0,  'C-5', 4,  55), (4,  'F-5', 8,  60), (12, 'G-5', 4,  58),
            (16, 'A-5', 10, 62, 'slide'), (26, 'G-5', 6,  56), (32, 'E-5', 12, 58),
            (44, 'C-5', 6,  54), (50, 'D-5', 6,  55), (56, 'E-5', 8,  58),
        ], vib=0x63, echo_ch=7 if intro_half_echo else None, echo_delay=3, echo_vol=0.35, echo_pan=192)
        if not intro_half_echo:
            s.put_phrase(p0, 7, LEAD_SAW, [
                (0,  'A-4', 4,  42), (4,  'C-5', 8,  46), (12, 'E-5', 4,  45),
                (16, 'F-5', 10, 48, 'slide'), (26, 'E-5', 6,  44), (32, 'C-5', 12, 46),
                (44, 'G-4', 6,  42), (50, 'Bb4', 6,  43), (56, 'C-5', 8,  46),
            ], vib=0x63, pan_override=176)

        # p1 melody
        s.put_phrase(p1, 6, LEAD_PWM, [
            (0,  'F-5', 10, 60), (10, 'E-5', 4,  56), (14, 'D-5', 6,  56),
            (20, 'A-4', 6,  54), (26, 'C-5', 6,  55), (32, 'D-5', 12, 58),
            (44, 'F-5', 6,  58), (50, 'G-5', 6,  59), (56, 'A-5', 8,  62, 'slide'),
        ], vib=0x54, echo_ch=7 if intro_half_echo else None, echo_delay=3, echo_vol=0.35, echo_pan=192)
        if not intro_half_echo:
            s.put_phrase(p1, 7, LEAD_SAW, [
                (0,  'D-5', 10, 46), (10, 'C-5', 4,  43), (14, 'A-4', 6,  43),
                (20, 'F-4', 6,  42), (26, 'A-4', 6,  43), (32, 'Bb4', 12, 46),
                (44, 'D-5', 6,  46), (50, 'E-5', 6,  47), (56, 'F-5', 8,  48, 'slide'),
            ], vib=0x54, pan_override=176)

        # p2: Soaring peak (climax_variation pushes up to C-6 -> D-6!)
        if climax_variation:
            s.put_phrase(p2, 6, LEAD_PWM, [
                (0,  'A-5', 6,  61), (6,  'C-6', 10, 63, 'slide'),
                (16, 'D-6', 8,  64, 'slide'), (24, 'C-6', 8,  60),
                (32, 'G-5', 8,  59), (40, 'A-5', 4,  58), (44, 'G-5', 4,  56),
                (48, 'F-5', 8,  58), (56, 'A-5', 8,  60),
            ], vib=0x64)
            s.put_phrase(p2, 7, LEAD_SAW, [
                (0,  'F-5', 6,  48), (6,  'A-5', 10, 50, 'slide'),
                (16, 'Bb5', 8,  52, 'slide'), (24, 'A-5', 8,  48),
                (32, 'E-5', 8,  47), (40, 'F-5', 4,  46), (44, 'E-5', 4,  44),
                (48, 'D-5', 8,  46), (56, 'F-5', 8,  48),
            ], vib=0x64, pan_override=176)
        else:
            s.put_phrase(p2, 6, LEAD_PWM, [
                (0,  'A-5', 8,  62), (8,  'Bb5', 8,  63, 'slide'),
                (16, 'A-5', 8,  61), (24, 'F-5', 8,  58),
                (32, 'G-5', 10, 60), (42, 'E-5', 6,  56),
                (48, 'F-5', 8,  58), (56, 'D-5', 8,  56),
            ], vib=0x64)
            s.put_phrase(p2, 7, LEAD_SAW, [
                (0,  'F-5', 8,  48), (8,  'G-5', 8,  50, 'slide'),
                (16, 'F-5', 8,  48), (24, 'C-5', 8,  46),
                (32, 'E-5', 10, 48), (42, 'C-5', 6,  44),
                (48, 'D-5', 8,  46), (56, 'A-4', 8,  44),
            ], vib=0x64, pan_override=176)

        if pivot_to_minor:
            s.put_phrase(p3, 6, LEAD_PWM, [
                (0,  'D-5', 8,  58), (8,  'F-5', 8,  60),
                (16, 'Bb5', 8,  62), (24, 'G-5', 8,  59),
                (32, 'E-5', 8,  58), (40, 'C#5', 14, 60),
                (54, 'E-5', 4,  56), (58, 'A-5', 6,  62, 'slide'),
            ], vib=0x64)
            s.put_phrase(p3, 7, LEAD_SAW, [
                (0,  'Bb4', 8,  46), (8,  'D-5', 8,  47),
                (16, 'G-5', 8,  49), (24, 'E-5', 8,  47),
                (32, 'C-5', 8,  46), (40, 'A-4', 14, 48),
                (54, 'C#5', 4,  45), (58, 'E-5', 6,  49, 'slide'),
            ], vib=0x64, pan_override=176)
            s.set_cell(p3, 44, 2, note='C-4', inst=FX_SWEEP, vol=s.v(34))
        else:
            s.put_phrase(p3, 6, LEAD_PWM, [
                (0,  'D-5', 8,  58), (8,  'F-5', 8,  60),
                (16, 'G-5', 8,  60), (24, 'E-5', 8,  58),
                (32, 'C-5', 8,  56), (40, 'E-5', 8,  58),
                (48, 'F-5', 14, 61), (62, 'C-5', 2,  52),
            ], vib=0x53)
            s.put_phrase(p3, 7, LEAD_SAW, [
                (0,  'Bb4', 8,  46), (8,  'D-5', 8,  47),
                (16, 'E-5', 8,  47), (24, 'C-5', 8,  46),
                (32, 'G-4', 8,  44), (40, 'C-5', 8,  46),
                (48, 'A-4', 14, 48), (62, 'A-4', 2,  40),
            ], vib=0x53, pan_override=176)

        if add_upper_bell:
            if climax_variation:
                # Sparkling 16th-note counter-arpeggio flourishes in Final Chorus!
                s.put_phrase(p0, 8, LEAD_BELL, [
                    (0, 'F-6', 4, 46), (8, 'C-6', 4, 44), (16, 'A-5', 4, 44), (24, 'F-6', 6, 48),
                    (32, 'E-6', 4, 46), (40, 'C-6', 4, 44), (48, 'G-5', 4, 42), (56, 'E-6', 6, 48),
                ])
                s.put_phrase(p1, 8, LEAD_BELL, [
                    (0, 'D-6', 4, 46), (8, 'A-5', 4, 44), (16, 'F-5', 4, 42), (24, 'C-6', 6, 46),
                    (32, 'Bb5', 4, 46), (40, 'D-6', 4, 46), (48, 'F-6', 4, 48), (56, 'D-6', 6, 48),
                ])
                s.put_phrase(p2, 8, LEAD_BELL, [
                    (0, 'C-6', 4, 46), (8, 'F-6', 4, 48), (16, 'Bb5', 4, 46), (24, 'F-6', 6, 48),
                    (32, 'C-6', 4, 46), (40, 'E-6', 4, 46), (48, 'D-6', 4, 46), (56, 'A-6' if False else 'F-6', 6, 48),
                ])
                s.put_phrase(p3, 8, LEAD_BELL, [
                    (0, 'D-6', 6, 46), (16, 'G-6', 6, 48), (32, 'E-6', 6, 46), (48, 'A-5', 10, 48),
                ])
            else:
                for p_idx, bell_notes in [
                    (p0, [(0, 'C-6', 8, 42), (16, 'F-6', 8, 44), (32, 'C-6', 8, 42), (48, 'G-6', 8, 44)]),
                    (p1, [(0, 'A-5', 8, 42), (16, 'F-6', 8, 44), (32, 'D-6', 8, 42), (48, 'Bb5', 8, 42)]),
                    (p2, [(0, 'F-6', 8, 45), (16, 'C-6', 8, 42), (32, 'E-6', 8, 44), (48, 'D-6', 8, 42)]),
                    (p3, [(0, 'D-6', 8, 42), (24, 'E-6', 8, 44), (48, 'A-5' if pivot_to_minor else 'F-6', 12, 46)]),
                ]:
                    s.put_phrase(p_idx, 8, LEAD_BELL, bell_notes)

    fill_chorus([10, 11, 12, 13], pivot_to_minor=False, add_upper_bell=False, intro_half_echo=True)
    fill_chorus([14, 15, 16, 17], pivot_to_minor=True, add_upper_bell=True)

    # =========================================================================
    # SECTION C1 — ATMOSPHERIC BREAKDOWN (Pat 18..21) — deeper dynamic breath!
    # =========================================================================
    s.put_crash(18, 0, ch=9, vol64=26)
    s.put_pad(18, 5, [(0, 32, 'G-4'), (32, 64, 'G-4')], vol64=18, pan=64)
    s.put_pad(18, 8, [(0, 32, 'Bb4'), (32, 64, 'E-4')], vol64=18, pan=192)
    s.put_broken_harp(18, 4, [
        (0, 32, ['G-4', 'A-4', 'Bb4', 'D-5', 'F-5', 'D-5', 'Bb4', 'A-4']),
        (32, 64, ['C-5', 'E-5', 'G-5', 'Bb5', 'A-5', 'G-5', 'E-5', 'C-5']),
    ], inst=ARP_BELL, vol64=24, step=4, pan_override=68)
    s.put_bass_groove(18, [(0, 32, 'G-2'), (32, 64, 'C-2')], style='pulse_8th', vol_scale=0.72)
    s.put_drums_standard(18, style='halftime', fill='none')
    s.put_phrase(18, 6, LEAD_BELL, [
        (0,  'D-5', 12, 52), (12, 'F-5', 8,  50), (20, 'A-5', 12, 54),
        (32, 'G-5', 10, 52), (42, 'E-5', 6,  48), (48, 'D-5', 16, 50),
    ], pan_override=168, echo_ch=7, echo_delay=6, echo_vol=0.40, echo_pan=72)

    s.put_pad(19, 5, [(0, 32, 'F-4'), (32, 64, 'D-4')], vol64=18, pan=64)
    s.put_pad(19, 8, [(0, 32, 'A-4'), (32, 64, 'A-4')], vol64=18, pan=192)
    s.put_broken_harp(19, 4, [
        (0, 32, ['F-4', 'A-4', 'C-5', 'E-5', 'A-5', 'E-5', 'C-5', 'A-4']),
        (32, 64, ['D-4', 'F-4', 'A-4', 'C-5', 'F-5', 'C-5', 'A-4', 'F-4']),
    ], inst=ARP_BELL, vol64=24, step=4, pan_override=68)
    s.put_bass_groove(19, [(0, 32, 'F-2'), (32, 64, 'D-2')], style='pulse_8th', vol_scale=0.72)
    s.put_drums_standard(19, style='halftime', fill='none')
    s.put_phrase(19, 6, LEAD_BELL, [
        (0,  'E-5', 12, 52), (12, 'C-5', 8,  48), (20, 'A-4', 12, 50),
        (32, 'C-5', 8,  50), (40, 'D-5', 8,  52), (48, 'F-5', 16, 54),
    ], pan_override=168, echo_ch=7, echo_delay=6, echo_vol=0.40, echo_pan=72)

    s.put_pad(20, 5, [(0, 32, 'Bb3'), (32, 64, 'G-4')], vol64=20, pan=64)
    s.put_pad(20, 8, [(0, 32, 'D-4'), (32, 64, 'Bb4')], vol64=20, pan=192)
    s.put_arp_chord_stream(20, 4, [(0, 32, 'Bb3', 4, 7), (32, 64, 'G-4', 3, 7)], inst=ARP_P25, vol64=24, pulse_every=4)
    s.put_bass_groove(20, [(0, 32, 'Bb1'), (32, 64, 'G-2')], style='octave_plk', vol_scale=0.85)
    s.put_drums_standard(20, style='build', fill='none')
    s.put_phrase(20, 6, LEAD_PWM, [
        (0,  'D-5', 12, 48), (12, 'F-5', 8,  50), (20, 'A-5', 12, 54, 'slide'),
        (32, 'G-5', 12, 52), (44, 'Bb5', 8,  55), (52, 'G-5', 12, 53),
    ], vib=0x53, echo_ch=7, echo_delay=3, echo_vol=0.35, echo_pan=192)

    s.put_pad(21, 5, [(0, 64, 'A-3')], vol64=20, pan=64)
    s.put_pad(21, 8, [(0, 64, 'E-4')], vol64=20, pan=192)
    s.put_arp_chord_stream(21, 4, [(0, 32, 'A-4', 5, 7), (32, 64, 'A-4', 4, 7)], inst=ARP_P25, vol64=26, pulse_every=4)
    s.put_bass_groove(21, [(0, 64, 'A-1')], style='octave_plk', vol_scale=0.95)
    s.put_drums_standard(21, style='build', fill='snare_roll')
    s.set_cell(21, 24, 2, note='C-4', inst=FX_SWEEP, vol=s.v(36))
    s.put_phrase(21, 6, LEAD_PWM, [
        (0,  'D-5', 12, 52), (12, 'E-5', 12, 55), (24, 'C#5', 16, 58),
        (40, 'E-5', 8,  56), (48, 'A-5', 12, 62, 'slide'), (60, 'G-5', 2,  56), (62, 'E-5', 2,  58),
    ], vib=0x64, echo_ch=7, echo_delay=3, echo_vol=0.35, echo_pan=192)

    # =========================================================================
    # SECTION C2 — VIRTUOSO KEYGEN CHIP SOLO (Pat 22..25)
    # =========================================================================
    s.put_crash(22, 0, ch=9, vol64=26)
    for p in (22, 23, 24, 25):
        s.put_drums_standard(p, style='solo', fill='tom_run' if p == 25 else ('snare_pick' if p == 23 else 'none'))

    s.put_bass_groove(22, [(0, 32, 'D-2'), (32, 64, 'C-2')], style='drive_mix', vol_scale=0.92)
    s.put_bass_groove(23, [(0, 32, 'Bb1'), (32, 64, 'A-1')], style='drive_mix', vol_scale=0.92)
    s.put_bass_groove(24, [(0, 32, 'G-2'), (32, 64, 'F-2')], style='drive_mix', vol_scale=0.92)
    s.put_bass_groove(25, [(0, 32, 'E-2'), (32, 64, 'A-1')], style='drive_mix', vol_scale=0.95)

    s.put_arp_chord_stream(22, 4, [(0, 32, 'D-4', 3, 7), (32, 64, 'C-4', 4, 7)], inst=ARP_P25, vol64=25, pulse_every=4)
    s.put_arp_chord_stream(23, 4, [(0, 32, 'Bb3', 4, 7), (32, 64, 'A-4', 4, 7)], inst=ARP_P25, vol64=25, pulse_every=4)
    s.put_arp_chord_stream(24, 4, [(0, 32, 'G-4', 3, 7), (32, 64, 'F-4', 4, 9)], inst=ARP_P25, vol64=25, pulse_every=4)
    s.put_arp_chord_stream(25, 4, [(0, 32, 'E-4', 4, 7), (32, 64, 'A-4', 4, 7)], inst=ARP_P25, vol64=26, pulse_every=4)

    solo_22 = [
        (0, 'D-5', 2, 58), (2, 'F-5', 2, 56), (4, 'A-5', 2, 60), (6, 'D-6', 4, 62),
        (10, 'C-6', 2, 58), (12, 'Bb5', 2, 57), (14, 'A-5', 2, 58), (16, 'F-5', 4, 56),
        (20, 'G-5', 2, 56), (22, 'A-5', 2, 58), (24, 'Bb5', 2, 59), (26, 'A-5', 2, 58),
        (28, 'G-5', 2, 56), (30, 'F-5', 2, 55),
        (32, 'E-5', 4, 58), (36, 'G-5', 2, 57), (38, 'C-6', 4, 61),
        (42, 'B-5', 2, 58), (44, 'A-5', 2, 57), (46, 'G-5', 2, 56),
        (48, 'E-5', 2, 55), (50, 'G-5', 2, 56), (52, 'C-6', 2, 60), (54, 'E-6', 4, 62),
        (58, 'D-6', 2, 58), (60, 'C-6', 4, 58),
    ]
    s.put_phrase(22, 6, LEAD_PWM, solo_22, vib=0x53, echo_ch=7, echo_delay=3, echo_vol=0.32, echo_pan=192)

    solo_23 = [
        (0, 'D-6', 4, 61), (4, 'Bb5', 2, 58), (6, 'F-5', 2, 56),
        (8, 'D-5', 2, 55), (10, 'F-5', 2, 56), (12, 'Bb5', 2, 58), (14, 'D-6', 2, 61),
        (16, 'C-6', 2, 59), (18, 'Bb5', 2, 58), (20, 'A-5', 2, 58), (22, 'G-5', 2, 56),
        (24, 'F-5', 4, 56), (28, 'D-5', 4, 54),
        (32, 'C#5', 2, 56), (34, 'A-5', 2, 60), (36, 'D-5', 2, 56), (38, 'A-5', 2, 60),
        (40, 'E-5', 2, 58), (42, 'A-5', 2, 60), (44, 'F-5', 2, 58), (46, 'A-5', 2, 60),
        (48, 'G-5', 2, 59), (50, 'A-5', 2, 61), (52, 'Bb5', 4, 62, 'slide'), (56, 'A-5', 8, 61),
    ]
    s.put_phrase(23, 6, LEAD_PWM, solo_23, vib=0x63, echo_ch=7, echo_delay=3, echo_vol=0.32, echo_pan=192)

    solo_24 = [
        (0, 'G-5', 4, 60), (4, 'Bb5', 4, 61), (8, 'D-6', 6, 63),
        (14, 'C-6', 1, 56), (15, 'D-6', 1, 58), (16, 'C-6', 2, 58), (18, 'Bb5', 2, 57),
        (20, 'A-5', 2, 56), (22, 'G-5', 2, 55), (24, 'F-5', 4, 56), (28, 'G-5', 4, 57),
        (32, 'A-5', 6, 60), (38, 'F-5', 2, 56), (40, 'D-5', 4, 56), (44, 'A-4', 4, 54),
        (48, 'D-5', 2, 56), (50, 'F-5', 2, 58), (52, 'A-5', 2, 60), (54, 'D-6', 4, 62),
        (58, 'C-6', 2, 58), (60, 'A-5', 4, 58),
    ]
    s.put_phrase(24, 6, LEAD_PWM, solo_24, vib=0x53, echo_ch=7, echo_delay=3, echo_vol=0.32, echo_pan=192)

    solo_25 = [
        (0, 'G#5', 4, 60), (4, 'B-5', 4, 61), (8, 'D-6', 4, 62), (12, 'E-6', 4, 63),
        (16, 'D-6', 2, 60), (18, 'B-5', 2, 58), (20, 'G#5', 2, 58), (22, 'E-5', 2, 56),
        (24, 'B-5', 4, 60), (28, 'G#5', 4, 58),
        (32, 'A-5', 4, 60), (36, 'G-5', 2, 58), (38, 'F-5', 2, 57),
        (40, 'E-5', 4, 58), (44, 'C#5', 4, 56),
        (48, 'E-5', 4, 58), (52, 'G-5', 4, 60), (56, 'A-5', 4, 62), (60, 'Bb5', 4, 62, 'slide'),
    ]
    s.put_phrase(25, 6, LEAD_PWM, solo_25, vib=0x64)
    s.put_phrase(25, 7, LEAD_SAW, [
        (0, 'E-5', 4, 46), (4, 'G#5', 4, 47), (8, 'B-5', 4, 48), (12, 'D-6', 4, 50),
        (16, 'B-5', 2, 47), (18, 'G#5', 2, 46), (20, 'E-5', 2, 46), (22, 'B-4', 2, 44),
        (24, 'G#5', 4, 48), (28, 'E-5', 4, 46),
        (32, 'C#5', 4, 48), (36, 'E-5', 2, 46), (38, 'D-5', 2, 46),
        (40, 'C#5', 4, 46), (44, 'A-4', 4, 44),
        (48, 'C#5', 4, 46), (52, 'E-5', 4, 48), (56, 'F-5', 4, 50), (60, 'G-5', 4, 50, 'slide'),
    ], vib=0x64, pan_override=176)
    s.set_cell(25, 48, 2, note='C-4', inst=FX_SWEEP, vol=s.v(34))

    # =========================================================================
    # SECTION D1 — CLIMACTIC FINAL CHORUS (Pat 26..29) with upper climax variation!
    # =========================================================================
    fill_chorus([26, 27, 28, 29], pivot_to_minor=True, add_upper_bell=True, climax_variation=True)

    # =========================================================================
    # SECTION D2 — GRAND TURNAROUND & SEAMLESS LOOP LAUNCHPAD (Pat 30..33 -> Pat 2!)
    # =========================================================================
    s.put_crash(30, 0, ch=9, vol64=26)
    s.put_drums_standard(30, style='drive2', fill='none')
    s.put_drums_standard(31, style='drive2', fill='snare_pick')
    s.put_drums_standard(32, style='chorus', fill='none')
    s.put_drums_standard(33, style='build', fill='snare_roll')

    s.put_bass_groove(30, [(0, 32, 'Bb1'), (32, 64, 'C-2')], style='drive_mix')
    s.put_bass_groove(31, [(0, 32, 'D-2'), (32, 64, 'C-2')], style='drive_mix')
    s.put_bass_groove(32, [(0, 32, 'G-2'), (32, 64, 'Bb1')], style='octave_plk')
    s.put_bass_groove(33, [(0, 32, 'A-1'), (32, 64, 'A-1')], style='octave_plk')

    s.put_arp_chord_stream(30, 4, [(0, 32, 'Bb3', 4, 7), (32, 64, 'C-4', 4, 7)], inst=ARP_P25, vol64=26, pulse_every=4)
    # Pat 31 rows 32..64: F-4 (4,7) = F-A-C (Fmaj7/C consonance!)
    s.put_arp_chord_stream(31, 4, [(0, 32, 'D-4', 3, 7), (32, 64, 'F-4', 4, 7)], inst=ARP_P25, vol64=26, pulse_every=4)
    s.put_arp_chord_stream(32, 4, [(0, 32, 'G-4', 3, 7), (32, 64, 'Bb3', 4, 7)], inst=ARP_P25, vol64=26, pulse_every=4)
    s.put_arp_chord_stream(33, 4, [(0, 32, 'A-4', 5, 7), (32, 64, 'A-4', 4, 7)], inst=ARP_P25, vol64=32, pulse_every=4)

    s.put_broken_harp(30, 5, [(0, 32, ['Bb4', 'D-5', 'F-5', 'Bb5']), (32, 64, ['C-5', 'E-5', 'G-5', 'C-6'])], inst=ARP_BELL, vol64=32, step=2)
    s.put_broken_harp(31, 5, [(0, 32, ['D-5', 'F-5', 'A-5', 'D-6']), (32, 64, ['C-5', 'F-5', 'A-5', 'C-6'])], inst=ARP_BELL, vol64=32, step=2)
    s.put_broken_harp(32, 5, [(0, 32, ['G-4', 'Bb4', 'D-5', 'G-5']), (32, 64, ['Bb4', 'D-5', 'F-5', 'Bb5'])], inst=ARP_BELL, vol64=32, step=2)
    s.put_broken_harp(33, 5, [(0, 32, ['A-4', 'D-5', 'E-5', 'A-5']), (32, 62, ['A-4', 'C#5', 'E-5', 'A-5'])], inst=ARP_BELL, vol64=34, step=2)

    s.put_phrase(30, 6, LEAD_PWM, [
        (0,  'F-5', 10, 60), (10, 'G-5', 6,  58), (16, 'F-5', 8,  58), (24, 'D-5', 8,  56),
        (32, 'E-5', 10, 59), (42, 'G-5', 6,  60), (48, 'C-6', 8,  62), (56, 'G-5', 8,  58),
    ], vib=0x54)
    s.put_phrase(30, 7, LEAD_SAW, [
        (0,  'D-5', 10, 46), (10, 'E-5', 6,  45), (16, 'D-5', 8,  45), (24, 'Bb4', 8,  44),
        (32, 'C-5', 10, 46), (42, 'E-5', 6,  47), (48, 'G-5', 8,  49), (56, 'E-5', 8,  46),
    ], vib=0x54, pan_override=176)

    s.put_phrase(31, 6, LEAD_PWM, [
        (0,  'A-5', 16, 62), (16, 'F-5', 8,  58), (24, 'D-5', 8,  56),
        (32, 'E-5', 12, 58), (44, 'C-5', 4,  54), (48, 'A-4', 16, 56),
    ], vib=0x53)
    s.put_phrase(31, 7, LEAD_SAW, [
        (0,  'F-5', 16, 48), (16, 'D-5', 8,  45), (24, 'A-4', 8,  44),
        (32, 'C-5', 12, 46), (44, 'A-4', 4,  42), (48, 'F-4', 16, 44),
    ], vib=0x53, pan_override=176)

    s.put_phrase(32, 6, LEAD_PWM, [
        (0,  'Bb4', 8,  56), (8,  'D-5', 8,  58), (16, 'G-5', 12, 61), (28, 'F-5', 4,  57),
        (32, 'D-5', 12, 58), (44, 'Bb4', 4,  54), (48, 'F-5', 16, 60),
    ], vib=0x54, echo_ch=7, echo_delay=3, echo_vol=0.36, echo_pan=192)

    # Pat 33: Leading-tone C#5 launches directly into Pat 2's D-5!
    s.put_phrase(33, 6, LEAD_PWM, [
        (0,  'E-5', 16, 58), (16, 'D-5', 16, 58),
        (32, 'C#5', 14, 60), (46, 'E-5', 6,  58),
        (52, 'A-5', 6,  61, 'slide'), (58, 'C#5', 6,  62),
    ], vib=0x64)
    s.put_phrase(33, 7, LEAD_SAW, [
        (0,  'A-4', 16, 45), (16, 'A-4', 16, 45),
        (32, 'A-4', 14, 47), (46, 'C#5', 6,  46),
        (52, 'E-5', 6,  48, 'slide'), (58, 'A-4', 6,  48),
    ], vib=0x64, pan_override=176)
    s.set_cell(33, 63, 7, note=97)
    s.set_cell(33, 63, 8, note=97)
    s.set_cell(33, 40, 2, note='C-4', inst=FX_SWEEP, vol=s.v(34))

    s.orders = list(range(34))
    s.loop_start = 2
    return s

def export_and_render(song, xm_path, wav_path, amp=16):
    insts = instruments.make_instruments()
    cmds = [
        {"name": "module_new", "arguments": {"channels": song.channels, "name": song.name}},
        {"name": "song_set", "arguments": {
            "name": song.name, "bpm": song.bpm, "speed": song.speed,
            "length": len(song.orders), "loop_start": song.loop_start
        }},
    ]
    for ins in insts:
        cmds.append({"name": "sample_create_from_pcm", "arguments": {
            "instrument": ins['id'], "sample": 0, "pcm": ins['pcm_b64'],
            "encoding": "int16", "name": ins['name']
        }})
        cmds.append({"name": "instrument_set", "arguments": {
            "instrument": ins['id'], "name": ins['name']
        }})
        cmds.append({"name": "sample_set", "arguments": {
            "instrument": ins['id'], "sample": 0,
            "volume": ins['volume'], "panning": ins['panning'],
            "relative_note": ins['relative_note'], "finetune": ins['finetune'],
            "loop_start": ins['loop_start'], "loop_length": ins['loop_length'],
            "flags": ins['flags']
        }})

    for p in range(song.num_patterns):
        cmds.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": song.pat_rows[p]}})
        for (row, ch), cell in sorted(song.patterns[p].items()):
            arg = {"pattern": p, "row": row, "channel": ch}
            arg.update(cell)
            cmds.append({"name": "pattern_set_cell", "arguments": arg})

    for pos, pat in enumerate(song.orders):
        cmds.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

    cmds.append({"name": "module_save", "arguments": {"path": xm_path, "format": "xm"}})
    if wav_path:
        cmds.append({"name": "module_render", "arguments": {
            "path": wav_path, "rate": 44100, "bits": 16, "amp": amp, "loops": 1
        }})

    batch_path = '/workspace/work/build_batch.json'
    with open(batch_path, 'w') as f:
        json.dump(cmds, f)
    print(f"Running ft2 batch ({len(cmds)} commands)...")
    res = subprocess.run(['ft2', 'batch', batch_path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ft2 batch failed: {res.stderr}")
    for line in res.stdout.splitlines():
        if '"isError": true' in line or '"isError":true' in line:
            raise RuntimeError(f"FT2 error: {line}")
    print("Successfully saved", xm_path, "size:", os.path.getsize(xm_path), "bytes")

if __name__ == '__main__':
    song = build_song()
    export_and_render(song, '/workspace/submission/tune.xm', '/workspace/test/tune_preview.wav', amp=16)
