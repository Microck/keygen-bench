import sys, numpy as np
sys.path.insert(0,'/workspace/work')
exec(open('/workspace/work/gen3.py').read())

C=Composer('Keygen Runner', bpm=164)

# =========================================================== melodic material
VERSE = [
 (0,69,2),(2,72,2),(4,76,3),(7,79,1),(8,76,2),(10,72,2),(12,69,4),
 (16,72,2),(18,76,2),(20,77,3),(23,76,1),(24,72,2),(26,69,2),(28,65,4),
 (32,72,2),(34,76,2),(36,79,3),(39,76,1),(40,72,2),(42,67,2),(44,72,4),
 (48,74,2),(50,79,2),(52,83,3),(55,79,1),(56,74,2),(58,71,2),(60,67,4),
]
VERSE_B = [
 (0,76,2),(2,79,2),(4,81,3),(7,79,1),(8,76,2),(10,72,2),(12,69,4),
 (16,77,2),(18,81,2),(20,84,3),(23,81,1),(24,77,2),(26,76,2),(28,72,4),
 (32,79,2),(34,83,2),(36,88,3),(38,86,1),(39,84,1),(40,79,2),(42,76,2),(44,72,4),
 (48,74,2),(50,79,2),(52,83,2),(54,81,2),(56,79,3),(59,74,1),(60,71,4),
]
CHORUS = [
 (0,77,2),(2,81,2),(4,84,3),(7,81,1),(8,84,2),(10,81,2),(12,77,4),
 (16,76,2),(18,79,2),(20,84,3),(23,79,1),(24,76,2),(26,72,2),(28,76,4),
 (32,74,2),(34,79,2),(36,83,3),(39,79,1),(40,74,2),(42,79,2),(44,83,4),
 (48,81,2),(50,76,2),(52,72,3),(55,69,1),(56,72,2),(58,76,2),(60,81,4),
]
CHORUS_B = [
 (0,81,2),(2,84,2),(4,86,3),(7,84,1),(8,81,2),(10,77,2),(12,81,4),
 (16,84,2),(18,79,2),(20,76,2),(22,79,2),(24,84,3),(27,83,1),(28,79,4),
 (32,83,2),(34,79,2),(36,74,2),(38,79,2),(40,83,3),(43,86,1),(44,88,4),
 (48,84,2),(50,81,2),(52,76,2),(54,81,2),(56,84,3),(59,88,1),(60,91,4),
]
BRIDGE = [
 (0,74,3),(3,77,1),(4,81,2),(6,77,2),(8,74,4),(12,69,4),
 (16,77,3),(19,76,1),(20,74,2),(22,69,2),(24,65,4),(28,69,4),
 (32,71,3),(35,76,1),(36,80,2),(38,76,2),(40,71,4),(44,64,4),
 (48,76,2),(50,80,2),(52,83,2),(54,80,2),(56,76,4),(60,71,4),
]
TAG = [
 # G:  B A G D G B
 (0,83,3),(3,81,1),(4,79,2),(6,74,2),(8,79,4),(12,83,4),
 # A:  C# B A E A C#
 (16,85,3),(19,83,1),(20,81,2),(22,76,2),(24,81,4),(28,85,4),
 # Bm: B A F# D F# B
 (32,83,3),(35,81,1),(36,78,2),(38,74,2),(40,78,4),(44,83,4),
 # E:  G# B E B G# E
 (48,80,2),(50,83,2),(52,88,3),(55,83,1),(56,80,4),(60,76,4),
]
# intro motif: sparse bell-like lead
INTRO_LEAD = [
 (0,69,4),(8,76,4),(16,72,4),(24,77,4),
 (32,79,4),(40,83,4),(48,80,4),(56,76,4),
]
COUNTERS = {
 'FCGA':[(0,72,8),(8,76,8),(16,76,8),(20,72,8),(24,67,8),(32,71,8),(40,74,8),(48,76,8),(52,72,8),(56,69,8),(60,64,4)],
 'GDAB':[(0,74,8),(8,71,8),(16,78,8),(24,74,8),(28,71,8),(32,76,8),(40,73,8),(44,69,8),(48,73,8),(52,76,8),(56,83,8)],
}

