"""Refine samples for cleaner loop ending and punchier keygen feel."""
import numpy as np
import wave
import os

SR = 22050
OUT = '/workspace/work/samples'
os.makedirs(OUT, exist_ok=True)

def save_wav(name, samples, sr=SR):
    s = np.clip(np.asarray(samples, dtype=np.float64), -1.0, 1.0)
    s = s - np.mean(s)
    s16 = (s * 32767.0).astype(np.int16)
    path = os.path.join(OUT, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(s16.tobytes())

def envelope(n, a=0.005, d=0.05, s=0.6, r=0.1):
    A = int(a * SR); D = int(d * SR); R = int(r * SR)
    S = max(0, n - A - D - R)
    env = np.zeros(n)
    if A > 0: env[:min(A,n)] = np.linspace(0, 1, min(A,n))
    if D > 0 and n > A:
        dlen = min(D, n - A); env[A:A+dlen] = np.linspace(1, s, dlen)
    if S > 0 and n > A + D:
        slen = min(S, n - A - D); env[A+D:A+D+slen] = s
    if R > 0 and n > A + D + S:
        rlen = min(R, n - A - D - S)
        if rlen > 0: env[A+D+S:A+D+S+rlen] = np.linspace(s, 0, rlen)
    if n > A + D + S + R:
        env[A+D+S+R:] = 0
    return env

# Lead: punchy square, 0.5s total
def gen_lead():
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    f = 523.25
    vib = 1 + 0.004*np.sin(2*np.pi*5.5*t)
    inst = np.zeros(n)
    phase = 0.0
    for i in range(n):
        phase += 2*np.pi*(f * vib[i]) / SR
        sq = np.sign(np.sin(phase))
        sw = 2*(phase/(2*np.pi) - np.floor(0.5+phase/(2*np.pi)))
        inst[i] = 0.55*sq + 0.18*sw
    inst = inst / np.max(np.abs(inst)) * 0.55
    env = envelope(n, a=0.004, d=0.04, s=0.50, r=0.15)
    return inst * env

# Pluck: triangle, 0.4s
def gen_pluck():
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    f = 523.25
    tri = 2*np.abs(2*(t*f - np.floor(0.5 + t*f))) - 1
    harm = 0.3*np.sin(2*np.pi*2*f*t)
    inst = tri + harm
    inst = inst / np.max(np.abs(inst)) * 0.55
    env = envelope(n, a=0.002, d=0.10, s=0.30, r=0.15)
    return inst * env

# Pad: 1.5s total, smoother attack
def gen_pad():
    n = int(SR * 1.5)
    t = np.arange(n) / SR
    f = 261.63
    sw = 2*(t*f - np.floor(0.5 + t*f)) - 1
    sub = np.sin(2*np.pi*f*0.5*t)
    phase = (t*f*2) % 1
    sq2 = np.where(phase < 0.5, 1.0, -1.0)
    inst = 0.45*sw + 0.40*sub + 0.20*sq2
    inst = inst / np.max(np.abs(inst)) * 0.50
    env = envelope(n, a=0.08, d=0.12, s=0.80, r=0.35)
    return inst * env

# Bass: 0.4s total, snappy
def gen_bass():
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    f = 65.41
    phase = (t*f) % 1
    sq = np.where(phase < 0.5, 1.0, -1.0)
    sub = np.sin(2*np.pi*f*t)
    inst = 0.45*sq + 0.55*sub
    click = np.sign(np.sin(2*np.pi*2500*t)) * np.exp(-150*t) * 0.15
    inst = inst + click
    inst = inst / np.max(np.abs(inst)) * 0.65
    env = envelope(n, a=0.005, d=0.06, s=0.55, r=0.12)
    return inst * env

# Kick (same)
def gen_kick():
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f_env = 130 * np.exp(-25*t) + 50
    phase = 2*np.pi*np.cumsum(f_env)/SR
    body = np.sin(phase)
    click = np.sign(np.sin(2*np.pi*2500*t)) * np.exp(-200*t)
    inst = 0.85*body + 0.20*click
    env = np.exp(-4*t)
    out = inst * env
    out = out / np.max(np.abs(out)) * 0.85
    return out

# Snare (same)
def gen_snare():
    n = int(SR * 0.20)
    t = np.arange(n) / SR
    np.random.seed(42)
    noise = np.random.uniform(-1, 1, n)
    body = 0.25*np.sin(2*np.pi*200*t)*np.exp(-12*t)
    out = noise * np.exp(-10*t) + body
    out = out / np.max(np.abs(out)) * 0.7
    return out

# Closed hat
def gen_chat():
    n = int(SR * 0.04)
    t = np.arange(n) / SR
    np.random.seed(123)
    noise = np.random.uniform(-1, 1, n)
    out = noise * np.exp(-90*t)
    out = out / np.max(np.abs(out)) * 0.45
    return out

# Open hat
def gen_ohat():
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    np.random.seed(456)
    noise = np.random.uniform(-1, 1, n)
    out = noise * np.exp(-7*t)
    out = out / np.max(np.abs(out)) * 0.40
    return out

# Crash
def gen_crash():
    n = int(SR * 0.8)
    t = np.arange(n) / SR
    np.random.seed(789)
    noise = np.random.uniform(-1, 1, n)
    hp = np.diff(noise, prepend=noise[0])
    out = hp * np.exp(-2.5*t) * 0.3 + noise * np.exp(-1.5*t) * 0.05
    out = out / np.max(np.abs(out)) * 0.5
    return out

# Tom
def gen_tom():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f_env = 180 * np.exp(-4*t) + 80
    phase = 2*np.pi*np.cumsum(f_env)/SR
    body = np.sin(phase)
    env = np.exp(-3.5*t)
    out = body * env
    out = out / np.max(np.abs(out)) * 0.6
    return out

# Organ: short stab
def gen_organ():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f = 261.63
    s = (np.sin(2*np.pi*f*t) + 0.4*np.sin(2*np.pi*2*f*t) + 0.25*np.sin(2*np.pi*3*f*t) + 0.15*np.sin(2*np.pi*4*f*t))
    s = s / np.max(np.abs(s)) * 0.50
    env = envelope(n, a=0.005, d=0.10, s=0.45, r=0.15)
    return s * env

# Arp: short pluck
def gen_arp():
    n = int(SR * 0.2)
    t = np.arange(n) / SR
    f = 523.25
    tri = 2*np.abs(2*(t*f - np.floor(0.5 + t*f))) - 1
    harm = 0.35*np.sin(2*np.pi*2*f*t)
    inst = tri + harm
    inst = inst / np.max(np.abs(inst)) * 0.50
    env = envelope(n, a=0.002, d=0.08, s=0.20, r=0.08)
    return inst * env

samples = {
    'lead':   gen_lead(),
    'pluck':  gen_pluck(),
    'pad':    gen_pad(),
    'bass':   gen_bass(),
    'kick':   gen_kick(),
    'snare':  gen_snare(),
    'chat':   gen_chat(),
    'ohat':   gen_ohat(),
    'crash':  gen_crash(),
    'tom':    gen_tom(),
    'organ':  gen_organ(),
    'arp':    gen_arp(),
}

for name, s in samples.items():
    save_wav(name, s)
    print(f"Wrote {name}: {len(s)} samples, dc={np.mean(s):.3f}")
