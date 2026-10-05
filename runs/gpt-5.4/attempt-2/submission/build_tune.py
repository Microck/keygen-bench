import json, math, wave
from pathlib import Path
import numpy as np

SR = 44100
C5 = 523.2511306011972
root = Path('/workspace/work')
samples_dir = root / 'samples'
samples_dir.mkdir(parents=True, exist_ok=True)
np.random.seed(1337)

# ---------- audio helpers ----------
def write_wav(path, x, sr=SR):
    x = np.asarray(x, dtype=np.float32)
    peak = float(np.max(np.abs(x))) if len(x) else 1.0
    if peak > 0:
        x = x / max(1.0, peak) * 0.98
    x = np.clip(x, -1.0, 1.0)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype('<i2').tobytes())


def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def simple_hp(x, cutoff_hz, sr=SR):
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / sr
    alpha = rc / (rc + dt)
    y = np.zeros_like(x)
    py = 0.0
    px = 0.0
    for i, xi in enumerate(x):
        yi = alpha * (py + xi - px)
        y[i] = yi
        py = yi
        px = xi
    return y


def simple_lp(x, cutoff_hz, sr=SR):
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    y = np.zeros_like(x)
    prev = 0.0
    for i, xi in enumerate(x):
        prev = prev + alpha * (xi - prev)
        y[i] = prev
    return y


def phase_from_freq(freq):
    return 2 * np.pi * np.cumsum(freq) / SR


