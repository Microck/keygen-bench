"""
Harmony, voice-leading, drum grooves, driving basslines, and stereo arpeggiators
for 'COBALT KEYRING' (148 BPM, Speed 3, 8 rows/beat = 32nd-note grid, 32 rows/bar, 128 rows/pattern).

14-Channel Map:
  Ch 0: Kick / Electro Toms (Center 128)
  Ch 1: Snare / Clap-Rim (Center 126)
  Ch 2: Closed/Open Hi-Hats & Crash (Right-ish 154)
  Ch 3: Aux Perc / Clap Layer / Snare Roll / Tom Fill (Left-ish 102)
  Ch 4: Razor Bass / Deep Sub Bass (Center 128)
  Ch 5: Hero Lead (PWM / Supersaw) (Slight Left 116)
  Ch 6: Stereo Tap Delay of Hero Lead (Right 156)
  Ch 7: Harmony Lead / Counter-Lead / Bell Obligato (Slight Right 142)
  Ch 8: SID 60Hz Chip Arp (0xy shimmer) (Wide Left 74)
  Ch 9: Baroque FM Harpsichord / Pluck Cascade (Wide Right 182)
  Ch 10: Velvet Poly Pad / Stab Voice 1 (Pan 96)
  Ch 11: Velvet Poly Pad / Stab Voice 2 (Pan 128)
  Ch 12: Velvet Poly Pad / Stab Voice 3 (Pan 160)
  Ch 13: Crystal Bell Chime / High Sparkle Accent (Pan 134)
"""
from xm_builder import (
    OFF, VOL, VSLIDE_DOWN, ARP3, TONE_PORTA, VIBRATO, PANNING,
    VOL_SLIDE, RETRIG, NOTE_CUT, NOTE_DELAY, SET_SPEED, SET_BPM,
    note_num, transpose
)

# Instrument IDs (1-indexed)
I_KICK   = 1
I_SNARE  = 2
I_CLAP   = 3
I_CHAT   = 4
I_OHAT   = 5
I_CRASH  = 6
I_TOM    = 7
I_BASS   = 8
I_SUB    = 9
I_PWM    = 10
I_SAW    = 11
I_HARM   = 12
I_SID    = 13
I_HARPSI = 14
I_BELL   = 15
I_PAD    = 16

CHANNEL_PANS = [128, 126, 154, 102, 128, 116, 156, 142, 74, 182, 96, 128, 160, 134]

