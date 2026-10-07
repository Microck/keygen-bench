"""Small helpers for note numbers / chords. All notes are plain MIDI
numbers (60 = C4, standard scientific pitch, A4=69=440Hz). XM pattern
note = midi - 11 (every instrument is calibrated so that XM note 49
reproduces 261.625565 Hz = C4 exactly, and integer semitone steps are
exact -- see synth.py)."""

# pitch classes ordered from C, matching standard octave numbering
C, Db, D, Eb, E, F, Gb, G, Ab, A, Bb, B = range(12)
PITCH_CLASS_NAMES = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']

def midi(pitch_class, octave):
    """octave follows scientific pitch: C4=60, A4=69, C5=72."""
    return (octave + 1) * 12 + pitch_class

def xm_note(m):
    n = m - 11
    if n < 1 or n > 96:
        raise ValueError(f"midi {m} -> xm note {n} out of range")
    return n

MINOR = [0, 2, 3, 5, 7, 8, 10]   # natural minor scale steps from tonic
MAJOR = [0, 2, 4, 5, 7, 9, 11]

def scale_notes(tonic_pc, steps, lo_oct=0, hi_oct=8):
    out = []
    for o in range(lo_oct, hi_oct + 1):
        base = midi(tonic_pc, o)
        for s in steps:
            out.append(base + s)
    return sorted(out)

A_MINOR_SCALE = scale_notes(A, MINOR)

def nearest_scale_degree_shift(m, shift, scale=A_MINOR_SCALE):
    """Move `shift` diatonic scale-steps from midi note m (can be
    negative), snapping m to the nearest scale member first."""
    idx = min(range(len(scale)), key=lambda i: abs(scale[i] - m))
    idx2 = max(0, min(len(scale) - 1, idx + shift))
    return scale[idx2]

# chord intervals (triad) by quality
TRIAD = {'min': [0, 3, 7], 'maj': [0, 4, 7]}

CHORDS = {
    'Am': (A, 'min'),
    'F':  (F, 'maj'),
    'C':  (C, 'maj'),
    'G':  (G, 'maj'),
    'Em': (E, 'min'),
    'Dm': (D, 'min'),
}

def chord_tones(name, octave=4):
    pc, qual = CHORDS[name]
    root = midi(pc, octave)
    return [root + iv for iv in TRIAD[qual]]