def fade_edges(x, ms=4):
    x = x.copy().astype(np.float32)
    m = max(1, int(SR * ms / 1000))
    if len(x) < 2 * m:
        m = max(1, len(x) // 4)
    ramp = np.linspace(0, 1, m, endpoint=False, dtype=np.float32)
    x[:m] *= ramp
    x[-m:] *= ramp[::-1]
    return x


def additive_saw(phase, harmonics=16, rolloff=1.0):
    out = np.zeros_like(phase, dtype=np.float64)
    for h in range(1, harmonics + 1):
        out += np.sin(h * phase) / (h ** rolloff)
    out *= 2 / math.pi
    return out


def additive_square(phase, harmonics=13, rolloff=1.0):
    out = np.zeros_like(phase, dtype=np.float64)
    for h in range(1, harmonics * 2, 2):
        out += np.sin(h * phase) / (h ** rolloff)
    out *= 4 / math.pi
    return out

# ---------- synths ----------
def synth_kick():
    length = 0.22
    t = np.arange(int(length * SR)) / SR
    freq = 34 + 150 * np.exp(-t * 26) + 18 * np.exp(-t * 7)
    phase = phase_from_freq(freq)
    body = np.sin(phase)
    punch = np.sin(phase * 2) * np.exp(-t * 18) * 0.22
    click = np.random.randn(len(t)).astype(np.float32)
    click = simple_hp(click, 4000)
    click *= np.exp(-t * 90)
    sub = np.sin(phase * 0.5) * np.exp(-t * 8) * 0.15
    env = np.exp(-t * 12)
    x = body * env + punch + click * 0.25 + sub
    x = softclip(x, 1.6)
    return fade_edges(x, 2)


def synth_snare():
    length = 0.23
    t = np.arange(int(length * SR)) / SR
    noise = np.random.randn(len(t)).astype(np.float32)
    noise = simple_hp(noise, 1200)
    noise = simple_lp(noise, 9000)
    tone = np.sin(2*np.pi*180*t) * np.exp(-t * 18) + 0.6*np.sin(2*np.pi*330*t) * np.exp(-t * 26)
    x = noise * np.exp(-t * 18) * 0.95 + tone * 0.5
    x += 0.15 * np.random.randn(len(t)).astype(np.float32) * np.exp(-t * 50)
    x = softclip(x, 1.4)
    return fade_edges(x, 2)


def synth_hat(length=0.08, open_hat=False):
    t = np.arange(int(length * SR)) / SR
    noise = np.random.randn(len(t)).astype(np.float32)
    noise = simple_hp(noise, 5000 if not open_hat else 4500)
    noise = simple_lp(noise, 14000)
    metal = np.sin(2*np.pi*6250*t) + 0.8*np.sin(2*np.pi*9370*t) + 0.6*np.sin(2*np.pi*11780*t)
    env = np.exp(-t * (55 if not open_hat else 16))
    x = (noise * 0.8 + metal * 0.28) * env
    x = softclip(x, 1.3)
    return fade_edges(x, 2)


def synth_bass():
    length = 0.15
    t = np.arange(int(length * SR)) / SR
    freq = C5 * (1 - 0.028*np.exp(-t*40))
    phase = phase_from_freq(freq)
    saw = additive_saw(phase, harmonics=12, rolloff=0.95)
    square = additive_square(phase, harmonics=7, rolloff=1.0)
    sub = np.sin(phase) * 0.65
    bright = np.exp(-t * 24)
    env = np.exp(-t * 9)
    x = 0.55*saw*bright + 0.35*square*bright + 0.55*sub*env + 0.08*np.sin(phase*2)*np.exp(-t*18)
    x = simple_lp(x.astype(np.float32), 3400)
    x = softclip(x, 1.8)
    x *= env
    return fade_edges(x, 2)


def synth_lead():
    length = 0.60
    t = np.arange(int(length * SR)) / SR
    vib = 0.0022*np.sin(2*np.pi*5.2*t) * (1 - np.exp(-t*8))
    freq = C5 * (1 + 0.004*np.exp(-t*8))
    phase = 2 * np.pi * np.cumsum(freq * (1 + vib)) / SR
    saw1 = additive_saw(phase, harmonics=18, rolloff=0.92)
    saw2 = additive_saw(phase*1.003, harmonics=14, rolloff=1.0)
    square = additive_square(phase*0.997, harmonics=9, rolloff=1.1)
    env = np.exp(-np.maximum(t-0.01, 0) * 4.8)
    att = np.clip(t/0.006, 0, 1)
    bright = np.exp(-t * 5)
    x = (0.45*saw1 + 0.20*saw2 + 0.25*square*bright + 0.18*np.sin(phase*2)*bright) * env * att
    x += 0.05*np.random.randn(len(t)).astype(np.float32) * np.exp(-t*16)
    x = simple_lp(x.astype(np.float32), 5200)
    x = softclip(x, 1.5)
    return fade_edges(x, 3)


def synth_pluck():
    length = 0.34
    t = np.arange(int(length * SR)) / SR
    freq = C5 * (1 + 0.003*np.exp(-t*28))
    phase = phase_from_freq(freq)
    pulse = additive_square(phase, harmonics=15, rolloff=1.05)
    saw = additive_saw(phase*1.002, harmonics=12, rolloff=1.1)
    env = np.exp(-t * 10)
    x = (0.58*pulse + 0.28*saw + 0.16*np.sin(phase*2)) * env
    x += 0.03*np.random.randn(len(t)).astype(np.float32) * np.exp(-t*35)
    x = simple_lp(x.astype(np.float32), 6500)
    x = softclip(x, 1.4)
    return fade_edges(x, 2)


def synth_chord(quality='maj', phase_offset=0.0, detune=0.0):
    length = 0.42
    t = np.arange(int(length * SR)) / SR
    intervals = [0, 4, 7] if quality == 'maj' else [0, 3, 7]
    x = np.zeros_like(t, dtype=np.float64)
    detunes = [0.0, detune, -detune]
    for interval, d in zip(intervals, detunes):
        f = C5 * (2 ** (interval / 12.0)) * (1 + d)
        phase = 2 * np.pi * f * t + phase_offset * (interval + 1)
        x += 0.60 * additive_saw(phase, harmonics=10, rolloff=0.98)
        x += 0.28 * additive_square(phase*0.999, harmonics=7, rolloff=1.15)
    env = np.exp(-t * 5.6)
    att = np.clip(t/0.008, 0, 1)
    x = (x / max(1.0, np.max(np.abs(x)))) * env * att
    x += 0.015*np.random.randn(len(t)).astype(np.float32) * np.exp(-t*15)
    x = simple_lp(x.astype(np.float32), 5000)
    x = softclip(x, 1.3)
    return fade_edges(x, 3)


def synth_crash():
    length = 0.55
    t = np.arange(int(length * SR)) / SR
    noise = np.random.randn(len(t)).astype(np.float32)
    noise = simple_hp(noise, 3000)
    noise = simple_lp(noise, 15000)
    metal = np.sin(2*np.pi*4310*t) + 0.7*np.sin(2*np.pi*6540*t) + 0.45*np.sin(2*np.pi*9320*t) + 0.3*np.sin(2*np.pi*12540*t)
    x = (noise*0.9 + metal*0.35) * np.exp(-t * 6.5)
    x = softclip(x, 1.2)
    return fade_edges(x, 2)

# ---------- create samples ----------
write_wav(samples_dir/'kick.wav', synth_kick())
write_wav(samples_dir/'snare.wav', synth_snare())
write_wav(samples_dir/'hat.wav', synth_hat(0.075, False))
write_wav(samples_dir/'bass.wav', synth_bass())
write_wav(samples_dir/'lead.wav', synth_lead())
write_wav(samples_dir/'majL.wav', synth_chord('maj', 0.11, 0.0020))
write_wav(samples_dir/'majR.wav', synth_chord('maj', 0.37, -0.0015))
write_wav(samples_dir/'minL.wav', synth_chord('min', 0.19, 0.0015))
write_wav(samples_dir/'minR.wav', synth_chord('min', 0.41, -0.0020))
write_wav(samples_dir/'arp.wav', synth_pluck())
write_wav(samples_dir/'crash.wav', synth_crash())
write_wav(samples_dir/'openhat.wav', synth_hat(0.18, True))

# ---------- ft2 command build ----------
cmds = []

def add(tool, **arguments):
    cmds.append({'name': tool, 'arguments': arguments})

VOL = lambda v: int(16 + v)

add('module_new', channels=8, name='Checksum Mirage')
add('song_set', name='Checksum Mirage', bpm=150, speed=6, length=8, loop_start=0, channels=8)
for p in range(8):
    add('pattern_set_length', pattern=p, rows=64)
    add('pattern_clear', pattern=p)
for pos in range(8):
    add('order_set', position=pos, pattern=pos)

instrs = [
    (1, 'Kick', 'kick.wav', 64, 128),
    (2, 'Snare', 'snare.wav', 56, 132),
    (3, 'Hat', 'hat.wav', 34, 182),
    (4, 'Bass', 'bass.wav', 42, 128),
    (5, 'Lead', 'lead.wav', 34, 110),
    (6, 'Maj L', 'majL.wav', 24, 56),
    (7, 'Maj R', 'majR.wav', 24, 200),
    (8, 'Min L', 'minL.wav', 24, 56),
    (9, 'Min R', 'minR.wav', 24, 200),
    (10, 'Arp', 'arp.wav', 28, 168),
    (11, 'Crash', 'crash.wav', 24, 128),
    (12, 'OpenHat', 'openhat.wav', 32, 188),
]
for inst, label, wavname, vol, pan in instrs:
    add('sample_load', path=str(samples_dir / wavname), instrument=inst)
    add('instrument_set', instrument=inst, name=label)
    add('sample_set', instrument=inst, name=label, volume=vol, panning=pan)

progressions = {
    0: ['Am', 'F', 'C', 'G'],
    1: ['Am', 'F', 'Dm', 'E'],
    2: ['F', 'G', 'Em', 'Am'],
    3: ['C', 'G', 'Am', 'F'],
    4: ['Am', 'G', 'F', 'E'],
    5: ['Am', 'F', 'C', 'G'],
    6: ['Dm', 'E', 'Am', 'E'],
    7: ['F', 'G', 'Am', 'E'],
}

chord_info = {
    'Am': {'quality': 'min', 'stab': 'A-4', 'arp_basic': ['A-5','E-6','C-6','E-6','A-6','E-6','C-6','G-6'], 'arp_light': ['E-6','C-6','E-6','G-6'], 'arp_dense': ['A-5','E-6','C-6','E-6','A-6','E-6','C-6','E-6','A-5','E-6','C-6','G-6','A-6','E-6','C-6','G-6'], 'bass': ['A-2','A-3','E-3','A-3','C-3','A-3','E-3','G-3'], 'bass_break': ['A-2','E-3','A-2','G-2']},
    'F':  {'quality': 'maj', 'stab': 'F-4', 'arp_basic': ['A-5','C-6','F-6','C-6','A-6','C-6','F-6','E-6'], 'arp_light': ['C-6','F-6','C-6','E-6'], 'arp_dense': ['A-5','C-6','F-6','C-6','A-6','C-6','F-6','C-6','A-5','C-6','F-6','E-6','A-6','C-6','F-6','E-6'], 'bass': ['F-2','F-3','C-3','F-3','A-2','F-3','C-3','E-3'], 'bass_break': ['F-2','C-3','F-2','E-2']},
    'C':  {'quality': 'maj', 'stab': 'C-5', 'arp_basic': ['G-5','C-6','E-6','G-6','C-7','G-6','E-6','B-6'], 'arp_light': ['C-6','E-6','G-6','B-6'], 'arp_dense': ['G-5','C-6','E-6','G-6','C-7','G-6','E-6','G-6','G-5','C-6','E-6','B-6','C-7','G-6','E-6','B-6'], 'bass': ['C-3','G-3','E-3','G-3','C-3','G-3','E-3','B-3'], 'bass_break': ['C-3','G-3','C-3','B-2']},
    'G':  {'quality': 'maj', 'stab': 'G-4', 'arp_basic': ['G-5','D-6','G-6','B-6','D-7','B-6','G-6','F-6'], 'arp_light': ['D-6','G-6','B-6','F-6'], 'arp_dense': ['G-5','D-6','G-6','B-6','D-7','B-6','G-6','B-6','G-5','D-6','G-6','F-6','D-7','B-6','G-6','F-6'], 'bass': ['G-2','G-3','D-3','G-3','B-2','G-3','D-3','F-3'], 'bass_break': ['G-2','D-3','G-2','F-2']},
    'Dm': {'quality': 'min', 'stab': 'D-5', 'arp_basic': ['A-5','D-6','F-6','A-6','D-7','A-6','F-6','C-6'], 'arp_light': ['D-6','F-6','A-6','C-6'], 'arp_dense': ['A-5','D-6','F-6','A-6','D-7','A-6','F-6','A-6','A-5','D-6','F-6','C-6','D-7','A-6','F-6','C-6'], 'bass': ['D-3','A-3','D-4','A-3','F-3','A-3','C-4','A-3'], 'bass_break': ['D-3','A-3','D-3','C-3']},
    'E':  {'quality': 'maj', 'stab': 'E-5', 'arp_basic': ['G#5','B-5','E-6','G#6','B-6','G#6','E-6','D-6'], 'arp_light': ['B-5','E-6','G#6','D-6'], 'arp_dense': ['G#5','B-5','E-6','G#6','B-6','G#6','E-6','G#6','G#5','B-5','E-6','D-6','B-6','G#6','E-6','D-6'], 'bass': ['E-2','B-2','E-3','G#3','B-2','E-3','D-3','G#3'], 'bass_break': ['E-2','B-2','E-2','D-3']},
    'Em': {'quality': 'min', 'stab': 'E-5', 'arp_basic': ['G-5','B-5','E-6','G-6','B-6','G-6','E-6','D-6'], 'arp_light': ['B-5','E-6','G-6','D-6'], 'arp_dense': ['G-5','B-5','E-6','G-6','B-6','G-6','E-6','G-6','G-5','B-5','E-6','D-6','B-6','G-6','E-6','D-6'], 'bass': ['E-2','B-2','E-3','G-3','B-2','E-3','D-3','G-3'], 'bass_break': ['E-2','B-2','E-2','D-3']},
}

lead_lines = {
    0: [(32,'E-5'), (36,'G-5'), (40,'C-6'), (44,'B-5'), (48,'D-5'), (52,'G-5'), (56,'A-5'), (60,'G-5')],
    1: [(0,'E-5'), (2,'G-5'), (4,'A-5'), (6,'C-6'), (8,'E-6'), (10,'C-6'), (12,'B-5'), (14,'A-5'), (16,'A-5'), (18,'C-6'), (20,'A-5'), (22,'G-5'), (24,'F-5'), (26,'A-5'), (28,'G-5'), (30,'E-5'), (32,'F-5'), (34,'A-5'), (36,'D-6'), (38,'A-5'), (40,'C-6'), (42,'A-5'), (44,'F-5'), (46,'E-5'), (48,'G#5'), (50,'B-5'), (52,'E-6'), (54,'B-5'), (56,'D-6'), (58,'B-5'), (60,'G#5'), (62,'E-5')],
    2: [(32,'B-5'), (36,'G-5'), (40,'E-6'), (44,'D-6'), (48,'C-6'), (50,'D-6'), (52,'E-6'), (54,'G-6'), (56,'A-6'), (60,'E-6')],
    3: [(0,'E-5'), (2,'G-5'), (4,'C-6'), (6,'G-5'), (8,'E-6'), (10,'C-6'), (12,'B-5'), (14,'G-5'), (16,'D-5'), (18,'G-5'), (20,'B-5'), (22,'D-6'), (24,'G-6'), (26,'D-6'), (28,'B-5'), (30,'A-5'), (32,'E-5'), (34,'A-5'), (36,'C-6'), (38,'E-6'), (40,'A-6'), (42,'E-6'), (44,'C-6'), (46,'B-5'), (48,'A-5'), (50,'C-6'), (52,'F-6'), (54,'C-6'), (56,'A-5'), (58,'G-5'), (60,'F-5'), (62,'E-5')],
    5: [(0,'A-5'), (2,'C-6'), (4,'E-6'), (6,'C-6'), (8,'B-5'), (10,'A-5'), (12,'G-5'), (14,'E-5'), (16,'A-5'), (18,'C-6'), (20,'F-6'), (22,'C-6'), (24,'A-5'), (26,'G-5'), (28,'E-5'), (30,'C-5'), (32,'G-5'), (34,'C-6'), (36,'E-6'), (38,'G-6'), (40,'E-6'), (42,'C-6'), (44,'B-5'), (46,'G-5'), (48,'F-5'), (50,'G-5'), (52,'B-5'), (54,'D-6'), (56,'B-5'), (58,'A-5'), (60,'G-5'), (62,'D-5')],
    6: [(0,'F-5'), (2,'A-5'), (4,'D-6'), (6,'F-6'), (8,'A-6'), (10,'F-6'), (12,'D-6'), (14,'C-6'), (16,'G#5'), (18,'B-5'), (20,'E-6'), (22,'G#6'), (24,'B-6'), (26,'G#6'), (28,'E-6'), (30,'D-6'), (32,'A-5'), (34,'C-6'), (36,'E-6'), (38,'A-6'), (40,'C-7'), (42,'A-6'), (44,'E-6'), (46,'C-6'), (48,'G#5'), (50,'B-5'), (52,'E-6'), (54,'B-5'), (56,'G#5'), (58,'B-5'), (60,'D-6'), (62,'E-6')],
    7: [(0,'A-5'), (2,'C-6'), (4,'F-6'), (6,'C-6'), (8,'A-5'), (10,'G-5'), (12,'F-5'), (14,'A-5'), (16,'B-5'), (18,'D-6'), (20,'G-6'), (22,'D-6'), (24,'B-5'), (26,'A-5'), (28,'G-5'), (30,'B-5'), (32,'C-6'), (34,'E-6'), (36,'A-6'), (38,'E-6'), (40,'C-6'), (42,'B-5'), (44,'A-5'), (46,'G-5'), (48,'G#5'), (50,'B-5'), (52,'D-6'), (54,'E-6'), (56,'B-5'), (58,'G#5'), (60,'D-6')],
}

bar_styles = {
    0: [('A', False, False, 'full', 'light'), ('A', False, False, 'full', 'light'), ('B', False, False, 'full', 'basic'), ('B', False, False, 'full', 'basic')],
    1: [('A', False, False, 'full', 'light'), ('B', False, False, 'full', 'light'), ('A', False, False, 'full', 'light'), ('FILL', False, False, 'full', 'light')],
    2: [('B', False, False, 'full', 'basic'), ('B', False, False, 'full', 'basic'), ('C', False, False, 'full', 'basic'), ('FILL', False, False, 'push', 'light')],
    3: [('C', False, False, 'full', 'light'), ('B', False, False, 'full', 'light'), ('C', False, False, 'full', 'light'), ('B', False, False, 'full', 'light')],
    4: [('BRK', False, True, 'half', 'dense'), ('HALF', False, True, 'half', 'dense'), ('A', False, False, 'half', 'dense'), ('FILL', True, False, 'push', 'dense')],
    5: [('A', False, False, 'full', 'basic'), ('B', False, False, 'full', 'basic'), ('A', False, False, 'full', 'basic'), ('B', False, False, 'full', 'basic')],
    6: [('C', True, False, 'full', 'light'), ('C', True, False, 'full', 'light'), ('B', True, False, 'full', 'light'), ('FILL', True, False, 'push', 'light')],
    7: [('B', False, False, 'full', 'basic'), ('B', False, False, 'full', 'basic'), ('C', False, False, 'full', 'basic'), ('FILL', False, False, 'push', 'basic')],
}


def cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {'pattern': pattern, 'row': row, 'channel': channel}
    if note is not None:
        args['note'] = note
    if instrument is not None:
        args['instrument'] = instrument
    if volume is not None:
        args['volume'] = int(volume)
    if effect is not None:
        args['effect'] = int(effect)
    if effect_param is not None:
        args['effect_param'] = int(effect_param)
    add('pattern_set_cell', **args)


def place_kick(pattern, row, vol=None):
    cell(pattern, row, 0, note='C-5', instrument=1, volume=vol)


def place_snare(pattern, row, vol=None):
    cell(pattern, row, 1, note='C-5', instrument=2, volume=vol)


def place_crash(pattern, row):
    cell(pattern, row, 1, note='C-5', instrument=11, volume=VOL(52))


def place_hat(pattern, row, open_hat=False, vol=None):
    inst = 12 if open_hat else 3
    cell(pattern, row, 2, note='C-5', instrument=inst, volume=vol)


def place_bass(pattern, row, note, vol=None):
    cell(pattern, row, 3, note=note, instrument=4, volume=vol)


def place_lead(pattern, row, note, vol=None):
    cell(pattern, row, 4, note=note, instrument=5, volume=vol)


def place_arp(pattern, row, note, vol=None):
    cell(pattern, row, 5, note=note, instrument=10, volume=vol)


def place_chord(pattern, row, chord, vol=None):
    info = chord_info[chord]
    li, ri = (6, 7) if info['quality'] == 'maj' else (8, 9)
    cell(pattern, row, 6, note=info['stab'], instrument=li, volume=vol)
    cell(pattern, row, 7, note=info['stab'], instrument=ri, volume=vol)


def drums_bar(pattern, row0, style='A', dense_hats=False, sparse_hats=False, final_fill=False):
    kick_map = {
        'A': [0, 6, 8, 14],
        'B': [0, 5, 8, 10, 14],
        'C': [0, 4, 7, 8, 11, 14],
        'BRK': [0, 8],
        'HALF': [0, 8, 12],
        'FILL': [0, 6, 8, 10, 12, 14],
    }
    for r in kick_map.get(style, kick_map['A']):
        place_kick(pattern, row0 + r, VOL(60 if r in (0, 8) else 52))

    if final_fill:
        snare_rows = [4, 8, 10, 12, 13, 14]
    elif style == 'BRK':
        snare_rows = [12]
    elif style == 'FILL':
        snare_rows = [4, 10, 12, 14]
    else:
        snare_rows = [4, 12]
    for r in snare_rows:
        v = 56 if r in (4, 12) else 44 + (r % 4) * 3
        place_snare(pattern, row0 + r, VOL(min(v, 64)))

    if sparse_hats:
        hat_rows = [2, 6, 10, 14]
    elif dense_hats:
        hat_rows = list(range(16))
    else:
        hat_rows = [0, 2, 4, 6, 8, 10, 12, 14]

    for r in hat_rows:
        if dense_hats:
            vol = VOL(28 if r % 2 else 38)
            if r in (0, 4, 8, 12):
                vol = VOL(46)
            place_hat(pattern, row0 + r, open_hat=False, vol=vol)
        else:
            open_hat = (r in (10, 14) and style in ('B', 'C', 'FILL'))
            base = {0: 46, 2: 34, 4: 42, 6: 34, 8: 46, 10: 36, 12: 42, 14: 38}.get(r, 36)
            if sparse_hats:
                base += 4
            place_hat(pattern, row0 + r, open_hat=open_hat, vol=VOL(base))


def bass_bar(pattern, row0, chord, break_mode=False):
    seq = chord_info[chord]['bass_break' if break_mode else 'bass']
    step = 4 if break_mode else 2
    for i, note in enumerate(seq):
        v = VOL(54 if i == 0 else 46 if i % 2 == 0 else 40)
        place_bass(pattern, row0 + i * step, note, vol=v)


def chords_bar(pattern, row0, chord, mode='full'):
    if mode == 'full':
        rows, vols = [0, 4, 8, 12], [VOL(46), VOL(36), VOL(44), VOL(34)]
    elif mode == 'half':
        rows, vols = [0, 8], [VOL(46), VOL(40)]
    elif mode == 'sync':
        rows, vols = [2, 6, 10, 14], [VOL(42), VOL(34), VOL(40), VOL(34)]
    elif mode == 'push':
        rows, vols = [0, 4, 8, 10, 12, 14], [VOL(44), VOL(34), VOL(42), VOL(32), VOL(40), VOL(32)]
    else:
        rows, vols = [0], [VOL(44)]
    for r, v in zip(rows, vols):
        place_chord(pattern, row0 + r, chord, vol=v)


def arp_bar(pattern, row0, chord, style='basic'):
    info = chord_info[chord]
    if style == 'basic':
        rows = list(range(0, 16, 2))
        seq = info['arp_basic']
        vols = [VOL(34 if i % 2 else 40) for i in range(len(rows))]
    elif style == 'light':
        rows = [2, 6, 10, 14]
        seq = info['arp_light']
        vols = [VOL(34), VOL(36), VOL(34), VOL(38)]
    elif style == 'dense':
        rows = list(range(16))
        seq = info['arp_dense']
        vols = [VOL(28 if i % 2 else 34) for i in range(len(rows))]
    elif style == 'off':
        return
    else:
        rows = list(range(0, 16, 4))
        seq = info['arp_light']
        vols = [VOL(34)] * len(rows)
    for r, note, v in zip(rows, seq, vols):
        place_arp(pattern, row0 + r, note, vol=v)

# arrange
crash_patterns = {0, 3, 5, 6}
for p in range(8):
    for bar, chord in enumerate(progressions[p]):
        row0 = bar * 16
        drum_style, dense_hats, sparse_hats, chord_mode, arp_style = bar_styles[p][bar]
        if p in crash_patterns and bar == 0:
            place_crash(p, row0)
        drums_bar(
            p, row0,
            style=drum_style,
            dense_hats=(dense_hats or p == 6),
            sparse_hats=sparse_hats,
            final_fill=(p == 7 and bar == 3),
        )
        bass_bar(p, row0, chord, break_mode=(p == 4 and bar < 2))
        chords_bar(p, row0, chord, mode=chord_mode)
        if p == 0 and bar < 2:
            arp_bar(p, row0, chord, style='light')
        else:
            arp_bar(p, row0, chord, style=arp_style)

# leads
for p, notes in lead_lines.items():
    for row, note in notes:
        v = VOL(50 if row % 16 in (0, 8) else 44)
        if p in (6, 7) and row >= 32:
            v = VOL(52 if row % 16 in (0, 8) else 46)
        place_lead(p, row, note, vol=v)

# special intro accents
place_kick(0, 0, VOL(64))
place_hat(0, 0, open_hat=True, vol=VOL(48))
for p in (3, 5, 6):
    place_kick(p, 0, VOL(64))

# clean loop: stop lingering voices on last row; avoid any event at exact restart
for ch in range(4, 8):
    cell(7, 63, ch, note='OFF')

with open(root / 'build_batch.json', 'w') as f:
    json.dump(cmds, f)
with open(root / 'arrangement.json', 'w') as f:
    json.dump({'progressions': progressions, 'lead_lines': lead_lines}, f, indent=2)

print(f'wrote {len(cmds)} FT2 commands')
