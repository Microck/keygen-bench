"""
Assembles the complete 16-pattern (64-bar, ~1m44s) keygen tracker module
'COBALT KEYRING' into /workspace/submission/tune.xm, plus a 2-pass loop-seam
verification module in /workspace/test/loop_check.xm.
"""
import os
import sys

sys.path.insert(0, '/workspace/src')
from xm_builder import XMModule, OFF, VOL, PANNING
from instruments import build_all_instruments
from harmony_and_grooves import (
    I_KICK, I_SNARE, I_CLAP, I_TOM, I_BASS, I_SUB,
    I_PWM, I_SAW, I_HARM, I_SID, I_HARPSI, I_BELL, I_PAD,
    init_row0_channel_pans, write_chord_pads, write_sid_arp,
    write_harpsi_arp, write_bassline, write_drums
)
from melodies import (
    write_lead_events,
    INTRO_P0_LEAD, INTRO_P0_BELL, INTRO_P1_LEAD,
    THEME_A1_LEAD, THEME_A1_COUNTER, THEME_A2_LEAD, THEME_A2_COUNTER,
    THEME_A3_LEAD, THEME_A3_HARM, THEME_A4_LEAD, THEME_A4_HARM,
    CHORUS_B1_LEAD, CHORUS_B2_LEAD, CHORUS_B3_LEAD, CHORUS_B3_BELL_OBLIGATO, CHORUS_B4_LEAD,
    BAROQUE_CANON_VOICE1, BAROQUE_CANON_VOICE2, BUILD_P11_LEAD,
    SOLO_P12_LEAD, FINALE_P13_DESCANT, FINALE_P14_LEAD, FINALE_P14_HARM,
    OUTRO_P15_LEAD,
)


