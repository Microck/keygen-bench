"""Original instrument synthesis for the keygen tune.

Every sample is generated in the domain it is *heard* (real pitch of its
reference note, real envelope seconds) and then converted into the sample
content the tracker needs:  content[i] = heard(i / s)  with
s = playback rate the engine applies at the reference note
(engine root note = label C-5, note names keep standard pitch meaning).
"""
import sys; sys.path.insert(0,'/workspace/tools')
import numpy as np, os, re, wave
from wav import save_wav

RATE = 44100
OUT  = '/workspace/samples'
os.makedirs(OUT, exist_ok=True)
rng  = np.random.default_rng(20240930)

_PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,
       'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def label_semi(lbl):
    m = re.match(r'^([A-G][#b]?)[- ]?(-?\d+)$', lbl.strip())
    pc = m.group(1)
    if pc.endswith('b'): pc = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}[pc]
    return (int(m.group(2))-4)*12 + _PC[pc]      # semitones above C-4 (middle C)
def freq_of(lbl):  return 261.625565*2.0**(label_semi(lbl)/12.0)
def scale_of(lbl): return 2.0**((label_semi(lbl)-12)/12.0)   # engine root = C-5

def to_content(heard, ref):
    s = scale_of(ref)
    n = max(2,int(round(len(heard)*s)))
    idx = np.clip(np.arange(n)/s, 0, len(heard)-1e-9)
    return np.interp(idx, np.arange(len(heard)), heard)

def norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x*(peak/m) if m > 1e-9 else x
def fade(x, fin=0.0, fout=0.004):
    x = np.array(x, float); ni, no = int(fin*RATE), int(fout*RATE)
    if ni: x[:ni] *= np.linspace(0,1,ni)
    if no and no < len(x): x[-no:] *= np.linspace(1,0,no)
    return x
def softclip(x, d=1.2): return np.tanh(x*d)/np.tanh(d)
def adsr(t, a, d, s, r, total, sus=0.6):
    y = np.clip(t/a, 0, 1)
    y = np.minimum(1.0, y*(1+ (0.0)))
    dec = sus + (1-sus)*np.exp(-np.clip(t-a,0,None)/d)
    rel = np.clip((total-t)/r, 0, 1)
    return y*dec*rel
def hp_noise(x, fc):
    y = np.zeros(len(x)); lp = 0.0; a = 2*np.pi*fc/(RATE+2*np.pi*fc)
    for i in range(len(x)):
        lp += a*(x[i]-lp); y[i] = x[i]-lp
    return y
def lpf(x, a):
    if np.isscalar(a): a = np.full(len(x), float(a))
    y = np.zeros(len(x)); acc = 0.0
    for i in range(len(x)):
        acc += a[i]*(x[i]-acc); y[i] = acc
    return y
def sawstack(t, f0, detunes, amps, nh=24):
    """band-limited detuned saw stack (additive)"""
    ph = 2*np.pi*f0*t
    x = np.zeros(len(t))
    for d,A in zip(detunes, amps):
        det = 2.0**(d/1200.0)
        y = np.zeros(len(t))
        for k in range(1, nh+1):
            y += np.sin(k*ph*det + 0.35*k)/k
        x += A*(y*2/np.pi)
    return x

def emit(name, ref, heard, peak):
    save_wav(f'{OUT}/{name}.wav', norm(fade(to_content(heard, ref), 0, 0.003), peak), RATE)

# ------------------------------- drums (ref C-5, rate 1.0) -------------------------------
def kick():
    ref='C-5'; dur=0.44; t=np.arange(int(dur*RATE))/RATE
    f = 47 + 140*np.exp(-t/0.030)
    body = np.sin(2*np.pi*np.cumsum(f)/RATE)
    amp  = np.minimum(1.0, t/0.0025)*np.exp(-t/0.085)
    x = softclip(body*amp*1.7, 1.5)
    L = int(0.012*RATE)
    x[:L] += 0.55*hp_noise(rng.standard_normal(L), 1800)*np.exp(-np.arange(L)/RATE/0.0035)
    x += 0.10*np.sin(2*np.pi*108*t)*np.exp(-t/0.10)
    emit('kick', ref, x, 0.94)

