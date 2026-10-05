"""Compose the keygen tune -> /workspace/submission/tune.xm"""
import sys, numpy as np
sys.path.insert(0, '/workspace/py')
from xmwrite import XMBuilder, note_to_num
from sound import build_samples

# --- channel map ---
CH_LEAD, CH_ARP, CH_BASS, CH_PAD, CH_KICK, CH_SNARE, CH_HAT, CH_FX = range(8)
# instrument numbers (1-based)
I_P25, I_P12, I_P50, I_BASS, I_PAD, I_BELL, I_KICK, I_SNARE, I_HATC, I_HATO, I_CRASH = range(1, 12)

def put(cells, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
    if row < 0: return
    if vol is not None:
        vol = 0x10 + max(0, min(64, int(vol)))   # volume column = 0x10 + volume(0..64)
    key = (row, ch)
    cur = cells.get(key)
    if cur is None:
        cells[key] = [note, inst, vol, fx, param]
    else:
        if note is not None: cur[0] = note
        if inst is not None: cur[1] = inst
        if vol is not None: cur[2] = vol
        if fx is not None: cur[3] = fx
        if param is not None: cur[4] = param

# ------------------------------------------------------------------ chords ---
# note numbers: C-4 = 49
CHORDS = {
    # note numbers: C-4 = 49 ; roots in the bass octave
    'Am':  dict(root=34, triad=[58, 61, 65], lo=[46, 49, 53], pad=46, padhi=58),   # A-2 | A-4 C-5 E-5
    'F':   dict(root=30, triad=[54, 58, 61], lo=[42, 46, 49], pad=42, padhi=54),   # F-2 | F-4 A-4 C-5
    'C':   dict(root=37, triad=[61, 65, 68], lo=[49, 53, 56], pad=49, padhi=61),   # C-3 | C-5 E-5 G-5
    'G':   dict(root=32, triad=[56, 60, 63], lo=[44, 48, 51], pad=44, padhi=56),   # G-2 | G-4 B-4 D-5
    'Dm':  dict(root=39, triad=[63, 66, 70], lo=[51, 54, 58], pad=51, padhi=63),   # D-3 | D-5 F-5 A-5
    'E7':  dict(root=29, triad=[53, 57, 60, 63], lo=[41, 45, 48, 51], pad=41, padhi=53),  # E-2 | E-4 G#4 B-4 D-5
    'E':   dict(root=29, triad=[53, 57, 60], lo=[41, 45, 48], pad=41, padhi=53),
    'Gm':  dict(root=32, triad=[56, 59, 63], lo=[44, 47, 51], pad=44, padhi=56),
}
#  E7 triad: E-4(53) G#4(57) B-4(60) D-5(63)

# arp figures (indices into the triad list)
FIG = {
 'up':    [0, 1, 2, 1],
 'rock':  [0, 2, 1, 2],
 'oct':   [0, 1, 2, 0],
 'down':  [2, 1, 0, 1],
 'wide':  [0, 1, 2, 3],
 'pump':  [0, 0, 1, 1],
 'roll':  [0, 1, 2, 3, 2, 1],
}

def arp_bar(cells, row0, chord, figure, inst=I_P12, vhi=0x2c, vlo=0x20, octshift=0, span=16):
    c = CHORDS[chord]
    tri = [n + 12*octshift for n in c['triad']]
    fig = FIG[figure]
    for i in range(span):
        n = tri[fig[i % len(fig)] % len(tri)]
        v = vhi if i % 4 == 0 else (vlo + (2 if i % 2 else 0))
        put(cells, row0+i, CH_ARP, n, inst, v)

def arp_hold(cells, row0, chord, arp_param=0x37, inst=I_P12, vol=0x28, dur=16):
    """hold one note with the arpeggio effect (fast triad shimmer)"""
    c = CHORDS[chord]
    put(cells, row0, CH_ARP, c['lo'][0], inst, vol, 0x00, arp_param)
    for r in range(row0+4, row0+dur, 4):
        put(cells, r, CH_ARP, None, None, vol)

# ------------------------------------------------------------------- bass ----
def bass_bar(cells, row0, chord, kind='drive', vol=0x32, inst=I_BASS):
    r = CHORDS[chord]['root']
    if kind == 'drive':
        pat = [(0, 0, 2), (2, 0, 2), (4, 12, 2), (6, 0, 2), (8, 0, 2), (10, 0, 2), (12, 12, 2), (14, 7, 2)]
    elif kind == 'gallop':
        pat = [(i, [0,0,12,0][i % 4], 1) for i in range(16)]
    elif kind == 'walk':
        pat = [(0, 0, 2), (2, 0, 2), (4, 12, 2), (6, 10, 2), (8, 12, 2), (10, 0, 2), (12, 7, 2), (14, 3, 2)]
    elif kind == 'long':
        pat = [(0, 0, 8), (8, 12, 8)]
    elif kind == 'half':
        pat = [(0, 0, 4), (4, 0, 4), (8, 12, 4), (12, 7, 4)]
    elif kind == 'roll':
        pat = [(i, 0 if i < 8 else 12, 1) for i in range(16)]
    else:
        raise ValueError(kind)
    for off, semi, dur in pat:
        put(cells, row0+off, CH_BASS, r+semi, inst, vol)

# ------------------------------------------------------------------- lead ----
def lead_phrase(cells, notes, inst=I_P25, vol=0x38, ch=CH_LEAD, cut=True, decay=None):
    """notes: list of (row, note, dur_rows). Adds EC0 cuts where a gap follows."""
    notes = sorted(notes, key=lambda x: x[0])
    for i, (r, n, d) in enumerate(notes):
        put(cells, r, ch, n, inst, vol)
        if decay:
            for k in range(1, d):
                nv = max(0, vol - decay*k)
                if nv != vol: put(cells, r+k, ch, None, None, nv)
        nxt = notes[i+1][0] if i+1 < len(notes) else 10**9
        if cut and d is not None and r+d < nxt:
            put(cells, r+d, ch, None, None, None, 0x0E, 0xC0)   # note cut

# ------------------------------------------------------------------ drums ----
def drums_bar(cells, row0, kind='main', hats=('8th', 0x28, 0x1c), fill=False):
    if kind in ('main', 'busy', 'hook'):
        kicks = [0, 4, 8, 12]
        if kind == 'busy': kicks = [0, 4, 8, 12, 14]
        if kind == 'hook': kicks = [0, 4, 8, 12, 10]
        for k in kicks:
            put(cells, row0+k, CH_KICK, 49, I_KICK, 0x40)
        for s in (4, 12):
            put(cells, row0+s, CH_SNARE, 49, I_SNARE, 0x38 if kind!='hook' else 0x40)
        if kind == 'busy':
            put(cells, row0+15, CH_SNARE, 49, I_SNARE, 0x20)
    elif kind == 'none':
        pass
    elif kind == 'thin':
        for k in (0, 8):
            put(cells, row0+k, CH_KICK, 49, I_KICK, 0x40)
        put(cells, row0+12, CH_SNARE, 49, I_SNARE, 0x34)
    # hats
    if hats and hats[0] == '8th':
        hv, ho = hats[1], hats[2]
        for i in range(0, 16, 2):
            put(cells, row0+i, CH_HAT, 49, I_HATC, hv if i % 4 == 0 else ho)
        put(cells, row0+14, CH_HAT, 49, I_HATO, 0x24)
    elif hats and hats[0] == '16th':
        hv, ho = hats[1], hats[2]
        for i in range(16):
            put(cells, row0+i, CH_HAT, 49, I_HATC, hv if i % 4 == 0 else ho)
    if fill:
        for i, r in enumerate(range(row0+12, row0+16)):
            put(cells, r, CH_SNARE, 49, I_SNARE, 0x20 + i*6)

def pad_bar(cells, row0, chord, octave='lo', vol=0x28, dur=16, inst=I_PAD):
    c = CHORDS[chord]
    n = c['pad'] if octave == 'lo' else c['padhi']
    put(cells, row0, CH_PAD, n, inst, vol)
    for r in range(row0+4, row0+dur, 4):
        put(cells, r, CH_PAD, None, None, vol)

def pad_progress(cells, row0, chord, v0=0x18, v1=0x30, dur=16):
    c = CHORDS[chord]
    n = c['pad']
    put(cells, row0, CH_PAD, n, I_PAD, v0)
    for r in range(row0+4, row0+dur, 4):
        v = int(v0 + (v1-v0)*((r-row0)/dur))
        put(cells, r, CH_PAD, None, None, v)

# =========================================================== patterns ========
def pat_intro():
    cells = {}
    # bar1 Am, bar2 F, bar3 C, bar4 G(build)
    bars = ['Am', 'F', 'C', 'G']
    for b, ch_name in enumerate(bars):
        r0 = b*16
        pad_progress(cells, r0, ch_name, 0x1e, 0x34)
    for b, ch_name in enumerate(bars):
        r0 = b*16
        if b < 2:
            arp_bar(cells, r0, ch_name, 'up', vhi=0x28, vlo=0x1c)
        else:
            arp_bar(cells, r0, ch_name, 'up', vhi=0x30, vlo=0x22)
    # hats from bar 2, kick from bar 3, snare bar 4
    for b in range(4):
        r0 = b*16
        if b >= 1:
            for i in range(0, 16, 2):
                put(cells, r0+i, CH_HAT, 49, I_HATC, 0x30 if i % 4 == 0 else 0x20)
    for b in range(2, 4):
        r0 = b*16
        for k in (0, 4, 8, 12):
            put(cells, r0+k, CH_KICK, 49, I_KICK, 0x38)
    for r in (12, 14):
        pass
    # fill in last bar
    for i, r in enumerate((52, 54, 56, 58, 60, 61, 62, 63)):
        put(cells, r, CH_SNARE, 49, I_SNARE, 0x14 + i*5)
    # bass enters in bar 3 (half notes)
    bass_bar(cells, 32, 'C', 'half', vol=0x2c)
    bass_bar(cells, 48, 'G', 'half', vol=0x2c)
    # bell accent
    put(cells, 0, CH_FX, 70, I_BELL, 0x28)
    put(cells, 32, CH_FX, 73, I_BELL, 0x24)
    put(cells, 60, CH_FX, 63, I_BELL, 0x20)
    # rising lead pickup in bar 4 (over G) -> launches the verse
    for i, n in enumerate([53, 56, 58, 60, 61, 63, 65, 68]):
        put(cells, 56+i, CH_LEAD, n, I_P25, 0x2c + (i % 2)*4)
    put(cells, 55, CH_LEAD, None, None, None, 0x0E, 0xC0)
    return cells

def verse(theme_variation=0, arp_oct=0, bell=False, busy=False):
    cells = {}
    bars = ['Am', 'F', 'C', 'G']
    # lead: theme A
    A = [(0,'E-5',2),(2,'A-5',2),(4,'C-6',2),(6,'B-5',2),(8,'A-5',4),(12,'E-6',2),(14,'D-6',2),
         (16,'C-6',2),(18,'A-5',2),(20,'F-5',2),(22,'A-5',2),(24,'C-6',4),(28,'D-6',2),(30,'C-6',2),
         (32,'E-6',4),(36,'D-6',2),(38,'C-6',2),(40,'G-5',2),(42,'E-5',2),(44,'G-5',2),(46,'C-6',2),
         (48,'D-6',4),(52,'B-5',2),(54,'G-5',2),(56,'D-6',2),(58,'B-5',2),(60,'G-5',1),(61,'A-5',1),(62,'B-5',1),(63,'C-6',1)]
    if theme_variation == 2:
        A = [(r, n, d) for (r, n, d) in A]
        A[-4:] = [(60,'G-5',1),(61,'A-5',1),(62,'B-5',1),(63,'D-6',1)]
    lead_phrase(cells, A)
    # arp figures vary
    figs = [['up','rock','oct','down'], ['down','oct','up','rock']][theme_variation % 2]
    for b, ch_name in enumerate(bars):
        r0 = b*16
        arp_bar(cells, r0, ch_name, figs[b], vhi=0x2a, vlo=0x1e, octshift=arp_oct)
    if bell:
        for (r, c), v in list(cells.items()):
            if c == CH_LEAD and v[0] and note_to_num(v[0]) and r % 8 == 0:
                put(cells, r, CH_FX, note_to_num(v[0]), I_BELL, 0x14)
    for b, ch_name in enumerate(bars):
        r0 = b*16
        bass_bar(cells, r0, ch_name, ['drive','drive','gallop','drive'][b], vol=0x32)
        pad_bar(cells, r0, ch_name, vol=0x24)
        kind = 'busy' if (b == 3 or (busy and b >= 2)) else 'main'
        drums_bar(cells, r0, kind, fill=(b==3))
    return cells

def hook():
    cells = {}
    bars = ['F', 'G', 'Am', 'E7']
    B = [(0,'A-5',2),(2,'C-6',2),(4,'F-6',4),(8,'D-6',2),(10,'C-6',2),(12,'A-5',4),
         (16,'B-5',2),(18,'D-6',2),(20,'G-6',4),(24,'F-6',2),(26,'D-6',2),(28,'B-5',4),
         (32,'C-6',2),(34,'E-6',2),(36,'A-6',4),(40,'G-6',2),(42,'E-6',2),(44,'C-6',4),
         (48,'B-5',2),(50,'D-6',2),(52,'G#5',4),(56,'B-5',1),(57,'C-6',1),(58,'D-6',1),(59,'E-6',1),(60,'G#6',4)]
    lead_phrase(cells, B, vol=0x3a)
    figs = ['rock','oct','up','wide']
    for b, ch_name in enumerate(bars):
        r0 = b*16
        arp_bar(cells, r0, ch_name, figs[b], vhi=0x2c, vlo=0x20)
    for b, ch_name in enumerate(bars):
        r0 = b*16
        bass_bar(cells, r0, ch_name, ['drive','gallop','drive','gallop'][b], vol=0x34)
        pad_bar(cells, r0, ch_name, vol=0x26)
        drums_bar(cells, r0, 'hook', fill=(b==3))
    # crash at start
    put(cells, 0, CH_FX, 49, I_CRASH, 0x30)
    return cells

def breakdown():
    cells = {}
    # terminate notes hanging from the previous section
    put(cells, 0, CH_LEAD, None, None, None, 0x0E, 0xC0)
    put(cells, 0, CH_BASS, None, None, None, 0x0E, 0xC0)
    bars = ['Am', 'F', 'C', 'G']
    for b, ch_name in enumerate(bars):
        r0 = b*16
        pad_progress(cells, r0, ch_name, 0x20, 0x30)
        if b < 2:
            arp_bar(cells, r0, ch_name, 'up' if b == 0 else 'rock', vhi=0x20, vlo=0x16)
        else:
            arp_bar(cells, r0, ch_name, 'wide' if b == 2 else 'oct', vhi=0x26, vlo=0x1a)
    # bell melody (sparse) using theme B fragments
    bell = [(0,'A-6',4),(8,'C-6',4),(16,'C-6',4),(24,'A-5',4),(32,'E-6',4),(40,'G-5',4),(48,'D-6',4),(56,'B-5',4)]
    for r, n, d in bell:
        put(cells, r, CH_FX, n, I_BELL, 0x2c)
    # second half: build-up
    put(cells, 32, CH_FX, 49, I_CRASH, 0x24)
    for i, r in enumerate(range(32, 64, 4)):
        put(cells, r, CH_KICK, 49, I_KICK, 0x1e + i*4)
    for i, r in enumerate(range(32, 64, 2)):
        put(cells, r, CH_SNARE, 49, I_SNARE, 0x10 + i*2)
    for i in range(16):
        put(cells, 48+i, CH_HAT, 49, I_HATC, 0x24 if i % 4 == 0 else 0x16)
    bass_bar(cells, 32, 'C', 'half', vol=0x2c)
    bass_bar(cells, 48, 'G', 'half', vol=0x2c)
    return cells

def hook2():
    cells = hook()
    for (r, c), v in list(cells.items()):
        if c == CH_LEAD and v[1] == I_P25:
            v[1] = I_P50
    for (r, c), v in list(cells.items()):
        if c == CH_LEAD and v[0] and v[0] not in (0, 97):
            put(cells, r, CH_FX, note_to_num(v[0]), I_BELL, 0x18)
    return cells

def bridge():
    """circle-of-fifths walk: Dm | G | C | F  (leads into the hook)"""
    cells = {}
    bars = ['Dm', 'G', 'C', 'F']
    lead = [(0,'A-5',2),(2,'D-6',4),(6,'F-6',2),(8,'E-6',4),(12,'D-6',4),
            (16,'D-6',2),(18,'G-6',4),(22,'F-6',2),(24,'D-6',4),(28,'B-5',4),
            (32,'C-6',2),(34,'E-6',4),(38,'G-6',2),(40,'E-6',4),(44,'C-6',4),
            (48,'F-6',4),(52,'E-6',2),(54,'C-6',2),(56,'A-5',2),(58,'C-6',2),(60,'F-6',4)]
    lead_phrase(cells, lead, vol=0x38)
    figs = ['up', 'rock', 'oct', 'down']
    for b, ch_name in enumerate(bars):
        r0 = b*16
        arp_bar(cells, r0, ch_name, figs[b], vhi=0x2a, vlo=0x1e)
    for b, ch_name in enumerate(bars):
        r0 = b*16
        kind = 'drive' if b < 2 else ('gallop' if b == 2 else 'walk')
        bass_bar(cells, r0, ch_name, kind, vol=0x32)
        pad_bar(cells, r0, ch_name, vol=0x24)
        drums_bar(cells, r0, 'main' if b < 3 else 'busy', fill=(b == 3))
    # bell accents on downbeats
    for r, n in ((0, 74), (16, 79), (32, 84), (48, 77)):
        put(cells, r, CH_FX, n, I_BELL, 0x1a)
    return cells

def verse3():
    cells = verse(0)
    for (r, c), v in list(cells.items()):
        if c == CH_LEAD and v[1] == I_P25:
            v[1] = I_P12
    # remove arpeggios, replace with off-beat chord stabs
    for k in [k for k in cells if k[1] == CH_ARP]:
        del cells[k]
    put(cells, 0, CH_ARP, None, None, None, 0x0E, 0xC0)   # stop the hanging 16th
    bars = ['Am', 'F', 'C', 'G']
    for b, ch_name in enumerate(bars):
        r0 = b*16
        tri = CHORDS[ch_name]['triad']
        fig = [0, 1, 2, 1, 2, 0, 1, 2]
        for i, off in enumerate([2, 6, 10, 14]):
            n = tri[fig[(b*4+i) % len(fig)] % len(tri)]
            put(cells, r0+off, CH_ARP, n, I_P50, 0x22)
            put(cells, r0+off+2, CH_ARP, None, None, 0x0e)
    # bell doubling on long lead notes
    for (r, c), v in list(cells.items()):
        if c == CH_LEAD and v[0] and v[0] not in (0, 97) and r % 8 == 0:
            put(cells, r, CH_FX, note_to_num(v[0]), I_BELL, 0x16)
    # 16th lead run in the last bar (G chord)
    for i, n in enumerate([68, 70, 72, 75, 77, 79, 80, 82]):
        put(cells, 56+i, CH_LEAD, n, I_P25, 0x34)
    put(cells, 0, CH_FX, 49, I_CRASH, 0x2c)
    return cells

def outro():
    cells = {}
    bars = ['Am', 'Am', 'G', 'E7']
    for b, ch_name in enumerate(bars):
        r0 = b*16
        pad_bar(cells, r0, ch_name, vol=0x2c)
        arp_bar(cells, r0, ch_name, 'up' if b % 2 == 0 else 'down', vhi=0x28, vlo=0x1e)
        bass_bar(cells, r0, ch_name, 'half' if b < 2 else 'drive', vol=0x30)
        drums_bar(cells, r0, 'main' if b < 3 else 'thin', hats=('8th', 0x2c, 0x1c))
    # bell accents
    put(cells, 0, CH_FX, 69, I_BELL, 0x24)
    put(cells, 8, CH_FX, 65, I_BELL, 0x20)
    put(cells, 32, CH_FX, 68, I_BELL, 0x22)
    put(cells, 48, CH_FX, 57, I_BELL, 0x22)
    # closing lead run over E7  (E-5 G#5 B-5 E-6)
    for i, (r, n) in enumerate([(52, 53), (54, 57), (56, 60), (58, 64)]):
        put(cells, r, CH_LEAD, n, I_P25, 0x34)
    # snare fill into the loop
    for i, r in enumerate((60, 62, 63)):
        put(cells, r, CH_SNARE, 49, I_SNARE, 0x20 + i*8)
    put(cells, 63, CH_BASS, None, None, None, 0x0E, 0xC0)   # stop bass before the loop
    put(cells, 63, CH_LEAD, None, None, None, 0x0E, 0xC0)   # stop lead before the loop
    return cells

PANS = {CH_LEAD: 0x80, CH_ARP: 0x68, CH_BASS: 0x80, CH_PAD: 0x98,
        CH_KICK: 0x80, CH_SNARE: 0x88, CH_HAT: 0x78, CH_FX: 0x78}

def apply_pan(cells):
    for ch, pan in PANS.items():
        rows = sorted(r for (r, c) in cells if c == ch)
        for r in rows:
            v = cells[(r, ch)]
            if v[3] is None:                 # free effect slot
                v[3], v[4] = 0x08, pan
                break
    return cells

MASTER = 0.42     # global level scale
CH_GAIN = [1.15, 1.10, 1.10, 0.90, 1.00, 0.95, 0.95, 0.90]   # per-channel trim

def scale_cells(pats, master):
    for p in pats:
        for k, v in list(p.items()):
            if v[2] is not None:
                vol = v[2] - 0x10
                vol = int(round(vol * master * CH_GAIN[k[1]]))
                v[2] = 0x10 + max(0, min(64, vol))
    return pats

def polish(pats):
    """panning + extra cymbal accents at section starts"""
    for p in pats:
        apply_pan(p)
    for idx in (1, 2, 3, 6):          # verse1, verse2, bridge, hook2
        if idx < len(pats):
            put(pats[idx], 0, CH_FX, 49, I_CRASH, 0x26)
    return pats


def build(S_scale=None):
    S = build_samples()
    master = MASTER if S_scale is None else S_scale
    for k in S:
        S[k]['volume'] = max(1, min(64, int(round(S[k]['volume']*0.85))))
    names = ['P25','P12','P50','BASS','PAD','BELL','KICK','SNARE','HATC','HATO','CRASH']
    b = XMBuilder(name='keygen', channels=8, bpm=150, speed=6, layout='dual')
    for n in names:
        b.add_instrument(n, [S[n]])
    pats = [pat_intro(), verse(0), verse(2, bell=True, busy=True), bridge(), hook(), breakdown(), hook2(), verse3(), outro()]
    polish(pats)
    pats = scale_cells(pats, master)
    for p in pats:
        b.add_pattern({k: tuple(v) for k, v in p.items()}, rows=64)
    b.orders = list(range(len(pats)))
    b.restart = 0
    return b

if __name__ == '__main__':
    import sys as _s
    master = float(_s.argv[1]) if len(_s.argv) > 1 else None
    out = _s.argv[2] if len(_s.argv) > 2 else '/workspace/work/tune_draft.xm'
    b = build(master)
    n = b.save(out)
    print('saved', n, 'bytes, master', master)
