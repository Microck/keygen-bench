import numpy as np, wave
sr=44100
rng=np.random.default_rng(7)
def wav(path,x):
    x=np.asarray(x,float); x=np.clip(x,-1,1); xi=(x*32767).astype(np.int16)
    import wave
    with wave.open(path,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(xi.tobytes())
    print(f"wrote {path} len={len(xi)} peak={np.max(np.abs(x)):.3f}")

fC4=261.63
def periodic(freqs, amps, L):
    n=np.arange(L); out=np.zeros(L,float)
    for f,a in zip(freqs,amps):
        k=round(f*L/sr)
        if k<1: k=1
        out+=a*np.sin(2*np.pi*k*n/L)
    return out

# BASS
loop_len=22050
harms=list(range(1,13)); amps=[1/(k**0.85) for k in harms]
bass_loop=periodic([fC4*k for k in harms],amps,loop_len)+periodic([fC4],[0.9],loop_len)
bass_loop/=np.max(np.abs(bass_loop))
pre_len=22050
pre=np.zeros(pre_len)
for k,a in zip(harms,amps):
    pre+=a*np.sin(2*np.pi*fC4*k*np.arange(pre_len)/sr)
pre+=0.9*np.sin(2*np.pi*fC4*np.arange(pre_len)/sr)
pre/=np.max(np.abs(pre))
a_len=int(0.006*sr); pre[:a_len]*=np.linspace(0,1,a_len)
pre[:int(0.003*sr)]+=0.4*np.hanning(int(0.003*sr))*np.sign(np.sin(2*np.pi*1200*np.arange(int(0.003*sr))/sr))
X=400
tail=pre[-X:].copy(); head=bass_loop[:X].copy(); b=np.linspace(0,1,X)
blend=tail*(1-b)+head*b
bass=np.concatenate([pre[:-X], blend, bass_loop])
bass=np.tanh(bass*1.2)*0.85; bass/=np.max(np.abs(bass)); bass*=0.9
ls=pre_len  # loop starts after pre[:-X]+blend (len = pre_len)
ll=loop_len
print(f"bass total {len(bass)} loopstart {ls} looplen {ll}")
# verify loop wrap continuity: last vs first of loop
loopseg=bass[ls:ls+ll]
print(f" bass loop wrap diff {abs(loopseg[-1]-loopseg[0]):.4f} (should be small-ish, periodic)")
# check first-entry junction: sample before loop vs loop start
print(f" bass entry diff {abs(bass[ls-1]-bass[ls]):.4f}")
wav("/workspace/samples/bass.wav",bass)
print(f"BASSLOOP {ls} {ll}")

# LEAD
odds=[1,3,5,7,9,11,13,15]; amps2=[1/k for k in odds]
cents=5; ratio=2**(cents/1200)
lead_loop=periodic([fC4*k for k in odds],amps2,loop_len)+periodic([fC4*ratio*k for k in odds],[a*0.6 for a in amps2],loop_len)
lead_loop/=np.max(np.abs(lead_loop))
pre2=np.zeros(pre_len)
for k,a in zip(odds,amps2):
    pre2+=a*np.sin(2*np.pi*fC4*k*np.arange(pre_len)/sr)+0.6*a*np.sin(2*np.pi*fC4*ratio*k*np.arange(pre_len)/sr)
pre2/=np.max(np.abs(pre2))
pre2[:int(0.005*sr)]*=np.linspace(0,1,int(0.005*sr))
tail2=pre2[-X:].copy(); head2=lead_loop[:X].copy()
blend2=tail2*(1-b)+head2*b
lead=np.concatenate([pre2[:-X],blend2,lead_loop])
lead=np.tanh(lead*1.1)*0.8; lead/=np.max(np.abs(lead)); lead*=0.85
print(f"lead total {len(lead)} loopstart {pre_len} looplen {loop_len}")
wav("/workspace/samples/lead.wav",lead)
print(f"LEADLOOP {pre_len} {loop_len}")

# PAD: search loop len
fG=392.00
best=None
for ll2 in range(18000,26000):
    kC=round(fC4*ll2/sr); kG=round(fG*ll2/sr)
    eC=1200*np.log2((kC*sr/ll2)/fC4); eG=1200*np.log2((kG*sr/ll2)/fG)
    err=max(abs(eC),abs(eG))
    if best is None or err<best[0]:
        best=(err,ll2,kC,kG,eC,eG)
print("pad best",best)
_,pad_ll,_,_,_,_=best
pad_loop_len=pad_ll
det=[-6,0,6]
pad_loop=np.zeros(pad_loop_len)
for base in [fC4,fG]:
    for d in det:
        r=2**(d/1200)
        for k in range(1,9):
            amp=1/(k**1.1)*0.5
            kk=round(base*r*k*pad_loop_len/sr)
            pad_loop+=amp*np.sin(2*np.pi*kk*np.arange(pad_loop_len)/pad_loop_len + rng.uniform(0,2*np.pi))
pad_loop/=np.max(np.abs(pad_loop))
prepad_len=30000
prepad=np.zeros(prepad_len)
for base in [fC4,fG]:
    for d in det:
        r=2**(d/1200)
        for k in range(1,9):
            amp=1/(k**1.1)*0.5
            prepad+=amp*np.sin(2*np.pi*base*r*k*np.arange(prepad_len)/sr + rng.uniform(0,2*np.pi))
prepad/=np.max(np.abs(prepad))
att=int(0.12*sr); prepad[:att]*=np.linspace(0,1,att)
prepad*=np.linspace(0.6,1.0,prepad_len)
Xp=2000
tailp=prepad[-Xp:]; headp=pad_loop[:Xp]; blp=np.linspace(0,1,Xp)
blendp=tailp*(1-blp)+headp*blp
pad=np.concatenate([prepad[:-Xp],blendp,pad_loop])
pad*=0.75; pad/=np.max(np.abs(pad)); pad*=0.7
lsp=prepad_len; llp=pad_loop_len
print(f"pad total {len(pad)} loopstart {lsp} looplen {llp}")
wav("/workspace/samples/pad.wav",pad)
print(f"PADLOOP {lsp} {llp}")
