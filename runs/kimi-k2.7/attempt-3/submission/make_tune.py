import numpy as np, wave, os, json, subprocess, math

SAMPLE_DIR = '/workspace/samples'
SUB_DIR = '/workspace/submission'
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SUB_DIR, exist_ok=True)
SR = 44100
LOOP_LEN = 168  # C-5 maps to ~262.5 Hz

def save_wav(name, data, sr=SR):
    path = os.path.join(SAMPLE_DIR, name + '.wav')
    data = (np.clip(data, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    return path

def bl_square(N, harmonics):
    t = np.arange(N) / N
    sig = np.zeros(N)
    for k in range(1, harmonics * 2, 2):
        sig += (4.0 / np.pi) / k * np.sin(2 * np.pi * k * t)
    return sig

def bl_saw(N, harmonics):
    t = np.arange(N) / N
    sig = np.zeros(N)
    for k in range(1, harmonics + 1):
        sig += (-1)**(k + 1) * (2.0 / np.pi) / k * np.sin(2 * np.pi * k * t)
    return sig

def bl_pulse(N, duty, harmonics):
    t = np.arange(N) / N
    sig = np.zeros(N)
    for k in range(1, harmonics + 1):
        sig += (2.0 / np.pi) * np.sin(np.pi * k * duty) / k * np.cos(2 * np.pi * k * (t - duty / 2))
    return sig

# generate looped single-cycle samples
square_lead = bl_square(LOOP_LEN, 14) * 0.42
saw_bass = bl_saw(LOOP_LEN, 18) * 0.55
pulse_arp = bl_pulse(LOOP_LEN, 0.25, 12) * 0.45
pad_wave = (bl_saw(LOOP_LEN, 16) * 0.6 + bl_square(LOOP_LEN, 12) * 0.4) * 0.42

save_wav('square_lead', square_lead)
save_wav('saw_bass', saw_bass)
save_wav('pulse_arp', pulse_arp)
save_wav('pad', pad_wave)

# Kick: sine sweep 180->55 over 0.18s, click, tail
kick_dur = 0.24
kick_n = int(SR * kick_dur)
t = np.arange(kick_n) / SR
f_start, f_end = 180.0, 50.0
phase = 2 * np.pi * (f_start * t + 0.5 * (f_end - f_start) / kick_dur * t**2)
kick = np.sin(phase)
env = np.exp(-t / 0.09)
click = np.zeros_like(t)
click[:120] = (np.random.rand(120) - 0.5) * np.exp(-np.arange(120) / 25.0)
kick = (kick * env + click * 0.35) * 0.95
fade_len = int(0.04 * SR)
kick[-fade_len:] *= np.linspace(1, 0, fade_len)
save_wav('kick', kick)

# Snare: noise + 180Hz tone burst
snare_dur = 0.22
snare_n = int(SR * snare_dur)
t = np.arange(snare_n) / SR
noise = (np.random.rand(snare_n) * 2 - 1)
noise = np.diff(noise, prepend=noise[0])
tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.045)
env = np.exp(-t / 0.055)
snare = (noise * 0.55 + tone * 0.45) * env * 0.85
save_wav('snare', snare)

# Closed hihat: short noise
chh_dur = 0.045
chh_n = int(SR * chh_dur)
noise = (np.random.rand(chh_n) * 2 - 1)
hp = np.diff(noise, prepend=noise[0])
env = np.exp(-np.arange(chh_n) / (SR * 0.0045))
chh = hp * env * 0.6
save_wav('chh', chh)

# Crash / open hihat: longer noise
crash_dur = 0.35
crash_n = int(SR * crash_dur)
noise = (np.random.rand(crash_n) * 2 - 1)
hp = np.diff(noise, prepend=noise[0])
env = np.exp(-np.arange(crash_n) / (SR * 0.07))
crash = hp * env * 0.55
save_wav('crash', crash)

print('Samples generated.')

# ----- Module construction -----

def ft2_call(name, args):
    out = subprocess.run(['ft2','call',name,json.dumps(args)], capture_output=True, text=True)
    if out.returncode != 0:
        print('ft2 error', out.stderr)
        raise RuntimeError(out.stderr)
    return out.stdout.strip()

ft2_call('module_new', {'name':'Neon Keygen','channels':8})

samples_meta = [
    (1, os.path.join(SAMPLE_DIR,'kick.wav'),   'Kick',    62, 0, 0, 0),
    (2, os.path.join(SAMPLE_DIR,'snare.wav'),  'Snare',   56, 0, 0, 0),
    (3, os.path.join(SAMPLE_DIR,'chh.wav'),    'CHH',     46, 0, 0, 0),
    (4, os.path.join(SAMPLE_DIR,'crash.wav'),  'Crash',   52, 0, 0, 0),
    (5, os.path.join(SAMPLE_DIR,'saw_bass.wav'), 'SawBass', 54, 1, 0, LOOP_LEN),
    (6, os.path.join(SAMPLE_DIR,'square_lead.wav'), 'SquareLead', 50, 1, 0, LOOP_LEN),
    (7, os.path.join(SAMPLE_DIR,'pulse_arp.wav'), 'PulseArp', 42, 1, 0, LOOP_LEN),
    (8, os.path.join(SAMPLE_DIR,'pad.wav'),   'Pad',     40, 1, 0, LOOP_LEN),
]
for inst, path, name, vol, flags, ls, ll in samples_meta:
    ft2_call('sample_load', {'path':path,'instrument':inst,'sample':0})
    ft2_call('sample_set', {'instrument':inst,'sample':0,'name':name,'volume':vol,'panning':128,
                            'loop_start':ls,'loop_length':ll,'flags':flags})
    ft2_call('instrument_set', {'instrument':inst,'name':name})

ft2_call('song_set', {'bpm':150,'speed':6,'length':4,'loop_start':0})
for p in range(4):
    ft2_call('pattern_set_length', {'pattern':p,'rows':64})
for pos, pat in enumerate([0,1,2,3]):
    ft2_call('order_set', {'position':pos,'pattern':pat})

cells = []

def add(pattern, row, ch, note=None, inst=None, vol=None, effect=None, effparam=None):
    d = {'pattern':pattern,'row':row,'channel':ch}
    if note is not None: d['note'] = note
    if inst is not None: d['instrument'] = inst
    if vol is not None: d['volume'] = vol
    if effect is not None: d['effect'] = effect
    if effparam is not None: d['effect_param'] = effparam
    cells.append(d)

CH_KICK=0; CH_SNARE=1; CH_CHH=2; CH_CRASH=3
CH_BASS=4; CH_LEAD=5; CH_ARP=6; CH_PAD=7

roots = {'Em':'E-4','C':'C-4','G':'G-4','D':'D-4','Am':'A-4'}
bass_roots = {'Em':'E-3','C':'C-3','G':'G-3','D':'D-3','Am':'A-3'}
arp_roots = {'Em':'E-4','C':'C-4','G':'G-4','D':'D-4','Am':'A-4'}
arp_params = {'Em':0x37,'Am':0x37,'C':0x47,'G':0x47,'D':0x47}

lead_main = [
    ['E-6','D-6','B-5','G-5','E-6','G-5','B-5','D-6','E-6','B-5','G-5','E-5','B-5','E-5','G-5','B-5'],
    ['C-6','B-5','G-5','E-5','C-6','E-5','G-5','B-5','C-6','G-5','E-5','C-5','G-5','C-5','E-5','G-5'],
    ['B-5','A-5','G-5','D-5','B-5','D-5','G-5','A-5','B-5','G-5','D-5','B-4','D-5','B-4','G-5','D-5'],
    ['A-5','G-5','F#5','D-5','A-5','D-5','F#5','G-5','A-5','F#5','D-5','A-4','F#5','A-4','D-5','F#5'],
]
lead_var = [
    ['A-5','G-5','E-5','C-5','A-5','C-5','E-5','G-5','A-5','E-5','C-5','A-4','E-5','A-4','C-5','E-5'],
    ['C-6','B-5','G-5','E-5','C-6','E-5','G-5','B-5','C-6','G-5','E-5','C-5','G-5','C-5','E-5','G-5'],
    ['B-5','A-5','G-5','D-5','B-5','D-5','G-5','A-5','B-5','G-5','D-5','B-4','D-5','B-4','G-5','D-5'],
    ['A-5','G-5','F#5','D-5','A-5','F#5','D-5','A-4','F#5','A-4','D-5','F#5','A-5','F#5','D-5','A-4'],
]

prog = ['Em','C','G','D']

def fill_bar(pattern, bar_idx, chord, lead_notes=None, fill=False, crash=False, arp=True, pad=True):
    base = bar_idx * 16
    root = roots[chord]
    bass_root = bass_roots[chord]
    arp_root = arp_roots[chord]

    # kick on 1 and 3, syncopated fill on 3+
    add(pattern, base+0, CH_KICK, 'C-3', 1, 60)
    add(pattern, base+8, CH_KICK, 'C-3', 1, 58)
    if fill:
        add(pattern, base+10, CH_KICK, 'C-3', 1, 52)

    # snare on 2 and 4
    add(pattern, base+4, CH_SNARE, 'C-4', 2, 54)
    add(pattern, base+12, CH_SNARE, 'C-4', 2, 52)

    # chh every odd 16th, short note cut
    for r in range(1,16,2):
        add(pattern, base+r, CH_CHH, 'C-6', 3, 32, 14, 0xC2)

    # crash on phrase downbeat
    if crash:
        add(pattern, base+0, CH_CRASH, 'C-5', 4, 50, 14, 0xC8)

    # bass quarter notes
    for br in [0,4,8,12]:
        add(pattern, base+br, CH_BASS, bass_root, 5, 46, 14, 0xC6)

    # pad whole bar
    if pad:
        add(pattern, base+0, CH_PAD, root, 8, 30)

    # arp quarter notes
    if arp:
        for br in [0,4,8,12]:
            add(pattern, base+br, CH_ARP, arp_root, 7, 38, 0, arp_params[chord])

    # lead melody
    if lead_notes:
        for i, n in enumerate(lead_notes):
            add(pattern, base+i, CH_LEAD, n, 6, 48)

# Pattern 0: main A
for bi, chord in enumerate(prog):
    fill_bar(0, bi, chord, lead_notes=lead_main[bi], fill=(bi==3), crash=(bi==0))

# Pattern 1: main A2 with small variation (same chords, lead same, maybe fills)
for bi, chord in enumerate(prog):
    fill_bar(1, bi, chord, lead_notes=lead_main[bi], fill=(bi in (1,3)), crash=False)

# Pattern 2: variation B (Am C G D)
prog_var = ['Am','C','G','D']
for bi, chord in enumerate(prog_var):
    fill_bar(2, bi, chord, lead_notes=lead_var[bi], fill=(bi in (1,3)), crash=False)

# Pattern 3: main A + final crash, lead variation, last bar fill
for bi, chord in enumerate(prog):
    fill_bar(3, bi, chord, lead_notes=lead_main[bi], fill=(bi==3), crash=(bi==0))

for pat in range(4):
    batch = [{'name':'pattern_set_cell','arguments':c} for c in cells if c['pattern']==pat]
    with open(f'/tmp/pat_{pat}.json','w') as f:
        json.dump(batch, f)
    out = subprocess.run(['ft2','batch',f'/tmp/pat_{pat}.json'], capture_output=True, text=True)
    print(f'pattern {pat} cells={len(batch)} rc={out.returncode}')

ft2_call('module_save', {'path':os.path.join(SUB_DIR,'tune.xm'),'format':'xm'})
print('Saved', os.path.join(SUB_DIR,'tune.xm'))
