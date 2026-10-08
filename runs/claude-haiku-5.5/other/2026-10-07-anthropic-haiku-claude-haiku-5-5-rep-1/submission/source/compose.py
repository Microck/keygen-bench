"""Composition source for 'Chrome Cathedral' (original keygen tune, music only).

Everything in the module is generated from this file + synth.py (deterministic).
Writes FT2 batch files under build/batches/ and a manifest of the score.
Musical summary: A minor / D minor, 160 BPM (speed 3 -> 8 rows per beat, 32 rows per bar).
Form (44 bars): intro 1-4 | A 5-12 | breakdown B 13-20 | A' 21-28 | modulated C 29-36 | A'' 37-44.
The song restarts at bar 5 (order position 4): bar 44 ends on E (V) and resolves to Am at bar 5.
"""
import base64, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth

BPM, SPEED = 160, 3
ROWS_PER_BAR = 32
NBARS = 44
RESTART_BAR = 5                      # loop restart (1-based bar number)
NCH = 14
SONG_ROWS = NBARS * ROWS_PER_BAR
RESTART_ROW = (RESTART_BAR - 1) * ROWS_PER_BAR

# channel roles
CH_LEAD, CH_HARM, CH_BASS, CH_ARP, CH_ARP2, CH_PAD1, CH_PAD2 = range(7)
CH_KICK, CH_SNARE, CH_HATC, CH_HATO, CH_RISER, CH_CRASH = 7, 8, 9, 10, 11, 12
# instrument numbers (1-based, match synth.INSTRUMENTS)
I_KICK, I_SNARE, I_HATC, I_HATO, I_BASS, I_LEAD, I_HARM, I_P16, I_P32, I_PAD, I_RISER, I_CRASH = range(1, 13)

PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

def N(name):
    """'A4' / 'F#5' / 'Bb4' -> FT2 note number (C-4 = 49)."""
    letter = name[0]; i = 1; acc = 0
    while name[i] in '#b':
        acc += 1 if name[i] == '#' else -1; i += 1
    return 12 * int(name[i:]) + PC[letter] + acc + 1

CHORDS = {  # name: (root_pc, third_pc, fifth_pc)
    'Am': (9, 0, 4), 'F': (5, 9, 0), 'C': (0, 4, 7), 'G': (7, 11, 2),
    'E': (4, 8, 11), 'Em': (4, 7, 11), 'Dm': (2, 5, 9), 'Bb': (10, 2, 5),
}
BASS_ROOT = {k: 12 * 2 + v[0] + 1 for k, v in CHORDS.items()}          # octave 2
A_MINOR = [9, 11, 0, 2, 4, 5, 7]
D_MINOR = [2, 4, 5, 7, 9, 10, 0]

def arp_tones(chord, base_oct):
    """ascending chord tones [root, third, fifth, root+12] starting in base_oct."""
    r, t, f = CHORDS[chord]
    def up(pc, add=0):
        return 12 * base_oct + pc + 1 + add + (12 if pc < r and add == 0 else 0)
    return [up(r), up(t), up(f), up(r) + 12]

