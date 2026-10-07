import numpy as np, wave, math
sr=44100
def save(name, sig):
    sig = np.clip(sig, -1, 1)
    data = np.int16(sig * 32767)
    with wave.open(name,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data.tobytes())
    print(name, len(data))

# Kick
N=int(sr*0.22)
t=np.arange(N)/sr
start=180.0; end=58.0
# exponential frequency sweep
freq=end + (start-end)*np.exp(-t/0.035)
phase=np.cumsum(2*np.pi*freq/sr)
body=np.sin(phase)
# click (filtered noise burst)
click_len=int(sr*0.004)
click=np.zeros(N)
ck=np.random.randn(click_len)
ck=ck[1:]-ck[:-1]
ck=np.concatenate(([0],ck))
env_click=np.exp(-np.arange(click_len)/2.0)
click[:click_len]=ck*env_click*0.4
env=np.exp(-t/0.11)
# small pitch bend for punch
drive=1.0+0.3*np.exp(-t/0.01)
kick=(body*drive + click)*env
save('kick.wav', kick)

# Snare
N=int(sr*0.18)
t=np.arange(N)/sr
body=np.sin(2*np.pi*220*t)*np.exp(-t/0.055)
noise=np.random.randn(N)
# high pass (difference twice)
hp=noise[1:]-noise[:-1]; hp=np.concatenate(([0],hp))
hp=hp[1:]-hp[:-1]; hp=np.concatenate(([0],hp))
env=np.exp(-t/0.10)
# snap (very short high noise burst)
snap_len=int(sr*0.015)
snap=np.zeros(N)
sn=np.random.randn(snap_len); sn=sn[1:]-sn[:-1]; sn=np.concatenate(([0],sn))
snap[:snap_len]=sn*np.exp(-np.arange(snap_len)/1.5)*0.5
snare=(body*0.55 + hp*0.35 + snap*0.25)*env
save('snare.wav', snare)

# Hihat
N=int(sr*0.07)
t=np.arange(N)/sr
noise=np.random.randn(N)
hp=noise[1:]-noise[:-1]; hp=np.concatenate(([0],hp))
hp=hp[1:]-hp[:-1]; hp=np.concatenate(([0],hp))
# ring
ring=np.sin(2*np.pi*8200*t)*np.exp(-t/0.015)
env=np.exp(-t/0.012)
hat=(hp*0.55 + ring*0.3)*env
save('hihat.wav', hat)

# Loop waveforms
L=168
print('loop length', L, 'base', sr/L)

def bl_saw(L, harmonics, cutoff=None):
    x=np.arange(L)/L
    y=np.zeros(L)
    for n in range(1, harmonics+1):
        amp=1.0/n
        if cutoff:
            amp*=math.exp(-(n-1)/cutoff)
        # random phases to avoid static timbre? Keep deterministic.
        y += amp*np.sin(2*np.pi*n*x)
    return y

def bl_square(L, harmonics, cutoff=None):
    x=np.arange(L)/L
    y=np.zeros(L)
    for n in range(1, harmonics+1, 2):
        amp=1.0/n
        if cutoff:
            amp*=math.exp(-(n-1)/cutoff)
        y += amp*np.sin(2*np.pi*n*x)
    return y

def bl_pulse(L, duty, harmonics, cutoff=None):
    x=np.arange(L)/L
    y=np.zeros(L)
    for n in range(1, harmonics+1):
        amp=math.sin(math.pi*n*duty)/n
        if cutoff:
            amp*=math.exp(-(n-1)/cutoff)
        y += amp*np.sin(2*np.pi*n*x)
    return y

# Lead: saw with moderate lowpass cutoff (make brighter)
lead=bl_saw(L, 28, cutoff=8)
lead=lead/np.max(np.abs(lead))*0.9
save('lead.wav', lead)

# Pad: mix saw and square, rich
pad=0.6*bl_saw(L, 24, cutoff=6) + 0.4*bl_square(L, 24, cutoff=6)
pad=pad/np.max(np.abs(pad))*0.9
save('pad.wav', pad)

# Arp: narrow pulse bright
arp=bl_pulse(L, 0.25, 40, cutoff=12)
arp=arp/np.max(np.abs(arp))*0.85
save('arp.wav', arp)

# Bass: square+saw mix, bass-heavy
bass=0.7*bl_square(L, 18, cutoff=4) + 0.3*bl_saw(L, 18, cutoff=4)
bass=bass/np.max(np.abs(bass))*0.95
save('bass.wav', bass)
