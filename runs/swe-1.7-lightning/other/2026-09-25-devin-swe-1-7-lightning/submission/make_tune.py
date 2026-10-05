import json, math, os, wave, struct, base64, io, numpy as np

SR = 8363  # sample rate matching FT2 C4

def save_wav(path, data):
    # data float -1..1
    data = np.clip(data, -1.0, 1.0)
    pcm16 = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm16.tobytes())
    return len(data)

def square(freq, dur, duty=0.5):
    N = int(SR * dur)
    period = SR / freq
    arr = np.zeros(N)
    for i in range(N):
        arr[i] = 1.0 if (i % period) / period < duty else -1.0
    return arr

def saw(freq, dur):
    N = int(SR * dur)
    period = SR / freq
    arr = np.zeros(N)
    for i in range(N):
        arr[i] = 2.0 * ((i % period) / period) - 1.0
    return arr

def kick(dur=0.2):
    N = int(SR * dur)
    arr = np.zeros(N)
    phase = 0.0
    for i in range(N):
        t = i / N
        freq = 120.0 * (1.0 - t*0.75) + 40.0  # sweep down
        phase += freq / SR
        arr[i] = math.sin(2*math.pi*phase) * (1.0 - t) ** 1.5
    return arr

def snare(dur=0.15):
    N = int(SR * dur)
    noise = np.random.uniform(-1, 1, N)
    env = np.exp(-np.linspace(0, 8, N))
    tone = np.sin(2*np.pi*np.cumsum(np.full(N, 180.0/SR))) * env
    return (noise * env * 0.8 + tone * 0.4)

def hihat(dur=0.04):
    N = int(SR * dur)
    noise = np.random.uniform(-1, 1, N)
    # simple high-pass-ish by differencing
    hp = np.diff(noise, prepend=0.0)
    env = np.exp(-np.linspace(0, 5, N))
    return hp * env * 0.6

# generate C4-ish pitched samples with integer period for clean loop
period = 32  # 8363/32 = 261.34 Hz (close to C4)
samples_dir = '/workspace/samples'
os.makedirs(samples_dir, exist_ok=True)

def make_loop(func, periods):
    N = period * periods
    arr = func(8363/period, N/SR)
    return arr, N

lead, Nlead = make_loop(square, 130)
bass, Nbass = make_loop(saw, 130)
arp, Narp = make_loop(square, 65)
kick_arr = kick()
snare_arr = snare()
hat_arr = hihat()

paths = {
    'kick': os.path.join(samples_dir,'kick.wav'),
    'snare': os.path.join(samples_dir,'snare.wav'),
    'hihat': os.path.join(samples_dir,'hihat.wav'),
    'bass': os.path.join(samples_dir,'bass.wav'),
    'lead': os.path.join(samples_dir,'lead.wav'),
    'arp': os.path.join(samples_dir,'arp.wav'),
}
Ns = {}
for name, arr in [('kick',kick_arr),('snare',snare_arr),('hihat',hat_arr),('bass',bass),('lead',lead),('arp',arp)]:
    Ns[name] = save_wav(paths[name], arr)

# Build pattern commands
batch = []
batch.append({"name":"module_new","arguments":{"channels":4,"name":"Neon Keygen"}})

# Load samples
instr_map = {'kick':1,'snare':2,'hihat':3,'bass':4,'lead':5,'arp':6}
for n, inst in instr_map.items():
    batch.append({"name":"sample_load","arguments":{"instrument":inst,"sample":0,"path":paths[n]}})
    batch.append({"name":"instrument_set","arguments":{"instrument":inst,"name":n.title()}})
    if n in ('bass','lead','arp'):
        # loop entire sample
        batch.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,
                      "loop_start":0,"loop_length":Ns[n],"volume":64,"finetune":0}})
    else:
        batch.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,
                      "loop_start":0,"loop_length":0,"volume":64,"finetune":0}})

# Song settings
batch.append({"name":"song_set","arguments":{"bpm":145,"speed":6,"length":4,"loop_start":0,"name":"Neon Keygen"}})
for p in range(4):
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
    batch.append({"name":"pattern_clear","arguments":{"pattern":p}})

# Helper
def cell(pattern, row, chan, note=None, inst=None, vol=None, eff=None, effp=None):
    d = {"pattern":pattern,"row":row,"channel":chan}
    if note is not None: d["note"] = note
    if inst is not None: d["instrument"] = inst
    if vol is not None: d["volume"] = vol
    if eff is not None: d["effect"] = eff
    if effp is not None: d["effect_param"] = effp
    return {"name":"pattern_set_cell","arguments":d}

