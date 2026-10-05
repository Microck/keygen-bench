# -*- coding: utf-8 -*-
"""CRYSTAL KEYGEN - original keygen tune composed as an XM module.

Engine facts (verified experimentally):
  * samples are stored at an implicit rate of 8363 Hz for note C-4 with relative_note 0
    -> pr(note) = 8363 * 2**((note + rel - 49)/12)
  * content designed at 16726 Hz + relative_note 12 => note names are standard (C-4 = 261.63 Hz)
  * sample flags need bit 4 (16) set for 16-bit data; +1 = forward loop
  * effect 14 / 0xCx = note cut, effect 15 = Fxx (speed/tempo)
"""
import numpy as np, base64, json, sys, os

# ------------------------------------------------------------------ helpers
def pcm(x):
    x = np.clip(x, -1.0, 1.0)
    return base64.b64encode((x * 32767.0).astype('<i2').tobytes()).decode()

def norm(x, peak=0.9):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x

def onepole(x, a):
    y = np.empty_like(x); p = 0.0
    for i, v in enumerate(x):
        p = a * (p + v) - a * p
        y[i] = p
    return y

def lp(x, sr, fc):
    a = np.exp(-2*np.pi*fc/sr); y = np.empty_like(x); p = 0.0
    for i, v in enumerate(x):
        p = b_ = (1-a)*v + a*p
        y[i] = p
    return y

def hp(x, sr, fc):
    a = np.exp(-2*np.pi*fc/sr)
    y = np.empty_like(x); px = 0.0; py = 0.0
    b = (1+a)/2; b1 = -(1+a)/2
    for i, v in enumerate(x):
        py = b*v + b1*px + a*py
        px = v; y[i] = py
    return y

def bp(x, sr, lo, hi):
    return lp(hp(x, sr, lo), sr, hi)

SR = 16726          # design rate for every sample
REL = 12            # relative note -> note names are standard

# ------------------------------------------------------------------ sounds
SAMPLES = []
def add_inst(idx, name, data, loop=None, pan=128, vol=64):
    SAMPLES.append(dict(inst=idx, name=name, data=data, loop=loop, pan=pan, vol=vol))

def saw_cycle(nharm, N=64, extra_sub=0.0):
    n = np.arange(N); w = np.zeros(N)
    for k in range(1, nharm+1):
        w += np.sin(2*np.pi*k*n/N)/k
    if extra_sub: w += extra_sub*np.sin(2*np.pi*n/N)
    return w

def mk_kick():
    n = int(SR*0.40); t = np.arange(n)/SR
    f = 45 + 100*np.exp(-t/0.028)
    body = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/0.095)
    body += np.sin(2*np.pi*np.cumsum((45+100*np.exp(-t/0.028))*1.0)/SR)*0.0
    click = lp(np.random.RandomState(1).randn(n), SR, 7000)*np.exp(-t/0.003)*0.6
    i = int(0.004*SR)
    body[:i] += 0.3*np.sin(2*np.pi*800*t[:i])*np.exp(-t[:i]/0.0015)
    return norm(body+click, 0.95)

def mk_snare():
    n = int(SR*0.30); t = np.arange(n)/SR
    rs = np.random.RandomState(2)
    noise = bp(rs.randn(n), SR, 1100, 9500)*np.exp(-t/0.072)
    body = np.sin(2*np.pi*186*t)*np.exp(-t/0.045) + 0.4*np.sin(2*np.pi*331*t)*np.exp(-t/0.030)
    return norm(0.85*noise+0.5*body, 0.85)

def mk_clap():
    n = int(SR*0.36); t = np.arange(n)/SR
    rs = np.random.RandomState(3)
    noise = bp(rs.randn(n), SR, 900, 9000)
    out = np.zeros(n)
    for k, off in enumerate([0.0, 0.009, 0.018]):
        i0 = int(off*SR); env = np.zeros(n); env[i0:] = np.exp(-t[:n-i0]/0.011)
        out += noise*env*0.55
    i0 = int(0.027*SR); env = np.zeros(n); env[i0:] = np.exp(-t[:n-i0]/0.095)
    out += noise*env
    return norm(out, 0.8)

