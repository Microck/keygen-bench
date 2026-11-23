"""Instrument design for KEYGEN.EXE.
Every tonal instrument is a short one-cycle/one-shot sample; all timbre and
attack shaping lives in the sample data (envelopes are not used).
"""
import numpy as np, sys
sys.path.insert(0,'/workspace/work')
from xm2 import Sample, Instrument

DESIGN = 8363.0                                   # base rate the waves are designed for
DRUM_NOTE = 78
DRUM_RATE = 8363.0 * 2 ** ((DRUM_NOTE - 49) / 12.0)

def pulse_cycle(duty, N=32, maxh=48, amp=1.0):
    t = np.arange(N) / N
    x = np.zeros(N)
    for n in range(1, maxh + 1):
        a = (2.0 / (n * np.pi)) * np.sin(np.pi * n * duty)
        x += a * np.sin(2 * np.pi * n * t)
    m = np.max(np.abs(x))
    return x * amp / m if m > 0 else x

def harmonic_cycle(amps, N=32, amp=1.0):
    t = np.arange(N) / N
    x = np.zeros(N)
    for i, a in enumerate(amps, start=1):
        x += a * np.sin(2 * np.pi * i * t)
    m = np.max(np.abs(x))
    return x * amp / m if m > 0 else x

def click(n, seed, decay=2.0, brighten=1, amp=1.0):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    for _ in range(brighten):
        x = np.diff(np.concatenate([[0.0], x]))
    x *= np.exp(-np.arange(n) / decay)
    m = np.max(np.abs(x))
    return x * amp / m if m > 0 else x

def looped(name, data, lstart, llen, volume=64, pan=128, finetune=0, relnote=0):
    return Sample(name, data, volume=volume, finetune=finetune, relnote=relnote,
                  panning=pan, loop_start=lstart, loop_length=llen, loop_type=1, bits=16)

def oneshot(name, data, volume=64, pan=128, finetune=0, relnote=0):
    return Sample(name, data, volume=volume, finetune=finetune, relnote=relnote,
                  panning=pan, loop_start=0, loop_length=0, loop_type=0, bits=16)

# ------------------------------------------------------------ tonal
def lead_wave():
    # four-cycle wavetable (25% -> 31.25% -> 18.75% -> 25% pulse) so the
    # timbre shimmers as it loops, giving the lead movement
    a = pulse_cycle(0.25, 32, 48, amp=0.85)
    b = pulse_cycle(0.3125, 32, 48, amp=0.85)
    c = pulse_cycle(0.1875, 32, 48, amp=0.85)
    a = a.copy(); a[:5] += click(5, 31, decay=1.2, brighten=1, amp=0.26)
    a = a / max(1.0, np.max(np.abs(a)))
    data = np.concatenate([a, b, c, a])
    return data, 0, 128

def lead2_wave():
    # softer 50% pulse with a hint of second harmonic -- the "break" lead
    a = pulse_cycle(0.5, 32, 32, amp=0.80)
    b = pulse_cycle(0.46875, 32, 32, amp=0.80)
    a = a.copy(); a[:6] += click(6, 33, decay=1.4, brighten=1, amp=0.30)
    a = a / max(1.0, np.max(np.abs(a)))
    data = np.concatenate([a, b, a])
    return data, 0, 96

def harm_wave():
    body = pulse_cycle(0.125, 32, 40, amp=0.75)
    return np.concatenate([body, body]), 32, 32

def arp_wave():
    body = pulse_cycle(0.25, 32, 40, amp=0.70)
    att = body.copy()
    att[:4] += click(4, 51, decay=1.0, brighten=1, amp=0.22)
    att = att / max(1.0, np.max(np.abs(att)))
    return np.concatenate([att, body]), 32, 32

def bass_wave():
    body = harmonic_cycle([0.75, 0.70, 0.45, 0.30, 0.20, 0.13, 0.09, 0.05], 32, amp=0.90)
    ramp = np.linspace(0.55, 1.0, 32)
    att = body * ramp + click(32, 41, decay=6.0, brighten=1, amp=0.35)
    att = att / max(1.0, np.max(np.abs(att)))
    return np.concatenate([att, body]), 32, 32

