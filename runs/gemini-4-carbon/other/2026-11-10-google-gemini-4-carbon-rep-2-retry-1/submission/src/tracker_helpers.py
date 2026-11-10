"""
Idiomatic FastTracker II composition helpers for 'CYBERNETIC FUGUE // KEYGEN'
Channel map (12 channels):
  Ch 0: Kick (Inst 1)
  Ch 1: Snare / Clap / Rim / Toms (Inst 2, 3, 4, 8)
  Ch 2: Closed Hat / Open Hat / Crash (Inst 5, 6, 7)
  Ch 3: Bass - RazorFM / AcidSync (Inst 9, 10)
  Ch 4: Hero Lead 1 - HeroPWM (Inst 11)
  Ch 5: Harmony / Counter Lead 2 - SyncShred (Inst 12)
  Ch 6: 58Hz Chip Arpeggiator - Pulse25 (Inst 13)
  Ch 7: Crystal DX Bell / Harpsichord Pluck (Inst 14)
  Ch 8..10: Poly Pad / Brass Chord Voices 1..3 (Inst 15, 16)
  Ch 11: Poly Pad / Brass Voice 4 & CyberRiser FX (Inst 15, 16, 17)
"""
from xm_builder import Pattern, parse_note

SEMI_TO_STR = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]

# Instrument IDs
I_KICK  = 1
I_SNARE = 2
I_CLAP  = 3
I_RIM   = 4
I_HATC  = 5
I_HATO  = 6
I_CRASH = 7
I_TOM   = 8
I_BASS  = 9
I_ACID  = 10
I_LEAD1 = 11
I_LEAD2 = 12
I_CHIP  = 13
I_BELL  = 14
I_PAD   = 15
I_STAB  = 16
I_RISER = 17

# Channel IDs
CH_KICK  = 0
CH_SNARE = 1
CH_HAT   = 2
CH_BASS  = 3
CH_LEAD1 = 4
CH_LEAD2 = 5
CH_CHIP  = 6
CH_BELL  = 7
CH_PAD1  = 8
CH_PAD2  = 9
CH_PAD3  = 10
CH_PAD4  = 11


def n_str(note_int: int) -> str:
    v = note_int - 1
    return f"{SEMI_TO_STR[v % 12]}{v // 12}"


def tr(note: str, semis: int) -> str:
    return n_str(parse_note(note) + semis)


# Chord dictionary: returns (bass_root_oct2, chip_root_oct4, arp_xy_hex, [4-voice pad/stab notes])
CHORDS = {
    "F#m":     ("F#2", "F#4", 0x37, ["F#3", "A-3", "C#4", "F#4"]),
    "F#m9":    ("F#2", "F#4", 0x37, ["F#3", "A-3", "C#4", "G#4"]),
    "F#m7":    ("F#2", "F#4", 0x3A, ["F#3", "A-3", "C#4", "E-4"]),
    "F#m/E":   ("E-2", "F#4", 0x3A, ["E-3", "A-3", "C#4", "F#4"]),
    "F#7":     ("F#2", "F#4", 0x4A, ["F#3", "A#3", "C#4", "E-4"]),
    "Dmaj7":   ("D-2", "D-4", 0x4B, ["D-3", "F#3", "A-3", "C#4"]),
    "D":       ("D-2", "D-4", 0x47, ["D-3", "F#3", "A-3", "D-4"]),
    "E":       ("E-2", "E-4", 0x47, ["E-3", "G#3", "B-3", "E-4"]),
    "E/D":     ("D-2", "E-4", 0x47, ["D-3", "G#3", "B-3", "E-4"]),
    "E/G#":    ("G#1", "E-4", 0x47, ["G#3", "B-3", "E-4", "G#4"]),
    "E7":      ("E-2", "E-4", 0x4A, ["E-3", "G#3", "B-3", "D-4"]),
    "E7sus4":  ("E-2", "E-4", 0x5A, ["E-3", "A-3", "B-3", "D-4"]),
    "A":       ("A-1", "A-4", 0x47, ["A-3", "C#4", "E-4", "A-4"]),
    "Amaj7":   ("A-1", "A-4", 0x4B, ["A-3", "C#4", "E-4", "G#4"]),
    "Bm7":     ("B-1", "B-4", 0x3A, ["B-3", "D-4", "F#4", "A-4"]),
    "C#m7":    ("C#2", "C#4", 0x3A, ["C#3", "E-3", "G#3", "B-3"]),
    "G#m7b5":  ("G#1", "G#4", 0x36, ["G#3", "B-3", "D-4", "F#4"]),
    "G#dim7":  ("G#1", "G#4", 0x36, ["G#3", "B-3", "D-4", "F-4"]),
    "C#7sus4": ("C#2", "C#4", 0x5A, ["C#3", "F#3", "G#3", "B-3"]),
    "C#7":     ("C#2", "C#4", 0x4A, ["C#3", "F-3", "G#3", "B-3"]),
    "C#7b9":   ("C#2", "F-4", 0x36, ["F-3", "G#3", "B-3", "D-4"]),
    "C#7/F":   ("F-2", "C#4", 0x4A, ["F-3", "G#3", "B-3", "C#4"]),
}


