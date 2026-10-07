import json, math, wave
from pathlib import Path
import numpy as np

SR = 44100
BASE_FREQ = 658.2551138257398  # tuned so C-4 with relative_note 12 lands near concert pitch
ROOT = Path('/workspace')
OUTDIR = ROOT / 'submission'
WORK = ROOT / 'work_tune'
SAMPLEDIR = WORK / 'samples'
WORK.mkdir(exist_ok=True)
SAMPLEDIR.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(1337)


def write_wav(path, data, sr=SR):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.asarray(data, dtype=np.float32)
    peak = np.max(np.abs(data)) if len(data) else 1.0
    if peak > 0.999:
        data = data / peak * 0.999
    pcm = np.int16(np.clip(data, -1, 1) * 32767)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def onepole_lowpass(x, cutoff_hz):
    x = np.asarray(x, dtype=np.float32)
    y = np.zeros_like(x)
    if cutoff_hz <= 0:
        return y
    a = 1.0 - math.exp(-2.0 * math.pi * cutoff_hz / SR)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def onepole_highpass(x, cutoff_hz):
    x = np.asarray(x, dtype=np.float32)
    lp = onepole_lowpass(x, cutoff_hz)
    return x - lp


def tanh_soft(x, drive=1.0):
    return np.tanh(np.asarray(x, dtype=np.float32) * drive)


def osc_phase(freq):
    return 2 * np.pi * np.cumsum(freq) / SR


def saw_from_phase(phase):
    return 2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0


def pulse_from_phase(phase, duty=0.32):
    return np.where(((phase / (2 * np.pi)) % 1.0) < duty, 1.0, -1.0)


def synth_kick():
    dur = 0.22
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 420.0 * np.exp(-t * 22.0) + 85.0
    phase = osc_phase(freq)
    body = 0.95 * np.sin(phase) + 0.22 * np.sin(2 * phase)
    env = np.exp(-t * 18.0)
    click = 0.22 * rng.uniform(-1, 1, n) * np.exp(-t * 140.0)
    sub = 0.12 * np.sin(0.5 * phase) * np.exp(-t * 14.0)
    y = tanh_soft(body * env + click + sub, 1.45)
    y *= np.linspace(1.0, 0.0, n) ** 0.35
    return y * 0.95


def synth_snare():
    dur = 0.20
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n).astype(np.float32)
    noise = onepole_highpass(noise, 1200)
    noise = onepole_lowpass(noise, 9000)
    noise_env = np.exp(-t * 20.0)
    tone_freq = 540.0 * np.exp(-t * 18.0) + 250.0
    phase = osc_phase(tone_freq)
    tone = (0.7 * np.sin(phase) + 0.2 * np.sin(2.03 * phase)) * np.exp(-t * 24.0)
    clap = 0.22 * np.sin(phase * 0.5 + 1.3) * np.exp(-t * 38.0)
    y = 0.78 * noise * noise_env + 0.45 * tone + clap
    y = tanh_soft(y, 1.25)
    return y * 0.75


def synth_hat(open_hat=False):
    dur = 0.24 if open_hat else 0.08
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n).astype(np.float32)
    noise = onepole_highpass(noise, 4500)
    metal = (
        np.sign(np.sin(2 * np.pi * 4120 * t)) +
        0.7 * np.sign(np.sin(2 * np.pi * 6190 * t + 0.31)) +
        0.5 * np.sign(np.sin(2 * np.pi * 7930 * t + 1.10))
    ) / 2.2
    env = np.exp(-t * (14.0 if open_hat else 55.0))
    y = 0.72 * noise + 0.28 * metal
    y = onepole_highpass(y, 5000)
    y *= env
    if open_hat:
        y *= (1.0 - 0.25 * np.exp(-t * 5.0))
    return tanh_soft(y, 1.1) * (0.48 if open_hat else 0.42)


