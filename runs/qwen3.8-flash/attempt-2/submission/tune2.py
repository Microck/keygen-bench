import sys, numpy as np
sys.path.insert(0,'/workspace/work')
from f2 import call
SR=44100; NCH=8; ROWS=64
SPEC=[ # name, file, loop_start, loop_len, samplevol, panning
 ('LEAD-SAW','lead',14700,7350,64,128),
 ('PLUCK-A','pluck',0,0,64,48),
 ('PLUCK-B','pluck2',0,0,60,208),
 ('PAD-STR','pad',15435,44100,56,96),
 ('BASS-DRV','bass',0,0,64,128),
 ('SUB-BASS','sub',0,0,64,128),
 ('KICK','kick',0,0,64,128),
 ('SNARE','snare',0,0,60,180),
 ('HAT-C','hat',0,0,52,84),
 ('HAT-O','hato',0,0,48,196),
 ('FX-SWELL','swell',0,0,56,64),
 ('TOM','tom',0,0,56,152),
]
def setup():
    call('module_new',{'channels':NCH,'name':'NEON CHAPEL'})
    for i,(nm,f,ls,ll,dv,pan) in enumerate(SPEC,start=1):
        call('sample_load',{'path':f'/workspace/work/samples/{f}.wav','instrument':i,'sample':0})
        a={'instrument':i,'sample':0,'volume':dv,'panning':pan}
        if ll>1: a.update(loop_start=ls, loop_length=ll, flags=1)
        call('sample_set',a)
        call('instrument_set',{'instrument':i,'name':nm})
def V(a):
    v=int(round(float(a))); return max(1,min(80,v))
def C(n,i,a,e=0,p=0): return (n,i,V(a),e,p)
OFF=(97,0,0,0,0); E0=(0,0,0,0,0)
def G(ed):
    g=[[E0]*NCH for _ in range(ROWS)]
    for (r,c),cell in ed.items():
        if 0<=r<ROWS and 0<=c<NCH: g[r][c]=cell
    return g
# ---------------- harmony ----------------
def CH(a0,a1,a2,a3,bass,arp): return dict(pad=[a0,a1,a2,a3],bass=bass,arp=arp)
# notes use fork naming: 49=C4,57=A4,61=C5,69=A5,73=C6,81=A6
Am =CH(57,60,64,69, 46,[60,64,69,72])   # A minor
F  =CH(53,57,60,65, 42,[57,60,65,69])   # F
Cm =CH(52,55,60,64, 37,[55,60,64,67])   # C  (I-vii style)
GX =CH(55,59,62,67, 41,[59,62,67,71])   # G
Dm =CH(50,53,57,62, 39,[50,57,62,65])
Em =CH(52,56,59,64, 44,[56,59,64,68])   # E major-ish (G#=56)

PR1=[Am,F,Cm,GX]; PR2=[Dm,Am,Em,GX]; PR3=[Am,F,Dm,Em]; PR4=[Cm,GX,Am,F]
# ---------------- melody voices ----------------
M1=[(0,73,3,58),(4,76,2,52),(6,73,2,50),(8,72,5,56),(14,69,2,48),
    (16,77,3,58),(20,76,2,52),(22,73,2,50),(24,69,7,56),
    (32,72,2,54),(34,71,2,50),(36,69,5,54),(42,71,2,50),(44,72,4,56),
    (48,73,9,60),(58,69,2,48),(60,67,3,46)]
M2=[(0,81,2,60),(2,77,2,54),(4,76,4,58),(8,73,2,50),(10,76,2,52),(12,77,5,56),
    (16,81,3,60),(20,79,2,54),(22,77,2,50),(24,76,8,58),
    (32,73,2,52),(34,72,2,50),(36,69,5,54),(42,71,2,50),(44,72,4,56),
    (48,64,9,58),(58,62,2,46),(60,64,3,50)]
