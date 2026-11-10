"""Handcrafted Leads, Twin-Harmony, Counter-Bell, Baroque Arps, Stabs & Pads (Ch 5..11)."""

from theory import OFF, arp_xy

I_LEAD  = 10  # Lead_Razorsaw (Ch 5)
I_TWIN  = 11  # Lead_TwinPulse (Ch 6 echo & twin 3rd/6th harmony)
I_BELL  = 12  # Bell_CrystalFM (Ch 7 motif & countermelody)
I_ARP1  = 13  # Arp_Pulse25 (Ch 8 wide-left 0xy & gated chip chords)
I_ARP2  = 14  # Arp_Hollow15 (Ch 9 wide-right Baroque 16th broken chords)
I_STAB  = 15  # Stab_PolyBrass (Ch 10 syncopated synthwave/demoscene stabs)
I_PAD   = 16  # Pad_Ensemble (Ch 11 lush ensemble string guide-tones)
I_RISER = 17  # FX_Riser1Bar (Ch 11 pre-drop 1-bar filter sweep)

# Common 0xy chord specs: (root_note_str, arp_param)
CHORD_SPECS = {
    "F#m":    ("F#4", arp_xy(7, 3),  ["C#5", "F#4", "A-4", "F#4", "D-5", "F#4", "C#5", "A-4"]),
    "F#m9":   ("A-4", arp_xy(9, 4),  ["G#5", "A-4", "C#5", "F#4", "F#5", "A-4", "C#5", "G#4"]),
    "F#7":    ("F#4", arp_xy(7, 4),  ["E-5", "F#4", "A#4", "F#4", "C#5", "F#4", "E-5", "A#4"]),
    "D":      ("D-4", arp_xy(7, 4),  ["A-4", "D-4", "F#4", "D-4", "D-5", "D-4", "A-4", "F#4"]),
    "Dmaj7":  ("F#4", arp_xy(7, 4),  ["C#5", "D-4", "A-4", "F#4", "D-5", "F#4", "C#5", "A-4"]),
    "D7":     ("F#4", arp_xy(6, 3),  ["C-5", "D-4", "A-4", "F#4", "D-5", "F#4", "C-5", "A-4"]),
    "E":      ("E-4", arp_xy(7, 4),  ["B-4", "E-4", "G#4", "E-4", "E-5", "E-4", "B-4", "G#4"]),
    "E7":     ("G#4", arp_xy(6, 3),  ["D-5", "E-4", "B-4", "G#4", "E-5", "G#4", "D-5", "B-4"]),
    "A":      ("E-4", arp_xy(8, 3),  ["C#5", "E-4", "A-4", "E-4", "E-5", "A-4", "C#5", "A-4"]),
    "Amaj7":  ("C#4", arp_xy(8, 4),  ["G#4", "C#4", "E-4", "A-4", "C#5", "E-4", "G#4", "E-4"]),
    "Bm7":    ("D-4", arp_xy(9, 4),  ["B-4", "D-4", "F#4", "D-4", "A-4", "D-4", "F#4", "A-4"]),
    "C#m7":   ("E-4", arp_xy(9, 4),  ["C#5", "E-4", "G#4", "E-4", "B-4", "E-4", "G#4", "B-4"]),
    "C#":     ("E#4", arp_xy(8, 3),  ["C#5", "E#4", "G#4", "E#4", "E#5", "G#4", "C#5", "G#4"]),
    "C#7":    ("E#4", arp_xy(6, 3),  ["B-4", "E#4", "G#4", "C#4", "C#5", "G#4", "B-4", "E#4"]),
    "C#7b9":  ("E#4", arp_xy(6, 3),  ["D-5", "E#4", "B-4", "G#4", "C#5", "E#4", "B-4", "D-5"]),
    "C#7sus": ("C#4", arp_xy(7, 5),  ["B-4", "C#4", "F#4", "G#4", "C#5", "F#4", "B-4", "G#4"]),
    "G#m7b5": ("D-4", arp_xy(6, 3),  ["B-4", "D-4", "F#4", "G#4", "D-5", "F#4", "B-4", "G#4"]),
    "B7":     ("D#4", arp_xy(6, 3),  ["B-4", "D#4", "A-4", "F#4", "B-4", "F#4", "A-4", "D#4"]),
    "D#m7b5": ("D#4", arp_xy(6, 3),  ["C#5", "D#4", "A-4", "F#4", "C#5", "F#4", "A-4", "F#4"]),
}

def _arp_segment(pat, r_start, n_rows, chord_key, mode="full", vel_scale=1.0):
    """Write complementary stereo arpeggios on Ch 8 (0xy chip chord) & Ch 9 (Baroque 16th broken chord)."""
    root_nt, xy, broken8 = CHORD_SPECS[chord_key]
    # Ch 8: rhythmic gated 0xy chip chord arpeggio
    if mode in ("full", "chorus", "intro"):
        gate_steps = [0, 3, 6, 8, 11, 14] if mode != "intro" else [0, 4, 8, 12]
        for s in range(n_rows):
            r = r_start + s
            sub = s % 16
            if sub in gate_steps or s == 0:
                v8 = min(64, int(round((54 if sub in (0, 8) else 48) * vel_scale)))
                pat.set(r, 8, note=root_nt, inst=I_ARP1, vol=v8, fx=0x0, param=xy)
            elif sub in (2, 5, 10, 13) and mode != "chorus":
                pat.off(r, 8)
            else:
                pat.set(r, 8, fx=0x0, param=xy)

    # Ch 9: agile Baroque 16th-note pedal-point broken chord
    if mode in ("full", "chorus", "intro", "musicbox"):
        contour = [60, 42, 54, 42, 58, 42, 54, 46]
        for s in range(n_rows):
            r = r_start + s
            nt9 = broken8[s % 8]
            v9 = int(round(contour[s % 8] * vel_scale))
            pat.set(r, 9, note=nt9, inst=I_ARP2, vol=v9)

def _stab_bar(pat, r0, chord_key, pattern_type="sync", chord_key_b=None):
    """Syncopated synthwave/demoscene brass-saw stabs on Ch 10."""
    hits = [(0, 50, 2), (3, 46, 2), (6, 48, 2), (10, 46, 2), (14, 48, 2)] if pattern_type == "sync" else [(2, 46, 2), (6, 48, 2), (10, 46, 2), (14, 50, 2)]
    for pos, vel, dur in hits:
        ck = chord_key_b if (chord_key_b and pos >= 8) else chord_key
        r_nt, xy, _ = CHORD_SPECS[ck]
        pat.set(r0 + pos, 10, note=r_nt, inst=I_STAB, vol=vel, fx=0x0, param=xy)
        for d in range(1, dur):
            if pos + d < 16:
                pat.set(r0 + pos + d, 10, fx=0x0, param=xy)
        if pos + dur < 16:
            pat.off(r0 + pos + dur, 10)

def _pad_span(pat, r_start, n_rows, note_str, vol=46):
    """Velvet chorus-string guide-tone sustain on Ch 11."""
    pat.set(r_start, 11, note=note_str, inst=I_PAD, vol=vol)
    if n_rows >= 4:
        pat.set(r_start + n_rows - 1, 11, fx=0xA, param=0x03)

