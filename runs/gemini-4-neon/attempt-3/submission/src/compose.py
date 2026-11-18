"""
NEON CIPHER — Original FastTracker II XM Keygen Tune (v3 Final Master)
Key: F# minor / A major | 140 BPM | Speed 6 | 16 Channels | 18 Unique Patterns (72 Bars, ~2:03)
Loop: Intro (Pos 0) -> Seamless Loop Pos 1..17 (restarts cleanly at Pos 1 on F#m!)
"""
import sys
import numpy as np
from xm_builder import XMModule, Pattern, parse_note, transpose_note
from synth import build_all_instruments

# Instrument indices (1-based)
INS_LEAD    = 1   # Hero PWM Lead
INS_ARP1    = 2   # Chip Arp 12.5%
INS_SAW     = 3   # Supersaw Lead
INS_BELL    = 4   # FM Glass Bell
INS_BASS    = 5   # SID Funk Bass
INS_BASS2   = 6   # Octave Pop Bass
INS_PAD     = 7   # Warm Retro Pad
INS_BRASS   = 8   # Chip Brass Stab
INS_ECHO    = 9   # Echo Muted Pulse
INS_ARP2    = 10  # Chip Arp 25%
INS_KICK    = 11  # Kick Drum
INS_SNARE   = 12  # Snare Drum
INS_CLAP    = 13  # Electro Clap
INS_CHAT    = 14  # Closed Hi-Hat
INS_OHAT    = 15  # Open Hi-Hat
INS_CRASH   = 16  # Crash Cymbal
INS_TOM     = 17  # Chip Synth Tom
INS_RISER   = 18  # Noise Riser
INS_LASER   = 19  # Chip Laser Zap

# Channel indices (0..15)
CH_KICK  = 0
CH_SNARE = 1
CH_CLAP  = 2
CH_HAT   = 3
CH_PERC  = 4
CH_BASS  = 5
CH_BASS2 = 6
CH_LEAD  = 7
CH_ECHO  = 8
CH_ARP1  = 9
CH_ARP2  = 10
CH_BELL  = 11
CH_SAW   = 12
CH_PAD1  = 13
CH_PAD2  = 14
CH_PAD3  = 15

# Wide, balanced 3D stereo field (low-end rock-solid mono center, mids/highs wide stereo!)
CH_PAN = {
    CH_KICK:  128,
    CH_SNARE: 128,
    CH_CLAP:   96,
    CH_HAT:   188,
    CH_PERC:   64,
    CH_BASS:  128,
    CH_BASS2: 128,
    CH_LEAD:   84,
    CH_ECHO:  216,
    CH_ARP1:   16,
    CH_ARP2:  240,
    CH_BELL:   48,
    CH_SAW:   158,
    CH_PAD1:   24,
    CH_PAD2:  232,
    CH_PAD3:  128,
}

# Verified chord library with exact consonant passing tones & allowed scales
CHORDS = {
    'F#m': {
        'bass': 'F#1', 'bass_hi': 'F#2', 'pass': 'E2',
        'arp1': ('F#4', 0x37), 'arp2': ('C#4', 0x58),
        'pad':  ['F#3', 'A3', 'C#4'], 'stab': ['A4', 'C#5', 'F#5'],
        'bell': ['F#5', 'A5', 'C#6', 'A5'],
        'scale': {6, 8, 9, 11, 1, 2, 4},
    },
    'F#m9': {
        'bass': 'F#1', 'bass_hi': 'F#2', 'pass': 'E2',
        'arp1': ('F#4', 0x37), 'arp2': ('A4', 0x4B),
        'pad':  ['A3', 'C#4', 'G#4'], 'stab': ['A4', 'C#5', 'G#5'],
        'bell': ['F#5', 'C#5', 'A4', 'G#5'],
        'scale': {6, 8, 9, 11, 1, 2, 4},
    },
    'F#m7': {
        'bass': 'F#1', 'bass_hi': 'F#2', 'pass': 'E2',
        'arp1': ('F#4', 0x3A), 'arp2': ('A4', 0x47),
        'pad':  ['F#3', 'A3', 'E4'], 'stab': ['A4', 'C#5', 'E5'],
        'bell': ['F#5', 'A5', 'C#6', 'E6'],
        'scale': {6, 8, 9, 11, 1, 2, 4},
    },
    'Dmaj7': {
        'bass': 'D2', 'bass_hi': 'D3', 'pass': 'C#2',
        'arp1': ('D4', 0x47), 'arp2': ('F#4', 0x37),
        'pad':  ['F#3', 'A3', 'C#4'], 'stab': ['F#4', 'A4', 'C#5'],
        'bell': ['D5', 'F#5', 'A5', 'C#6'],
        'scale': {2, 4, 6, 8, 9, 11, 1},
    },
    'D': {
        'bass': 'D2', 'bass_hi': 'D3', 'pass': 'C#2',
        'arp1': ('D4', 0x47), 'arp2': ('A4', 0x59),
        'pad':  ['D3', 'F#3', 'A3'], 'stab': ['F#4', 'A4', 'D5'],
        'bell': ['D5', 'F#5', 'A5', 'D6'],
        'scale': {2, 4, 6, 8, 9, 11, 1},
    },
    'Bm7': {
        'bass': 'B1', 'bass_hi': 'B2', 'pass': 'A1',
        'arp1': ('B3', 0x37), 'arp2': ('D4', 0x47),
        'pad':  ['D3', 'F#3', 'A3'], 'stab': ['F#4', 'A4', 'D5'],
        'bell': ['B4', 'D5', 'F#5', 'A5'],
        'scale': {11, 1, 2, 4, 6, 8, 9},
    },
    'C#7': {
        'bass': 'C#2', 'bass_hi': 'C#3', 'pass': 'B1',
        'arp1': ('C#4', 0x47), 'arp2': ('F4', 0x36),
        'pad':  ['F3', 'G#3', 'B3'], 'stab': ['F4', 'G#4', 'C#5'],
        'bell': ['C#5', 'F5', 'G#5', 'B5'],
        'scale': {1, 2, 5, 6, 8, 9, 11},
    },
    'C#7sus4': {
        'bass': 'C#2', 'bass_hi': 'C#3', 'pass': 'B1',
        'arp1': ('C#4', 0x57), 'arp2': ('F#4', 0x25),
        'pad':  ['F#3', 'G#3', 'B3'], 'stab': ['F#4', 'G#4', 'C#5'],
        'bell': ['C#5', 'F#5', 'G#5', 'B5'],
        'scale': {1, 2, 5, 6, 8, 9, 11},
    },
    'E': {
        'bass': 'E2', 'bass_hi': 'E3', 'pass': 'B1',
        'arp1': ('E4', 0x47), 'arp2': ('B4', 0x59),
        'pad':  ['E3', 'G#3', 'B3'], 'stab': ['G#4', 'B4', 'E5'],
        'bell': ['E5', 'G#5', 'B5', 'E6'],
        'scale': {4, 6, 8, 9, 11, 1, 2, 3},
    },
    'E/G#': {
        'bass': 'G#1', 'bass_hi': 'G#2', 'pass': 'B1',
        'arp1': ('G#4', 0x38), 'arp2': ('E4', 0x47),
        'pad':  ['G#3', 'B3', 'E4'], 'stab': ['G#4', 'B4', 'E5'],
        'bell': ['G#5', 'B5', 'E6', 'B5'],
        'scale': {4, 6, 8, 9, 11, 1, 2},
    },
    'E7': {
        'bass': 'E2', 'bass_hi': 'E3', 'pass': 'D2',
        'arp1': ('E4', 0x4A), 'arp2': ('G#4', 0x36),
        'pad':  ['G#3', 'B3', 'D4'], 'stab': ['G#4', 'B4', 'D5'],
        'bell': ['E5', 'G#5', 'B5', 'D6'],
        'scale': {4, 6, 8, 9, 11, 1, 2},
    },
    'E7sus4': {
        'bass': 'E2', 'bass_hi': 'E3', 'pass': 'D2',
        'arp1': ('E4', 0x57), 'arp2': ('A4', 0x25),
        'pad':  ['A3', 'B3', 'D4'], 'stab': ['A4', 'B4', 'E5'],
        'bell': ['E5', 'A5', 'B5', 'D6'],
        'scale': {4, 6, 8, 9, 11, 1, 2},
    },
    'A': {
        'bass': 'A1', 'bass_hi': 'A2', 'pass': 'G#1',
        'arp1': ('A4', 0x47), 'arp2': ('E4', 0x59),
        'pad':  ['A3', 'C#4', 'E4'], 'stab': ['A4', 'C#5', 'E5'],
        'bell': ['A5', 'C#6', 'E6', 'C#6'],
        'scale': {9, 11, 1, 2, 4, 6, 8},
    },
    'Amaj7': {
        'bass': 'A1', 'bass_hi': 'A2', 'pass': 'G#1',
        'arp1': ('A4', 0x47), 'arp2': ('C#4', 0x37),
        'pad':  ['A3', 'C#4', 'G#4'], 'stab': ['A4', 'C#5', 'G#5'],
        'bell': ['A5', 'C#6', 'E6', 'G#5'],
        'scale': {9, 11, 1, 2, 4, 6, 8},
    },
    'A/C#': {
        'bass': 'C#2', 'bass_hi': 'C#3', 'pass': 'E2',
        'arp1': ('C#4', 0x38), 'arp2': ('A4', 0x47),
        'pad':  ['A3', 'C#4', 'E4'], 'stab': ['A4', 'C#5', 'E5'],
        'bell': ['C#5', 'E5', 'A5', 'C#6'],
        'scale': {9, 11, 1, 2, 4, 6, 8},
    },
    'A/E': {
        'bass': 'E2', 'bass_hi': 'E3', 'pass': 'C#2',
        'arp1': ('E4', 0x59), 'arp2': ('A4', 0x47),
        'pad':  ['A3', 'C#4', 'E4'], 'stab': ['A4', 'C#5', 'E5'],
        'bell': ['E5', 'A5', 'C#6', 'E6'],
        'scale': {9, 11, 1, 2, 4, 6, 8},
    },
    'D#dim7': {
        'bass': 'D#2', 'bass_hi': 'D#3', 'pass': 'F#2',
        'arp1': ('D#4', 0x36), 'arp2': ('F#4', 0x36),
        'pad':  ['F#3', 'A3', 'C4'], 'stab': ['F#4', 'A4', 'C5'],
        'bell': ['D#5', 'F#5', 'A5', 'C6'],
        'scale': {3, 6, 9, 0},
    },
    'F#7': {
        'bass': 'F#1', 'bass_hi': 'F#2', 'pass': 'C#2',
        'arp1': ('F#4', 0x4A), 'arp2': ('A#4', 0x36),
        'pad':  ['F#3', 'A#3', 'E4'], 'stab': ['A#4', 'C#5', 'E5'],
        'bell': ['F#5', 'A#5', 'C#6', 'E6'],
        'scale': {6, 8, 10, 11, 1, 2, 4},
    },
    'C#m7': {
        'bass': 'C#2', 'bass_hi': 'C#3', 'pass': 'B1',
        'arp1': ('C#4', 0x37), 'arp2': ('E4', 0x47),
        'pad':  ['E3', 'G#3', 'B3'], 'stab': ['E4', 'G#4', 'B4'],
        'bell': ['C#5', 'E5', 'G#5', 'B5'],
        'scale': {1, 3, 4, 6, 8, 9, 11},
    },
    'Gmaj7': {
        'bass': 'G1', 'bass_hi': 'G2', 'pass': 'F#1',
        'arp1': ('G4', 0x47), 'arp2': ('B4', 0x37),
        'pad':  ['G3', 'B3', 'F#4'], 'stab': ['B4', 'D5', 'F#5'],
        'bell': ['G5', 'B5', 'D6', 'F#5'],
        'scale': {7, 9, 11, 1, 2, 4, 6},
    },
    'G#m7b5': {
        'bass': 'G#1', 'bass_hi': 'G#2', 'pass': 'B1',
        'arp1': ('G#4', 0x36), 'arp2': ('B4', 0x37),
        'pad':  ['G#3', 'B3', 'D4'], 'stab': ['B4', 'D5', 'F#5'],
        'bell': ['G#5', 'B5', 'D6', 'F#5'],
        'scale': {8, 9, 11, 1, 2, 4, 6},
    },
}


# =====================================================================
# MUSICAL PATTERN HELPERS
# =====================================================================

def init_pattern_state(pat):
    """Ensure exact channel panning & native global vol=64 (G40) on Pos 0 & Loop Start."""
    for ch, pan in CH_PAN.items():
        if pat.cells[0][ch][3] == 0 and pat.cells[0][ch][4] == 0:
            pat.set(0, ch, eff=0x08, param=pan)
    pat.set(0, CH_KICK, eff=0x10, param=64)  # Explicit G40 (native 64) for guaranteed consistency


