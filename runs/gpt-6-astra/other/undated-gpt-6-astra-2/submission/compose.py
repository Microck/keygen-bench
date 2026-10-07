import numpy as np, json, base64
rng=np.random.default_rng(729)
R=8363; calls=[]
def call(n,**a): calls.append(dict(name=n,arguments=a))
call('module_new',channels=12,name='HEX / Afterimage')
call('song_set',bpm=142,speed=6,length=32,loop_start=0)
def sample(i,name,x,vol=64,pan=128):
 x=np.asarray(x); x=x/max(1,np.max(np.abs(x)))*.92
 call('sample_create_from_pcm',instrument=i,pcm=base64.b64encode((x*32767).astype('<i2').tobytes()).decode(),encoding='int16',name=name)
 call('sample_set',instrument=i,volume=vol,panning=pan,relative_note=0)
 call('instrument_set',instrument=i,name=name)
def time(s): return np.arange(int(R*s))/R
def env(t,dec,a=.003):return np.minimum(t/a,1)*np.exp(-t/dec)*np.minimum((t[-1]-t)/.015,1)
t=time(.35); f=48+125*np.exp(-t/ .019); sample(1,'01 Silicon kick',np.sin(2*np.pi*np.cumsum(f)/R)*np.exp(-t/ .095)+.12*rng.normal(size=len(t))*np.exp(-t/.006),60)
t=time(.24); n=rng.normal(size=len(t)); n=np.r_[0,np.diff(n)]; sample(2,'02 Bitcrush clap',(.47*n+ .35*np.sin(2*np.pi*185*t))*env(t,.055,.001),46)
t=time(.09); n=rng.normal(size=len(t)); sample(3,'03 Closed silver',np.r_[0,np.diff(n)]*env(t,.017,.001),27,166)
t=time(.29); n=rng.normal(size=len(t)); sample(4,'04 Open silver',np.r_[0,np.diff(n)]*env(t,.072,.001),22,90)
f=261.625565
# Bass has a round fundamental and a short bright edge
t=time(.20); phase=2*np.pi*f*t
sample(5,'05 Neon rubber bass',(np.sin(phase)+.32*np.sin(2*phase)+.16*np.sin(3*phase)*np.exp(-t/.035))*env(t,.075),53)
t=time(.65); phase=2*np.pi*f*t+.018*np.sin(2*np.pi*5*t)
x=sum(np.sin(k*phase)/k for k in range(1,12,2))
sample(6,'06 Pixel ribbon',x*env(t,.24),42,112)
t=time(.5); phase=2*np.pi*f*t
x=sum(np.cos(k*phase)/k**1.3 for k in range(1,9))
sample(7,'07 Glass staircase',x*env(t,.10),27,190)
t=time(1.5);phase=2*np.pi*f*t
x=np.sin(phase)+.24*np.sin(2*phase)+.14*np.sin(phase*1.004)
sample(8,'08 Warm phosphor',x*env(t,.65,.035),26,66)
t=time(.65);phase=2*np.pi*f*t
sample(9,'09 Ribbon reflection',sum(np.sin(k*phase)/k for k in range(1,10,2))*env(t,.18),20,202)
t=time(.5); n=rng.normal(size=len(t));sample(10,'10 Boot sparkle',n*env(t,.1,.001),26,128)
# tracker note numbers: C-4 = 49; MIDI C4 = 60
# Em(add9), Cmaj7, G6, D; contrasting bridge Am C Em B7
chords=[(40,[64,67,71,74]),(36,[60,64,67,71]),(43,[62,67,71,76]),(38,[62,66,69,76])]
bridge=[(45,[60,64,69,71]),(36,[60,64,67,74]),(40,[59,64,67,74]),(35,[59,63,66,69])]
melodies=[[(0,76,3),(3,79,1),(4,83,2),(7,81,1),(8,79,3),(12,76,2),(14,74,2)],[(0,76,3),(4,79,2),(6,83,2),(8,84,3),(12,83,2),(14,79,2)],[(0,83,3),(3,81,1),(4,79,3),(8,78,2),(10,79,2),(12,76,4)],[(0,78,3),(4,81,2),(6,78,2),(8,74,3),(12,78,2),(14,75,2)]]
def cell(p,r,c,midi=None,inst=None,v=None,fx=None,param=None):
 a=dict(pattern=p,row=r,channel=c)
 if midi is not None:a['note']=midi-11
 if inst is not None:a['instrument']=inst
 if v is not None:a['volume']=16+v
 if fx is not None:a.update(effect=fx,effect_param=param)
 call('pattern_set_cell',**a)
for p in range(32):
 call('order_set',position=p,pattern=p);call('pattern_set_length',pattern=p,rows=16)
 section=p//8;j=(p//2)%4
 root,notes=(bridge if section==2 else chords)[j]
 # variations with 2 bars per chord
 sparse=section==2 and p%8<4
 for r in ([0,8] if sparse else [0,4,8,12]):cell(p,r,0,60,1,53 if r==0 else 48)
 for r in [4,12]:cell(p,r,1,60,2,45)
 if p%8==7:
  for r in [14,15]:cell(p,r,1,60,2,25 if r==14 else 34)
 for r in range(0,16,2):cell(p,r,2,60,3,22 if r%4==0 else 32)
 if not sparse:
  for r in [6,14]:cell(p,r,3,60,4,26)
 if p in [0,8,16,24]:cell(p,0,3,60,10,26)
 for r,delta in [(0,0),(3,0),(6,12),(8,0),(10,0),(14,7)]:
  cell(p,r,4,root+delta,5,48 if r%4==0 else 40)
 # alternating stereo rolling arpeggios
 for r in range(0,16,2 if sparse else 1):
  note=notes[[0,1,2,3,2,1,3,1][r%8]]+12
  cell(p,r,5,note,7,22 if r%4 else 30)
 # sustained dyad, finite envelopes
 for c,note in [(6,notes[0]),(7,notes[2])]:
  cell(p,0,c,note,8,29)
  cell(p,8,c,note,8,23)
 if section==2:
  motif=[(0,notes[2]+12,4),(6,notes[1]+12,2),(8,notes[0]+12,4),(14,notes[3]+12,2)]
 else:
  motif=melodies[j].copy()
  if p%2==1:
   motif=[(0,melodies[j][0][1],2),(2,notes[1]+12,2),(4,notes[2]+12,3),(8,notes[3]+12,2),(10,notes[2]+12,2),(12,notes[1]+12,2),(14,(75 if j==3 else notes[0]+12),2)]
  if section==3 and p%2:motif=[(r,n+ (12 if r==8 else 0),d) for r,n,d in motif]
 for r,n,d in motif:
  cell(p,r,8,n,6,43 if section!=2 else 36)
  # echo wraps naturally into next pattern; populated separately later
  end=r+d
  if end<16 and not any(rr==end for rr,_,_ in motif):cell(p,end,8,v=0)
  dest=(p+(r+3)//16)%32; rr=(r+3)%16
  cell(dest,rr,9,n,9,22)
 # flourish on the last bar of each phrase
 if p%8==7:
  for r,n in zip([12,13,14,15],[notes[0]+12,notes[1]+12,notes[2]+12,notes[3]+12]):cell(p,r,10,n,7,26)
call('module_save',path='/workspace/submission/tune.xm')
call('module_render',path='/workspace/submission/preview.wav',rate=44100,bits=16,amp=1)
json.dump(calls,open('/workspace/build.json','w'))
