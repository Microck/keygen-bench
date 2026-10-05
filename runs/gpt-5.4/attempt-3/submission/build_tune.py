import os, json, math, wave, struct
import numpy as np

SR = 44100
ROOT_FREQ = 261.6255653005986  # C4
SAMPLES_DIR = '/workspace/samples'
os.makedirs(SAMPLES_DIR, exist_ok=True)

rng = np.random.default_rng(12345)

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

def midi_to_ft2(midi):
    octave = midi // 12 - 1
    return f"{NOTE_NAMES[midi % 12]}{octave}"


def norm(x, peak=0.92):
    m = float(np.max(np.abs(x)))
    if m < 1e-9:
        return x.astype(np.float32)
    return (x / m * peak).astype(np.float32)


def write_wav(path, data, sr=SR):
    data = np.asarray(np.clip(data, -1, 1), dtype=np.float32)
    pcm = (data * 32767.0).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def lowpass(x, cutoff, sr=SR):
    x = np.asarray(x, dtype=np.float32)
    if cutoff <= 0:
        return np.zeros_like(x)
    a = 1.0 - math.exp(-2.0 * math.pi * cutoff / sr)
    y = np.empty_like(x)
    prev = 0.0
    for i, xi in enumerate(x):
        prev += a * (float(xi) - prev)
        y[i] = prev
    return y


def highpass(x, cutoff, sr=SR):
    return np.asarray(x, dtype=np.float32) - lowpass(x, cutoff, sr)


def bandpass(x, low, high, sr=SR):
    return lowpass(highpass(x, low, sr), high, sr)


def phase_from_freq(freq, sr=SR):
    return np.cumsum(freq, dtype=np.float64) / sr


def saw_from_phase(ph):
    return 2.0 * np.mod(ph, 1.0) - 1.0


def square_from_phase(ph, duty=0.5):
    return np.where(np.mod(ph, 1.0) < duty, 1.0, -1.0)


def tri_from_phase(ph):
    frac = np.mod(ph, 1.0)
    return 4.0 * np.abs(frac - 0.5) - 1.0


def synth_kick():
    dur = 0.30
    t = np.arange(int(SR * dur)) / SR
    freq = 155.0 * np.exp(-28.0 * t) + 42.0
    ph = phase_from_freq(freq)
    body = np.sin(2 * np.pi * ph)
    sub = np.sin(2 * np.pi * (ph * 0.5 + 0.02))
    click = highpass(rng.normal(0, 1, len(t)).astype(np.float32), 3500) * np.exp(-180 * t)
    amp = np.exp(-12.5 * t)
    x = (0.92 * body + 0.22 * sub) * amp + 0.25 * click
    x = np.tanh(2.8 * x)
    x *= np.exp(-4.0 * t)
    x[:64] *= np.linspace(0, 1, 64)
    return norm(x, 0.94)


def synth_snare():
    dur = 0.20
    t = np.arange(int(SR * dur)) / SR
    noise = rng.normal(0, 1, len(t)).astype(np.float32)
    n_hi = highpass(noise, 2200) * np.exp(-24 * t)
    n_mid = bandpass(noise, 700, 4000) * np.exp(-18 * t)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-28 * t)
    tone2 = np.sin(2 * np.pi * 330 * t) * np.exp(-34 * t)
    x = 0.72 * n_hi + 0.32 * n_mid + 0.30 * tone + 0.12 * tone2
    x = np.tanh(1.8 * x)
    x[:64] *= np.linspace(0, 1, 64)
    return norm(x, 0.90)


def synth_hat():
    dur = 0.065
    t = np.arange(int(SR * dur)) / SR
    noise = rng.normal(0, 1, len(t)).astype(np.float32)
    ph1 = phase_from_freq(np.full(len(t), 6321.0))
    ph2 = phase_from_freq(np.full(len(t), 9127.0))
    metallic = square_from_phase(ph1, 0.35) * square_from_phase(ph2, 0.47)
    x = 0.7 * highpass(noise, 6000) + 0.3 * metallic
    x *= np.exp(-62 * t)
    x = highpass(x, 3500)
    x[:32] *= np.linspace(0, 1, 32)
    return norm(x, 0.85)