def write_melody(pat, ch, inst, events, default_vol=54, echo_ch=None, echo_vol=26, echo_delay=3, echo_inst=INS_ECHO):
    note_starts = {ev[0] for ev in events if ev[1] not in (None, 'OFF')}

    for ev in events:
        row, note, dur = ev[0], ev[1], ev[2]
        opts = ev[3] if len(ev) > 3 else {}
        vol = opts.get('vol', default_vol)
        slide = opts.get('slide', 0)

        if slide:
            pat.set(row, ch, note=note, eff=0x03, param=slide)
            pat.set_vol(row, ch, vol)
        else:
            pat.set(row, ch, note=note, inst=inst)
            pat.set_vol(row, ch, vol)
            if 'vib' in opts:
                pat.set(row, ch, eff=0x04, param=opts['vib'])
            elif 'retrig' in opts:
                pat.set(row, ch, eff=0x0E, param=0x90 | opts['retrig'])
            elif 'delay' in opts:
                pat.set(row, ch, eff=0x0E, param=0xD0 | opts['delay'])
            elif 'cut' in opts:
                pat.set(row, ch, eff=0x0E, param=0xC0 | opts['cut'])
            elif 'pan' in opts:
                pat.set(row, ch, eff=0x08, param=opts['pan'])
            elif 'arp' in opts:
                pat.set(row, ch, eff=0x00, param=opts['arp'])

        if 'vib_cont' in opts:
            for vr in range(row + 1, min(64, row + dur)):
                if vr not in note_starts:
                    pat.set(vr, ch, eff=0x04, param=opts['vib_cont'])

        off_row = row + dur
        if dur > 0 and off_row < 64 and off_row not in note_starts:
            pat.set(off_row, ch, note='OFF')

        if echo_ch is not None and not opts.get('no_echo', False):
            er = row + echo_delay
            if er < 62:
                pat.set(er, echo_ch, note=note, inst=echo_inst)
                pat.set_vol(er, echo_ch, max(12, int(vol * echo_vol / max(default_vol, 1))))

    if echo_ch is not None:
        echo_starts = {ev[0] + echo_delay for ev in events if not (len(ev) > 3 and ev[3].get('no_echo')) and ev[0] + echo_delay < 62}
        for ev in events:
            opts = ev[3] if len(ev) > 3 else {}
            if opts.get('no_echo'):
                continue
            er = ev[0] + echo_delay
            e_off = min(63, er + max(2, min(ev[2], 5)))
            if er < 62 and e_off not in echo_starts and pat.cells[e_off][echo_ch][0] == 0:
                pat.set(e_off, echo_ch, note='OFF')


def write_bar_drums(pat, bar, style='main', fill=None, crash=False, clap=False):
    r0 = bar * 16
    if crash:
        pat.set(r0, CH_PERC, note='C-4', inst=INS_CRASH, eff=0x08, param=64)
        pat.set_vol(r0, CH_PERC, 46)

    if style == 'intro':
        for step in range(16):
            if step % 2 == 0:
                pat.set(r0 + step, CH_HAT, note='C-4', inst=INS_CHAT)
                pat.set_vol(r0 + step, CH_HAT, 40 if step % 4 == 0 else 26)
        if bar >= 2:
            for step in [0, 4, 8, 12]:
                pat.set(r0 + step, CH_KICK, note='C-4', inst=INS_KICK)
                pat.set_vol(r0 + step, CH_KICK, 32 if bar == 2 else 40)
        if bar == 3:
            pat.set(r0, CH_PERC, note='C-4', inst=INS_RISER)
            pat.set_vol(r0, CH_PERC, 44)
            for s, v in [(4, 38), (8, 42), (10, 38), (12, 46), (13, 42), (14, 50), (15, 52)]:
                pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
                pat.set_vol(r0 + s, CH_SNARE, v)
            pat.set(r0 + 12, CH_CLAP, note='C-4', inst=INS_LASER)
            pat.set_vol(r0 + 12, CH_CLAP, 36)
        return

    if style == 'breakdown_light':
        for step in [0, 2, 4, 6, 8, 10, 12, 14]:
            pat.set(r0 + step, CH_HAT, note='C-4', inst=INS_CHAT)
            pat.set_vol(r0 + step, CH_HAT, 30 if step % 4 == 0 else 18)
        if bar % 2 == 1:
            pat.set(r0 + 12, CH_CLAP, note='C-4', inst=INS_CLAP)
            pat.set_vol(r0 + 12, CH_CLAP, 26)
        return

    if style == 'breakdown_half':
        if bar in (0, 1):
            for s, v in [(0, 50), (6, 38), (10, 44)]:
                pat.set(r0 + s, CH_KICK, note='C-4', inst=INS_KICK)
                pat.set_vol(r0 + s, CH_KICK, v)
            pat.set(r0 + 8, CH_SNARE, note='C-4', inst=INS_SNARE)
            pat.set_vol(r0 + 8, CH_SNARE, 52)
            pat.set(r0 + 8, CH_CLAP, note='C-4', inst=INS_CLAP)
            pat.set_vol(r0 + 8, CH_CLAP, 38)
            for s in range(0, 16, 2):
                pat.set(r0 + s, CH_HAT, note='C-4', inst=INS_OHAT if s == 14 else INS_CHAT)
                pat.set_vol(r0 + s, CH_HAT, 42 if s % 4 == 0 else 28)
        elif bar == 2:
            for s in [0, 4, 8, 12]:
                pat.set(r0 + s, CH_KICK, note='C-4', inst=INS_KICK)
                pat.set_vol(r0 + s, CH_KICK, 48 if s in (0, 8) else 40)
            for idx, s in enumerate([4, 8, 10, 12, 14]):
                pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
                pat.set_vol(r0 + s, CH_SNARE, 38 + idx * 3)
            for s in range(0, 16, 2):
                pat.set(r0 + s, CH_HAT, note='C-4', inst=INS_CHAT)
                pat.set_vol(r0 + s, CH_HAT, 40)
        elif bar == 3:
            pat.set(r0, CH_PERC, note='C-4', inst=INS_RISER)
            pat.set_vol(r0, CH_PERC, 46)
            for s in [0, 4, 8]:
                pat.set(r0 + s, CH_KICK, note='C-4', inst=INS_KICK)
                pat.set_vol(r0 + s, CH_KICK, 46)
            for s in range(16):
                pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
                pat.set_vol(r0 + s, CH_SNARE, 22 + int(s * 2.1))
            pat.set(r0 + 12, CH_CLAP, note='C-4', inst=INS_LASER)
            pat.set_vol(r0 + 12, CH_CLAP, 38)
        return

    # Full driving grooves ('main', 'chorus', 'solo', 'turnaround')
    if style == 'main':
        kicks = [0, 4, 8, 10, 12] if bar % 2 == 1 else [0, 4, 8, 12, 14]
    elif style == 'chorus':
        kicks = [0, 4, 8, 12, 14] if bar % 2 == 0 else [0, 3, 8, 10, 12]
    elif style == 'solo':
        kicks = [0, 4, 6, 10, 12] if bar % 2 == 0 else [0, 4, 8, 10, 14]
    elif style == 'turnaround':
        if bar == 2:
            kicks = [0, 3, 6, 8, 11, 14]
        elif bar == 3:
            kicks = [0, 4, 8]
        else:
            kicks = [0, 4, 8, 12, 14]
    else:
        kicks = [0, 4, 8, 12]

    snares = [3, 8, 11] if (style == 'turnaround' and bar == 2) else [4, 12]
    snare_set = set(snares)

    # Smart Kick dynamics: 54 on pure downbeats (0, 8), 44 when layered with Snare+Clap (prevents peak stacking!)
    for s in kicks:
        pat.set(r0 + s, CH_KICK, note='C-4', inst=INS_KICK)
        if s in (0, 8) and s not in snare_set:
            kv = 54
        elif s in snare_set:
            kv = 42
        else:
            kv = 44
        pat.set_vol(r0 + s, CH_KICK, kv)

    for s in snares:
        pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
        pat.set_vol(r0 + s, CH_SNARE, 54 if not clap else 50)
        if clap:
            pat.set(r0 + s, CH_CLAP, note='C-4', inst=INS_CLAP)
            pat.set_vol(r0 + s, CH_CLAP, 42)
    if fill is None and bar % 2 == 1 and style in ('main', 'solo'):
        pat.set(r0 + 15, CH_SNARE, note='C-4', inst=INS_SNARE)
        pat.set_vol(r0 + 15, CH_SNARE, 34)

    # Shimmering 16th-note Hi-Hats!
    for s in range(16):
        if style in ('chorus', 'solo'):
            if s in (2, 6, 10, 14):
                pat.set(r0 + s, CH_HAT, note='C-4', inst=INS_OHAT)
                pat.set_vol(r0 + s, CH_HAT, 46)
            else:
                pat.set(r0 + s, CH_HAT, note='C-4', inst=INS_CHAT)
                pat.set_vol(r0 + s, CH_HAT, 48 if s % 4 == 0 else 30)
        else:
            if s in (6, 14):
                pat.set(r0 + s, CH_HAT, note='C-4', inst=INS_OHAT)
                pat.set_vol(r0 + s, CH_HAT, 44)
            elif s % 2 == 0 or s in (3, 11):
                pat.set(r0 + s, CH_HAT, note='C-4', inst=INS_CHAT)
                pat.set_vol(r0 + s, CH_HAT, 48 if s % 4 == 0 else 30)

    # Stereo-panned drum fills!
    if fill == 'snare_pick':
        for s, v in [(12, 50), (14, 46), (15, 52)]:
            pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
            pat.set_vol(r0 + s, CH_SNARE, v)
    elif fill == 'tom_desc':
        for s, tn, v, pan in [
            (10, 'C-4', 46, 48), (11, 'A-3', 46, 86),
            (12, 'F#3', 48, 128), (13, 'E-3', 48, 166),
            (14, 'D-3', 50, 200), (15, 'B-2', 52, 224)
        ]:
            pat.set(r0 + s, CH_PERC, note=tn, inst=INS_TOM, eff=0x08, param=pan)
            pat.set_vol(r0 + s, CH_PERC, v)
        pat.set(r0 + 12, CH_SNARE, note='C-4', inst=INS_SNARE)
        pat.set_vol(r0 + 12, CH_SNARE, 48)
    elif fill == 'riser_launch':
        pat.set(r0, CH_PERC, note='C-4', inst=INS_RISER)
        pat.set_vol(r0, CH_PERC, 42)
        for s, v in [(8, 40), (10, 44), (12, 48), (13, 44), (14, 50), (15, 52)]:
            pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
            pat.set_vol(r0 + s, CH_SNARE, v)
        pat.set(r0 + 14, CH_CLAP, note='C-4', inst=INS_CLAP)
        pat.set_vol(r0 + 14, CH_CLAP, 42)
    elif fill == 'tom_riser_big':
        pat.set(r0, CH_PERC, note='C-4', inst=INS_RISER)
        pat.set_vol(r0, CH_PERC, 36)
        for s, v in [(8, 40), (10, 42), (11, 38), (12, 46), (13, 44), (14, 46), (15, 48)]:
            pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
            pat.set_vol(r0 + s, CH_SNARE, v)
        pat.set(r0 + 12, CH_CLAP, note='C-4', inst=INS_LASER)
        pat.set_vol(r0 + 12, CH_CLAP, 38)
    elif fill == 'laser_drop':
        pat.set(r0 + 8, CH_SNARE, note='C-4', inst=INS_SNARE)
        pat.set_vol(r0 + 8, CH_SNARE, 50)
        pat.set(r0 + 10, CH_PERC, note='C-4', inst=INS_LASER)
        pat.set_vol(r0 + 10, CH_PERC, 42)
        for s in range(12, 16):
            for c in (CH_KICK, CH_SNARE, CH_CLAP, CH_HAT):
                pat.cells[r0 + s][c] = [0, 0, 0, 0, 0]
        pat.set(r0 + 12, CH_PERC, note='A-3', inst=INS_TOM, eff=0x08, param=84)
        pat.set_vol(r0 + 12, CH_PERC, 44)
        pat.set(r0 + 14, CH_PERC, note='E-3', inst=INS_TOM, eff=0x08, param=180)
        pat.set_vol(r0 + 14, CH_PERC, 46)
    elif fill == 'slingshot_loop':
        for s in range(8, 16):
            pat.cells[r0 + s][CH_HAT] = [0, 0, 0, 0, 0]
        for s, tn, v, pan in [
            (8, 'C-4', 46, 52), (10, 'A-3', 48, 96),
            (11, 'F#3', 46, 136), (12, 'D-3', 48, 178), (13, 'B-2', 48, 218)
        ]:
            pat.set(r0 + s, CH_PERC, note=tn, inst=INS_TOM, eff=0x08, param=pan)
            pat.set_vol(r0 + s, CH_PERC, v)
        for s, v in [(12, 48), (14, 50), (15, 52)]:
            pat.set(r0 + s, CH_SNARE, note='C-4', inst=INS_SNARE)
            pat.set_vol(r0 + s, CH_SNARE, v)
        pat.set(r0 + 14, CH_CLAP, note='C-4', inst=INS_CLAP)
        pat.set_vol(r0 + 14, CH_CLAP, 42)
        pat.set(r0 + 15, CH_KICK, note='C-4', inst=INS_KICK)
        pat.set_vol(r0 + 15, CH_KICK, 42)


