"""Build the keygen module with the FT2 bridge tools."""
import sys, os
sys.path.insert(0, '/workspace/scripts')
from ft2 import call, batch
import score as S

WORK = '/workspace/work'
SAMPLES = os.path.join(WORK, 'samples')

INSTR = {
    'LEAD': 1, 'ARPA': 2, 'ARPB': 3, 'BASS': 4, 'SUB': 5, 'KICK': 6, 'SNARE': 7,
    'HAT': 8, 'OHAT': 9, 'STAB1': 10, 'STAB2': 11, 'STAB3': 12, 'BELL': 13,
    'PLUCK': 14, 'FX': 15, 'PAD': 16, 'RISER': 17, 'RIM': 18,
}
SPEC = {
    # voice: (sample file, loop length, flags, volume, panning)
    'LEAD': ('lead', 128, 1, 64, 128),     # 25% pulse, natural C4
    'ARPA': ('arpa', 128, 1, 64, 88),      # 50% pulse, natural C4
    'ARPB': ('arpb', 128, 1, 64, 168),     # 12.5% pulse, natural C4
    'BASS': ('bass', 256, 1, 64, 128),     # rounded saw, natural C3
    'SUB':  ('sub', 511, 1, 64, 128),      # sine, natural C2
    'KICK': ('kick', 0, 0, 64, 128),
    'SNARE':('snare', 0, 0, 64, 128),
    'HAT':  ('hat', 0, 0, 64, 96),
    'OHAT': ('ohat', 0, 0, 64, 160),
    'STAB1':('stabshot', 0, 0, 64, 104),
    'STAB2':('stabshot', 0, 0, 64, 152),
    'STAB3':('stabshot', 0, 0, 64, 128),
    'BELL': ('bell', 0, 0, 64, 120),
    'PLUCK':('pluck', 0, 0, 64, 136),
    'FX':   ('crash', 0, 0, 64, 128),
    'PAD':  ('pad', 256, 1, 64, 128),
    'RISER':('riser', 0, 0, 64, 128),
    'RIM':  ('rim', 0, 0, 64, 120),
}
# clone note 73 == this midi pitch for each voice
BASE = {'LEAD': 60, 'ARPA': 60, 'ARPB': 60, 'BASS': 48, 'SUB': 36,
        'STAB1': 60, 'STAB2': 60, 'STAB3': 60, 'PAD': 48}

def clone_note(voice, midi):
    # this tracker build plays a looped sample one octave above its natural
    # pitch at clone note 61 (one-shot samples sound at their natural pitch
    # on clone note 73)
    return 61 + (midi - BASE[voice])