def synth_crash():
    dur = 0.75
    t = np.arange(int(SR * dur)) / SR
    noise = rng.normal(0, 1, len(t)).astype(np.float32)
    x = 0.55 * highpass(noise, 3500) + 0.25 * bandpass(noise, 1200, 5000)
    env = np.exp(-3.7 * t) * (1.0 - np.exp(-80 * t))
    x = lowpass(x, 9000) * env
    x = np.tanh(1.6 * x)
    x[:64] *= np.linspace(0, 1, 64)
    return norm(x, 0.82)


def synth_bass():
    dur = 0.092
    t = np.arange(int(SR * dur)) / SR
    freq = ROOT_FREQ * (1.0 + 0.06 * np.exp(-35 * t))
    ph = phase_from_freq(freq)
    saw = saw_from_phase(ph)
    tri = tri_from_phase(ph)
    sub = np.sin(2 * np.pi * ph)
    x = 0.44 * saw + 0.34 * tri + 0.22 * sub
    x = lowpass(x, 1350)
    env = (1.0 - np.exp(-220 * t)) * np.exp(-27 * t)
    x *= env
    x = np.tanh(2.0 * x)
    x[:32] *= np.linspace(0, 1, 32)
    return norm(x, 0.88)


def synth_arp():
    dur = 0.175
    t = np.arange(int(SR * dur)) / SR
    detunes = [-0.0065, 0.0, 0.0058]
    layers = []
    for d in detunes:
        ph = phase_from_freq(np.full(len(t), ROOT_FREQ * (1.0 + d)))
        layers.append(saw_from_phase(ph))
    phm = phase_from_freq(np.full(len(t), ROOT_FREQ))
    pulse = square_from_phase(phm, 0.38)
    x = 0.25 * layers[0] + 0.35 * layers[1] + 0.25 * layers[2] + 0.15 * pulse
    x = lowpass(x, 3600)
    x = highpass(x, 260)
    env = (1.0 - np.exp(-260 * t)) * np.exp(-16.5 * t)
    x *= env
    x = np.tanh(1.7 * x)
    x[:48] *= np.linspace(0, 1, 48)
    return norm(x, 0.80)


def synth_lead():
    dur = 0.38
    t = np.arange(int(SR * dur)) / SR
    vib = 0.0035 * np.sin(2 * np.pi * 5.8 * t) * (1.0 - np.exp(-8 * t))
    freq = ROOT_FREQ * (1.0 + 0.035 * np.exp(-11 * t)) * (1.0 + vib)
    ph = phase_from_freq(freq)
    pulse = square_from_phase(ph, 0.36 + 0.03 * np.sin(2 * np.pi * 4.5 * t))
    saw = saw_from_phase(ph)
    tri = tri_from_phase(ph)
    x = 0.42 * pulse + 0.33 * saw + 0.25 * tri
    x = lowpass(x, 2900)
    env = (1.0 - np.exp(-200 * t)) * np.exp(-7.2 * t)
    x *= env
    delay = int(0.017 * SR)
    if delay < len(x):
        y = np.copy(x)
        y[delay:] += 0.22 * x[:-delay]
        x = y
    x = np.tanh(1.6 * x)
    x[:48] *= np.linspace(0, 1, 48)
    return norm(x, 0.84)


def synth_bell():
    dur = 0.54
    t = np.arange(int(SR * dur)) / SR
    f = ROOT_FREQ
    x = (
        1.00 * np.sin(2 * np.pi * f * t) * np.exp(-6.2 * t)
        + 0.55 * np.sin(2 * np.pi * 2.01 * f * t) * np.exp(-7.4 * t)
        + 0.32 * np.sin(2 * np.pi * 3.87 * f * t) * np.exp(-9.5 * t)
        + 0.18 * np.sin(2 * np.pi * 5.43 * f * t) * np.exp(-12.0 * t)
    )
    x += 0.05 * highpass(rng.normal(0, 1, len(t)).astype(np.float32), 1800) * np.exp(-22 * t)
    x = highpass(x, 180)
    x[:48] *= np.linspace(0, 1, 48)
    return norm(x, 0.86)


