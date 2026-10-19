import numpy as np, wave, os

SR = 44100

def write_wav(path, data):
    x = np.clip(np.asarray(data, dtype=np.float64), -1.0, 1.0)
    pcm = (x*32767.0).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

def period_len(f0):
    return max(4, int(round(SR/f0)))

def frac(n, P):
    return (np.arange(n)/P) % 1.0

def wave_pulse(n, P, duty=0.5):
    f = frac(n, P)
    return np.where(f < duty, 1.0, -1.0)

def wave_saw(n, P):
    return 2.0*frac(n, P) - 1.0

def wave_tri(n, P):
    f = frac(n, P)
    return 4.0*np.abs(f-0.5) - 1.0

def wave_sine(n, P, phase=0.0):
    return np.sin(2*np.pi*(frac(n, P)+phase))

def wave_organ(n, P):
    out = np.zeros(n)
    for h, a in ((1,1.0),(2,0.5),(3,0.33),(4,0.22),(6,0.12),(8,0.07)):
        out += a*np.sin(2*np.pi*h*frac(n,P))
    return out/2.3

def wave_buzz(n, P):
    # harmonically rich "saw bass" with mild even-harmonic emphasis
    out = np.zeros(n)
    for h, a in ((1,1.0),(2,0.55),(3,0.38),(4,0.26),(5,0.18),(6,0.13),(7,0.09),(8,0.06)):
        out += a*np.sin(2*np.pi*h*frac(n,P))
    return out/2.6

def env_body(n, body_end, sustain, tau, attack, close=0.03):
    t = np.arange(n)/SR
    e = sustain + (1.0-sustain)*np.exp(-t/max(tau,1e-4))
    e = np.minimum(1.0, t/max(attack,1e-4))*e
    closemask = np.clip((body_end - np.arange(n))/(close*SR), 0.0, 1.0)
    e = sustain + (e-sustain)*closemask
    return e

def bitcrush(x, levels=32, hold=0):
    if hold:
        # sample & hold at lower rate
        step = int(round(SR/hold))
        idx = (np.arange(len(x))//step)*step
        x = x[idx]
    q = np.round(x*levels)/levels
    return q

def dist(x, drive=1.0):
    return np.tanh(x*drive)

def hp(x):
    y = np.empty_like(x); y[0] = x[0]
    y[1:] = x[1:]-x[:-1]
    return y

def lp(x, cutoff):
    # one-pole lowpass
    a = np.exp(-2*np.pi*cutoff/SR)
    y = np.empty_like(x); y[0] = x[0]
    acc = 0.0
    for i in range(len(x)):
        acc = (1-a)*x[i] + a*acc
        y[i] = acc
    return y

def make_voice(wavefn, f0, body_sec, sustain, tau, attack, loops=4,
               post=None, norm=0.9):
    P = period_len(f0)
    body_end = int(round(body_sec*SR/P))*P
    loop_len = loops*P
    n = body_end + loop_len
    w = wavefn(n, P)
    e = np.ones(n)
    e[:body_end] = env_body(body_end, body_end, sustain, tau, attack)
    e[body_end:] = sustain
    x = w*e
    if post is not None:
        x = post(x)
    peak = np.max(np.abs(x)) or 1.0
    x = x/peak*norm
    return x, P, body_end, loop_len, P and int(round(57 + 12*np.log2((SR/P)/440.0)))
