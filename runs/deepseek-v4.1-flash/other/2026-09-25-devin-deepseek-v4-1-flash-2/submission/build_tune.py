"""Compose the keygen tune and write /workspace/submission/tune.xm"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xmbuild import XM, Instrument, Sample, save_xm
import sounds as S

SR=S.SR
PITCH={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(nm):
    o=int(nm[-1])
    p=nm[:-1].rstrip('-')
    return 49+PITCH[p]+12*(o-4)

CH = dict(kick=0, snare=1, hat=2, perc=3, bass=4, arp=5, lead=6, harm=7,
          pad1=8, pad2=9, pad3=10, fx=11, openhat=3)
NCH=12
ROWS=64          # 64 rows per pattern -> 6.4 s at 150 BPM / speed 6
ROW_S=0.1

CHORDS={
 'Am': ('A', [0,3,7]),
 'F' : ('F', [0,4,7]),
 'C' : ('C', [0,4,7]),
 'G' : ('G', [0,4,7]),
 'E' : ('E', [0,4,7]),
 'Dm': ('D', [0,3,7]),
}
def chord_notes(name, octv):
    root,iv=CHORDS[name]
    base=N(root+'-4')+12*(octv-4)
    return [base+i for i in iv]

# ---------------------------------------------------------------- instruments
def G(x, boost=1.0):
    return np.asarray(x,dtype=np.float64)*GAIN*boost

def build_instruments():
    ins=[]
    ins.append(Instrument('kick',[Sample('kick',G(S.kick(), DRUM),volume=64,panning=128,bits=16)]))
    ins.append(Instrument('snare',[Sample('snare',G(S.snare(), DRUM),volume=58,panning=132,bits=16)]))
    ins.append(Instrument('hat',[Sample('hat',G(S.hat(), DRUM),volume=42,panning=144,bits=16)]))
    ins.append(Instrument('openhat',[Sample('openhat',G(S.openhat(), DRUM),volume=32,panning=112,bits=16)]))
    ins.append(Instrument('crash',[Sample('crash',G(S.crash(), DRUM),volume=40,panning=128,bits=16)]))
    rng=np.random.default_rng(97)
    n=int(0.10*SR)
    noi=rng.standard_normal(n+1); noi=np.diff(noi); noi/=np.max(np.abs(noi))
    ins.append(Instrument('riser',[Sample('riser',G(noi*0.9),loop=(0,n),volume=64,panning=128,bits=16)],
                          vol_env=[(0,32),(16,64),(48,64)], vol_sus=2, fadeout=900))
    bw=S.looped(S.bass_wave())
    ins.append(Instrument('bass',[Sample('bass',G(bw),loop=(4,32),volume=56,panning=128,bits=16)],
                          vol_env=[(0,64),(2,62),(16,56),(40,46)], vol_sus=1, fadeout=5200))
    aw=S.looped(S.arp_wave())
    ins.append(Instrument('arp',[Sample('arp',G(aw),loop=(4,32),volume=38,panning=112,bits=16)],
                          vol_env=[(0,64),(2,62),(30,56)], vol_sus=1, fadeout=2600))
    lw=S.looped(S.lead_wave())
    ins.append(Instrument('lead',[Sample('lead',G(lw),loop=(4,32),volume=38,panning=142,bits=16)],
                          vol_env=[(0,64),(2,62),(24,52),(48,44)], vol_sus=2, fadeout=4200))
    l2=S.looped(S.pulse(32,0.5))
    ins.append(Instrument('lead2',[Sample('lead2',G(l2),loop=(4,32),volume=32,panning=114,bits=16)],
                          vol_env=[(0,64),(2,62),(24,52),(48,44)], vol_sus=2, fadeout=4200))
    pw=S.looped(S.pad_wave())
    ins.append(Instrument('padA',[Sample('padA',G(pw),loop=(4,32),volume=29,panning=84,bits=16)],
                          vol_env=[(0,0),(8,64),(96,64)], vol_sus=1, fadeout=4200))
    ins.append(Instrument('padB',[Sample('padB',G(pw),loop=(4,32),volume=27,panning=128,bits=16)],
                          vol_env=[(0,0),(8,64),(96,64)], vol_sus=1, fadeout=4200))
    ins.append(Instrument('padC',[Sample('padC',G(pw),loop=(4,32),volume=29,panning=172,bits=16)],
                          vol_env=[(0,0),(8,64),(96,64)], vol_sus=1, fadeout=4200))
    n=int(0.9*SR); t=np.arange(n)/SR
    pg=(np.sin(2*np.pi*1046.5*t)*np.exp(-t/0.32)
        +0.45*np.sin(2*np.pi*2093*t)*np.exp(-t/0.16)
        +0.20*np.sin(2*np.pi*3139.5*t)*np.exp(-t/0.07))
    pg[:12]*=np.linspace(0,1,12)
    ins.append(Instrument('ping',[Sample('ping',G(pg/np.max(np.abs(pg))*0.95),volume=36,panning=180,bits=16)]))
    ins.append(Instrument('tom',[Sample('tom',G(S.tom(), DRUM),volume=46,panning=96,bits=16)]))
    return ins

GAIN=0.325
DRUM=1.95   # keep the full mix inside full scale (renderers may use amp 16)

INST={name:i+1 for i,name in enumerate(
    ['kick','snare','hat','openhat','crash','riser','bass','arp','lead','lead2',
     'padA','padB','padC','ping','tom'])}

# ---------------------------------------------------------------- score helpers
class Song:
    def __init__(self, npat):
        self.xm=XM('Keygen Anthem',channels=NCH,speed=6,bpm=150)
        self.xm.instruments=build_instruments()
        self.xm.orders=list(range(npat))
        self.xm.restart=0
        for _ in range(npat):
            self.xm.add_pattern(ROWS)
        self.npat=npat
    def note(self,pat,row,ch,note,ins,vol=None,eff=0,par=0):
        v = 0x50 if vol is None else max(0x10, min(0x50, int(vol)))
        self.xm.set_cell(pat,row,ch,note=note,ins=INST[ins] if isinstance(ins,str) else ins,
                         vol=v,eff=eff,par=par)
    def keyoff(self,pat,row,ch):
        self.xm.set_cell(pat,row,ch,note=97,ins=0,vol=0,eff=0,par=0)
    def fx(self,pat,row,ch,eff,par):
        self.xm.set_cell(pat,row,ch,note=0,ins=0,vol=0,eff=eff,par=par)
    def vol(self,pat,row,ch,vol):
        self.xm.set_cell(pat,row,ch,note=0,ins=0,vol=max(0x10,min(0x50,int(vol))),eff=0,par=0)

# ---------------------------------------------------------------- parts
def drums(song, pat, prog, style='main'):
    k=CH['kick']; s=CH['snare']; h=CH['hat']; o=CH['openhat']
    if style=='none': return
    if style in ('main','build','fill'):
        for r in range(0,64,4):
            song.note(pat,r,k,N('C-4'),'kick',0x50)
        for r in (4,12,20,28,36,44,52,60):
            song.note(pat,r,s,N('C-4'),'snare',0x50)
        for r in range(0,64,2):
            song.note(pat,r,h,N('C-4'),'hat',0x38 if r%4==0 else 0x28)
        for r in range(0,64,4):
            if (r//4)%2==1:
                song.note(pat,r+2,o,N('C-4'),'openhat',0x30)
    if style=='build':
        for r in range(56,64,2):
            song.note(pat,r,s,N('C-4'),'snare',0x40)
    if style=='fill':
        # tom fill over the last bar
        for i,r in enumerate(range(48,64,2)):
            song.note(pat,r,CH['perc'],N(['A-3','A-3','C-4','C-4','D-4','D-4','E-4','E-4'][i]),'tom',0x44)
        song.note(pat,60,s,N('C-4'),'snare',0x48)
        song.note(pat,63,s,N('C-4'),'snare',0x50)
    if style=='outro':
        for r in range(0,48,4):
            song.note(pat,r,k,N('C-4'),'kick',0x50)
        for r in (4,12,20,28,36,44):
            song.note(pat,r,s,N('C-4'),'snare',0x50)
        for r in range(0,48,2):
            song.note(pat,r,h,N('C-4'),'hat',0x38 if r%4==0 else 0x28)
        for r in (2,6,10,14,18,22,26,30,34,38,42,46):
            if (r//2)%4==1:
                song.note(pat,r,o,N('C-4'),'openhat',0x30)
    if style=='busy':
        for r in range(0,64,4):
            song.note(pat,r,k,N('C-4'),'kick',0x50)
        song.note(pat,6,k,N('C-4'),'kick',0x40)
        song.note(pat,14,k,N('C-4'),'kick',0x40)
        song.note(pat,22,k,N('C-4'),'kick',0x40)
        song.note(pat,30,k,N('C-4'),'kick',0x40)
        song.note(pat,38,k,N('C-4'),'kick',0x40)
        song.note(pat,46,k,N('C-4'),'kick',0x40)
        song.note(pat,54,k,N('C-4'),'kick',0x40)
        song.note(pat,62,k,N('C-4'),'kick',0x40)
        for r in (4,12,20,28,36,44,52,60):
            song.note(pat,r,s,N('C-4'),'snare',0x50)
        for r in range(1,64,2):
            song.note(pat,r,h,N('C-4'),'hat',0x2c)
        for r in range(0,64,4):
            song.note(pat,r,h,N('C-4'),'hat',0x3a)
        for r in (3,11,19,27,35,43,51,59):
            song.note(pat,r,o,N('C-4'),'openhat',0x30)
    if style=='b':
        for r in range(0,64,4):
            song.note(pat,r,k,N('C-4'),'kick',0x50)
        for r in (8,16,24,40,48,56):
            song.note(pat,r,k,N('C-4'),'kick',0x44)
        for r in (4,12,20,28,36,44,52,60):
            song.note(pat,r,s,N('C-4'),'snare',0x50)
        for r in range(0,64,2):
            song.note(pat,r,h,N('C-4'),'hat',0x38 if r%8==0 else 0x26)
        for r in (2,10,18,26,34,42,50,58):
            song.note(pat,r,o,N('C-4'),'openhat',0x2e)
    if style=='sparse':
        for r in (0,16,32,48):
            song.note(pat,r,k,N('C-4'),'kick',0x50)
        for r in (8,24,40,56):
            song.note(pat,r,s,N('C-4'),'snare',0x44)
        for r in range(0,64,4):
            song.note(pat,r,h,N('C-4'),'hat',0x24)

def bassline(song, pat, prog, style='main'):
    b=CH['bass']
    if style=='none': return
    for bar,ch in enumerate(prog):
        base=bar*16
        root=N(CHORDS[ch][0]+'-2')
        if style=='main':
            seq=[(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,12)]
        elif style=='drive':
            seq=[(0,0),(1,12),(2,0),(3,12),(4,0),(6,12),(8,0),(9,12),(10,0),(12,7),(14,12)]
        elif style=='sparse':
            seq=[(0,0),(4,0),(8,0),(12,7)]
        elif style=='build':
            seq=[(0,0),(2,0),(4,0),(6,0),(8,0),(10,0),(12,0),(14,0)]
        else:
            seq=[(0,0)]
        for off,semi in seq:
            song.note(pat,base+off,b,root+semi,'bass',0x50)

def arpline(song, pat, prog, octv=5, style='main', ch=None):
    a = CH['arp'] if ch is None else ch
    if style=='none': return
    for bar,cname in enumerate(prog):
        tones=chord_notes(cname,octv)
        base=bar*16
        if style=='main':
            order=[0,1,2,1, 0,1,2,1, 0,1,2,1, 0,1,2,1]
        elif style=='up':
            order=[0,1,2,1, 0,1,2,1, 0,1,2,1, 0,1,2,1]
        elif style=='roll':
            order=[0,1,2,1, 2,1,2,1, 0,1,2,1, 2,1,0,1]
        else:
            order=[0,1,2,1]*4
        for i,idx in enumerate(order):
            song.note(pat,base+i,a,tones[idx],'arp',0x30 if i%4==0 else 0x24)

def pad(song, pat, prog, style='hold'):
    if style=='none': return
    for bar,cname in enumerate(prog):
        tones=chord_notes(cname,4)
        base=bar*16
        if style=='hold':
            song.note(pat,base,CH['pad1'],tones[0],'padA',0x40)
            song.note(pat,base,CH['pad2'],tones[1],'padB',0x3c)
            song.note(pat,base,CH['pad3'],tones[2],'padC',0x40)
        elif style=='swell':
            song.note(pat,base,CH['pad1'],tones[0],'padA',0x30)
            song.note(pat,base,CH['pad2'],tones[1],'padB',0x2c)
            song.note(pat,base,CH['pad3'],tones[2],'padC',0x30)

MIDI_NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def name_of(note):
    """Inverse of N(): XM note number -> note name."""
    q=note-49
    return MIDI_NAMES[q%12]+str(4+q//12)

def harmonize(melody, prog):
    """Build a consonant lower harmony line from a lead melody."""
    out=[]
    for (row, nm, dur, vol) in melody:
        if nm is None: continue
        bar=row//16
        cn=prog[bar]
        root,iv=CHORDS[cn]
        pcs={ (N(root+'-4')+i)%12 for i in iv }
        M=N(nm)
        pick=None
        for d in (3,4,5,8,9):
            cand=M-d
            if cand%12 in pcs:
                pick=cand; break
        if pick is None: pick=M-12
        while pick>=M: pick-=12
        out.append((row, name_of(pick), dur, min(vol,0x38)))
    return out

def melody(song, pat, notes, ch='lead', ins='lead', vib=True, transpose=0):
    """vib adds a gentle vibrato on sustained notes (depth 3, speed 6)."""
    for (row, nm, dur, vol) in notes:
        if nm is None: continue
        eff, par = (4, 0x36) if (vib and dur>=6) else (0,0)
        song.note(pat,row,CH[ch],N(nm)+transpose,ins,vol,eff,par)

# ---------------------------------------------------------------- melody data
MEL_A = [
 (0,'E-5',4,0x50),(4,'C-5',2,0x48),(6,'D-5',2,0x48),(8,'E-5',4,0x50),(12,'A-4',4,0x48),
 (16,'F-5',4,0x50),(20,'E-5',2,0x48),(22,'D-5',2,0x48),(24,'C-5',8,0x4c),
 (32,'E-5',4,0x50),(36,'G-5',4,0x50),(40,'E-5',4,0x4c),(44,'C-5',4,0x48),
 (48,'D-5',6,0x50),(54,'B-4',2,0x48),(56,'D-5',4,0x4c),(60,'G-5',4,0x50),
]
MEL_A2 = [
 (0,'A-5',4,0x50),(4,'E-5',2,0x48),(6,'F-5',2,0x48),(8,'E-5',4,0x50),(12,'C-5',4,0x48),
 (16,'D-5',4,0x50),(20,'C-5',2,0x48),(22,'D-5',2,0x48),(24,'F-5',8,0x50),
 (32,'E-5',4,0x50),(36,'C-5',4,0x4c),(40,'G-4',4,0x48),(44,'C-5',4,0x4c),
 (48,'B-4',8,0x50),(56,'D-5',4,0x4c),(60,'B-4',4,0x50),
]
MEL_B = [
 (0,'A-5',4,0x50),(4,'E-5',4,0x4c),(8,'C-5',4,0x48),(12,'D-5',4,0x4c),
 (16,'G-5',4,0x50),(20,'B-4',4,0x48),(24,'D-5',8,0x4c),
 (32,'E-5',4,0x50),(36,'G-5',4,0x50),(40,'C-6',4,0x50),(44,'G-5',4,0x4c),
 (48,'A-5',8,0x50),(56,'E-5',4,0x4c),(60,'B-4',4,0x50),
]
MEL_B2 = [
 (0,'E-5',4,0x50),(4,'A-5',2,0x4c),(6,'G-5',2,0x4c),(8,'E-5',4,0x4c),(12,'C-5',4,0x48),
 (16,'D-5',4,0x50),(20,'G-5',4,0x4c),(24,'B-5',8,0x50),
 (32,'A-5',8,0x50),(40,'G-5',4,0x50),(44,'E-5',4,0x48),
 (48,'B-4',4,0x48),(52,'D#5',4,0x4c),(56,'G#5',8,0x50),
]
MEL_BREAK = [
 (0,'A-4',8,0x3c),(8,'C-5',4,0x38),(12,'E-5',4,0x3c),
 (16,'F-5',8,0x3c),(24,'C-5',8,0x38),
 (32,'E-5',8,0x3c),(40,'G-5',4,0x3c),(44,'C-6',4,0x40),
 (48,'B-5',8,0x3c),(56,'G#5',8,0x38),
]
MEL_OUT = [
 (0,'A-5',4,0x50),(4,'F-5',4,0x4c),(8,'C-5',4,0x48),(12,'E-5',4,0x4c),
 (16,'G-5',4,0x50),(20,'D-5',4,0x4c),(24,'C-5',4,0x48),(28,'D-5',4,0x4c),
 (32,'C-5',4,0x50),(36,'E-5',4,0x4c),(40,'G-5',8,0x50),
]

# ---------------------------------------------------------------- arrangement
A=['Am','F','C','G']
B=['Am','G','F','E']
A2=['Am','F','C','E']

def compose():
    song=Song(13)
    # ---- 0 intro: pads + ping, sparse kick
    pad(song,0,A,'swell'); drums(song,0,A,'sparse')
    for r in range(0,64,8):
        song.note(0,r,CH['perc'],N('A-4') if r%16==0 else N('C-5'),'ping',0x30)
    arpline(song,0,A,5,'main')
    # ---- 1 intro B: bass + hats + open hat
    pad(song,1,A,'hold'); drums(song,1,A,'sparse')
    bassline(song,1,A,'sparse'); arpline(song,1,A,5,'main')
    for r in range(0,64,8):
        song.note(1,r,CH['perc'],N('A-4'),'ping',0x2c)
    # ---- 2 main A1
    drums(song,2,A,'main'); bassline(song,2,A,'main'); arpline(song,2,A,5,'main')
    melody(song,2,MEL_A); pad(song,2,A,'hold')
    song.note(2,0,CH['perc'],N('C-4'),'crash',0x44)
    # ---- 3 main A2
    drums(song,3,A,'main'); bassline(song,3,A,'main'); arpline(song,3,A,5,'main')
    melody(song,3,MEL_A2); pad(song,3,A,'hold')
    # ---- 4 B section 1
    drums(song,4,B,'b'); bassline(song,4,B,'drive'); arpline(song,4,B,5,'main')
    melody(song,4,MEL_B); pad(song,4,B,'hold')
    # ---- 5 B section 2
    drums(song,5,B,'b'); bassline(song,5,B,'drive'); arpline(song,5,B,5,'main')
    melody(song,5,MEL_B2); pad(song,5,B,'hold')
    song.note(5,0,CH['perc'],N('C-4'),'crash',0x48)
    # ---- 6 A repeat with harmony
    drums(song,6,A,'busy'); bassline(song,6,A,'drive'); arpline(song,6,A,5,'up')
    melody(song,6,MEL_A)
    melody(song,6,harmonize(MEL_A,A), ch='harm', ins='lead2')
    pad(song,6,A,'hold')
    # ---- 7 A repeat harmony swapped
    drums(song,7,A,'busy'); bassline(song,7,A,'drive'); arpline(song,7,A,5,'up')
    for i,r in enumerate(range(56,64,2)):   # tom fill into the breakdown
        song.note(7,r,CH['perc'],N(['A-3','C-4','D-4','E-4'][i%4]),'tom',0x3c)
    melody(song,7,MEL_A2)
    melody(song,7,harmonize(MEL_A2,A), ch='harm', ins='lead2')
    pad(song,7,A,'hold')
    # ---- 8 breakdown
    pad(song,8,B,'hold'); arpline(song,8,B,4,'main')
    melody(song,8,MEL_BREAK)
    song.note(8,0,CH['perc'],N('C-4'),'crash',0x3c)
    for r in range(0,64,16):
        song.note(8,r,CH['perc'],N('A-4') if r%32==0 else N('E-5'),'ping',0x2a)
    # ---- 9 build with riser
    drums(song,9,A2,'build'); bassline(song,9,A2,'build'); arpline(song,9,A2,5,'roll')
    melody(song,9,MEL_BREAK)
    song.note(9,0,CH['perc'],N('C-4'),'crash',0x40)
    song.fx(9,31,CH['fx'],0x0F,0xA5)      # lift to 165 BPM for the last bar
    song.note(9,32,CH['fx'],N('C-3'),'riser',0x30)
    song.fx(10,0,CH['fx'],0x0F,0x96)      # back to 150 BPM for the final section
    for r in range(33,62):
        song.fx(9,r,CH['fx'],1,0x0a)
    song.keyoff(9,62,CH['fx'])
    # ---- 10 full A with harmony + crash
    drums(song,10,A,'main'); bassline(song,10,A,'drive'); arpline(song,10,A,5,'main')
    melody(song,10,MEL_A)
    melody(song,10,harmonize(MEL_A,A), ch='harm', ins='lead2')
    pad(song,10,A,'hold')
    song.note(10,0,CH['perc'],N('C-4'),'crash',0x48)
    # ---- 11 B with harmony
    drums(song,11,B,'busy'); bassline(song,11,B,'drive'); arpline(song,11,B,5,'up')
    melody(song,11,MEL_B)
    melody(song,11,[(r,n,d,min(v,0x36)) for (r,n,d,v) in MEL_B2], ch='harm', ins='lead2')
    pad(song,11,B,'hold')
    # ---- 12 outro: three bars of the A progression, then a final Am chord
    #          whose release decays just before the loop seam
    drums(song,12,A,'outro')
    for bar,cn in enumerate(['Am','F','C']):
        base=bar*16
        root=N(CHORDS[cn][0]+'-2')
        for off,semi in [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,12)]:
            song.note(12,base+off,CH['bass'],root+semi,'bass',0x50)
        tones=chord_notes(cn,5)
        order=([0,1,2,1]*4) if bar<2 else ([0,1,2,1]*3)
        for i,idx in enumerate(order):
            song.note(12,base+i,CH['arp'],tones[idx],'arp',0x30 if i%4==0 else 0x24)
        pt=chord_notes(cn,4)
        song.note(12,base,CH['pad1'],pt[0],'padA',0x40)
        song.note(12,base,CH['pad2'],pt[1],'padB',0x3c)
        song.note(12,base,CH['pad3'],pt[2],'padC',0x40)
    melody(song,12,MEL_OUT)
    song.note(12,0,CH['perc'],N('C-4'),'crash',0x44)
    # release the moving parts before the final chord
    for r,ch in ((44,CH['arp']),(45,CH['bass']),(46,CH['lead']),(46,CH['harm']),
                 (45,CH['pad1']),(45,CH['pad2']),(45,CH['pad3'])):
        song.keyoff(12,r,ch)
    # final tonic chord, held and then released to fade out over the seam
    song.note(12,48,CH['perc'],N('C-4'),'crash',0x30)
    song.note(12,48,CH['bass'],N('A-2'),'bass',0x50)
    for ch_,nm,ins_ in ((CH['pad1'],'A-4','padA'),(CH['pad2'],'C-5','padB'),(CH['pad3'],'E-5','padC')):
        song.note(12,48,ch_,N(nm),ins_,0x48)
    song.note(12,48,CH['lead'],N('A-5'),'lead',0x48)
    # renderer-independent fade-out on the sustained voices (works even if the
    # instrument volume envelope is ignored by a player), then key-off release
    for r in range(58,63):
        song.fx(12,r,CH['bass'],0x0A,0x04)
        song.fx(12,r,CH['pad1'],0x0A,0x02)
        song.fx(12,r,CH['pad2'],0x0A,0x02)
        song.fx(12,r,CH['pad3'],0x0A,0x02)
    for r in range(55,61):
        song.fx(12,r,CH['lead'],0x0A,0x06)
    for r,ch in ((61,CH['bass']),(61,CH['lead']),(61,CH['pad1']),(61,CH['pad2']),(61,CH['pad3'])):
        song.keyoff(12,r,ch)
    # a crash ringing through the loop point keeps the seam musical
    song.note(12,58,CH['perc'],N('C-4'),'crash',0x2e)
    return song

if __name__=='__main__':
    song=compose()
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tune.xm')
    n=save_xm(song.xm,path)
    print('wrote',path,n,'bytes,',song.npat,'patterns,',NCH,'channels')
