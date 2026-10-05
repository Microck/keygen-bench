import json

NOTE_BASE = {'C':1,'C#':2,'D':3,'D#':4,'E':5,'F':6,'F#':7,'G':8,'G#':9,'A':10,'A#':11,'B':12}
def note(name):
    if name == 'off':
        return '==='
    n, oct = name[:-1], int(name[-1])
    return NOTE_BASE[n] + oct*12

CH_KICK=0; CH_SNARE=1; CH_HAT=2; CH_BASS=3; CH_LEAD=4; CH_ARP=5; CH_PAD=6; CH_LEAD2=7

BPM=152
SPEED=6
ROWS=64
PATTERNS=6
SONG_LEN=PATTERNS

I_KICK=1; I_SNARE=2; I_HAT=3; I_BASS=4; I_LEAD=5; I_ARP=6; I_PAD=7

# file, instrument, volume, loop_start, loop_length, flags, finetune, panning, name
SAMPLES=[
    ('kick.wav', I_KICK, 64, 0,0, 4, 0, 128, 'Kick'),
    ('snare.wav', I_SNARE, 56, 0,0, 4, 0, 180, 'Snare'),
    ('hihat.wav', I_HAT, 44, 0,0, 4, 0, 80, 'Hihat'),
    ('bass.wav', I_BASS, 58, 0,168, 5, -7, 128, 'Bass'),
    ('lead.wav', I_LEAD, 50, 0,168, 5, -7, 200, 'Lead'),
    ('arp.wav', I_ARP, 42, 0,168, 5, -7, 70, 'Arp'),
    ('pad.wav', I_PAD, 40, 0,168, 5, -7, 128, 'Pad'),
]

calls=[]
calls.append({'name':'module_new','arguments':{'name':'Neon Keygen','channels':8}})
calls.append({'name':'song_set','arguments':{'bpm':BPM,'speed':SPEED,'length':SONG_LEN,'loop_start':1}})
for p in range(PATTERNS):
    calls.append({'name':'pattern_clear','arguments':{'pattern':p}})
    calls.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':ROWS}})
for f,inst,vol,ls,ll,fl,ft,pan,name in SAMPLES:
    calls.append({'name':'sample_load','arguments':{'path':f'/workspace/{f}','instrument':inst,'sample':0}})
    args={'instrument':inst,'sample':0,'volume':vol,'flags':fl,'finetune':ft,'panning':pan}
    if fl & 1:
        args['loop_start']=ls; args['loop_length']=ll
    calls.append({'name':'sample_set','arguments':args})
    calls.append({'name':'instrument_set','arguments':{'instrument':inst,'name':name}})
for pos in range(SONG_LEN):
    calls.append({'name':'order_set','arguments':{'position':pos,'pattern':pos}})

def cell(p, r, ch, **kwargs):
    args={'pattern':p,'row':r,'channel':ch}
    if 'note' in kwargs:
        args['note']=kwargs['note'] if isinstance(kwargs['note'], str) else kwargs['note']
    if 'inst' in kwargs:
        args['instrument']=kwargs['inst']
    if 'vol' in kwargs:
        args['volume']=kwargs['vol']
    if 'eff' in kwargs:
        args['effect']=kwargs['eff']
    if 'ep' in kwargs:
        args['effect_param']=kwargs['ep']
    calls.append({'name':'pattern_set_cell','arguments':args})

def drum_pattern(p, kicks, snares, hats):
    for r in kicks:
        cell(p,r,CH_KICK,note='C-4',inst=I_KICK,vol=64)
    for r in snares:
        cell(p,r,CH_SNARE,note='C-4',inst=I_SNARE,vol=56)
    for r in hats:
        v = 32 if r%4==2 else 22
        cell(p,r,CH_HAT,note='C-4',inst=I_HAT,vol=v)

def bass_bar(p, bar, root, fifth):
    base=bar*16
    cell(p,base+0,CH_BASS,note=root,inst=I_BASS,vol=54)
    cell(p,base+4,CH_BASS,note=fifth,inst=I_BASS,vol=48)
    cell(p,base+8,CH_BASS,note=root,inst=I_BASS,vol=54)
    cell(p,base+12,CH_BASS,note=fifth,inst=I_BASS,vol=48)
    cell(p,base+14,CH_BASS,note=root,inst=I_BASS,vol=40)

def pad_bar(p, bar, root):
    base=bar*16
    cell(p,base+0,CH_PAD,note=root,inst=I_PAD,vol=42)
    cell(p,base+15,CH_PAD,note='off')

def arp_bar(p, bar, root, arp_param):
    base=bar*16
    for r in range(base, base+16, 2):
        v = 34 if r%4==0 else 26
        cell(p,r,CH_ARP,note=root,inst=I_ARP,vol=v,eff=0,ep=arp_param)

def chords_for_pattern(p, prog):
    for bar, (root,fifth,arp_param,pad_root) in enumerate(prog):
        bass_bar(p,bar,root,fifth)
        pad_bar(p,bar,pad_root)
        arp_bar(p,bar,root,arp_param)

# E minor progression Em-C-G-D.  arp params: minor 0x37, major 0x47.
EM=('E2','B2',0x37,'E3')
C=('C3','G3',0x47,'C4')
G=('G2','D3',0x47,'G3')
D=('D3','A3',0x47,'D4')
PROG=[EM,C,G,D]
PROG5=[EM,C,G,EM]