def synth_bass():
    dur = 0.34
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = BASE_FREQ * (1.018 - 0.018 * (1 - np.exp(-t * 18.0)))
    phase = osc_phase(freq)
    saw = saw_from_phase(phase)
    pulse = pulse_from_phase(phase, 0.42)
    osc = 0.58 * saw + 0.34 * pulse + 0.18 * np.sin(2 * phase) + 0.09 * np.sin(3 * phase)
    osc += 0.04 * rng.uniform(-1, 1, n) * np.exp(-t * 80.0)
    env = np.exp(-t * 10.0)
    y = osc * env
    y = onepole_lowpass(y, 2300)
    y = tanh_soft(y, 1.45)
    y *= np.exp(-t * 1.4)
    return y * 0.72


def synth_lead():
    dur = 1.8
    n = int(SR * dur)
    t = np.arange(n) / SR
    vib = 0.0035 * np.sin(2 * np.pi * 5.4 * t)
    freq1 = BASE_FREQ * (1.0 + 0.010 * np.exp(-t * 14.0) + vib)
    freq2 = BASE_FREQ * (1.003 + 0.008 * np.exp(-t * 12.0) - 0.7 * vib)
    p1 = osc_phase(freq1)
    p2 = osc_phase(freq2)
    pulse = pulse_from_phase(p1, 0.34)
    saw = saw_from_phase(p2)
    osc = 0.52 * pulse + 0.40 * saw + 0.12 * np.sin(2 * p1) + 0.08 * np.sin(3 * p2)
    atk = 1.0 - np.exp(-t * 220.0)
    env = atk * np.exp(-t * 2.25)
    env += 0.06 * np.exp(-t * 0.45)
    y = osc * env + 0.03 * rng.uniform(-1, 1, n) * np.exp(-t * 90.0)
    y = onepole_lowpass(y, 5200)
    y = tanh_soft(y, 1.18)
    return y * 0.56


def synth_stab():
    dur = 1.28
    n = int(SR * dur)
    t = np.arange(n) / SR
    detunes = [0.996, 1.0, 1.004]
    osc = np.zeros(n, dtype=np.float32)
    for i, d in enumerate(detunes):
        ph = osc_phase(np.full(n, BASE_FREQ * d, dtype=np.float32))
        osc += (0.34 if i == 1 else 0.25) * saw_from_phase(ph)
        osc += 0.08 * np.sin(2 * ph + i * 0.7)
    env = (1.0 - np.exp(-t * 150.0)) * np.exp(-t * 2.8)
    y = osc * env
    y = onepole_lowpass(y, 3200)
    y = tanh_soft(y, 1.15)
    return y * 0.48




def finalize_sample(data, fade_in=0, fade_out=0, remove_dc=True, peak=None):
    x = np.asarray(data, dtype=np.float32).copy()
    if remove_dc:
        x = x - np.mean(x)
    if fade_in > 0:
        fade_in = min(int(fade_in), len(x))
        x[:fade_in] *= np.linspace(0.0, 1.0, fade_in, dtype=np.float32)
    if fade_out > 0:
        fade_out = min(int(fade_out), len(x))
        x[-fade_out:] *= np.linspace(1.0, 0.0, fade_out, dtype=np.float32)
    if peak is not None:
        p = float(np.max(np.abs(x))) if len(x) else 1.0
        if p > 1e-9:
            x *= float(peak) / p
    return x

def synth_bell():
    dur = 0.42
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = np.full(n, BASE_FREQ, dtype=np.float32)
    car = osc_phase(freq)
    mod = osc_phase(freq * 2.0)
    fm_index = 3.4 * np.exp(-t * 11.0)
    y = np.sin(car + fm_index * np.sin(mod)) * np.exp(-t * 7.8)
    y += 0.26 * np.sin(2 * car) * np.exp(-t * 12.0)
    y += 0.12 * np.sin(3 * car + 0.2) * np.exp(-t * 9.0)
    y = onepole_highpass(y, 500)
    return tanh_soft(y, 0.95) * 0.5


