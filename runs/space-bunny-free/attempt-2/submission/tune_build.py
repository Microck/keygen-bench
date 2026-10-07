#!/usr/bin/env python3
"""'Neon Licence' - an original keygen tune.
Writes a FastTracker II XM module directly (instruments + patterns do the work)."""
import sys, subprocess, json
sys.path.insert(0, '/workspace')
from music import *
from xmwrite import build_xm

ROWS = 64
# This renderer's period table is offset: samples must be tuned with +16 semitones
# and a +96/128 semitone fine offset so that note numbers sound at their real pitch.
REL_NOTE, FINETUNE = 16, 96
# ------------------------------------------------------------------ channels
CH_LEAD, CH_ARPR, CH_ARPL, CH_BASS, CH_SUB, CH_KICK, CH_SNAR, CH_HAT, \
    CH_PADL, CH_PADR, CH_PLUCK, CH_STAB = range(12)

# ---------------------------------------------------------------- instruments
SAMPLES = {
    'lead': ('lead.wav', 64, 128), 'arp': ('arp.wav', 62, 208),
    'arpw': ('arpw.wav', 54, 56), 'bass': ('bass.wav', 64, 128),
    'sub': ('sub.wav', 52, 128), 'kick': ('kick.wav', 64, 128),
    'snare': ('snare.wav', 56, 128), 'hat': ('hat.wav', 34, 170),
    'hato': ('hato.wav', 30, 96), 'tom': ('tom.wav', 52, 128),
    'padl': ('pad.wav', 42, 44), 'padr': ('pad.wav', 42, 212),
    'pluck': ('pluck.wav', 56, 64),
    'stab': ('stab.wav', 50, 128), 'bell': ('bell.wav', 46, 156),
}
INS = {k: i + 1 for i, k in enumerate(SAMPLES)}

class Pat:
    def __init__(self, rows=ROWS):
        self.rows, self.cells = rows, {}
    def put(self, ch, row, note, ins, vol=None, fx=None, fxp=None):
        if 0 <= row < self.rows:
            self.cells[(row, ch)] = dict(note=note, ins=ins, vol=vol, fx=fx, fxp=fxp)
    def merge(self, ch, row, cell):
        c = self.cells.setdefault((row, ch), dict(note=None, ins=None, vol=None, fx=None, fxp=None))
        for k, v in cell.items():
            if v is not None: c[k] = v

def tone(x):
    return x if isinstance(x, int) else nn(x)

# ------------------------------------------------------------------- one bar
def bar(P, r0, chord, arp=None, arpch=CH_ARPR, arpvol=28, arpinst=None, arpoct=3,
        arp2=None, arp2ch=CH_ARPL, arp2vol=18, arp2inst=None, arp2oct=3,
        bass=None, bassvol=46, bassoct=2, sub=None, subvol=28,
        kick=None, snare=None, hat=None, hato=None, toms=None, ride=None,
        pad=False, padvol=20, lead=None, leadvol=52, leadch=CH_LEAD,
        pluck=None, pluckvol=36, stab=None, stabvol=28, bell=None, bellvol=26,
        cut=None, cutfx=0xC3):
    for steps, ch, vol, ii, oc in ((arp, arpch, arpvol, arpinst, arpoct),
                                   (arp2, arp2ch, arp2vol, arp2inst, arp2oct)):
        if not steps:
            continue
        inst = ii or (INS['arp'] if ch == CH_ARPR else INS['arpw'])
        for s, n in enumerate(steps):
            if n is None:
                continue
            fx = fxp = None
            if cut and ch in cut and s in cut[ch]:
                fx, fxp = 18, cutfx
            P.put(ch, r0 + s, n, inst, vol, fx, fxp)
    if bass:
        for s, n in bass_bar(chord, bass, bassoct):
            if n is not None:
                P.put(CH_BASS, r0 + s, n, INS['bass'], bassvol)
    if sub:
        for s, n in sub:
            P.put(CH_SUB, r0 + s, n, INS['sub'], subvol)
    for lst, ch, key in ((kick, CH_KICK, 'kick'), (snare, CH_SNAR, 'snare'),
                         (hat, CH_HAT, 'hat'), (hato, CH_HAT, 'hato'),
                         (ride, CH_HAT, 'hat')):
        if lst:
            for s, v in lst:
                P.put(ch, r0 + s, 61, INS[key], v)
    if toms:
        for s, n, v in toms:
            P.put(CH_KICK, r0 + s, n, INS['tom'], v)
    if pad:
        for n in chord_notes(chord, 3):
            P.put(CH_PADL, r0, n, INS['padl'], padvol)
            P.put(CH_PADR, r0, n, INS['padr'], padvol)
        P.put(CH_PADL, r0, chord_notes(chord, 4)[0], INS['padl'], max(6, padvol - 4))
    if lead:
        for s, name, ln in lead:
            P.put(leadch, r0 + s, tone(name), INS['lead'], leadvol)
    if pluck:
        for s, name, ln in pluck:
            P.put(CH_PLUCK, r0 + s, tone(name), INS['pluck'], pluckvol)
    if stab:
        for s, name in stab:
            P.put(CH_STAB, r0 + s, tone(name), INS['stab'], stabvol)
    if bell:
        for s, name in bell:
            P.put(CH_STAB, r0 + s, tone(name), INS['bell'], bellvol)