# ---------------- melody (slot = 16th note, 16 slots per bar) ----------------
# entries: (slot, note, length_in_slots)
LEAD = {
 5: [(0,'E5',3),(3,'D5',1),(4,'C5',4),(8,'A4',2),(10,'C5',2),(12,'E5',2),(14,'A5',2)],
 6: [(0,'F5',2),(2,'A5',2),(4,'G5',2),(6,'F5',2),(8,'E5',4),(12,'C5',2),(14,'A4',2)],
 7: [(0,'G5',2),(2,'E5',2),(4,'C5',2),(6,'E5',2),(8,'G5',4),(12,'A5',2),(14,'G5',2)],
 8: [(0,'D5',4),(4,'G5',2),(6,'B5',2),(8,'G5',2),(10,'F#5',2),(12,'D5',4)],
 9: [(0,'E5',2),(2,'A5',2),(4,'C6',4),(8,'A5',2),(10,'E5',2),(12,'C5',2),(14,'A4',2)],
 10:[(0,'F5',4),(4,'A5',2),(6,'C6',2),(8,'A5',2),(10,'G5',2),(12,'F5',2),(14,'E5',2)],
 11:[(0,'E5',2),(2,'G#5',2),(4,'B5',4),(8,'E6',2),(10,'D#6',2),(12,'B5',2),(14,'G#5',2)],
 12:[(0,'E5',4),(4,'G#5',2),(6,'B5',2),(8,'E6',4),(12,'D#6',2),(14,'B5',2)],
 13:[(0,'C6',8),(8,'A5',4),(12,'F5',4)],
 14:[(0,'D6',4),(4,'B5',4),(8,'G5',8)],
 15:[(0,'E5',4),(4,'G5',4),(8,'B5',4),(12,'E6',4)],
 16:[(0,'A5',8),(8,'C6',4),(12,'E6',4)],
 17:[(0,'F5',4),(4,'A5',4),(8,'C6',4),(12,'A5',2),(14,'G5',2)],
 18:[(0,'G5',2),(2,'B5',2),(4,'D6',4),(8,'B5',4),(12,'G5',4)],
 19:[(0,'C6',4),(4,'E6',4),(8,'E6',2),(10,'C6',2),(12,'G5',4)],
 20:[(0,'E5',2),(2,'G#5',2),(4,'B5',2),(6,'D#6',2),(8,'E6',8)],
 29:[(0,'D6',2),(2,'F6',2),(4,'A5',4),(8,'D6',2),(10,'C6',2),(12,'Bb5',2),(14,'A5',2)],
 30:[(0,'Bb5',4),(4,'D6',2),(6,'F6',2),(8,'D6',4),(12,'C6',2),(14,'Bb5',2)],
 31:[(0,'A5',2),(2,'C6',2),(4,'F6',4),(8,'E6',2),(10,'D6',2),(12,'C6',2),(14,'A5',2)],
 32:[(0,'G5',2),(2,'C6',2),(4,'E6',4),(8,'G6',2),(10,'E6',2),(12,'C6',4)],
 33:[(0,'A5',2),(2,'D6',2),(4,'F6',2),(6,'D6',2),(8,'A6',4),(12,'F6',2),(14,'D6',2)],
 34:[(0,'D6',4),(4,'F6',4),(8,'D6',4),(12,'Bb5',4)],
 35:[(0,'C6',2),(2,'E6',2),(4,'G6',4),(8,'E6',2),(10,'C6',2),(12,'G5',2),(14,'E5',2)],
 36:[(0,'E5',2),(2,'G#5',2),(4,'B5',2),(6,'E6',2),(8,'G#6',4),(12,'E6',2),(14,'B5',2)],
}
# A-section bars reuse the same phrase in other sections
PHRASE_MAP = {21: 5, 22: 6, 23: 7, 24: 8, 25: 9, 26: 10, 27: 11, 28: 12,
              37: 5, 38: 6, 39: 7, 40: 8, 41: 9, 42: 10, 43: 11, 44: 12}
for dst, src in PHRASE_MAP.items():
    LEAD[dst] = LEAD[src]
LEAD[44] = [(0,'E5',4),(4,'G#5',2),(6,'B5',2),(8,'E6',8)]   # final bar, cadence to loop

CHORD_OF = {}
prog = {1:'Am',2:'F',3:'C',4:'G', 5:'Am',6:'F',7:'C',8:'G', 9:'Am',10:'F',11:'E',12:'E',
        13:'F',14:'G',15:'Em',16:'Am', 17:'F',18:'G',19:'C',20:'E',
        21:'Am',22:'F',23:'C',24:'G', 25:'Am',26:'F',27:'E',28:'E',
        29:'Dm',30:'Bb',31:'F',32:'C', 33:'Dm',34:'Bb',35:'C',36:'E',
        37:'Am',38:'F',39:'C',40:'G', 41:'Am',42:'F',43:'E',44:'E'}
CHORD_OF.update(prog)

def section_of(b):
    if b <= 4: return 'intro'
    if b <= 12: return 'A'
    if b <= 20: return 'B'
    if b <= 28: return 'A2'
    if b <= 36: return 'C'
    return 'A3'

KICK4 = [0, 8, 16, 24]
BACK = [8, 24]
HATS16 = list(range(0, 32, 2))
OPEN8 = [4, 12, 20, 28]
ROLL = lambda a, b: list(range(a, b + 1, 2))

