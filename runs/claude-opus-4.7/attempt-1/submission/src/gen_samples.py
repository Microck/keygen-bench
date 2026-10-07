"""Final sample generation with DC removal and smooth zero-start."""
import numpy as np, wave

BASE = 8363
OUT = "/workspace/samples"
N = 256  # Use 256-sample cycles for pitched (reduced noise, same pitch)

def save_wav(path, data, sr):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())

def remove_dc(y):
    return y - np.mean(y)

def normalize(y, target=0.88):
    peak = np.max(np.abs(y))
    if peak > 0: y = y / peak * target
    return y

# ---- Pitched single-cycle waves (N samples at BASE Hz) ----
# All built from sine series so DC=0 and start=0.
# Native freq = BASE/N = 8363/256 = 32.67 Hz (C-1), playing C-4 = 261Hz. ✓

def sine():
    x = np.arange(N) / N
    return np.sin(2*np.pi*x)

def harmonic_series(amps):
    """Build waveform from harmonic amplitudes.
    amps[k] = amplitude for harmonic k+1 (so amps[0] is fundamental).
    All sines so starts at 0 and DC=0."""
    x = np.arange(N) / N
    y = np.zeros(N)
    for k, a in enumerate(amps, start=1):
        y += a * np.sin(2*np.pi*k*x)
    return y

# Bass: saw-ish (1/k harmonics, up to k=15)
bass = harmonic_series([1/k for k in range(1, 16)])
bass = normalize(np.tanh(bass * 1.4), target=0.82)  # soft saturate for warmth

# Lead: pulse-ish (odd harmonics with decreasing amp, like 30% pulse)
# Pulse of duty d has fourier: a_k = 2/pi * sin(pi*k*d)/k, cosine terms
# Here using sines for zero-start, approximating "pulse" shape via harmonic blend
def pulse_from_sine(duty, n_harm=20):
    # Build pulse using cosine series which is DC-centered
    # Shift to start at 0 by using sine basis with proper phase
    x = np.arange(N) / N
    y = np.zeros(N)
    for k in range(1, n_harm+1):
        ak = (2/(np.pi*k)) * np.sin(np.pi*k*duty)
        # cosine term with proper phase to start at 0 with upward slope
        y += ak * np.sin(2*np.pi*k*x)
    return y

lead = pulse_from_sine(0.30, 20)
lead = normalize(lead, target=0.85)

arp = pulse_from_sine(0.125, 25)
arp = normalize(arp, target=0.82)

# Pluck: fundamental + 2nd + 3rd + small 4th
pluck = harmonic_series([1.0, 0.5, 0.3, 0.15, 0.05])
pluck = normalize(pluck, target=0.80)

# Sub: pure sine
sub = sine() * 0.92

# Pad: longer, multiple voices with slight detune for warm width
def pad():
    Np = 2048  # longer loop for smoother sustain
    x = np.arange(Np) / Np
    y = np.zeros(Np)
    # Main voice
    for k in [1,2,3,4,5]:
        y += (1.0/k) * np.sin(2*np.pi*k*x)
    # Octave up detuned
    for k in [1,2,3]:
        y += (0.4/k) * np.sin(2*np.pi*k*2.005*x)
    # Octave down 
    for k in [1,2]:
        y += (0.5/k) * np.sin(2*np.pi*k*0.5*x)
    y = remove_dc(y)
    y = normalize(y, target=0.70)
    return y

# Save all
save_wav(f"{OUT}/bass.wav", bass, BASE)
save_wav(f"{OUT}/lead.wav", lead, BASE)
save_wav(f"{OUT}/arp.wav", arp, BASE)
save_wav(f"{OUT}/pluck.wav", pluck, BASE)
save_wav(f"{OUT}/sub.wav", sub, BASE)
save_wav(f"{OUT}/pad.wav", pad(), BASE)

# Verify
for name in ['bass','lead','arp','pluck','sub','pad']:
    import os
    f = f"{OUT}/{name}.wav"
    with wave.open(f) as w:
        d = w.readframes(w.getnframes())
    x = np.frombuffer(d, dtype=np.int16).astype(np.float32)/32768
    print(f"{name}: n={len(x)}  first={x[0]:+.3f}  last={x[-1]:+.3f}  dc={np.mean(x):+.4f}  peak={np.max(np.abs(x)):.3f}")

print("\nDrums unchanged.")
