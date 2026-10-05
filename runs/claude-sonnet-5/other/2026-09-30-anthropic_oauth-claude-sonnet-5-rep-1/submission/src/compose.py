import json

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def nn(letter, octave):
    idx = NAMES.index(letter)
    absn = idx + 12*octave
    return absn

def name_of(absn):
    octave = absn // 12
    idx = absn % 12
    n = NAMES[idx]
    if '#' in n:
        return f"{n}{octave}"
    return f"{n}-{octave}"

# instrument ids
KICK, SNARE, HAT_C, HAT_O, CLAP, BASS, LEAD, PAD, LEAD2 = 1,2,3,4,5,6,7,8,9

# chord defs: (root letter, quality) ; quality 'min' third=3, 'maj' third=4
CHORDS = {
    'Am': ('A', 'min'),
    'F':  ('F', 'maj'),
    'C':  ('C', 'maj'),
    'G':  ('G', 'maj'),
}

def triad(letter, quality, root_octave):
    root = nn(letter, root_octave)
    third = root + (3 if quality == 'min' else 4)
    fifth = root + 7
    return root, third, fifth

def bass_root(letter, octave=3):
    return nn(letter, octave)

def lead_cycle(letter, quality, octave=5):
    r, t, f = triad(letter, quality, octave)
    return [r, t, f, r+12]  # root,3rd,5th,octave

cells = []  # list of dict cmds

PAN = {0: 128, 1: 128, 2: 160, 3: 128, 4: 96, 5: 80, 6: 128, 7: 176}