def clap():
    ref='C-5'; dur=0.38; t=np.arange(int(dur*RATE))/RATE; x=np.zeros(len(t))
    for i,off in enumerate([0.0,0.010,0.020,0.030]):
        k=int(off*RATE); ln=int((0.05 if i<3 else 0.26)*RATE)
        x[k:k+ln] += hp_noise(rng.standard_normal(ln), 850)*np.exp(-np.arange(ln)/RATE/(0.011 if i<3 else 0.070))
    x += 0.46*np.sin(2*np.pi*318*t)*np.exp(-t/0.06) + 0.26*np.sin(2*np.pi*176*t)*np.exp(-t/0.10)
    emit('clap', ref, x, 0.92)

def hats():
    for name,dur,tau,fc,pk in [('hathc',0.10,0.014,6400,0.62),('hatop',0.52,0.12,5500,0.46)]:
        t=np.arange(int(dur*RATE))/RATE
        x = hp_noise(rng.standard_normal(len(t)), fc)*np.exp(-t/tau)
        x += 0.20*np.sin(2*np.pi*fc*1.4*t)*np.exp(-t/(tau*0.6))
        for fr in (5100,6900,8300,10700):
            x += 0.05*np.sin(2*np.pi*fr*t+0.7)*np.exp(-t/(tau*1.5))
        emit(name, 'C-5', x, pk)

def crash():
    t=np.arange(int(2.1*RATE))/RATE
    x = hp_noise(rng.standard_normal(len(t)), 2800)*np.exp(-t/0.52)
    for fr in (4200,5300,6100,7400,9100,11500):
        x += 0.09*np.sin(2*np.pi*fr*t+rng.uniform(0,6))*np.exp(-t/rng.uniform(0.3,0.85))
    x *= 1.0-0.45*np.exp(-t/0.02)
    emit('crash','C-5', x, 0.58)

def tom():
    ref='D-5'; dur=0.5; t=np.arange(int(dur*RATE))/RATE
    f = 165 + 200*np.exp(-t/0.045)
    x = np.sin(2*np.pi*np.cumsum(f)/RATE)*np.exp(-t/0.19)
    x += 0.32*hp_noise(rng.standard_normal(len(t)), 1300)*np.exp(-t/0.018)
    emit('tom', ref, softclip(x,1.1), 0.72)

def riser():
    ref='C-5'; dur=2.3; t=np.arange(int(dur*RATE))/RATE
    n = rng.standard_normal(len(t))
    fc = 360*2.0**(6.0*t/dur); a = 2*np.pi*fc/(RATE+2*np.pi*fc)
    lpv = np.zeros(len(t)); acc=0.0
    for i in range(len(t)):
        acc += a[i]*(n[i]-acc); lpv[i]=acc
    x = (n-lpv)*(t/dur)**2.1
    f2 = 320*2.0**(5.0*t/dur)
    x += 0.22*np.sin(2*np.pi*np.cumsum(f2)/RATE)*(t/dur)**1.6
    save_wav(f'{OUT}/riser.wav', norm(fade(x,0,0.10),0.55), RATE)

# ------------------------------- tonal -------------------------------
def bass():
    ref='A-2'; dur=0.30; t=np.arange(int(dur*RATE))/RATE
    f0 = freq_of(ref)
    ph = 2*np.pi*f0*t
    sw = np.zeros(len(t)); sq=np.zeros(len(t))
    for k in range(1,42):
        sw += np.sin(k*ph)/k
        if k%2: sq += np.sin(k*ph)/k
    x = 0.72*(sw*2/np.pi) + 0.42*(sq*4/np.pi)
    fc = 300 + 2750*np.exp(-t/0.042)
    x = lpf(x, np.minimum(0.95, 2*np.pi*fc/RATE))
    x = softclip(x*np.minimum(1.0, t/0.0035)*np.exp(-t/0.072), 1.25)
    emit('bass', ref, x, 0.92)

def sub():
    ref='A-1'; dur=0.55; t=np.arange(int(dur*RATE))/RATE
    ph = 2*np.pi*freq_of(ref)*t
    x = np.sin(ph) + 0.30*np.sin(2*ph) + 0.10*np.sin(3*ph)
    x = softclip(x*np.minimum(1.0,t/0.010)*(0.30+0.70*np.exp(-t/0.17)), 1.1)
    emit('sub', ref, x, 0.86)

