"""Compose + build the keygen tune through the FT2 tool API."""
import json, os

BPM, SPEED = 150, 3          # clone timing: row = 5*speed/bpm = 100 ms (16th @150 BPM)
ROWS = 64                     # rows per pattern (4 bars)

# ------------------------------------------------------------------ voices
I_KICK, I_SNARE, I_HAT, I_OHAT, I_BASS, I_ARP, I_LEAD, I_CRASH = 1, 2, 3, 4, 5, 6, 7, 16
I_STAB = {'Am': 8, 'F': 9, 'C': 10, 'G': 11}
I_PAD = {'Am': 12, 'F': 13, 'C': 14, 'G': 15}

CH = {
    'Am': dict(root=45, tones=(69, 72, 76, 81), stab=57, pad=57),
    'F':  dict(root=41, tones=(65, 69, 72, 77), stab=53, pad=53),
    'C':  dict(root=48, tones=(72, 76, 79, 84), stab=48, pad=48),
    'G':  dict(root=43, tones=(67, 71, 74, 79), stab=55, pad=55),
}
PROG = ['Am', 'F', 'C', 'G']

C_KICK, C_SNARE, C_HAT, C_BASS, C_ARP, C_LEAD, C_STAB, C_PAD = range(8)


def cn(midi):
    return midi - 11          # clone note number for a MIDI note


class Pat:
    def __init__(self):
        self.cells = {}

    def put(self, row, ch, midi, inst, vol, fx=0, prm=0):
        self.cells[(row, ch)] = (cn(midi) if midi else 0, inst, vol, fx, prm)

    def inst(self, row, ch, inst, vol, fx=0, prm=0):
        old = self.cells.get((row, ch), (0, 0, 0, 0, 0))
        self.cells[(row, ch)] = (old[0], inst, vol, fx, prm)


DRUM = 60          # percussion is played at C-4 so the samples keep their level


def kick(p, bar, rows=(0, 4, 8, 12), vol=64, extra=()):
    for r in rows:
        p.put(bar * 16 + r, C_KICK, DRUM, I_KICK, vol)
    for r in extra:
        p.put(bar * 16 + r, C_KICK, DRUM, I_KICK, vol - 10)


def snare(p, bar, rows=(4, 12), vol=56, ghosts=()):
    for r in rows:
        p.put(bar * 16 + r, C_SNARE, DRUM, I_SNARE, vol)
    for r in ghosts:
        p.put(bar * 16 + r, C_SNARE, DRUM, I_SNARE, vol - 26)


def crash(p, bar, vol=44):
    p.put(bar * 16, C_SNARE, DRUM, I_CRASH, vol)


def hat(p, bar, step=2, vol=30, ohat=(), ovol=26):
    for i in range(0, 16, step):
        p.put(bar * 16 + i, C_HAT, DRUM, I_HAT, vol if i % 4 == 0 else vol - 6)
    for r in ohat:
        p.put(bar * 16 + r, C_HAT, DRUM, I_OHAT, ovol)


def bass(p, bar, chord, seq, vol=60, step=2):
    root = CH[chord]['root']
    table = {'r': root, 'f': root + 7, 'o': root + 12, 'R': root - 12, 'O': root + 24}
    for i, s in enumerate(seq):
        p.put(bar * 16 + i * step, C_BASS, table[s], I_BASS, vol)


def arp(p, bar, chord, seq, vol=34, high=False, step=1):
    tones = list(CH[chord]['tones'])
    for i, k in enumerate(seq):
        t = tones[k]
        if high and i >= 8:
            t += 12
        p.put(bar * 16 + i * step, C_ARP, t, I_ARP, vol)


def stab(p, bar, chord, rows=(0,), vol=40):
    for r in rows:
        p.put(bar * 16 + r, C_STAB, CH[chord]['stab'], I_STAB[chord], vol)


def pad(p, bar, chord, vol=32):
    p.put(bar * 16, C_PAD, CH[chord]['pad'], I_PAD[chord], vol)


def lead(p, bar, notes, vol=62):
    for off, m, ln in notes:
        p.put(bar * 16 + off, C_LEAD, m, I_LEAD, vol)


# ------------------------------------------------------------------ patterns
ARP_A = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 0, 1, 3, 2, 1, 0]
ARP_B = [0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3, 3, 2, 1, 0]
ARP_C = [0, 1, 2, 3, 1, 0, 3, 2, 0, 1, 2, 3, 3, 1, 2, 0]
BASS_A = ['r', 'r', 'f', 'r', 'r', 'f', 'r', 'o']
BASS_B = ['r', 'f', 'r', 'o', 'r', 'f', 'r', 'r']
BASS_C = ['r', 'r', 'r', 'f', 'o', 'r', 'f', 'r']