def bar_plan(b):
    """Per-bar musical plan: which roles play and how."""
    p = dict(kick=[], snare=[], hatc=[], hato=[], bass='none', arp='none', arp2=False,
             lead=False, harm=None, fx=[], lead_vol=None, pad_vol=None, bass_vol=None)
    sec = section_of(b)
    if sec == 'intro':
        if b == 2: p.update(arp='8th', hatc=OPEN8)
        if b == 3: p.update(bass='half', arp='16th', hatc=HATS16, hato=OPEN8, fx=[(0, I_RISER)])
        if b == 4: p.update(bass='16th', kick=KICK4, snare=BACK, hatc=HATS16, hato=OPEN8, arp='16th')
    elif sec in ('A', 'A2', 'A3'):
        p.update(kick=KICK4, snare=BACK, hatc=HATS16, hato=OPEN8, bass='16th', arp='16th', lead=True)
        if b in (5, 21, 37): p['fx'].append((0, I_CRASH))
        if b in (9, 10, 11, 12, 21, 22, 23, 24, 25, 26, 27, 28, 37, 38, 39, 40, 41, 42, 43):
            p['harm'] = 'third'                                   # harmony voice in the A-type sections
        if 21 <= b <= 28 or b >= 37:
            p['arp2'] = True                                      # second arp layer
        if b == 12: p['snare'] = BACK + ROLL(24, 30)              # fill into B
        if b == 28: p['fx'].append((0, I_RISER))
        if b == 44:
            p['snare'] = BACK + ROLL(16, 30)                      # fill into the loop
            p['fx'].append((0, I_RISER))
    elif sec == 'B':
        if b in (13, 14, 15, 16):
            p.update(lead=True, harm=None, lead_vol=16, pad_vol=12)
        if b in (13, 14):
            p.update(bass='none')
            if b == 13: p['fx'].append((0, I_CRASH))
        if b == 15:
            p.update(bass='half', bass_vol=20)
        if b == 16:
            p.update(bass='eighth', bass_vol=26, kick=[16, 20, 24, 28], snare=ROLL(20, 30), hatc=ROLL(24, 30),
                     fx=[(0, I_RISER)])
        if b in (17, 18, 19):
            p.update(kick=KICK4, snare=BACK, hatc=HATS16, hato=OPEN8, bass='eighth', arp='8th',
                     lead=True, harm='third', fx=[(0, I_CRASH)] if b == 17 else [])
        if b == 20:
            p.update(kick=KICK4, snare=ROLL(16, 30), hatc=HATS16, hato=OPEN8, bass='16th',
                     arp='16th', lead=True, harm='third')
    elif sec == 'C':
        p.update(kick=KICK4, snare=BACK, hatc=HATS16, hato=OPEN8, bass='16th', lead=True,
                 harm='octave_down', arp='16th', arp2=True)
        if b == 29: p['fx'].append((0, I_CRASH))
        if b in (33, 34, 35, 36):
            p.update(arp='32nd', arp2=False)
        if b == 32: p['fx'].append((0, I_RISER))
    return p

# ----- sanity: every bar defined -----
for b in range(1, NBARS + 1):
    assert b in CHORD_OF
LEAD_BARS = {b for b in range(1, NBARS + 1) if bar_plan(b)['lead']}
for b in LEAD_BARS:
    assert b in LEAD, f"missing melody bar {b}"


def in_key_third_below(n, scale):
    cand = [x for x in range(n - 1, n - 16, -1) if ((x - 1) % 12) in scale]
    return cand[1]


