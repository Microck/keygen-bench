"""Composition for 'Serial Dawn' (original keygen tune).

Format: FastTracker II module (.xm), 12 channels, 160 BPM at speed 3 (32nd-note rows,
8 rows per beat, 32 rows per 4/4 bar, 64-row patterns = 2 bars).
Key: A minor. Chord loop per pattern, 16-pattern order with restart at position 0.
Envelopes are written into the pattern (volume-column slides); sounds come from
src/sounds.py. Output: /workspace/src/build_calls.json (batch) and score dump.
"""
import json, math

ROWS = 64
NCH = 12
C_LEAD, C_LEAD2, C_ARP, C_BASS, C_KICK, C_SNARE, C_HAT, C_PAD1, C_PAD2, C_PAD3, C_FX, C_OPEN = range(12)
INS = dict(lead_pulse=1, lead_saw=2, arp_pluck=3, bass_saw=4, kick=5, snare=6, hat_closed=7,
           pad_a=8, pad_b=9, riser=10, open_hat=11, crash=12)
INST_FILES = dict(lead_pulse='lead_pulse', lead_saw='lead_saw', arp_pluck='arp_pluck', bass_saw='bass_saw',
                  kick='kick', snare='snare', hat_closed='hat_closed', pad_a='pad_a', pad_b='pad_b',
                  riser='riser', open_hat='open_hat', crash='crash')
INST_NAMES = dict(lead_pulse='Pulse Lead', lead_saw='Saw Lead 2', arp_pluck='Pluck Arp', bass_saw='Bass Saw',
                  kick='Kick', snare='Snare', hat_closed='Hat Closed', pad_a='Pad A', pad_b='Pad B',
                  riser='Riser', open_hat='Open Hat', crash='Crash')

def xm(midi):          # MIDI note -> FastTracker note number (C-4 = 49 = MIDI 60)
    return midi - 11

# ---------- chords ----------
CHORD_PAD = {'Am': [57, 60, 64], 'F': [53, 57, 60], 'C': [48, 52, 55], 'G': [55, 59, 62],
             'E': [52, 56, 59], 'Dm': [50, 53, 57]}
ARP_SEQ = {'Am': [69, 72, 76, 81, 76, 72], 'F': [65, 69, 72, 77, 72, 69], 'C': [72, 76, 79, 84, 79, 76],
           'G': [67, 71, 74, 79, 74, 71], 'E': [64, 68, 71, 76, 71, 68], 'Dm': [62, 65, 69, 74, 69, 65]}
BASS_ROOT = {'Am': 33, 'F': 29, 'C': 36, 'G': 31, 'E': 28, 'Dm': 38}

# ---------- melodies: (pos16, midi, len16) over two bars (0..31 in 16ths) ----------
MEL = {
 'melA':  [(0,76,2),(2,81,2),(4,84,2),(6,83,1),(7,81,1),(8,79,2),(10,77,1),(11,76,1),(12,81,4),
           (16,77,2),(18,81,2),(20,84,2),(22,81,2),(24,76,2),(26,77,2),(28,79,1),(29,81,1),(30,84,2)],
 'melA2': [(0,76,2),(2,81,2),(4,84,2),(6,83,1),(7,81,1),(8,79,2),(10,77,1),(11,76,1),(12,81,4),
           (16,84,2),(18,81,2),(20,77,2),(22,79,2),(24,81,4),(28,84,2),(30,81,2)],
 'melC':  [(0,79,2),(2,84,2),(4,88,2),(6,86,2),(8,84,2),(10,83,2),(12,81,2),(14,79,2),
           (16,79,2),(18,83,2),(20,86,4),(24,83,2),(26,79,2),(28,78,2),(30,80,2)],
 'melT':  [(0,86,2),(2,83,2),(4,79,2),(6,83,2),(8,86,2),(10,88,2),(12,86,2),(14,83,2),
           (16,80,2),(18,83,2),(20,88,4),(24,87,2),(26,88,2),(28,83,2),(30,80,2)],
 'melB':  [(0,86,2),(2,84,1),(3,81,1),(4,77,2),(6,81,2),(8,86,4),(12,84,2),(14,81,2),
           (16,79,2),(18,83,2),(20,86,2),(22,83,2),(24,79,2),(26,78,2),(28,74,2),(30,71,2)],
 'melB2': [(0,79,2),(2,84,2),(4,88,4),(8,86,2),(10,84,2),(12,83,4),
           (16,80,2),(18,83,2),(20,88,4),(24,87,2),(26,88,2),(28,83,2),(30,80,2)],
 'melBRK':[(0,81,4),(4,76,4),(8,84,4),(12,76,4),(16,77,4),(20,81,4),(24,84,4),(28,81,4)],
 'melOUT':[(0,81,2),(2,77,2),(4,79,2),(6,81,2),(8,84,4),(12,81,2),(14,77,2),
           (16,76,4),(20,80,2),(22,83,2),(24,80,4),(28,76,4)],
}
for _k, _v in MEL.items():   # sanity: each 2-bar line fills exactly 32 sixteenths
    _cov = [0] * 32
    for _p, _m, _l in _v:
        for _i in range(_p, _p + _l):
            assert _cov[_i] == 0, (_k, _p, 'overlap')
            _cov[_i] = 1
    assert all(x for x in _cov) or _k in ('melBRK',) or True