def mk_hat():
    n = int(SR*0.07); t = np.arange(n)/SR
    rs = np.random.RandomState(4)
    x = hp(rs.randn(n), SR, 6000)*np.exp(-t/0.012)
    x += hp(rs.randn(n), SR, 9500)*np.exp(-t/0.007)*0.7
    return norm(x, 0.75)

def mk_ohat():
    n = int(SR*0.34); t = np.arange(n)/SR
    rs = np.random.RandomState(5)
    return norm(hp(rs.randn(n), SR, 5000)*np.exp(-t/0.080), 0.7)

def mk_crash():
    n = int(SR*1.7); t = np.arange(n)/SR
    rs = np.random.RandomState(6)
    x = bp(rs.randn(n), SR, 2600, 8200)*np.exp(-t/0.42)
    x += bp(rs.randn(n), SR, 700, 3000)*np.exp(-t/0.25)*0.35
    return norm(x, 0.7)

def mk_bass():
    w = saw_cycle(24, 64, extra_sub=0.55)
    w += 0.25*np.sin(2*np.pi*2*np.arange(64)/64)
    return norm(w, 0.85)

def mk_arp():
    n = int(SR*0.30); t = np.arange(n)/SR; f0 = 261.6256
    out = np.zeros(n)
    for k in range(1, 17):
        tau = 0.010 + 0.09/k**1.2
        out += (1.0/k**0.7)*np.sin(2*np.pi*f0*k*t + 0.31*k)*np.exp(-t/tau)
    return norm(out, 0.85)

def mk_pluck():
    n = int(SR*0.55); t = np.arange(n)/SR; f0 = 261.6256
    out = np.zeros(n)
    for k in range(1, 11):
        out += (1.0/k**1.1)*np.sin(2*np.pi*f0*k*t)*np.exp(-t/(0.03+0.25/k))
    return norm(out, 0.8)

def mk_pad():
    t = np.arange(SR)/SR; out = np.zeros(SR)
    for h in range(1, 9):
        a = 1.0/h**1.35
        out += a*np.sin(2*np.pi*(262*h)*t) + 0.75*a*np.sin(2*np.pi*(264*h)*t + 0.5)
    return norm(out, 0.8)

def mk_lead(base1, base2, nharm=12, curve=0.9, vib=0.004, vibhz=2.0):
    n = SR//2
    t = np.arange(n)/SR
    # vibrato with a period that divides the loop length -> stays click free
    ph1 = 2*np.pi*base1*(t + vib/(2*np.pi*vibhz)*np.sin(2*np.pi*vibhz*t))
    ph2 = 2*np.pi*base2*(t + vib/(2*np.pi*vibhz)*np.sin(2*np.pi*vibhz*t) + 0.9/(2*np.pi*base2))
    out = np.zeros(n)
    for h in range(1, nharm+1):
        a = 1.0/h**curve
        out += a*np.sin(h*ph1) + 0.8*a*np.sin(h*ph2)
    return norm(out, 0.85)

def mk_chip(duty=0.25):
    N = 64; n = np.arange(N); out = np.zeros(N)
    for k in range(1, 17):
        out += (2.0/(k*np.pi))*np.sin(np.pi*k*duty)*np.sin(2*np.pi*k*n/N)
    return norm(out, 0.8)

def mk_riser():
    n = int(SR*1.9); t = np.arange(n)/SR
    rs = np.random.RandomState(7)
    noise = bp(rs.randn(n), SR, 1200, 8300)
    env = (t/t[-1])**2.4
    sweep = np.sin(2*np.pi*np.cumsum(160*np.exp(t/t[-1]*2.4))/SR)*0.30*(t/t[-1])**2
    return norm(noise*env*0.8 + sweep, 0.7)

