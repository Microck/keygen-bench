import json, os, subprocess, numpy as np
W='/workspace/work/'; D=W+'samples/'
SR=22050
# ---------- instruments ----------
# name -> (file, loop_len, flags, volume, panning)
INST=[
 ('crash','crash.wav',0,0,64,150),('riser','riser.wav',0,0,64,120),('kick','kick.wav',0,0,64,128),('snare','snare.wav',0,0,64,128),('hat','hat.wav',0,0,64,150),
 ('ohat','ohat.wav',0,0,64,150),('tom','tom.wav',0,0,64,100),
 ('bass','bass.wav',159,1,64,128),('lead','lead.wav',159,1,64,128),('arp','arp.wav',159,1,64,96),
 ('pad','pad.wav',159,1,64,128),('bell','bell.wav',0,0,64,128),('pluck','pluck.wav',0,0,64,168),
 ('stab_am','stab_am.wav',0,0,64,128),('stab_f','stab_f.wav',0,0,64,128),
 ('stab_c','stab_c.wav',0,0,64,120),('stab_e','stab_e.wav',0,0,64,128),
]
IIDX={n[0]:i+1 for i,n in enumerate(INST)}
CH={'lead':0,'bell':1,'pad1':2,'pad2':3,'pad3':4,'bass':5,'arp':6,'drum':7,'hat':8,'stab':9}
NCH=10
ROWS=64
# ---------- harmony ----------
# chord: (bass_root, [pad notes], stab instrument)
CH_AM=(45,[57,60,64],'stab_am'); CH_F=(41,[53,57,60],'stab_f')
CH_C=(48,[52,55,60],'stab_c'); CH_E=(40,[52,56,59,64],'stab_e')
CH_DM=(50,[50,53,57],'stab_c'); CH_G=(43,[55,59,62],'stab_f')
def chord(nm):
    return {'Am':CH_AM,'F':CH_F,'C':CH_C,'E7':CH_E,'Dm':CH_DM,'G':CH_G}[nm]
# ---------- pattern container ----------
P=[]
def newpat(): P.append({}); return len(P)-1
PG=[0.70,0.85,1.00,1.00,1.00,1.00,0.72,0.90,1.02,1.02,1.05,1.00,1.00,0.72,0.90,1.05,0.80,1.00]
GLOBAL=0.70
def vmap(v,pg=1.0):
    # engine only honours note volumes 16..64 linearly (0-15 broken)
    v=max(0.0,min(1.0,v/64.0))*pg*GLOBAL
    return max(16,min(64,int(16+round(48*v))))
def put(p,row,ch,note,ins,vol=64,fx=None,par=None):
    if row<0 or row>=ROWS: return
    P[p][(row,ch)]=dict(note=note,instrument=ins,volume=vmap(vol,PG[p] if p<len(PG) else 1.0),effect=fx,effect_param=par)
def pat_chords(p,seq):
    """pad + bass roots per chord; seq=list of chord names, one per bar"""
    for b,nm in enumerate(seq):
        rt,padnotes,st=chord(nm)
        for i,pn in enumerate(padnotes[:3]):
            put(p,b*16,CH['pad%d'%(i+1)],pn,IIDX['pad'],40 if i==1 else 34)
        put(p,b*16,CH['stab'],60,IIDX[st],44)
# ---------- note helper: list of (row,note,dur,vol) ----------
def seq(p,ch,items,ins,vol=64,step=1):
    for it in items:
        r,n,d,v=(it+(vol,))[:4] if len(it)==4 else (it[0],it[1],it[2],vol)
        put(p,r,ch,n,ins,v)
