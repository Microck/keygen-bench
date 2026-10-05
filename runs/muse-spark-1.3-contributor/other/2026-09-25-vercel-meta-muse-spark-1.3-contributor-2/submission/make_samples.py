import numpy as np, wave, pathlib
sr=44100
rng=np.random.default_rng(7)
def wav(path, x, sr=44100):
    x=np.asarray(x,dtype=np.float64)
    x=np.clip(x,-1,1)
    xi=(x*32767).astype(np.int16)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(xi.tobytes())
    print(f"wrote {path} len={len(xi)} ({len(xi)/sr:.3f}s) peak={np.max(np.abs(x)):.3f}")

fC4=261.63
# helper: integer-cycle sustain synth
def periodic_sustain(freqs, amps, sr, loop_len, phase=None):
    # freqs will be snapped? we pass exact desired; to make periodic, snap each freq to nearest integer cycle
    n=np.arange(loop_len)
    out=np.zeros(loop_len)
    for f,a in zip(freqs,amps):
        k=round(f*loop_len/sr)
        if k==0: k=1
        # snapped freq implied by k
        out+=a*np.sin(2*np.pi*k*n/loop_len)
    return out

# ---------- BASS (recorded at C4, played low) ----------
N=int(sr*1.2)
t=np.arange(N)/sr
# attack portion 0.15s then periodic sustain
loop_len=22050  # 0.5s
# freqs: harmonics of C4
harms=list(range(1,13))
amps=[1/(k**0.85) for k in harms]
# sub sine boost
bass_loop=periodic_sustain([fC4*k for k in harms],[a for a in amps],sr,loop_len)
bass_loop+=periodic_sustain([fC4],[0.9],sr,loop_len)
bass_loop/=np.max(np.abs(bass_loop))
# envelope: attack 6ms, sustain full, slight decay to 0.85 at end? keep flat for loop
a_len=int(0.006*sr)
attack_seg=np.linspace(0,1,a_len)
pre_len=N-loop_len
# build pre (attack + timbre blend): use non-snapped version for natural attack then crossfade into loop
pre=np.zeros(pre_len)
for k,a in zip(harms,amps):
    pre+=a*np.sin(2*np.pi*fC4*k*np.arange(pre_len)/sr)
pre+=0.9*np.sin(2*np.pi*fC4*np.arange(pre_len)/sr)
pre/=np.max(np.abs(pre))
pre[:a_len]*=attack_seg
# click
pre[:int(0.003*sr)]+=0.4*np.hanning(int(0.003*sr))*np.sign(np.sin(2*np.pi*1200*np.arange(int(0.003*sr))/sr))
# crossfade pre tail into loop start over 200 samples to avoid discontinuity
X=400
tail=pre[-X:].copy(); head=bass_loop[:X].copy()
# simple: blend
blend=np.linspace(0,1,X)
bass_loop[:X]=tail*(1-blend)+head*blend  # hmm tail was pre end; better to regenerate: actually set pre end to match? alternative: crossfade pre->loop
# assemble
bass=np.concatenate([pre[:-X], tail*(1-blend)+head*blend, bass_loop[X:]])
# overall scale + slight saturation
bass=np.tanh(bass*1.2)*0.85
# normalize
bass/=np.max(np.abs(bass)); bass*=0.9
bass_loopstart=len(bass)- (loop_len-X)
bass_looplen=loop_len-X
print(f"bass total {len(bass)} loopstart {bass_loopstart} looplen {bass_looplen}")
wav("/workspace/samples/bass.wav", bass)
print("BASSLOOP",bass_loopstart,bass_looplen)

# ---------- LEAD square (C4) ----------
N2=int(sr*1.2)
loop_len2=22050
odds=[1,3,5,7,9,11,13,15]
amps2=[1/(k**1.0) for k in odds]
# two detuned voices: +0 and +4 cents
cents=5
ratio=2**(cents/1200)
lead_loop=periodic_sustain([fC4*k for k in odds],amps2,sr,loop_len2)
lead_loop2=periodic_sustain([fC4*ratio*k for k in odds],[a*0.7 for a in amps2],sr,loop_len2)
# snapping second voice separately causes beating that breaks periodicity slightly; but both snapped to grid so beating is quantized - ok
lead_loop=(lead_loop+lead_loop2*0.6)
lead_loop/=np.max(np.abs(lead_loop))
a_len2=int(0.005*sr)
pre_len2=N2-loop_len2
pre2=np.zeros(pre_len2)
for k,a in zip(odds,amps2):
    pre2+=a*np.sin(2*np.pi*fC4*k*np.arange(pre_len2)/sr)+0.6*a*np.sin(2*np.pi*fC4*ratio*k*np.arange(pre_len2)/sr)
