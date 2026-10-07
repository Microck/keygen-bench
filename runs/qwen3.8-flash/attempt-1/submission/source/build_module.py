import sys; sys.path.insert(0,'/workspace/build')
from song import *
import json

INST={'kick':1,'snare':2,'hatc':3,'fato':4,'clap':5,'shak':6,'tom':7,'ltom':8,'hit':9,
      'crash':10,'riser':11,'bass':12,'sub':13,'sync':14,'steel':15,'harpsi':16,'pad':17,
      'lead':18,'soft':19,'stab':20,'arp':21,'swell':22}
# channel: name -> (channel index, instrument key, panning-ish role)
CHS=[('kick','kick'),('snare','snare'),('hatc','hatc'),('fato','fato'),('clap','clap'),
     ('shak','shak'),('tom','tom'),('ltom','ltom'),('bass','bass'),('sub','sub'),
     ('sync','sync'),('steel','steel'),('harpsi','harpsi'),('pad1','pad'),('pad2','pad'),
     ('lead','lead'),('lead2','soft'),('stab','stab'),('fx','crash')]
CHAN={name:k for k,(name,_) in enumerate(CHS)}
CHIN={name:inst for name,inst in CHS}
ROWS=16; HALF=32
NPAT=36                     # 72 bars

def vol(v,trim=1.0):
    a=max(0.0,min(1.0,v))/trim
    x=16+48*a
    return 0 if x<=16.4 else max(0,min(64,int(round(x))))
# arrangement amplitudes are on a 0..64 scale; TRIM compensates per-sample peak levels
TRIMF={'bass':1.18,'sub':1.20,'sync':0.96,'steel':0.19,'harpsi':0.16,'pad':0.41,'lead':0.54,
 'soft':0.40,'stab':0.35,'arp':0.16,'kick':1.42,'snare':0.92,'clap':0.27,'hatc':0.22,'fato':0.11,
 'shak':0.14,'hit':0.27,'tom':0.60,'ltom':0.64,'crash':0.22,'riser':0.38,'swell':0.36,'inst':0.55}
def V(v,inst):
    t=TRIMF.get(inst,0.6)
    return vol(v/64.0*t, 1.0)

class Pat:
    def __init__(self): self.grid={}; self.rows=HALF
    def setcell(self,row,ch,note,inst,v,force=False):
        ci = ch if isinstance(ch,int) else CHAN[ch]
        k=(row,ci)
        if (not force) and k in self.grid and self.grid[k][2]!=0 and self.grid[k][2]!=97:
            return False                    # keep existing real note
        self.grid[k]=(row,ci,note,inst,v)
        return True
    def note(self,row,ch,note,inst,v,off=None):
        if v<=0: return
        ok=self.setcell(row,ch,note,inst,v,force=True)
        if ok and off is not None:
            r2=min(row+off,self.rows-1)
            if r2>row:
                self.setcell(r2,ch,97,0,0,force=False)
    @property
    def cells(self):
        return [self.grid[k] for k in sorted(self.grid)]
P=[Pat() for _ in range(NPAT)]
def loc(b): return b%2
def pat(b): return b//2
def note_cell(b): return P[pat(b)]

# ---------- layers ----------
def drums(bars, spec):
    for i,b in enumerate(list(bars)):
        p=note_cell(b); off=loc(b)*ROWS
        k = spec[i%len(spec)] if isinstance(spec,list) else spec
        for ch,key in k.items():
            if not key: continue
            kk = key
            inst=CHIN[ch]
            for r,v in (DRUMS[kk] if isinstance(kk,str) else kk):
                p.note(off+r, CHAN[ch], 61, INST[inst], V(v,inst))
def bass(bars, prog, style, amp, inst='bass'):
    for i,b in enumerate(bars):
        p=note_cell(b); off=loc(b)*ROWS
        st = style[i%len(style)] if isinstance(style,list) else style
        for r,n,v in bass_walk(prog,b%8,st):
            p.note(off+r, CHAN['bass'], n, INST[inst], V(amp*v/50.0,inst), off=(3 if st in ('drive','gallop') else (2 if st=='punk' else 14)))
def subs(bars, prog, style, amp):
    for b in bars:
        p=note_cell(b); off=loc(b)*ROWS
        for r,n,v in bass_sub(prog,b%8,style):
            p.note(off+r, CHAN['sub'], n, INST['sub'], V(amp,'sub'), off=(15 if style=='hold' else 3))
