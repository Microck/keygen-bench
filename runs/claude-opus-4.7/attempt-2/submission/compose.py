"""Final keygen tune composition script.
Enterprise Keygen - a classic trance-flavored chiptune loop in A minor.
8 channels, 150 BPM, 10 orders, ~53 seconds per loop.
"""
import json

I_PULSE, I_SAW, I_SUB, I_PAD, I_PLUCK, I_BLIP, I_BELL = 1,2,3,4,5,6,7
I_KICK, I_SNARE, I_CHAT, I_OHAT, I_CRASH = 8,9,10,11,12

CH_LEAD, CH_LEAD2, CH_ARP, CH_PAD, CH_BASS, CH_KICK, CH_SNARE, CH_HAT = range(8)

CH_PAN = {
    CH_LEAD:   128, CH_LEAD2:  195, CH_ARP:    50,  CH_PAD:    155,
    CH_BASS:   128, CH_KICK:   128, CH_SNARE:  148, CH_HAT:    60,
}

NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def oct_up(n, k=1): return n[:2]+str(int(n[2])+k)

CHORDS = {
    'Am': ['A-3','C-4','E-4'], 'F':  ['F-3','A-3','C-4'],
    'C':  ['C-4','E-4','G-4'], 'G':  ['G-3','B-3','D-4'],
}
CHORD_ARP = {'Am': 0x37, 'F': 0x47, 'C': 0x47, 'G': 0x47}  # semitone pattern for 0xy effect
ROOT = {'Am':'A-','F':'F-','C':'C-','G':'G-'}
PROG = ['Am','F','C','G']

E_PAN, E_ARP, E_VSL = 8, 0, 10

cells = []
def put(p, r, ch, note=None, inst=None, vol=None, eff=None, par=None):
    args = {'pattern':p,'row':r,'channel':ch}
    if note is not None: args['note'] = note
    if inst is not None: args['instrument'] = inst
    if vol is not None: args['volume'] = vol
    if eff is None and note is not None and isinstance(note, str):
        args['effect'] = E_PAN; args['effect_param'] = CH_PAN[ch]
    elif eff is not None:
        args['effect'] = eff
        if par is not None: args['effect_param'] = par
    cells.append({'name':'pattern_set_cell','arguments':args})

