import sys, numpy as np
sys.path.insert(0,'/workspace/work')
from dsp import *

OUT = {}

def add(name, arr, loop=None, pan=128, vol=64, ref='C-5'):
    """ref: my-convention note name at which this sample plays at its native rate
    (i.e. the fundamental frequency present in `arr` sounds at that note)."""
    OUT[name] = dict(data=np.clip(arr,-1.0,1.0), loop=loop, pan=pan, vol=vol, ref=ref)

# ---------------------------------------------------------------- drums
def kick():
    t = t_axis(0.30)
    f = 44.0 + 150.0*np.exp(-t/0.016)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)*np.exp(-t/0.085)
    click = fftfilt(np.random.RandomState(1).randn(len(t)), lo=1200, hi=6500)*np.exp(-t/0.0035)*0.7
    thump = fftfilt(np.sin(ph*1.0)*np.exp(-t/0.02), hi=400)*0.5
    x = body + click + thump
    x = np.tanh(x*2.2)*0.85
    add('KICK', norm(x,0.97), pan=128, ref='C-5')

def snare():
    t = t_axis(0.24)
    rs = np.random.RandomState(2)
    n = fftfilt(rs.randn(len(t)), lo=700, hi=9500)*np.exp(-t/0.055)
    tone = (np.sin(2*np.pi*186*t)*0.55 + np.sin(2*np.pi*331*t)*0.30)*np.exp(-t/0.030)
    x = n*1.0 + tone
    x = np.tanh(x*1.8)
    add('SNARE', norm(x,0.95), pan=118, ref='C-5')

def clap():
    t = t_axis(0.36)
    rs = np.random.RandomState(3)
    n = rs.randn(len(t))
    env = np.zeros_like(t)
    for st,dec,g in ((0.0,0.006,1.0),(0.011,0.006,0.85),(0.022,0.006,0.9)):
        m = (t>=st)
        env[m] += g*np.exp(-(t[m]-st)/dec)
    m = t>=0.022
    env[m] += 1.1*np.exp(-(t[m]-0.022)/0.085)
    x = fftfilt(n*env, lo=750, hi=5200)
    x = np.tanh(x*2.0)
    add('CLAP', norm(x,0.92), pan=142, ref='C-5')

def chat():
    t = t_axis(0.06)
    rs = np.random.RandomState(4)
    x = fftfilt(rs.randn(len(t)), lo=6800)*np.exp(-t/0.010)
    x += fftfilt(rs.randn(len(t)), lo=9000)*np.exp(-t/0.004)*0.5
    add('CHAT', norm(x,0.85), pan=88, ref='C-5')

def ohat():
    t = t_axis(0.34)
    rs = np.random.RandomState(5)
    x = fftfilt(rs.randn(len(t)), lo=6200)*np.exp(-t/0.080)
    x += fftfilt(rs.randn(len(t)), lo=9500)*np.exp(-t/0.05)*0.4
    add('OHAT', norm(x,0.82), pan=154, ref='C-5')

def crash():
    t = t_axis(1.15)
    rs = np.random.RandomState(6)
    x = fftfilt(rs.randn(len(t)), lo=3800)*np.exp(-t/0.30)
    for f,g,d in ((5120,0.35,0.22),(6930,0.25,0.18),(8790,0.18,0.15)):
        x += np.sin(2*np.pi*f*t+rs.rand()*6)*np.exp(-t/d)*g
    x = np.tanh(x*1.4)
    add('CRASH', norm(x,0.80), pan=110, ref='C-5')

def tom():
    t = t_axis(0.30)
    f = 90.0 + 190.0*np.exp(-t/0.030)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph)*np.exp(-t/0.11)
    x += fftfilt(np.random.RandomState(7).randn(len(t)), lo=300, hi=3000)*np.exp(-t/0.02)*0.25
    add('TOM', norm(np.tanh(x*1.5),0.92), pan=170, ref='C-5')

def riser():
    t = t_axis(1.15)
    rs = np.random.RandomState(8)
    n = rs.randn(len(t))
    # rising bandpass via FFT of overlapping windows -> approximate with sweep of hp cutoff
    x = np.zeros_like(t)
    step = 1024
    for i in range(0, len(t)-step, step):
        frac = i/(len(t)-step)
        seg = n[i:i+step]
        lo = 300*(2.0**(3.0*frac))
        x[i:i+step] = fftfilt(seg, lo=lo, hi=11000)
    env = (t/t[-1])**1.5
    x = x*env
    x = np.tanh(x*1.6)
    add('RISER', norm(x,0.78), pan=128, ref='C-5')

# ---------------------------------------------------------------- tonal
def bass():
    dur = 0.46; t = t_axis(dur)
    f0 = 110.0   # A2 fundamental reference
    w = 0.6*saw(f0,t) + 0.5*pulse(f0,t,0.5) + 0.62*np.sin(np.pi*f0*t) + 0.25*np.sin(2*np.pi*f0*t)
    fc = 900.0 + 4200.0*np.exp(-t/0.012)
    x = onepole_lp(w, fc)
    x = onepole_hp(x, 32.0)
    env = (1-np.exp(-t/0.0015))*np.exp(-t/0.22)
    x = x*env
    x = np.tanh(x*1.9)
    add('BASS', norm(fade_edges(x,0.0,0.012),0.96), pan=128, ref='A2')