def build_events():
    """Return dict channel -> {abs_row: cell} and the list of per-bar chords."""
    ev = {c: {} for c in range(NCH)}

    def put(ch, row, note=None, inst=None, vol=None, fx=None, fxp=0, dur=None):
        cell = ev[ch].get(row, {})
        if note is not None:
            cell.update(note=note, inst=inst)
        if vol is not None:
            cell['vol'] = vol
        if dur is not None:
            cell['dur'] = dur          # rows the note lasts (used only for fade-out placement)
        if fx is not None:
            cell['fx'] = fx; cell['fxp'] = fxp
        ev[ch][row] = cell

    for b in range(1, NBARS + 1):
        base = (b - 1) * ROWS_PER_BAR
        ch_name = CHORD_OF[b]
        plan = bar_plan(b)
        scale = D_MINOR if section_of(b) == 'C' else A_MINOR
        # --- drums (one-shots) ---
        for r in plan['kick']:
            put(CH_KICK, base + r, N('C4'), I_KICK)
        for r in plan['snare']:
            put(CH_SNARE, base + r, N('C4'), I_SNARE)
        for r in plan['hatc']:
            v = 40 if r % 8 == 0 else (34 if r % 4 == 0 else 26)
            put(CH_HATC, base + r, N('C4'), I_HATC, vol=16 + v)
        for r in plan['hato']:
            put(CH_HATO, base + r, N('C4'), I_HATO)
        for r, inst in plan['fx']:
            ch = CH_CRASH if inst == I_CRASH else CH_RISER
            put(ch, base + r, N('C4'), inst)
        # --- pads: root (oct 3) and third (oct 4) once per bar ---
        r_pc, t_pc, f_pc = CHORDS[ch_name]
        pv = None if plan['pad_vol'] is None else 16 + plan['pad_vol']
        put(CH_PAD1, base, 12 * 3 + r_pc + 1, I_PAD, vol=pv, dur=32)
        put(CH_PAD2, base, 12 * 4 + t_pc + 1, I_PAD, vol=pv, dur=32)
        # --- bass ---
        root = BASS_ROOT[ch_name]
        bv = None if plan['bass_vol'] is None else 16 + plan['bass_vol']
        if plan['bass'] == 'half':
            for r in (0, 16):
                put(CH_BASS, base + r, root, I_BASS, vol=bv, dur=16)
        elif plan['bass'] == 'eighth':
            for i, r in enumerate(range(0, 32, 4)):
                put(CH_BASS, base + r, root + (12 if i % 2 else 0), I_BASS, vol=bv, dur=4)
        elif plan['bass'] == '16th':
            for i, r in enumerate(range(0, 32, 2)):
                put(CH_BASS, base + r, root + (12 if i % 2 else 0), I_BASS, vol=bv, dur=2)
        # --- arps ---
        if plan['arp'] != 'none':
            if plan['arp'] == '32nd':
                tones = arp_tones(ch_name, 5)
                motif = [0, 1, 2, 3, 2, 1, 2, 1]
                for i, r in enumerate(range(32)):
                    put(CH_ARP, base + r, tones[motif[i % 8]], I_P32)
            else:
                tones = arp_tones(ch_name, 4 if section_of(b) != 'C' else 5)
                motif = [0, 1, 2, 1]
                step = 4 if plan['arp'] == '8th' else 2
                for i, r in enumerate(range(0, 32, step)):
                    put(CH_ARP, base + r, tones[motif[i % 4]], I_P16)
        if plan['arp2']:
            tones = arp_tones(ch_name, 5 if section_of(b) != 'C' else 6)
            motif = [0, 1, 2, 1]
            for i, r in enumerate(range(0, 32, 2)):
                put(CH_ARP2, base + r, tones[motif[i % 4]], I_P16)
        # --- lead and harmony ---
        if plan['lead']:
            lv = None if plan['lead_vol'] is None else 16 + plan['lead_vol']
            for slot, name, dur in LEAD[b]:
                n = N(name)
                put(CH_LEAD, base + 2 * slot, n, I_LEAD, vol=lv, dur=2 * dur)
                if plan['harm'] == 'third':
                    put(CH_HARM, base + 2 * slot, in_key_third_below(n, scale), I_HARM, dur=2 * dur)
                elif plan['harm'] == 'octave_down':
                    put(CH_HARM, base + 2 * slot, n - 12, I_HARM, dur=2 * dur)
    return ev


def add_release_effects(ev):
    """Gate every sustained (looped) note. A note ends at its natural length or at the next
    note on the same channel, whichever comes first. The last 2 rows before that end get a
    volume fade (A0F = slide down 15/tick), so no looped note is cut at full level (no clicks)
    and no note rings through a rest. Notes still sounding at the end of the song are faded
    at the loop seam, so nothing rings across the restart point."""
    for ch in (CH_LEAD, CH_HARM, CH_BASS, CH_PAD1, CH_PAD2):
        rows = sorted(ev[ch].keys())
        for i, r in enumerate(rows):
            dur = ev[ch][r].get('dur', 2)
            natural_end = r + dur
            end = natural_end
            if i + 1 < len(rows) and rows[i + 1] < natural_end:
                end = rows[i + 1]
            end = min(end, SONG_ROWS)
            for rr in (end - 2, end - 1):
                if not (r <= rr < SONG_ROWS) or rr < r:
                    continue
                cell = ev[ch].get(rr, {})
                if cell.get('fx') not in (None, 10):
                    continue
                cell['fx'] = 10; cell['fxp'] = 0x0F
                ev[ch][rr] = cell
    return ev