M3=[(0,81,2,62),(2,80,2,58),(4,77,2,56),(6,76,2,54),(8,73,4,60),(12,76,2,52),(14,77,2,54),
    (16,81,2,62),(18,83,2,58),(20,84,4,60),(24,83,2,56),(26,81,2,56),(28,77,4,58),
    (32,80,2,58),(34,79,2,54),(36,77,2,52),(38,76,2,52),(40,73,4,56),(44,71,2,50),(46,72,2,52),
    (48,76,2,56),(50,77,2,54),(52,80,4,60),(56,81,6,62),(62,79,2,52)]
M4=[(0,79,3,58),(4,76,2,52),(6,74,2,50),(8,71,6,56),(16,72,2,52),(18,71,2,50),(20,69,6,56),
    (32,68,2,50),(34,71,2,50),(36,76,6,58),(44,72,3,52),(48,69,8,58),(58,66,2,48),(60,68,3,50)]
MSOLO=[(0,69,2,50),(2,72,2,50),(4,76,2,52),(6,73,2,48),(8,77,5,56),(14,81,2,52),
    (16,80,2,50),(18,76,2,48),(20,73,5,54),(26,76,7,56),
    (32,68,2,50),(36,76,4,56),(40,72,2,50),(44,69,9,56),(56,64,3,50),(60,62,3,48)]
def lead(mel,ins=1,base=0,transpose=0):
    e={}
    for (r,n,l,a) in mel:
        rr=r+base
        if rr>=ROWS: continue
        e[(rr,0)]=C(n+transpose,ins,a)
        if rr+l<ROWS: e[(rr+l,0)]=OFF
    return e
def pad(prog,amps=(46,40,36,32),octave=12,chans=(2,2,3,3)):
    e={}
    for b in range(4):
        for i,nt in enumerate(prog[b]['pad']):
            e[(b*16,chans[i])]=C(nt+octave,4,amps[i])
            e[(b*16+14,chans[i])]=OFF
    return e
def bassline(pat,prog,ins=5):
    e={}
    for b in range(4):
        rt=prog[b]['bass']
        for (r,off,a,l) in pat:
            if r>15: continue
            row=b*16+r
            e[(row,4)]=C(rt+off,ins,a)
            if l and row+l<ROWS: e[(row+l,4)]=OFF
    return e
B_P1=[(0,0,58,1),(3,0,46,1),(6,12,50,1),(8,0,58,1),(11,7,46,1),(14,12,50,1)]
B_P2=[(0,0,60,1),(2,0,48,1),(4,12,50,1),(6,7,46,1),(8,0,60,1),(10,12,48,1),(12,7,50,1),(14,0,46,1)]
B_DRV=[(i,(0 if i%4==0 else (12 if i%4==2 else 7)),(58 if i%4==0 else 46),1) for i in range(0,16,2)]
B_16=[(i,(0 if i%2==0 else 12),(56 if i%4==0 else 44),1) for i in range(16)]
def arp(seq,prog,ins=2,amp=48,oct_up=12,ch=1,skip=()):
    e={}
    for b in range(4):
        nn=prog[b]['arp']
        for i,idx in enumerate(seq):
            if idx is None or (b,i) in skip: continue
            nt=nn[idx%4]+(oct_up if idx>=4 else 0)
            e[(b*16+i,ch)]=C(nt,ins,amp if i%2==0 else amp-10)
    return e
A1=[0,1,2,3,2,1,0,2,1,2,3,2,1,3,2,4]
A2=[0,2,1,3,0,2,3,1,2,0,1,3,2,1,3,2]
A3=[4,3,2,1,0,1,2,3,4,3,2,1,0,2,3,4]
A4=[0,1,2,3,4,3,2,1,0,2,3,4,2,1,0,1]
def drums(k,s,h,ch_h=7,extra=()):
    e={}
    for b in range(4):
        for r in k: e[(b*16+r,5)]=C(61,7,64)
        for r in s: e[(b*16+r,6)]=C(61,8,56)
        for r,a in h: e[(b*16+r,ch_h)]=C(73,9,a)
        for (r,c,n,i,a) in extra: e[(b*16+r,c)]=C(n,i,a)
    return e
