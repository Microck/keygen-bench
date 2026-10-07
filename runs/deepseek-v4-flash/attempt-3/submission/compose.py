"""Compose a keygen tune: build events, write XM, render preview."""
import numpy as np, sys
sys.path.insert(0, '/workspace')
from xmwrite import build_xm
from samples import build_instruments

SEMI = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
        'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def N(name):
    name = name.replace('-', '')
    return 1 + int(name[-1]) * 12 + SEMI[name[:-1]]

# channels
CH_LEAD, CH_ECHO, CH_ARP, CH_BASS, CH_KICK, CH_SNARE, CH_HAT, CH_PAD = range(8)
INST_LEAD, INST_ECHO, INST_ARP, INST_BASS, INST_KICK, INST_SNARE, INST_HAT, INST_OHAT, INST_CRASH, INST_PAD = 1,2,3,4,6,7,8,9,10,5

CHORDS = {
    'Am': dict(bass='A2', arp='A4', pad='A3', arpfx=0x37),
    'F':  dict(bass='F2', arp='F4', pad='F3', arpfx=0x47),
    'C':  dict(bass='C3', arp='C5', pad='C4', arpfx=0x47),
    'G':  dict(bass='G2', arp='G4', pad='G3', arpfx=0x47),
    'E':  dict(bass='E2', arp='E4', pad='E3', arpfx=0x47),
}

def add(ev, row, ch, note=0, inst=0, vol=0, fx=0, fxp=0):
    ev.append((row, ch, note, inst, vol, fx, fxp))

def drums(ev, bar, style='full', crash=False, roll=False):
    b = bar * 16
    if style in ('light', 'half', 'full'):
        for r in (0, 8):
            add(ev, b + r, CH_KICK, N('C-4'), INST_KICK, 0x2E)
    if style in ('full',):
        for r in (4, 12):
            add(ev, b + r, CH_KICK, N('C-4'), INST_KICK, 0x2A)
    if style in ('half', 'full'):
        for r in (4, 12):
            add(ev, b + r, CH_SNARE, N('C-4'), INST_SNARE, 0x2A)
    for r in range(0, 16, 2):
        vol = 0x20 if r % 8 == 0 else 0x14
        add(ev, b + r, CH_HAT, N('C-4'), INST_HAT, vol)
    if crash:
        add(ev, b, CH_HAT, N('C-4'), INST_CRASH, 0x26)
    if roll:
        for i, r in enumerate((24, 26, 28, 30)):
            add(ev, b + r, CH_SNARE, N('C-4'), INST_SNARE, 0x18 + i * 3)

def bass_bar(ev, bar, chord, style='drive'):
    b = bar * 16
    root = N(CHORDS[chord]['bass'])
    octv = root + 12
    fifth = root + 7
    if style == 'drive':
        seq = [root, root, octv, root, root, root, octv, fifth]
        for i, n in enumerate(seq):
            vol = 0x2A if i % 4 == 0 else 0x20
            add(ev, b + i * 2, CH_BASS, n, INST_BASS, vol)
    elif style == 'half':
        add(ev, b, CH_BASS, root, INST_BASS, 0x2C)
        add(ev, b + 8, CH_BASS, octv, INST_BASS, 0x28)
    elif style == 'pulse':
        # 16th pulse on root for energy (chorus)
        for r in range(0, 16, 2):
            n = root if r % 4 == 0 else octv
            vol = 0x2C if r % 4 == 0 else 0x22
            add(ev, b + r, CH_BASS, n, INST_BASS, vol)

def arp_bar(ev, bar, chord, style='full'):
    b = bar * 16
    base = N(CHORDS[chord]['arp'])
    arpfx = CHORDS[chord]['arpfx']
    if style == 'full':
        rows = range(0, 16)
    elif style == 'sparse':
        rows = range(0, 16, 4)
    elif style == 'half':
        rows = range(0, 16, 2)
    for r in rows:
        n = base + (12 if r >= 8 else 0)
        vol = 0x24 if r % 4 == 0 else 0x1C
        add(ev, b + r, CH_ARP, n, INST_ARP, vol, fx=0, fxp=arpfx)

def pad_bar(ev, bar, chord, double=False):
    b = bar * 16
    root = N(CHORDS[chord]['pad'])
    add(ev, b, CH_PAD, root, INST_PAD, 0x22)
    if double:
        add(ev, b + 16, CH_PAD, root + 12, INST_PAD, 0x20)

