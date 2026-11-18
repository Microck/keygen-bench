"""
COBALT KEYGEN — Original 16-Channel FastTracker II Keygen Tune (v2: Wide Stereo & Studio Mix)
Key: D minor (with F major heroic chorus & jazzy circle-of-fifths solo)
Tempo: 142 BPM, Speed 6 (56.8 Hz tick rate, 64 rows = 4 bars)
Seamless loop from Order 14 back to Restart Position (Order 1).
"""
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xm_writer import XMModule, XMPattern, KEY_OFF
from instruments import build_instruments

# 21 Stereo-Crafted Instrument IDs (1-based)
INS_KICK      = 1
INS_SNARE     = 2
INS_CLAP      = 3
INS_HATC      = 4
INS_HATO      = 5
INS_CRASH     = 6
INS_TOM       = 7
INS_PWMLEAD   = 8
INS_LEADECHO  = 9
INS_THIN      = 10
INS_HARMECHO  = 11
INS_SOLO      = 12
INS_SOLOECHO  = 13
INS_BASS      = 14
INS_SUBTRI    = 15
INS_ARPL      = 16
INS_ARPR      = 17
INS_PADL      = 18
INS_PADR      = 19
INS_BELL      = 20
INS_FX        = 21

# 16-Channel Assignments
CH_KICK       = 0
CH_SNARE      = 1
CH_HAT        = 2
CH_PERC       = 3   # Crash / Toms / FX
CH_BASS       = 4
CH_LEAD       = 5
CH_LEAD_ECHO  = 6
CH_HARM       = 7
CH_HARM_ECHO  = 8
CH_ARP_L      = 9
CH_ARP_R      = 10
CH_BELL       = 11
CH_PAD_1      = 12  # Wide Left (INS_PADL)
CH_PAD_2      = 13  # Wide Right (INS_PADR)
CH_PAD_3      = 14  # Center-L/R blend (INS_PADL/R lower vol)
CH_CLAP       = 15

# Sustaining (looped) instruments that must never accidentally drone across section boundaries
SUSTAINING_INS = {
    INS_PWMLEAD, INS_LEADECHO, INS_THIN, INS_HARMECHO,
    INS_SOLO, INS_SOLOECHO, INS_BASS, INS_SUBTRI,
    INS_ARPL, INS_ARPR, INS_PADL, INS_PADR,
}

# --- Musical Helper Functions ---

def write_melody(pat, ch, ins, events, base_vol=48, echo_ch=None, echo_ins=None,
                 echo_vol_ratio=0.34, echo_delay=3):
    """
    Write expressive melody events with optional stereo echo using dedicated echo instrument.
    Each event: (row, note, dur[, kwargs])
    """
    if echo_ins is None:
        if ins == INS_PWMLEAD:
            echo_ins = INS_LEADECHO
        elif ins == INS_SOLO:
            echo_ins = INS_SOLOECHO
        elif ins in (INS_THIN, INS_BELL):
            echo_ins = INS_HARMECHO
        else:
            echo_ins = ins

    for ev in events:
        if len(ev) == 3:
            row, note, dur = ev
            kw = {}
        else:
            row, note, dur, kw = ev
        if row >= pat.rows:
            continue
        vol = kw.get('vol', base_vol)
        eff = kw.get('eff', None)
        param = kw.get('param', None)
        if kw.get('porta', False):
            eff = 0x03
            param = kw.get('porta_speed', 0x28)
            use_ins = kw.get('retrig_ins', None)
        else:
            use_ins = ins

        pat.set(row, ch, note=note, ins=use_ins, vol=vol, eff=eff, param=param)

        vib = kw.get('vib', None)
        if vib is not None and dur is not None and dur >= 4:
            for vr in range(row + 2, min(pat.rows, row + dur)):
                if pat.data[vr][ch][0] == 0:
                    pat.set(vr, ch, eff=0x04, param=vib)

        if kw.get('keyoff', True) and dur is not None:
            end_r = row + dur
            if 0 <= end_r < pat.rows and pat.data[end_r][ch][0] == 0:
                pat.set(end_r, ch, note=KEY_OFF)

        if echo_ch is not None and not kw.get('no_echo', False):
            er = row + echo_delay
            if 0 <= er < pat.rows:
                evol = max(8, int(round(vol * echo_vol_ratio)))
                pat.set(er, echo_ch, note=note, ins=echo_ins, vol=evol)
                if dur is not None:
                    eend = er + max(1, dur - 1)
                    if 0 <= eend < pat.rows and pat.data[eend][echo_ch][0] == 0:
                        pat.set(eend, echo_ch, note=KEY_OFF)

def write_arp_bar(pat, bar_idx, root_note, arp_xy, ch=CH_ARP_L, ins=None,
                  vol=34, rhythm="16th_pulse", start_row_off=0, length=16):
    """Write classic FastTracker II 0xy chiptune chord arpeggios with true L/R instruments."""
    if ins is None:
        ins = INS_ARPL if ch == CH_ARP_L else INS_ARPR
    r0 = bar_idx * 16 + start_row_off
    for i in range(length):
        r = r0 + i
        if r >= pat.rows:
            break
        if rhythm == "16th_pulse":
            if i % 4 == 0:
                pat.set(r, ch, note=root_note, ins=ins, vol=vol, eff=0x00, param=arp_xy)
            elif i % 2 == 0:
                pat.set(r, ch, note=root_note, ins=ins, vol=int(vol * 0.78), eff=0x00, param=arp_xy)
            else:
                pat.set(r, ch, eff=0x00, param=arp_xy)
        elif rhythm == "8th_bounce":
            if i % 2 == 0:
                v = vol if (i % 4 == 0) else int(vol * 0.80)
                pat.set(r, ch, note=root_note, ins=ins, vol=v, eff=0x00, param=arp_xy)
            else:
                pat.set(r, ch, eff=0x00, param=arp_xy)
        elif rhythm == "sustain":
            if i == 0:
                pat.set(r, ch, note=root_note, ins=ins, vol=vol, eff=0x00, param=arp_xy)
            else:
                pat.set(r, ch, eff=0x00, param=arp_xy)
        elif rhythm == "offbeat":
            if i in (2, 6, 10, 14):
                pat.set(r, ch, note=root_note, ins=ins, vol=vol, eff=0x00, param=arp_xy)
            elif i in (3, 7, 11, 15):
                pat.set(r, ch, eff=0x00, param=arp_xy)
            elif i in (0, 4, 8, 12):
                pat.set(r, ch, note=KEY_OFF)
        elif rhythm == "sparkle_16":
            contour = [1.0, 0.56, 0.84, 0.60]
            v = int(vol * contour[i % 4])
            pat.set(r, ch, note=root_note, ins=ins, vol=v, eff=0x00, param=arp_xy)