def lead():
    ref='D-5'; dur=1.00; t=np.arange(int(dur*RATE))/RATE
    vib = np.sin(2*np.pi*5.7*t)*0.0125*np.clip((t-0.09)/0.30,0,1)
    f = freq_of(ref)*2.0**vib
    ph = 2*np.pi*np.cumsum(f)/RATE
    x = sawstack(t, 1.0, [-16,-8,0,8,16], [0.30,0.35,0.45,0.35,0.28], nh=22) * 0  # placeholder
    # build with the (modulated) phase directly
    x = np.zeros(len(t))
    for d,A in zip([-16,-8,0,8,16],[0.30,0.35,0.45,0.35,0.28]):
        det = 2.0**(d/1200.0)
        y = np.zeros(len(t))
        for k in range(1,24):
            y += np.sin(k*ph*det + 0.4*k)/k
        x += A*(y*2/np.pi)
    x += 0.16*np.sin(2*ph)
    x = lpf(x, np.minimum(0.92, 2*np.pi*3400/RATE))
    x = softclip(x*adsr(t, 0.008, 0.16, 0.52, 0.30, dur), 1.3)
    emit('lead', ref, x, 0.88)

def stab():
    ref='A-4'; dur=0.42; t=np.arange(int(dur*RATE))/RATE
    ph = 2*np.pi*freq_of(ref)*t
    x = np.zeros(len(t))
    for d,A in zip([-25,-12,-5,0,5,12,25],[0.24,0.30,0.35,0.40,0.35,0.30,0.24]):
        det = 2.0**(d/1200.0); y=np.zeros(len(t))
        for k in range(1,18): y += np.sin(k*ph*det+0.3*k)/k
        x += A*(y*2/np.pi)
    x = lpf(x, np.minimum(0.92, 2*np.pi*3000/RATE))
    x = softclip(x*np.clip(t/0.005,0,1)*np.exp(-t/0.075), 1.3)
    emit('stab', ref, x, 0.78)

def pluck():
    ref='E-5'; dur=0.26; t=np.arange(int(dur*RATE))/RATE
    ph = 2*np.pi*freq_of(ref)*t
    x = np.zeros(len(t))
    for i,(A,ta) in enumerate(zip([1.0,.6,.4,.28,.18,.11,.07],[0.075,0.055,0.04,0.03,0.022,0.016,0.012])):
        x += A*np.sin((i+1)*ph)*np.exp(-t/ta)
    x += 0.22*np.sin(2.01*ph)*np.exp(-t/0.03)
    x = lpf(x*np.clip(t/0.0012,0,1), np.minimum(0.95, 2*np.pi*5200/RATE))
    emit('pluck', ref, x, 0.78)

def bell():
    ref='E-5'; dur=1.05; t=np.arange(int(dur*RATE))/RATE
    f0 = freq_of(ref)
    phc = 2*np.pi*f0*t; phm = 2*np.pi*3.02*f0*t
    idx = np.exp(-t/0.075)*7.5
    x = np.sin(phc + idx*np.sin(phm)) + 0.30*np.sin(2*phc)*np.exp(-t/0.35)
    x = x*np.clip(t/0.002,0,1)*np.exp(-t/0.33)
    emit('bell', ref, x, 0.70)

def pad():
    ref='C-4'; dur=2.3; t=np.arange(int(dur*RATE))/RATE
    f0 = freq_of(ref)
    ph = 2*np.pi*np.cumsum(f0*(1+0.004*np.sin(2*np.pi*4.3*t)))/RATE
    x = np.zeros(len(t))
    for d,A in zip([-14,-7,-2.5,0,2.5,7,14],[0.24,0.30,0.35,0.40,0.35,0.30,0.24]):
        det = 2.0**(d/1200.0); y=np.zeros(len(t))
        for k in range(1,15): y += np.sin(k*ph*det+0.25*k)/k
        x += A*(y*2/np.pi)
    x += 0.12*np.sin(2*ph)
    x = lpf(x, np.minimum(0.85, 2*np.pi*(1250+600*np.sin(2*np.pi*0.3*t))/RATE))
    x = softclip(x*np.clip(t/0.30,0,1)*(0.55+0.45*np.exp(-np.clip(t-0.3,0,None)/1.3))
                 *np.clip((dur-t)/0.55,0,1)**1.2, 1.15)
    emit('pad', ref, x, 0.60)

for fn in [kick, clap, hats, crash, tom, riser, bass, sub, lead, stab, pluck, bell, pad]:
    fn()
print("built:", sorted(os.listdir(OUT)))
