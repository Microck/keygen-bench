import sys; sys.path.insert(0,'/workspace/src')
from loadins import load_calls, run
import numpy as np

# ---- instrument ids ----
BD,SD,SG,CP,HC,HO,CY,TM,RI,SW = 1,2,3,4,5,6,7,8,9,10
BASS,SUB = 11,12
ARPL,ARPR = 13,14
LEDL,LEDR = 15,16
PADL,PADR = 17,18
PLK = 19
STBL,STBR = 20,21

# ---- channels ----
C_KICK,C_SNR,C_HAT,C_PRC,C_FX,C_BAS,C_SUB = 0,1,2,3,4,5,6
C_ARL,C_ARR,C_LDL,C_LDR,C_PDL,C_PDR,C_PLK,C_STL,C_STR = 7,8,9,10,11,12,13,14,15
C_ECL,C_ECR = 16,17
NCH = 18

SONG_NAME = 'neon cascade - keygen'
BPM   = 142
SPEED = 6
ROWS  = 64
CELLS = {}          # (pat,row,ch) -> dict
PATS  = set()

def put(p,r,ch,**kw):
    if r >= ROWS: return
    PATS.add(p)
    c = CELLS.setdefault((p,r,ch), {})
    c.update(kw)

def note(p,r,ch,midi,ins,vol=None,eff=None,par=None):
    n = int(midi)+1
    if not (1 <= n <= 96): return
    kw = dict(note=n, instrument=ins)
    if vol is not None: kw['volume'] = vol
    if eff is not None: kw['effect'] = eff; kw['effect_param'] = par or 0
    put(p,r,ch,**kw)

def off(p,r,ch):
    put(p,r,ch,note=97)

def fx(p,r,ch,eff,par):
    put(p,r,ch,effect=eff,effect_param=par)

def vcol(p,r,ch,v):
    put(p,r,ch,volume=v)

# ---- harmony ----
# chord: (name, bass_root_midi, [chord tone pitch classes ascending from root])
CH = {
 'Dm': dict(bass=38, root=50, ints=[0,3,7,12]),
 'Bb': dict(bass=34, root=46, ints=[0,4,7,12]),
 'F' : dict(bass=41, root=41, ints=[0,4,7,12]),
 'C' : dict(bass=36, root=48, ints=[0,4,7,12]),
 'Gm': dict(bass=43, root=43, ints=[0,3,7,12]),
 'Am': dict(bass=33, root=45, ints=[0,3,7,12]),
}
PROG_A = ['Dm','Bb','F','C']
PROG_B = ['Bb','F','C','Dm']
PROG_C = ['Gm','Dm','Bb','C']
PROG_E = ['Bb','F','C','C']      # turnaround into loop

def tones(cname, lo, hi):
    """all chord tones inside [lo,hi] midi, ascending"""
    d = CH[cname]; out=[]
    for oc in range(-3,5):
        for iv in d['ints'][:3]:
            m = d['root']+iv+12*oc
            if lo <= m <= hi: out.append(m)
    return sorted(set(out))

SCALE = [0,2,3,5,7,8,10]   # D natural minor relative to D
def scale_note(deg, base=62):
    """deg 0 = base (D), moves through D-minor scale"""
    o,i = divmod(deg,7)
    return base + 12*o + SCALE[i]

# ============================= DRUM PARTS =============================
def drums(p, kind, bars=range(4)):
    for b in bars:
        B = b*16
        if kind in ('full','fullA','fullB','big','ghost'):
            for r in (0,4,8,12): note(p,B+r,C_KICK,48,BD,0x48)
            if kind=='big' and b%2==1: note(p,B+14,C_KICK,48,BD,0x40)
            note(p,B+4,C_SNR,48,CP,0x3C); note(p,B+12,C_SNR,48,CP,0x3C)
            note(p,B+4,C_PRC,48,SD,0x34); note(p,B+12,C_PRC,48,SD,0x34)
            for r in (2,6,10,14):
                note(p,B+r,C_HAT,48,HC,0x36 if r in (2,10) else 0x3C)
            for r in (1,5,9,13):
                note(p,B+r,C_HAT,48,HC,0x24)
            if b in (1,3): note(p,B+14,C_HAT,48,HO,0x34)
            if kind=='ghost':
                for r in (7,15,23): note(p,B+r,C_PRC,48,SG,0x22)
        elif kind=='half':
            for r in (0,8): note(p,B+r,C_KICK,48,BD,0x44)
            note(p,B+12,C_SNR,48,CP,0x36)
            for r in (2,6,10,14): note(p,B+r,C_HAT,48,HC,0x26)
        elif kind=='light':
            note(p,B+0,C_KICK,48,BD,0x40)
            for r in (4,12): note(p,B+r,C_HAT,48,HC,0x22)
            for r in (2,6,10,14): note(p,B+r,C_HAT,48,HC,0x1A)
        elif kind=='four':
            for r in (0,4,8,12): note(p,B+r,C_KICK,48,BD,0x46)
            for r in (2,6,10,14): note(p,B+r,C_HAT,48,HC,0x28)
        elif kind=='hats':
            for r in (0,2,4,6,8,10,12,14): note(p,B+r,C_HAT,48,HC,0x1C+b*3)

