"""Keygen tune composer: writes a standard XM using xmwrite."""
import sys
import numpy as np
sys.path.insert(0, '/workspace/build')
import xmwrite as X
import samples_lib as S
from dsp import SR, q8

# ---- note helpers -------------------------------------------------------
# ft2-clone renders note index n at frequency 261.63*2**((n-32)/12).
# Traditional names: 'C4'..'B6'.  Our writer indices: 'C-0'=1.
def t(name):
    """traditional note name (C4) -> tracker note name for this build"""
    key = name[:-1].upper(); octv = int(name[-1])
    semi = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}[key]
    trad_idx = octv * 12 + semi + 1     # C4 -> 49
    return X.i2n(trad_idx - 24)          # shift so C4 -> index 32

def freq(name):
    """traditional note name -> Hz (as rendered by this build)"""
    key = name[:-1].upper(); octv = int(name[-1])
    semi = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}[key]
    n = X.n2i(t(name))
    return 261.626 * 2 ** ((n - 32) / 12.0)

# musical constants
BPM = 150
SPEED = 4
ROWS_PER_BAR = 16
BAR = ROWS_PER_BAR
NCH = 12

# ---------------------------------------------------------------- samples
BASS_REF = freq('A2') / 2.0      # bass sample designed so 'A2' tab sounds an octave below? -> see use
LEAD_REF = freq('C5')
ARP_REF = freq('C5')
STAB_REF = freq('C4')
PAD_REF = freq('C4')

SAMPLES = {}   # instrument index -> dict
def add_sample(idx, name, pcm, loop_start, loop_len, volume, panning, loop, rel=0):
    SAMPLES[idx] = dict(name=name, pcm=pcm, ls=loop_start, ll=loop_len,
                        vol=volume, pan=panning, loop=loop, rel=rel)

lead_pcm = q8(S.make_lead(LEAD_REF, cycles=48, cents=(-19,-9,0,8,19)))
bass_pcm = q8(S.make_bass(freq('A1'), cycles=24, duty=0.5))
arp_pcm  = q8(S.make_arp(ARP_REF, cycles=24, duty=0.28))
sub_pcm  = q8(S.make_bass(freq('A0'), cycles=16, duty=0.5, sub=True, clickspan=400))
stab_pcm = q8(S.make_stab(STAB_REF, dur=0.40, intervals=(0, 7, 12, 19)))
pad_pcm  = q8(S.make_pad(PAD_REF, dur=1.7, intervals=(0, 3, 7, 12)))
pad2_pcm = q8(S.make_pad(PAD_REF, dur=1.7, intervals=(0, 7, 16, 19)))
kick_pcm = q8(S.kick())
snare_pcm = q8(S.snare())
hatc_pcm = q8(S.hat(0.05))
hato_pcm = q8(S.hat(0.26, (6500, 12000)))
crash_pcm = q8(S.crash())
riser_pcm = q8(S.riser())

add_sample(1,  'LEAD',      lead_pcm, 1400, len(lead_pcm)-1400, 42, 12, True)
add_sample(2,  'LEAD2',     lead_pcm, 1400, len(lead_pcm)-1400, 34, 52, True)
add_sample(3,  'ARP',       arp_pcm, 700, len(arp_pcm)-700, 30, 40, True)
add_sample(4,  'BASS',      bass_pcm, 900, len(bass_pcm)-900, 48, 4, True)
add_sample(5,  'SUBBASS',   sub_pcm, 600, len(sub_pcm)-600, 44, 60, True)
add_sample(6,  'STAB',      stab_pcm, 0, 0, 44, 64, False)
add_sample(7,  'PAD',       pad_pcm, 0, 0, 40, 24, False)
add_sample(8,  'PAD2',      pad2_pcm, 0, 0, 36, 40, False)
add_sample(9,  'KICK',      kick_pcm, 0, 0, 58, 32, False)
add_sample(10, 'SNARE',     snare_pcm, 0, 0, 54, 32, False)
add_sample(11, 'HATC',      hatc_pcm, 0, 0, 44, 56, False)
add_sample(12, 'HATO',      hato_pcm, 0, 0, 40, 48, False)
add_sample(13, 'CRASH',     crash_pcm, 0, 0, 42, 32, False)
add_sample(14, 'RISER',     riser_pcm, 0, 0, 34, 20, False)

# ---------------------------------------------------------------- grid tools
def R(row, note, inst, vol=None, eff=0, ep=0):
    """row event"""
    n = X.n2i(t(note)) if isinstance(note, str) else note
    return dict(row=row, note=n, inst=inst, vol=vol, eff=eff, ep=ep)

