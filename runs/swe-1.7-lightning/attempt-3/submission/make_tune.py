import wave, struct, math, json, os, numpy as np

SR = 44100
SAMPLE_DIR = '/workspace/samples'
BATCH_FILE = '/workspace/batch.json'
OUT_XM = '/workspace/submission/tune.xm'

os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUT_XM), exist_ok=True)

def save_wav(path, arr, rate=SR):
    arr = np.asarray(arr, dtype=np.float64)
    mx = np.max(np.abs(arr))
    if mx == 0:
        mx = 1
    arr = (arr / mx * 32767 * 0.9).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.setnframes(len(arr))
        w.writeframes(arr.tobytes())

def band_square(N, harmonics=21):
    t = np.linspace(0, 1, N, endpoint=False)
    s = np.zeros(N)
    for k in range(1, harmonics+1, 2):
        s += (1.0/k) * np.sin(2*np.pi*k*t)
    return s

def pulse(N, duty=0.25, harmonics=25):
    t = np.linspace(0, 1, N, endpoint=False)
    s = np.zeros(N)
    for k in range(1, harmonics+1):
        s += (np.sin(2*np.pi*k*duty)/k) * np.cos(2*np.pi*k*t)
    return s

def saw(N, harmonics=30):
    t = np.linspace(0, 1, N, endpoint=False)
    s = np.zeros(N)
    for k in range(1, harmonics+1):
        s += ((-1)**(k+1)) * (1.0/k) * np.sin(2*np.pi*k*t)
    return s

