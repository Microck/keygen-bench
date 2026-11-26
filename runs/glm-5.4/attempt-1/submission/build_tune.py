#!/usr/bin/env python3
"""Neon Cascade -- original FastTracker II keygen module.

All instruments are synthesized from scratch below.  The music is written as
16-channel XM patterns (64 rows / four bars), not as a rendered audio stream.
"""
from __future__ import annotations
import math, struct, wave
from pathlib import Path
import numpy as np

SR = 44100
BPM = 150
SPEED = 3
ROWS = 64
CH = 16
NPAT = 44
OUT = Path(__file__).resolve().parent
WORK = OUT.parent / 'work'
WORK.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Pure NumPy sample synthesis
# ---------------------------------------------------------------------------
def tarr(dur: float) -> np.ndarray:
    return np.arange(max(2, int(round(dur * SR))), dtype=np.float64) / SR

def env_ad(t, attack=0.003, decay=8.0, power=1.0):
    a = np.clip(t / max(attack, 1e-6), 0, 1)
    return (a * np.exp(-decay * t)) ** power

def fades(x, attack=0.002, release=0.01):
    n = len(x)
    na = min(n, max(1, int(attack * SR)))
    nr = min(n, max(1, int(release * SR)))
    x[:na] *= np.linspace(0, 1, na)
    x[-nr:] *= np.linspace(1, 0, nr)
    return x