K_A=[0,6,8,14]; S_A=[4,12]; H8=[(i,40) for i in range(0,16,2)]; H16=[(i,38) for i in range(16)]
K_A2=[0,3,8,11,14]; S_A2=[4,12,15]
K_BRK=[0]; S_BRK=[8]
def merge(*ds):
    o={}
    for d in ds: o.update(d)
    return o
H_OFF=lambda a: [(14,a)]
setup()
# ---------------- patterns ----------------
PT0=G(merge(pad(PR1,(34,30,26,22)),
   {(0,0):C(73,1,30),(4,0):OFF,(16,0):C(72,1,28),(22,0):OFF,(32,0):C(69,1,30),(40,0):OFF,
    (44,0):C(71,1,26),(50,0):OFF,(56,7):C(61,11,40)},
   {(48,4):C(46,6,44),(60,4):OFF}))
PT1=G(merge(lead(M1),pad(PR1),bassline(B_P1,PR1),arp(A1,PR1,2,50),
   drums(K_A,S_A,H8,extra=[(12,6,61,8,20)])))
PT2=G(merge(lead(M2),pad(PR1),bassline(B_P2,PR1),arp(A2,PR1,2,52),
   drums(K_A2,S_A2,H8,extra=[(2,6,69,12,32),(10,6,73,12,28),(13,7,73,10,34)])))
PT3=G(merge(lead(MSOLO),pad(PR2,(40,36,32,28)),bassline(B_P1,PR2),arp(A3,PR2,3,44),
   drums(K_BRK,[4,12],[(i,20) for i in range(0,16,4)],extra=[(14,6,61,8,44),(15,6,69,12,30)])))
PT4=G(merge(lead(M3),pad(PR3,(46,42,38,32)),bassline(B_16,PR3,5),arp(A4,PR3,2,54),
   drums(K_A2+[6],S_A2,H16,extra=[(7,6,61,8,44),(9,4,None,None,None) if False else (9,6,69,12,30)])))
PT5=G(merge(lead(M4),pad(PR4,(44,38,34,30)),bassline(B_P2,PR4),arp(A2,PR4,2,50),
   drums(K_A,S_A,H8,extra=[(11,6,61,8,22),(12,7,73,10,20)])))
PT6=G(merge(lead(M1,base=0),pad(PR1,(46,42,38,34)),bassline(B_P1,PR1),arp(A1,PR1,2,48),
   drums(K_A,S_A,H8),
   {(48,4):C(33,6,52),(58,4):OFF,(52,5):C(61,7,56),(56,6):C(61,8,50),(60,7):C(73,10,40)}))
PATS=[PT0,PT1,PT2,PT3,PT4,PT5,PT6]
for i,p in enumerate(PATS):
    call('pattern_set_length',{'pattern':i,'rows':ROWS})
    for r in range(ROWS):
        for c in range(NCH):
            nt,ins,v,ef,ep=p[r][c]
            if nt or ins or v or ef or ep:
                call('pattern_set_cell',{'pattern':i,'row':r,'channel':c,'note':nt,'instrument':ins,
                    'volume':v,'effect':ef,'effect_param':ep})
ORDER=[0,1,2,3,4,5,6,0]
for i,o in enumerate(ORDER): call('order_set',{'position':i,'pattern':o})
call('song_set',{'bpm':150,'speed':6,'length':len(ORDER),'loop_start':1,'global_volume':64})
call('module_save',{'path':'/workspace/submission/tune.xm'})
print('saved')
print(call('module_render',{'path':'/workspace/work/tune2.wav','rate':44100,'bits':16,'amp':16})[0])
