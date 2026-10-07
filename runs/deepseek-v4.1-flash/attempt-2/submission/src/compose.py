# -*- coding: utf-8 -*-
"""Compose the keygen tune: builds FT2 batch calls for samples + patterns."""
import json, sys, re
sys.path.insert(0, '/workspace/work')
from mkmod import write_batch

BPM = 140
SPEED = 6
NCH = 8
ROWS = 64
BAR = 16

# ---------------- note helpers ----------------
BASE = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def N(s):
    m = re.match(r'^([A-G])(#?)-?(\d+)$', s)
    assert m, s
    semi = BASE[m.group(1)] + (1 if m.group(2) else 0)
    octv = int(m.group(3))
    return 1 + 12*(octv+1) + semi - 12   # C-0 == 1
def Nn(s, d):  # transpose by d semitones
    v = N(s)+d
    return v

CHORDS = {
 'Am': ['A-3','C-4','E-4','A-4'],
 'F' : ['F-3','A-3','C-4','F-4'],
 'C' : ['C-4','E-4','G-4','C-5'],
 'G' : ['G-3','B-3','D-4','G-4'],
 'Dm': ['D-4','F-4','A-4','D-5'],
 'E7': ['E-3','G#3','B-3','E-4'],
 'Bb': ['A#3','D-4','F-4','A#4'],
}
BASS_ROOT = {'Am':'A-1','F':'F-1','C':'C-2','G':'G-1','Dm':'D-2','E7':'E-2','Bb':'A#1'}
PAD_ROOT  = {'Am':'A-3','F':'F-3','C':'C-4','G':'G-3','Dm':'D-4','E7':'E-3','Bb':'A#3'}
PAD_5TH   = {'Am':'E-3','F':'C-4','C':'G-3','G':'D-4','Dm':'A-3','E7':'B-3','Bb':'F-4'}

INST = dict(bass=1, lead=2, arp=3, pad=4, kick=5, snare=6, hat=7, ohat=8, crash=9, pluck=10)

class Pat:
    def __init__(self, idx, nrows=ROWS):
        self.idx = idx
        self.nrows = nrows
        self.cells = {}   # (row,ch) -> dict
    def put(self, row, ch, note=None, inst=None, vol=None, eff=None, par=None):
        if note is None and inst is None and vol is None and eff is None:
            return
        c = self.cells.setdefault((row, ch), {})
        if note is not None: c['note'] = note
        if inst is not None: c['instrument'] = inst
        if vol is not None: c['volume'] = vol
        if eff is not None: c['effect'] = eff
        if par is not None: c['effect_param'] = par
    def note(self, row, ch, name, inst, vol=None, eff=None, par=None):
        self.put(row, ch, note=N(name), inst=inst, vol=vol, eff=eff, par=par)

def add_bass(p, bar, chord, style, root_oct=0):
    r = N(BASS_ROOT[chord]) + 12*root_oct
    if style == 'sparse':      # half notes
        seq = [(0,0),(6,0),(8,0),(12,7)]
    elif style == 'drive':     # 8ths
        seq = [(0,0),(2,0),(4,12),(6,0),(8,7),(10,0),(12,12),(14,7)]
    elif style == 'drive2':
        seq = [(0,0),(2,12),(4,0),(6,7),(8,0),(10,12),(12,7),(14,12)]
    elif style == 'gallop':    # 16ths
        seq = [(0,0),(1,0),(2,12),(3,0),(4,7),(5,0),(6,12),(7,7),
               (8,0),(9,0),(10,12),(11,0),(12,7),(13,12),(14,7),(15,0)]
    elif style == 'push':      # syncopated
        seq = [(0,0),(3,0),(4,12),(6,0),(8,0),(11,0),(12,7),(14,12)]
    for (ro, off) in seq:
        p.note(bar*BAR+ro, 1, note_name(r+off), INST['bass'])

NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def note_name(v):
    v = int(v)
    o = (v-1)//12
    return NAMES[(v-1)%12] + str(o)

def add_arp(p, bar, chord, style='flow', vol=None):
    tones = [N(x) for x in CHORDS[chord]]
    tones = tones + [tones[0]+12]
    if style == 'flow':
        fig = [0,1,2,3,2,1,0,1,2,3,4,3,2,1,2,3]
    elif style == 'up':
        fig = [0,1,2,3,4,3,2,1,0,1,2,3,4,3,2,1]
    elif style == 'stab':
        fig = [0,None,1,None,2,None,1,None,0,None,1,None,2,None,3,None]
    elif style == 'sparkle':
        fig = [4,3,2,3,4,3,2,3,4,3,2,3,4,3,2,3]
    for i,f in enumerate(fig):
        if f is None: continue
        p.note(bar*BAR+i, 2, note_name(tones[f]), INST['arp'], vol=vol)

def add_pad(p, bar, chord, vol=None, inst=None):
    inst = inst or INST['pad']
    p.note(bar*BAR, 3, PAD_ROOT[chord], inst, vol=vol)

def add_drums(p, bar, spec):
    k = spec.get('k', [])
    for ro in k:
        p.note(bar*BAR+ro, 4, 'C-4', INST['kick'], vol=spec.get('kv'))
    for ro in spec.get('s', []):
        p.note(bar*BAR+ro, 5, 'C-4', INST['snare'], vol=spec.get('sv'))
    for ro in spec.get('s2', []):
        p.note(bar*BAR+ro, 5, 'C-4', INST['snare'], vol=spec.get('s2v', 29))  # VC: channel vol 13
    for ro in spec.get('h', []):
        p.note(bar*BAR+ro, 6, 'C-4', INST['hat'], vol=spec.get('hv'))
    for ro in spec.get('o', []):
        p.note(bar*BAR+ro, 6, 'C-4', INST['ohat'], vol=spec.get('ov'))
    if 'crash' in spec:
        p.note(bar*BAR+spec['crash'], 6, 'C-4', INST['crash'], vol=spec.get('cv'))