def place(chan, rows, events):
    """events: list of (startrow, dur, note, vol, eff, ep)"""
    for ev in rows:
        r, dur, note, vol, eff, ep = ev
        if note is not None:
            chan[r] = dict(row=r, note=X.n2i(t(note)) if isinstance(note, str) else note,
                           inst=None, vol=vol, eff=eff, ep=ep)

def cell(note, inst, vol=None, eff=0, ep=0):
    n = X.n2i(t(note)) if isinstance(note, str) else note
    return (n, inst, vol or 0, eff, ep)

def put(pat, ch, row, note, inst, vol=None, eff=0, ep=0):
    pat.setdefault((ch, row), None)
    pat[(ch, row)] = cell(note, inst, vol, eff, ep)

def blank_rows(n):
    return [[None] * NCH for _ in range(n)]

def seq(notes, start=0, step=1):
    """notes: list with None allowed -> events (row, dur, note)"""
    ev = []
    r = start
    for n in notes:
        if n is not None:
            ev.append((r, step, n, None, 0, 0))
        r += step
    return ev

def arp_seq(chord, start, step, cycles=2, oct=12):
    """16th arpeggio through chord tones"""
    tones = list(chord)
    if oct:
        tones = tones + [c + oct for c in chord[:1]]
    ev = []
    r = start
    total = ROWS_PER_BAR * cycles
    i = 0
    while r < start + total:
        n = tones[i % len(tones)]
        ev.append((r, step, n, None, 0, 0))
        i += 1
        r += step
    return ev

# ---------------------------------------------------------------- instrument build
def build_module():
    m = X.XM('KEYGEN DREAM', NCH, tempo=SPEED, bpm=BPM, linear=True)
    for idx in sorted(SAMPLES):
        s = SAMPLES[idx]
        m.add_instrument(s['name'], s['pcm'][0], loop_start=s['ls'], loop_len=s['ll'],
                         volume=s['vol'], panning=s['pan'], loop=s['loop'], extra_flags=0)
    return m

# chord tables (traditional note names, root position wanted)
CHORDS = {
    'Am': ['A2', 'C3', 'E3'],
    'F':  ['F2', 'A2', 'C3'],
    'C':  ['C3', 'E3', 'G3'],
    'G':  ['G2', 'B2', 'D3'],
    'Dm': ['D3', 'F3', 'A3'],
    'E':  ['E2', 'G#2', 'B2'],
    'Em': ['E2', 'G2', 'B2'],
}
ROOTS = {'Am':'A2','F':'F2','C':'C3','G':'G2','Dm':'D3','E':'E2'}

BASS_PAT = [0, 3, 6, 8, 11, 14]

def bass_line(root, pat=BASS_PAT, var=0):
    """groovy 8th bassline around the root"""
    r = ROOTS[root]
    def s(n): return n
    seq = {0: r, 3: r, 6: transpose(r, 7), 8: r, 11: r, 14: transpose(r, 12)}
    if var == 1:
        seq = {0: r, 2: transpose(r,12), 4: r, 6: transpose(r,7), 8: r, 10: transpose(r,12), 12: r, 14: transpose(r,5)}
    if var == 2:
        seq = {0: r, 4: transpose(r,12), 6: r, 8: r, 12: transpose(r,12), 14: transpose(r,7)}
    if var == 3:
        seq = {0: r, 2: transpose(r,12), 4: transpose(r,12), 6: r, 8: r, 11: transpose(r,7), 14: transpose(r,12)}
    return seq

def transpose(note, semis):
    key = note[:-1].upper(); octv = int(note[-1])
    semi = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}[key]
    i = octv*12 + semi + semis
    names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    return '%s%d' % (names[i % 12], i // 12)

def drum_bar(bar, pat, style):
    """style: 'intro','main','break'"""
    r = pat
    k, sn, hc, ho = [], [], [], []
    if style == 'intro':
        k = [0, 8]
        sn = [4, 12]
        hc = [2, 6, 10, 14]
    elif style == 'main':
        k = [0, 4, 8, 12]
        if bar % 2 == 0:
            k += [6, 14]
        sn = [4, 12, 11]
        hc = [0, 2, 4, 6, 8, 10, 12, 14]
        ho = [14]
    elif style == 'drive':
        k = [0, 3, 4, 8, 11, 12]
        sn = [4, 12, 11]
        hc = [0, 2, 4, 6, 8, 10, 12, 14]
        ho = [14]
    elif style == 'break':
        k = [0]
        sn = [12]
        hc = [4, 8, 12]
    elif style == 'pads':
        hc = [6]
    return k, sn, hc, ho
