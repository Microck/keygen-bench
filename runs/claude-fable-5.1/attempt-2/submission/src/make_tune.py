"""Compose the keygen tune and write /workspace/submission/tune.xm"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import synth
from xmwrite import Sample, Instrument, write_xm, note_num, note_name, transpose

BPM, SPEED = 140, 6
VOLSCALE = float(os.environ.get('VOLSCALE', '0.57'))
SOLO = [int(x) for x in os.environ['SOLO'].split(',')] if os.environ.get('SOLO') else None
ROWS = 64                   # rows per pattern (4 bars of 4/4, 16th-note rows)
NPAT = 10
TOTAL = ROWS * NPAT
NCH = 16
# channel map
K, SN, HH, BS, ARP, LD, ECHO, PD1, PD2, PD3, HARM, FX, STAB, HI, LD8, ECHO2 = range(16)
# instruments (1-based)
I_KICK, I_SNARE, I_HC, I_HO, I_BASS, I_LEAD, I_P25, I_ARP, I_PAD, I_STAB, I_CRASH, I_RISER, I_BELL, I_P33, I_ARPR = range(1, 16)

# ------------------------------------------------------------------ harmony
PROG = (['Em','C','G','D', 'Em','C','Am','B7'] * 3)[:24] + ['Am','Em','C','G', 'Am','Em','F','B7'] + ['Em','C','G','D', 'Em','C','Am','B7']
assert len(PROG) == 40
CH = {  # bass root, arp base note, arp xy, pad voicing (low, mid, high), chord pitch classes
 'Em': dict(bass='E2', arp='E4', xy=0x37, pad=('E3','B3','G4'), pcs=[4,7,11]),
 'C' : dict(bass='C2', arp='C4', xy=0x47, pad=('E3','C4','G4'), pcs=[0,4,7]),
 'G' : dict(bass='G2', arp='G4', xy=0x47, pad=('D3','B3','G4'), pcs=[7,11,2]),
 'D' : dict(bass='D2', arp='D4', xy=0x47, pad=('D3','A3','F#4'), pcs=[2,6,9]),
 'Am': dict(bass='A2', arp='A3', xy=0x37, pad=('E3','C4','A4'), pcs=[9,0,4]),
 'B7': dict(bass='B2', arp='B3', xy=0x47, pad=('D#3','B3','A4'), pcs=[11,3,6,9]),
 'F' : dict(bass='F2', arp='F4', xy=0x47, pad=('F3','C4','A4'), pcs=[5,9,0]),
}

# ------------------------------------------------------------------ song grid
cells = {}   # (row, ch) -> [note, inst, vol, eff, par]
def put(ch, row, note=None, inst=0, vol=None, eff=0, par=0):
    row %= TOTAL
    n = note_num(note) if isinstance(note, str) else (note or 0)
    v = 0 if vol is None else (0x10 + max(0, min(64, int(round(vol * VOLSCALE)))))
    cells[(row, ch)] = [n, inst, v, eff, par]
def put_off(ch, row):
    row %= TOTAL
    if (row, ch) in cells and cells[(row, ch)][0]:
        return
    cells[(row, ch)] = [97, 0, 0, 0, 0]
def bar_row(bar): return bar * 16

# ------------------------------------------------------------------ drums
def drums_theme(bar, hats16=False, snare_vol=58, ohat=True, ghosts=True):
    r = bar_row(bar)
    for k in (0, 4, 8, 12):
        put(K, r + k, 'C4', I_KICK, 64)
    if bar % 2 == 1:
        put(K, r + 14, 'C4', I_KICK, 52)          # anticipation kick on the 'and' of 4
    for s in (4, 12):
        put(SN, r + s, 'C4', I_SNARE, snare_vol)
    if ghosts:
        put(SN, r + 7, 'C4', I_SNARE, 20)
        put(SN, r + 15, 'C4', I_SNARE, 22)
    for h in range(0, 16, 2):
        if ohat and h in (6, 14):
            put(HH, r + h, 'C4', I_HO, 42)
        else:
            put(HH, r + h, 'C4', I_HC, 50 if h % 4 == 0 else 38)
    if hats16:
        for h in range(1, 16, 2):
            put(HH, r + h, 'C4', I_HC, 24)

def drums_intro(bar, snare=False):
    r = bar_row(bar)
    for k in (0, 4, 8, 12):
        put(K, r + k, 'C4', I_KICK, 64)
    if snare:
        for s in (4, 12):
            put(SN, r + s, 'C4', I_SNARE, 54)
    for h in range(0, 16, 2):
        put(HH, r + h, 'C4', I_HO if h == 14 else I_HC, 42 if h == 14 else (48 if h % 4 == 0 else 34))

def drums_bridge(bar):
    """half-time feel: kick 0 & 10, snare on 8, sparse hats."""
    r = bar_row(bar)
    put(K, r + 0, 'C4', I_KICK, 60)
    put(K, r + 10, 'C4', I_KICK, 52)
    put(SN, r + 8, 'C4', I_SNARE, 56)
    for h in range(0, 16, 4):
        put(HH, r + h, 'C4', I_HC, 38)
    put(HH, r + 14, 'C4', I_HO, 34)

def fill_snare(bar, start=12, vols=(30, 38, 48, 58)):
    r = bar_row(bar)
    for i, v in enumerate(vols):
        put(SN, r + start + i, 'C4', I_SNARE, v)

def fill_toms(bar):
    """snare pitched down = toms: last beat and a half"""
    r = bar_row(bar)
    seq = [(10, 'C4', 50), (11, 'A3', 46), (12, 'G3', 52), (13, 'E3', 48), (14, 'D3', 54), (15, 'C3', 58)]
    for off, n, v in seq:
        put(SN, r + off, n, I_SNARE, v)

def roll_bar(bar):
    """16th snare roll rising over a whole bar + kick 4-on-floor"""
    r = bar_row(bar)
    for i in range(16):
        v = int(22 + (64 - 22) * (i / 15) ** 1.3)
        put(SN, r + i, 'C4', I_SNARE, v)
    for k in (0, 4, 8, 12):
        put(K, r + k, 'C4', I_KICK, 64)
    for h in range(0, 16, 2):
        put(HH, r + h, 'C4', I_HC, 30)

# ------------------------------------------------------------------ bass
def bass_theme(bar, vol=50):
    r = bar_row(bar); root = CH[PROG[bar]]['bass']
    for k in (0, 4, 8, 12):
        put(BS, r + k, root, I_BASS, vol)
    for k in (2, 6, 10, 14):
        put(BS, r + k, transpose(root, 12), I_BASS, vol - 8)

def bass_drive(bar, vol=50):
    r = bar_row(bar); root = CH[PROG[bar]]['bass']
    for k in range(16):
        if k % 4 == 0: put(BS, r + k, root, I_BASS, vol)
        elif k % 2 == 0: put(BS, r + k, transpose(root, 12), I_BASS, vol - 8)
        else: put(BS, r + k, root if k % 4 == 3 else transpose(root, 12), I_BASS, vol - 14)

def bass_bridge(bar, vol=50):
    r = bar_row(bar); root = CH[PROG[bar]]['bass']
    put(BS, r + 0, root, I_BASS, vol)
    put(BS, r + 3, root, I_BASS, vol - 6)
    put(BS, r + 6, transpose(root, 12), I_BASS, vol - 8)
    put(BS, r + 8, root, I_BASS, vol)
    put(BS, r + 11, root, I_BASS, vol - 6)
    put(BS, r + 14, transpose(root, 7), I_BASS, vol - 8)

def bass_walk_end(bar):
    """last bar of a phrase: approach walk in rows 12..15"""
    r = bar_row(bar); root = CH[PROG[bar]]['bass']
    nxt = CH[PROG[(bar + 1) % 40]]['bass']
    put(BS, r + 12, root, I_BASS, 50)
    put(BS, r + 13, transpose(root, 12), I_BASS, 42)
    put(BS, r + 14, transpose(nxt, 2), I_BASS, 46)   # whole step above next root
    put(BS, r + 15, transpose(nxt, 1), I_BASS, 48)   # chromatic approach

# ------------------------------------------------------------------ arp
def arp_bar(bar, vol=36, sixteenths=False, ch=ARP, inst=I_ARP, oct_shift=0):
    r = bar_row(bar); c = CH[PROG[bar]]
    base = transpose(c['arp'], oct_shift)
    if not sixteenths:
        pat = [(0, 0, 0), (2, 0, -6), (4, 12, -2), (6, 0, -6), (8, 0, 0), (10, 12, -2), (12, 0, -6), (14, 12, -2)]
    else:
        pat = [(i, (12 if i % 4 in (2, 3) else 0) + (12 if i in (7, 15) else 0), (0 if i % 4 == 0 else -6)) for i in range(16)]
    for off, tr, dv in pat:
        put(ch, r + off, transpose(base, tr), inst, vol + dv, 0x0, c['xy'])

# ------------------------------------------------------------------ pads
def pad_bar(bar, vol=22):
    r = bar_row(bar); lo, mid, hi = CH[PROG[bar]]['pad']
    put(PD1, r, lo, I_PAD, vol)
    put(PD2, r, mid, I_PAD, vol)
    put(PD3, r, hi, I_PAD, vol)

# ------------------------------------------------------------------ stabs
def stabs_bar(bar, vol=30, rows=(6, 14)):
    r = bar_row(bar); c = CH[PROG[bar]]
    for off in rows:
        put(STAB, r + off, transpose(c['arp'], 12), I_STAB, vol, 0x0, c['xy'])

# ------------------------------------------------------------------ lead
# (row_in_bar, note, duration_rows)
THEME = {
 0: [(0,'E5',3),(3,'G5',3),(6,'F#5',2),(8,'E5',4),(12,'B4',4)],
 1: [(0,'C5',3),(3,'E5',3),(6,'D5',2),(8,'C5',2),(10,'D5',2),(12,'E5',4)],
 2: [(0,'D5',3),(3,'B4',3),(6,'D5',2),(8,'G5',4),(12,'F#5',2),(14,'E5',2)],
 3: [(0,'D5',3),(3,'F#5',3),(6,'A5',2),(8,'F#5',6,0x0A),(14,'E5',1),(15,'D5',1)],
 4: [(0,'E5',3),(3,'G5',3),(6,'F#5',2),(8,'E5',4),(12,'B4',4)],
 5: [(0,'C5',3),(3,'E5',3),(6,'G5',2),(8,'A5',4),(12,'G5',4)],
 6: [(0,'E5',3),(3,'C5',3),(6,'A4',2),(8,'C5',2),(10,'E5',2),(12,'A5',4)],
 7: [(0,'F#5',3),(3,'D#5',3),(6,'B4',2),(8,'D#5',4),(12,'F#5',2),(14,'A5',2)],
}
THEME_B_END = {   # bar 23 variant (into bridge)
 7: [(0,'B5',3),(3,'A5',3),(6,'F#5',2),(8,'D#5',6)],
}
BRIDGE = {
 0: [(0,'A4',2),(2,'C5',2),(4,'E5',4,0x0C),(8,'D5',2),(10,'C5',2),(12,'B4',4)],
 1: [(0,'G4',2),(2,'B4',2),(4,'E5',4,0x0C),(8,'D5',2),(10,'B4',2),(12,'G4',4)],
 2: [(0,'C5',2),(2,'E5',2),(4,'G5',4,0x0C),(8,'E5',2),(10,'D5',2),(12,'C5',4)],
 3: [(0,'B4',3),(3,'D5',3),(6,'G5',2),(8,'F#5',4),(12,'D5',4,0x08)],
 4: [(0,'A4',2),(2,'C5',2),(4,'E5',4,0x0C),(8,'D5',2),(10,'C5',2),(12,'B4',4)],
 5: [(0,'G4',2),(2,'B4',2),(4,'E5',4,0x0C),(8,'F#5',2),(10,'G5',2),(12,'A5',4,0x0A)],
 6: [(0,'A5',3),(3,'F5',3),(6,'C5',2),(8,'F5',4),(12,'A5',4)],
 7: [(0,'A5',3),(3,'F#5',3),(6,'D#5',10,0x06)],
}
FINAL_BAR = [(0,'F#5',2),(2,'D#5',2),(4,'B4',2),(6,'D#5',2),(8,'F#5',2),(10,'A5',2),(12,'B5',4)]

lead_events = []   # (abs_row, note or 'off', vol, portamento_speed)
def lead_phrase(bar, notes, vol=64, cut_tail=True):
    r = bar_row(bar)
    for i, ev in enumerate(notes):
        off, n, d = ev[:3]; porta = ev[3] if len(ev) > 3 else 0
        lead_events.append((r + off, n, vol, porta, bar))
        end = r + off + d
        nxt = notes[i + 1][0] + r if i + 1 < len(notes) else None
        if cut_tail and (nxt is None or end < nxt):
            lead_events.append((end, 'off', 0, 0, bar))

def chord_tone_below(note, pcs, lo=3, hi=8):
    n = note_num(note)
    for d in range(lo, hi + 1):
        if (n - d - 1) % 12 in pcs:
            return note_name(n - d)
    return note_name(n - 7)

def write_lead():
    for row, n, v, p, _ in lead_events:
        if n == 'off': put_off(LD, row)
        else: put(LD, row, n, I_LEAD, v, 0x3 if p else 0, p)

def write_echo(delay=3, ratio=0.42):
    for row, n, v, p, _ in lead_events:
        rr = row + delay
        if n == 'off': put_off(ECHO, rr)
        else: put(ECHO, rr, n, I_P25, int(v * ratio), 0x3 if p else 0, p)
    for row, n, v, p, _ in lead_events:
        rr = row + 2 * delay
        if n == 'off': put_off(ECHO2, rr)
        else: put(ECHO2, rr, n, I_P25, int(v * ratio * 0.5), 0x3 if p else 0, p)

def write_octave_double(bars, vol=26):
    for row, n, v, p, bar in lead_events:
        if bar not in bars: continue
        if n == 'off': put_off(LD8, row)
        else: put(LD8, row, transpose(n, 12), I_P25, vol, 0x3 if p else 0, p)

def write_harmony(bars, vol=40):
    for row, n, v, p, bar in lead_events:
        if bar not in bars: continue
        if n == 'off': put_off(HARM, row); continue
        put(HARM, row, chord_tone_below(n, CH[PROG[bar]]['pcs']), I_P33, vol)

# ------------------------------------------------------------------ arrangement
# P0 (bars 0-3): intro 1
for b in range(0, 4):
    drums_intro(b, snare=False); bass_theme(b); arp_bar(b, vol=40); stabs_bar(b, vol=26)
put(FX, 0, 'C4', I_CRASH, 40)
for c in (PD1, PD2, PD3): put_off(c, 0)      # pads from the loop tail fade out here
fill_snare(3, start=14, vols=(36, 48))
# P1 (bars 4-7): intro 2
for b in range(4, 8):
    drums_intro(b, snare=True); bass_theme(b); arp_bar(b, vol=40); pad_bar(b, vol=20); stabs_bar(b, vol=26)
bass_walk_end(7)
fill_toms(7)
lead_phrase(7, [(12,'B4',1),(13,'C5',1),(14,'D5',1),(15,'D#5',1)], vol=54)   # pickup into the theme
put(FX, bar_row(7), 'C4', I_RISER, 34)
# bell motif in intro 2 (channel HI): chord tones, sparse
put_off(ARP, bar_row(24))          # arp silent in bridge 1
put_off(HI, bar_row(28))           # (bells are one-shot; safety)
BELL_MOTIF = {0: [(0,'B5'),(6,'G5'),(12,'E5')], 1: [(0,'G5'),(6,'E5'),(12,'C5')], 2: [(0,'D5'),(6,'B4'),(12,'G5')], 3: [(0,'A5'),(6,'F#5'),(12,'D5')],
              4: [(0,'B5'),(6,'G5'),(12,'E5')], 5: [(0,'G5'),(6,'E5'),(12,'C5')], 6: [(0,'E5'),(6,'C5'),(10,'A5'),(12,'E5')], 7: [(0,'F#5'),(6,'D#5'),(12,'B5')]}
for b, ev in BELL_MOTIF.items():
    for off, n in ev:
        put(HI, bar_row(b) + off, n, I_BELL, 32)
# P2-P3 (bars 8-15): theme 1
put(FX, bar_row(8), 'C4', I_CRASH, 44)
for b in range(8, 16):
    drums_theme(b); bass_theme(b); arp_bar(b, vol=42); pad_bar(b, vol=18); stabs_bar(b, vol=28)
    lead_phrase(b, THEME[b - 8])
fill_snare(11, start=14, vols=(40, 52)); fill_snare(15); bass_walk_end(15)
RUN_D = ['D6','A5','F#5','D5','A4','D5','F#5','A5']
def run(bar, notes, start=8, vol=30, inst=I_P25):
    r = bar_row(bar)
    for i, n in enumerate(notes):
        put(HI, r + start + i, n, inst, vol)
    put_off(HI, r + start + len(notes))
run(11, RUN_D); run(19, RUN_D)
run(15, ['B5','F#5','D#5','B4','F#4','B4','D#5','F#5'], start=8)
# P4-P5 (bars 16-23): theme 2 with harmony
for b in range(16, 24):
    drums_theme(b, hats16=(b >= 20)); bass_theme(b); arp_bar(b, vol=42); pad_bar(b, vol=18)
    lead_phrase(b, THEME_B_END[7] if b == 23 else THEME[b - 16])
fill_snare(19, start=14, vols=(40, 52)); fill_toms(23)
put(FX, bar_row(23), 'C4', I_RISER, 26)
put(FX, bar_row(24), 'C4', I_CRASH, 26)
# P6 (bars 24-27): bridge 1 (half-time, pads up front, bell)
for b in range(24, 28):
    drums_bridge(b); bass_bridge(b); pad_bar(b, vol=32)
    lead_phrase(b, BRIDGE[b - 24], vol=58)
BELL_BRIDGE = {24: [(4,'E6'),(12,'B5')], 25: [(4,'E6'),(12,'G5')], 26: [(4,'G6'),(12,'C6')], 27: [(6,'G6'),(8,'F#6')]}
for b, ev in BELL_BRIDGE.items():
    for off, n in ev:
        put(HI, bar_row(b) + off, n, I_BELL, 28)
fill_snare(27, start=12, vols=(28, 36, 46, 56))
# P7 (bars 28-31): bridge 2 (drive returns, build-up)
for b in range(28, 32):
    if b < 31:
        drums_theme(b, hats16=(b == 30), ohat=True); bass_theme(b); arp_bar(b, vol=38, sixteenths=(b == 30))
    else:
        roll_bar(b); bass_theme(b); arp_bar(b, vol=42, sixteenths=True)
    pad_bar(b, vol=26)
    lead_phrase(b, BRIDGE[b - 24], vol=60)
put(FX, bar_row(31), 'C4', I_RISER, 40)
# P8-P9 (bars 32-39): theme 3, full
put(FX, bar_row(32), 'C4', I_CRASH, 46)
for b in range(32, 40):
    drums_theme(b, hats16=True); bass_drive(b); arp_bar(b, vol=42); pad_bar(b, vol=20); stabs_bar(b, vol=26, rows=(6,))
    arp_bar(b, vol=24, sixteenths=True, ch=HI, inst=I_ARPR, oct_shift=12)
    lead_phrase(b, FINAL_BAR if b == 39 else THEME[b - 32])
fill_snare(35, start=14, vols=(40, 52)); fill_snare(39, start=12, vols=(34, 44, 54, 62)); bass_walk_end(39)

def extend_portamento():
    """3xx only slides on rows where it is present: add 300 continuation cells until the target is reached."""
    for ch in (LD, ECHO, ECHO2, LD8):
        rows = sorted(r for (r, c) in cells if c == ch)
        for idx, r in enumerate(rows):
            n, ins, v, eff, par = cells[(r, ch)]
            if eff != 3 or par == 0 or n == 0 or n == 97: continue
            prev = next((cells[(rows[j], ch)][0] for j in range(idx - 1, -1, -1) if cells[(rows[j], ch)][0] not in (0, 97)), None)
            if prev is None: continue
            dist = abs(n - prev) * 64                  # linear period units
            ticks = int(np.ceil(dist / (par * 4)))
            nrows = int(np.ceil(ticks / 5))
            for k in range(1, nrows):
                rr = (r + k) % TOTAL
                if (rr, ch) not in cells or not any(cells[(rr, ch)]):
                    cells[(rr, ch)] = [0, 0, 0, 3, 0]
                else:
                    break

write_lead(); write_echo(); write_harmony(list(range(16, 24)) + list(range(32, 40))); write_octave_double(list(range(32, 40))); extend_portamento()

# ------------------------------------------------------------------ instruments
def S(gen, **kw):
    d, ls, ll = gen
    lt = kw.pop('loop_type', 1 if ll else 0)
    return Sample(d, loop_start=ls, loop_len=ll, loop_type=lt, relnote=24, **kw)
def D(data, **kw):
    return Sample(data, relnote=24, **kw)

instruments = [
 Instrument('kick',   [D(synth.kick(), name='kick', panning=128)]),
 Instrument('snare',  [D(synth.snare(), name='snare', panning=128)]),
 Instrument('hat cl', [D(synth.hat_closed(), name='hhc', panning=150)]),
 Instrument('hat op', [D(synth.hat_open(), name='hho', panning=150)]),
 Instrument('bass',   [S(synth.bass_sample(), name='bass', panning=128)],
            vol_env=[(0,64),(2,64),(14,48),(60,48)], vol_sustain=3, fadeout=3000),
 Instrument('lead pwm',[S(synth.pwm_lead(), name='pwm', panning=128)],
            vol_env=[(0,54),(1,64),(10,52),(60,52)], vol_sustain=3, fadeout=2200, vibrato=(0, 30, 9, 26)),
 Instrument('echo p25',[S(synth.pulse_wave(0.25), name='pulse25', panning=190)],
            vol_env=[(0,64),(60,64)], vol_sustain=1, fadeout=2600),
 Instrument('arp p12',[S(synth.arp_pulse(), name='pulse12', panning=80)],
            vol_env=[(0,64),(3,40),(60,40)], vol_sustain=2, fadeout=4000),
 Instrument('pad',    [S(synth.pad_sample(), name='pad3saw', panning=128)],
            vol_env=[(0,0),(7,60),(40,52),(100,52)], vol_sustain=3, fadeout=900),
 Instrument('stab',   [S(synth.stab_sample(), name='stab', panning=100, loop_type=0)]),
 Instrument('crash',  [D(synth.crash(), name='crash', panning=128)]),
 Instrument('riser',  [D(synth.riser(), name='riser', panning=128)]),
 Instrument('bell',   [Sample(synth.bell_sample()[0], name='bell', panning=170, relnote=0)]),
 Instrument('harm p33',[S(synth.pulse_wave(0.33), name='pulse33', panning=70)],
            vol_env=[(0,64),(60,64)], vol_sustain=1, fadeout=2600),
 Instrument('arp p18 R',[S(synth.arp_pulse(), name='pulse18r', panning=176)],
            vol_env=[(0,64),(3,40),(60,40)], vol_sustain=2, fadeout=4000),
]
# pad channels get stereo spread via pattern panning? use per-channel 8xx on first pad notes instead
for b in range(40):
    r = bar_row(b)
    for c, pan in ((PD1, 0x60), (PD3, 0xA0)):
        if (r, c) in cells and cells[(r, c)][1]:
            cells[(r, c)][3] = 0x8; cells[(r, c)][4] = pan

# ------------------------------------------------------------------ write
patterns = []
for p in range(NPAT):
    pc = {}
    for (row, ch), v in cells.items():
        if SOLO is not None and ch not in SOLO: continue
        if row // ROWS == p:
            pc[(row % ROWS, ch)] = tuple(v)
    patterns.append((ROWS, pc))
order = list(range(NPAT)) * (2 if os.environ.get('TWICE') else 1)
out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/submission/tune.xm'
n = write_xm(out, 'unlocked', NCH, patterns, order, 0, SPEED, BPM, instruments)
print('wrote', out, n, 'bytes;', len(cells), 'cells')
