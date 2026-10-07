#!/usr/bin/env python3
"""Regenerate clean loopable + one-shot samples with perfect DC and loops."""
import numpy as np
import wave
import os

OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)
SR = 44100

def save_wav(path, data, sr=SR):
    data = np.asarray(data, dtype=np.float64)
    data = data - data.mean()
    pk = np.abs(data).max()
    if pk > 1e-9:
        data = data / pk * 0.88
    pcm = np.clip(data * 32767.0, -32767, 32767).astype(np.int16)
    with wave.open(path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"saved {path} n={len(data)} ({len(data)/sr:.4f}s) pk={pk:.3f}")
    return len(data)

def adsr(n, a=0.005, d=0.1, s=0.6, r=0.2, sr=SR):
    env = np.zeros(n)
    na = max(1, int(a*sr)); nd = max(1, int(d*sr)); nr = max(1, int(r*sr))
    ns = max(0, n - na - nd - nr)
    i = 0
    env[i:i+na] = np.linspace(0, 1, na); i += na
    end = min(i+nd, n); env[i:end] = np.linspace(1, s, end-i); i = end
    end = min(i+ns, n); env[i:end] = s; i = end
    if i < n:
        env[i:] = np.linspace(s, 0, n-i)
    return env

def perfect_loop_wave(freq, n_periods, wave_fn, fade_x=0):
    """Exact integer number of periods at SR (rounded)."""
    # Choose length as nearest samples for exact periods
    n = int(round(n_periods * SR / freq))
    # Adjust so n * freq / SR is nearly integer
    t = np.arange(n) / SR
    # Phase advances exactly n_periods over n samples
    phase = 2 * np.pi * n_periods * np.arange(n) / n
    sig = wave_fn(phase, t)
    # Force seamless: match first sample
    sig = sig - sig.mean()
    # Crossfade tiny ends if needed
    if fade_x > 0:
        f = fade_x
        env = np.linspace(0, 1, f)
        sig[:f] = sig[:f]*env + sig[-f:]* (1-env)  # no this doubles
    # Better approach: synthesize then blend end into start
    sig[-1] = sig[0]
    return sig, 0, n

rng = np.random.RandomState(42)

# KICK
def make_kick():
    dur = 0.3
    n = int(SR * dur)
    t = np.arange(n)/SR
    freq = 140*np.exp(-t*16) + 32
    phase = 2*np.pi*np.cumsum(freq)/SR
    body = np.sin(phase)
    click = np.sin(2*np.pi*900*t) * np.exp(-t*90)
    sub = np.sin(2*np.pi*42*t) * np.exp(-t*7)
    env = np.exp(-t*10)
    env[:max(1,int(0.003*SR))] = np.linspace(0, env[max(1,int(0.003*SR))-1] if int(0.003*SR)<n else 1, max(1,int(0.003*SR)))
    sig = np.tanh((0.75*body + 0.2*click + 0.45*sub)*1.4) * env
    # fade out end
    sig[-200:] *= np.linspace(1,0,200)
    return sig

# SNARE
def make_snare():
    n = int(0.25*SR); t = np.arange(n)/SR
    tone = np.sin(2*np.pi*185*t)*np.exp(-t*18) + 0.45*np.sin(2*np.pi*340*t)*np.exp(-t*22)
    noise = rng.randn(n)
    noise = np.concatenate([[0], np.diff(noise)])
    noise /= (np.abs(noise).max()+1e-12)
    sig = 0.4*tone + 0.6*noise*np.exp(-t*12) + 0.25*rng.randn(n)*np.exp(-t*55)
    sig = np.tanh(sig*1.2)
    sig[-300:] *= np.linspace(1,0,300)
    return sig

# HATS
def make_hat(dur, decay, seed):
    n = int(dur*SR); t = np.arange(n)/SR
    r = np.random.RandomState(seed)
    noise = r.randn(n)
    metal = sum(np.sign(np.sin(2*np.pi*f*t + r.rand()*6))*a for f,a in
                [(4200,0.15),(5600,0.12),(7300,0.1),(9000,0.08),(11000,0.06)])
    sig = (0.55*noise + 0.45*metal) * np.exp(-t*decay)
    sig[-80:] *= np.linspace(1,0,80)
    return np.tanh(sig)

# CLAP
def make_clap():
    n = int(0.22*SR); t = np.arange(n)/SR
    r = np.random.RandomState(11)
    sig = np.zeros(n)
    for delay, amp in [(0,1.0),(0.011,0.85),(0.021,0.65),(0.030,0.45)]:
        d = int(delay*SR); bl = int(0.035*SR)
        if d+bl > n: continue
        burst = r.randn(bl)*np.exp(-np.arange(bl)/SR*55)
        sig[d:d+bl] += burst*amp
    sig = sig - np.convolve(sig, np.ones(5)/5, mode='same')*0.25
    sig *= np.exp(-t*9)
    sig[-200:] *= np.linspace(1,0,200)
    return np.tanh(sig*1.4)

# BASS: multi supersaw, exact periods at C3=130.8128
def make_bass():
    freq = 130.8128
    n_per = 16
    n = int(round(n_per * SR / freq))
    # generate detuned saws over this length with EXACT period count per oscillator...
    # Use continuous phase based on exact freq, then force loop by crossfade
    t = np.arange(n)/SR
    sig = np.zeros(n)
    for det in [-7, -3, 0, 3, 6]:  # cents
        f = freq * (2**(det/1200.0))
        ph = 2*np.pi*f*t
        saw = 2*((ph/(2*np.pi)) % 1) - 1
        sig += saw
    sig /= 5.0
    # soft LPF
    k = 28
    sig = np.convolve(sig, np.ones(k)/k, mode='same')
    sig = np.tanh(sig*1.15)
    # crossfade loop
    cf = 64
    env_out = np.linspace(1, 0, cf)
    env_in = np.linspace(0, 1, cf)
    start = sig[:cf].copy()
    end = sig[-cf:].copy()
    blend = end*env_out + start*env_in
    sig[:cf] = blend
    sig[-cf:] = blend
    sig = sig - sig.mean()
    return sig, 0, n