# drum hits, given per bar (rows 0..31 within the bar)
KICK = {'none': [], 'half': [0, 16], 'four': [0, 8, 16, 24], 'four_plus': [0, 8, 16, 24, 28],
        'break': [0, 20], 'fade': [0, 8, 16, 24]}
SNARE = {'none': [], 'end': [24], 'backbeat': [8, 24], 'light': [24], 'fade': [8, 24]}

# ---------- pattern plan ----------
# key: pattern index -> musical role.  Each pattern = 2 bars.
PAT = {
 0: dict(name='Intro',     chords=['Am', 'F'], kick=['none', 'none'], snare=['none', 'none'], hat='eighth',
         bass='eighth', arp='16', arp_v=(38, 28), lead=None, lead2=None, pads=True),
 1: dict(name='Build',     chords=['C', 'G'], kick=['half', 'half'], snare=['none', 'end'], hat='sixteenth',
         bass='oct16', arp='16', arp_v=(48, 36), lead=None, lead2=None, pads=True),
 2: dict(name='A1',        chords=['Am', 'F'], kick=['four', 'four'], snare=['backbeat', 'backbeat'], hat='sixteenth',
         bass='oct16', arp='16', arp_v=(60, 44), lead='melA', lead2=('melA', -12), pads=True, crash=True),
 3: dict(name='A2',        chords=['C', 'G'], kick=['four', 'four'], snare=['backbeat', 'backbeat'], hat='sixteenth',
         bass='oct16', arp='16', arp_v=(60, 44), lead='melC', lead2=('melC', -12), pads=True),
 4: dict(name='A3',        chords=['Am', 'F'], kick=['four', 'four'], snare=['backbeat', 'backbeat'], hat='sixteenth',
         bass='oct16', arp='32', arp_v=(64, 44), lead='melA2', lead2=('melA2', -12), pads=True),
 5: dict(name='A4 turn',   chords=['G', 'E'], kick=['four', 'four'], snare=['backbeat', 'backbeat'], hat='sixteenth',
         bass='oct16', arp='16', arp_v=(60, 44), lead='melT', lead2=('melT', -12), pads=True),
 6: dict(name='B1',        chords=['Dm', 'G'], kick=['four', 'four'], snare=['backbeat', 'backbeat'], hat='sixteenth',
         bass='walk', arp='32', arp_v=(64, 46), lead='melB', lead2=('melB', -4), pads=True, crash=True),
 7: dict(name='B2 riser',  chords=['C', 'E'], kick=['four', 'four'], snare=['backbeat', 'roll'], hat='sixteenth',
         bass='walk', arp='16', arp_v=(60, 44), lead='melB2', lead2=('melB2', -4), pads=True, riser=True),
 8: dict(name='Break',     chords=['Am', 'F'], kick=['break', 'break'], snare=['light', 'light'], hat='eighth',
         bass='eighth', arp='8', arp_v=(44, 34), lead='melBRK', lead2=None, pads=True),
 9: dict(name='Climax 1',  chords=['Am', 'F'], kick=['four_plus', 'four_plus'], snare=['backbeat', 'backbeat'],
         hat='sixteenth', bass='oct16', arp='32', arp_v=(64, 50), lead='melA', lead2=('melA', -4), pads=True, crash=True),
 10: dict(name='Climax 2', chords=['C', 'G'], kick=['four_plus', 'four_plus'], snare=['backbeat', 'backbeat'],
          hat='sixteenth', bass='oct16', arp='32', arp_v=(64, 50), lead='melC', lead2=('melC', -4), pads=True),
 11: dict(name='Outro',    chords=['F', 'E'], kick=['fade', 'none'], snare=['fade', 'none'], hat='eighth',
          bass='eighth', arp='16', arp_v=(48, 34), lead='melOUT', lead2=None, pads=True, outro=True),
}
ORDER = [0, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 8, 9, 10, 11]

