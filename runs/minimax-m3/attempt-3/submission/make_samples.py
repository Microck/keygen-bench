"""Generate samples v3 - with bass loop and cleaner sounds."""
import numpy as np
import wave
import os

SR = 44100

def save_wav(path, samples, sr=SR):
    s = np.clip(samples, -1.0, 1.0)
    s16 = (s * 32767.0).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(s16.tobytes())

def hp_noise(n, alpha=0.3, seed=0):
    np.random.seed(seed)
    noise = np.random.randn(n)
    out = np.zeros(n)
    out[0] = noise[0]
    for i in range(1, n):
        out[i] = alpha * (out[i-1] + noise[i] - noise[i-1])
    return out

def make_saw_at(freq, n, sr=SR):
    t = np.arange(n) / sr
    saw = 2 * (t * freq - np.floor(0.5 + t * freq))
    return saw

def make_lead(dur_total=1.4, freq=220, sr=SR):
    n_attack = int(0.02 * sr)
    n_release = int(0.15 * sr)
    n_loop = int(round(1.0 * freq * sr / freq))  # freq cycles
    n = n_attack + n_loop + n_release
    
    t = np.arange(n) / sr
    saw = make_saw_at(freq, n, sr)
    pulse = np.where(np.sin(2*np.pi*freq*t) > 0, 1.0, -1.0) * 0.2
    sig = saw * 0.6 + pulse
    
    env = np.ones(n)
    env[:n_attack] = np.linspace(0, 0.7, n_attack)
    env[n_attack:n_attack+n_loop] = 0.7
    env[n_attack+n_loop:] = np.linspace(0.7, 0, n_release)
    
    sig = sig * env * 0.6
    sig = np.tanh(sig * 1.0)
    return sig, n_attack, n_loop, n_release

def make_pad(dur_total=3.0, freq=110, sr=SR):
    n_attack = int(0.1 * sr)
    n_release = int(0.3 * sr)
    n_loop_cycles = int(round(2.0 * freq))
    n_loop = int(round(n_loop_cycles * sr / freq))
    n = n_attack + n_loop + n_release
    
    t = np.arange(n) / sr
    sig = (np.sin(2*np.pi*freq*t) * 0.6 +
           np.sin(2*np.pi*freq*2*t) * 0.2 +
           np.sin(2*np.pi*freq*3*t) * 0.1)
    env = np.ones(n)
    env[:n_attack] = (np.linspace(0, 1, n_attack) ** 0.5) * 0.7
    env[n_attack:n_attack+n_loop] = 0.7
    env[n_attack+n_loop:] = np.linspace(0.7, 0, n_release)
    sig = sig * env * 0.35
    return sig, n_attack, n_loop, n_release

def make_bass(dur=0.5, freq=110, sr=SR):
    """Bass with loop - sustained bass note."""
    n_attack = int(0.005 * sr)
    n_release = int(0.05 * sr)
    # Loop length: 1 second for cleanness
    n_loop = int(round(1.0 * freq * sr / freq))  # freq cycles
    n = n_attack + n_loop + n_release
    
    t = np.arange(n) / sr
    saw = make_saw_at(freq, n, sr)
    # No sub - just saw for clean loop
    sig = saw * 0.7
    
    # Envelope
    env = np.ones(n)
    env[:n_attack] = np.linspace(0, 0.5, n_attack)
    env[n_attack:n_attack+n_loop] = 0.5
    env[n_attack+n_loop:] = np.linspace(0.5, 0, n_release)
    
    sig = sig * env
    sig = np.tanh(sig * 1.2)
    return sig, n_attack, n_loop, n_release

