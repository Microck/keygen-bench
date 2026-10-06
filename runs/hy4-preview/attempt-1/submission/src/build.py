"""Build the module: create instruments, write patterns, save, render, analyse."""
import json, subprocess, wave, sys, os, wave as _w
import numpy as np
sys.path.insert(0, '/workspace/src')
from compose import *
from waves import T, freq

BPM, SPEED = 145, 6
ROWSEC = 60.0/(BPM*SPEED) * SPEED / 6 * SPEED/6   # placeholder (recomputed below)
ROWSEC = None

import os
SOLO = int(os.environ.get('SOLO', 0))

INSTS = [
    # (index, file, name, vol, pan, looped)
    (1,  'kick',    'KickDrv',      50, 128, False),
    (2,  'snare',   'SnareX',       48, 128, False),
    (3,  'tom',     'TomFill',      50, 108, False),
    (4,  'hat',     'HatCls',       40, 152, False),
    (5,  'openhat', 'HatOpn',       30, 152, False),
    (6,  'crash',   'CrashRide',    34, 100, False),
    (7,  'bass',    'BassFat',      62, 128, True),
    (8,  'pad',     'PadSaw',       36, 104, True),
    (9,  'organ',   'OrganSoft',    40, 150, True),
    (10, 'chip',    'ChipPls',      48,  56, True),
    (11, 'lead',    'LeadPls',      46, 192, True),
    (12, 'lead2',   'LeadEcho',     40,  64, True),
]

# ------------------------------------------------------------------ melody
m = lambda *ev: list(ev)
TH_A = [
    m((0,2,'A-5'),(2,2,'B-5'),(4,2,'C-6'),(6,2,'E-6'),(8,2,'D-6'),(10,2,'C-6'),(12,4,'B-5')),
    m((0,2,'C-6'),(2,2,'A-5'),(4,2,'F-5'),(6,2,'G-5'),(8,4,'A-5'),(12,2,'C-6'),(14,2,'D-6')),
    m((0,2,'E-6'),(2,2,'G-6'),(4,2,'E-6'),(6,2,'C-6'),(8,2,'D-6'),(10,2,'E-6'),(12,4,'G-6')),
    m((0,2,'D-6'),(2,2,'B-5'),(4,2,'G-5'),(6,2,'B-5'),(8,4,'D-6'),(12,2,'B-5'),(14,2,'G-5')),
    m((0,2,'A-5'),(2,2,'C-6'),(4,4,'E-6'),(8,2,'G-6'),(10,2,'E-6'),(12,4,'C-6')),
    m((0,2,'F-6'),(2,2,'E-6'),(4,4,'C-6'),(8,2,'A-5'),(10,2,'C-6'),(12,4,'F-5')),
    m((0,2,'D-6'),(2,2,'F-6'),(4,2,'E-6'),(6,2,'D-6'),(8,2,'C-6'),(10,2,'B-5'),(12,4,'A-5')),
    m((0,2,'B-5'),(2,2,'G#5'),(4,2,'B-5'),(6,2,'E-6'),(8,2,'D-6'),(10,2,'B-5'),(12,4,'E-6')),
]
TH_B = [
    m((0,4,'A-5'),(4,4,'C-6'),(8,6,'F-6'),(14,2,'E-6')),
    m((0,4,'D-6'),(4,4,'B-5'),(8,6,'G-6'),(14,2,'F-6')),
    m((0,4,'E-6'),(4,4,'C-6'),(8,8,'A-5')),
    m((0,2,'E-6'),(2,2,'G-6'),(4,4,'F-6'),(8,8,'E-6')),
    m((0,4,'C-6'),(4,4,'A-5'),(8,6,'F-5'),(14,2,'A-5')),
    m((0,4,'B-5'),(4,4,'D-6'),(8,6,'G-6'),(14,2,'B-5')),
    m((0,4,'A-5'),(4,4,'F-6'),(8,8,'D-6')),
    m((0,2,'G#5'),(2,2,'B-5'),(4,4,'E-6'),(8,8,'B-5')),
]
SUS = m((0,8,'E-6'),(8,8,'C-6'))