def render_samples():
    sample_defs = {
        'kick.wav': synth_kick(),
        'snare.wav': synth_snare(),
        'hat.wav': synth_hat(),
        'crash.wav': synth_crash(),
        'bass.wav': synth_bass(),
        'arp.wav': synth_arp(),
        'lead.wav': synth_lead(),
        'bell.wav': synth_bell(),
    }
    for name, data in sample_defs.items():
        write_wav(os.path.join(SAMPLES_DIR, name), data)


# Composition data -----------------------------------------------------------

commands = []

def add_cmd(name, arguments):
    commands.append({'name': name, 'arguments': arguments})

# module + song
add_cmd('module_new', {'channels': 10, 'name': 'Checksum Skies'})
add_cmd('song_set', {'name': 'Checksum Skies', 'bpm': 150, 'speed': 6, 'length': 8, 'loop_start': 1, 'channels': 10})
for p in range(8):
    add_cmd('pattern_set_length', {'pattern': p, 'rows': 64})
for pos, pat in enumerate(range(8)):
    add_cmd('order_set', {'position': pos, 'pattern': pat})

# sample loading
sample_loads = [
    (1, 'kick.wav', 'Kick', 64, 128),
    (2, 'snare.wav', 'Snare', 58, 128),
    (3, 'hat.wav', 'Hat', 42, 176),
    (4, 'crash.wav', 'Crash', 44, 188),
    (5, 'bass.wav', 'BassPlk', 56, 128),
    (6, 'arp.wav', 'Arp L', 38, 48),
    (7, 'arp.wav', 'Arp R', 38, 208),
    (8, 'lead.wav', 'Lead', 46, 148),
    (9, 'bell.wav', 'Bell', 40, 96),
    (10, 'lead.wav', 'Lead Echo', 34, 104),
]
for inst, wav, iname, vol, pan in sample_loads:
    add_cmd('sample_load', {'path': os.path.join(SAMPLES_DIR, wav), 'instrument': inst})
    add_cmd('instrument_set', {'instrument': inst, 'name': iname})
    add_cmd('sample_set', {'instrument': inst, 'sample': 0, 'name': iname, 'volume': vol, 'panning': pan})

# Event storage
cells = {}

def add_cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    key = (pattern, row, channel)
    cell = {'pattern': pattern, 'row': row, 'channel': channel}
    if note is not None:
        cell['note'] = midi_to_ft2(note) if isinstance(note, int) else note
    if instrument is not None:
        cell['instrument'] = instrument
    if volume is not None:
        v = max(0, min(64, int(volume)))
        cell['volume'] = 16 + v
    if effect is not None:
        cell['effect'] = int(effect)
    if effect_param is not None:
        cell['effect_param'] = int(effect_param)
    cells[key] = cell

# Harmonic material
progA = [
    {'name': 'Em7', 'chord': [76, 79, 83, 86], 'bass': [40, 52, 47, 50, 50]},
    {'name': 'Cmaj7', 'chord': [72, 76, 79, 83], 'bass': [36, 48, 43, 47, 50]},
    {'name': 'Gmaj7', 'chord': [79, 83, 86, 90], 'bass': [43, 55, 50, 47, 42]},
    {'name': 'Dadd9', 'chord': [74, 78, 81, 88], 'bass': [38, 50, 45, 45, 47]},
]
progB = [
    {'name': 'Em7', 'chord': [76, 79, 83, 86], 'bass': [40, 52, 47, 50, 38]},
    {'name': 'Dadd9', 'chord': [74, 78, 81, 88], 'bass': [38, 50, 45, 47, 36]},
    {'name': 'Cmaj7', 'chord': [72, 76, 79, 83], 'bass': [36, 48, 43, 47, 35]},
    {'name': 'B7', 'chord': [71, 75, 78, 81], 'bass': [35, 47, 42, 45, 47]},
]

seqL_a = [0, 2, 1, 2, 3, 2, 1, 2]
seqR_a = [1, 3, 2, 3, 2, 3, 1, 3]
seqL_b = [0, 1, 2, 1, 3, 1, 2, 1]
seqR_b = [2, 3, 1, 3, 2, 3, 0, 3]


