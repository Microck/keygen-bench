import sys; sys.path.insert(0,'/workspace/work')
import numpy as np
from lib2 import *
from xm import XM, Pattern
import synth2 as S2

PC={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def N(s):
    if isinstance(s,int): return s
    i=1; pc=PC[s[0]]
    if i<len(s) and s[i] in '#b':
        pc += 1 if s[i]=='#' else -1; i+=1
    rest=s[i:]
    if rest.startswith('-'): rest=rest[1:]
    return int(rest)*12+pc+1
def nm(b):
    v=int(b)-1; return NAMES[v%12]+str(v//12)
def tr(s,semis): return nm(N(s)+semis)

RATE=16726.0; DRATE=33452.0; F0=261.6256

PADS={'Am':(220.00,(0,3,7,12,15)),'F':(174.61,(0,4,7,12,16)),'C':(261.63,(0,4,7,12,16)),
      'G':(196.00,(0,4,7,12,16)),'Dm':(146.83,(0,3,7,12,15)),'Bb':(233.08,(0,4,7,12,16)),
      'E':(164.81,(0,4,7,12,19)),'Em':(164.81,(0,3,7,12,15))}
CHORD_PC={'Am':{9,0,4},'F':{5,9,0},'C':{0,4,7},'G':{7,11,2},'Dm':{2,5,9},'Bb':{10,2,5},
          'E':{4,8,11},'Em':{4,7,11}}

# Calibrated sample volumes (0..64) and pans (0..255)
VOL=dict(lead=30, leadR=22, lead2=28, echo=22, arpL=14, arpR=13, spark=11,
         bass=34, kick=50, snare=54, hatC=40, hatO=34, crash=24, tom=26, rim=22,
         riser=22, bell=22, padL=16, padR=16)
PAN=dict(lead=96, leadR=152, lead2=100, echo=224, arpL=38, arpR=218, spark=52,
         bass=128, kick=128, snare=138, hatC=196, hatO=200, crash=58, tom=32, rim=228,
         riser=128, bell=180, padL=70, padR=188)

GAIN={}
def _gain(name):
    if name in GAIN: return GAIN[name]
    if name.startswith('pad'): return GAIN.get('padL' if name.endswith('L') else 'padR',1.0)
    return 1.0

_CACHE={}
def make_instruments():
    import json, os
    if os.path.exists('/workspace/work/gains.json'):
        g=json.load(open('/workspace/work/gains.json'))
        for k,v in g.items():
            if k in VOL: VOL[k]=v
    import json, os
    if os.path.exists('/workspace/work/gaindata.json'):
        g=json.load(open('/workspace/work/gaindata.json'))
        GAIN.update(g)
    if 'data' not in _CACHE:
        _CACHE['data']=make_instrument_data()
    ins=[]
    for item in _CACHE['data']:
        name=item['name']
        key=name if name in VOL else ('padL' if name.endswith('L') else 'padR')
        d=dict(item); d['vol']=VOL[key]; d['pan']=PAN[key]
        g=_gain(name)
        if abs(g-1.0)>1e-6:
            d['data']=np.clip(item['data']*g,-0.999,0.999)
        ins.append(d)
    return ins

def make_instrument_data():
    ins=[]
    def add(name,data,relnote,loop=False):
        ins.append(dict(name=name,data=data,relnote=relnote,loop=loop))
    add('lead',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.25,nharm=28,cycles=32,amp=0.92),12,True)
    add('leadR', S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=22,cycles=48,amp=0.85),12,True)
    add('lead2', S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=24,cycles=40,amp=0.88),12,True)
    add('echo',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.25,nharm=18,cycles=32,amp=0.85),12,True)
    add('arpL',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=16,cycles=48,amp=0.8),12,True)
    add('arpR',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=16,cycles=48,amp=0.8),12,True)
    add('spark', S2.pulse_loop(rate=RATE,f0=F0,duty=0.0625,nharm=10,cycles=96,amp=0.65),12,True)
    add('bass',  S2.bass_oneshot(rate=RATE,f0=F0,dur=0.42,amp=0.95,decay=0.17),12)
    add('kick',  S2.kick(rate=RATE,dur=0.34,f0=195,f1=48,decay=0.10,click=0.55),12)
    add('snare', S2.snare(rate=RATE,dur=0.24,tone=200),12)
    add('hatC',  S2.hat(rate=DRATE,dur=0.05,decay=0.011,fc=7600),24)
    add('hatO',  S2.openhat(rate=DRATE,dur=0.24,decay=0.055,fc=6400),24)
    add('crash', S2.crash(rate=DRATE,dur=1.4,decay=0.42),24)
    add('tom',   S2.tom(rate=RATE,dur=0.26,f0=340,f1=140),12)
    add('rim',   S2.zap(rate=RATE,dur=0.09,amp=0.6),12)
    add('riser', S2.riser(rate=RATE,dur=1.7),12)
    add('bell',  S2.bell(rate=RATE,f=F0,dur=1.1,amp=0.7),12)
    for ch,(root,ivs) in PADS.items():
        add('pad'+ch+'L', S2.pad(root,ivs,rate=RATE,dur=1.50,amp=0.72,det=0.0040),12)
        add('pad'+ch+'R', S2.pad(root,ivs,rate=RATE,dur=1.50,amp=0.72,det=-0.0052),12)
    return ins