def add_wave(freq, t, kind='sine', phase=0.0, max_h=None):
    """Band-limited additive oscillator; phase is in cycles."""
    freq = np.broadcast_to(freq, t.shape)
    # Direct phase integration supports pitch envelopes.
    if np.asarray(freq).shape == t.shape:
        ph = np.cumsum(freq) / SR + phase
    else:
        ph = float(freq) * t + phase
    f = float(np.mean(freq))
    if kind == 'sine':
        return np.sin(2*np.pi*ph)
    if kind == 'tri':
        hmax = max_h or min(31, int((SR*0.45)/max(f, 1)))
        out = np.zeros_like(t)
        for h in range(1, hmax+1, 2):
            out += ((-1)**((h-1)//2)) * np.sin(2*np.pi*h*ph) / (h*h)
        return out * (8/np.pi**2)
    if kind in ('saw', 'pulse12', 'pulse25'):
        hmax = max_h or min(48, int((SR*0.43)/max(f, 1)))
        out = np.zeros_like(t)
        duty = 0.5 if kind == 'saw' else (0.25 if kind == 'pulse25' else 0.125)
        for h in range(1, hmax+1):
            # pulse Fourier amplitude; saw is the 50% pulse special case
            if kind == 'saw':
                amp = 1/h
            else:
                amp = 4/(h*np.pi) * np.sin(np.pi*h*duty)
            out += amp * np.sin(2*np.pi*h*ph + (0.0 if kind=='saw' else np.pi*h*duty))
        return out * (0.8 if kind=='saw' else 0.9)
    raise ValueError(kind)

def noise(dur):
    return np.random.default_rng(1977 + int(dur*100000)).uniform(-1,1,len(tarr(dur)))

def onepole_lp(x, cutoff):
    cutoff = np.broadcast_to(cutoff, x.shape)
    y = np.empty_like(x)
    z = 0.0
    # Cutoff array is in Hz; exponential moving average.
    for i, c in enumerate(cutoff):
        a = 1 - math.exp((-2*np.pi*float(c))/SR)
        z += a * (x[i]-z)
        y[i] = z
    return y

def onepole_hp(x, cutoff):
    return x - onepole_lp(x, cutoff)

def norm(x, peak=0.9):
    m = np.max(np.abs(x))
    return x * (peak/m if m > 1e-9 else 1.0)

def save_preview(name, x):
    # Only for offline inspection; the XM embeds the PCM itself.
    x = norm(x, 0.94)
    with wave.open(str(WORK/(name+'.wav')), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())

def make_samples():
    s = {}
    # Kick: sine pitch sweep, soft saturation, short noise beater.
    t=tarr(.48); f=46 + 150*np.exp(-t/.027)
    ph=np.cumsum(f)/SR
    body=np.sin(2*np.pi*ph)*np.exp(-t*7.2)
    click=np.random.default_rng(11).normal(0,1,len(t))*np.exp(-t/.003)
    click=onepole_hp(click,1800)
    x=np.tanh(1.8*body + .23*click)
    s['Kick']=norm(fades(x,.001,.025),.92)

    # Snare with a tuned body and crisp noise.
    t=tarr(.30); rng=np.random.default_rng(22)
    f=175*np.exp(-t*12)+105
    body=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*19)
    n=onepole_hp(rng.normal(0,1,len(t)),1100)
    n=onepole_lp(n,8500)*np.exp(-t*18)
    x=.52*body+.72*n
    s['Snare']=norm(fades(x,.001,.018),.82)

    # Three-burst hand clap, band limited around the right sibilant range.
    t=tarr(.28); x=np.zeros_like(t); rng=np.random.default_rng(23)
    for k,delay in enumerate([0,.012,.027,.044]):
        tt=t-delay; mask=tt>=0
        n=onepole_hp(rng.normal(0,1,len(t)),900)
        n=onepole_lp(n,4700)
        burst=n*np.exp(-np.maximum(tt,0)*(24 if k==3 else 48))*mask
        x += burst*(.65 if k<3 else 1.0)
    s['Clap']=norm(fades(x,.001,.025),.72)

    t=tarr(.080); rng=np.random.default_rng(24)
    x=onepole_hp(rng.normal(0,1,len(t)),6500)*np.exp(-t*52)
    x+=.18*np.sin(2*np.pi*9230*t)*np.exp(-t*70)
    s['Hat Closed']=norm(fades(x,.0005,.006),.55)

    t=tarr(.32); rng=np.random.default_rng(25)
    x=onepole_hp(rng.normal(0,1,len(t)),4200)*np.exp(-t*13)
    x+=.15*np.sin(2*np.pi*6137*t)*np.exp(-t*18)
    s['Hat Open']=norm(fades(x,.001,.035),.60)

    t=tarr(1.65); rng=np.random.default_rng(26)
    n=onepole_hp(rng.normal(0,1,len(t)),2600)
    metal=np.zeros_like(t)
    for f,a in [(317,0.22),(491,0.18),(743,0.14),(1139,0.10)]:
        metal += a*np.sin(2*np.pi*f*t+0.3*f)
    x=(n+.19*metal)*np.exp(-t*2.35)
    s['Crash']=norm(fades(x,.002,.20),.68)

    # Sub oscillator at C2 (root note is set in the XM instrument).
    t=tarr(.29); f=65.406391325
    x=np.sin(2*np.pi*f*t)+.16*np.sin(2*np.pi*2*f*t)+.055*np.sin(2*np.pi*3*f*t)
    x=np.tanh(1.25*x)*env_ad(t,.003,3.2)
    s['Sub']=norm(fades(x,.003,.045),.88)

    # Resonant acid bass at C2. SVF cutoff closes quickly for apluck-like snap.
    t=tarr(.19); f=65.406391325
    raw=add_wave(f,t,'saw')
    cutoff=250 + 2900*np.exp(-t/.038)
    low=np.zeros_like(t); band=np.zeros_like(t)
    q=.16
    for i in range(len(t)):
        fn=2*math.sin(math.pi*min(cutoff[i],9000)/SR)
        low[i]=low[i-1] if i else 0.0
        band[i]=band[i-1] if i else 0.0
        high=raw[i]-low[i]-q*band[i]
        band[i]+=fn*high
        low[i]+=fn*band[i]
    x=np.tanh(1.9*low)*env_ad(t,.0015,12)
    s['Acid']=norm(fades(x,.001,.018),.80)

    # Glass arpeggio / fast chip lead at C5.
    t=tarr(.20); f=523.2511306
    x=add_wave(f,t,'pulse25') + .32*add_wave(f*2.003,t,'tri')
    x*=env_ad(t,.0015,19)
    s['Chip Lead']=norm(fades(x,.001,.025),.64)

    # FM glass arpeggio at C5: bright initial partials, short bladed decay.
    t=tarr(.17); f=523.2511306
    mod=np.sin(2*np.pi*f*3.01*t)*.85*np.exp(-t*24)
    x=np.sin(2*np.pi*f*t+mod)+.30*np.sin(2*np.pi*f*2.002*t)
    x+=.16*add_wave(f*3.003,t,'tri')
    x*=env_ad(t,.001,23)
    s['Glass Arp']=norm(fades(x,.001,.025),.66)

    # Wide anthem lead at C5, with pitch vibrato and a vocal formant boost.
    t=tarr(.72); f=523.2511306*(1+.0038*np.sin(2*np.pi*5.3*t)*np.clip((t-.10)/.15,0,1))
    x=add_wave(f,t,'pulse12') + .48*add_wave(f*1.003,t,'saw') + .28*add_wave(f*.999,t,'pulse25')
    x+=.20*np.sin(2*np.pi*2*f*t)
    x=np.tanh(1.15*x)
    a=np.clip(t/.004,0,1); sus=np.clip((.72-t)/.25,0,1)
    x*=a*(.68+.32*np.exp(-t*3))*sus
    s['Anthem Lead']=norm(fades(x,.003,.035),.78)

    # Warm evolving pad at C4. One bar long at the original transposition.
    t=tarr(.67); f=261.6255653
    x=np.zeros_like(t)
    for ratio,amp,k in [(0.9965,.38,'saw'),(1.0,.34,'pulse25'),(1.0035,.38,'saw'),(2.001,.12,'tri')]:
        x += amp*add_wave(f*ratio,t,k)
    x=onepole_lp(x,1900 + 650*np.sin(2*np.pi*2.2*t))
    a=np.clip(t/.065,0,1); r=np.clip((.67-t)/.22,0,1)
    x*=a*r*(.78+.12*np.sin(2*np.pi*3*t))
    s['Neon Pad']=norm(fades(x,.005,.04),.62)

    # Low chords need a shorter release: at C/Db three this still lasts the
    # whole bar, but reaches silence just before the next chord change.
    t=tarr(.42); f=261.6255653
    x=np.zeros_like(t)
    for ratio,amp,k in [(0.9965,.38,'saw'),(1.0,.34,'pulse25'),(1.0035,.38,'saw'),(2.001,.12,'tri')]:
        x += amp*add_wave(f*ratio,t,k)
    x=onepole_lp(x,1800 + 500*np.sin(2*np.pi*2.2*t))
    x*=np.clip(t/.040,0,1)*np.clip((.42-t)/.20,0,1)
    s['Low Neon Pad']=norm(fades(x,.004,.025),.62)

    # Crystal FM bell at C5.
    t=tarr(.90); f=523.2511306
    x=np.zeros_like(t)
    for ratio,amp,dec in [(1,1,4.2),(2.01,.35,6.5),(2.76,.42,7),(4.07,.18,9),(5.40,.22,10),(8.93,.09,14)]:
        x += amp*np.sin(2*np.pi*f*ratio*t)*np.exp(-t*dec)
    x*=np.clip(t/.002,0,1)
    s['Crystal Bell']=norm(fades(x,.002,.10),.67)

    # Short rave piano/stab at C4.
    t=tarr(.38); f=261.6255653
    x=add_wave(f,t,'saw')+.55*add_wave(f*1.501,t,'pulse25')+.35*add_wave(f*2.002,t,'tri')
    x=onepole_lp(x,4200)*env_ad(t,.002,12)
    s['Rave Stab']=norm(fades(x,.002,.04),.67)

    # Riser occupies one complete 4-bar pattern when played at C4.
    t=tarr(3.14); rng=np.random.default_rng(31)
    n=onepole_hp(rng.normal(0,1,len(t)),700+2600*(t/t[-1])**1.4)
    f=95 + 690*(t/t[-1])**2.2
    tone=np.sin(2*np.pi*np.cumsum(f)/SR)*(.35+.25*(t/t[-1]))
    x=(.75*n+tone)*(.12+.88*(t/t[-1])**1.8)
    s['Riser']=norm(fades(x,.015,.035),.70)

    t=tarr(1.55); rng=np.random.default_rng(32)
    n=onepole_hp(rng.normal(0,1,len(t)),400+2200*np.exp(-t*2))
    f=850*np.exp(-t*1.25)+85
    x=(.7*n+.4*np.sin(2*np.pi*np.cumsum(f)/SR))*np.exp(-t*1.7)
    s['Downlifter']=norm(fades(x,.003,.12),.63)

    t=tarr(.18); f=1750*np.exp(-t*15)+150
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*12)
    x+=.2*np.sign(np.sin(2*np.pi*np.cumsum(f*1.01)/SR))*np.exp(-t*18)
    s['Laser Zip']=norm(fades(x,.001,.025),.56)

    t=tarr(.34); f=145*np.exp(-t*8)+58
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*10)
    x+=.18*np.sin(2*np.pi*2*np.cumsum(f)/SR)*np.exp(-t*13)
    s['Glow Tom']=norm(fades(x,.001,.045),.73)

    # Reverse noise swell, exactly 16 rows long, peak into the next downbeat.
    t=tarr(.79); rng=np.random.default_rng(33)
    n=onepole_hp(rng.normal(0,1,len(t)),1800)
    x=n*(t/t[-1])**2.4
    s['Reverse Crash']=norm(fades(x,.01,.003),.61)

    t=tarr(.52); rng=np.random.default_rng(34)
    n=onepole_hp(rng.normal(0,1,len(t)),900)
    x=n*np.sin(np.pi*t/t[-1])**2
    s['Pressure Noise']=norm(fades(x,.01,.06),.48)

    # Soft plucked octave at C4, useful for sparse breakdown answers.
    t=tarr(.58); f=261.6255653
    mod=np.sin(2*np.pi*f*2*t)*1.8*np.exp(-t*7)
    x=np.sin(2*np.pi*f*t+mod)*np.exp(-t*5.2)
    x+=.25*np.sin(2*np.pi*f*2.003*t)*np.exp(-t*7)
    s['Soft Pluck']=norm(fades(x,.002,.06),.64)

    pcm={}
    shape={'Snare':.50,'Clap':.50,'Hat Closed':.50,'Hat Open':.55,
           'Crash':.60,'Chip Lead':.55,'Glass Arp':.55,'Crystal Bell':.55,'Rave Stab':.65,
           'Laser Zip':.70,'Glow Tom':.65}
    for name,x in s.items():
        peak=min(.94, float(np.max(np.abs(x))) if np.max(np.abs(x))<.9 else .9)
        if name in shape:
            m=np.max(np.abs(x)); x=np.sign(x/m)*np.abs(x/m)**shape[name]*m
        x=norm(x,peak)
        pcm[name]=(np.clip(x,-1,1)*32767).astype('<i2')
        save_preview(name.replace(' ','_'),x)
    return pcm

