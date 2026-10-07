#!/usr/bin/env python3
import sys, os, json, subprocess
sys.path.insert(0, '/workspace/work')
import numpy as np
import samples as S
import song as SG

OUT = '/workspace/work'
SUB = '/workspace/submission'
N = SG.N; INS = SG.INS; CH = SG.CH; CHORDS = SG.CHORDS; PROG = SG.PROG

cells = {}   # (pat,row,ch) -> dict
def put(pat, row, ch, note=None, ins=None, vol=None, eff=None, par=None):
    if row is None or row < 0 or row > 63: return
    d = {}
    if note is not None: d['note'] = note
    if ins is not None: d['instrument'] = ins
    if vol is not None: d['volume'] = vol
    if eff is not None: d['effect'] = eff
    if par is not None: d['effect_param'] = par
    key = (pat, row, ch)
    cells.setdefault(key, {}).update(d)

def C4row(pat, row, ins, vol): put(pat, row, CH['kick'], note=49, ins=ins, vol=vol)

def kick(pat, rows, vol=56): [put(pat, r, CH['kick'], note=49, ins=INS['KICK'], vol=vol) for r in rows]
def snare(pat, rows, vol=48): [put(pat, r, CH['kick'], note=49, ins=INS['SNARE'], vol=vol) for r in rows]
def tom(pat, rows, notes, vol=46): [put(pat, r, CH['kick'], note=n, ins=INS['TOM'], vol=vol) for r, n in zip(rows, notes)]
def hat(pat, rows, vol=32): [put(pat, r, CH['perc'], note=49, ins=INS['HAT'], vol=vol) for r in rows]
def ohat(pat, rows, vol=36): [put(pat, r, CH['perc'], note=49, ins=INS['OHAT'], vol=vol) for r in rows]
def crash(pat, rows, vol=46): [put(pat, r, CH['perc'], note=49, ins=INS['CRASH'], vol=vol) for r in rows]
def zap(pat, rows, vol=40): [put(pat, r, CH['kick'], note=49, ins=INS['ZAP'], vol=vol) for r in rows]

def hats16(pat, bar, base_vol=30, acc=38, accents=(2, 6, 10, 14)):
    for i in range(16):
        r = bar*16 + i
        if i % 2 == 1:
            put(pat, r, CH['perc'], note=49, ins=INS['HAT'], vol=base_vol)
    for a in accents:
        put(pat, bar*16 + a, CH['perc'], note=49, ins=INS['HAT'], vol=acc)

def bass_bar(pat, bar, ch, pattern, ins=None, vol=46):
    chd = CHORDS[PROG[pat][bar]]
    root = chd['bass']
    for i, off in enumerate(pattern):
        put(pat, bar*16+i, CH['bass'], note=root+off, ins=ins or INS['BASS'], vol=vol)

def arp_bar(pat, bar, style, vol=30, ins=None):
    chd = CHORDS[PROG[pat][bar]]
    a, b, c = chd['arp']
    seq8 = [a, b, c, b, a, b, c, b]
    if style == '8th':
        for i, r in enumerate(range(0, 16, 2)):
            put(pat, bar*16+r, CH['arp'], note=seq8[i % 8], ins=ins or INS['PLUCK'], vol=vol)
    elif style == '8thup':
        seq = [a, b, c, a+12, c, b, a+12, b]
        for i, r in enumerate(range(0, 16, 2)):
            put(pat, bar*16+r, CH['arp'], note=seq[i % 8], ins=ins or INS['PLUCK'], vol=vol)
    elif style == '16th':
        seq = [a, b, c, b]
        for i in range(16):
            put(pat, bar*16+i, CH['arp'], note=seq[i % 4], ins=ins or INS['PLUCK'], vol=vol)
    elif style == '16thup':
        seq = [a, b, c, a+12]
        for i in range(16):
            put(pat, bar*16+i, CH['arp'], note=seq[i % 4], ins=ins or INS['PLUCK'], vol=vol)
    elif style == 'eff':
        # tracker-style arpeggio: one pluck per beat, 0xy cycling on every row
        for r in (0, 4, 8, 12):
            put(pat, bar*16+r, CH['arp'], note=a, ins=ins or INS['PLUCK'], vol=vol,
                eff=0, par=chd['eff'])
        for r in range(16):
            if r % 4:
                put(pat, bar*16+r, CH['arp'], eff=0, par=chd['eff'])

def pad_bar(pat, bar, vol=28, volr=None):
    chd = CHORDS[PROG[pat][bar]]
    t, f = chd['pad']
    put(pat, bar*16, CH['padL'], note=t, ins=INS['PADL'], vol=vol)
    put(pat, bar*16, CH['padR'], note=f, ins=INS['PADR'], vol=(volr if volr is not None else vol))