INS={}
CH=dict(lead=0,harm=1,echo=2,arpL=3,arpR=4,bass=5,kick=6,snare=7,hats=8,
        padL=9,padR=10,fx=11,fx2=12,spark=13,perc=14)

class Tr:
    def __init__(self,rows=64,channels=15):
        self.p=Pattern(rows,channels); self.rows=rows
    def note(self,row,ch,n,inst,vol=64):
        self.p.set(row,ch,note=N(n),inst=inst,vol=vol)
    def off(self,row,ch): self.p.set(row,ch,note=97)
    def cut(self,row,ch): self.p.set(row,ch,eff=0x0E,par=0xC0)
    def vol(self,row,ch,v): self.p.set(row,ch,vol=v)
    def fx(self,row,ch,e,p): self.p.set(row,ch,eff=e,par=p)

BASS_ROOT={'Am':'A-2','F':'F-2','C':'C-3','G':'G-2','Dm':'D-2','Bb':'Bb-2','E':'E-2','Em':'E-2'}
ARP={'Am':['A-3','C-4','E-4','A-4'],'F':['F-3','A-3','C-4','F-4'],'C':['C-4','E-4','G-4','C-5'],
     'G':['G-3','B-3','D-4','G-4'],'Dm':['D-3','F-3','A-3','D-4'],'Bb':['Bb-3','D-4','F-4','Bb-4'],
     'E':['E-3','G#-3','B-3','E-4'],'Em':['E-3','G-3','B-3','E-4']}
PAD_NOTE='C-4'

def bass_bar(T,bar,chord,vol=64,style='8ths'):
    r=BASS_ROOT[chord]; r12=tr(r,12); fifth=tr(r,7)
    row0=bar*16
    if style=='8ths': seq=[r,r,r,r12,r,fifth,r12,fifth]
    elif style=='drive': seq=[r,None,r,r12,None,r,fifth,r12]
    elif style=='walk': seq=[r,r12,fifth,r12,r,fifth,tr(r,3),fifth]
    elif style=='oct': seq=[r,r12,r,r12,r,r12,fifth,tr(fifth,12)]
    elif style=='sparse': seq=[r,None,None,None,r12,None,fifth,None]
    elif style=='push': seq=[r,r,r12,r,r,r12,fifth,r]
    elif style=='long': seq=[r,None,None,None,None,None,None,None]
    for i,n in enumerate(seq):
        if n is not None: T.note(row0+i*2,CH['bass'],n,INS['bass'],vol)

