"""Build the keygen tune: writes an FT2 batch file, runs it, saves + renders."""
import json, os, subprocess, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tune_data import *

HERE = os.path.dirname(os.path.abspath(__file__))
INST_DIR = os.path.join(HERE, 'inst')

ROWS = 64
NCH = 8
BPM, SPEED = 150, 6

# ------------------------------------------------------------------ pattern
class Pat:
    def __init__(self):
        self.cells = {}          # (ch,row) -> dict
        self.notes = {}          # ch -> list of (row, length, vol)
    def put(self, ch, row, midi, length, vol, inst, fx=None, param=0, cell=None):
        row = int(row)
        if row >= ROWS: return
        if cell is None:
            cell = dict(note=midi-12, instrument=inst, volume=vol)
            if fx is not None:
                cell['effect'] = fx; cell['effect_param'] = param
        self.cells[(ch, row)] = cell
        if length:
            self.notes.setdefault(ch, []).append((row, int(length), vol))
    def fx(self, ch, row, fx, param):
        row = int(row)
        if row >= ROWS: return
        c = self.cells.setdefault((ch, row), {})
        c['effect'] = fx; c['effect_param'] = param
    def drum(self, ch, row, inst, vol, note=61):
        self.put(ch, row, note, 0, vol, inst)

def fade_rate(vol, rows):
    return max(1, min(15, int(math.ceil(vol/(6.0*rows)))))

def finalize(p, smooth_channels=(CH_LEAD, CH_HARM, CH_BASS, CH_PAD)):
    """Insert short volume slides before every re-trigger so notes end smoothly."""
    for ch, lst in p.notes.items():
        if ch not in smooth_channels: continue
        lst.sort()
        for i, (row, length, vol) in enumerate(lst):
            end = row + length
            if i+1 < len(lst):
                nxt = lst[i+1][0]
                gap = nxt - end
                if gap == 0:
                    fr, start = 1, nxt-1
                else:
                    fr = min(gap, 3); start = nxt-fr
            else:
                fr = min(ROWS-end, 3)
                if fr <= 0: continue
                start = end
            if start < 0: continue
            key = (ch, start)
            if key in p.cells and 'note' in p.cells[key]:
                continue
            p.cells[key] = dict(effect=10, effect_param=fade_rate(vol, fr))

# ------------------------------------------------------------------ parts
def add_bass(p, chordname, style='drive', vol=50, base=0):
    ch = CHORDS[chordname]; r = ch['root']
    if style == 'drive':
        seq = [(0, r), (2, r), (4, r+12), (6, r), (8, r), (10, r+7), (12, r), (14, r+12)]
    elif style == 'simple':
        seq = [(0, r), (8, r)]
    elif style == 'busy':
        seq = [(0, r), (2, r), (3, r+12), (4, r), (6, r+7), (8, r),
               (10, r), (11, r+12), (12, r), (14, r+7)]
    elif style == 'walk':
        seq = [(0, r), (4, r), (6, r+7), (8, r+12), (12, r+12), (14, r+7)]
    else:
        seq = [(0, r), (2, r), (4, r+12), (6, r), (8, r), (10, r+7), (12, r), (14, r)]
    for off, n in seq:
        p.put(CH_BASS, base+off, n, 2, vol, I['bass'])

def add_drums(p, style='drive'):
    for b in range(4):
        base = b*16
        if style == 'light':
            kicks = [0, 8]; snares = [4, 12]
        elif style == 'drive':
            kicks = [0, 6, 8, 14]; snares = [4, 12]
        elif style == 'hard':
            kicks = [0, 3, 6, 8, 11, 14]; snares = [4, 12, 15]
        elif style == 'half':
            kicks = [0]; snares = [8]
        else:
            kicks = [0, 8]; snares = [4, 12]
        for k in kicks:
            p.drum(CH_DRUM, base+k, I['kick'], 52)
        for s in snares:
            p.drum(CH_DRUM, base+s, I['snare'], 46)