def keyoff(ev, row, ch):
    add(ev, row, ch, 97)

def lead_events(ev, bar, melody, echo=True, echo_vol=6):
    """melody: list of (row_in_bar, note_name, vol) — no keyoffs; notes auto-cut."""
    b = bar * 16
    for (r, nm, vol) in melody:
        note = N(nm)
        add(ev, b + r, CH_LEAD, note, INST_LEAD, vol, fx=4, fxp=0x44)
        # cut 2 rows later (8th rest) unless next note comes sooner
        add(ev, b + r + 2, CH_LEAD, 97)
        if echo:
            add(ev, b + r + 2, CH_ECHO, note, INST_ECHO, max(0x12, vol - echo_vol), fx=4, fxp=0x34)
            add(ev, b + r + 4, CH_ECHO, 97)
    # remove duplicate keyoffs (keep last per row)
    return ev

def dedupe(ev):
    d = {}
    for (row, ch, note, inst, vol, fx, fxp) in ev:
        key = (row, ch)
        if key in d and d[key][2] == 97 and note == 97:
            continue
        d[key] = (row, ch, note, inst, vol, fx, fxp)
    return list(d.values())

# ---------------- melodies ----------------
M_INTRO_C = [(0,'G5',0x28),(4,'E5',0x22),(8,'C5',0x26),(12,'D5',0x20)]
M_INTRO_G = [(0,'B5',0x28),(4,'G5',0x22),(8,'D5',0x26),(12,'E5',0x20)]
M_VERSE_AM = [(0,'A5',0x2C),(2,'G5',0x24),(4,'E5',0x28),(6,'D5',0x22),
              (8,'C5',0x2A),(10,'B4',0x22),(12,'A4',0x28),(14,'C5',0x22)]
M_VERSE_F  = [(0,'F5',0x2C),(2,'E5',0x24),(4,'D5',0x28),(6,'C5',0x22),
              (8,'A4',0x2A),(10,'C5',0x22),(12,'D5',0x26),(14,'E5',0x24)]
M_VERSE_C  = [(0,'G5',0x2C),(2,'E5',0x26),(4,'C5',0x28),(6,'E5',0x22),
              (8,'G5',0x2A),(10,'A5',0x24),(12,'G5',0x28),(14,'E5',0x22)]
M_VERSE_G  = [(0,'D5',0x2C),(2,'E5',0x24),(4,'G5',0x28),(6,'B4',0x22),
              (8,'D5',0x2A),(10,'G5',0x24),(12,'A5',0x28),(14,'G5',0x22)]
M_CHORUS_AM = [(0,'A5',0x2C),(1,'C6',0x26),(2,'B5',0x24),(3,'A5',0x22),
               (4,'G5',0x28),(5,'E5',0x22),(6,'D5',0x24),(7,'C5',0x22),
               (8,'E5',0x2A),(10,'G5',0x24),(12,'A5',0x28),(14,'B5',0x22)]
M_CHORUS_F  = [(0,'C6',0x2C),(1,'B5',0x26),(2,'A5',0x24),(3,'G5',0x22),
               (4,'F5',0x28),(5,'E5',0x22),(6,'D5',0x24),(7,'C5',0x22),
               (8,'A5',0x2A),(10,'C6',0x24),(12,'B5',0x28),(14,'A5',0x22)]
M_CHORUS_C  = [(0,'C6',0x2C),(2,'G5',0x26),(4,'E5',0x28),(6,'C5',0x22),
               (8,'D5',0x2A),(10,'E5',0x24),(12,'G5',0x28),(14,'C6',0x22)]
M_CHORUS_G  = [(0,'B5',0x2C),(2,'A5',0x24),(4,'G5',0x28),(6,'E5',0x22),
               (8,'D5',0x2A),(10,'E5',0x24),(12,'G5',0x28),(14,'B5',0x22)]
M_BREAK_E = [(0,'E5',0x2A),(8,'G#5',0x24),(12,'B5',0x28)]
M_BREAK_AM = [(0,'A5',0x2A),(8,'C6',0x24),(12,'E6',0x28)]
M_FINAL_F = [(0,'C6',0x2C),(1,'B5',0x26),(2,'A5',0x24),(3,'G5',0x22),
             (4,'F5',0x28),(5,'E5',0x22),(6,'D5',0x24),(7,'C5',0x22),
             (8,'A5',0x2A),(10,'G5',0x24),(12,'E5',0x28),(14,'D5',0x22)]
