import sys
sys.path.insert(0, '.')
import music_theory as mt
from instruments import CHANNEL_OF, INSTRUMENT_OF
from ft2lib import run_batch, call

ROWS_PER_BAR = 16

def note_cell(pattern, row, part, midi_note, volume=60, effect=None, effect_param=None):
    ch = CHANNEL_OF[part]
    inst = INSTRUMENT_OF[part]
    args = {"pattern": pattern, "row": row, "channel": ch,
            "note": mt.xm_note(midi_note), "instrument": inst, "volume": volume}
    if effect is not None:
        args["effect"] = effect
        args["effect_param"] = effect_param
    return {"name": "pattern_set_cell", "arguments": args}

def fx_cell(pattern, row, part, effect, effect_param):
    ch = CHANNEL_OF[part]
    args = {"pattern": pattern, "row": row, "channel": ch,
            "effect": effect, "effect_param": effect_param}
    return {"name": "pattern_set_cell", "arguments": args}

# ---------------------------------------------------------------------
# Generic rhythm generators (bar-relative row offsets; caller supplies
# the bar's absolute starting row).
# ---------------------------------------------------------------------

def bass_riff(base_row, root, variant='a', volume=62):
    """One bar (16 rows) of bass events relative to base_row.
    root: midi note of the chord root (we use a low octave)."""
    patterns = {
        'a': [(0, 0), (2, 0), (4, 12), (6, 0), (8, 0), (10, 7), (12, 0), (14, 12)],
        'b': [(0, 0), (4, 12), (6, 0), (10, 7), (12, 12), (14, 10)],
        'c': [(0, 0), (2, 0), (4, 12), (6, 7), (8, 0), (10, 12), (12, 7), (14, 12)],
        'sustain': [(0, 0)],
        'g_push': [(0, 0), (2, 0), (4, 0), (6, 12), (8, 0), (10, 0), (12, 7), (14, 12)],
    }
    out = []
    for off, iv in patterns[variant]:
        out.append((base_row + off, root + iv, volume))
    return out

ARP_SHAPE_UP = [0, 1, 2, 1]
ARP_SHAPE_UPDOWN = [0, 1, 2, 3, 2, 1, 0, 1]
ARP_SHAPE_PULSE = [0, 1, 2, 1, 0, 2, 1, 2]

def arp_riff(base_row, chord, shape=ARP_SHAPE_UPDOWN, step=2, volume=50, octave_up_last=False):
    tones = list(chord) + [chord[0] + 12]
    out = []
    n_steps = ROWS_PER_BAR // step
    for i in range(n_steps):
        row = base_row + i * step
        deg = shape[i % len(shape)]
        out.append((row, tones[deg], volume))
    return out

def drum_hits(base_row, rows, instrument_key, volume=60):
    return [(base_row + r, instrument_key, volume) for r in rows]

KICK_STRAIGHT = [0, 4, 8, 12]
KICK_SYNCO    = [0, 4, 8, 11, 12]
SNARE_BACKBEAT = [4, 12]
HAT_8TH = [0, 2, 4, 6, 8, 10, 12, 14]
HAT_16TH = list(range(0, 16))

def place(calls, pattern, events, part):
    for row, midi_note, vol in events:
        calls.append(note_cell(pattern, row, part, midi_note, vol))

def place_drum(calls, pattern, rows, part, volume=60):
    for row in rows:
        ch = CHANNEL_OF[part]
        inst = INSTRUMENT_OF[part]
        calls.append({"name": "pattern_set_cell", "arguments": {
            "pattern": pattern, "row": row, "channel": ch,
            "note": mt.xm_note(mt.midi(mt.C, 4)), "instrument": inst, "volume": volume}})

def add_vibrato(calls, pattern, motif, part, total_rows, min_dur=4, speed=3, depth=4):
    """Continue a gentle vibrato (effect 4) for the sustain of any note in
    `motif` that lasts at least min_dur rows before the next event (or the
    end of the pattern)."""
    events = sorted(motif, key=lambda e: e[0])
    ch = CHANNEL_OF[part]
    param = (speed << 4) | depth
    for i, (row, m, v) in enumerate(events):
        nxt = events[i + 1][0] if i + 1 < len(events) else total_rows
        dur = nxt - row
        if dur >= min_dur:
            # start one row after the trigger (never touch the row that
            # already holds the note -- pattern_set_cell overwrites the
            # whole cell, so re-stating only the effect there would wipe
            # the note/instrument/volume) and stop one row early so the
            # vibrato doesn't bleed into the next note's attack.
            for r in range(row + 1, nxt - 1):
                calls.append({"name": "pattern_set_cell", "arguments": {
                    "pattern": pattern, "row": r, "channel": ch,
                    "effect": 4, "effect_param": param}})

def arp_stab(calls, pattern, channel_part, row, root_midi, param, hold_rows=9, volume=40):
    """A short XM-style 0xy arpeggio stab: trigger the note with the
    arpeggio effect, then restate the effect for a few more rows so it
    keeps warbling for as long as the pluck is actually audible."""
    ch = CHANNEL_OF[channel_part]
    inst = INSTRUMENT_OF[channel_part]
    calls.append({"name": "pattern_set_cell", "arguments": {
        "pattern": pattern, "row": row, "channel": ch,
        "note": mt.xm_note(root_midi), "instrument": inst, "volume": volume,
        "effect": 0, "effect_param": param}})
    for r in range(row + 1, row + hold_rows):
        calls.append({"name": "pattern_set_cell", "arguments": {
            "pattern": pattern, "row": r, "channel": ch,
            "effect": 0, "effect_param": param}})