def events_conv(ev):
    return [(st, du, N(nt)) for st, du, nt in ev]

# ------------------------------------------------------------------ arrangement (one entry per bar)
ARR = []
def B(chord, drums, bass, pad, arp, lead=None, organ=None, crash=False, leadvol=50,
      echovol=None, arpv=26, paddv=34, arpstyle='up', echodelay=3, leadinst='lead',
      bassv=None, nopad=False):
    ARR.append(dict(chord=chord, drums=drums, bass=bass, pad=pad, arp=arp, lead=lead,
                    organ=organ, crash=crash, leadvol=leadvol, echovol=echovol, arpv=arpv,
                    paddv=paddv, arpstyle=arpstyle, echodelay=echodelay, leadinst=leadinst,
                    bassv=bassv, nopad=nopad))

# intro 4 bars
B('Am', 'intro1', 'none', 'none', 'none', crash=True)
B('Am', 'intro1', 'quiet', 'none', 'none')
B('F',  'intro2', 'eighth', 'hold', 'none')
B('E',  'intro2', 'eighth', 'hold', 'sparse', arpv=22)
# theme A  (8 bars)
for i, (ch, mel) in enumerate(zip(['Am','F','C','G','Am','F','Dm','E'], TH_A)):
    B(ch, 'main', 'main', 'hold', 'up', lead=mel, leadvol=50,
      echovol=(28, 16), crash=(i == 0))
# section B (8 bars)
for i, (ch, mel) in enumerate(zip(['F','G','Am','Am','F','G','Dm','E'], TH_B)):
    B(ch, 'busy', 'driving', 'stabs', 'oct', lead=mel, leadvol=48, paddv=30,
      echovol=(26, 14), organ='off', crash=(i == 0), echodelay=2)
# breakdown (4 bars)
B('Am', 'nodrums', 'root', 'hold', 'sparse', lead=SUS, leadvol=44, paddv=36, arpv=20, echovol=(24,0))
B('F',  'half',    'root', 'hold', 'sparse', paddv=36, arpv=20)
B('G',  'breakfill', 'eighth', 'hold', 'up', arpv=26, paddv=34)
B('E',  'nodrums', 'none', 'hold', 'sparse', arpv=20, paddv=38)
# theme A' (8 bars) - fuller
for i, (ch, mel) in enumerate(zip(['Am','F','C','G','Am','F','Dm','E'], TH_A)):
    B(ch, 'busy', 'driving', 'hold', 'updn' if False else 'updn2', lead=mel, leadvol=52,
      echovol=(30, 18), organ='off', crash=(i == 0), arpv=26)
# section B' + coda (8 bars)
for i, (ch, mel) in enumerate(zip(['F','G','Am','Am','F','G','Dm','E'], TH_B)):
    B(ch, 'busy', 'driving', 'hold', 'oct', lead=mel, leadvol=50, paddv=32,
      echovol=(28, 16), organ='off', arpv=24)
# outro (4 bars)
B('Am', 'main', 'main', 'hold', 'up', lead=None, arpv=26, crash=True)
B('Am', 'main', 'main', 'hold', 'up', lead=m((0,4,'E-6'),(4,4,'C-6'),(8,8,'A-5')), leadvol=48, echovol=(26,14), arpv=24)
B('Am', 'half', 'root', 'hold', 'sparse', lead=None, paddv=38, arpv=20)
B('E',  'lastbar', 'none', 'hold', 'none', paddv=34)