def write_bar_bass(pat, bar, chord_a, chord_b=None, style='bounce'):
    """
    Funky octave-bouncing bass WITH authentic FT2 A40 Sidechain Volume-Slide Pump on Kick beats!
    On steps 0, 4, 8, 12 (where Kick slams), Bass starts ducked (-4 dB) on tick 0 so Kick pops
    crystal-clear, then blooms right up to full power via A40 (+4/tick) over ticks 1..5!
    """
    r0 = bar * 16
    ca = CHORDS[chord_a]
    cb = CHORDS[chord_b] if chord_b else ca

    def c_at(step):
        return ca if step < 8 else cb

    if style == 'intro_pulse':
        base_v = 22 + bar * 7
        for step in [0, 2, 4, 6, 8, 10, 12, 14]:
            c = c_at(step)
            if step % 4 == 0:
                pat.set(r0 + step, CH_BASS, note=c['bass'], inst=INS_BASS)
                pat.set_vol(r0 + step, CH_BASS, min(46, base_v))
                pat.set(r0 + step + 2, CH_BASS, note='OFF')
            else:
                pat.set(r0 + step, CH_BASS2, note=c['bass_hi'], inst=INS_BASS2)
                pat.set_vol(r0 + step, CH_BASS2, min(42, base_v - 2))
                if step + 2 < 16:
                    pat.set(r0 + step + 2, CH_BASS2, note='OFF')
        return

    if style == 'breakdown_soft':
        pat.set(r0, CH_BASS, note=ca['bass'], inst=INS_BASS)
        pat.set_vol(r0, CH_BASS, 38)
        pat.set(r0 + 7, CH_BASS, note='OFF')
        pat.set(r0 + 8, CH_BASS, note=cb['bass'], inst=INS_BASS)
        pat.set_vol(r0 + 8, CH_BASS, 36)
        pat.set(r0 + 14, CH_BASS, note='OFF')
        pat.set(r0 + 14, CH_BASS2, note=cb['bass_hi'], inst=INS_BASS2)
        pat.set_vol(r0 + 14, CH_BASS2, 30)
        return

    if style == 'stops':
        for step, hi in [(0, False), (3, True), (6, False), (8, False), (11, True), (14, False)]:
            c = c_at(step)
            if hi:
                pat.set(r0 + step, CH_BASS2, note=c['bass_hi'], inst=INS_BASS2)
                pat.set_vol(r0 + step, CH_BASS2, 44)
                pat.set(r0 + step, CH_BASS, note='OFF')
                if step + 2 < 16:
                    pat.set(r0 + step + 2, CH_BASS2, note='OFF')
            else:
                # Sidechain duck on kick beats 0 & 8!
                sc = step in (0, 8)
                pat.set(r0 + step, CH_BASS, note=c['bass'], inst=INS_BASS,
                        eff=(0x0A if sc else 0), param=(0x40 if sc else 0))
                pat.set_vol(r0 + step, CH_BASS, 30 if sc else 46)
                if step + 2 < 16:
                    pat.set(r0 + step + 2, CH_BASS, note='OFF')
        return

    if style == 'chorus':
        pattern = [
            (0, 'lo', 48, True), (2, 'hi', 44, False), (4, 'lo', 46, True), (6, 'hi', 44, False), (7, 'lo', 40, False),
            (8, 'lo', 48, True), (10, 'hi', 44, False), (12, 'lo', 46, True), (14, 'hi', 44, False), (15, 'pass', 40, False)
        ]
    elif style == 'solo':
        pattern = [
            (0, 'lo', 48, True), (2, 'hi', 44, False), (3, 'lo', 42, False), (6, 'hi', 44, False),
            (8, 'lo', 48, True), (10, 'hi', 44, False), (11, 'lo', 42, False), (12, 'lo', 46, True), (14, 'hi', 46, False), (15, 'pass', 40, False)
        ]
    else:
        pattern = [
            (0, 'lo', 48, True), (2, 'hi', 44, False), (4, 'lo', 46, True), (6, 'hi', 44, False),
            (8, 'lo', 48, True), (10, 'hi', 42, False), (11, 'lo', 42, False), (12, 'lo', 46, True), (14, 'hi', 44, False), (15, 'pass', 40, False)
        ]

    for step, kind, vol, sidechain in pattern:
        c = c_at(step)
        if kind == 'lo':
            if sidechain:
                # Start ducked (-18 vol steps = ~4 dB), slide up +4/tick (A40) -> full 48+ by tick 5!
                pat.set(r0 + step, CH_BASS, note=c['bass'], inst=INS_BASS, eff=0x0A, param=0x40)
                pat.set_vol(r0 + step, CH_BASS, max(24, vol - 18))
            else:
                pat.set(r0 + step, CH_BASS, note=c['bass'], inst=INS_BASS)
                pat.set_vol(r0 + step, CH_BASS, vol)
            pat.set(r0 + step, CH_BASS2, note='OFF')
        elif kind == 'hi':
            pat.set(r0 + step, CH_BASS2, note=c['bass_hi'], inst=INS_BASS2)
            pat.set_vol(r0 + step, CH_BASS2, vol)
            pat.set(r0 + step, CH_BASS, note='OFF')
        elif kind == 'pass':
            pat.set(r0 + step, CH_BASS, note=c['pass'], inst=INS_BASS)
            pat.set_vol(r0 + step, CH_BASS, vol)
            pat.set(r0 + step, CH_BASS2, note='OFF')


def write_bar_arps(pat, bar, chord_a, chord_b=None, style='dual', vol1=46, vol2=42, octave_shift=0):
    """Wide-stereo 56Hz FT2 0xy chiptune arpeggios (Left=16, Right=240!)."""
    r0 = bar * 16
    ca = CHORDS[chord_a]
    cb = CHORDS[chord_b] if chord_b else ca

    def c_at(s):
        return ca if s < 8 else cb

    if style == 'soft_wave':
        for s in range(16):
            c = c_at(s)
            n1, p1 = c['arp1']
            n1 = transpose_note(n1, octave_shift)
            if s in (0, 8):
                pat.set(r0 + s, CH_ARP1, note=n1, inst=INS_ARP1, eff=0x00, param=p1)
                pat.set_vol(r0 + s, CH_ARP1, vol1)
            elif s in (6, 14):
                pat.set(r0 + s, CH_ARP1, note='OFF')
            elif s not in (7, 15):
                pat.set(r0 + s, CH_ARP1, eff=0x00, param=p1)
        return

    if style == 'shimmer':
        for s in range(16):
            c = c_at(s)
            n1, p1 = c['arp1']
            n2, p2 = c['arp2']
            n1 = transpose_note(n1, octave_shift)
            n2 = transpose_note(n2, octave_shift)
            if s % 2 == 0:
                pat.set(r0 + s, CH_ARP1, note=n1, inst=INS_ARP1, eff=0x00, param=p1)
                pat.set_vol(r0 + s, CH_ARP1, vol1 if s % 4 == 0 else int(vol1 * 0.80))
            else:
                pat.set(r0 + s, CH_ARP1, eff=0x00, param=p1)
                pat.set(r0 + s, CH_ARP2, note=n2, inst=INS_ARP2, eff=0x00, param=p2)
                pat.set_vol(r0 + s, CH_ARP2, vol2)
        return

    if style == 'cascade':
        for s in range(16):
            c = c_at(s)
            n1, p1 = c['arp1']
            n2, p2 = c['arp2']
            oct_s = 12 if (s % 8 >= 4) else 0
            n1 = transpose_note(n1, octave_shift + oct_s)
            n2 = transpose_note(n2, octave_shift + (12 - oct_s))
            if s in (0, 3, 6, 8, 11, 14):
                pat.set(r0 + s, CH_ARP1, note=n1, inst=INS_ARP1, eff=0x00, param=p1)
                pat.set_vol(r0 + s, CH_ARP1, vol1)
            else:
                pat.set(r0 + s, CH_ARP1, eff=0x00, param=p1)
            if s in (2, 4, 10, 12):
                pat.set(r0 + s, CH_ARP2, note=n2, inst=INS_ARP2, eff=0x00, param=p2)
                pat.set_vol(r0 + s, CH_ARP2, vol2)
            else:
                pat.set(r0 + s, CH_ARP2, eff=0x00, param=p2)
        return

    # 'dual': funky 3-3-2 stereo interplay
    for s in range(16):
        c = c_at(s)
        n1, p1 = c['arp1']
        n2, p2 = c['arp2']
        n1 = transpose_note(n1, octave_shift)
        n2 = transpose_note(n2, octave_shift)
        if s in (0, 3, 6, 8, 11, 14):
            pat.set(r0 + s, CH_ARP1, note=n1, inst=INS_ARP1, eff=0x00, param=p1)
            pat.set_vol(r0 + s, CH_ARP1, vol1)
        else:
            pat.set(r0 + s, CH_ARP1, eff=0x00, param=p1)
        if s in (2, 5, 10, 13):
            pat.set(r0 + s, CH_ARP2, note=n2, inst=INS_ARP2, eff=0x00, param=p2)
            pat.set_vol(r0 + s, CH_ARP2, vol2)
        else:
            pat.set(r0 + s, CH_ARP2, eff=0x00, param=p2)


def write_bar_pad(pat, bar, chord_a, chord_b=None, vol=28, release_end=False):
    r0 = bar * 16
    pad_pans = (24, 232, 128)
    va = CHORDS[chord_a]['pad']
    for ci, note, pan in zip((CH_PAD1, CH_PAD2, CH_PAD3), va, pad_pans):
        pat.set(r0, ci, note=note, inst=INS_PAD, eff=0x08, param=pan)
        pat.set_vol(r0, ci, vol)
    if chord_b:
        vb = CHORDS[chord_b]['pad']
        for ci, note, pan in zip((CH_PAD1, CH_PAD2, CH_PAD3), vb, pad_pans):
            pat.set(r0 + 8, ci, note=note, inst=INS_PAD, eff=0x08, param=pan)
            pat.set_vol(r0 + 8, ci, vol)
    if release_end:
        for ci in (CH_PAD1, CH_PAD2, CH_PAD3):
            pat.set(r0 + 14, ci, note='OFF')


def write_bar_brass(pat, bar, chord_a, chord_b=None, hits=None, vol=36):
    r0 = bar * 16
    if hits is None:
        hits = [(0, 2), (6, 2), (10, 2)]
    pad_pans = (24, 232, 128)
    ca = CHORDS[chord_a]['stab']
    cb = CHORDS[chord_b]['stab'] if chord_b else ca
    for step, dur in hits:
        notes = ca if step < 8 else cb
        for ci, note, pan in zip((CH_PAD1, CH_PAD2, CH_PAD3), notes, pad_pans):
            pat.set(r0 + step, ci, note=note, inst=INS_BRASS, eff=0x08, param=pan)
            pat.set_vol(r0 + step, ci, vol)
            if step + dur < 16:
                pat.set(r0 + step + dur, ci, note='OFF')


def write_bar_bell_sparkles(pat, bar, chord_a, chord_b=None, pattern_kind='offbeat', vol=42, ping_pong=False):
    r0 = bar * 16
    ba = CHORDS[chord_a]['bell']
    bb = CHORDS[chord_b]['bell'] if chord_b else ba
    if pattern_kind == 'offbeat':
        steps = [(3, 0), (6, 1), (11, 2), (14, 3)]
    elif pattern_kind == 'arp16':
        steps = [(s, s % 4) for s in range(0, 16, 2)]
    elif pattern_kind == 'chorus_sparkle':
        steps = [(2, 1), (5, 2), (10, 3), (13, 2), (15, 0)]
    else:
        steps = [(0, 0), (6, 1), (12, 2)]
    for idx, (step, bi) in enumerate(steps):
        b = ba if step < 8 else bb
        pan = (36 if idx % 2 == 0 else 220) if ping_pong else 48
        pat.set(r0 + step, CH_BELL, note=b[bi % len(b)], inst=INS_BELL, eff=0x08, param=pan)
        pat.set_vol(r0 + step, CH_BELL, vol if step % 4 in (0, 2, 3) else int(vol * 0.84))


PATTERN_CHORD_MAP = []

def register_chords(pat_idx, chords):
    PATTERN_CHORD_MAP.append((pat_idx, chords))


# =====================================================================
# ALL 18 UNIQUE PATTERNS OF "NEON CIPHER"
# =====================================================================

