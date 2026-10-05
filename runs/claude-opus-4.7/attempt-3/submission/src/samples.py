"""Generate samples for the keygen tune. All samples at 22050 Hz mono float32."""
import numpy as np
import base64

SR = 22050
REL_NOTE = 17   # 12*log2(22050/8363) ≈ 16.78
FINETUNE = -28  # fine shift to match exactly

C4 = 261.6256

def to_int16(x, headroom=0.95):
    x = np.asarray(x, dtype=np.float32)
    # Remove DC offset
    x = x - np.mean(x)
    peak = np.max(np.abs(x))
    if peak > 0:
        x = x / peak * headroom
    return (x * 32767).astype(np.int16)

def enc(x):
    return base64.b64encode(x.tobytes()).decode('ascii')

def one_pole_lp(x, cutoff, sr=SR):
    out = np.zeros_like(x)
    y = 0.0
    alpha = 1 - np.exp(-2*np.pi*cutoff/sr)
    for i, v in enumerate(x):
        y = y + alpha * (v - y); out[i] = y
    return out

def dyn_lp(x, cutoff, sr=SR):
    out = np.zeros_like(x)
    y = 0.0
    for i, v in enumerate(x):
        c = cutoff[i] if hasattr(cutoff, '__len__') else cutoff
        alpha = 1 - np.exp(-2*np.pi*c/sr); y = y + alpha * (v - y); out[i] = y
    return out

def highpass(x, cutoff, sr=SR): return x - one_pole_lp(x, cutoff, sr)
def bandpass(x, lo, hi, sr=SR): return one_pole_lp(highpass(x, lo, sr), hi, sr)

def saw(f, n, sr=SR, phase0=0.0):
    t = np.arange(n) / sr
    return 2 * ((f * t + phase0) % 1.0) - 1

def square(f, n, duty=0.5, sr=SR, phase0=0.0):
    t = np.arange(n) / sr
    p = (f * t + phase0) % 1.0
    return np.where(p < duty, 1.0, -1.0)