def _phrase(pat, ch, inst, events):
    """Write an expressive melodic phrase from tuples:
    (row, note, dur, vol, kind)
    where kind can be:
      None       -> crisp articulated note + delayed vibrato if dur >= 4
      'leg'      -> smooth 3xx tone portamento from previous note!
      'vib'      -> rich singing 485 vibrato
      'mord_up'  -> Baroque 32nd-note upper ornament using ED3!
      'stac'     -> crisp staccato cut (EC3)
    """
    for idx, ev in enumerate(events):
        row, nt, dur, vol, kind = ev
        next_row = events[idx + 1][0] if idx + 1 < len(events) else None
        next_is_leg = (idx + 1 < len(events) and events[idx + 1][4] == "leg")

        if kind == "leg":
            pat.set(row, ch, note=nt, vol=vol, fx=0x3, param=0x34)
            if dur >= 2:
                pat.set(row + 1, ch, fx=0x3, param=0x34)
            if dur >= 4:
                for r in range(row + 2, min(64, row + dur)):
                    pat.set(r, ch, fx=0x4, param=0x84)
        elif kind == "stac":
            pat.set(row, ch, note=nt, inst=inst, vol=vol, fx=0xE, param=0xC3)
        else:
            pat.set(row, ch, note=nt, inst=inst, vol=vol)
            if dur >= 4 or kind == "vib":
                v_prm = 0x85 if kind == "vib" else 0x73
                for r in range(row + 2, min(64, row + dur)):
                    pat.set(r, ch, fx=0x4, param=v_prm)

        # Clean phrase release if there is a rest before next event and not legato
        end_r = row + dur
        if not next_is_leg and end_r < 64 and (next_row is None or end_r < next_row):
            pat.off(end_r, ch)