# ------------------------------------------------------------------ render arrangement into grid
def build_grid():
    s = Song()
    prev = None
    for bi, b in enumerate(ARR):
        r0 = bi*BAR
        ch = b['chord']
        if b['crash']:
            add_crash(s, r0, 38)
        # last bar of every eight-bar phrase gets a drum fill (outside intro/breakdown)
        dstyle = b['drums']
        if b['drums'] in ('main', 'busy') and (bi % 8) == 7:
            dstyle = 'fill'
        drum(s, r0, dstyle)
        bass_part(s, r0, ch, b['bass'])
        prev = pad_part(s, r0, ch, prev, b['pad'], vol=b['paddv'])
        if b['arp'] != 'none':
            arp_part(s, r0, ch, b['arp'], vol=b['arpv'])
        if b['organ']:
            organ_stabs(s, r0, ch, prev, vol=b['paddv']+2)
        if b['lead']:
            line(s, LEAD, r0, events_conv(b['lead']), b['leadinst'], vol=b['leadvol'],
                 echo='lead2', echoch=ECHO, echodelay=b['echodelay'], echovol=b['echovol'])
    # final bar: accelerating hats + stop everything for a clean loop
    nrows = len(ARR)*BAR
    last = (len(ARR)-1)*BAR
    for i in range(16):
        s.put(last+i, HAT, note=49, inst=INST['hat'], vol=16+int(i*2.4))
    s.put(last+15, SNARE, note=49, inst=INST['snare'], vol=52)
    cut(s, nrows-1, [BASS, P1, P2, P3, ARP, LEAD, ECHO, ORG1, ORG2, ORG3])
    return s, nrows

# per-instrument output trim, applied to the pattern volume column
GAIN = 0.75
MIX = {1:0.75, 2:0.82, 3:0.9, 4:1.3, 5:1.0, 6:0.85, 7:1.05, 8:1.0, 9:0.75, 10:1.5, 11:1.0, 12:0.7}

def main():
    s, nrows = build_grid()
    for k, v in s.g.items():
        inst = v['inst']
        if inst in MIX and v['vol']:
            v['vol'] = int(max(1, min(64, round(v['vol']*MIX[inst]*GAIN))))
    if SOLO:
        s.g = {k: v for k, v in s.g.items() if v['inst'] == SOLO}
    calls = [{'name': 'module_new', 'arguments': {'name': 'Keygen Drive', 'channels': 16}},
             {'name': 'song_set', 'arguments': {'name': 'Keygen Drive', 'bpm': BPM, 'speed': SPEED}}]
    for idx, fn, nm, vol, pan, looped in INSTS:
        calls.append({'name': 'sample_load', 'arguments': {'path': f'/workspace/src/wav/{fn}.wav', 'instrument': idx}})
        st = {'instrument': idx, 'sample': 0, 'name': nm, 'volume': vol, 'panning': pan,
              'finetune': 0, 'relative_note': 0}
        if looped:
            L = len(open(f'/workspace/src/wav/{fn}.wav','rb').read()) and None
            wv = _w.open(f'/workspace/src/wav/{fn}.wav'); ln = wv.getnframes(); wv.close()
            st.update(loop_start=0, loop_length=ln, flags=1)
        else:
            st.update(loop_start=0, loop_length=0, flags=0)
        calls.append({'name': 'sample_set', 'arguments': st})
        calls.append({'name': 'instrument_set', 'arguments': {'instrument': idx, 'name': nm}})
    ROWS_PER_PAT = 64
    npat = (nrows + ROWS_PER_PAT - 1)//ROWS_PER_PAT
    for pi in range(npat):
        calls.append({'name': 'pattern_clear', 'arguments': {'pattern': pi}})
        calls.append({'name': 'pattern_set_length', 'arguments': {'pattern': pi, 'rows': ROWS_PER_PAT}})
    for (row, ch), f in sorted(s.g.items()):
        pi, r = divmod(row, ROWS_PER_PAT)
        args = {'pattern': pi, 'row': r, 'channel': ch}
        for key, val in (('note', f['note']), ('instrument', f['inst']), ('volume', f['vol']),
                         ('effect', f['eff']), ('effect_param', f['param'])):
            if val is not None:
                args[key] = val
        calls.append({'name': 'pattern_set_cell', 'arguments': args})
    for pos in range(npat):
        calls.append({'name': 'order_set', 'arguments': {'position': pos, 'pattern': pos}})
    calls.append({'name': 'song_set', 'arguments': {'length': npat}})
    json.dump(calls, open('/tmp/build.json','w'))
    print('cells', len(s.g), 'calls', len(calls), 'rows', nrows, 'patterns', npat,
          'bars', len(ARR), 'seconds', round(nrows*(SPEED*60.0/(BPM*24)),2))
    return calls

if __name__ == '__main__':
    main()