def setc(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    d = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        d["note"] = note if isinstance(note, str) else name_of(note)
    if instrument is not None:
        d["instrument"] = instrument
    if volume is not None:
        d["volume"] = volume
    if effect is None and note is not None and channel in PAN:
        effect = 8
        effect_param = PAN[channel]
    if effect is not None:
        d["effect"] = effect
    if effect_param is not None:
        d["effect_param"] = effect_param
    cells.append(d)

ROWS_PER_BEAT = 4
ROWS_PER_BAR = 16

def bar_rows(bar_index):
    return bar_index * ROWS_PER_BAR

# ---------------- PATTERN 0: INTRO (4 bars, 64 rows) ----------------
PAT_INTRO = 0
progression_intro = ['Am', 'F', 'C', 'G']

for bar, chord_name in enumerate(progression_intro):
    base = bar_rows(bar)
    letter, quality = CHORDS[chord_name]
    root, third, fifth = triad(letter, quality, 4)
    # pad enters bar0, sustained whole-bar chord on all bars
    vol_pad = 38 if bar == 0 else 44
    setc(PAT_INTRO, base, 5, note=root, instrument=PAD, volume=vol_pad)
    setc(PAT_INTRO, base, 6, note=third, instrument=PAD, volume=vol_pad)
    setc(PAT_INTRO, base, 7, note=fifth, instrument=PAD, volume=vol_pad)
    # bass enters bar1
    if bar >= 1:
        broot = bass_root(letter, 3)
        for r in range(base, base+ROWS_PER_BAR, 2):
            setc(PAT_INTRO, r, 3, note=broot, instrument=BASS, volume=46)
    # hats enter bar2
    if bar >= 2:
        for r in range(base, base+ROWS_PER_BAR):
            setc(PAT_INTRO, r, 2, note='C-5', instrument=HAT_C, volume=22 if r % ROWS_PER_BEAT else 30)
    # kick enters bar2 (sparse: beats 1 and 3), full four-on-floor bar3
    if bar == 2:
        for r in (base, base+8):
            setc(PAT_INTRO, r, 0, note='C-5', instrument=KICK, volume=56)
    if bar == 3:
        for r in range(base, base+ROWS_PER_BAR, ROWS_PER_BEAT):
            setc(PAT_INTRO, r, 0, note='C-5', instrument=KICK, volume=60)
        # snare on beats 2 & 4
        setc(PAT_INTRO, base+4, 1, note='C-5', instrument=SNARE, volume=52)
        setc(PAT_INTRO, base+12, 1, note='C-5', instrument=SNARE, volume=52)
        # pickup fill lead last 4 rows leading to main
        cyc = lead_cycle(letter, quality, 5)
        for i, r in enumerate(range(base+12, base+16)):
            setc(PAT_INTRO, r, 4, note=cyc[i % len(cyc)], instrument=LEAD, volume=40)

# ---------------- shared groove builder for MAIN patterns ----------------

def build_main(pat_index, progression, variant='A'):
    for bar, chord_name in enumerate(progression):
        base = bar_rows(bar)
        letter, quality = CHORDS[chord_name]
        root, third, fifth = triad(letter, quality, 4)
        # pad sustained chord, one hit per bar
        setc(pat_index, base, 5, note=root, instrument=PAD, volume=42)
        setc(pat_index, base, 6, note=third, instrument=PAD, volume=42)
        if variant == 'A':
            setc(pat_index, base, 7, note=fifth, instrument=PAD, volume=42)
        else:
            # Main B: replace voice3 with a counter melody (Lead2) for interest
            counter = [fifth, root+12, third+12, fifth]
            for i, r in enumerate(range(base, base+ROWS_PER_BAR, 4)):
                setc(pat_index, r, 7, note=counter[i % len(counter)], instrument=LEAD2, volume=34)

        # four-on-floor kick
        for r in range(base, base+ROWS_PER_BAR, ROWS_PER_BEAT):
            setc(pat_index, r, 0, note='C-5', instrument=KICK, volume=62)
        # backbeat snare/clap on beats 2 & 4
        snare_inst = SNARE if (variant == 'A' or bar % 2 == 0) else CLAP
        setc(pat_index, base+4, 1, note='C-5', instrument=snare_inst, volume=54)
        setc(pat_index, base+12, 1, note='C-5', instrument=snare_inst, volume=54)
        # hats: 16th closed, accent on beat, open hat pickup before next bar
        for r in range(base, base+ROWS_PER_BAR):
            if r == base+15:
                continue
            v = 30 if r % ROWS_PER_BEAT == 0 else 20
            setc(pat_index, r, 2, note='C-5', instrument=HAT_C, volume=v)
        setc(pat_index, base+15, 2, note='C-5', instrument=HAT_O, volume=26)

        # pumping 8th-note bass
        broot = bass_root(letter, 3)
        for r in range(base, base+ROWS_PER_BAR, 2):
            setc(pat_index, r, 3, note=broot, instrument=BASS, volume=48)

        # lead arpeggio 16th notes
        cyc = lead_cycle(letter, quality, 5)
        if variant == 'A':
            order_idx = [0, 1, 2, 3] * 4
        else:
            # variant B: different contour + occasional octave jump for lift
            order_idx = [0, 2, 1, 3, 0, 2, 3, 1, 0, 1, 2, 3, 0, 2, 3, 3]
        for i, r in enumerate(range(base, base+ROWS_PER_BAR)):
            note_v = cyc[order_idx[i] % len(cyc)]
            if variant == 'B' and i in (14, 15):
                note_v += 12  # lift at bar end
            accent = 44 if r % ROWS_PER_BEAT == 0 else 34
            setc(pat_index, r, 4, note=note_v, instrument=LEAD, volume=accent)

PAT_MAIN_A = 1
PAT_MAIN_B = 2
progression_main = ['Am', 'F', 'C', 'G']
build_main(PAT_MAIN_A, progression_main, variant='A')
build_main(PAT_MAIN_B, progression_main, variant='B')

# ---------------- PATTERN 3: OUTRO (2 bars, 32 rows) ----------------
PAT_OUTRO = 3
progression_outro = ['C', 'G']
for bar, chord_name in enumerate(progression_outro):
    base = bar_rows(bar)
    letter, quality = CHORDS[chord_name]
    root, third, fifth = triad(letter, quality, 4)
    setc(PAT_OUTRO, base, 5, note=root, instrument=PAD, volume=40)
    setc(PAT_OUTRO, base, 6, note=third, instrument=PAD, volume=40)
    setc(PAT_OUTRO, base, 7, note=fifth, instrument=PAD, volume=40)

    broot = bass_root(letter, 3)
    for r in range(base, base+ROWS_PER_BAR, 2):
        setc(PAT_OUTRO, r, 3, note=broot, instrument=BASS, volume=44)

    if bar == 0:
        # still full drums or last hurrah
        for r in range(base, base+ROWS_PER_BAR, ROWS_PER_BEAT):
            setc(PAT_OUTRO, r, 0, note='C-5', instrument=KICK, volume=58)
        setc(PAT_OUTRO, base+4, 1, note='C-5', instrument=SNARE, volume=50)
        setc(PAT_OUTRO, base+12, 1, note='C-5', instrument=SNARE, volume=50)
        for r in range(base, base+ROWS_PER_BAR, 2):
            setc(PAT_OUTRO, r, 2, note='C-5', instrument=HAT_C, volume=22)
        cyc = lead_cycle(letter, quality, 5)
        for i, r in enumerate(range(base, base+ROWS_PER_BAR)):
            setc(PAT_OUTRO, r, 4, note=cyc[i % len(cyc)], instrument=LEAD, volume=36)
    else:
        # bar1: strip back, just kick on 1&3, open hat swell ending, no lead
        setc(PAT_OUTRO, base, 0, note='C-5', instrument=KICK, volume=56)
        setc(PAT_OUTRO, base+8, 0, note='C-5', instrument=KICK, volume=56)
        setc(PAT_OUTRO, base+12, 1, note='C-5', instrument=SNARE, volume=46)
        # swelling open hihat leading back into loop
        setc(PAT_OUTRO, base+12, 2, note='C-4', instrument=HAT_O, volume=36)

with open('/workspace/work/batch_patterns.json', 'w') as f:
    json.dump([{"name": "pattern_set_cell", "arguments": c} for c in cells], f)

print("total cells:", len(cells))
