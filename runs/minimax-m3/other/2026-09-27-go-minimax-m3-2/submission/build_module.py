"""
Build the keygen tune tracker module.
v7: Add crash on row 8 of P3 for impact, vibrato on lead.
"""

import json

def note(octave, semi):
    return octave * 12 + semi + 1

C  = lambda o: note(o, 0)
D  = lambda o: note(o, 2)
E  = lambda o: note(o, 4)
F  = lambda o: note(o, 5)
G  = lambda o: note(o, 7)
A  = lambda o: note(o, 9)
B  = lambda o: note(o, 11)
REST = 0

LEAD = 1; PLUCK = 2; PAD = 3; BASS = 4; KICK = 5; SNARE = 6
CHAT = 7; OHAT = 8; CRASH = 9; TOM = 10; ORGAN = 11; ARP = 12

SAMPLE_RELNOTE = {
    'lead':   65 - 61, 'pluck': 65 - 61, 'pad': 65 - 49,
    'bass':   65 - 25, 'kick': 0, 'snare': 0, 'chat': 0, 'ohat': 0,
    'crash':  0, 'tom': 0, 'organ': 65 - 49, 'arp': 65 - 61,
}

def empty_cells(nc=8, nr=16):
    return [[None] * nc for _ in range(nr)]
def set_cell(cells, row, ch, note_v, instr=0, vol=0, fx=0, fxp=0):
    cells[row][ch] = (note_v, instr, vol, fx, fxp)

def standard_drums(cells, with_openhat_end=True):
    for r in range(0, 16, 2):
        set_cell(cells, r, 7, REST, CHAT, 48, 0, 0)
    for r in (0, 8):
        set_cell(cells, r, 5, REST, KICK, 64, 0, 0)
    for r in (4, 12):
        set_cell(cells, r, 6, REST, SNARE, 64, 0, 0)
    if with_openhat_end:
        set_cell(cells, 15, 7, REST, OHAT, 64, 0, 0)
    return cells

def bass_line(cells, notes, ch=4, instr=BASS, vol=64):
    for i, r in enumerate((0, 4, 8, 12)):
        if i < len(notes) and notes[i] is not None:
            set_cell(cells, r, ch, notes[i], instr, vol, 0, 0)
    return cells

def lead_eighths(cells, notes, ch=0, instr=LEAD, vol=64, fx=0, fxp=0):
    for i, r in enumerate(range(0, 16, 2)):
        if i < len(notes) and notes[i] is not None:
            if fx:
                set_cell(cells, r, ch, notes[i], instr, vol, fx, fxp)
            else:
                set_cell(cells, r, ch, notes[i], instr, vol, 0, 0)
    return cells

def counter_phrase(cells, notes, ch=1, instr=ARP, vol=48):
    for i, r in enumerate((2, 6, 10, 14)):
        if i < len(notes) and notes[i] is not None:
            set_cell(cells, r, ch, notes[i], instr, vol, 0, 0)
    return cells

def pad_chord(cells, chord_notes, ch=2, instr=PAD, vol=48):
    for n_v in chord_notes:
        if n_v is not None:
            set_cell(cells, 0, ch, n_v, instr, vol, 0, 0)
    return cells

def organ_arpeggio(cells, arp_notes, ch=3, instr=ORGAN, vol=56):
    for i, r in enumerate((0, 4, 8, 12)):
        if i < len(arp_notes) and arp_notes[i] is not None:
            set_cell(cells, r, ch, arp_notes[i], instr, vol, 0, 0)
    return cells

def Am_bass(): return [A(2), E(3), A(2), A(2)]
def F_bass():  return [F(2), C(3), F(2), F(2)]
def C_bass():  return [C(2), G(2), C(2), E(3)]
def G_bass():  return [G(2), D(3), G(2), B(2)]
def Dm_bass(): return [D(2), A(2), D(2), F(2)]
def Am_pad(): return [A(3), C(4), E(4)]
def F_pad():  return [F(3), A(3), C(4)]
def C_pad():  return [C(3), E(3), G(3)]
def G_pad():  return [G(3), B(3), D(4)]
def Dm_pad(): return [D(3), F(3), A(3)]
def Am_org(): return [A(4), C(5), E(5), A(4)]
def F_org():  return [F(4), A(4), C(5), F(4)]
def C_org():  return [C(4), E(4), G(4), C(5)]
def G_org():  return [G(4), B(4), D(5), G(4)]
def Dm_org(): return [D(4), F(4), A(4), D(5)]