def add_hats(p, style='8th', openbar=False, vol=32):
    step = 2 if style == '8th' else 1
    for b in range(4):
        base = b*16
        for off in range(0, 16, step):
            v = vol if off % 4 == 0 else (vol-8 if step == 1 else vol-6)
            p.drum(CH_HAT, base+off, I['hat'], v)
        if openbar and b % 2 == 1:
            p.drum(CH_HAT, base+14, I['openhat'], 34)

def add_arp(p, chordname, style='beat', vol=30, base=0):
    ch = CHORDS[chordname]
    if style == 'beat':
        offs = [0, 4, 8, 12]
    elif style == 'bar':
        offs = [0]
    elif style == 'half':
        offs = [0, 8]
    elif style == 'sync':
        offs = [0, 3, 6, 8, 11, 14]
    else:
        offs = [0, 4, 8, 12]
    for j, off in enumerate(offs):
        n = ch['root']+12
        if j % 3 == 2: n += 12
        p.put(CH_ARP, base+off, n, 4, vol, I['arp'], fx=0, param=ch['arp'])

def add_pad(p, chordname, vol=26, base=0):
    ch = CHORDS[chordname]
    p.put(CH_PAD, base, ch['pad'], 16, vol, I['pad'])

def add_chords(p, chordname, style='off', vol=30, base=0):
    ch = CHORDS[chordname]
    if style == 'off':
        offs = [2, 6, 10, 14]
    elif style == 'on':
        offs = [0, 4, 8, 12]
    elif style == 'half':
        offs = [0, 8]
    else:
        offs = [2, 10]
    for off in offs:
        p.put(CH_CHORD, base+off, ch['root']+24, 2, vol, I['chord'], fx=0, param=ch['arp'])

def add_phrase(p, ch, phrase, vib=None):
    """vib = (speed, depth) -> adds a held vibrato on the longer notes"""
    for (row, midi, length, vol) in phrase:
        p.put(ch, row, midi, length, vol, I['lead'] if ch == CH_LEAD else I['harm'])
        if vib and length >= 4:
            sp, dp = vib
            c = p.cells[(ch, row)]
            c['effect'] = 4; c['effect_param'] = (sp << 4) | dp
            for r in range(row+1, row+length-1):
                if (ch, r) not in p.cells:
                    p.fx(ch, r, 4, (sp << 4) | dp)

FILL_UP   = [(60, 77, 1, 56), (61, 79, 1, 58), (62, 81, 1, 60), (63, 84, 1, 64)]
FILL_DOWN = [(60, 84, 1, 60), (61, 81, 1, 58), (62, 79, 1, 56), (63, 74, 1, 54)]

def add_fill(p, phrase, drums=True, snare_roll=True):
    for (row, midi, length, vol) in phrase:
        p.put(CH_LEAD, row, midi, length, vol, I['lead'])
    if snare_roll:
        for i, r in enumerate(range(60, 64)):
            p.drum(CH_DRUM, r, I['snare'], 30+i*8)

def add_organ(p, figure=None, vol=34):
    """sustained arpeggiated organ chords for the break"""
    for (row, midi, length, v) in (figure or BREAK_CHORD):
        p.put(CH_PAD, row, midi, length, v, I['organ'], fx=0, param=0x47)

def add_toms(p, row=60, vol=46):
    for i, n in enumerate((45, 48, 50, 53)):
        p.drum(CH_DRUM, row+i, I['tom'], vol+i*3)

def add_crash(p, row=0, vol=40):
    p.drum(CH_HAT, row, I['crash'], vol)

# ------------------------------------------------------------------ section
def section(prog, lead=None, harm=None, arp=None, bass='drive', bassvol=50,
            drums='drive', hats='8th', pad=False, chords=None, crash=False,
            arpvol=30, chordvol=30, padvol=26, vib=None, fill=None,
            hatsvol=32, harmvol=None):
    p = Pat()
    for b, cname in enumerate(prog):
        base = b*16
        if bass:
            add_bass(p, cname, bass, bassvol, base)
        if arp:
            add_arp(p, cname, arp, arpvol, base)
        if pad:
            add_pad(p, cname, padvol, base)
        if chords:
            add_chords(p, cname, chords, chordvol, base)
    if lead:
        add_phrase(p, CH_LEAD, lead, vib)
    if harm:
        add_phrase(p, CH_HARM, harm)
    add_drums(p, drums)
    add_hats(p, hats, openbar=bool(harm or chords), vol=hatsvol)
    if crash:
        add_crash(p, 0, 42)
    if fill:
        add_fill(p, fill)
    finalize(p)
    return p