def make_pluck(dur=0.4, freq=220, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    saw = make_saw_at(freq, n, sr)
    sig = saw
    env = np.exp(-t * 8.0)
    sig = sig * env * 0.6
    return sig, 0, 0, 0

# Use integer Hz for cleanest loops
LEAD_FREQ = 220
PLUCK_FREQ = 220
PAD_FREQ = 110
BASS_FREQ = 110

samples_dir = '/workspace/work/samples'
os.makedirs(samples_dir, exist_ok=True)

print("Generating samples...")

s, na, nl, nr = make_lead(freq=LEAD_FREQ)
save_wav(f'{samples_dir}/lead.wav', s)
print(f"lead: {len(s)} samples, loop {na}-{na+nl}, total {len(s)/SR:.3f}s")

s, na, nl, nr = make_pad(freq=PAD_FREQ)
save_wav(f'{samples_dir}/pad.wav', s)
print(f"pad: {len(s)} samples, loop {na}-{na+nl}, total {len(s)/SR:.3f}s")

s, na, nl, nr = make_bass(freq=BASS_FREQ)
save_wav(f'{samples_dir}/bass.wav', s)
print(f"bass: {len(s)} samples, loop {na}-{na+nl}, total {len(s)/SR:.3f}s")

s, _, _, _ = make_pluck(freq=PLUCK_FREQ)
save_wav(f'{samples_dir}/pluck.wav', s)
print(f"pluck: {len(s)} samples, no loop, total {len(s)/SR:.3f}s")

def make_kick(dur=0.3, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    pitch_env = np.exp(-t*30) * 60 + 35
    phase = 2*np.pi * np.cumsum(pitch_env) / sr
    sig = np.sin(phase)
    amp_env = np.exp(-t*8)
    sig = sig * amp_env
    click = hp_noise(n, alpha=0.5, seed=1) * np.exp(-t*100) * 0.4
    sig = sig + click
    sig = np.tanh(sig * 1.5)
    return sig

def make_snare(dur=0.2, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    hp = hp_noise(n, alpha=0.2, seed=42)
    tone = np.sin(2*np.pi*200*t)
    sig = hp * 0.5 + tone * 0.3
    env = np.exp(-t * 18.0)
    sig = sig * env
    sig = np.tanh(sig * 1.3)
    return sig

def make_hat_closed(dur=0.08, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    hp = hp_noise(n, alpha=0.4, seed=7)
    env = np.exp(-t * 80.0)
    sig = hp * env * 0.5
    return sig

def make_hat_open(dur=0.3, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    hp = hp_noise(n, alpha=0.3, seed=11)
    env = np.exp(-t * 12.0)
    sig = hp * env * 0.5
    return sig

def make_tom(dur=0.3, freq=180, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    pitch_env = np.exp(-t*15) * (freq-80) + 80
    phase = 2*np.pi * np.cumsum(pitch_env) / sr
    sig = np.sin(phase)
    env = np.exp(-t*10)
    sig = sig * env * 0.7
    return sig

def make_fx(dur=0.4, freq=220, sr=SR):
    n = int(dur * sr)
    t = np.arange(n) / sr
    sig = (np.sin(2*np.pi*freq*t) + np.sin(2*np.pi*freq*1.5*t)*0.5)
    env = np.exp(-t * 6.0)
    sig = sig * env * 0.5
    return sig

save_wav(f'{samples_dir}/kick.wav', make_kick())
save_wav(f'{samples_dir}/snare.wav', make_snare())
save_wav(f'{samples_dir}/hatc.wav', make_hat_closed())
save_wav(f'{samples_dir}/hato.wav', make_hat_open())
save_wav(f'{samples_dir}/tom.wav', make_tom())
save_wav(f'{samples_dir}/fx.wav', make_fx())

# Verify bass loop
s, na, nl, nr = make_bass(freq=BASS_FREQ)
print(f"\nBass loop check:")
loop_start = na
loop_end = na + nl
print(f"  Loop start ({loop_start}): {s[loop_start]:.4f}")
print(f"  Loop end ({loop_end}): {s[loop_end]:.4f}")
print(f"  Difference: {s[loop_start] - s[loop_end]:.4f}")

print("\nDone")
