import sys, numpy as np
sys.path.insert(0,'/workspace/work')
from xmlib import Song, Instrument, Sample, Pattern, write_xm
import sounds3 as sy

S, NCYC, REL = 33452.0, 128, 24

def norm(x,p=0.9): return sy.norm(x,p)
def midi(name):
    names={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
           'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    body=name[:-1]
    if body.endswith('-'): body=body[:-1]
    return 12*(int(name[-1])+1)+names[body]
def n(m): return m-11

def additive(nn,kind,duty=0.5,harm=16): return sy.additive(nn,kind,duty,harm)

W = {}
W['lead']  = norm(additive(NCYC,'pulse',0.25,16)*0.72 + additive(NCYC,'saw',harm=8)*0.28, 0.46)
W['harm']  = norm(additive(NCYC,'pulse',0.125,12)*0.5 + additive(NCYC,'pulse',0.5,10)*0.5, 0.40)
W['arp']   = norm(additive(NCYC,'pulse',0.125,10), 0.42)
W['arp2']  = norm(additive(NCYC,'pulse',0.25,9),  0.34)
W['bass']  = norm(additive(NCYC,'tri',harm=9)*0.5 + additive(NCYC,'saw',harm=9)*0.5, 0.58)
W['pad']   = norm(additive(NCYC,'saw',harm=12), 0.34)
W['organ'] = norm(additive(NCYC,'pulse',0.5,12)*0.5 + additive(NCYC,'saw',harm=7)*0.5, 0.40)
W['soft']  = norm(additive(NCYC,'tri',harm=6), 0.34)
W['sub']   = norm(additive(NCYC,'tri',harm=4), 0.50)
W['bell']  = norm(additive(NCYC,'tri',harm=9)*0.6 + additive(NCYC,'sine',harm=1)*0.4, 0.40)

def loop_inst(name,pan,cycles,peak,env=None,fade=0,rel=REL,wave=None):
    w = wave if wave is not None else W.get(name, W['pad'])
    w = w - w.mean()   # kill DC (safe: integer cycles -> mean is loop mean)
    L=len(w); clean=np.tile(w,cycles); atk=w*(np.linspace(0,1,L)**0.4)
    pcm=norm(np.concatenate([atk,clean]),peak)
    smp=Sample(name,pcm,loop_start=L,loop_end=L*(1+cycles),relative_note=rel,panning=pan,volume=64)
    ins=Instrument(name,[smp],fadeout=fade)
    if env: ins.vol_env=env; ins.vol_type=1
    return ins

def shot(name,pcm,pan,peak,env=None,fade=0):
    pcm=np.asarray(pcm,float)
    if len(pcm)%2: pcm=np.concatenate([pcm,[0.0]])
    smp=Sample(name,norm(pcm,peak),loop=False,relative_note=REL,panning=pan,volume=64)
    ins=Instrument(name,[smp],fadeout=fade)
    if env: ins.vol_env=env; ins.vol_type=1
    return ins

NAMES=['lead','harm','arp','arp2','bass','sub','pad1','pad2','pad3','pad4','organ','bell',
       'kick','snare','clap','hatc','hato','crash','riser','shaker','soft','tick','lead2','organ2']
LEAD_ENV=[(0,0),(1,64),(12,50),(13,50)]
HARM_ENV=[(0,0),(1,54),(12,40),(13,40)]
ARP_ENV =[(0,0),(1,60),(5,46),(6,0)]
ARP2_ENV=[(0,0),(1,50),(5,36),(6,0)]
BASS_ENV=[(0,0),(1,64),(8,48),(9,48)]
PAD_ENV =[(0,0),(10,58),(18,50),(19,50)]
ORG_ENV =[(0,0),(1,58),(9,44),(10,44)]
BEL_ENV =[(0,0),(1,62),(9,20),(10,0)]

INSTRUMENTS=[
    loop_inst('lead', 148, 3, 0.46, LEAD_ENV, 0x1400),
    loop_inst('harm', 100, 3, 0.40, HARM_ENV, 0x1400),
    loop_inst('arp',   48, 3, 0.60, ARP_ENV,  0x2600),
    loop_inst('arp2', 208, 3, 0.50, ARP2_ENV, 0x2600),
    loop_inst('bass', 128, 2, 0.48, BASS_ENV, 0x3400),
    loop_inst('sub',  128, 4, 0.26, BASS_ENV, 0x3400, rel=12),
    loop_inst('pad1',  8,  2, 0.42, PAD_ENV, 0x00b0),
    loop_inst('pad2',  88, 2, 0.42, PAD_ENV, 0x00b0),
    loop_inst('pad3', 168, 2, 0.42, PAD_ENV, 0x00b0),
    loop_inst('pad4', 248, 2, 0.42, PAD_ENV, 0x00b0),
    loop_inst('organ',132, 2, 0.50, ORG_ENV, 0x2200),
    loop_inst('bell',  72, 3, 0.62, BEL_ENV, 0x3000),
    shot('kick',  sy.kick(),   128, 0.94),
    shot('snare', sy.snare(peak=0.85),  118, 0.85),
    shot('clap',  sy.clap(peak=0.6),   104, 0.60),
    shot('hatc',  sy.hat(peak=0.55), 206, 0.55),
    shot('hato',  sy.openhat(peak=0.45),176, 0.45),
    shot('crash', sy.crash(peak=0.55), 74, 0.55),
    shot('riser', sy.riser(dur=0.72, tail_fade=1400), 128, 0.32),
    shot('shaker',sy.hat(peak=0.42,decay=0.02,dur=0.08,seed=9), 110, 0.42),
    loop_inst('soft', 128, 2, 0.34, PAD_ENV, 0x0500, wave=W['soft']),
    shot('tick', sy.hat(peak=0.30, decay=0.006, dur=0.03, seed=13), 168, 0.30),
    loop_inst('lead2', 220, 3, 0.36, LEAD_ENV, 0x1400, wave=W['lead']),
    loop_inst('organ2', 64, 2, 0.40, ORG_ENV, 0x2200, wave=W['organ']),
]
IDX={k:i+1 for i,k in enumerate(NAMES)}

CHANNELS=24
CH=dict(lead=0,harm=1,arp=2,arp2=3,bass=4,sub=5,pad1=6,pad2=7,pad3=8,pad4=9,
        organ=10,bell=11,kick=12,snare=13,clap=14,hatc=15,hato=16,
        crash=17,riser=18,shaker=19,soft=10,echo=20,tick=21,lead2=22,organ2=23)

CHORDS = {
 'Am': dict(third=60, arp=[57,60,64,69], pad=[57,60,64,69], root=45),
 'F':  dict(third=57, arp=[57,60,65,69], pad=[53,57,60,65], root=41),
 'C':  dict(third=64, arp=[60,64,67,72], pad=[55,60,64,67], root=48),
 'G':  dict(third=59, arp=[59,62,67,71], pad=[55,59,62,67], root=43),
 'Dm': dict(third=65, arp=[62,65,69,74], pad=[50,53,57,62], root=38),
 'E':  dict(third=64, arp=[59,64,68,71], pad=[52,56,59,64], root=40),
 'Em': dict(third=64, arp=[59,64,67,71], pad=[52,55,59,64], root=40),
 'Bm': dict(third=62, arp=[59,62,66,71], pad=[54,59,62,71], root=47),
 'D':  dict(third=66, arp=[62,66,69,74], pad=[50,57,62,66], root=38),
 'A':  dict(third=64, arp=[61,64,69,73], pad=[57,61,64,69], root=45),
}
A_MINOR_PC={9,11,0,2,4,5,7}
def chord_pcs(name,shift=0):
    c=CHORDS[name]
    return set((x+shift)%12 for x in c['arp'])
def cd(name,shift=0):
    c=CHORDS[name]
    return dict(arp=[x+shift for x in c['arp']], pad=[x+shift for x in c['pad']],
                root=c['root']+shift, third=c['third']+shift)
def harmonize(m, pcs):
    for d in (3,4,5,2):
        if (m-d)%12 in pcs: return m-d
    return m-4
A_MINOR_SCALE={9,11,0,2,4,5,7}
def scale_pcs(shift=0):
    return set((pc+shift)%12 for pc in A_MINOR_SCALE)

class Composer:
    def __init__(self, name='Keygen Runner', bpm=156):
        self.song=Song(name,CHANNELS,bpm=bpm,speed=6)
        self.song.instruments=INSTRUMENTS
        self.pat=None
    def new(self,rows=64):
        p=Pattern(rows,CHANNELS); self.song.add_pattern(p); self.pat=p; return p
    VOL_SCALE=1.55
    def put(self,row,ch,note=None,ins=None,vol=None,fx=None,param=None):
        if vol is not None and isinstance(vol,(int,float)) and 0<=vol<=64:
            vol=max(1,min(64,int(round(vol*Composer.VOL_SCALE))))
        self.pat.set(row,CH[ch],note=note,ins=(IDX[ins] if isinstance(ins,str) else ins),vol=vol,fx=fx,param=param)
    def pad(self,row,chord,vol=12,shift=0,keyoff=None,voices=('pad1','pad2','pad3','pad4')):
        c=cd(chord,shift)
        for i,nm_ in enumerate(voices):
            self.put(row,nm_,note=n(c['pad'][i]),ins=nm_,vol=vol)
        if keyoff is not None:
            for nm_ in voices: self.put(keyoff,nm_,note='off')
    def bass(self,row,chord,vol=38,shift=0,style='8ths',sub=True):
        r=cd(chord,shift)['root']
        seqs={
          '8ths':  [(0,r),(2,r),(4,r),(6,r+12),(8,r),(10,r),(12,r+12),(14,r+7)],
          'drive': [(0,r),(2,r),(4,r+12),(6,r),(8,r+7),(10,r),(12,r+12),(14,r+7)],
          'gallop':[(0,r),(1,r),(3,r),(4,r),(6,r),(8,r),(9,r),(11,r),(12,r),(14,r)],
          'half':  [(0,r),(8,r+7)],
          'long':  [(0,r)],
          'oct':   [(0,r),(2,r+12),(4,r),(6,r+12),(8,r+7),(10,r),(12,r+12),(14,r+7)],
          'run':   [(0,r),(2,r),(4,r+7),(6,r+12),(8,r+12),(10,r+7),(12,r+12),(14,r+19)],
          'pump':  [(0,r),(3,r),(4,r),(7,r),(8,r),(11,r),(12,r),(15,r)],
          '16ths': [(i,r if i%4 else r) for i in range(16)],
        }
        for dr,nt in seqs[style]:
            self.put(row+dr,'bass',note=n(nt),ins='bass',vol=vol)
        if sub:
            for dr in (0,8):
                self.put(row+dr,'sub',note=n(r),ins='sub',vol=max(1,min(64,int(vol*0.50))))
    def arp(self,row,chord,mode='up',step=2,vol=24,ch='arp',shift=0,rows=16,start=0,skips=()):
        a=cd(chord,shift)['arp']
        pats={'up':[a[0],a[1],a[2],a[3]],
              'down':[a[3],a[2],a[1],a[0]],
              'updown':[a[0],a[1],a[2],a[3],a[2],a[1]],
              'wide':[a[0],a[2],a[1],a[3]],
              'oct':[a[0],a[0]+12,a[1],a[1]+12,a[2],a[2]+12,a[3],a[3]+12],
              'octup':[a[0],a[1],a[2],a[3],a[0]+12,a[1]+12,a[2]+12,a[3]+12],
              'pump':[a[0],a[2],a[1],a[3]],
              'up2':[a[0],a[1],a[2],a[3],a[1],a[2]]}
        pat=pats[mode]; k=start
        for dr in range(0,rows,step):
            if (dr % 16) in skips:
                k+=1; continue
            self.put(row+dr,ch,note=n(pat[k%len(pat)]),ins=ch,vol=vol)
            k+=1
        return k
    def organ(self,row,chord,vol=15,shift=0,rhythm=(2,6,10,14),sel='third'):
        c=cd(chord,shift)
        note={'root':c['root'],'third':c['third'],'root12':c['root']+12,'fifth':c['root']+7}[sel]
        for dr in rhythm:
            self.put(row+dr,'organ',note=n(note),ins='organ',vol=vol)
    def drums(self,row,style='full',vol=1.0,crash=False,chord_rows=16,fill=False,fill_at=None):
        SN=49
        def v(x): return max(1,min(64,int(round(x*vol))))
        if crash: self.put(row,'crash',note=SN,ins='crash',vol=v(26))
        blocks=64//chord_rows
        for b in range(blocks):
            r0=row+b*chord_rows
            if style in ('full','chorus','drive','dense'):
                for dr in (0,4,8,12): self.put(r0+dr,'kick',note=SN,ins='kick',vol=v(44))
                for dr in (4,12):     self.put(r0+dr,'snare',note=SN,ins='snare',vol=v(52))
                if style in ('chorus','dense'):
                    for dr in (4,12): self.put(r0+dr,'clap',note=SN,ins='clap',vol=v(32))
                if style in ('drive','dense','chorus'):
                    for dr in (7,15):
                        self.put(r0+dr,'snare',note=SN,ins='snare',vol=v(12))
                hstep = 1 if style in ('drive','dense') else 2
                for dr in range(0,chord_rows,hstep):
                    if dr%4==2 and style!='dense':
                        self.put(r0+dr,'hato',note=SN,ins='hato',vol=v(30))
                    else:
                        acc = 36 if dr%4==0 else 23
                        self.put(r0+dr,'hatc',note=SN,ins='hatc',vol=v(acc))
                if style=='dense':
                    for dr in range(2,chord_rows,4):
                        self.put(r0+dr,'shaker',note=SN,ins='shaker',vol=v(18))
            elif style=='half':
                for dr in (0,8): self.put(r0+dr,'kick',note=SN,ins='kick',vol=v(40))
                for dr in (4,12): self.put(r0+dr,'snare',note=SN,ins='snare',vol=v(42))
                for dr in range(0,chord_rows,2):
                    self.put(r0+dr,'hatc',note=SN,ins='hatc',vol=v(21))
            elif style=='light':
                for dr in (0,8): self.put(r0+dr,'kick',note=SN,ins='kick',vol=v(36))
                for dr in (4,12): self.put(r0+dr,'snare',note=SN,ins='snare',vol=v(38))
                for dr in range(0,chord_rows,4):
                    self.put(r0+dr,'hatc',note=SN,ins='hatc',vol=v(22))
            elif style=='sparse':
                self.put(r0,'kick',note=SN,ins='kick',vol=v(34))
                for dr in range(0,chord_rows,4):
                    self.put(r0+dr,'hatc',note=SN,ins='hatc',vol=v(17))
            elif style=='break':
                if b%2==0: self.put(r0,'kick',note=SN,ins='kick',vol=v(30))
                if b%2==1: self.put(r0+8,'snare',note=SN,ins='snare',vol=v(32))
        if fill:
            at = fill_at if fill_at is not None else row+chord_rows*blocks-8
            for i,dr in enumerate(range(at,at+8)):
                self.put(dr,'snare',note=SN,ins='snare',vol=v(22+i*5))
    def snare_roll(self,start,end,v0=12,v1=40,step=1):
        rows=list(range(start,end,step))
        for i,r in enumerate(rows):
            vol=int(v0+(v1-v0)*i/max(1,len(rows)-1))
            self.put(r,'snare',note=49,ins='snare',vol=vol)
    def phrase(self,row,notes,vol=36,ch='lead',shift=0,ins=None,harm=False,harm_vol=22,bar_chords=None,echo=False,echo_vol=14,echo_delay=3,vibrato=None):
        inst=ins or ch
        starts=set(r for r,_,_ in notes)
        for r,m,ln in notes:
            self.put(row+r,ch,note=n(m+shift),ins=inst,vol=vol)
            if vibrato and ln>=4:
                self.put(row+r,ch,note=n(m+shift),ins=inst,vol=vol,fx=4,param=vibrato)
            if r+ln not in starts: self.put(row+r+ln,ch,note='off')
        if harm:
            for r,m,ln in notes:
                pcs = chord_pcs(bar_chords[r//16], shift) if bar_chords else A_MINOR_PC
                self.put(row+r,'harm',note=n(harmonize(m+shift, pcs)),ins='harm',vol=harm_vol)
                if r+ln not in starts: self.put(row+r+ln,'harm',note='off')
        if echo:
            starts_e=set(r for r,_,_ in notes)
            for r,m,ln in notes:
                rr=r+echo_delay; ll=ln
                if rr>62: continue
                if rr+ll>63: ll=63-rr
                if ll<1: ll=1
                self.put(row+rr,'echo',note=n(m+shift),ins='lead2',vol=echo_vol)
                if rr+ll<=63 and (r+ln) not in starts_e:
                    self.put(row+rr+ll,'echo',note='off')
    def riser(self,row,vol=22): self.put(row,'riser',note=49,ins='riser',vol=vol)
    def run_up(self,row,notes,vol=24,ch='arp',ins=None,step=1):
        inst=ins or ch
        for i,mm in enumerate(notes):
            self.put(row+i*step,ch,note=n(mm),ins=inst,vol=vol)
    def chime_hook(self,row,chord,vol=13,shift=0,octave=24,pattern=None):
        """Signature keygen arpeggio: rapid up-down through chord tones in high octaves."""
        a=cd(chord,shift)['arp']
        seq = pattern or [a[0],a[2],a[1],a[3],a[2],a[0],a[1],a[3]]
        for i,mm in enumerate(seq):
            self.put(row+i*2,'bell',note=n(mm+octave),ins='bell',vol=vol)
            self.put(row+i*2+1,'bell',note='off')
    def ticks(self,row,vol=8,step=2,offset=0,ch='tick',rows=64):
        for dr in range(offset,rows,step):
            self.put(row+dr,ch,note=49,ins='tick',vol=vol)
    def bell(self,row,m,vol=20): self.put(row,'bell',note=n(m),ins='bell',vol=vol)
    def sparkle(self,row,chord,vol=9,shift=0,step=2,rows=16,octave=24,start=0):
        a=cd(chord,shift)['arp']
        pat=[a[0],a[1],a[2],a[3],a[2],a[1]]
        k=start
        for dr in range(0,rows,step):
            self.put(row+dr,'bell',note=n(pat[k%len(pat)]+octave),ins='bell',vol=vol)
            k+=1
    def counter(self,row,chord,vol=13,shift=0,rhythm=None,sel='fifth'):
        c=cd(chord,shift)
        note={'root':c['root'],'third':c['third'],'fifth':c['root']+7,
              'root12':c['root']+12}[sel]
        for dr in (rhythm or (0,8,12)):
            self.put(row+dr,'organ2',note=n(note),ins='organ2',vol=vol)