def mel(i, m):
    return m[i % len(m)]

# ================================================================ ARRANGEMENT
def p_intro():
    """A : the arpeggio alone, then a bass pulse creeps in."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_RUN if b >= 2 else ARP_UP, 3),
            arpvol=[58, 62, 64, 64][b],
            arp2=arp_bar(c, ARP_SPARSE, 4) if b >= 1 else None,
            arp2vol=[0, 30, 34, 36][b],
            sub=[(s, n) for s, n in bass_bar(c, BASS_E, 2)] if b >= 2 else None,
            subvol=22,
            pad=b >= 2, padvol=16,
            hat=HAT_C if b >= 3 else None)
    return P

def p_rhythm():
    """A2 : bass + drums join."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=38,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=24,
            bass=BASS_A if b % 2 == 0 else BASS_C, bassvol=46,
            kick=DRUM_KICK_A if b < 3 else [(0, 62), (6, 48), (8, 62), (12, 50)],
            snare=SNARE_A if b < 3 else [(4, 52), (12, 52), (14, 34), (15, 42)],
            hat=HAT_A)
    return P

def p_lead_a():
    """B : theme A enters on the lead."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=29,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=17,
            bass=BASS_B if b % 2 else BASS_A, bassvol=47,
            kick=DRUM_KICK_B, snare=SNARE_A, hat=HAT_B,
            lead=mel(b, MEL_A), leadvol=52)
    return P

def p_lead_a2():
    """B2 : theme A answering variation."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_DOWN, 3) if b == 3 else arp_bar(c, ARP_UP, 3),
            arpvol=29,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=17,
            bass=BASS_C if b % 2 else BASS_B, bassvol=47,
            kick=DRUM_KICK_B, snare=SNARE_B if b == 3 else SNARE_A, hat=HAT_B,
            lead=mel(b, MEL_A2), leadvol=52,
            stab=[(0, chord_notes(c, 4)[0]), (8, chord_notes(c, 4)[0])] if b % 2 == 1 else None)
    return P

def p_lead_a3():
    """B3 : theme A over the darker progression."""
    P = Pat()
    for b, c in enumerate(PROG_B):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_RUN, 3) if b == 3 else arp_bar(c, ARP_UP, 3), arpvol=30,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=18,
            bass=BASS_D if b == 3 else (BASS_B if b % 2 else BASS_A), bassvol=48,
            kick=DRUM_KICK_C if b == 3 else DRUM_KICK_B, snare=SNARE_A, hat=HAT_B,
            lead=mel(b, MEL_A), leadvol=52,
            toms=[(12 + i*2, nn('D-4') + i, 38 - i*3) for i in range(4)] if b == 3 else None)
    return P

def p_lead_b():
    """C : theme B, first statement on the pluck."""
    P = Pat()
    for b, c in enumerate(PROG_B):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP2, 3), arpvol=25,
            arp2=arp_bar(c, ARP_SPARSE, 4), arp2vol=14,
            bass=BASS_A if b % 2 == 0 else BASS_C, bassvol=45,
            kick=DRUM_KICK_A, snare=SNARE_A, hat=HAT_A,
            pluck=mel(b, MEL_B), pluckvol=38)
    return P