def add_arp_bar(pattern, bar, chord, mode='full', variant=0, vol_l=22, vol_r=20):
    base = bar * 16
    if variant % 2 == 0:
        seqL, seqR = seqL_a, seqR_a
    else:
        seqL, seqR = seqL_b, seqR_b
    if mode == 'none':
        return
    if mode == 'intro':
        rowsL = [0, 4, 8, 12]
        idxL = [0, 2, 1, 3]
        rowsR = [2, 6, 10, 14]
        idxR = [1, 3, 2, 3]
    elif mode == 'half':
        rowsL = [0, 4, 8, 12]
        idxL = [0, 2, 3, 1]
        rowsR = [1, 5, 9, 13]
        idxR = [1, 3, 2, 3]
    else:
        rowsL = list(range(0, 16, 2))
        idxL = seqL
        rowsR = list(range(1, 16, 2))
        idxR = seqR
    for rr, ii in zip(rowsL, idxL):
        v = vol_l + (2 if rr in (0, 8) else 0)
        add_cell(pattern, base + rr, 5, chord[ii], 6, v)
    for rr, ii in zip(rowsR, idxR):
        v = vol_r + (2 if rr in (1, 9) else 0)
        add_cell(pattern, base + rr, 6, chord[ii], 7, v)


def add_bass_bar(pattern, bar, bar_data, style='normal'):
    base = bar * 16
    notes = bar_data['bass']
    if style == 'none':
        return
    if style == 'sparse':
        rows = [0, 8, 12]
        idxs = [0, 2, 3]
        vols = [42, 34, 30]
    elif style == 'break':
        rows = [0, 12]
        idxs = [0, 4]
        vols = [40, 28]
    elif style == 'busy':
        rows = [0, 4, 6, 8, 10, 12, 14]
        idxs = [0, 1, 2, 2, 3, 3, 4]
        vols = [42, 34, 28, 32, 28, 30, 24]
    else:
        rows = [0, 4, 8, 12, 14]
        idxs = [0, 1, 2, 3, 4]
        vols = [42, 34, 30, 32, 24]
    for r, i, v in zip(rows, idxs, vols):
        add_cell(pattern, base + r, 4, notes[i], 5, v)


def add_hat_row(pattern, row, vol=20, note='C-4'):
    add_cell(pattern, row, 2, note, 3, vol)


def add_drum_bar(pattern, bar, style='normal_a'):
    base = bar * 16
    def kick(rr, vol=48):
        add_cell(pattern, base + rr, 0, 'C-4', 1, vol)
    def snare(rr, vol=42):
        add_cell(pattern, base + rr, 1, 'C-4', 2, vol)
    def hat_series(rows, basevol=18, accent=25):
        for rr in rows:
            v = accent if rr % 4 == 2 else basevol
            note = 'C-4' if rr % 4 else 'D-4'
            add_hat_row(pattern, base + rr, v, note)

    if style == 'none':
        return
    if style == 'hatlight':
        for rr, v in [(4, 14), (8, 16), (12, 14)]:
            add_hat_row(pattern, base + rr, v)
        return
    if style == 'breakdown':
        hat_series([2, 6, 10, 14], 16, 20)
        snare(12, 34)
        return
    if style == 'sparse':
        kick(0, 42); kick(8, 40)
        snare(12, 38)
        hat_series([2, 6, 10, 14], 17, 22)
        return
    if style == 'light':
        kick(0, 46); kick(8, 42)
        snare(4, 40); snare(12, 40)
        hat_series(range(0, 16, 2), 15, 22)
        return
    if style == 'normal_a':
        for rr, v in [(0, 50), (8, 46), (10, 38), (14, 34)]:
            kick(rr, v)
        snare(4, 44); snare(12, 44)
        hat_series(range(0, 16, 2), 18, 26)
        return
    if style == 'normal_b':
        for rr, v in [(0, 50), (6, 34), (8, 46), (11, 32), (14, 34)]:
            kick(rr, v)
        snare(4, 44); snare(12, 44)
        hat_series(range(0, 16, 2), 18, 26)
        add_hat_row(pattern, base + 15, 14, 'F#4')
        return
    if style == 'drive':
        for rr, v in [(0, 50), (5, 34), (8, 46), (10, 38), (14, 36)]:
            kick(rr, v)
        snare(4, 44); snare(12, 44)
        hat_series(range(0, 16, 2), 19, 28)
        add_hat_row(pattern, base + 15, 16, 'F#4')
        return
    if style == 'fill':
        for rr, v in [(0, 50), (8, 46), (10, 38), (14, 34)]:
            kick(rr, v)
        snare(4, 44); snare(12, 42); snare(15, 32)
        hat_series(range(0, 16, 2), 18, 26)
        add_hat_row(pattern, base + 13, 16, 'D-4')
        add_hat_row(pattern, base + 15, 18, 'F#4')
        return
    if style == 'fill2':
        for rr, v in [(0, 50), (6, 36), (8, 46), (11, 34), (14, 36)]:
            kick(rr, v)
        snare(4, 44); snare(12, 42); snare(14, 30); snare(15, 26)
        hat_series(range(0, 16, 2), 18, 26)
        add_hat_row(pattern, base + 13, 16, 'D-4')
        return
    if style == 'build':
        for rr, v in [(0, 44), (8, 42), (12, 36), (14, 34)]:
            kick(rr, v)
        snare(4, 38); snare(12, 40)
        hat_series(range(0, 8, 2), 16, 22)
        for rr in range(8, 16):
            add_hat_row(pattern, base + rr, 14 + (rr % 2) * 4, 'D-4' if rr % 2 == 0 else 'F#4')
        return
    if style == 'turnaround':
        for rr, v in [(0, 50), (6, 34), (8, 46), (10, 38), (14, 34)]:
            kick(rr, v)
        snare(4, 44); snare(12, 44)
        hat_series(range(0, 16, 2), 18, 26)
        add_hat_row(pattern, base + 15, 14, 'C-4')
        return