def write_melody_and_harmony(patterns):
    """Populate Ch 5..11 across all 16 patterns (0..15)."""

    # =========================================================================
    # SECTION I: IGNITION / BAROQUE CRYSTAL INTRO-GROOVE (Patterns 0..1)
    # =========================================================================
    p0 = patterns[0]
    _arp_segment(p0, 0,  16, "F#m",    mode="intro", vel_scale=0.90)
    _arp_segment(p0, 16, 16, "Dmaj7",  mode="intro", vel_scale=0.92)
    _arp_segment(p0, 32, 16, "Bm7",    mode="intro", vel_scale=0.94)
    _arp_segment(p0, 48, 8,  "C#7sus", mode="intro", vel_scale=0.96)
    _arp_segment(p0, 56, 8,  "C#7",    mode="intro", vel_scale=0.98)
    _pad_span(p0, 0,  16, "A-4", 42)
    _pad_span(p0, 16, 16, "A-4", 44)
    _pad_span(p0, 32, 16, "F#4", 44)
    _pad_span(p0, 48, 8,  "F#4", 46)
    _pad_span(p0, 56, 8,  "E#4", 48)
    # Ch 5 resolves the loop-turnaround E#5 cleanly onto tonic F#5 on Row 0, then hands off to Ch 7 Bell!
    _phrase(p0, 5, I_LEAD, [(0, "F#5", 6, 52, "vib")])
    # Ch 7 Crystal FM Bell states the signature Baroque Keygen Hook!
    _phrase(p0, 7, I_BELL, [
        (0,  "F#5", 3, 56, None), (3,  "G#5", 1, 48, None), (4,  "A-5", 2, 56, None), (6,  "C#6", 4, 60, "vib"),
        (12, "B-5", 2, 52, None), (14, "A-5", 2, 50, None),
        (16, "F#5", 3, 56, None), (19, "A-5", 3, 56, None), (22, "D-6", 4, 60, "vib"),
        (28, "C#6", 2, 54, None), (30, "A-5", 2, 50, None),
        (32, "B-5", 3, 56, None), (35, "A-5", 1, 48, None), (36, "F#5", 2, 54, None), (38, "D-5", 4, 56, "vib"),
        (44, "F#5", 2, 52, None), (46, "G#5", 2, 54, None),
        (48, "F#5", 6, 56, "vib"), (54, "G#5", 2, 54, None), (56, "E#5", 6, 60, "vib"),
    ])
    p0.apply_echo(7, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.42)

    p1 = patterns[1]
    _arp_segment(p1, 0,  16, "F#m",   mode="full", vel_scale=0.95)
    _arp_segment(p1, 16, 16, "Dmaj7", mode="full", vel_scale=0.96)
    _arp_segment(p1, 32, 16, "E",     mode="full", vel_scale=0.98)
    _arp_segment(p1, 48, 16, "C#7b9", mode="full", vel_scale=1.00)
    _pad_span(p1, 0,  16, "C#5", 44)
    _pad_span(p1, 16, 16, "A-4", 46)
    _pad_span(p1, 32, 16, "B-4", 48)
    # Bar 8: 1-Bar Filter Riser on Ch 11!
    p1.set(48, 11, note="C-4", inst=I_RISER, vol=58)
    # Ch 7 continues crystalline motif while Ch 5 Hero Lead enters with a rising teaser call!
    _phrase(p1, 7, I_BELL, [
        (0,  "F#5", 2, 54, None), (2,  "A-5", 2, 52, None), (4,  "C#6", 4, 58, "vib"),
        (16, "D-6", 2, 56, None), (18, "C#6", 2, 52, None), (20, "A-5", 4, 56, "vib"),
        (32, "B-5", 2, 56, None), (34, "G#5", 2, 52, None), (36, "E-6", 4, 60, "vib"),
        (48, "E#5", 2, 56, None), (50, "G#5", 2, 58, None), (52, "B-5", 2, 60, None),
        (54, "C#6", 2, 60, None), (56, "D-6", 4, 62, None), (60, "E#6", 4, 64, "vib"),
    ])
    _phrase(p1, 5, I_LEAD, [
        (8,  "C#5", 3, 52, None), (11, "F#5", 3, 56, "leg"), (14, "E-5", 2, 52, None),
        (24, "D-5", 3, 54, None), (27, "A-5", 3, 58, "leg"), (30, "F#5", 2, 54, None),
        (40, "E-5", 3, 56, None), (43, "B-5", 3, 60, "leg"), (46, "G#5", 2, 58, None),
        (48, "E#5", 4, 60, "vib"), (52, "G#5", 4, 62, "leg"), (56, "B-5", 4, 62, "leg"),
        (60, "C#6", 2, 64, None), (62, "E#5", 2, 62, None),
    ])
    p1.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.45)

    # =========================================================================
    # SECTION II: MAIN THEME A ("RAZOR HORIZON") (Patterns 2..5, Bars 9..24)
    # =========================================================================
    # Pat 2: F#m | D | E | A -> C#/E#
    p2 = patterns[2]
    _arp_segment(p2, 0,  16, "F#m", mode="full")
    _arp_segment(p2, 16, 16, "D",   mode="full")
    _arp_segment(p2, 32, 16, "E",   mode="full")
    _arp_segment(p2, 48, 8,  "A",   mode="full")
    _arp_segment(p2, 56, 8,  "C#",  mode="full")
    _stab_bar(p2, 0,  "F#m", "off")
    _stab_bar(p2, 16, "D",   "off")
    _stab_bar(p2, 32, "E",   "off")
    _stab_bar(p2, 48, "A",   "sync", chord_key_b="C#")
    _pad_span(p2, 32, 16, "G#4", 38)
    _pad_span(p2, 48, 8, "A-4", 40)
    _pad_span(p2, 56, 8, "G#4", 42)
    # Hero Razorsaw Lead states Theme A!
    _phrase(p2, 5, I_LEAD, [
        (0,  "F#5", 3, 62, None), (3,  "C#5", 1, 52, None), (4,  "F#5", 2, 60, None),
        (6,  "G#5", 2, 60, None), (8,  "A-5", 5, 64, "leg"), (14, "G#5", 2, 58, None),
        (16, "F#5", 3, 62, None), (19, "D-5", 1, 52, None), (20, "F#5", 2, 60, None),
        (22, "A-5", 4, 64, "vib"), (28, "G#5", 2, 58, None), (30, "F#5", 2, 58, None),
        (32, "G#5", 3, 62, None), (35, "E-5", 1, 52, None), (36, "G#5", 2, 60, None),
        (38, "B-5", 5, 64, "leg"), (44, "A-5", 2, 60, None), (46, "G#5", 2, 58, None),
        (48, "A-5", 3, 62, None), (51, "C#6", 3, 64, "leg"), (54, "B-5", 2, 60, None),
        (56, "G#5", 3, 62, None), (59, "E#5", 3, 62, "vib"), (62, "C#5", 2, 56, None),
    ])
    p2.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.45)
    # Answer sparkles on Ch 7 Bell in phrase gaps
    _phrase(p2, 7, I_BELL, [
        (12, "C#6", 2, 50, None), (14, "A-5", 2, 48, None),
        (26, "D-6", 2, 52, None), (28, "A-5", 2, 48, None),
        (42, "E-6", 2, 52, None), (44, "B-5", 2, 48, None),
        (60, "C#6", 2, 52, None), (62, "E#6", 2, 54, None),
    ])

    # Pat 3: D | Bm7 | G#m7b5 | C#7
    p3 = patterns[3]
    _arp_segment(p3, 0,  16, "D",      mode="full")
    _arp_segment(p3, 16, 16, "Bm7",    mode="full")
    _arp_segment(p3, 32, 16, "G#m7b5", mode="full")
    _arp_segment(p3, 48, 16, "C#7",    mode="full")
    _stab_bar(p3, 0,  "D",      "off")
    _stab_bar(p3, 16, "Bm7",    "off")
    _stab_bar(p3, 32, "G#m7b5", "sync")
    _stab_bar(p3, 48, "C#7",    "sync")
    _pad_span(p3, 16, 16, "F#4", 38)
    _pad_span(p3, 32, 16, "F#4", 40)
    _pad_span(p3, 48, 16, "E#4", 44)
    _phrase(p3, 5, I_LEAD, [
        (0,  "F#5", 3, 62, None), (3,  "A-5", 3, 64, "leg"), (6,  "D-6", 4, 64, "vib"),
        (12, "C#6", 2, 60, None), (14, "A-5", 2, 58, None),
        (16, "B-5", 3, 62, None), (19, "F#5", 1, 52, None), (20, "A-5", 2, 60, None),
        (22, "F#5", 4, 62, "vib"), (28, "E-5", 2, 58, None), (30, "D-5", 2, 58, None),
        # Baroque sequential climb over G#m7b5 -> C#7!
        (32, "D-5", 2, 60, None), (34, "F#5", 2, 60, None), (36, "B-5", 2, 62, None), (38, "A-5", 2, 60, None),
        (40, "G#5", 2, 62, None), (42, "B-5", 2, 62, None), (44, "D-6", 2, 64, None), (46, "B-5", 2, 60, None),
        (48, "C#6", 6, 64, "vib"), (54, "B-5", 2, 60, None),
        (56, "A-5", 2, 60, None), (58, "G#5", 2, 62, None), (60, "E#5", 2, 62, None), (62, "G#5", 2, 64, None),
    ])
    p3.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.45)
    _phrase(p3, 7, I_BELL, [
        (8,  "A-5", 2, 50, None), (10, "F#5", 2, 48, None),
        (24, "D-6", 2, 52, None), (26, "B-5", 2, 48, None),
        (50, "E#6", 2, 52, None), (52, "C#6", 2, 50, None),
    ])

    # Pat 4: F#m | F#m/E | Dmaj7 | C#m7 -> F#7 (with Bell Baroque Countermelody & Secondary Dom A#!)
    p4 = patterns[4]
    _arp_segment(p4, 0,  16, "F#m",   mode="full")
    _arp_segment(p4, 16, 16, "F#m",   mode="full")
    _arp_segment(p4, 32, 16, "Dmaj7", mode="full")
    _arp_segment(p4, 48, 8,  "C#m7",  mode="full")
    _arp_segment(p4, 56, 8,  "F#7",   mode="full")
    _stab_bar(p4, 0,  "F#m",   "sync")
    _stab_bar(p4, 16, "F#m",   "off")
    _stab_bar(p4, 32, "Dmaj7", "sync")
    _stab_bar(p4, 48, "C#m7",  "sync", chord_key_b="F#7")
    _pad_span(p4, 0,  16, "F#4", 44)
    _pad_span(p4, 16, 16, "E-4", 44)
    _pad_span(p4, 32, 16, "F#4", 46)
    _pad_span(p4, 48, 8,  "G#4", 46)
    _pad_span(p4, 56, 8,  "A#4", 50)
    _phrase(p4, 5, I_LEAD, [
        (0,  "A-5", 3, 64, None), (3,  "G#5", 1, 56, None), (4,  "A-5", 2, 62, None),
        (6,  "C#6", 4, 64, "leg"), (12, "B-5", 2, 60, None), (14, "A-5", 2, 60, None),
        (16, "G#5", 2, 60, None), (18, "A-5", 2, 62, None), (20, "C#6", 4, 64, "vib"),
        (26, "B-5", 2, 60, None), (28, "A-5", 2, 58, None), (30, "G#5", 2, 58, None),
        (32, "F#5", 3, 62, None), (35, "A-5", 3, 62, "leg"), (38, "D-6", 4, 64, "vib"),
        (44, "C#6", 2, 60, None), (46, "B-5", 2, 60, None),
        (48, "G#5", 3, 62, None), (51, "B-5", 3, 62, None), (54, "C#6", 2, 62, None),
        # Thrilling F#7 secondary dominant lift via A#5 -> C#6 -> E6!
        (56, "A#5", 3, 64, "vib"), (59, "C#6", 3, 64, "leg"), (62, "E-6", 2, 64, None),
    ])
    p4.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.45)
    # Agile contrary-motion Bell countermelody!
    _phrase(p4, 7, I_BELL, [
        (8,  "F#5", 2, 54, None), (10, "G#5", 2, 52, None), (12, "A-5", 4, 56, None),
        (24, "E-5", 2, 54, None), (26, "F#5", 2, 52, None), (28, "C#6", 4, 56, None),
        (40, "A-5", 2, 54, None), (42, "F#5", 2, 52, None), (44, "D-5", 4, 56, None),
        (56, "F#5", 2, 54, None), (58, "E-5", 2, 54, None), (60, "C#5", 2, 56, None), (62, "A#5", 2, 58, None),
    ])

    # Pat 5: Bm7 | E7 | Amaj7 -> Dmaj7 | G#m7b5 -> C#7 (Circle of Fifths Sequence!)
    p5 = patterns[5]
    _arp_segment(p5, 0,  16, "Bm7",    mode="full")
    _arp_segment(p5, 16, 16, "E7",     mode="full")
    _arp_segment(p5, 32, 8,  "Amaj7",  mode="full")
    _arp_segment(p5, 40, 8,  "Dmaj7",  mode="full")
    _arp_segment(p5, 48, 8,  "G#m7b5", mode="full")
    _arp_segment(p5, 56, 8,  "C#7b9",  mode="full")
    _stab_bar(p5, 0,  "Bm7",    "sync")
    _stab_bar(p5, 16, "E7",     "sync")
    _stab_bar(p5, 32, "Amaj7",  "sync", chord_key_b="Dmaj7")
    _stab_bar(p5, 48, "G#m7b5", "sync", chord_key_b="C#7")
    _pad_span(p5, 0,  16, "A-4", 46)
    _pad_span(p5, 16, 16, "G#4", 46)
    _pad_span(p5, 32, 8,  "G#4", 48)
    _pad_span(p5, 40, 8,  "F#4", 48)
    p5.set(48, 11, note="C-4", inst=I_RISER, vol=60)  # Riser into Chorus!
    _phrase(p5, 5, I_LEAD, [
        (0,  "D-6", 4, 64, "vib"), (4,  "C#6", 2, 60, None), (6,  "B-5", 2, 62, None),
        (8,  "A-5", 4, 62, "vib"), (12, "F#5", 2, 58, None), (14, "B-5", 2, 62, None),
        (16, "B-5", 4, 64, "vib"), (20, "A-5", 2, 60, None), (22, "G#5", 2, 62, None),
        (24, "E-5", 2, 58, None), (26, "G#5", 2, 60, None), (28, "B-5", 2, 62, None), (30, "D-6", 2, 64, None),
        (32, "C#6", 4, 64, "vib"), (36, "B-5", 2, 60, None), (38, "A-5", 2, 62, None),
        (40, "F#5", 3, 62, None), (43, "A-5", 3, 64, "leg"), (46, "D-6", 2, 64, None),
        (48, "B-5", 3, 62, None), (51, "D-6", 3, 64, "leg"), (54, "B-5", 2, 60, None),
        (56, "C#6", 4, 64, "vib"), (60, "D-6", 2, 64, None), (62, "E-6", 2, 64, None),
    ])
    p5.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.45)
    _phrase(p5, 7, I_BELL, [
        (0,  "B-5", 3, 54, None), (4,  "F#5", 2, 52, None), (6,  "D-5", 2, 50, None),
        (20, "D-5", 2, 52, None), (22, "B-4", 2, 50, None),
        (36, "E-5", 2, 54, None), (44, "F#5", 2, 54, None),
        (56, "E#5", 2, 56, None), (58, "G#5", 2, 58, None), (60, "B-5", 2, 60, None), (62, "C#6", 2, 62, None),
    ])

    # =========================================================================
    # SECTION III: ANTHEMIC CHORUS ("KEYGEN OVERDRIVE") (Patterns 6..9, Bars 25..40)
    # =========================================================================
    # Pat 6: Dmaj7 | E | C#m7 | F#m -> E  (Soaring Twin-Lead 3rds/6ths Harmony!!)
    p6 = patterns[6]
    _arp_segment(p6, 0,  16, "Dmaj7", mode="chorus")
    _arp_segment(p6, 16, 16, "E",     mode="chorus")
    _arp_segment(p6, 32, 16, "C#m7",  mode="chorus")
    _arp_segment(p6, 48, 12, "F#m",   mode="chorus")
    _arp_segment(p6, 60, 4,  "E",     mode="chorus")
    _stab_bar(p6, 0,  "Dmaj7", "sync")
    _stab_bar(p6, 16, "E",     "sync")
    _stab_bar(p6, 32, "C#m7",  "sync")
    _stab_bar(p6, 48, "F#m",   "sync")
    _pad_span(p6, 0,  16, "A-4", 48)
    _pad_span(p6, 16, 16, "B-4", 48)
    _pad_span(p6, 32, 16, "G#4", 48)
    _pad_span(p6, 48, 16, "A-4", 48)
    # Hero Chorus Anthem (Ch 5) + Twin Diatonic 3rd/6th Harmony (Ch 6)!
    _phrase(p6, 5, I_LEAD, [
        (0,  "F#6", 4, 64, "vib"), (4,  "E-6", 2, 62, None), (6,  "C#6", 4, 64, "leg"),
        (12, "A-5", 2, 60, None), (14, "D-6", 2, 62, None),
        (16, "E-6", 4, 64, "vib"), (20, "D-6", 2, 62, None), (22, "B-5", 4, 64, "leg"),
        (28, "G#5", 2, 60, None), (30, "B-5", 2, 62, None),
        (32, "C#6", 3, 64, None), (35, "B-5", 1, 58, None), (36, "C#6", 2, 62, None),
        (38, "E-6", 4, 64, "leg"), (44, "D-6", 2, 60, None), (46, "B-5", 2, 60, None),
        (48, "C#6", 3, 64, None), (51, "A-5", 3, 62, "leg"), (54, "F#5", 4, 64, "vib"),
        (60, "G#5", 2, 60, None), (62, "A-5", 2, 62, None),
    ])
    _phrase(p6, 6, I_TWIN, [
        (0,  "D-6", 4, 50, "vib"), (4,  "C#6", 2, 48, None), (6,  "A-5", 4, 50, "leg"),
        (12, "F#5", 2, 46, None), (14, "A-5", 2, 48, None),
        (16, "B-5", 4, 50, "vib"), (20, "B-5", 2, 48, None), (22, "G#5", 4, 50, "leg"),
        (28, "E-5", 2, 46, None), (30, "G#5", 2, 48, None),
        (32, "G#5", 3, 50, None), (35, "F#5", 1, 44, None), (36, "G#5", 2, 48, None),
        (38, "C#6", 4, 50, "leg"), (44, "B-5", 2, 48, None), (46, "G#5", 2, 48, None),
        (48, "A-5", 3, 50, None), (51, "F#5", 3, 48, "leg"), (54, "C#5", 4, 50, "vib"),
        (60, "E-5", 2, 48, None), (62, "F#5", 2, 50, None),
    ])
    _phrase(p6, 7, I_BELL, [
        (10, "A-6", 2, 50, None), (26, "G#6", 2, 50, None),
        (42, "E-6", 2, 50, None), (56, "F#6", 2, 52, None), (58, "C#6", 2, 50, None),
    ])

    # Pat 7: Dmaj7 | E/G# | A -> E/G# | F#m -> C#/E#
    p7 = patterns[7]
    _arp_segment(p7, 0,  16, "Dmaj7", mode="chorus")
    _arp_segment(p7, 16, 16, "E",     mode="chorus")
    _arp_segment(p7, 32, 8,  "A",     mode="chorus")
    _arp_segment(p7, 40, 8,  "E",     mode="chorus")
    _arp_segment(p7, 48, 8,  "F#m",   mode="chorus")
    _arp_segment(p7, 56, 8,  "C#",    mode="chorus")
    _stab_bar(p7, 0,  "Dmaj7", "sync")
    _stab_bar(p7, 16, "E",     "sync")
    _stab_bar(p7, 32, "A",     "sync", chord_key_b="E")
    _stab_bar(p7, 48, "F#m",   "sync", chord_key_b="C#")
    _pad_span(p7, 0,  16, "A-4", 48)
    _pad_span(p7, 16, 16, "B-4", 48)
    _pad_span(p7, 32, 8,  "C#5", 50)
    _pad_span(p7, 40, 8,  "B-4", 48)
    _pad_span(p7, 48, 8,  "A-4", 48)
    _pad_span(p7, 56, 8,  "G#4", 50)
    _phrase(p7, 5, I_LEAD, [
        (0,  "A-5", 3, 62, None), (3,  "D-6", 3, 64, "leg"), (6,  "C#6", 4, 64, "vib"),
        (12, "B-5", 2, 60, None), (14, "A-5", 2, 60, None),
        (16, "B-5", 3, 62, None), (19, "E-6", 3, 64, "leg"), (22, "D-6", 4, 64, "vib"),
        (28, "C#6", 2, 62, None), (30, "B-5", 2, 62, None),
        (32, "C#6", 3, 64, None), (35, "E-6", 3, 64, "leg"), (38, "A-6", 2, 64, None),
        (40, "G#6", 3, 64, "vib"), (43, "E-6", 3, 62, None), (46, "B-5", 2, 60, None),
        (48, "C#6", 4, 64, "vib"), (52, "A-5", 2, 60, None), (54, "F#5", 2, 60, None),
        (56, "E#5", 4, 64, "vib"), (60, "G#5", 2, 62, None), (62, "C#6", 2, 64, None),
    ])
    _phrase(p7, 6, I_TWIN, [
        (0,  "F#5", 3, 48, None), (3,  "A-5", 3, 50, "leg"), (6,  "A-5", 4, 50, "vib"),
        (12, "G#5", 2, 46, None), (14, "F#5", 2, 46, None),
        (16, "G#5", 3, 48, None), (19, "B-5", 3, 50, "leg"), (22, "B-5", 4, 50, "vib"),
        (28, "A-5", 2, 48, None), (30, "G#5", 2, 48, None),
        (32, "A-5", 3, 50, None), (35, "C#6", 3, 50, "leg"), (38, "E-6", 2, 52, None),
        (40, "E-6", 3, 50, "vib"), (43, "B-5", 3, 48, None), (46, "G#5", 2, 46, None),
        (48, "A-5", 4, 50, "vib"), (52, "F#5", 2, 48, None), (54, "C#5", 2, 48, None),
        (56, "C#5", 4, 50, "vib"), (60, "E#5", 2, 48, None), (62, "G#5", 2, 50, None),
    ])

    # Pat 8: Dmaj7 | C#7/E# | F#m -> F#m/E | B7/D# (Chromatic Dorian B7/D# Spotlight!)
    p8 = patterns[8]
    _arp_segment(p8, 0,  16, "Dmaj7", mode="chorus")
    _arp_segment(p8, 16, 16, "C#7",   mode="chorus")
    _arp_segment(p8, 32, 16, "F#m",   mode="chorus")
    _arp_segment(p8, 48, 16, "B7",    mode="chorus")
    _stab_bar(p8, 0,  "Dmaj7", "sync")
    _stab_bar(p8, 16, "C#7",   "sync")
    _stab_bar(p8, 32, "F#m",   "sync")
    _stab_bar(p8, 48, "B7",    "sync")
    _pad_span(p8, 0,  16, "A-4", 48)
    _pad_span(p8, 16, 16, "G#4", 48)
    _pad_span(p8, 32, 16, "A-4", 48)
    _pad_span(p8, 48, 16, "A-4", 50)
    _phrase(p8, 5, I_LEAD, [
        (0,  "D-6", 4, 64, "vib"), (4,  "C#6", 2, 62, None), (6,  "A-5", 4, 62, "leg"),
        (12, "B-5", 2, 60, None), (14, "D-6", 2, 62, None),
        (16, "C#6", 4, 64, "vib"), (20, "B-5", 2, 62, None), (22, "G#5", 4, 62, "leg"),
        (28, "B-5", 2, 60, None), (30, "E#5", 2, 62, None),
        (32, "F#5", 3, 62, None), (35, "A-5", 3, 62, "leg"), (38, "C#6", 4, 64, "vib"),
        (44, "E-6", 2, 64, None), (46, "F#6", 2, 64, None),
        # Goosebump Dorian D#6 note singing over B7/D#!
        (48, "D#6", 6, 64, "vib"), (54, "B-5", 2, 60, None),
        (56, "F#6", 4, 64, "leg"), (60, "E-6", 2, 62, None), (62, "D#6", 2, 62, None),
    ])
    _phrase(p8, 6, I_TWIN, [
        (0,  "A-5", 4, 50, "vib"), (4,  "A-5", 2, 48, None), (6,  "F#5", 4, 48, "leg"),
        (12, "G#5", 2, 46, None), (14, "A-5", 2, 48, None),
        (16, "G#5", 4, 50, "vib"), (20, "G#5", 2, 48, None), (22, "E#5", 4, 48, "leg"),
        (28, "G#5", 2, 46, None), (30, "C#5", 2, 48, None),
        (32, "C#5", 3, 48, None), (35, "F#5", 3, 48, "leg"), (38, "A-5", 4, 50, "vib"),
        (44, "C#6", 2, 50, None), (46, "C#6", 2, 50, None),
        (48, "B-5", 6, 52, "vib"), (54, "F#5", 2, 48, None),
        (56, "B-5", 4, 50, "leg"), (60, "B-5", 2, 48, None), (62, "A-5", 2, 48, None),
    ])

    # Pat 9: Bm7 | C#m7 -> Dmaj7 | E -> C#7/E# | F#m (Stop-Time Break at row 56!)
    p9 = patterns[9]
    _arp_segment(p9, 0,  16, "Bm7",   mode="chorus")
    _arp_segment(p9, 16, 8,  "C#m7",  mode="chorus")
    _arp_segment(p9, 24, 8,  "Dmaj7", mode="chorus")
    _arp_segment(p9, 32, 8,  "E",     mode="chorus")
    _arp_segment(p9, 40, 8,  "C#7",   mode="chorus")
    _arp_segment(p9, 48, 9,  "F#m",   mode="chorus")
    p9.off(58, 8)
    p9.off(58, 9)
    _stab_bar(p9, 0,  "Bm7",  "sync")
    _stab_bar(p9, 16, "C#m7", "sync", chord_key_b="Dmaj7")
    _stab_bar(p9, 32, "E",    "sync", chord_key_b="C#7")
    p9.set(56, 10, note="F#4", inst=I_STAB, vol=58, fx=0x0, param=arp_xy(7, 3))
    p9.off(58, 10)
    _pad_span(p9, 0,  16, "A-4", 48)
    _pad_span(p9, 16, 8,  "G#4", 48)
    _pad_span(p9, 24, 8,  "A-4", 48)
    _pad_span(p9, 32, 8,  "B-4", 50)
    _pad_span(p9, 40, 8,  "B-4", 50)
    _pad_span(p9, 48, 9,  "A-4", 50)
    p9.off(58, 11)
    _phrase(p9, 5, I_LEAD, [
        (0,  "D-6", 4, 62, "vib"), (4,  "B-5", 2, 60, None), (6,  "F#5", 2, 58, None),
        (8,  "A-5", 4, 62, "vib"), (12, "B-5", 2, 60, None), (14, "C#6", 2, 62, None),
        (16, "E-6", 4, 64, "vib"), (20, "C#6", 2, 62, None), (22, "B-5", 2, 60, None),
        (24, "D-6", 4, 64, "vib"), (28, "E-6", 2, 64, None), (30, "F#6", 2, 64, None),
        (32, "G#6", 4, 64, "vib"), (36, "E-6", 2, 62, None), (38, "B-5", 2, 60, None),
        (40, "C#6", 2, 62, None), (42, "D-6", 2, 62, None), (44, "E-6", 2, 64, None), (46, "E#6", 2, 64, None),
        (48, "F#6", 6, 64, "vib"), (54, "C#6", 2, 60, None),
        (56, "F#6", 2, 64, "stac"),  # Crisp stop-time hit!
    ])
    _phrase(p9, 6, I_TWIN, [
        (0,  "B-5", 4, 48, "vib"), (8,  "F#5", 4, 48, "vib"),
        (16, "G#5", 4, 50, "vib"), (24, "A-5", 4, 50, "vib"),
        (32, "B-5", 4, 52, "vib"), (40, "G#5", 4, 50, None), (44, "B-5", 4, 52, None),
        (48, "A-5", 6, 52, "vib"), (56, "A-5", 2, 54, "stac"),
    ])
    # Delicate crystal bell pickup in the stop-time silence leading into Breakdown!
    _phrase(p9, 7, I_BELL, [
        (60, "C#6", 2, 46, None), (62, "E-6", 2, 48, None),
    ])

    # =========================================================================
    # SECTION IV: CRYSTALLINE BREAKDOWN & BAROQUE SOLO BUILD (Patterns 10..11)
    # =========================================================================
    # Pat 10: Intimate Music-Box Breakdown (F#m9 | Dmaj7 | Bm7 | C#7sus -> C#7)
    p10 = patterns[10]
    _arp_segment(p10, 0,  16, "F#m9",   mode="musicbox", vel_scale=0.78)
    _arp_segment(p10, 16, 16, "Dmaj7",  mode="musicbox", vel_scale=0.80)
    _arp_segment(p10, 32, 16, "Bm7",    mode="musicbox", vel_scale=0.82)
    _arp_segment(p10, 48, 8,  "C#7sus", mode="musicbox", vel_scale=0.85)
    _arp_segment(p10, 56, 8,  "C#7",    mode="musicbox", vel_scale=0.88)
    _pad_span(p10, 0,  16, "A-4", 46)
    _pad_span(p10, 16, 16, "F#4", 46)
    _pad_span(p10, 32, 16, "F#4", 46)
    _pad_span(p10, 48, 8,  "F#4", 48)
    _pad_span(p10, 56, 8,  "E#4", 48)
    # Expressive music-box variation on Ch 7 Bell + stereo echo on Ch 6!
    _phrase(p10, 7, I_BELL, [
        (0,  "G#5", 2, 52, None), (2,  "A-5", 4, 56, "vib"), (8,  "C#6", 4, 54, "vib"), (14, "B-5", 2, 48, None),
        (16, "A-5", 4, 54, "vib"), (22, "F#5", 2, 48, None), (24, "D-6", 4, 56, "vib"), (30, "C#6", 2, 50, None),
        (32, "B-5", 4, 54, "vib"), (38, "F#5", 2, 48, None), (40, "A-5", 4, 54, "vib"), (46, "G#5", 2, 50, None),
        (48, "F#5", 6, 56, "vib"), (56, "E#5", 4, 58, "vib"), (60, "G#5", 2, 54, None), (62, "C#6", 2, 56, None),
    ])
    p10.apply_echo(7, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.36)

    # Pat 11: VIRTUOSO BAROQUE 16TH-NOTE SYNTH SOLO + MASSIVE BUILD!
    # Chords: Dmaj7 | Bm7 -> E7 | F#m -> D#m7b5 | D7 -> C#7
    p11 = patterns[11]
    _arp_segment(p11, 0,  16, "Dmaj7",  mode="full", vel_scale=0.88)
    _arp_segment(p11, 16, 8,  "Bm7",    mode="full", vel_scale=0.92)
    _arp_segment(p11, 24, 8,  "E7",     mode="full", vel_scale=0.94)
    _arp_segment(p11, 32, 8,  "F#m",    mode="full", vel_scale=0.96)
    _arp_segment(p11, 40, 8,  "D#m7b5", mode="full", vel_scale=0.98)
    _arp_segment(p11, 48, 8,  "D7",     mode="full", vel_scale=1.00)
    _arp_segment(p11, 56, 8,  "C#7b9",  mode="full", vel_scale=1.00)
    _pad_span(p11, 0,  16, "A-4", 46)
    _pad_span(p11, 16, 8,  "A-4", 48)
    _pad_span(p11, 24, 8,  "G#4", 48)
    _pad_span(p11, 32, 8,  "A-4", 50)
    _pad_span(p11, 40, 8,  "A-4", 50)
    p11.set(48, 11, note="C-4", inst=I_RISER, vol=62)  # Huge 1-bar riser into Grand Climax!

    # Blazing 16th-note Neo-Classical Baroque Solo on Ch 5 (every note chord-tone accurate!!):
    solo_notes = [
        # Bar 45 (Dmaj7): cascading pedal-point & scalar run
        "F#5", "A-5", "D-6", "C#6",  "A-5", "F#5", "A-5", "C#6",
        "D-6", "F#6", "E-6", "D-6",  "C#6", "A-5", "B-5", "C#6",
        # Bar 46 (Bm7 -> E7):
        "D-6", "B-5", "F#5", "B-5",  "D-6", "F#6", "E-6", "D-6",
        "B-5", "G#5", "E-5", "G#5",  "B-5", "D-6", "E-6", "D-6",
        # Bar 47 (F#m -> D#m7b5):
        "C#6", "A-5", "F#5", "A-5",  "C#6", "F#6", "E-6", "C#6",
        "D#6", "C#6", "A-5", "F#5",  "A-5", "C#6", "D#6", "F#6",
        # Bar 48 (D7 -> C#7(b9) climax launch!):
        "F#6", "D-6", "C-6", "A-5",  "C-6", "D-6", "F#6", "A-6",
        "G#6", "E#6", "D-6", "B-5",  "C#6", "D-6", "E#6", "G#6",
    ]
    for r, s_nt in enumerate(solo_notes):
        vel = 54 + min(10, r // 6)
        p11.set(r, 5, note=s_nt, inst=I_LEAD, vol=vel)
    p11.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.42)
    _phrase(p11, 7, I_BELL, [
        (0, "D-6", 4, 52, "vib"), (16, "F#6", 3, 50, None), (24, "G#6", 3, 52, None),
        (32, "A-6", 3, 52, None), (40, "F#6", 3, 54, None), (48, "A-6", 4, 56, None), (56, "G#6", 6, 58, "vib"),
    ])

    # =========================================================================
    # SECTION V: GRAND CLIMAX CHORUS & OUTRO TURNAROUND (Patterns 12..15)
    # =========================================================================
    # Pat 12: Dmaj7 | E | C#m7 -> F#7 | Bm7 -> C#7 (Overdrive Chorus + Secondary Dominant!)
    p12 = patterns[12]
    _arp_segment(p12, 0,  16, "Dmaj7", mode="chorus")
    _arp_segment(p12, 16, 16, "E",     mode="chorus")
    _arp_segment(p12, 32, 8,  "C#m7",  mode="chorus")
    _arp_segment(p12, 40, 8,  "F#7",   mode="chorus")
    _arp_segment(p12, 48, 8,  "Bm7",   mode="chorus")
    _arp_segment(p12, 56, 8,  "C#7",   mode="chorus")
    _stab_bar(p12, 0,  "Dmaj7", "sync")
    _stab_bar(p12, 16, "E",     "sync")
    _stab_bar(p12, 32, "C#m7",  "sync", chord_key_b="F#7")
    _stab_bar(p12, 48, "Bm7",   "sync", chord_key_b="C#7")
    _pad_span(p12, 0,  16, "A-4", 50)
    _pad_span(p12, 16, 16, "B-4", 50)
    _pad_span(p12, 32, 8,  "G#4", 50)
    _pad_span(p12, 40, 8,  "A#4", 52)
    _pad_span(p12, 48, 8,  "A-4", 50)
    _pad_span(p12, 56, 8,  "G#4", 52)
    _phrase(p12, 5, I_LEAD, [
        (0,  "F#6", 4, 64, "vib"), (4,  "E-6", 2, 62, None), (6,  "C#6", 4, 64, "leg"),
        (12, "D-6", 2, 62, None), (14, "F#6", 2, 64, None),
        (16, "G#6", 4, 64, "vib"), (20, "E-6", 2, 62, None), (22, "B-5", 4, 64, "leg"),
        (28, "C#6", 2, 62, None), (30, "D-6", 2, 62, None),
        (32, "E-6", 3, 64, None), (35, "C#6", 3, 62, None), (38, "B-5", 2, 60, None),
        (40, "A#5", 3, 64, "vib"), (43, "C#6", 3, 64, "leg"), (46, "E-6", 2, 64, None),
        (48, "D-6", 4, 64, "vib"), (52, "B-5", 2, 60, None), (54, "F#6", 2, 64, None),
        (56, "E#6", 4, 64, "vib"), (60, "C#6", 2, 62, None), (62, "G#5", 2, 62, None),
    ])
    _phrase(p12, 6, I_TWIN, [
        (0,  "D-6", 4, 52, "vib"), (4,  "C#6", 2, 50, None), (6,  "A-5", 4, 52, "leg"),
        (12, "A-5", 2, 50, None), (14, "D-6", 2, 52, None),
        (16, "E-6", 4, 52, "vib"), (20, "B-5", 2, 50, None), (22, "G#5", 4, 52, "leg"),
        (28, "A-5", 2, 50, None), (30, "B-5", 2, 50, None),
        (32, "C#6", 3, 52, None), (35, "G#5", 3, 50, None), (38, "G#5", 2, 48, None),
        (40, "F#5", 3, 52, "vib"), (43, "A#5", 3, 52, "leg"), (46, "C#6", 2, 52, None),
        (48, "B-5", 4, 52, "vib"), (52, "F#5", 2, 48, None), (54, "D-6", 2, 52, None),
        (56, "C#6", 4, 52, "vib"), (60, "G#5", 2, 50, None), (62, "E#5", 2, 50, None),
    ])
    _phrase(p12, 7, I_BELL, [
        (0,  "A-6", 2, 54, None), (8,  "F#6", 2, 52, None),
        (16, "B-6", 2, 54, None), (24, "G#6", 2, 52, None),
        (40, "F#6", 2, 54, None), (56, "G#6", 2, 56, None),
    ])

    # Pat 13: F#m | Dmaj7 | E | A -> C#7/E# (Dual-Theme Contrapuntal Fusion: Chorus Soar + Theme A Bell!)
    p13 = patterns[13]
    _arp_segment(p13, 0,  16, "F#m",   mode="chorus")
    _arp_segment(p13, 16, 16, "Dmaj7", mode="chorus")
    _arp_segment(p13, 32, 16, "E",     mode="chorus")
    _arp_segment(p13, 48, 8,  "A",     mode="chorus")
    _arp_segment(p13, 56, 8,  "C#7",   mode="chorus")
    _stab_bar(p13, 0,  "F#m",   "sync")
    _stab_bar(p13, 16, "Dmaj7", "sync")
    _stab_bar(p13, 32, "E",     "sync")
    _stab_bar(p13, 48, "A",     "sync", chord_key_b="C#7")
    _pad_span(p13, 0,  16, "C#5", 50)
    _pad_span(p13, 16, 16, "A-4", 50)
    _pad_span(p13, 32, 16, "B-4", 50)
    _pad_span(p13, 48, 8,  "C#5", 50)
    _pad_span(p13, 56, 8,  "B-4", 52)
    # Ch 5 sings a high soaring counter-descant while Ch 7 plays Theme A simultaneously!!
    _phrase(p13, 5, I_LEAD, [
        (0,  "C#6", 6, 64, "vib"), (6,  "B-5", 2, 60, None), (8,  "F#6", 6, 64, "leg"), (14, "E-6", 2, 62, None),
        (16, "D-6", 6, 64, "vib"), (22, "C#6", 2, 62, None), (24, "F#6", 6, 64, "leg"), (30, "A-6", 2, 64, None),
        (32, "G#6", 6, 64, "vib"), (38, "E-6", 2, 62, None), (40, "B-5", 4, 62, "vib"), (44, "C#6", 2, 62, None), (46, "D-6", 2, 62, None),
        (48, "E-6", 4, 64, "vib"), (52, "C#6", 4, 62, None), (56, "E#6", 4, 64, "vib"), (60, "G#6", 4, 64, "leg"),
    ])
    _phrase(p13, 6, I_TWIN, [
        (0,  "A-5", 6, 50, "vib"), (8,  "C#6", 6, 50, "leg"),
        (16, "A-5", 6, 50, "vib"), (24, "D-6", 6, 50, "leg"),
        (32, "E-6", 6, 52, "vib"), (40, "G#5", 4, 50, "vib"),
        (48, "C#6", 4, 50, "vib"), (56, "C#6", 4, 52, "vib"), (60, "E#6", 4, 52, "leg"),
    ])
    _phrase(p13, 7, I_BELL, [
        (0,  "F#5", 3, 58, None), (3, "C#5", 1, 50, None), (4, "F#5", 2, 56, None), (6, "G#5", 2, 56, None), (8, "A-5", 4, 60, None),
        (16, "F#5", 3, 58, None), (19, "D-5", 1, 50, None), (20, "F#5", 2, 56, None), (22, "A-5", 4, 60, None),
        (32, "G#5", 3, 58, None), (35, "E-5", 1, 50, None), (36, "G#5", 2, 56, None), (38, "B-5", 4, 60, None),
        (48, "A-5", 2, 58, None), (50, "C#6", 2, 58, None), (56, "B-5", 2, 58, None), (58, "G#5", 2, 58, None),
    ])

    # Pat 14: Dmaj7 | C#7/E# | F#m -> E | D#m7b5 -> Dmaj7 (Chromatic Climax Descent!)
    p14 = patterns[14]
    _arp_segment(p14, 0,  16, "Dmaj7",  mode="chorus")
    _arp_segment(p14, 16, 16, "C#7",    mode="chorus")
    _arp_segment(p14, 32, 8,  "F#m",    mode="chorus")
    _arp_segment(p14, 40, 8,  "E",      mode="chorus")
    _arp_segment(p14, 48, 8,  "D#m7b5", mode="chorus")
    _arp_segment(p14, 56, 8,  "Dmaj7",  mode="chorus")
    _stab_bar(p14, 0,  "Dmaj7",  "sync")
    _stab_bar(p14, 16, "C#7",    "sync")
    _stab_bar(p14, 32, "F#m",    "sync", chord_key_b="E")
    _stab_bar(p14, 48, "D#m7b5", "sync", chord_key_b="Dmaj7")
    _pad_span(p14, 0,  16, "A-4", 50)
    _pad_span(p14, 16, 16, "G#4", 50)
    _pad_span(p14, 32, 8,  "A-4", 50)
    _pad_span(p14, 40, 8,  "G#4", 50)
    _pad_span(p14, 48, 8,  "A-4", 52)
    _pad_span(p14, 56, 8,  "A-4", 50)
    _phrase(p14, 5, I_LEAD, [
        (0,  "F#6", 4, 64, "vib"), (4,  "D-6", 2, 62, None), (6,  "A-5", 4, 62, "leg"),
        (12, "B-5", 2, 62, None), (14, "D-6", 2, 64, None),
        (16, "C#6", 4, 64, "vib"), (20, "E#6", 4, 64, "leg"), (24, "G#6", 4, 64, "vib"),
        (28, "F#6", 2, 62, None), (30, "E#6", 2, 62, None),
        (32, "F#6", 4, 64, "vib"), (36, "C#6", 2, 62, None), (38, "A-5", 2, 60, None),
        (40, "B-5", 4, 62, "vib"), (44, "E-6", 4, 64, "leg"),
        (48, "D#6", 4, 64, "vib"), (52, "C#6", 2, 62, None), (54, "A-5", 2, 60, None),
        (56, "D-6", 4, 64, "vib"), (60, "C#6", 2, 62, None), (62, "A-5", 2, 60, None),
    ])
    _phrase(p14, 6, I_TWIN, [
        (0,  "D-6", 4, 50, "vib"), (6,  "F#5", 4, 50, "leg"),
        (16, "G#5", 4, 50, "vib"), (20, "C#6", 4, 52, "leg"), (24, "E#6", 4, 52, "vib"),
        (32, "C#6", 4, 50, "vib"), (40, "G#5", 4, 50, "vib"), (44, "B-5", 4, 50, "leg"),
        (48, "A-5", 4, 52, "vib"), (56, "A-5", 4, 50, "vib"),
    ])

    # Pat 15: Bm7 | G#m7b5 | C#7sus4 | C#7(b9) -> SEAMLESS LOOP TURNAROUND TO PAT 0 ROW 0!
    p15 = patterns[15]
    _arp_segment(p15, 0,  16, "Bm7",    mode="full", vel_scale=0.98)
    _arp_segment(p15, 16, 16, "G#m7b5", mode="full", vel_scale=0.96)
    _arp_segment(p15, 32, 16, "C#7sus", mode="full", vel_scale=0.96)
    _arp_segment(p15, 48, 16, "C#7b9",  mode="full", vel_scale=0.94)
    _stab_bar(p15, 0,  "Bm7",    "sync")
    _stab_bar(p15, 16, "G#m7b5", "sync")
    _stab_bar(p15, 32, "C#7sus", "off")
    p15.set(48, 10, note="E#4", inst=I_STAB, vol=50, fx=0x0, param=arp_xy(6, 3))
    p15.off(52, 10)  # Stabs clear cleanly before loop seam so Pat 0 crystal texture breathes!
    _pad_span(p15, 0,  16, "A-4", 48)
    _pad_span(p15, 16, 16, "B-4", 48)
    _pad_span(p15, 32, 16, "B-4", 48)
    _pad_span(p15, 48, 14, "G#4", 46)
    p15.off(62, 11)  # Pad releases smoothly before Pat 0 Row 0 A-4 pad entry!

    # Hero Lead winds down from climax and plays a thrilling leading-tone pickup E#5 -> Pat 0 Row 0 F#5!
    _phrase(p15, 5, I_LEAD, [
        (0,  "B-5", 4, 62, "vib"), (4,  "A-5", 2, 60, None), (6,  "F#5", 4, 60, "leg"),
        (12, "A-5", 2, 60, None), (14, "B-5", 2, 62, None),
        (16, "D-6", 4, 64, "vib"), (20, "B-5", 2, 60, None), (22, "G#5", 4, 60, "leg"),
        (28, "A-5", 2, 58, None), (30, "B-5", 2, 60, None),
        (32, "F#5", 6, 62, "vib"), (38, "G#5", 2, 58, None), (40, "C#6", 6, 62, "vib"),
        # Final bar C#7(b9) turnaround pickup: G#4 -> B4 -> C#5 -> D5 -> E#5 -> [Pat 0 Row 0 F#5!]
        (48, "E#5", 4, 60, "vib"), (52, "D-5", 2, 56, None), (54, "C#5", 2, 56, None),
        (56, "B-4", 2, 54, None), (58, "C#5", 2, 56, None), (60, "D-5", 2, 58, None), (62, "E#5", 2, 60, None),
    ])
    p15.apply_echo(5, 6, echo_inst=I_TWIN, delay_rows=3, vol_scale=0.42, max_row=61)
    p15.off(62, 6)  # Clean echo release before wrap!
    # Crystal Bell joins on the final 4 notes to weld seamlessly into Pat 0 Row 0's Bell motif!
    _phrase(p15, 7, I_BELL, [
        (56, "G#5", 2, 50, None), (58, "B-5", 2, 52, None), (60, "D-6", 2, 54, None), (62, "E#5", 2, 56, None),
    ])

    # --- Authentic Keygen Baroque Cadential Trills & 32nd-Note Ornaments ---
    # Pat 0 row 60-61: Bell Baroque trill E#5-G#5 on dominant C#7 turnaround
    p0.set(60, 7, fx=0x0, param=arp_xy(3, 3))
    p0.set(61, 7, fx=0x0, param=arp_xy(3, 3))
    # Pat 3 row 52-53: Hero Lead C#6-D6 b9 Baroque trill over C#7 cadence
    p3.set(52, 5, fx=0x0, param=arp_xy(1, 1))
    p3.set(53, 5, fx=0x0, param=arp_xy(1, 1))
    # Pat 6 & Pat 12 row 3: 32nd-note grace-note flick into E-6 in Chorus Anthem!
    p6.set(3,  5, note="G#6", inst=I_LEAD, vol=54, fx=0xE, param=0xD3)
    p12.set(3, 5, note="G#6", inst=I_LEAD, vol=56, fx=0xE, param=0xD3)
    # Pat 7 row 58-59: Hero Lead E#5-G#5 cadential trill before C#6 leap
    p7.set(58, 5, fx=0x0, param=arp_xy(3, 3))
    p7.set(59, 5, fx=0x0, param=arp_xy(3, 3))

    # --- Cross-Pattern Sustain Hygiene (Zero unintended hanging notes across all 16 boundaries) ---
    sustained_chs = [3, 4, 5, 6, 7, 8, 9, 10, 11]
    for p_idx in range(len(patterns)):
        cur_p = patterns[p_idx]
        nxt_p = patterns[(p_idx + 1) % len(patterns)]
        for ch in sustained_chs:
            # Find last note state in cur_p
            last_state = None
            for r in range(64):
                c = cur_p.cells.get((r, ch))
                if c:
                    if c.get("note") == OFF or c.get("instrument") == I_RISER:
                        last_state = "off"
                    elif c.get("note") is not None:
                        last_state = "on"
                    if c.get("effect") == 0xE and (c.get("effect_param", 0) & 0xF0) == 0xC0:
                        last_state = "off"
            if last_state == "on":
                nxt_c0 = nxt_p.cells.get((0, ch))
                if not nxt_c0 or nxt_c0.get("note") is None:
                    nxt_p.off(0, ch)
