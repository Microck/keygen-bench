#!/usr/bin/env python3
"""Generate samples as 16-bit WAVs + instr.json calls for NEBULA KEYGEN."""
import numpy as np, json, wave, os

os.makedirs('work/samples', exist_ok=True)
calls=[]
def call(tool, **kw): calls.append({'name':tool,'arguments':kw})

def wsave(path, pcm):
    w=wave.open(path,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(8363)
    w.writeframes((np.clip(pcm,-1,1)*32767).astype('<i2').tobytes()); w.close()

META={}
def inst(i, pcm, name, vol, pan, rel=0, ft=0, loop=None):
    p='work/samples/i%02d.wav'%i
    np.save('work/samples/i%02d.npy'%i, np.asarray(pcm,dtype=np.float64))
    META[i]={'name':name,'vol':vol,'pan':pan,'rel':rel,'ft':ft,'loop':loop}
    wsave(p,pcm)
    call('sample_load',path='/workspace/'+p,instrument=i,sample=0)
    a={'instrument':i,'sample':0,'name':name,'volume':vol,'panning':pan,'relative_note':rel,'finetune':ft}
    if loop: a.update({'loop_start':loop[0],'loop_length':loop[1],'flags':1})
    call('sample_set',**a)
    call('instrument_set',instrument=i,name=name)
    if i==1: call('instrument_set',instrument=1,name='LEAD pwm')

R=8363.0
def cycle(n,kind):
    t=np.arange(n)/n
    if kind=='saw':     return 2*(t%1)-1
    if kind=='pulse50': return np.where((t%1)<0.5,1.,-1.)
    if kind=='pulse25': return np.where((t%1)<0.25,1.,-1.)
    if kind=='tri':     return 4*np.abs((t%1)-0.5)-1
    if kind=='sawdet256':
        i=np.arange(256)/256.0
        return ((2*((i)%1)-1)+0.8*(2*((i*1.008)%1)-1)+0.8*(2*((i*0.994)%1)-1))/2.6

# 1 LEAD: PWM pulse, 512-pt loop (4 cycles) at +36 rel
i=np.arange(512)/128.0
pwm=np.clip(0.5+0.18*np.sin(2*np.pi*i/4.0),0.06,0.94)
lead=np.where((i%1.0)<pwm,1.,-1.)
# soften edges with a circular smooth (keeps loop seamless)
k=np.exp(-0.5*(np.arange(-3,4)/0.9)**2); k/=k.sum()
lead=np.convolve(np.r_[lead[-3:],lead,lead[:3]],k,'same')[3:-3]*0.9
inst(1, lead, 'LEAD', 52, 92, rel=36, loop=(0,512))
# 2 ECHO
inst(2, lead, 'ECHO', 40, 216, rel=36, loop=(0,512))
# 3 BASS: saw 32-cycle tiled, baked decay
N=32*96; inst(3, np.tile(cycle(32,'saw'),96)*(np.exp(-np.linspace(0,4.5,N))+0.12)*0.85, 'BASS', 56, 128)
# 4 ARP pluck: pulse25 decay
N=32*30; inst(4, np.tile(cycle(32,'pulse25'),30)*np.exp(-np.linspace(0,4.8,N))*0.9, 'ARP', 46, 140)
# 5 KICK (design 12545, trigger C-4 -> rel 7)
DK=12545; t=np.arange(int(0.19*DK))/DK
kick=np.sin(2*np.pi*(52+110*np.exp(-t*46))*t)*np.exp(-t*22)
kick[:4]*=np.linspace(0,1,4); kick-=np.convolve(kick,np.ones(96)/96,'same')
inst(5, kick, 'KICK', 64, 128, rel=7)
# 6 SNARE
DS=12545; t=np.arange(int(0.15*DS))/DS
nz=np.random.RandomState(7).randn(len(t))
k=np.convolve(nz,np.ones(3)/3,'same')-np.convolve(nz,np.ones(48)/48,'same')
snare=np.sin(2*np.pi*(190*np.exp(-t*9))*t)*np.exp(-t*42)+k*np.exp(-t*34)*2.4
snare[:2]*=np.linspace(0,1,2); snare/=np.abs(snare).max()*1.05
inst(6, snare, 'SNARE', 60, 128, rel=7)
# 7 HAT closed (33452 design, trigger C-5 -> rel 12)
DH=33452; t=np.arange(int(0.05*DH))/DH
nz=np.random.RandomState(3).randn(len(t))
hp=nz-np.convolve(nz,np.ones(24)/24,'same')
ch=hp*np.exp(-t*120)*0.9; ch/=np.abs(ch).max(); ch[:8]*=np.linspace(0,1,8)
inst(7, ch, 'HAT', 42, 72, rel=12)
# 8 O-HAT
t=np.arange(int(0.30*DH))/DH
nz=np.random.RandomState(5).randn(len(t))
hp=nz-np.convolve(nz,np.ones(24)/24,'same')
oh=hp*np.exp(-t*11)*0.9; oh/=np.abs(oh).max(); oh[:8]*=np.linspace(0,1,8)
inst(8, oh, 'O-HAT', 36, 184, rel=12)
# 9 RISER
t=np.arange(int(0.5*DH))/DH
nz=np.random.RandomState(9).randn(len(t))
lp=np.convolve(nz,np.ones(16)/16,'same')
ris=lp*np.minimum(t*8,1)*np.exp(-t*2.0)*0.8; ris/=np.abs(ris).max(); ris[:8]*=np.linspace(0,1,8)
inst(9, ris, 'RISER', 46, 128, rel=12)
# 10 PAD: detuned saw 256-cycle at +36
N=256*85
env=np.minimum(np.linspace(0,1.5,N),1.0)*np.exp(-np.linspace(0,4.2,N))*0.8
inst(10, np.tile(cycle(256,'sawdet256'),85)*env*0.75, 'PAD', 34, 150, rel=36)
# 11 CRASH: lowpassed noise
DC=8363; t=np.arange(int(1.4*DC))/DC
nz=np.random.RandomState(11).randn(len(t))
lp=np.convolve(nz,np.ones(10)/10,'same')
cr=lp*np.exp(-t*4.5); cr[:20]*=np.linspace(0,1,20); cr/=np.abs(cr).max()
inst(11, cr*0.8, 'CRASH', 30, 110)

json.dump(META,open('work/meta.json','w'))
json.dump(calls,open('work/instr.json','w'))
print('calls',len(calls))
