import numpy as np, struct as S
from pathlib import Path
rng=np.random.default_rng(29)
out=Path('/workspace/submission')
def u16(x):return S.pack('<H',x)
def u32(x):return S.pack('<I',x)
def text(s,n):return s.encode()[:n].ljust(n,b'\0')
inst=[]
def add(name,w,vol=48,pan=128,loop=False,rel=0,env=None):
 w=np.asarray(w); w=np.clip(w,-1,1); pcm=(w*29000).astype(np.int16);inst.append((name,pcm,vol,pan,loop,rel,env))
p=np.arange(128)/128
# band limited pulse and bright triangle
pulse=sum(np.sin(2*np.pi*k*p)*np.sin(np.pi*k*.32)/k for k in range(1,30));pulse/=max(abs(pulse))
add('01 | phosphor lead',pulse,43,145,True,24,[(0,64),(2,62),(9,49),(20,40),(24,0)])
bass=sum(np.sin(2*np.pi*k*p)/k**1.5 for k in range(1,17));bass/=max(abs(bass))
add('02 | rubber sub',bass,53,128,True,24,[(0,64),(2,58),(8,40),(12,0)])
tri=2/np.pi*np.arcsin(np.sin(2*np.pi*p))
add('03 | glass pixels',.6*tri+.3*np.sin(4*np.pi*p)+.1*np.sin(14*np.pi*p),34,65,True,24,[(0,64),(2,50),(5,24),(9,0)])
add('04 | velvet chord',.65*np.sin(2*np.pi*p)+.2*np.sin(4*np.pi*p)+.1*np.sin(6*np.pi*p),27,170,True,24,[(0,0),(5,48),(17,44),(27,0)])
sr=22050
def t(d):return np.arange(int(sr*d))/sr
x=t(.34);f=48+150*np.exp(-x*38);kick=np.sin(2*np.pi*np.cumsum(f)/sr)*np.exp(-x*13)+rng.normal(0,.14,len(x))*np.exp(-x*150)
add('05 | pocket kick',kick,57,128,False,17)
x=t(.22);n=rng.normal(size=len(x));sn=.48*n*np.exp(-x*23)+.48*np.sin(2*np.pi*185*x)*np.exp(-x*28);sn=np.tanh(sn*1.5)*.8
add('06 | neon snare',sn,47,133,False,17)
x=t(.065);n=rng.normal(size=len(x));n=np.r_[0,np.diff(n)];add('07 | closed hat',n*.23*np.exp(-x*62),32,188,False,17)
x=t(.28);n=rng.normal(size=len(x));n=np.r_[0,np.diff(n)];add('08 | open hat',n*.19*np.exp(-x*14),29,70,False,17)
x=t(.8);n=rng.normal(size=len(x));add('09 | starburst',(.18*n+.09*np.sin(2*np.pi*4300*x))*np.exp(-x*5),38,100,False,17)
add('10 | echo trace',pulse,22,205,True,24,[(0,53),(3,36),(10,0)])
# channels: kick snare hats bass arp chord3 lead echo ornament
C=12; patterns=[]
def note(s):
 names={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11};return names[s[0]]+(1 if '#' in s else 0)+12*int(s[-1])+1
