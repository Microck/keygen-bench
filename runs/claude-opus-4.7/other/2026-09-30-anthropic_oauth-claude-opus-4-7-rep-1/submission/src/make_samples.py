import numpy as np
import os, struct, wave

os.makedirs('/workspace/samples', exist_ok=True)
SR = 22050  # sample rate for our source samples; XM will pitch-shift

def save_wav(path, data, sr=SR):
    data = np.clip(data, -1, 1)
    d16 = (data * 32000).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(d16.tobytes())

# ---- Helper: single-cycle waveforms for looped instruments ----
# We'll create looped waveforms so notes can hold at any length.

def cycle_saw(length=256):
    x = np.linspace(-1, 1, length, endpoint=False)
    return x

def cycle_square(length=256, duty=0.5):
    x = np.linspace(0, 1, length, endpoint=False)
    return np.where(x < duty, 1.0, -1.0)

def cycle_tri(length=256):
    x = np.linspace(0, 1, length, endpoint=False)
    return 2*np.abs(2*(x - np.floor(x+0.5))) - 1

def cycle_pulse25(length=256):
    return cycle_square(length, 0.25)

# For pitched samples in FT2, base rate matters. Use single-cycle at ~C-4.
# XM's C-4 with a sample loop of 1 cycle = frequency depends on sample rate and length.
# Rate 8363 Hz at C-4 is Amiga standard. C-4 = ~261.6 Hz. So one cycle at 261.6 Hz needs 8363/261.6 ≈ 31.97 samples.
# We'll use 32 samples/cycle at 8363 Hz base rate.

BASE_SR = 8363

def one_cycle_saw():
    L = 32
    return cycle_saw(L), L

def one_cycle_square():
    L = 32
    return cycle_square(L, 0.5), L

def one_cycle_pulse25():
    L = 32
    return cycle_pulse25(L), L

def one_cycle_tri():
    L = 32
    return cycle_tri(L), L

# Slightly wavetable-ish: a saw with a soft filter
def one_cycle_soft_saw():
    L = 64
    x = np.linspace(-1,1,L,endpoint=False)
    # low-pass by weighted average
    y = 0.6*x + 0.3*np.sin(np.linspace(0,2*np.pi,L,endpoint=False))
    y = y / np.max(np.abs(y))
    return y, L

# ---- Drums: one-shots ----
def kick():
    dur = 0.18
    n = int(SR*dur)
    t = np.arange(n)/SR
    # pitch drop
    f = 140*np.exp(-t*22) + 45
    phase = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(phase) * np.exp(-t*8)
    click = (np.random.rand(n)*2-1) * np.exp(-t*80) * 0.5
    y = body*0.9 + click*0.6
    # short attack fade in
    y[:20] *= np.linspace(0,1,20)
    return y / np.max(np.abs(y)) * 0.95

def snare():
    dur = 0.16
    n = int(SR*dur)
    t = np.arange(n)/SR
    noise = (np.random.rand(n)*2-1)
    env = np.exp(-t*22)
    tone = np.sin(2*np.pi*220*t)*np.exp(-t*30)*0.4
    y = noise*env*0.9 + tone
    return y / np.max(np.abs(y)) * 0.9

def hat(closed=True):
    dur = 0.05 if closed else 0.18
    n = int(SR*dur)
    t = np.arange(n)/SR
    noise = (np.random.rand(n)*2-1)
    # bandpass-ish by differencing
    noise = np.diff(np.concatenate([[0],noise]))
    env = np.exp(-t*(50 if closed else 12))
    y = noise*env
    return y / np.max(np.abs(y)) * 0.7

def clap():
    dur = 0.14
    n = int(SR*dur)
    t = np.arange(n)/SR
    noise = (np.random.rand(n)*2-1)
    # multi-hit
    env = np.zeros(n)
    for hit_t, amp in [(0.0,1.0),(0.012,0.9),(0.024,0.9),(0.038,1.0)]:
        idx = int(hit_t*SR)
        env[idx:] += amp*np.exp(-(np.arange(n-idx))/SR*40)
    env *= np.exp(-t*6)
    y = noise*env
    return y / np.max(np.abs(y)) * 0.85

# --- FM-ish bass one-shot loop ---
def bass_cycle():
    # A short looped waveform that's punchy
    L = 64
    t = np.linspace(0, 1, L, endpoint=False)
    y = np.sin(2*np.pi*t) + 0.5*np.sin(2*np.pi*2*t + 0.3) + 0.2*np.sin(2*np.pi*3*t)
    y = np.tanh(y*1.5)
    y = y / np.max(np.abs(y))
    return y, L

# --- Pad-ish cycle ---
def pad_cycle():
    L = 128
    t = np.linspace(0, 1, L, endpoint=False)
    y = (np.sin(2*np.pi*t) + 0.6*np.sin(2*np.pi*2*t + 0.1) 
         + 0.4*np.sin(2*np.pi*3*t + 0.3) + 0.3*np.sin(2*np.pi*5*t))
    y = y / np.max(np.abs(y))
    return y, L

# Save everything
saw, saw_len = one_cycle_saw()
sqr, sqr_len = one_cycle_square()
pul, pul_len = one_cycle_pulse25()
tri, tri_len = one_cycle_tri()
soft, soft_len = one_cycle_soft_saw()
bcyc, bcyc_len = bass_cycle()
pcyc, pcyc_len = pad_cycle()

# Save single-cycles at BASE_SR
def save_cycle(path, cyc, sr=BASE_SR):
    # save just one cycle; loop_start=0, loop_length=len
    save_wav(path, cyc, sr=sr)

save_cycle('/workspace/samples/saw.wav', saw)
save_cycle('/workspace/samples/square.wav', sqr)
save_cycle('/workspace/samples/pulse25.wav', pul)
save_cycle('/workspace/samples/tri.wav', tri)
save_cycle('/workspace/samples/softsaw.wav', soft)
save_cycle('/workspace/samples/bass.wav', bcyc)
save_cycle('/workspace/samples/pad.wav', pcyc)

# Drums saved at SR
save_wav('/workspace/samples/kick.wav', kick())
save_wav('/workspace/samples/snare.wav', snare())
save_wav('/workspace/samples/hat_c.wav', hat(True))
save_wav('/workspace/samples/hat_o.wav', hat(False))
save_wav('/workspace/samples/clap.wav', clap())

print("saw cycle len:", saw_len)
print("Saved all samples.")