def pads(bars, prog, voic, a1, a2):
    for b in bars:
        p=note_cell(b); off=loc(b)*ROWS
        for j,n in enumerate(pad_voicing(prog,b%8,voic)):
            ch='pad1' if j==0 else 'pad2'
            p.note(off, CHAN[ch], n, INST['pad'], V(a1 if j==0 else a2,'pad'), off=15)
def arps(bars, prog, kind, shape, octv, amp, ch, inst):
    for b in bars:
        p=note_cell(b); off=loc(b)*ROWS
        ev = arp_shape(prog,b%8,shape,octv) if kind=='16' else arp_8th(prog,b%8,shape,octv)
        for r,n,v in ev:
            p.note(off+r, CHAN[ch], n, INST[inst], V(amp*v/42.0,inst), off=(2 if inst=='harpsi' else 3))
def melody(bars, prog, mel, amp, ch, inst, transpose=0):
    for i,b in enumerate(bars):
        p=note_cell(b); off=loc(b)*ROWS
        a = amp[i%len(amp)] if isinstance(amp,list) else amp
        for r,n,d in lead_events(prog,mel,b%8,0):
            p.note(off+r, CHAN[ch], n+transpose, INST[inst], V(a,inst), off=max(1,min(15-r,d)))
def pads2(bars, prog, voic, a1, a2):
    for b in bars:
        p=note_cell(b); off=loc(b)*ROWS
        for j,n in enumerate(pad_voicing(prog,b%8,voic)[1:]):
            p.note(off+6, CHAN['pad2'], n, INST['pad'], V(a2,'pad'), off=ROWS-7)

def stabs(bars, prog, patt, amp):
    for i,b in enumerate(bars):
        k = patt[i%len(patt)] if isinstance(patt,list) else patt
        if not k: continue
        p=note_cell(b); off=loc(b)*ROWS
        ns=pad_voicing(prog,b%8,'B')
        rows={'A':[2,5,8,11],'B':[3,7,10],'C':[0,4,8],'D':[1,4,7,9],'E':[2,6,10]}[k]
        for r in rows:
            for n in ns:
                p.note(off+r, CHAN['stab'], n, INST['stab'], V(amp,'stab'))
def fill(bars, key):
    for i,b in enumerate(bars):
        k = key[i%len(key)] if isinstance(key,list) else key
        if not k: continue
        p=note_cell(b); off=loc(b)*ROWS
        for r,(which,v,semi) in FILLS[k]:
            base={'tom':61,'ltom':61,'hit':61}[which]
            ch='tom' if which=='tom' else ('ltom' if which=='ltom' else 'hatc')
            p.note(off+r, CHAN[ch], base+semi, INST[which], V(v,which))
def fx(bars, items_fn):
    for i,b in enumerate(bars):
        its=items_fn(i,b)
        if not its: continue
        p=note_cell(b); off=loc(b)*ROWS
        for r,which,amp,semi,dur in its:
            ch='fx' if which in ('crash','riser','swell') else 'hatc'
            p.note(off+r, CHAN[ch], 61+semi, INST[which], V(amp,which), off=None)

def suppress_stale():
    """if a channel played in bar b-1 but not in bar b, cut it at row 0 of bar b"""
    prev=None
    for pi,p in enumerate(P):
        cur  ={ch for (r,ch,n,i,v) in p.cells if n not in (0,97) and r<16}
        cur2 ={ch for (r,ch,n,i,v) in p.cells if n not in (0,97) and r>=16}
        if prev is not None:
            for chn in prev-cur:
                p.setcell(0,chn,97,0,0,force=True)
        prev=cur2

R=range
BARS=lambda a,b: list(R(a,b))
# ============ ARRANGEMENT (72 bars) ============
# S1a 0-1 : sub drone + shaker + rising pad
subs(BARS(0,2),'A','hold',30)
pads(BARS(0,2),'A','A',20,18)
drums(BARS(0,2),[{'shak':[(r,14) for r in R(0,12)]},
                 {'shak':[(r,16) for r in R(0,12)],'hatc':[(4,22),(10,22)]}])
fx(BARS(0,2), lambda i,b: [(0,'riser',28,0,None)] if i==0 else [])
# S1b 2-3 : bass enters, first arp, kick break
subs(BARS(2,4),'A','hold',26)
bass(BARS(2,4),'A','drive',32)
pads(BARS(2,4),'A','A',22,20)
arps(BARS(2,4),'A','8','up',0,24,'steel','steel')
drums(BARS(2,4),[{'kick':'K_BRK','snare':'S_BRK','shak':'P_TAP'},
                 {'kick':'K_BRK','snare':'S_BB','shak':'P_TAP','hatc':'H_8'}])