def add_melody(pattern, notes, channel=7, instrument=8, basevol=44):
    for item in notes:
        if len(item) == 2:
            row, midi = item
            vol = basevol
        else:
            row, midi, vol = item
        add_cell(pattern, row, channel, midi, instrument, vol)


def add_bell(pattern, notes, channel=8, instrument=9, basevol=30):
    for item in notes:
        if len(item) == 2:
            row, midi = item
            vol = basevol
        else:
            row, midi, vol = item
        add_cell(pattern, row, channel, midi, instrument, vol)


# Patterns ------------------------------------------------------------------

# Pattern 0 intro
for bar, chord_data in enumerate(progA):
    arp_mode = ['half', 'intro', 'full', 'full'][bar]
    arp_vol = [16, 18, 21, 22][bar]
    add_arp_bar(0, bar, chord_data['chord'], mode=arp_mode, variant=bar, vol_l=arp_vol, vol_r=max(12, arp_vol - 2))
    bass_style = ['none', 'sparse', 'normal', 'normal'][bar]
    add_bass_bar(0, bar, chord_data, bass_style)
for bar, style in enumerate(['none', 'hatlight', 'sparse', 'fill']):
    add_drum_bar(0, bar, style)
add_bell(0, [(30, 83, 24), (50, 71, 26), (54, 74, 28), (58, 79, 30), (62, 83, 32)])
add_cell(0, 32, 3, 'C-4', 4, 28)

# Pattern 1 main A
for bar, chord_data in enumerate(progA):
    add_arp_bar(1, bar, chord_data['chord'], mode='full', variant=bar, vol_l=22, vol_r=20)
    add_bass_bar(1, bar, chord_data, 'normal')
for bar, style in enumerate(['normal_a', 'normal_b', 'normal_a', 'fill']):
    add_drum_bar(1, bar, style)
add_cell(1, 0, 3, 'C-4', 4, 34)
mel1 = [
    (2, 71), (4, 74), (6, 76), (8, 79, 48), (10, 78), (12, 76), (14, 74),
    (18, 67), (20, 71), (22, 72), (24, 76, 48), (26, 74), (28, 72), (30, 71),
    (34, 74), (36, 79), (38, 81), (40, 83, 48), (42, 81), (44, 79), (46, 76),
    (50, 69), (52, 74), (54, 76), (56, 78, 48), (58, 76), (60, 74), (62, 71),
]
add_melody(1, mel1, 7, 8, 44)
add_bell(1, [(14, 86, 28), (30, 83, 28), (46, 81, 28)])