# Chord dictionary: (bass_root, pad_voicing_3notes, arp_base_note, arp_semitones_(s1,s2), harpsi_4notes)
# Carefully voice-led around C#4..C#5 so pads sound smooth and lush without mud!
CHORDS = {
    'F#m':    ('F#2', ('F#3', 'A-3', 'C#4'), 'F#4', (3, 7),  ['F#4', 'A-4', 'C#5', 'F#5']),
    'F#m/A':  ('A-2', ('F#3', 'C#4', 'F#4'), 'A-4', (4, 9),  ['A-4', 'C#5', 'F#5', 'A-5']),
    'F#m/C#': ('C#2', ('F#3', 'A-3', 'C#4'), 'C#4', (5, 9),  ['C#4', 'F#4', 'A-4', 'C#5']),
    'F#m7':   ('F#2', ('F#3', 'A-3', 'E-4'), 'F#4', (3, 10), ['F#4', 'A-4', 'C#5', 'E-5']),
    'D':      ('D-2', ('F#3', 'A-3', 'D-4'), 'D-4', (4, 7),  ['D-4', 'F#4', 'A-4', 'D-5']),
    'Dmaj7':  ('D-2', ('F#3', 'A-3', 'C#4'), 'D-4', (4, 11), ['D-4', 'F#4', 'A-4', 'C#5']),
    'Dm6':    ('D-2', ('F-3', 'A-3', 'B-3'), 'D-4', (3, 9),  ['D-4', 'F-4', 'A-4', 'B-4']),
    'E':      ('E-2', ('G#3', 'B-3', 'E-4'), 'E-4', (4, 7),  ['E-4', 'G#4', 'B-4', 'E-5']),
    'E/G#':   ('G#2', ('E-3', 'B-3', 'E-4'), 'G#4', (3, 8),  ['G#4', 'B-4', 'E-5', 'G#5']),
    'E/D':    ('D-2', ('G#3', 'B-3', 'E-4'), 'E-4', (4, 10), ['E-4', 'G#4', 'B-4', 'D-5']),
    'E7':     ('E-2', ('G#3', 'B-3', 'D-4'), 'E-4', (4, 10), ['E-4', 'G#4', 'B-4', 'D-5']),
    'E7sus4': ('E-2', ('A-3', 'B-3', 'D-4'), 'E-4', (5, 10), ['E-4', 'A-4', 'B-4', 'D-5']),
    'A':      ('A-2', ('E-3', 'A-3', 'C#4'), 'A-4', (4, 7),  ['A-4', 'C#5', 'E-5', 'A-5']),
    'Amaj7':  ('A-2', ('E-3', 'G#3', 'C#4'), 'A-4', (4, 11), ['A-4', 'C#5', 'E-5', 'G#5']),
    'Bm7':    ('B-1', ('F#3', 'A-3', 'D-4'), 'B-4', (3, 7),  ['B-4', 'D-5', 'F#5', 'A-5']),
    'B7/D#':  ('D#2', ('F#3', 'A-3', 'B-3'), 'B-4', (4, 10), ['F#4', 'A-4', 'B-4', 'D#5']),
    'C#m7':   ('C#2', ('E-3', 'G#3', 'B-3'), 'C#4', (3, 7),  ['C#4', 'E-4', 'G#4', 'B-4']),
    'C#7':    ('C#2', ('E#3', 'G#3', 'B-3'), 'C#4', (4, 10), ['C#4', 'E#4', 'G#4', 'B-4']),
    'C#7/E#': ('E#2', ('G#3', 'B-3', 'C#4'), 'E#4', (3, 8),  ['E#4', 'G#4', 'B-4', 'C#5']),
    'C#7sus4':('C#2', ('F#3', 'G#3', 'B-3'), 'C#4', (5, 10), ['C#4', 'F#4', 'G#4', 'B-4']),
    'F#7':    ('F#2', ('E-3', 'A#3', 'C#4'), 'F#4', (4, 10), ['F#4', 'A#4', 'C#5', 'E-5']),
    'F#7/A#': ('A#2', ('E-3', 'F#3', 'C#4'), 'F#4', (4, 10), ['A#4', 'C#5', 'E-5', 'F#5']),
    'G#m7b5': ('G#2', ('F#3', 'B-3', 'D-4'), 'G#4', (3, 6),  ['G#4', 'B-4', 'D-5', 'F#5']),
    'G#dim7': ('G#2', ('F-3', 'B-3', 'D-4'), 'G#4', (3, 6),  ['G#4', 'B-4', 'D-5', 'F-5']),
    'D#dim7': ('D#2', ('F#3', 'A-3', 'C-4'), 'D#4', (3, 6),  ['D#4', 'F#4', 'A-4', 'C-5']),
    'Fdim7':  ('F-2', ('G#3', 'B-3', 'D-4'), 'F-4', (3, 6),  ['F-4', 'G#4', 'B-4', 'D-5']),
}


def init_row0_channel_pans(pat, set_tempo=True):
    """Ensure explicit channel panning & tempo on Pattern 0 Row 0 for deterministic looping."""
    for ch, pan in enumerate(CHANNEL_PANS):
        pat.set(0, ch, eff=PANNING(pan))
    if set_tempo:
        # Put speed=3 on Ch 12 and BPM=148 on Ch 13 at row 0 (and restore their pans on row 1)
        pat.set(0, 12, eff=SET_SPEED(3))
        pat.set(0, 13, eff=SET_BPM(148))
        pat.set(1, 12, eff=PANNING(CHANNEL_PANS[12]))
        pat.set(1, 13, eff=PANNING(CHANNEL_PANS[13]))


