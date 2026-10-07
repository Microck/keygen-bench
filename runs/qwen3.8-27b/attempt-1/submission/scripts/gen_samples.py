"""Synthesize all 10 original samples for the Keygen tune (44.1 kHz mono 16-bit).
Run: python3 gen_samples.py  -> writes *.wav next to this script's out dir.
No external audio; everything is generated from scratch with NumPy."""
import numpy as np, wave, os

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1234)
rng_n = np.random.default_rng(42)  # dedicated for hat/openhat/riser (matches module)

def save(name, x, peak=0.9):
    x = np.asarray(x, float); m = np.max(np.abs(x))
    if m > 1e-9: x = x / m * peak
    xi = np.clip(x * 32767, -32768, 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name), 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(xi.tobytes())
    print('wrote', name, len(x), 'samples')

def fir_lp(x, cutoff, order=96):
    n = np.arange(order); fc = cutoff / SR
    h = np.sinc(2*fc*(n - order//2)) * np.hanning(order); h *= 2*fc
    return np.convolve(x, h, mode='same')
def band(x, lo, hi):
    return fir_lp(x, hi) - fir_lp(x, lo)
def saw(ph):
    return 2.0 * (ph / (2*np.pi) % 1.0) - 1.0

# KICK: sine sweep 165->41 Hz + click
t = np.arange(int(SR*0.32)) / SR
f = 41 + (165-41)*np.exp(-t/0.075)
ph = 2*np.pi*np.cumsum(f)/SR
x = np.sin(ph)*np.exp(-t/0.065) + 0.5*np.sin(2*ph)*np.exp(-t/0.03)
click = rng.standard_normal(len(t))*np.exp(-t/0.0035)*0.6
x += (click - fir_lp(click, 1500, 48))
save('kick.wav', x * (1 - np.exp(-t/0.0012)))

# SNARE: tone + bandpassed noise
t = np.arange(int(SR*0.28)) / SR
tone = np.sin(2*np.pi*185*t + 5*np.sin(2*np.pi*88*t)) * np.exp(-t/0.045)
noise = band(rng.standard_normal(len(t)), 700, 7000) * np.exp(-t/0.085)
save('snare.wav', (0.55*tone + 0.9*noise) * (1 - np.exp(-t/0.0008)))

# HAT (closed): bandpass 7k-14k, short
t = np.arange(int(SR*0.05)) / SR
save('hat.wav', band(rng_n.standard_normal(len(t)), 7000, 14000) * np.exp(-t/0.012) * (1-np.exp(-t/0.0004)))

# OPEN HAT: bandpass 7k-13k, longer
t = np.arange(int(SR*0.28)) / SR
save('openhat.wav', band(rng_n.standard_normal(len(t)), 7000, 13000) * np.exp(-t/0.07) * (1-np.exp(-t/0.0004)))

# BASS: saw pluck at A-2 (110 Hz) with pitch-drop + sub, lowpass 1100
t = np.arange(int(SR*0.30)) / SR
f = 110.0 * (1.0 + 0.35*np.exp(-t/0.025))
ph = 2*np.pi*np.cumsum(f)/SR
x = 0.55*saw(ph) + 0.8*np.sin(ph)
x = fir_lp(x, 1100)
save('bass.wav', x * (1 - np.exp(-t/0.0035)) * np.exp(-t/0.085))

# SUB: sine at A-1 (55 Hz) with pitch drop, tight
t = np.arange(int(SR*0.28)) / SR
f = 55.0 * (1.0 + 0.6*np.exp(-t/0.018))
ph = 2*np.pi*np.cumsum(f)/SR
x = np.sin(ph) + 0.3*np.sin(2*ph)
x = fir_lp(x, 400)
save('sub.wav', x * (1 - np.exp(-t/0.0015)) * np.exp(-t/0.055))

# ARP: square/saw pluck at A-4 (440 Hz), lowpass 3800
t = np.arange(int(SR*0.15)) / SR
ph = 2*np.pi*440.0*t
x = saw(ph)
x = fir_lp(x, 3800)
save('arp.wav', x * (1 - np.exp(-t/0.0015)) * np.exp(-t/0.04))

# PAD: detuned saws at A-3 (220 Hz), 1.6s (one bar), short attack, NO loop
t = np.arange(int(SR*1.6)) / SR
f0 = 220.0
x = np.zeros_like(t)
for det in (0.994, 1.0, 1.006):
    x += saw(2*np.pi*f0*det*t)
x += 0.6*np.sin(2*np.pi*f0*t)
x /= 3.6
x = fir_lp(x, 1900)
x *= 0.85 + 0.15*np.sin(2*np.pi*0.5*t - np.pi/2)
att, rel = 0.08, 0.12
env = np.ones_like(t); na, nr = int(att*SR), int(rel*SR)
env[:na] = np.linspace(0, 1, na)**2
env[-nr:] *= np.linspace(1, 0, nr)**2
save('pad.wav', x * env)

# LEAD: saw at A-4 (440 Hz) with baked vibrato (5.5 Hz, ~12 cents)
t = np.arange(int(SR*0.5)) / SR
f = 440.0; vrate = 5.5; vdepth = 0.012
ramp = np.minimum(1.0, t/0.12)
ph = 2*np.pi*f*t + (f*vdepth/vrate)*ramp*(1 - np.cos(2*np.pi*vrate*t))
x = saw(ph) + 0.35*saw(2*ph)
x = fir_lp(x, 2800)
save('lead.wav', x * (1 - np.exp(-t/0.006)) * np.exp(-t/0.13))

# RISER: 4s noise sweep, rising band, amplitude swell
dur = 4.0
t = np.arange(int(SR*dur)) / SR
n = rng_n.standard_normal(len(t))
low = band(n, 300, 3000); high = band(n, 2000, 12000)
x = low*(1 - t/dur)*0.7 + high*(t/dur)**1.5*0.9
x *= (1 - np.exp(-t/0.05)) * (t/dur)**1.2
save('riser.wav', x)
print('done')