# ---------- lead melodies (16th grid, rows within 4-bar pattern) ----------
LEAD_A=[  # (row,note,dur,vol)
 (0,69,3,60),(3,72,2,52),(5,71,2,54),(7,69,4,58),(11,64,2,50),(13,67,2,54),(15,69,1,56),
 (16,77,4,62),(20,76,2,54),(22,72,2,52),(24,69,4,58),(28,72,4,60),
 (32,67,2,54),(34,69,2,56),(36,72,4,62),(40,76,2,60),(42,74,2,54),(44,72,4,60),
 (48,71,2,58),(50,74,2,56),(52,68,6,60),(58,77,2,54),(60,76,4,62)]
LEAD_B=[  # higher / more driving variation
 (0,81,2,62),(2,80,2,56),(4,77,4,64),(8,76,2,56),(10,72,2,54),(12,76,4,62),
 (16,81,4,64),(20,79,2,56),(22,76,2,54),(24,77,4,60),(28,72,2,52),(30,69,2,56),
 (32,84,4,66),(36,81,2,58),(38,79,2,54),(40,76,4,62),(44,72,2,54),
 (48,80,2,60),(50,77,2,56),(52,76,4,64),(56,74,2,56),(58,71,2,54),(60,68,4,58)]
LEAD_C=[  # calmer, lower
 (0,64,6,52),(6,67,2,50),(8,69,6,58),(14,72,2,52),
 (16,69,8,56),(24,65,4,52),(28,64,4,50),
 (32,72,6,58),(38,76,2,54),(40,74,8,60),
 (48,71,4,56),(52,68,4,54),(56,64,8,54)]
LEAD_D=[  # fill / answer
 (0,76,2,60),(2,72,2,56),(4,69,6,58),(10,71,2,54),(12,72,4,60),
 (16,74,4,60),(20,76,4,62),(24,77,8,64),
 (32,72,2,56),(34,69,2,54),(36,71,4,58),(40,74,4,60),
 (48,77,4,64),(52,76,4,62),(56,74,8,58)]
# ---------- arpeggio generator ----------
def arp(p,seqc,mode='up',step=1,vol=32,ins=None):
    ins=ins or IIDX['arp']
    for b,nm in enumerate(seqc):
        rt,padnotes,_=chord(nm)
        tones=[x+12 for x in padnotes]+[padnotes[0]+24]
        for i in range(16):
            r=b*16+i
            if mode=='up': n=tones[[0,1,2,3,2,1][i%6]]
            elif mode=='down': n=tones[[3,2,1,0,1,2][i%6]]
            elif mode=='fast': n=tones[i%4] if i%4<3 else tones[0]+12
            else: n=tones[[0,2,1,3,2,1,0,1][i%8]]
            put(p,r,CH['arp'],n,ins,vol if i%4 else vol+8)
# ---------- drums ----------
def drums(p,style='main'):
    k=IIDX['kick']; s=IIDX['snare']; h=IIDX['hat']; o=IIDX['ohat']; tm=IIDX['tom']
    for b in range(4):
        o0=b*16
        if style=='full':
            for r in (0,6,8,14): put(p,o0+r,CH['drum'],60,k,60)
            for r in (4,12): put(p,o0+r,CH['drum'],60,s,58)
            for i in range(16): put(p,o0+i,CH['hat'],60,h,30 if i%4 else 40)
            put(p,o0+14,CH['hat'],60,o,30)
        elif style=='drive':
            for r in (0,3,6,8,11,14): put(p,o0+r,CH['drum'],60,k,58)
            for r in (4,12): put(p,o0+r,CH['drum'],60,s,60)
            for i in range(16): put(p,o0+i,CH['hat'],60,h,26 if i%2 else 38)
            put(p,o0+15,CH['hat'],60,o,30)
        elif style=='light':
            for r in (0,8): put(p,o0+r,CH['drum'],60,k,56)
            for r in (4,12): put(p,o0+r,CH['drum'],60,s,52)
            for i in range(0,16,2): put(p,o0+i,CH['hat'],60,h,26)
        elif style=='half':
            for r in (0,10): put(p,o0+r,CH['drum'],60,k,54)
            for r in (4,12): put(p,o0+r,CH['drum'],60,s,48)
            for i in range(0,16,4): put(p,o0+i,CH['hat'],60,h,24)
        elif style=='roll':
            for r in (12,13,14,15): put(p,o0+r,CH['drum'],60,s,30+r*10)
            for r in (0,8): put(p,o0+r,CH['drum'],60,k,50)
