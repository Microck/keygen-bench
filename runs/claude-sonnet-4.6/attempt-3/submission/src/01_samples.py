#!/usr/bin/env python3
"""Regenerate all samples with DC = 0 and correct peak levels"""
import numpy as np, wave

SR = 44100
np.random.seed(0xBEEF)
P = 168

def save_wav(path, data):
    d = np.clip(data, -1.0, 1.0)
    i = (d * 32767).astype(np.int16)
    with wave.open(path, 'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(i.tobytes())

def dc_free(x):
    return x - np.mean(x)

def norm(x, peak=0.90):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x

# 1. SQUARE LEAD — symmetric by construction
sq = np.zeros(P)
sq[:P//2] = 0.72; sq[P//2:] = -0.72
# DC = 0 already (symmetric 50% duty)
save_wav('/workspace/src/01_lead_square.wav', sq)

# 2. SAW ARP — add DC correction
t_a = np.arange(P) / P
saw_arp = np.linspace(-0.70, 0.70, P, endpoint=False)
saw_arp += np.sin(2*np.pi*t_a) * 0.06
saw_arp = dc_free(saw_arp)
saw_arp *= 0.70 / np.max(np.abs(saw_arp))
save_wav('/workspace/src/02_saw_arp.wav', saw_arp)

# 3. SAW BASS — bandlimited (sum of sines = zero DC by definition)
t_b = np.linspace(0, 2*np.pi, P, endpoint=False)
saw_bass = sum((-1)**(n+1) * np.sin(n*t_b)/n for n in range(1, 9))
saw_bass = dc_free(saw_bass) * (2/np.pi) * 0.75
save_wav('/workspace/src/03_saw_bass.wav', saw_bass)

# 4. PULSE 25% — DC-corrected asymmetric pulse
#    Want mean=0: if high=H, low=L, duty=0.25 → 0.25H + 0.75L = 0 → H = -3L
#    Use L=-0.30, H=0.90
pulse = np.full(P, -0.30)
pulse[:P//4] = 0.90
save_wav('/workspace/src/04_pulse.wav', pulse)

# 5. PAD — detuned triple saw, DC-correct
P2 = 174
sa = np.linspace(-1, 1, P,  endpoint=False)
sb = np.interp(np.linspace(0, P2-1, P), np.arange(P2),
               np.linspace(-1, 1, P2, endpoint=False))
sc = np.roll(sa, P//3)
pad = (sa + sb + sc*0.5) * 0.20
pad = dc_free(pad)
save_wav('/workspace/src/05_pad.wav', pad)

# 6. HIHAT — filtered noise, DC-correct
n_hh = 600
noise = np.cumsum(np.random.choice([-1,1], n_hh).astype(float))
noise = dc_free(noise); noise /= np.max(np.abs(noise))
env = np.exp(-np.arange(n_hh) / 45.0)
hh = dc_free(noise * env) * 0.50
save_wav('/workspace/src/06_hihat.wav', hh)

# 7. KICK — sine sweep + click, DC-correct
n_k = 8820
f0, f1, tau_f = 200, 42, 800
f_k = f1 + (f0-f1)*np.exp(-np.arange(n_k)/tau_f)
ph_k = np.cumsum(f_k/SR) * 2*np.pi
body = np.sin(ph_k)*0.80 + np.sin(2*np.pi*40*np.arange(n_k)/SR)*0.20
amp  = np.exp(-np.arange(n_k)/1600.0)
click = np.zeros(n_k)
click[:80] = np.random.randn(80) * np.exp(-np.arange(80)/5.0) * 0.60
kick = body*amp + click
kick = dc_free(kick)
kick = norm(kick, 0.92)
save_wav('/workspace/src/07_kick.wav', kick)

# 8. SNARE — DC-correct and normalize below 1.0
n_sn = 5512
t_sn = np.arange(n_sn)/SR
noise = np.random.randn(n_sn)
body1 = np.sin(2*np.pi*180*t_sn)*0.35
body2 = np.sin(2*np.pi* 80*t_sn)*0.25
snare = (noise*0.60 + body1)*np.exp(-np.arange(n_sn)/380.0) + \
         body2 * np.exp(-np.arange(n_sn)/120.0)
snare = dc_free(snare)
snare = norm(snare, 0.90)
save_wav('/workspace/src/08_snare.wav', snare)

print("Fixed samples written. Verifying DC:")
import os
for fname in sorted(os.listdir('/workspace/src')):
    if fname.endswith('.wav') and fname[:2].isdigit():
        path = f'/workspace/src/{fname}'
        with wave.open(path) as f:
            raw = f.readframes(f.getnframes())
        d = np.frombuffer(raw, np.int16).astype(np.float32)/32768.0
        dc = np.mean(d); pk = np.max(np.abs(d))
        flag = ' *** DC!' if abs(dc)>0.005 else ''
        print(f"  {fname:30s}  DC={dc:+.6f}  Peak={pk:.4f}{flag}")
