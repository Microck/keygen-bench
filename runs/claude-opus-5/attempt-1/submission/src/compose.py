import sys
sys.path.insert(0,'/workspace')
from song import *

BAR = 16
# ---------------- chord tables ----------------
# (root pitch-class name, quality)
PROG_A = [('A','min'),('F','maj'),('C','maj'),('G','maj')]
PROG_B = [('D','min'),('A','min'),('F','maj'),('E','maj')]
IV = {'min':[0,3,7,12,15,19,24],'maj':[0,4,7,12,16,19,24]}
STAB = {'min':I_STABMIN,'maj':I_STABMAJ}
PAD  = {'min':I_PADMIN ,'maj':I_PADMAJ }
# bass root (octave 2) ; arp root (octave 3) ; pad root (octave 3/4)
BROOT = {'A':N('A2'),'F':N('F2'),'C':N('C2'),'G':N('G2'),'D':N('D2'),'E':N('E2')}
AROOT = {'A':N('A3'),'F':N('F3'),'C':N('C4'),'G':N('G3'),'D':N('D3'),'E':N('E3')}
PROOT = {'A':N('A3'),'F':N('F3'),'C':N('C4'),'G':N('G3'),'D':N('D3'),'E':N('E3')}
SROOT = {'A':N('A3'),'F':N('F3'),'C':N('C4'),'G':N('G3'),'D':N('D3'),'E':N('E3')}