def p_lead_b2():
    """C2 : theme B with the lead answering an octave up."""
    P = Pat()
    for b, c in enumerate(PROG_B):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=26,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=15,
            bass=BASS_B if b % 2 == 0 else BASS_D, bassvol=46,
            kick=DRUM_KICK_B, snare=SNARE_A, hat=HAT_B,
            pluck=mel(b, MEL_B), pluckvol=34,
            lead=mel(b, MEL_B2), leadvol=48,
            bell=[(0, ['A-5', 'A-5', 'D-6', 'B-5'][b])] if b % 2 == 0 else None)
    return P

def p_break():
    """D : breakdown - pad and a slow arpeggio."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c, pad=True, padvol=30 + b,
            arp=arp_bar(c, ARP_SPARSE, 3), arpch=CH_ARPL, arpvol=36,
            arp2=arp_bar(c, ARP_SPARSE, 4) if b >= 2 else None, arp2vol=26,
            sub=[(s, n) for s, n in bass_bar(c, BASS_E, 2)] if b >= 1 else None, subvol=24,
            bell=(BELL_PHRASE_A[b] if b >= 2 else
                  ([(0, ['A-5', 'C-6'][b])] if b % 2 == 0 else None)),
            bellvol=30)
    return P

def p_break2():
    """D2 : the pluck melody returns over the pad."""
    P = Pat()
    for b, c in enumerate(PROG_B):
        bar(P, b*16, c, pad=True, padvol=28,
            arp=arp_bar(c, ARP_SPARSE, 3), arpch=CH_ARPL, arpvol=32,
            arp2=arp_bar(c, ARP_GATE, 3) if b >= 2 else None, arp2vol=16,
            pluck=mel(b, MEL_B), pluckvol=42,
            bass=[(s, n) for s, n in bass_bar(c, BASS_E)] if b >= 2 else None,
            bassvol=44,
            kick=[(0, 54), (8, 46)] if b >= 2 else None,
            hat=HAT_C if b >= 2 else None,
            bell=BELL_PHRASE_B[b] if b >= 2 else None, bellvol=28)
    return P

def p_build():
    """E : everything returns, lead fills in."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_RUN, 3) if b == 3 else arp_bar(c, ARP_UP, 3),
            arpinst=INS['arpw'], arpvol=25 if b < 3 else 34,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=16,
            bass=BASS_C if b % 2 else BASS_A, bassvol=45,
            sub=[(s, n) for s, n in bass_bar(c, BASS_E, 2)], subvol=26,
            kick=DRUM_KICK_B, snare=SNARE_A, hat=HAT_B,
            pluck=mel(b, MEL_B) if b >= 2 else None, pluckvol=30,
            lead=FILL_A if b == 3 else None, leadvol=48)
    return P