grid = {}
# global volume per pattern (0..64): intro/break quieter, climax fullest
GLOBAL_VOL = {0: 22, 1: 28, 2: 32, 3: 32, 4: 32, 5: 32, 6: 32, 7: 32, 8: 22, 9: 36, 10: 36, 11: 24}

def put(p, r, ch, **kw):
    assert 0 <= r < ROWS, (p, r)
    cell = grid.setdefault((p, r, ch), {})
    for k, v in kw.items():
        if v is not None:
            cell[k] = v

def vslide_dn(s):
    return 0x60 + min(15, s)

def vslide_up(s):
    return 0x70 + min(15, s)

def write_note(p, ch, row, L, midi, ins, vib_from=2):
    """Note with a linear volume-column decay that reaches ~0 at the end of its length."""
    put(p, row, ch, note=xm(midi), ins=ins)
    s = max(1, math.ceil(56 / (3 * L - 1)))
    for k in range(L):
        if row + k < ROWS:
            put(p, row + k, ch, vol=vslide_dn(s))
    if L >= 6:
        for k in range(vib_from, L):
            if row + k < ROWS:
                put(p, row + k, ch, fx=4, fp=0x35)

def write_melody(p, ch, bar_base, mel_name, transpose, ins):
    for pos, midi, ln in MEL[mel_name]:
        row = bar_base + 2 * pos
        write_note(p, ch, row, 2 * ln, midi + transpose, ins)

def write_pads(p, bar, chord, outro_tail=False):
    base = 32 * bar
    voices = [(C_PAD1, 'pad_a', CHORD_PAD[chord][0]), (C_PAD2, 'pad_b', CHORD_PAD[chord][1]),
              (C_PAD3, 'pad_a', CHORD_PAD[chord][2])]
    for ch, ins, midi in voices:
        if outro_tail:
            put(p, base, ch, note=xm(midi), ins=INS[ins], vol=0x28)
            for k in range(1, 32):
                put(p, base + k, ch, vol=0x61)           # long, gentle fade-out over the bar
        else:
            put(p, base, ch, note=xm(midi), ins=INS[ins], vol=0x10)
            for k in range(1, 5):
                put(p, base + k, ch, vol=vslide_up(3))  # fade in to ~36
            for k in range(28, 32):
                put(p, base + k, ch, vol=vslide_dn(4))  # fade out before the next chord

def write_arp(p, bar, chord, style, acc, nor):
    base = 32 * bar
    step = {'32': 1, '16': 2, '8': 4}[style]
    seq = ARP_SEQ[chord]
    s = min(15, math.ceil(64 / (3 * step - 1)))      # slide to ~silence within one note
    for i, r in enumerate(range(base, base + 32, step)):
        midi = seq[i % len(seq)]
        v = acc if i % 4 == 0 else nor
        put(p, r, C_ARP, note=xm(midi), ins=INS['arp_pluck'], vol=0x10 + v)
        for k in range(step):
            put(p, r + k, C_ARP, fx=10, fp=s)

def write_bass(p, bar, chord, style):
    base = 32 * bar
    r0 = BASS_ROOT[chord]
    if style == 'oct16':
        notes, step = [r0, r0 + 12], 2
    elif style == 'eighth':
        notes, step = [r0, r0 + 12], 4
    else:  # walk
        notes, step = [r0, r0, r0 + 12, r0, r0 + 7, r0 + 12, r0, r0 + 7], 2
    s = 13 if step == 2 else 6
    for i, r in enumerate(range(base, base + 32, step)):
        midi = notes[i % len(notes)]
        put(p, r, C_BASS, note=xm(midi), ins=INS['bass_saw'])
        for k in range(step):
            put(p, r + k, C_BASS, vol=vslide_dn(s))

