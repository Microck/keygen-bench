"""FINAL keygen tune: 'KEYGEN // NEON VAULT' — A-minor chip anthem, seamless loop.
8 channels, speed 3, BPM 140, 8x64-row patterns. All sound from 8 small samples."""
import sys
sys.path.insert(0,"/workspace/src")
from lib import call, upload_packed, xm_info
import numpy as np
from samples import band_square32, bass32, saw32, pad32, kick8363, snare8363, hat_closed8363, crash8363
import random
random.seed(11); np.random.seed(11)

call("module_new", {"channels":8, "name":"KEYGEN // NEON VAULT"})
call("song_set", {"bpm":140,"speed":3,"length":8,"loop_start":0})

upload_packed(band_square32(amp=112), 1, "LeadSQ", loop_start=0, loop_length=32, flags=1, volume=60, panning=128)
upload_packed(bass32(amp=118),        2, "BassPU", loop_start=0, loop_length=32, flags=1, volume=62, panning=100)
upload_packed(saw32(amp=100),         3, "ArpSAW", loop_start=0, loop_length=32, flags=1, volume=48, panning=160)
upload_packed(pad32(amp=100),         4, "PadTRI", loop_start=0, loop_length=32, flags=1, volume=52, panning=128)
upload_packed(kick8363(),             5, "KickBD", loop_start=0, loop_length=0, flags=0, volume=64, panning=128)
upload_packed(snare8363(),            6, "Snare",  loop_start=0, loop_length=0, flags=0, volume=58, panning=128)
upload_packed(hat_closed8363(),       7, "HatCl",  loop_start=0, loop_length=0, flags=0, volume=34, panning=180)
upload_packed(crash8363(),            8, "Crash",  loop_start=0, loop_length=0, flags=0, volume=38, panning=128)

N2S={0:"C-",1:"C#",2:"D-",3:"D#",4:"E-",5:"F-",6:"F#",7:"G-",8:"G#",9:"A-",10:"A#",11:"B-"}
def nm(m): return f"{N2S[m%12]}{m//12-1}"
def cell(pat,row,ch,note=None,inst=None,vol=None,fx=None,fxp=None):
    a={"pattern":pat,"row":row,"channel":ch}
    if note is not None: a["note"]=note
    if inst is not None: a["instrument"]=inst
    if vol is not None: a["volume"]=vol
    if fx is not None: a["effect"]=fx
    if fxp is not None: a["effect_param"]=fxp
    call("pattern_set_cell", a)
def off(pat,row,ch):  # key-off WITHOUT instrument = hard stop in this build
    call("pattern_set_cell", {"pattern":pat,"row":row,"channel":ch,"note":97})

for p in range(8):
    call("pattern_set_length", {"pattern":p,"rows":64})
for pos,pat in enumerate([0,1,2,3,4,5,6,7]):
    call("order_set", {"position":pos,"pattern":pat})
call("song_set", {"length":8,"loop_start":0})

CHORDS={
 0: [("Am",45,[57,60,64]),("Am",45,[57,60,64]),("F",41,[53,57,60]),("G",43,[55,59,62])],
 1: [("Am",45,[57,60,64]),("Am",45,[57,60,64]),("F",41,[53,57,60]),("G",43,[55,59,62])],
 2: [("Am",45,[57,60,64]),("F",41,[53,57,60]),("C",48,[60,64,67]),("G",43,[55,59,62])],
 3: [("Am",45,[57,60,64]),("F",41,[53,57,60]),("C",48,[60,64,67]),("G",43,[55,59,62])],
 4: [("Am",45,[57,60,64]),("F",41,[53,57,60]),("C",48,[60,64,67]),("E",52,[52,56,59])],
 5: [("Am",45,[57,60,64]),("Am",45,[57,60,64]),("F",41,[53,57,60]),("E",52,[52,56,59])],
 6: [("Am",45,[57,60,64]),("F",41,[53,57,60]),("C",48,[60,64,67]),("G",43,[55,59,62])],
 7: [("Am",45,[57,60,64]),("Am",45,[57,60,64]),("F",41,[53,57,60]),("G",43,[55,59,62])],
}
LEAD_EV={
 0: [],
 1: [(32,76),(34,79),(36,81),(38,79),(40,76),(42,74),(44,76),(46,79),
     (48,81),(50,83),(52,84),(54,83),(56,81),(58,79),(60,81),(62,79)],
 2: [(0,76),(2,76),(4,79),(6,76),(8,81),(10,79),(12,76),(14,74),
     (16,77),(18,77),(20,81),(22,77),(24,81),(26,79),(28,77),(30,76),
     (32,79),(34,79),(36,81),(38,79),(40,76),(42,74),(44,76),(46,79),
     (48,81),(50,79),(52,77),(54,76),(56,74),(58,76),(60,74),(62,71)],
 3: [(0,81),(2,79),(4,76),(6,79),(8,81),(10,79),(12,84),(14,83),
     (16,81),(18,79),(20,77),(22,76),(24,77),(26,76),(28,74),(30,76),
     (32,76),(34,79),(36,84),(38,83),(40,81),(42,79),(44,76),(46,74),
     (48,76),(50,74),(52,72),(54,74),(56,76),(58,74),(60,71),(62,72)],
 4: [(0,76),(2,76),(4,79),(6,76),(8,81),(10,79),(12,76),(14,74),
     (16,77),(18,77),(20,81),(22,77),(24,81),(26,79),(28,77),(30,76),
     (32,79),(34,81),(36,83),(38,84),(40,83),(42,81),(44,79),(46,81),
     (48,80),(50,81),(52,83),(54,84),(56,83),(58,81),(60,80),(62,81)],
 5: [(32,69),(34,72),(36,76),(38,72),(40,74),(42,71),(44,69),(46,67),
     (48,64),(50,67),(52,69),(54,71),(56,72),(58,71),(60,69),(62,67)],
 6: [(0,76),(2,76),(4,79),(6,76),(8,81),(10,79),(12,76),(14,74),
     (16,77),(18,77),(20,81),(22,77),(24,84),(26,81),(28,79),(30,77),
     (32,88),(34,86),(36,84),(38,81),(40,79),(42,81),(44,84),(46,81),
     (48,83),(50,84),(52,83),(54,81),(56,79),(58,81),(60,83),(62,81)],
 7: [],
}