# Pattern 2 main B
for bar, chord_data in enumerate(progA):
    add_arp_bar(2, bar, chord_data['chord'], mode='full', variant=bar + 1, vol_l=23, vol_r=21)
    add_bass_bar(2, bar, chord_data, 'busy' if bar in (1, 2) else 'normal')
for bar, style in enumerate(['normal_b', 'drive', 'normal_b', 'fill2']):
    add_drum_bar(2, bar, style)
mel2 = [
    (0, 76, 46), (2, 79), (6, 83, 48), (8, 81), (10, 79), (12, 78), (14, 76),
    (16, 72, 44), (18, 76), (20, 79), (24, 83, 48), (26, 81), (28, 79), (30, 76),
    (32, 71, 44), (34, 74), (36, 79, 46), (38, 81), (42, 86, 50), (44, 83), (46, 81),
    (48, 69, 42), (50, 78), (52, 81, 46), (54, 83), (58, 81), (60, 78), (62, 74),
]
add_melody(2, mel2, 7, 8, 44)
add_melody(2, [(36, 74, 28), (38, 76, 28), (42, 79, 30), (44, 78, 28), (52, 76, 28), (54, 78, 28)], 9, 10, 28)
add_bell(2, [(14, 83, 26), (30, 79, 26), (46, 86, 28)])

# Pattern 3 bridge
for bar, chord_data in enumerate(progB):
    add_arp_bar(3, bar, chord_data['chord'], mode='half' if bar < 2 else 'full', variant=bar, vol_l=18 if bar < 2 else 20, vol_r=16 if bar < 2 else 18)
    add_bass_bar(3, bar, chord_data, 'break' if bar < 2 else 'sparse')
for bar, style in enumerate(['sparse', 'sparse', 'light', 'build']):
    add_drum_bar(3, bar, style)
add_cell(3, 0, 3, 'C-4', 4, 24)
add_bell(3, [(6, 88, 28), (10, 91, 28), (14, 95, 30), (22, 81, 26), (26, 78, 26), (30, 76, 26),
             (42, 88, 28), (58, 90, 28)])
mel3 = [(34, 72, 40), (38, 67, 38), (42, 76, 42), (46, 71, 40), (50, 75, 42), (54, 78, 42), (58, 81, 44), (62, 83, 46)]
add_melody(3, mel3, 7, 8, 42)

# Pattern 4 high return
for bar, chord_data in enumerate(progA):
    add_arp_bar(4, bar, chord_data['chord'], mode='full', variant=bar + 1, vol_l=24, vol_r=22)
    add_bass_bar(4, bar, chord_data, 'busy' if bar in (0, 2) else 'normal')
for bar, style in enumerate(['drive', 'normal_b', 'drive', 'fill']):
    add_drum_bar(4, bar, style)
add_cell(4, 0, 3, 'C-4', 4, 36)
mel4 = [
    (2, 83, 46), (4, 86, 48), (6, 88, 46), (8, 91, 50), (10, 90, 46), (12, 88, 44), (14, 86, 44),
    (18, 79, 44), (20, 83, 46), (22, 84, 44), (24, 88, 48), (26, 86, 44), (28, 84, 42), (30, 83, 42),
    (34, 86, 46), (36, 91, 50), (38, 93, 50), (40, 95, 52), (42, 93, 48), (44, 91, 46), (46, 88, 44),
    (50, 81, 44), (52, 86, 46), (54, 88, 46), (56, 90, 48), (58, 88, 44), (60, 86, 44), (62, 83, 44),
]
add_melody(4, mel4, 7, 8, 45)
# octave-down support on echo channel
support4 = [(2, 71, 24), (8, 79, 26), (24, 76, 24), (36, 79, 26), (40, 83, 28), (56, 78, 24)]
add_melody(4, support4, 9, 10, 24)

# Pattern 5 solo
for bar, chord_data in enumerate(progA):
    add_arp_bar(5, bar, chord_data['chord'], mode='full', variant=bar, vol_l=23, vol_r=21)
    add_bass_bar(5, bar, chord_data, 'busy' if bar in (0, 3) else 'normal')
for bar, style in enumerate(['normal_a', 'drive', 'normal_b', 'fill2']):
    add_drum_bar(5, bar, style)
