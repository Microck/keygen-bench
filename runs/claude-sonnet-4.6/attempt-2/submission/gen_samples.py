"""
Generate PCM samples for keygen tune "SERIAL CRACK"
All samples tuned to C-4 at 8363 Hz (FT2 standard).
"""
import numpy as np
import base64, json, sys

RATE = 8363  # FT2 C-4 sample rate

def b64(arr):
    arr = np.clip(arr, -1.0, 1.0)
    return base64.b64encode((arr * 32767).astype(np.int16).tobytes()).decode()

# ── 1. LEAD SYNTH ─── bandlimited sawtooth ─────────────────────────────────
def make_lead():
    period = 32                     # samples/cycle at C-4 (8363/32 ≈ 261 Hz)
    atk  = period * 2               # 64-sample attack ramp
    loop = period * 4               # 128-sample sustain loop
    total = atk + loop
    t = np.arange(total, dtype=float)
    wave = np.zeros(total)
    for h in range(1, 14):          # bandlimited saw
        wave += ((-1)**(h+1) / h) * np.sin(2*np.pi*h*t/period)
    wave /= np.max(np.abs(wave)); wave *= 0.82
    env = np.ones(total)
    env[:atk] = np.linspace(0, 1, atk)**0.5
    return b64(wave*env), atk, loop

# ── 2. BASS SYNTH ─── thick square wave ────────────────────────────────────
def make_bass():
    period = 64                     # lower period → deeper sound
    atk  = period
    loop = period * 4
    total = atk + loop
    t = np.arange(total, dtype=float)
    phase = (t % period) / period
    wave = np.where(phase < 0.5, 0.82, -0.82)
    env = np.ones(total)
    env[:atk] = np.linspace(0, 1, atk)**0.3
    return b64(wave*env), atk, loop

# ── 3. ARP SYNTH ─── thin pulse (25% duty) ─────────────────────────────────
def make_arp():
    period = 32
    atk  = 6
    loop = period * 4
    total = atk + loop
    t = np.arange(total, dtype=float)
    phase = (t % period) / period
    wave = np.where(phase < 0.25, 1.0, -1.0/3.0)
    wave -= np.mean(wave)
    wave /= np.max(np.abs(wave)); wave *= 0.78
    env = np.ones(total)
    env[:atk] = np.linspace(0, 1, atk)**0.4
    return b64(wave*env), atk, loop

# ── 4. PAD ─── 3 detuned sawtooths (lush chord layer) ──────────────────────
def make_pad():
    period = 32
    atk  = period * 8               # long, slow swell
    loop = period * 8
    total = atk + loop
    t = np.arange(total, dtype=float)
    wave = np.zeros(total)
    for det, vol in [(1.0, 0.45), (1.009, 0.30), (0.991, 0.30)]:
        p = period * det
        ph = (t % p) / p
        wave += (2*ph - 1) * vol
    wave /= np.max(np.abs(wave)); wave *= 0.60
    env = np.ones(total)
    env[:atk] = np.linspace(0, 1, atk)**2.2   # slow attack
    return b64(wave*env), atk, loop

# ── 5. KICK ─── sine pitch-sweep ───────────────────────────────────────────
def make_kick():
    dur = 0.19; n = int(dur * RATE)
    t = np.arange(n) / RATE
    freq = 125.0 * (38.0/125.0)**(t/dur)
    phase = 2*np.pi * np.cumsum(freq) / RATE
    env = np.exp(-5.5 * t / dur)
    click_n = int(0.005*RATE)
    click = np.zeros(n); click[:click_n] = np.linspace(0.45, 0, click_n)
    wave = np.sin(phase)*env*0.95 + click
    return b64(np.clip(wave, -1, 1))

# ── 6. SNARE ─── noise + body tone ─────────────────────────────────────────
def make_snare():
    dur = 0.09; n = int(dur * RATE)
    t = np.arange(n) / RATE
    rng = np.random.default_rng(42)
    noise = rng.standard_normal(n)
    noise /= np.max(np.abs(noise))
    tone = np.sin(2*np.pi*210*t)
    wave = noise * np.exp(-14*t/dur)*0.65 + tone * np.exp(-22*t/dur)*0.35
    return b64(np.clip(wave, -1, 1))

# ── 7. HIHAT ─── HPF noise burst ───────────────────────────────────────────
def make_hihat():
    dur = 0.038; n = int(dur * RATE)
    t = np.arange(n) / RATE
    rng = np.random.default_rng(77)
    noise = rng.standard_normal(n)
    # simple first-difference high-pass
    noise = np.diff(noise, prepend=noise[0])
    noise /= np.max(np.abs(noise))
    env = np.exp(-22*t/dur)
    return b64(np.clip(noise*env*0.62, -1, 1))

# ── 8. OPEN HIHAT ─── longer HPF noise ─────────────────────────────────────
def make_open_hat():
    dur = 0.09; n = int(dur * RATE)
    t = np.arange(n) / RATE
    rng = np.random.default_rng(55)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=noise[0])
    noise /= np.max(np.abs(noise))
    env = np.exp(-8*t/dur)
    return b64(np.clip(noise*env*0.55, -1, 1))

# ─── Collect ────────────────────────────────────────────────────────────────
results = {}

lead_pcm,  lead_ls,  lead_ll  = make_lead()
bass_pcm,  bass_ls,  bass_ll  = make_bass()
arp_pcm,   arp_ls,   arp_ll   = make_arp()
pad_pcm,   pad_ls,   pad_ll   = make_pad()
kick_pcm                       = make_kick()
snare_pcm                      = make_snare()
hat_pcm                        = make_hihat()
ohat_pcm                       = make_open_hat()

results = {
    'lead':  {'pcm': lead_pcm,  'ls': lead_ls,  'll': lead_ll },
    'bass':  {'pcm': bass_pcm,  'ls': bass_ls,  'll': bass_ll },
    'arp':   {'pcm': arp_pcm,   'ls': arp_ls,   'll': arp_ll  },
    'pad':   {'pcm': pad_pcm,   'ls': pad_ls,   'll': pad_ll  },
    'kick':  {'pcm': kick_pcm,  'ls': 0,        'll': 0       },
    'snare': {'pcm': snare_pcm, 'ls': 0,        'll': 0       },
    'hat':   {'pcm': hat_pcm,   'ls': 0,        'll': 0       },
    'ohat':  {'pcm': ohat_pcm,  'ls': 0,        'll': 0       },
}

# Print loop info for verification
for name, d in results.items():
    pcm_bytes = len(base64.b64decode(d['pcm']))
    print(f"{name:6s}: samples={pcm_bytes//2:5d}  loop_start={d['ls']:4d}  loop_len={d['ll']:4d}", file=sys.stderr)

json.dump(results, sys.stdout)