LEADS = {
    0: [E(5), C(5), A(5), G(5), G(5), E(5), E(5), D(5)],
    1: [A(5), F(5), A(5), G(5), A(5), F(5), F(5), E(5)],
    2: [G(5), E(5), G(5), E(5), G(5), C(5), E(5), G(5)],
    3: [D(5), B(4), D(5), B(4), D(5), G(4), B(4), D(5)],
    4: [D(5), A(4), F(4), A(4), D(5), A(4), F(4), A(4)],
    5: [A(5), E(5), C(5), E(5), A(5), E(5), C(5), A(4)],
}
ARPS = {
    0: [E(5), G(5), D(5), C(5)],
    1: [F(5), C(5), E(5), A(5)],
    2: [E(5), C(5), B(4), A(4)],
    3: [B(4), G(4), A(4), B(4)],
    4: [A(4), D(5), A(4), F(4)],
    5: [E(5), C(5), A(4), E(5)],
}
BASSES = {0: Am_bass(), 1: F_bass(), 2: C_bass(), 3: G_bass(),
          4: Dm_bass(), 5: Am_bass()}
PADS = {0: Am_pad(), 1: F_pad(), 2: C_pad(), 3: G_pad(),
        4: Dm_pad(), 5: None}
ORGS = {0: Am_org(), 1: F_org(), 2: C_org(), 3: G_org(),
        4: Dm_org(), 5: Am_org()}

patterns = []
for p_idx in range(6):
    cells = empty_cells()
    standard_drums(cells, with_openhat_end=(p_idx < 4))
    bass_line(cells, BASSES[p_idx])
    lead_eighths(cells, LEADS[p_idx])
    counter_phrase(cells, ARPS[p_idx])
    pad_notes = PADS[p_idx]
    if pad_notes is not None:
        pad_chord(cells, pad_notes)
    organ_arpeggio(cells, ORGS[p_idx])
    patterns.append(cells)

batch_calls = []

samples = [(1,'lead'),(2,'pluck'),(3,'pad'),(4,'bass'),(5,'kick'),(6,'snare'),
           (7,'chat'),(8,'ohat'),(9,'crash'),(10,'tom'),(11,'organ'),(12,'arp')]
for ins, name in samples:
    batch_calls.append({"name": "sample_load",
        "arguments": {"path": f"/workspace/work/samples/{name}.wav", "instrument": ins}})

sample_vol = {'lead':50,'pluck':50,'pad':55,'bass':64,'kick':64,'snare':64,
              'chat':48,'ohat':50,'crash':56,'tom':56,'organ':48,'arp':48}

for ins, name in samples:
    batch_calls.append({"name": "instrument_set",
        "arguments": {"instrument": ins, "name": name}})
    batch_calls.append({"name": "sample_set",
        "arguments": {"instrument": ins, "sample": 0, "name": name,
                       "volume": sample_vol[name],
                       "relative_note": SAMPLE_RELNOTE[name]}})

for p_idx in range(6):
    batch_calls.append({"name": "pattern_set_length",
        "arguments": {"pattern": p_idx, "rows": 16}})

batch_calls.append({"name": "song_set",
    "arguments": {"name": "PROMETHEUS KEYGEN", "bpm": 132, "speed": 6,
                  "length": 6, "loop_start": 0, "channels": 8}})

for i in range(6):
    batch_calls.append({"name": "order_set",
        "arguments": {"position": i, "pattern": i}})

for p_idx, cells in enumerate(patterns):
    for row, row_cells in enumerate(cells):
        for ch, cell in enumerate(row_cells):
            if cell is not None:
                note_v, instr, vol, fx, fxp = cell
                batch_calls.append({"name": "pattern_set_cell",
                    "arguments": {"pattern": p_idx, "row": row, "channel": ch,
                                  "note": note_v, "instrument": instr,
                                  "volume": vol, "effect": fx, "effect_param": fxp}})

with open('build_batch.json', 'w') as f:
    json.dump(batch_calls, f, indent=2)

print(f"Built batch with {len(batch_calls)} calls")
