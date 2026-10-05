"""Original sound material for the keygen tune, synthesized with NumPy."""
import numpy as np
from xmwrite import Sample

R = 22050  # native rate for most samples

def bl_saw(phase, nharm):
    """band-limited saw, phase in cycles (float array)."""
    out = np.zeros_like(phase)
    for n in range(1, nharm+1):
        out += np.sin(2*np.pi*n*phase)/n
    return out * (2/np.pi)

def bl_pulse(phase, width, nharm):
    return bl_saw(phase, nharm) - bl_saw(phase + width, nharm)

def env_exp(n, rate, tau, hold=0.0):
    t = np.arange(n)/rate
    e = np.exp(-np.maximum(t-hold, 0)/tau)
    return e

def tail(x, n=240):
    """fade the last n samples to zero so one-shots never end with a click"""
    x = x.copy(); x[-n:] *= np.linspace(1, 0, n)
    return x

def norm(x, peak=0.95):
    m = np.abs(x).max()
    return x/m*peak if m > 0 else x

def lead_pwm():
    # loop of exactly 22048 samples = 264 cycles (f0 = 264.02 Hz); pulse width sweeps once per loop
    n = 22048; ncyc = 264
    t = np.arange(n)/R
    f0 = ncyc*R/n
    ph = f0*t
    width = 0.5 + 0.22*np.sin(2*np.pi*np.arange(n)/n)
    x = bl_pulse(ph, width, 18)
    x = norm(x, 0.9)
    atk = 64
    x = np.concatenate([x[-atk:]*np.linspace(0,1,atk), x])
    return Sample('lead pwm', x, rate=R, f0=f0, volume=64, panning=112,
                  loop_start=atk, loop_length=n, loop_type=1)

def lead_soft():
    # softer 25% pulse w/ slight detune chorus, loop 0.5s: 132 cycles @264 and 133 @266
    n = R//2; t = np.arange(n)/R
    f0 = 264.0
    x = bl_pulse(f0*t, 0.25, 14) + 0.7*bl_pulse(266.0*t + 0.3, 0.25, 14)
    x = norm(x, 0.9)
    atk = 64
    x = np.concatenate([x[-atk:]*np.linspace(0,1,atk), x])
    return Sample('lead soft', x, rate=R, f0=f0, volume=64, panning=144,
                  loop_start=atk, loop_length=n, loop_type=1)

def bass():
    # saw + sub octave; punchy attack then a seamless 8-cycle sustain loop (cycle = 168 samples)
    cyc = 168; ncyc = 40
    n = cyc*ncyc; t = np.arange(n)/R
    f = R/cyc   # 131.25 Hz
    x = bl_saw(f*t, 24)*0.7 + 0.5*np.sin(2*np.pi*f*t/2) + 0.25*bl_pulse(f*t, 0.5, 10)
    e = 0.55 + 0.45*np.exp(-t/0.06)
    x = norm(x*e, 0.9)
    ls = cyc*32; ll = cyc*8
    return Sample('bass', x, rate=R, f0=f, volume=64, panning=128,
                  loop_start=ls, loop_length=ll, loop_type=1)

def arp_stab():
    f0 = 261.63; n = int(R*0.42); t = np.arange(n)/R
    x = bl_pulse(f0*t, 0.5, 16)
    e = np.exp(-t/0.10)*(1-np.exp(-t/0.002))
    x = norm(x*e, 0.9)
    return Sample('arp stab', tail(x), rate=R, f0=f0, volume=64, panning=168)

def pluck():
    f0 = 261.63; n = int(R*0.5); t = np.arange(n)/R
    # bright pluck: saw with decaying brightness (crossfade between bright and dull)
    bright = bl_saw(f0*t, 20); dull = bl_saw(f0*t, 4)
    k = np.exp(-t/0.05)
    x = bright*k + dull*(1-k)
    e = np.exp(-t/0.14)
    x = norm(x*e, 0.9)
    return Sample('pluck', tail(x), rate=R, f0=f0, volume=64, panning=88)

def bell():
    f0 = 523.25; n = int(R*0.9); t = np.arange(n)/R
    mod = np.sin(2*np.pi*f0*3.0*t)*np.exp(-t/0.12)*1.6
    x = np.sin(2*np.pi*f0*t + mod)*np.exp(-t/0.28) + 0.3*np.sin(2*np.pi*f0*2*t)*np.exp(-t/0.10)
    x = norm(x, 0.85)
    return Sample('fm bell', tail(x, 600), rate=R, f0=f0, volume=64, panning=160)