def arp_bars(T,bar,chord,vol=44,mode='updown',step=1,octv=0,vol2=None):
    base=[nm(N(x)+12*octv) for x in ARP[chord]]
    if mode=='up': seq=base
    elif mode=='down': seq=base[::-1]
    elif mode=='updown': seq=base+base[-2:0:-1]
    elif mode=='skip': seq=[base[0],base[2],base[1],base[3]]
    row0=bar*16; vol2=vol if vol2 is None else vol2
    for i in range(0,16,step):
        ch=CH['arpL'] if i%2==0 else CH['arpR']
        inst=INS['arpL'] if ch==CH['arpL'] else INS['arpR']
        v=vol if i%4==0 else (vol2 if ch==CH['arpR'] else vol-6)
        T.note(row0+i,ch,seq[i%len(seq)],inst,v)

def pad_bar(T,bar,chord,vol=44):
    T.note(bar*16,CH['padL'],PAD_NOTE,INS['pad'+chord+'L'],vol)
    T.note(bar*16,CH['padR'],PAD_NOTE,INS['pad'+chord+'R'],vol)

def kick_bar(T,bar,rows,vol=64):
    for r in rows: T.note(bar*16+r,CH['kick'],'C-4',INS['kick'],vol)
def snare_bar(T,bar,rows,vol=64):
    for r in rows: T.note(bar*16+r,CH['snare'],'C-4',INS['snare'],vol)
def hat_bar(T,bar,mode='8ths',vol=56):
    row0=bar*16
    if mode=='8ths':
        for i in range(0,16,2):
            inst=INS['hatO'] if i in (6,14) else INS['hatC']
            T.note(row0+i,CH['hats'],'C-4',inst,vol if i%4==0 else vol-9)
    elif mode=='16ths':
        for i in range(16):
            inst=INS['hatO'] if i in (6,14) else INS['hatC']
            T.note(row0+i,CH['hats'],'C-4',inst,(vol if i%4==0 else vol-11)-(5 if i%2 else 0))
    elif mode=='off':
        for i in range(16):
            if i%4==2: T.note(row0+i,CH['hats'],'C-4',INS['hatO'],vol+4)
            elif i%2==0: T.note(row0+i,CH['hats'],'C-4',INS['hatC'],vol-10)
    elif mode=='sparse':
        for i in range(0,16,4): T.note(row0+i,CH['hats'],'C-4',INS['hatC'],vol-18)
    elif mode=='ride':
        for i in range(0,16,2): T.note(row0+i,CH['hats'],'C-4',INS['hatO'] if i%4==2 else INS['hatC'],vol-4)
    elif mode=='16soft':
        for i in range(16):
            T.note(row0+i,CH['hats'],'C-4',INS['hatC'],(vol-20 if i%4==0 else vol-28)-(4 if i%2 else 0))

def drums(T,bar,kind='basic',hat='8ths'):
    if kind=='basic': kick_bar(T,bar,[0,8]); snare_bar(T,bar,[4,12]); hat_bar(T,bar,hat)
    elif kind=='four': kick_bar(T,bar,[0,4,8,12]); snare_bar(T,bar,[4,12]); hat_bar(T,bar,hat)
    elif kind=='drive': kick_bar(T,bar,[0,4,7,8,12]); snare_bar(T,bar,[4,12]); hat_bar(T,bar,hat)
    elif kind=='push': kick_bar(T,bar,[0,4,8,12,14]); snare_bar(T,bar,[4,12]); hat_bar(T,bar,hat)
    elif kind=='half': kick_bar(T,bar,[0,10]); snare_bar(T,bar,[8]); hat_bar(T,bar,hat)
    elif kind=='break': kick_bar(T,bar,[0]); snare_bar(T,bar,[8]); hat_bar(T,bar,hat)
    elif kind=='none': pass