mel5 = [
    (0, 76, 44), (2, 79, 44), (4, 83, 46), (6, 86, 48), (8, 83, 46), (10, 79, 44), (12, 78, 42), (14, 76, 42),
    (16, 79, 44), (18, 76, 42), (20, 84, 46), (22, 83, 46), (24, 79, 44), (26, 76, 42), (28, 74, 42), (30, 72, 42),
    (32, 74, 44), (34, 79, 44), (36, 81, 46), (38, 83, 46), (40, 86, 48), (42, 83, 46), (44, 81, 44), (46, 79, 44),
    (48, 69, 42), (50, 74, 44), (52, 78, 44), (54, 81, 46), (56, 83, 48), (58, 81, 46), (60, 78, 44), (62, 76, 44),
]
add_melody(5, mel5, 7, 8, 44)
add_bell(5, [(7, 91, 24), (23, 88, 24), (39, 93, 26), (55, 90, 26)])
add_melody(5, [(6, 79, 24), (20, 76, 24), (40, 74, 24), (56, 71, 24)], 9, 10, 24)

# Pattern 6 breakdown/build
for bar, chord_data in enumerate(progA):
    add_arp_bar(6, bar, chord_data['chord'], mode='half' if bar < 2 else 'full', variant=bar + 1, vol_l=18 if bar < 2 else 22, vol_r=16 if bar < 2 else 20)
    add_bass_bar(6, bar, chord_data, 'sparse' if bar < 2 else 'normal')
for bar, style in enumerate(['breakdown', 'light', 'build', 'turnaround']):
    add_drum_bar(6, bar, style)
# extra build hats/snare roll
for rr, vol in zip([48, 50, 52, 54, 56, 58, 60, 62], [20, 22, 24, 26, 28, 32, 36, 40]):
    add_cell(6, rr, 1, 'C-4', 2, vol)
for rr in range(48, 64):
    add_hat_row(6, rr, 14 + (rr % 2) * 6, 'D-4' if rr % 2 == 0 else 'F#4')
add_bell(6, [(32, 76, 24), (36, 78, 24), (40, 79, 26), (44, 81, 26), (48, 83, 28), (52, 84, 28), (56, 86, 30), (60, 88, 32)])
add_cell(6, 32, 3, 'C-4', 4, 30)
add_melody(6, [(56, 83, 34), (60, 86, 36)], 7, 8, 34)

# Pattern 7 finale / turnaround back to pattern 1
for bar, chord_data in enumerate(progA):
    add_arp_bar(7, bar, chord_data['chord'], mode='full', variant=bar, vol_l=24, vol_r=22)
    add_bass_bar(7, bar, chord_data, 'busy' if bar in (0, 2) else 'normal')
for bar, style in enumerate(['drive', 'normal_b', 'drive', 'turnaround']):
    add_drum_bar(7, bar, style)
add_cell(7, 0, 3, 'C-4', 4, 36)
mel7 = [
    (2, 76, 46), (4, 79, 46), (6, 83, 48), (8, 81, 46), (10, 79, 44), (12, 78, 44), (14, 76, 44),
    (18, 72, 44), (20, 76, 44), (22, 79, 46), (24, 83, 48), (26, 81, 46), (28, 79, 44), (30, 76, 44),
    (34, 83, 46), (36, 86, 48), (38, 91, 50), (40, 88, 48), (42, 86, 46), (44, 83, 44), (46, 81, 44),
    (50, 74, 44), (52, 78, 46), (54, 81, 46), (56, 78, 44), (58, 76, 42), (62, 71, 42),
]
add_melody(7, mel7, 7, 8, 44)
add_melody(7, [(36, 79, 26), (38, 83, 28), (40, 86, 28), (42, 83, 26), (54, 74, 24)], 9, 10, 24)
add_bell(7, [(14, 83, 24), (30, 79, 24), (46, 86, 26)])

# Commit cells into commands in stable order
for _, cell in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
    add_cmd('pattern_set_cell', cell)

# Write assets
render_samples()
with open('/workspace/build_commands.json', 'w') as f:
    json.dump(commands, f)
print(f'wrote {len(commands)} commands and {len(cells)} cells')
