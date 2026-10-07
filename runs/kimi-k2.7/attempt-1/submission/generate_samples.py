import numpy as np, wave, os

SR = 44100

def save(name, data, target_peak=0.7):
    peak = np.max(np.abs(data))
    if peak > 0:
        data = data / peak * target_peak
    data = np.clip(data, -1, 1)
    data16 = (data * 32767).astype(np.int16)
    with wave.open(f'{name}.wav','wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data16.tobytes())

# Kick
t = np.linspace(0, 0.18, int(SR*0.18), False)
f0, f1 = 150, 42
phase = 2*np.pi*(f0*t + (f1-f0)*t*t/(2*0.18))
sine = np.sin(phase)
env = np.exp(-t/0.055)
click = np.random.uniform(-1,1,size=len(t)) * np.exp(-t/0.003) * 0.25
save('kick', sine*env + click, 0.9)

# Snare
noise = np.random.uniform(-1,1,size=len(t))
tone = np.sin(2*np.pi*180*t) + 0.5*np.sin(2*np.pi*250*t)
env = np.exp(-t/0.075)
save('snare', (noise*0.6 + tone*0.35)*env, 0.85)

# Hihat
t2 = np.linspace(0, 0.05, int(SR*0.05), False)
noise = np.random.uniform(-1,1,size=len(t2))
hp = noise - np.roll(noise, 2); hp[:2]=0
env = np.exp(-t2/0.012)
save('hihat', hp*env, 0.55)

# Bass saw C-2 loop
N = int(SR/65.40639)
t = np.linspace(0, 1, N, False)
saw = sum(np.sin(2*np.pi*k*t)/k for k in range(1,16))
save('bass_saw', saw, 0.7)

# Lead square-ish C-4 loop
N = int(SR/261.6255)
t = np.linspace(0, 1, N, False)
sq = np.sign(np.sin(2*np.pi*t))
sq = np.convolve(sq, np.ones(3)/3, mode='same')
save('lead_sq', sq, 0.65)

# Arp pad pulse C-5 loop
N = int(SR/523.2511)
t = np.linspace(0, 1, N, False)
pulse = np.where(t < 0.3, 1.0, -0.5)
pulse = np.convolve(pulse, np.ones(3)/3, mode='same')
save('arp_pad', pulse, 0.55)

# Bell FM C-6 loop
N = int(SR/1046.502)
t = np.linspace(0, 1, N, False)
mod = np.sin(2*np.pi*3.5*t)
bell = np.sin(2*np.pi*t + 0.8*mod)
save('bell', bell, 0.55)
