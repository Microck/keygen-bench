"""Composition: 'key of D minor' keygen-style chiptune, 140 BPM, speed 3
(8 rows per beat, 64-row patterns = 2 bars).  All notes are entered as tracker
pattern data; this file only describes them in a compact text form."""

RPB = 32          # rows per bar
STEP = 2          # rows per 16th note
NCH = 16
VSCALE = 1.10     # master trim applied to every volume-column value

CH = dict(lead=0, echo=1, arp=2, plk=3, plk2=4, bass=5, kick=6, snare=7, hat=8,
          fx=9, pad1=10, pad2=11, pad3=12, dbl=13, clap=14, fx2=15)

SEMI = {'c': 0, 'c#': 1, 'db': 1, 'd': 2, 'd#': 3, 'eb': 3, 'e': 4, 'f': 5, 'f#': 6,
        'gb': 6, 'g': 7, 'g#': 8, 'ab': 8, 'a': 9, 'a#': 10, 'bb': 10, 'b': 11}
KEYOFF = 97


def nn(s):
    """'d6' -> XM note number (C-0 == 1)."""
    return 12 * int(s[-1]) + SEMI[s[:-1]] + 1


class Song:
    def __init__(self):
        self.cells = {}

    def put(self, row, ch, note=None, ins=None, vol=None, fx=None, fxp=None, force_fx=True):
        if row < 0:
            return
        c = self.cells.setdefault((row, ch), [0, 0, 0, None, 0])
        if note is not None:
            c[0] = note
        if ins is not None:
            c[1] = ins
        if vol is not None:
            c[2] = 0x10 + max(0, min(64, int(round(vol * VSCALE))))
        if fx is not None and (force_fx or c[3] is None):
            c[3] = fx
            c[4] = fxp

    def raw_vol(self, row, ch, byte):
        c = self.cells.setdefault((row, ch), [0, 0, 0, None, 0])
        c[2] = byte

    def off(self, row, ch):
        c = self.cells.setdefault((row, ch), [0, 0, 0, None, 0])
        if c[0] == 0:
            c[0] = KEYOFF


# ----------------------------------------------------------------------------
# harmony
# ----------------------------------------------------------------------------
CHORD = {
    #        bass   arp-channel (note, 0xy)   six chord tones for plucks / pads
    'Dm': ('d2', ('d5', 0x37), 'd4 f4 a4 d5 f5 a5'),
    'Bb': ('bb1', ('d5', 0x38), 'd4 f4 bb4 d5 f5 bb5'),
    'F': ('f2', ('c5', 0x59), 'c4 f4 a4 c5 f5 a5'),
    'C': ('c2', ('c5', 0x47), 'c4 e4 g4 c5 e5 g5'),
    'Gm': ('g1', ('d5', 0x58), 'd4 g4 bb4 d5 g5 bb5'),
    'A': ('a1', ('c#5', 0x38), 'c#4 e4 a4 c#5 e5 a5'),
    'Am': ('a1', ('c5', 0x49), 'c4 e4 a4 c5 e5 a5'),
}
PROG_A = ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'Gm', 'A']
PROG_B = ['Gm', 'Am', 'Bb', 'C', 'Gm', 'Am', 'Bb', 'C']
PROG_C = ['F', 'C', 'Dm', 'Bb', 'F', 'C', 'Dm', 'A']
PROG_K = ['Dm', 'Dm', 'Bb', 'Bb', 'Gm', 'Gm', 'A', 'A']