# ---------------- drums ----------------
def drums(p, style, bars=4, fill=None, hatvol=56, start_bar=0):
    for bar in range(start_bar, start_bar+bars):
        b = bar*BAR
        last = (bar==start_bar+bars-1)
        if style in ('full','fullA','fullB'):
            for r in (0,4,8,12): p.set(b+r,CH_KICK,'C4',I_KICK,64)
            if style!='fullA' and bar%2==1: p.set(b+14,CH_KICK,'C4',I_KICK,46)
            p.set(b+4,CH_SNR,'C4',I_CLAP,60); p.set(b+12,CH_SNR,'C4',I_SNR,62)
            if style=='fullB': p.set(b+10,CH_SNR,'C4',I_CLAP,34)
        elif style=='half':
            for r in (0,8): p.set(b+r,CH_KICK,'C4',I_KICK,64)
            p.set(b+8,CH_SNR,'C4',I_CLAP,56)
        elif style=='kicks':
            for r in (0,8): p.set(b+r,CH_KICK,'C4',I_KICK,60)
        elif style=='intro':
            if bar>=2:
                for r in (0,8): p.set(b+r,CH_KICK,'C4',I_KICK,60)
        elif style=='build':
            for r in (0,4,8,12): p.set(b+r,CH_KICK,'C4',I_KICK,64)
        if style in ('full','fullA','fullB','half','intro','build','hats','kicks'):
            for r in range(0,16,2):
                v = hatvol if r%4==2 else hatvol-14
                if r==14 and bar%2==1 and style.startswith('full'):
                    p.set(b+r,CH_HAT,'C4',I_HHO,hatvol+4,fx=8,fxp=138)
                else:
                    p.set(b+r,CH_HAT,'C4',I_HHC,v,fx=8,fxp=112 if (r//2)%2==0 else 168)
            if style.startswith('full'):
                for r in range(1,16,2):
                    if r!=15: p.set(b+r,CH_HAT,'C4',I_HHC,22,fx=8,fxp=86 if (r//2)%2==0 else 190)
    END=(start_bar+bars)*BAR
    if fill=='snare':
        for i,r in enumerate(range(END-8, END)):
            p.set(r,CH_SNR,'C4',I_SNR,30+i*4)
        p.set(END-8,CH_KICK,'C4',I_KICK,64)
    elif fill=='tom':
        seq=[('C4',48),('A3',52),('G3',56),('E3',60)]
        for i,r in enumerate(range(END-8, END,2)):
            n,v = seq[i]; p.set(r,CH_PERC,n,I_TOM,v)
    elif fill=='clap':
        for i,r in enumerate([END-6,END-4,END-3,END-1]):
            p.set(r,CH_SNR,'C4',I_CLAP,44+i*5)

def crash(p,row=0,vol=58):
    p.set(row,CH_FX,'C4',I_CRASH,vol)

# ---------------- bass ----------------
def bass(p, prog, style='eighths', bars=4, vol=64, sub=True, start_bar=0):
    for bar in range(start_bar,start_bar+bars):
        b=bar*BAR; root,q = prog[bar%len(prog)]
        r0 = BROOT[root]
        if style=='eighths':
            pat=[(0,0,vol),(2,0,vol-14),(3,12,vol-20),(4,0,vol-4),(6,0,vol-14),(7,12,vol-20),
                 (8,0,vol),(10,0,vol-14),(11,12,vol-20),(12,0,vol-4),(14,0,vol-14),(15,12,vol-18)]
        elif style=='g332':
            pat=[(0,0,vol),(3,0,vol-8),(6,12,vol-14),(8,0,vol),(11,0,vol-8),(14,12,vol-14)]
        elif style=='drive':
            pat=[(0,0,vol),(2,12,vol-18),(4,0,vol-6),(6,12,vol-18),(8,0,vol),(10,12,vol-18),
                 (12,0,vol-6),(14,0,vol-10),(15,12,vol-16)]
        elif style=='long':
            pat=[(0,0,vol),(8,0,vol-6)]
        else:
            pat=[]
        for r,o,v in pat:
            p.set(b+r,CH_BASS,r0+o,I_BASS,v)
        if sub:
            sn = r0-12 if r0-12 >= 17 else r0
            p.set(b+0,CH_SUB,sn,I_SUB,60)
            if style!='long': p.set(b+8,CH_SUB,sn,I_SUB,50)

# ---------------- arp ----------------
ARPSEQ = [0,1,2,3,4,5,4,3]
def arp(p, prog, bars=4, vol=56, inst=I_PLUCK, seq=None, step=1, oct_off=0, start_bar=0):
    seq = seq or ARPSEQ
    for bar in range(start_bar,start_bar+bars):
        b=bar*BAR; root,q=prog[bar%len(prog)]
        base=AROOT[root]+oct_off
        for i in range(0,16,step):
            idx=seq[(i//step)%len(seq)]
            note=base+IV[q][idx]
            ch = CH_ARPL if ((i//step)%2==0) else CH_ARPR
            v = vol if (i%4==0 or i%4==3) else vol-12
            p.set(b+i,ch,note,inst,v)

# ---------------- stabs ----------------
def stabs(p, prog, bars=4, rows=(2,6,10,14), vol=56, oct_off=0, start_bar=0):
    for bar in range(start_bar,start_bar+bars):
        b=bar*BAR; root,q=prog[bar%len(prog)]
        for i,r in enumerate(rows):
            p.set(b+r,CH_STAB,SROOT[root]+oct_off,STAB[q],vol if i%2==0 else vol-8)

# ---------------- pad ----------------
def pad(p, prog, bars=4, vol=56, oct_off=0, fade=True, start_bar=0):
    for bar in range(start_bar,start_bar+bars):
        b=bar*BAR; root,q=prog[bar%len(prog)]
        p.set(b,CH_PAD,PROOT[root]+oct_off,PAD[q],vol)
        if fade: p.set(b+15,CH_PAD,fx=0x0A,fxp=0x0F)

# ---------------- melody ----------------
def melody(p, ch, inst, notes, vol=60, vib=0x23, fade=True, det=None):
    notes=sorted(notes)
    for i,(r,name,ln) in enumerate(notes):
        p.set(r,ch,name,inst,vol)
        if det is not None and i==0: pass
        nxt = notes[i+1][0] if i+1<len(notes) else 10**6
        end = r+ln
        if vib and ln>=3:
            for rr in range(r+2,min(end,p.rows)):
                if not p.has_fx(rr,ch): p.set(rr,ch,fx=4,fxp=vib)
        if fade and end<nxt:
            fr=max(r+1,end-1)
            p.set(fr,ch,fx=0x0A,fxp=0x0C)
            if end<p.rows: p.set(end,ch,note=97)