def pad_wave():
    body = harmonic_cycle([1.0, 0.40, 0.18, 0.28, 0.10, 0.18, 0.06, 0.10], 32, amp=0.9)
    ramp = np.linspace(0.35, 1.0, 128) ** 1.5
    att = np.tile(body, 4) * ramp
    return np.concatenate([att, body]), 128, 32

def pluck_wave():
    n = int(0.75 * DESIGN)
    t = np.arange(n) / DESIGN
    f = DESIGN / 32.0
    x = np.zeros(n)
    for h in range(1, 18):
        a = (1.0 / h) * (1.0 if h % 2 else 0.5) * np.exp(-h / 9.0)
        x += a * np.sin(2 * np.pi * h * f * t)
    x *= np.exp(-t / 0.22) * (1 - np.exp(-t / 0.002))
    x += click(n, 43, decay=0.004, brighten=2, amp=0.5)
    x /= np.max(np.abs(x))
    return x * 0.85

# ------------------------------------------------------------ drums (designed at DRUM_RATE)
def kick():
    n = int(0.26 * DRUM_RATE)
    t = np.arange(n) / DRUM_RATE
    # punchy 808/909 hybrid: fast pitch sweep, short body, click for midrange
    f = 68 + 210 * np.exp(-t / 0.014)
    ph = 2 * np.pi * np.cumsum(f) / DRUM_RATE
    x = np.sin(ph) * np.exp(-t / 0.050)
    x += 0.50 * np.sin(2*ph) * np.exp(-t / 0.026)
    x += 0.30 * np.sin(3*ph) * np.exp(-t / 0.016)
    x += 0.12 * np.sin(5*ph) * np.exp(-t / 0.010)
    body_click = click(n, 3, decay=0.0035, brighten=1, amp=0.55)
    x += body_click
    # high-passed snap in the 1-3 kHz region
    snap = click(n, 13, decay=0.0018, brighten=3, amp=0.42)
    x += snap
    x /= np.max(np.abs(x))
    return x * 0.95

def snare():
    n = int(0.22 * DRUM_RATE)
    t = np.arange(n) / DRUM_RATE
    noise = click(n, 5, decay=0.070, brighten=1, amp=1.0)
    tone = (np.sin(2*np.pi*185*t) + 0.65*np.sin(2*np.pi*278*t)
            + 0.25*np.sin(2*np.pi*415*t)) * np.exp(-t / 0.040)
    tone /= np.max(np.abs(tone))
    x = noise * 1.0 + tone * 0.75
    x /= np.max(np.abs(x))
    return x * 0.92

def hat(decay=0.010, dur=0.055, seed=7, amp=0.75):
    n = int(dur * DRUM_RATE)
    t = np.arange(n) / DRUM_RATE
    # 808-ish metallic tone cluster + noise sparkle, high-passed
    freqs = [316.0, 451.0, 623.0, 787.0, 1103.0, 1420.0, 1793.0, 2317.0]
    ton = np.zeros(n)
    for i, f in enumerate(freqs):
        ton += np.sin(2*np.pi*f*t*2.6 + i*0.7)
    ton /= len(freqs)
    ton = np.diff(np.concatenate([[0.0], ton]))
    ton *= np.exp(-t/decay)
    noi = click(n, seed, decay=decay*0.8, brighten=2, amp=1.0)
    x = ton*1.6 + noi*0.7
    m = np.max(np.abs(x))
    return x * amp / m if m > 0 else x

def crash():
    n = int(1.3 * DRUM_RATE)
    t = np.arange(n) / DRUM_RATE
    rng = np.random.default_rng(11)
    base = rng.standard_normal(n)
    base = np.diff(np.concatenate([[0.0], base]))
    base *= (1 - np.exp(-t/0.002)) * np.exp(-t/0.40)
    # add body: dense inharmonic partials so RMS is meaningful
    ton = np.zeros(n)
    for i, f in enumerate([421., 587., 803., 1091., 1427., 1789., 2251., 2683., 3119.]):
        ton += np.sin(2*np.pi*f*t + i) * np.exp(-t/(0.5 - i*0.03))
    ton /= 9
    x = base*0.8 + ton*0.9
    x /= np.max(np.abs(x))
    return x * 0.8