def write_lead_phrase(pat: Pattern, ch: int, inst: int, events: list, base_vol: int = 58, pan: int = None):
    """
    Render an expressive tracker lead phrase!
    Each event in `events`:
      (row, dur, note, style)  OR  (row, dur, note)
    Styles:
      'norm'   : crisp attack + automatic delayed vibrato (453/464) on sustained notes (dur >= 4)
      'slide'  : legato 3xx tone portamento from previous note (speed auto-scaled by interval!)
      'grace'  : quick grace-note ornament (ED2 delay or fast slide from -2/+2 semitones)
      'stacc'  : tight staccato gate (EC3 / note-off halfway)
      'accent' : +6 vol punch + strong vibrato
      'soft'   : -8 vol gentle phrasing
    """
    if pan is not None:
        pat.set(0, ch, eff=8, param=pan)

    prev_note_int = None
    for idx, ev in enumerate(events):
        row, dur, note = ev[0], ev[1], ev[2]
        style = ev[3] if len(ev) > 3 else "norm"
        if row >= pat.rows:
            continue

        if note in ("off", "==="):
            pat.set(row, ch, note="off")
            continue

        n_int = parse_note(note)
        vol = base_vol
        if style == "accent":
            vol = min(64, base_vol + 6)
        elif style == "soft":
            vol = max(16, base_vol - 9)

        next_start = events[idx + 1][0] if idx + 1 < len(events) else min(pat.rows, row + dur)
        actual_span = min(dur, next_start - row)

        if style == "slide" and prev_note_int is not None:
            diff = abs(n_int - prev_note_int)
            # In FT2 linear freqs, 1 semitone = 16 units per tick; over 5 active ticks/row, param = diff * 4 reaches target in ~1 row!
            porta_spd = max(0x14, min(0x60, diff * 7))
            pat.set(row, ch, note=note, inst=0, vol=vol, eff=3, param=porta_spd)
            if actual_span >= 2 and row + 1 < pat.rows and row + 1 < next_start:
                pat.set(row + 1, ch, eff=3, param=0x00)
        elif style == "grace":
            pat.set(row, ch, note=note, inst=inst, vol=vol, eff=14, param=0xD2)
            if pan is not None and row + 1 < pat.rows and row + 1 < next_start:
                pat.set(row + 1, ch, eff=8, param=pan)
        elif style == "stacc":
            pat.set(row, ch, note=note, inst=inst, vol=vol, eff=14, param=0xC3)
        else:
            if pan is not None:
                pat.set(row, ch, note=note, inst=inst, vol=vol, eff=8, param=pan)
            else:
                pat.set(row, ch, note=note, inst=inst, vol=vol)

        # Expressive delayed vibrato & gentle tail taper on sustained notes!
        if actual_span >= 3 and style != "stacc":
            vib_start = row + (2 if style == "slide" else 1)
            for r in range(vib_start, min(pat.rows, row + actual_span)):
                if r >= next_start:
                    break
                # Last row of long note gets gentle volume taper before next articulation
                if r == row + actual_span - 1 and actual_span >= 5:
                    pat.set(r, ch, vol=("raw", 0x62), eff=4, param=0x64)
                else:
                    pat.set(r, ch, eff=4, param=0x63 if r == vib_start else 0x00)

        # Clean note-off if there's an explicit rest gap before next event
        end_r = row + dur
        if style != "stacc" and end_r < next_start and end_r < pat.rows:
            pat.set(end_r, ch, note="off")

        prev_note_int = n_int


