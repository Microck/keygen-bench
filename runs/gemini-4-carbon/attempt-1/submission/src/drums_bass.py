"""Handcrafted Drums (Ch 0..2) & Synth/Sub Basslines (Ch 3..4) across all 16 Patterns (64 Bars)."""

from theory import OFF

# Instrument IDs
I_KICK  = 1
I_SNARE = 2
I_CLAP  = 3
I_HATC  = 4
I_HATO  = 5
I_TOM   = 6
I_CRASH = 7
I_BASS  = 8
I_SUB   = 9

def _hat_16th_bar(pat, r0, open_offbeats=True, crash_start=False, intensity=1.0):
    """Sculpted 16th-note hi-hat groove over 1 bar (16 rows starting at r0)."""
    base_vels = [44, 24, 38, 26,  40, 22, 38, 28,  42, 24, 38, 26,  40, 24, 40, 30]
    for i in range(16):
        r = r0 + i
        vel = max(12, min(60, int(round(base_vels[i] * intensity))))
        if i == 0 and crash_start:
            pat.set(r, 2, note="C-4", inst=I_CRASH, vol=min(56, int(50 * intensity + 6)))
        elif open_offbeats and i in (2, 6, 10, 14):
            pat.set(r, 2, note="C-4", inst=I_HATO, vol=min(56, vel + 6))
        else:
            pat.set(r, 2, note="C-4", inst=I_HATC, vol=vel)

def _driving_beat_bar(pat, r0, variant=0, clap_layer=False, crash=False, intensity=1.0):
    """1-bar driving keygen drum groove with musical ghost snares & syncopated kicks."""
    _hat_16th_bar(pat, r0, open_offbeats=True, crash_start=crash, intensity=intensity)
    # Kick pattern variants
    if variant == 0:
        kicks = [(0, 62), (4, 56), (8, 60), (10, 48), (12, 56)]
    elif variant == 1:
        kicks = [(0, 62), (4, 56), (7, 44), (8, 60), (12, 56), (14, 50)]
    elif variant == 2:
        kicks = [(0, 62), (3, 44), (6, 52), (8, 60), (10, 50), (12, 58)]
    else:  # energetic chorus drive
        kicks = [(0, 64), (4, 58), (8, 62), (10, 50), (12, 58), (15, 46)]

    for idx_k, (pos, kv) in enumerate(kicks):
        # Ensure Ch 0 returns to dead-center 0x80 after any stereo tom fill!
        fx_k = 0x8 if idx_k == 0 else None
        prm_k = 0x80 if idx_k == 0 else None
        pat.set(r0 + pos, 0, note="C-4", inst=I_KICK, vol=int(round(kv * intensity)), fx=fx_k, param=prm_k)

    # Snare / Clap on 2 & 4 + ghost notes
    sn_inst = I_CLAP if clap_layer else I_SNARE
    pat.set(r0 + 4, 1, note="C-4", inst=I_SNARE, vol=int(round(60 * intensity)))
    pat.set(r0 + 12, 1, note="C-4", inst=sn_inst, vol=int(round(62 * intensity)))
    if variant in (1, 3):
        # Ghost snare on 16th offbeat with subtle tick-1 micro-groove
        pat.set(r0 + 9, 1, note="C-4", inst=I_SNARE, vol=int(round(22 * intensity)), fx=0xE, param=0xD1)
    if variant == 2:
        pat.set(r0 + 7, 1, note="C-4", inst=I_SNARE, vol=int(round(24 * intensity)))
        pat.set(r0 + 15, 1, note="C-4", inst=I_SNARE, vol=int(round(28 * intensity)))