def tom(f0=180, f1=92, dur=0.20, amp=0.8):
    n = int(dur * DRUM_RATE)
    t = np.arange(n) / DRUM_RATE
    f = f1 + (f0 - f1) * np.exp(-t / 0.032)
    ph = 2 * np.pi * np.cumsum(f) / DRUM_RATE
    x = np.sin(ph) * np.exp(-t / 0.070)
    x += click(n, 9, decay=0.004, brighten=1, amp=0.25)
    x /= np.max(np.abs(x))
    return x * amp

TARGET_RMS = 0.105          # consistent loudness across tonal voices

def normalize_rms(smp):
    """Scale the sustaining (or whole) part to TARGET_RMS, keeping headroom."""
    if smp.loop_length:
        seg = smp.data[smp.loop_start:smp.loop_start+smp.loop_length]
    else:
        seg = smp.data
    rms = float(np.sqrt((seg**2).mean()))
    if rms < 1e-9:
        return smp
    g = TARGET_RMS / rms
    peak = float(np.max(np.abs(smp.data))) * g
    if peak > 0.92:
        g *= 0.92 / peak
    smp.data = smp.data * g
    return smp

def build_instruments():
    ins = {}
    d, ls, ll = lead_wave();   ins['lead']  = Instrument("square lead", [looped("lead", d, ls, ll, volume=64, pan=128)])
    d, ls, ll = lead2_wave();  ins['lead2'] = Instrument("fat lead",    [looped("lead2", d, ls, ll, volume=64, pan=128)])
    d, ls, ll = harm_wave();   ins['harm']  = Instrument("thin harm",   [looped("harm", d, ls, ll, volume=64, pan=200)])
    d, ls, ll = arp_wave();    ins['arp']   = Instrument("arp chip",    [looped("arp", d, ls, ll, volume=64, pan=56)])
    d, ls, ll = bass_wave();   ins['bass']  = Instrument("chip bass",   [looped("bass", d, ls, ll, volume=64, pan=128)])
    d, ls, ll = pad_wave();    ins['pad']   = Instrument("warm pad",    [looped("pad", d, ls, ll, volume=64, pan=96)])
    ins['pluck'] = Instrument("pluck", [oneshot("pluck", pluck_wave(), volume=64, pan=228)])
    ins['kick']  = Instrument("kick",  [oneshot("kick", kick(), volume=64, pan=128)])
    ins['snare'] = Instrument("snare", [oneshot("snare", snare(), volume=64, pan=128)])
    ins['hat']   = Instrument("hat",   [oneshot("hat", hat(0.008, 0.05, 7, 0.75), volume=64, pan=210)])
    ins['ohat']  = Instrument("open hat", [oneshot("ohat", hat(0.055, 0.20, 8, 0.7), volume=64, pan=196)])
    ins['crash'] = Instrument("crash", [oneshot("crash", crash(), volume=64, pan=120)])
    ins['tom']   = Instrument("tom",   [oneshot("tom", tom(), volume=64, pan=72)])
    ins['tom2']  = Instrument("tom hi",[oneshot("tom2", tom(270, 150, 0.16, 0.8), volume=64, pan=184)])
    # level-match the tonal voices so the pattern volume column is meaningful
    for key in ('lead', 'lead2', 'harm', 'arp', 'bass', 'pad', 'pluck'):
        for smp in ins[key].samples:
            normalize_rms(smp)
    # percussion: scale to fixed peaks so transients stay intact
    drum_peak = {'kick': 0.66, 'snare': 0.58, 'hat': 0.34, 'ohat': 0.36,
                 'crash': 0.36, 'tom': 0.56, 'tom2': 0.56}
    for key, pk in drum_peak.items():
        smp = ins[key].samples[0]
        cur = float(np.max(np.abs(smp.data)))
        if cur > 1e-9:
            smp.data = smp.data * (pk / cur)
    return ins