# ------------------------------------------------------------------ arrangement
def build_all():
    pats = []
    # ---- intro -------------------------------------------------------------
    pats.append(section(['Dm', 'Dm', 'Bb', 'C'], arp='bar', bass='drive', drums='light',
                         hats='8th', pad=True, padvol=20, chords='off', chordvol=24,
                         bassvol=48, arpvol=26, hatsvol=28))
    pats.append(section(['Dm', 'Bb', 'Gm', 'A'], arp='sync', bass='drive', drums='light',
                         hats='8th', pad=True, padvol=24, chords='off', chordvol=26,
                         bassvol=48, arpvol=28, hatsvol=30))
    # ---- build -------------------------------------------------------------
    pats.append(section(['Dm', 'Bb', 'F', 'C'], lead=BUILD_A, arp='beat', bass='drive',
                         drums='drive', hats='8th', chords='off', chordvol=28, arpvol=28))
    pats.append(section(['Dm', 'C', 'Bb', 'Am'], lead=BUILD_B, arp='beat', bass='busy',
                         drums='hard', hats='16th', pad=True, chords='off', chordvol=30,
                         arpvol=30, fill=FILL_UP))
    # ---- main themes -------------------------------------------------------
    pats.append(section(['Dm', 'Bb', 'F', 'C'], lead=MAIN_A, harm=HARM_A, arp='sync',
                         bass='drive', drums='drive', hats='16th', pad=True, chords='off',
                         chordvol=30, arpvol=30, crash=True, vib=(6, 4)))
    pats.append(section(['Dm', 'Bb', 'Gm', 'Am'], lead=MAIN_A2, harm=HARM_B, arp='sync',
                         bass='drive', drums='drive', hats='16th', pad=True, chords='off',
                         chordvol=30, arpvol=30, vib=(6, 4)))
    pats.append(section(['F', 'C', 'Dm', 'Bb'], lead=MAIN_B, harm=HARM_A, arp='sync',
                         bass='drive', drums='drive', hats='16th', pad=True, chords='off',
                         chordvol=30, arpvol=30, vib=(6, 4)))
    p = section(['Dm', 'Gm', 'Am', 'Am'], lead=MAIN_C, harm=HARM_B, arp='sync',
                bass='drive', drums='drive', hats='16th', pad=True, chords='off',
                chordvol=30, arpvol=30, vib=(6, 4), fill=FILL_UP)
    add_toms(p, 56, 40)
    pats.append(p)
    # ---- break -------------------------------------------------------------
    p = section(['Dm', 'Bb', 'F', 'C'], harm=HARM_A, arp='bar', bass='walk',
                drums='half', hats='8th', padvol=30, arpvol=24,
                bassvol=44, hatsvol=26)
    add_organ(p, BREAK_CHORD)
    finalize(p)
    pats.append(p)
    p = section(['Gm', 'Am', 'Dm', 'Am'], harm=HARM_B, arp='beat', bass='walk',
                drums='half', hats='8th', padvol=30, arpvol=26,
                bassvol=44, hatsvol=26, fill=FILL_DOWN)
    add_organ(p, BREAK_CHORD2)
    finalize(p)
    pats.append(p)
    # ---- main themes, hotter ------------------------------------------------
    pats.append(section(['Dm', 'Bb', 'F', 'C'], lead=MAIN_A, harm=HARM_A, arp='sync',
                         bass='busy', drums='hard', hats='16th', pad=True, chords='on',
                         chordvol=32, arpvol=32, crash=True, vib=(6, 4)))
    pats.append(section(['Dm', 'Bb', 'Gm', 'Am'], lead=MAIN_A2, harm=HARM_B, arp='sync',
                         bass='busy', drums='hard', hats='16th', pad=True, chords='on',
                         chordvol=32, arpvol=32, vib=(6, 4)))
    pats.append(section(['F', 'C', 'Dm', 'Bb'], lead=MAIN_B, harm=HARM_A, arp='sync',
                         bass='busy', drums='hard', hats='16th', pad=True, chords='on',
                         chordvol=32, arpvol=32, vib=(6, 4)))
    pats.append(section(['Dm', 'Gm', 'Am', 'Am'], lead=MAIN_C, harm=HARM_B, arp='sync',
                         bass='busy', drums='hard', hats='16th', pad=True, chords='on',
                         chordvol=32, arpvol=32, vib=(6, 4), fill=FILL_UP))
    # ---- peak ---------------------------------------------------------------
    pats.append(section(['Dm', 'Bb', 'F', 'C'], lead=MAIN_A, harm=HARM_A, arp='sync',
                         bass='busy', drums='hard', hats='16th', pad=True, chords='on',
                         chordvol=34, arpvol=34, crash=True, vib=(8, 6)))
    pats.append(section(['Dm', 'C', 'Bb', 'Am'], lead=MAIN_C, harm=HARM_B, arp='sync',
                         bass='busy', drums='hard', hats='16th', pad=True, chords='on',
                         chordvol=34, arpvol=34, crash=True, vib=(8, 6), fill=FILL_DOWN))
    # ---- outro --------------------------------------------------------------
    pats.append(section(['Dm', 'Bb', 'F', 'C'], lead=OUTRO_LEAD, arp='beat', bass='drive',
                         drums='drive', hats='16th', pad=True, chords='off', chordvol=28,
                         arpvol=30, bassvol=48, hatsvol=30))
    p = section(['Dm', 'Gm', 'A', 'Dm'], arp='beat', bass='walk', drums='light',
                hats='8th', pad=True, padvol=30, arpvol=30, bassvol=46, crash=True,
                hatsvol=28)
    for r, n, v in ((48, 61, 40), (52, 65, 42), (56, 67, 44)):
        p.put(CH_HAT, r, n, 0, v, I['zap'])
    # let the last chord ring out and fade the loop seam
    finalize(p)
    pats.append(p)
    return pats