def fill(T,bar,kind='snare',vol=56,start=12):
    row0=bar*16
    if kind=='snare':
        for i in range(start,16): T.note(row0+i,CH['snare'],'C-4',INS['snare'],vol if i%2==0 else vol-12)
    elif kind=='snare16':
        for i in range(start,16): T.note(row0+i,CH['snare'],'C-4',INS['snare'],vol if i%4==0 else vol-14)
    elif kind=='toms':
        seq=[('C-4',vol),('E-4',vol-5),('G-4',vol-9),('C-4',vol-3)]
        for k,i in enumerate(range(start,16)):
            n,v=seq[k%4]; T.note(row0+i,CH['perc'],n,INS['tom'],v)
    elif kind=='mix':
        T.note(row0+start,CH['snare'],'C-4',INS['snare'],vol)
        T.note(row0+start+2,CH['snare'],'C-4',INS['snare'],vol-12)
        T.note(row0+start+3,CH['perc'],'E-4',INS['tom'],vol-8)
        T.note(row0+14,CH['perc'],'G-4',INS['tom'],vol-4)
        T.note(row0+15,CH['perc'],'C-4',INS['tom'],vol)

def crash_row(T,row,vol=48): T.note(row,CH['fx'],'C-4',INS['crash'],vol)
def riser_row(T,row,vol=48): T.note(row,CH['fx'],'C-4',INS['riser'],vol)
def bell_row(T,row,n,vol=48): T.note(row,CH['fx2'],n,INS['bell'],vol)
def rim_row(T,row,vol=32): T.note(row,CH['perc'],'C-4',INS['rim'],vol)
def spark_row(T,row,ch=None,vol=24):
    ch=CH['spark'] if ch is None else ch
    T.note(row,ch,'C-4',INS['spark'],vol)

def chord_tone_below(note_name,chord,lo=3,hi=7,prefer=(4,3,5)):
    b=N(note_name); tones=CHORD_PC[chord]
    cands=[d for d in range(lo,hi+1) if ((b-d-1)%12) in tones]
    if not cands: return nm(b-4)
    cands.sort(key=lambda d:(prefer.index(d) if d in prefer else 9, d))
    return nm(b-cands[0])

