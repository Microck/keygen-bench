import os, wave, struct, math, numpy as np
os.makedirs('/workspace/samples', exist_ok=True)
SR=44100

def write_wav(path, data, sr=SR):
    # data float -1..1
    data = np.clip(data, -1.0, 1.0)
    ints = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(ints.tobytes())

# Looped waveforms at C4 (~261.63Hz): length ~168
L = 168
# Square
sq = np.zeros(L)
sq[:L//2] = 0.8
sq[L//2:] = -0.8
write_wav('/workspace/samples/square.wav', sq)
# Saw
saw = np.linspace(0.7, -0.7, L, endpoint=False)
write_wav('/workspace/samples/saw.wav', saw)
# Triangle
tri = np.zeros(L)
for i in range(L):
    x = i/L
    tri[i] = 4*abs(x-0.5)-1
write_wav('/workspace/samples/triangle.wav', tri*0.8)
# Pulse 25%
pulse = np.where(np.arange(L) < L//4, 0.8, -0.8)
write_wav('/workspace/samples/pulse.wav', pulse)

# Kick ~0.12s
N=int(SR*0.12)
t=np.arange(N)/SR
freq=180*np.exp(-t*25)
env=np.exp(-t*18)
kick=np.sin(2*np.pi*np.cumsum(freq)/SR)*env*0.95
write_wav('/workspace/samples/kick.wav', kick)

# Snare ~0.18s
N=int(SR*0.18)
t=np.arange(N)/SR
noise=np.random.uniform(-1,1,N)
# simple low-pass via moving average
noise_lp=np.convolve(noise, np.ones(8)/8, mode='same')
snare=noise_lp*np.exp(-t*12)
# add tonal body
body=np.sin(2*np.pi*180*t)*np.exp(-t*25)*0.4
snare=(snare+body)*0.9
write_wav('/workspace/samples/snare.wav', snare)

# Hihat ~0.08s
N=int(SR*0.08)
t=np.arange(N)/SR
noise=np.random.uniform(-1,1,N)
# high-pass-ish via differentiator-ish and clipping
hp=noise[2:]-noise[:-2]
hp=np.pad(hp,(1,1),mode='constant')
hat=hp*np.exp(-t*45)
write_wav('/workspace/samples/hihat.wav', hat*0.7)

print('samples created')