def write_pad_chord(pat, start_row, dur, notes3, vol=22, keyoff=True, swell=False):
    """Write lush wide-stereo 3-voice chord pad (L, R, subtle L/R middle) in clean mid-register."""
    ch_ins = [(CH_PAD_1, INS_PADL, vol), (CH_PAD_2, INS_PADR, vol), (CH_PAD_3, INS_PADL, int(vol * 0.72))]
    for (ch, ins, v), nt in zip(ch_ins, notes3):
        if nt is not None and start_row < pat.rows:
            if swell:
                # Start soft and swell in with A20 volume slide up!
                pat.set(start_row, ch, note=nt, ins=ins, vol=max(6, v // 2), eff=0x0A, param=0x20)
                for sr in range(start_row + 1, min(pat.rows, start_row + 4)):
                    pat.set(sr, ch, eff=0x0A, param=0x10)
                if ch == CH_PAD_3:
                    pass
            else:
                pat.set(start_row, ch, note=nt, ins=ins, vol=v)
                if ch == CH_PAD_3:
                    pat.set_pan(start_row, ch, 128) # Center 3rd voice!
            if keyoff and start_row + dur < pat.rows:
                pat.set(start_row + dur, ch, note=KEY_OFF)

def write_bass_bar(pat, bar_idx, root_lo, root_hi, fifth_lo=None, style="keygen_oct",
                   ins=INS_BASS, vol=50, start_off=0, length=16, walk_end=None, oct_slide=False):
    """Write driving, bouncy keygen bass patterns with optional octave portamento slide."""
    r0 = bar_idx * 16 + start_off
    f5 = fifth_lo if fifth_lo else root_hi

    if style == "keygen_oct":
        seq = [
            (0, root_lo, 1.00), (2, root_hi, 0.84), (3, root_lo, 0.88),
            (4, None, 0),       (6, root_hi, 0.90), (7, root_lo, 0.78),
            (8, root_lo, 0.98), (10, root_hi, 0.86), (11, root_lo, 0.86),
            (12, f5, 0.92),     (14, root_hi, 0.90), (15, root_lo, 0.78),
        ]
    elif style == "driving_8th":
        seq = [
            (0, root_lo, 1.00), (2, root_hi, 0.86), (4, root_lo, 0.96), (6, root_hi, 0.88),
            (8, root_lo, 0.98), (10, root_hi, 0.88), (12, f5, 0.94),   (14, root_hi, 0.88),
        ]
    elif style == "funk_slap":
        seq = [
            (0, root_lo, 1.00), (2, root_lo, 0.76), (3, root_hi, 0.92),
            (6, root_lo, 0.94), (8, None, 0),       (9, root_hi, 0.86),
            (10, root_lo, 0.92),(12, f5, 0.94),     (14, root_hi, 0.92),
        ]
    elif style == "half_8th":
        seq = [
            (0, root_lo, 1.00), (2, root_hi, 0.85), (3, root_lo, 0.85),
            (4, root_lo, 0.94), (6, root_hi, 0.88), (7, f5, 0.84),
        ]
    elif style == "sub_breathe":
        # Spacious, breathing breakdown sub-bass with gentle rest on beat 3!
        seq = [(0, root_lo, 0.95), (7, None, 0), (10, f5, 0.82), (13, None, 0), (14, root_hi, 0.78)]
    elif style == "intro_pulse":
        seq = [(i, root_lo if i % 4 == 0 else root_hi, 0.92 if i % 4 == 0 else 0.74) for i in range(0, 16, 2)]
    else:
        seq = [(0, root_lo, 1.00), (4, root_hi, 0.88), (8, root_lo, 0.96), (12, root_hi, 0.88)]

    for loc, nt, vs in seq:
        if loc >= length:
            continue
        r = r0 + loc
        if r >= pat.rows:
            continue
        if nt is None:
            pat.set(r, CH_BASS, note=KEY_OFF)
        else:
            pat.set(r, CH_BASS, note=nt, ins=ins, vol=int(round(vol * vs * 0.85)))

    if oct_slide and length >= 16 and r0 + 14 < pat.rows:
        # Classic funky octave glide on beat 4&!
        pat.set(r0 + 14, CH_BASS, note=root_hi, eff=0x03, param=0x38)

    if walk_end:
        for loc, nt in walk_end:
            r = r0 + loc
            if 0 <= r < pat.rows:
                if nt is None:
                    pat.set(r, CH_BASS, note=KEY_OFF)
                else:
                    pat.set(r, CH_BASS, note=nt, ins=ins, vol=int(round(vol * 0.80)))

def write_drums_bar(pat, bar_idx, style="main", fill=None, crash=False, clap_layer=False):
    """Write punchy keygen drum grooves with stereo-panned tom fills & 32nd rolls."""
    r0 = bar_idx * 16
    if crash:
        pat.set(r0, CH_PERC, note="C-4", ins=INS_CRASH, vol=44)

    if style == "silent":
        pass
    elif style == "intro":
        for i in range(16):
            if i % 2 == 0:
                v = 34 if i % 4 == 0 else 24
                pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=v)
            elif i in (7, 15):
                pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=18)

    elif style == "breakdown_sparse":
        for i in (0, 4, 6, 8, 12, 14):
            pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=26 if i % 4 == 0 else 18)
        pat.set(r0 + 12, CH_CLAP, note="C-4", ins=INS_CLAP, vol=26)

    elif style == "breakdown_build":
        for i in (0, 4, 8, 12):
            pat.set(r0 + i, CH_KICK, note="C-4", ins=INS_KICK, vol=50)
        for i in range(0, 16, 2):
            ins_h = INS_HATO if i in (6, 14) else INS_HATC
            pat.set(r0 + i, CH_HAT, note="C-4", ins=ins_h, vol=34 if ins_h == INS_HATO else 28)
        pat.set(r0 + 4, CH_SNARE, note="C-4", ins=INS_SNARE, vol=46)
        pat.set(r0 + 12, CH_SNARE, note="C-4", ins=INS_SNARE, vol=50)

    elif style in ("main", "chorus", "energetic", "funk"):
        if style == "main":
            kicks = [(0, 56), (6, 46), (8, 54), (10, 48)]
        elif style == "chorus":
            kicks = [(0, 58), (4, 50), (8, 56), (10, 46), (12, 50)]
        elif style == "energetic":
            kicks = [(0, 58), (3, 44), (6, 48), (8, 56), (10, 50), (14, 46)]
        elif style == "funk":
            kicks = [(0, 58), (3, 48), (6, 46), (10, 54), (11, 42)]

        for loc, kv in kicks:
            pat.set(r0 + loc, CH_KICK, note="C-4", ins=INS_KICK, vol=int(round(kv * 0.90)))

        pat.set(r0 + 4, CH_SNARE, note="C-4", ins=INS_SNARE, vol=49)
        pat.set(r0 + 12, CH_SNARE, note="C-4", ins=INS_SNARE, vol=51)
        if style in ("energetic", "funk"):
            pat.set(r0 + 15, CH_SNARE, note="C-4", ins=INS_SNARE, vol=28)
        if style == "funk":
            pat.set(r0 + 7, CH_SNARE, note="C-4", ins=INS_SNARE, vol=26)

        if clap_layer:
            pat.set(r0 + 4, CH_CLAP, note="C-4", ins=INS_CLAP, vol=38)
            pat.set(r0 + 12, CH_CLAP, note="C-4", ins=INS_CLAP, vol=40)

        for i in range(16):
            if style == "chorus":
                if i in (2, 6, 10, 14):
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATO, vol=38)
                elif i % 2 == 0:
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=32)
                else:
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=20)
            elif style == "energetic":
                if i in (2, 10, 14):
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATO, vol=38)
                elif i % 2 == 0:
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=32)
                else:
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=22)
            else:
                if i in (6, 14):
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATO, vol=36)
                elif i % 2 == 0:
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=32)
                elif i in (3, 11):
                    pat.set(r0 + i, CH_HAT, note="C-4", ins=INS_HATC, vol=20)

    # Fills
    if fill == "snare_pick":
        pat.set(r0 + 12, CH_SNARE, note="C-4", ins=INS_SNARE, vol=54)
        pat.set(r0 + 14, CH_SNARE, note="C-4", ins=INS_SNARE, vol=44)
        pat.set(r0 + 15, CH_SNARE, note="C-4", ins=INS_SNARE, vol=56)

    elif fill == "snare_roll":
        for loc in range(12, 16):
            pat.data[r0 + loc][CH_KICK] = [0, 0, 0, 0, 0]
        for loc, sv in [(10, 40), (12, 48), (13, 44), (14, 52)]:
            pat.set(r0 + loc, CH_SNARE, note="C-4", ins=INS_SNARE, vol=sv)
        pat.set(r0 + 15, CH_SNARE, note="C-4", ins=INS_SNARE, vol=56, eff=0x0E, param=0x93)

    elif fill == "tom_cascade":
        # Stereo L->R sweeping melodic chip-tom fill!
        for loc in range(10, 16):
            pat.data[r0 + loc][CH_KICK] = [0, 0, 0, 0, 0]
            pat.data[r0 + loc][CH_HAT] = [0, 0, 0, 0, 0]
        pat.set(r0 + 10, CH_SNARE, note="C-4", ins=INS_SNARE, vol=50)
        tom_seq = [
            (11, "G-3", 50, 0x38),
            (12, "F-3", 52, 0x60),
            (13, "D-3", 52, 0x88),
            (14, "C-3", 54, 0xB4),
            (15, "A-2", 56, 0xDC),
        ]
        for loc, tn, tv, tpan in tom_seq:
            pat.set(r0 + loc, CH_PERC, note=tn, ins=INS_TOM, vol=tv, eff=0x08, param=tpan)
        pat.set(r0 + 15, CH_SNARE, note="C-4", ins=INS_SNARE, vol=48)

    elif fill == "big_build":
        for loc in range(8, 16):
            pat.data[r0 + loc][CH_KICK] = [0, 0, 0, 0, 0]
        for loc, sv in [(8, 36), (10, 42), (12, 48), (13, 50), (14, 54)]:
            pat.set(r0 + loc, CH_SNARE, note="C-4", ins=INS_SNARE, vol=sv)
        pat.set(r0 + 15, CH_SNARE, note="C-4", ins=INS_SNARE, vol=58, eff=0x0E, param=0x92)
        pat.set(r0 + 8, CH_PERC, note="C-3", ins=INS_FX, vol=38, eff=0x01, param=0x18)
        for loc in range(9, 16):
            pat.set(r0 + loc, CH_PERC, eff=0x01, param=0x18)

    elif fill == "loop_turnaround":
        # Pure A7-tuned stereo tom & 32nd snare turnaround right into Order 1!
        for loc in range(10, 16):
            pat.data[r0 + loc][CH_KICK] = [0, 0, 0, 0, 0]
        pat.set(r0 + 10, CH_SNARE, note="C-4", ins=INS_SNARE, vol=50)
        pat.set(r0 + 12, CH_SNARE, note="C-4", ins=INS_SNARE, vol=54)
        pat.set(r0 + 13, CH_PERC, note="E-3", ins=INS_TOM, vol=48, eff=0x08, param=0x50)
        pat.set(r0 + 14, CH_PERC, note="A-2", ins=INS_TOM, vol=52, eff=0x08, param=0xB8)
        pat.set(r0 + 15, CH_SNARE, note="C-4", ins=INS_SNARE, vol=58, eff=0x0E, param=0x93)
        pat.set(r0 + 15, CH_CLAP, note="C-4", ins=INS_CLAP, vol=44)

# =====================================================================
# PATTERN COMPOSERS
# =====================================================================