samples = {
    'kick.wav': finalize_sample(synth_kick(), fade_in=16, fade_out=96, remove_dc=True, peak=0.92),
    'snare.wav': finalize_sample(synth_snare(), fade_in=12, fade_out=96, remove_dc=True, peak=0.72),
    'hat.wav': finalize_sample(synth_hat(False), fade_in=8, fade_out=48, remove_dc=True, peak=0.23),
    'openhat.wav': finalize_sample(synth_hat(True), fade_in=8, fade_out=96, remove_dc=True, peak=0.21),
    'bass.wav': finalize_sample(synth_bass(), fade_in=64, fade_out=128, remove_dc=True, peak=0.34),
    'lead.wav': finalize_sample(synth_lead(), fade_in=96, fade_out=256, remove_dc=True, peak=0.48),
    'stab.wav': finalize_sample(synth_stab(), fade_in=96, fade_out=256, remove_dc=True, peak=0.31),
    'bell.wav': finalize_sample(synth_bell(), fade_in=48, fade_out=192, remove_dc=True, peak=0.42),
}

for name, data in samples.items():
    write_wav(SAMPLEDIR / name, data)

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

def note_name(midi):
    if midi is None:
        return None
    octave = midi // 12 - 1
    return f"{NOTE_NAMES[midi % 12]}{octave}"

cmds = []

def add_call(tool, **arguments):
    cmds.append({'name': tool, 'arguments': arguments})


def cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {'pattern': pattern, 'row': row, 'channel': channel}
    if note is not None:
        args['note'] = note_name(note) if isinstance(note, int) else note
    if instrument is not None:
        args['instrument'] = instrument
    if volume is not None:
        args['volume'] = volume
    if effect is not None:
        args['effect'] = effect
    if effect_param is not None:
        args['effect_param'] = effect_param
    add_call('pattern_set_cell', **args)

# Song/module setup
add_call('module_new', channels=8, name='Keyphase Prism')
add_call('song_set', name='Keyphase Prism', bpm=150, speed=6, length=8, loop_start=1, channels=8)
for p in range(8):
    add_call('pattern_set_length', pattern=p, rows=64)
    add_call('pattern_clear', pattern=p)
for pos, pat in enumerate(range(8)):
    add_call('order_set', position=pos, pattern=pat)

# Load instruments
inst_defs = [
    (1, 'Kick', 'kick.wav', 64, 128),
    (2, 'Snare', 'snare.wav', 64, 96),
    (3, 'Hat', 'hat.wav', 48, 224),
    (4, 'OpenHat', 'openhat.wav', 50, 216),
    (5, 'Bass Pluck', 'bass.wav', 64, 128),
    (6, 'Lead Pulse', 'lead.wav', 64, 48),
    (7, 'Warm Stab', 'stab.wav', 50, 208),
    (8, 'Bell Arp', 'bell.wav', 46, 240),
]
for inst, iname, fname, vol, pan in inst_defs:
    add_call('instrument_set', instrument=inst, name=iname)
    add_call('sample_load', path=str(SAMPLEDIR / fname), instrument=inst)
    meta = dict(instrument=inst, sample=0, name=iname, volume=vol, panning=pan, relative_note=12)
    add_call('sample_set', **meta)

# Chord helpers
CHORDS = {
    'Am': {'root': 45, 'intervals': [0, 3, 7]},
    'F':  {'root': 41, 'intervals': [0, 4, 7]},
    'C':  {'root': 48, 'intervals': [0, 4, 7]},
    'G':  {'root': 43, 'intervals': [0, 4, 7]},
    'Dm': {'root': 38, 'intervals': [0, 3, 7]},
    'E':  {'root': 40, 'intervals': [0, 4, 7]},
    'Em': {'root': 40, 'intervals': [0, 3, 7]},
}

def chord_tones(name):
    c = CHORDS[name]
    r = c['root']
    i1, i2 = c['intervals'][1], c['intervals'][2]
    return {
        'bass': r,
        'third_bass': r + i1,
        'fifth_bass': r + i2,
        'oct_bass': r + 12,
        'arp_root': r + 12,
        'arp_third': r + 12 + i1,
        'arp_fifth': r + 12 + i2,
        'arp_oct': r + 24,
        'stab_root': r + 24,
        'stab_third': r + 24 + i1,
        'stab_fifth': r + 24 + i2,
    }