# arpeggio fill runs (16ths)
FILL_AM=[69,72,76,79,81,84,88,91]
FILL_F =[65,69,72,77,81,84,89,93]
FILL_C =[72,76,79,84,88,91,96,100]
FILL_G =[67,71,74,79,83,86,91,95]
FILL_DM=[62,65,69,74,77,81,86,89]
FILL_E =[64,68,71,76,80,83,88,92]
FILL_BM=[59,62,66,71,74,78,83,86]
FILL_D =[62,66,69,74,78,81,86,90]

BAR_INTRO  =['Am','F','G','E']
BAR_VERSE  =['Am','F','C','G']
BAR_CHORUS =['F','C','G','Am']
BAR_BRIDGE =['Dm','Dm','E','E']
BAR_VERSE2 =['Bm','G','D','A']
BAR_CHORUS2=['G','D','A','Bm']
BAR_OUTRO  =['G','A','Bm','E']
SH=2

# =============================================================== P0: intro
C.new()
# bar 1-2: pad + arp only, bar 3-4: add bass & ticks & bells
for i,ch in enumerate(BAR_INTRO):
    C.pad(i*16,ch,vol=17 if i<2 else 16)
C.arp(0,'Am','updown',1,20,'arp',rows=16)
C.arp(16,'F','updown',1,20,'arp',rows=16)
C.arp(32,'G','updown',1,21,'arp',rows=16)
C.arp(48,'E','updown',1,22,'arp',rows=16)
C.arp(0,'Am','wide',4,10,'arp2',rows=64)
for dr,mm in [(4,88),(12,84),(20,88),(28,84),(36,86),(44,91),(52,83),(60,88)]:
    C.bell(dr,mm,15)
C.put(0,'crash',note=49,ins='crash',vol=22)
for i,ch in enumerate(BAR_INTRO):
    if i>=1:
        C.put(i*16,'bass',note=n(CHORDS[ch]['root']),ins='bass',vol=26)
        C.put(i*16+8,'bass',note=n(CHORDS[ch]['root']+12),ins='bass',vol=22)
C.ticks(32,vol=6,step=2,offset=1,rows=32)
C.riser(56,17)
C.run_up(56,[64,68,71,76,80,83,88,92],vol=20,ch='arp')
# keygen signature chime motif
C.chime_hook(0,'Am',vol=18,octave=12)
C.chime_hook(8,'Am',vol=15,octave=24)
C.chime_hook(16,'F',vol=17,octave=12)
C.chime_hook(24,'F',vol=15,octave=24)
C.chime_hook(32,'G',vol=17,octave=12)
C.chime_hook(40,'G',vol=15,octave=24)
C.chime_hook(48,'E',vol=17,octave=12)

# =============================================================== P1: intro B
C.new()
for i,ch in enumerate(BAR_INTRO):
    C.pad(i*16,ch,vol=15)
    C.bass(i*16,ch,vol=32,style='half',sub=False)
    C.organ(i*16,ch,vol=11,rhythm=(0,10),sel='root12')
C.arp(0,'Am','updown',1,17,'arp',rows=16)
C.arp(16,'F','updown',1,17,'arp',rows=16)
C.arp(32,'G','updown',1,18,'arp',rows=16)
C.arp(48,'E','updown',1,19,'arp',rows=16)
C.arp(0,'Am','oct',4,8,'arp2',rows=64)
C.drums(0,'sparse',1.0,chord_rows=32)
C.drums(32,'half',1.0,chord_rows=32)
C.snare_roll(56,64,12,44,1)
C.phrase(0,INTRO_LEAD,vol=28,bar_chords=BAR_INTRO,echo=True,echo_vol=11)
C.run_up(56,[64,68,71,76,80,83,88,92],vol=21,ch='arp')

# =============================================================== P2: verse 1
C.new()
for i,ch in enumerate(BAR_VERSE):
    C.pad(i*16,ch,vol=9)
    C.bass(i*16,ch,vol=35,style='drive')
    C.arp(i*16,ch,'up',2,22,'arp2',start=i*3,skips=(6,14))
C.drums(0,'full',1.0,chord_rows=16,fill=True,fill_at=56)
C.phrase(0,VERSE,vol=34,bar_chords=BAR_VERSE,vibrato=0x46)
C.ticks(0,vol=4,step=4)
C.run_up(56,[67,71,74,79,83,86,91,95],vol=20,ch='arp')