def make_pat0_intro():
    """Order 0: INTRO 'Boot Sequence' — 4 bars (Dm9 | Dm9 | Bbmaj7 Gm7 | A7sus4 A7)"""
    p = XMPattern(64, 16)

    write_arp_bar(p, 0, "D-4", 0x37, ch=CH_ARP_L, vol=30, rhythm="sparkle_16")
    write_arp_bar(p, 0, "A-4", 0x37, ch=CH_ARP_R, vol=24, rhythm="offbeat")
    write_arp_bar(p, 1, "D-4", 0x3A, ch=CH_ARP_L, vol=34, rhythm="sparkle_16")
    write_arp_bar(p, 1, "A-4", 0x37, ch=CH_ARP_R, vol=28, rhythm="offbeat")

    write_arp_bar(p, 2, "Bb3", 0x47, ch=CH_ARP_L, vol=36, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 2, "D-4", 0x37, ch=CH_ARP_R, vol=30, rhythm="16th_pulse", start_row_off=0, length=8)
    write_arp_bar(p, 2, "G-3", 0x3A, ch=CH_ARP_L, vol=38, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 2, "Bb4", 0x37, ch=CH_ARP_R, vol=32, rhythm="16th_pulse", start_row_off=8, length=8)

    write_arp_bar(p, 3, "A-3", 0x57, ch=CH_ARP_L, vol=40, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 3, "A-3", 0x4A, ch=CH_ARP_L, vol=42, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 3, "E-4", 0x39, ch=CH_ARP_R, vol=34, rhythm="16th_pulse", start_row_off=8, length=8)

    write_bass_bar(p, 0, "D-2", "D-3", "A-2", style="intro_pulse", vol=38)
    write_bass_bar(p, 1, "D-2", "D-3", "A-2", style="intro_pulse", vol=44)
    write_bass_bar(p, 2, "Bb1", "Bb2", "F-2", style="half_8th", vol=48, start_off=0, length=8)
    write_bass_bar(p, 2, "G-2", "G-3", "D-3", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 3, "A-1", "A-2", "E-2", style="driving_8th", vol=52,
                   walk_end=[(12, "A-2"), (13, "E-2"), (14, "A-2"), (15, "C#3")])

    write_drums_bar(p, 0, style="intro")
    write_drums_bar(p, 1, style="intro")
    write_drums_bar(p, 2, style="breakdown_build")
    write_drums_bar(p, 3, style="breakdown_build", fill="big_build")

    bell_ev = [
        (0, "D-5", 3), (3, "F-5", 3), (6, "E-5", 2), (8, "A-5", 4), (12, "F-5", 4),
        (16, "D-5", 3), (19, "F-5", 3), (22, "E-5", 2), (24, "C-5", 4), (28, "D-5", 4),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_ev, base_vol=40, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.35)

    lead_ev = [
        (32, "D-5", 3), (35, "F-5", 3), (38, "D-5", 2),
        (40, "G-5", 3), (43, "F-5", 3), (46, "D-5", 2),
        (48, "E-5", 4, {'vib': 0x42}), (52, "D-5", 2), (54, "E-5", 2),
        (56, "E-5", 2), (58, "G-5", 2), (60, "A-5", 2), (62, "E-5", 1), (63, "C#5", 1, {'keyoff': False, 'no_echo': True}),
    ]
    write_melody(p, CH_LEAD, INS_PWMLEAD, lead_ev, base_vol=48, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.35)

    p.set(28, CH_PERC, note="C-3", ins=INS_FX, vol=24, eff=0x01, param=0x16)
    for loc in range(29, 32): p.set(loc, CH_PERC, eff=0x01, param=0x16)
    write_pad_chord(p, 32, 8, ["F-3", "A-3", "D-4"], vol=20)
    write_pad_chord(p, 40, 8, ["G-3", "Bb3", "F-4"], vol=22)
    write_pad_chord(p, 48, 8, ["G-3", "A-3", "D-4"], vol=24)
    write_pad_chord(p, 56, 8, ["G-3", "A-3", "C#4"], vol=25, keyoff=False)
    return p

# --- Reusable Theme A Melody & Harmony Data ---

MELODY_A_PART1 = [
    (0,  "D-5", 3), (3,  "F-5", 3), (6,  "E-5", 2),
    (8,  "C-5", 2), (10, "D-5", 2), (12, "A-4", 4, {'vib': 0x42}),
    (16, "Bb4", 3), (19, "D-5", 3), (22, "C-5", 2),
    (24, "A-4", 2), (26, "F-4", 2), (28, "G-4", 2), (30, "A-4", 2),
    (32, "G-4", 3), (35, "C-5", 3), (38, "D-5", 2),
    (40, "E-5", 3), (43, "D-5", 3), (46, "C-5", 2),
    (48, "A-4", 4, {'vib': 0x42}), (52, "C-5", 2), (54, "D-5", 2),
    (56, "E-5", 4, {'vib': 0x42}), (60, "G-5", 2), (62, "E-5", 1), (63, "C#5", 1, {'keyoff': False}),
]

HARM_A_PART1 = [
    (0,  "A-4", 3), (3,  "D-5", 3), (6,  "C-5", 2),
    (8,  "A-4", 2), (10, "A-4", 2), (12, "F-4", 4),
    (16, "F-4", 3), (19, "Bb4", 3), (22, "A-4", 2),
    (24, "F-4", 2), (26, "D-4", 2), (28, "E-4", 2), (30, "F-4", 2),
    (32, "E-4", 3), (35, "G-4", 3), (38, "G-4", 2),
    (40, "C-5", 3), (43, "G-4", 3), (46, "G-4", 2),
    (48, "E-4", 4), (52, "G-4", 2), (54, "A-4", 2),
    (56, "C#5", 4, {'vib': 0x42}), (60, "E-5", 2), (62, "C#5", 1), (63, "A-4", 1, {'keyoff': False}),
]

def get_melody_a_part2(to_chorus=False, glam=False):
    ev = [
        (0,  "D-5", 3), (3,  "F-5", 3), (6,  "E-5", 2),
        # Soaring leap to A-5 (with expressive portamento glide on A3 climax!)
        (8,  "A-5", 3, {'vib': 0x42, 'porta': glam, 'porta_speed': 0x38, 'retrig_ins': INS_PWMLEAD}),
        (11, "G-5", 3), (14, "F-5", 2),
        (16, "E-5", 3), (19, "F-5", 3), (22, "C-5", 2),
        (24, "A-4", 2), (26, "C-5", 2), (28, "D-5", 2), (30, "E-5", 2),
        (32, "F-5", 2), (34, "D-5", 2), (36, "Bb4", 2), (38, "D-5", 2),
        (40, "E-5", 2), (42, "D-5", 2), (44, "C-5", 2), (46, "G-4", 2),
    ]
    if to_chorus:
        ev += [
            (48, "A-4", 3), (51, "D-5", 3), (54, "F-5", 2),
            (56, "E-5", 3), (59, "G-5", 3), (62, "A-5", 2, {'keyoff': False}),
        ]
    else:
        ev += [
            (48, "A-4", 3), (51, "D-5", 3), (54, "C-5", 2),
            (56, "C#5", 4, {'vib': 0x42}), (60, "E-5", 2), (62, "C#5", 2, {'keyoff': False}),
        ]
    return ev

def get_harm_a_part2(to_chorus=False):
    ev = [
        (0,  "A-4", 3), (3,  "D-5", 3), (6,  "C-5", 2),
        (8,  "F-5", 3, {'vib': 0x42}), (11, "E-5", 3), (14, "D-5", 2),
        (16, "C-5", 3), (19, "C-5", 3), (22, "A-4", 2),
        (24, "F-4", 2), (26, "A-4", 2), (28, "A-4", 2), (30, "C-5", 2),
        (32, "D-5", 2), (34, "Bb4", 2), (36, "G-4", 2), (38, "Bb4", 2),
        (40, "C-5", 2), (42, "Bb4", 2), (44, "G-4", 2), (46, "E-4", 2),
    ]
    if to_chorus:
        ev += [
            (48, "F-4", 3), (51, "A-4", 3), (54, "D-5", 2),
            (56, "C-5", 3), (59, "E-5", 3), (62, "G-5", 2, {'keyoff': False}),
        ]
    else:
        ev += [
            (48, "F-4", 3), (51, "A-4", 3), (54, "A-4", 2),
            (56, "A-4", 4), (60, "C#5", 2), (62, "A-4", 2, {'keyoff': False}),
        ]
    return ev