def _fill_bar(pat, r0, fill_type="launch"):
    """Handcrafted 1-bar keygen drum fills (toms, 32nd snare rolls, stop-time breaks)."""
    if fill_type == "launch":
        # Bar 8 launch into Theme A: accelerating kicks + melodic Simmons tom cascade + 32nd snare roll!
        for i in (0, 2, 4, 6):
            pat.set(r0 + i, 0, note="C-4", inst=I_KICK, vol=54 + i)
            pat.set(r0 + i, 2, note="C-4", inst=I_HATC, vol=36 + i)
        pat.set(r0 + 4, 1, note="C-4", inst=I_SNARE, vol=58)
        # Beats 3 & 4: tom cascade + blazing snare crescendo
        # Stereo panning Simmons tom cascade sweeping Left (0x28) -> Right (0xD8)!
        toms = [(8, "F#4", 52, 0x28), (9, "E-4", 50, 0x40), (10, "D-4", 54, 0x58), (11, "C#4", 52, 0x74),
                (12, "B-3", 56, 0x90), (13, "A-3", 56, 0xAC), (14, "G#3", 58, 0xC4), (15, "F#3", 58, 0xD8)]
        for pos, tn, tv, tpan in toms:
            pat.set(r0 + pos, 0, note=tn, inst=I_TOM, vol=tv, fx=0x8, param=tpan)
        for pos, sv in [(8, 34), (10, 42), (12, 50), (13, 54), (14, 58), (15, 64)]:
            fx = 0xE if pos >= 14 else None
            prm = 0x93 if pos >= 14 else None  # 32nd-note retrigger on last two 16ths!
            pat.set(r0 + pos, 1, note="C-4", inst=I_SNARE, vol=sv, fx=fx, param=prm)
        pat.set(r0 + 12, 2, note="C-4", inst=I_HATO, vol=54)

    elif fill_type == "mid_tom":
        # Punchy 2-beat groove -> 2-beat syncopated tom/snare turnaround
        _hat_16th_bar(pat, r0, open_offbeats=True, crash_start=False, intensity=1.0)
        for pos in (0, 4, 7):
            pat.set(r0 + pos, 0, note="C-4", inst=I_KICK, vol=60)
        pat.set(r0 + 4, 1, note="C-4", inst=I_SNARE, vol=60)
        pat.set(r0 + 8, 0, note="C-4", inst=I_KICK, vol=62)
        pat.set(r0 + 9, 1, note="C-4", inst=I_SNARE, vol=44)
        pat.set(r0 + 10, 0, note="D-4", inst=I_TOM, vol=56, fx=0x8, param=0x38)
        pat.set(r0 + 11, 0, note="B-3", inst=I_TOM, vol=56, fx=0x8, param=0x68)
        pat.set(r0 + 12, 1, note="C-4", inst=I_CLAP, vol=60)
        pat.set(r0 + 13, 0, note="A-3", inst=I_TOM, vol=58, fx=0x8, param=0xA8)
        pat.set(r0 + 14, 1, note="C-4", inst=I_SNARE, vol=56, fx=0xE, param=0x93)
        pat.set(r0 + 15, 0, note="F#3", inst=I_TOM, vol=58, fx=0x8, param=0xD4)

    elif fill_type == "chorus_lift":
        # Bar 24 huge lift into Anthem Chorus
        _hat_16th_bar(pat, r0, open_offbeats=False, crash_start=False, intensity=1.0)
        for pos in (0, 3, 6, 8):
            pat.set(r0 + pos, 0, note="C-4", inst=I_KICK, vol=62)
        pat.set(r0 + 4, 1, note="C-4", inst=I_SNARE, vol=60)
        for pos, sv in [(9, 36), (10, 42), (11, 48), (12, 54), (13, 58), (14, 62), (15, 64)]:
            pat.set(r0 + pos, 1, note="C-4", inst=I_SNARE, vol=sv,
                    fx=(0xE if pos >= 13 else None), param=(0x92 if pos == 15 else (0x93 if pos >= 13 else None)))
        for pos, tn, tp in [(10, "E-4", 0x34), (12, "C#4", 0x6C), (14, "A-3", 0xA8), (15, "G#3", 0xD4)]:
            pat.set(r0 + pos, 0, note=tn, inst=I_TOM, vol=56, fx=0x8, param=tp)
        pat.set(r0 + 14, 2, note="C-4", inst=I_HATO, vol=58)

    elif fill_type == "break_stop":
        # Bar 40 dramatic stop-time tutti hit on beat 3 ("1 - 2 - HIT! [silence]") into Breakdown!
        for i in range(9):
            pat.set(r0 + i, 2, note="C-4", inst=(I_HATO if i in (2, 6) else I_HATC), vol=40)
        pat.set(r0 + 0, 0, note="C-4", inst=I_KICK, vol=62)
        pat.set(r0 + 4, 1, note="C-4", inst=I_SNARE, vol=62)
        pat.set(r0 + 6, 0, note="C-4", inst=I_KICK, vol=56)
        # Beat 3 (r0+8): crisp punchy stop-hit!
        pat.set(r0 + 8, 0, note="C-4", inst=I_KICK, vol=64)
        pat.set(r0 + 8, 1, note="C-4", inst=I_CLAP, vol=60)
        pat.set(r0 + 8, 2, note="C-4", inst=I_CRASH, vol=52)
        # Beat 4: delicate pickup closed-hat whisper into breakdown
        pat.set(r0 + 14, 2, note="C-4", inst=I_HATC, vol=22)
        pat.set(r0 + 15, 2, note="C-4", inst=I_HATC, vol=28)

    elif fill_type == "loop_turnaround":
        # Bar 64 V7(b9) turnaround resolving seamlessly onto Pattern 0 Row 0 F#m downbeat!
        _hat_16th_bar(pat, r0, open_offbeats=True, crash_start=False, intensity=1.0)
        for pos in (0, 4, 6):
            pat.set(r0 + pos, 0, note="C-4", inst=I_KICK, vol=62)
        pat.set(r0 + 4, 1, note="C-4", inst=I_SNARE, vol=60)
        # Syncopated keygen tom + snare turnaround over beats 3 & 4 leading straight to Row 0!
        turn_toms = [(8, "E#4", 56, 0x30), (10, "D-4", 56, 0x58), (11, "C#4", 58, 0x80), (13, "B-3", 58, 0xAC), (14, "G#3", 60, 0xD4)]
        for pos, tn, tv, tp in turn_toms:
            pat.set(r0 + pos, 0, note=tn, inst=I_TOM, vol=tv, fx=0x8, param=tp)
        pat.set(r0 + 15, 0, note="C-4", inst=I_KICK, vol=52, fx=0x8, param=0x80)  # tight pickup kick into Pat 0 Row 0!
        pat.set(r0 + 9, 1, note="C-4", inst=I_SNARE, vol=44)
        pat.set(r0 + 12, 1, note="C-4", inst=I_CLAP, vol=62)
        pat.set(r0 + 14, 1, note="C-4", inst=I_SNARE, vol=56)
        pat.set(r0 + 15, 1, note="C-4", inst=I_SNARE, vol=62, fx=0xE, param=0x93)
        pat.set(r0 + 15, 2, note="C-4", inst=I_HATC, vol=48)  # chokes open hat cleanly before wrap!

