#!/usr/bin/env python3
"""Generate all instrument samples for keygen tune 'Ghost Protocol'"""
import numpy as np
import wave, os

SR = 44100
os.makedirs('/workspace/samples', exist_ok=True)

def write_wav(path, data):
    arr = np.clip(data, -32768, 32767).astype(np.int16)
    with wave.open(path, 'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(arr.tobytes())

# Reference period: C-5 = 523.25 Hz → XM base note
C5_PERIOD = round(SR / 523.25)   # 84 samples

# ── Inst 1: Square lead ──────────────────────────────────────
sq = np.zeros(C5_PERIOD, dtype=np.float64)
sq[:C5_PERIOD//2] =  20000
sq[C5_PERIOD//2:] = -20000
write_wav('/workspace/samples/01_square_lead.wav', sq)

# ── Inst 2: Sawtooth arp (ascending saw, bright) ─────────────
saw = np.linspace(-18000, 18000, C5_PERIOD)
write_wav('/workspace/samples/02_saw_arp.wav', saw)

# ── Inst 3: Sine bass ─────────────────────────────────────────
t = np.linspace(0, 2*np.pi, C5_PERIOD, endpoint=False)
sine = 26000 * np.sin(t)
write_wav('/workspace/samples/03_sine_bass.wav', sine)

# ── Inst 4: Pulse arp (25% duty — nasal/buzzy) ───────────────
pulse = np.full(C5_PERIOD, -14000, dtype=np.float64)
pulse[:C5_PERIOD//4] = 14000
write_wav('/workspace/samples/04_pulse_arp.wav', pulse)

# ── Inst 5: Kick drum (sine sweep + thud) ────────────────────
kick_len = int(SR * 0.32)
t_k = np.arange(kick_len) / SR
freq_k = 160 * np.exp(-22*t_k) + 45
phase_k = np.cumsum(2*np.pi * freq_k / SR)
env_k  = np.exp(-18*t_k)
# small click at attack for definition
click = np.zeros(kick_len)
click[:12] = np.linspace(1, 0, 12)
kick = 30000*(np.sin(phase_k)*env_k + 0.25*click)
write_wav('/workspace/samples/05_kick.wav', kick)

# ── Inst 6: Snare (noise + body tone) ────────────────────────
snare_len = int(SR * 0.18)
t_s = np.arange(snare_len) / SR
rng = np.random.default_rng(42)
noise_s = rng.uniform(-1, 1, snare_len)
# body = mix of noise + 200 Hz snap
body  = 0.6*noise_s + 0.4*np.sin(2*np.pi*210*t_s)
env_s = np.exp(-28*t_s)
snare = 28000 * body * env_s
write_wav('/workspace/samples/06_snare.wav', snare)

# ── Inst 7: Closed hi-hat ─────────────────────────────────────
hh_len = int(SR * 0.045)
t_h = np.arange(hh_len) / SR
rng2 = np.random.default_rng(100)
noise_h = rng2.uniform(-1, 1, hh_len)
# band-pass-ish: multiply noise by high-freq oscillation
noise_h *= np.sin(2*np.pi*8000*t_h)**2
env_h  = np.exp(-100*t_h)
chhat  = 22000 * noise_h * env_h
write_wav('/workspace/samples/07_chhat.wav', chhat)

# ── Inst 8: Open hi-hat ───────────────────────────────────────
ohh_len = int(SR * 0.38)
t_o = np.arange(ohh_len) / SR
rng3 = np.random.default_rng(200)
noise_o = rng3.uniform(-1, 1, ohh_len)
noise_o *= np.sin(2*np.pi*7000*t_o)**2
env_o  = np.exp(-9*t_o)
ohhat  = 18000 * noise_o * env_o
write_wav('/workspace/samples/08_ohhat.wav', ohhat)

# ── Inst 9: Chord pad (odd harmonics = warm square-ish) ───────
pad_len = C5_PERIOD * 4   # 4 cycles for smooth looping
t_p = np.linspace(0, 2*np.pi*4, pad_len, endpoint=False)
pad = np.zeros(pad_len)
for h, vol in [(1,1.0),(3,0.35),(5,0.18),(7,0.10)]:
    pad += vol * np.sin(h * t_p / 4)   # one period = pad_len
pad = (pad / np.max(np.abs(pad))) * 11000
write_wav('/workspace/samples/09_pad.wav', pad)

# ── Inst 10: FX blip (square burst for accent hits) ───────────
blip_period = round(SR / 880)   # A5 reference
blip_len = blip_period * 8      # 8 cycles only → short stab
blip = np.zeros(blip_len)
blip[:blip_len//2] =  16000
blip[blip_len//2:] = -16000
# shape with tiny decay
env_b = np.exp(-5 * np.arange(blip_len) / blip_len)
blip *= env_b
write_wav('/workspace/samples/10_blip.wav', blip)

print(f"All 10 samples generated. C5_PERIOD={C5_PERIOD}")
for f in sorted(os.listdir('/workspace/samples')):
    print(' ', f)