# ----------------------------------------------------------------------------
# melodies: 16 tokens per bar (16th notes); '-' hold, '.' rest, '/x' scoop
# ----------------------------------------------------------------------------
THEME_A = [
    'd6 - - a5 - - f5 - g5 - a5~ - - - g5 a5',
    'bb5 - - f5 - - bb5 - d6 - - - c6 - bb5 -',
    'a5 - - c6 - - f6 - d6 - c6~ - - - a5 c6',
    'e6 - - d6 - - c6 - g5 - - - e5 g5 c6 e6',
    'f6 - - e6 - - d6 - a5 - c6~ - - - d6 e6',
    'f6 - - d6 - - bb5 - c6 - d6 - - - e6 f6',
    '/g6 - - f6 - - d6 - bb5 - d6 - - - c6 bb5',
    'a5 - - - c#6 - /e6! - - - - - . . . .',
]
THEME_A3 = THEME_A[:4] + [      # third statement: the answer phrase breaks into 16th-note runs
    'f6 e6 d6 a5 f6 e6 d6 a5 d6 c6 a5 f5 a5 c6 d6 e6',
    'f6 d6 bb5 f5 f6 d6 bb5 f5 bb5 c6 d6 f6 d6 c6 d6 f6',
    'g6 d6 bb5 g5 g6 d6 bb5 g5 bb5 d6 g6 d6 bb5 d6 c6 bb5',
    'a5 c#6 e6 a5 c#6 e6 a5 c#6 /e6! - - - . . . .',
]
HARM_A = [   # harmony voice for bars 5-8 of the theme
    'd6 - - c6 - - a5 - f5 - a5 - - - bb5 c6',
    'd6 - - bb5 - - f5 - g5 - bb5 - - - c6 d6',
    'bb5 - - d6 - - bb5 - g5 - bb5 - - - a5 g5',
    'e5 - - - a5 - c#6 - - - - - . . . .',
]
THEME_B = [
    '/d6 - - - - - - - - - - - - - . .',
    '/e6 - - - - - - - - - - - - - . .',
    '/f6 - - - - - - - - - - - - - . .',
    '/g6 - - - - - - - e6 - - - c6 - - -',
    'bb5 - - g5 - - bb5 - d6 - - - c6 - bb5 -',
    'c6 - - a5 - - c6 - e6 - - - d6 - c6 -',
    'd6 - - bb5 - - d6 - f6 - - - g6 - f6 -',
    'e6 - - - - - /g6 - - - - - - - . .',
]
HARM_B = [
    'bb5 - - - - - - - - - - - - - . .',
    'c6 - - - - - - - - - - - - - . .',
    'd6 - - - - - - - - - - - - - . .',
    'e6 - - - - - - - c6 - - - g5 - - -',
]
THEME_C = [
    'a5 - c6 - /f6 - - - - - e6 - f6 - g6 -',
    'e6 - - - - - c6 - g5 - - - c6 - e6 -',
    'f6 - - - - - e6 - d6 - - - a5 - c6 -',
    'd6 - - - c6 - bb5 - - - c6 - d6 - f6 -',
    'a5 - c6 - /f6 - - - - - e6 - f6 - g6 -',
    '/g6 - - - - - e6 - c6 - - - e6 - g6 -',
    'f6 - - - - - e6 - d6 - - - f6 - e6 -',
    'e6 - - - c#6 - a5! - - - . . . . . .',
]
HARM_C = [      # lower harmony (thirds / chord tones) that joins the last chorus
    'f5 - a5 - c6 - - - - - c6 - d6 - e6 -',
    'c6 - - - - - g5 - e5 - - - g5 - c6 -',
    'd6 - - - - - c6 - a5 - - - f5 - a5 -',
    'bb5 - - - g5 - f5 - - - g5 - bb5 - d6 -',
    'f5 - a5 - c6 - - - - - c6 - d6 - e6 -',
    'e6 - - - - - c6 - g5 - - - c6 - e6 -',
    'd6 - - - - - c6 - a5 - - - d6 - c6 -',
    'c#6 - - - a5 - e5! - - - . . . . . .',
]
TEASER = [      # soft triangle line over the second half of the intro; its C# leads into the theme's D
    'd6 - - - - - - - a5 - - - - - f5 -',
    'bb5 - - - - - - - d6 - - - - - - -',
    'd6 - - - - - - - bb5 - - - g5 - - -',
    'a5 - - - - - - - c#6 - - - . . . .',
]
THEME_K = [
    'a5 - - - - - - - f5 - - - a5 - - -',
    '/d6 - - - - - - - - - - - c6 - a5 -',
    'bb5 - - - - - - - f5 - - - bb5 - - -',
    '/d6 - - - - - - - - - - - f6 - d6 -',
    'd6 - - - - - - - bb5 - - - g5 - - -',
    'bb5 - - - - - - - g5 - - - bb5 - - -',
    'a5 - - - - - - - - - - - - - - -',
    'c#6 - - - - - - - /e6 - - - - - . .',
]


