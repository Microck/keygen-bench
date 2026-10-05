import json, os
import numpy as np, wave

sr = 44100
base = 22050.0

def note_name(n):
    names = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
    octave = 4 + n // 12
    idx = n % 12
    return names[idx] + str(octave)

os.makedirs('samples', exist_ok=True)

def save_wav(path, data, amp=0.9):
    data = np.clip(data * amp, -1, 1)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())

L = 84
lead = np.where(np.arange(L) / L < 0.25, 1.0, -1.0); lead -= lead.mean()
save_wav('samples/lead_sq.wav', lead)
bass = 2 * np.arange(L) / L - 1
save_wav('samples/bass_saw84.wav', bass)
L2 = 42
arp = np.where(np.arange(L2) / L2 < 0.125, 1.0, -1.0); arp -= arp.mean()
save_wav('samples/arp_sq42.wav', arp)

N = int(sr * 0.25)
t = np.arange(N) / sr
freq = 200 * np.exp(-4 * t)
ph = np.cumsum(2 * np.pi * freq / sr)
kick = np.sin(ph) * np.exp(-t / 0.12)
click = np.zeros(N)
click[:100] = np.random.randn(100) * np.exp(-np.arange(100) / 20)
save_wav('samples/kick.wav', kick + click * 0.3)

N = int(sr * 0.22)
noise = np.random.randn(N)
f = np.fft.rfft(noise)
freqs = np.fft.rfftfreq(N, 1 / sr)
f[freqs < 200] *= 0.1
noise = np.fft.irfft(f, N)
env = np.exp(-np.arange(N) / (0.08 * sr))
noise *= env
tone = np.sin(2 * np.pi * 180 * np.arange(N) / sr) * np.exp(-np.arange(N) / (0.1 * sr)) * 0.5
save_wav('samples/snare.wav', noise + tone)

N = int(sr * 0.06)
noise = np.random.randn(N)
f = np.fft.rfft(noise)
freqs = np.fft.rfftfreq(N, 1 / sr)
f[(freqs < 5000) | (freqs > 12000)] *= 0.05
noise = np.fft.irfft(f, N)
env = np.exp(-np.arange(N) / (0.015 * sr))
noise *= env
save_wav('samples/hihat.wav', noise)

batch = []

def call(name, args):
    batch.append({'name': name, 'arguments': args})

call('module_new', {'channels': 8, 'name': 'Neon Keygen'})

def load_loop(inst, path, L, vol, name):
    call('sample_load', {'path': path, 'instrument': inst, 'sample': 0})
    call('sample_set', {'instrument': inst, 'sample': 0, 'loop_start': 0, 'loop_length': L,
                        'flags': 17, 'volume': vol})
    call('instrument_set', {'instrument': inst, 'name': name})

load_loop(1, 'samples/lead_sq.wav', 84, 36, 'LeadSquare')
load_loop(2, 'samples/bass_saw84.wav', 84, 40, 'BassSaw')
load_loop(3, 'samples/arp_sq42.wav', 42, 32, 'ArpPulse')

for inst, path, vol, name in [(4, 'samples/kick.wav', 48, 'Kick'),
                              (5, 'samples/snare.wav', 42, 'Snare'),
                              (6, 'samples/hihat.wav', 28, 'Hihat')]:
    call('sample_load', {'path': path, 'instrument': inst, 'sample': 0})
    call('sample_set', {'instrument': inst, 'sample': 0, 'volume': vol})
    call('instrument_set', {'instrument': inst, 'name': name})

call('song_set', {'bpm': 250, 'speed': 6, 'length': 4, 'loop_start': 0})

for p in range(4):
    call('pattern_set_length', {'pattern': p, 'rows': 64})
    call('pattern_clear', {'pattern': p})

def cell(p, r, c, note=None, inst=None, vol=None, eff=None, effp=None):
    args = {'pattern': p, 'row': r, 'channel': c}
    if note is not None:
        args['note'] = note
    if inst is not None:
        args['instrument'] = inst
    if vol is not None:
        args['volume'] = vol
    if eff is not None:
        args['effect'] = eff
    if effp is not None:
        args['effect_param'] = effp
    call('pattern_set_cell', args)

root_offsets = {'C-':0,'C#':1,'D-':2,'D#':3,'E-':4,'F-':5,'F#':6,'G-':7,'G#':8,'A-':9,'A#':10,'B-':11}

def build_rhythm(p, chords, lead_rows=None, lead_transpose=0):
    for bar, (root, qual) in enumerate(chords):
        base = root_offsets[root]
        bass_note = base - 24
        arp_note = base - 12
        arp_eff = 0x37 if qual == 'minor' else 0x47
        start = bar * 16
        for beat in range(4):
            cell(p, start + beat * 4, 3, note_name(bass_note), 2)
        for r in range(16):
            cell(p, start + r, 2, note_name(arp_note), 3, vol=24 if r%2 else 28, eff=0, effp=arp_eff)
        cell(p, start + 0, 4, 'C-4', 4)
        cell(p, start + 8, 4, 'C-4', 4)
        cell(p, start + 4, 5, 'C-4', 5)
        cell(p, start + 12, 5, 'C-4', 5)
        for r in range(16):
            cell(p, start + r, 6, 'C-4', 6, vol=32 if r % 4 == 0 else 20)
        if lead_rows is not None:
            for r, n in lead_rows[bar].items():
                note = n + lead_transpose
                cell(p, start + r, 0, note_name(note), 1)
                if r + 2 < 16:
                    cell(p, start + r + 2, 1, note_name(note - 12), 1, vol=22)

progression = [('A-', 'minor'), ('F-', 'major'), ('C-', 'major'), ('G-', 'major')]

P1 = [
    {0:9, 1:12, 2:16, 3:21, 4:16, 5:12, 6:11, 7:9,
     8:9, 9:12, 10:16, 11:12, 12:11, 13:9, 14:7, 15:4},
    {0:5, 1:9, 2:12, 3:17, 4:12, 5:9, 6:7, 7:5,
     8:5, 9:9, 10:12, 11:9, 12:5, 13:7, 14:9, 15:12},
    {0:7, 1:12, 2:16, 3:19, 4:16, 5:12, 6:11, 7:7,
     8:7, 9:12, 10:16, 11:12, 12:7, 13:4, 14:7, 15:12},
    {0:2, 1:7, 2:11, 3:14, 4:11, 5:7, 6:6, 7:2,
     8:2, 9:7, 10:11, 11:7, 12:2, 13:-1, 14:2, 15:7},
]
P2 = [dict(b) for b in P1]
P2[3] = {0:21, 1:24, 2:28, 3:33, 4:28, 5:24, 6:23, 7:21,
         8:21, 9:24, 10:28, 11:24, 12:23, 13:21, 14:19, 15:16}

build_rhythm(0, progression)
build_rhythm(1, progression, lead_rows=P1)
build_rhythm(2, progression, lead_rows=P2, lead_transpose=12)
# pattern 3 = intro groove ending on Am for clean loop
build_rhythm(3, [('A-', 'minor'), ('F-', 'major'), ('C-', 'major'), ('A-', 'minor')])

order = [0, 1, 2, 3]
for pos, pat in enumerate(order):
    call('order_set', {'position': pos, 'pattern': pat})

with open('batch.json', 'w') as f:
    json.dump(batch, f)
print('wrote batch.json with', len(batch), 'calls')