def write_chord_pads(pat, segments, style='sustain', vol_base=40):
    """
    segments: list of (start_row, end_row, chord_name)
    Writes 3-voice chords on Ch 10, 11, 12.
    styles: 'sustain', 'pulsing' (trance/keygen rhythmic gate), 'stabs' (syncopated brassy hits)
    """
    for s_row, e_row, cname in segments:
        _, voices, _, _, _ = CHORDS[cname]
        if style == 'sustain':
            for idx, vnote in enumerate(voices):
                ch = 10 + idx
                pat.set(s_row, ch, note=vnote, inst=I_PAD, vol=VOL(vol_base), eff=PANNING((24, 128, 232)[idx]))
                if e_row - 2 > s_row:
                    pat.set(e_row - 2, ch, vol=VSLIDE_DOWN(4))
                if e_row - 1 > s_row:
                    pat.set(e_row - 1, ch, note=OFF)
        elif style == 'pulsing':
            # Syncopated keygen chord pulses at 8th-note / dotted-8th positions (0, 6, 12, 16, 22, 28)
            length = e_row - s_row
            offsets = [o for o in [0, 6, 12, 16, 22, 26] if o + 3 <= length]
            for off in offsets:
                r = s_row + off
                v = vol_base + (4 if off in (0, 16) else -3)
                for idx, vnote in enumerate(voices):
                    ch = 10 + idx
                    pat.set(r, ch, note=vnote, inst=I_PAD, vol=VOL(v), eff=PANNING((24, 128, 232)[idx]))
                    if r + 3 < e_row:
                        pat.set(r + 3, ch, note=OFF)
        elif style == 'stabs':
            # Heroic fanfare hits on beat 1 (0), 'and' of 2 (12), beat 4 (24)
            length = e_row - s_row
            hits = [(0, 4, vol_base + 5), (12, 3, vol_base), (24, 4, vol_base + 2)]
            for off, dur, v in hits:
                if off + dur <= length:
                    for idx, vnote in enumerate(voices):
                        ch = 10 + idx
                        pat.set(s_row + off, ch, note=vnote, inst=I_PAD, vol=VOL(v), eff=PANNING((24, 128, 232)[idx]))
                        pat.set(s_row + off + dur, ch, note=OFF)