LEAD_A = [
    [(0, 76, 4), (4, 81, 2), (6, 79, 2), (8, 76, 6), (14, 74, 2)],
    [(0, 77, 4), (4, 81, 4), (8, 84, 4), (12, 81, 4)],
    [(0, 76, 4), (4, 79, 4), (8, 76, 4), (12, 74, 4)],
    [(0, 72, 4), (4, 74, 4), (8, 71, 4), (12, 69, 4)],
]
LEAD_B = [
    [(0, 81, 2), (2, 84, 2), (4, 83, 4), (8, 81, 8)],
    [(0, 84, 4), (4, 81, 4), (8, 77, 8)],
    [(0, 76, 4), (4, 79, 4), (8, 84, 8)],
    [(0, 83, 2), (2, 86, 2), (4, 83, 4), (8, 79, 8)],
]
LEAD_C = [
    [(0, 81, 4), (4, 88, 4), (8, 81, 4), (12, 79, 4)],
    [(0, 77, 4), (4, 84, 4), (8, 81, 8)],
    [(0, 79, 4), (4, 88, 4), (8, 84, 8)],
    [(0, 86, 4), (4, 83, 4), (8, 79, 4), (12, 81, 4)],
]


def pat_intro():
    p = Pat()
    for b, ch in enumerate(PROG):
        pad(p, b, ch, 46 if b < 2 else 40)
        arp(p, b, ch, ARP_A, 38 if b < 2 else 34)
        if b >= 2:
            hat(p, b, 2, 26)
        if b == 0:
            stab(p, b, ch, (0,), 36)
        if b == 2:
            stab(p, b, ch, (0,), 30)
    bass(p, 2, 'C', ['r', 'r', 'f', 'r', 'r', 'f', 'r', 'o'], 46)
    lead(p, 1, [(0, 77, 4), (8, 72, 4)], 38)
    lead(p, 2, [(0, 76, 4), (4, 79, 4), (8, 76, 4), (12, 72, 4)], 44)
    lead(p, 3, [(0, 74, 4), (4, 71, 4), (8, 74, 4), (12, 69, 4)], 48)
    crash(p, 3, 46)
    p.put(3 * 16 + 12, C_SNARE, DRUM, I_CRASH, 48)
    bass(p, 3, 'G', ['r', 'r', 'f', 'r', 'r', 'f', 'r', 'o'], 52)
    return p


def pat_groove(lead_notes, bass_seq, arp_seq, hat_step=2, hat_vol=28,
               stab_rows=(0,), stab_vol=40, ohat=(), kick_extra=(), snare_ghosts=(),
               crash_bars=(), last_bar_16th=False, arp_seq2=None):
    p = Pat()
    for b, ch in enumerate(PROG):
        kick(p, b, (0, 4, 8, 12), 64, kick_extra if b == 3 else ())
        snare(p, b, (4, 12), 56, snare_ghosts)
        if last_bar_16th and b == 3:
            hat(p, b, 1, 20)
        else:
            hat(p, b, hat_step, hat_vol, ohat if b % 2 == 0 else ())
        bass(p, b, ch, bass_seq, 60)
        arp(p, b, ch, (arp_seq2 or arp_seq) if b >= 2 else arp_seq, 32)
        stab(p, b, ch, stab_rows, stab_vol)
        if b in crash_bars:
            crash(p, b, 44)
        lead(p, b, lead_notes[b], 60)
    return p


def pat_bridge():
    p = Pat()
    for b, ch in enumerate(PROG[:2]):
        pad(p, b, ch, 34)
        arp(p, b, ch, ARP_A, 30)
        bass(p, b, ch, ['r', 'r', 'f', 'r', 'r', 'r', 'f', 'o'], 52)
    lead(p, 1, [(0, 77, 4), (8, 72, 4)], 48)
    ch = PROG[2]
    pad(p, 2, ch, 26)
    arp(p, 2, ch, ARP_B, 32)
    bass(p, 2, ch, BASS_A, 60)
    kick(p, 2, (0, 4, 8, 12), 60)
    snare(p, 2, (4, 12), 52)
    hat(p, 2, 2, 24)
    lead(p, 2, [(0, 76, 4), (4, 79, 4), (8, 76, 4), (12, 72, 4)], 56)
    ch = PROG[3]
    pad(p, 3, ch, 26)
    arp(p, 3, ch, ARP_B, 34)
    bass(p, 3, ch, BASS_A, 62)
    kick(p, 3, (0, 4, 8, 12), 64)
    snare(p, 3, (4, 12), 58, ghosts=(7, 10, 13, 15))
    hat(p, 3, 1, 22)
    crash(p, 3, 40)
    lead(p, 3, [(0, 74, 4), (4, 76, 4), (8, 79, 4), (12, 83, 4)], 60)
    return p


def pat_finale():
    p = Pat()
    for b, ch in enumerate(PROG):
        kick(p, b, (0, 4, 8, 12), 64, (14,) if b % 2 else ())
        snare(p, b, (4, 12), 58, (7, 11) if b % 2 else (10,))
        hat(p, b, 1, 24, (6,) if b % 2 else ())
        bass(p, b, ch, BASS_C, 62)
        arp(p, b, ch, ARP_B if b >= 2 else ARP_C, 36 if b >= 2 else 34)
        stab(p, b, ch, (0, 8), 42)
        pad(p, b, ch, 20)
        crash(p, b, 46)
        lead(p, b, LEAD_C[b], 62)
    # fill into the loop: 16th bass run and a snare roll in the last bar
    for i, m in enumerate([43, 50, 55, 59]):
        p.put(3 * 16 + 12 + i, C_BASS, m, I_BASS, 62)
    for i, v in enumerate([46, 52, 58, 62]):
        p.put(3 * 16 + 12 + i, C_SNARE, DRUM, I_SNARE, v)
    return p


