import json, os, random
from pathlib import Path

calls=[]
def call(tool, **arguments): calls.append({'name':tool,'arguments':arguments})
call('module_new',channels=16,name='CHROMA CIRCUIT')
# Instruments
insts={
1:('01_neon_pulse.wav','NEON PULSE',45,72,1,168,0),
2:('02_arp_spark.wav','ARP SPARK',35,190,1,168,0),
3:('03_round_triangle.wav','ROUND TRI',41,110,1,168,0),
4:('04_copper_bass.wav','COPPER BASS',44,128,1,168,0),
5:('05_velvet_pluck.wav','VELVET PLUCK',46,72,0,0,0),
6:('06_kick.wav','PUNCH KICK',59,128,0,0,-24),
7:('07_snare.wav','PIXEL SNARE',50,144,0,0,0),
8:('08_closed_hat.wav','CLOSED HAT',36,205,0,0,0),
9:('09_open_hat.wav','OPEN HAT',35,210,0,0,0),
10:('10_poly_organ.wav','POLY ORGAN',27,128,1,168,0),
12:('12_glass_bell.wav','GLASS BELL',38,184,0,0,0),
13:('13_crash.wav','NOISE CRASH',34,128,0,0,0),
14:('14_electro_tom.wav','ELECTRO TOM',43,105,0,0,-12),
15:('15_noise_lift.wav','NOISE LIFT',32,160,0,0,0),
16:('16_air_lead.wav','AIR LEAD',36,184,1,168,0),
}
for i,(fn,nm,vol,pan,loop,ll,rel) in insts.items():
    call('sample_load',path='/workspace/samples/'+fn,instrument=i)
    call('instrument_set',instrument=i,name=nm)
    kw=dict(instrument=i,sample=0,name=nm[:22],volume=vol,panning=pan,relative_note=rel)
    if loop: kw.update(loop_start=0,loop_length=ll,flags=1)
    call('sample_set',**kw)

# 15 unique 32-row patterns, one per 8-bar arrangement section.
P=15
for p in range(P): call('pattern_set_length',pattern=p,rows=32)

# effect constants (XM)
ARP=0x0; PORTA_UP=0x1; PORTA_DN=0x2; TONE=0x3; VIB=0x4; VOLSLIDE=0xA; PAN=0x8; OFF=0xC; BREAK=0xD; EXT=0xE

def setc(p,r,ch,note=None,ins=None,vol=None,fx=None,fp=None):
    a={'pattern':p,'row':r,'channel':ch}
    if note is not None:a['note']=note
    if ins is not None:a['instrument']=ins
    if vol is not None:a['volume']=vol
    if fx is not None:a['effect']=fx
    if fp is not None:a['effect_param']=fp
    call('pattern_set_cell',**a)

def note_name(pc,oct):
    return ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-'][pc]+str(oct)