def write_sid_arp(pat, segments, mode='shimmer', vol_base=42):
    """
    Writes authentic 60Hz `0xy` SID pulse arpeggios on Ch 8.
    Remember: in XM, `0xy` must be present on every row where arpeggiation continues!
    """
    for s_row, e_row, cname in segments:
        _, _, base_note, (s1, s2), _ = CHORDS[cname]
        arp_eff = ARP3(s1, s2)
        if mode == 'shimmer':
            # Retrigger every 8 rows (quarter beat) with octave jump on off-beats (row+4)!
            for r in range(s_row, e_row):
                local = r - s_row
                if local % 8 == 0:
                    pat.set(r, 8, note=base_note, inst=I_SID, vol=VOL(vol_base), eff=arp_eff)
                elif local % 8 == 4:
                    pat.set(r, 8, note=transpose(base_note, 12), inst=I_SID, vol=VOL(vol_base - 5), eff=arp_eff)
                elif r == e_row - 1:
                    pat.set(r, 8, note=OFF)
                else:
                    pat.set(r, 8, eff=arp_eff)
        elif mode == 'gallop':
            # Rhythmic gated 16th-note 60Hz chord pulses (2 rows on, 2 rows gated down)
            for r in range(s_row, e_row):
                local = r - s_row
                step16 = (local // 2) % 4
                if local % 2 == 0:
                    if step16 in (0, 2, 3):
                        nt = transpose(base_note, 12 if step16 == 2 else 0)
                        vv = vol_base if step16 == 0 else vol_base - 6
                        pat.set(r, 8, note=nt, inst=I_SID, vol=VOL(vv), eff=arp_eff)
                    else:
                        pat.set(r, 8, vol=VOL(14), eff=arp_eff)
                else:
                    if r == e_row - 1:
                        pat.set(r, 8, note=OFF)
                    else:
                        pat.set(r, 8, eff=arp_eff)
        elif mode == 'sparkle_high':
            # Chorus high-register crystalline 60Hz shimmer
            hi_note = transpose(base_note, 12)
            for r in range(s_row, e_row):
                local = r - s_row
                if local % 4 == 0:
                    v = vol_base if (local % 8 == 0) else (vol_base - 7)
                    pat.set(r, 8, note=hi_note, inst=I_SID, vol=VOL(v), eff=arp_eff)
                elif r == e_row - 1:
                    pat.set(r, 8, note=OFF)
                else:
                    pat.set(r, 8, eff=arp_eff)


def write_harpsi_arp(pat, segments, pattern_type='baroque16', vol_base=46):
    """
    Writes plucked Baroque FM Harpsichord cascades on Ch 9 (every 2 rows = 16th notes,
    with occasional 32nd-note ornaments!).
    """
    orders = {
        'baroque16': [0, 1, 2, 3, 2, 1, 3, 2, 0, 2, 1, 3, 2, 3, 1, 2],
        'rising16':  [0, 1, 2, 3, 1, 2, 3, 0, 0, 1, 2, 3, 2, 3, 1, 3],
        'alberti':   [0, 2, 1, 2, 0, 3, 1, 3, 0, 2, 1, 2, 0, 3, 2, 1],
    }
    seq = orders.get(pattern_type, orders['baroque16'])
    for s_row, e_row, cname in segments:
        _, _, _, _, hnotes = CHORDS[cname]
        step = 0
        for r in range(s_row, e_row, 2):
            idx = seq[step % len(seq)]
            nt = hnotes[idx]
            # Subtle accent on beats (every 8 rows)
            accent = 5 if ((r - s_row) % 8 == 0) else (-3 if (step % 2 == 1) else 0)
            pat.set(r, 9, note=nt, inst=I_HARPSI, vol=VOL(vol_base + accent))
            step += 1


def write_bassline(pat, segments, style='octave_drive', walk_overrides=None):
    """
    Writes tight, monophonic basslines on Ch 4 (never overlapping low notes!).
    walk_overrides: optional dict {row: (note, inst, vol)} for custom passing tones / fills.
    """
    walk_overrides = walk_overrides or {}
    for s_row, e_row, cname in segments:
        root, _, _, _, _ = CHORDS[cname]
        oct_up = transpose(root, 12)
        fifth = transpose(root, 7)

        if style == 'octave_drive':
            # Classic demoscene 16th-note octave gallop: Root - Oct - Root - Oct with syncopated fifths
            for r in range(s_row, e_row, 2):
                if r in walk_overrides:
                    continue
                step = ((r - s_row) // 2) % 8
                if step == 0:
                    pat.set(r, 4, note=root, inst=I_BASS, vol=VOL(62))
                elif step in (2, 4, 6):
                    pat.set(r, 4, note=root, inst=I_BASS, vol=VOL(56))
                elif step in (1, 3, 5):
                    pat.set(r, 4, note=oct_up, inst=I_BASS, vol=VOL(52))
                elif step == 7:
                    pat.set(r, 4, note=fifth, inst=I_BASS, vol=VOL(54))
                # Slight crisp gate on offbeat octaves so bass bounces!
                if step in (1, 3, 5) and r + 1 < e_row:
                    pat.set(r + 1, 4, vol=VOL(32))

        elif style == 'chorus_melodic':
            # Bouncy, singing anthem bassline with 8th/16th propulsion
            for r in range(s_row, e_row, 2):
                if r in walk_overrides:
                    continue
                step = ((r - s_row) // 2) % 8
                if step == 0:
                    pat.set(r, 4, note=root, inst=I_BASS, vol=VOL(63))
                elif step == 2:
                    pat.set(r, 4, note=oct_up, inst=I_BASS, vol=VOL(55))
                elif step == 3:
                    pat.set(r, 4, note=root, inst=I_BASS, vol=VOL(53))
                elif step == 4:
                    pat.set(r, 4, note=fifth, inst=I_BASS, vol=VOL(57))
                elif step == 6:
                    pat.set(r, 4, note=oct_up, inst=I_BASS, vol=VOL(56))
                elif step == 7:
                    pat.set(r, 4, note=fifth, inst=I_BASS, vol=VOL(52))

        elif style == 'intro_pulse':
            # Strong 8th-note pulse building to 16ths
            for r in range(s_row, e_row, 4):
                if r in walk_overrides:
                    continue
                beat_pos = ((r - s_row) // 4) % 2
                nt = root if beat_pos == 0 else oct_up
                vv = 60 if beat_pos == 0 else 50
                pat.set(r, 4, note=nt, inst=I_BASS, vol=VOL(vv))
                if r + 3 < e_row:
                    pat.set(r + 3, 4, vol=VOL(24))

        elif style == 'sub_lament':
            # Deep Sub Bass for Baroque Breakdown (warm, sustained pedal with gentle breathing)
            pat.set(s_row, 4, note=root, inst=I_SUB, vol=VOL(58))
            if s_row + 16 < e_row:
                pat.set(s_row + 16, 4, note=transpose(root, 12), inst=I_SUB, vol=VOL(46))
            if s_row + 20 < e_row:
                pat.set(s_row + 20, 4, note=root, inst=I_SUB, vol=VOL(54))
            if e_row - 1 > s_row:
                pat.set(e_row - 1, 4, note=OFF)

    for r, (nt, ins, vv) in walk_overrides.items():
        pat.set(r, 4, note=nt, inst=ins, vol=VOL(vv))


def write_drums(pat, groove='drive', crash_rows=(0,), fill_end='standard'):
    """
    128-row (4-bar) drum programmer across Ch 0 (Kick/Tom), Ch 1 (Snare/Rim),
    Ch 2 (Hats/Crash), Ch 3 (Clap/Roll/Tom fills).
    1 bar = 32 rows; Beats 1, 2, 3, 4 = rows 0, 8, 16, 24.
    """
    stop_bar4 = 112 if fill_end else 128

    if groove == 'fanfare_intro':
        for bar in range(4):
            b = bar * 32
            if b >= stop_bar4:
                break
            # Heroic syncopated kicks matching fanfare stabs: 0, 12, 16, 28
            for ko, kv in [(0, 64), (12, 56), (16, 62), (28, 54)]:
                pat.set(b + ko, 0, note='C-4', inst=I_KICK, vol=VOL(kv))
            # Crisp snare + clap on beats 2 & 4 (rows 8, 24) starting bar 2 (or rim on bar 1)
            for so in [8, 24]:
                if bar == 0:
                    pat.set(b + so, 1, note='C-4', inst=I_CLAP, vol=VOL(52))
                else:
                    pat.set(b + so, 1, note='C-4', inst=I_SNARE, vol=VOL(60))
                    pat.set(b + so, 3, note='C-4', inst=I_CLAP, vol=VOL(44))
            # Crisp 8th/16th hi-hats
            for h in range(0, 32, 2):
                if (b + h) in crash_rows:
                    continue
                if h % 8 == 4:
                    pat.set(b + h, 2, note='C-4', inst=I_OHAT, vol=VOL(46))
                else:
                    pat.set(b + h, 2, note='C-4', inst=I_CHAT, vol=VOL(42 if h % 4 == 0 else 30))

    elif groove in ('drive', 'chorus', 'solo'):
        for bar in range(4):
            b = bar * 32
            for r_local in range(0, 32, 2):
                r = b + r_local
                if r >= stop_bar4:
                    break
                # Kick pattern: punchy beats 1 & 3 + classic demoscene syncopation on 14, 20/28!
                if groove == 'drive':
                    kick_map = {0: 64, 6: 48, 16: 63, 22: 52, 28: 54}
                elif groove == 'chorus':
                    # Driving four-on-the-floor + offbeat bounce!
                    kick_map = {0: 64, 6: 50, 14: 54, 16: 64, 22: 50, 28: 54, 30: 46}
                else:  # solo: high-velocity double-kick energy!
                    kick_map = {0: 64, 6: 54, 12: 52, 16: 64, 20: 52, 28: 58}

                if r_local in kick_map:
                    pat.set(r, 0, note='C-4', inst=I_KICK, vol=VOL(kick_map[r_local]))

                # Snare on Beat 2 (8) & Beat 4 (24) + ghost snare on 14 or 30
                if r_local in (8, 24):
                    pat.set(r, 1, note='C-4', inst=I_SNARE, vol=VOL(63))
                    if groove in ('chorus', 'solo') or r_local == 24:
                        pat.set(r, 3, note='C-4', inst=I_CLAP, vol=VOL(48 if groove == 'chorus' else 42))
                elif r_local == 30 and bar % 2 == 1 and groove != 'chorus':
                    pat.set(r, 1, note='C-4', inst=I_SNARE, vol=VOL(34))

                # Hi-hats: Closed on beats & 16ths, sizzling Open Hat on the '+' of every beat (4, 12, 20, 28)!
                if r not in crash_rows:
                    if r_local in (4, 12, 20, 28):
                        pat.set(r, 2, note='C-4', inst=I_OHAT, vol=VOL(50 if groove == 'chorus' else 46))
                    else:
                        v_hat = 44 if (r_local % 8 == 0) else 32
                        pat.set(r, 2, note='C-4', inst=I_CHAT, vol=VOL(v_hat))

    elif groove == 'breakdown':
        # Light, intimate Baroque Silicon groove: soft rim clicks & delicate 16th hats
        for bar in range(4):
            b = bar * 32
            if bar >= 2:
                pat.set(b + 0, 0, note='C-4', inst=I_KICK, vol=VOL(46))
                pat.set(b + 16, 0, note='C-4', inst=I_KICK, vol=VOL(44))
            for so in [8, 24]:
                pat.set(b + so, 1, note='C-4', inst=I_CLAP, vol=VOL(38))
            for h in range(0, 32, 4):
                pat.set(b + h, 2, note='C-4', inst=I_CHAT, vol=VOL(30 if h % 8 == 0 else 22))

    elif groove == 'build_riser':
        # Accelerating 4-bar EDM/demoscene snare & kick build (Bars 45-48 -> Solo!)
        # Bar 1: 8th kicks, Bar 2: 8th kicks + snares, Bar 3: 16th snares crescendo, Bar 4: 32nd-note blitz!
        for r in range(0, 64, 4):
            pat.set(r, 0, note='C-4', inst=I_KICK, vol=VOL(50 + (r // 8)))
            if r >= 32:
                pat.set(r, 1, note='C-4', inst=I_SNARE, vol=VOL(40 + (r - 32) // 2))
            pat.set(r, 2, note='C-4', inst=I_CHAT, vol=VOL(36))
        for r in range(64, 96, 2):
            v = 42 + (r - 64) // 2
            pat.set(r, 0, note='C-4', inst=I_KICK, vol=VOL(min(62, v)))
            pat.set(r, 1, note='C-4', inst=I_SNARE, vol=VOL(min(60, v)))
            if r % 4 == 0:
                pat.set(r, 2, note='C-4', inst=I_OHAT, vol=VOL(46))
        # Bar 4 (96..127): exhilarating 32nd-note crescendo roll + descending electro toms!
        for r in range(96, 124):
            if r in (112, 116, 120):
                continue
            v = 36 + int((r - 96) * 0.95)
            pat.set(r, 1, note='C-4', inst=I_SNARE, vol=VOL(min(62, v)))
        for idx, (tr, tnote) in enumerate([(112, 'A-3'), (116, 'F#3'), (120, 'E-3'), (124, 'C#3')]):
            pat.set(tr, 0, note=tnote, inst=I_TOM, vol=VOL(62))
            pat.set(tr, 3, note='C-4', inst=I_CLAP, vol=VOL(54))
        fill_end = None  # already wrote custom build!

    # Section crash hits
    for cr in crash_rows:
        if 0 <= cr < 128:
            pat.set(cr, 2, note='C-4', inst=I_CRASH, vol=VOL(54))

    # End-of-pattern drum fills (rows 112..127 = Beats 3 & 4 of Bar 4)
    if fill_end == 'standard':
        pat.set(112, 0, note='C-4', inst=I_KICK, vol=VOL(64))
        pat.set(114, 1, note='C-4', inst=I_SNARE, vol=VOL(46))
        pat.set(116, 1, note='C-4', inst=I_SNARE, vol=VOL(52))
        pat.set(118, 0, note='F#3', inst=I_TOM,   vol=VOL(58))
        pat.set(120, 1, note='C-4', inst=I_SNARE, vol=VOL(62))
        pat.set(120, 3, note='C-4', inst=I_CLAP,  vol=VOL(50))
        pat.set(122, 0, note='E-3', inst=I_TOM,   vol=VOL(58))
        pat.set(124, 0, note='C#3', inst=I_TOM,   vol=VOL(62))
        pat.set(126, 1, note='C-4', inst=I_SNARE, vol=VOL(64))
    elif fill_end == 'snare_blitz':
        pat.set(112, 0, note='C-4', inst=I_KICK,  vol=VOL(64))
        for r in range(114, 124, 2):
            pat.set(r, 1, note='C-4', inst=I_SNARE, vol=VOL(44 + (r - 114) * 2))
        # Crisp 32nd-note snare + tom burst on 124..127!
        pat.set(124, 1, note='C-4', inst=I_SNARE, vol=VOL(62), eff=RETRIG(2))
        pat.set(124, 0, note='F#3', inst=I_TOM,   vol=VOL(60))
        pat.set(126, 0, note='C#3', inst=I_TOM,   vol=VOL(64))
        pat.set(126, 1, note='C-4', inst=I_SNARE, vol=VOL(64))
    elif fill_end == 'turnaround_loop':
        # Seamless pickup fill into Order 0 Row 0! Clean hits ending at row 126 so Row 0 Kick/Crash slams!
        pat.set(112, 0, note='C-4', inst=I_KICK,  vol=VOL(64))
        pat.set(116, 0, note='A-3', inst=I_TOM,   vol=VOL(58))
        pat.set(118, 1, note='C-4', inst=I_SNARE, vol=VOL(54))
        pat.set(120, 1, note='C-4', inst=I_SNARE, vol=VOL(62))
        pat.set(120, 3, note='C-4', inst=I_CLAP,  vol=VOL(52))
        pat.set(122, 0, note='F#3', inst=I_TOM,   vol=VOL(60))
        pat.set(124, 0, note='C#3', inst=I_TOM,   vol=VOL(63))
        pat.set(125, 1, note='C-4', inst=I_SNARE, vol=VOL(52))
        pat.set(126, 1, note='C-4', inst=I_SNARE, vol=VOL(64))