def mel_events(bars):
    ev, cur, step = [], None, 0
    for b in bars:
        toks = b.split()
        assert len(toks) == 16, (len(toks), b)
        for t in toks:
            if t == '-':
                if cur is not None:
                    cur['len'] += 1
            elif t == '.':
                cur = None
            else:
                cur = dict(step=step, len=1, note=nn(t.strip('/!~')), scoop=t.startswith('/'),
                           fall=t.endswith('!'), mord=t.endswith('~'))
                ev.append(cur)
            step += 1
    return ev


def build(I):
    """I: instrument-name -> instrument number.  Returns (Song, total_rows, restart_bar)."""
    s = Song()

    def lead_ins(n):
        return I['lead_lo'] if n < nn('c6') else I['lead_hi']

    def dbl_ins(n):
        return I['dbl_lo'] if n < nn('c6') else I['dbl_hi']

    def const(name):
        return lambda n: I[name]

    TOTAL_BARS = 72
    MAXROW = TOTAL_BARS * RPB
    BAR_CHORD = {}
    SONG_CHORDS = PROG_A * 3 + PROG_B + PROG_C + PROG_K + PROG_A + PROG_B + PROG_C
    assert len(SONG_CHORDS) == TOTAL_BARS

    def in_key(n, bar):
        pc = (n - 1) % 12
        if SONG_CHORDS[bar] == 'A':
            return pc in (2, 4, 5, 7, 9, 10, 1)
        return pc in (2, 4, 5, 7, 9, 10, 0)

    def melody(ch, bar, bars, ins_fn, vol, env=(1.0, 0.88, 0.80, 0.76), vib=0x63, delay=0,
               pan=None, transpose=0, offs=None, vib_min=8):
        ev = mel_events(bars)
        row0 = bar * RPB + delay
        for i, e in enumerate(ev):
            r0 = row0 + e['step'] * STEP
            L = e['len'] * STEP
            if r0 >= MAXROW:
                continue
            n = e['note'] + transpose
            if delay and not in_key(n, r0 // RPB):
                # an echo that would land on a chord it does not belong to is dropped
                if r0 < MAXROW:
                    s.off(r0, ch)
                continue
            ins = ins_fn(n)
            if e['mord'] and L >= 6:
                # mordent: note - upper scale neighbour - note, one row (a 32nd) each
                up = n + 1
                while not in_key(up, min(r0 // RPB, TOTAL_BARS - 1)):
                    up += 1
                s.put(r0, ch, note=n, ins=ins, vol=vol * env[0])
                s.put(r0 + 1, ch, note=up, ins=ins_fn(up), vol=vol * env[0] * 0.85)
                if pan is not None:
                    s.put(r0, ch, fx=8, fxp=pan, force_fx=False)
                    s.put(r0 + 1, ch, fx=8, fxp=pan, force_fx=False)
                r0 += 2
                L -= 2
            if e['scoop'] and L >= 4:
                s.put(r0, ch, note=n - 2, ins=ins, vol=vol * env[0])
                s.put(r0 + 1, ch, note=n, fx=3, fxp=0x20)
            else:
                s.put(r0, ch, note=n, ins=ins, vol=vol * env[0])
            if offs is not None:
                s.put(r0, ch, fx=9, fxp=offs, force_fx=False)
            elif pan is not None:
                s.put(r0, ch, fx=8, fxp=pan, force_fx=False)
            for k in range(1, min(L, len(env))):
                if r0 + k < MAXROW:
                    s.put(r0 + k, ch, vol=vol * env[k])
            if vib and L >= vib_min:
                for k in range(4, L):
                    if r0 + k < MAXROW:
                        s.put(r0 + k, ch, fx=4, fxp=vib, force_fx=False)
            if e['fall'] and L >= 6:
                # classic chip "fall": pitch drops while the note fades out
                for j, k in enumerate(range(L - 3, L)):
                    if r0 + k < MAXROW:
                        s.put(r0 + k, ch, vol=vol * env[-1] * (0.7, 0.45, 0.22)[j], fx=2, fxp=0x14)
            nxt = (row0 + ev[i + 1]['step'] * STEP) if i + 1 < len(ev) else None
            if (nxt is None or nxt > r0 + L) and r0 + L < MAXROW:
                s.off(r0 + L, ch)

    def lead_with_echo(bar, bars, vol=46, echo=0.34, pan=None, ins_fn=None, **kw):
        ins_fn = ins_fn or lead_ins
        melody(CH['lead'], bar, bars, ins_fn, vol, pan=pan, **kw)
        melody(CH['echo'], bar, bars, ins_fn, vol * echo, delay=6, pan=0xD0,
               env=(1.0, 0.9, 0.85), **kw)

    # -- chords on the arp channel -------------------------------------------
    TRESILLO = [(0, 2, 1.0), (3, 2, 0.8), (6, 2, 0.9), (8, 2, 1.0), (11, 2, 0.8), (14, 2, 0.9)]
    OFFBEAT = [(2, 2, 1.0), (6, 2, 0.9), (10, 2, 1.0), (14, 2, 0.9)]
    SIXTEENTHS = [(i, 1, (1.0, 0.6, 0.8, 0.6)[i % 4]) for i in range(16)]

    def chord_hits(bar, chord, hits, vol, ins='sq50', octave=0, decay=0.82):
        note, arp = CHORD[chord][1]
        n = nn(note) + 12 * octave
        for st, ln, vs in hits:
            r0 = bar * RPB + st * STEP
            rows = ln * STEP
            s.put(r0, CH['arp'], note=n, ins=I[ins], vol=vol * vs, fx=0, fxp=arp)
            for k in range(1, rows):
                s.put(r0 + k, CH['arp'], vol=vol * vs * decay ** k, fx=0, fxp=arp)
            s.off(r0 + rows, CH['arp'])

    def chord_hold(bar, chord, v0, v1, ins='sq50', rows=RPB):
        note, arp = CHORD[chord][1]
        r0 = bar * RPB
        for k in range(rows):
            v = v0 + (v1 - v0) * k / max(1, rows - 1)
            if k == 0:
                s.put(r0, CH['arp'], note=nn(note), ins=I[ins], vol=v, fx=0, fxp=arp)
            else:
                s.put(r0 + k, CH['arp'], vol=v, fx=0, fxp=arp)
        s.off(r0 + rows, CH['arp'])

    # -- bass -------------------------------------------------------------------
    BASS_VERSE = 'L - H - L - H L - L H - L - H -'
    BASS_VERSE2 = 'L - H - L - H L - L H - L H 5 H'
    BASS_PRE = 'L - - L - - L - - - L - L - H -'
    BASS_CHOR = 'L L H L L L H L L L H L L H L H'
    BASS_CHOR2 = 'L L H L L L H L L L H L 5 H 5 H'
    BASS_LONG = 'L - - - - - - - - - - - - - H -'
    BASS_HALF = 'L - - - - - - - L - - - - - H -'

    def bass(bar, chord, pat, vol=35):
        root = nn(CHORD[chord][0])
        toks = pat.split()
        assert len(toks) == 16
        iv = {'L': 0, 'H': 12, '5': 7, '7': 10, '4': 5}
        i = 0
        while i < 16:
            t = toks[i]
            if t in iv:
                j = i + 1
                while j < 16 and toks[j] == '-':
                    j += 1
                r0 = bar * RPB + i * STEP
                acc = 1.0 if t == 'L' else 0.86
                s.put(r0, CH['bass'], note=root + iv[t], ins=I['bass'], vol=vol * acc)
                s.off(bar * RPB + j * STEP, CH['bass'])
                i = j
            else:
                i += 1

    # -- drums ------------------------------------------------------------------
    def hits(bar, ch, pat, ins_map, note='c4'):
        n = len(pat)
        assert n in (16, 32), n
        per = RPB // n
        for i, c in enumerate(pat):
            if c in ins_map:
                ins, vol = ins_map[c]
                s.put(bar * RPB + i * per, ch, note=nn(note), ins=I[ins], vol=vol)

    KICK = {'x': ('kick', 47), 'o': ('kick', 38)}
    SNARE = {'x': ('snare', 40), 'o': ('snare', 19), 'm': ('snare', 31)}
    HAT = {'x': ('hat', 48), 'o': ('hat', 28), 'O': ('ohat', 44), 'm': ('hat', 36)}
    CLAP = {'x': ('clap', 26)}

    def drums(bar, k=None, sn=None, h=None, cl=None):
        if k:
            hits(bar, CH['kick'], k, KICK)
        if sn:
            hits(bar, CH['snare'], sn, SNARE)
        if h:
            hits(bar, CH['hat'], h, HAT)
        if cl:
            hits(bar, CH['clap'], cl, CLAP)

    def crash(bar, vol=44):
        s.put(bar * RPB, CH['fx'], note=nn('c4'), ins=I['crash'], vol=vol)

    def snare_roll(bar, v0=11, v1=45, start_row=0):
        """8ths -> 16ths -> 32nds with a crescendo over one bar."""
        rows = [r for r in range(0, 16, 4)] + [r for r in range(16, 24, 2)] + list(range(24, 32))
        rows = [r for r in rows if r >= start_row]
        for r in rows:
            v = v0 + (v1 - v0) * (r / 31.0) ** 1.3
            s.put(bar * RPB + r, CH['snare'], note=nn('c4'), ins=I['snare'], vol=v)
            if r >= 30:
                s.put(bar * RPB + r, CH['snare'], fx=0xE, fxp=0x91)   # E91: buzz the last two hits

    def riser(bar, nbars=1, v0=3, v1=34, speed=None):
        rows = nbars * RPB
        speed = speed or max(1, int(round(36 * 64 / (rows * 2.0) / 4.0)))  # ~3 octaves
        r0 = bar * RPB
        for k in range(rows):
            v = v0 + (v1 - v0) * (k / (rows - 1.0)) ** 1.6
            if k == 0:
                s.put(r0, CH['fx2'], note=nn('c3'), ins=I['noise'], vol=v, fx=1, fxp=speed)
            else:
                s.put(r0 + k, CH['fx2'], vol=v, fx=1, fxp=speed)
        if r0 + rows < MAXROW:
            s.off(r0 + rows, CH['fx2'])
        else:
            s.put(8 * RPB, CH['fx2'], note=KEYOFF)   # song end: stop it at the restart row

    def tom_fill(bar, spec, vol=42):
        """spec: list of (row_in_bar, note)"""
        for r, note in spec:
            pan = {'g4': 0x40, 'e4': 0x58, 'c4': 0x74, 'a3': 0x90, 'f3': 0xA8}.get(note, 0x80)
            s.put(bar * RPB + r, CH['fx2'], note=nn(note), ins=I['tom'], vol=vol, fx=8, fxp=pan)

    def runup(bar, notes, start_row=24, v0=13, v1=30, ins='p25'):
        """32nd-note chord run sweeping left -> right into the next downbeat."""
        n = len(notes)
        for j, name in enumerate(notes):
            r = bar * RPB + start_row + j
            s.put(r, CH['dbl'], note=nn(name), ins=I[ins], vol=v0 + (v1 - v0) * j / (n - 1.0),
                  fx=8, fxp=int(0x38 + (0xC8 - 0x38) * j / (n - 1.0)))
        end = bar * RPB + start_row + n
        s.off(end if end < MAXROW else 8 * RPB, CH['dbl'])     # song end: cut on the restart row

    RUN_A = ['e4', 'a4', 'c#5', 'e5', 'a5', 'c#6', 'e6', 'a6']     # over A major -> Dm
    RUN_C = ['e4', 'g4', 'c5', 'e5', 'g5', 'c6', 'e6', 'g6']       # over C major -> F

    # -- plucked sequences ---------------------------------------------------------
    P_FLOW = [0, 2, 3, 2, 4, 2, 3, 2, 5, 2, 3, 2, 4, 2, 3, 2]
    P_FORE = [0, 3, 4, 3, 5, 3, 4, 3, 0, 3, 4, 5, 4, 3, 2, 3]
    P_SPARK = [3, 4, 5, 4, 3, 4, 5, 4, 3, 4, 5, 4, 3, 5, 4, 5]
    P_VERSE = [0, None, 3, 2, None, 3, 2, None, 4, None, 3, 2, None, 3, 4, 3]
    ACC = (1.0, 0.62, 0.8, 0.62)

    def pluck(bar, chord, pat, vol, echo=0.38, transpose=0, vscale=None):
        BAR_CHORD[bar] = chord
        tones = [nn(t) for t in CHORD[chord][2].split()]
        for i, ix in enumerate(pat):
            if ix is None:
                continue
            v = vol * ACC[i % 4] * (vscale(i) if vscale else 1.0)
            r0 = bar * RPB + i * STEP
            s.put(r0, CH['plk'], note=tones[ix] + transpose, ins=I['pluck'], vol=v)
            if echo and r0 + 6 < MAXROW:
                eb = (r0 + 6) // RPB
                if eb != bar and SONG_CHORDS[eb] != chord:
                    continue                      # would ring the previous chord into the new one
                s.put(r0 + 6, CH['plk2'], note=tones[ix] + transpose, ins=I['pluck_e'], vol=v * echo)

    def pad(bar, chord, vol, nbars=1, fade_in=8, fade_out=6):
        tones = [nn(t) for t in CHORD[chord][2].split()][:3]
        rows = nbars * RPB
        r0 = bar * RPB
        for ch, n, ins in ((CH['pad1'], tones[0], 'pad_l'), (CH['pad2'], tones[1], 'pad_r'),
                           (CH['pad3'], tones[2], 'pad_l')):
            for k in range(rows):
                if k < fade_in:
                    v = vol * (0.25 + 0.75 * k / fade_in)
                elif k >= rows - fade_out:
                    v = vol * (0.35 + 0.65 * (rows - 1 - k) / fade_out)
                else:
                    v = None
                if k == 0:
                    s.put(r0, ch, note=n, ins=I[ins], vol=v)
                    if ch == CH['pad3']:
                        s.put(r0, ch, fx=9, fxp=0x10)        # different phase of the beating
                elif v is not None or k == fade_in:
                    s.put(r0 + k, ch, vol=v if v is not None else vol)
            if r0 + rows < MAXROW:
                s.off(r0 + rows, ch)

    # ==========================================================================
    # INTRO  (bars 0-7)  -- played once, the loop restarts at bar 8
    # ==========================================================================
    b0 = 0
    for i, c in enumerate(PROG_A):
        bar = b0 + i
        pluck(bar, c, P_FLOW, (42, 44, 45, 46)[min(i, 3)], echo=0.42)
        pad(bar, c, 18 + i)
        # the buzzing chord arpeggio is there from the very first row
        chord_hits(bar, c, TRESILLO, (20, 22, 24, 25, 26, 26, 27, 27)[i])
        if i >= 4:
            bass(bar, c, BASS_HALF if i < 7 else 'L - - - L - - - L - L - L L L L', vol=30 + 2 * (i - 4))
            drums(bar, k='x...x...x...x...', h='x.o.x.o.x.o.x.o.' if i < 6 else 'x.o.x.oox.o.x.oo')
        elif i >= 2:
            drums(bar, h='..o...o...o...o.' if i == 2 else 'x.o.x.o.x.o.x.oo')
    snare_roll(b0 + 7, 9, 43)
    riser(b0 + 6, nbars=2, v0=2, v1=30)
    runup(b0 + 7, RUN_A)
    melody(CH['lead'], b0 + 4, TEASER, const('tri'), 19, env=(1.0, 0.95, 0.9), vib=0x52)
    melody(CH['echo'], b0 + 4, TEASER, const('tri'), 8, delay=6, pan=0xC8, env=(1.0, 0.95, 0.9), vib=0x52)

    # ==========================================================================
    # A1  (bars 8-15)  main theme
    # ==========================================================================
    def verse(b0, variant):
        crash(b0)
        theme = THEME_A3 if variant == 2 else THEME_A
        lead_with_echo(b0, theme)
        for i, c in enumerate(PROG_A):
            bar = b0 + i
            chord_hits(bar, c, TRESILLO, 24)
            bass(bar, c, BASS_VERSE2 if i % 4 == 3 else BASS_VERSE)
            last = (i == 7)
            if variant == 0:
                h = 'x.o.x.o.x.o.x.oo' if i % 2 == 0 else 'x.o.x.o.x.o.O.o.'
            else:
                h = 'xooomooOxooomooo' if i % 2 == 0 else 'xooomoooxoooO.oo'
            if not last:
                drums(bar, k='x......x..x.....' if i % 4 != 3 else 'x......x..x..x..',
                      sn='....x.......x...' if i % 2 == 0 else '....x.......x..o', h=h)
            else:
                drums(bar, k='x......x........', sn='....x...x.xx.x..', h=h[:8] + 'x.x.....')
                tom_fill(bar, [(24, 'e4'), (26, 'c4'), (28, 'a3'), (30, 'f3')] if variant == 0 else
                         [(22, 'g4'), (24, 'e4'), (26, 'e4'), (28, 'c4'), (29, 'c4'), (30, 'a3'), (31, 'f3')])
            if variant >= 1:
                pluck(bar, c, P_VERSE, 28, echo=0.4)
        if variant == 1:
            # second statement: harmony voice joins for the last four bars
            melody(CH['dbl'], b0 + 4, HARM_A, const('p25'), 27, pan=0xA8, vib=0x62)
        if variant == 2:
            # third statement: the theme is doubled an octave below
            melody(CH['dbl'], b0, theme, const('p25'), 24, pan=0xA8, transpose=-12, vib=0x62)

    verse(8, 0)
    verse(16, 1)

    # ==========================================================================
    # B  (pre-chorus)  rising ii-iii-IV-V of the relative major
    # ==========================================================================
    def pre(b0, variant):
        crash(b0, 38)
        lead_with_echo(b0, THEME_B, vol=44)
        if variant == 1:
            melody(CH['dbl'], b0, HARM_B, const('p25'), 22, pan=0xA8, vib=0x62)
        else:
            # first time: a soft triangle octave-shimmer (0C0 arpeggio) on the long notes
            for i, name in enumerate(('d6', 'e6', 'f6')):
                r0 = (b0 + i) * RPB
                for k in range(4, 28):
                    v = 15 * min(1.0, (k - 3) / 6.0) * (1.0 if k < 24 else (28 - k) / 4.0)
                    if k == 4:
                        s.put(r0 + k, CH['dbl'], note=nn(name), ins=I['tri32'], vol=v, fx=0, fxp=0xC0)
                    else:
                        s.put(r0 + k, CH['dbl'], vol=v, fx=0, fxp=0xC0)
                s.off(r0 + 28, CH['dbl'])
        for i, c in enumerate(PROG_B):
            bar = b0 + i
            pluck(bar, c, P_FORE, (44 if variant == 0 else 39) if i < 4 else 36, echo=0.45)
            pad(bar, c, 18)
            bass(bar, c, BASS_PRE, vol=36)
            if i >= 4:
                chord_hits(bar, c, OFFBEAT, 20)
            if i < 7:
                if variant == 0 and i < 4:
                    drums(bar, k='x.......x.....x.' if i % 2 else 'x.......x.......', sn='....x.......x...',
                          h='x.o.x.o.x.o.x.o.')
                else:
                    drums(bar, k='x.....x.x.....x.' if i % 2 else 'x.....x.x.......', sn='....x.......x...',
                          h='momomomomomomoOo' if i % 2 else 'momomomomomomomo')
            else:
                drums(bar, k='x...x...x...x...', h='xoxoxoxoxoxoxoxo')
                snare_roll(bar, 11, 45)
                riser(bar, 1, v0=4, v1=32)
                runup(bar, RUN_C)

    pre(24, 0)

    # ==========================================================================
    # C  (chorus)  relative major: F C Dm Bb | F C Dm A
    # ==========================================================================
    def chorus(b0, variant):
        crash(b0, 48)
        melody(CH['lead'], b0, THEME_C, lead_ins, 48, pan=0x6C)
        melody(CH['dbl'], b0, THEME_C, dbl_ins, 32, offs=0x20, vib=0x63)
        melody(CH['echo'], b0, THEME_C, lead_ins, 15, delay=6, pan=0xD8, env=(1.0, 0.9, 0.85))
        for i, c in enumerate(PROG_C):
            bar = b0 + i
            last = (i == 7)
            if variant == 0:
                chord_hits(bar, c, OFFBEAT, 31)
            else:
                chord_hits(bar, c, SIXTEENTHS, 42, ins='p12', octave=0, decay=0.7)
            pluck(bar, c, P_SPARK, 28, echo=0.4)
            bass(bar, c, BASS_CHOR2 if i % 4 == 3 else BASS_CHOR, vol=36)
            if not last:
                drums(bar, k='x...x...x...x...' if i % 4 != 3 else 'x...x...x...x.x.',
                      sn='....x.......x...', cl='....x.......x...',
                      h='ooOoooOoooOoooOo')
            elif variant == 0:
                drums(bar, k='x...x...x.......', sn='....x...x.x.xxxx', cl='....x...........', h='ooOoooOo........')
                tom_fill(bar, [(16, 'e4'), (20, 'c4'), (24, 'a3'), (28, 'f3')])
            else:
                # last bar of the song: build straight back into the restart
                drums(bar, k='x...x...x...x...', cl='....x...........', h='ooOoooOoooOoooOo')
                snare_roll(bar, 13, 46, start_row=8)
                riser(bar, 1, v0=4, v1=30)
                runup(bar, RUN_A)
        if variant == 1:
            crash(b0 + 4, 44)
            melody(CH['pad1'], b0, HARM_C, const('p25'), 19, pan=0xB8, vib=0x62)

    chorus(32, 0)

    # ==========================================================================
    # K  (breakdown)
    # ==========================================================================
    b0 = 40
    crash(b0, 46)
    melody(CH['lead'], b0, THEME_K, const('tri'), 26, env=(1.0, 0.95, 0.9), vib=0x52)
    melody(CH['echo'], b0, THEME_K, const('tri'), 12, delay=6, pan=0xC8, env=(1.0, 0.95, 0.9), vib=0x52)
    for i, c in enumerate(PROG_K):
        bar = b0 + i
        pluck(bar, c, P_FLOW, 38 if i < 6 else 32, echo=0.45)
        pad(bar, c, 22 if i < 6 else 17)
        bass(bar, c, BASS_LONG if i < 4 else BASS_HALF, vol=27 if i < 4 else 32)
        if i in (2, 3):
            drums(bar, h='..o...o...o...o.' if i == 2 else 'x.o.x.o.x.o.x.oo')
        elif i in (4, 5):
            drums(bar, k='o...o...o...o...', h='x.o.x.o.x.o.x.oo')
            chord_hold(bar, c, 6 + 4 * (i - 4), 10 + 4 * (i - 4))
        elif i == 6:
            drums(bar, k='o...o...o...o...', sn='....m.......m...', h='xoxoxoxoxoxoxoxo')
            chord_hold(bar, c, 12, 15)
        elif i == 7:
            drums(bar, k='o...o...o...o...', h='xoxoxoxoxoxoxoxo')
            chord_hold(bar, c, 15, 20)
            snare_roll(bar, 11, 45)
    riser(b0 + 6, nbars=2, v0=2, v1=32)
    runup(b0 + 7, RUN_A)

    # ==========================================================================
    verse(48, 2)       # A3
    pre(56, 1)         # B2
    chorus(64, 1)      # C2  -> loops back to bar 8

    # ==========================================================================
    # tracker-style "sidechain": the bass ducks for two rows under every kick so the
    # kick keeps its punch and the low end does not pile up
    # ==========================================================================
    state, sounding, cur = {}, False, None
    for r in range(MAXROW):
        c = s.cells.get((r, CH['bass']))
        if c:
            if c[0] == KEYOFF:
                sounding = False
            elif c[0]:
                sounding = True
            if c[2]:
                cur = c[2] - 0x10
        state[r] = (sounding, cur)
    kick_rows = sorted(r for (r, ch), c in s.cells.items() if ch == CH['kick'] and c[0] not in (0, KEYOFF))
    for r in kick_rows:
        if not state[r][0]:
            continue
        for k, f in ((0, 0.62), (1, 0.80), (2, 1.0)):
            rr = r + k
            if rr >= MAXROW:
                break
            c = s.cells.get((rr, CH['bass']))
            if k > 0 and c and c[0]:
                break                               # a new bass note (or key-off) takes over
            s.raw_vol(rr, CH['bass'], 0x10 + int(round(state[rr][1] * f)))

    return s, MAXROW, 8
