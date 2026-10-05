#!/usr/bin/env python3
"""MIDNIGHT KEYGEN - original tracker tune composer for FT2-clone.
Emits a JSON batch of pattern_set_cell calls + order/song settings."""
import json

# ---------- note helpers ----------
SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(name):
    # 'C-4' / 'C#4' -> XM note number
    letter = name[:-1].replace('-','').upper()
    octv = int(name[-1])
    return octv*12 + 1 + SEMI[letter]

# instrument table
KICK, SNARE, HATC, HATO, CLAP, CRASH = 1,2,3,4,5,6
BASS, PLUCK, PADM, PADM2, LEAD, BLIP = 7,8,9,10,11,12

# channel table
CH_KICK, CH_SNARE, CH_HATC, CH_HATO, CH_BASS = 0,1,2,3,4
CH_ARP, CH_ARP2, CH_PAD, CH_LEAD, CH_ECHO = 5,6,7,8,9

cells = []
def ev(pat, ch, row, note=None, inst=None, vol=None, eff=None, ep=None):
    args = {"pattern":pat,"row":row,"channel":ch}
    if note is not None: args["note"] = note
    if inst is not None: args["instrument"] = inst
    if vol is not None: args["volume"] = vol
    if eff is not None: args["effect"] = eff
    if ep is not None: args["effect_param"] = ep
    cells.append({"name":"pattern_set_cell","arguments":args})

# ---------- chord table ----------
# chord: (root_xm, arp_base_semitone_offsets, pad_inst, bass_oct)
CHORDS = {
 'Em': dict(root=N('E-2'), arp=[0,3,7,12,15,12,7,3], pad=PADM,  padroot=N('E-2')),
 'C':  dict(root=N('C-2'), arp=[0,4,7,12,16,12,7,4], pad=PADM2, padroot=N('C-2')),
 'G':  dict(root=N('G-2'), arp=[0,4,7,12,14,12,7,4], pad=PADM2, padroot=N('G-2')),
 'D':  dict(root=N('D-2'), arp=[0,4,7,12,14,12,7,4], pad=PADM2, padroot=N('D-2')),
 'B':  dict(root=N('B-2'), arp=[0,4,7,12,16,12,7,4], pad=PADM2, padroot=N('B-2')),
 'Am': dict(root=N('A-2'), arp=[0,3,7,12,15,12,7,3], pad=PADM,  padroot=N('A-2')),
}