def build(out_xm=None, out_wav=None, render=True, scale=0.52, only=None):
    out_xm = out_xm or os.path.join(WORK, 'tune.xm')
    out_wav = out_wav or os.path.join(WORK, 'tune.wav')
    call('module_new', channels=18, name='NEON KEYGEN')
    call('song_set', bpm=150, speed=6, length=len(S.PATTERNS), loop_start=0)
    for voice, (fn, loop, flags, vol, pan) in SPEC.items():
        idx = INSTR[voice]
        call('instrument_set', instrument=idx, name=voice)
        call('sample_load', path=os.path.join(SAMPLES, fn + '.wav'), instrument=idx, sample=0)
        call('sample_set', instrument=idx, sample=0, name=fn, loop_start=0,
             loop_length=loop, flags=flags, volume=int(vol * scale), panning=pan)
    npat = len(S.PATTERNS)
    for i in range(npat):
        call('order_set', position=i, pattern=i)
    for i in range(npat):
        call('pattern_set_length', pattern=i, rows=S.ROWS)

    cells = []
    def put(pat, row, ch, note=None, vol=None, cut=None, inst=None, off=False):
        a = {'pattern': pat, 'row': row, 'channel': ch}
        if off:
            a['note'] = 97
        else:
            a['note'] = note
            a['instrument'] = inst
            a['volume'] = 15
            if cut is not None:
                a['effect'] = 14
                a['effect_param'] = 0xC0 + int(cut)
            else:
                a['effect'] = 12
                a['effect_param'] = max(0, min(64, int(vol)))
        cells.append({'name': 'pattern_set_cell', 'arguments': a})

    last_pat = npat - 1
    for pi, P in enumerate(S.PATTERNS):
        gain = P.get('gain', 1.0)
        for b, cname in enumerate(P['chords']):
            r0 = b * 16
            tones = S.CHORDS[cname]
            final = (pi == last_pat and b == 3)
            # ---- arpeggios
            if P['arp']:
                lvl = P['arp']
                idxs = S.ARP_A if (pi + b) % 2 == 0 else S.ARP_B
                nrow = 8 if final else 16
                for i in range(nrow):
                    t = tones[idxs[i]]
                    put(pi, r0 + i, S.CH['ARPA'], clone_note('ARPA', t + 12),
                        (13 if lvl == 1 else 19) * gain, inst=INSTR['ARPA'])
                    put(pi, r0 + i, S.CH['ARPB'], clone_note('ARPB', t),
                        (11 if lvl == 1 else 15) * gain, inst=INSTR['ARPB'])
            # ---- bass
            bl = S.BASSLINE[cname]
            use_bass = P['bass'] == 1 or (isinstance(P['bass'], list) and b in P['bass'])
            if use_bass:
                bvol = 42
                if P['name'] == 'INTRO' and b < 2:
                    bvol = 26
                for i, m in enumerate(bl):
                    put(pi, r0 + i * 2, S.CH['BASS'], clone_note('BASS', m), bvol * gain, inst=INSTR['BASS'])
                put(pi, r0, S.CH['SUB'], clone_note('SUB', bl[0]), 26 * gain, inst=INSTR['SUB'])
                put(pi, r0 + 8, S.CH['SUB'], clone_note('SUB', bl[4]), 22 * gain, inst=INSTR['SUB'])
            # ---- pad
            if P['pad']:
                put(pi, r0, S.CH['PAD'], clone_note('PAD', tones[0]), 13 * gain, inst=INSTR['PAD'])
            # ---- drums
            lvl = P['drums']
            if lvl and not final:
                if lvl == 1:
                    for k in (0, 8):
                        put(pi, r0 + k, S.CH['KICK'], 61, 56 * gain, inst=INSTR['KICK'])
                else:
                    for k in (0, 6, 8, 14):
                        put(pi, r0 + k, S.CH['KICK'], 61, 60 * gain, inst=INSTR['KICK'])
                for s in (4, 12):
                    put(pi, r0 + s, S.CH['SNARE'], 61, 50 * gain, inst=INSTR['SNARE'])
                for i in range(0, 16, 2):
                    put(pi, r0 + i, S.CH['HAT'], 61, (22 if i % 4 == 0 else 15) * gain, inst=INSTR['HAT'])
                if lvl == 2:
                    for i in range(1, 16, 2):
                        put(pi, r0 + i, S.CH['HAT'], 61, 9 * gain, inst=INSTR['HAT'])
                    put(pi, r0 + 14, S.CH['OHAT'], 61, 26 * gain, inst=INSTR['OHAT'])
            # ---- drum fill at the end of a bar
            if P.get('fill') and b == 3 and lvl and not final:
                for i in range(11, 16):
                    put(pi, r0 + i, S.CH['SNARE'], 61, 20 + (i - 10) * 8, inst=INSTR['SNARE'])
                put(pi, r0 + 15, S.CH['KICK'], 61, 60 * gain, inst=INSTR['KICK'])
            # ---- snare roll into the climax (last bar of the build)
            if P['roll'] and b == 3:
                for i in range(8, 16):
                    v = 16 + i * 3
                    put(pi, r0 + i, S.CH['SNARE'], 61, min(v, 58), inst=INSTR['SNARE'])
                    put(pi, r0 + i, S.CH['RIM'], 61, 20 + i, inst=INSTR['RIM'])
            # ---- chord stabs
            if P['stabs']:
                for st in (2, 6, 10, 14):
                    for vc, tn in (('STAB1', tones[0]), ('STAB2', tones[1]), ('STAB3', tones[2])):
                        put(pi, r0 + st, S.CH[vc], clone_note(vc, tn), 21 * gain, inst=INSTR[vc])
            # ---- bell counter line
            if P['bell']:
                for (rr, mm) in P['bell'][b]:
                    put(pi, r0 + rr, S.CH['BELL'], 61 + (mm - 72), 42 * gain, inst=INSTR['BELL'])
            # ---- pluck accents
            if P['pluck']:
                for rr, mm in ((2, 69), (10, 72)):
                    put(pi, r0 + rr, S.CH['PLUCK'], 61 + (mm - 60), 30 * gain, inst=INSTR['PLUCK'])
            # ---- lead melody
            if P['lead']:
                for (rr, mm, dur) in P['lead'][b]:
                    put(pi, r0 + rr, S.CH['LEAD'], clone_note('LEAD', mm), 58 * gain, inst=INSTR['LEAD'])
        # a lead pickup at the end of the intro
        if P['name'] == 'INTRO':
            put(pi, 3 * 16 + 12, S.CH['LEAD'], clone_note('LEAD', 79), 34, inst=INSTR['LEAD'])
        # releases at the end of a pattern
        if P['pad']:
            put(pi, S.ROWS - 1, S.CH['PAD'], off=True)
        if P['lead']:
            put(pi, S.ROWS - 1, S.CH['LEAD'], off=True)
        if P['bell']:
            put(pi, S.ROWS - 1, S.CH['BELL'], off=True)

    # ---- global events
    put(1, 0, S.CH['FX'], 61, 44, inst=INSTR['FX'])        # crash on the A drop
    put(6, 0, S.CH['FX'], 61, 46, inst=INSTR['FX'])        # crash at the climax
    put(5, 56, S.CH['RISER'], 61, 40, inst=INSTR['RISER'])# riser through the build
    put(0, 60, S.CH['RISER'], 61, 16, inst=INSTR['RISER'])# small riser into the drop

    if only is not None:
        cells = [c for c in cells if c['arguments']['channel'] in only]
    for c in cells:
        n = c['arguments'].get('note')
        if n is not None and not (0 <= n <= 97):
            raise ValueError('note out of range: %r' % c)
    batch(cells)
    if render:
        call('module_render', path=out_wav, rate=44100, bits=16, loops=1)
    call('module_save', path=out_xm, format='xm')
    return out_xm, out_wav

if __name__ == '__main__':
    xm, wav = build()
    print('saved', xm, wav)