def stab(name, freqs, dur=0.55):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for i,f in enumerate(freqs):
        d = 0.004*(i%2)
        x += saw(f*1.004,t)+saw(f*0.996,t,0.31)
        x += 0.35*pulse(f*2.0,t,0.5,0.13)
    x = onepole_lp(x, 4600.0)
    env = (1-np.exp(-t/0.004))*np.exp(-t/0.20)
    x = x*env
    x = np.tanh(x*1.35)
    add(name, norm(fade_edges(x,0.0,0.05),0.9), pan=128, ref='C-5')

def pad():
    dur = 0.95; t = t_axis(dur)
    f0 = 220.0
    x = (saw(f0*1.003,t)+saw(f0*0.997,t,0.27))*0.6 + tri(f0,t)*0.35 + saw(f0*0.5,t)*0.30
    x = onepole_lp(x, 2200.0)
    atk = np.clip(t/0.16,0,1)**1.5
    x = x*atk
    x = norm(x,0.8)
    # loop region: 0.25 .. 0.90
    ls, le = int(0.25*SR), int(0.90*SR)
    x, ls, ll = make_loop(x, ls, le, 512)
    add('PAD', x, loop=(ls,ll), pan=128, ref='A3')

def lead():
    dur = 0.55; t = t_axis(dur)
    f0 = 440.0
    x = saw(f0,t)*0.75 + pulse(f0,t,0.28,0.1)*0.45 + saw(f0*2.004,t,0.5)*0.22 + pulse(f0*1.006,t,0.5)*0.15
    x = onepole_lp(x, 7200.0)
    x = onepole_hp(x, 180.0)
    atk = np.clip(t/0.008,0,1)
    x = x*atk
    x = norm(x,0.85)
    ls, le = int(0.10*SR), int(0.50*SR)
    x, ls, ll = make_loop(x, ls, le, 300)
    add('LEAD', x, loop=(ls,ll), pan=128, ref='A-4')

def lead2():
    """slightly different colour lead (for harmony / doubling)"""
    dur = 0.55; t = t_axis(dur)
    f0 = 440.0
    x = pulse(f0,t,0.18,0.05)*0.7 + saw(f0*0.997,t)*0.45 + np.sin(2*np.pi*f0*t)*0.25
    x = onepole_lp(x, 5600.0)
    x = norm(x* np.clip(t/0.010,0,1), 0.82)
    ls, le = int(0.10*SR), int(0.50*SR)
    x, ls, ll = make_loop(x, ls, le, 300)
    add('LEAD2', x, loop=(ls,ll), pan=128, ref='A-4')

def bell():
    t = t_axis(0.62)
    f0 = 880.0
    parts = ((1.0,1.0,0.16),(2.76,0.42,0.10),(5.40,0.22,0.07),(8.93,0.10,0.05),(1.5,0.35,0.12))
    x = np.zeros_like(t)
    for r,g,d in parts:
        x += np.sin(2*np.pi*f0*r*t)*np.exp(-t/d)*g
    x = onepole_hp(x, 200.0)
    add('BELL', norm(x* np.clip(t/0.003,0,1),0.85), pan=128, ref='A-5')

def arp():
    dur = 0.26; t = t_axis(dur)
    f0 = 440.0
    x = pulse(f0,t,0.30,0.0)*0.6 + saw(f0,t)*0.4 + pulse(f0*2.0,t,0.5,0.3)*0.18
    fc = 1500.0 + 6000.0*np.exp(-t/0.010)
    x = onepole_lp(x, fc)
    env = np.clip(t/0.0012,0,1)*np.exp(-t/0.055)
    x = x*env
    add('ARP', norm(fade_edges(np.tanh(x*1.5),0.0,0.01),0.9), pan=158, ref='A-4')

kick(); snare(); clap(); chat(); ohat(); crash(); tom(); riser()
bass(); stab('STAB_AM',[220.0,261.63,329.63,440.0])
stab('STAB_F',[174.61,220.0,261.63,349.23])
stab('STAB_C',[196.0,261.63,329.63,392.0])
stab('STAB_G',[196.0,246.94,293.66,392.0])
pad(); lead(); lead2(); bell(); arp()

def finalize():
    for name,v in OUT.items():
        d=v['data']; lp=v['loop']
        d -= d.mean()                       # DC blocker
        d = onepole_hp(d, 11.0)             # remove slow drift
        v['data'] = d = np.ascontiguousarray(d)
        m=float(np.abs(d).max())
        if m > 0.97: d *= 0.97/m
        k=int(0.0018*SR); d[:k]*=np.linspace(0,1,k)
        if lp is None:
            k2=int(0.008*SR); d[-k2:]*=np.linspace(1,0,k2)
        else:
            k2=int(0.008*SR); d[-k2:]*=np.linspace(1,0,k2)

finalize()

if __name__ == '__main__':
    for k,v in OUT.items():
        d=v['data']; lp=v['loop']
        # spectral centroid
        X=np.abs(np.fft.rfft(d*np.hanning(len(d)))); f=np.fft.rfftfreq(len(d),1/SR)
        cen=float((X*f).sum()/max(X.sum(),1e-9))
        print(f"{k:9s} len={len(d):6d} ({len(d)/SR:.3f}s) peak={np.abs(d).max():.3f} rms={np.sqrt((d**2).mean()):.3f} cen={cen:7.0f} loop={lp} pan={v['pan']}")