pre2/=np.max(np.abs(pre2))
pre2[:a_len2]*=np.linspace(0,1,a_len2)
X2=400
tail2=pre2[-X2:]; head2=lead_loop[:X2]; blend2=np.linspace(0,1,X2)
lead=np.concatenate([pre2[:-X2], tail2*(1-blend2)+head2*blend2, lead_loop[X2:]])
lead=np.tanh(lead*1.1)*0.8
lead/=np.max(np.abs(lead)); lead*=0.85
ls2=len(lead)-(loop_len2-X2); ll2=loop_len2-X2
print(f"lead total {len(lead)} loopstart {ls2} looplen {ll2}")
wav("/workspace/samples/lead.wav", lead)
print("LEADLOOP",ls2,ll2)

# ---------- ARPLUCK (one-shot, no loop) ----------
Lp=int(sr*0.45)
n=np.arange(Lp)
arp=np.zeros(Lp,dtype=float)
for k,a in zip([1,2,3,4,5,6,7,8],[1,0.5,0.33,0.25,0.2,0.16,0.12,0.1]):
    arp+=a*np.sin(2*np.pi*fC4*k*n/sr)
arp/=np.max(np.abs(arp))
arp*=np.exp(-n/(sr*0.09))  # decay ~90ms
arp[:int(0.002*sr)]*=np.linspace(0,1,int(0.002*sr))
arp*=0.9
wav("/workspace/samples/arp.wav", arp)

# ---------- PAD fifth C+G (power chord pad) ----------
# find loop_len minimizing cents error for both C4 and G4(392.00)
fG=392.00
best=None
for ll in range(18000,26000):
    kC=round(fC4*ll/sr); kG=round(fG*ll/sr)
    fCs=kC*sr/ll; fGs=kG*sr/ll
    eC=1200*np.log2(fCs/fC4); eG=1200*np.log2(fGs/fG)
    err=max(abs(eC),abs(eG))
    if best is None or err<best[0]:
        best=(err,ll,kC,kG,eC,eG)
print("pad loop search best",best)
_,pad_ll,kC,kG,eC,eG=best
pad_loop_len=pad_ll
Npad=int(sr*1.8)
prepad_len=Npad-pad_loop_len
# pad voices: C + G, each 3 detuned saws ±6 cents, harmonics 1..8 rolloff
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
# slow attack pre
prepad=np.zeros(prepad_len)
for base in [fC4,fG]:
    for d in det:
        r=2**(d/1200)
        for k in range(1,9):
            amp=1/(k**1.1)*0.5
            prepad+=amp*np.sin(2*np.pi*base*r*k*np.arange(prepad_len)/sr + rng.uniform(0,2*np.pi))
prepad/=np.max(np.abs(prepad))
att=int(0.12*sr)
prepad[:att]*=np.linspace(0,1,att)
# gentle swell: multiply pre by 0.7->1
swell=np.linspace(0.6,1.0,prepad_len)
prepad*=swell
Xp=2000
tailp=prepad[-Xp:]; headp=pad_loop[:Xp]; blp=np.linspace(0,1,Xp)
pad=np.concatenate([prepad[:-Xp], tailp*(1-blp)+headp*blp, pad_loop[Xp:]])
pad*=0.75
pad/=np.max(np.abs(pad)); pad*=0.7
lsp=len(pad)-(pad_loop_len-Xp); llp=pad_loop_len-Xp
print(f"pad total {len(pad)} loopstart {lsp} looplen {llp}")
wav("/workspace/samples/pad.wav", pad)
print("PADLOOP",lsp,llp)