# LEAD: pulse at C5
def make_lead():
    freq = 523.2511
    n_per = 32
    n = int(round(n_per * SR / freq))
    t = np.arange(n)/SR
    sig = np.zeros(n)
    for det, w in [(-5,0.32), (0,0.38), (6,0.30)]:
        f = freq*(2**(det/1200.0))
        ph = (f*t) % 1.0
        pulse = np.where(ph < w, 1.0, -1.0)
        sig += pulse
    sig /= 3
    # mild lowpass
    k = 6
    sig = np.convolve(sig, np.ones(k)/k, mode='same')
    # add quiet octave sine for body
    sig += 0.15*np.sin(2*np.pi*freq*t)
    sig = np.tanh(sig*0.95)
    cf = 48
    env_out = np.linspace(1,0,cf); env_in = np.linspace(0,1,cf)
    blend = sig[-cf:]*env_out + sig[:cf]*env_in
    sig[:cf] = blend; sig[-cf:] = blend
    sig = sig - sig.mean()
    return sig, 0, n

# PAD soft
def make_pad():
    freq = 261.6256
    n_per = 64
    n = int(round(n_per * SR / freq))
    t = np.arange(n)/SR
    sig = np.zeros(n)
    for det, amp in [(-15,0.35),(-5,0.45),(0,0.5),(7,0.4),(14,0.3)]:
        f = freq*(2**(det/1200.0))
        ph = 2*np.pi*f*t
        saw = 2*((ph/(2*np.pi))%1)-1
        sig += (0.7*saw + 0.3*np.sin(ph))*amp
    sig /= 2.5
    for k in (100, 50):
        sig = np.convolve(sig, np.ones(k)/k, mode='same')
    cf = 128
    env_out = np.linspace(1,0,cf); env_in = np.linspace(0,1,cf)
    blend = sig[-cf:]*env_out + sig[:cf]*env_in
    sig[:cf] = blend; sig[-cf:] = blend
    sig = sig - sig.mean()
    return sig, 0, n

# ARP pluck - short, no loop
def make_arp():
    # multi harmonic decaying - tuned so C-4 relative will be adjusted; content at A4=440
    freq = 440.0
    n = int(0.4*SR); t = np.arange(n)/SR
    sig = np.zeros(n)
    for h, amp, dcy in [(1,1.0,8),(2,0.55,12),(3,0.35,16),(4,0.2,20),(5,0.12,25),(7,0.06,30)]:
        sig += amp*np.sin(2*np.pi*freq*h*t)*np.exp(-t*dcy)
    click_n = int(0.004*SR)
    sig[:click_n] += rng.randn(click_n)*0.25*np.linspace(1,0,click_n)
    sig *= adsr(n, a=0.001, d=0.1, s=0.2, r=0.25)
    return np.tanh(sig)

# BELL FM
def make_bell():
    freq = 1046.5
    n = int(1.0*SR); t = np.arange(n)/SR
    mod = np.sin(2*np.pi*freq*1.4*t)*np.exp(-t*3.5)*2.2
    car = np.sin(2*np.pi*freq*t + mod)*np.exp(-t*2.5)
    car2 = 0.25*np.sin(2*np.pi*freq*2.02*t)*np.exp(-t*4.5)
    sig = (car+car2)*adsr(n, a=0.001, d=0.2, s=0.25, r=0.6)
    return np.tanh(sig)

def make_tom():
    n = int(0.22*SR); t = np.arange(n)/SR
    freq = 130*np.exp(-t*9)+55
    phase = 2*np.pi*np.cumsum(freq)/SR
    sig = np.sin(phase)*np.exp(-t*11)
    sig += 0.15*rng.randn(n)*np.exp(-t*28)
    sig[-150:] *= np.linspace(1,0,150)
    return np.tanh(sig*1.3)

kick = make_kick(); save_wav(f"{OUT}/kick.wav", kick)
snare = make_snare(); save_wav(f"{OUT}/snare.wav", snare)
hat_c = make_hat(0.055, 80, 7); save_wav(f"{OUT}/hat_c.wav", hat_c)
hat_o = make_hat(0.28, 11, 9); save_wav(f"{OUT}/hat_o.wav", hat_o)
clap = make_clap(); save_wav(f"{OUT}/clap.wav", clap)
bass, bls, bll = make_bass(); save_wav(f"{OUT}/bass.wav", bass); print("bass loop", bls, bll)
lead, lls, lll = make_lead(); save_wav(f"{OUT}/lead.wav", lead); print("lead loop", lls, lll)
arp = make_arp(); save_wav(f"{OUT}/arp.wav", arp)
pad, pls, pll = make_pad(); save_wav(f"{OUT}/pad.wav", pad); print("pad loop", pls, pll)
bell = make_bell(); save_wav(f"{OUT}/bell.wav", bell)
tom = make_tom(); save_wav(f"{OUT}/tom.wav", tom)

# write lengths for loop setup
with open(f"{OUT}/loops.txt","w") as f:
    f.write(f"bass {bll}\nlead {lll}\npad {pll}\n")
print("done", open(f"{OUT}/loops.txt").read())