# ------------------------------------------------------------------ batch
def build_batch(pats, out_path):
    calls = []
    calls.append(dict(name='module_new', arguments=dict(channels=NCH, name='Keygen Sequence')))
    for i, (nm, wav, vol, pan) in enumerate(INSTS):
        calls.append(dict(name='sample_load',
                          arguments=dict(path=os.path.join(INST_DIR, wav), instrument=i+1)))
        calls.append(dict(name='sample_set',
                          arguments=dict(instrument=i+1, sample=0, name=nm, volume=vol,
                                         panning=pan, flags=0)))
    for pi, p in enumerate(pats):
        calls.append(dict(name='pattern_set_length', arguments=dict(pattern=pi, rows=ROWS)))
    for pi, p in enumerate(pats):
        for (ch, row), c in sorted(p.cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            a = dict(pattern=pi, row=row, channel=ch)
            for k in ('note', 'instrument', 'volume', 'effect', 'effect_param'):
                if k in c and c[k] is not None:
                    a[k] = c[k]
            if 'volume' in a:
                a['volume'] = max(8, int(round(a['volume']*0.88)))
            calls.append(dict(name='pattern_set_cell', arguments=a))
    calls.append(dict(name='song_set', arguments=dict(name='Keygen Sequence', bpm=BPM,
                                                      speed=SPEED, length=len(pats),
                                                      loop_start=0, channels=NCH)))
    for i in range(len(pats)):
        calls.append(dict(name='order_set', arguments=dict(position=i, pattern=i)))
    json.dump(calls, open(out_path, 'w'))
    return len(calls)

if __name__ == '__main__':
    pats = build_all()
    n = build_batch(pats, '/workspace/build/batch.json')
    print('patterns', len(pats), 'calls', n, 'cells', sum(len(p.cells) for p in pats))