M_OUTRO_C  = [(0,'C6',0x2C),(2,'G5',0x26),(4,'E5',0x28),(6,'C5',0x22),
              (8,'D5',0x2A),(10,'E5',0x24),(12,'G5',0x28),(14,'C6',0x22)]
M_OUTRO_G  = [(0,'B5',0x2C),(2,'A5',0x24),(4,'G5',0x28),(6,'D5',0x22),
              (8,'B4',0x2A),(10,'D5',0x24),(12,'E5',0x28),(14,'G5',0x22)]

def pattern(name, chords, opts):
    """Build a 32-row pattern from two bars.
    opts: lead lists per bar, drum style, crash, echo, arp style, bass style, pad double, release."""
    ev = []
    for i, ch in enumerate(chords):
        bar = i
        st = opts.get('drums', 'full')
        drums(ev, bar, style=st, crash=opts.get('crash', False) and i == 0,
              roll=opts.get('roll', False) and i == 1)
        bass_bar(ev, bar, ch, style=opts.get('bass', 'drive'))
        arp_bar(ev, bar, ch, style=opts.get('arp', 'full'))
        pad_bar(ev, bar, ch, double=opts.get('pad_double', False))
        if opts.get('leads'):
            lead_events(ev, bar, opts['leads'][i], echo=opts.get('echo', True))
    if opts.get('release'):
        for ch in (CH_LEAD, CH_ECHO, CH_ARP, CH_BASS, CH_PAD):
            keyoff(ev, 31, ch)
    return dedupe(ev)

patterns = {}
patterns[0] = pattern('intro', ['Am','F'], dict(drums='light', arp='sparse', bass='drive', leads=None))
patterns[1] = pattern('intro2', ['C','G'], dict(drums='full', arp='full', bass='drive',
                                                leads=[M_INTRO_C, M_INTRO_G]))
patterns[2] = pattern('verse', ['Am','F'], dict(drums='full', arp='full', bass='drive',
                                                leads=[M_VERSE_AM, M_VERSE_F], echo=True))
patterns[3] = pattern('verse2', ['C','G'], dict(drums='full', arp='full', bass='drive',
                                                leads=[M_VERSE_C, M_VERSE_G], echo=True, roll=True))
patterns[4] = pattern('chorus', ['Am','F'], dict(drums='full', arp='full', bass='pulse',
                                                 leads=[M_CHORUS_AM, M_CHORUS_F], crash=True, echo=True))
patterns[5] = pattern('chorus2', ['C','G'], dict(drums='full', arp='full', bass='pulse',
                                                 leads=[M_CHORUS_C, M_CHORUS_G], crash=True, echo=True))
patterns[6] = pattern('break', ['E','Am'], dict(drums='none', arp='half', bass='half',
                                                leads=[M_BREAK_E, M_BREAK_AM], echo=False,
                                                pad_double=True, roll=True))
patterns[7] = pattern('final', ['Am','F'], dict(drums='full', arp='full', bass='pulse',
                                                leads=[M_CHORUS_AM, M_FINAL_F], crash=True, echo=True))
patterns[8] = pattern('outro', ['C','G'], dict(drums='full', arp='full', bass='drive',
                                               leads=[M_OUTRO_C, M_OUTRO_G], echo=True, crash=True, release=True))

ORDER = [0,0,1,1,2,3,4,4,5,4,6,6,7,8,8]

def build_tune(path='/workspace/submission/tune.xm'):
    instruments = build_instruments()
    pats = [(32, patterns[i]) for i in range(9)]
    xm = build_xm(name='KEYGEN FORCE', channels=8,
                  patterns=pats, order=ORDER, instruments=instruments,
                  speed=6, bpm=150)
    open(path, 'wb').write(xm)
    return xm

if __name__ == '__main__':
    xm = build_tune()
    print('tune bytes', len(xm))
    # sanity parse
    from xmwrite import parse_xm
    m = parse_xm(xm)
    print('patterns', len(m['patterns']), 'order', m['order'], 'instruments', len(m['instruments']))
    print('events per pattern:', [len(p[1]) for p in m['patterns']])