def melody(pat, ch, notes, ins, vol, transpose=0):
    ns = sorted([(r, d, N(x)) for r, d, x in notes])
    for i, (row, dur, note) in enumerate(ns):
        put(pat, row, ch, note=note+transpose, ins=ins, vol=vol)
        nxt = ns[i+1][0] if i+1 < len(ns) else None
        if nxt is None or nxt > row+dur:
            if row+dur < 64:
                put(pat, row+dur, ch, note='off')

# ============================================================ PATTERNS
B16A  = [0,12,0,12, 0,12,0,12, 0,12,0,12, 0,12,7,12]
B16C  = [0,0,12,0, 12,0,12,12, 0,0,12,0, 12,12,7,7]
B8    = [0,12,0,12, 0,12,0,12, 0,12,0,12, 0,12,0,12]

def build_pattern(pat):
    prog = PROG[pat]
    # ---------- P0 : intro A ----------
    if pat == 0:
        crash(0, [0], 46)
        for b in range(4):
            kick(0, [b*16+r for r in (0,4,8,12)], 54)
        hat(0, [2,6,10,14], 28); hat(0, [18,22,26,30], 30)
        for r in (34,38,42,46): put(0, r, CH['perc'], note=49, ins=INS['HAT'], vol=32)
        for r in (50,54,58,62): put(0, r, CH['perc'], note=49, ins=INS['HAT'], vol=36)
        put(0, 44, CH['kick'], note=49, ins=INS['SNARE'], vol=40)
        put(0, 56, CH['kick'], note=49, ins=INS['SNARE'], vol=42)
        put(0, 60, CH['kick'], note=49, ins=INS['SNARE'], vol=44)
        put(0, 62, CH['kick'], note=49, ins=INS['SNARE'], vol=46)
        for b in range(4):
            bass_bar(0, b, CH['bass'], B8, vol=44)
        for b in (2, 3):
            arp_bar(0, b, '8th', vol=26)
    # ---------- P1 : intro B ----------
    elif pat == 1:
        crash(1, [0], 46)
        for b in range(4):
            kick(1, [b*16+r for r in (0,8)], 56)
            if b < 3: snare(1, [b*16+r for r in (4,12)], 46)
            hats16(1, b, 28, 36)
            if b < 3: ohat(1, [b*16+14], 30)
        snare(1, [52,60], 48)
        for r, v in ((56,44),(57,46),(58,48),(59,50),(60,52),(61,54),(62,56),(63,58)):
            put(1, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        for b in range(4):
            bass_bar(1, b, CH['bass'], B8, vol=46)
        for b in range(4):
            arp_bar(1, b, '16th', vol=28)
            pad_bar(1, b, 26)
        # sneak preview of the theme hook, quiet, over the last two bars
        melody(1, CH['lead'], [(r + 16, d, n) for r, d, n in SG.THEME_A if r < 32],
               INS['LEAD'], 38)
    # ---------- P2 : theme A ----------
    elif pat == 2:
        crash(2, [0], 48)
        for b in range(4):
            kick(2, [b*16+r for r in (0,8)], 56)
            snare(2, [b*16+r for r in (4,12)], 48)
            hats16(2, b, 28, 36)
            ohat(2, [b*16+14], 30)
            bass_bar(2, b, CH['bass'], B16A, vol=46)
            arp_bar(2, b, '16th', vol=28)
            pad_bar(2, b, 26)
        snare(2, [63], 52)
        melody(2, CH['lead'], SG.THEME_A, INS['LEAD'], 52)
        melody(2, CH['harm'], SG.THEME_A, INS['LEAD2'], 33, transpose=-12)
    # ---------- P3 : theme A' ----------
    elif pat == 3:
        crash(3, [0], 48)
        for b in range(4):
            kick(3, [b*16+r for r in (0,8)], 56)
            snare(3, [b*16+r for r in (4,12)], 48)
            hats16(3, b, 28, 36)
            ohat(3, [b*16+14], 30)
            bass_bar(3, b, CH['bass'], B16A, vol=46)
            arp_bar(3, b, '16thup', vol=28)
            pad_bar(3, b, 26)
        for r, v in ((56,42),(57,44),(58,46),(59,48),(60,50),(61,52),(62,54),(63,58)):
            put(3, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        melody(3, CH['lead'], SG.THEME_A2, INS['LEAD'], 52)
        melody(3, CH['harm'], SG.THEME_A2, INS['LEAD2'], 33, transpose=-12)
    # ---------- P4 : sequence ----------
    elif pat == 4:
        crash(4, [0], 48)
        for b in range(4):
            kick(4, [b*16+r for r in (0,8)], 56)
            snare(4, [b*16+r for r in (4,12)], 48)
            hats16(4, b, 28, 36)
            ohat(4, [b*16+6, b*16+14], 30)
            bass_bar(4, b, CH['bass'], B16A, vol=46)
            arp_bar(4, b, 'eff', vol=30)
            pad_bar(4, b, 26)
        tom(4, [60,61,62], [49,46,44], 44)
        zap(4, [62], 40)
        for b in range(4):
            fig = SG.SEQ16[prog[b]]
            for i in range(16):
                put(4, b*16+i, CH['lead'], note=fig[i % 4], ins=INS['LEAD'], vol=52)
        for i, n in enumerate(SG.SEQ16_TAIL):
            put(4, 56+i, CH['lead'], note=n, ins=INS['LEAD'], vol=54)
    # ---------- P5 : break ----------
    elif pat == 5:
        put(5, 0, CH['lead'], note='off')      # cut lead ringing from previous pattern
        crash(5, [0], 38)
        for b in range(4):
            bass_bar(5, b, CH['bass'], [0,0,0,0,0,0,0,0,7,7,7,7,7,7,7,7], vol=44)
            arp_bar(5, b, '8thup', vol=24)
            pad_bar(5, b, 34)
        kick(5, [0,32,48,56], 52)
        snare(5, [8,24,40], 44)
        hat(5, [4,12,20,28,36,44], 24)
        snare(5, [46], 40)
        put(5, 50, CH['kick'], note=49, ins=INS['SNARE'], vol=42)
        for r, v in ((56,40),(58,44),(60,48),(62,52),(63,56)):
            put(5, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        for r in (57,59,61):
            put(5, r, CH['perc'], note=49, ins=INS['HAT'], vol=26)
        melody(5, CH['harm'], SG.BREAK_MEL, INS['PLUCK'], 44)
    # ---------- P6 : build ----------
    elif pat == 6:
        crash(6, [0], 46)
        for b in range(4):
            pad_bar(6, b, 30)
            arp_bar(6, b, '16th' if b >= 2 else '8th', vol=26+2*b)
        for b in range(2):
            kick(6, [b*16+r for r in (0,8)], 52)
            snare(6, [b*16+r for r in (4,12)], 44)
            hat(6, [b*16+r for r in (2,6,10,14)], 28)
        kick(6, [32,40], 54); snare(6, [36,44], 46); hats16(6, 2, 28, 36)
        kick(6, [48,56], 56)
        for r, v in ((48,38),(50,42),(52,46),(54,50),(56,50),(57,52),(58,54),(59,56),
                     (60,56),(61,58),(62,60),(63,62)):
            put(6, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        ohat(6, [14,30,46], 30)
        zap(6, [62], 42)
        for b in range(4):
            bass_bar(6, b, CH['bass'], B8 if b < 2 else B16A, vol=46)
        melody(6, CH['lead'], SG.BUILD_MEL, INS['LEAD'], 50)
        melody(6, CH['harm'], SG.BUILD_MEL, INS['LEAD2'], 42, transpose=-12)
    # ---------- P7 : climax 1 ----------
    elif pat == 7:
        crash(7, [0], 50)
        for b in range(4):
            kick(7, [b*16+r for r in (0,8)], 58)
            if b < 3: kick(7, [b*16+14], 52)
            snare(7, [b*16+r for r in (4,12)], 50)
            hats16(7, b, 28, 36)
            ohat(7, [b*16+6], 30)
            bass_bar(7, b, CH['bass'], B16A, ins=INS['BASS2'], vol=46)
            arp_bar(7, b, '16th', vol=30)
            pad_bar(7, b, 26)
        snare(7, [52,60], 50)
        for r, v in ((61,48),(62,52),(63,56)):
            put(7, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        melody(7, CH['lead'], SG.THEME_A, INS['LEAD2'], 52, transpose=12)
        melody(7, CH['harm'], SG.THEME_A, INS['LEAD'], 44)
    # ---------- P8 : climax 2 ----------
    elif pat == 8:
        crash(8, [0], 50)
        for b in range(4):
            kick(8, [b*16+r for r in (0,8)], 58)
            if b < 3: kick(8, [b*16+11], 52)
            snare(8, [b*16+r for r in (4,12)], 50)
            hats16(8, b, 28, 36)
            ohat(8, [b*16+14], 30)
            bass_bar(8, b, CH['bass'], B16C, ins=INS['BASS2'], vol=46)
            arp_bar(8, b, '16thup', vol=30)
            pad_bar(8, b, 26)
        tom(8, [60,61,62,63], [53,49,46,44], 46)
        melody(8, CH['lead'], SG.THEME_A2, INS['LEAD2'], 52, transpose=12)
        melody(8, CH['harm'], SG.THEME_A2, INS['LEAD'], 44)
    # ---------- P9 : climax 3 ----------
    elif pat == 9:
        crash(9, [0], 50)
        for b in range(4):
            kick(9, [b*16+r for r in (0,8)], 58)
            if b < 3: kick(9, [b*16+14], 54)
            snare(9, [b*16+r for r in (4,12)], 50)
            hats16(9, b, 28, 36)
            ohat(9, [b*16+6, b*16+14], 30)
            bass_bar(9, b, CH['bass'], B16A, ins=INS['BASS2'], vol=46)
            arp_bar(9, b, 'eff', vol=32)
            pad_bar(9, b, 26)
        kick(9, [48,56], 56)
        for r, v in ((52,44),(54,48),(56,50),(57,52),(58,54),(59,56),(60,56),(61,58),(62,60),(63,62)):
            put(9, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        for b in range(4):
            fig = SG.SEQ16[prog[b]]
            for i in range(16):
                put(9, b*16+i, CH['lead'], note=fig[i % 4] + 12, ins=INS['LEAD2'], vol=52)
                put(9, b*16+i, CH['harm'], note=fig[i % 4], ins=INS['LEAD'], vol=44)
        for i, n in enumerate(SG.SEQ16_TAIL):
            put(9, 56+i, CH['lead'], note=n + 12, ins=INS['LEAD2'], vol=54)
            put(9, 56+i, CH['harm'], note=n, ins=INS['LEAD'], vol=44)
    # ---------- P10 : outro ----------
    elif pat == 10:
        put(10, 0, CH['harm'], note='off')     # cut harmony ringing from previous pattern
        crash(10, [0], 48)
        kick(10, [0,8,16,24,32,40,48,56], 54)
        snare(10, [4,12,20,28,36], 48)
        hats16(10, 0, 28, 36)
        hat(10, [18,22,26,30], 28); hat(10, [34,38,42,46], 26)
        ohat(10, [14], 28)
        for r, v in ((48,42),(50,44),(52,46),(54,48),(56,48),(57,50),(58,52),(59,54),
                     (60,54),(61,56),(62,58),(63,60)):
            put(10, r, CH['kick'], note=49, ins=INS['SNARE'], vol=v)
        for b in range(4):
            bass_bar(10, b, CH['bass'], B8, vol=44)
            arp_bar(10, b, '8th', vol=24)
            pad_bar(10, b, 26)
        melody(10, CH['lead'], SG.OUTRO_MEL, INS['LEAD'], 48)
    return

for p in range(11):
    build_pattern(p)

# ============================================================ emit
calls = []
calls.append({"name": "module_new", "arguments": {"channels": 8, "name": "PHOSPHOR TRACE"}})
for i, (name, fn, rel, pan, vol, meta) in enumerate(S.INSTRUMENTS):
    idx = i + 1
    pcm, m = fn()
    meta = dict(m)
    args = {"instrument": idx, "sample": 0, "pcm": pcm, "encoding": "int16", "name": name}
    calls.append({"name": "sample_create_from_pcm", "arguments": args})
    s = {"instrument": idx, "sample": 0, "name": name, "volume": vol, "panning": pan,
         "relative_note": rel, "finetune": 0}
    if meta.get('loop_start') is not None:
        s.update({"loop_start": int(meta['loop_start']), "loop_length": int(meta['loop_length']),
                  "flags": 17})
    else:
        s.update({"loop_start": 0, "loop_length": 0, "flags": 16})
    calls.append({"name": "sample_set", "arguments": s})
    calls.append({"name": "instrument_set", "arguments": {"instrument": idx, "name": name}})

for p in range(11):
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
    calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})
for (p, r, ch), d in sorted(cells.items()):
    a = {"pattern": p, "row": int(r), "channel": ch}
    a.update(d)
    calls.append({"name": "pattern_set_cell", "arguments": a})

for pos, pat in enumerate(range(11)):
    calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})
calls.append({"name": "song_set", "arguments": {"name": "PHOSPHOR TRACE", "bpm": 168, "speed": 6,
                                                "length": 11, "loop_start": 2, "channels": 8}})
calls.append({"name": "module_save", "arguments": {"path": os.path.join(SUB, "tune.xm")}})

# write batches in chunks
CH = 400
os.makedirs(OUT, exist_ok=True)
for i in range(0, len(calls), CH):
    fn = os.path.join(OUT, f"batch_{i//CH:03d}.json")
    with open(fn, 'w') as f:
        json.dump(calls[i:i+CH], f)
    print("wrote", fn, min(i+CH, len(calls)) - i, "calls")
print("total calls", len(calls), "cells", len(cells))