def _bass_octave_bar(pat, r0, root_low, root_hi, walk_notes=None, sub_note=None, duck_kick=True, style="drive"):
    """Idiomatic keygen octave-jumping synth bassline over 16 rows (1 bar) on Ch 3 (+ optional Sub on Ch 4).
    Uses sample offset 910 on kick downbeats so Kick + Bass never fight for transient headroom!
    """
    if style == "drive":
        # Classic relentless keygen octave bounce: Low - low - HI - low | Low - HI - low - HI ...
        seq = [
            (0,  root_low, 44, True),
            (2,  root_hi,  60, False),
            (3,  root_low, 46, False),
            (4,  root_low, 46, True),
            (6,  root_hi,  62, False),
            (7,  root_hi,  50, False),
            (8,  root_low, 44, True),
            (10, root_hi,  60, False),
            (11, root_low, 48, False),
            (12, root_low, 46, True),
            (14, root_hi,  62, False),
            (15, root_low, 52, False),
        ]
        if walk_notes:
            # Replace rows 12..15 with custom melodic bass walkup/walkdown!
            seq = [x for x in seq if x[0] < 12] + walk_notes
        for pos, nt, vel, is_down in seq:
            if duck_kick and is_down:
                pat.set(r0 + pos, 3, note=nt, inst=I_BASS, vol=vel, fx=0x9, param=0x10)
            else:
                pat.set(r0 + pos, 3, note=nt, inst=I_BASS, vol=vel)
            # Tight articulation cut on certain 16ths for funky bounce
            if pos in (2, 6, 10) and (pos + 1) not in [x[0] for x in seq]:
                pat.off(r0 + pos + 1, 3)

    elif style == "pulse_intro":
        # Syncopated pulsing 8th/16th bass for Section I Ignition
        pts = [(0, root_low, 54, False), (3, root_hi, 52, False), (6, root_hi, 56, False),
               (8, root_low, 52, duck_kick), (10, root_hi, 54, False), (12, root_low, 50, duck_kick), (14, root_hi, 56, False)]
        if walk_notes:
            pts = [x for x in pts if x[0] < 12] + walk_notes
        for pos, nt, vel, dk in pts:
            pat.set(r0 + pos, 3, note=nt, inst=I_BASS, vol=vel, fx=(0x9 if dk else None), param=(0x10 if dk else None))
        pat.off(r0 + 2, 3)
        pat.off(r0 + 5, 3)
        pat.off(r0 + 7, 3)

    if sub_note is not None:
        # Smooth sub-bass sustain on Ch 4, gently ducked on beat 1 & 3
        pat.set(r0 + 0, 4, note=sub_note, inst=I_SUB, vol=36)
        pat.set(r0 + 1, 4, vol=52)
        pat.set(r0 + 8, 4, vol=38)
        pat.set(r0 + 9, 4, vol=52)
        pat.set(r0 + 15, 4, fx=0xA, param=0x04)