def fill(p, start, kind='snare'):
    """drum fill occupying rows start..63"""
    if kind=='snare':
        rows = list(range(start,ROWS))
        for i,r in enumerate(rows):
            v = 0x1C + int(0x24*i/max(1,len(rows)-1))
            note(p,r,C_PRC,48,SG,v)
        note(p,ROWS-1,C_SNR,48,SD,0x44)
    elif kind=='tom':
        seq=[(0,45),(2,45),(4,41),(6,41),(8,38),(10,38),(12,36),(13,36),(14,33),(15,33)]
        for o,m in seq:
            r=start+o
            if r<ROWS: note(p,r,C_PRC,m,TM,0x40)
    elif kind=='roll':
        r=start; step=8
        while r<ROWS:
            for k in range(step):
                if r+k<ROWS: note(p,r+k,C_PRC,48,SG,0x20+k*2)
            r+=step; step=max(2,step//2)

# ============================= BASS =============================
BGROOVE = [(0,0,0x44),(2,0,0x36),(3,12,0x3A),(4,0,0x3E),(6,0,0x34),(7,7,0x3A),
           (8,0,0x44),(10,0,0x36),(11,12,0x3A),(12,0,0x3E),(14,0,0x34),(15,7,0x3C)]
BSIMPLE= [(0,0,0x46),(4,0,0x3C),(6,12,0x38),(8,0,0x44),(12,0,0x3C),(14,7,0x38)]
BDRIVE = [(r,(12 if r%8==7 else 0),0x40 if r%4==0 else 0x34) for r in range(0,16)]

def bass(p, prog, style='groove', sub=True, cut=None):
    G = {'groove':BGROOVE,'simple':BSIMPLE,'drive':BDRIVE}[style]
    for b,cn in enumerate(prog):
        B=b*16; root=CH[cn]['bass']
        for (r,iv,v) in G:
            e,pa = (0x0E,0xC0|cut) if cut else (None,None)
            note(p,B+r,C_BAS,root+iv,BASS,v,e,pa)
        if sub:
            note(p,B+0,C_SUB,root,SUB,0x2A)
            note(p,B+8,C_SUB,root,SUB,0x24)

# ============================= ARP =============================
ARP_PAT = [0,1,2,3,2,1]
def arp(p, prog, lo=62, hi=90, vol=0x34, pat=None, step=1, skew=2):
    """skew = how many steps the right-hand voice lags, giving a stereo canon."""
    pat = pat or ARP_PAT
    for b,cn in enumerate(prog):
        B=b*16
        t = tones(cn, lo, hi)
        if not t: continue
        for k in range(0,16,step):
            i = k//step
            mL = t[pat[i % len(pat)] % len(t)]
            mR = t[pat[(i+skew) % len(pat)] % len(t)]
            v = vol + (6 if k%4==0 else 0)
            note(p,B+k,C_ARL,mL,ARPL,v)
            note(p,B+k,C_ARR,mR,ARPR,v-2)

# ============================= PAD =============================
def pad(p, prog, vol=0x26, lowoct=0, vib=True):
    for b,cn in enumerate(prog):
        B=b*16; d=CH[cn]
        lo = d['root']+12*lowoct
        hi = d['root']+d['ints'][2]+12*lowoct
        note(p,B,C_PDL,lo,PADL,vol)
        note(p,B,C_PDR,hi,PADR,vol)
        if vib:
            fx(p,B+4,C_PDL,4,0x23); fx(p,B+4,C_PDR,4,0x23)

def stab(p, prog, rows=(0,6,10), vol=0x30, oct=0):
    for b,cn in enumerate(prog):
        B=b*16; d=CH[cn]
        a=d['root']+12*oct; c=d['root']+d['ints'][1]+12*oct; e=d['root']+d['ints'][2]+12*oct
        for r in rows:
            note(p,B+r,C_STL,a,STBL,vol)
            note(p,B+r,C_STR,e,STBR,vol)
            if r==rows[0]: note(p,B+r,C_PLK,c,PLK,vol)

# ============================= LEAD =============================
def lead(p, mel, vol=0x38, harm=None, vib=0x34, det=0, echo=3):
    """mel: list of (row, midi, dur_rows).  echo = delay in rows (0 = none)"""
    for (r,m,dur) in mel:
        note(p,r,C_LDL,m+det,LEDL,vol)
        note(p,r,C_LDR,m+det,LEDR,vol)
        if dur>=6:
            fx(p,r+4,C_LDL,4,vib); fx(p,r+4,C_LDR,4,vib)
        if harm is not None:
            note(p,r,C_STL,m+harm,STBL,vol-0x14)
            note(p,r,C_STR,m+harm,STBR,vol-0x14)
        if echo:
            # two taps, swapped across the stereo field, each quieter.
            # skip a tap if a new melody note starts on that row.
            starts = {x[0] for x in mel}
            if r+echo not in starts:
                note(p,r+echo,   C_ECR, m+det, LEDR, max(0x0E, vol-0x1E))
            if r+2*echo not in starts:
                note(p,r+2*echo, C_ECL, m+det, LEDL, max(0x0A, vol-0x2C))
    # release last
def leadcut(p, mel):
    for (r,m,dur) in mel:
        e=r+dur
        if e<ROWS:
            nxt=[x for x in mel if x[0]==e]
            if not nxt: off(p,e,C_LDL); off(p,e,C_LDR)

MEL_A = [(0,74,2),(2,74,2),(4,77,2),(6,74,2),(8,72,4),(12,74,4),
         (16,70,2),(18,70,2),(20,74,2),(22,70,2),(24,69,4),(28,70,4),
         (32,72,2),(34,72,2),(36,77,2),(38,76,2),(40,74,4),(44,72,4),
         (48,79,2),(50,76,2),(52,74,2),(54,72,2),(56,74,8)]
MEL_A2= [(0,74,2),(2,74,2),(4,77,2),(6,81,2),(8,79,4),(12,77,4),
         (16,77,2),(18,77,2),(20,74,2),(22,70,2),(24,69,6),(30,70,2),
         (32,72,2),(34,74,2),(36,77,2),(38,79,2),(40,81,6),(46,79,2),
         (48,79,2),(50,77,2),(52,76,2),(54,74,2),(56,72,8)]
HOOK1 = [(0,74,6),(6,72,2),(8,70,6),(14,69,2),
         (16,69,6),(22,70,2),(24,72,8),
         (32,74,4),(36,76,4),(40,79,8),
         (48,77,4),(52,74,12)]
HOOK2 = [(0,77,6),(6,76,2),(8,74,6),(14,72,2),
         (16,72,6),(22,74,2),(24,76,8),
         (32,76,4),(36,79,4),(40,81,8),
         (48,79,4),(52,77,4),(56,74,8)]
HOOK3 = [(0,81,6),(6,79,2),(8,77,6),(14,76,2),
         (16,77,6),(22,76,2),(24,74,8),
         (32,76,4),(36,79,4),(40,81,8),
         (48,77,4),(52,74,12)]
HOOK4 = [(0,74,4),(4,77,4),(8,81,6),(14,79,2),
         (16,77,4),(20,74,4),(24,72,8),
         (32,74,4),(36,76,4),(40,79,4),(44,81,4),
         (48,81,8),(56,86,8)]

def solo_mel():
    """16th-note run built from the D-minor scale, phrased"""
    degs = [7,8,9,10,9,8,7,6, 5,6,7,8,7,6,5,4,
            3,4,5,6,7,8,9,10, 11,10,9,8,7,6,5,6,
            7,9,8,10,9,11,10,12, 11,10,9,8,7,8,9,10,
            11,12,11,10,9,8,7,8, 9,10,11,12,13,12,11,14]
    out=[]
    for i,d in enumerate(degs):
        out.append((i, scale_note(d,62), 1))
    return out

# ============================= PATTERNS =============================
def build_patterns():
    # --- 0: intro pad ---
    p=0
    pad(p,PROG_A,0x2A,lowoct=0)
    for b,cn in enumerate(PROG_A):
        t=tones(cn,62,86); B=b*16
        for i,r in enumerate((0,6,10)):
            note(p,B+r,C_PLK,t[min(i,len(t)-1)],PLK,0x2C-i*4)
    note(p,0,C_PRC,48,CY,0x34)
    note(p,48,C_FX,48,RI,0x30)

    # --- 1: intro + arp ---
    p=1
    pad(p,PROG_A,0x28)
    arp(p,PROG_A,62,86,0x2C,step=2)
    drums(p,'light')
    for b,cn in enumerate(PROG_A):
        note(p,b*16,C_SUB,CH[cn]['bass'],SUB,0x2E)
    note(p,56,C_FX,48,RI,0x36)

    # --- 2: build ---
    p=2
    pad(p,PROG_A,0x24)
    arp(p,PROG_A,62,90,0x32)
    bass(p,PROG_A,'simple',sub=True)
    drums(p,'four')
    fill(p,56,'snare')
    note(p,32,C_FX,48,RI,0x40)

    # --- 3: groove A1 ---
    p=3
    note(p,0,C_PRC,48,CY,0x36)
    drums(p,'full'); bass(p,PROG_A,'groove')
    arp(p,PROG_A,62,90,0x33)
    pad(p,PROG_A,0x20)

    # --- 4: groove A2 + lead ---
    p=4
    drums(p,'full'); bass(p,PROG_A,'groove')
    arp(p,PROG_A,57,79,0x2C)
    pad(p,PROG_A,0x18)
    lead(p,MEL_A,0x3C); leadcut(p,MEL_A)

    # --- 5: chorus B1 ---
    p=5
    note(p,0,C_PRC,48,CY,0x38)
    drums(p,'fullB'); bass(p,PROG_B,'groove')
    arp(p,PROG_B,57,79,0x2C)
    pad(p,PROG_B,0x1A)
    stab(p,PROG_B,(0,),0x20,oct=0)
    lead(p,HOOK1,0x40); leadcut(p,HOOK1)

    # --- 6: chorus B2 ---
    p=6
    drums(p,'fullB'); bass(p,PROG_B,'groove')
    arp(p,PROG_B,57,79,0x2C)
    pad(p,PROG_B,0x1A)
    stab(p,PROG_B,(0,),0x20)
    lead(p,HOOK2,0x40); leadcut(p,HOOK2)
    fill(p,60,'snare')

    # --- 7: break ---
    p=7
    pad(p,PROG_C,0x1E)
    for b,cn in enumerate(PROG_C):
        t=tones(cn,62,86); B=b*16
        for i,r in enumerate((0,4,7,10,13)):
            note(p,B+r,C_PLK,t[i%len(t)],PLK,0x28-i*3)
    drums(p,'half')
    for b,cn in enumerate(PROG_C):
        note(p,b*16,C_SUB,CH[cn]['bass'],SUB,0x26)
    note(p,0,C_PRC,48,CY,0x30)
    note(p,0,C_FX,48,SW,0x34)

    # --- 8: build 2 ---
    p=8
    pad(p,PROG_C,0x26)
    arp(p,PROG_C,62,90,0x24)
    for b in range(4):
        for k in range(0,16,2):
            v=0x24+int((b*16+k)*0x14/64)
            vcol(p,b*16+k,C_ARL,v); vcol(p,b*16+k,C_ARR,max(0x10,v-2))
    bass(p,PROG_C,'simple')
    drums(p,'four')
    note(p,16,C_FX,48,RI,0x42)
    fill(p,48,'roll')

    # --- 9: groove A3 + counter ---
    p=9
    note(p,0,C_PRC,48,CY,0x36)
    drums(p,'ghost'); bass(p,PROG_A,'drive')
    arp(p,PROG_A,57,79,0x2C)
    pad(p,PROG_A,0x1A)
    stab(p,PROG_A,(0,6,10),0x1A)
    lead(p,MEL_A2,0x3C); leadcut(p,MEL_A2)

    # --- 10: chorus B3 (harmonised) ---
    p=10
    note(p,0,C_PRC,48,CY,0x38)
    drums(p,'big'); bass(p,PROG_B,'groove')
    arp(p,PROG_B,57,79,0x2C)
    pad(p,PROG_B,0x1A)
    lead(p,HOOK3,0x40,harm=-5); leadcut(p,HOOK3)

    # --- 11: chorus B4 final -> loop ---
    p=11
    drums(p,'big'); bass(p,PROG_E,'groove')
    arp(p,PROG_E,57,79,0x2C)
    pad(p,PROG_E,0x1A)
    lead(p,HOOK4,0x42,harm=-5); leadcut(p,HOOK4)
    fill(p,56,'tom')
    # voices that pattern 3 does NOT retrigger must be silenced before the wrap,
    # with a 2-row fade so the seam has no step discontinuity
    for ch in (C_LDL,C_LDR,C_STL,C_STR,C_PLK,C_FX,C_ECL,C_ECR):
        fx(p,62,ch,0x0A,0x0A); fx(p,63,ch,0x0A,0x0A); off(p,63,ch)

    # --- 12: bridge ---
    p=12
    note(p,0,C_FX,48,SW,0x30)
    pad(p,PROG_C,0x22)
    drums(p,'half')
    bass(p,PROG_C,'simple',sub=True)
    for b,cn in enumerate(PROG_C):
        t=tones(cn,62,86); B=b*16
        for i,r in enumerate((0,6,11)):
            note(p,B+r,C_PLK,t[(i*2)%len(t)],PLK,0x22-(i%3)*3)
    m=[(0,69,4),(4,70,4),(8,74,8),(16,69,8),(24,67,8),
       (32,70,4),(36,72,4),(40,74,8),(48,72,4),(52,70,4),(56,69,8)]
    lead(p,m,0x3E,echo=4); leadcut(p,m)

    # --- 13: groove A4 (ghosts + toms) ---
    p=13
    drums(p,'ghost'); bass(p,PROG_A,'groove')
    arp(p,PROG_A,62,90,0x33,pat=[0,2,1,3,2,0,3,1])
    pad(p,PROG_A,0x20)
    stab(p,PROG_A,(2,10),0x22)
    fill(p,60,'snare')

    # --- 14: solo ---
    p=14
    drums(p,'fullB'); bass(p,PROG_B,'drive')
    pad(p,PROG_B,0x16)
    sm=solo_mel()
    for (r,m,d) in sm:
        note(p,r,C_LDL,m,LEDL,0x42)
        note(p,r,C_LDR,m,LEDR,0x42)
        if r % 4 == 0:
            note(p,r+3,C_ECR,m,LEDR,0x1C)
            note(p,r+6,C_ECL,m,LEDL,0x12)
    note(p,0,C_PRC,48,CY,0x30)

def build_order():
    return [0,1,2, 3,4,5,6, 7,8, 9,13, 10,5, 12,14, 3,9, 10,11], 3

def emit():
    build_patterns()
    order, loopstart = build_order()
    C, ins = load_calls(NCH, SONG_NAME)
    npat = max(PATS)+1
    C.append({"name":"song_set","arguments":{"bpm":BPM,"speed":SPEED,
              "length":len(order),"loop_start":loopstart}})
    for p in range(npat):
        C.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":ROWS}})
    for i,p in enumerate(order):
        C.append({"name":"order_set","arguments":{"position":i,"pattern":p}})
    for (p,r,ch),kw in sorted(CELLS.items()):
        a = dict(pattern=p,row=r,channel=ch); a.update(kw)
        C.append({"name":"pattern_set_cell","arguments":a})
    return C, order, npat

def emit_seamtest():
    import copy
    build_patterns()
    order, loopstart = build_order()
    order = order + order[loopstart:loopstart+2]
    C, ins = load_calls(NCH, "seamtest")
    npat = max(PATS)+1
    C.append({"name":"song_set","arguments":{"bpm":142,"speed":6,"length":len(order),"loop_start":loopstart}})
    for p in range(npat):
        C.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":ROWS}})
    for i,p in enumerate(order):
        C.append({"name":"order_set","arguments":{"position":i,"pattern":p}})
    for (p,r,ch),kw in sorted(CELLS.items()):
        a = dict(pattern=p,row=r,channel=ch); a.update(kw)
        C.append({"name":"pattern_set_cell","arguments":a})
    return C, order

if __name__ == '__main__':
    C, order, npat = emit()
    C.append({"name":"module_save","arguments":{"path":"/workspace/build/tune.xm","format":"xm"}})
    C.append({"name":"module_render","arguments":{"path":"/workspace/build/tune.wav","rate":44100,"bits":16,"loops":0}})
    print("patterns",npat,"order",len(order),"cells",len(CELLS))
    r=run(C,'/workspace/build/song.json')
    print([l for l in r.stdout.splitlines() if 'duration' in l])
