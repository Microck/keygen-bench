"""Small music-theory + note-name helpers shared by the composition script."""
import math

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NAME_TO_IDX = {n: i for i, n in enumerate(NAMES)}
# also accept flat spellings
FLATS = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def nn(name):
    """'C-4' / 'A#3' / 'Eb5' -> FT2 note number (1..96), C-0 == 1."""
    if isinstance(name, int):
        return name
    s = name.strip()
    if s[1] in ("#",):
        letter = s[0:2]
        rest = s[2:]
    elif s[1] == "b":
        letter = FLATS[s[0:2]]
        rest = s[2:]
    else:
        letter = s[0:1]
        rest = s[1:]
    if rest.startswith("-"):
        rest = rest[1:]
        octave = -int(rest) if rest else 0
    octave = int(rest)
    idx = NAME_TO_IDX[letter]
    return octave * 12 + idx + 1


def name_of(num):
    num = int(round(num))
    octave = (num - 1) // 12
    idx = (num - 1) % 12
    return f"{NAMES[idx]}-{octave}" if len(NAMES[idx]) == 1 else f"{NAMES[idx]}{octave}"


def transpose(name, semitones):
    return name_of(nn(name) + semitones)


def calibrate(data_rate, ref_rate=8363.0, detune_cents=0.0):
    """Return (relative_note, finetune) so that FT2 note C-4 (49) plays this
    sample back at exactly data_rate samples/sec (times an optional cents
    detune), matching the pitch baked into the waveform at generation time."""
    d_eff = data_rate * (2 ** (detune_cents / 1200.0))
    semi = 12 * math.log2(d_eff / ref_rate)
    rel = round(semi)
    fine = round((semi - rel) * 128)
    if fine > 127:
        fine -= 128
        rel += 1
    if fine < -128:
        fine += 128
        rel -= 1
    rel = max(-96, min(95, rel))
    fine = max(-128, min(127, fine))
    return rel, fine


# ---- chord tables (triads), using sharp spelling only, octave picked by caller
MINOR = [0, 3, 7]
MAJOR = [0, 4, 7]


def chord(root_name, quality):
    root = nn(root_name)
    ivs = MINOR if quality == "m" else MAJOR
    return [name_of(root + i) for i in ivs]


if __name__ == "__main__":
    for s in ["C-4", "A-3", "A#3", "Eb5", "G-2"]:
        print(s, nn(s), name_of(nn(s)))
    print(chord("A-3", "m"))
    print(chord("F-3", "M"))
    print(calibrate(44100))
    print(calibrate(11025))


# ---- diatonic (A natural minor == C major, all-white-key) helper machinery
_DIATONIC_PITCH_CLASSES = {0, 2, 4, 5, 7, 9, 11}  # C D E F G A B


def _build_diatonic_table():
    table = []
    for num in range(1, 200):
        if (num - 1) % 12 in _DIATONIC_PITCH_CLASSES:
            table.append(num)
    return table


_DIATONIC = _build_diatonic_table()
_DIATONIC_INDEX = {num: i for i, num in enumerate(_DIATONIC)}


def degree_index(note_name):
    num = nn(note_name)
    if num not in _DIATONIC_INDEX:
        raise ValueError(f"{note_name} (#{num}) is not in the diatonic (white-key) scale")
    return _DIATONIC_INDEX[num]


def from_degree(idx):
    idx = max(0, min(len(_DIATONIC) - 1, idx))
    return name_of(_DIATONIC[idx])


def degree_step(note_name, steps):
    """Move `note_name` by `steps` diatonic scale steps (2 steps ~ a third)."""
    return from_degree(degree_index(note_name) + steps)


if __name__ == "__main__":
    print("diatonic check:")
    print(degree_step("A-4", 2), "expect C-5")
    print(degree_step("F-4", 2), "expect A-4")
    print(degree_step("A-3", 7), "expect A-4 (octave)")
    print(degree_step("C-4", -2), "expect A-3")