def triangle(N, harmonics=17):
    t = np.linspace(0, 1, N, endpoint=False)
    s = np.zeros(N)
    for k in range(1, harmonics+1, 2):
        s += ((-1)**((k-1)//2)) * (1.0/k**2) * np.sin(2*np.pi*k*t)
    return s

def tone_at_freq(shape_func, freq, dur=1.0, cycle_len=256):
    N2 = int(SR * dur)
    phase = (np.arange(N2) * freq / SR) % 1.0
    cycle = shape_func(cycle_len)
    idx = (phase * (cycle_len - 1)).astype(np.int32)
    return cycle[idx]

lead_sq = tone_at_freq(band_square, 261.63, 1.0)
pulse_w = tone_at_freq(pulse, 261.63, 1.0)
bass_sw = tone_at_freq(saw, 130.81, 1.0)
pad_tri = tone_at_freq(triangle, 261.63, 1.0)

save_wav(os.path.join(SAMPLE_DIR, 'lead_square.wav'), lead_sq)
save_wav(os.path.join(SAMPLE_DIR, 'lead_pulse.wav'), pulse_w)
save_wav(os.path.join(SAMPLE_DIR, 'bass_saw.wav'), bass_sw)
save_wav(os.path.join(SAMPLE_DIR, 'pad_triangle.wav'), pad_tri)

# Drums
N_kick = int(SR * 0.25)
tk = np.arange(N_kick) / SR
freq = 220 * np.exp(-tk / 0.08) + 60
phase = np.cumsum(2 * np.pi * freq / SR)
kick = np.sin(phase) * np.exp(-tk / 0.12) * (1 - np.exp(-tk / 0.005))

N_snare = int(SR * 0.2)
ts = np.arange(N_snare) / SR
noise = np.random.uniform(-1, 1, N_snare)
noise = noise * np.exp(-ts / 0.08)
tone = np.sin(2 * np.pi * 180 * ts) * np.exp(-ts / 0.06)
snare = noise * 0.7 + tone * 0.3

N_hat = int(SR * 0.05)
th = np.arange(N_hat) / SR
noise = np.random.uniform(-1, 1, N_hat)
hp = np.concatenate(([0], noise[1:] - noise[:-1]))
env = np.exp(-np.arange(N_hat) / (SR * 0.015))
hat = hp * env

save_wav(os.path.join(SAMPLE_DIR, 'kick.wav'), kick)
save_wav(os.path.join(SAMPLE_DIR, 'snare.wav'), snare)
save_wav(os.path.join(SAMPLE_DIR, 'hihat.wav'), hat)

samples = [
    ('lead_square.wav', 1, 0, len(lead_sq), True, 56, 'Lead Square'),
    ('lead_pulse.wav', 2, 0, len(pulse_w), True, 48, 'Lead Pulse'),
    ('bass_saw.wav', 3, 0, len(bass_sw), True, 52, 'Bass Saw'),
    ('pad_triangle.wav', 4, 0, len(pad_tri), True, 28, 'Pad'),
    ('kick.wav', 5, 0, len(kick), False, 64, 'Kick'),
    ('snare.wav', 6, 0, len(snare), False, 56, 'Snare'),
    ('hihat.wav', 7, 0, len(hat), False, 40, 'HiHat'),
]

channels = {
    'lead': 0,
    'harmony': 1,
    'arp': 2,
    'bass': 3,
    'kick': 4,
    'snare': 5,
    'hihat': 6,
    'pad': 7,
}

events = []

def add_note(pat, row, chan, note, inst, vol):
    if note is None:
        return
    events.append({"name":"pattern_set_cell","arguments":{"pattern":pat,"row":row,"channel":chan,"note":note,"instrument":inst,"volume":vol}})

chords = {
    'C': {'root':72, 'third':76, 'fifth':79, 'bass':60, 'pad':60, 'arp_high':[84,88,91]},
    'G': {'root':79, 'third':83, 'fifth':86, 'bass':67, 'pad':67, 'arp_high':[79,83,86]},
    'Am': {'root':69, 'third':72, 'fifth':76, 'bass':69, 'pad':69, 'arp_high':[81,84,88]},
    'F': {'root':77, 'third':81, 'fifth':84, 'bass':65, 'pad':65, 'arp_high':[77,81,84]},
}
prog = ['C','G','Am','F']

def fill_bass(pat, prog=prog):
    for bar, ch in enumerate(prog):
        base = bar * 16
        r = chords[ch]['bass']
        f = chords[ch]['fifth']
        for i, n in enumerate([r, f, r, f]):
            add_note(pat, base + i*4, channels['bass'], n, 3, 52)

def fill_arp(pat, prog=prog):
    for bar, ch in enumerate(prog):
        base = bar * 16
        tri = chords[ch]['arp_high']
        seq = [tri[0], tri[1], tri[2], tri[1]]
        for i in range(8):
            add_note(pat, base + i*2, channels['arp'], seq[i%4], 2, 40)

def fill_drums(pat, with_kick=True, with_snare=True, with_hat=True, kick_rows=[0,16,32,48], snare_rows=[8,24,40,56]):
    if with_kick:
        for r in kick_rows:
            add_note(pat, r, channels['kick'], 72, 5, 64)
    if with_snare:
        for r in snare_rows:
            add_note(pat, r, channels['snare'], 72, 6, 56)
    if with_hat:
        for r in range(0, 64, 2):
            add_note(pat, r, channels['hihat'], 84, 7, 36)

def fill_pad(pat, prog=prog):
    for bar, ch in enumerate(prog):
        base = bar * 16
        add_note(pat, base, channels['pad'], chords[ch]['pad'], 4, 28)

def fill_lead_melody(pat, notes, inst=1, vol=52):
    for i, n in enumerate(notes):
        if n is None:
            continue
        bar = i // 4
        pos = (i % 4) * 4
        add_note(pat, bar*16+pos, channels['lead'], n, inst, vol)

def fill_harmony_melody(pat, notes, vol=36):
    for i, n in enumerate(notes):
        if n is None:
            continue
        bar = i // 4
        pos = (i % 4) * 4
        hn = n - 12
        if hn < 60:
            hn = n - 7
            if hn < 60:
                hn = n
        add_note(pat, bar*16+pos, channels['harmony'], hn, 2, vol)

# Pattern 0: Intro
fill_drums(0, with_kick=True, with_snare=True, with_hat=True)
fill_bass(0)
fill_arp(0)
fill_pad(0)
intro_lead = [None]*8 + [72,76,79,84, 83,81,79,76]
fill_lead_melody(0, intro_lead)
fill_harmony_melody(0, intro_lead)

# Pattern 1: Main A
mainA_lead = [
    76,76,79,81,
    79,79,83,86,
    81,84,81,76,
    77,77,81,84,
]
fill_lead_melody(1, mainA_lead)
fill_harmony_melody(1, mainA_lead)
fill_bass(1); fill_arp(1); fill_drums(1); fill_pad(1)

# Pattern 2: Main B
mainB_lead = [
    72,76,79,81,
    83,81,79,76,
    77,81,79,76,
    72,76,79,84,
]
fill_lead_melody(2, mainB_lead)
fill_harmony_melody(2, mainB_lead)
fill_bass(2); fill_arp(2); fill_drums(2); fill_pad(2)

# Pattern 3: Break
fill_drums(3, with_kick=True, with_snare=True, with_hat=True,
            kick_rows=[0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60],
            snare_rows=[8,24,40,56])
fill_bass(3); fill_arp(3); fill_pad(3)
add_note(3, 32, channels['lead'], 84, 1, 44)

# Pattern 4: Main A return, octave up
mainA_up = [
    88,88,91,84,
    91,91,86,83,
    88,84,88,81,
    89,89,84,81,
]
fill_lead_melody(4, mainA_up)
fill_harmony_melody(4, mainA_up)
fill_bass(4); fill_arp(4); fill_drums(4); fill_pad(4)

# Pattern 5: Main B / Outro
mainB2_lead = [
    84,86,88,89,
    91,89,88,86,
    84,81,79,76,
    72,76,79,84,
]
fill_lead_melody(5, mainB2_lead)
fill_harmony_melody(5, mainB2_lead)
fill_bass(5); fill_arp(5); fill_drums(5); fill_pad(5)

# Build batch JSON
batch = []
batch.append({"name":"module_new","arguments":{"name":"Keygen Vibes","channels":8}})
for fname, inst, slot, length, loop, vol, sname in samples:
    path = os.path.join(SAMPLE_DIR, fname)
    batch.append({"name":"sample_load","arguments":{"path":path,"instrument":inst,"sample":slot}})
    smd = {"instrument":inst,"sample":slot,"name":sname,"volume":vol}
    if loop:
        smd["loop_start"] = 0
        smd["loop_length"] = length
        smd["flags"] = 1
    batch.append({"name":"sample_set","arguments":smd})
    batch.append({"name":"instrument_set","arguments":{"instrument":inst,"name":sname}})

batch.append({"name":"song_set","arguments":{"bpm":165,"speed":3,"length":6,"loop_start":1}})

for p in range(6):
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
    batch.append({"name":"pattern_clear","arguments":{"pattern":p}})

for pos in range(6):
    batch.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})

batch.extend(events)

batch.append({"name":"module_save","arguments":{"path":OUT_XM,"format":"xm"}})

with open(BATCH_FILE, 'w') as f:
    json.dump(batch, f)

print('batch JSON written', BATCH_FILE, 'events', len(events))