PATS = [
    pat_intro(),
    pat_groove(LEAD_A, BASS_A, ARP_A, hat_step=2, hat_vol=28, stab_rows=(0, 10),
               stab_vol=40, ohat=(14,), kick_extra=(14,), crash_bars=(0, 2),
               last_bar_16th=True, arp_seq2=ARP_B),
    pat_groove(LEAD_B, BASS_B, ARP_B, hat_step=1, hat_vol=22, stab_rows=(0, 6),
               stab_vol=42, ohat=(14,), kick_extra=(6, 14), snare_ghosts=(10, 15),
               crash_bars=(0, 2), arp_seq2=ARP_C),
    pat_bridge(),
    pat_finale(),
]

# ------------------------------------------------------------------ build
INSTR_NAMES = {
    I_KICK: 'kick', I_SNARE: 'snare', I_HAT: 'hat', I_OHAT: 'open hat',
    I_BASS: 'bass', I_ARP: 'arp', I_LEAD: 'lead', I_CRASH: 'crash',
    8: 'stab Am', 9: 'stab F', 10: 'stab C', 11: 'stab G',
    12: 'pad Am', 13: 'pad F', 14: 'pad C', 15: 'pad G',
}
SAMPLE_FILES = {
    I_KICK: 'kick.wav', I_SNARE: 'snare.wav', I_HAT: 'hat.wav', I_OHAT: 'ohat.wav',
    I_BASS: 'bass.wav', I_ARP: 'arp.wav', I_LEAD: 'lead.wav', I_CRASH: 'crash.wav',
    8: 'stab_Am.wav', 9: 'stab_F.wav', 10: 'stab_C.wav', 11: 'stab_G.wav',
    12: 'pad_Am.wav', 13: 'pad_F.wav', 14: 'pad_C.wav', 15: 'pad_G.wav',
}
PANNING = {I_KICK: 128, I_SNARE: 128, I_HAT: 90, I_OHAT: 100, I_BASS: 128,
           I_ARP: 70, I_LEAD: 190, I_CRASH: 128, 8: 160, 9: 100, 10: 150, 11: 105,
           12: 150, 13: 100, 14: 150, 15: 100}
SAMPLE_VOL = {I_KICK: 64, I_SNARE: 58, I_HAT: 44, I_OHAT: 34, I_BASS: 60,
              I_ARP: 46, I_LEAD: 58, I_CRASH: 42, 8: 48, 9: 48, 10: 48, 11: 48,
              12: 40, 13: 40, 14: 40, 15: 40}

calls = [{'name': 'module_new', 'arguments': {'channels': 8, 'name': 'Keygen Codex'}}]
for i in sorted(SAMPLE_FILES):
    calls.append({'name': 'sample_load',
                  'arguments': {'path': '/workspace/samples/' + SAMPLE_FILES[i], 'instrument': i}})
    calls.append({'name': 'instrument_set',
                  'arguments': {'instrument': i, 'name': INSTR_NAMES[i]}})
    calls.append({'name': 'sample_set',
                  'arguments': {'instrument': i, 'sample': 0, 'volume': SAMPLE_VOL[i],
                                'panning': PANNING[i]}})
calls.append({'name': 'song_set', 'arguments': {
    'name': 'Keygen Codex', 'bpm': BPM, 'speed': SPEED, 'length': len(PATS), 'loop_start': 0}})
for i in range(len(PATS)):
    calls.append({'name': 'order_set', 'arguments': {'position': i, 'pattern': i}})
for i in range(len(PATS)):
    calls.append({'name': 'pattern_set_length', 'arguments': {'pattern': i, 'rows': ROWS}})
for i, p in enumerate(PATS):
    for (row, ch), (note, inst, vol, fx, prm) in sorted(p.cells.items()):
        args = {'pattern': i, 'row': row, 'channel': ch, 'note': note, 'instrument': inst,
                'volume': vol}
        if fx:
            args['effect'] = fx
            args['effect_param'] = prm
        calls.append({'name': 'pattern_set_cell', 'arguments': args})
calls.append({'name': 'module_save', 'arguments': {'path': '/workspace/submission/tune.xm',
                                                     'format': 'xm'}})
calls.append({'name': 'module_render', 'arguments': {'path': '/workspace/preview.wav',
                                                      'rate': 44100, 'bits': 16}})

os.makedirs('/workspace/submission', exist_ok=True)
with open('/workspace/build.json', 'w') as f:
    json.dump(calls, f)
print('calls:', len(calls), 'cells:', sum(len(p.cells) for p in PATS))
