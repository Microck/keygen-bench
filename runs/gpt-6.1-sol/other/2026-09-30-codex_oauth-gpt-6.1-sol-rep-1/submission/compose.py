import numpy as np, struct, wave, os
S=16726; rng=np.random.default_rng(814)
OUT='/workspace/submission'
# XM notes follow FastTracker's C-0=1 numbering.
def note(n):
    names={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    return 1+names[n[:-1]]+12*int(n[-1])
def pitched(duration,kind):
    t=np.arange(int(S*duration))/S; f=261.625565; ph=f*t
    if kind=='lead':
        ph+=.0025*np.sin(2*np.pi*5.7*t)*(1-np.exp(-t*12))
        x=sum((2*np.sin(np.pi*k*.28)/(np.pi*k))*np.cos(2*np.pi*k*(ph-.14)) for k in range(1,24))
        x+=.2*np.sin(2*np.pi*ph)
        env=(1-np.exp(-t*650))*(.75+.25*np.exp(-t*14))*np.minimum(1,(duration-t)/.13)
    elif kind=='bass':
        x=.72*np.sin(2*np.pi*ph)+.24*np.sin(4*np.pi*ph)+.15*np.sin(6*np.pi*ph)+.10*np.sin(8*np.pi*ph)
        env=(1-np.exp(-t*650))*np.exp(-t*3)*np.minimum(1,(duration-t)/.023)
    elif kind=='arp':
        x=sum(np.sin(2*np.pi*k*ph)/k**1.2*np.exp(-t*k*9) for k in range(1,15))
        env=(1-np.exp(-t*1300))*np.exp(-t*7)*np.minimum(1,(duration-t)/.04)
    elif kind=='pad':
        x=np.zeros_like(t)
        for det in [-.003,0,.003]:
            for k in range(1,9): x+=np.sin(2*np.pi*k*ph*(1+det)+.4*k)/(k**1.9*3)
        env=(1-np.exp(-t*9))*np.minimum(1,(duration-t)/.45)*(.8+.2*np.cos(2*np.pi*.7*t))
    elif kind=='bell':
        x=np.sin(2*np.pi*ph)*np.exp(-t*3)+.45*np.sin(2*np.pi*ph*2)*np.exp(-t*7)+.2*np.sin(2*np.pi*ph*3)*np.exp(-t*12)
        env=(1-np.exp(-t*950))*np.minimum(1,(duration-t)/.12)
    elif kind=='counter':
        x=sum(((-1)**((k-1)//2))*np.sin(2*np.pi*k*ph)/(k*k) for k in [1,3,5,7,9])
        env=(1-np.exp(-t*250))*np.exp(-t*2)*np.minimum(1,(duration-t)/.12)
    return x*env

def drum(dur,kind):
    t=np.arange(int(S*dur))/S; noise=rng.normal(0,1,len(t)); high=noise-np.roll(noise,1)
    if kind=='kick':
        f=48+115*np.exp(-t*38); ph=np.cumsum(f)/S
        x=np.sin(2*np.pi*ph)*np.exp(-t*16)+.17*high*np.exp(-t*190)
    elif kind=='snare':
        # Tuned body plus crisp, short gated noise tail.
        filt=np.convolve(noise,[.22,.56,.22],mode='same')
        x=.62*filt*np.exp(-t*19)+.28*np.sin(2*np.pi*180*t)*np.exp(-t*30)+.10*high*np.exp(-t*70)
    elif kind in ['hat','open']:
        env=np.exp(-t*(95 if kind=='hat' else 19))
        x=(.26*high+.10*sum(np.sin(2*np.pi*f*t) for f in [3921,5173,6719]))*env
    elif kind=='tom':
        f=100+110*np.exp(-t*22); x=np.sin(2*np.pi*np.cumsum(f)/S)*np.exp(-t*13)+.08*noise*np.exp(-t*60)
    elif kind=='sweep':
        x=np.convolve(noise,[.25,.5,.25],mode='same')*(t/dur)**1.5*.4
    x*=np.minimum(1,t/.0015)*np.minimum(1,(dur-t)/.008)
    return x

spec=[('01 | phosphor pulse','lead',1.45,.74,128),('02 | rubber sub','bass',.17,.68,128),('03 | clockwork pluck','arp',.49,.65,64),('04 | velvet sky','pad',2.5,.63,128),('05 | pocket kick','kick',.36,.84,128),('06 | byte snare','snare',.24,.89,136),('07 | silver tick','hat',.09,.65,154),('08 | loose hi-hat','open',.32,.65,175),('09 | prism bell','bell',1.2,.66,185),('10 | triangle reply','counter',.82,.72,95),('11 | down tom','tom',.4,.77,106),('12 | reverse air','sweep',1.70,.65,128)]
samples=[]
for name,kind,dur,amp,pan in spec:
    x=pitched(dur,kind) if kind in ['lead','bass','arp','pad','bell','counter'] else drum(dur,kind)
    x=x/(max(abs(x))+.00001)*amp
    pcm=np.round(np.clip(x,-1,1)*32767).astype('<i2'); samples.append((name,pcm,pan))

NCH=14; pats=[]
def pat(): return np.zeros((32,NCH,5),dtype=np.uint8)
def put(p,r,c,n=None,i=0,v=None,fx=0,arg=0):
    if r<0 or r>=32:return
    p[r,c]=[note(n) if isinstance(n,str) else (n or 0),i,0x10+v if v is not None else 0,fx,arg]
def hit(p,r,c,i,v,n='C4',fx=0,arg=0):put(p,r,c,n,i,v,fx,arg)
# Each pattern is two bars. Melody is explicitly phrased, not an automatic random walk.
melA=[[(0,'A4',3),(3,'D5',3),(6,'F5',2),(8,'E5',2),(10,'D5',3),(14,'A4',2),(16,'C5',3),(19,'D5',3),(22,'F5',3),(26,'E5',2),(28,'D5',3)],
[(0,'F5',3),(4,'D5',3),(7,'A#4',2),(10,'A4',2),(12,'F4',3),(16,'A4',2),(18,'A#4',3),(22,'D5',2),(24,'F5',3),(28,'D5',3)],
[(0,'A4',3),(3,'C5',3),(6,'F5',3),(10,'G5',2),(12,'A5',3),(16,'G5',3),(20,'F5',3),(24,'E5',3),(28,'C5',3)],
[(0,'G4',3),(4,'C5',3),(8,'E5',3),(12,'D5',2),(14,'C5',2),(16,'G4',3),(20,'A4',3),(24,'C5',2),(26,'C#5',2),(28,'E5',3)]]
melB=[[(0,'D5',5),(6,'A5',3),(10,'G5',3),(14,'F5',3),(18,'E5',2),(20,'F5',4),(26,'D5',5)],
[(0,'F5',5),(6,'G5',2),(8,'A5',3),(12,'C6',5),(18,'A5',3),(22,'G5',3),(26,'F5',5)],
[(0,'G5',3),(4,'E5',3),(8,'C5',5),(14,'D5',3),(18,'E5',3),(22,'G5',3),(26,'E5',5)],
[(0,'C#5',3),(4,'E5',3),(8,'A5',5),(14,'G5',3),(18,'E5',3),(22,'C#5',3),(26,'A4',3),(30,'C#5',2)]]
chA=[['D3','F3','A3','C4'],['A#2','D3','F3','A3'],['F3','A3','C4','E4'],['C3','E3','G3','D4']]
chB=[['G2','A#2','D3','F3'],['A#2','D3','F3','A3'],['C3','E3','G3','D4'],['A2','C#3','E3','G3']]
# intro 4 bars; A 8; A' 8; air break 4; bridge 8; peak 8; coda 8.
sections=[('intro',2),('A',4),('Av',4),('break',2),('B',4),('peak',4),('out',4)]
for sec,count in sections:
  for k in range(count):
    p=pat(); idx=k%4
    chord=(chB if sec=='B' else chA)[idx]
    root=chord[0]; bassnote=note(root)-12
    active=sec not in ['break']
    # chord breathing, two 1-bar swells.
    for bar in [0,16]:
      for j in range(3):
        pn=note(chord[j])+12
        put(p,bar,8+j,pn,4, 12 if sec not in ['break','intro'] else 16,8,[60,128,196][j])
    # sixteenth arpeggio motif with space, delayed partner
    seq=[0,2,1,3,2,1,0,2,0,2,3,1,2,3,1,2]
    for r in range(0,32,2):
      if sec=='intro' and k==0 and r<16: continue
      if sec=='break' and r%4==2: continue
      arpnote=note(chord[seq[(r//2)%16]])+24
      if arpnote>note('G5'):arpnote-=12
      put(p,r,4,arpnote,3,27 if r%4==0 else 21,8,54)
      if r+3<32:put(p,r+3,5,arpnote,3,10,8,220)
    # Bass syncopation; ninth-note pickup toward the next phrase.
    if active:
      for r,delta,v in [(0,0,46),(6,0,36),(8,12,36),(12,0,42),(16,0,47),(22,0,35),(24,12,35),(28,0,42),(30,7,30)]:
        if sec=='intro' and k==0 and r<16:continue
        put(p,r,3,bassnote+delta,2,v)
    else:
      for r in [0,16]:put(p,r,3,bassnote,2,37)
    # Punchy four-on-floor, backbeat snare and lively hats.
    if active:
      for r in range(0,32,4):
        if sec=='intro' and k==0 and r<16:continue
        hit(p,r,0,5,52 if r%8==0 else 47)
      for r in [4,12,20,28]:
        if sec=='intro' and k==0:continue
        hit(p,r,1,6,43)
      for r in range(0,32,2):
        if sec=='intro' and k==0 and r<16:continue
        hit(p,r,2,7,20 if r%4==0 else 30)
      for r in [6,14,22,30]:
        if sec=='intro' and k==0:continue
        hit(p,r,12,8,21)
      if k==count-1 and sec in ['Av','B','peak']:
        for r,v in [(27,18),(29,24),(30,29),(31,37)]: hit(p,r,1,6,v)
        for r,n in [(26,'E4'),(28,'C4'),(30,'A3')]:hit(p,r,12,11,34,n)
    elif k==1:
      for r in [20,24,28]:hit(p,r,0,5,40)
      for r,v in [(26,18),(28,23),(30,29),(31,35)]:hit(p,r,1,6,v)
    # Lead and discrete right-channel echo, with rhythmic cuts for articulation.
    if sec in ['A','Av','B','peak'] or (sec=='out' and k<2):
      phrase=(melB if sec=='B' else melA)[idx]
      for r,n,l in phrase:
        nn=note(n)
        if sec=='Av' and r in [16,19,18] and idx in [0,1]:nn+=12
        if sec=='peak' and idx==3 and r>=16:nn+=12
        put(p,r,6,nn,1,(42 if sec=='peak' else 39) - (3 if r%4==2 else 0),8,116)
        # Cut before the next note, an audible breath rather than a drone.
        cut=min(r+l,31)
        if cut<32 and all(cut!=a[0] for a in phrase):put(p,cut,6,None,0,None,14,0xC2)
        if r+3<32:
          put(p,r+3,7,nn,1,14,8,205)
          if r+l+3<32:put(p,r+l+3,7,None,0,None,14,0xC2)
      if sec in ['Av','peak']:
        for r,j in [(2,2),(10,1),(18,3),(26,2)]:
          put(p,r,11,note(chord[j])+12,10,22,8,65)
    elif sec=='intro':
      for r,j in [(0,2),(12,3),(20,1),(28,2)]:
        put(p,r,11,note(chord[j])+24,9,24,8,178)
    elif sec=='break':
      for r,n in [(0,'A5'),(10,'F5'),(18,'D5'),(26,'C5')]:put(p,r,11,n,9,25,8,180)
      if k==1:hit(p,16,13,12,21)
    elif sec=='out':
      for r,j in [(0,0),(8,2),(20,1),(28,3)]:put(p,r,11,note(chord[j])+24,9,23)
    # Last eight bars gently thin out; the final C harmony turns back to D minor.
    if sec=='out' and k>=2:
      for r in range(32):
        if r%8!=0:p[r,0]=0
        p[r,1]=0; p[r,12]=0
        if r%4!=2:p[r,2]=0
      if k==3:
        for r in range(24,32):
          p[r,0:3]=0;p[r,3]=0
        for r,n in [(24,'G4'),(26,'A4'),(28,'C5'),(30,'C#5')]:
          put(p,r,6,n,1,28,8,116)
          put(p,r+1,6,None,0,None,14,0xC4)
    pats.append(p)
# Standard XM 1.04 serialization, editable notes and individually synthesized instruments.
def fixed(s,n):return s.encode('ascii')[:n].ljust(n,b'\0')
data=bytearray(b'Extended Module: '+fixed('Phosphor Nightdrive',20)+b'\x1a'+fixed('FT2 original studio',20)+struct.pack('<H',0x104))
data+=struct.pack('<I8H',276,len(pats),0,NCH,len(pats),len(samples),1,6,138)
data+=bytes(range(len(pats)))+bytes(256-len(pats))
for p in pats:
    raw=p.tobytes();data+=struct.pack('<IBHH',9,0,32,len(raw))+raw
for name,pcm,pan in samples:
    ih=bytearray(263)
    struct.pack_into('<I',ih,0,263);ih[4:26]=fixed(name,22);struct.pack_into('<H',ih,27,1);struct.pack_into('<I',ih,29,40)
    # no envelopes or mappings: timbre and articulation are in the samples and patterns
    data+=ih
    data+=struct.pack('<III',len(pcm)*2,0,0)+bytes([64,0,16,pan,12,0])+fixed(name,22)
    delta=(pcm.astype(np.int32)-np.r_[0,pcm[:-1].astype(np.int32)]).astype('<i2')
    data+=delta.tobytes()
open(OUT+'/tune.xm','wb').write(data)
print('Patterns:',len(pats),'seconds:',len(pats)*32*6*2.5/138,'size:',len(data))