def arp_cycle(chord, base_oct=4, stride=1):
    """rows for a full bar of fast arp (32 rows / stride)"""
    offs = CHORDS[chord]['arp']
    root = CHORDS[chord]['root']
    root_arp = root + 24 + (base_oct-4)*12  # Em->E4 etc.
    seq = []
    for r in range(0, 32, stride):
        idx = (r//stride) % len(offs)
        seq.append((r, root_arp + offs[idx]))
    return seq

def bass_bar(pat, bar, chord, style='b8', vol=52):
    """bar = 0..1 within a 64-row pattern; 32 rows per bar"""
    base = bar*32
    r = CHORDS[chord]['root']
    if style == 'b8':
        for i in range(8):
            row = base + i*4
            note = r if i not in (3,7) else r+12
            ev(pat, CH_BASS, row, note, BASS, vol)
    elif style == 'b8up':
        for i in range(8):
            row = base + i*4
            note = r+12 if i in (2,3,6,7) else r
            ev(pat, CH_BASS, row, note, BASS, vol)
    elif style == 'brun':  # 8ths + 16th run in last beat
        for i in range(6):
            row = base + i*4
            note = r if i not in (3,) else r+12
            ev(pat, CH_BASS, row, note, BASS, vol)
        run = [r, r+2, r+4, r+7]
        for j, n in enumerate(run):
            ev(pat, CH_BASS, base+24+j*2, n, BASS, vol)
    elif style == 'bhalf':
        ev(pat, CH_BASS, base+0, r, BASS, vol)
        ev(pat, CH_BASS, base+16, r+12, BASS, vol)
    elif style == 'bq':
        for i in range(4):
            ev(pat, CH_BASS, base+i*8, r, BASS, vol)
    elif style == 'rest':
        ev(pat, CH_BASS, base, None, BASS, 16)

def drum_bar(pat, bar, style, extra=None):
    base = bar*32
    if style == 'intro':      # kick 4-on-floor + closed hats 8ths
        for i in range(4): ev(pat, CH_KICK, base+i*8, 'C-4', KICK, 64)
        for i in range(8): ev(pat, CH_HATC, base+i*4, 'C-6', HATC, 36)
    elif style == 'build':    # + snare on 2&4, open hat offbeats
        for i in range(4): ev(pat, CH_KICK, base+i*8, 'C-4', KICK, 64)
        ev(pat, CH_SNARE, base+8, 'C-5', SNARE, 56)
        ev(pat, CH_SNARE, base+24, 'C-5', SNARE, 56)
        for i in range(8): ev(pat, CH_HATC, base+i*4, 'C-6', HATC, 36)
        for i in (1,3,5,7): ev(pat, CH_HATO, base+i*4, 'C-6', HATO, 34)
    elif style == 'full':     # standard groove
        for i in range(4): ev(pat, CH_KICK, base+i*8, 'C-4', KICK, 64)
        ev(pat, CH_SNARE, base+8, 'C-5', SNARE, 56)
        ev(pat, CH_SNARE, base+24, 'C-5', SNARE, 56)
        for i in range(8): ev(pat, CH_HATC, base+i*4, 'C-6', HATC, 36)
        for i in (1,3,5,7): ev(pat, CH_HATO, base+i*4, 'C-6', HATO, 32)
    elif style == 'drive':    # 16th hats
        for i in range(4): ev(pat, CH_KICK, base+i*8, 'C-4', KICK, 64)
        ev(pat, CH_SNARE, base+8, 'C-5', SNARE, 56)
        ev(pat, CH_SNARE, base+24, 'C-5', SNARE, 56)
        for i in range(16): ev(pat, CH_HATC, base+i*2, 'C-6', HATC, 32)
        for i in (2,6,10,14): ev(pat, CH_HATO, base+i*2, 'C-6', HATO, 30)
    elif style == 'half':     # half-time feel
        ev(pat, CH_KICK, base+0, 'C-4', KICK, 60)
        ev(pat, CH_KICK, base+16, 'C-4', KICK, 60)
        ev(pat, CH_SNARE, base+8, 'C-5', SNARE, 52)
        ev(pat, CH_SNARE, base+24, 'C-5', SNARE, 52)
        for i in range(8): ev(pat, CH_HATC, base+i*4, 'C-6', HATC, 34)
    elif style == 'roll':     # snare roll build
        ev(pat, CH_KICK, base+0, 'C-4', KICK, 60)
        ev(pat, CH_KICK, base+8, 'C-4', KICK, 56)
        ev(pat, CH_KICK, base+16, 'C-4', KICK, 60)
        ev(pat, CH_KICK, base+24, 'C-4', KICK, 64)
        for i in range(16):
            v = 28 + (i % 8) * 4
            ev(pat, CH_SNARE, base+i*2, 'C-5', SNARE, min(56, v))
    elif style == 'fill':     # drum fill into next pattern
        for i in range(4): ev(pat, CH_KICK, base+i*8, 'C-4', KICK, 64)
        for i in range(16):
            v = 30 + (i % 8) * 4
            ev(pat, CH_SNARE, base+i*2, 'C-5', SNARE, min(56, v))
        for i in range(8): ev(pat, CH_HATC, base+i*4, 'C-6', HATC, 34)
    elif style == 'rest':
        pass
    if extra == 'crash':
        ev(pat, CH_HATO, base+0, 'C-5', CRASH, 32)

def arp_bar(pat, bar, chord, vol=40, base_oct=4, stride=1, ch=CH_ARP, detune=None):
    for r, note in arp_cycle(chord, base_oct, stride):
        if detune is not None:
            ev(pat, ch, bar*32+r, note, PLUCK, vol, 1 if detune>0 else 2, abs(detune))
        else:
            ev(pat, ch, bar*32+r, note, PLUCK, vol)

def arp_hold(pat, bar, chord, vol=40, ch=CH_ARP, every=8):
    """slow chord-tone pulses"""
    offs = CHORDS[chord]['arp']
    root = CHORDS[chord]['root'] + 24
    for i in range(0, 32, every):
        off = offs[(i//every) % len(offs)]
        ev(pat, ch, bar*32+i, root+off, PLUCK, vol)

def pad_bar(pat, bar, chord, vol=38):
    chd = CHORDS[chord]
    ev(pat, CH_PAD, bar*32+0, chd['padroot'], chd['pad'], vol)

def stab_bar(pat, bar, chord, vol=34):
    """offbeat chord stabs on arp2 channel"""
    base = bar*32
    offs = CHORDS[chord]['arp']
    root = CHORDS[chord]['root'] + 24
    for i in (2,6,10,14,18,22,26,30):
        off = offs[(i//2) % len(offs)]
        ev(pat, CH_ARP2, base+i, root+off, PLUCK, vol)

# ---------- melody helpers ----------
def lead(pat, bar, events, vol=48, ch=CH_LEAD):
    for (r, note, ln) in events:
        ev(pat, ch, bar*32+r, note, LEAD, vol)

def echo(pat, bar, events, vol=24, delay=2):
    for (r, note, ln) in events:
        row = bar*32+r+delay
        if row > 63: continue
        ev(pat, CH_ECHO, row, note, LEAD, vol)

# ================= MELODIES =================
RIFF_EM = [(0,'E-4',2),(2,'G-4',2),(4,'B-4',4),(8,'A-4',2),(10,'G-4',2),
           (12,'E-4',2),(14,'D-4',2),(16,'E-4',2),(18,'G-4',2),(20,'A-4',4),
           (24,'B-4',4),(28,'D-5',2),(30,'B-4',2)]
RIFF_C  = [(0,'E-5',4),(4,'D-5',2),(6,'C-5',2),(8,'G-4',4),(12,'E-4',2),(14,'G-4',2),
           (16,'C-5',4),(20,'D-5',2),(22,'E-5',2),(24,'D-5',4),(28,'C-5',2),(30,'G-4',2)]
RIFF_G  = [(0,'D-4',2),(2,'G-4',2),(4,'B-4',4),(8,'D-5',2),(10,'B-4',2),
           (12,'G-4',2),(14,'A-4',2),(16,'B-4',4),(20,'A-4',2),(22,'G-4',2),
           (24,'F#4',4),(28,'D-4',2),(30,'E-4',2)]
RIFF_D  = [(0,'F#4',2),(2,'A-4',2),(4,'D-5',4),(8,'A-4',2),(10,'F#4',2),
           (12,'E-4',2),(14,'F#4',2),(16,'A-4',4),(20,'D-5',2),(22,'C#5',2),
           (24,'A-4',4),(28,'F#4',2),(30,'E-4',2)]
RIFF_B  = [(0,'B-4',4),(4,'D#5',4),(8,'F#5',4),(12,'D#5',2),(14,'B-4',2),
           (16,'F#4',4),(20,'B-4',2),(22,'C#5',2),(24,'D#5',4),(28,'F#5',2),(30,'D#5',2)]

VERSE_C  = [(0,'G-4',8),(8,'E-4',4),(12,'G-4',4),(16,'C-5',8),(24,'E-5',4),(28,'D-5',4)]
VERSE_D  = [(0,'F#4',8),(8,'A-4',4),(12,'D-5',4),(16,'A-4',8),(24,'F#4',4),(28,'E-4',4)]
VERSE_EM = [(0,'E-4',8),(8,'B-4',8),(16,'G-4',4),(20,'A-4',4),(24,'B-4',8)]
VERSE_EM2= [(0,'E-5',8),(8,'D-5',4),(12,'B-4',4),(16,'G-4',8),(24,'A-4',4),(28,'B-4',4)]
VERSE_B  = [(0,'F#4',8),(8,'B-4',8),(16,'D#5',4),(20,'C#5',4),(24,'B-4',4),(28,'F#4',4)]

CHORUS_C = [(0,'E-5',4),(4,'G-5',4),(8,'E-5',4),(12,'D-5',4),(16,'C-5',8),(24,'D-5',4),(28,'E-5',4)]
CHORUS_D = [(0,'F#5',4),(4,'A-5',4),(8,'F#5',4),(12,'D-5',4),(16,'A-4',8),(24,'B-4',4),(28,'C#5',4)]
CHORUS_EM= [(0,'B-4',4),(4,'E-5',4),(8,'G-5',8),(16,'E-5',4),(20,'D-5',4),(24,'B-4',4),(28,'A-4',4)]
CHORUS_G = [(0,'D-5',4),(4,'B-4',4),(8,'G-4',8),(16,'D-5',4),(20,'B-4',4),(24,'G-4',4),(28,'A-4',4)]
CHORUS_B = [(0,'F#5',8),(8,'D#5',8),(16,'B-4',4),(20,'C#5',4),(24,'D#5',4),(28,'F#5',4)]

TEASER   = [(0,'E-4',4),(4,'G-4',4),(8,'B-4',8),(16,'A-4',4),(20,'B-4',4),(24,'D-5',8)]
PICKUP   = [(0,'D-4',2),(2,'E-4',2),(4,'F#4',2),(6,'G-4',2),(8,'A-4',4),(12,'B-4',4),(16,'C-5',2),(18,'D-5',2),(20,'E-5',4),(24,'D-5',2),(26,'B-4',2),(28,'G-4',4)]

Riff = {'Em':RIFF_EM,'C':RIFF_C,'G':RIFF_G,'D':RIFF_D,'B':RIFF_B}
Verse = {'C':VERSE_C,'D':VERSE_D,'Em':VERSE_EM,'Em2':VERSE_EM2,'B':VERSE_B}
Chorus = {'C':CHORUS_C,'D':CHORUS_D,'Em':CHORUS_EM,'G':CHORUS_G,'B':CHORUS_B}

# ================= SONG =================
# (pattern, [(chord bar0, chord bar1)], drum_style, extras)
SONG = [
 # bars 0-7 intro
 ('intro0', ['Em','Em'], ['intro','intro']),
 ('intro1', ['Em','Em'], ['intro','build']),
 ('intro2', ['Em','C'],  ['build','build']),
 ('intro3', ['D','D'],   ['build','fill']),
 # bars 8-15 main riff A
 ('mainA1', ['Em','C'],  ['full','full']),
 ('mainA2', ['G','D'],   ['full','full']),
 ('mainB1', ['Em','C'],  ['drive','drive']),
 ('mainB2', ['D','B'],   ['drive','fill']),
 # bars 16-23 verse
 ('verse1', ['C','D'],   ['full','full']),
 ('verse2', ['Em','Em'], ['full','full']),
 ('verse3', ['C','D'],   ['drive','drive']),
 ('verse4', ['B','B'],   ['drive','fill']),
 # bars 24-31 chorus
 ('chor1', ['C','D'],    ['drive','drive']),
 ('chor2', ['Em','Em'],  ['drive','drive']),
 ('chor3', ['C','D'],    ['drive','drive']),
 ('chor4', ['G','B'],    ['drive','fill']),
 # bars 32-35 break+build
 ('break', ['Em','Em'],  ['half','half']),
 ('build', ['C','D'],    ['roll','roll']),
 # bars 36-43 main reprise
 ('mainA1r',['Em','C'],  ['full','full']),
 ('mainA2r',['G','D'],   ['full','full']),
 ('mainB1r',['Em','C'],  ['drive','drive']),
 ('mainB2r',['D','B'],   ['drive','fill']),
 # bars 44-51 chorus reprise
 ('chor1r', ['C','D'],   ['drive','drive']),
 ('chor2r', ['Em','Em'], ['drive','drive']),
 ('chor3r', ['C','D'],   ['drive','drive']),
 ('chor4r', ['G','B'],   ['drive','fill']),
 # bars 52-55 outro
 ('outro1', ['Em','C'],  ['full','full']),
 ('outro2', ['D','B'],   ['build','fill']),
]

def build_patterns():
    for pidx, (sec, chords, drums) in enumerate(SONG):
        for bar in (0,1):
            ch = chords[bar]; dr = drums[bar]
            # drums
            drum_bar(pidx, bar, dr)
            # bass
            if sec in ('intro0','break'):
                bass_bar(pidx, bar, ch, 'bhalf', 48)
            elif sec == 'intro1':
                bass_bar(pidx, bar, ch, 'bq', 50)
            elif sec in ('intro2','intro3'):
                bass_bar(pidx, bar, ch, 'b8', 52)
            elif sec in ('build',):
                bass_bar(pidx, bar, ch, 'b8up', 52)
            elif sec in ('outro2',):
                bass_bar(pidx, bar, ch, 'brun', 50)
            elif bar == 1 and dr == 'fill':
                bass_bar(pidx, bar, ch, 'brun', 52)
            else:
                bass_bar(pidx, bar, ch, 'b8', 52)
            # arp
            if sec in ('intro0','break'):
                arp_hold(pidx, bar, ch, vol=34, every=8)
                stab_bar(pidx, bar, ch, vol=28)
            elif sec in ('intro1','intro2','intro3'):
                arp_bar(pidx, bar, ch, vol=34, stride=2)
            elif sec in ('outro1','outro2'):
                arp_bar(pidx, bar, ch, vol=32, stride=2)
                stab_bar(pidx, bar, ch, vol=26)
            elif sec.startswith('chor') or sec.startswith('build'):
                arp_bar(pidx, bar, ch, vol=36, stride=1)
                arp_bar(pidx, bar, ch, vol=28, base_oct=5, stride=1, ch=CH_ARP2, detune=2)
            else:
                arp_bar(pidx, bar, ch, vol=40, stride=1)
                arp_bar(pidx, bar, ch, vol=28, base_oct=5, stride=1, ch=CH_ARP2, detune=2)
            # pad
            if sec in ('intro0','break','chor1','chor2','chor3','chor4','chor1r','chor2r','chor3r','chor4r','outro1'):
                pad_bar(pidx, bar, ch, vol=38)
            elif sec in ('intro2','intro3'):
                pad_bar(pidx, bar, ch, vol=32)
            # stabs
            if sec in ('verse1','verse2','verse3','verse4') and bar==1:
                stab_bar(pidx, bar, ch, vol=30)
            # leads
            leads = None
            if sec == 'intro1':
                leads = [(0,TEASER,40)]
            elif sec == 'intro3':
                leads = [(1,PICKUP,44)]
            elif sec in ('mainA1','mainA2','mainA1r','mainA2r'):
                leads = [(0,Riff[chords[0]],46),(1,Riff[chords[1]],46)]
            elif sec in ('mainB1','mainB2','mainB1r','mainB2r'):
                leads = [(0,Riff[chords[0]],48),(1,Riff[chords[1]],48)]
            elif sec in ('verse1','verse3'):
                leads = [(0,Verse[chords[0]],44),(1,Verse[chords[1]],44)]
            elif sec == 'verse2':
                leads = [(0,Verse['Em'],44),(1,Verse['Em2'],44)]
            elif sec == 'verse4':
                leads = [(0,Verse[chords[0]],44),(1,Verse[chords[1]],44)]
            elif sec in ('chor1','chor2','chor3','chor4','chor1r','chor2r','chor3r','chor4r'):
                leads = [(0,Chorus[chords[0]],50),(1,Chorus[chords[1]],50)]
            elif sec == 'outro1':
                leads = [(0,Riff[chords[0]],42),(1,Riff[chords[1]],42)]
            elif sec == 'outro2':
                leads = [(1,RIFF_B,44)]
            if leads:
                for (b, events, vol) in leads:
                    lead(pidx, b, events, vol)
                    echo(pidx, b, events, min(24, vol-24), delay=2)
        # claps layered on snare in chorus/drive sections
        if sec.startswith('chor') or sec in ('mainB1','mainB2','mainB1r','mainB2r','verse3','verse4'):
            for bar in (0,1):
                base = bar*32
                ev(pidx, CH_HATO, base+8, 'C-5', CLAP, 34)
                ev(pidx, CH_HATO, base+24, 'C-5', CLAP, 34)
        # crash on section starts
        if sec in ('mainA1','verse1','chor1','mainA1r','chor1r'):
            ev(pidx, CH_HATO, 0, 'C-5', CRASH, 30)
        if sec == 'break':
            ev(pidx, CH_HATO, 0, 'C-5', CRASH, 26)
    # final pickup into the loop (last 16th of the song = E4 lead pickup)
    ev(27, CH_LEAD, 62, 'E-4', LEAD, 40)
    ev(27, CH_BASS, 60, N('E-2'), BASS, 50)
    # ---- sustained-loop cuts (lead/echo are looped samples) ----
    # end of TEASER (P1 bar 0) before the quiet bar
    ev(1, CH_LEAD, 32, None, LEAD, 16)
    ev(1, CH_ECHO, 32, None, LEAD, 16)
    # chorus -> break
    ev(16, CH_LEAD, 0, None, LEAD, 16)
    ev(16, CH_ECHO, 0, None, LEAD, 16)
    # loop restart: cut the outro pickup
    ev(0, CH_LEAD, 0, None, LEAD, 16)
    ev(0, CH_ECHO, 0, None, LEAD, 16)

build_patterns()
print('cells:', len(cells))
json.dump(cells, open('/workspace/work/pattern_batch.json','w'))
