"""
Source script for generating the keygen tune.
Run in an environment with Python 3, NumPy, and the ft2 CLI tools.
"""
import numpy as np, wave, json, os, subprocess

SR = 44100

def save_wav(path, data):
    data = np.clip(data, -1.0, 1.0)
    data_int16 = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(data_int16.tobytes())

os.makedirs('samples', exist_ok=True)

# Kick: sine sweep 180->50 Hz, decay
dur = 0.25; n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
freq = 180.0 * np.exp(np.log(50/180)*(t/dur))
phase = 2*np.pi*np.cumsum(freq)/SR
kick = np.sin(phase)*np.exp(-t/0.12)*0.9
save_wav('samples/kick.wav', kick)

# Snare: noise + body + snap
dur = 0.2; n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
noise = np.random.randn(n); env = np.exp(-t/0.06)
body = np.sin(2*np.pi*180*t)*np.exp(-t/0.03)
snap = np.sin(2*np.pi*400*t)*np.exp(-t/0.02)
snare = (noise*env*0.7 + body*0.5 + snap*0.3)*0.8
save_wav('samples/snare.wav', snare)

# Closed hi-hat: short high-passed noise
dur = 0.05; n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
hh = np.random.randn(n)*np.exp(-t/0.015)
hh = hh - np.convolve(hh, np.ones(5)/5, mode='same')
hh *= 0.5
save_wav('samples/closed_hh.wav', hh)

# Open hi-hat: longer high-passed noise
dur = 0.25; n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
ohh = np.random.randn(n)*np.exp(-t/0.08)
ohh = ohh - np.convolve(ohh, np.ones(5)/5, mode='same')
ohh *= 0.5
save_wav('samples/open_hh.wav', ohh)

# Bass: square wave loop with attack click
period = 168
bass = np.array([1.0 if i < period/2 else -1.0 for i in range(period)])
for i in range(4):
    bass[i] = bass[i]*0.5 + ((i/4)*2-1)*0.5
bass = np.convolve(bass, np.ones(3)/3, mode='same')*0.7
save_wav('samples/bass.wav', bass)

# Lead: detuned saw loop (4 cycles)
period = 168; cycles = 4; n = period*cycles
lead = np.zeros(n)
for i in range(n):
    s1 = ((i/period)%1)*2-1
    s2 = ((i/(period-0.5))%1)*2-1
    lead[i] = 0.6*s1 + 0.4*s2
lead = np.convolve(lead, np.ones(3)/3, mode='same')*0.6
save_wav('samples/lead.wav', lead)

# Pluck: sine with harmonics, decay
dur = 0.5; n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
fund = 440.0
pluck = np.sin(2*np.pi*fund*t)*np.exp(-t/0.15)
pluck += 0.3*np.sin(2*np.pi*fund*2*t)*np.exp(-t/0.1)
pluck += 0.1*np.sin(2*np.pi*fund*3*t)*np.exp(-t/0.08)
pluck *= 0.7
save_wav('samples/pluck.wav', pluck)

# Crash: long noise decay, high-passed
dur = 1.0; n = int(SR*dur); t = np.linspace(0, dur, n, endpoint=False)
crash = np.random.randn(n)*np.exp(-t/0.4)
crash = crash - np.convolve(crash, np.ones(7)/7, mode='same')
crash *= 0.6
save_wav('samples/crash.wav', crash)

print("Samples generated.")