def midi_name(m): return note_name(m%12,m//12-1)

def put(p,r,ch,m,ins,vol=None,fx=None,fp=None): setc(p,r,ch,midi_name(m),ins,None if vol is None else min(64, vol+12),fx,fp)

def off(p,r,ch): setc(p,r,ch,'OFF')

# Harmonic plan: two 4-bar phrases per pattern. Each tuple is 4 beat-level chords.
# Roots around octave 3 (MIDI) and chord tones; all intentionally diatonic to E harmonic/minor/Dorian mixture.
CH={
'Em':([52,55,59,62],40),    # E4 G4 B4 D5 / E2 root
'C': ([48,52,55,59],36),
'G': ([55,59,62,66],43),
'D': ([50,54,57,62],38),
'Am':([57,60,64,67],45),
'B': ([59,63,66,69],47),
'F#d':([54,57,60,63],42),
'Bm':([59,62,66,69],47),
}
progressions=[
 ['Em','C','G','D'],
 ['Em','C','G','D'],
 ['Em','C','G','D'],
 ['Em','C','G','D'],
 ['C','D','Em','Em'],
 ['C','D','B','B'],
 ['Am','C','Em','D'],
 ['Am','C','B','B'],
 ['G','D','Em','C'],
 ['G','D','C','B'],
 ['C','G','D','Em'],
 ['C','G','B','B'],
 ['Em','D','C','B'],
 ['Em','D','C','B'],
 ['Em','C','G','D'],
]
# Second half variations per section
second=[
 ['Em','C','G','D'], ['Em','C','G','B'], ['Em','C','G','D'], ['Em','C','G','B'],
 ['C','D','Em','Em'], ['C','D','B','B'], ['Am','C','Em','D'], ['Am','C','B','B'],
 ['G','D','Em','C'], ['G','D','C','B'], ['C','G','D','Em'], ['C','G','B','B'],
 ['Am','C','Em','B'], ['Em','D','C','B'], ['Em','C','G','B']]

# Section-level arrangement intensity and labels
# 0 introA, 1 introB, 2 themeA, 3 themeA+, 4 themeB, 5 themeB+, 6 bridge, 7 bridge build,
# 8 solo, 9 solo+, 10 breakdown, 11 rebuild, 12 climaxA, 13 climaxB, 14 final turnaround.

# Beat chord accessor (row //4; 8 beats? Actually every chord spans 8 rows = 2 beats, 4 chords/pattern)
def chord_at(p,r):
    prog=progressions[p] if r<16 else second[p]
    idx=(r%16)//4  # each listed chord = one beat (4 rows), repeats phrase twice
    return prog[idx]

# PAD / sustained harmonic bed (channels 8-10) in selected sections.
pad_sections={0:19,1:21,4:20,5:21,6:19,7:21,8:17,9:18,10:20,11:22,12:18,13:19,14:21}
for p,pv in pad_sections.items():
    # Change chord every 4 rows. Use restrained triads, retrigger to shape articulation.
    for r in range(0,32,4):
        cn=chord_at(p,r); tones=CH[cn][0][:3]
        # lower voicing by octave; channel pan via sample panning/explicit first rows
        for j,m in enumerate(tones):
            put(p,r,8+j,m-12,10,pv+(2 if j==0 else 0))
            # cut before next chord for clean tracker phrasing
            off(p,r+3,8+j)

# BASS patterns. Syncopated 16th pulse; later patterns get octave and approach notes.
for p in range(P):
    active = p not in {0,10} or True
    for beatrow in range(0,32,4):
        cn=chord_at(p,beatrow); root=CH[cn][1]  # roots E2 etc
        # Intro sparse / breakdown pulse / normal keygen drive
        if p==0:
            if beatrow%8==0:
                put(p,beatrow,4,root,4,27)
                off(p,beatrow+3,4)
        elif p==10:
            put(p,beatrow,4,root,4,28)
            put(p,beatrow+3,4,root+12,4,20)
        elif p in {1,4,6,11,14}:
            for d,m,v in [(0,root,35),(2,root+12,24),(3,root,29)]: put(p,beatrow+d,4,m,4,v)
        else:
            seq=[(0,root,39),(1,root,28),(2,root+12,33),(3,root,30)]
            for d,m,v in seq: put(p,beatrow+d,4,m,4,v)
    # End-of-pattern leading tone fill in energetic transitions
    if p in {3,5,7,9,11,13,14}:
        # chromatic approach to E2; override last 3 rows
        for d,m,v in [(29,45,28),(30,46,31),(31,47,35)]: put(p,d,4,m,4,v)

# ARPEGGIO motor channel 1, sixteenth notes, chord contours and occasional effect arps.
arp_sections={1:24,2:30,3:32,4:27,5:31,6:26,7:32,8:31,9:34,11:25,12:32,13:34,14:30}
for p,av in arp_sections.items():
    for beatrow in range(0,32,4):
        cn=chord_at(p,beatrow); tones=CH[cn][0]
        # Pattern-dependent rotations produce continuous, composed movement.
        rot=(beatrow//4 + p)%4
        contour=[0,1,2,3] if ((beatrow//4+p)&1)==0 else [2,1,3,1]
        for d,ix in enumerate(contour):
            m=tones[(ix+rot)%4] + (12 if ((d==3 and p>=7) or (p in {12,13} and d==2)) else 0)
            v=av + (3 if d==0 else 0) - (2 if d in (1,3) else 0)
            put(p,beatrow+d,1,m,2,v)
    # Resolve fill using classic tracker arpeggio on last note in select sections.
    if p in {3,5,7,9,11,13}:
        put(p,31,1,59,2,av,ARP,0x37)

# Secondary pluck/chord ostinato channel 5, offbeat to leave room.
pluck_sections={2:30,3:33,4:31,5:33,6:29,7:33,8:27,9:28,11:27,12:31,13:33,14:30}
for p,pv in pluck_sections.items():
    for beatrow in range(0,32,4):
        tones=CH[chord_at(p,beatrow)][0]
        # tonic/dyad answer on off-sixteenths
        put(p,beatrow+1,5,tones[1]+12,5,pv-3)
        put(p,beatrow+3,5,tones[2]+12,5,pv)

# Main melody phrases, MIDI pitches. Rows cover each 32-row section.
# Hooks centered E minor; motifs are deliberately repeated then answered.
melodies={
2:[(0,71,40),(2,74,36),(4,76,43),(7,74,35),(8,71,40),(10,67,34),(12,69,39),(14,71,43),(16,74,41),(18,76,44),(20,79,46),(23,78,35),(24,76,42),(26,74,39),(28,71,43),(31,69,31)],
3:[(0,71,42),(2,74,38),(4,76,45),(6,79,43),(8,78,40),(10,76,38),(12,74,42),(14,71,38),(16,67,36),(18,69,38),(20,71,43),(22,74,40),(24,76,46),(27,74,39),(28,71,44),(30,78,41)],
4:[(0,76,42),(3,74,36),(4,72,41),(6,71,38),(8,69,43),(11,71,38),(12,72,42),(14,74,40),(16,76,44),(18,79,40),(20,78,42),(22,76,38),(24,74,43),(26,72,38),(28,71,42),(30,69,35)],
5:[(0,76,43),(2,79,41),(4,81,46),(7,79,38),(8,78,43),(10,76,39),(12,74,42),(15,71,37),(16,72,40),(18,74,42),(20,76,45),(22,78,41),(24,79,46),(27,78,40),(28,76,44),(30,75,42)],
6:[(0,69,39),(2,72,42),(4,76,45),(7,74,37),(8,72,41),(10,71,38),(12,69,42),(14,67,36),(16,71,41),(18,74,43),(20,76,46),(23,79,42),(24,78,43),(26,76,40),(28,74,44),(30,71,38)],
7:[(0,69,41),(2,72,43),(4,76,47),(6,79,44),(8,81,48),(11,79,41),(12,76,45),(14,74,39),(16,72,42),(18,76,45),(20,79,47),(22,83,49),(24,81,47),(26,79,44),(28,78,45),(30,75,41)],
12:[(0,83,45),(2,81,42),(4,79,47),(6,78,42),(8,76,46),(10,79,43),(12,83,48),(15,81,41),(16,79,45),(18,76,42),(20,74,45),(22,76,43),(24,78,47),(26,81,45),(28,83,49),(30,78,42)],
13:[(0,83,47),(2,86,45),(4,88,50),(7,86,43),(8,83,47),(10,81,44),(12,79,46),(14,78,42),(16,76,44),(18,79,46),(20,83,50),(22,81,45),(24,79,47),(26,78,43),(28,76,46),(30,75,42)],
14:[(0,71,43),(2,74,40),(4,76,46),(7,74,38),(8,71,43),(10,67,37),(12,69,41),(14,71,45),(16,74,43),(18,76,46),(20,79,48),(23,78,40),(24,76,45),(26,74,42),(28,71,46),(30,78,42)],
}
for p,seq in melodies.items():
    for i,(r,m,v) in enumerate(seq):
        # lead channel 0. Vibrato on sustained starts, occasional portamento-like grace handled separately.
        fx=VIB if r in {4,12,20,24} else None; fp=0x35 if fx is not None else None
        put(p,r,0,m,1,v,fx,fp)
        # Note-off before some gaps, never clobber adjacent row.
        nr=seq[i+1][0] if i+1<len(seq) else 32
        if nr-r>=3 and r+2<32: off(p,r+2,0)

# Intro bell identity motif and sparse preview of hook.
for r,m,v in [(0,76,34),(4,79,31),(8,83,37),(12,78,30),(16,76,34),(20,74,30),(24,71,34),(28,75,32)]: put(0,r,6,m,12,v)
for r,m,v in [(0,71,34),(4,74,31),(8,76,36),(12,74,30),(16,71,35),(20,67,29),(24,69,34),(28,78,34)]: put(1,r,0,m,16,v,VIB if r in {8,24} else None,0x24 if r in {8,24} else None)

# Bridge counter melody on channel 6 (glass bell), then lead interlocks.
for p,seq in {
6:[(1,76),(5,79),(9,76),(13,72),(17,74),(21,78),(25,81),(29,78)],
7:[(1,81),(5,79),(9,76),(13,74),(17,76),(21,79),(25,83),(29,87)],
10:[(0,76),(6,74),(12,71),(16,69),(22,71),(28,75)],
11:[(2,71),(6,74),(10,76),(14,78),(18,79),(22,83),(26,81),(30,78)],
}.items():
    for r,m in seq: put(p,r,6,m,12,31 if p!=10 else 27)

# Solo lead on channel 0 with air lead color and rapid expressive runs.
solo8=[(0,76),(1,78),(2,79),(3,83),(4,81),(6,79),(7,78),(8,76),(10,74),(11,71),(12,72),(13,74),(14,76),(15,79),(16,83),(18,81),(19,79),(20,78),(21,76),(22,74),(23,71),(24,74),(25,76),(26,78),(27,81),(28,79),(29,78),(30,76),(31,74)]
solo9=[(0,79),(1,81),(2,83),(3,86),(4,88),(6,86),(7,83),(8,81),(9,79),(10,78),(11,76),(12,78),(13,79),(14,81),(15,83),(16,86),(18,83),(19,81),(20,79),(21,78),(22,76),(23,74),(24,76),(25,78),(26,79),(27,83),(28,81),(29,79),(30,78),(31,75)]
for p,seq in [(8,solo8),(9,solo9)]:
    for i,(r,m) in enumerate(seq):
        fx=VIB if r in {4,16} else None
        put(p,r,0,m,16,39+(4 if r%4==0 else 0),fx,0x46 if fx is not None else None)

# Climax counter harmony / octave answer on ch 6 with pulse instrument for distinct spatial line.
for p in {12,13}:
    for r in range(2,32,4):
        # harmonize current melody-ish chord at a third below in upper register
        tones=CH[chord_at(p,r)][0]
        m=tones[(r//4+1)%3]+12
        put(p,r,6,m,3,31)
        off(p,r+1,6)

# DRUMS channels 12 kick, 13 snare, 14 hats, 15 cymbals/fills.
def drum_kick(p,rows,vol=55):
    for r in rows: put(p,r,12,48,6,vol if r%8==0 else vol-4)
def drum_snare(p,rows,vol=47):
    for r in rows: put(p,r,13,48,7,vol)
def hats(p,step=2,vol=31,open_rows=()):
    opens=set(open_rows)
    for r in range(0,32,step):
        if r in opens: put(p,r,14,48,9,vol+1)
        else: put(p,r,14,48,8,vol+(2 if r%4==0 else -3))
# Intro no drums p0. Intro B filtered impression: kick on beat starts, hats eighths.
drum_kick(1,[0,8,16,24],48); hats(1,4,25,[28])
# Most active sections use four-on-floor plus syncopation and backbeat every 8 rows at row 4.
for p in [2,3,4,5,6,7,8,9,11,12,13,14]:
    kicks=[0,4,8,12,16,20,24,28]
    if p in {3,5,7,9,12,13}: kicks += [10,22,27]
    elif p in {4,6,11,14}: kicks += [14,30]
    drum_kick(p,sorted(set(kicks)),56 if p>=12 else 53)
    drum_snare(p,[4,12,20,28],49 if p>=12 else 46)
    hats(p,1 if p in {3,5,7,9,12,13} else 2,33 if p>=12 else 30,[6,14,22,30])
# Breakdown minimal rim-like snare and hats
drum_kick(10,[0,8,16,24],45); drum_snare(10,[12,28],35); hats(10,4,23,[28])
# Open hats overwrite selected closed hats
for p in [2,3,4,5,6,7,8,9,11,12,13,14]:
    for r in [6,14,22,30]: put(p,r,14,48,9,32)
# Crashes at section anchors
for p in [2,4,6,8,10,12]: put(p,0,15,48,13,34 if p<12 else 39)
# reverse lift near build endings, will swell into next pattern
for p in [1,3,5,7,9,11]: put(p,30,15,48,15,29)
# Tom fills
fills={3:[(29,52),(30,55),(31,59)],5:[(29,55),(30,59),(31,64)],7:[(28,52),(29,55),(30,59),(31,64)],9:[(29,59),(30,55),(31,52)],11:[(28,52),(29,55),(30,59),(31,64)],13:[(29,55),(30,59),(31,64)],14:[(29,59),(30,55),(31,52)]}
for p,seq in fills.items():
    for r,m in seq: put(p,r,15,m,14,36+(r-28)*2)

# Dedicated effect-only automation is intentionally omitted: sample panning supplies stable stereo placement.
# Explicit stereo animation via pan effect on the two lead channels at phrase starts.
for p in range(0):
    pass

# Pattern 14 end should lead seamlessly to pattern 2 (loop start): add pickup and no hard break.
# Final row effects: global style volume slide? use note-based lead pickup already B/D# into E.

# Song order: 15 patterns, loop from pattern/order 2 after one-time 16-bar intro.
for pos,p in enumerate(range(P)): call('order_set',position=pos,pattern=p)
call('song_set',name='CHROMA CIRCUIT',bpm=150,speed=3,length=P,loop_start=2)

Path('/workspace/build.json').write_text(json.dumps(calls))
print('calls',len(calls))