def make_pat_A1(variant="A1"):
    """Theme A Part 1 (Bars 1-4): Dm9 | Bbmaj7 | Cadd9 | Am7 A7/C#"""
    p = XMPattern(64, 16)
    is_big = (variant == "A3")
    has_harm = variant in ("A2", "A3")

    write_melody(p, CH_LEAD, INS_PWMLEAD, MELODY_A_PART1,
                 base_vol=49 if is_big else 48, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.36)

    if has_harm:
        write_melody(p, CH_HARM, INS_THIN, HARM_A_PART1,
                     base_vol=36 if is_big else 33, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.32)

    if is_big:
        bell_sparkles = [
            (0, "A-5", 2), (4, "D-6", 2), (8, "G-5", 2), (12, "F-5", 2), (14, "E-5", 2),
            (16, "A-5", 2), (20, "F-5", 2), (24, "D-5", 2), (28, "F-5", 2),
            (32, "G-5", 2), (36, "E-5", 2), (40, "G-5", 2), (44, "D-5", 2),
            (48, "E-5", 2), (52, "C-5", 2), (56, "G-5", 2), (60, "E-5", 2), (62, "A-5", 2),
        ]
        write_melody(p, CH_BELL, INS_BELL, bell_sparkles, base_vol=30)

    write_bass_bar(p, 0, "D-2", "D-3", "A-2", style="keygen_oct", vol=50)
    write_bass_bar(p, 1, "Bb1", "Bb2", "F-2", style="keygen_oct", vol=50, oct_slide=has_harm)
    write_bass_bar(p, 2, "C-2", "C-3", "G-2", style="keygen_oct", vol=50)
    write_bass_bar(p, 3, "A-1", "A-2", "E-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 3, "C#2", "C#3", "A-2", style="half_8th", vol=50, start_off=8, length=8,
                   walk_end=[(6, "C#3"), (7, "A-2")])

    arp_v = 34 if is_big else 31
    write_arp_bar(p, 0, "D-4", 0x37, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse")
    write_arp_bar(p, 0, "A-4", 0x37, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat")
    write_arp_bar(p, 1, "Bb3", 0x47, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse")
    write_arp_bar(p, 1, "F-4", 0x49, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat")
    write_arp_bar(p, 2, "C-4", 0x47, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse")
    write_arp_bar(p, 2, "G-4", 0x57, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat")
    write_arp_bar(p, 3, "A-3", 0x37, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse", start_row_off=0, length=8)
    write_arp_bar(p, 3, "A-3", 0x4A, ch=CH_ARP_L, vol=arp_v + 2, rhythm="16th_pulse", start_row_off=8, length=8)
    write_arp_bar(p, 3, "E-4", 0x39, ch=CH_ARP_R, vol=arp_v - 2, rhythm="offbeat", start_row_off=8, length=8)

    # Cleaner mid-register pad voicings (A3-F4 range: zero low-mid mud!)
    pv = 19 if is_big else (17 if has_harm else 15)
    write_pad_chord(p, 0,  15, ["F-3", "A-3", "C-4"], vol=pv)
    write_pad_chord(p, 16, 15, ["F-3", "A-3", "D-4"], vol=pv)
    write_pad_chord(p, 32, 15, ["G-3", "C-4", "D-4"], vol=pv)
    write_pad_chord(p, 48, 7,  ["G-3", "A-3", "C-4"], vol=pv)
    write_pad_chord(p, 56, 7,  ["G-3", "A-3", "C#4"], vol=pv)

    dstyle = "energetic" if is_big else ("chorus" if variant == "A2" else "main")
    write_drums_bar(p, 0, style=dstyle, crash=True, clap_layer=has_harm)
    write_drums_bar(p, 1, style=dstyle, clap_layer=has_harm)
    write_drums_bar(p, 2, style=dstyle, clap_layer=has_harm)
    write_drums_bar(p, 3, style=dstyle, fill="snare_pick", clap_layer=has_harm)
    return p

def make_pat_A2(variant="A1"):
    """Theme A Part 2 (Bars 5-8): Dm9 | Fmaj7/C | Gm7 C9 | Dm7 A7 (or C7/E into Chorus!)"""
    p = XMPattern(64, 16)
    to_chorus = variant in ("A2", "A3")
    is_big = (variant == "A3")
    has_harm = variant in ("A2", "A3")

    write_melody(p, CH_LEAD, INS_PWMLEAD, get_melody_a_part2(to_chorus=to_chorus, glam=is_big),
                 base_vol=49 if is_big else 48, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.36)

    if has_harm:
        write_melody(p, CH_HARM, INS_THIN, get_harm_a_part2(to_chorus=to_chorus),
                     base_vol=36 if is_big else 33, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.32)

    if is_big:
        bell_sparkles = [
            (0, "F-5", 2), (4, "A-5", 2), (8, "D-6", 2), (12, "A-5", 2),
            (16, "C-6", 2), (20, "A-5", 2), (24, "F-5", 2), (28, "A-5", 2),
            (32, "Bb5", 2), (36, "G-5", 2), (40, "G-5", 2), (44, "E-5", 2),
            (48, "F-5", 2), (52, "D-5", 2), (56, "G-5", 2), (60, "C-6", 2),
        ]
        write_melody(p, CH_BELL, INS_BELL, bell_sparkles, base_vol=30)

    write_bass_bar(p, 0, "D-2", "D-3", "A-2", style="keygen_oct", vol=50)
    write_bass_bar(p, 1, "C-2", "C-3", "A-2", style="keygen_oct", vol=50, oct_slide=has_harm)
    write_bass_bar(p, 2, "G-2", "G-3", "D-3", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 2, "C-2", "C-3", "G-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 3, "D-2", "D-3", "A-2", style="half_8th", vol=50, start_off=0, length=8)
    if to_chorus:
        write_bass_bar(p, 3, "E-2", "E-3", "C-3", style="half_8th", vol=50, start_off=8, length=8,
                       walk_end=[(4, "F-2"), (5, "G-2"), (6, "A-2"), (7, "A-2")])
    else:
        write_bass_bar(p, 3, "A-1", "A-2", "E-2", style="half_8th", vol=50, start_off=8, length=8,
                       walk_end=[(5, "E-2"), (6, "A-2"), (7, "C#3")])

    arp_v = 34 if is_big else 31
    write_arp_bar(p, 0, "D-4", 0x37, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse")
    write_arp_bar(p, 0, "A-4", 0x37, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat")
    write_arp_bar(p, 1, "F-4", 0x47, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse")
    write_arp_bar(p, 1, "C-4", 0x49, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat")
    write_arp_bar(p, 2, "G-3", 0x3A, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse", start_row_off=0, length=8)
    write_arp_bar(p, 2, "C-4", 0x4A, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse", start_row_off=8, length=8)
    write_arp_bar(p, 2, "Bb4", 0x37, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat", start_row_off=0, length=8)
    write_arp_bar(p, 2, "G-4", 0x37, ch=CH_ARP_R, vol=arp_v - 4, rhythm="offbeat", start_row_off=8, length=8)
    write_arp_bar(p, 3, "D-4", 0x3A, ch=CH_ARP_L, vol=arp_v, rhythm="16th_pulse", start_row_off=0, length=8)
    if to_chorus:
        write_arp_bar(p, 3, "C-4", 0x4A, ch=CH_ARP_L, vol=arp_v + 2, rhythm="sparkle_16", start_row_off=8, length=8)
        write_arp_bar(p, 3, "G-4", 0x38, ch=CH_ARP_R, vol=arp_v - 2, rhythm="16th_pulse", start_row_off=8, length=8)
    else:
        write_arp_bar(p, 3, "A-3", 0x4A, ch=CH_ARP_L, vol=arp_v + 2, rhythm="sparkle_16", start_row_off=8, length=8)
        write_arp_bar(p, 3, "E-4", 0x39, ch=CH_ARP_R, vol=arp_v - 2, rhythm="16th_pulse", start_row_off=8, length=8)

    pv = 19 if is_big else (17 if has_harm else 15)
    write_pad_chord(p, 0,  15, ["F-3", "A-3", "C-4"], vol=pv)
    write_pad_chord(p, 16, 15, ["F-3", "A-3", "C-4"], vol=pv)
    write_pad_chord(p, 32, 7,  ["G-3", "Bb3", "F-4"], vol=pv)
    write_pad_chord(p, 40, 7,  ["G-3", "Bb3", "E-4"], vol=pv)
    write_pad_chord(p, 48, 7,  ["F-3", "A-3", "C-4"], vol=pv)
    if to_chorus:
        write_pad_chord(p, 56, 7, ["G-3", "Bb3", "E-4"], vol=pv + 2)
    else:
        write_pad_chord(p, 56, 7, ["G-3", "A-3", "C#4"], vol=pv + 2)

    dstyle = "energetic" if is_big else ("chorus" if variant == "A2" else "main")
    fill_type = "tom_cascade" if to_chorus else "snare_roll"
    write_drums_bar(p, 0, style=dstyle, clap_layer=has_harm)
    write_drums_bar(p, 1, style=dstyle, clap_layer=has_harm)
    write_drums_bar(p, 2, style=dstyle, clap_layer=has_harm)
    write_drums_bar(p, 3, style=dstyle, fill=fill_type, clap_layer=has_harm)
    return p

# --- Section B: Heroic Major Chorus ---

MELODY_B_PART1 = [
    (0,  "F-5", 4, {'vib': 0x42}), (4,  "G-5", 2), (6,  "A-5", 2),
    (8,  "F-5", 3), (11, "D-5", 3), (14, "C-5", 2),
    (16, "D-5", 3), (19, "E-5", 3), (22, "G-5", 4, {'vib': 0x42}),
    (26, "E-5", 2), (28, "D-5", 2), (30, "C-5", 2),
    (32, "E-5", 3), (35, "C-5", 3), (38, "A-4", 2),
    (40, "D-5", 3), (43, "F-5", 3), (46, "E-5", 2),
    (48, "D-5", 3), (51, "Bb4", 3), (54, "G-4", 2),
    (56, "C-5", 4, {'vib': 0x42}), (60, "D-5", 2), (62, "E-5", 2, {'keyoff': False}),
]

HARM_B_PART1 = [
    (0,  "D-5", 4), (4,  "E-5", 2), (6,  "F-5", 2),
    (8,  "D-5", 3), (11, "Bb4", 3), (14, "A-4", 2),
    (16, "Bb4", 3), (19, "C-5", 3), (22, "E-5", 4, {'vib': 0x42}),
    (26, "C-5", 2), (28, "Bb4", 2), (30, "G-4", 2),
    (32, "C-5", 3), (35, "A-4", 3), (38, "E-4", 2),
    (40, "A-4", 3), (43, "D-5", 3), (46, "C-5", 2),
    (48, "Bb4", 3), (51, "G-4", 3), (54, "D-4", 2),
    (56, "G-4", 4), (60, "Bb4", 2), (62, "C-5", 2, {'keyoff': False}),
]

def make_pat_B1(climax=False):
    """Section B Part 1 (Bars 1-4): Bbmaj7 | C9 | Am7 Dm7 | Gm7 C7"""
    p = XMPattern(64, 16)

    write_melody(p, CH_LEAD, INS_PWMLEAD, MELODY_B_PART1,
                 base_vol=49, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.35)
    write_melody(p, CH_HARM, INS_THIN, HARM_B_PART1,
                 base_vol=36 if climax else 31, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.30)

    bell_b1 = [
        (0, "A-5", 2), (6, "F-5", 2), (12, "A-5", 2),
        (16, "G-5", 2), (22, "E-5", 2), (28, "G-5", 2),
        (32, "G-5", 2), (40, "A-5", 2), (44, "F-5", 2),
        (48, "F-5", 2), (56, "G-5", 2), (60, "Bb5", 2),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_b1, base_vol=32 if climax else 26)

    write_bass_bar(p, 0, "Bb1", "Bb2", "F-2", style="driving_8th", vol=50)
    write_bass_bar(p, 1, "C-2", "C-3", "G-2", style="driving_8th", vol=50)
    write_bass_bar(p, 2, "A-1", "A-2", "E-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 2, "D-2", "D-3", "A-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 3, "G-2", "G-3", "D-3", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 3, "C-2", "C-3", "G-2", style="half_8th", vol=50, start_off=8, length=8,
                   walk_end=[(6, "C-3"), (7, "A-2")])

    av = 34 if climax else 31
    write_arp_bar(p, 0, "Bb3", 0x47, ch=CH_ARP_L, vol=av, rhythm="sparkle_16")
    write_arp_bar(p, 0, "F-4", 0x49, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce")
    write_arp_bar(p, 1, "C-4", 0x4A, ch=CH_ARP_L, vol=av, rhythm="sparkle_16")
    write_arp_bar(p, 1, "G-4", 0x37, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce")
    write_arp_bar(p, 2, "A-3", 0x37, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 2, "D-4", 0x3A, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 2, "E-4", 0x58, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=0, length=8)
    write_arp_bar(p, 2, "A-4", 0x35, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=8, length=8)
    write_arp_bar(p, 3, "G-3", 0x3A, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 3, "C-4", 0x4A, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 3, "D-4", 0x58, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=0, length=8)
    write_arp_bar(p, 3, "G-4", 0x39, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=8, length=8)

    pv = 19 if climax else 18
    write_pad_chord(p, 0,  15, ["F-3", "A-3", "D-4"], vol=pv)
    write_pad_chord(p, 16, 15, ["G-3", "Bb3", "E-4"], vol=pv)
    write_pad_chord(p, 32, 7,  ["G-3", "A-3", "C-4"], vol=pv)
    write_pad_chord(p, 40, 7,  ["F-3", "A-3", "C-4"], vol=pv)
    write_pad_chord(p, 48, 7,  ["G-3", "Bb3", "F-4"], vol=pv)
    write_pad_chord(p, 56, 7,  ["G-3", "Bb3", "E-4"], vol=pv)

    ds = "energetic" if climax else "chorus"
    write_drums_bar(p, 0, style=ds, crash=True, clap_layer=True)
    write_drums_bar(p, 1, style=ds, clap_layer=True)
    write_drums_bar(p, 2, style=ds, clap_layer=True)
    write_drums_bar(p, 3, style=ds, fill="snare_pick", clap_layer=True)
    return p

def make_pat_B2(is_loop_end=False):
    """Section B Part 2 (Bars 5-8): B1b -> Breakdown, OR B2b -> Seamless Loop Turnaround to Order 1!"""
    p = XMPattern(64, 16)

    lead_ev = [
        (0,  "F-5", 3), (3,  "A-5", 3), (6,  "G-5", 2),
        (8,  "F-5", 3), (11, "D-5", 3), (14, "F-5", 2),
        (16, "G-5", 4, {'vib': 0x42}), (20, "A-5", 2), (22, "G-5", 2),
        (24, "E-5", 3), (27, "D-5", 3), (30, "C-5", 2),
    ]
    harm_ev = [
        (0,  "D-5", 3), (3,  "F-5", 3), (6,  "E-5", 2),
        (8,  "D-5", 3), (11, "Bb4", 3), (14, "D-5", 2),
        (16, "E-5", 4, {'vib': 0x42}), (20, "F-5", 2), (22, "E-5", 2),
        (24, "C-5", 3), (27, "Bb4", 3), (30, "G-4", 2),
    ]

    if not is_loop_end:
        lead_ev += [
            (32, "D-5", 2), (34, "E-5", 2), (36, "F-5", 2), (38, "A-5", 2),
            (40, "G-5", 3), (43, "E-5", 3), (46, "G-5", 2),
            (48, "A-5", 6, {'vib': 0x43}), (54, "G-5", 2),
            (56, "F#5", 4, {'vib': 0x42}), (60, "D-5", 2), (62, "C-5", 2),
        ]
        harm_ev += [
            (32, "A-4", 2), (34, "C-5", 2), (36, "D-5", 2), (38, "F-5", 2),
            (40, "E-5", 3), (43, "C-5", 3), (46, "E-5", 2),
            (48, "F-5", 6, {'vib': 0x42}), (54, "E-5", 2),
            (56, "D-5", 4), (60, "C-5", 2), (62, "A-4", 2),
        ]
    else:
        # Pure A7 dominant turnaround -> crisp pickup C#5 resolving straight to D-5 on Order 1 Row 0!
        lead_ev += [
            (32, "D-5", 2), (34, "F-5", 2), (36, "G-5", 2), (38, "Bb5", 2),
            (40, "A-5", 2), (42, "G-5", 2), (44, "E-5", 2), (46, "G-5", 2),
            (48, "A-5", 4, {'vib': 0x43}), (52, "G-5", 2), (54, "E-5", 2),
            (56, "G-5", 2), (58, "E-5", 2), (60, "A-4", 2), (62, "C#5", 2, {'keyoff': False, 'no_echo': True}),
        ]
        harm_ev += [
            (32, "Bb4", 2), (34, "D-5", 2), (36, "D-5", 2), (38, "G-5", 2),
            (40, "E-5", 2), (42, "E-5", 2), (44, "C-5", 2), (46, "E-5", 2),
            (48, "E-5", 4, {'vib': 0x42}), (52, "D-5", 2), (54, "D-5", 2),
            (56, "E-5", 2), (58, "C#5", 2), (60, "G-4", 2), (62, "A-4", 1, {'no_echo': True}),
        ]

    write_melody(p, CH_LEAD, INS_PWMLEAD, lead_ev, base_vol=48, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.35)
    write_melody(p, CH_HARM, INS_THIN, harm_ev, base_vol=36 if is_loop_end else 32, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.30)

    bell_b2 = [
        (0, "A-5", 2), (8, "D-6", 2), (16, "C-6", 2), (24, "G-5", 2),
        (32, "F-5", 2), (40, "G-5", 2), (48, "A-5", 2), (56, "E-5" if is_loop_end else "D-5", 2),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_b2, base_vol=30)

    write_bass_bar(p, 0, "Bb1", "Bb2", "F-2", style="driving_8th", vol=50)
    write_bass_bar(p, 1, "C-2", "C-3", "G-2", style="driving_8th", vol=50)
    if not is_loop_end:
        write_bass_bar(p, 2, "D-2", "D-3", "A-2", style="half_8th", vol=50, start_off=0, length=8)
        write_bass_bar(p, 2, "E-2", "E-3", "C-3", style="half_8th", vol=50, start_off=8, length=8)
        write_bass_bar(p, 3, "F-2", "F-3", "C-3", style="half_8th", vol=50, start_off=0, length=8)
        write_bass_bar(p, 3, "F#2", "F#3", "D-3", style="half_8th", vol=48, start_off=8, length=8,
                       walk_end=[(6, "F#2"), (7, None)])
    else:
        write_bass_bar(p, 2, "G-2", "G-3", "D-3", style="half_8th", vol=50, start_off=0, length=8)
        write_bass_bar(p, 2, "E-2", "E-3", "C-3", style="half_8th", vol=50, start_off=8, length=8)
        # Pure A7 chord-tone bass turnaround: A -> E -> A -> C# -> (resolves to D-2!)
        write_bass_bar(p, 3, "A-1", "A-2", "E-2", style="driving_8th", vol=52,
                       walk_end=[(12, "A-2"), (13, "E-2"), (14, "A-2"), (15, "C#3")])

    av = 34 if is_loop_end else 31
    write_arp_bar(p, 0, "Bb3", 0x47, ch=CH_ARP_L, vol=av, rhythm="sparkle_16")
    write_arp_bar(p, 0, "F-4", 0x49, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce")
    write_arp_bar(p, 1, "C-4", 0x4A, ch=CH_ARP_L, vol=av, rhythm="sparkle_16")
    write_arp_bar(p, 1, "G-4", 0x37, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce")
    if not is_loop_end:
        write_arp_bar(p, 2, "D-4", 0x37, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=0, length=8)
        write_arp_bar(p, 2, "C-4", 0x47, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=8, length=8)
        write_arp_bar(p, 2, "A-4", 0x37, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=0, length=8)
        write_arp_bar(p, 2, "G-4", 0x57, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=8, length=8)
        write_arp_bar(p, 3, "F-4", 0x47, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=0, length=8)
        write_arp_bar(p, 3, "D-4", 0x4A, ch=CH_ARP_L, vol=av - 2, rhythm="16th_pulse", start_row_off=8, length=8)
        write_arp_bar(p, 3, "A-4", 0x37, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=0, length=8)
        write_arp_bar(p, 3, "F#4", 0x38, ch=CH_ARP_R, vol=av - 5, rhythm="offbeat", start_row_off=8, length=8)
    else:
        write_arp_bar(p, 2, "G-3", 0x3A, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=0, length=8)
        write_arp_bar(p, 2, "C-4", 0x47, ch=CH_ARP_L, vol=av, rhythm="sparkle_16", start_row_off=8, length=8)
        write_arp_bar(p, 2, "D-4", 0x58, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=0, length=8)
        write_arp_bar(p, 2, "G-4", 0x59, ch=CH_ARP_R, vol=av - 3, rhythm="8th_bounce", start_row_off=8, length=8)
        write_arp_bar(p, 3, "A-3", 0x57, ch=CH_ARP_L, vol=av + 2, rhythm="sparkle_16", start_row_off=0, length=8)
        write_arp_bar(p, 3, "A-3", 0x4A, ch=CH_ARP_L, vol=av + 3, rhythm="sparkle_16", start_row_off=8, length=8)
        write_arp_bar(p, 3, "E-4", 0x39, ch=CH_ARP_R, vol=av, rhythm="sparkle_16", start_row_off=8, length=8)

    pv = 19 if is_loop_end else 18
    write_pad_chord(p, 0,  15, ["F-3", "A-3", "D-4"], vol=pv)
    write_pad_chord(p, 16, 15, ["G-3", "Bb3", "E-4"], vol=pv)
    if not is_loop_end:
        write_pad_chord(p, 32, 7, ["F-3", "A-3", "C-4"], vol=pv)
        write_pad_chord(p, 40, 7, ["G-3", "C-4", "E-4"], vol=pv)
        write_pad_chord(p, 48, 7, ["F-3", "A-3", "E-4"], vol=pv)
        write_pad_chord(p, 56, 7, ["F#3", "A-3", "C-4"], vol=pv - 2)
    else:
        write_pad_chord(p, 32, 7, ["G-3", "Bb3", "F-4"], vol=pv)
        write_pad_chord(p, 40, 7, ["G-3", "C-4", "E-4"], vol=pv)
        write_pad_chord(p, 48, 7, ["G-3", "A-3", "D-4"], vol=pv + 1)
        write_pad_chord(p, 56, 7, ["G-3", "A-3", "C#4"], vol=pv + 1)

    ds = "energetic" if is_loop_end else "chorus"
    write_drums_bar(p, 0, style=ds, clap_layer=True)
    write_drums_bar(p, 1, style=ds, clap_layer=True)
    write_drums_bar(p, 2, style=ds, clap_layer=True)
    if is_loop_end:
        write_drums_bar(p, 3, style=ds, fill="loop_turnaround", clap_layer=True)
    else:
        write_drums_bar(p, 3, style=ds, clap_layer=True)
        for loc in range(10, 16):
            p.data[48 + loc][CH_KICK] = [0, 0, 0, 0, 0]
            p.data[48 + loc][CH_HAT] = [0, 0, 0, 0, 0]
        p.set(58, CH_PERC, note="G-3", ins=INS_TOM, vol=44, eff=0x08, param=0x55)
        p.set(60, CH_PERC, note="D-3", ins=INS_TOM, vol=46, eff=0x08, param=0xB0)
        p.set(62, CH_SNARE, note="C-4", ins=INS_SNARE, vol=44)
    return p

# --- Section C: Glassy Breakdown & Virtuoso SID Saw Solo ---

def make_pat7_breakdown():
    """Order 7: Section C1 — Spacious Dreamy Breakdown -> Dynamic Groove Build (Gm9 | C13 | Fmaj7 | Bbmaj7)"""
    p = XMPattern(64, 16)

    # Dreamy swelling stereo pads in bars 0-1 -> richer in bars 2-3!
    write_pad_chord(p, 0,  15, ["G-3", "Bb3", "F-4"], vol=21, swell=True)
    write_pad_chord(p, 16, 15, ["E-3", "Bb3", "D-4"], vol=22, swell=True)
    write_pad_chord(p, 32, 15, ["F-3", "A-3", "E-4"], vol=23)
    write_pad_chord(p, 48, 15, ["F-3", "A-3", "D-4"], vol=24)

    # Soft breathing SubTriBass in bars 0-1 (true -19dB contrast!), slamming to ChipFMBass in bars 2-3!
    write_bass_bar(p, 0, "G-2", "G-3", "D-3", style="sub_breathe", ins=INS_SUBTRI, vol=36)
    write_bass_bar(p, 1, "C-2", "C-3", "G-2", style="sub_breathe", ins=INS_SUBTRI, vol=38)
    write_bass_bar(p, 2, "F-2", "F-3", "C-3", style="keygen_oct", ins=INS_BASS, vol=48)
    write_bass_bar(p, 3, "Bb1", "Bb2", "F-2", style="funk_slap", ins=INS_BASS, vol=50,
                   walk_end=[(14, "D-2"), (15, "E-2")])

    bell_mel = [
        (0,  "A-5", 3), (3,  "F-5", 3), (6,  "D-5", 4), (10, "F-5", 2), (12, "G-5", 2), (14, "A-5", 2),
        (16, "A-5", 3), (19, "G-5", 3), (22, "E-5", 4), (26, "G-5", 2), (28, "A-5", 2), (30, "Bb5", 2),
        (32, "A-5", 4), (36, "G-5", 2), (38, "F-5", 2), (40, "E-5", 3), (43, "C-5", 3), (46, "E-5", 2),
        (48, "D-5", 4), (52, "F-5", 2), (54, "A-5", 2), (56, "G-5", 4), (60, "F-5", 4),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_mel, base_vol=42, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.40)

    # Delicate whispered stereo arps in bars 0-1 -> waking up in bars 2-3!
    write_arp_bar(p, 0, "G-4", 0x3A, ch=CH_ARP_L, vol=18, rhythm="offbeat")
    write_arp_bar(p, 1, "E-4", 0x6A, ch=CH_ARP_R, vol=18, rhythm="offbeat")
    write_arp_bar(p, 2, "F-4", 0x4B, ch=CH_ARP_L, vol=26, rhythm="8th_bounce")
    write_arp_bar(p, 2, "C-5", 0x49, ch=CH_ARP_R, vol=24, rhythm="offbeat")
    write_arp_bar(p, 3, "Bb3", 0x4B, ch=CH_ARP_L, vol=31, rhythm="16th_pulse")
    write_arp_bar(p, 3, "F-4", 0x49, ch=CH_ARP_R, vol=28, rhythm="16th_pulse")

    swell_ev = [
        (32, "A-4", 6, {'vib': 0x32}), (38, "C-5", 2), (40, "E-5", 8, {'vib': 0x42}),
        (48, "D-5", 6, {'vib': 0x42}), (54, "F-5", 2), (56, "A-5", 4, {'vib': 0x42}), (60, "G-5", 4),
    ]
    write_melody(p, CH_HARM, INS_THIN, swell_ev, base_vol=28)

    write_drums_bar(p, 0, style="breakdown_sparse", crash=True)
    write_drums_bar(p, 1, style="breakdown_sparse")
    write_drums_bar(p, 2, style="breakdown_build")
    write_drums_bar(p, 3, style="main", fill="snare_roll", clap_layer=True)
    p.set(60, CH_PERC, note="C-3", ins=INS_FX, vol=32, eff=0x01, param=0x1C)
    for loc in range(61, 64): p.set(loc, CH_PERC, eff=0x01, param=0x1C)
    return p

def make_pat8_solo():
    """Order 8: Section C2 — VIRTUOSO SID SAW SOLO! (Em7b5 A7b9 | Dm9 Dm7/C | Bbmaj7 Gm7 | A7sus4 A7)"""
    p = XMPattern(64, 16)

    solo_ev = [
        (0,  "G-4", 1), (1,  "Bb4", 2, {'porta': True, 'porta_speed': 0x30}),
        (3,  "D-5", 2), (5,  "Bb4", 1), (6,  "A-4", 1), (7,  "G-4", 1),
        (8,  "G-4", 1), (9,  "Bb4", 1), (10, "C#5", 1), (11, "E-5", 1),
        (12, "G-5", 4, {'vib': 0x53}),
        (16, "F-5", 2, {'porta': True, 'porta_speed': 0x24}),
        (18, "D-5", 1), (19, "A-4", 1), (20, "D-5", 1), (21, "F-5", 1), (22, "A-5", 2, {'vib': 0x42}),
        (24, "G-5", 1), (25, "F-5", 1), (26, "E-5", 1), (27, "D-5", 1),
        (28, "C-5", 2), (30, "E-5", 1), (31, "D-5", 1),
        (32, "D-5", 3), (35, "F-5", 3), (38, "A-5", 2),
        (40, "Bb5", 4, {'porta': True, 'porta_speed': 0x22, 'vib': 0x53}),
        (44, "A-5", 2), (46, "G-5", 2),
        (48, "A-5", 1), (49, "G-5", 1), (50, "E-5", 1), (51, "D-5", 1),
        (52, "E-5", 1), (53, "G-5", 1), (54, "A-5", 1), (55, "G-5", 1),
        (56, "E-5", 1), (57, "C#5", 1), (58, "A-4", 1), (59, "C#5", 1),
        (60, "E-5", 1), (61, "G-5", 1), (62, "A-5", 2),
    ]
    write_melody(p, CH_LEAD, INS_SOLO, solo_ev, base_vol=54, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.34)

    write_bass_bar(p, 0, "E-2", "E-3", "Bb2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 0, "A-1", "A-2", "E-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 1, "D-2", "D-3", "A-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 1, "C-2", "C-3", "A-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 2, "Bb1", "Bb2", "F-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 2, "G-2", "G-3", "D-3", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 3, "A-1", "A-2", "E-2", style="funk_slap", vol=52,
                   walk_end=[(12, "A-2"), (13, "E-2"), (14, "A-2"), (15, "C#3")])

    write_arp_bar(p, 0, "E-4", 0x36, ch=CH_ARP_L, vol=29, rhythm="16th_pulse", start_row_off=0, length=8)
    write_arp_bar(p, 0, "A-3", 0x4A, ch=CH_ARP_L, vol=31, rhythm="16th_pulse", start_row_off=8, length=8)
    write_arp_bar(p, 0, "G-4", 0x36, ch=CH_ARP_R, vol=26, rhythm="offbeat", start_row_off=8, length=8)
    write_arp_bar(p, 1, "D-4", 0x37, ch=CH_ARP_L, vol=29, rhythm="16th_pulse", start_row_off=0, length=8)
    write_arp_bar(p, 1, "C-4", 0x59, ch=CH_ARP_L, vol=29, rhythm="16th_pulse", start_row_off=8, length=8)
    write_arp_bar(p, 1, "A-4", 0x37, ch=CH_ARP_R, vol=26, rhythm="offbeat")
    write_arp_bar(p, 2, "Bb3", 0x47, ch=CH_ARP_L, vol=31, rhythm="16th_pulse", start_row_off=0, length=8)
    write_arp_bar(p, 2, "G-3", 0x3A, ch=CH_ARP_L, vol=31, rhythm="16th_pulse", start_row_off=8, length=8)
    write_arp_bar(p, 2, "D-4", 0x37, ch=CH_ARP_R, vol=26, rhythm="offbeat")
    write_arp_bar(p, 3, "A-3", 0x57, ch=CH_ARP_L, vol=33, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 3, "A-3", 0x4A, ch=CH_ARP_L, vol=35, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 3, "E-4", 0x39, ch=CH_ARP_R, vol=30, rhythm="16th_pulse", start_row_off=8, length=8)

    write_pad_chord(p, 0,  7, ["G-3", "Bb3", "D-4"], vol=18)
    write_pad_chord(p, 8,  7, ["G-3", "A-3", "C#4"], vol=18)
    write_pad_chord(p, 16, 7, ["F-3", "A-3", "C-4"], vol=18)
    write_pad_chord(p, 24, 7, ["F-3", "A-3", "C-4"], vol=18)
    write_pad_chord(p, 32, 7, ["F-3", "A-3", "D-4"], vol=18)
    write_pad_chord(p, 40, 7, ["G-3", "Bb3", "F-4"], vol=18)
    write_pad_chord(p, 48, 7, ["G-3", "A-3", "D-4"], vol=20)
    write_pad_chord(p, 56, 7, ["G-3", "A-3", "C#4"], vol=22)

    write_drums_bar(p, 0, style="funk", crash=True, clap_layer=True)
    write_drums_bar(p, 1, style="funk", clap_layer=True)
    write_drums_bar(p, 2, style="energetic", clap_layer=True)
    write_drums_bar(p, 3, style="energetic", fill="tom_cascade", clap_layer=True)
    return p

# --- Section D: Chromatic SID-Funk Bridge & Explosive Build ---

def make_pat9_bridge1():
    """Order 9: Section D1 — Chromatic SID-Funk Call-and-Response!"""
    p = XMPattern(64, 16)

    sid_call = [
        (0,  "D-4", 2), (2,  "D-4", 1), (3,  "F-4", 2), (5,  "D-4", 1), (6,  "A-4", 2),
        (8,  "C#5", 2), (10, "A-4", 2),
        (16, "D-4", 2), (18, "D-4", 1), (19, "F-4", 2), (21, "D-4", 1), (22, "C-5", 2),
        (24, "B-4", 2), (26, "A-4", 2),
        (32, "Bb4", 2), (34, "Bb4", 1), (35, "D-5", 2), (37, "F-5", 2),
        (40, "B-4", 2), (42, "D-5", 2), (44, "G-5", 2),
        (48, "C-5", 2), (50, "E-5", 2), (52, "G-5", 2), (54, "D-5", 2),
        (56, "E-5", 3), (59, "G-5", 3), (62, "E-5", 2),
    ]
    write_melody(p, CH_LEAD, INS_SOLO, sid_call, base_vol=53, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.30)

    # Iconic chromatic inner-voice counter-line (D -> C# -> C -> B -> Bb -> B -> C -> C#)!
    chrom_line = [
        (0, "D-4", 8), (8, "C#4", 8), (16, "C-4", 8), (24, "B-3", 8),
        (32, "Bb3", 8), (40, "B-3", 8), (48, "C-4", 8), (56, "C#4", 8),
    ]
    write_melody(p, CH_HARM, INS_THIN, chrom_line, base_vol=26)

    bell_ans = [
        (8,  "A-5", 2), (10, "F-5", 2), (12, "E-5", 2), (14, "C#5", 2),
        (24, "A-5", 2), (26, "F-5", 2), (28, "D-5", 2), (30, "B-4", 2),
        (38, "A-5", 2), (44, "G-5", 2), (46, "F-5", 2),
        (56, "A-5", 2), (58, "G-5", 2), (60, "E-5", 2), (62, "C#5", 2),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_ans, base_vol=40, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.34)

    write_bass_bar(p, 0, "D-2", "D-3", "A-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 0, "C#2", "C#3", "A-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 1, "C-2", "C-3", "A-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 1, "B-1", "B-2", "G-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 2, "Bb1", "Bb2", "F-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 2, "B-1", "B-2", "G-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 3, "C-2", "C-3", "G-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 3, "C#2", "C#3", "A-2", style="half_8th", vol=50, start_off=8, length=8)

    write_arp_bar(p, 0, "D-4", 0x37, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 0, "C#4", 0x48, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 1, "C-4", 0x59, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 1, "B-3", 0x36, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 2, "Bb3", 0x47, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 2, "B-3", 0x38, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 3, "C-4", 0x47, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 3, "C#4", 0x38, ch=CH_ARP_L, vol=34, rhythm="sparkle_16", start_row_off=8, length=8)

    write_arp_bar(p, 0, "A-4", 0x58, ch=CH_ARP_R, vol=26, rhythm="offbeat")
    write_arp_bar(p, 1, "A-4", 0x58, ch=CH_ARP_R, vol=26, rhythm="offbeat")
    write_arp_bar(p, 2, "D-5", 0x37, ch=CH_ARP_R, vol=26, rhythm="offbeat")
    write_arp_bar(p, 3, "G-4", 0x59, ch=CH_ARP_R, vol=28, rhythm="offbeat")

    write_drums_bar(p, 0, style="funk", crash=True, clap_layer=False)
    write_drums_bar(p, 1, style="funk", clap_layer=True)
    write_drums_bar(p, 2, style="funk", clap_layer=False)
    write_drums_bar(p, 3, style="funk", fill="snare_pick", clap_layer=True)
    return p

def make_pat10_bridge2():
    """Order 10: Section D2 — Tension Acceleration & Stop-Time Drum Break into Grand Finale A3!"""
    p = XMPattern(64, 16)

    lead_ev = [
        (0,  "D-5", 2), (2,  "F-5", 2), (4,  "E-5", 2), (6,  "D-5", 2),
        (8,  "C-5", 2), (10, "D-5", 2), (12, "F-5", 2), (14, "A-5", 2),
        (16, "A-5", 3), (19, "G-5", 3), (22, "F-5", 2),
        (24, "E-5", 3), (27, "D-5", 3), (30, "C-5", 2),
        (32, "D-5", 2), (34, "Bb4", 2), (36, "G-4", 2), (38, "Bb4", 2),
        (40, "D-5", 2), (42, "E-5", 2), (44, "G-5", 2), (46, "Bb5", 2),
        (48, "A-5", 4, {'vib': 0x53}),
        (56, "A-4", 1), (57, "C#5", 1), (58, "E-5", 1), (59, "G-5", 1),
        (60, "A-5", 1), (61, "G-5", 1), (62, "E-5", 1), (63, "C#5", 1, {'keyoff': False, 'no_echo': True}),
    ]
    write_melody(p, CH_LEAD, INS_PWMLEAD, lead_ev, base_vol=48, echo_ch=CH_LEAD_ECHO, echo_vol_ratio=0.34)

    harm_ev = [
        (0,  "A-4", 2), (2,  "D-5", 2), (4,  "C-5", 2), (6,  "A-4", 2),
        (8,  "A-4", 2), (10, "A-4", 2), (12, "D-5", 2), (14, "F-5", 2),
        (16, "F-5", 3), (19, "E-5", 3), (22, "D-5", 2),
        (24, "C-5", 3), (27, "A-4", 3), (30, "A-4", 2),
        (32, "Bb4", 2), (34, "G-4", 2), (36, "D-4", 2), (38, "G-4", 2),
        (40, "Bb4", 2), (42, "Bb4", 2), (44, "E-5", 2), (46, "G-5", 2),
        (48, "E-5", 4),
        (56, "E-4", 1), (57, "G-4", 1), (58, "A-4", 1), (59, "C#5", 1),
        (60, "E-5", 1), (61, "E-5", 1), (62, "C#5", 1), (63, "A-4", 1, {'keyoff': False, 'no_echo': True}),
    ]
    write_melody(p, CH_HARM, INS_THIN, harm_ev, base_vol=35, echo_ch=CH_HARM_ECHO, echo_vol_ratio=0.30)

    write_bass_bar(p, 0, "D-2", "D-3", "A-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 0, "C-2", "C-3", "A-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 1, "Bb1", "Bb2", "F-2", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 1, "A-1", "A-2", "E-2", style="half_8th", vol=50, start_off=8, length=8)
    write_bass_bar(p, 2, "G-2", "G-3", "D-3", style="half_8th", vol=50, start_off=0, length=8)
    write_bass_bar(p, 2, "E-2", "E-3", "Bb2", style="half_8th", vol=50, start_off=8, length=8)
    p.set(48, CH_BASS, note="A-1", ins=INS_BASS, vol=54)
    p.set(52, CH_BASS, note=KEY_OFF)
    for loc, bn, bv in [(56, "A-1", 48), (58, "A-2", 50), (60, "A-1", 52), (62, "C#2", 54), (63, "C#3", 52)]:
        p.set(loc, CH_BASS, note=bn, ins=INS_BASS, vol=bv)

    write_arp_bar(p, 0, "D-4", 0x37, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 0, "C-4", 0x59, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 1, "Bb3", 0x47, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 1, "A-3", 0x37, ch=CH_ARP_L, vol=32, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 2, "G-3", 0x3A, ch=CH_ARP_L, vol=34, rhythm="sparkle_16", start_row_off=0, length=8)
    write_arp_bar(p, 2, "E-4", 0x36, ch=CH_ARP_L, vol=34, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 3, "A-3", 0x57, ch=CH_ARP_L, vol=36, rhythm="sustain", start_row_off=0, length=4)
    p.set(52, CH_ARP_L, note=KEY_OFF)
    write_arp_bar(p, 3, "A-3", 0x4A, ch=CH_ARP_L, vol=38, rhythm="sparkle_16", start_row_off=8, length=8)
    write_arp_bar(p, 3, "E-4", 0x39, ch=CH_ARP_R, vol=34, rhythm="sparkle_16", start_row_off=8, length=8)

    write_pad_chord(p, 0,  7, ["F-3", "A-3", "D-4"], vol=20)
    write_pad_chord(p, 8,  7, ["F-3", "A-3", "C-4"], vol=20)
    write_pad_chord(p, 16, 7, ["F-3", "A-3", "D-4"], vol=20)
    write_pad_chord(p, 24, 7, ["G-3", "A-3", "C-4"], vol=20)
    write_pad_chord(p, 32, 7, ["G-3", "Bb3", "F-4"], vol=21)
    write_pad_chord(p, 40, 7, ["G-3", "Bb3", "E-4"], vol=21)
    write_pad_chord(p, 48, 4, ["G-3", "A-3", "D-4"], vol=24)
    write_pad_chord(p, 56, 7, ["G-3", "A-3", "C#4"], vol=24)

    write_drums_bar(p, 0, style="energetic", clap_layer=True)
    write_drums_bar(p, 1, style="energetic", clap_layer=True)
    write_drums_bar(p, 2, style="energetic", clap_layer=True)
    p.set(48, CH_KICK, note="C-4", ins=INS_KICK, vol=58)
    p.set(48, CH_PERC, note="C-4", ins=INS_CRASH, vol=44)
    p.set(48, CH_CLAP, note="C-4", ins=INS_CLAP, vol=40)
    write_drums_bar(p, 3, style="silent", fill="big_build")
    return p

# =====================================================================
# AUTOMATED HANGING-NOTE / BOUNDARY CLEANER
# =====================================================================

def clean_section_boundaries(mod):
    """
    Simulate sustaining voice state across EVERY song order transition (including
    Order[-1] -> Order[restart_pos]!) and insert KEY_OFF on Row 0 of any channel that
    would otherwise accidentally drone into a section that doesn't retrigger it!
    """
    transitions = []
    for i in range(len(mod.order) - 1):
        transitions.append((mod.order[i], mod.order[i + 1]))
    transitions.append((mod.order[-1], mod.order[mod.restart_pos]))

    cleaned = 0
    for prev_pid, next_pid in transitions:
        pp = mod.patterns[prev_pid]
        np_ = mod.patterns[next_pid]
        for ch in range(mod.channels):
            # Determine if a sustaining instrument is still sounding at end of prev_pid
            active = False
            for r in range(pp.rows):
                nt, ins, _, _, _ = pp.data[r][ch]
                if nt == KEY_OFF:
                    active = False
                elif 1 <= nt <= 96:
                    if ins == 0:
                        pass # porta keeps previous state
                    else:
                        active = (ins in SUSTAINING_INS)
            if active:
                # Check if next_pid Row 0 already has a note or KEY_OFF on this channel
                if np_.data[0][ch][0] == 0:
                    np_.set(0, ch, note=KEY_OFF)
                    cleaned += 1
    return cleaned

# =====================================================================
# ASSEMBLE FULL MODULE
# =====================================================================

def build_module():
    mod = XMModule(
        name="COBALT KEYGEN",
        channels=16,
        speed=6,
        bpm=142,
        restart_pos=1
    )

    for ins in build_instruments():
        mod.add_instrument(ins)

    pats = [
        make_pat0_intro(),                  # 0:  Intro (4 bars)
        make_pat_A1("A1"),                  # 1:  A1a Main Hook (RESTART POS = 1)
        make_pat_A2("A1"),                  # 2:  A1b Main Hook
        make_pat_A1("A2"),                  # 3:  A2a Main Hook + Twin Harmony
        make_pat_A2("A2"),                  # 4:  A2b Main Hook + Lift to Chorus
        make_pat_B1(climax=False),          # 5:  B1a Heroic Major Chorus
        make_pat_B2(is_loop_end=False),     # 6:  B1b Chorus -> Breakdown D7/F#
        make_pat7_breakdown(),              # 7:  C1  Glassy Breakdown -> Build
        make_pat8_solo(),                   # 8:  C2  Virtuoso SID Saw Solo!
        make_pat9_bridge1(),                # 9:  D1  Chromatic SID-Funk Bridge
        make_pat10_bridge2(),               # 10: D2  Acceleration & Explosive Break
        make_pat_A1("A3"),                  # 11: A3a Grand Climax Hook!
        make_pat_A2("A3"),                  # 12: A3b Grand Climax Hook -> Chorus
        make_pat_B1(climax=True),           # 13: B2a Final Anthemic Chorus!
        make_pat_B2(is_loop_end=True),      # 14: B2b Final Chorus & Seamless Loop Turnaround -> Order 1!
    ]

    for pat in pats:
        pid = mod.add_pattern(pat)
        mod.order.append(pid)

    n_clean = clean_section_boundaries(mod)
    print(f"Boundary cleaner inserted {n_clean} KEY_OFF guards across transitions & loop seam.")
    return mod

if __name__ == "__main__":
    mod = build_module()
    out_path = "/workspace/submission/tune.xm"
    sz = mod.save(out_path)
    print(f"Saved {out_path}: {sz/1024:.1f} KiB, {len(mod.patterns)} patterns, {len(mod.instruments)} instruments, restart={mod.restart_pos}")