def pat0_intro():
    """Pat 0: INTRO — Boot Sequence (Sparkling Ping-Pong Bell + Stereo Chip Arps -> Drop!)."""
    p = Pattern(64, 16)
    chords = [('F#m9', None), ('Dmaj7', None), ('Bm7', None), ('C#7sus4', 'C#7')]
    register_chords(0, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='intro')
        if b >= 1:  # Bar 0 opens crisp with pure crystal Bell + stereo Arps, Bass enters Bar 1!
            write_bar_bass(p, b, ca, cb, style='intro_pulse')
        write_bar_arps(p, b, ca, cb, style='shimmer', vol1=32 + b * 4, vol2=28 + b * 4)
        write_bar_pad(p, b, ca, cb, vol=18 + b * 3, release_end=(b == 3))

    bell_hook = [
        (0,  'F#5', 3, {'vol': 50, 'pan': 44}),  (3,  'C#5', 3, {'vol': 44, 'pan': 212}),
        (6,  'A4',  2, {'vol': 46, 'pan': 76}),  (8,  'B4',  2, {'vol': 46, 'pan': 184}),
        (10, 'C#5', 2, {'vol': 48, 'pan': 60}),  (12, 'G#5', 4, {'vol': 52, 'pan': 216}),
        (16, 'F#5', 3, {'vol': 48, 'pan': 44}),  (19, 'D5',  3, {'vol': 44, 'pan': 212}),
        (22, 'A4',  2, {'vol': 46, 'pan': 76}),  (24, 'C#5', 2, {'vol': 46, 'pan': 184}),
        (26, 'D5',  2, {'vol': 48, 'pan': 60}),  (28, 'A5',  4, {'vol': 52, 'pan': 216}),
        (32, 'F#5', 3, {'vol': 50, 'pan': 44}),  (35, 'D5',  3, {'vol': 44, 'pan': 212}),
        (38, 'B4',  2, {'vol': 46, 'pan': 76}),  (40, 'D5',  2, {'vol': 48, 'pan': 184}),
        (42, 'F#5', 2, {'vol': 50, 'pan': 60}),  (44, 'A5',  4, {'vol': 52, 'pan': 216}),
        (48, 'G#5', 3, {'vol': 50, 'pan': 64}),  (51, 'F#5', 3, {'vol': 48, 'pan': 196}),
        (54, 'F5',  2, {'vol': 52, 'pan': 88}),  (56, 'G#5', 2, {'vol': 52, 'pan': 176}),
        (58, 'B5',  2, {'vol': 54, 'pan': 72}),  (60, 'C#6', 2, {'vol': 54, 'pan': 192}),
        (62, 'F6',  2, {'vol': 56, 'pan': 128}),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_hook, default_vol=50, echo_ch=CH_ECHO, echo_vol=22)

    lead_tease = [
        (56, 'C#5', 2, {'vol': 38}), (58, 'F5', 2, {'vol': 44}),
        (60, 'G#5', 2, {'vol': 50}), (62, 'C#6', 2, {'vol': 56}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, lead_tease, default_vol=48)
    init_pattern_state(p)
    return p


def pat1_a1a():
    """Pat 1 (LOOP_START!): SECTION A1a — Main Theme Part 1."""
    p = Pattern(64, 16)
    chords = [('F#m', None), ('Dmaj7', None), ('Bm7', None), ('C#7', None)]
    register_chords(1, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='main', crash=(b == 0), fill=('snare_pick' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='bounce')
        write_bar_arps(p, b, ca, cb, style='dual', vol1=46, vol2=40)

    melody = [
        (0,  'F#5', 3, {'vol': 58}), (3,  'A5',  1, {'vol': 54}),
        (4,  'G#5', 2, {'vol': 56}), (6,  'F#5', 2, {'vol': 56}),
        (8,  'C#5', 2, {'vol': 52}), (10, 'E5',  2, {'vol': 54}),
        (12, 'F#5', 4, {'vol': 58, 'vib_cont': 0x43}),
        (16, 'A5',  3, {'vol': 58}), (19, 'G#5', 1, {'vol': 52}),
        (20, 'F#5', 2, {'vol': 56}), (22, 'E5',  2, {'vol': 54}),
        (24, 'D5',  2, {'vol': 52}), (26, 'C#5', 2, {'vol': 52}),
        (28, 'D5',  2, {'vol': 54}), (30, 'E5',  2, {'vol': 56, 'slide': 0x18}),
        (32, 'F#5', 2, {'vol': 58}), (34, 'D5',  2, {'vol': 54}),
        (36, 'B4',  2, {'vol': 52}), (38, 'D5',  2, {'vol': 54}),
        (40, 'E5',  3, {'vol': 56}), (43, 'F#5', 1, {'vol': 54}),
        (44, 'D5',  2, {'vol': 54}), (46, 'B4',  2, {'vol': 52}),
        (48, 'C#5', 4, {'vol': 56}),
        (52, 'F5',  2, {'vol': 56}), (54, 'G#5', 2, {'vol': 58}),
        (56, 'B5',  2, {'vol': 60, 'retrig': 3}), (58, 'G#5', 2, {'vol': 56}),
        (60, 'F5',  2, {'vol': 56}), (62, 'C#5', 2, {'vol': 54}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=56, echo_ch=CH_ECHO, echo_vol=28)
    write_bar_brass(p, 3, 'C#7', hits=[(0, 2), (8, 2), (12, 2)], vol=32)
    init_pattern_state(p)
    return p


def pat2_a1b():
    """Pat 2: SECTION A1b — Main Theme Part 2."""
    p = Pattern(64, 16)
    chords = [('F#m', None), ('E/G#', None), ('A', 'Bm7'), ('C#7sus4', 'C#7')]
    register_chords(2, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='main', fill=('tom_desc' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='bounce')
        write_bar_arps(p, b, ca, cb, style='dual', vol1=46, vol2=40)
    # Soft Warm Pad blooms underneath bars 2-3 to build into A2!
    write_bar_pad(p, 2, 'A', 'Bm7', vol=22)
    write_bar_pad(p, 3, 'C#7sus4', 'C#7', vol=24, release_end=True)

    melody = [
        (0,  'F#5', 3, {'vol': 58}), (3,  'A5',  1, {'vol': 54}),
        (4,  'G#5', 2, {'vol': 56}), (6,  'F#5', 2, {'vol': 56}),
        (8,  'C#5', 2, {'vol': 52}), (10, 'E5',  2, {'vol': 54}),
        (12, 'F#5', 3, {'vol': 58}), (15, 'A5',  1, {'vol': 56}),
        (16, 'B5',  3, {'vol': 60}), (19, 'A5',  1, {'vol': 54}),
        (20, 'G#5', 2, {'vol': 58}), (22, 'E5',  2, {'vol': 54}),
        (24, 'G#5', 2, {'vol': 56}), (26, 'B5',  2, {'vol': 60}),
        (28, 'E5',  4, {'vol': 54}),
        (32, 'C#6', 2, {'vol': 60, 'retrig': 3}), (34, 'A5',  2, {'vol': 56}),
        (36, 'E5',  2, {'vol': 54}), (38, 'A5',  2, {'vol': 56}),
        (40, 'B5',  2, {'vol': 60}), (42, 'F#5', 2, {'vol': 56}),
        (44, 'D5',  2, {'vol': 54}), (46, 'F#5', 2, {'vol': 56}),
        (48, 'G#5', 4, {'vol': 58}), (52, 'F#5', 2, {'vol': 56}),
        (54, 'F5',  2, {'vol': 58}),
        (56, 'G#5', 2, {'vol': 58}), (58, 'F5',  1, {'vol': 54}), (59, 'G#5', 1, {'vol': 56}),
        (60, 'C#6', 2, {'vol': 60}), (62, 'B5',  1, {'vol': 54}), (63, 'G#5', 1, {'vol': 54}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=56, echo_ch=CH_ECHO, echo_vol=28)
    write_bar_bell_sparkles(p, 2, 'A', 'Bm7', pattern_kind='offbeat', vol=38)
    write_bar_bell_sparkles(p, 3, 'C#7sus4', 'C#7', pattern_kind='offbeat', vol=40)
    return p


def pat3_a2a():
    """Pat 3: SECTION A2a — Main Theme Elevated with lively Contrapuntal Supersaw Call & Response!"""
    p = Pattern(64, 16)
    chords = [('F#m', None), ('Dmaj7', None), ('Bm7', None), ('C#7', None)]
    register_chords(3, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='main', crash=(b == 0), clap=True, fill=('snare_pick' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='bounce')
        write_bar_arps(p, b, ca, cb, style='dual', vol1=46, vol2=40)
        write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='offbeat', vol=40)

    melody = [
        (0,  'F#5', 3, {'vol': 58}), (3,  'A5',  1, {'vol': 54}),
        (4,  'G#5', 2, {'vol': 56}), (6,  'F#5', 2, {'vol': 56}),
        (8,  'C#5', 2, {'vol': 52}), (10, 'E5',  2, {'vol': 54}),
        (12, 'F#5', 4, {'vol': 58, 'vib_cont': 0x43}),
        (16, 'A5',  3, {'vol': 58, 'slide': 0x20}), (19, 'G#5', 1, {'vol': 52}),
        (20, 'F#5', 2, {'vol': 56}), (22, 'E5',  2, {'vol': 54}),
        (24, 'D5',  2, {'vol': 52}), (26, 'C#5', 2, {'vol': 52}),
        (28, 'D5',  2, {'vol': 54}), (30, 'E5',  2, {'vol': 56, 'slide': 0x18}),
        (32, 'F#5', 2, {'vol': 58}), (34, 'D5',  2, {'vol': 54}),
        (36, 'B4',  2, {'vol': 52}), (38, 'D5',  2, {'vol': 54}),
        (40, 'E5',  3, {'vol': 56}), (43, 'F#5', 1, {'vol': 54}),
        (44, 'A5',  2, {'vol': 58}), (46, 'F#5', 2, {'vol': 56}),
        (48, 'F5',  3, {'vol': 56}), (51, 'G#5', 1, {'vol': 56}),
        (52, 'B5',  2, {'vol': 58}), (54, 'C#6', 2, {'vol': 60}),
        (56, 'B5',  2, {'vol': 58}), (58, 'G#5', 2, {'vol': 56}),
        (60, 'F5',  2, {'vol': 56}), (62, 'G#5', 2, {'vol': 56}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=56, echo_ch=CH_ECHO, echo_vol=26)

    # Independent contrapuntal Supersaw: answers Hero Lead's held notes with rising 16th-note flourishes!
    counter = [
        (0,  'C#5', 4, {'vol': 40}), (4,  'E5',  2, {'vol': 40}), (6,  'C#5', 2, {'vol': 40}),
        (8,  'A4',  4, {'vol': 40}),
        (12, 'C#5', 1, {'vol': 44}), (13, 'E5',  1, {'vol': 44}), (14, 'F#5', 1, {'vol': 46}), (15, 'A5', 1, {'vol': 48}),  # Rising answer!
        (16, 'F#5', 4, {'vol': 42}), (20, 'D5',  2, {'vol': 40}), (22, 'C#5', 2, {'vol': 40}),
        (24, 'A4',  4, {'vol': 40}), (28, 'A4',  2, {'vol': 42}), (30, 'C#5', 2, {'vol': 44}),
        (32, 'D5',  4, {'vol': 42}), (36, 'F#4', 2, {'vol': 38}), (38, 'B4',  2, {'vol': 40}),
        (40, 'C#5', 3, {'vol': 42}), (43, 'D5',  1, {'vol': 42}), (44, 'F#5', 2, {'vol': 44}), (46, 'D5', 2, {'vol': 42}),
        (48, 'C#5', 4, {'vol': 42}), (52, 'F5',  2, {'vol': 44}), (54, 'G#5', 2, {'vol': 46}),
        (56, 'G#5', 2, {'vol': 44}), (58, 'F5',  2, {'vol': 42}), (60, 'C#5', 2, {'vol': 42}), (62, 'F5', 2, {'vol': 44}),
    ]
    write_melody(p, CH_SAW, INS_SAW, counter, default_vol=42)
    return p


def pat4_a2b():
    """Pat 4: SECTION A2b — Pre-Chorus Launch into A Major!"""
    p = Pattern(64, 16)
    chords = [('F#m', None), ('E/G#', None), ('Dmaj7', None), ('E7', None)]
    register_chords(4, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='main', clap=True, fill=('riser_launch' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='bounce')
        write_bar_arps(p, b, ca, cb, style='shimmer' if b >= 2 else 'dual', vol1=46, vol2=42)
        write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='offbeat', vol=40)

    write_bar_pad(p, 2, 'Dmaj7', vol=26)
    write_bar_pad(p, 3, 'E7', vol=30)

    melody = [
        (0,  'F#5', 3, {'vol': 58}), (3,  'A5',  1, {'vol': 54}),
        (4,  'G#5', 2, {'vol': 56}), (6,  'F#5', 2, {'vol': 56}),
        (8,  'C#5', 2, {'vol': 54}), (10, 'E5',  2, {'vol': 56}),
        (12, 'F#5', 3, {'vol': 58}), (15, 'A5',  1, {'vol': 56}),
        (16, 'B5',  3, {'vol': 60}), (19, 'A5',  1, {'vol': 56}),
        (20, 'G#5', 2, {'vol': 58}), (22, 'E5',  2, {'vol': 54}),
        (24, 'G#5', 2, {'vol': 56}), (26, 'B5',  2, {'vol': 60}),
        (28, 'E5',  4, {'vol': 56}),
        (32, 'F#5', 3, {'vol': 58}), (35, 'A5',  1, {'vol': 56}),
        (36, 'C#6', 2, {'vol': 60}), (38, 'B5',  2, {'vol': 58}),
        (40, 'A5',  2, {'vol': 58}), (42, 'F#5', 2, {'vol': 56}),
        (44, 'A5',  4, {'vol': 58}),
        (48, 'G#5', 2, {'vol': 58}), (50, 'B5',  2, {'vol': 60}),
        (52, 'D6',  2, {'vol': 60}), (54, 'B5',  2, {'vol': 58}),
        (56, 'G#5', 2, {'vol': 58}), (58, 'A5',  2, {'vol': 60}),
        (60, 'B5',  2, {'vol': 62}), (62, 'D6',  2, {'vol': 62}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=58, echo_ch=CH_ECHO, echo_vol=26)

    saw = [
        (0,  'C#5', 4, {'vol': 42}), (4,  'E5',  4, {'vol': 42}), (8,  'A4',  4, {'vol': 40}), (12, 'C#5', 4, {'vol': 42}),
        (16, 'G#5', 4, {'vol': 44}), (20, 'E5',  4, {'vol': 42}), (24, 'B4',  4, {'vol': 42}),
        (28, 'G#5', 1, {'vol': 44}), (29, 'A5',  1, {'vol': 44}), (30, 'B5',  2, {'vol': 46}),  # Counter-fill!
        (32, 'D5',  4, {'vol': 44}), (36, 'A5',  4, {'vol': 46}), (40, 'F#5', 4, {'vol': 44}), (44, 'F#5', 4, {'vol': 46}),
        (48, 'E5',  2, {'vol': 46}), (50, 'G#5', 2, {'vol': 48}), (52, 'B5',  2, {'vol': 48}), (54, 'G#5', 2, {'vol': 46}),
        (56, 'E5',  2, {'vol': 48}), (58, 'F#5', 2, {'vol': 50}), (60, 'G#5', 2, {'vol': 52}), (62, 'B5',  2, {'vol': 52}),
    ]
    write_melody(p, CH_SAW, INS_SAW, saw, default_vol=46)
    return p


def pat5_b1a(pat_idx, variant='b1'):
    """
    SECTION B Part 1 (A | E/G# | F#m7 | E) — 3 progressively elevated variants:
      'b1' (Pat 5)  : Warm soaring Chorus 1 with lush Retro Pads
      'b2' (Pat 7)  : Overdrive Chorus 2 with Brass Stabs, cascading Arps, expressive ornaments!
      'b3' (Pat 15) : Final Super-Chorus with ecstatic high-register climax & ping-pong Bell fanfare!
    """
    p = Pattern(64, 16)
    chords = [('A', None), ('E/G#', None), ('F#m7', None), ('E', None)]
    register_chords(pat_idx, chords)
    arp_style = 'shimmer' if variant == 'b1' else 'cascade'
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='chorus', crash=(b == 0), clap=True,
                        fill=('snare_pick' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='chorus')
        write_bar_arps(p, b, ca, cb, style=arp_style, vol1=46, vol2=42)
        if variant == 'b3':
            write_bar_brass(p, b, ca, cb, hits=[(0, 3), (6, 2), (10, 2), (14, 2)], vol=36)
        elif variant == 'b2':
            write_bar_brass(p, b, ca, cb, hits=[(0, 3), (6, 2), (10, 2)], vol=34)
        else:
            write_bar_pad(p, b, ca, cb, vol=30)
        if variant in ('b2', 'b3'):
            write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='chorus_sparkle',
                                    vol=44 if variant == 'b3' else 40, ping_pong=(variant == 'b3'))

    if variant == 'b1':
        melody = [
            (0,  'C#6', 3, {'vol': 58}), (3,  'B5',  1, {'vol': 52}), (4,  'A5',  2, {'vol': 56}), (6,  'E5',  2, {'vol': 52}),
            (8,  'A5',  2, {'vol': 54}), (10, 'B5',  2, {'vol': 56}), (12, 'C#6', 4, {'vol': 58, 'vib_cont': 0x43}),
            (16, 'B5',  3, {'vol': 58}), (19, 'C#6', 1, {'vol': 54}), (20, 'B5',  2, {'vol': 56}), (22, 'G#5', 2, {'vol': 54}),
            (24, 'E5',  2, {'vol': 52}), (26, 'G#5', 2, {'vol': 54}), (28, 'B5',  4, {'vol': 58, 'vib_cont': 0x43}),
            (32, 'A5',  3, {'vol': 56}), (35, 'B5',  1, {'vol': 54}), (36, 'A5',  2, {'vol': 56}), (38, 'F#5', 2, {'vol': 52}),
            (40, 'C#5', 2, {'vol': 50}), (42, 'F#5', 2, {'vol': 54}), (44, 'A5',  2, {'vol': 56}), (46, 'G#5', 2, {'vol': 54}),
            (48, 'G#5', 4, {'vol': 56}), (52, 'B5',  4, {'vol': 58}), (56, 'E6',  3, {'vol': 58}), (59, 'C#6', 1, {'vol': 54}),
            (60, 'B5',  4, {'vol': 56}),
        ]
    elif variant == 'b2':
        # Overdrive: expressive glides, high E6 grace ornaments & snappy chip retrigs!
        melody = [
            (0,  'C#6', 3, {'vol': 58, 'retrig': 3}), (3,  'E6',  1, {'vol': 56}), (4,  'C#6', 2, {'vol': 56}), (6,  'A5',  2, {'vol': 54}),
            (8,  'A5',  2, {'vol': 54}), (10, 'B5',  2, {'vol': 56}), (12, 'C#6', 2, {'vol': 58}), (14, 'E6',  2, {'vol': 60, 'slide': 0x22}),
            (16, 'B5',  3, {'vol': 58}), (19, 'C#6', 1, {'vol': 54}), (20, 'B5',  2, {'vol': 56}), (22, 'G#5', 2, {'vol': 54}),
            (24, 'E5',  2, {'vol': 52}), (26, 'G#5', 2, {'vol': 54}), (28, 'B5',  2, {'vol': 58}), (30, 'C#6', 2, {'vol': 58, 'slide': 0x20}),
            (32, 'A5',  3, {'vol': 56}), (35, 'B5',  1, {'vol': 54}), (36, 'C#6', 2, {'vol': 58}), (38, 'A5',  2, {'vol': 54}),
            (40, 'F#5', 2, {'vol': 52}), (42, 'A5',  2, {'vol': 56}), (44, 'C#6', 2, {'vol': 58}), (46, 'B5',  2, {'vol': 56}),
            (48, 'G#5', 2, {'vol': 56}), (50, 'B5',  2, {'vol': 58}), (52, 'E6',  4, {'vol': 60, 'vib_cont': 0x44}),
            (56, 'E6',  2, {'vol': 60, 'retrig': 3}), (58, 'C#6', 2, {'vol': 56}), (60, 'B5',  4, {'vol': 58}),
        ]
    else:  # 'b3' Final Super-Chorus: soaring peak up to F#6!
        melody = [
            (0,  'C#6', 3, {'vol': 60, 'retrig': 3}), (3,  'B5',  1, {'vol': 54}), (4,  'A5',  2, {'vol': 58}), (6,  'E5',  2, {'vol': 54}),
            (8,  'A5',  2, {'vol': 56}), (10, 'C#6', 2, {'vol': 58}), (12, 'E6',  4, {'vol': 60, 'vib_cont': 0x44}),
            (16, 'E6',  3, {'vol': 60}), (19, 'C#6', 1, {'vol': 56}), (20, 'B5',  2, {'vol': 58}), (22, 'G#5', 2, {'vol': 56}),
            (24, 'E5',  2, {'vol': 54}), (26, 'G#5', 2, {'vol': 56}), (28, 'B5',  4, {'vol': 60, 'vib_cont': 0x44}),
            (32, 'C#6', 3, {'vol': 60}), (35, 'B5',  1, {'vol': 56}), (36, 'A5',  2, {'vol': 58}), (38, 'F#5', 2, {'vol': 54}),
            (40, 'F#5', 2, {'vol': 54}), (42, 'A5',  2, {'vol': 56}), (44, 'C#6', 2, {'vol': 60}), (46, 'B5',  2, {'vol': 58}),
            (48, 'G#5', 2, {'vol': 58}), (50, 'B5',  2, {'vol': 60}),
            (52, 'E6',  2, {'vol': 62}), (54, 'F#6', 2, {'vol': 62, 'slide': 0x24}),
            (56, 'E6',  3, {'vol': 62, 'retrig': 3}), (59, 'C#6', 1, {'vol': 56}),
            (60, 'B5',  4, {'vol': 60, 'vib_cont': 0x44}),
        ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=58, echo_ch=CH_ECHO, echo_vol=28)

    bar3_saw = [
        (48, 'E5',  2, {'vol': 48}), (50, 'G#5', 2, {'vol': 50}),
        (52, 'B5',  2, {'vol': 52}), (54, 'C#6', 2, {'vol': 52}),
        (56, 'B5',  3, {'vol': 52}), (59, 'A5',  1, {'vol': 48}),
        (60, 'G#5', 4, {'vol': 50}),
    ] if variant == 'b3' else [
        (48, 'E5',  4, {'vol': 46}), (52, 'G#5', 4, {'vol': 48}),
        (56, 'B5',  3, {'vol': 50}), (59, 'A5',  1, {'vol': 46}),
        (60, 'G#5', 4, {'vol': 48}),
    ]
    saw = [
        (0,  'A5',  3, {'vol': 48}), (3,  'G#5', 1, {'vol': 42}), (4,  'E5',  2, {'vol': 46}), (6,  'C#5', 2, {'vol': 42}),
        (8,  'E5',  2, {'vol': 46}), (10, 'G#5', 2, {'vol': 46}), (12, 'A5',  4, {'vol': 50}),
        (16, 'G#5', 3, {'vol': 48}), (19, 'A5',  1, {'vol': 46}), (20, 'G#5', 2, {'vol': 48}), (22, 'E5',  2, {'vol': 44}),
        (24, 'B4',  2, {'vol': 42}), (26, 'E5',  2, {'vol': 46}), (28, 'G#5', 4, {'vol': 48}),
        (32, 'F#5', 3, {'vol': 48}), (35, 'G#5', 1, {'vol': 46}), (36, 'F#5', 2, {'vol': 46}), (38, 'C#5', 2, {'vol': 44}),
        (40, 'A4',  2, {'vol': 42}), (42, 'C#5', 2, {'vol': 44}), (44, 'F#5', 2, {'vol': 48}), (46, 'E5',  2, {'vol': 46}),
    ] + bar3_saw
    write_melody(p, CH_SAW, INS_SAW, saw, default_vol=48)
    return p


def pat6_b1b():
    p = Pattern(64, 16)
    chords = [('Dmaj7', None), ('A/C#', None), ('Bm7', None), ('E7', None)]
    register_chords(6, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='chorus', clap=True, fill=('tom_desc' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='chorus')
        write_bar_arps(p, b, ca, cb, style='shimmer', vol1=46, vol2=42)
        write_bar_pad(p, b, ca, cb, vol=30)

    melody = [
        (0,  'A5',  3, {'vol': 58}), (3,  'F#5', 1, {'vol': 54}), (4,  'D5',  2, {'vol': 54}), (6,  'F#5', 2, {'vol': 56}),
        (8,  'A5',  2, {'vol': 58}), (10, 'B5',  2, {'vol': 58}), (12, 'C#6', 4, {'vol': 60}),
        (16, 'E6',  3, {'vol': 60}), (19, 'C#6', 1, {'vol': 56}), (20, 'A5',  2, {'vol': 58}), (22, 'E5',  2, {'vol': 54}),
        (24, 'A5',  2, {'vol': 56}), (26, 'C#6', 2, {'vol': 60}), (28, 'B5',  4, {'vol': 58}),
        (32, 'D6',  3, {'vol': 60}), (35, 'C#6', 1, {'vol': 56}), (36, 'B5',  2, {'vol': 58}), (38, 'F#5', 2, {'vol': 54}),
        (40, 'A5',  2, {'vol': 56}), (42, 'B5',  2, {'vol': 58}), (44, 'D6',  4, {'vol': 60}),
        (48, 'E6',  4, {'vol': 60}), (52, 'D6',  2, {'vol': 58}), (54, 'C#6', 2, {'vol': 58}),
        (56, 'B5',  2, {'vol': 58}), (58, 'G#5', 2, {'vol': 56}), (60, 'E5',  2, {'vol': 54}), (62, 'B5',  2, {'vol': 58}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=58, echo_ch=CH_ECHO, echo_vol=28)

    saw = [
        (0,  'F#5', 3, {'vol': 46}), (3,  'D5',  1, {'vol': 42}), (4,  'A4',  2, {'vol': 40}), (6,  'D5',  2, {'vol': 44}),
        (8,  'F#5', 2, {'vol': 46}), (10, 'G#5', 2, {'vol': 46}), (12, 'A5',  4, {'vol': 48}),
        (16, 'C#6', 3, {'vol': 50}), (19, 'A5',  1, {'vol': 46}), (20, 'E5',  2, {'vol': 44}), (22, 'C#5', 2, {'vol': 42}),
        (24, 'E5',  2, {'vol': 44}), (26, 'A5',  2, {'vol': 48}), (28, 'G#5', 4, {'vol': 48}),
        (32, 'B5',  3, {'vol': 50}), (35, 'A5',  1, {'vol': 46}), (36, 'F#5', 2, {'vol': 46}), (38, 'D5',  2, {'vol': 44}),
        (40, 'F#5', 2, {'vol': 46}), (42, 'G#5', 2, {'vol': 46}), (44, 'B5',  4, {'vol': 50}),
        (48, 'B5',  4, {'vol': 50}), (52, 'G#5', 2, {'vol': 48}), (54, 'A5',  2, {'vol': 48}),
        (56, 'G#5', 2, {'vol': 48}), (58, 'E5',  2, {'vol': 46}), (60, 'B4',  2, {'vol': 42}), (62, 'G#5', 2, {'vol': 48}),
    ]
    write_melody(p, CH_SAW, INS_SAW, saw, default_vol=48)
    return p


def pat8_b2b(pat_idx, to_breakdown=True):
    p = Pattern(64, 16)
    last_chord = ('Bm7', 'C#7') if to_breakdown else ('Bm7', 'E7')
    chords = [('Dmaj7', None), ('D#dim7', None), ('A/E', 'F#7'), last_chord]
    register_chords(pat_idx, chords)
    for b, (ca, cb) in enumerate(chords):
        fill = ('laser_drop' if to_breakdown else 'tom_desc') if b == 3 else None
        write_bar_drums(p, b, style='chorus', clap=True, fill=fill)
        write_bar_bass(p, b, ca, cb, style='chorus')
        write_bar_arps(p, b, ca, cb, style='cascade', vol1=46, vol2=42)
        write_bar_brass(p, b, ca, cb,
                        hits=[(0, 3), (6, 2), (8, 3), (14, 2)] if b >= 2 else [(0, 3), (6, 2), (10, 2)],
                        vol=36)
        write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='chorus_sparkle',
                                vol=42, ping_pong=(not to_breakdown))

    if to_breakdown:
        for r in range(60, 64):
            for c in (CH_BASS, CH_BASS2, CH_ARP1, CH_ARP2, CH_BELL):
                p.cells[r][c] = [0, 0, 0, 0, 0]
        for c in (CH_BASS, CH_BASS2, CH_ARP1, CH_ARP2):
            p.set(60, c, note='OFF')

    melody = [
        (0,  'F#5', 2, {'vol': 58}), (2,  'A5',  2, {'vol': 58}), (4,  'C#6', 2, {'vol': 60}), (6,  'B5',  2, {'vol': 58}),
        (8,  'A5',  2, {'vol': 58}), (10, 'F#5', 2, {'vol': 56}), (12, 'D5',  2, {'vol': 54}), (14, 'F#5', 2, {'vol': 56}),
        (16, 'A5',  2, {'vol': 60}), (18, 'C6',  2, {'vol': 62}), (20, 'A5',  2, {'vol': 60}), (22, 'F#5', 2, {'vol': 58}),
        (24, 'D#5', 2, {'vol': 56}), (26, 'F#5', 2, {'vol': 58}), (28, 'A5',  2, {'vol': 60}), (30, 'C6',  2, {'vol': 62}),
        (32, 'C#6', 3, {'vol': 62}), (35, 'B5',  1, {'vol': 58}), (36, 'A5',  2, {'vol': 58}), (38, 'E5',  2, {'vol': 56}),
        (40, 'A#5', 2, {'vol': 60}), (42, 'C#6', 2, {'vol': 62}), (44, 'E6',  2, {'vol': 62}), (46, 'C#6', 2, {'vol': 60}),
    ]
    if to_breakdown:
        melody += [
            (48, 'D6',  2, {'vol': 60}), (50, 'B5',  2, {'vol': 58}), (52, 'F#5', 2, {'vol': 56}), (54, 'D5',  2, {'vol': 54}),
            (56, 'C#5', 2, {'vol': 54}), (58, 'F5',  2, {'vol': 56}), (60, 'G#5', 3, {'vol': 50, 'no_echo': True}),
        ]
    else:
        melody += [
            (48, 'D6',  2, {'vol': 60}), (50, 'F#6', 2, {'vol': 62, 'retrig': 3}), (52, 'D6', 2, {'vol': 60}), (54, 'B5', 2, {'vol': 58}),
            (56, 'E6',  2, {'vol': 62}), (58, 'D6',  2, {'vol': 60}), (60, 'B5', 2, {'vol': 60}), (62, 'G#5', 2, {'vol': 58}),
        ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=60, echo_ch=CH_ECHO, echo_vol=28)

    saw = [
        (0,  'D5',  2, {'vol': 46}), (2,  'F#5', 2, {'vol': 48}), (4,  'A5',  2, {'vol': 50}), (6,  'G#5', 2, {'vol': 48}),
        (8,  'F#5', 2, {'vol': 48}), (10, 'D5',  2, {'vol': 46}), (12, 'A4',  2, {'vol': 42}), (14, 'D5',  2, {'vol': 46}),
        (16, 'F#5', 2, {'vol': 50}), (18, 'A5',  2, {'vol': 52}), (20, 'F#5', 2, {'vol': 50}), (22, 'D#5', 2, {'vol': 48}),
        (24, 'C5',  2, {'vol': 46}), (26, 'D#5', 2, {'vol': 48}), (28, 'F#5', 2, {'vol': 50}), (30, 'A5',  2, {'vol': 52}),
        (32, 'A5',  3, {'vol': 52}), (35, 'G#5', 1, {'vol': 48}), (36, 'E5',  2, {'vol': 48}), (38, 'C#5', 2, {'vol': 46}),
        (40, 'F#5', 2, {'vol': 50}), (42, 'A#5', 2, {'vol': 52}), (44, 'C#6', 2, {'vol': 54}), (46, 'A#5', 2, {'vol': 50}),
    ]
    if to_breakdown:
        saw += [
            (48, 'B5',  2, {'vol': 50}), (50, 'F#5', 2, {'vol': 48}), (52, 'D5', 2, {'vol': 46}), (54, 'B4', 2, {'vol': 44}),
            (56, 'G#4', 2, {'vol': 44}), (58, 'C#5', 2, {'vol': 46}), (60, 'F5', 3, {'vol': 42}),
        ]
    else:
        saw += [
            (48, 'B5',  2, {'vol': 52}), (50, 'D6',  2, {'vol': 54}), (52, 'B5', 2, {'vol': 50}), (54, 'F#5', 2, {'vol': 48}),
            (56, 'B5',  2, {'vol': 52}), (58, 'G#5', 2, {'vol': 50}), (60, 'E5', 2, {'vol': 48}), (62, 'B5',  2, {'vol': 50}),
        ]
    write_melody(p, CH_SAW, INS_SAW, saw, default_vol=50)
    return p


def pat9_c1():
    """Pat 9: SECTION C1 — Dreamy Cyber Breakdown with Ping-Pong Bell & Portamento Counter-Sigh!"""
    p = Pattern(64, 16)
    chords = [('Dmaj7', None), ('C#m7', None), ('Bm7', None), ('F#m9', None)]
    register_chords(9, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='breakdown_light', crash=(b == 0))
        write_bar_bass(p, b, ca, cb, style='breakdown_soft')
        write_bar_pad(p, b, ca, cb, vol=32)
        write_bar_arps(p, b, ca, cb, style='soft_wave', vol1=24)
        write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='arp16', vol=38, ping_pong=True)

    melody = [
        (0,  'F#5', 6, {'vol': 48, 'vib_cont': 0x33}), (6,  'A5',  2, {'vol': 46}),
        (8,  'C#6', 4, {'vol': 50, 'vib_cont': 0x33}), (12, 'B5',  2, {'vol': 46}), (14, 'A5', 2, {'vol': 44}),
        (16, 'G#5', 6, {'vol': 48, 'vib_cont': 0x33}), (22, 'E5',  2, {'vol': 44}),
        (24, 'B5',  4, {'vol': 50, 'vib_cont': 0x33}), (28, 'G#5', 4, {'vol': 46}),
        (32, 'F#5', 4, {'vol': 48}), (36, 'D5',  2, {'vol': 44}), (38, 'F#5', 2, {'vol': 46}),
        (40, 'A5',  6, {'vol': 50, 'vib_cont': 0x33}), (46, 'G#5', 2, {'vol': 46}),
        (48, 'G#5', 4, {'vol': 50, 'vib_cont': 0x33}), (52, 'F#5', 4, {'vol': 48}),
        (56, 'C#5', 4, {'vol': 44}), (60, 'E5',  2, {'vol': 44}), (62, 'F#5', 2, {'vol': 46}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=48, echo_ch=CH_ECHO, echo_vol=28)

    # Delicate gliding Supersaw counter-sigh entering quietly on bars 2-3!
    sigh = [
        (32, 'D5',  6, {'vol': 28}), (38, 'F#5', 2, {'vol': 28, 'slide': 0x10}),
        (40, 'F#5', 8, {'vol': 30}),
        (48, 'C#6', 4, {'vol': 30}), (52, 'A5',  4, {'vol': 30, 'slide': 0x10}),
        (56, 'A5',  6, {'vol': 28}),
    ]
    write_melody(p, CH_SAW, INS_SAW, sigh, default_vol=28)
    return p


def pat10_c2():
    """Pat 10: SECTION C2 — Neapolitan Gmaj7 Goosebumps & Epic Riser!"""
    p = Pattern(64, 16)
    chords = [('Gmaj7', None), ('F#m7', None), ('Bm7', 'G#m7b5'), ('C#7sus4', 'C#7')]
    register_chords(10, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='breakdown_half', crash=(b == 0))
        write_bar_bass(p, b, ca, cb, style='breakdown_soft' if b < 2 else 'bounce')
        write_bar_pad(p, b, ca, cb, vol=34 if b < 3 else 26, release_end=(b == 3))
        write_bar_arps(p, b, ca, cb, style='soft_wave' if b == 0 else ('dual' if b == 1 else 'shimmer'),
                       vol1=30 + b * 4, vol2=26 + b * 4)
        write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='arp16' if b < 2 else 'offbeat',
                                vol=40, ping_pong=(b < 2))

    melody = [
        (0,  'B5',  4, {'vol': 54, 'vib_cont': 0x43}), (4,  'A5',  2, {'vol': 52}), (6,  'G5',  2, {'vol': 50}),
        (8,  'F#5', 4, {'vol': 54, 'vib_cont': 0x43}), (12, 'D5',  2, {'vol': 50}), (14, 'G5',  2, {'vol': 52}),
        (16, 'A5',  4, {'vol': 56, 'vib_cont': 0x43}), (20, 'G#5', 2, {'vol': 52}), (22, 'F#5', 2, {'vol': 52}),
        (24, 'E5',  4, {'vol': 52}), (28, 'C#5', 2, {'vol': 50}), (30, 'F#5', 2, {'vol': 52}),
        (32, 'D6',  3, {'vol': 56}), (35, 'B5',  1, {'vol': 52}), (36, 'A5',  2, {'vol': 54}), (38, 'F#5', 2, {'vol': 52}),
        (40, 'B5',  3, {'vol': 58}), (43, 'D6',  1, {'vol': 56}), (44, 'F#6', 4, {'vol': 58}),
        (48, 'G#5', 2, {'vol': 56}), (50, 'C#6', 2, {'vol': 58}),
        (52, 'F#6', 2, {'vol': 60}), (54, 'F6',  2, {'vol': 60}),
        (56, 'C#6', 2, {'vol': 60}), (58, 'B5',  2, {'vol': 58}),
        (60, 'G#5', 2, {'vol': 58}), (62, 'F5',  2, {'vol': 58}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, melody, default_vol=54, echo_ch=CH_ECHO, echo_vol=28)

    saw_build = [
        (0,  'G5',  8, {'vol': 34}), (8,  'D5',  8, {'vol': 34}),
        (16, 'F#5', 8, {'vol': 36}), (24, 'C#5', 8, {'vol': 36}),
        (32, 'F#5', 4, {'vol': 42}), (36, 'D5',  4, {'vol': 44}),
        (40, 'G#5', 4, {'vol': 46}), (44, 'B5',  4, {'vol': 48}),
        (48, 'F#5', 4, {'vol': 50}), (52, 'F5',  4, {'vol': 52}),
        (56, 'G#5', 2, {'vol': 54}), (58, 'B5',  2, {'vol': 56}),
        (60, 'C#6', 2, {'vol': 58}), (62, 'F6',  2, {'vol': 58}),
    ]
    write_melody(p, CH_SAW, INS_SAW, saw_build, default_vol=48)
    return p


def pat11_d1a():
    """Pat 11: SECTION D1a — Virtuoso Baroque-Keygen Chip Solo Part 1!"""
    p = Pattern(64, 16)
    chords = [('F#m', None), ('E', None), ('D', None), ('C#7', None)]
    register_chords(11, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='solo', crash=(b == 0), clap=True, fill=('snare_pick' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='solo')
        write_bar_arps(p, b, ca, cb, style='cascade', vol1=44, vol2=40)
        write_bar_brass(p, b, ca, cb, hits=[(0, 2), (8, 2)], vol=34)

    solo_saw = [
        (0,  'F#5', 1, {'vol': 60}), (1,  'A5',  1, {'vol': 56}), (2,  'C#6', 1, {'vol': 60}), (3,  'F#6', 1, {'vol': 62}),
        (4,  'E6',  1, {'vol': 58}), (5,  'C#6', 1, {'vol': 56}), (6,  'A5',  1, {'vol': 58}), (7,  'F#5', 1, {'vol': 56}),
        (8,  'G#5', 1, {'vol': 58}), (9,  'A5',  1, {'vol': 58}), (10, 'C#6', 1, {'vol': 60}), (11, 'A5',  1, {'vol': 56}),
        (12, 'F#5', 2, {'vol': 60, 'retrig': 3}), (14, 'C#5', 1, {'vol': 56}), (15, 'F#5', 1, {'vol': 58}),
        (16, 'G#5', 1, {'vol': 60}), (17, 'B5',  1, {'vol': 58}), (18, 'E6',  1, {'vol': 62}), (19, 'B5',  1, {'vol': 58}),
        (20, 'G#5', 1, {'vol': 58}), (21, 'E5',  1, {'vol': 54}), (22, 'G#5', 1, {'vol': 58}), (23, 'B5',  1, {'vol': 60}),
        (24, 'E6',  2, {'vol': 62, 'retrig': 3}), (26, 'D#6', 1, {'vol': 58}), (27, 'E6',  1, {'vol': 60}),
        (28, 'B5',  2, {'vol': 60}), (30, 'G#5', 1, {'vol': 58}), (31, 'B5',  1, {'vol': 58}),
        (32, 'A5',  1, {'vol': 60}), (33, 'F#5', 1, {'vol': 56}), (34, 'D5',  1, {'vol': 54}), (35, 'F#5', 1, {'vol': 58}),
        (36, 'A5',  1, {'vol': 60}), (37, 'D6',  1, {'vol': 62}), (38, 'F#6', 1, {'vol': 62}), (39, 'D6',  1, {'vol': 58}),
        (40, 'E6',  2, {'vol': 62, 'slide': 0x20}), (42, 'D6',  1, {'vol': 58}), (43, 'C#6', 1, {'vol': 58}),
        (44, 'A5',  2, {'vol': 60}), (46, 'F#5', 1, {'vol': 56}), (47, 'A5',  1, {'vol': 58}),
        (48, 'G#5', 1, {'vol': 60}), (49, 'F5',  1, {'vol': 58}), (50, 'C#5', 1, {'vol': 56}), (51, 'F5',  1, {'vol': 58}),
        (52, 'G#5', 1, {'vol': 60}), (53, 'B5',  1, {'vol': 60}), (54, 'C#6', 1, {'vol': 62}), (55, 'F6',  1, {'vol': 62}),
        (56, 'G#6', 2, {'vol': 60, 'retrig': 3}), (58, 'F6',  1, {'vol': 60}), (59, 'C#6', 1, {'vol': 58}),
        (60, 'B5',  1, {'vol': 58}), (61, 'G#5', 1, {'vol': 58}), (62, 'F5',  1, {'vol': 56}), (63, 'G#5', 1, {'vol': 58}),
    ]
    write_melody(p, CH_SAW, INS_SAW, solo_saw, default_vol=60, echo_ch=CH_ECHO, echo_vol=26)

    # Punchy harmonic accents + C#7 047 harmonic minor shred flash on Hero Lead!
    lead_acc = [
        (0, 'F#5', 3, {'vol': 44}), (12, 'A5', 3, {'vol': 44}),
        (16, 'G#5', 3, {'vol': 44}), (28, 'E5', 3, {'vol': 44}),
        (32, 'F#5', 3, {'vol': 44}), (44, 'D5', 3, {'vol': 44}),
        (48, 'C#5', 4, {'vol': 46, 'arp': 0x47}), (56, 'G#5', 4, {'vol': 48}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, lead_acc, default_vol=46)
    return p


def pat12_d1b():
    """Pat 12: SECTION D1b — Call-and-Response Duel + Dramatic 2-Beat Solo Spotlight Break!"""
    p = Pattern(64, 16)
    chords = [('Bm7', None), ('E7', None), ('Amaj7', None), ('C#7', None)]
    register_chords(12, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='solo', clap=True, fill=('tom_desc' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='solo')
        write_bar_arps(p, b, ca, cb, style='dual', vol1=44, vol2=38)
        write_bar_brass(p, b, ca, cb, hits=[(0, 2), (6, 2), (12, 2)], vol=34)

    # DRAMATIC 2-BEAT SOLO BREAK (rows 48..55): Kick, Snare, Bass drop out -> Supersaw shreds solo, then FULL BAND SLAMS BACK on row 56!!
    for r in range(48, 56):
        for c in (CH_KICK, CH_SNARE, CH_CLAP, CH_HAT, CH_BASS, CH_BASS2, CH_PAD1, CH_PAD2, CH_PAD3):
            p.cells[r][c] = [0, 0, 0, 0, 0]
    p.set(48, CH_BASS, note='C#2', inst=INS_BASS); p.set_vol(48, CH_BASS, 48)
    p.set(50, CH_BASS, note='OFF')
    p.set(48, CH_KICK, note='C-4', inst=INS_KICK); p.set_vol(48, CH_KICK, 52)
    p.set(48, CH_PERC, note='C-4', inst=INS_LASER); p.set_vol(48, CH_PERC, 42)
    # Full slam back on row 56!
    p.set(56, CH_PERC, note='C-4', inst=INS_CRASH, eff=0x08, param=64); p.set_vol(56, CH_PERC, 44)

    lead_duel = [
        (0,  'B5',  2, {'vol': 60}), (2,  'D6',  1, {'vol': 58}), (3,  'C#6', 1, {'vol': 56}),
        (4,  'B5',  1, {'vol': 58}), (5,  'A5',  1, {'vol': 56}), (6,  'F#5', 2, {'vol': 58}),
        (8,  'D5',  1, {'vol': 54}), (9,  'F#5', 1, {'vol': 56}), (10, 'A5',  1, {'vol': 58}), (11, 'B5', 1, {'vol': 60}),
        (12, 'D6',  2, {'vol': 62, 'retrig': 3}), (14, 'C#6', 2, {'vol': 58}),
        (32, 'C#6', 2, {'vol': 60}), (34, 'E6',  1, {'vol': 60}), (35, 'D6',  1, {'vol': 58}),
        (36, 'C#6', 1, {'vol': 58}), (37, 'B5',  1, {'vol': 56}), (38, 'A5',  2, {'vol': 58}),
        (40, 'E5',  1, {'vol': 54}), (41, 'A5',  1, {'vol': 56}), (42, 'C#6', 1, {'vol': 60}), (43, 'E6', 1, {'vol': 62}),
        (44, 'G#5', 2, {'vol': 58}), (46, 'A5',  2, {'vol': 60, 'slide': 0x20}),
        (56, 'C#6', 2, {'vol': 60}), (58, 'B5',  2, {'vol': 58}),
        (60, 'G#5', 2, {'vol': 58}), (62, 'F5',  2, {'vol': 58}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, lead_duel, default_vol=58, echo_ch=CH_ECHO, echo_vol=26)

    saw_duel = [
        (16, 'B5',  2, {'vol': 60}), (18, 'E6',  1, {'vol': 62}), (19, 'D6',  1, {'vol': 58}),
        (20, 'B5',  1, {'vol': 58}), (21, 'G#5', 1, {'vol': 56}), (22, 'E5',  2, {'vol': 56}),
        (24, 'G#5', 1, {'vol': 56}), (25, 'B5',  1, {'vol': 58}), (26, 'D6',  1, {'vol': 60}), (27, 'E6', 1, {'vol': 62}),
        (28, 'D6',  2, {'vol': 60, 'retrig': 3}), (30, 'B5',  2, {'vol': 58}),
        # SPOTLIGHT BREAK SHRED!!
        (48, 'F5',  1, {'vol': 60}), (49, 'G#5', 1, {'vol': 60}), (50, 'B5',  1, {'vol': 62}), (51, 'C#6', 1, {'vol': 62}),
        (52, 'F6',  2, {'vol': 64, 'retrig': 3}), (54, 'C#6', 2, {'vol': 60}),
        (56, 'F6',  2, {'vol': 62}), (58, 'D6',  2, {'vol': 58}),
        (60, 'B5',  2, {'vol': 58}), (62, 'G#5', 2, {'vol': 58}),
    ]
    write_melody(p, CH_SAW, INS_SAW, saw_duel, default_vol=58)
    return p


def pat13_d2a():
    """Pat 13: SECTION D2a — Twin-Lead Harmonized Shred Climax!"""
    p = Pattern(64, 16)
    chords = [('Dmaj7', None), ('E', None), ('F#m', None), ('A/E', None)]
    register_chords(13, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='solo', crash=(b == 0), clap=True, fill=('snare_pick' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='solo')
        write_bar_arps(p, b, ca, cb, style='cascade', vol1=46, vol2=40)
        write_bar_bell_sparkles(p, b, ca, cb, pattern_kind='offbeat', vol=40)

    top = [
        (0,  'F#5', 2, {'vol': 58}), (2,  'A5',  2, {'vol': 58}), (4,  'D6',  3, {'vol': 60}), (7,  'C#6', 1, {'vol': 56}),
        (8,  'B5',  2, {'vol': 58}), (10, 'A5',  2, {'vol': 58}), (12, 'F#5', 2, {'vol': 58}), (14, 'A5',  2, {'vol': 58}),
        (16, 'G#5', 2, {'vol': 58}), (18, 'B5',  2, {'vol': 60}), (20, 'E6',  3, {'vol': 62}), (23, 'D6',  1, {'vol': 58}),
        (24, 'C#6', 2, {'vol': 60}), (26, 'B5',  2, {'vol': 58}), (28, 'G#5', 2, {'vol': 58}), (30, 'B5',  2, {'vol': 60}),
        (32, 'A5',  2, {'vol': 60}), (34, 'C#6', 2, {'vol': 60}), (36, 'F#6', 3, {'vol': 62}), (39, 'E6',  1, {'vol': 58}),
        (40, 'C#6', 2, {'vol': 60}), (42, 'A5',  2, {'vol': 58}), (44, 'C#6', 2, {'vol': 60}), (46, 'E6',  2, {'vol': 60}),
        (48, 'E6',  3, {'vol': 62, 'retrig': 3}), (51, 'C#6', 1, {'vol': 58}),
        (52, 'A5',  2, {'vol': 58}), (54, 'C#6', 2, {'vol': 60}),
        (56, 'E6',  2, {'vol': 62}), (58, 'C#6', 2, {'vol': 60}), (60, 'B5',  2, {'vol': 58}), (62, 'A5',  2, {'vol': 58}),
    ]
    bot = [
        (0,  'D5',  2, {'vol': 50}), (2,  'F#5', 2, {'vol': 50}), (4,  'A5',  3, {'vol': 52}), (7,  'A5',  1, {'vol': 48}),
        (8,  'F#5', 2, {'vol': 50}), (10, 'F#5', 2, {'vol': 50}), (12, 'D5',  2, {'vol': 50}), (14, 'F#5', 2, {'vol': 50}),
        (16, 'E5',  2, {'vol': 50}), (18, 'G#5', 2, {'vol': 52}), (20, 'B5',  3, {'vol': 54}), (23, 'B5',  1, {'vol': 50}),
        (24, 'G#5', 2, {'vol': 52}), (26, 'G#5', 2, {'vol': 50}), (28, 'E5',  2, {'vol': 50}), (30, 'G#5', 2, {'vol': 52}),
        (32, 'F#5', 2, {'vol': 52}), (34, 'A5',  2, {'vol': 52}), (36, 'C#6', 3, {'vol': 54}), (39, 'C#6', 1, {'vol': 50}),
        (40, 'A5',  2, {'vol': 52}), (42, 'F#5', 2, {'vol': 50}), (44, 'A5',  2, {'vol': 52}), (46, 'C#6', 2, {'vol': 52}),
        (48, 'C#6', 3, {'vol': 54, 'retrig': 3}), (51, 'A5',  1, {'vol': 50}),
        (52, 'E5',  2, {'vol': 50}), (54, 'A5',  2, {'vol': 52}),
        (56, 'C#6', 2, {'vol': 54}), (58, 'A5',  2, {'vol': 52}), (60, 'G#5', 2, {'vol': 50}), (62, 'E5',  2, {'vol': 50}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, top, default_vol=60, echo_ch=CH_ECHO, echo_vol=26)
    write_melody(p, CH_SAW, INS_SAW, bot, default_vol=52)
    return p


def pat14_d2b():
    """Pat 14: SECTION D2b — Twin-Lead Climax -> Launch to Final Super-Chorus!"""
    p = Pattern(64, 16)
    chords = [('Dmaj7', None), ('Bm7', None), ('E7sus4', None), ('E7', None)]
    register_chords(14, chords)
    for b, (ca, cb) in enumerate(chords):
        write_bar_drums(p, b, style='solo', clap=True, fill=('tom_riser_big' if b == 3 else None))
        write_bar_bass(p, b, ca, cb, style='solo')
        write_bar_arps(p, b, ca, cb, style='shimmer' if b >= 2 else 'cascade', vol1=46, vol2=42)
        write_bar_pad(p, b, ca, cb, vol=24 if b < 3 else 22, release_end=(b == 3))

    top = [
        (0,  'A5',  2, {'vol': 58}), (2,  'B5',  2, {'vol': 58}), (4,  'C#6', 2, {'vol': 60}), (6,  'D6',  2, {'vol': 60}),
        (8,  'F#6', 3, {'vol': 60}), (11, 'E6',  1, {'vol': 56}), (12, 'D6',  2, {'vol': 58}), (14, 'A5',  2, {'vol': 56}),
        (16, 'B5',  2, {'vol': 58}), (18, 'D6',  2, {'vol': 58}), (20, 'F#6', 3, {'vol': 60}), (23, 'E6',  1, {'vol': 56}),
        (24, 'D6',  2, {'vol': 58}), (26, 'B5',  2, {'vol': 56}), (28, 'A5',  2, {'vol': 56}), (30, 'B5',  2, {'vol': 58}),
        (32, 'A5',  4, {'vol': 58, 'vib_cont': 0x44}), (36, 'B5',  4, {'vol': 58, 'vib_cont': 0x44}),
        (40, 'D6',  4, {'vol': 60, 'vib_cont': 0x44}), (44, 'E6',  4, {'vol': 60, 'vib_cont': 0x44}),
        (48, 'G#5', 1, {'vol': 56}), (49, 'B5',  1, {'vol': 56}), (50, 'D6',  1, {'vol': 58}), (51, 'E6',  1, {'vol': 58}),
        (52, 'G#5', 1, {'vol': 56}), (53, 'B5',  1, {'vol': 56}), (54, 'D6',  1, {'vol': 58}), (55, 'E6',  1, {'vol': 60}),
        (56, 'B5',  2, {'vol': 58}), (58, 'C#6', 2, {'vol': 58}), (60, 'D6',  2, {'vol': 60}), (62, 'E6',  2, {'vol': 60}),
    ]
    bot = [
        (0,  'F#5', 2, {'vol': 48}), (2,  'G#5', 2, {'vol': 48}), (4,  'A5',  2, {'vol': 50}), (6,  'A5',  2, {'vol': 50}),
        (8,  'D6',  3, {'vol': 52}), (11, 'C#6', 1, {'vol': 48}), (12, 'A5',  2, {'vol': 50}), (14, 'F#5', 2, {'vol': 48}),
        (16, 'F#5', 2, {'vol': 50}), (18, 'B5',  2, {'vol': 50}), (20, 'D6',  3, {'vol': 52}), (23, 'C#6', 1, {'vol': 48}),
        (24, 'B5',  2, {'vol': 50}), (26, 'F#5', 2, {'vol': 48}), (28, 'F#5', 2, {'vol': 48}), (30, 'G#5', 2, {'vol': 50}),
        (32, 'E5',  4, {'vol': 50}), (36, 'A5',  4, {'vol': 50}), (40, 'B5',  4, {'vol': 52}), (44, 'B5',  4, {'vol': 52}),
        (48, 'E5',  1, {'vol': 48}), (49, 'G#5', 1, {'vol': 48}), (50, 'B5',  1, {'vol': 50}), (51, 'D6',  1, {'vol': 50}),
        (52, 'E5',  1, {'vol': 48}), (53, 'G#5', 1, {'vol': 48}), (54, 'B5',  1, {'vol': 50}), (55, 'D6',  1, {'vol': 52}),
        (56, 'G#5', 2, {'vol': 50}), (58, 'A5',  2, {'vol': 50}), (60, 'B5',  2, {'vol': 52}), (62, 'B5',  2, {'vol': 52}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, top, default_vol=58, echo_ch=CH_ECHO, echo_vol=24)
    write_melody(p, CH_SAW, INS_SAW, bot, default_vol=50)
    return p


def pat17_turnaround():
    """Pat 17: SECTION E — Turbo Turnaround / Slingshot to Pos 1 (LOOP_START on F#m!)."""
    p = Pattern(64, 16)
    chords = [('Dmaj7', None), ('E', None), ('F#m', 'Bm7'), ('C#7sus4', 'C#7')]
    register_chords(17, chords)
    for b, (ca, cb) in enumerate(chords):
        fill = 'slingshot_loop' if b == 3 else None
        write_bar_drums(p, b, style='turnaround', crash=(b == 0), clap=True, fill=fill)
        write_bar_bass(p, b, ca, cb, style='stops' if b == 2 else 'bounce')
        write_bar_arps(p, b, ca, cb, style='shimmer', vol1=46, vol2=42)
        if b == 2:
            write_bar_brass(p, b, ca, cb, hits=[(0, 2), (3, 2), (6, 2), (8, 2), (11, 2), (14, 2)], vol=36)
        elif b == 3:
            write_bar_brass(p, b, ca, cb, hits=[(0, 3), (4, 3), (8, 2)], vol=36)
        else:
            write_bar_brass(p, b, ca, cb, hits=[(0, 3), (6, 2), (10, 2)], vol=34)

    bell_cb = [
        (0,  'F#5', 3, {'vol': 50, 'pan': 48}),  (3,  'D5',  3, {'vol': 46, 'pan': 208}),
        (6,  'A4',  2, {'vol': 48, 'pan': 76}),  (8,  'C#5', 2, {'vol': 48, 'pan': 184}),
        (10, 'D5',  2, {'vol': 50, 'pan': 60}),  (12, 'A5',  4, {'vol': 52, 'pan': 212}),
        (16, 'G#5', 3, {'vol': 50, 'pan': 48}),  (19, 'E5',  3, {'vol': 46, 'pan': 208}),
        (22, 'B4',  2, {'vol': 48, 'pan': 76}),  (24, 'E5',  2, {'vol': 48, 'pan': 184}),
        (26, 'G#5', 2, {'vol': 50, 'pan': 60}),  (28, 'B5',  4, {'vol': 52, 'pan': 212}),
        (32, 'F#5', 2, {'vol': 52, 'pan': 56}),  (35, 'A5',  2, {'vol': 52, 'pan': 204}),
        (38, 'C#6', 2, {'vol': 54, 'pan': 68}),  (40, 'B5',  2, {'vol': 52, 'pan': 192}),
        (43, 'F#5', 2, {'vol': 52, 'pan': 76}),  (46, 'D5',  2, {'vol': 50, 'pan': 184}),
        (48, 'G#5', 2, {'vol': 52, 'pan': 68}),  (52, 'F5',  2, {'vol': 54, 'pan': 192}),
        (56, 'C#6', 2, {'vol': 54, 'pan': 128}),
    ]
    write_melody(p, CH_BELL, INS_BELL, bell_cb, default_vol=50)

    lead_end = [
        (0,  'D6',  3, {'vol': 58}), (3,  'C#6', 1, {'vol': 54}), (4,  'A5',  2, {'vol': 56}), (6,  'F#5', 2, {'vol': 54}),
        (8,  'A5',  4, {'vol': 58}), (12, 'C#6', 4, {'vol': 60}),
        (16, 'B5',  3, {'vol': 58}), (19, 'C#6', 1, {'vol': 56}), (20, 'B5',  2, {'vol': 58}), (22, 'G#5', 2, {'vol': 56}),
        (24, 'B5',  4, {'vol': 58}), (28, 'E6',  4, {'vol': 60}),
        (32, 'F#5', 2, {'vol': 60}), (35, 'A5',  2, {'vol': 60}), (38, 'C#6', 2, {'vol': 60}),
        (40, 'D6',  2, {'vol': 60}), (43, 'B5',  2, {'vol': 58}), (46, 'F#5', 2, {'vol': 58}),
        (48, 'G#5', 3, {'vol': 60}), (51, 'F#5', 1, {'vol': 56}),
        (52, 'F5',  2, {'vol': 60}), (54, 'G#5', 2, {'vol': 60}),
        (56, 'B5',  2, {'vol': 60}), (58, 'G#5', 2, {'vol': 58}),
        (60, 'F5',  2, {'vol': 58, 'no_echo': True}), (62, 'G#5', 2, {'vol': 60, 'no_echo': True}),
    ]
    write_melody(p, CH_LEAD, INS_LEAD, lead_end, default_vol=58, echo_ch=CH_ECHO, echo_vol=26)

    saw_end = [
        (0,  'A5',  4, {'vol': 48}), (4,  'F#5', 4, {'vol': 48}), (8,  'F#5', 4, {'vol': 48}), (12, 'A5',  4, {'vol': 50}),
        (16, 'G#5', 4, {'vol': 50}), (20, 'E5',  4, {'vol': 48}), (24, 'G#5', 4, {'vol': 50}), (28, 'B5',  4, {'vol': 52}),
        (32, 'C#5', 2, {'vol': 50}), (35, 'F#5', 2, {'vol': 50}), (38, 'A5',  2, {'vol': 50}),
        (40, 'B5',  2, {'vol': 50}), (43, 'F#5', 2, {'vol': 48}), (46, 'D5',  2, {'vol': 48}),
        (48, 'F#5', 3, {'vol': 50}), (51, 'F5',  1, {'vol': 50}), (52, 'C#5', 2, {'vol': 50}), (54, 'F5', 2, {'vol': 52}),
        (56, 'G#5', 2, {'vol': 52}), (58, 'F5',  2, {'vol': 50}), (60, 'C#5', 2, {'vol': 48}),
    ]
    write_melody(p, CH_SAW, INS_SAW, saw_end, default_vol=50)

    # Clean loop-seam exit into Pos 1 (F#m)!
    p.set(62, CH_SAW, note='OFF')
    p.set(62, CH_ECHO, note='OFF')
    for c in (CH_PAD1, CH_PAD2, CH_PAD3):
        p.set(62, c, note='OFF')
    for r in range(56, 64):
        p.cells[r][CH_BASS] = [0, 0, 0, 0, 0]
        p.cells[r][CH_BASS2] = [0, 0, 0, 0, 0]
    p.set(56, CH_BASS, note='C#2', inst=INS_BASS, eff=0x0A, param=0x40); p.set_vol(56, CH_BASS, 30)
    p.set(58, CH_BASS2, note='C#3', inst=INS_BASS2); p.set_vol(58, CH_BASS2, 42); p.set(58, CH_BASS, note='OFF')
    p.set(60, CH_BASS, note='G#1', inst=INS_BASS); p.set_vol(60, CH_BASS, 44); p.set(60, CH_BASS2, note='OFF')
    p.set(62, CH_BASS, note='C#2', inst=INS_BASS); p.set_vol(62, CH_BASS, 48)
    return p


def verify_harmony(patterns):
    NOTE_PC = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    pitched_chs = (CH_BASS, CH_BASS2, CH_LEAD, CH_ARP1, CH_ARP2, CH_BELL, CH_SAW, CH_PAD1, CH_PAD2, CH_PAD3)
    issues = []
    for pat_idx, chords in PATTERN_CHORD_MAP:
        pat = patterns[pat_idx]
        for r in range(64):
            b = r // 16
            step = r % 16
            ca, cb = chords[b]
            cname = ca if (step < 8 or cb is None) else cb
            allowed = CHORDS[cname]['scale']
            for ch in pitched_chs:
                note, inst, vol, eff, param = pat.cells[r][ch]
                if 1 <= note <= 96:
                    pc = (note - 1) % 12
                    if pc not in allowed:
                        issues.append((pat_idx, r, ch, f"{NOTE_PC[pc]}{(note-1)//12}", cname))
                    if eff == 0x00 and param != 0:
                        x, y = (param >> 4) & 0xF, param & 0xF
                        for off in (x, y):
                            apc = (note - 1 + off) % 12
                            if apc not in allowed:
                                issues.append((pat_idx, r, ch, f"ARP+{off}({NOTE_PC[apc]})", cname))
    return issues


def build_song(out_path='/workspace/work/neon_cipher.xm', duplicate_loop_for_test=False):
    PATTERN_CHORD_MAP.clear()
    xm = XMModule(name="NEON CIPHER", channels=16, bpm=140, speed=6, restart_pos=1)
    for ins in build_all_instruments():
        xm.add_instrument(ins)

    pats = [
        pat0_intro(),                              # 0:  Intro
        pat1_a1a(),                                # 1:  A1a [LOOP_START]
        pat2_a1b(),                                # 2:  A1b
        pat3_a2a(),                                # 3:  A2a
        pat4_a2b(),                                # 4:  A2b
        pat5_b1a(5, variant='b1'),                 # 5:  B1a
        pat6_b1b(),                                # 6:  B1b
        pat5_b1a(7, variant='b2'),                 # 7:  B2a
        pat8_b2b(8, to_breakdown=True),            # 8:  B2b
        pat9_c1(),                                 # 9:  C1
        pat10_c2(),                                # 10: C2
        pat11_d1a(),                               # 11: D1a
        pat12_d1b(),                               # 12: D1b
        pat13_d2a(),                               # 13: D2a
        pat14_d2b(),                               # 14: D2b
        pat5_b1a(15, variant='b3'),                # 15: B3a
        pat8_b2b(16, to_breakdown=False),          # 16: B3b
        pat17_turnaround(),                        # 17: E Turnaround
    ]
    for p in pats:
        xm.add_pattern(p)

    issues = verify_harmony(pats)
    if not duplicate_loop_for_test:
        print(f"HARMONY VERIFIER: {len(issues)} out-of-scale notes across all 18 patterns (1152 rows x 10 pitched chs)!")
        for iss in issues[:20]:
            print("  ISSUE:", iss)

    if duplicate_loop_for_test:
        xm.order = [17, 1]
        xm.restart_pos = 0
    else:
        xm.order = list(range(len(pats)))
        xm.restart_pos = 1

    xm.save(out_path)
    return xm


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work/neon_cipher.xm'
    xm = build_song(out)
    print(f"Saved {out}: {len(xm.patterns)} patterns, {len(xm.instruments)} instruments")
    build_song('/workspace/work/loop_seam_test.xm', duplicate_loop_for_test=True)