# Pattern 0: Intro build
chords_for_pattern(0, PROG)
for bar in range(4):
    base=bar*16
    if bar>=1:
        for r in range(base+2,base+16,4):
            cell(0,r,CH_HAT,note='C-4',inst=I_HAT,vol=24)
    if bar>=2:
        cell(0,base+0,CH_KICK,note='C-4',inst=I_KICK,vol=64)
        cell(0,base+8,CH_KICK,note='C-4',inst=I_KICK,vol=48)
    if bar>=3:
        cell(0,base+4,CH_SNARE,note='C-4',inst=I_SNARE,vol=56)
        cell(0,base+12,CH_SNARE,note='C-4',inst=I_SNARE,vol=44)

# Pattern 1: Main A
def fill_drums(p):
    drum_pattern(p,
        [r for bar in range(4) for r in [bar*16, bar*16+8, bar*16+14]],
        [bar*16+4 for bar in range(4)] + [bar*16+12 for bar in range(4)],
        [r for bar in range(4) for r in range(bar*16+2, bar*16+16, 2)])
chords_for_pattern(1, PROG)
fill_drums(1)
leadA=[
    ('B4',0,64),('off',1,None),
    ('A4',4,64),('off',5,None),
    ('G4',8,60),('off',9,None),
    ('E4',12,64),('off',13,None),
    ('G4',16,64),('off',17,None),
    ('A4',20,64),('off',21,None),
    ('B4',24,68),('off',25,None),
    ('C5',28,64),('off',29,None),
    ('B4',32,64),('off',33,None),
    ('A4',36,60),('off',37,None),
    ('G4',40,64),('off',41,None),
    ('D4',44,60),('off',45,None),
    ('F#4',48,64),('off',49,None),
    ('A4',52,60),('off',53,None),
    ('G4',56,64),('off',57,None),
    ('F#4',60,60),('off',61,None),
]
for n,r,v in leadA:
    if v: cell(1,r,CH_LEAD,note=n,inst=I_LEAD,vol=v)
    else: cell(1,r,CH_LEAD,note=n)

# Pattern 2: Main B
def drop_octave(n):
    if n[1]=='#': base=n[:2]; oct=int(n[2])-1; return base+str(oct)
    else: base=n[0]; oct=int(n[1])-1; return base+str(oct)
chords_for_pattern(2, PROG)
fill_drums(2)
notesB=[
    (0,'E5',64),(2,'B4',56),(4,'G4',56),(6,'E4',56),
    (8,'B4',64),(10,'D5',56),(12,'B4',56),(14,'G4',56),
    (16,'C5',64),(18,'G4',56),(20,'E4',56),(22,'C4',56),
    (24,'G4',64),(26,'B4',56),(28,'C5',56),(30,'D5',56),
    (32,'B4',64),(34,'G4',56),(36,'D4',56),(38,'B3',56),
    (40,'G4',64),(42,'B4',56),(44,'D5',56),(46,'G5',56),
    (48,'A4',64),(50,'F#4',56),(52,'D4',56),(54,'A3',56),
    (56,'F#4',64),(58,'A4',56),(60,'D5',56),(62,'F#5',56),
]
for r,n,v in notesB:
    cell(2,r,CH_LEAD,note=n,inst=I_LEAD,vol=v)
for r,n,v in notesB:
    if r%4==0:
        cell(2,r,CH_LEAD2,note=drop_octave(n),inst=I_LEAD,vol=28)

# Pattern 3: Main A repeat + snare fill
def copy_lead(src,dst):
    for n,r,v in leadA:
        if v: cell(dst,r,CH_LEAD,note=n,inst=I_LEAD,vol=v)
        else: cell(dst,r,CH_LEAD,note=n)
chords_for_pattern(3, PROG)
fill_drums(3)
copy_lead(leadA,3)
for r in [60,61,62,63]:
    cell(3,r,CH_SNARE,note='C-4',inst=I_SNARE,vol=48)

# Pattern 4: Breakdown (no drums)
chords_for_pattern(4, PROG)
for bar in range(4):
    base=bar*16
    cell(4,base+8,CH_HAT,note='C-4',inst=I_HAT,vol=24)
lead_break=[(0,'E5',48,0x24),(16,'C5',48,0x24),(32,'B4',48,0x24),(48,'A4',52,0x24)]
for r,n,v,effp in lead_break:
    cell(4,r,CH_LEAD,note=n,inst=I_LEAD,vol=v,eff=4,ep=effp)
    cell(4,r+14,CH_LEAD,note='off')

# Pattern 5: Outro / final build -> loops back to intro
chords_for_pattern(5, PROG5)
drum_pattern(5,
    [r for bar in range(4) for r in [bar*16, bar*16+8]],
    [bar*16+4 for bar in range(4)],
    [r for bar in range(4) for r in range(bar*16+2, bar*16+16, 4)])
outro=[
    (0,'E4',56),(4,'G4',56),(8,'B4',60),(12,'E5',64),
    (16,'D4',56),(20,'F#4',56),(24,'A4',60),(28,'D5',64),
    (32,'G4',56),(36,'B4',56),(40,'D5',60),(44,'G5',64),
    (48,'B4',56),(52,'E5',56),(56,'G5',60),(60,'B5',64),
]
for r,n,v in outro:
    cell(5,r,CH_LEAD,note=n,inst=I_LEAD,vol=v)

with open('batch_compose.json','w') as f:
    json.dump(calls,f,indent=None)
print('total calls', len(calls))