def echo(p,items,ins,shift=12,row0=2,vol=26,dur_keep=None):
    for it in items:
        r,n,d,v=(it+(0,))[:4]
        put(p,r+row0,CH['bell'],n+shift,ins,vol)
def fill(p,at=48,style='snare'):
    for i,r in enumerate(range(at,64)):
        d=i+1
        if style=='snare':
            put(p,r,CH['drum'],60,IIDX['snare'],28+d*5)
            if d>=3: put(p,r,CH['hat'],60,IIDX['hat'],22+d*4)
        else:
            put(p,r,CH['drum'],60,IIDX['tom'] if d%2 else IIDX['snare'],26+d*5)
    put(p,63,CH['drum'],60,IIDX['snare'],64)
def crashat(p,row,vol=64): put(p,row,CH['hat'],60,IIDX['crash'],vol)
def riserat(p,row,vol=64): put(p,row,CH['hat'],60,IIDX['riser'],vol)
# ---------- bass generator ----------
def bass(p,seqc,style='drive',vol=52):
    bi=IIDX['bass']
    for b,nm in enumerate(seqc):
        rt,_,_=chord(nm)
        o0=b*16
        if style=='drive':
            pat=[(0,0),(2,0),(3,12),(4,0),(6,0),(8,0),(10,12),(11,0),(12,0),(14,12),(15,0)]
            for r,o in pat: put(p,o0+r,CH['bass'],rt+o,bi,vol)
        elif style=='off':
            pat=[(0,0),(3,0),(4,12),(6,0),(8,0),(10,0),(11,12),(12,0),(14,0)]
            for r,o in pat: put(p,o0+r,CH['bass'],rt+o,bi,vol-4)
        elif style=='root':
            put(p,o0,CH['bass'],rt,bi,vol); put(p,o0+6,CH['bass'],rt,bi,vol-8)
            put(p,o0+8,CH['bass'],rt,bi,vol); put(p,o0+14,CH['bass'],rt+12,bi,vol-10)
        elif style=='walk':
            pat=[(0,0),(2,0),(4,0),(6,7),(8,0),(10,12),(12,0),(14,7)]
            for r,o in pat: put(p,o0+r,CH['bass'],rt+o,bi,vol)