# FT2's note C-4 advances a raw sample at about 8362.93 Hz.  The synthesized
# 44.1 kHz material is resampled once to 22326.34 Hz and transposed +17 in the
# XM, which restores both its original pitch and its original duration.
FT2_BASE_RATE = 8362.92927715654
TRACKER_RATE = FT2_BASE_RATE * 2 ** (17/12)

def tracker_resample(x):
    """Band-limited FFT interpolation to the FT2-compatible playback rate."""
    n = len(x)
    m = max(2, int(round(n * TRACKER_RATE / SR)))
    X = np.fft.rfft(x)
    Y = np.zeros(m//2 + 1, dtype=np.complex128)
    cut = int((m//2 + 1) * 0.96)
    common = min(len(X), cut)
    Y[:common] = X[:common]
    y = np.fft.irfft(Y, m) * (m / n)
    return y

# ---------------------------------------------------------------------------
# XM writer
# ---------------------------------------------------------------------------
def instrument_bytes(name, sample_name, rel, pan, pcm):
    # FT2 stores 16-bit XM samples as delta-encoded little-endian words.
    d=np.empty(len(pcm),dtype=np.int32); d[0]=pcm[0]; d[1:]=pcm[1:].astype(np.int32)-pcm[:-1].astype(np.int32)
    d=((d+32768)%65536-32768).astype('<i2')
    # Exact FT2-style 263-byte instrument header + 40-byte sample header.
    env=np.zeros(24,dtype='<H')
    head=struct.pack('<I22sBHI',263,name.encode('ascii')[:22].ljust(22,b'\0'),0,1,40)
    head+=bytes(96)+env.tobytes()+env.tobytes()
    head+=struct.pack('<11B4BH21s',0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,128,bytes(21))
    assert len(head)==263, len(head)
    sh=struct.pack('<IIIBBBBbB22s',len(pcm)*2,0,0,64,0,16,pan,rel,0,
                   sample_name.encode('ascii')[:22].ljust(22,b'\0'))
    assert len(sh)==40, len(sh)
    return head+sh+d.tobytes()

def write_xm(path, patterns, instruments, order):
    assert len(patterns)==NPAT and len(instruments)==22
    tracker=b'FastTracker II clone'
    h=struct.pack('<17s20sB20sH',b'Extended Module: ',b'Neon Cascade'.ljust(20,b'\0'),0x1a,
                  tracker.ljust(20,b'\0'),0x0104)
    h+=struct.pack('<IHHHHHHHH',276,len(order),0,CH,len(patterns),len(instruments),0,SPEED,BPM)
    ordbytes=bytes(order)+bytes(256-len(order))
    h+=ordbytes
    assert len(h)==336,len(h)
    body=bytearray(h)
    for cells in patterns:
        data=bytearray()
        for r in range(ROWS):
            for c in range(CH):
                e=cells.get((r,c))
                if e is None:
                    data+=bytes([0,0,255,0,0])
                else:
                    note=e.get('note',0); ins=e.get('ins',0); vol=e.get('vol',255)
                    eff=e.get('eff',0); par=e.get('par',0)
                    if e.get('off'): note=97
                    data+=bytes([note,ins,vol,eff,par])
        body+=struct.pack('<I',9)+struct.pack('>H',ROWS)+struct.pack('<BH',0,len(data))+data
    for name,rel,pan,pcm in instruments:
        body+=instrument_bytes(name,name[:22],rel,pan,pcm)
    Path(path).write_bytes(body)

# ---------------------------------------------------------------------------
# Musical notation and band helper functions
# ---------------------------------------------------------------------------
PC={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'Fb':4,'F':5,'F#':6,'Gb':6,
    'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'Cb':11}
def N(s):
    p=s[:-1]; o=int(s[-1]); return o*12+PC[p]+1

CHORDS={
 'Fm':  dict(root=N('F1'), acid=N('F2'), pad=[N('F3'),N('Ab3'),N('C4'),N('Eb4')], arp=[N('F4'),N('Ab4'),N('C5'),N('Eb5')]),
 'Db':  dict(root=N('Db1'),acid=N('Db2'),pad=[N('Db3'),N('F3'),N('Ab3'),N('C4')], arp=[N('Db4'),N('F4'),N('Ab4'),N('C5')]),
 'Ab':  dict(root=N('Ab1'),acid=N('Ab2'),pad=[N('Eb3'),N('Ab3'),N('C4'),N('Eb4')],arp=[N('Ab4'),N('C5'),N('Eb5'),N('G5')]),
 'Eb':  dict(root=N('Eb1'),acid=N('Eb2'),pad=[N('Eb3'),N('G3'),N('Bb3'),N('Eb4')],arp=[N('Eb4'),N('G4'),N('Bb4'),N('Db5')]),
 'Bbm': dict(root=N('Bb0'),acid=N('Bb2'),pad=[N('F3'),N('Bb3'),N('Db4'),N('F4')],arp=[N('Bb4'),N('Db5'),N('F5'),N('Ab5')]),
 'C7':  dict(root=N('C1'), acid=N('C2'), pad=[N('C3'),N('E3'),N('G3'),N('Bb3')],arp=[N('C4'),N('E4'),N('G4'),N('Bb4')]),
 'Cm':  dict(root=N('C1'), acid=N('C2'), pad=[N('C3'),N('Eb3'),N('G3'),N('Bb3')],arp=[N('C4'),N('Eb4'),N('G4'),N('Bb4')]),
}
PROG={'A':['Fm','Db','Ab','Eb'], 'B':['Fm','Db','Bbm','C7'],
      'C':['Db','Eb','Fm','Cm'], 'D':['Db','Eb','Fm','C7'],
      'E':['Ab','Db','Eb','Cm'], 'F':['Bbm','Db','Eb','C7']}

# Note rows below are offsets within a 16-row bar. Volume is XM 0..64.
MAIN_A=[
 [ (0,'C5',48),(2,'Ab4',42),(4,'F4',44),(6,'C5',46),(8,'Eb5',50),(10,'Db5',46),(12,'C5',44),(14,'Bb4',40) ],
 [ (0,'F5',50),(3,'Eb5',46),(6,'Db5',45),(8,'C5',44),(10,'Ab4',40),(12,'Bb4',42),(14,'C5',44) ],
 [ (0,'Eb5',49),(2,'C5',45),(4,'Ab4',42),(6,'C5',44),(8,'Eb5',47),(10,'F5',51),(12,'Eb5',47),(14,'C5',43) ],
 [ (0,'Db5',47),(2,'C5',43),(4,'Bb4',41),(6,'G4',38),(8,'Bb4',43),(10,'C5',45),(12,'Db5',47),(14,'Eb5',49) ],
]
MAIN_B=[
 [ (0,'F5',50),(3,'Eb5',47),(6,'C5',45),(8,'Ab4',41),(10,'Bb4',43),(12,'C5',45),(14,'Eb5',48) ],
 [ (0,'F5',50),(4,'Ab5',52),(6,'F5',47),(8,'Eb5',45),(10,'Db5',44),(12,'C5',43),(14,'Ab4',39) ],
 [ (0,'Ab4',42),(2,'Bb4',43),(4,'C5',45),(6,'Eb5',48),(8,'F5',51),(12,'Eb5',47),(14,'C5',44) ],
 [ (0,'Db5',47),(2,'F5',49),(4,'Ab5',51),(6,'F5',47),(8,'Eb5',46),(10,'Db5',45),(12,'C5',43),(14,'Bb4',41) ],
]
MAIN_B_C7=[MAIN_B[0],MAIN_B[1],MAIN_B[2],
 [ (0,'G4',38),(2,'Bb4',41),(4,'C5',44),(6,'E5',48),(8,'G5',50),(10,'E5',46),(12,'C5',43),(14,'Bb4',41) ],
]
BUILD=[
 [ (0,'Bb4',43),(3,'Db5',45),(6,'F5',47),(8,'Ab5',49),(12,'Ab5',46),(14,'F5',44) ],
 [ (0,'Ab5',47),(4,'F5',44),(6,'Eb5',42),(8,'Db5',42),(12,'C5',40),(14,'Ab4',38) ],
 [ (0,'Bb4',42),(4,'G4',39),(6,'Bb4',41),(8,'Eb5',44),(12,'Db5',42),(14,'C5',40) ],
 [ (0,'G4',38),(2,'Bb4',41),(4,'C5',44),(6,'E5',48),(8,'G5',50),(10,'E5',46),(12,'C5',43),(14,'Bb4',41) ],
]
MAIN_B_EB=[
 [ (0,'F5',50),(3,'Eb5',47),(6,'C5',45),(8,'Ab4',41),(10,'Bb4',43),(12,'C5',45),(14,'Eb5',48) ],
 [ (0,'F5',50),(4,'Ab5',52),(6,'F5',47),(8,'Eb5',45),(10,'Db5',44),(12,'C5',43),(14,'Ab4',39) ],
 [ (0,'Ab4',42),(2,'Bb4',43),(4,'C5',45),(6,'Eb5',48),(8,'F5',51),(12,'Eb5',47),(14,'C5',44) ],
 [ (0,'Bb4',45),(2,'C5',46),(4,'Db5',48),(6,'Eb5',49),(8,'G5',52),(10,'F5',49),(12,'Eb5',46),(14,'C5',43) ],
]
BUILD_VAR=[
 [ (0,'F5',48),(3,'Eb5',44),(6,'Db5',43),(8,'Bb4',41),(12,'Ab4',38),(14,'Bb4',40) ],
 [ (0,'F5',47),(4,'Ab5',49),(6,'F5',45),(8,'Eb5',43),(12,'Db5',42),(14,'C5',40) ],
 [ (0,'G5',47),(4,'Eb5',44),(6,'Bb4',41),(8,'Eb5',44),(12,'F5',46),(14,'G5',47) ],
 [ (0,'G4',38),(2,'Bb4',41),(4,'C5',44),(6,'E5',48),(8,'G5',50),(10,'E5',46),(12,'C5',43),(14,'Bb4',41) ],
]
CHORUS_A=[
 [ (0,'F5',52),(4,'Ab5',50),(6,'F5',47),(8,'Eb5',46),(12,'Db5',44),(14,'Eb5',46) ],
 [ (0,'G5',51),(4,'Bb5',49),(6,'G5',47),(8,'Eb5',45),(12,'F5',47),(14,'G5',49) ],
 [ (0,'Ab5',51),(4,'C6',50),(6,'Ab5',47),(8,'F5',46),(12,'Eb5',45),(14,'Db5',44) ],
 [ (0,'Eb5',48),(4,'G5',49),(6,'Eb5',46),(8,'C5',44),(12,'Bb4',42),(14,'C5',44) ],
]
CHORUS_B=[
 [ (0,'Ab5',52),(2,'F5',47),(4,'Eb5',45),(6,'Db5',44),(8,'F5',48),(12,'Ab5',50),(14,'Bb5',50) ],
 [ (0,'Bb5',51),(2,'G5',47),(4,'F5',45),(6,'Eb5',44),(8,'G5',48),(12,'Bb5',50),(14,'C6',51) ],
 [ (0,'C6',52),(2,'Ab5',48),(4,'F5',46),(6,'Eb5',44),(8,'Db5',44),(10,'C5',43),(12,'Ab4',40),(14,'Bb4',42) ],
 [ (0,'C5',46),(2,'Eb5',47),(4,'G5',49),(6,'Bb5',50),(8,'C6',51),(10,'Bb5',48),(12,'G5',47),(14,'E5',45) ],
]
CHORUS_B_CM=[
 [ (0,'Ab5',52),(2,'F5',47),(4,'Eb5',45),(6,'Db5',44),(8,'F5',48),(12,'Ab5',50),(14,'Bb5',50) ],
 [ (0,'Bb5',51),(2,'G5',47),(4,'F5',45),(6,'Eb5',44),(8,'G5',48),(12,'Bb5',50),(14,'C6',51) ],
 [ (0,'C6',52),(2,'Ab5',48),(4,'F5',46),(6,'Eb5',44),(8,'Db5',44),(10,'C5',43),(12,'Ab4',40),(14,'Bb4',42) ],
 [ (0,'C5',46),(2,'Eb5',47),(4,'G5',49),(6,'Bb5',50),(8,'C6',51),(10,'Bb5',48),(12,'G5',47),(14,'Eb5',45) ],
]
BREAK=[
 [ (0,'C5',42),(4,'Eb5',45),(8,'Ab5',47),(14,'G5',43) ],
 [ (0,'F5',43),(4,'Ab5',47),(8,'F5',42),(12,'Db5',41),(14,'C5',40) ],
 [ (0,'Bb4',40),(4,'Eb5',44),(8,'G5',46),(12,'F5',43),(14,'Eb5',42) ],
 [ (0,'Eb5',43),(4,'G5',45),(8,'C6',46),(12,'Bb4',39),(14,'C5',41) ],
]

class Track:
    def __init__(self):
        self.cells={}
    def put(self,row,ch,note=0,ins=0,vol=255,eff=0,par=0,off=False):
        if row<0 or row>=ROWS: return
        self.cells[(row,ch)]=dict(note=note,ins=ins,vol=vol,eff=eff,par=par,off=off)
    def note(self,row,ch,name,ins,vol=48,eff=0,par=0):
        self.put(row,ch,N(name) if isinstance(name,str) else name,ins,vol,eff,par)
    def drum(self,row,ch,ins,vol=48,eff=0,par=0):
        self.put(row,ch,N('C4'),ins,vol,eff,par)
    def merge(self,other):
        self.cells.update(other.cells)

def put_melody(tr, bars, ch=7, inst=10, volmul=1.0, echo=0, echo_inst=10, echo_vol=.62):
    echo_rows={}
    for b,events in enumerate(bars):
        for off,name,v in events:
            r=b*16+off; vv=max(1,min(64,int(v*volmul)))
            eff,par=(0x08,0x30) if off==0 else ((0x44,0x42) if off in (4,8) else (0,0))
            tr.note(r,ch,name,inst,vv,eff,par)
            if echo and r+echo<64:
                er=r+echo
                if er not in echo_rows or echo_rows[er]<vv:
                    echo_rows[er]=(name,vv)
    if echo:
        for r,(name,v) in sorted(echo_rows.items()):
            tr.note(r,ch+1,name,echo_inst,max(1,int(v*echo_vol)),0x08,0xE0)

def put_drums(tr, energy=2, fill=0, four=True):
    # 0 = none, 1 = sparse, 2 = full, 3 = dense
    if energy==0: return
    for bar in range(4):
        o=bar*16
        if four:
            kicks=[0,4,8,12] if energy>=2 else [0,8]
            if energy==1 and bar%2: kicks=[0,8,11]
        else:
            kicks=[0,3,8,10] if energy>=2 else [0,8]
        if bar==3 and fill>=2: kicks=[0,4,8,12,14]
        for r in kicks: tr.drum(o+r,0,1,52 if r in (0,8) else 46)
        if energy>=1:
            for r in (4,12):
                tr.drum(o+r,1,2,56 if energy>=2 else 40)
                tr.drum(o+r,2,3,44 if energy>=2 else 32)
        if energy>=2:
            for r in range(1,16,2):
                tr.drum(o+r,3,4,36 if r%4==1 else 42)
            for r in (2,6,10,14): tr.drum(o+r,4,5,46 if energy==2 else 52)
        elif energy==1:
            for r in (2,6,10,14): tr.drum(o+r,3,4,30)
        if bar==3:
            if fill==1:
                for r,v in [(14,28),(15,33)]: tr.drum(o+r,1,2,v)
            elif fill>=2:
                for r in range(56,64):
                    v=20+int((r-56)*2.2)
                    tr.drum(r,1,2,v)
                for r,v in [(58,30),(60,32),(62,34)]: tr.drum(r,4,18,v+10)
        if energy==3:
            # Additional 32nd-style feel using one-row closed-hat ticks.
            for r in range(o,o+16):
                if r%2==0: tr.drum(r,3,4,24)

def put_bass(tr, prog, style=2, variation=0):
    # style 0 = sub only, 1 = sparse, 2 = rolling, 3 = offbeat octaves
    for bar,cname in enumerate(prog):
        c=CHORDS[cname]; o=bar*16
        if style==0:
            tr.note(o,5,c['root'],7,24)
            tr.note(o+8,5,c['root'],7,20)
            continue
        tr.note(o,5,c['root'],7,32)
        tr.note(o+8,5,c['root']+(7 if variation and bar%2 else 0),7,28)
        if style==1:
            for r,deg,v in [(2,0,30),(6,12,25),(10,7,28),(14,0,24)]:
                tr.note(o+r,6,c['acid']+deg,8,v,0xED,1 if r%2 else 0)
        else:
            pattern=[(0,0,40),(2,12,31),(3,0,28),(6,7,34),(8,12,38),
                     (10,0,29),(11,3 if cname not in ('C7','Eb') else 4,27),
                     (14,10 if cname not in ('C7',) else 7,30),(15,12,25)]
            if style==3: pattern=[(0,0,41),(2,12,34),(4,0,35),(6,12,32),(8,7,38),(10,12,35),(12,0,32),(14,7,31)]
            for r,deg,v in pattern:
                swing=1 if (r&1) and variation else 0
                tr.note(o+r,6,c['acid']+deg,8,v,0xED if swing else 0,swing)

def put_pads(tr, prog, volume=28, breakdown=False, stab=False):
    for bar,cname in enumerate(prog):
        c=CHORDS[cname]; o=bar*16
        for j,name in enumerate(c['pad']):
            v=int(volume*(1.0 if j in (1,2) else .88))
            tr.note(o,10+j,name,22 if name<=N('G3') else 11,v,0x08,(0x30,0x70,0xA0,0xE0)[j])
        if breakdown:
            # A fifth above the top pad note enters softly on the third beat.
            tr.note(o+8,13,c['pad'][2]+7,13,int(volume*.42),0x08,0xE0)
        if stab:
            for r in (2,6,10,14):
                tr.note(o+r,10,c['acid'],14,31 if r!=14 else 35,0xED,1)

def put_arp(tr, prog, density=2, variation=0, vol=28):
    # density 1 = quarter notes, 2 = eighths, 3 = sixteenths
    seq=[0,1,2,3,2,1,0,2,1,3,2,1,0,1,2,3]
    for bar,cname in enumerate(prog):
        c=CHORDS[cname]; o=bar*16; notes=c['arp']
        step=1 if density==3 else (2 if density==2 else 4)
        for k,r in enumerate(range(0,16,step)):
            if variation and ((k+bar)%8 in (3,7)): continue
            idx=seq[(k+bar*2)%len(seq)]
            octave=12 if (variation and ((k//8+bar)%4==3) and idx<2) else 0
            v=vol + (5 if r%4==0 else (-3 if r%4==2 else 0))
            pan=0x60 if (r//step)%2==0 else 0xC0
            tr.note(o+r,9,notes[idx]+octave,12,v,0x08,pan)

def put_fx(tr, p, section_end=False, riser=False, reverse=False, zip_=False):
    if (p%4==0 and p>=4) or p==0:
        tr.drum(0,15,6,48)
    if riser:
        tr.note(0,15,N('C4'),15,48,0x08,0x80)
    if reverse:
        tr.note(48,14,N('C4'),19,42)
    if zip_:
        tr.note(62,13,N('C5'),17,35,0x08,0xC0)

def base_pattern(p, prog, energy=2, fill=0, bass=2, arp=2, pads=28, **kw):
    tr=Track()
    put_drums(tr,energy,fill)
    put_bass(tr,prog,bass,p%2)
    put_pads(tr,prog,pads,breakdown=(energy==0),stab=(energy>=3))
    put_arp(tr,prog,arp,p%4,(38 if energy>=3 else 30) if energy else 24)
    put_fx(tr,p,riser=(p in (3,27,39)),reverse=(p in (0,7,19,31,43)),zip_=(p in (3,15,27,39)))
    return tr

# ---------------------------------------------------------------------------
# Arrangement
# ---------------------------------------------------------------------------
def build_patterns():
    pats=[]
    for p in range(NPAT):
        if p<4: prog=['Fm','Fm','Db','Eb'] if p==0 else PROG['A']
        elif p<8: prog=PROG['A'] if p<6 else PROG['B']
        elif p<12: prog=PROG['A'] if p<10 else PROG['B']
        elif p<16: prog=PROG['C']
        elif p<20: prog=PROG['D'] if p<19 else PROG['C']
        elif p<24: prog=PROG['E'] if p<23 else PROG['F']
        elif p<28: prog=PROG['F']
        elif p<32: prog=PROG['A']
        elif p<36: prog=PROG['D']
        elif p<40: prog=PROG['A']
        else: prog=PROG['A']

        if p==0:
            tr=base_pattern(p,prog,energy=0,bass=0,arp=2,pads=31,reverse=True)
            put_melody(tr,[[ (0,'C5',36),(6,'Ab4',31),(10,'F4',32),(14,'C5',34) ]] +
                          [[ (0,'Db5',34),(6,'C5',31),(10,'Ab4',30),(14,'F4',29) ]] +
                          [[ (0,'Eb5',35),(6,'C5',32),(10,'Ab4',30),(14,'Eb4',28) ]] +
                          [[ (0,'Bb4',32),(6,'G4',29),(10,'Bb4',31),(14,'Db5',33) ]],
                          ch=7,inst=13,volmul=.85,echo=3,echo_inst=13,echo_vol=.48)
            # Kick and sub quietly establish pulse in the second half.
            for r in range(16,64,8): tr.drum(r,0,1,36)
            for bar,cname in enumerate(prog):
                tr.note(bar*16,5,CHORDS[cname]['root'],7,24)
                tr.note(bar*16+8,5,CHORDS[cname]['root'],7,20)
            tr.note(32,14,N('C4'),20,28)
        elif p in (1,2):
            tr=base_pattern(p,prog,energy=1 if p==1 else 2,fill=0,bass=1 if p==1 else 2,arp=2,pads=27)
            if p==1:
                put_melody(tr,[[ (0,'F4',34),(4,'Ab4',35),(8,'C5',37),(12,'Ab4',32) ],
                              [(0,'F4',33),(4,'Ab4',34),(8,'Db5',36),(12,'C5',32)],
                              [(0,'Eb4',32),(4,'Ab4',34),(8,'C5',36),(12,'Eb5',35)],
                              [(0,'Bb4',32),(4,'G4',30),(8,'Bb4',33),(12,'Db5',34)]],
                          inst=13,volmul=.9,echo=3,echo_inst=21,echo_vol=.60)
            else:
                put_melody(tr,MAIN_B_EB,ch=7,inst=9,volmul=.70,echo=3,echo_inst=13,echo_vol=.52)
            tr.note(48,14,N('C4'),20,34)
        elif p==3:
            tr=base_pattern(p,prog,energy=3,fill=3,bass=3,arp=3,pads=25)
            put_melody(tr,[[ (0,'C5',39),(4,'Eb5',41),(8,'F5',43),(12,'Ab5',44) ],
                          [(0,'F5',41),(4,'Eb5',38),(8,'C5',37),(12,'Ab4',35)],
                          [(0,'Eb5',39),(4,'C5',37),(8,'Ab4',35),(12,'C5',38)],
                          [(0,'Bb4',37),(4,'C5',39),(8,'Db5',41),(12,'Eb5',43)]],
                          inst=9,volmul=.85,echo=1,echo_inst=9,echo_vol=.56)
            # Snare roll is reinforced by the noise sweep.
            tr.note(48,14,N('C4'),20,38)
        elif p<8: # first main theme
            tr=base_pattern(p,prog,energy=3 if p>=6 else 2,fill=3 if p==7 else 1,
                            bass=3 if p>=6 else 2,arp=3 if p>=6 else 2,pads=27)
            melody=MAIN_A if p in (4,5) else MAIN_B_C7
            put_melody(tr,melody,ch=7,inst=9 if p<6 else 10,volmul=.82 if p<6 else .94,
                       echo=2,echo_inst=9,echo_vol=.54)
            if p==5:
                # A short answer in the crystal register prevents a four-bar loop feel.
                for r,name in [(34,'Ab4'),(38,'C5'),(42,'Eb5'),(50,'Db5'),(54,'C5'),(58,'Ab4')]:
                    tr.note(r,14,name,13,30)
        elif p<12: # hook / second main theme
            tr=base_pattern(p,prog,energy=3,fill=3 if p==11 else 1,bass=3,arp=3,pads=29)
            melody=MAIN_A if p==8 else (MAIN_B_EB if p==9 else MAIN_B_C7)
            put_melody(tr,melody,inst=10,volmul=1.0,echo=2,echo_inst=9,echo_vol=.60)
            if p in (9,11):
                for r,name in [(4,'F5'),(12,'C5'),(20,'Ab5'),(28,'F5'),(36,'Eb5'),(44,'C5'),(52,'Db5'),(60,'Bb4')]:
                    tr.note(r,14,name,13,26)
        elif p<20: # chorus, two 16-bar statements
            tr=base_pattern(p,prog,energy=3,fill=3 if p in (15,19) else 1,bass=3,arp=3,pads=40)
            if p<16:
                melody=CHORUS_B_CM if p in (13,15) else CHORUS_A
            else:
                melody=CHORUS_B_CM if p==19 else CHORUS_B
            put_melody(tr,melody,inst=10,volmul=1.12,echo=2,echo_inst=10,echo_vol=.62)
            # Bell doubles only the crown notes, not the whole melody.
            for b,events in enumerate(melody):
                for off,name,v in events:
                    if off in (0,4) and N(name)>=N('G5'):
                        tr.note(b*16+off,14,name,13,27)
            if p in (12,16):
                for r in range(0,64,4): tr.note(r,13,CHORDS[prog[r//16]]['arp'][2]+12,12,20)
        elif p<24: # breakdown, harmonic breathing room
            if p==20:
                tr=base_pattern(p,prog,energy=0,bass=0,arp=1,pads=37)
                put_melody(tr,BREAK,ch=7,inst=13,volmul=.9,echo=3,echo_inst=21,echo_vol=.58)
            elif p==21:
                tr=base_pattern(p,prog,energy=1,bass=1,arp=2,pads=35)
                put_melody(tr,BREAK,ch=7,inst=10,volmul=.75,echo=3,echo_inst=13,echo_vol=.50)
                for bar,cname in enumerate(prog):
                    tr.note(bar*16+8,14,CHORDS[cname]['arp'][1]+12,13,28)
            elif p==22:
                tr=base_pattern(p,prog,energy=1,bass=1,arp=2,pads=33)
                put_melody(tr,BREAK,ch=7,inst=10,volmul=.85,echo=2,echo_inst=9,echo_vol=.52)
                for bar,cname in enumerate(prog):
                    for r in (4,12): tr.note(bar*16+r,13,CHORDS[cname]['acid'],19,24)
            else:
                tr=base_pattern(p,prog,energy=2,fill=2,bass=2,arp=3,pads=32)
                put_melody(tr,BUILD,inst=9,volmul=.78,echo=2,echo_inst=9,echo_vol=.52)
                for r in range(32,64,4): tr.note(r,14,N('C5'),13,18+(r-32)//8)
        elif p<28: # second build / variation
            tr=base_pattern(p,prog,energy=3 if p>=25 else 2,fill=3 if p in (25,27) else 1,
                            bass=3 if p>=25 else 2,arp=3,pads=29)
            melody=BUILD if p<26 else BUILD_VAR
            put_melody(tr,melody,inst=9 if p<26 else 10,volmul=.80 if p<26 else .95,
                       echo=2,echo_inst=9,echo_vol=.56)
            if p==24: tr.note(0,14,N('C4'),16,35)
            if p==26:
                for r in (8,12,24,28,40,44,56,60): tr.note(r,15,N('C4'),18,24)
        elif p<32: # recapitulation, brighter and more direct
            tr=base_pattern(p,prog,energy=3,fill=3 if p==31 else 1,bass=3,arp=3,pads=30)
            melody=MAIN_A if p<30 else MAIN_B_EB
            put_melody(tr,melody,inst=10,volmul=.96,echo=2,echo_inst=9,echo_vol=.60)
            if p>=30:
                for r in (4,12,20,28,36,44,52,60): tr.note(r,14,N('C5'),17,24)
        elif p<40: # final chorus / climax
            tr=base_pattern(p,prog,energy=3,fill=3 if p in (35,39) else 1,bass=3,arp=3,pads=42)
            if p<36:
                melody=CHORUS_B
            else:
                melody=MAIN_B_EB if p in (37,39) else MAIN_A
            put_melody(tr,melody,inst=10,volmul=1.0,echo=2,echo_inst=10,echo_vol=.60)
            for b,events in enumerate(melody):
                for off,name,v in events:
                    if off==0 and N(name)>=N('F5'):
                        tr.note(b*16+off,14,name,13,28)
            if p in (32,36):
                for r in range(0,64,8): tr.note(r,13,CHORDS[prog[r//16]]['arp'][0]+12,12,24)
        else: # outro: retain harmony, remove layers, then turn back to the intro
            energy=3 if p==40 else (2 if p==41 else (1 if p==42 else 1))
            tr=base_pattern(p,prog,energy=energy,fill=3 if p==43 else 0,
                            bass=3 if p==40 else (2 if p==41 else 1),arp=3 if p<42 else 2,
                            pads=33 if p==40 else (29 if p<42 else 27))
            melody=MAIN_B_EB if p==40 else (MAIN_A if p==41 else
                    [[ (0,'C5',39),(4,'Ab4',34),(8,'F4',33),(12,'C5',35) ],
                     [(0,'Db5',36),(4,'C5',33),(8,'Ab4',31),(12,'F4',30) ],
                     [(0,'Eb5',36),(4,'C5',33),(8,'Ab4',31),(12,'Eb4',29) ],
                     [(0,'Bb4',33),(4,'G4',30),(8,'Bb4',32),(12,'Db5',34) ]])
            put_melody(tr,melody,inst=10 if p<42 else 13,volmul=.85 if p<42 else .80,
                       echo=2 if p<42 else 3,echo_inst=9 if p<42 else 13,echo_vol=.52)
            if p==43:
                # Final two bars resolve Eb back to the opening Fm; reverse crash
                # at row 48 lands exactly on the loop restart.
                tr.note(48,14,N('C4'),19,45)
                tr.note(60,13,N('C5'),17,28)
                tr.note(62,7,N('C5'),9,35)
                tr.note(63,7,N('Eb5'),9,37)
                # Clear a little space for the transition, but keep the harmonic pad.
                for r in range(48,64):
                    for c in (0,1,2,3,4,6,9):
                        if (r,c) in tr.cells: del tr.cells[(r,c)]
                for r in (48,56):
                    tr.drum(r,0,1,42)
                for r in (52,60): tr.drum(r,1,2,30)
                # Avoid stale echo/note tails when order position 43 restarts 0.
                for (r,c) in list(tr.cells):
                    if c==8 and r>=48: del tr.cells[(r,c)]
                for r in (60,61,62): tr.put(r,0,eff=0xA,par=0x0F)
                for r in (61,62): tr.put(r,2,eff=0xA,par=0x0F)
                tr.put(63,0,off=True); tr.put(63,2,off=True)
        pats.append(tr.cells)
    return pats

def main():
    pcm=make_samples()
    specs=[
        ('Kick',0,128),('Snare',0,112),('Clap',0,148),('Hat Closed',0,96),
        ('Hat Open',0,154),('Crash',0,132),('Sub',-24,128),('Acid',-24,104),
        ('Chip Lead',12,116),('Anthem Lead',12,116),('Neon Pad',0,128),
        ('Glass Arp',12,132),('Crystal Bell',12,168),('Rave Stab',0,100),
        ('Riser',0,128),('Downlifter',0,128),('Laser Zip',12,168),
        ('Glow Tom',0,120),('Reverse Crash',0,140),('Pressure Noise',0,120),('Soft Pluck',0,148),('Low Neon Pad',0,128),
    ]
    # 22 instruments: drums/bass 1..8, leads/pads 9..14, FX 15..20,
    # soft pluck 21 and the shorter low-register pad 22.
    ins=[]
    for idx,(name,rel,pan) in enumerate(specs,1):
        key=name
        if name=='Soft Pluck': key='Soft Pluck'
        ins.append((name,17,pan,(np.clip(tracker_resample(pcm[key].astype(np.float64)/32768),-1,1)*32767).astype('<i2')))
    patterns=build_patterns()
    write_xm(OUT/'tune.xm',patterns,ins,list(range(NPAT)))
    print('Wrote',OUT/'tune.xm', (OUT/'tune.xm').stat().st_size,'bytes')
    print('Duration',NPAT*ROWS*0.05,'seconds; loop start 0')

if __name__=='__main__': main()