progress=[('F#2',['F#4','A4','C#5'],'F#'),('D2',['D4','F#4','A4'],'D'),('A2',['A3','C#4','E4'],'A'),('E2',['E4','G#4','B4'],'E')]
# two-bar melodic lines with deliberate gaps, pickups and repeated hook
melA=[[(0,'C#5',3),(4,'F#5',3),(8,'E5',2),(10,'C#5',2),(14,'A4',2),(18,'C#5',4),(24,'E5',2),(28,'F#5',3)],[(0,'A5',4),(6,'F#5',2),(10,'E5',2),(14,'D5',4),(20,'F#5',3),(26,'E5',2),(30,'C#5',2)],[(0,'E5',3),(4,'C#5',3),(8,'B4',2),(12,'A4',5),(20,'C#5',2),(24,'E5',3),(28,'F#5',3)],[(0,'G#5',4),(6,'F#5',2),(10,'E5',3),(16,'B4',3),(22,'D5',2),(26,'E5',2),(30,'F5',2)]]
melB=[[(0,'F#5',5),(6,'C#6',2),(10,'B5',2),(12,'A5',3),(18,'F#5',3),(22,'A5',2),(26,'G#5',2),(28,'F#5',3)],[(0,'A5',4),(6,'F#5',3),(10,'A5',2),(14,'D6',4),(20,'C#6',2),(24,'A5',3),(28,'F#5',3)],[(0,'E5',3),(4,'A5',3),(8,'C#6',4),(14,'B5',2),(18,'A5',3),(22,'E5',2),(26,'F#5',2),(30,'A5',2)],[(0,'B5',4),(6,'G#5',3),(10,'E5',3),(16,'F#5',2),(20,'G#5',2),(24,'B5',3),(28,'C#6',2),(30,'E6',2)]]
sections=['intro']*2+['A']*4+['B']*4+['break']*2+['A2']*4+['B2']*4+['outro']*4
for pi,sec in enumerate(sections):
 pat=np.zeros((32,C,5),dtype=np.uint8)
 def put(r,c,n=0,i=0,v=0,e=0,a=0):
  if 0<=r<32:pat[r,c]=[note(n) if isinstance(n,str) else n,i,v+16 if v else 0,e,a]
 ci=pi%4 if sec not in ('A','B','A2','B2') else (pi-(2 if sec=='A' else 6 if sec=='B' else 12 if sec=='A2' else 16))%4
 root,ch,_=progress[ci];rn=note(root);ch=[note(z) for z in ch]
 full=sec not in ('intro','break','outro');drums=sec!='break' and not(sec=='intro' and pi==0)
 if drums:
  for r in [0,8,16,24]+([14,30] if full else []):put(r,0,'C-4'.replace('-',''),5,52 if r%8==0 else 36)
  for r in [4,12,20,28]:put(r,1,'C4',6,46)
  if pi%4==1 and full:
   for r in [27,30,31]:put(r,1,'C4',6,25+(r%3)*6)
  for r in range(0,32,2):put(r,2,'C4',8 if r%8==6 else 7,23 if r%4==0 else 34)
 if sec!='intro' or pi==1:
  for r in [0,3,6,8,11,14,16,19,22,24,27,30]:put(r,3,rn+(12 if r%8==6 else 0),2,46 if r%8==0 else 38)
 for r in range(0,32,2):
  put(r,4,ch[[0,1,2,1,0,2,1,2][(r//2)%8]]+(12 if sec in ('B','B2') else 0),3,25 if r%4 else 33)
 for r in [0,16]:
  for j,z in enumerate(ch):put(r,5+j,z,4,23 if full else 30)
 if sec in ('A','A2','B','B2'):
  line=(melB if sec.startswith('B') else melA)[ci]
  for r,n,dur in line:
   put(r,8,n,1,43 if sec.startswith('B') else 39,4,0x24 if dur>=4 else 0)
   if r+dur<32:put(r+dur,8,97)
   put(r+3,9,n,10,19)
  if sec=='B2':
   for r in [2,10,18,26]:put(r,10,ch[(r//8)%3]+12,3,27,8,35)
 elif sec=='break':
  for r in [0,8,16,24]:put(r,8,ch[(r//8)%3]+12,3,39)
 elif sec=='outro' and pi<22:
  for r,n,d in melA[ci][:4]:put(r,8,n,10,26)
 if pi in [2,6,12,16,20]:put(0,11,'C4',9,37)
 if pi==23:
  # final tonic resolution and decay, then a clean stop
  pat[:]=0
  for j,n in enumerate(['F#3','A3','C#4']):put(0,5+j,n,4,30)
  put(0,3,'F#2',2,45);put(0,8,'F#5',1,38);put(7,8,97);put(3,9,'F#5',10,22);put(0,11,'C4',9,28)
 patterns.append(pat)
# XM binary
b=b'Extended Module: '+text('PHOSPHOR / 29',20)+b'\x1a'+text('original numpy studio',20)+u16(0x104)
b+=u32(276)+u16(len(patterns))+u16(0)+u16(C)+u16(len(patterns))+u16(len(inst))+u16(1)+u16(6)+u16(142)+bytes(range(len(patterns))).ljust(256,b'\0')
for pat in patterns:
 data=pat.tobytes();b+=u32(9)+b'\0'+u16(32)+u16(len(data))+data
for name,pcm,vol,pan,loop,rel,env in inst:
 h=u32(263)+text(name,22)+b'\0'+u16(1)+u32(40)+bytes(96)
 points=env or [(0,64),(1,64)]
 h+=b''.join(u16(t)+u16(v) for t,v in points).ljust(48,b'\0')+bytes(48)
 h+=bytes([len(points),0,0,0,0,0,0,0,1 if env else 0,0,0,0,0,0])+u16(256)+u16(0)+bytes(20)
 assert len(h)==263,len(h)
 size=len(pcm)*2
 sh=u32(size)+u32(0)+u32(size if loop else 0)+bytes([vol,0,17 if loop else 16,pan])+S.pack('b',rel)+b'\0'+text(name,22)
 delta=(pcm.astype(np.int32)-np.r_[0,pcm[:-1]].astype(np.int32)).astype('<i2').tobytes()
 b+=h+sh+delta
(out/'tune.xm').write_bytes(b)
print(len(b),'bytes',len(patterns)*32*6*2.5/142,'seconds')