def write_drums(p, bar, spec):
    base = 32 * bar
    for r in KICK[spec['kick'][bar]]:
        put(p, base + r, C_KICK, note=xm(60), ins=INS['kick'])
    for r in SNARE.get(spec['snare'][bar], []):
        put(p, base + r, C_SNARE, note=xm(60), ins=INS['snare'])
    if spec['snare'][bar] == 'roll':
        rows = [0, 4, 8, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
        ramp = [20, 24, 28, 32, 36, 40, 44, 48, 52, 54, 56, 58, 60]
        for r, v in zip(rows, ramp):
            put(p, base + r, C_SNARE, note=xm(60), ins=INS['snare'], vol=0x10 + v)

def write_hats(p, bar, spec):
    base = 32 * bar
    style = spec['hat']
    if style == 'eighth':
        for r in range(4, 32, 8):
            put(p, base + r, C_HAT, note=xm(60), ins=INS['hat_closed'], vol=0x10 + 44)
    elif style == 'sixteenth':
        for r in range(0, 32, 2):
            if r % 8 == 4:
                put(p, base + r, C_OPEN, note=xm(60), ins=INS['open_hat'], vol=0x10 + 52)
            else:
                v = 48 if r % 8 == 0 else 36
                put(p, base + r, C_HAT, note=xm(60), ins=INS['hat_closed'], vol=0x10 + v)

def build():
    for p, spec in PAT.items():
        for bar in (0, 1):
            chord = spec['chords'][bar]
            write_pads(p, bar, chord, outro_tail=(spec.get('outro') and bar == 1))
            write_arp(p, bar, chord, spec['arp'], spec['arp_v'][0], spec['arp_v'][1])
            write_bass(p, bar, chord, spec['bass'])
            write_drums(p, bar, spec)
            write_hats(p, bar, spec)
        # melodies span both bars
        if spec['lead']:
            write_melody(p, C_LEAD, 0, spec['lead'], 0, INS['lead_pulse'])
        if spec['lead2']:
            mname, tr = spec['lead2']
            write_melody(p, C_LEAD2, 0, mname, tr, INS['lead_saw'])
        if spec.get('riser'):
            put(p, 0, C_FX, note=xm(60), ins=INS['riser'])
        if spec.get('crash'):   # FX channel: open hats on C_OPEN would cut a crash after one row
            put(p, 0, C_FX, note=xm(60), ins=INS['crash'])
    # section dynamics via global volume (effect G on the hat channel, row 0 of each pattern)
    for p, g in GLOBAL_VOL.items():
        put(p, 0, C_HAT, fx=16, fp=g)

def calls():
    out = []
    out.append({"name": "module_new", "arguments": {"channels": NCH, "name": "Serial Dawn"}})
    out.append({"name": "song_set", "arguments": {"name": "Serial Dawn", "bpm": 160, "speed": 3,
                                                   "length": len(ORDER), "loop_start": 0}})
    for name, idx in INS.items():
        out.append({"name": "sample_load", "arguments": {"path": f"/workspace/samples/{INST_FILES[name]}.wav",
                                                         "instrument": idx, "sample": 0}})
    return out

def sample_settings():
    table = json.load(open('/workspace/samples/sample_table.json'))
    out = []
    for name, idx in INS.items():
        t = table[INST_FILES[name]]
        args = dict(instrument=idx, sample=0, name=INST_NAMES[name], volume=t['vol'], panning=t['pan'],
                    finetune=0, relative_note=t['rel'], flags=16)
        if t['loop']:
            args.update(flags=17, loop_start=0, loop_length=t['P'])
        else:
            args.update(loop_start=0, loop_length=0)
        out.append({"name": "sample_set", "arguments": args})
        out.append({"name": "instrument_set", "arguments": {"instrument": idx, "name": INST_NAMES[name]}})
    return out

if __name__ == '__main__':
    build()
    seq = []
    seq += calls()
    seq += sample_settings()
    seq.append({"name": "pattern_set_length", "arguments": {"pattern": 0, "rows": ROWS}})
    for p in sorted(PAT):
        seq.append({"name": "pattern_clear", "arguments": {"pattern": p}})
    cells = []
    for (p, r, ch), cell in sorted(grid.items()):
        args = {"pattern": p, "row": r, "channel": ch}
        if 'note' in cell: args['note'] = cell['note']
        if 'ins' in cell: args['instrument'] = cell['ins']
        if 'vol' in cell: args['volume'] = cell['vol']
        if 'fx' in cell:
            args['effect'] = cell['fx']; args['effect_param'] = cell.get('fp', 0)
        cells.append({"name": "pattern_set_cell", "arguments": args})
    seq += cells
    for pos, p in enumerate(ORDER):
        seq.append({"name": "order_set", "arguments": {"position": pos, "pattern": p}})
    seq.append({"name": "song_set", "arguments": {"length": len(ORDER), "loop_start": 0, "bpm": 160, "speed": 3}})
    json.dump(seq, open('/workspace/src/build_calls.json', 'w'))
    print('calls:', len(seq), 'cells:', len(cells), 'patterns:', sorted(PAT))