def fill_drums_driving(pat: Pattern, bar_start: int = 0, bars: int = 4, clap: bool = False, crash_bar0: bool = False, energy: int = 0):
    """
    Classic punchy demoscene/keygen drum groove over `bars` bars starting at `bar_start * 16`.
    Includes syncopated ghost kicks, crisp offbeat open hi-hats (choked by closed hats!),
    ghost snares, and musical micro-variations.
    """
    for b in range(bars):
        r0 = (bar_start + b) * 16
        if r0 >= pat.rows:
            break
        # Kick pattern: driving 4-on-the-floor + syncopated keygen bounce on step 10/14
        kicks = [(0, 64), (4, 60), (8, 63), (12, 60)]
        if b % 2 == 1:
            kicks.extend([(6, 46), (14, 52)])
        elif energy >= 1:
            kicks.append((10, 48))
        for step, kv in kicks:
            pat.set(r0 + step, CH_KICK, "C-4", I_KICK, min(64, kv + energy * 2))

        # Snare / Clap on 4 and 12 + tracker ghost hits
        for step in (4, 12):
            if clap and step == 12:
                pat.set(r0 + step, CH_SNARE, "C-4", I_CLAP, 62)
            else:
                pat.set(r0 + step, CH_SNARE, "C-4", I_SNARE, 63)
        # Subtle ghost snare/rim for groove
        if b % 2 == 0:
            pat.set(r0 + 7, CH_SNARE, "C-4", I_RIM, 32)
            pat.set(r0 + 15, CH_SNARE, "C-4", I_SNARE, 34)
        else:
            pat.set(r0 + 9, CH_SNARE, "C-4", I_RIM, 34)
            if b < bars - 1:
                pat.set(r0 + 15, CH_SNARE, "C-4", I_SNARE, 40)

        # Hi-hats on Ch 2 (Closed chokes Open naturally!)
        for step in range(16):
            if b == 0 and step == 0 and crash_bar0:
                pat.set(r0 + step, CH_HAT, "C-4", I_CRASH, 58)
            elif step in (2, 6, 10, 14):
                pat.set(r0 + step, CH_HAT, "C-4", I_HATO, 50 + energy * 3)
            else:
                v_hat = 42 if step % 4 == 0 else (28 if step % 2 == 1 else 34)
                pat.set(r0 + step, CH_HAT, "C-4", I_HATC, min(60, v_hat + energy * 3))


def fill_drum_turnaround(pat: Pattern, start_row: int = 48, intense: bool = True):
    """
    Signature stereo keygen snare + pitched electro-tom fill over 1 bar (16 rows, e.g. 48..63)
    or half-bar (8 rows, e.g. 56..63)!
    """
    if intense:
        # Full 1-bar explosive build & stereo tom cascade (rows start_row .. start_row+15)
        r = start_row
        # Kick build
        for step, v in [(0, 62), (2, 54), (4, 62), (6, 56), (8, 63), (10, 63), (12, 64), (14, 64)]:
            pat.set(r + step, CH_KICK, "C-4", I_KICK, v)
        # Snare roll + stereo panned pitched electro-toms!
        pat.set(r + 0, CH_SNARE, "C-4", I_SNARE, 50, 8, 128)
        pat.set(r + 2, CH_SNARE, "C-4", I_SNARE, 54)
        pat.set(r + 4, CH_SNARE, "F#4", I_TOM,   58, 8, 64)   # Left high tom
        pat.set(r + 6, CH_SNARE, "E-4", I_TOM,   58, 8, 96)
        pat.set(r + 7, CH_SNARE, "E-4", I_TOM,   52, 8, 112)
        pat.set(r + 8, CH_SNARE, "D-4", I_TOM,   60, 8, 128)  # Center mid tom
        pat.set(r + 10, CH_SNARE, "C#4", I_TOM,  60, 8, 160)
        pat.set(r + 11, CH_SNARE, "B-3", I_TOM,  58, 8, 184)  # Right low tom
        # Blazing 32nd-note snare roll (E93 = retrigger every 3 ticks!) on beats 4 & 4-and!
        pat.set(r + 12, CH_SNARE, "C-4", I_SNARE, 56, 8, 128)
        pat.set(r + 13, CH_SNARE, "C-4", I_SNARE, 58, 14, 0x93)
        pat.set(r + 14, CH_SNARE, "C#4", I_SNARE, 61, 14, 0x93)
        pat.set(r + 15, CH_SNARE, "D-4", I_SNARE, 64, 14, 0x92)  # Tight 3-hit buzz pickup into Row 0!
        # Open hat accents on quarter/eighths
        for step in range(0, 16, 2):
            pat.set(r + step, CH_HAT, "C-4", I_HATO if step % 4 == 2 else I_HATC, 52)
    else:
        # Crisp 8-row (2-beat) turnaround fill at start_row (e.g. 56..63)
        r = start_row
        pat.set(r + 0, CH_KICK, "C-4", I_KICK, 62)
        pat.set(r + 4, CH_KICK, "C-4", I_KICK, 64)
        pat.set(r + 0, CH_SNARE, "C-4", I_SNARE, 56, 8, 128)
        pat.set(r + 2, CH_SNARE, "E-4", I_TOM,   58, 8, 76)
        pat.set(r + 3, CH_SNARE, "D-4", I_TOM,   56, 8, 112)
        pat.set(r + 4, CH_SNARE, "C#4", I_TOM,  60, 8, 152)
        pat.set(r + 6, CH_SNARE, "C-4", I_SNARE, 60, 8, 128)
        pat.set(r + 7, CH_SNARE, "C#4", I_SNARE, 63, 14, 0x93)


