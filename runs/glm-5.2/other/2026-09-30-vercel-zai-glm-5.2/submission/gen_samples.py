# Sample generator for "Cracktro Dreams" keygen tune (8-bit WAVs)
import numpy as np, wave, os
OUT="/workspace/samples"; os.makedirs(OUT,exist_ok=True); SR=44100
def w8(p,data,sr=SR):
    d=np.clip(data,-1,1); i=(d*127).astype(np.int8)
    with wave.open(p,'w') as w:
        w.setnchannels(1);w.setsampwidth(1);w.setframerate(sr);w.writeframes(i.tobytes())
def cyc(func,n=64):
    t=np.linspace(0,1,n,endpoint=False); return func(t)
w8(f"{OUT}/lead.wav", cyc(lambda t: np.where(t<0.5,0.85,-0.85)))     # 50% square
w8(f"{OUT}/arp.wav",  cyc(lambda t: 0.8*(2*t-1)))                      # saw
w8(f"{OUT}/bass.wav", cyc(lambda t: 0.9*(2*np.abs(2*(t-0.5))-1)))     # triangle
w8(f"{OUT}/pad.wav",  cyc(lambda t: 0.6*(2*t-1)))                      # saw (soft)
w8(f"{OUT}/stab.wav", cyc(lambda t: np.where(t<0.5,0.85,-0.85)))      # square
def kick(dur=0.25):
    n=int(SR*dur); t=np.linspace(0,dur,n,endpoint=False)
    freq=160+(45-160)*(t/dur)**2; ph=2*np.pi*np.cumsum(freq)/SR
    env=np.exp(-t*13); body=np.sin(ph)*env
    click=np.random.randn(n)*np.exp(-t*150)*0.35
    return (body*0.95+click)*0.9
def snare(dur=0.18):
    n=int(SR*dur); t=np.linspace(0,dur,n,endpoint=False)
    noise=np.random.randn(n); lp=np.zeros(n); a=0.35
    for i in range(1,n): lp[i]=lp[i-1]+a*(noise[i]-lp[i-1])
    tone=np.sin(2*np.pi*185*t); env=np.exp(-t*22)
    return (0.75*lp+0.25*tone)*env*0.85
def hat(dur=0.045):
    n=int(SR*dur); t=np.linspace(0,dur,n,endpoint=False)
    noise=np.random.randn(n); hp=np.zeros(n)
    for i in range(1,n): hp[i]=noise[i]-0.45*noise[i-1]
    env=np.exp(-t*70); return hp*env*0.55
w8(f"{OUT}/kick.wav", kick())
w8(f"{OUT}/snare.wav", snare())
w8(f"{OUT}/hat.wav", hat())
print("samples generated")