# ---------- arrangement ----------
MAIN=['Am','F','C','E7']
DRV=['Am','F','Dm','E7']
BRK=['F','C','Dm','E7']
def build():
    # P0 intro: pad + arp  (opens on Am so the loop's last chord resolves into it)
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'soft',vol=24); bass(p,MAIN,'root',vol=34)
    # keep the very first row sparse so the loop point breathes
    for (rr,cc),cc2 in list(P[-1].items()):
        if rr<4 and cc2['volume']>18: P[-1][(rr,cc)]['volume']=16
    for b in range(4): put(p,b*16+8,CH['stab'],60,IIDX[chord(MAIN[b])[2]],28)
    # P1 intro b: add bells + light drums
    p=newpat(); pat_chords(p,BRK); arp(p,BRK,'wide',vol=30); bass(p,BRK,'root',vol=40)
    drums(p,'half')
    seq(p,CH['bell'],[(0,76,6,44),(6,72,4,40),(8,74,8,46),(20,69,6,42),(24,71,8,44),
                      (32,72,6,46),(38,76,4,44),(40,77,8,48),(52,72,8,44)],IIDX['bell'])
    # P2..P5 main theme
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'up',vol=38); bass(p,MAIN,'drive'); drums(p,'full'); seq(p,CH['lead'],LEAD_A,IIDX['lead'])
    crashat(p,0); echo(p,LEAD_A,IIDX['bell'],12,2,24)
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'wide',vol=40); bass(p,MAIN,'drive'); drums(p,'full'); seq(p,CH['lead'],LEAD_A[7:],IIDX['lead'])
    seq(p,CH['lead'],LEAD_D,IIDX['lead'],40)
    fill(p,52,'snare')
    echo(p,LEAD_D,IIDX['bell'],12,2,22)
    p=newpat(); pat_chords(p,DRV); arp(p,DRV,'fast',vol=40); bass(p,DRV,'walk'); drums(p,'drive'); seq(p,CH['lead'],LEAD_B,IIDX['lead'])
    crashat(p,0,60); echo(p,LEAD_B,IIDX['bell'],12,2,26)
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'down',vol=40); bass(p,MAIN,'drive'); drums(p,'full'); seq(p,CH['lead'],LEAD_B,IIDX['lead'])
    seq(p,CH['lead'],LEAD_D,IIDX['lead'],40)
    # P6,P7 break: pad+bell, then build
    p=newpat(); pat_chords(p,BRK); arp(p,BRK,'soft',vol=22); bass(p,BRK,'root',vol=32)
    seq(p,CH['bell'],[(0,72,8,46),(8,76,8,44),(16,79,8,48),(24,76,8,44),
                      (32,74,8,46),(40,72,8,44),(48,71,12,42)],IIDX['bell'])
    put(p,60,CH['bell'],81,IIDX['bell'],34)
    p=newpat(); pat_chords(p,BRK); arp(p,BRK,'wide',vol=32); bass(p,BRK,'walk',vol=44); drums(p,'light')
    seq(p,CH['bell'],[(0,72,4,44),(4,76,4,46),(8,79,8,48),(16,76,8,46),(24,72,8,44),
                      (32,71,8,46),(40,74,8,48),(48,76,8,50)],IIDX['bell'])
    for r in range(12,16): put(p,r,CH['drum'],60,IIDX['snare'],26+(r-12)*12)
    for r in range(12,16): put(p,r,CH['hat'],60,IIDX['hat'],26+(r-12)*10)
    riserat(p,32,60)
    # P8..P10 drive section
    p=newpat(); pat_chords(p,DRV); arp(p,DRV,'fast',vol=42); bass(p,DRV,'drive',56); drums(p,'drive'); seq(p,CH['lead'],LEAD_A,IIDX['lead'],64)
    crashat(p,0,64)
    p=newpat(); pat_chords(p,DRV); arp(p,DRV,'up',vol=42); bass(p,DRV,'drive',56); drums(p,'drive'); seq(p,CH['lead'],LEAD_B,IIDX['lead'],64)
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'fast',vol=38); bass(p,MAIN,'drive',58); drums(p,'drive'); seq(p,CH['lead'],LEAD_B,IIDX['lead'],64)
    seq(p,CH['lead'],LEAD_D,IIDX['lead'],60)
    fill(p,50,'snare')
    # P11,P12 reprise with pluck counter
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'up',vol=40); bass(p,MAIN,'drive'); drums(p,'full'); seq(p,CH['lead'],LEAD_A,IIDX['lead'])
    crashat(p,0,60)
    seq(p,CH['bell'],[(2,76,2,30),(6,72,2,28),(10,64,2,30),(14,67,2,28),
                      (18,77,2,32),(26,72,2,30),(34,76,2,30),(42,74,2,28),(50,68,2,30),(58,77,2,32)],IIDX['pluck'])
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'wide',vol=40); bass(p,MAIN,'drive'); drums(p,'full'); seq(p,CH['lead'],LEAD_B,IIDX['lead'])
    seq(p,CH['bell'],[(2,81,2,30),(6,79,2,28),(10,72,2,30),(14,76,2,28),
                      (18,81,2,32),(26,77,2,30),(34,84,2,32),(42,79,2,30),(50,76,2,30),(58,80,2,32)],IIDX['pluck'])
    # P13 soft breakdown
    p=newpat(); pat_chords(p,BRK); arp(p,BRK,'soft',vol=24); bass(p,BRK,'root',vol=34)
    seq(p,CH['bell'],LEAD_C,IIDX['bell'])
    # P14 build
    p=newpat(); pat_chords(p,DRV); arp(p,DRV,'wide',vol=30); bass(p,DRV,'walk',vol=44); drums(p,'light')
    seq(p,CH['bell'],LEAD_C[12:],IIDX['bell'])
    for r in range(8,16): put(p,r,CH['hat'],60,IIDX['hat'],24+(r-8)*4)
    for r in range(12,16): put(p,r,CH['drum'],60,IIDX['snare'],30+(r-12)*12)
    riserat(p,32,64)
    # P15 peak
    p=newpat(); pat_chords(p,DRV); arp(p,DRV,'fast',vol=44); bass(p,DRV,'drive',58); drums(p,'drive'); seq(p,CH['lead'],LEAD_B,IIDX['lead'],64)
    crashat(p,0,64); echo(p,LEAD_B,IIDX['bell'],12,2,30)
    fill(p,48,'snare')
    # P16 outro: strip down
    p=newpat(); pat_chords(p,MAIN); arp(p,MAIN,'down',vol=28); bass(p,MAIN,'off',vol=44)
    seq(p,CH['lead'],LEAD_C,IIDX['lead'],48)
    drums(p,'half')
    for r in range(32,40): put(p,r,CH['drum'],60,IIDX['snare'],34+(r-32)*7)
    # P17 final build + chord
    p=newpat(); pat_chords(p,DRV); arp(p,DRV,'wide',vol=30); bass(p,DRV,'walk',vol=48)
    drums(p,'light'); seq(p,CH['lead'],LEAD_D,IIDX['lead'],56)
    for r in range(8,16): put(p,r,CH['hat'],60,IIDX['hat'],24+(r-8)*5)
    for r in range(8,16): put(p,r,CH['drum'],60,IIDX['snare'],28+(r-8)*7)
    for r in range(24,32): put(p,r,CH['hat'],60,IIDX['hat'],30+(r-24)*5)
    for r in range(24,32): put(p,r,CH['drum'],60,IIDX['snare'],30+(r-24)*7)
    for r in range(40,48): put(p,r,CH['drum'],60,IIDX['snare'],34+(r-40)*5)
    for r in range(44,48): put(p,r,CH['hat'],60,IIDX['hat'],44)
    # final Am chord at row 48
    rt,padn,st=chord('Am')
    for j,pn in enumerate(padn[:3]): put(p,48,CH['pad%d'%(j+1)],pn,IIDX['pad'],40)
    put(p,48,CH['bass'],rt,IIDX['bass'],54)
    put(p,48,CH['stab'],60,IIDX['stab_am'],48)
    put(p,48,CH['lead'],69,IIDX['lead'],58)
    put(p,48,CH['bell'],69,IIDX['bell'],40)
    arp(p,['Am','Dm','E7','Am'],'up',vol=30)
    # stutter fade-out of everything after row 48 (volume-0 retriggers cut the sustains)
    for r in range(49,64):
        f=(63-r)/15.0
        v=max(0,int(46*f))
        for j,pn in enumerate(padn[:3]): put(p,r,CH['pad%d'%(j+1)],pn,IIDX['pad'],int(40*f)+ (12 if j==1 else 0))
        put(p,r,CH['arp'],69,IIDX['arp'],max(1,int(30*f)))
        put(p,r,CH['bass'],rt,IIDX['bass'],1)
        put(p,r,CH['lead'],69,IIDX['lead'],1)
        put(p,r,CH['drum'],60,IIDX['kick'],1)
        put(p,r,CH['hat'],60,IIDX['hat'],1)
        put(p,r,CH['bell'],69,IIDX['bell'],1)
    return P
if __name__=='__main__':
    pats=build()
    print('patterns',len(pats),'cells',sum(len(p) for p in pats))