# Channels
LEAD = 0
ARP = 1
BASS = 2
STAB = 3
KICK = 4
SNARE = 5
HAT = 6
ECHO = 7

# Instruments
I_KICK, I_SNARE, I_HAT, I_OHAT, I_BASS, I_LEAD, I_STAB, I_BELL = range(1, 9)


def add_kick(pattern, row, vol=48):
    cell(pattern, row, KICK, note=60, instrument=I_KICK, volume=vol)


def add_snare(pattern, row, vol=34):
    cell(pattern, row, SNARE, note=60, instrument=I_SNARE, volume=vol)


def add_hat(pattern, row, vol=16):
    cell(pattern, row, HAT, note=60, instrument=I_HAT, volume=vol)


def add_ohat(pattern, row, vol=20):
    cell(pattern, row, HAT, note=60, instrument=I_OHAT, volume=vol)


def drums_bar(pattern, bar, style):
    b = bar * 16
    if style == 'intro1':
        kicks, snares, oh = [0, 8], [], None
        hats = [8, 10, 12, 14]
    elif style == 'intro2':
        kicks, snares, oh = [0, 8], [12], 14
        hats = [4, 6, 8, 10, 12, 14]
    elif style == 'mainA':
        kicks, snares, oh = [0, 6, 8, 11, 14], [4, 12], 14
        hats = list(range(0, 16, 2))
    elif style == 'mainB':
        kicks, snares, oh = [0, 3, 8, 10, 13], [4, 12], 14
        hats = list(range(0, 16, 2))
    elif style == 'bridge':
        kicks, snares, oh = [0, 5, 8, 11, 14], [4, 12], 15
        hats = list(range(0, 16, 2)) + [15]
    elif style == 'break':
        kicks, snares, oh = [0, 8, 10], [12], 14
        hats = [0, 4, 8, 12, 14]
    elif style == 'climax':
        kicks, snares, oh = [0, 2, 6, 8, 11, 14], [4, 12], 15
        hats = list(range(0, 16, 2)) + [15]
    elif style == 'turnfill':
        kicks, snares, oh = [0, 6, 8, 10, 14], [4, 12, 14, 15], 15
        hats = list(range(0, 16, 2)) + [15]
    else:
        raise ValueError(style)

    for r in kicks:
        add_kick(pattern, b + r, vol=52 if r in (0, 8) else 44)
    for r in snares:
        add_snare(pattern, b + r, vol=38 if r in (4, 12) else 28)
    for r in hats:
        if r == oh:
            continue
        add_hat(pattern, b + r, vol=18 if r in (2, 6, 10, 14) else 14)
    if oh is not None:
        add_ohat(pattern, b + oh, vol=22)


def bass_bar(pattern, bar, chord_name, style='main'):
    b = bar * 16
    t = chord_tones(chord_name)
    r = t['bass']
    third = t['third_bass']
    fifth = t['fifth_bass']
    octv = t['oct_bass']
    if style == 'main':
        seq_rows = [0, 2, 4, 6, 8, 10, 12, 14]
        seq_notes = [r, octv, fifth, octv, r, octv, third + 12, fifth]
    elif style == 'alt':
        seq_rows = [0, 3, 4, 7, 8, 10, 12, 15]
        seq_notes = [r, fifth, octv, fifth, r, third + 12, fifth, octv]
    elif style == 'break':
        seq_rows = [0, 4, 6, 8, 12, 14]
        seq_notes = [r, fifth, octv, r, third + 12, fifth]
    elif style == 'intro':
        seq_rows = [0, 8, 12, 14]
        seq_notes = [r, octv, fifth, third + 12]
    else:
        raise ValueError(style)
    for rr, nn in zip(seq_rows, seq_notes):
        cell(pattern, b + rr, BASS, note=nn, instrument=I_BASS, volume=30 if rr not in (0, 8) else 34)