def fill_bass_gallop(pat: Pattern, start_row: int, length: int, chord_name: str, inst: int = I_BASS, vol: int = 60, walk_end: str = None):
    """
    Driving classic keygen octave-jumping bassline!
    Root on downbeats, tight +12 octave bounce on offbeats, subtle fifth/passing tone at bar end.
    """
    root = CHORDS[chord_name][0]
    root_hi = tr(root, 12)
    if "/" in chord_name:
        fifth = tr(root, 8 if chord_name == "E/G#" else 9)
    elif "b5" in chord_name or "dim" in chord_name:
        fifth = tr(root, 6)
    else:
        fifth = tr(root, 7)
    for step in range(length):
        r = start_row + step
        if r >= pat.rows:
            break
        if walk_end is not None and step >= length - 2:
            if step == length - 2:
                pat.set(r, CH_BASS, walk_end, inst, vol)
            else:
                pat.set(r, CH_BASS, walk_end, 0, vol - 8, 14, 0xC4)
            continue

        m = step % 4
        if m == 0:
            pat.set(r, CH_BASS, root, inst, vol)
        elif m == 1:
            # Tight gate before offbeat octave!
            pat.set(r, CH_BASS, None, None, ("raw", 0x63))
        elif m == 2:
            n_pick = fifth if (step == length - 2 and length >= 8) else root_hi
            pat.set(r, CH_BASS, n_pick, inst, vol - 4, 14, 0xC4)  # Crisp gated offbeat octave
        elif m == 3:
            if step % 8 == 7:
                pat.set(r, CH_BASS, root, inst, vol - 8, 14, 0xC3)


def fill_chip_arp_bar(pat: Pattern, start_row: int, length: int, chord_name: str, mode: str = "0xy", vol: int = 44):
    """
    Ch 6 Pulse25Arp:
      mode == '0xy'   : Authentic 58Hz rhythmic 0xy chip-chord shimmer with syncopated tracker gates!
      mode == 'sweep' : Blazing 2-octave 16th-note broken chord wave!
    """
    _, chip_root, xy, v_notes = CHORDS[chord_name]
    if mode == "0xy":
        # Syncopated Dubmood-style rhythmic chip-chord pattern
        for step in range(length):
            r = start_row + step
            if r >= pat.rows:
                break
            pos4 = step % 4
            if pos4 == 0:
                pat.set(r, CH_CHIP, chip_root, I_CHIP, vol, 0, xy)
            elif pos4 == 1:
                pat.set(r, CH_CHIP, None, None, ("raw", 0x62), 0, xy)
            elif pos4 == 2:
                pat.set(r, CH_CHIP, tr(chip_root, 12), I_CHIP, vol - 4, 0, xy)
            else:
                # Crisp gate on 4th 16th so chords bounce!
                pat.set(r, CH_CHIP, "off")
    else:
        # 2-octave 16th-note sparkling up-down broken chord
        seq = [
            v_notes[0], v_notes[1], v_notes[2], v_notes[3],
            tr(v_notes[0], 12), tr(v_notes[1], 12), tr(v_notes[2], 12), tr(v_notes[3], 12),
            tr(v_notes[2], 12), tr(v_notes[1], 12), tr(v_notes[0], 12), v_notes[3],
            v_notes[2], v_notes[1], v_notes[2], v_notes[3],
        ]
        for step in range(length):
            r = start_row + step
            if r >= pat.rows:
                break
            v_s = vol if step % 2 == 0 else vol - 8
            pat.set(r, CH_CHIP, tr(seq[step % 16], 12), I_CHIP, v_s)