def crossfade_loop(sig, loop_start, loop_length, fade=256):
    """Create smooth loop by crossfading the end of the loop with pre-loop region."""
    fade = min(fade, loop_length // 4)
    # In the loop region at the end, blend from pre-loop to make the join smooth.
    # Replace the last 'fade' samples of the loop with a crossfade from the loop's end
    # into the loop's start, so that the next iteration begins cleanly.
    s = sig.copy()
    end = loop_start + loop_length
    # Crossfade: samples at positions [end-fade, end) blend with [loop_start, loop_start+fade)
    w = np.linspace(1, 0, fade)
    s[end-fade:end] = s[end-fade:end]*w + s[loop_start:loop_start+fade]*(1-w)
    return s

# ---------- Percussion ----------
def gen_kick():
    sr = SR; dur = 0.33
    t = np.arange(int(sr*dur)) / sr
    freq = 55 + 200 * np.exp(-t * 32)
    phase = 2*np.pi*np.cumsum(freq)/sr
    body = np.sin(phase)*np.exp(-t*6)
    click = (np.random.RandomState(3).uniform(-1,1,len(t)))*np.exp(-t*400)*0.5
    sub = np.sin(2*np.pi*52*t)*np.exp(-t*4)*0.35
    sig = np.tanh((body + click + sub) * 1.2)
    return sig

def gen_snare():
    sr = SR; dur = 0.22; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(7)
    noise = rs.uniform(-1,1,n)
    env = np.exp(-t*18)
    tone1 = np.sin(2*np.pi*220*t)*np.exp(-t*25)*0.4
    tone2 = np.sin(2*np.pi*330*t)*np.exp(-t*25)*0.25
    sig = noise*env*0.9 + tone1 + tone2
    sig = highpass(sig, 700, sr)
    return sig

def gen_clap():
    sr = SR; dur = 0.3; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(13)
    noise = rs.uniform(-1,1,n)
    env = np.zeros(n)
    for offset in [0.0, 0.012, 0.023, 0.035]:
        o = int(offset*sr)
        tt = np.arange(n-o)/sr
        env[o:] += np.exp(-tt*90)
    env /= env.max()
    tail = np.exp(-t*18)*0.4
    sig = noise*(env*0.85 + tail)
    sig = bandpass(sig, 900, 2500, sr)
    return sig

def gen_hat_closed():
    sr = SR; dur = 0.06; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(21)
    sig = rs.uniform(-1,1,n)*np.exp(-t*150)
    sig = highpass(sig, 6500, sr)
    return sig

def gen_hat_open():
    sr = SR; dur = 0.3; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(27)
    sig = rs.uniform(-1,1,n)*np.exp(-t*10)
    sig = highpass(sig, 7000, sr)
    return sig

def gen_crash():
    """Longer open hat / ride-ish sound."""
    sr = SR; dur = 0.9; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(28)
    sig = rs.uniform(-1,1,n)*np.exp(-t*3.5)
    # dual-band for metallic character
    s1 = bandpass(sig, 4500, 8000, sr)
    s2 = bandpass(sig, 8000, 11000, sr)
    sig = s1*0.6 + s2*0.9
    return sig

# ---------- Melodic ----------
def gen_bass():
    """Pluck bass with filter sweep."""
    sr = SR; dur = 0.55; n = int(sr*dur)
    t = np.arange(n)/sr
    s = saw(C4, n, sr) + 0.5*saw(C4/2, n, sr)
    cutoff = 300 + 2800 * np.exp(-t*12)
    s = dyn_lp(s, cutoff, sr)
    env = np.exp(-t*4)
    env[:40] *= np.linspace(0,1,40)
    return s*env

def gen_pluck():
    """Short saw pluck."""
    sr = SR; dur = 0.35; n = int(sr*dur)
    t = np.arange(n)/sr
    s = saw(C4, n, sr)*0.5 + square(C4, n, duty=0.5, sr=sr)*0.5
    s = one_pole_lp(s, 2800, sr)
    env = np.exp(-t*8)
    env[:30] *= np.linspace(0,1,30)
    return s*env

def gen_lead():
    """Looped lead: hollow square + saw with cycle-exact loop region."""
    sr = SR
    # Use a frequency with integer period for perfect loop
    period = 84  # samples
    f = sr / period  # ~262.5 Hz (close to C4 — 6 cents sharp)
    cycles_pre = 80
    cycles_loop = 2
    n_pre = period * cycles_pre
    n_loop = period * cycles_loop
    n = n_pre + n_loop
    t = np.arange(n)/sr
    s = saw(f, n, sr)*0.5 + square(f, n, duty=0.33, sr=sr)*0.5
    # add 5th harmonic for brightness
    s += 0.15*np.sin(2*np.pi*f*5*t)
    s = one_pole_lp(s, 3500, sr)
    s = s/np.max(np.abs(s))*0.9
    loop_start = n_pre
    loop_length = n_loop
    return s, loop_start, loop_length, f

def gen_pad():
    """Pad: supersaw with crossfaded loop."""
    sr = SR
    period = 84
    f = sr / period
    cycles = 80
    n = period * cycles
    t = np.arange(n)/sr
    s = np.zeros(n)
    rs = np.random.RandomState(43)
    for d in [-10, -5, 0, 5, 10]:
        fd = f * (2**(d/1200))
        s += saw(fd, n, sr, phase0=rs.random())
    s = s/len(range(-10,15,5))
    s = one_pole_lp(s, 1800, sr)
    s = s/np.max(np.abs(s))*0.85
    # Loop a large portion (not period-aligned because of detune), use crossfade
    loop_cycles = 8
    loop_length = period * loop_cycles
    loop_start = n - loop_length
    s = crossfade_loop(s, loop_start, loop_length, fade=200)
    return s, loop_start, loop_length, f

def gen_arp():
    """Bright pluck for arps."""
    sr = SR; dur = 0.25; n = int(sr*dur)
    t = np.arange(n)/sr
    s = square(C4, n, duty=0.5, sr=sr)*0.6 + saw(C4, n, sr)*0.4
    s = one_pole_lp(s, 4000, sr)
    env = np.exp(-t*12)
    env[:20] *= np.linspace(0,1,20)
    return s*env

def gen_chord_stab():
    """PWM stab."""
    sr = SR; dur = 0.4; n = int(sr*dur)
    t = np.arange(n)/sr
    s = square(C4, n, duty=0.5, sr=sr)*0.5 + square(C4, n, duty=0.33, sr=sr, phase0=0.2)*0.5
    s = one_pole_lp(s, 2800, sr)
    env = np.exp(-t*5)
    env[:int(sr*0.01)] *= np.linspace(0,1,int(sr*0.01))
    return s*env

def gen_zap():
    """Downsweep FX."""
    sr = SR; dur = 0.5; n = int(sr*dur)
    t = np.arange(n)/sr
    freq = 2000*np.exp(-t*6) + 100
    phase = 2*np.pi*np.cumsum(freq)/sr
    s = np.sin(phase)*0.5 + np.sin(phase*1.5)*0.3
    env = np.exp(-t*3); env[:20] *= np.linspace(0,1,20)
    return s*env

def gen_noise_sweep():
    """White-noise riser."""
    sr = SR; dur = 1.9; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(61)
    noise = rs.uniform(-1,1,n)
    cutoff = 200 + 7000*(t/dur)
    s = noise - dyn_lp(noise, cutoff, sr)
    env = (t/dur)**2
    return s*env*0.7

def gen_reverse_cymbal():
    """Reverse crash."""
    sr = SR; dur = 1.2; n = int(sr*dur)
    t = np.arange(n)/sr
    rs = np.random.RandomState(67)
    noise = rs.uniform(-1,1,n)
    noise = highpass(noise, 4000, sr)
    env = (t/dur)**1.8
    return noise*env*0.5

if __name__ == "__main__":
    for name, g in [('kick',gen_kick),('snare',gen_snare),('clap',gen_clap),
                    ('hat_c',gen_hat_closed),('hat_o',gen_hat_open),('crash',gen_crash),
                    ('bass',gen_bass),('pluck',gen_pluck),
                    ('arp',gen_arp),('stab',gen_chord_stab),('zap',gen_zap),
                    ('sweep',gen_noise_sweep),('rev',gen_reverse_cymbal)]:
        s = g()
        print(f"{name:>8}: len={len(s):>5}  peak={np.max(np.abs(s)):.3f}")
    for name, g in [('lead',gen_lead),('pad',gen_pad)]:
        s, ls, ll, f = g()
        print(f"{name:>8}: len={len(s):>5}  loop=({ls},{ll})  f={f:.2f}Hz  disc={abs(s[ls+ll-1]-s[ls]):.4f}")