def pad():
    # detuned saw stack, loop 1 s (integer cycles: 259, 261, 263 Hz)
    n = R; t = np.arange(n)/R
    x = bl_saw(259.0*t, 12) + bl_saw(261.0*t+0.33, 12) + bl_saw(263.0*t+0.67, 12)
    x += 0.5*bl_pulse(130.5*t, 0.5, 8)  # can't: 130.5 not integer cycles in 1s -> use 130
    x -= 0.5*bl_pulse(130.5*t, 0.5, 8)
    x += 0.5*bl_pulse(130.0*t, 0.5, 8)
    x = norm(x, 0.8)
    atk = int(R*0.12)
    x = np.concatenate([x[-atk:]*np.linspace(0,1,atk)**2, x])
    return Sample('pad', x, rate=R, f0=261.0, volume=64, panning=96,
                  loop_start=atk, loop_length=n, loop_type=1)

def kick():
    n = int(R*0.3); t = np.arange(n)/R
    f = 42 + 140*np.exp(-t/0.045)
    ph = np.cumsum(f)/R
    x = np.sin(2*np.pi*ph)*np.exp(-t/0.11)
    click = np.random.RandomState(1).randn(n)
    click = np.convolve(click, np.ones(4)/4, 'same')*np.exp(-t/0.006)
    x += 0.5*click
    x[:8] *= np.linspace(0, 1, 8)
    x = np.tanh(x*1.6)
    x = norm(x, 0.95)
    return Sample('kick', tail(x, 600), rate=R, volume=64, panning=128)

def snare():
    n = int(R*0.32); t = np.arange(n)/R
    rs = np.random.RandomState(2)
    noise = rs.randn(n)
    # band-limit noise: differentiate (emphasise highs) then light smoothing
    hp = np.concatenate([[0], np.diff(noise)])
    sm = np.convolve(hp, np.ones(3)/3, 'same')
    x = (0.5*noise + 0.9*sm)*np.exp(-t/0.085)
    body = np.sin(2*np.pi*(175+90*np.exp(-t/0.025))*t)*np.exp(-t/0.06)
    x = x*0.8 + body*1.1
    x[:6] *= np.linspace(0, 1, 6)
    x = np.tanh(x*1.3)
    x = norm(x, 0.95)
    return Sample('snare', tail(x, 600), rate=R, volume=64, panning=128)

def hat(closed=True):
    n = int(R*(0.05 if closed else 0.22)); t = np.arange(n)/R
    rs = np.random.RandomState(3 if closed else 4)
    noise = rs.randn(n)
    hp = noise - np.concatenate([[0], noise[:-1]])
    hp = hp - np.concatenate([[0], hp[:-1]])
    x = hp*np.exp(-t/(0.012 if closed else 0.07))
    x[:6] *= np.linspace(0, 1, 6)
    x = norm(x, 0.8)
    return Sample('hat closed' if closed else 'hat open', tail(x, 120 if closed else 600), rate=R, volume=64, panning=150)

def crash():
    n = int(R*1.4); t = np.arange(n)/R
    rs = np.random.RandomState(6)
    noise = rs.randn(n)
    hp = noise - np.concatenate([[0], noise[:-1]])
    # shimmering metallic component: a few inharmonic partials
    metal = sum(np.sin(2*np.pi*f*t + k) for k, f in enumerate((3113, 4231, 5570, 6890, 8120)))/5
    x = (hp*0.8 + metal*0.5*np.exp(-t/0.25))*np.exp(-t/0.35)
    x[-300:] *= np.linspace(1, 0, 300)
    x = norm(x, 0.85)
    return Sample('crash', x, rate=R, volume=64, panning=140)

def riser():
    n = int(R*1.7); t = np.arange(n)/R
    rs = np.random.RandomState(5)
    noise = rs.randn(n)
    # time-varying bandpass by overlap-add of windowed FFT chunks
    win = 1024; hop = 256
    y = np.zeros(n+win)
    w = np.hanning(win)
    fr = np.fft.rfftfreq(win, 1/R)
    for i in range(0, n-win, hop):
        frac = i/(n-win)
        fc = 250*np.exp(np.log(5000/250)*frac)
        seg = noise[i:i+win]*w
        S = np.fft.rfft(seg)
        g = np.exp(-0.5*((np.log(fr+1e-9)-np.log(fc))/0.35)**2)
        y[i:i+win] += np.fft.irfft(S*g, win)*w
    y = y[:n]*(0.15+0.85*t/t[-1])
    x = norm(y, 0.8)
    x[-200:] *= np.linspace(1,0,200)
    return Sample('riser', x, rate=R, volume=64, panning=128)

def build_all():
    return [lead_pwm(), lead_soft(), bass(), arp_stab(), pluck(), bell(), pad(),
            kick(), snare(), hat(True), hat(False), riser(), crash()]