def place_pad_chord(pat: Pattern, start_row: int, length: int, chord_name: str, vol: int = 30, include_ch11: bool = True):
    """Warm stereo 3- or 4-voice LushEnsmb pad on Ch 8..11 with balanced stereo spread."""
    v_notes = CHORDS[chord_name][3]
    pans = [16, 240, 68, 188]
    n_voices = 4 if include_ch11 else 3
    for i in range(n_voices):
        ch = CH_PAD1 + i
        pat.set(start_row, ch, v_notes[i], I_PAD, vol, 8, pans[i])
        # Gentle release fade on last 2 rows of chord
        if length >= 4 and start_row + length - 2 < pat.rows:
            pat.set(start_row + length - 2, ch, vol=("raw", 0x62))
        if start_row + length - 1 < pat.rows:
            pat.set(start_row + length - 1, ch, vol=("raw", 0x63))


def place_brass_stabs(pat: Pattern, start_row: int, chord_name: str, steps=(0, 6, 12), vol: int = 36, include_ch11: bool = True):
    """Punchy rhythmic 3- or 4-voice PolyBrass chord stabs with 1-tick stereo Haas micro-strum!"""
    v_notes = CHORDS[chord_name][3]
    pans = [16, 240, 68, 188]
    pan_nibbles = [0xC1, 0xCE, 0xC4, 0xCB]
    n_voices = 4 if include_ch11 else 3
    for st in steps:
        r = start_row + st
        if r >= pat.rows:
            continue
        v_hit = vol if st == 0 else vol - 4
        for i in range(n_voices):
            ch = CH_PAD1 + i
            if i < 2:
                pat.set(r, ch, tr(v_notes[i], 12), I_STAB, v_hit, 8, pans[i])
            else:
                # 1-tick (17ms) stereo strum on upper chord voices!
                pat.set(r, ch, tr(v_notes[i], 12), I_STAB, ("raw", pan_nibbles[i]), 14, 0xD1)


def write_stereo_delay_echo(
    pat: Pattern,
    echo_ch: int,
    inst: int,
    events: list,
    delay_rows: int = 3,
    echo_vol: int = 21,
    pan: int = 204,
    max_row: int = 64,
):
    """
    Classic FastTracker II dotted-16th (+3 rows) stereo ping-pong echo channel!
    Renders soft right-panned echoes of a solo left-panned lead phrase, cutting cleanly at max_row.
    """
    for idx, ev in enumerate(events):
        r_orig, dur, note = ev[0], ev[1], ev[2]
        r = r_orig + delay_rows
        if r >= max_row:
            continue
        if note in ("off", "==="):
            pat.set(r, echo_ch, note="off")
            continue
        pat.set(r, echo_ch, note=note, inst=inst, vol=echo_vol, eff=8, param=pan)
        next_r = (events[idx + 1][0] + delay_rows) if (idx + 1 < len(events)) else (r + dur)
        end_r = min(max_row - 1, r + dur)
        if dur >= 3 and r + 1 < min(next_r, max_row):
            pat.set(r + 1, echo_ch, eff=4, param=0x53)
        if end_r < next_r and end_r < max_row:
            pat.set(end_r, echo_ch, note="off")
    if max_row <= pat.rows:
        pat.set(max_row - 1, echo_ch, note="off")