def melody(T,phrase,inst,vol=58,ch=None,echo=True,echo_vol=30,echo_delay=3,echo_inst=None,
           harm=False,chords=None,harm_vol=None,harm_inst=None,vib_par=0x46,do_echo_off=True):
    ch=CH['lead'] if ch is None else ch
    echo_inst=INS['echo'] if echo_inst is None else echo_inst
    harm_inst=INS['leadR'] if harm_inst is None else harm_inst
    phrase=sorted(phrase,key=lambda x:x[0])
    for i,(row,n,dur,v) in enumerate(phrase):
        vv=v if v is not None else vol
        T.note(row,ch,n,inst,vv)
        nxt=phrase[i+1][0] if i+1<len(phrase) else 64

        if row+dur<nxt: T.off(row+dur,ch)
        if dur>=3: T.fx(row+1,ch,0x04,vib_par)
        if harm and chords is not None:
            bar=min(row//16,len(chords)-1)
            hn=chord_tone_below(n,chords[bar])
            T.note(row,CH['harm'],hn,harm_inst,(harm_vol if harm_vol is not None else vv))
            if row+dur<nxt: T.off(row+dur,CH['harm'])
        if echo:
            r2=row+echo_delay
            if r2<64:
                T.note(r2,CH['echo'],n,echo_inst,echo_vol)
                if do_echo_off:
                    nxt2=(phrase[i+1][0]+echo_delay) if i+1<len(phrase) else 128
                    if r2+dur<nxt2: T.off(r2+dur,CH['echo'])

# ---------------- melodies (16 rows per bar) ----------------
def hookA():   # Am F C G
    return [(0,'A-5',2,60),(2,'C-6',1,54),(3,'E-6',1,56),(4,'A-6',4,62),
            (8,'G-6',2,56),(10,'E-6',2,52),(12,'C-6',2,56),(14,'E-6',2,54),
            (16,'F-5',2,56),(18,'A-5',1,52),(19,'C-6',1,54),(20,'F-6',4,62),
            (24,'E-6',2,54),(26,'C-6',2,52),(28,'A-5',2,54),(30,'C-6',2,56),
            (32,'C-6',2,58),(34,'E-6',1,52),(35,'G-6',1,56),(36,'C-7',2,60),
            (38,'G-6',2,58),(40,'E-6',2,54),(42,'C-6',2,52),(44,'G-5',2,50),(46,'E-5',2,48),
            (48,'G-5',2,56),(50,'B-5',1,52),(51,'D-6',1,54),(52,'G-6',4,60),
            (56,'D-6',2,54),(58,'B-5',2,50),(60,'G-5',2,52),(62,'D-6',2,54)]
def hookA2():
    return [(0,'E-6',2,58),(2,'C-6',1,52),(3,'A-5',1,54),(4,'E-5',2,52),
            (6,'A-5',2,54),(8,'C-6',2,58),(10,'E-6',2,60),(12,'A-6',3,64),(15,'G-6',1,52),
            (16,'F-6',2,58),(18,'C-6',1,52),(19,'A-5',1,54),(20,'F-5',2,50),
            (22,'A-5',2,54),(24,'C-6',2,56),(26,'F-6',2,60),(28,'E-6',3,58),(31,'D-6',1,50),
            (32,'E-6',2,58),(34,'C-6',1,52),(35,'G-5',1,54),(36,'E-5',2,50),
            (38,'G-5',2,54),(40,'C-6',2,56),(42,'E-6',2,58),(44,'G-6',3,62),(47,'E-6',1,52),
            (48,'D-6',2,56),(50,'B-5',1,50),(51,'G-5',1,52),(52,'D-5',2,48),
            (54,'G-5',2,54),(56,'B-5',2,56),(58,'D-6',2,58),(60,'G-6',3,62),(63,'B-5',1,48)]
def hookB():   # Dm Bb F E
    return [(0,'D-6',2,60),(2,'F-6',1,54),(3,'A-6',1,58),(4,'D-6',2,54),
            (6,'A-5',2,52),(8,'F-6',2,60),(10,'D-6',2,54),(12,'A-5',2,50),(14,'D-6',2,56),
            (16,'Bb-5',2,58),(18,'D-6',1,52),(19,'F-6',1,56),(20,'Bb-6',3,64),
            (23,'A-6',1,52),(24,'F-6',2,58),(26,'D-6',2,52),(28,'Bb-5',2,50),(30,'D-6',2,54),
            (32,'C-6',2,56),(34,'A-5',1,50),(35,'F-5',1,52),(36,'C-6',2,56),
            (38,'A-5',2,52),(40,'F-5',2,50),(42,'A-5',2,52),(44,'C-6',2,56),(46,'E-6',2,58),
            (48,'B-5',2,58),(50,'E-6',1,52),(51,'G#-6',1,56),(52,'B-6',3,64),
            (55,'A-6',1,52),(56,'E-6',2,58),(58,'D-6',2,52),(60,'B-5',2,50),(62,'G#-5',2,48)]
def hookB2():
    return [(0,'F-6',2,62),(2,'D-6',1,52),(3,'A-5',1,54),(4,'D-6',2,58),
            (6,'F-6',2,60),(8,'A-6',4,64),(12,'G-6',2,56),(14,'F-6',2,54),
            (16,'D-6',2,58),(18,'F-6',1,52),(19,'A-6',1,56),(20,'Bb-6',3,64),
            (23,'A-6',1,54),(24,'F-6',2,60),(26,'D-6',2,54),(28,'Bb-5',2,52),(30,'D-6',2,56),
            (32,'E-6',2,60),(34,'C-6',1,52),(35,'A-5',1,54),(36,'C-6',2,58),
            (38,'F-6',2,60),(40,'A-6',3,64),(43,'G-6',1,54),(44,'E-6',2,58),(46,'C-6',2,54),
            (48,'B-5',2,58),(50,'E-6',1,52),(51,'G#-6',1,56),(52,'B-6',3,64),
            (55,'A-6',1,54),(56,'E-6',2,58),(58,'D-6',2,52),(60,'B-5',2,50),(62,'G#-5',2,48)]
def hookC():   # F G Em Am
    return [(0,'F-5',2,56),(2,'A-5',1,52),(3,'C-6',1,54),(4,'F-6',2,60),
            (6,'C-6',2,54),(8,'A-5',2,52),(10,'C-6',2,56),(12,'F-6',2,60),(14,'E-6',2,58),
            (16,'G-5',2,56),(18,'B-5',1,52),(19,'D-6',1,56),(20,'G-6',2,62),
            (22,'D-6',2,54),(24,'B-5',2,52),(26,'D-6',2,56),(28,'G-6',2,60),(30,'F-6',2,58),
            (32,'E-6',2,60),(34,'B-5',1,52),(35,'G-5',1,54),(36,'E-5',2,52),
            (38,'G-5',2,54),(40,'B-5',2,58),(42,'E-6',2,60),(44,'G-6',2,62),(46,'B-6',2,64),
            (48,'A-6',2,62),(50,'E-6',1,54),(51,'C-6',1,56),(52,'A-5',2,54),
            (54,'C-6',2,58),(56,'E-6',2,60),(58,'A-6',2,64),(60,'G-6',2,58),(62,'E-6',2,54)]
def hookOut():
    return [(0,'E-6',2,60),(2,'D-6',2,54),(4,'C-6',2,56),(6,'B-5',2,52),
            (8,'A-5',4,58),(12,'G-5',2,50),(14,'A-5',2,52),
            (16,'C-6',2,58),(18,'B-5',2,52),(20,'A-5',2,54),(22,'G-5',2,50),
            (24,'F-5',4,56),(28,'A-5',2,52),(30,'C-6',2,56),
            (32,'E-6',2,60),(34,'C-6',2,54),(36,'A-5',2,56),(38,'E-5',2,52),
            (40,'A-5',2,56),(42,'C-6',2,58),(44,'E-6',2,60),(46,'A-6',2,64),
            (48,'A-5',1,56),(49,'B-5',1,54),(50,'C-6',1,56),(51,'D-6',1,58),
            (52,'E-6',1,58),(53,'F-6',1,60),(54,'G-6',1,62),(55,'A-6',3,64),
            (58,'E-6',1,54),(59,'D-6',1,52),(60,'C-6',1,54),(61,'B-5',1,50),
            (62,'A-5',2,52)]

PROG_A=['Am','F','C','G']
PROG_B=['Dm','Bb','F','E']
PROG_C=['F','G','Em','Am']
PROG_O=['Am','F','C','G']

def build():
    global INS
    ins=make_instruments(); INS={I['name']:i+1 for i,I in enumerate(ins)}
    xm=XM('keygen',channels=15,bpm=150,speed=6,restart=0)
    P=[]

    # ---- P0 Intro ----
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=48 if b==0 else 46)
    for r,n,v in [(0,'A-5',52),(4,'E-6',44),(8,'C-6',46),(12,'A-5',40),
                  (16,'F-5',44),(20,'C-6',42),(24,'A-5',38),(32,'G-5',42),(36,'E-6',44),(40,'D-6',40),(48,'A-5',42)]:
        bell_row(T,r,n,v)
    arp_bars(T,1,'F',vol=34,mode='updown',step=2)
    arp_bars(T,2,'C',vol=40,mode='updown',step=2)
    arp_bars(T,3,'G',vol=46,mode='updown',step=1)
    hat_bar(T,1,'sparse',vol=34); hat_bar(T,2,'off',vol=44); hat_bar(T,3,'8ths',vol=50)
    kick_bar(T,2,[0,8],vol=52); kick_bar(T,3,[0,4,8,12],vol=60)
    snare_bar(T,3,[4,12],vol=56)
    crash_row(T,0,vol=40); riser_row(T,32,vol=46)
    rim_row(T,16,vol=26); rim_row(T,48,vol=30)
    # intro bell flourish at the end
    for i,(r,n) in enumerate([(52,'A-5'),(54,'C-6'),(56,'E-6'),(58,'A-6'),(60,'G-6'),(62,'E-6')]):
        bell_row(T,r,n,30+i*2)
    P.append(T.p)

    # ---- P1 A ----
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=40); bass_bar(T,b,ch,vol=60); arp_bars(T,b,ch,vol=40,mode='updown'); drums(T,b,'basic','8ths')
    crash_row(T,0,vol=48)
    melody(T,hookA(),INS['lead'],vol=58,harm=True,chords=PROG_A,harm_vol=36)
    fill(T,3,'snare',vol=48,start=14)
    P.append(T.p)

    # ---- P2 A2 ----
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=40); bass_bar(T,b,ch,vol=60,style='oct' if b==1 else '8ths')
        arp_bars(T,b,ch,vol=38,mode='updown')
        drums(T,b,'drive' if b in (1,3) else 'basic','16ths' if b==3 else '8ths')
    crash_row(T,0,vol=48); crash_row(T,32,vol=40)
    melody(T,hookA2(),INS['lead'],vol=58)
    fill(T,3,'mix',vol=50)
    P.append(T.p)

    # ---- P3 B ----
    T=Tr()
    for b,ch in enumerate(PROG_B):
        pad_bar(T,b,ch,vol=42); bass_bar(T,b,ch,vol=60); arp_bars(T,b,ch,vol=40,mode='up')
        drums(T,b,'basic','8ths')
    crash_row(T,0,vol=48); crash_row(T,32,vol=40)
    melody(T,hookB(),INS['lead'],vol=58,harm=True,chords=PROG_B,harm_vol=36)
    fill(T,3,'snare',vol=50,start=14)
    P.append(T.p)

    # ---- P4 Break ----
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=58)
        arp_bars(T,b,ch,vol=28,mode='updown' if b%2 else 'up')
    crash_row(T,0,vol=36)
    for r,n,v in [(0,'A-5',44),(6,'C-6',40),(12,'E-6',44),(16,'F-5',40),(22,'A-5',38),
                  (28,'C-6',42),(32,'G-5',40),(38,'B-5',38),(44,'D-6',42),(48,'E-5',36),
                  (54,'G-5',38),(60,'B-5',40)]:
        bell_row(T,r,n,v)
    bass_bar(T,2,'C',vol=50,style='sparse'); bass_bar(T,3,'G',vol=50,style='sparse')
    hat_bar(T,2,'sparse',vol=32); hat_bar(T,3,'sparse',vol=36)
    kick_bar(T,3,[0,8],vol=48); snare_bar(T,3,[12],vol=44)
    riser_row(T,48,vol=48)
    fill(T,3,'toms',vol=46,start=12)
    P.append(T.p)

    # ---- P5 A full ----
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=42); bass_bar(T,b,ch,vol=62,style='push' if b==1 else '8ths')
        arp_bars(T,b,ch,vol=38,mode='updown')
        arp_bars(T,b,ch,vol=24,mode='down',octv=1)
        drums(T,b,'four','8ths')
    crash_row(T,0,vol=50); crash_row(T,32,vol=42)
    melody(T,hookA(),INS['lead'],vol=60,harm=True,chords=PROG_A,harm_vol=40)
    for i in range(2,16,4): spark_row(T,i,vol=26)
    fill(T,3,'mix',vol=52)
    P.append(T.p)

    # ---- P6 B full ----
    T=Tr()
    for b,ch in enumerate(PROG_B):
        pad_bar(T,b,ch,vol=44); bass_bar(T,b,ch,vol=62)
        arp_bars(T,b,ch,vol=36,mode='up')
        arp_bars(T,b,ch,vol=22,mode='down',octv=1)
        drums(T,b,'push' if b in (1,3) else 'four','16ths' if b in (1,3) else '8ths')
    crash_row(T,0,vol=50); crash_row(T,32,vol=44)
    melody(T,hookB2(),INS['lead'],vol=60,harm=True,chords=PROG_B,harm_vol=40)
    for i in range(0,16,4): spark_row(T,i,vol=24)
    fill(T,3,'snare16',vol=52,start=8)
    P.append(T.p)

    # ---- P7 C ----
    T=Tr()
    for b,ch in enumerate(PROG_C):
        pad_bar(T,b,ch,vol=42); bass_bar(T,b,ch,vol=60,style='oct' if b<2 else '8ths')
        arp_bars(T,b,ch,vol=38,mode='skip' if b%2 else 'updown')
        drums(T,b,'drive' if b%2 else 'basic','8ths' if b%2 else '16ths')
    crash_row(T,0,vol=48); crash_row(T,32,vol=42)
    melody(T,hookC(),INS['lead2'],vol=60,harm=True,chords=PROG_C,harm_vol=36)
    for i in range(2,16,4): spark_row(T,i,vol=24)
    fill(T,3,'mix',vol=50)
    P.append(T.p)

    # ---- P8 A final ----
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=44); bass_bar(T,b,ch,vol=64,style='drive' if b==1 else '8ths')
        arp_bars(T,b,ch,vol=38,mode='updown')
        arp_bars(T,b,ch,vol=24,mode='up',octv=1)
        drums(T,b,'push' if b in (1,3) else 'four','16ths')
    crash_row(T,0,vol=50); crash_row(T,32,vol=44)
    melody(T,hookA2(),INS['lead'],vol=62,harm=True,chords=PROG_A,harm_vol=42)
    for i in range(0,16,2): spark_row(T,i,vol=22)
    fill(T,3,'snare16',vol=54,start=8)
    P.append(T.p)

    # ---- P9 Outro -> loops back to intro ----
    T=Tr()
    for b,ch in enumerate(PROG_O):
        pad_bar(T,b,ch,vol=46 if b<3 else 44)
        if b<3: bass_bar(T,b,ch,vol=56,style='8ths' if b!=1 else 'push')
        arp_bars(T,b,ch,vol=34,mode='updown')
        if b<3: drums(T,b,'basic','8ths')
    crash_row(T,0,vol=44)
    melody(T,hookOut(),INS['lead'],vol=58,harm=True,chords=PROG_O,harm_vol=36)
    fill(T,3,'snare16',vol=50,start=12)
    rim_row(T,60,vol=30); rim_row(T,62,vol=32)
    P.append(T.p)

    for p in P: xm.add_pattern(p)
    xm.order=list(range(len(P)))
    for I in ins:
        xm.add_instrument([dict(data=I['data'],name=I['name'],volume=I['vol'],panning=I['pan'],finetune=0,
                                relnote=I['relnote'],loop=((0,len(I['data'])) if I['loop'] else None),bits=16)],I['name'])
    return xm

if __name__=='__main__':
    xm=build(); xm.save('work/f4.xm')
    L,R=render_xm(xm,'f4')
    print('dur %.2f peak %.3f rms %.4f corr %.3f side/mid %.3f'%(len(L)/44100,max(np.abs(L).max(),np.abs(R).max()),
          np.sqrt(((L**2).mean()+(R**2).mean())/2),np.corrcoef(L,R)[0,1],
          np.sqrt((((L-R)/2)**2).mean())/np.sqrt((((L+R)/2)**2).mean())))