# Progression: Am, F, C, G
chords = [
    [('A',3),('C',4),('E',4)],  # Am
    [('F',3),('A',3),('C',4)],  # F
    [('C',4),('E',4),('G',4)],  # C
    [('G',3),('B',3),('D',4)],  # G
]
prog = [0,1,2,3]*4  # each bar one chord for 4 patterns

# Drums for every pattern
def add_drums(p):
    for row in range(64):
        if row % 8 == 0:
            batch.append(cell(p, row, 4, 'C-4', 1, 50))
        elif row % 8 == 4:
            batch.append(cell(p, row, 4, 'C-4', 2, 45))
        if row % 2 == 1:
            batch.append(cell(p, row, 4, 'C-4', 3, 28))

# Bass: quarter notes root on chord changes / pattern
def note_name(note, octv):
    return f"{note}-{octv}"

def add_bass(p):
    roots = ['A','F','C','G']
    for bar in range(4):
        chord = prog[p*4+bar]
        root = roots[chord]
        octv = 2
        base_row = bar*16
        # root on beats 1,3, plus fifth on beat 2
        for i, row in enumerate([0,4,8,12]):
            n = root if i%2==0 else (['C','A','E','B'][chord] if chord!=1 else 'C')  # simplistic 5th
            if chord == 0:  # Am
                n = root if i%2==0 else 'E'
            elif chord == 1:  # F
                n = root if i%2==0 else 'C'
            elif chord == 2:  # C
                n = root if i%2==0 else 'G'
            elif chord == 3:  # G
                n = root if i%2==0 else 'D'
            batch.append(cell(p, base_row+row, 3, note_name(n, octv), 4, 48))

# Arp: fast 2-row chord tones on channel 2
def add_arp(p):
    tones = ['A','C','E','G']
    for bar in range(4):
        chord = prog[p*4+bar]
        chord_tones = chords[chord]
        base_row = bar*16
        for step in range(8):
            row = base_row + step*2
            tone, octv = chord_tones[step % 3]
            if octv == 3 and step%3==2:
                octv = 4  # vary octaves a bit
            # use 3rd or 4th octave for sparkle
            batch.append(cell(p, row, 2, note_name(tone, 5 if step%2==0 else 4), 6, 38))

# Lead melody per pattern
lead_phrases = {
    0: [(0,'E',4),(4,'E',4),(8,'D',4),(12,'C',4),
        (16,'A',3),(20,'A',3),(24,'C',4),(28,'D',4),
        (32,'E',4),(36,'G',4),(40,'E',4),(44,'D',4),
        (48,'C',4),(52,'A',3),(56,'G',3),(60,'A',3)],
    1: [(0,'A',4),(4,'A',4),(8,'G',4),(12,'F',4),
        (16,'E',4),(20,'E',4),(24,'F',4),(28,'G',4),
        (32,'A',4),(36,'C',5),(40,'A',4),(44,'G',4),
        (48,'F',4),(52,'E',4),(56,'D',4),(60,'E',4)],
    2: [(0,'E',4),(2,'G',4),(4,'A',4),(6,'G',4),(8,'E',4),(12,'D',4),
        (16,'C',4),(18,'E',4),(20,'F',4),(22,'G',4),(24,'A',4),(28,'C',5),
        (32,'B',4),(34,'A',4),(36,'G',4),(38,'E',4),(40,'D',4),(44,'C',4),
        (48,'A',4),(52,'G',4),(56,'F',4),(60,'E',4)],
    3: [(0,'A',4),(4,'G',4),(8,'F',4),(12,'E',4),
        (16,'D',4),(20,'E',4),(24,'F',4),(28,'G',4),
        (32,'A',4),(36,'C',5),(40,'B',4),(44,'A',4),
        (48,'G',4),(52,'F',4),(56,'E',4),(60,'D',4)],
}

def add_lead(p):
    for row, note, octv in lead_phrases[p]:
        # hold notes by not cutting? In tracker note lasts until next note. Good.
        batch.append(cell(p, row, 1, note_name(note, octv), 5, 52))
    # add a few volume cut effects? not needed

for p in range(4):
    add_drums(p)
    add_bass(p)
    add_arp(p)
    add_lead(p)

# Set order
for pos in range(4):
    batch.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})

# Save and render
batch.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
batch.append({"name":"module_render","arguments":{"path":"/workspace/submission/tune.wav","rate":44100,"bits":16,"amp":128,"loops":2}})

with open('/workspace/setup.json','w') as f:
    json.dump(batch, f)
print('Wrote setup.json and samples')