def arp_bar(pattern, bar, chord_name, style='main'):
    b = bar * 16
    t = chord_tones(chord_name)
    if style == 'main':
        seq = [t['arp_root'], t['arp_fifth'], t['arp_third'], t['arp_oct'], t['arp_fifth'], t['arp_third'], t['arp_fifth'], t['arp_oct']]
        rows = list(range(16))
        notes = [seq[i % 8] for i in range(16)]
        vols = [20 if i % 4 == 0 else 16 for i in range(16)]
    elif style == 'bridge':
        seq = [t['arp_root'], t['arp_third'], t['arp_fifth'], t['arp_oct'], t['arp_third'], t['arp_fifth'], t['arp_oct'], t['arp_fifth']]
        rows = list(range(16))
        notes = [seq[i % 8] for i in range(16)]
        vols = [20 if i % 4 == 0 else 17 for i in range(16)]
    elif style == 'sparse':
        seq = [t['arp_root'], t['arp_third'], t['arp_fifth'], t['arp_oct']]
        rows = list(range(0, 16, 2))
        notes = [seq[(i // 2) % 4] for i in rows]
        vols = [18 if idx % 2 == 0 else 14 for idx, _ in enumerate(rows)]
    elif style == 'climax':
        seq = [t['arp_root'], t['arp_fifth'], t['arp_oct'], t['arp_third'], t['arp_fifth'], t['arp_oct'], t['arp_third'], t['arp_fifth']]
        rows = list(range(16))
        notes = [seq[i % 8] for i in range(16)]
        vols = [22 if i % 4 == 0 else 18 for i in range(16)]
    else:
        raise ValueError(style)
    for rr, nn, vv in zip(rows, notes, vols):
        cell(pattern, b + rr, ARP, note=nn, instrument=I_BELL, volume=vv)


def stab_bar(pattern, bar, chord_name, level='full'):
    b = bar * 16
    t = chord_tones(chord_name)
    if level == 'none':
        return
    cell(pattern, b + 0, STAB, note=t['stab_root'], instrument=I_STAB, volume=20)
    cell(pattern, b + 8, STAB, note=t['stab_third'], instrument=I_STAB, volume=18)
    if level == 'full':
        cell(pattern, b + 12, STAB, note=t['stab_fifth'], instrument=I_STAB, volume=16)


def add_lead_events(pattern, events, inst=I_LEAD, channel=LEAD):
    for row, midi, vol in events:
        cell(pattern, row, channel, note=midi, instrument=inst, volume=vol)


def add_echo_from_events(pattern, events, delay=2, transpose=0, min_gap=3, vol=12):
    rows = {r for r, _, _ in events}
    for i, (row, midi, _v) in enumerate(events):
        next_row = events[i + 1][0] if i + 1 < len(events) else 64
        if next_row - row < min_gap:
            continue
        erow = row + delay
        if erow >= 64:
            continue
        if erow in rows:
            continue
        cell(pattern, erow, ECHO, note=midi + transpose, instrument=I_BELL, volume=vol)


def add_manual_bell(pattern, events):
    for row, midi, vol in events:
        cell(pattern, row, ECHO, note=midi, instrument=I_BELL, volume=vol)


# Pattern chord progressions per bar
prog = {
    0: ['Am', 'F', 'C', 'E'],
    1: ['Am', 'F', 'C', 'G'],
    2: ['Am', 'F', 'Dm', 'E'],
    3: ['Dm', 'F', 'C', 'E'],
    4: ['Am', 'F', 'C', 'G'],
    5: ['Am', 'G', 'F', 'E'],
    6: ['Am', 'F', 'Dm', 'E'],
    7: ['F', 'G', 'Em', 'E'],
}

# Fill accompaniment per pattern 0 (intro)
for bar, ch in enumerate(prog[0]):
    arp_bar(0, bar, ch, 'sparse' if bar == 0 else 'main')
    if bar >= 1:
        bass_bar(0, bar, ch, 'intro' if bar == 1 else 'main')
    if bar >= 2:
        stab_bar(0, bar, ch, 'light')
intro_drum_styles = ['intro1', 'intro2', 'mainA', 'bridge']
for bar, st in enumerate(intro_drum_styles):
    drums_bar(0, bar, st)

# Patterns 1-7 accompaniment
style_map = {
    1: [('mainA','main','main','full'), ('mainB','main','main','full'), ('mainA','alt','main','full'), ('mainB','alt','main','full')],
    2: [('mainA','main','main','full'), ('mainB','main','main','full'), ('bridge','alt','bridge','full'), ('bridge','alt','bridge','full')],
    3: [('bridge','alt','bridge','full'), ('bridge','main','bridge','full'), ('mainA','alt','bridge','full'), ('bridge','alt','bridge','full')],
    4: [('climax','main','climax','full'), ('mainB','main','climax','full'), ('mainA','alt','climax','full'), ('mainB','alt','climax','full')],
    5: [('break','break','sparse','light'), ('break','break','sparse','light'), ('break','break','sparse','light'), ('bridge','break','bridge','light')],
    6: [('climax','alt','climax','full'), ('climax','main','climax','full'), ('climax','alt','climax','full'), ('turnfill','alt','climax','full')],
    7: [('mainA','main','bridge','full'), ('mainB','alt','bridge','full'), ('mainA','alt','bridge','full'), ('turnfill','alt','climax','full')],
}
for pat in range(1, 8):
    for bar, chord in enumerate(prog[pat]):
        drum_style, bass_style, arp_style, stab_level = style_map[pat][bar]
        drums_bar(pat, bar, drum_style)
        bass_bar(pat, bar, chord, bass_style)
        arp_bar(pat, bar, chord, arp_style)
        stab_bar(pat, bar, chord, stab_level)

# Lead / melody material
lead_p0 = [
    (48, 76, 26), (52, 80, 28), (56, 83, 30), (60, 86, 28), (62, 83, 24)
]
lead_p1 = [
    (0, 76, 30), (4, 79, 30), (6, 81, 28), (8, 84, 32), (12, 83, 28), (14, 81, 26),
    (16, 81, 30), (20, 79, 28), (22, 77, 28), (24, 76, 30), (28, 72, 26), (30, 76, 26),
    (32, 79, 30), (36, 76, 28), (38, 74, 26), (40, 72, 28), (44, 76, 28), (46, 79, 28),
    (48, 83, 30), (50, 81, 28), (52, 79, 28), (56, 74, 26), (58, 76, 26), (60, 79, 28), (62, 83, 30)
]
lead_p2 = [
    (0, 84, 32), (2, 83, 28), (4, 81, 28), (8, 76, 28), (12, 79, 28), (14, 81, 28),
    (16, 81, 30), (18, 79, 28), (20, 77, 28), (24, 72, 26), (28, 76, 26), (30, 77, 26),
    (32, 81, 30), (36, 77, 28), (38, 76, 26), (40, 74, 28), (44, 77, 26), (46, 81, 28),
    (48, 80, 30), (50, 83, 30), (52, 86, 32), (56, 84, 30), (60, 83, 28), (62, 80, 28)
]
lead_p3 = [
    (0, 77, 30), (2, 81, 30), (4, 86, 32), (8, 84, 30), (12, 81, 28), (14, 77, 26),
    (16, 81, 30), (18, 84, 30), (20, 81, 28), (24, 77, 28), (28, 76, 26), (30, 72, 26),
    (32, 79, 30), (36, 76, 28), (38, 74, 26), (40, 72, 28), (44, 74, 26), (46, 76, 26),
    (48, 80, 30), (50, 83, 30), (52, 86, 32), (56, 83, 28), (58, 80, 26), (60, 77, 24), (62, 76, 24)
]
lead_p4 = [
    (0, 76, 30), (4, 79, 30), (6, 81, 28), (8, 84, 32), (12, 83, 28), (14, 81, 26),
    (16, 81, 30), (20, 79, 28), (22, 77, 28), (24, 76, 30), (28, 72, 26), (30, 76, 26),
    (32, 79, 30), (34, 81, 28), (36, 84, 32), (38, 79, 26), (40, 76, 28), (44, 79, 28), (46, 84, 30),
    (48, 83, 30), (50, 81, 28), (52, 79, 28), (56, 74, 26), (58, 76, 26), (60, 79, 28), (62, 83, 30)
]
lead_p5 = [
    (0, 72, 28), (4, 76, 28), (8, 81, 30), (12, 79, 28), (14, 76, 24),
    (16, 71, 26), (20, 74, 26), (24, 79, 28), (28, 77, 26), (30, 74, 24),
    (32, 69, 26), (36, 72, 26), (40, 77, 28), (44, 76, 26), (46, 72, 24),
    (48, 68, 26), (52, 71, 26), (56, 76, 28), (60, 74, 24), (62, 71, 22)
]
lead_p6 = [
    (0, 76, 30), (2, 79, 30), (4, 81, 30), (6, 84, 32), (8, 88, 34), (10, 84, 28), (12, 83, 28), (14, 81, 28),
    (16, 77, 30), (18, 81, 30), (20, 84, 32), (22, 81, 28), (24, 79, 28), (26, 77, 26), (28, 76, 26), (30, 72, 24),
    (32, 77, 30), (34, 81, 30), (36, 86, 32), (38, 81, 28), (40, 77, 28), (42, 76, 26), (44, 74, 26), (46, 77, 26),
    (48, 80, 30), (50, 83, 30), (52, 88, 34), (54, 86, 30), (56, 84, 30), (58, 83, 28), (60, 80, 26), (62, 76, 24)
]
lead_p7 = [
    (0, 81, 30), (2, 84, 30), (4, 81, 28), (8, 79, 28), (12, 77, 26), (14, 81, 28),
    (16, 83, 30), (18, 86, 32), (20, 83, 28), (24, 81, 28), (28, 79, 26), (30, 83, 28),
    (32, 83, 30), (34, 79, 28), (36, 76, 26), (40, 78, 26), (44, 79, 28), (46, 83, 30),
    (48, 80, 30), (50, 83, 30), (52, 86, 32), (54, 83, 28), (56, 80, 28), (58, 76, 26), (60, 74, 24), (62, 71, 22)
]

lead_patterns = {
    0: lead_p0, 1: lead_p1, 2: lead_p2, 3: lead_p3,
    4: lead_p4, 5: lead_p5, 6: lead_p6, 7: lead_p7,
}
for pat, events in lead_patterns.items():
    add_lead_events(pat, events)

# Echo / extra bell layers
add_echo_from_events(4, lead_p4, delay=2, transpose=0, min_gap=4, vol=12)
add_echo_from_events(6, lead_p6, delay=2, transpose=-12, min_gap=3, vol=12)
add_echo_from_events(7, lead_p7, delay=2, transpose=0, min_gap=4, vol=12)
# Breakdown extra sparse bell replies
add_manual_bell(5, [(2, 84, 14), (10, 83, 14), (18, 79, 14), (26, 77, 14), (34, 76, 14), (42, 72, 14), (50, 71, 14), (58, 68, 12)])
# Intro bell sparkles near handoff
add_manual_bell(0, [(58, 80, 12), (60, 83, 14), (62, 86, 14)])

# Save commands and summary
with open(WORK / 'commands.json', 'w') as f:
    json.dump(cmds, f)

summary = {
    'song': 'Keyphase Prism',
    'bpm': 150,
    'speed': 6,
    'order': list(range(8)),
    'loop_start': 1,
    'patterns': {str(k): v for k, v in prog.items()},
    'lead_counts': {str(k): len(v) for k, v in lead_patterns.items()},
    'command_count': len(cmds),
}
with open(WORK / 'summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

print('Wrote', WORK / 'commands.json')
print('Commands', len(cmds))