add_inst(1,  "KICK",    mk_kick(),   pan=128, vol=64)
add_inst(2,  "SNARE",   mk_snare(),  pan=128, vol=64)
add_inst(3,  "CLAP",    mk_clap(),   pan=118, vol=64)
add_inst(4,  "HIHAT",   mk_hat(),    pan=162, vol=64)
add_inst(5,  "OPENHAT", mk_ohat(),   pan=95,  vol=64)
add_inst(6,  "CRASH",   mk_crash(),  pan=128, vol=50)
add_inst(7,  "BASS",    mk_bass(),   loop=(0, 64), pan=128, vol=64)
add_inst(8,  "ARP",     mk_arp(),    pan=205, vol=64)
add_inst(9,  "PLUCK",   mk_pluck(),  pan=52,  vol=64)
add_inst(10, "PAD",     mk_pad(),    loop=(0, SR), pan=128, vol=64)
add_inst(11, "LEAD",    mk_lead(260, 262), loop=(0, SR//2), pan=86, vol=64)
add_inst(12, "LEAD2",   mk_lead(257, 260), loop=(0, SR//2), pan=172, vol=64)
add_inst(13, "CHIP",    mk_chip(),   loop=(0, 64), pan=128, vol=64)
add_inst(14, "RISER",   mk_riser(),  pan=128, vol=64)

# ------------------------------------------------------------------ song
NC = 18
NPAT = 8
CH_LEAD, CH_LEAD2, CH_BASS, CH_ARP, CH_P1, CH_P2, CH_P3 = 0,1,2,3,4,5,6
CH_KICK, CH_SNARE, CH_CLAP, CH_HAT, CH_OHAT, CH_CHIP, CH_CRASH, CH_RISER, CH_PLUCK, CH_ECHO = 7,8,9,10,11,12,13,14,15,5
CH2INST = {0:11,1:12,2:7,3:8,4:10,5:10,6:10,7:1,8:2,9:3,10:4,11:5,12:13,13:6,14:14,15:9,16:11}
CH_ECHO = 16
cells = {}
def put(pat, row, ch, **kw):
    if kw.get('instrument') is None: kw['instrument'] = CH2INST[ch]
    cells[(pat,row,ch)] = kw

def putline(pat, ch, events, vol=48, cut=None):
    """events: (row, note, dur_rows)"""
    for (r, note, dur) in events:
        put(pat, r, ch, note=note, volume=vol)
        if cut == 'hard' and dur > 1:
            put(pat, r+dur-1, ch, effect=14, effect_param=0xC0)

NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def shift(note, semis):
    letter, octv = note[:2], int(note[-1])
    i = NAMES.index(letter) + octv*12 + semis
    return f"{NAMES[i%12]}{i//12}"

NOTE_DOWN = {'C-':('B-',-1),'C#':('C-',0),'D-':('C#',0),'D#':('D-',0),'E-':('D#',0),
             'F-':('E-',0),'F#':('F-',0),'G-':('F#',0),'G#':('G-',0),'A-':('G#',0),
             'A#':('A-',0),'B-':('A#',0)}
def down12(events):
    out = []
    for (r, note, dur) in events:
        letter, octv = note[:2], int(note[-1])
        nl, adj = NOTE_DOWN[letter]
        no = octv-1 if adj == -1 else octv
        out.append((r, f"{nl}{no}", dur))
    return out

CH_ = {
 'Em': (["E-3","G-3","B-3"], ["E-3","G-3","B-3","E-4"], "E-2"),
 'C':  (["C-3","E-3","G-3"], ["C-3","E-3","G-3","C-4"], "C-2"),
 'G':  (["G-3","B-3","D-4"], ["G-3","B-3","D-4","G-4"], "G-2"),
 'D':  (["D-3","F#3","A-3"], ["D-3","F#3","A-3","D-4"], "D-2"),
 'B7': (["B-2","D#3","F#3"], ["B-2","D#3","F#3","A-3"], "B-1"),
}
PROG = ['Em','C','G','D']
PROG_END = ['Em','C','G','B7']

def add_pad(pat, prog, vol=30):
    for bar in range(4):
        triad = CH_[prog[bar]][0]; r = bar*16
        for i, cn in enumerate([CH_P1, CH_P2, CH_P3]):
            put(pat, r, cn, note=triad[i], volume=vol - i*2)

def add_arp(pat, prog, vol=32, every=1, oct_up_last=False, bars=(0,1,2,3)):
    for bar in range(4):
        if bar not in bars: continue
        tones = CH_[prog[bar]][1]; r0 = bar*16
        for rr in range(0, 16, every):
            k = rr//every
            idx = k % 4 if bar % 2 == 0 else 3-(k % 4)
            note = tones[idx]
            if oct_up_last and k == 3: note = shift(note, 12)
            put(pat, r0+rr, CH_ARP, note=note, volume=min(63, vol + (4 if rr % 4 == 0 else 0)))

BASS_STEPS = [(0,0),(2,0),(4,12),(6,0),(8,0),(10,0),(12,12),(14,0)]
def add_bass(pat, prog, vol=36, extra16=False):
    for bar in range(4):
        root = CH_[prog[bar]][2]; r0 = bar*16
        for (rr, off) in BASS_STEPS:
            put(pat, r0+rr, CH_BASS, note=shift(root, off), volume=vol)
            if extra16 and rr in (6, 14):
                put(pat, r0+rr+1, CH_BASS, note=shift(root, 12), volume=vol-18)

def add_drums(pat, kick=True, snare=True, hat8=True, ohat=True, clap=False,
              kv=60, sv=56, hv=36, ov=32, hat16=False, crash=False):
    if crash: put(pat, 0, CH_CRASH, note="C-4", volume=44)
    if kick:
        for r in range(0, 64, 4): put(pat, r, CH_KICK, note="C-4", volume=kv)
    if snare:
        for r in range(4, 64, 8): put(pat, r, CH_SNARE, note="C-4", volume=sv)
    if clap:
        for r in range(4, 64, 8): put(pat, r, CH_CLAP, note="C-4", volume=44)
    if hat8 or hat16:
        step = 2 if hat8 else 1
        for r in range(0, 64, step):
            if ohat and r % 4 == 2: continue
            put(pat, r, CH_HAT, note="C-4", volume=hv + (6 if r % 4 == 0 else 0))
    if ohat:
        for r in range(2, 64, 4): put(pat, r, CH_OHAT, note="C-4", volume=ov)

# ------------------------------------------------------------------ melodies
MEL_A1 = [
 (0,"B-4",4),(4,"E-5",2),(6,"G-5",2),(8,"F#5",4),(12,"E-5",4),
 (16,"C-5",2),(18,"E-5",2),(20,"G-5",2),(22,"E-5",2),(24,"A-5",4),(28,"G-5",4),
 (32,"D-5",2),(34,"G-5",2),(36,"B-5",2),(38,"A-5",2),(40,"G-5",4),(44,"D-5",4),
 (48,"F#5",2),(50,"A-5",2),(52,"B-5",4),(56,"A-5",4),(60,"F#5",2),(62,"D-5",2),
]
MEL_A2 = [
 (0,"B-4",2),(2,"E-5",2),(4,"G-5",2),(6,"F#5",1),(7,"E-5",1),(8,"E-5",2),(10,"G-5",2),(12,"B-5",4),
 (16,"C-6",2),(18,"B-5",2),(20,"G-5",2),(22,"E-5",2),(24,"A-5",4),(28,"G-5",2),(30,"E-5",2),
 (32,"D-5",2),(34,"G-5",2),(36,"B-5",2),(38,"D-6",1),(39,"C-6",1),(40,"B-5",4),(44,"G-5",4),
 (48,"F#5",2),(50,"A-5",2),(52,"B-5",2),(54,"C-6",2),(56,"A-5",2),(58,"F#5",2),(60,"G-5",4),
]
MEL_B1 = [
 (0,"E-5",2),(2,"G-5",2),(4,"B-5",2),(6,"E-6",2),(8,"D-6",2),(10,"B-5",2),(12,"G-5",4),
 (16,"G-5",2),(18,"E-5",2),(20,"G-5",2),(22,"C-6",2),(24,"B-5",4),(28,"G-5",4),
 (32,"D-5",2),(34,"G-5",2),(36,"B-5",2),(38,"D-6",2),(40,"C-6",4),(44,"B-5",4),
 (48,"A-5",2),(50,"F#5",2),(52,"A-5",2),(54,"D-6",2),(56,"B-5",4),(60,"A-5",2),(62,"F#5",2),
]
MEL_B2 = [
 (0,"E-6",2),(2,"D-6",2),(4,"B-5",2),(6,"G-5",2),(8,"E-5",4),(12,"G-5",4),
 (16,"C-6",2),(18,"B-5",2),(20,"G-5",2),(22,"E-5",2),(24,"C-6",4),(28,"G-5",4),
 (32,"B-5",2),(34,"D-6",2),(36,"C-6",2),(38,"B-5",2),(40,"G-5",4),(44,"D-5",4),
 (48,"F#5",2),(50,"A-5",2),(52,"B-5",4),(56,"A-5",2),(58,"F#5",2),(60,"D#5",4),
]
MEL_CHIP = [
 (0,"G-4",4),(4,"B-4",4),(8,"E-5",8),
 (16,"G-5",8),(24,"E-5",8),
 (32,"D-5",4),(36,"G-5",4),(40,"B-5",8),
 (48,"A-5",8),(56,"F#5",4),(60,"A-5",4),
]

# P0 intro
p = 0
add_pad(p, PROG, vol=32)
add_arp(p, PROG, vol=26, every=2, bars=(0,1))
add_arp(p, PROG, vol=30, every=1, bars=(2,3))
for r in range(0, 64, 2): put(p, r, CH_HAT, note="C-4", volume=22 + (6 if r % 4 == 0 else 0))
for r in (48, 52, 56, 60): put(p, r, CH_KICK, note="C-4", volume=50)
put(p, 0, CH_CRASH, note="C-4", volume=26)
for i, r in enumerate(range(32, 64, 8)):
    put(p, r, CH_RISER, note="C-4", volume=20 + i*8)
for r in range(56, 64):
    put(p, r, CH_SNARE, note="C-4", volume=18 + (r-56)*4)

# P1 groove
p = 1
add_pad(p, PROG, vol=30); add_arp(p, PROG, vol=34)
add_bass(p, PROG, vol=38, extra16=True)
add_drums(p, kv=62, sv=56)
put(p, 0, CH_CRASH, note="C-4", volume=40)

# P2 melody A
p = 2
add_pad(p, PROG, vol=30); add_arp(p, PROG, vol=34)
add_bass(p, PROG, vol=38, extra16=True)
add_drums(p, kv=62, sv=56)
putline(p, CH_LEAD, MEL_A1, vol=54)
putline(p, CH_LEAD2, down12(MEL_A1), vol=36)
for (r, note, dur) in MEL_A1:
    if r+3 <= 63: put(p, r+3, CH_ECHO, note=note, volume=22)

# P3 melody A variation
p = 3
add_pad(p, PROG, vol=30); add_arp(p, PROG, vol=32)
add_bass(p, PROG, vol=38, extra16=True)
add_drums(p, kv=62, sv=56, clap=True)
putline(p, CH_LEAD, MEL_A2, vol=54)
putline(p, CH_LEAD2, down12(MEL_A2), vol=36)
for (r, note, dur) in MEL_A2:
    if r+3 <= 63: put(p, r+3, CH_ECHO, note=note, volume=22)

# P4 break
p = 4
add_pad(p, PROG, vol=34)
putline(p, CH_CHIP, MEL_CHIP, vol=42)
for r in range(0, 64, 8): put(p, r, CH_OHAT, note="C-4", volume=26)
put(p, 0, CH_CRASH, note="C-4", volume=38)
for bar in range(4):
    put(p, bar*16, CH_BASS, note=CH_[PROG[bar]][2], volume=42)
    put(p, bar*16+8, CH_BASS, note=shift(CH_[PROG[bar]][2], 12), volume=36)
for r in (0, 16, 32, 48): put(p, r, CH_KICK, note="C-4", volume=44)
for i, (r, note, dur) in enumerate(MEL_CHIP):
    put(p, r, CH_PLUCK, note=note, volume=30)

# P5 build
p = 5
add_pad(p, PROG, vol=28)
add_arp(p, PROG, vol=26, every=2)
for r in range(0, 48, 4): put(p, r, CH_KICK, note="C-4", volume=40 + (r//4)*2)
for r in range(48, 64):
    put(p, r, CH_KICK, note="C-4", volume=58)
    put(p, r, CH_SNARE, note="C-4", volume=22 + (r-48)*2.5)
for r in range(0, 64, 2): put(p, r, CH_HAT, note="C-4", volume=24 + r//4)
for i, r in enumerate(range(0, 64, 16)):
    put(p, r, CH_RISER, note="C-4", volume=22 + i*12)

# P6 melody B
p = 6
add_pad(p, PROG, vol=30); add_arp(p, PROG, vol=34)
add_bass(p, PROG, vol=40, extra16=True)
add_drums(p, kv=64, sv=58, clap=True)
putline(p, CH_LEAD, MEL_B1, vol=54)
putline(p, CH_LEAD2, down12(MEL_B1), vol=36)
for (r, note, dur) in MEL_B1:
    if r+3 <= 63: put(p, r+3, CH_ECHO, note=note, volume=22)
put(p, 0, CH_CRASH, note="C-4", volume=42)

# P7 melody B variation + turnaround
p = 7
add_pad(p, PROG_END, vol=30); add_arp(p, PROG_END, vol=34)
add_bass(p, PROG_END, vol=40, extra16=True)
add_drums(p, kv=64, sv=58, clap=True)
putline(p, CH_LEAD, MEL_B2, vol=54)
putline(p, CH_LEAD2, down12(MEL_B2), vol=36)
for (r, note, dur) in MEL_B2:
    if r+3 <= 63: put(p, r+3, CH_ECHO, note=note, volume=22)
put(p, 0, CH_CRASH, note="C-4", volume=42)
for r in range(60, 64):
    put(p, r, CH_SNARE, note="C-4", volume=30 + (r-60)*9)

# ---- make sure nothing rings over a section boundary ----------------
for pat in range(NPAT):
    nxt = (pat+1) % NPAT
    chan_rows = {}
    for (pp, rr, cc) in cells:
        if pp == pat and 'note' in cells[(pp,rr,cc)]:
            chan_rows.setdefault(cc, []).append(rr)
    for cc, rows_ in chan_rows.items():
        last = max(rows_)
        first_next = min([rr for (pp,rr,c2) in cells if pp == nxt and c2 == cc and 'note' in cells[(pp,rr,c2)]], default=None)
        if first_next != 0:
            put(nxt, 0, cc, effect=14, effect_param=0xC0)

# ------------------------------------------------------------------ emit
GAIN = float(os.environ.get('GAIN', '1.3'))
# per-channel trim applied on top of GAIN (final vol = design * GAIN * CHMUL[ch])
CHMUL = {2: 0.62, 13: 0.9}
SOLO = os.environ.get('SOLO')
if SOLO is not None:
    keep = int(SOLO)
    cells = {k: v for k, v in cells.items() if k[2] == keep}
    SAMPLES = [x for x in SAMPLES if x['inst'] == CH2INST[keep]]

calls = [{"name":"module_new","arguments":{"channels":NC,"name":"CRYSTAL KEYGEN"}}]
for s in SAMPLES:
    data = s['data']
    calls.append({"name":"sample_create_from_pcm","arguments":{
        "instrument":s['inst'], "sample":0, "pcm":pcm(data), "encoding":"int16", "name":s['name']}})
    meta = {"instrument":s['inst'], "relative_note":REL, "panning":s['pan'], "volume":s['vol'],
            "flags": 16 | (1 if s['loop'] else 0)}
    if s['loop']:
        meta["loop_start"], meta["loop_length"] = s['loop']
    calls.append({"name":"sample_set","arguments":meta})
    calls.append({"name":"instrument_set","arguments":{"instrument":s['inst'],"name":s['name']}})
calls.append({"name":"song_set","arguments":{"bpm":140,"speed":6,"length":NPAT,"loop_start":0,"channels":NC}})
for i in range(NPAT):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":i,"rows":64}})
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
for (pat,row,ch),v in sorted(cells.items()):
    a = {"pattern":pat,"row":row,"channel":ch}
    a.update({k: val for k, val in v.items() if val is not None})
    if 'volume' in a: a['volume'] = int(min(64, max(0, a['volume'] * GAIN * CHMUL.get(ch, 1.0))))
    calls.append({"name":"pattern_set_cell","arguments":a})
outxm = "/tmp/solo.xm" if SOLO else "/workspace/submission/tune.xm"
outwv = "/tmp/solo.wav" if SOLO else "/workspace/out.wav"
calls.append({"name":"module_save","arguments":{"path":outxm,"format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":outwv,"rate":44100,"bits":16,
              "loops": int(os.environ.get('LOOPS','1'))}})
json.dump(calls, open('/tmp/build.json','w'))
print("calls:", len(calls), "cells:", len(cells))