# =============================================================== P3: verse 2
C.new()
for i,ch in enumerate(BAR_VERSE):
    C.pad(i*16,ch,vol=10)
    C.bass(i*16,ch,vol=36,style='gallop')
    C.arp(i*16,ch,'octup',1,18,'arp2',start=i*4,skips=(4,12))
C.drums(0,'drive',1.0,chord_rows=16,fill=True,fill_at=54)
C.phrase(0,VERSE_B,vol=35,bar_chords=BAR_VERSE,echo=True,echo_vol=12,vibrato=0x48)
for i,ch in enumerate(BAR_VERSE):
    C.organ(i*16,ch,vol=12,rhythm=(0,6,10,14),sel='third')
C.run_up(56,[67,71,74,79,83,86,91,95],vol=22,ch='arp')

# =============================================================== P4: chorus 1
C.new()
for i,ch in enumerate(BAR_CHORUS):
    C.pad(i*16,ch,vol=14)
    C.bass(i*16,ch,vol=37,style='8ths')
    C.arp(i*16,ch,'pump',1,20,'arp',start=i*2,skips=(4,12))
C.drums(0,'chorus',1.0,crash=True,chord_rows=16)
C.phrase(0,CHORUS,vol=36,harm=True,harm_vol=22,bar_chords=BAR_CHORUS,echo=True,echo_vol=13,vibrato=0x47)
for i,ch in enumerate(BAR_CHORUS):
    C.chime_hook(i*16,ch,vol=13,octave=12)
for i,ch in enumerate(BAR_CHORUS):
    C.counter(i*16,ch,vol=14,rhythm=(0,6),sel='fifth')
for i,ch in enumerate(BAR_CHORUS):
    C.organ(i*16,ch,vol=12,rhythm=(6,14),sel='fifth')
C.run_up(56,[69,72,76,79,81,84,88,91],vol=22,ch='arp')

# =============================================================== P5: chorus 2
C.new()
for i,ch in enumerate(BAR_CHORUS):
    C.pad(i*16,ch,vol=14)
    C.bass(i*16,ch,vol=38,style='drive')
    C.arp(i*16,ch,'oct',1,19,'arp',start=i*3)
C.drums(0,'chorus',1.0,crash=True,chord_rows=16,fill=True,fill_at=56)
C.phrase(0,CHORUS_B,vol=37,harm=True,harm_vol=23,bar_chords=BAR_CHORUS,echo=True,echo_vol=14,vibrato=0x49)
for i,ch in enumerate(BAR_CHORUS):
    C.chime_hook(i*16,ch,vol=13,octave=24 if i%2 else 12)
for i,ch in enumerate(BAR_CHORUS):
    C.counter(i*16,ch,vol=14,rhythm=(0,6),sel='fifth')
for i,ch in enumerate(BAR_CHORUS):
    C.organ(i*16,ch,vol=11,rhythm=(0,8),sel='third')
C.run_up(56,[69,72,76,79,81,84,88,91],vol=22,ch='arp')

# =============================================================== P6: bridge
C.new()
for i,ch in enumerate(BAR_BRIDGE):
    C.pad(i*16,ch,vol=13)
C.bass(0,'Dm',vol=33,style='long')
C.bass(32,'E',vol=35,style='drive2' if False else 'oct')
C.arp(0,'Dm','updown',2,16,'arp',rows=32)
C.arp(32,'E','updown',2,18,'arp',rows=32)
C.arp(0,'Dm','oct',4,10,'arp2',rows=32)
C.arp(32,'E','oct',4,11,'arp2',rows=32)
C.drums(0,'light',0.75,chord_rows=32)
C.drums(32,'half',0.9,chord_rows=32)
C.phrase(0,BRIDGE,vol=35,harm=True,harm_vol=20,bar_chords=BAR_BRIDGE,echo=True,echo_vol=12,vibrato=0x45)
for dr,mm in [(4,86),(12,81),(20,86),(28,89),(36,88),(44,83)]: C.bell(dr,mm,14)
C.organ(32,'E',vol=14,rhythm=(0,4,8,12),sel='root12')
C.put(32,'crash',note=49,ins='crash',vol=20)
C.snare_roll(40,56,12,34,2)
C.snare_roll(56,64,16,44,1)
C.riser(48,22)
C.run_up(56,[64,68,71,76,80,83,88,92],vol=22,ch='arp')
# rising arp figure under the build
C.run_up(48,[64,71,76,80,64,71,76,80],vol=15,ch='arp2',step=1)