# S1c 4-7 : soft lead, more motion, fill to verse
subs(BARS(4,8),'A','pulse',22)
bass(BARS(4,8),'A','drive',36)
pads(BARS(4,8),'A','A',20,18)
arps(BARS(4,8),'A','8','ud',0,26,'steel','steel')
melody(BARS(4,8),'A',VERSE_LEAD,[26,28,30,32],'lead2','soft')
drums(BARS(4,8),[{'kick':'K_V','snare':'S_BB','hatc':'H_8','shak':'P_TAP'},
                 {'kick':'K_V','snare':'S_BB','hatc':'H_8','shak':'P_HIT','fato':'O_OFF'},
                 {'kick':'K_V2','snare':'S_BB','hatc':'H_8','fato':'O_8','shak':'P_TAP'},
                 {'kick':'K_V','snare':'S_BB2','hatc':'H_12','shak':'P_HIT'}])
fill(BARS(4,8),[None,None,None,'F1'])
# S2 8-15 : VERSE 1 (full band)
subs(BARS(8,16),'A','pulse',20)
bass(BARS(8,16),'A','drive',42)
pads(BARS(8,16),'A','A',18,16)
arps(BARS(8,16),'A','16','ud',0,30,'harpsi','harpsi')
arps(BARS(8,16),'A','8','up',1,20,'steel','steel')
melody(BARS(8,16),'A',VERSE_LEAD,[40,42,42,44,40,42,42,44],'lead','lead')
drums(BARS(8,16),[{'kick':'K_V','snare':'S_BB','hatc':'H_8','shak':'P_TAP'},
                  {'kick':'K_V','snare':'S_BB','hatc':'H_12','shak':'P_HIT'},
                  {'kick':'K_V2','snare':'S_BB','hatc':'H_8','fato':'O_8','shak':'P_TAP'},
                  {'kick':'K_V','snare':'S_BB2','hatc':'H_12','shak':'P_HIT'},
                  {'kick':'K_V','snare':'S_BB','hatc':'H_8','shak':'P_TAP'},
                  {'kick':'K_V2','snare':'S_BB','hatc':'H_12','fato':'O_OFF'},
                  {'kick':'K_V','snare':'S_BB2','hatc':'H_8','shak':'P_HIT'},
                  {'kick':'K_V','snare':'S_BB','hatc':'H_12','clap':'P_TAP'}])
fill(BARS(8,16),[None,None,'F4',None,None,None,'F1',None])
fx(BARS(8,16), lambda i,b: [(0,'crash',22,0,None)] if i==0 else [])
# S3 16-23 : PRE-CHORUS (tension, offbeat bass, stabs)
subs(BARS(16,24),'P','hold',22)
bass(BARS(16,24),'P',['off','off','punk','punk','off','off','punk','punk'],42)
pads(BARS(16,24),'P','C',18,16)
arps(BARS(16,24),'P','16','up',0,26,'harpsi','harpsi')
melody(BARS(16,24),'P',PRE_LEAD,[36,38,40,40,42,40,42,44],'lead','lead')
stabs(BARS(16,24),'P',[None,'B',None,'B',None,'C',None,'D'],26)
drums(BARS(16,24),[{'kick':'K_P','snare':'S_BB','hatc':'H_8','shak':'P_TAP'},
                   {'kick':'K_P','snare':'S_BB','hatc':'H_12','shak':'P_HIT'},
                   {'kick':'K_P','snare':'S_BB2','hatc':'H_8','fato':'O_8'},
                   {'kick':'K_P','snare':'S_BB','hatc':'H_12','shak':'P_TAP'},
                   {'kick':'K_P','snare':'S_BB','hatc':'H_8','fato':'O_OFF'},
                   {'kick':'K_P','snare':'S_BB2','hatc':'H_12','shak':'P_HIT'},
                   {'kick':'K_P','snare':'S_BB','hatc':'H_16','fato':'O_8'},
                   {'kick':'K_P','snare':'S_BB','hatc':'H_16','shak':'P_TAP'}])
fill(BARS(16,24),[None,None,None,None,None,None,'F4','F2'])
fx(BARS(16,24), lambda i,b: ([(0,'riser',30,0,None)] if i>=6 else []))