def fill_bass_styled(
    pat: Pattern,
    start_row: int,
    length: int,
    chord_name: str,
    style: str = "gallop",
    inst: int = I_BASS,
    vol: int = 60,
    walk_end: str = None,
):
    """
    Multi-style demoscene bassline generator:
      - 'gallop'        : Classic tight keygen octave bounce + fifth pickup
      - 'chorus_drive'  : Propulsive 16th arcade/synthwave melodic pattern (root-root-oct-5th-root-oct-7th-5th)
      - 'baroque_pedal' : Driving neo-classical 16th pedal point for Shred Duel
      - 'climax_funk'   : Deep sub-drop Beat 1 (E-1 / F#1) + syncopated funk/keygen octave slap!
    """
    root = CHORDS[chord_name][0]
    root_hi = tr(root, 12)
    if "/" in chord_name:
        fifth = tr(root, 8 if chord_name == "E/G#" else 9)
    elif "b5" in chord_name or "dim" in chord_name:
        fifth = tr(root, 6)
    else:
        fifth = tr(root, 7)
    is_maj7 = "maj7" in chord_name
    seventh = tr(root, 11 if is_maj7 else 10)
    deep_sub = tr(root, -12) if parse_note(root) >= parse_note("E-2") else root

    for step in range(length):
        r = start_row + step
        if r >= pat.rows:
            break
        if walk_end is not None and step >= length - 2:
            if step == length - 2:
                pat.set(r, CH_BASS, walk_end, inst, vol)
            else:
                pat.set(r, CH_BASS, tr(walk_end, 12), inst, vol - 6, 14, 0xC4)
            continue

        if style == "chorus_drive":
            # Propulsive 8-step melodic arcade groove!
            cell8 = [
                (root, vol, None),
                (root, vol - 10, 0xC3),
                (root_hi, vol - 3, 0xC4),
                (fifth, vol - 7, 0xC3),
                (root, vol - 2, None),
                (root_hi, vol - 4, 0xC4),
                (seventh if "7" in chord_name else root_hi, vol - 5, 0xC4),
                (fifth, vol - 6, 0xC3),
            ]
            nt, v_s, cut = cell8[step % 8]
            if cut is not None:
                pat.set(r, CH_BASS, nt, inst, v_s, 14, cut)
            else:
                pat.set(r, CH_BASS, nt, inst, v_s)

        elif style == "baroque_pedal":
            # Relentless neo-classical 16th-note pedal with octave accents on offbeats!
            m = step % 4
            if m == 0:
                pat.set(r, CH_BASS, deep_sub if step == 0 else root, inst, vol)
            elif m == 2:
                pat.set(r, CH_BASS, root_hi, inst, vol - 4, 14, 0xC4)
            else:
                pat.set(r, CH_BASS, root, inst, vol - 9, 14, 0xC3)

        elif style == "climax_funk":
            # Deep F#1/E-1 sub impact on Beat 1 + syncopated slap octaves & fifths!
            m8 = step % 8
            if step == 0:
                pat.set(r, CH_BASS, deep_sub, inst, min(64, vol + 2))
            elif m8 == 2:
                pat.set(r, CH_BASS, root_hi, inst, vol - 3, 14, 0xC4)
            elif m8 == 3:
                pat.set(r, CH_BASS, fifth, inst, vol - 8, 14, 0xC3)
            elif m8 == 4:
                pat.set(r, CH_BASS, root, inst, vol)
            elif m8 == 6:
                pat.set(r, CH_BASS, root_hi, inst, vol - 2, 14, 0xC4)
            elif m8 == 7:
                pat.set(r, CH_BASS, seventh if "7" in chord_name else root, inst, vol - 6, 14, 0xC3)

        else:
            # Classic gallop (with deep_sub punch on bar downbeat!)
            m = step % 4
            if m == 0:
                pat.set(r, CH_BASS, deep_sub if step == 0 else root, inst, vol)
            elif m == 1:
                pat.set(r, CH_BASS, None, None, ("raw", 0x63))
            elif m == 2:
                n_pick = fifth if (step == length - 2 and length >= 8) else root_hi
                pat.set(r, CH_BASS, n_pick, inst, vol - 4, 14, 0xC4)
            elif m == 3 and step % 8 == 7:
                pat.set(r, CH_BASS, root, inst, vol - 8, 14, 0xC3)