# ---- Drums ----
def kick4(p, start=0, end=64, step=4, vol=62):
    for r in range(start, end, step):
        v = min(64, vol+2 if (r//16)%2==1 else vol)
        put(p, r, CH_KICK, 'C-5', I_KICK, v)

def snare_bb(p, vol=52, ghosts=False):
    for r in [4,12,20,28,36,44,52,60]:
        put(p, r, CH_SNARE, 'C-5', I_SNARE, vol)
    if ghosts:
        for r in [15,31,47,63]:
            put(p, r, CH_SNARE, 'C-5', I_SNARE, 22)

def hat8(p, vol=32, start=0, end=64):
    for r in range(start, end, 2):
        v = vol-6 if (r%4)==0 else vol
        put(p, r, CH_HAT, 'C-5', I_CHAT, v)

def hat16(p, vol=24, start=0, end=64):
    for r in range(start, end):
        v = vol+6 if (r%4)==0 else vol
        put(p, r, CH_HAT, 'C-5', I_CHAT, v)

def ohat_off(p, vol=32):
    for r in [6,14,22,30,38,46,54,62]:
        put(p, r, CH_HAT, 'C-5', I_OHAT, vol)

# ---- Bass ----
def bass_off8(p, prog=PROG, inst=I_SAW, vol=52, oct=2):
    for i, c in enumerate(prog):
        root = ROOT[c]+str(oct); base = i*16
        for r in [2,6,10,14]: put(p, base+r, CH_BASS, root, inst, vol)

def bass_drive(p, prog=PROG, inst=I_SAW, vol=52, oct=2):
    for i, c in enumerate(prog):
        root = ROOT[c]+str(oct); base = i*16
        for r in range(0,16,2):
            v = vol if (r%4)==0 else vol-4
            put(p, base+r, CH_BASS, root, inst, v)

def bass_16th(p, prog=PROG, inst=I_SAW, vol=50, oct=2):
    for i, c in enumerate(prog):
        root = ROOT[c]+str(oct); base = i*16
        for r in range(16):
            v = vol if (r%4)==0 else vol-10
            put(p, base+r, CH_BASS, root, inst, v)

def bass_rock(p, prog=PROG, inst=I_SAW, vol=56, oct=2):
    for i, c in enumerate(prog):
        root = ROOT[c]+str(oct); fifth_up = ROOT[c]+str(oct+1); base = i*16
        for r,n,v in [(0,root,64),(3,root,44),(4,root,50),(7,root,44),
                      (8,root,56),(10,root,44),(12,fifth_up,50),(14,root,48)]:
            put(p, base+r, CH_BASS, n, inst, v)

def sub_long(p, prog=PROG, inst=I_SUB, vol=46, oct=2):
    for i, c in enumerate(prog):
        put(p, i*16, CH_BASS, ROOT[c]+str(oct), inst, vol)

# ---- Pad ----
def pad(p, prog=PROG, inst=I_PAD, vol=26):
    for i, c in enumerate(prog):
        put(p, i*16, CH_PAD, CHORDS[c][1], inst, vol)

def pad_arp(p, prog=PROG, inst=I_PAD, vol=30):
    """Pad with chord arpeggio for breakdown density."""
    for i, c in enumerate(prog):
        base = i*16
        args = {'pattern':p,'row':base,'channel':CH_PAD,
                'note':CHORDS[c][0],'instrument':inst,'volume':vol,
                'effect':E_ARP,'effect_param':CHORD_ARP[c]}
        cells.append({'name':'pattern_set_cell','arguments':args})

# ---- Arps ----
def arp_updown(p, prog=PROG, inst=I_BLIP, vol=34):
    for i, c in enumerate(prog):
        base = i*16; notes = CHORDS[c]
        tones = [notes[0], notes[1], notes[2], oct_up(notes[0])]
        for j, idx in enumerate([0,1,2,3,2,1,0,1]):
            v = vol if j%2==0 else vol-6
            put(p, base+j*2, CH_ARP, oct_up(tones[idx]), inst, v)

def arp_fast(p, prog=PROG, inst=I_BLIP, vol=36):
    for i, c in enumerate(prog):
        base = i*16; notes = CHORDS[c]
        tones = [notes[0], notes[1], notes[2], oct_up(notes[0])]
        seq = [0,2,1,3, 2,0,1,2, 0,2,1,3, 2,3,2,1]
        for j in range(16):
            v = vol if j%4==0 else vol-8
            put(p, base+j, CH_ARP, oct_up(tones[seq[j]]), inst, v)

def arp_trance(p, prog=PROG, inst=I_BLIP, vol=34):
    for i, c in enumerate(prog):
        base = i*16; notes = CHORDS[c]; tones = [notes[0], notes[1], notes[2]]
        for j in range(16):
            n = tones[(j//2)%3]
            if j%2==1: n = oct_up(n)
            v = vol if j%2==0 else vol-6
            put(p, base+j, CH_ARP, oct_up(n), inst, v)

# ---- Chord stabs on CH_LEAD2 ----
def chord_stabs(p, prog=PROG, inst=I_PULSE, vol=32, rows=[2,6,10,14], scale_vol=False):
    """Chord stabs via 0xy arpeggio effect."""
    for i, c in enumerate(prog):
        base = i*16
        root = CHORDS[c][0]
        for j, r in enumerate(rows):
            v = vol
            if scale_vol:
                v = min(64, vol + i*2 + j//2)
            args = {'pattern':p,'row':base+r,'channel':CH_LEAD2,
                    'note':root,'instrument':inst,'volume':v,
                    'effect':E_ARP,'effect_param':CHORD_ARP[c]}
            cells.append({'name':'pattern_set_cell','arguments':args})

# ---- Leads ----
def lead_hook(p, prog=PROG, inst=I_PULSE, ch=CH_LEAD):
    """Main hook melody."""
    melodies = {
        'Am': [(0,'E-5',62),(2,'E-5',52),(4,'A-5',58),(6,'G-5',52),
               (8,'E-5',58),(10,'C-5',52),(12,'D-5',54),(14,'E-5',58)],
        'F':  [(0,'F-5',62),(2,'F-5',52),(4,'A-5',58),(6,'G-5',52),
               (8,'F-5',58),(10,'C-6',52),(12,'A-5',54),(14,'F-5',58)],
        'C':  [(0,'G-5',62),(2,'G-5',52),(4,'C-6',58),(6,'B-5',52),
               (8,'G-5',58),(10,'E-6',52),(12,'C-6',54),(14,'E-5',58)],
        'G':  [(0,'D-5',62),(2,'D-5',52),(4,'G-5',58),(6,'F#5',52),
               (8,'D-5',58),(10,'B-5',52),(12,'D-6',54),(14,'G-5',58)],
    }
    for i, c in enumerate(prog):
        base = i*16
        for r,n,v in melodies[c]:
            put(p, base+r, ch, n, inst, v)

def lead_hook_up(p, prog=PROG, inst=I_PULSE, ch=CH_LEAD):
    """Hook up an octave for climax."""
    melodies = {
        'Am': [(0,'E-6',62),(2,'E-6',52),(4,'A-6',58),(6,'G-6',52),
               (8,'E-6',58),(10,'C-6',52),(12,'D-6',54),(14,'E-6',58)],
        'F':  [(0,'F-6',62),(2,'F-6',52),(4,'A-6',58),(6,'G-6',52),
               (8,'F-6',58),(10,'C-7',52),(12,'A-6',54),(14,'F-6',58)],
        'C':  [(0,'G-6',62),(2,'G-6',52),(4,'C-7',58),(6,'B-6',52),
               (8,'G-6',58),(10,'E-7',52),(12,'C-7',54),(14,'E-6',58)],
        'G':  [(0,'D-6',62),(2,'D-6',52),(4,'G-6',58),(6,'F#6',52),
               (8,'D-6',58),(10,'B-6',52),(12,'D-7',54),(14,'G-6',58)],
    }
    for i, c in enumerate(prog):
        base = i*16
        for r,n,v in melodies[c]:
            put(p, base+r, ch, n, inst, v)

def lead_variation(p, prog=PROG, inst=I_PULSE, ch=CH_LEAD):
    """Syncopated variation."""
    melodies = {
        'Am': [(0,'A-5',62),(3,'E-6',56),(5,'A-5',58),(7,'C-6',56),
               (9,'B-5',56),(11,'A-5',52),(13,'G-5',56),(15,'E-5',50)],
        'F':  [(0,'C-6',62),(3,'F-6',56),(5,'C-6',58),(7,'A-5',56),
               (9,'G-5',56),(11,'F-5',52),(13,'E-5',56),(15,'C-5',50)],
        'C':  [(0,'E-6',62),(3,'G-6',56),(5,'E-6',58),(7,'C-6',56),
               (9,'B-5',56),(11,'G-5',52),(13,'E-5',56),(15,'C-5',50)],
        'G':  [(0,'D-6',62),(3,'G-6',56),(5,'D-6',58),(7,'B-5',56),
               (9,'A-5',56),(11,'G-5',52),(13,'F#5',56),(15,'D-5',50)],
    }
    for i, c in enumerate(prog):
        base = i*16
        for r,n,v in melodies[c]:
            put(p, base+r, ch, n, inst, v)

def bell_sparkle(p, prog=PROG, inst=I_BELL, ch=CH_LEAD2):
    phrases = {
        'Am': [(0,'A-5',44)],
        'F':  [(0,'C-6',44)],
        'C':  [(0,'E-6',44)],
        'G':  [(0,'D-6',40),(8,'G-5',36)],
    }
    for i, c in enumerate(prog):
        base = i*16
        for r,n,v in phrases[c]:
            put(p, base+r, ch, n, inst, v)

def pluck_counter(p, prog=PROG, inst=I_PLUCK, ch=CH_LEAD2):
    phrases = {
        'Am': [(1,'A-4',38),(5,'C-5',38),(9,'A-4',38),(13,'E-5',38)],
        'F':  [(1,'F-4',38),(5,'A-4',38),(9,'C-5',38),(13,'A-4',38)],
        'C':  [(1,'C-5',38),(5,'E-5',38),(9,'G-4',38),(13,'C-5',38)],
        'G':  [(1,'G-4',38),(5,'B-4',38),(9,'D-5',38),(13,'G-4',38)],
    }
    for i, c in enumerate(prog):
        base = i*16
        for r,n,v in phrases[c]:
            put(p, base+r, ch, n, inst, v)

# ======== Patterns ========
def build_p0():
    """Intro - drums + sub bass + subtle arp."""
    p = 0
    kick4(p, vol=58); hat8(p, vol=24); sub_long(p, vol=46)
    arp_updown(p, vol=22)
    put(p, 0, CH_HAT, 'C-5', I_CRASH, 44)
    for r in [60,62]: put(p, r, CH_HAT, 'C-5', I_CHAT, 32)

def build_p1():
    """Verse - full groove + arp + bell hints."""
    p = 1
    kick4(p, vol=62); snare_bb(p, vol=46); hat8(p, vol=28); ohat_off(p, vol=26)
    bass_off8(p, inst=I_SAW, vol=48); sub_long(p, inst=I_SUB, vol=42)
    pad(p, vol=22); arp_updown(p, vol=34)
    put(p, 0, CH_LEAD2, 'A-5', I_BELL, 36)
    put(p, 48, CH_LEAD2, 'D-6', I_BELL, 32)

def build_p2():
    """Chorus 1 - main hook."""
    p = 2
    kick4(p, vol=64); snare_bb(p, vol=52); hat8(p, vol=32); ohat_off(p, vol=30)
    bass_drive(p, inst=I_SAW, vol=52); sub_long(p, inst=I_SUB, vol=38)
    pad(p, vol=22); arp_updown(p, vol=30)
    lead_hook(p)
    put(p, 0, CH_HAT, 'C-5', I_CRASH, 42)
    for r,n in [(15,'A-5'),(31,'C-6'),(47,'E-6'),(63,'D-6')]:
        put(p, r, CH_LEAD2, n, I_PLUCK, 40)

def build_p3():
    """Chorus 2 - fast arp + syncopated lead + chord stabs."""
    p = 3
    kick4(p, vol=64); snare_bb(p, vol=52, ghosts=True)
    hat16(p, vol=22); ohat_off(p, vol=28)
    bass_rock(p, inst=I_SAW, vol=54); sub_long(p, inst=I_SUB, vol=36)
    pad(p, vol=20); arp_fast(p, vol=32)
    lead_variation(p)
    bell_sparkle(p)
    chord_stabs(p, vol=32)

def build_p4():
    """Breakdown - atmospheric pad arp + bell melody."""
    p = 4
    for r in [0, 32]:
        put(p, r, CH_KICK, 'C-5', I_KICK, 44)
    for r in [4,12,20,28,36,44,52,60]:
        put(p, r, CH_HAT, 'C-5', I_CHAT, 24)
    sub_long(p, inst=I_SUB, vol=42)
    pad_arp(p, vol=30)
    bell_phrases = {
        'Am': [(0,'A-5',48),(4,'C-6',42),(8,'E-6',42),(12,'A-5',38)],
        'F':  [(0,'C-6',48),(4,'A-5',42),(8,'F-5',42),(12,'C-6',38)],
        'C':  [(0,'G-5',48),(4,'E-6',42),(8,'G-6',42),(12,'E-6',38)],
        'G':  [(0,'D-6',48),(4,'B-5',42),(8,'G-5',42),(12,'D-6',38)],
    }
    for i, c in enumerate(PROG):
        base = i*16
        for r,n,v in bell_phrases[c]:
            put(p, base+r, CH_LEAD2, n, I_BELL, v)
    lead_phrases = {
        'Am': [(0,'A-4',46),(8,'C-5',42)],
        'F':  [(0,'F-4',46),(8,'A-4',42)],
        'C':  [(0,'E-5',46),(8,'G-5',42)],
        'G':  [(0,'D-5',46),(8,'B-4',42)],
    }
    for i, c in enumerate(PROG):
        base = i*16
        for r,n,v in lead_phrases[c]:
            put(p, base+r, CH_LEAD, n, I_PLUCK, v)

def build_p5():
    """Build - snare roll, chord stabs, rising lead."""
    p = 5
    # 4/4 kicks first 3 bars, accelerating last bar
    for r in range(0, 48, 4):
        put(p, r, CH_KICK, 'C-5', I_KICK, 58)
    for r in [48,52,54,56,58,60,61,62,63]:
        put(p, r, CH_KICK, 'C-5', I_KICK, min(64, 50+r-48))
    # Snare backbeat + rising roll
    for r in [4,12,20,28,36,44]:
        put(p, r, CH_SNARE, 'C-5', I_SNARE, 48)
    for r in [48,52,54,56,58,60,61,62,63]:
        v = min(60, 32 + (r-48)*2)
        put(p, r, CH_SNARE, 'C-5', I_SNARE, v)
    hat16(p, vol=22)
    bass_16th(p, inst=I_SAW, vol=50)
    sub_long(p, inst=I_SUB, vol=38)
    pad(p, vol=22)
    arp_trance(p, vol=36)
    # Rising lead octave climb
    rising = [(0,'A-5',48),(8,'C-6',50),(16,'E-6',52),(24,'G-6',54),
              (32,'A-6',56),(40,'E-6',58),(48,'G-6',60),(56,'A-6',62)]
    for r,n,v in rising:
        put(p, r, CH_LEAD, n, I_PULSE, v)
    # Chord stabs with increasing volume
    chord_stabs(p, vol=36, scale_vol=True)
    put(p, 56, CH_HAT, 'C-5', I_CRASH, 50)

def build_p6():
    """Final chorus - octave up hook."""
    p = 6
    kick4(p, vol=64); snare_bb(p, vol=54, ghosts=True)
    hat8(p, vol=36); ohat_off(p, vol=34)
    bass_drive(p, inst=I_SAW, vol=56); sub_long(p, inst=I_SUB, vol=40)
    pad(p, vol=24); arp_fast(p, vol=36)
    lead_hook_up(p)
    pluck_counter(p)
    bell_sparkle(p)
    put(p, 0, CH_HAT, 'C-5', I_CRASH, 50)

def build_p7():
    """Outro - descending resolve to A tonic."""
    p = 7
    for r in [0,4,8,12,16,20,24,28]:
        put(p, r, CH_KICK, 'C-5', I_KICK, 58)
    for r in [32,40,48,56]:
        put(p, r, CH_KICK, 'C-5', I_KICK, 54)
    for r in [4,12,20,28]:
        put(p, r, CH_SNARE, 'C-5', I_SNARE, 50)
    for r in [36,44,52,60]:
        put(p, r, CH_SNARE, 'C-5', I_SNARE, 46)
    hat8(p, vol=28, end=32); hat8(p, vol=20, start=32)
    bass_off8(p, inst=I_SAW, vol=48); sub_long(p, inst=I_SUB, vol=40)
    pad(p, vol=22); arp_updown(p, vol=30)
    desc = [(0,'E-6',52),(4,'C-6',50),(8,'A-5',48),(12,'G-5',46),
            (16,'E-5',48),(20,'C-5',46),(24,'A-4',44),(28,'E-5',42),
            (32,'A-5',56),(36,'E-5',48),(40,'A-5',52),(44,'G-5',46),
            (48,'A-5',54),(52,'E-5',46),(56,'C-5',44),(60,'A-4',40)]
    for r,n,v in desc:
        put(p, r, CH_LEAD, n, I_PULSE, v)
    put(p, 48, CH_LEAD2, 'A-5', I_BELL, 48)
    put(p, 56, CH_LEAD2, 'E-5', I_BELL, 42)
    # Clean key-offs for loop
    for ch in [CH_LEAD, CH_LEAD2, CH_PAD, CH_ARP, CH_BASS]:
        put(p, 62, ch, 97)
    put(p, 63, CH_HAT, 'C-5', I_CHAT, 20)

# Build everything
for p in range(8):
    cells.append({'name':'pattern_clear','arguments':{'pattern':p}})
    cells.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':64}})

build_p0(); build_p1(); build_p2(); build_p3()
build_p4(); build_p5(); build_p6(); build_p7()

# Post-build: bass walkups at end of chorus patterns
put(2, 60, CH_BASS, 'G-2', I_SAW, 48)
put(2, 62, CH_BASS, 'A-2', I_SAW, 52)
put(3, 62, CH_BASS, 'A-2', I_SAW, 52)
put(6, 60, CH_BASS, 'G-2', I_SAW, 52)
put(6, 62, CH_BASS, 'A-2', I_SAW, 56)

order = [0, 1, 2, 3, 2, 4, 5, 6, 3, 7]
cells.append({'name':'song_set','arguments':{'bpm':150,'speed':5,'length':len(order),'loop_start':0}})
for i, patn in enumerate(order):
    cells.append({'name':'order_set','arguments':{'position':i,'pattern':patn}})

print(f'Total calls: {len(cells)}')
with open('/tmp/compose.json','w') as f:
    json.dump(cells, f)