# S4 24-31 : CHORUS A (prog C)
subs(BARS(24,32),'C','pulse',20)
bass(BARS(24,32),'C',['drive','drive','punk','drive','drive','punk','drive','drive'],48)
pads(BARS(24,32),'C','A',20,18)
arps(BARS(24,32),'C','16','ud',0,30,'harpsi','harpsi')
arps(BARS(24,32),'C','8','down',1,22,'steel','steel')
melody(BARS(24,32),'C',CHORUS_LEAD,[46,46,48,46,46,48,46,48],'lead','lead')
melody(BARS(24,32),'C',CHORUS_LEAD,[24,24,26,24,24,26,24,26],'lead2','soft',-12)
drums(BARS(24,32),[{'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_HIT','fato':'O_8'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_12','clap':'P_TAP'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_8','clap':'S_BB','fato':'O_OFF'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_12','clap':'P_HIT'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_TAP','fato':'O_8'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','clap':'S_BB'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_HIT','fato':'O_OFF'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_16','clap':'P_TAP'}])
fill(BARS(24,32),[None,'F4',None,'F1',None,'F4',None,'F2'])
fx(BARS(24,32), lambda i,b: [(0,'crash',24,0,None)] if i in (0,4) else [])
# S5 32-39 : CHORUS B (prog D)
subs(BARS(32,40),'D','pulse',20)
bass(BARS(32,40),'D',['punk','drive','punk','drive','punk','drive','drive','punk'],48)
pads(BARS(32,40),'D','B',20,18)
arps(BARS(32,40),'D','16','up',0,32,'harpsi','harpsi')
arps(BARS(32,40),'D','16','down',1,20,'steel','steel')
melody(BARS(32,40),'D',CHORUS_LEAD2,[46,48,46,48,46,48,46,48],'lead','lead')
stabs(BARS(32,40),'D',['A',None,'A',None,'A',None,'A',None],24)
drums(BARS(32,40),[{'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','clap':'P_HIT','fato':'O_8'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_TAP'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','clap':'S_BB','fato':'O_OFF'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_HIT'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','clap':'P_TAP','fato':'O_8'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'S_BB'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_16','clap':'P_HIT','fato':'O_OFF'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_12','clap':'P_TAP'}])
fill(BARS(32,40),[None,'F4',None,'F1',None,'F4',None,'F3'])
fx(BARS(32,40), lambda i,b: [(0,'crash',24,0,None)] if i in (0,6) else [])
# ============ second half ============
# S7 48-55 : BRIDGE (prog E, sync bass, high lead, sparse then build)
subs(BARS(48,56),'E','hold',26)
bass(BARS(48,56),'E',['drive','drive','punk','punk','off','off','punk','punk'],44,'bass')
pads(BARS(48,56),'E','C',18,16)
arps(BARS(48,56),'E','8','ud',0,24,'steel','steel')
arps(BARS(48,56),'E',[('16','up',0,20),('16','up',0,22),('16','up',0,24),('16','up',0,26),
                      ('16','up',0,28),('16','up',0,28),('16','up',0,30),('16','up',0,30)],26,'harpsi','harpsi') if False else None
melody(BARS(48,56),'E',BRIDGE_LEAD,[40,42,42,44,44,42,44,46],'lead','lead')
stabs(BARS(48,56),'E',[None,None,'B','B','C','C','D','D'],26)
drums(BARS(48,56),[{'kick':'K_BRIDGE','snare':'S_BB2','hatc':None},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_8'},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_8','fato':'O_8'},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_12','clap':'P_TAP'},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_12','clap':'P_HIT','fato':'O_OFF'},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_16','clap':'P_TAP'},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_12','clap':'P_HIT','fato':'O_8'},
                   {'kick':'K_BRIDGE','snare':'S_BB2','hatc':'H_16','clap':'S_BB'}])