# ---------- KICK ----------
t2=np.arange(int(sr*0.32))/sr
freq=42+(165-42)*np.exp(-t2*32)
phase=2*np.pi*np.cumsum(freq)/sr
kick=np.sin(phase)*np.exp(-t2*9.5)
kick+=0.35*np.sin(phase*2.01)*np.exp(-t2*16)
# click
cl=int(0.004*sr)
kick[:cl]+=0.8*np.sin(2*np.pi*1500*np.arange(cl)/sr)*np.exp(-np.arange(cl)/(sr*0.001))
kick/=np.max(np.abs(kick)); kick*=0.95
wav("/workspace/samples/kick.wav", kick)

# ---------- SNARE ----------
Ls=int(sr*0.24)
ns=rng.standard_normal(Ls)
# body
tb=np.arange(Ls)/sr
body=np.sin(2*np.pi*190*tb)*np.exp(-tb*22)+0.5*np.sin(2*np.pi*330*tb)*np.exp(-tb*28)
# noise with decay + highpass-ish (differentiate)
noise=ns*np.exp(-tb*30)
# crude highpass: noise - smoothed
from numpy import convolve
k=np.ones(8)/8
sm=convolve(noise,k,mode='same')
noise_hp=noise-sm
snare=body*0.8+noise_hp*0.7
snare[:int(0.001*sr)]*=np.linspace(0,1,int(0.001*sr))
snare/=np.max(np.abs(snare)); snare*=0.9
wav("/workspace/samples/snare.wav", snare)

# ---------- CHH ----------
Lh=int(sr*0.07)
nh=rng.standard_normal(Lh)
th=np.arange(Lh)/sr
# highpass via diff
hp=np.diff(nh,prepend=0)
chh=hp*np.exp(-th*90)
chh/=np.max(np.abs(chh)); chh*=0.55
wav("/workspace/samples/chh.wav", chh)

# ---------- OHH ----------
Lo=int(sr*0.38)
no=rng.standard_normal(Lo)
to=np.arange(Lo)/sr
hpo=np.diff(no,prepend=0)
ohh=hpo*np.exp(-to*14)
ohh/=np.max(np.abs(ohh)); ohh*=0.5
wav("/workspace/samples/ohh.wav", ohh)

# ---------- CRASH ----------
Lc=int(sr*1.6)
nc=rng.standard_normal(Lc)
tc=np.arange(Lc)/sr
hpc=np.diff(nc,prepend=0)
# shimmer: add metallic partials
shimmer=np.zeros(Lc)
for f in [523,740,932,1244,1568,2093]:
    shimmer+=np.sin(2*np.pi*f*tc+ rng.uniform(0,6))*np.exp(-tc*2.5)*0.15
crash=hpc*np.exp(-tc*3.2)*0.8+shimmer
crash[:int(0.002*sr)]*=np.linspace(0,1,int(0.002*sr))
crash/=np.max(np.abs(crash)); crash*=0.7
wav("/workspace/samples/crash.wav", crash)

# ---------- SWEEP UP ----------
Lsw=int(sr*1.6)
nsw=rng.standard_normal(Lsw)
tsw=np.arange(Lsw)/sr
# sweeping resonant feel: amplitude swell + pitch-ish via filtered noise (simple: cumulative with moving cutoff approx by smoothing window shrinking)
# simple approach: white noise with exp swell and highpass cutoff sweeping up: implement via STFT-ish? approximate: mix lowpassed versions
# lowpass via moving average with window shrinking from 40 -> 2
sweep=np.zeros(Lsw)
# build via FFT filter sweep: chunk into 32 frames, each with different lowpass
frames=40
for i in range(frames):
    a=int(i*Lsw/frames); b=int((i+1)*Lsw/frames)
    seg=nsw[a:b]
    # lowpass strength decreases: window size
    wsize=int(60*(1-i/frames)+2)
    ker=np.ones(wsize)/wsize
    lp=convolve(seg,ker,mode='same')
    # crossfade lp->hp as sweep rises: early mostly lp, late mostly hp
    hp_seg=seg-lp
    mix=i/frames
    sweep[a:b]=lp*(1-mix)*0.7+ (seg*0.4+hp_seg*0.8)*mix
env_sw=np.linspace(0,1,Lsw)**1.5
sweep*=env_sw
sweep*=np.exp(-np.linspace(0,0.3,Lsw))*1.2+0.2
sweep/=np.max(np.abs(sweep)); sweep*=0.6
wav("/workspace/samples/sweep.wav", sweep)