def p_peak_a():
    """F : full band, theme A."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=32,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=19,
            bass=BASS_B if b % 2 == 0 else BASS_D, bassvol=48,
            kick=DRUM_KICK_C, snare=SNARE_A, hat=HAT_B, hato=[(14, 20)],
            lead=mel(b, MEL_A), leadvol=54)
    return P

def p_peak_a2():
    """F2 : theme A doubled with a stutter arp."""
    P = Pat()
    for b, c in enumerate(PROG_B):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=32,
            arp2=arp_bar(c, ARP_DOWN if b == 3 else ARP_GATE, 3), arp2vol=19,
            bass=BASS_D if b % 2 == 0 else BASS_C, bassvol=48,
            kick=DRUM_KICK_C, snare=SNARE_B if b == 3 else SNARE_A, hat=HAT_B,
            lead=mel(b, MEL_A2), leadvol=54,
            pluck=[(s, nn_name(nn(nm)+12), ln) for s, nm, ln in mel(b, MEL_A) if s % 8 == 0],
            pluckvol=25,
            stab=[(0, chord_notes(c, 4)[0]), (8, chord_notes(c, 4)[0])],
            toms=[(8 + i*2, nn('D-4') + i, 40 - i*4) for i in range(4)] if b == 3 else None)
    return P

def p_peak_b():
    """G : theme B with the full band."""
    P = Pat()
    for b, c in enumerate(PROG_B):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=31,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=18,
            bass=BASS_B if b % 2 == 0 else BASS_A, bassvol=48,
            kick=DRUM_KICK_C, snare=SNARE_A, hat=HAT_B,
            lead=mel(b, MEL_B), leadvol=52,
            pluck=[(s, nn_name(nn(nm)+12), ln) for s, nm, ln in mel(b, MEL_B)], pluckvol=25,
            stab=[(s, chord_notes(c, 4)[0]) for s in (0, 6, 8, 14)] if b % 2 else None)
    return P

def p_bridge():
    """H : chromatic bridge."""
    P = Pat()
    for b, c in enumerate(PROG_C):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_UP, 3), arpvol=26,
            arp2=arp_bar(c, ARP_SPARSE, 4), arp2vol=15,
            bass=BASS_D if b % 2 == 0 else BASS_C, bassvol=45,
            pad=b < 2, padvol=17,
            kick=DRUM_KICK_A if b < 2 else DRUM_KICK_B,
            snare=None if b < 2 else SNARE_A,
            hat=None if b < 2 else HAT_B,
            lead=mel(b, MEL_C), leadvol=50)
    return P

def p_climax():
    """I : climax, with a snare fill rolling into the outro."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        bar(P, b*16, c,
            arp=arp_bar(c, ARP_RUN if b == 3 else ARP_UP, 3), arpvol=33,
            arp2=arp_bar(c, ARP_GATE, 3), arp2vol=20,
            bass=BASS_D if b % 2 == 0 else BASS_B, bassvol=49,
            sub=[(s, n) for s, n in bass_bar(c, BASS_E, 2)], subvol=26,
            kick=DRUM_KICK_C if b < 3 else [(0, 62), (8, 52)],
            snare=SNARE_A if b < 3 else [(s, min(64, 24 + (s - 8) * 7)) for s in range(8, 16)],
            hat=HAT_B if b < 3 else None,
            hato=[(14, 22)],
            lead=mel(b, MEL_A3), leadvol=55,
            stab=[(0, chord_notes(c, 4)[0]), (8, chord_notes(c, 4)[0])])
    return P

def p_outro():
    """J : strip back down to the intro arpeggio."""
    P = Pat()
    for b, c in enumerate(PROG_A):
        full = b < 2
        steps = arp_bar(c, ARP_UP, 3)
        if b == 3:                       # let the loop breathe: stop before the seam
            steps = steps[:12]
        bl = [(s, n) for s, n in bass_bar(c, BASS_E)]
        if b == 3:
            bl = bl[:1]
        bar(P, b*16, c,
            arp=steps, arpvol=[33, 32, 30, 30][b],
            arp2=arp_bar(c, ARP_GATE, 3) if full else None,
            arp2vol=19 if full else 0,
            bass=(BASS_B if b % 2 == 0 else BASS_D) if full else bl,
            bassvol=48 if full else 36,
            kick=DRUM_KICK_C if full else [(0, 56)],
            snare=SNARE_A if full else None,
            hat=HAT_B if full else None,
            lead=mel(b, MEL_A) if full else None, leadvol=53)
    return P

BUILDERS = [p_intro, p_rhythm, p_lead_a, p_lead_a2, p_lead_a3, p_lead_b, p_lead_b2,
            p_break, p_break2, p_build, p_peak_a, p_peak_a2, p_peak_b, p_bridge,
            p_climax, p_outro]

def build(out="/workspace/submission/tune.xm", bpm=150, speed=6):
    pats = []
    for fn in BUILDERS:
        P = fn()
        pats.append((P.rows, P.cells))
    instruments = [dict(name=k.upper()[:22], sample_path='/workspace/samples/' + v[0],
                        vol=v[1], pan=v[2], rel_note=REL_NOTE, finetune=FINETUNE)
                   for k, v in SAMPLES.items()]
    build_xm(out, "Neon Licence", pats, instruments,
             order=list(range(len(pats))), bpm=bpm, speed=speed, channels=12, restart=0)
    return out, pats

if __name__ == "__main__":
    path, pats = build()
    notes = sum(len(c) for _, c in pats)
    print(f"wrote {path}: {len(pats)} patterns, {notes} note events")