def arp_notes(chord):
    tones=chord[2]
    return [tones[i%3]+(12 if (i//3)%2==1 else 0) for i in range(16)]
def bass_notes(root):
    out=[None]*16
    for i in range(0,16,2):
        out[i]= root+12 if (i//2)%4==3 else root
        if i==14: out[i+1]=root+12
    return out

def write_drums_and_harmony(pat, kind):
    """kind: 'intro' (==outro), 'grow', 'main', 'break'"""
    chords=CHORDS[pat]
    for bar in range(4):
        chord=chords[bar]; root=chord[1]; tones=chord[2]
        an=arp_notes(chord); bn=bass_notes(root); base=bar*16
        for i in range(16):
            row=base+i
            if kind!="break":
                cell(pat,row,5, nm(an[i]), 3, 40 if kind=="intro" else 44)
            cell(pat,row,2, nm(bn[i]) if bn[i] is not None else None, 2, 44 if kind in ("intro","break") else 52) if bn[i] is not None else None
            if i==0:
                cell(pat,row,4, nm(tones[1]), 4, 34 if kind in ("intro","break") else 30)
            # kick
            if kind=="main":
                if i%4==0: cell(pat,row,6, nm(48), 5, 64)
            elif kind in ("intro",):
                if bar>=2 and i%4==0 and row<=56: cell(pat,row,6, nm(48), 5, 56)
            elif kind=="grow":
                if bar>=2 and i%4==0: cell(pat,row,6, nm(48), 5, 60)
            elif kind=="break":
                if bar==3 and i in (0,8): cell(pat,row,6, nm(48), 5, 56)
            # snare
            if kind=="main":
                if i in (4,12): cell(pat,row,7, nm(48), 6, 56)
            elif kind=="grow":
                if bar>=2 and i in (4,12): cell(pat,row,7, nm(48), 6, 50)
            # hats ch3
            if kind=="intro":
                if bar>=2 and i%4==2: cell(pat,row,3, nm(72), 7, 30)
            elif kind in ("main","grow"):
                if i%2==0: cell(pat,row,3, nm(72), 7, 30 if i%4==0 else 38)
                elif pat in (2,3,4,6) and i%2==1 and bar in (1,3): cell(pat,row,3, nm(72), 7, 20)
            elif kind=="break":
                if i%4==2: cell(pat,row,3, nm(72), 7, 28)

# intro/outro identical content written to pat0 AND pat7 (loop seam = pattern repeat)
write_drums_and_harmony(0,"intro")
write_drums_and_harmony(7,"intro")
write_drums_and_harmony(1,"grow")
for p in (2,3,4,6): write_drums_and_harmony(p,"main")
write_drums_and_harmony(5,"break")

# crashes: phrase accents; pat7 none (seam), pat0 none (seam)
for p in (1,2,3,4,6):
    cell(p,0,1, nm(72), 8, 40)
cell(5,32,1, nm(72), 8, 30)   # break motif entry shimmer
cell(4,48,1, nm(72), 8, 34)   # E-lift accent

# snare fills into break and into outro
for r,m in [(56,48),(58,48),(60,48),(62,48)]:
    cell(4,r,7, nm(m), 6, 60)
    cell(6,r,7, nm(m), 6, 60)
# extra kick under fills
for r in (56,60,62):
    cell(4,r,6, nm(48), 5, 60)
    cell(6,r,6, nm(48), 5, 60)

# leads with vibrato
for pat,ev in LEAD_EV.items():
    for (row,m) in ev:
        cell(pat,row,0, nm(m), 1, 58, 4, 0x37)

# echo sparkle on ch1 (skip near crash rows and last 2 rows so tails can be cut)
for pat in (1,2,3,4,6):
    evrows={r for (r,m) in LEAD_EV[pat]}
    for (row,m) in LEAD_EV[pat]:
        er=row+3
        if er<=61 and er not in evrows and er>=4:
            cell(pat,er,1, nm(m), 1, 22)

# releases: cut lead ring where next pattern starts with rest; cut echo tails
off(4,63,0)   # pat4 -> break (rest until row32)
off(6,63,0); off(6,63,1)  # final -> outro
off(4,63,1)   # echo tail before break
off(5,63,0)   # break motif -> final downbeat retrig anyway; keep ring short: cut at 63, final retrigs row0
# (pat5->pat6: pat6 row0 retrigs ch0, so off(5,63,0) only removes 1 row of ring — keeps it tight)

call("module_save", {"path":"/workspace/src/final.xm","format":"xm"})
print(call("module_render", {"path":"/workspace/src/final.wav","rate":44100,"bits":16}))
print("info", xm_info("/workspace/src/final.xm"))
