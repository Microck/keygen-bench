import numpy as np, wave

def save(name, data, rate=33452):
    x = np.clip(data, -1, 1)
    pcm = (x*32000).astype('<i2')
    with wave.open(f'/workspace/samples/{name}.wav','wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    print(name, len(pcm))

N = 64  # samples per cycle (relative_note +12 => C-4 in tune)

def cycles(wavecycle, ncyc, decay_to, sustain):
    # repeat cycle with exponential amp decay to 'decay_to', then final cycle at sustain level
    out = []
    for i in range(ncyc):
        a = decay_to ** (i/(ncyc-1))
        out.append(wavecycle * a)
    out.append(wavecycle * sustain)
    return np.concatenate(out)

t = np.arange(N)/N
# 25% pulse lead
pulse = np.where(t < 0.25, 1.0, -1.0) - (2*0.25-1)  # dc-correct
pulse = pulse/np.max(np.abs(pulse))
lead = cycles(pulse, 90, 0.30, 0.30)
save('lead', lead*0.9)
print('lead loopstart', 90*N, 'looplen', N)

# 50% square soft (echo / pad / arp)
sq = np.where(t < 0.5, 1.0, -1.0)
soft = cycles(sq, 70, 0.5, 0.5)
save('square', soft*0.75)
print('square loopstart', 70*N, 'looplen', N)

# bass: saw + square mix, plucky
saw = 2*t - 1
bwave = 0.65*saw + 0.45*sq
bwave = bwave/np.max(np.abs(bwave))
bass = cycles(bwave, 50, 0.55, 0.55)
save('bass', bass*0.95)
print('bass loopstart', 50*N, 'looplen', N)

rate = 33452
# kick
dur = 0.16; n = int(dur*rate); tt = np.arange(n)/rate
f = 150*np.exp(-tt*22) + 42
ph = 2*np.pi*np.cumsum(f)/rate
k = np.sin(ph)*np.exp(-tt*16)
k[:60] += np.random.RandomState(1).randn(60)*0.3*np.linspace(1,0,60)
save('kick', k*0.95)

# snare
dur=0.19; n=int(dur*rate); tt=np.arange(n)/rate
rng = np.random.RandomState(2)
noise = rng.randn(n)
noise = np.diff(noise, prepend=0)*0.5 + noise*0.5
sn = noise*np.exp(-tt*24)*0.8 + np.sin(2*np.pi*185*tt)*np.exp(-tt*40)*0.7
save('snare', sn*0.85)

# closed hat
dur=0.05; n=int(dur*rate); tt=np.arange(n)/rate
rng=np.random.RandomState(3)
h = np.diff(rng.randn(n), prepend=0)
h = h/np.max(np.abs(h))*np.exp(-tt*80)
save('chat', h*0.7)

# open hat
dur=0.22; n=int(dur*rate); tt=np.arange(n)/rate
rng=np.random.RandomState(4)
h = np.diff(rng.randn(n), prepend=0)
h = h/np.max(np.abs(h))*np.exp(-tt*16)
save('ohat', h*0.65)

# crash-ish noise sweep
dur=0.9; n=int(dur*rate); tt=np.arange(n)/rate
rng=np.random.RandomState(5)
c = np.diff(rng.randn(n), prepend=0)
c = c/np.max(np.abs(c))*np.exp(-tt*5)
save('crash', c*0.7)
