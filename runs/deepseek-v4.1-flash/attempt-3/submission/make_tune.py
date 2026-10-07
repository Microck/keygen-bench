# -*- coding: utf-8 -*-
"""Build the keygen tune: samples + patterns -> ft2 batch JSON."""
import json, base64, wave, numpy as np

NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def N(name):
    return 1 + NAMES.index(name[:2]) + 12*int(name[2])
def NN(v):
    v = int(v)
    return NAMES[(v-1) % 12] + str((v-1)//12)

CH = dict(LEAD=0, ARP=1, BASS=2, PAD1=3, PAD2=4, PAD3=5, KICK=6, SNARE=7, HAT=8, FX=9, BELL=10)
I  = dict(LEAD=1, ARP=2, BASS=3, PAD=4, KICK=5, SNARE=6, HAT=7, OHAT=8, CRASH=9, BELL=10, RISER=11, BLIP=12)

# ---------------------------------------------------------------- instruments
INST = [
 # (num, file, name, vol, flags, loop_start, loop_len, panning)
 (1,"lead.wav","LEAD",56,17,240,8192,128),
 (2,"arp.wav","ARP",30,17,90,256,86),
 (3,"bass.wav","BASS",48,16,0,0,128),
 (4,"pad.wav","PAD",20,17,900,4096,128),
 (5,"kick.wav","KICK",56,16,0,0,128),
 (6,"snare.wav","SNARE",64,16,0,0,136),
 (7,"hat.wav","HAT",56,16,0,0,164),
 (8,"ohat.wav","OHAT",30,16,0,0,164),
 (9,"crash.wav","CRASH",40,16,0,0,80),
 (10,"bell.wav","BELL",38,16,0,0,118),
 (11,"riser.wav","RISER",48,16,0,0,128),
 (12,"blip.wav","BLIP",44,16,0,0,176),
]

CHORDS = {
 'Am': dict(root='A-2', pad=['A-3','C-4','E-4'], arp=['A-4','C-5','E-5']),
 'F' : dict(root='F-2', pad=['A-3','C-4','F-4'], arp=['A-4','C-5','F-5']),
 'C' : dict(root='C-3', pad=['G-3','C-4','E-4'], arp=['G-4','C-5','E-5']),
 'G' : dict(root='G-2', pad=['G-3','B-3','D-4'], arp=['G-4','B-4','D-5']),
 'Dm': dict(root='D-3', pad=['F-3','A-3','D-4'], arp=['F-4','A-4','D-5']),
 'E' : dict(root='E-2', pad=['G#3','B-3','E-4'], arp=['G#4','B-4','E-5']),
}

ev = []          # (pattern,row,channel,kwargs)
def E(p,row,ch,**kw):
    ev.append((p,int(row),ch,kw))

PADPAN=[0x8,0xA,0xC]   # 8xy set panning: 0x80=left..0xFF=right
def pad_bar(p, r0, chord, vol):
    vol = min(64, int(vol*1.6))
    for i,ch in enumerate([CH['PAD1'],CH['PAD2'],CH['PAD3']]):
        E(p, r0, ch, note=CHORDS[chord]['pad'][i], inst=I['PAD'], vol=vol, eff=8, par=PADPAN[i])

BASS_GROOVE = [(0,0),(3,0),(4,12),(6,0),(8,0),(11,0),(12,12),(14,7)]
BASS_SIMPLE = [(0,0),(4,12),(8,0),(12,12)]
BASS_DRIVE = [(0,0),(2,0),(3,12),(4,0),(6,0),(7,12),(8,0),(10,0),(11,12),(12,0),(14,0),(15,7)]
def bass_bar(p, r0, chord, vol, groove=BASS_GROOVE):
    root = N(CHORDS[chord]['root'])
    for r,off in groove:
        E(p, r0+r, CH['BASS'], note=NN(root+off), inst=I['BASS'], vol=vol)

ARP_A = [(0,0),(1,0),(2,0),(1,0)]
ARP_B = [(0,0),(2,0),(1,1),(2,0),(1,0),(0,0),(1,0),(2,0)]
def arp_bar(p, r0, chord, vol, cycle=ARP_A):
    vol = min(64, int(vol*1.25))
    tones = [N(x) for x in CHORDS[chord]['arp']]
    for i in range(16):
        ti, oc = cycle[i % len(cycle)]
        E(p, r0+i, CH['ARP'], note=NN(tones[ti]+12*oc), inst=I['ARP'], vol=vol)

def kick(p, rows, r0=0):
    for r in rows: E(p, r0+r, CH['KICK'], note='C-4', inst=I['KICK'])
def snare(p, rows, r0=0, vol=None):
    if vol is not None: vol = min(64, int(vol*1.3))
    for r in rows: E(p, r0+r, CH['SNARE'], note='F#6', inst=I['SNARE'], vol=vol)
def hats(p, r0, rows, vol=26, accent=0, inst=None):
    vol = int(vol*1.75)
    accent = int(accent*1.75)
    for r in rows:
        v = vol + (accent if r % 4 == 0 else 0)
        E(p, r0+r, CH['HAT'], note='F#6', inst=inst or I['HAT'], vol=min(64,v))
def ohat(p, r0, r, vol=24):
    E(p, r0+r, CH['HAT'], note='F#6', inst=I['OHAT'], vol=vol)
def bell(p, r0, r, note, vol=30):
    E(p, r0+r, CH['BELL'], note=note, inst=I['BELL'], vol=vol)

def fx(p, r0, r, inst, vol, note='F#6'):
    E(p, r0+r, CH['FX'], note=note, inst=inst, vol=min(64,int(vol*1.2)))

H8  = [0,2,4,6,8,10,12,14]
H16 = list(range(16))
def lead(p, row, note, vol=58, ln=2, vib=None):
    vol = max(1, min(64, int(vol*0.85)))
    E(p, row, CH['LEAD'], note=note, inst=I['LEAD'], vol=vol)
    if vib:
        for k in range(1, ln):
            E(p, row+k, CH['LEAD'], eff=4, par=vib)
def leadrun(p, row, items):
    # items: list of (note, len) 16th note runs
    r = row
    for note, ln in items:
        lead(p, r, note, 58, ln)
        r += ln

# ================================================================ PATTERNS
# ---- P0 intro : Am | Am | F | G
p=0
arp_bar(p, 0,  'Am', 16)
pad_bar(p, 0,  'Am', 9)
bass_bar(p, 0,  'Am', 38, BASS_SIMPLE)
kick(p, [0,8]); hats(p, 0, H8, 20)
arp_bar(p, 16, 'Am', 18)
pad_bar(p, 16, 'Am', 12)
bass_bar(p, 16, 'Am', 44, BASS_SIMPLE)
kick(p, [16,20,24,28]); hats(p, 16, H8, 22)
arp_bar(p, 32, 'F', 20)
pad_bar(p, 32, 'F', 14)
bass_bar(p, 32, 'F', 46)
kick(p, [32,36,40,44]); snare(p,[36,44]); hats(p, 32, H8, 24)
arp_bar(p, 48, 'G', 22)
pad_bar(p, 48, 'G', 16)
bass_bar(p, 48, 'G', 48)
kick(p, [48,52,56,60]); snare(p,[52,60]); hats(p, 48, H8, 26)
snare(p, [58,60,62,63], vol=40)
fx(p, 0, 0, I['CRASH'], 20)
fx(p, 48, 0, I['RISER'], 36)
for r,n in [(0,'A-5'),(4,'C-6'),(8,'E-6'),(12,'A-6')]: bell(p,0,r,n,30)
for r,n in [(16,'C-6'),(20,'E-6'),(24,'A-6')]: bell(p,0,r,n,26)
# lead pickup
for i,(r,n) in enumerate([(56,'A-5'),(58,'B-5'),(60,'C-6'),(62,'D-6')]):
    lead(p, r, n, 48+i*4)

# ---- P1 A1 : Am | F | C | G
p=1
THEME_A = [
  (0,'E-6',64,2),(2,'A-6',58,2),(4,'G-6',58,2),(6,'E-6',58,2),(8,'D-6',62,4),(12,'C-6',58,4),
  (16,'D-6',58,2),(18,'C-6',58,2),(20,'A-5',58,2),(22,'C-6',58,2),(24,'D-6',60,2),(26,'F-6',58,2),(28,'E-6',64,4),
  (32,'E-6',58,2),(34,'G-6',58,2),(36,'E-6',58,2),(38,'C-6',58,2),(40,'G-6',60,2),(42,'E-6',58,2),(44,'D-6',62,4),
  (48,'B-5',58,2),(50,'D-6',58,2),(52,'G-6',60,2),(54,'D-6',58,2),(56,'B-5',58,2),(58,'A-5',58,2),(60,'B-5',64,4),
]
def play_theme(p, theme, vib=None):
    for row,note,vol,ln in theme:
        lead(p, row, note, vol, ln, vib)
for bar,(r0,chord) in enumerate([(0,'Am'),(16,'F'),(32,'C'),(48,'G')]):
    pad_bar(p, r0, chord, 16)
    arp_bar(p, r0, chord, 22, ARP_A if bar%2==0 else ARP_B)
    bass_bar(p, r0, chord, 48)
    kick(p, [r0+0,r0+4,r0+8,r0+12])
    snare(p, [r0+4,r0+12])
    hats(p, r0, H8, 26, accent=6)
    ohat(p, r0, 14, 20)
play_theme(p, THEME_A, vib=0x83)
fx(p, 0, 0, I['CRASH'], 34)

# ---- P2 A2 : variation
p=2
for bar,(r0,chord) in enumerate([(0,'Am'),(16,'F'),(32,'C'),(48,'G')]):
    pad_bar(p, r0, chord, 16)
    arp_bar(p, r0, chord, 22, ARP_B if bar in (1,3) else ARP_A)
    bass_bar(p, r0, chord, 48)
    kick(p, [r0+0,r0+4,r0+8,r0+12] + ([r0+6] if bar in (1,3) else [r0+14]))
    snare(p, [r0+4,r0+12])
    hats(p, r0, H16 if bar==3 else H8, 24, accent=8)
    ohat(p, r0, 14, 20)
play_theme(p, THEME_A[:12], vib=0x83)
# bar 3 variation (C)
for row,note,vol,ln in [(32,'E-6',58,2),(34,'G-6',58,2),(36,'E-6',58,2),(38,'C-6',58,2),(40,'G-6',60,2),(42,'E-6',58,2),(44,'D-6',62,4)]:
    lead(p,row,note,vol,ln)
# bar 4 fill
leadrun(p, 48, [('B-5',2),('D-6',2),('G-6',2),('D-6',2)])
leadrun(p, 56, [('E-6',1),('D-6',1),('C-6',1),('B-5',1),('A-5',2),('B-5',2)])
# bass fill in bar 4
root=N(CHORDS['G']['root'])
for i,r in enumerate([56,58,60,62,63]):
    E(p, r, CH['BASS'], note=NN(root+[0,0,12,7,0][i]), inst=I['BASS'], vol=50)
fx(p, 32, 0, I['BLIP'], 26)

# ---- P3 B1 : F | G | Am | Am
p=3
THEME_B = [
  (0,'A-5',62,2),(2,'C-6',60,2),(4,'F-6',64,2),(6,'E-6',58,2),(8,'D-6',60,4),(12,'C-6',58,4),
  (16,'B-5',60,2),(18,'D-6',60,2),(20,'G-6',64,2),(22,'F-6',58,2),(24,'E-6',60,4),(28,'D-6',58,4),
  (32,'C-6',60,2),(34,'E-6',60,2),(36,'A-6',66,2),(38,'G-6',60,2),(40,'E-6',60,2),(42,'D-6',58,2),(44,'C-6',62,4),
  (48,'B-5',58,2),(50,'C-6',58,2),(52,'E-6',60,2),(54,'D-6',58,2),(56,'C-6',58,2),(58,'B-5',58,2),(60,'A-5',64,4),
]
for bar,(r0,chord) in enumerate([(0,'F'),(16,'G'),(32,'Am'),(48,'Am')]):
    pad_bar(p, r0, chord, 18)
    arp_bar(p, r0, chord, 24, ARP_A if bar%2==0 else ARP_B)
    bass_bar(p, r0, chord, 48)
    kick(p, [r0+0,r0+4,r0+8,r0+12])
    snare(p, [r0+4,r0+12])
    hats(p, r0, H8, 26, accent=6)
    ohat(p, r0, 14, 22)
play_theme(p, THEME_B, vib=0x83)
fx(p, 0, 0, I['CRASH'], 34)

# ---- P4 B2 : F | G | Am | E
p=4
for bar,(r0,chord) in enumerate([(0,'F'),(16,'G'),(32,'Am'),(48,'E')]):
    pad_bar(p, r0, chord, 18)
    arp_bar(p, r0, chord, 24, ARP_B if bar in (0,2) else ARP_A)
    bass_bar(p, r0, chord, 48)
    kick(p, [r0+0,r0+4,r0+8,r0+12])
    snare(p, [r0+4,r0+12])
    hats(p, r0, H8, 26, accent=6)
    ohat(p, r0, 14, 22)
play_theme(p, THEME_B[:12], vib=0x83)
leadrun(p, 48, [('E-6',2),('D-6',2),('B-5',2),('G#5',2),('A-5',4),('B-5',4)])
# chromatic walk up in bar 4
for i,(r,nn) in enumerate([(48,'E-2'),(52,'E-2'),(56,'E-2'),(58,'F-2'),(60,'F#2'),(62,'G#2')]):
    E(p, r, CH['BASS'], note=nn, inst=I['BASS'], vol=50)
snare(p,[62],vol=44)
fx(p, 0, 0, I['CRASH'], 34)

# ---- P5 SOLO : Am | Dm | E | Am
p=5
for bar,(r0,chord) in enumerate([(0,'Am'),(16,'Dm'),(32,'E'),(48,'Am')]):
    pad_bar(p, r0, chord, 18)
    arp_bar(p, r0, chord, 26, ARP_A if bar%2==0 else ARP_B)
    bass_bar(p, r0, chord, 50, BASS_DRIVE)
    kick(p, [r0+0,r0+4,r0+8,r0+12] + ([r0+6] if bar%2 else [r0+14]))
    snare(p, [r0+4,r0+12])
    hats(p, r0, H16, 22, accent=8)
    ohat(p, r0, 14, 22)
SOLO = [
 (0,'A-5'),(1,'C-6'),(2,'E-6'),(3,'A-6'),(4,'G-6'),(6,'E-6'),(8,'D-6'),(9,'C-6'),(10,'B-5'),(11,'C-6'),(12,'D-6'),(14,'E-6'),
 (16,'F-6'),(17,'E-6'),(18,'D-6'),(19,'F-6'),(20,'A-6'),(22,'F-6'),(24,'E-6'),(25,'D-6'),(26,'C-6'),(27,'D-6'),(28,'E-6'),(30,'F-6'),
 (32,'E-6'),(33,'D-6'),(34,'B-5'),(35,'G#5'),(36,'B-5'),(38,'D-6'),(40,'E-6'),(41,'D-6'),(42,'B-5'),(43,'A-5'),(44,'G#5'),(46,'B-5'),
 (48,'A-5'),(49,'B-5'),(50,'C-6'),(51,'D-6'),(52,'E-6'),(54,'A-6'),(56,'G-6'),(57,'E-6'),(58,'D-6'),(59,'C-6'),(60,'B-5'),(62,'A-5'),
]
for i,(r,n) in enumerate(SOLO):
    nxt = SOLO[i+1][0] if i+1<len(SOLO) else 64
    vol = 56 if (nxt-r)<=1 else 60
    lead(p, r, n, vol, max(1,nxt-r))
fx(p, 0, 0, I['CRASH'], 34)

# ---- P6 break : Am | F | Dm | E
p=6
pad_bar(p, 0,  'Am', 20)
pad_bar(p, 16, 'F', 20)
for r,n in [(2,'E-6'),(6,'A-6'),(10,'E-6'),(14,'C-6')]: bell(p,0,r,n,24)
lead(p, 0, 'C-6', 54, 4, vib=0x83)
lead(p, 4, 'E-6', 56, 4, vib=0x83)
lead(p, 8, 'A-6', 60, 8, vib=0x83)
lead(p, 16,'G-6', 56, 4, vib=0x83)
lead(p, 20,'F-6', 56, 4, vib=0x83)
lead(p, 24,'D-6', 58, 8, vib=0x83)
# bar3 Dm
pad_bar(p, 32, 'Dm', 18)
arp_bar(p, 32, 'Dm', 18, ARP_A)
bass_bar(p, 32, 'Dm', 46, BASS_SIMPLE)
kick(p, [32,36,40,44]); hats(p, 32, H8, 22)
lead(p, 32,'D-6', 56, 4, vib=0x83)
lead(p, 36,'F-6', 56, 4, vib=0x83)
lead(p, 40,'A-6', 60, 4, vib=0x83)
lead(p, 44,'G-6', 56, 4, vib=0x83)
# bar4 E build
pad_bar(p, 48, 'E', 20)
arp_bar(p, 48, 'E', 20, ARP_A)
for r in range(48,64,2):
    E(p, r, CH['BASS'], note='E-2' if (r//2)%2==0 else 'E-3', inst=I['BASS'], vol=50)
kick(p, [48,52,56,60]); snare(p, list(range(48,64,2)), vol=30)
hats(p, 48, H16, 20)
lead(p, 48,'G#5', 56, 4, vib=0x83)
lead(p, 52,'B-5', 58, 4, vib=0x83)
lead(p, 56,'D-6', 60, 4, vib=0x83)
lead(p, 60,'B-5', 62, 4, vib=0x83)
fx(p, 48, 0, I['RISER'], 40)
fx(p, 32, 0, I['CRASH'], 30)

# ---- P6 A3 : Am | F | C | G
p=7
for bar,(r0,chord) in enumerate([(0,'Am'),(16,'F'),(32,'C'),(48,'G')]):
    pad_bar(p, r0, chord, 18)
    arp_bar(p, r0, chord, 26, ARP_B)
    bass_bar(p, r0, chord, 50)
    kick(p, [r0+0,r0+4,r0+8,r0+12] + ([r0+6] if bar in (1,3) else [r0+14]))
    snare(p, [r0+4,r0+12])
    hats(p, r0, H16 if bar in (1,3) else H8, 24, accent=8)
    ohat(p, r0, 14, 22)
lead(p, 0,'E-6',64,2); lead(p, 2,'A-6',58,2); lead(p, 4,'G-6',58,2); lead(p, 6,'E-6',58,2)
lead(p, 8,'D-6',62,4, vib=0x83); lead(p, 12,'C-6',58,4, vib=0x83)
lead(p,16,'D-6',58,2); lead(p,18,'C-6',58,2); lead(p,20,'A-5',58,2)
lead(p,21,'B-5',56,1); lead(p,22,'C-6',56,2)
lead(p,24,'D-6',60,2); lead(p,26,'F-6',58,2); lead(p,28,'E-6',64,4, vib=0x83)
lead(p,32,'E-6',58,2); lead(p,34,'G-6',58,2); lead(p,36,'E-6',58,2); lead(p,38,'C-6',58,2)
lead(p,40,'G-6',60,2); lead(p,42,'E-6',58,2); lead(p,44,'D-6',62,4, vib=0x83)
leadrun(p, 48, [('B-5',2),('D-6',2),('G-6',2),('F-6',1),('E-6',1),('D-6',1),('C-6',1),('B-5',2),('A-5',2),('B-5',2)])
fx(p, 0, 0, I['CRASH'], 34)
fx(p, 32, 0, I['BLIP'], 28)

# ---- P7 B3 : F | G | Am | E
p=8
for bar,(r0,chord) in enumerate([(0,'F'),(16,'G'),(32,'Am'),(48,'E')]):
    pad_bar(p, r0, chord, 18)
    arp_bar(p, r0, chord, 26, ARP_A if bar%2 else ARP_B)
    bass_bar(p, r0, chord, 50)
    kick(p, [r0+0,r0+4,r0+8,r0+12] + ([r0+6,r0+14] if bar in (1,3) else []))
    snare(p, [r0+4,r0+12])
    hats(p, r0, H16, 22, accent=8)
    ohat(p, r0, 14, 22)
lead(p, 0,'A-5',62,2); lead(p, 2,'C-6',60,2); lead(p, 4,'F-6',64,2); lead(p, 6,'E-6',58,2)
lead(p, 8,'D-6',60,4, vib=0x83); lead(p, 12,'C-6',58,4, vib=0x83)
lead(p,16,'B-5',60,2); lead(p,18,'D-6',60,2); lead(p,20,'G-6',64,2); lead(p,22,'F-6',58,2)
lead(p,24,'E-6',60,4, vib=0x83); lead(p,28,'D-6',58,4, vib=0x83)
lead(p,32,'C-6',60,2); lead(p,34,'E-6',60,2); lead(p,36,'A-6',66,2); lead(p,38,'G-6',60,2)
lead(p,40,'E-6',60,2); lead(p,41,'D-6',56,1); lead(p,42,'C-6',56,1); lead(p,43,'D-6',56,1)
lead(p,44,'E-6',60,4, vib=0x83)
lead(p,48,'E-6',62,2); lead(p,50,'D-6',58,2); lead(p,52,'B-5',58,2); lead(p,54,'G#5',58,2)
lead(p,56,'A-5',60,4, vib=0x83); lead(p,60,'B-5',64,4, vib=0x83)
for i,(r,nn) in enumerate([(48,'E-2'),(52,'E-2'),(56,'E-2'),(58,'F-2'),(60,'F#2'),(62,'G#2')]):
    E(p, r, CH['BASS'], note=nn, inst=I['BASS'], vol=52)
snare(p, list(range(60,64)), vol=44)
fx(p, 0, 0, I['CRASH'], 34)
fx(p, 32, 0, I['CRASH'], 30)

# ---- P8 outro : Am | F | C | E  (loops back to P0)
p=9
for bar,(r0,chord) in enumerate([(0,'Am'),(16,'F'),(32,'C'),(48,'E')]):
    pad_bar(p, r0, chord, 18)
    arp_bar(p, r0, chord, 24, ARP_A)
    bass_bar(p, r0, chord, 48)
    kick(p, [r0+0,r0+4,r0+8,r0+12])
    snare(p, [r0+4,r0+12])
    hats(p, r0, H8 if bar<3 else H16, 26, accent=6)
    ohat(p, r0, 14, 22)
play_theme(p, THEME_A[:12], vib=0x83)
lead(p,48,'E-6',62,2); lead(p,50,'D-6',58,2); lead(p,52,'B-5',58,2); lead(p,54,'G#5',58,2)
lead(p,56,'A-5',60,4, vib=0x83); lead(p,60,'B-5',64,4, vib=0x83)
for i,(r,nn) in enumerate([(48,'E-2'),(52,'E-2'),(56,'E-2'),(58,'F-2'),(60,'F#2'),(62,'G#2')]):
    E(p, r, CH['BASS'], note=nn, inst=I['BASS'], vol=52)
snare(p, list(range(56,64)), vol=40)
fx(p, 0, 0, I['CRASH'], 34)
fx(p, 48, 0, I['RISER'], 38)
for r,n in [(8,'D-5'),(24,'E-5'),(40,'E-5'),(56,'A-4'),(60,'B-4')]: bell(p,0,r,n,22)

# ================================================================ emit batch
def rd(p):
    w=wave.open(p,'rb'); return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2')

calls=[{"name":"module_new","arguments":{"channels":12,"name":"ACTIVATION CODE"}}]
for num,f,name,vol,flags,ls,ll,pan in INST:
    b=base64.b64encode(rd("/workspace/work/smp/"+f).tobytes()).decode()
    calls.append({"name":"sample_create_from_pcm","arguments":{"instrument":num,"sample":0,"pcm":b,"encoding":"int16","name":name}})
    calls.append({"name":"instrument_set","arguments":{"instrument":num,"name":name}})
    calls.append({"name":"sample_set","arguments":{"instrument":num,"sample":0,"volume":vol,"panning":pan,"relative_note":0,"finetune":0,"flags":flags,"loop_start":ls,"loop_length":ll}})

NPAT=10
for p in range(NPAT):
    calls.append({"name":"pattern_clear","arguments":{"pattern":p}})
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
for (p,row,ch,kw) in ev:
    args={"pattern":p,"row":row,"channel":ch}
    for k,v in kw.items():
        if k=="note": args["note"]=v
        elif k=="inst": args["instrument"]=v
        elif k=="vol": args["volume"]=v
        elif k=="eff": args["effect"]=v
        elif k=="par": args["effect_param"]=v
    calls.append({"name":"pattern_set_cell","arguments":args})
calls.append({"name":"song_set","arguments":{"name":"ACTIVATION CODE","bpm":150,"speed":6,"length":NPAT,"loop_start":0,"channels":12}})
for i in range(NPAT):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
json.dump(calls, open('/workspace/work/build.json','w'))
print("events:", len(ev), "calls:", len(calls))
# sanity: any duplicate note cells on same (p,row,ch)?
seen={}
dups=0
for (p,row,ch,kw) in ev:
    k=(p,row,ch)
    if k in seen: dups+=1
    seen[k]=kw
print("duplicate cells (later overwrites earlier):", dups)
