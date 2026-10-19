"""Instrument samples for the keygen tune: 8-bit mono WAV @ 44100 Hz."""
import numpy as np, wave, os, sys
sys.path.insert(0, '/workspace')
from lib_samples import *

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inst')
os.makedirs(OUT, exist_ok=True)
P = 159                      # waveform period -> 277.36 Hz base; cell note 60 == C5

# Every sample carries a silent tail of 1/3 of its total length.  That tail is
# used as the sample's loop point, which makes the XM "C5 speed" of every
# sample come out at 12481 Hz - the value that reproduces the intended pitches
# in strict XM players as well as in the tracker.
TAIL = 1.0/3.0

def w8(name, x):
    n = len(x)
    tail = int(round(n*TAIL/(1.0-TAIL)))
    x = np.concatenate([x, np.zeros(tail)])
    d = np.round(np.clip(x, -1, 1)*127).astype(np.int8)
    with wave.open(os.path.join(OUT, name+'.wav'), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(1); f.setframerate(SR); f.writeframes(d.tobytes())
    return len(d), tail

def voice(name, wavefn, body, sustain, tau, attack, post=None, norm=0.92, p=P,
          tail=0.10):
    x, Pp, be, ll, _ = make_voice(wavefn, SR/p, body, sustain, tau, attack,
                                  loops=1, post=post)
    # make_voice appends one loop period; trim it -> pure one-shot body
    x = x[:be]
    # fade the very end to silence: this region becomes the sample's loop
    # point, so a looping player sustains silence instead of a drone
    n = int(len(x)*tail)
    if n > 2:
        ramp = np.linspace(1.0, 0.0, n)**1.5
        x[-n:] *= ramp
    n, tail = w8(name, x)
    print('%-8s len=%6d body=%6d tail=%6d  (%.2f s @base)' % (name, n, be, tail, be/SR))
    return be

def grit(x, levels=28, hold_rate=13000):
    return bitcrush(x, levels, hold_rate)

def soft_saw(n, p):
    out = np.zeros(n)
    for h in range(1, 14):
        out += np.sin(2*np.pi*h*frac(n, p))/h**1.7
    return out/np.max(np.abs(out))

def buzz(n, p):
    out = np.zeros(n)
    for h in range(1, 11):
        out += np.sin(2*np.pi*h*frac(n, p))/h**1.15
    return out/np.max(np.abs(out))

def pulse_stack(n, p):
    return 0.62*wave_pulse(n, p, 0.5) + 0.3*wave_pulse(n, p, 0.25) + 0.18*wave_pulse(n, p, 0.125)

# --- pitched voices (identical period => identical note/pitch mapping) -------
voice('lead',  lambda n,p: wave_pulse(n,p,0.25),  0.62, 0.26, 0.11, 0.002, grit)
voice('lead2', lambda n,p: wave_pulse(n,p,0.125), 0.55, 0.20, 0.13, 0.002, lambda x: bitcrush(x, 40, 0))
voice('arp',   lambda n,p: wave_pulse(n,p,0.5),   0.30, 0.17, 0.055, 0.001, lambda x: bitcrush(x, 48, 0))
voice('bass',  buzz,                            0.20, 0.26, 0.035, 0.002, lambda x: dist(x, 1.9)*0.72)
voice('pad',   soft_saw,                        3.20, 0.52, 1.20, 0.050)
voice('stab',  lambda n,p: wave_pulse(n,p,0.5), 0.24, 0.13, 0.040, 0.001, lambda x: bitcrush(x, 36, 0))
voice('organ', pulse_stack,                    0.45, 0.30, 0.22, 0.022)

# --- drums -------------------------------------------------------------------
rng = np.random.RandomState(42)
def noise(n): return rng.uniform(-1, 1, n)
def hpnoise(n):
    y = hp(noise(n)); y = hp(y)
    return y/np.max(np.abs(y))
def sweep_pulse(dur, f0, f1, duty=0.5, decay=16.0, click=0.0):
    n = int(dur*SR); t = np.arange(n)/SR
    f = f1 + (f0-f1)*np.exp(-t*18.0)
    ph = np.cumsum(f)/SR
    w = np.where((ph % 1.0) < duty, 1.0, -1.0)
    x = w*np.exp(-t*decay)
    if click > 0:
        x[:int(0.005*SR)] += click*rng.uniform(-1, 1, int(0.005*SR))
    return x

w8('kick',   np.tanh(sweep_pulse(0.26, 140, 45, 0.5, 15.0, click=0.6)*1.5))
n = int(0.19*SR); t = np.arange(n)/SR
w8('snare',  hpnoise(n)*np.exp(-t*26)*0.8 + wave_pulse(n, 88, 0.5)*np.exp(-t*30)*0.45)
n = int(0.05*SR); t = np.arange(n)/SR
w8('hat',    hpnoise(n)*np.exp(-t*62)*0.65)
n = int(0.28*SR); t = np.arange(n)/SR
w8('openhat', hpnoise(n)*np.exp(-t*10)*0.5)
n = int(0.95*SR); t = np.arange(n)/SR
w8('crash',  hpnoise(n)*np.exp(-t*3.8)*0.45)
w8('zap',    sweep_pulse(0.17, 2800, 170, 0.5, 13.0))
w8('tom',    sweep_pulse(0.24, 210, 90, 0.25, 12.0))
print('done')
