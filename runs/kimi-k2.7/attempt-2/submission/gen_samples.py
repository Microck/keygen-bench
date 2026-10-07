import numpy as np
import wave, struct, os

SAMPLE_RATE = 44100

def save_wav(path, data, rate=SAMPLE_RATE):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())

def kick():
    duration = 0.25
    N = int(SAMPLE_RATE*duration)
    t = np.linspace(0, duration, N, False)
    f = 200 * np.exp(-t*8) + 40
    phase = np.cumsum(2*np.pi*f/SAMPLE_RATE)
    sine = np.sin(phase)
    amp = np.exp(-t*12)
    click = np.random.uniform(-1,1,size=N) * np.exp(-t*120) * 0.5
    return sine*amp + click

def snare():
    duration = 0.25
    N = int(SAMPLE_RATE*duration)
    t = np.linspace(0, duration, N, False)
    noise = np.random.uniform(-1,1,size=N)
    noise = np.diff(noise, prepend=0)
    env = np.exp(-t*15)
    tone = np.sin(2*np.pi*180*t) * np.exp(-t*25) * 0.3
    return noise*env*0.7 + tone

def hihat():
    duration = 0.08
    N = int(SAMPLE_RATE*duration)
    t = np.linspace(0, duration, N, False)
    noise = np.random.uniform(-1,1,size=N)
    for _ in range(3):
        noise = np.diff(noise, prepend=0)
    env = np.exp(-t*50)
    return noise*env*0.6

def crash():
    duration = 1.0
    N = int(SAMPLE_RATE*duration)
    t = np.linspace(0, duration, N, False)
    noise = np.random.uniform(-1,1,size=N)
    for _ in range(2):
        noise = np.diff(noise, prepend=0)
    env = np.exp(-t*4)
    return noise*env*0.5

def saw_cycle(freq):
    samples = int(SAMPLE_RATE/freq)
    t = np.arange(samples)/SAMPLE_RATE
    out = np.zeros(samples)
    for k in range(1, 40):
        out += np.sin(2*np.pi*k*freq*t)/k
    out = out/np.max(np.abs(out))*0.8
    return out

def square_cycle(freq, width=0.5):
    samples = int(SAMPLE_RATE/freq)
    t = np.arange(samples)/SAMPLE_RATE
    out = np.zeros(samples)
    for k in range(1, 40, 2):
        out += np.sin(2*np.pi*k*freq*t)/k * (np.sin(np.pi*k*width)*2/(np.pi*k))
    mx = np.max(np.abs(out))
    if mx>0:
        out = out/mx*0.8
    return out

def bass():
    return square_cycle(65.41)

def lead():
    return saw_cycle(261.63)

def arp():
    return square_cycle(523.25, width=0.3)

def pad():
    s1 = saw_cycle(130.81)
    s2 = saw_cycle(130.81*1.005)
    minlen = min(len(s1), len(s2))
    out = s1[:minlen] + s2[:minlen]
    out = out/np.max(np.abs(out))*0.7
    return out

os.makedirs('samples', exist_ok=True)

samples = {
    'kick.wav': kick(),
    'snare.wav': snare(),
    'hihat.wav': hihat(),
    'crash.wav': crash(),
    'bass.wav': bass(),
    'lead.wav': lead(),
    'arp.wav': arp(),
    'pad.wav': pad(),
}

for name, data in samples.items():
    save_wav(f'samples/{name}', data)
    print(name, len(data))
