"""
Generate instrument samples for our keygen tune.
Output: 16-bit mono WAV files at 22050 Hz.
"""
import numpy as np
import wave
import struct
import os

SR = 22050
OUT = '/workspace/work/samples'
os.makedirs(OUT, exist_ok=True)

def save_wav(name, samples, sr=SR):
    """Save float [-1, 1] samples as 16-bit mono WAV."""
    # Clip and convert to int16
    s = np.clip(np.asarray(samples, dtype=np.float64), -1.0, 1.0)
    s16 = (s * 32767.0).astype(np.int16)
    path = os.path.join(OUT, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(s16.tobytes())
    print(f"Wrote {name}: {len(s16)} samples")
    return path

def envelope(n, a=0.005, d=0.05, s=0.6, r=0.1, total=None):
    """ADSR envelope (in seconds)."""
    if total is None:
        total = n / SR
    A = int(a * SR); D = int(d * SR); R = int(r * SR)
    S = max(0, n - A - D - R)
    env = np.zeros(n)
    if A > 0:
        a_len = min(A, n)
        env[:a_len] = np.linspace(0, 1, a_len)
    if D > 0:
        d_len = min(D, max(0, n - A))
        env[A:A+d_len] = np.linspace(1, s, d_len)
    if S > 0:
        s_len = min(S, max(0, n - A - D))
        env[A+D:A+D+s_len] = s
    if R > 0:
        r_len = min(R, max(0, n - A - D - S))
        if r_len > 0:
            env[A+D+S:A+D+S+r_len] = np.linspace(s, 0, r_len)
    # Last samples go to 0
    if n > A + D + S + R:
        env[A+D+S+R:] = 0
    return env

# ---------------- Lead (square + vibrato) ----------------
def gen_lead():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    # C5 fundamental
    f = 523.25
    # square wave + slight detune saw
    sq = np.sign(np.sin(2*np.pi*f*t))
    sw = 2*(t*f - np.floor(0.5 + t*f))
    vib = 1 + 0.005*np.sin(2*np.pi*5.5*t)
    wave_data = 0.55*sq + 0.25*sw
    # slight pitch sweep at start (plucky)
    pitch_env = np.ones(n)
    pitch_env[:int(0.005*SR)] = np.linspace(1.02, 1.0, int(0.005*SR))
    # phase-modulate using a slowly-changing pitch
    inst = np.zeros(n)
    phase = 0.0
    for i in range(n):
        phase += 2*np.pi*(f * pitch_env[i] * vib[i]) / SR
        inst[i] = 0.55*np.sign(np.sin(phase)) + 0.25*(2*(phase/(2*np.pi) - np.floor(0.5+phase/(2*np.pi))))
    inst = inst / np.max(np.abs(inst)) * 0.6
    env = envelope(n, a=0.005, d=0.05, s=0.55, r=0.4)
    out = inst * env
    return out

# ---------------- Pluck (bright triangle) ----------------
def gen_pluck():
    n = int(SR * 0.8)
    t = np.arange(n) / SR
    f = 523.25
    # triangle
    tri = 2*np.abs(2*(t*f - np.floor(0.5 + t*f))) - 1
    # add some harmonic for sparkle
    harm = 0.3*np.sin(2*np.pi*2*f*t) * np.exp(-3*t)
    inst = tri + harm
    inst = inst / np.max(np.abs(inst)) * 0.55
    env = envelope(n, a=0.002, d=0.10, s=0.4, r=0.3)
    out = inst * env
    return out

# ---------------- Soft pad ----------------
def gen_pad():
    n = int(SR * 2.0)
    t = np.arange(n) / SR
    f = 261.63  # C4
    # saw
    sw = 2*(t*f - np.floor(0.5 + t*f))
    # sub
    sub = np.sin(2*np.pi*f*0.5*t)
    # soft square at 2x
    sq = 0.3*np.sign(np.sin(2*np.pi*f*2*t))
    inst = 0.4*sw - 0.2 + 0.4*sub + sq  # center around 0
    inst = inst / np.max(np.abs(inst)) * 0.5
    env = envelope(n, a=0.08, d=0.20, s=0.85, r=0.4)
    out = inst * env
    return out

# ---------------- Bass (deep sub square) ----------------
def gen_bass():
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    f = 65.41  # C2
    # Pulse wave with slight detune
    sq = np.sign(np.sin(2*np.pi*f*t))
    sub = np.sin(2*np.pi*f*t)
    inst = 0.6*sq + 0.5*sub
    # High-freq content gets filtered with decay
    click = np.exp(-100*t)*np.sin(2*np.pi*2000*t)*0.2
    inst = inst + click
    inst = inst / np.max(np.abs(inst)) * 0.6
    env = envelope(n, a=0.005, d=0.10, s=0.7, r=0.15)
    out = inst * env
    return out

# ---------------- Kick ----------------
def gen_kick():
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    # Pitch envelope: starts high, drops fast
    f_env = 150 * np.exp(-30*t) + 45
    phase = 2*np.pi*np.cumsum(f_env)/SR
    body = np.sin(phase)
    # Click transient
    click = np.sign(np.sin(2*np.pi*2500*t)) * np.exp(-200*t)
    inst = body + 0.15*click
    env = np.exp(-3.5*t)
    out = inst * env
    out = out / np.max(np.abs(out)) * 0.85
    return out

# ---------------- Snare ----------------
def gen_snare():
    n = int(SR * 0.25)
    t = np.arange(n) / SR
    np.random.seed(42)
    noise = np.random.uniform(-1, 1, n)
    body = 0.3*np.sin(2*np.pi*200*t)*np.exp(-15*t)
    out = noise * np.exp(-12*t) + body
    out = out / np.max(np.abs(out)) * 0.7
    return out

# ---------------- Closed Hat ----------------
def gen_chat():
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    np.random.seed(123)
    noise = np.random.uniform(-1, 1, n)
    # High-pass-ish via subtracting mean over short window
    out = noise * np.exp(-90*t)
    out = out / np.max(np.abs(out)) * 0.4
    return out

# ---------------- Open Hat ----------------
def gen_ohat():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    np.random.seed(456)
    noise = np.random.uniform(-1, 1, n)
    out = noise * np.exp(-7*t)
    out = out / np.max(np.abs(out)) * 0.4
    return out

# ---------------- Crash ----------------
def gen_crash():
    n = int(SR * 1.0)
    t = np.arange(n) / SR
    np.random.seed(789)
    noise = np.random.uniform(-1, 1, n)
    # Band-pass-ish noise: subtract low-pass component
    # simple high-pass via diff
    hp = np.diff(noise, prepend=noise[0])
    out = hp * np.exp(-2.5*t) * 0.3 + noise * np.exp(-1.5*t) * 0.05
    out = out / np.max(np.abs(out)) * 0.5
    return out

# ---------------- Tom ----------------
def gen_tom():
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    f_env = 200 * np.exp(-5*t) + 80
    phase = 2*np.pi*np.cumsum(f_env)/SR
    body = np.sin(phase)
    inst = body
    env = np.exp(-3*t)
    out = inst * env
    out = out / np.max(np.abs(out)) * 0.6
    return out

# ---------------- Organ (staccato chord stab) ----------------
def gen_organ():
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    f = 261.63
    # multiple sine partials
    s = (np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*2*f*t) + 0.3*np.sin(2*np.pi*3*f*t) + 0.2*np.sin(2*np.pi*4*f*t))
    s = s / np.max(np.abs(s)) * 0.55
    env = envelope(n, a=0.005, d=0.20, s=0.5, r=0.2)
    out = s * env
    return out

# ---------------- Pluck arp ----------------
def gen_arp():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f = 523.25
    # Short triangle pluck
    tri = 2*np.abs(2*(t*f - np.floor(0.5 + t*f))) - 1
    harm = 0.4*np.sin(2*np.pi*2*f*t)
    inst = tri + harm
    inst = inst / np.max(np.abs(inst)) * 0.5
    env = envelope(n, a=0.002, d=0.15, s=0.3, r=0.1)
    out = inst * env
    return out

# Generate all
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

print("\nAll samples generated.")