def write_drums_and_bass(patterns):
    """Populate Ch 0..4 across all 16 patterns (0..15)."""

    # =========================================================================
    # SECTION I: IGNITION / BAROQUE CRYSTAL GROOVE (Patterns 0..1, Bars 1..8)
    # =========================================================================
    p0 = patterns[0]
    # Row 0 tonic impact (resolves Pat 15 turnaround AND ignites initial play!)
    p0.set(0, 0, note="C-4", inst=I_KICK, vol=62, fx=0x8, param=0x80)
    _hat_16th_bar(p0, 0,  open_offbeats=False, crash_start=True,  intensity=0.82)
    _hat_16th_bar(p0, 16, open_offbeats=False, crash_start=False, intensity=0.85)
    _hat_16th_bar(p0, 32, open_offbeats=True,  crash_start=False, intensity=0.88)
    _hat_16th_bar(p0, 48, open_offbeats=True,  crash_start=False, intensity=0.92)
    # Light rim/clap pulse on beat 4 of bars 2 & 4
    p0.set(28, 1, note="C-4", inst=I_CLAP, vol=38)
    p0.set(60, 1, note="C-4", inst=I_CLAP, vol=44)
    p0.set(62, 1, note="C-4", inst=I_SNARE, vol=36)
    # Pat 0 Bass: F#m | Dmaj7 | Bm7 | C#7sus4 -> C#7
    _bass_octave_bar(p0, 0,  "F#1", "F#2", style="pulse_intro", sub_note="F#1")
    _bass_octave_bar(p0, 16, "D-2", "D-3", style="pulse_intro", sub_note="D-2")
    _bass_octave_bar(p0, 32, "B-1", "B-2", style="pulse_intro", sub_note="B-1")
    _bass_octave_bar(p0, 48, "C#2", "C#3", style="pulse_intro", sub_note="C#2",
                     walk_notes=[(12, "C#2", 54, False), (14, "D-2", 56, False), (15, "E#2", 60, False)])

    p1 = patterns[1]
    # Bars 5..7: 4-on-the-floor kick enters + crisp hats; Bar 8: huge Launch Fill!
    for bar_i, r0 in enumerate([0, 16, 32]):
        _hat_16th_bar(p1, r0, open_offbeats=True, crash_start=(bar_i == 0), intensity=0.94)
        for kpos in (0, 4, 8, 12):
            p1.set(r0 + kpos, 0, note="C-4", inst=I_KICK, vol=58)
        p1.set(r0 + 12, 1, note="C-4", inst=I_SNARE, vol=48 + bar_i * 4)
    _fill_bar(p1, 48, "launch")
    # Pat 1 Bass: F#m | Dmaj7 | E | C#7/E# -> C#7
    _bass_octave_bar(p1, 0,  "F#1", "F#2", duck_kick=True, style="pulse_intro", sub_note="F#1")
    _bass_octave_bar(p1, 16, "D-2", "D-3", duck_kick=True, style="pulse_intro", sub_note="D-2")
    _bass_octave_bar(p1, 32, "E-2", "E-3", duck_kick=True, style="pulse_intro", sub_note="E-2")
    _bass_octave_bar(p1, 48, "E#2", "C#3", duck_kick=True, style="drive",
                     walk_notes=[(12, "C#2", 60, False), (13, "B-1", 58, False), (14, "A-1", 60, False), (15, "G#1", 62, False)])
    p1.off(48, 4)

    # =========================================================================
    # SECTION II: MAIN THEME A ("RAZOR HORIZON") (Patterns 2..5, Bars 9..24)
    # =========================================================================
    # Pat 2: F#m | D | E | A -> C#/E#
    p2 = patterns[2]
    _driving_beat_bar(p2, 0,  variant=0, crash=True)
    _driving_beat_bar(p2, 16, variant=1)
    _driving_beat_bar(p2, 32, variant=0)
    _driving_beat_bar(p2, 48, variant=2)
    p2.off(0, 4)
    _bass_octave_bar(p2, 0,  "F#1", "F#2", walk_notes=[(12, "F#1", 48, True), (14, "F#2", 60, False), (15, "E-2", 56, False)])
    _bass_octave_bar(p2, 16, "D-2", "D-3", walk_notes=[(12, "D-2", 48, True), (14, "D-3", 60, False), (15, "D#2", 56, False)])
    _bass_octave_bar(p2, 32, "E-2", "E-3", walk_notes=[(12, "E-2", 48, True), (14, "G#2", 60, False), (15, "B-2", 58, False)])
    # Split bar: A (beats 1..2) -> C#/E# (beats 3..4)
    _bass_octave_bar(p2, 48, "A-1", "A-2",
                     walk_notes=[(8, "E#2", 48, True), (10, "C#3", 60, False), (11, "G#2", 54, False),
                                 (12, "E#2", 48, True), (14, "C#2", 60, False), (15, "E#2", 58, False)])

    # Pat 3: D | Bm7 | G#m7b5 | C#7
    p3 = patterns[3]
    _driving_beat_bar(p3, 0,  variant=0)
    _driving_beat_bar(p3, 16, variant=1)
    _driving_beat_bar(p3, 32, variant=2)
    _fill_bar(p3, 48, "mid_tom")
    _bass_octave_bar(p3, 0,  "D-2", "D-3", walk_notes=[(12, "D-2", 48, True), (14, "C#2", 58, False), (15, "C-2", 56, False)])
    _bass_octave_bar(p3, 16, "B-1", "B-2", walk_notes=[(12, "B-1", 48, True), (14, "A-1", 58, False), (15, "A-2", 58, False)])
    _bass_octave_bar(p3, 32, "G#1", "G#2", walk_notes=[(12, "G#1", 48, True), (14, "B-1", 58, False), (15, "D-2", 60, False)])
    _bass_octave_bar(p3, 48, "C#2", "C#3", walk_notes=[(12, "C#2", 56, False), (13, "D-2", 58, False), (14, "E-2", 60, False), (15, "E#2", 62, False)])

    # Pat 4: F#m | F#m/E | Dmaj7 | C#m7 -> F#7 (with secondary dominant A#!)
    p4 = patterns[4]
    _driving_beat_bar(p4, 0,  variant=3, clap_layer=True, crash=True)
    _driving_beat_bar(p4, 16, variant=1, clap_layer=True)
    _driving_beat_bar(p4, 32, variant=0, clap_layer=True)
    _driving_beat_bar(p4, 48, variant=2, clap_layer=True)
    _bass_octave_bar(p4, 0,  "F#1", "F#2", sub_note="F#1")
    _bass_octave_bar(p4, 16, "E-2", "E-3", sub_note="E-2")
    _bass_octave_bar(p4, 32, "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p4, 48, "C#2", "C#3", sub_note="F#1",
                     walk_notes=[(8, "F#1", 48, True), (10, "F#2", 62, False), (11, "E-2", 56, False),
                                 (12, "A#1", 52, True), (14, "A#2", 62, False), (15, "C#2", 58, False)])

    # Pat 5: Bm7 | E7 | Amaj7 -> Dmaj7 | G#m7b5 -> C#7 (Circle of Fifths!)
    p5 = patterns[5]
    _driving_beat_bar(p5, 0,  variant=0, clap_layer=True)
    _driving_beat_bar(p5, 16, variant=3, clap_layer=True)
    _driving_beat_bar(p5, 32, variant=1, clap_layer=True)
    _fill_bar(p5, 48, "chorus_lift")
    _bass_octave_bar(p5, 0,  "B-1", "B-2", sub_note="B-1")
    _bass_octave_bar(p5, 16, "E-2", "E-3", sub_note="E-2",
                     walk_notes=[(12, "E-2", 48, True), (14, "F#2", 58, False), (15, "G#2", 60, False)])
    _bass_octave_bar(p5, 32, "A-1", "A-2", sub_note="A-1",
                     walk_notes=[(8, "D-2", 48, True), (10, "D-3", 62, False), (11, "A-2", 54, False),
                                 (12, "D-2", 48, True), (14, "B-1", 58, False), (15, "A-1", 58, False)])
    p5.off(48, 4)
    _bass_octave_bar(p5, 48, "G#1", "G#2",
                     walk_notes=[(8, "C#2", 56, True), (10, "C#3", 62, False), (12, "C#2", 58, False),
                                 (13, "B-1", 58, False), (14, "C#2", 60, False), (15, "E#2", 64, False)])

    # =========================================================================
    # SECTION III: ANTHEMIC CHORUS ("KEYGEN OVERDRIVE") (Patterns 6..9, Bars 25..40)
    # =========================================================================
    # Pat 6: Dmaj7 | E | C#m7 | F#m -> E
    p6 = patterns[6]
    _driving_beat_bar(p6, 0,  variant=3, clap_layer=True, crash=True)
    _driving_beat_bar(p6, 16, variant=1, clap_layer=True)
    _driving_beat_bar(p6, 32, variant=3, clap_layer=True)
    _driving_beat_bar(p6, 48, variant=2, clap_layer=True)
    _bass_octave_bar(p6, 0,  "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p6, 16, "E-2", "E-3", sub_note="E-2")
    _bass_octave_bar(p6, 32, "C#2", "C#3", sub_note="C#2")
    _bass_octave_bar(p6, 48, "F#1", "F#2", sub_note="F#1",
                     walk_notes=[(12, "E-2", 50, True), (14, "E-3", 62, False), (15, "C#2", 58, False)])

    # Pat 7: Dmaj7 | E/G# | A -> E/G# | F#m -> C#/E#
    p7 = patterns[7]
    _driving_beat_bar(p7, 0,  variant=3, clap_layer=True)
    _driving_beat_bar(p7, 16, variant=1, clap_layer=True)
    _driving_beat_bar(p7, 32, variant=2, clap_layer=True)
    _fill_bar(p7, 48, "mid_tom")
    _bass_octave_bar(p7, 0,  "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p7, 16, "G#1", "G#2", sub_note="G#1")
    _bass_octave_bar(p7, 32, "A-1", "A-2", sub_note="A-1",
                     walk_notes=[(8, "G#1", 48, True), (10, "G#2", 62, False), (11, "E-2", 56, False),
                                 (12, "G#1", 48, True), (14, "G#2", 62, False), (15, "E-2", 58, False)])
    _bass_octave_bar(p7, 48, "F#1", "F#2", sub_note="F#1",
                     walk_notes=[(8, "E#2", 54, True), (10, "C#3", 62, False), (12, "C#2", 58, False),
                                 (14, "D-2", 60, False), (15, "D#2", 60, False)])

    # Pat 8: Dmaj7 | C#7/E# | F#m -> F#m/E | B7/D# (Dorian spotlight!)
    p8 = patterns[8]
    _driving_beat_bar(p8, 0,  variant=3, clap_layer=True, crash=True)
    _driving_beat_bar(p8, 16, variant=1, clap_layer=True)
    _driving_beat_bar(p8, 32, variant=3, clap_layer=True)
    _driving_beat_bar(p8, 48, variant=2, clap_layer=True)
    _bass_octave_bar(p8, 0,  "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p8, 16, "E#2", "C#3", sub_note="C#2")
    _bass_octave_bar(p8, 32, "F#1", "F#2", sub_note="F#1",
                     walk_notes=[(8, "E-2", 48, True), (10, "E-3", 62, False), (12, "E-2", 48, True), (14, "E-3", 62, False), (15, "E-2", 56, False)])
    _bass_octave_bar(p8, 48, "D#2", "B-2", sub_note="B-1",
                     walk_notes=[(12, "D#2", 50, True), (14, "B-2", 62, False), (15, "C#2", 58, False)])

    # Pat 9: Bm7 | C#m7 -> Dmaj7 | E -> C#7/E# | F#m (Stop-Time Break!)
    p9 = patterns[9]
    _driving_beat_bar(p9, 0,  variant=0, clap_layer=True)
    _driving_beat_bar(p9, 16, variant=1, clap_layer=True)
    _driving_beat_bar(p9, 32, variant=3, clap_layer=True)
    _fill_bar(p9, 48, "break_stop")
    _bass_octave_bar(p9, 0,  "B-1", "B-2", sub_note="B-1")
    _bass_octave_bar(p9, 16, "C#2", "C#3", sub_note="C#2",
                     walk_notes=[(8, "D-2", 48, True), (10, "D-3", 62, False), (12, "D-2", 48, True), (14, "D-3", 62, False), (15, "C#2", 58, False)])
    _bass_octave_bar(p9, 32, "E-2", "E-3", sub_note="E-2",
                     walk_notes=[(8, "E#2", 50, True), (10, "C#3", 62, False), (12, "E#2", 52, True), (14, "C#3", 64, False), (15, "E#2", 60, False)])
    # Bar 40 stop-time bass hit on beat 3 (row 56) then clean silence!
    p9.set(48, 3, note="F#1", inst=I_BASS, vol=48, fx=0x9, param=0x10)
    p9.set(50, 3, note="F#2", inst=I_BASS, vol=60)
    p9.set(52, 3, note="F#1", inst=I_BASS, vol=50)
    p9.set(54, 3, note="C#2", inst=I_BASS, vol=56)
    p9.set(56, 3, note="F#2", inst=I_BASS, vol=64)
    p9.set(56, 4, note="F#1", inst=I_SUB,  vol=58)
    p9.off(58, 3)
    p9.off(58, 4)

    # =========================================================================
    # SECTION IV: CRYSTALLINE BREAKDOWN & BAROQUE SOLO BUILD (Pats 10..11, Bars 41..48)
    # =========================================================================
    # Pat 10: Atmospheric music-box & velvet sub-bass breathing space!
    p10 = patterns[10]
    p10.set(0, 2, note="C-4", inst=I_CRASH, vol=42)
    for r0 in [0, 16, 32, 48]:
        for pos in (4, 12):
            if r0 >= 16:
                p10.set(r0 + pos, 2, note="C-4", inst=I_HATC, vol=24)
        if r0 >= 32:
            p10.set(r0 + 12, 1, note="C-4", inst=I_CLAP, vol=30)
            p10.set(r0 + 8,  2, note="C-4", inst=I_HATC, vol=22)
    # Velvet sustained Sub-Bass only (Ch 3 rests for dramatic textural contrast!)
    for r0, sn in [(0, "F#1"), (16, "D-2"), (32, "B-1"), (48, "C#2")]:
        p10.set(r0, 4, note=sn, inst=I_SUB, vol=48)
        p10.set(r0 + 14, 4, fx=0xA, param=0x02)
    p10.set(56, 4, note="E#2", inst=I_SUB, vol=46)

    # Pat 11: Baroque Solo Acceleration Build (8th kicks -> 16th kicks -> massive 32nd roll!)
    p11 = patterns[11]
    _hat_16th_bar(p11, 0,  open_offbeats=False, crash_start=True,  intensity=0.78)
    _hat_16th_bar(p11, 16, open_offbeats=True,  crash_start=False, intensity=0.88)
    _hat_16th_bar(p11, 32, open_offbeats=True,  crash_start=False, intensity=0.96)
    # Bar 45: 4-on-floor kick; Bar 46: 8th kicks; Bar 47: 8th kicks + 8th snares; Bar 48: 16th/32nd eruption!
    for pos in (0, 4, 8, 12):
        p11.set(pos, 0, note="C-4", inst=I_KICK, vol=50)
    for pos in range(0, 16, 2):
        p11.set(16 + pos, 0, note="C-4", inst=I_KICK, vol=52 + pos // 2)
    p11.set(20, 1, note="C-4", inst=I_SNARE, vol=48)
    p11.set(28, 1, note="C-4", inst=I_SNARE, vol=54)
    for pos in range(0, 16, 2):
        p11.set(32 + pos, 0, note="C-4", inst=I_KICK, vol=56)
        p11.set(32 + pos, 1, note="C-4", inst=I_SNARE, vol=38 + pos)
    # Bar 48 (r0=48): Explosive 16th kick + 32nd snare + tom eruption!
    for pos in range(16):
        if pos < 12 or pos % 2 == 0:
            p11.set(48 + pos, 0, note="C-4", inst=I_KICK, vol=42 + pos // 2, fx=(0x8 if pos == 0 else None), param=(0x80 if pos == 0 else None))
        sv = 36 + int(pos * 1.9)
        fx = 0xE if pos >= 12 else None
        prm = 0x92 if pos >= 14 else (0x93 if pos >= 12 else None)
        p11.set(48 + pos, 1, note="C-4", inst=I_SNARE, vol=min(64, sv), fx=fx, param=prm)
        p11.set(48 + pos, 2, note="C-4", inst=(I_HATO if pos == 14 else I_HATC), vol=38 + pos)
    # Pat 11 Bass: Dmaj7 | Bm7 -> E7 | F#m -> D#m7b5 | D7 -> C#7
    _bass_octave_bar(p11, 0,  "D-2", "D-3", style="pulse_intro", sub_note="D-2")
    _bass_octave_bar(p11, 16, "B-1", "B-2", sub_note="B-1",
                     walk_notes=[(8, "E-2", 52, True), (10, "E-3", 60, False), (12, "E-2", 52, True), (14, "G#2", 62, False), (15, "E-2", 58, False)])
    _bass_octave_bar(p11, 32, "F#1", "F#2", sub_note="F#1",
                     walk_notes=[(8, "D#2", 54, True), (10, "D#3", 62, False), (12, "D#2", 56, True), (14, "B-2", 62, False), (15, "A-2", 60, False)])
    p11.off(48, 4)
    for pos in range(0, 8, 2):
        p11.set(48 + pos, 3, note=("D-2" if pos % 4 == 0 else "D-3"), inst=I_BASS, vol=58)
    for pos, bn in [(8, "C#2"), (10, "C#3"), (12, "C#2"), (13, "D-2"), (14, "E-2"), (15, "E#2")]:
        p11.set(48 + pos, 3, note=bn, inst=I_BASS, vol=62)

    # =========================================================================
    # SECTION V: GRAND CLIMAX CHORUS & OUTRO TURNAROUND (Pats 12..15, Bars 49..64)
    # =========================================================================
    # Pat 12: Dmaj7 | E | C#m7 -> F#7 | Bm7 -> C#7
    p12 = patterns[12]
    _driving_beat_bar(p12, 0,  variant=3, clap_layer=True, crash=True)
    _driving_beat_bar(p12, 16, variant=2, clap_layer=True)
    _driving_beat_bar(p12, 32, variant=3, clap_layer=True)
    _fill_bar(p12, 48, "mid_tom")
    _bass_octave_bar(p12, 0,  "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p12, 16, "E-2", "E-3", sub_note="E-2")
    _bass_octave_bar(p12, 32, "C#2", "C#3", sub_note="C#2",
                     walk_notes=[(8, "F#1", 50, True), (10, "F#2", 62, False), (12, "A#1", 54, True), (14, "A#2", 64, False), (15, "C#3", 60, False)])
    _bass_octave_bar(p12, 48, "B-1", "B-2", sub_note="B-1",
                     walk_notes=[(8, "C#2", 52, True), (10, "C#3", 62, False), (12, "C#2", 58, False), (14, "D-2", 60, False), (15, "E#2", 62, False)])

    # Pat 13: F#m | Dmaj7 | E | A -> C#7/E# (Dual-Theme Fusion!)
    p13 = patterns[13]
    _driving_beat_bar(p13, 0,  variant=3, clap_layer=True, crash=True)
    _driving_beat_bar(p13, 16, variant=1, clap_layer=True)
    _driving_beat_bar(p13, 32, variant=3, clap_layer=True)
    _driving_beat_bar(p13, 48, variant=2, clap_layer=True)
    _bass_octave_bar(p13, 0,  "F#1", "F#2", sub_note="F#1")
    _bass_octave_bar(p13, 16, "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p13, 32, "E-2", "E-3", sub_note="E-2")
    _bass_octave_bar(p13, 48, "A-1", "A-2", sub_note="A-1",
                     walk_notes=[(8, "E#2", 50, True), (10, "C#3", 62, False), (12, "E#2", 52, True), (14, "C#2", 62, False), (15, "E#2", 60, False)])

    # Pat 14: Dmaj7 | C#7/E# | F#m -> E | D#m7b5 -> Dmaj7 (Chromatic Climax Descent!)
    p14 = patterns[14]
    _driving_beat_bar(p14, 0,  variant=3, clap_layer=True, crash=True)
    _driving_beat_bar(p14, 16, variant=2, clap_layer=True)
    _driving_beat_bar(p14, 32, variant=3, clap_layer=True)
    _driving_beat_bar(p14, 48, variant=1, clap_layer=True)
    _bass_octave_bar(p14, 0,  "D-2", "D-3", sub_note="D-2")
    _bass_octave_bar(p14, 16, "E#2", "C#3", sub_note="C#2")
    _bass_octave_bar(p14, 32, "F#1", "F#2", sub_note="F#1",
                     walk_notes=[(8, "E-2", 50, True), (10, "E-3", 62, False), (12, "E-2", 52, True), (14, "E-3", 62, False), (15, "E-2", 58, False)])
    _bass_octave_bar(p14, 48, "D#2", "B-2", sub_note="D-2",
                     walk_notes=[(8, "D-2", 50, True), (10, "D-3", 62, False), (12, "D-2", 52, True), (14, "C#2", 60, False), (15, "C-2", 58, False)])

    # Pat 15: Bm7 | G#m7b5 | C#7sus4 | C#7(b9) -> Seamless Loop Turnaround to Pat 0!
    p15 = patterns[15]
    _driving_beat_bar(p15, 0,  variant=0, clap_layer=True)
    _driving_beat_bar(p15, 16, variant=2, clap_layer=True)
    _driving_beat_bar(p15, 32, variant=3, clap_layer=True)
    _fill_bar(p15, 48, "loop_turnaround")
    _bass_octave_bar(p15, 0,  "B-1", "B-2", sub_note="B-1")
    _bass_octave_bar(p15, 16, "G#1", "G#2", sub_note="G#1")
    _bass_octave_bar(p15, 32, "C#2", "C#3", sub_note="C#2")
    # Bar 64 dominant turnaround bass walk leading directly into F#1 on Pat 0 Row 0!
    _bass_octave_bar(p15, 48, "C#2", "C#3", sub_note="C#2",
                     walk_notes=[(8, "C#2", 58, False), (10, "D-2", 60, False), (12, "E#2", 62, False),
                                 (14, "C#2", 62, False), (15, "E#2", 64, False)])
    p15.off(62, 4)  # Sub releases cleanly 2 rows before wrap so Pat 0 Row 0 F#1 sub enters fresh!