arps(BARS(52,56),'E','16','ud',0,26,'sync','sync')     # acid ostinato joins in the 2nd half of the bridge
fill(BARS(48,56),[None,None,None,'F4',None,None,'F4','F3'])
fx(BARS(48,56), lambda i,b: [(0,'crash',22,0,None)] if i==0 else ([] if i<6 else [(0,'riser',32,0,None)]))
# S8 56-63 : FINAL CHORUS (prog C, melody octave up, everything on)
subs(BARS(56,64),'C','pulse',22)
bass(BARS(56,64),'C','punk',50)
pads(BARS(56,64),'C','C',20,18)
arps(BARS(56,64),'C','16','ud',0,34,'harpsi','harpsi')
arps(BARS(56,64),'C','16','up',1,24,'steel','steel')
melody(BARS(56,64),'C',CHORUS_LEAD,[46,46,48,46,46,48,46,48],'lead','lead',12)
melody(BARS(56,64),'C',CHORUS_LEAD,[28,28,30,28,28,30,28,30],'lead2','soft',0)
drums(BARS(56,64),[{'kick':'K_CH2','snare':'S_BB2','hatc':'H_16','clap':'S_BB','fato':'O_8'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_16','clap':'P_HIT'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_16','clap':'S_BB','fato':'O_OFF'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_16','clap':'P_TAP'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_16','clap':'S_BB','fato':'O_8'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_16','clap':'P_HIT'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_16','clap':'S_BB','fato':'O_OFF'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_16','clap':'P_TAP'}])
fill(BARS(56,64),[None,'F4',None,'F1',None,'F4',None,'F2'])
fx(BARS(56,64), lambda i,b: [(0,'crash',26,0,None)] if i in (0,4) else [])
# S9 64-71 : OUTRO (prog O) : hook echo, thinning to drone, last bar = G + riser
subs(BARS(64,72),'O','hold',26)
pads(BARS(64,72),'O','A',22,20)
arps(BARS(64,72),'O','8','up',0,26,'steel','steel')
melody(BARS(64,72),'O',[(('A-4',4),('C-5',4),('F-5',4),('E-5',4)),
                        (('C-5',6),('G-4',6),('E-4',12)),
                        (('F-5',8),('E-5',4),('C-5',8)),
                        (('A-4',12),)],34,'lead','lead')
bass(BARS(64,68),'O','drive',40)
drums(BARS(64,68),[{'kick':'K_V','snare':'S_BB','hatc':'H_8'},
                   {'kick':'K_V','snare':'S_BB','hatc':'H_8','shak':'P_TAP'},
                   {'kick':'K_BRK','snare':'S_BRK','hatc':None},
                   {'kick':'K_BRK','snare':None,'shak':[(r,14) for r in R(0,12)]}])
drums(BARS(68,72),[{'shak':[(r,13) for r in R(0,12)],'hatc':[(6,18)]},
                   {'shak':[(r,12) for r in R(0,12)]},
                   {'shak':[(r,12) for r in R(0,12)],'hatc':[(4,16),(10,16)]},
                   {'shak':[(r,13) for r in R(0,12)],'kick':'S_BRK'}])
fill(BARS(64,72),[None,'F4',None,'F5'])
fx(BARS(64,72), lambda i,b: [(0,'crash',22,0,None)] if i==0 else ([] if i<3 else [(0,'riser',30,0,None)]))

# S6 40-47 : SOLO / BREAK (prog D) - bars 40-41 half-time breather, then solo
subs(BARS(40,48),'D','hold',24)
bass(BARS(40,44),'D','hold',40)
bass(BARS(44,48),'D',['drive','drive','punk','punk'],46)
pads(BARS(40,48),'D','B',20,18)
arps(BARS(40,48),'D','16','ud',1,22,'arp','harpsi') if False else None
arps(BARS(42,48),'D','16','ud',0,24,'harpsi','harpsi')
melody(BARS(40,48),'D',SOLO_LEAD,[30,32,42,42,44,44,46,44],'lead','lead')
melody(BARS(44,48),'D',SOLO_LEAD,[24,24,26,26],'lead2','soft',-12) if False else None
drums(BARS(40,48),[{'kick':'K_P','snare':'S_BB','hatc':None,'shak':[(0,16),(6,16)]},
                   {'kick':'K_P','snare':None,'hatc':'H_8','shak':[(0,15),(6,15)]},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_TAP'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','fato':'O_8'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_8','clap':'P_HIT'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','clap':'S_BB'},
                   {'kick':'K_CH','snare':'S_BB2','hatc':'H_16','clap':'P_TAP','fato':'O_OFF'},
                   {'kick':'K_CH2','snare':'S_BB2','hatc':'H_12','clap':'P_HIT'}])
fill(BARS(40,48),[None,'F4',None,None,None,'F4',None,'F2'])
fx(BARS(40,48), lambda i,b: [(0,'crash',22,0,None)] if i in (0,2) else [])

# single-shot pluck arps (no keyoff - shots decay naturally)
def plucks(bars, prog, shape, octv, amp, ch='stab', inst='arp'):
    for b in bars:
        p=note_cell(b); off=loc(b)*ROWS
        ev = arp_8th(prog,b%8,shape,octv)
        for r,n,v in ev:
            p.note(off+r, CHAN[ch], n, INST[inst], V(amp*v/42.0,inst))
plucks(BARS(42,48),'D','ud',1,30,'stab','arp')
plucks(BARS(64,68),'O','up',1,26,'stab','arp')
fx(BARS(0,2), lambda i,b: [(0,'swell',20,0,None)])
fx(BARS(68,72), lambda i,b: [(0,'swell',18,0,None)] if i%2==0 else [])

suppress_stale()
