import numpy as np, wave, os, json, math
SR = 44100
os.makedirs('wavs', exist_ok=True)

def write_wav(path, data):
    arr = (np.clip(data,-1,1)*32767).astype(np.int16)
    with wave.open(path,'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(arr.tobytes())

def make_loop(form, cycles=1, freq=261.625565):
    L = int(round(SR * cycles / freq))
    t = np.arange(L) / SR
    ph = (t*freq) % 1.0
    if form == 'square':
        return np.sign(np.sin(2*np.pi*freq*t))
    if form == 'saw':
        return 2*ph - 1
    if form == 'triangle':
        return 2*np.abs(2*ph-1)-1
    if form == 'pulse25':
        return np.where(ph < 0.25, 1.0, -1.0)
    return np.sin(2*np.pi*freq*t)

# Kick
L=int(SR*0.28); t=np.arange(L)/SR
phase=0.0; kick=np.zeros(L)
for i in range(L):
    frac=i/L
    f=180.0*(45.0/180.0)**(frac**0.9)
    phase+=2*np.pi*f/SR
    kick[i]=math.sin(phase)
kick*=np.exp(-t/0.12)
np.random.seed(1)
click=np.random.uniform(-1,1,int(SR*0.003))
kick[:len(click)] += 0.6*click
write_wav('wavs/kick.wav', kick)

# Snare
L=int(SR*0.22); t=np.arange(L)/SR
noise=np.random.uniform(-1,1,L)
noise=np.convolve(noise, np.ones(8)/8, mode='same')
snap=np.sin(2*np.pi*220*t)*np.exp(-t/0.04)
snare=0.7*noise*np.exp(-t/0.08) + 0.4*snap
write_wav('wavs/snare.wav', snare)

# Hihat
L=int(SR*0.06); noise=np.random.uniform(-1,1,L)
noise = noise - np.convolve(noise, np.ones(20)/20, mode='same')
hh=noise*np.exp(-np.arange(L)/(SR*0.015))
write_wav('wavs/hihat.wav', hh)

# Bass saw loop
bass=make_loop('saw')
write_wav('wavs/bass.wav', bass)

# Lead square loop
lead=make_loop('square')
write_wav('wavs/lead.wav', lead)

# Arp pulse25 loop
arp=make_loop('pulse25')
write_wav('wavs/arp.wav', arp)

# Pad triangle+saw loop
pad=0.6*make_loop('triangle') + 0.4*make_loop('saw')
write_wav('wavs/pad.wav', pad)

samples = [
    ('Kick', 'kick.wav', False, 32, 128),
    ('Snare', 'snare.wav', False, 32, 128),
    ('Hihat', 'hihat.wav', False, 26, 168),
    ('Bass', 'bass.wav', True, 26, 128),
    ('Lead', 'lead.wav', True, 26, 128),
    ('Arp', 'arp.wav', True, 26, 128),
    ('Pad', 'pad.wav', True, 22, 96),
]

batch=[]
batch.append({"name":"module_new","arguments":{"channels":8,"name":"Keygen Odyssey"}})
for idx,(name,filename,loop,vol,pan) in enumerate(samples, start=1):
    batch.append({"name":"instrument_set","arguments":{"instrument":idx,"name":name}})
    batch.append({"name":"sample_load","arguments":{"instrument":idx,"sample":0,"path":"wavs/"+filename}})
    # preserve 16-bit (bit4=16) + loop bit0 if needed
    flags = 16 | (1 if loop else 0)
    # get length for loop
    with wave.open('wavs/'+filename,'rb') as f:
        length = f.getnframes()
    batch.append({"name":"sample_set","arguments":{"instrument":idx,"sample":0,"volume":vol,"panning":pan,"relative_note":0,"finetune":0,"loop_start":0,"loop_length":length if loop else 0,"flags":flags}})

batch.append({"name":"song_set","arguments":{"name":"Keygen Odyssey","bpm":155,"speed":6,"length":8,"loop_start":2}})
for p in range(8):
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
    batch.append({"name":"pattern_clear","arguments":{"pattern":p}})

with open('setup_batch.json','w') as f:
    json.dump(batch,f)
print('setup batch entries', len(batch))