# =============================================================== P7: verse 3 (+2)
C.new()
for i,ch in enumerate(BAR_VERSE):
    C.pad(i*16,ch,vol=10,shift=SH)
    C.bass(i*16,ch,vol=36,style='gallop',shift=SH)
    C.arp(i*16,ch,'octup',1,18,'arp2',shift=SH,start=i*2)
C.drums(0,'drive',1.0,crash=True,chord_rows=16,fill=True,fill_at=56)
C.phrase(0,VERSE,vol=35,shift=SH,bar_chords=BAR_VERSE,echo=True,echo_vol=12,vibrato=0x46)
for i,ch in enumerate(BAR_VERSE):
    C.organ(i*16,ch,vol=11,shift=SH,rhythm=(0,6),sel='third')
C.run_up(56,[59,62,66,71,74,78,83,86],vol=22,ch='arp')

# =============================================================== P8: final chorus (+2)
C.new()
for i,ch in enumerate(BAR_CHORUS):
    C.pad(i*16,ch,vol=14,shift=SH)
    C.bass(i*16,ch,vol=39,style='8ths',shift=SH)
    C.arp(i*16,ch,'pump',1,21,'arp',shift=SH,start=i*2,skips=(4,12))
C.drums(0,'dense',1.0,crash=True,chord_rows=16)
C.phrase(0,CHORUS,vol=37,shift=SH,harm=True,harm_vol=24,bar_chords=BAR_CHORUS,echo=True,echo_vol=14,vibrato=0x48)
for i,ch in enumerate(BAR_CHORUS):
    C.chime_hook(i*16,ch,vol=13,shift=SH,octave=12)
for i,ch in enumerate(BAR_CHORUS):
    C.counter(i*16,ch,vol=14,shift=SH,rhythm=(0,6),sel='fifth')
for i,ch in enumerate(BAR_CHORUS):
    C.organ(i*16,ch,vol=12,shift=SH,rhythm=(6,14),sel='fifth')
C.run_up(56,[62,66,69,74,78,81,86,90],vol=22,ch='arp')

# =============================================================== P9: outro / turnaround
C.new()
for i,ch in enumerate(BAR_OUTRO):
    C.pad(i*16,ch,vol=13)
    C.bass(i*16,ch,vol=35,style='8ths' if i<2 else 'half')
C.arp(0,'G','updown',1,16,'arp',rows=16)
C.arp(16,'A','updown',1,15,'arp',rows=16)
C.arp(32,'Bm','updown',1,15,'arp',rows=16)
C.arp(48,'E','updown',1,17,'arp',rows=16)
C.arp(0,'G','wide',4,9,'arp2',rows=64)
C.drums(0,'full',1.0,crash=True,chord_rows=32)
C.drums(32,'half',1.0,chord_rows=32)
C.phrase(0,TAG,vol=35,harm=True,harm_vol=21,bar_chords=BAR_OUTRO,echo=True,echo_vol=12,vibrato=0x46)
for dr,mm in [(48,84),(52,80),(56,83),(60,88)]: C.bell(dr,mm,15)
C.riser(56,16)
C.ticks(0,vol=4,step=4)
C.arp(60,'E','updown',1,26,'arp',rows=3,start=0)
C.snare_roll(56,64,14,40,1)
C.put(0,'crash',note=49,ins='crash',vol=20)
for chn in ['lead','harm','arp','arp2','bass','sub','organ','tick']:
    C.put(63,chn,note='off')
# pads ring across the loop point (retriggered at P0) for a seamless seam
C.put(62,'echo',note='off')
C.put(62,'lead',note='off')
C.put(62,'harm',note='off')

C.song.orders=list(range(len(C.song.patterns)))
C.song.restart=2   # loop back to the verse (outro E -> Am); intro plays once
sz=write_xm(C.song,'/workspace/work/candidate.xm')
print('patterns',len(C.song.patterns),'orders',C.song.orders,'size',sz)
