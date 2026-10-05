# Regenerates the instrument samples for "midnight keygen" using only numpy.
# Oscillators are one 256-sample cycle (looped; tuned with relative_note=36).
# Percussion are one-shots at 44.1 kHz (tuned with relative_note=29).
import numpy as np, wave, os
OUT="samples"; os.makedirs(OUT,exist_ok=True)
def wv(name,d,rate=44100):
    d=np.clip(d,-1,1);pcm=(d*32767).astype('<i2')
    with wave.open(os.path.join(OUT,name),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(pcm.tobytes())
L=256;t=np.arange(L)/L
pulse=lambda duty,nh: (lambda y:y/(np.max(np.abs(y))+1e-9)*0.92)(sum((2/(k*np.pi))*np.sin(k*np.pi*duty)*np.cos(2*np.pi*k*t) for k in range(1,nh+1)))
saw=lambda nh,r=1.0:(lambda y:y/(np.max(np.abs(y))+1e-9)*0.92)(sum(((-1)**(k+1))*(1.0/k)*(r**(k-1))*np.sin(2*np.pi*k*t) for k in range(1,nh+1)))
sine=np.sin(2*np.pi*t)*0.92
wv("lead_256.wav",pulse(0.25,14)); wv("arp_256.wav",pulse(0.5,10))
wv("bass_256.wav",saw(32,0.93));   wv("pad_256.wav",saw(16,0.82)+0.2*sine)
wv("lead2_256.wav",pulse(0.16,16));wv("sub_256.wav",sine)
Fs=44100; rng=np.random.default_rng(1234)
def kick():
    n=int(0.26*Fs);tt=np.arange(n)/Fs;k=np.log(48/150.)
    ph=2*np.pi*150*(np.exp(k*tt/0.26)-1)/(k/0.26)
    body=np.sin(ph)*np.exp(-tt/0.11)
    cl=np.exp(-tt/0.004)*rng.standard_normal(n)*0.5; cl=np.concatenate([[0],np.diff(cl)])
    y=(body+0.6*cl)*np.exp(-tt/0.16); return y/(np.max(np.abs(y))+1e-9)*0.99
wv("kick.wav",kick())
def shaped(dur,dec,peak,width,tilt=0.5,seed=23):
    r=np.random.default_rng(seed);n=int(dur*Fs);f=np.fft.rfftfreq(n,1/Fs)
    mag=(1.0/(f+60.)**tilt)*np.exp(-((np.log(f+1)-np.log(peak))/width)**2)
    y=np.fft.irfft(mag*np.exp(1j*r.uniform(0,2*np.pi,len(f))),n)
    y*=np.exp(-np.arange(len(y))/Fs/dec); return y/(np.max(np.abs(y))+1e-9)
def snare():
    n=int(0.19*Fs);tt=np.arange(n)/Fs
    tone=(np.sin(2*np.pi*185*tt)+0.6*np.sin(2*np.pi*335*tt))*np.exp(-tt/0.05)
    y=shaped(0.19,0.06,2300,1.0,0.4,23)*0.9+tone*0.45; return y/(np.max(np.abs(y))+1e-9)*0.97
wv("snare3.wav",snare())
wv("hatc4.wav",shaped(0.05,0.013,5200,0.55,seed=101)*0.9)
wv("hato4.wav",shaped(0.26,0.07,5200,0.55,seed=102)*0.9)
def clap():
    n=int(0.22*Fs);tt=np.arange(n)/Fs;y=np.zeros(n)
    for off in [0,0.009,0.018,0.028]:
        s=int(off*Fs);b=np.zeros(n);b[s:]=rng.standard_normal(n-s)*np.exp(-(tt[:n-s])/0.012);y+=b
    y+=rng.standard_normal(n)*np.exp(-tt/0.08)*0.5;y=np.concatenate([[0],np.diff(y)])
    return y/(np.max(np.abs(y))+1e-9)*0.95
wv("clap.wav",clap())
def crash():
    n=int(0.6*Fs);tt=np.arange(n)/Fs;y=np.zeros(n)
    for fq in [320,511,733,1050,1500,2100,3000,4200]:
        y+=np.sin(2*np.pi*fq*(1+0.001*rng.standard_normal())*tt)*rng.uniform(0.5,1)
    nz=rng.standard_normal(n)
    for _ in range(3): nz=np.concatenate([[0],np.diff(nz)])
    y=0.5*y/8+0.6*nz; y*=np.exp(-tt/0.22); return y/(np.max(np.abs(y))+1e-9)*0.9
wv("crash.wav",crash())
print("generated all samples into ./samples/")