def create_module(unroll_loop_test=False):
    mod = XMModule(name="COBALT KEYRING", channels=14, bpm=148, speed=3, restart_pos=0)
    for inst in build_all_instruments():
        mod.add_instrument(inst)

    pats = [mod.add_pattern(rows=128)[1] for _ in range(16)]

    # Always initialize channel pans & tempo on Pattern 0 Row 0
    init_row0_channel_pans(pats[0], set_tempo=True)

    # -------------------------------------------------------------------------
    # PAT 0 (Bars 1-4): CRACKTRO FANFARE INTRO A
    # -------------------------------------------------------------------------
    segs_p0 = [(0, 32, 'F#m'), (32, 64, 'Dmaj7'), (64, 96, 'E'), (96, 128, 'C#7/E#')]
    write_drums(pats[0], groove='fanfare_intro', crash_rows=(0,), fill_end='standard')
    write_bassline(pats[0], segs_p0, style='intro_pulse', walk_overrides={
        28: ('E-2', I_BASS, 56), 60: ('D#2', I_BASS, 56),
        92: ('E-2', I_BASS, 58), 124: ('C#2', I_BASS, 62),
    })
    write_chord_pads(pats[0], segs_p0, style='stabs', vol_base=42)
    write_sid_arp(pats[0], segs_p0, mode='shimmer', vol_base=40)
    write_harpsi_arp(pats[0], segs_p0, pattern_type='baroque16', vol_base=46)
    write_lead_events(pats[0], 5, I_PWM, INTRO_P0_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.35)
    write_lead_events(pats[0], 13, I_BELL, INTRO_P0_BELL)

    # -------------------------------------------------------------------------
    # PAT 1 (Bars 5-8): CRACKTRO FANFARE INTRO B (Groove Launch!)
    # -------------------------------------------------------------------------
    segs_p1 = [(0, 32, 'F#m'), (32, 64, 'Bm7'), (64, 96, 'G#m7b5'), (96, 112, 'C#7sus4'), (112, 128, 'C#7')]
    write_drums(pats[1], groove='drive', crash_rows=(0,), fill_end='snare_blitz')
    write_bassline(pats[1], segs_p1, style='octave_drive', walk_overrides={
        28: ('A-2', I_BASS, 58), 30: ('A#2', I_BASS, 58),
        60: ('A-2', I_BASS, 58), 120: ('C#2', I_BASS, 62), 124: ('E#2', I_BASS, 63),
    })
    write_chord_pads(pats[1], segs_p1, style='pulsing', vol_base=40)
    write_sid_arp(pats[1], segs_p1, mode='gallop', vol_base=42)
    write_harpsi_arp(pats[1], segs_p1, pattern_type='rising16', vol_base=45)
    write_lead_events(pats[1], 5, I_PWM, INTRO_P1_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.34, max_echo_row=120)

    # -------------------------------------------------------------------------
    # PAT 2 (Bars 9-12): THEME A1 — "RAZOR VELOCITY"
    # -------------------------------------------------------------------------
    segs_p2 = [(0, 32, 'F#m'), (32, 64, 'D'), (64, 96, 'E'), (96, 112, 'F#m'), (112, 128, 'E/G#')]
    write_drums(pats[2], groove='drive', crash_rows=(0,), fill_end=None)
    write_bassline(pats[2], segs_p2, style='octave_drive', walk_overrides={
        30: ('E-2', I_BASS, 56), 62: ('D#2', I_BASS, 56), 124: ('G#2', I_BASS, 60),
    })
    write_chord_pads(pats[2], segs_p2, style='pulsing', vol_base=38)
    write_sid_arp(pats[2], segs_p2, mode='shimmer', vol_base=42)
    write_harpsi_arp(pats[2], segs_p2, pattern_type='baroque16', vol_base=44)
    write_lead_events(pats[2], 5, I_PWM, THEME_A1_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.35)
    write_lead_events(pats[2], 7, I_BELL, THEME_A1_COUNTER)

    # -------------------------------------------------------------------------
    # PAT 3 (Bars 13-16): THEME A2 — Chromatic Walk & Secondary Dominants
    # -------------------------------------------------------------------------
    segs_p3 = [(0, 32, 'A'), (32, 64, 'Bm7'), (64, 96, 'G#dim7'), (96, 128, 'C#7')]
    write_drums(pats[3], groove='drive', crash_rows=(), fill_end='standard')
    write_bassline(pats[3], segs_p3, style='octave_drive', walk_overrides={
        28: ('A-2', I_BASS, 58), 30: ('A#2', I_BASS, 60),  # Chromatic A -> A# -> B!
        60: ('A-2', I_BASS, 58), 92: ('G#2', I_BASS, 60),
        120: ('C#3', I_BASS, 62), 124: ('G#2', I_BASS, 62),
    })
    write_chord_pads(pats[3], segs_p3, style='pulsing', vol_base=39)
    write_sid_arp(pats[3], segs_p3, mode='shimmer', vol_base=42)
    write_harpsi_arp(pats[3], segs_p3, pattern_type='alberti', vol_base=44)
    write_lead_events(pats[3], 5, I_PWM, THEME_A2_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.35)
    write_lead_events(pats[3], 7, I_HARM, THEME_A2_COUNTER)

    # -------------------------------------------------------------------------
    # PAT 4 (Bars 17-20): THEME A3 — Twin-Lead 3rd/6th Harmony Lift!
    # -------------------------------------------------------------------------
    segs_p4 = [(0, 32, 'F#m'), (32, 48, 'Dmaj7'), (48, 64, 'D'), (64, 96, 'B7/D#'), (96, 112, 'E'), (112, 128, 'E7/G#' if 'E7/G#' in {} else 'E/G#')]
    write_drums(pats[4], groove='drive', crash_rows=(0,), fill_end=None)
    write_bassline(pats[4], segs_p4, style='octave_drive', walk_overrides={
        60: ('D-2', I_BASS, 58), 62: ('D#2', I_BASS, 60),
        124: ('G#2', I_BASS, 62),
    })
    write_chord_pads(pats[4], segs_p4, style='sustain', vol_base=38)
    write_sid_arp(pats[4], segs_p4, mode='gallop', vol_base=43)
    write_harpsi_arp(pats[4], segs_p4, pattern_type='baroque16', vol_base=45)
    write_lead_events(pats[4], 5, I_PWM, THEME_A3_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.34)
    write_lead_events(pats[4], 7, I_HARM, THEME_A3_HARM)

    # -------------------------------------------------------------------------
    # PAT 5 (Bars 21-24): THEME A4 — Cadence Launch into Anthem Chorus!
    # -------------------------------------------------------------------------
    segs_p5 = [(0, 32, 'A'), (32, 64, 'F#7/A#'), (64, 96, 'Bm7'), (96, 112, 'E7sus4'), (112, 128, 'E7')]
    write_drums(pats[5], groove='drive', crash_rows=(), fill_end='snare_blitz')
    write_bassline(pats[5], segs_p5, style='octave_drive', walk_overrides={
        30: ('A#2', I_BASS, 60), 62: ('B-2', I_BASS, 60),
        112: ('E-2', I_BASS, 63), 120: ('G#2', I_BASS, 62), 124: ('B-2', I_BASS, 63),
    })
    write_chord_pads(pats[5], segs_p5, style='sustain', vol_base=40)
    write_sid_arp(pats[5], segs_p5, mode='gallop', vol_base=44)
    write_harpsi_arp(pats[5], segs_p5, pattern_type='rising16', vol_base=46)
    write_lead_events(pats[5], 5, I_PWM, THEME_A4_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.34, max_echo_row=120)
    write_lead_events(pats[5], 7, I_HARM, THEME_A4_HARM)

    # -------------------------------------------------------------------------
    # PAT 6 (Bars 25-28): THEME B1 — "SKYLINE ANTHEM CHORUS" (Hyperion Supersaw!)
    # -------------------------------------------------------------------------
    segs_p6 = [(0, 32, 'Dmaj7'), (32, 64, 'E'), (64, 96, 'C#m7'), (96, 128, 'F#m7')]
    write_drums(pats[6], groove='chorus', crash_rows=(0,), fill_end=None)
    write_bassline(pats[6], segs_p6, style='chorus_melodic')
    write_chord_pads(pats[6], segs_p6, style='sustain', vol_base=43)
    write_sid_arp(pats[6], segs_p6, mode='sparkle_high', vol_base=41)
    write_harpsi_arp(pats[6], segs_p6, pattern_type='rising16', vol_base=46)
    write_lead_events(pats[6], 5, I_SAW, CHORUS_B1_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.36)
    write_lead_events(pats[6], 13, I_BELL, [(0, 12, 'A-5', 46), (32, 12, 'B-5', 46), (64, 12, 'G#5', 46), (96, 12, 'A-5', 48)])

    # -------------------------------------------------------------------------
    # PAT 7 (Bars 29-32): THEME B2 — Mid-Chorus Harmonic Acceleration
    # -------------------------------------------------------------------------
    segs_p7 = [(0, 32, 'Bm7'), (32, 64, 'E7'), (64, 80, 'Amaj7'), (80, 96, 'Dmaj7'), (96, 112, 'G#m7b5'), (112, 128, 'C#7')]
    write_drums(pats[7], groove='chorus', crash_rows=(), fill_end='standard')
    write_bassline(pats[7], segs_p7, style='chorus_melodic', walk_overrides={
        112: ('C#2', I_BASS, 63), 120: ('E#2', I_BASS, 62), 124: ('G#2', I_BASS, 63),
    })
    write_chord_pads(pats[7], segs_p7, style='sustain', vol_base=43)
    write_sid_arp(pats[7], segs_p7, mode='sparkle_high', vol_base=41)
    write_harpsi_arp(pats[7], segs_p7, pattern_type='alberti', vol_base=46)
    write_lead_events(pats[7], 5, I_SAW, CHORUS_B2_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.36)

    # -------------------------------------------------------------------------
    # PAT 8 (Bars 33-36): THEME B3 — High Chorus Lift + Bell Obligato
    # -------------------------------------------------------------------------
    segs_p8 = [(0, 32, 'Dmaj7'), (32, 64, 'E/D'), (64, 96, 'C#m7'), (96, 128, 'F#7')]
    write_drums(pats[8], groove='chorus', crash_rows=(0,), fill_end=None)
    write_bassline(pats[8], segs_p8, style='chorus_melodic')
    write_chord_pads(pats[8], segs_p8, style='sustain', vol_base=44)
    write_sid_arp(pats[8], segs_p8, mode='sparkle_high', vol_base=42)
    write_harpsi_arp(pats[8], segs_p8, pattern_type='baroque16', vol_base=47)
    write_lead_events(pats[8], 5, I_SAW, CHORUS_B3_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.36)
    write_lead_events(pats[8], 7, I_BELL, CHORUS_B3_BELL_OBLIGATO)

    # -------------------------------------------------------------------------
    # PAT 9 (Bars 37-40): THEME B4 — Minor-iv (Dm6) Emotional Resolution -> Breakdown
    # -------------------------------------------------------------------------
    segs_p9 = [(0, 32, 'Bm7'), (32, 64, 'Dm6'), (64, 96, 'F#m/C#'), (96, 112, 'C#7'), (112, 128, 'F#m')]
    write_drums(pats[9], groove='chorus', crash_rows=(32,), fill_end='standard')
    write_bassline(pats[9], segs_p9, style='chorus_melodic')
    write_chord_pads(pats[9], segs_p9, style='sustain', vol_base=43)
    write_sid_arp(pats[9], segs_p9, mode='shimmer', vol_base=40)
    write_harpsi_arp(pats[9], segs_p9, pattern_type='alberti', vol_base=45)
    write_lead_events(pats[9], 5, I_SAW, CHORUS_B4_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.35, max_echo_row=124)

    # -------------------------------------------------------------------------
    # PAT 10 (Bars 41-44): SECTION IV — BAROQUE SILICON BREAKDOWN (2-Voice Canon!)
    # -------------------------------------------------------------------------
    segs_p10 = [(0, 32, 'F#m'), (32, 64, 'E'), (64, 96, 'Dmaj7'), (96, 128, 'C#7')]
    write_drums(pats[10], groove='breakdown', crash_rows=(0,), fill_end=None)
    write_bassline(pats[10], segs_p10, style='sub_lament')
    write_chord_pads(pats[10], segs_p10, style='sustain', vol_base=26)
    # Two-voice baroque counterpoint: Harpsichord on Ch 9 (Right) + Sync/SID on Ch 7 (Center-Right) + soft SID shimmer on Ch 8 (Left)!
    write_sid_arp(pats[10], segs_p10, mode='shimmer', vol_base=27)
    write_lead_events(pats[10], 9, I_HARPSI, BAROQUE_CANON_VOICE1, echo_ch=6, echo_delay=8, echo_scale=0.32)
    write_lead_events(pats[10], 7, I_HARM, BAROQUE_CANON_VOICE2)
    write_lead_events(pats[10], 13, I_BELL, [(0, 16, 'F#5', 38), (32, 16, 'G#5', 38), (64, 16, 'A-5', 38), (96, 16, 'E#5', 40)])

    # -------------------------------------------------------------------------
    # PAT 11 (Bars 45-48): RISER & ACCELERATING BUILD INTO SOLO!
    # -------------------------------------------------------------------------
    segs_p11 = [(0, 32, 'Bm7'), (32, 64, 'C#m7'), (64, 80, 'Dmaj7'), (80, 96, 'D#dim7'), (96, 112, 'C#7sus4'), (112, 128, 'C#7')]
    write_drums(pats[11], groove='build_riser', crash_rows=(), fill_end=None)
    write_bassline(pats[11], segs_p11, style='octave_drive')
    write_chord_pads(pats[11], segs_p11, style='pulsing', vol_base=40)
    write_sid_arp(pats[11], segs_p11, mode='gallop', vol_base=43)
    write_harpsi_arp(pats[11], segs_p11, pattern_type='rising16', vol_base=47)
    write_lead_events(pats[11], 5, I_PWM, BUILD_P11_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.32, max_echo_row=118)

    # -------------------------------------------------------------------------
    # PAT 12 (Bars 49-52): SECTION V — OVERCLOCK VIRTUOSO SHRED SOLO!
    # -------------------------------------------------------------------------
    segs_p12 = [(0, 32, 'D'), (32, 64, 'E'), (64, 96, 'Fdim7'), (96, 128, 'F#m')]
    write_drums(pats[12], groove='solo', crash_rows=(0, 96), fill_end='snare_blitz')
    write_bassline(pats[12], segs_p12, style='octave_drive', walk_overrides={
        60: ('E-2', I_BASS, 60), 62: ('F-2', I_BASS, 62),
        92: ('E#2', I_BASS, 63),
    })
    write_chord_pads(pats[12], segs_p12, style='pulsing', vol_base=42)
    write_sid_arp(pats[12], segs_p12, mode='gallop', vol_base=44)
    write_harpsi_arp(pats[12], segs_p12, pattern_type='baroque16', vol_base=46)
    write_lead_events(pats[12], 5, I_PWM, SOLO_P12_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.33)
    write_lead_events(pats[12], 13, I_BELL, [(0, 8, 'A-5', 48), (32, 8, 'B-5', 48), (64, 8, 'B-5', 50), (96, 12, 'C#6', 52)])

    # -------------------------------------------------------------------------
    # PAT 13 (Bars 53-56): GRAND DUAL-THEME REPRISE (Theme A + Soaring Descant!)
    # -------------------------------------------------------------------------
    segs_p13 = [(0, 32, 'F#m'), (32, 48, 'Dmaj7'), (48, 64, 'D'), (64, 96, 'E'), (96, 112, 'A'), (112, 128, 'C#7/E#')]
    write_drums(pats[13], groove='solo', crash_rows=(0,), fill_end=None)
    write_bassline(pats[13], segs_p13, style='chorus_melodic')
    write_chord_pads(pats[13], segs_p13, style='sustain', vol_base=43)
    write_sid_arp(pats[13], segs_p13, mode='sparkle_high', vol_base=43)
    write_harpsi_arp(pats[13], segs_p13, pattern_type='rising16', vol_base=47)
    write_lead_events(pats[13], 5, I_SAW, THEME_A1_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.35)
    write_lead_events(pats[13], 7, I_HARM, FINALE_P13_DESCANT)

    # -------------------------------------------------------------------------
    # PAT 14 (Bars 57-60): TRIUMPHANT CLIMAX CADENCE (Twin-Lead Supersaw + Sync!)
    # -------------------------------------------------------------------------
    segs_p14 = [(0, 32, 'Bm7'), (32, 64, 'E7'), (64, 80, 'C#m7'), (80, 96, 'F#7'), (96, 112, 'Bm7'), (112, 128, 'C#7')]
    write_drums(pats[14], groove='chorus', crash_rows=(0, 64), fill_end='standard')
    write_bassline(pats[14], segs_p14, style='chorus_melodic')
    write_chord_pads(pats[14], segs_p14, style='sustain', vol_base=44)
    write_sid_arp(pats[14], segs_p14, mode='sparkle_high', vol_base=43)
    write_harpsi_arp(pats[14], segs_p14, pattern_type='baroque16', vol_base=47)
    write_lead_events(pats[14], 5, I_SAW, FINALE_P14_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.35)
    write_lead_events(pats[14], 7, I_HARM, FINALE_P14_HARM)

    # -------------------------------------------------------------------------
    # PAT 15 (Bars 61-64): OUTRO CODA & SEAMLESS LOOP TURNAROUND -> PAT 0!
    # -------------------------------------------------------------------------
    segs_p15 = [(0, 32, 'F#m'), (32, 64, 'E'), (64, 72, 'Dmaj7'), (72, 96, 'D'), (96, 112, 'C#7sus4'), (112, 128, 'C#7')]
    write_drums(pats[15], groove='drive', crash_rows=(0,), fill_end='turnaround_loop')
    write_bassline(pats[15], segs_p15, style='octave_drive', walk_overrides={
        112: ('C#2', I_BASS, 64), 116: ('C#3', I_BASS, 58),
        120: ('G#2', I_BASS, 62), 124: ('E#2', I_BASS, 64),
        127: ('OFF', 0, 0),
    })
    # Ensure bass releases cleanly on row 127 right before Row 0's F#2 tonic!
    pats[15].set(127, 4, note=OFF)

    # Pads taper cleanly by row 124 so loop seam into Pat 0 stabs has zero overhang
    write_chord_pads(pats[15], [(0, 32, 'F#m'), (32, 64, 'E'), (64, 72, 'Dmaj7'), (72, 96, 'D'), (96, 124, 'C#7')], style='stabs', vol_base=42)
    write_sid_arp(pats[15], [(0, 32, 'F#m'), (32, 64, 'E'), (64, 72, 'Dmaj7'), (72, 96, 'D'), (96, 124, 'C#7')], mode='shimmer', vol_base=41)
    pats[15].set(124, 8, note=OFF)
    write_harpsi_arp(pats[15], [(0, 32, 'F#m'), (32, 64, 'E'), (64, 72, 'Dmaj7'), (72, 96, 'D'), (96, 120, 'C#7')], pattern_type='baroque16', vol_base=45)
    pats[15].set(124, 9, note=OFF)
    write_lead_events(pats[15], 5, I_PWM, OUTRO_P15_LEAD, echo_ch=6, echo_delay=6, echo_scale=0.33, max_echo_row=120)
    # Ensure auxiliary melodic channels are cleanly released before row 0 wrap
    for ch_clean in (6, 7, 10, 11, 12, 13):
        pats[15].set(126, ch_clean, note=OFF)

    if not unroll_loop_test:
        mod.orders = list(range(16))
    else:
        # Render [14, 15, 0, 1] to inspect the exact Order 15 -> Order 0 loop boundary in FT2!
        mod.orders = [14, 15, 0, 1]
    return mod


if __name__ == '__main__':
    os.makedirs('/workspace/submission', exist_ok=True)
    os.makedirs('/workspace/test', exist_ok=True)

    main_mod = create_module(unroll_loop_test=False)
    xm_path = '/workspace/submission/tune.xm'
    main_mod.save(xm_path)
    print(f"Saved {xm_path} ({os.path.getsize(xm_path) / 1024:.1f} KiB, {len(main_mod.orders)} orders)")

    loop_mod = create_module(unroll_loop_test=True)
    loop_path = '/workspace/test/loop_seam.xm'
    loop_mod.save(loop_path)
    print(f"Saved {loop_path} for loop seam verification")
