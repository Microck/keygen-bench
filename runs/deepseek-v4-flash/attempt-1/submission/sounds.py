"""Sample synthesis for the keygen tune. All samples one-shot, natural pitch, 44100Hz 16-bit mono."""
import numpy as np
import wave, os

SR = 44100

NOTE = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def semi(name):
    pc = NOTE[name[0]]
    if len(name)>1 and name[1]=='#':
        pc += 1
    oct_ = int(name[-1])
    return oct_*12 + pc   # C-0 = 0 ... C-4 = 48, A-4 = 57 (440 Hz)
def name(s):
    pcs = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
    return pcs[s%12] + str(s//12)
def hz(n):
    return 440.0 * 2**((n-57)/12)

SCALE = 0.27

def save(name_, y, peak=27000, path='/workspace/snd'):
    y = np.asarray(y, dtype=np.float64)
    if y.size == 0: raise ValueError("empty sample " + name_)
    m = np.abs(y).max()
    if m > 0: y = y * (peak / m) * SCALE
    y = np.clip(y, -32767, 32767)
    p = os.path.join(path, name_ + '.wav')
    w = wave.open(p, 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(y.astype(np.int16).tobytes())
    w.close()
    return p

def env_ad(n, a, d=0.0, sus=1.0, rel=0.0):
    """attack a seconds, then optional linear decay d to sus, release rel at end."""
    e = np.ones(n)
    na = max(1, int(a*SR))
    e[:na] = np.linspace(0,1,na)**1.5
    i = na
    if d > 0:
        nd = max(1, int(d*SR))
        e[i:i+nd] = np.linspace(1, sus, nd)
        i += nd
    if rel > 0:
        nr = max(1, int(rel*SR))
        e[-nr:] = np.linspace(e[-nr-1] if n>nr else 1, 0, nr)
    return e

def exp_env(n, tau, a=0.002):
    e = np.ones(n)
    na = max(1,int(a*SR)); e[:na] = np.linspace(0,1,na)
    e[na:] = np.exp(-(np.arange(n-na)/(SR*tau)))
    return e

def lowpass(x, cutoff, order=1):
    """simple butter-ish via scipy-free: FFT brickwall with soft rolloff"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1/SR)
    H = 1.0/(1.0 + (f/cutoff)**(2*order))
    return np.fft.irfft(X*H, len(x))

def highpass(x, cutoff, order=1):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1/SR)
    H = 1.0 - 1.0/(1.0 + (f/cutoff)**(2*order))
    return np.fft.irfft(X*H, len(x))

def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1/SR)
    H = (f>lo) & (f<hi)
    # smooth edges
    H = np.clip((f-lo)/50,0,1)*np.clip((hi-f)/50,0,1)
    return np.fft.irfft(X*H, len(x))

def softclip(x, k=2.0):
    return np.tanh(k*x)/np.tanh(k)

# ---------------- instruments ----------------
def kick():
    dur=0.34; t=np.arange(int(dur*SR))/SR
    f0, f1 = 170.0, 40.0
    f = f1 + (f0-f1)*np.exp(-t/0.045)
    phase = 2*np.pi*np.cumsum(f)/SR
    y = np.sin(phase)
    click = np.random.default_rng(1).normal(0,1,int(0.004*SR))
    click = click*np.exp(-np.arange(len(click))/(SR*0.0012))
    y[:len(click)] += click*1.2
    e = np.exp(-t/0.11); e[:int(0.002*SR)] = np.linspace(0,1,int(0.002*SR))
    y = y*e
    y = softclip(y*1.6, 2.5)
    y[int(0.25*SR):] *= np.linspace(1,0,int(0.09*SR))
    return y

def snare():
    dur=0.24; n=int(dur*SR); t=np.arange(n)/SR
    rng=np.random.default_rng(2)
    noise = rng.normal(0,1,n)
    bp = bandpass(noise, 1400, 4200)
    crack = bandpass(noise, 5000, 10000)
    tone = np.sin(2*np.pi*190*t)
    y = 0.55*bp*np.exp(-t/0.045) + 1.0*crack*np.exp(-t/0.012) + 0.5*tone*np.exp(-t/0.03)
    y[:int(0.001*SR)] = 0
    return y

def chh():
    dur=0.07; n=int(dur*SR); t=np.arange(n)/SR
    rng=np.random.default_rng(3)
    noise = rng.normal(0,1,n)
    y = highpass(noise, 6500, 2)*np.exp(-t/0.014)
    return y*1.2

def ohh():
    dur=0.30; n=int(dur*SR); t=np.arange(n)/SR
    rng=np.random.default_rng(4)
    noise = rng.normal(0,1,n)
    y = highpass(noise, 5500, 2)*np.exp(-t/0.085)
    return y*1.2

def crash():
    dur=1.6; n=int(dur*SR); t=np.arange(n)/SR
    rng=np.random.default_rng(5)
    noise = rng.normal(0,1,n)
    y = highpass(noise, 4200, 2)*np.exp(-t/0.38)
    shimmer = np.sin(2*np.pi*(1200+800*np.exp(-t/0.5))*t)
    y += 0.10*shimmer*np.exp(-t/0.5)
    return y

def bass():
    dur=0.42; n=int(dur*SR); t=np.arange(n)/SR
    # saw with 12 harmonics, dark; content pitched so A-2 (semi 33) sounds at 110 Hz
    f0 = 110.0 * 2**((48-33)/12)
    y=np.zeros(n)
    for h in range(1,13):
        y += (1.0/h**1.05)*np.sin(2*np.pi*h*f0*t + 0.3*h)
    e = env_ad(n, 0.004, d=0.25, sus=0.55, rel=0.06)
    y = y*e
    y = softclip(y*1.4, 3)
    return y

def _lead_square(vib_rate=5.5, vib_delay=0.15, vib_depth=0.004, dur=2.0, bright=11, peak=26000):
    n=int(dur*SR); t=np.arange(n)/SR
    f=659.26 * 2**((48-64)/12)  # content pitch: tracker note E-5 (semi 64) sounds at 659 Hz
    vib = np.where(t>vib_delay, vib_depth*f/vib_rate*(1-np.cos(2*np.pi*vib_rate*(t-vib_delay))), 0.0)
    phase = 2*np.pi*f*t + vib
    y=np.zeros(n)
    for h in range(1,bright+1,2):
        y += (1.0/h**1.1)*np.sin(h*phase)
    # add a touch of saw body (even harmonics)
    for h in range(2,bright+1,2):
        y += (0.35/h**1.1)*np.sin(h*phase)
    e = env_ad(n, 0.006, d=0.1, sus=0.85, rel=0.25)
    y = y*e
    return softclip(y*1.3, 2.5)*peak

def lead1():
    return _lead_square(5.5, 0.15, 0.004, 2.0, 11, 26000)

def lead2():
    # slightly softer, more vibrato
    return _lead_square(5.0, 0.1, 0.005, 1.8, 9, 23000)

def arp_sq():
    dur=0.30; n=int(dur*SR); t=np.arange(n)/SR
    f=440.0 * 2**((48-57)/12)  # content pitch: A-4 sounds at 440 Hz
    y=np.zeros(n)
    for h in range(1,9,2):
        y += (1.0/h**1.0)*np.sin(2*np.pi*h*f*t)
    e = exp_env(n, 0.10, a=0.002)
    return y*e*1.3

def pad_chord(tones, dur=3.6, bright=7):
    """tones: list of semitone names (natural pitch). detuned saw stack."""
    n=int(dur*SR); t=np.arange(n)/SR
    y=np.zeros(n)
    rng=np.random.default_rng(10)
    for tn in tones:
        f=hz(semi(tn))
        for det, amp in [(1.0,0.6),(1.003,0.22),(0.997,0.22)]:
            for h in range(1,bright+1):
                y += amp*(1.0/h**1.35)*np.sin(2*np.pi*f*det*h*t + rng.uniform(0,6.28))
    e = env_ad(n, 0.45, rel=0.35)
    return y*e*0.8

def pluck():
    dur=1.4; n=int(dur*SR); t=np.arange(n)/SR
    f=659.26 * 2**((48-64)/12)  # content pitch: tracker note E-5 (semi 64) sounds at 659 Hz
    y = np.sin(2*np.pi*f*t)*np.exp(-t/0.30)
    y += 0.5*np.sin(2*np.pi*f*2.01*t)*np.exp(-t/0.18)
    y += 0.25*np.sin(2*np.pi*f*3.0*t)*np.exp(-t/0.12)
    y += 0.12*np.sin(2*np.pi*f*5.01*t)*np.exp(-t/0.08)
    e = env_ad(n, 0.002, rel=0.10)
    return y*e*1.2

def stab(tones, dur=0.32):
    n=int(dur*SR); t=np.arange(n)/SR
    y=np.zeros(n)
    for tn in tones:
        f=hz(semi(tn))
        for h in range(1,8,2):
            y += (1.0/h**1.0)*np.sin(2*np.pi*h*f*t)
    e = exp_env(n, 0.11, a=0.002)
    return y*e*1.4

def riser():
    dur=1.7; n=int(dur*SR); t=np.arange(n)/SR
    rng=np.random.default_rng(7)
    noise = rng.normal(0,1,n)
    # rising one-pole highpass
    out=np.zeros(n); lp=0.0
    cf = np.linspace(200, 9000, n)
    for i in range(n):
        alpha = cf[i]/SR
        lp = lp + alpha*(noise[i]-lp)
        hp = noise[i]-lp
        out[i]=hp
    # rising saw underneath
    f0=80.0; f1=900.0
    inst = np.cumsum(f0 + (f1-f0)*t/dur)/SR
    saw = 2*((inst*440)%1)-1
    sweep = lowpass(saw, 4000)
    y = out*0.8 + sweep*0.5
    e = np.linspace(0,1,n)**2.5
    nr = int(0.06*SR)
    e[-nr:] *= np.linspace(1,0,nr)
    return y*e

def impact():
    dur=0.7; n=int(dur*SR); t=np.arange(n)/SR
    f = 60*np.exp(-t/0.09)+30
    phase=2*np.pi*np.cumsum(f)/SR
    y = np.sin(phase)*np.exp(-t/0.22)
    rng=np.random.default_rng(8)
    noise = rng.normal(0,1,int(0.05*SR))*np.exp(-np.arange(int(0.05*SR))/(SR*0.012))
    y[:len(noise)] += noise*0.8
    y[:int(0.002*SR)]=0
    return y

def build_all(outdir='/workspace/snd'):
    os.makedirs(outdir, exist_ok=True)
    specs = {
        'kick': kick,
        'snare': snare,
        'chh': chh,
        'ohh': ohh,
        'crash': crash,
        'bass': bass,
        'lead1': lead1,
        'lead2': lead2,
        'arp': arp_sq,
        'pluck': pluck,
        'riser': riser,
        'impact': impact,
    }
    for k, fn in specs.items():
        save(k, fn(), path=outdir)
    # pads
    pads = {
        'pad_am': ['A-3','C-4','E-4','A-4'],
        'pad_f':  ['F-3','A-3','C-4','F-4'],
        'pad_c':  ['C-3','G-3','C-4','E-4'],
        'pad_g':  ['G-2','D-3','G-3','B-3'],
        'pad_e':  ['E-2','B-2','E-3','G#3'],
        'pad_dm': ['D-3','A-3','D-4','F-4'],
    }
    for k, tones in pads.items():
        save(k, pad_chord(tones), peak=24000, path=outdir)
    stabs = {
        'stab_am': ['A-3','C-4','E-4','A-4'],
        'stab_f':  ['F-3','A-3','C-4','F-4'],
        'stab_c':  ['C-3','E-3','G-3','C-4'],
        'stab_g':  ['G-2','B-2','D-3','G-3'],
        'stab_e':  ['E-2','G#2','B-2','E-3'],
    }
    for k, tones in stabs.items():
        save(k, stab(tones), peak=25000, path=outdir)

if __name__ == '__main__':
    build_all()
    print("samples written")