def pattern_cells(ev, b):
    base = (b - 1) * ROWS_PER_BAR
    cells = []
    for ch in range(NCH):
        for r in range(ROWS_PER_BAR):
            c = ev[ch].get(base + r)
            if c:
                keep = {k: c[k] for k in ('note', 'inst', 'vol', 'fx', 'fxp') if k in c}
                cells.append(dict(row=r, channel=ch, **keep))
    return cells


def main(out_dir=None):
    out_dir = out_dir or os.path.join(HERE, 'batches')
    os.makedirs(out_dir, exist_ok=True)
    ev = add_release_effects(build_events())
    # dedupe bars into patterns
    pats, bar_pat = [], {}
    key_to = {}
    for b in range(1, NBARS + 1):
        cells = pattern_cells(ev, b)
        key = json.dumps(cells, sort_keys=True)
        if key not in key_to:
            key_to[key] = len(pats)
            pats.append(cells)
        bar_pat[b] = key_to[key]

    # ---- batch 0: module + samples + instruments ----
    calls = [{"name": "module_new", "arguments": {"channels": NCH, "name": "Chrome Cathedral"}},
             {"name": "song_set", "arguments": {"bpm": BPM, "speed": SPEED, "length": NBARS,
                                               "loop_start": RESTART_BAR - 1}}]
    for idx, name, builder, rel, vol, pan, loop in synth.INSTRUMENTS:
        x = builder()
        pcm = base64.b64encode(synth.to_int16(x).tobytes()).decode()
        calls.append({"name": "sample_create_from_pcm",
                      "arguments": {"instrument": idx, "sample": 0, "pcm": pcm,
                                    "encoding": "int16", "name": name}})
        calls.append({"name": "sample_set",
                      "arguments": {"instrument": idx, "sample": 0, "name": name, "volume": vol,
                                    "panning": pan, "relative_note": rel, "finetune": 0,
                                    "loop_start": 0, "loop_length": len(x) if loop else 0,
                                    "flags": 17 if loop else 16}})
        calls.append({"name": "instrument_set", "arguments": {"instrument": idx, "name": name}})
    json.dump(calls, open(os.path.join(out_dir, 'b00_setup.json'), 'w'))

    # ---- batch 1: patterns ----
    calls = []
    for p, cells in enumerate(pats):
        calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": ROWS_PER_BAR}})
        for c in cells:
            a = {"pattern": p, "row": c['row'], "channel": c['channel']}
            if 'note' in c: a['note'] = c['note']
            if 'inst' in c: a['instrument'] = c['inst']
            if 'vol' in c: a['volume'] = c['vol']
            if 'fx' in c: a['effect'] = c['fx']; a['effect_param'] = c['fxp']
            calls.append({"name": "pattern_set_cell", "arguments": a})
    json.dump(calls, open(os.path.join(out_dir, 'b01_patterns.json'), 'w'))

    # ---- batch 2: order + loop ----
    calls = [{"name": "order_set", "arguments": {"position": b - 1, "pattern": bar_pat[b]}}
             for b in range(1, NBARS + 1)]
    calls.append({"name": "song_set", "arguments": {"length": NBARS, "loop_start": RESTART_BAR - 1,
                                                   "bpm": BPM, "speed": SPEED}})
    json.dump(calls, open(os.path.join(out_dir, 'b02_order.json'), 'w'))

    # manifest for audit trail
    manifest = {
        "title": "Chrome Cathedral", "bpm": BPM, "speed": SPEED, "channels": NCH,
        "bars": NBARS, "restart_bar": RESTART_BAR, "unique_patterns": len(pats),
        "bar_to_pattern": bar_pat,
        "chords": CHORD_OF,
        "instruments": [dict(idx=i, name=n, rel=r, volume=v, pan=p, looped=l)
                        for i, n, _, r, v, p, l in synth.INSTRUMENTS],
        "cells_total": sum(len(p) for p in pats),
    }
    json.dump(manifest, open(os.path.join(out_dir, 'manifest.json'), 'w'), indent=1)
    print("patterns:", len(pats), "cells:", manifest["cells_total"], "bars:", NBARS)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
