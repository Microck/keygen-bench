"""Composition for the keygen loop (original material).

Key A minor, 150 BPM, speed 6 (16th-note rows, 16 rows per bar, 4 bars per 64-row pattern).
Patterns: 0 INTRO, 1 A1, 2 A2, 3 BREAK, 4 C1 (climax), 5 C2 (turnaround to the loop start).
Order: 0 1 2 3 1 4 5, restart position = 1 (A1). The loop body is A1..C2; C2 ends on the
dominant (E) with a snare build and riser, and resolves into A1's Am downbeat with a crash.
"""
import json, sys

CH_LEAD, CH_HARM, CH_ARP, CH_ARP2 = 0, 1, 2, 3
CH_PADL, CH_PADM, CH_PADH, CH_BASS = 4, 5, 6, 7
CH_KICK, CH_SNARE, CH_HATS, CH_FX = 8, 9, 10, 11
NCH = 12
I_LEAD, I_HARM, I_PLUCK, I_PAD, I_BASS, I_KICK, I_SNARE, I_HATC, I_HATO, I_RISER, I_CRASH, I_BASS16 = range(1, 13)
PAT_INTRO, PAT_A1, PAT_A2, PAT_BRK, PAT_C1, PAT_C2 = range(6)
ORDER = [PAT_INTRO, PAT_A1, PAT_A2, PAT_BRK, PAT_A1, PAT_C1, PAT_C2]
RESTART = 1
DRUM = 'C-4'
PAN = {CH_LEAD: 0x58, CH_HARM: 0xA8, CH_ARP: 0x40, CH_ARP2: 0xC0, CH_PADL: 0x22,
       CH_PADM: 0x80, CH_PADH: 0xDE, CH_BASS: 0x80, CH_KICK: 0x80, CH_SNARE: 0x80,
       CH_HATS: 0xB8, CH_FX: 0x80}

NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
def nm(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"

# ---- harmony -------------------------------------------------------------
CHORDS = {  # arp tones (root in octave 4) and pad voicing, bass root
    'Am': dict(arp=[69, 72, 76, 81], pad=[57, 60, 64], bass=45, third=72),
    'F':  dict(arp=[65, 69, 72, 77], pad=[53, 57, 60], bass=41, third=69),
    'C':  dict(arp=[60, 64, 67, 72], pad=[60, 64, 67], bass=36, third=64),
    'G':  dict(arp=[67, 71, 74, 79], pad=[55, 59, 62], bass=43, third=71),
    'E':  dict(arp=[64, 68, 71, 76], pad=[56, 59, 64], bass=40, third=68),
    'Em': dict(arp=[64, 67, 71, 76], pad=[52, 55, 59], bass=40, third=67),
    'Dm': dict(arp=[62, 65, 69, 74], pad=[50, 53, 57], bass=38, third=65),
}
A_MINOR = [69, 71, 72, 74, 76, 77, 79]  # A B C D E F G (pitch classes mod 12 used below)
SCALE_PC = {9, 11, 0, 2, 4, 5, 7}

def third_below(m):
    """Diatonic third below in A minor (non-scale notes resolve to the scale tone beneath)."""
    s = m
    while (s % 12) not in SCALE_PC:
        s -= 1
    # scale degrees available below s
    degs = [x for x in range(s - 14, s + 1) if (x % 12) in SCALE_PC]
    idx = degs.index(s)
    return degs[idx - 2]

# ---- melodies: (start_row, midi, length_rows) ------------------------------------------
LEAD_INTRO = [(32, 81, 8), (40, 84, 8), (48, 83, 8), (56, 86, 8)]
LEAD_A1 = [
    (0, 76, 3), (4, 81, 2), (6, 79, 2), (8, 76, 4), (12, 72, 2), (14, 74, 2),
    (16, 77, 4), (20, 81, 2), (22, 84, 2), (24, 81, 4), (28, 79, 2), (30, 77, 2),
    (32, 76, 2), (34, 79, 2), (36, 84, 4), (40, 83, 2), (42, 81, 2), (44, 79, 4),
    (48, 77, 2), (50, 76, 2), (52, 74, 4), (56, 67, 2), (58, 71, 2), (60, 74, 4)]
LEAD_A2 = [
    (0, 81, 2), (2, 84, 2), (4, 88, 4), (8, 86, 2), (10, 84, 2), (12, 81, 4),
    (16, 79, 2), (18, 77, 2), (20, 81, 4), (24, 84, 2), (26, 81, 2), (28, 77, 4),
    (32, 83, 2), (34, 80, 2), (36, 76, 4), (40, 80, 2), (42, 83, 2), (44, 88, 4),
    (48, 76, 2), (50, 81, 2), (52, 84, 4), (56, 81, 2), (58, 79, 2), (60, 76, 4)]
LEAD_BRK = [(0, 84, 8), (8, 81, 4), (12, 77, 4), (16, 86, 4), (20, 83, 4), (24, 79, 8),
            (32, 76, 4), (36, 79, 4), (40, 83, 8), (48, 80, 4), (52, 83, 4), (56, 88, 8)]
LEAD_C1 = [
    (0, 81, 2), (2, 84, 2), (4, 88, 2), (6, 93, 2), (8, 91, 2), (10, 88, 2), (12, 84, 2), (14, 81, 2),
    (16, 83, 2), (18, 86, 2), (20, 91, 4), (24, 90, 2), (26, 88, 2), (28, 86, 4),
    (32, 84, 2), (34, 89, 2), (36, 93, 4), (40, 91, 2), (42, 89, 2), (44, 84, 4),
    (48, 83, 2), (50, 88, 2), (52, 92, 4), (56, 88, 2), (58, 83, 2), (60, 80, 4)]
LEAD_C2 = [
    (0, 86, 4), (4, 89, 2), (6, 88, 2), (8, 86, 4), (12, 81, 2), (14, 84, 2),
    (16, 84, 2), (18, 88, 2), (20, 93, 4), (24, 91, 2), (26, 88, 2), (28, 84, 4),
    (32, 77, 2), (34, 81, 2), (36, 84, 4), (40, 89, 2), (42, 88, 2), (44, 86, 4),
    (48, 83, 4), (52, 88, 2), (54, 87, 2), (56, 88, 8)]

VIB = 0x46  # vibrato speed 4, depth 6 on sustained lead notes

class Score:
    def __init__(self):
        self.cells = {}
    def put(self, pat, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
        assert 0 <= row < 64, row
        key = (pat, row, ch)
        c = self.cells.get(key, {})
        if note is not None: c['note'] = note
        if ins is not None: c['instrument'] = ins
        if vol is not None: c['volume'] = vol
        if fx is not None: c['effect'] = fx; c['effect_param'] = fp
        self.cells[key] = c
    def melody(self, pat, events, ch, ins, vol, transform=None, vib=True, cut=True):
        for i, (r, m, ln) in enumerate(events):
            mm = transform(m) if transform else m
            self.put(pat, r, ch, note=nm(mm), ins=ins, vol=vol,
                     fx=(4 if (vib and ln >= 4) else None), fp=(VIB if (vib and ln >= 4) else None))
            end = r + ln
            nxt = events[i + 1][0] if i + 1 < len(events) else 64
            if cut and end < 64 and end < nxt:
                self.put(pat, end, ch, note=97)
            # release: the last row of every note fades out, so the next note or note-off
            # never cuts a sounding sawtooth/pulse at a random phase
            last = min(end, 64) - 1
            if 'effect' not in self.cells.get((pat, last, ch), {}) and self.cells.get((pat, last, ch), {}).get('note') in (None, 97):
                self.put(pat, last, ch, fx=0x0A, fp=0x08)
            elif (pat, last, ch) in self.cells and 'effect' not in self.cells[(pat, last, ch)]:
                self.put(pat, last, ch, fx=0x0A, fp=0x08)
    def pan_row0(self, pat):
        for ch, p in PAN.items():
            c = self.cells.get((pat, 0, ch))
            if c is None:
                self.put(pat, 0, ch, fx=8, fp=p)
            else:
                c['effect'] = 8; c['effect_param'] = p

LOOPED_CH = (CH_LEAD, CH_HARM, CH_PADL, CH_PADM, CH_PADH)

def fade_pattern_ends(S):
    """Any looped voice still sounding at row 63 gets a volume slide over its last rows,
    so the next pattern never cuts a sustained tone at a random phase (no clicks at joins)."""
    for pat in range(6):
        for ch in LOOPED_CH:
            ons = sorted(r for (p, r, c), v in S.cells.items() if p == pat and c == ch and 'note' in v and v['note'] != 97)
            offs = sorted(r for (p, r, c), v in S.cells.items() if p == pat and c == ch and v.get('note') == 97)
            if not ons:
                continue
            last_on = ons[-1]
            if offs and offs[-1] > last_on:
                continue  # already released inside the pattern
            start = max(last_on + 1, 60)
            for row in range(start, 64):
                c = S.cells.get((pat, row, ch), {})
                if 'effect' in c and c['effect'] != 0x0A:
                    continue
                S.put(pat, row, ch, fx=0x0A, fp=0x03)  # volume slide down

def build():
    S = Score()
    chords = {
        PAT_INTRO: ['Am', 'Am', 'F', 'G'],
        PAT_A1: ['Am', 'F', 'C', 'G'],
        PAT_A2: ['Am', 'F', 'E', 'Am'],
        PAT_BRK: ['F', 'G', 'Em', 'E'],
        PAT_C1: ['Am', 'G', 'F', 'E'],
        PAT_C2: ['Dm', 'Am', 'F', 'E'],
    }
    # ----- pads: a voicing on each chord change, held through repeated bars
    for pat, ch_list in chords.items():
        for b, c in enumerate(ch_list):
            if b == 0 or ch_list[b - 1] != c:
                v = CHORDS[c]['pad']
                S.put(pat, 16 * b, CH_PADL, note=nm(v[0]), ins=I_PAD)
                S.put(pat, 16 * b, CH_PADM, note=nm(v[1]), ins=I_PAD)
                S.put(pat, 16 * b, CH_PADH, note=nm(v[2]), ins=I_PAD)

    # ----- arpeggios on channel ARP (16ths or 8ths) and sparkle on ARP2
    def arp(pat, bars, style, step, vol, order='up'):
        for b in bars:
            tones = CHORDS[chords[pat][b]]['arp']
            seq = {'up': [0, 1, 2, 3], 'down': [3, 2, 1, 0], 'updown': [0, 1, 2, 3, 2, 1]}[order]
            for k in range(0, 16, step):
                t = tones[seq[(k // step) % len(seq)]]
                S.put(pat, 16 * b + k, CH_ARP, note=nm(t), ins=I_PLUCK, vol=vol)
    # INTRO: 8ths from bar 2
    arp(PAT_INTRO, [1, 2, 3], 'up', 2, 30)
    arp(PAT_A1, [0, 1, 2, 3], 'up', 1, 40)
    arp(PAT_A2, [0, 1, 2, 3], 'down', 1, 36)
    arp(PAT_BRK, [0, 1, 2, 3], 'up', 2, 16)
    arp(PAT_C1, [0, 1, 2, 3], 'updown', 1, 44)
    arp(PAT_C2, [0, 1, 2, 3], 'up', 1, 40)
    # sparkle (ARP2): offbeat plucks an octave above the chord's third
    for pat in (PAT_A2, PAT_C1):
        for b in range(4):
            for k in (2, 6, 10, 14):
                S.put(pat, 16 * b + k, CH_ARP2, note=nm(CHORDS[chords[pat][b]]['third'] + 12), ins=I_PLUCK, vol=30)

    # ----- melodies
    S.melody(PAT_INTRO, LEAD_INTRO, CH_LEAD, I_LEAD, 40)
    S.melody(PAT_A1, LEAD_A1, CH_LEAD, I_LEAD, 40)
    S.melody(PAT_A2, LEAD_A2, CH_LEAD, I_LEAD, 40)
    S.melody(PAT_BRK, LEAD_BRK, CH_LEAD, I_LEAD, 36)
    S.melody(PAT_C1, LEAD_C1, CH_LEAD, I_LEAD, 44)
    S.melody(PAT_C2, LEAD_C2, CH_LEAD, I_LEAD, 42)
    # harmony a diatonic third below the lead (absent in the breakdown)
    for pat, ev in ((PAT_A1, LEAD_A1), (PAT_A2, LEAD_A2), (PAT_C1, LEAD_C1), (PAT_C2, LEAD_C2)):
        S.melody(pat, ev, CH_HARM, I_HARM, 26, transform=third_below, vib=False)

    # ----- bass
    for b in range(4):
        r = CHORDS[chords[PAT_A1][b]]['bass']
        for k in range(0, 16, 2):  # 8ths, root / octave alternating (A1, A2, C2 patterns)
            for pat in (PAT_A1, PAT_A2, PAT_C2):
                rr = CHORDS[chords[pat][b]]['bass']
                S.put(pat, 16 * b + k, CH_BASS, note=nm(rr if (k // 2) % 2 == 0 else rr + 12), ins=I_BASS, vol=44)
        for k in range(16):  # 16ths in the climax (short plucks)
            rr = CHORDS[chords[PAT_C1][b]]['bass']
            S.put(PAT_C1, 16 * b + k, CH_BASS, note=nm(rr if k % 2 == 0 else rr + 12), ins=I_BASS16, vol=40)
        rr = CHORDS[chords[PAT_BRK][b]]['bass']  # sparse breakdown plucks
        for k in (0, 8):
            S.put(PAT_BRK, 16 * b + k, CH_BASS, note=nm(rr if k == 0 else rr + 12), ins=I_BASS, vol=40)
    for k in (0, 4, 8, 12):  # intro bar 4 bass pulse
        S.put(PAT_INTRO, 48 + k, CH_BASS, note=nm(CHORDS['G']['bass']), ins=I_BASS, vol=34)
    # (bass 8ths in A1/A2/C2 use the 8th-note pluck; retriggers never cut a sustained saw)

    # ----- drums
    for pat in (PAT_A1, PAT_A2, PAT_C1, PAT_C2):
        for b in range(4):
            for k in (0, 4, 8, 12):
                S.put(pat, 16 * b + k, CH_KICK, note=DRUM, ins=I_KICK, vol=64)
            for k in (4, 12):
                S.put(pat, 16 * b + k, CH_SNARE, note=DRUM, ins=I_SNARE, vol=60 if pat != PAT_C1 else 64)
            if pat in (PAT_A1, PAT_A2, PAT_C2):
                for k in (2, 6, 10, 14):
                    if pat == PAT_A1 and k == 14 and b in (1, 3):
                        S.put(pat, 16 * b + k, CH_HATS, note=DRUM, ins=I_HATO, vol=30)
                    else:
                        S.put(pat, 16 * b + k, CH_HATS, note=DRUM, ins=I_HATC, vol=34)
            if pat == PAT_C1:
                for k in (2, 6, 10, 14):
                    S.put(pat, 16 * b + k, CH_ARP2, note=DRUM, ins=I_HATO, vol=30)
                for k in (1, 3, 5, 7, 9, 11, 13, 15):
                    S.put(pat, 16 * b + k, CH_HATS, note=DRUM, ins=I_HATC, vol=16)
    # C2 fill: snare climb in the last bar
    for k, v in ((56, 44), (58, 50), (60, 56), (62, 64)):
        S.put(PAT_C2, k, CH_SNARE, note=DRUM, ins=I_SNARE, vol=v)
    # INTRO: kick build in bar 4, closed hats from bar 3
    for k in (48, 52, 56, 60):
        S.put(PAT_INTRO, k, CH_KICK, note=DRUM, ins=I_KICK, vol=48)
    for b in (2, 3):
        for k in (2, 6, 10, 14):
            S.put(PAT_INTRO, 16 * b + k, CH_HATS, note=DRUM, ins=I_HATC, vol=26)
    # BREAKDOWN: half-time kick, offbeat hats, snare roll that climbs in the last bar
    for b in range(3):
        for k in (0, 8):
            S.put(PAT_BRK, 16 * b + k, CH_KICK, note=DRUM, ins=I_KICK, vol=52)
        for k in (2, 6, 10, 14):
            S.put(PAT_BRK, 16 * b + k, CH_HATS, note=DRUM, ins=I_HATC, vol=22)
    for k, v in zip(range(48, 64), [16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40, 44, 48, 52, 56, 64]):
        S.put(PAT_BRK, k, CH_SNARE, note=DRUM, ins=I_SNARE, vol=v)
    for k, v in ((48, 40), (52, 48), (56, 56), (58, 60), (60, 62), (62, 64)):
        S.put(PAT_BRK, k, CH_KICK, note=DRUM, ins=I_KICK, vol=v)

    # ----- FX: riser into each drop, crash on the downbeat of the drops
    S.put(PAT_INTRO, 48, CH_FX, note=DRUM, ins=I_RISER, vol=36)
    S.put(PAT_A1, 0, CH_FX, note=DRUM, ins=I_CRASH, vol=48)
    S.put(PAT_BRK, 48, CH_FX, note=DRUM, ins=I_RISER, vol=36)
    S.put(PAT_C1, 0, CH_FX, note=DRUM, ins=I_CRASH, vol=56)
    S.put(PAT_C2, 48, CH_FX, note=DRUM, ins=I_RISER, vol=40)

    # ----- clean seams: sustained parts fade to silence over the final rows of the
    # breakdown and of C2, so the restart never cuts a sounding tone
    fade_pattern_ends(S)

    # ----- panning on row 0 of every pattern
    for pat in range(6):
        S.pan_row0(pat)
    return S

SAMPLES = [
    # instrument, sample wav, looped?, relative note, finetune, default volume, name
    (I_LEAD, 'i01_lead_saw.wav', True, 36, 0, 40, 'Lead Saw'),
    (I_HARM, 'i02_harm_pulse.wav', True, 36, 0, 28, 'Harmony Pulse'),
    (I_PLUCK, 'i03_pluck.wav', False, 36, 0, 36, 'Arp Pluck'),
    (I_PAD, 'i04_pad.wav', True, 36, 0, 22, 'Pad Warm'),
    (I_BASS, 'i05_bass.wav', False, 36, 0, 40, 'Bass Pluck'),
    (I_KICK, 'i06_kick.wav', False, 28, 100, 64, 'Kick'),
    (I_SNARE, 'i07_snare.wav', False, 28, 100, 56, 'Snare'),
    (I_HATC, 'i08_hat_closed.wav', False, 28, 100, 34, 'Hat Closed'),
    (I_HATO, 'i09_hat_open.wav', False, 28, 100, 30, 'Hat Open'),
    (I_RISER, 'i10_riser.wav', False, 28, 100, 36, 'Riser'),
    (I_CRASH, 'i11_crash.wav', False, 28, 100, 40, 'Crash'),
    (I_BASS16, 'i12_bass16.wav', False, 36, 0, 40, 'Bass Pluck Short'),
]

def calls():
    out = [{'name': 'module_new', 'arguments': {'channels': NCH, 'name': 'Night Serial'}}]
    for ins, wav, looped, rel, ft, vol, name in SAMPLES:
        out.append({'name': 'sample_load', 'arguments': {'path': f'/workspace/build/samples/{wav}', 'instrument': ins, 'sample': 0}})
        args = {'instrument': ins, 'sample': 0, 'volume': vol, 'panning': 128,
                'relative_note': rel, 'finetune': ft, 'name': name}
        if looped:
            args.update({'flags': 17, 'loop_start': 0, 'loop_length': 256})
        else:
            args.update({'flags': 16, 'loop_start': 0, 'loop_length': 0})
        out.append({'name': 'sample_set', 'arguments': args})
        out.append({'name': 'instrument_set', 'arguments': {'instrument': ins, 'name': name}})
    out.append({'name': 'song_set', 'arguments': {'name': 'Night Serial', 'bpm': 150, 'speed': 6,
                                                  'length': len(ORDER), 'loop_start': RESTART}})
    for pos, pat in enumerate(ORDER):
        out.append({'name': 'order_set', 'arguments': {'position': pos, 'pattern': pat}})
    S = build()
    for (pat, row, ch) in sorted(S.cells):
        c = S.cells[(pat, row, ch)]
        args = {'pattern': pat, 'row': row, 'channel': ch}
        args.update(c)
        out.append({'name': 'pattern_set_cell', 'arguments': args})
    return out, S

if __name__ == '__main__':
    out, S = calls()
    path = sys.argv[1] if len(sys.argv) > 1 else '/workspace/build/compose_batch.json'
    with open(path, 'w') as f:
        json.dump(out, f)
    print('calls', len(out), 'cells', len(S.cells), 'written', path)
