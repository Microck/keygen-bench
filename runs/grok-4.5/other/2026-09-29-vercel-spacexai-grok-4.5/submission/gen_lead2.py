import numpy as np, wave, os
SR=44100
OUT="/workspace/samples"

def save_wav(path, data):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())

# Brighter lead with slight PWM feel, longer for legato
freq = 523.25
dur = 0.7
n = int(SR*dur)
t = np.arange(n)/SR
sig = np.zeros(n)
for h in range(1, 24):
    amp = (1.0/h) * (0.55 if h%2==0 else 1.0)
    amp *= np.exp(-(h-1)*0.08)
    sig += amp * np.sin(2*np.pi*freq*h*t)
# detuned twin
twin = np.zeros(n)
for h in range(1, 12):
    twin += (1.0/h)*np.sin(2*np.pi*freq*1.004*h*t+0.2)
sig = 0.72*sig + 0.28*twin
# soft saturate
sig = np.tanh(sig * 1.3)
attack = 1 - np.exp(-t*300)
sustain = np.ones(n)
rel_n = int(0.2*SR)
sustain[-rel_n:] = np.linspace(1, 0, rel_n)
# body decay mild
body = np.exp(-t*1.2)*0.3 + 0.7
env = attack * sustain * body
sig *= env
sig = sig / np.max(np.abs(sig)) * 0.85
save_wav(f"{OUT}/lead.wav", sig)

# Better arp - more metallic pluck
freq = 523.25
dur = 0.22
n = int(SR*dur)
t = np.arange(n)/SR
sig = np.zeros(n)
for h in range(1, 30):
    amp = 1.0/(h**0.85)
    sig += amp * np.sin(2*np.pi*freq*h*t + h*0.05)
env = np.exp(-t*18) * (1-np.exp(-t*500))
sig *= env
sig = np.tanh(sig*1.1)
sig = sig / np.max(np.abs(sig)) * 0.8
save_wav(f"{OUT}/arp.wav", sig)

# Punchier bass - slightly filtered saw, seamless loop
freq = 65.406
periods = 8
n = int(round(SR * periods / freq))
t = np.arange(n)/SR
sig = np.zeros(n)
for h in range(1, 16):
    amp = 1.0/h
    # lowpass-ish
    amp *= 1.0 / (1 + (h/8)**2)
    sig += amp * np.sin(2*np.pi*freq*h*t)
sig = np.tanh(sig*1.5)
# remove DC and ensure loop
sig = sig - sig.mean()
# crossfade ends for seamless
xf = 64
sig[-xf:] = sig[-xf:]*np.linspace(1,0,xf) + sig[:xf]*np.linspace(0,1,xf)
sig = sig / np.max(np.abs(sig)) * 0.88
save_wav(f"{OUT}/bass.wav", sig)
print("bass len", len(sig))

# Soft pad with slow beat - longer loop
freq = 130.81
periods = 32
n = int(round(SR * periods / freq))
t = np.arange(n)/SR
sig = 0.4*np.sin(2*np.pi*freq*t)
sig += 0.25*np.sin(2*np.pi*freq*1.002*t + 0.3)
sig += 0.2*np.sin(2*np.pi*freq*0.998*t + 1.0)
sig += 0.15*np.sin(2*np.pi*freq*2*t)/2
sig += 0.1*np.sin(2*np.pi*freq*3*t)/3
sig += 0.08*(2*np.abs(2*((t*freq)%1)-1)-1)  # tri
sig = sig - sig.mean()
xf = 128
sig[-xf:] = sig[-xf:]*np.linspace(1,0,xf) + sig[:xf]*np.linspace(0,1,xf)
sig = sig / np.max(np.abs(sig)) * 0.65
save_wav(f"{OUT}/pad.wav", sig)
print("pad len", len(sig))
print("ok")
