import numpy as np, wave, os
SR=44100
os.makedirs('/workspace/samples',exist_ok=True)
def write_wav(path, data, sr=SR):
    data=np.asarray(data,dtype=float); peak=np.max(np.abs(data))+1e-9
    d=(data/peak*32767).astype('<i2')
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(d.tobytes())

# Lead / Arp base ~194 Hz (note 25 -> ~419 Hz, A-4-ish)
k_lead=9; L_lead=2048
f_lead=SR*k_lead/L_lead
n=np.arange(L_lead); phase=2*np.pi*f_lead*n/SR
duty=0.25
pulse=((phase/(2*np.pi))%1 < duty).astype(float)*2-1
pulse=pulse-np.mean(pulse)
write_wav('/workspace/samples/lead.wav', pulse)
write_wav('/workspace/samples/lead2.wav', pulse)
write_wav('/workspace/samples/arp.wav', np.sin(phase))

# Bass base = lead/4 = ~48.45 Hz  -> exactly 2 octaves below lead (ratio 4, a power of 2)
k_bass=9; L_bass=8192
f_bass=SR*k_bass/L_bass
phaseB=2*np.pi*f_bass*np.arange(L_bass)/SR
sq=((phaseB/(2*np.pi))%1 < 0.5).astype(float)*2-1
write_wav('/workspace/samples/bass.wav', sq)
print("lead base",round(f_lead,2),"bass base",round(f_bass,2),"ratio",round(f_lead/f_bass,3))

# Drums (one-shot, trigger at note 37)
def noise(n,hp=1):
    x=np.random.randn(n)
    for _ in range(hp): x=x-np.roll(x,2)
    return x
dur=0.30; N=int(SR*dur); t=np.arange(N)/SR
freq=45+115*np.exp(-t*30); ph=2*np.pi*np.cumsum(freq)/SR
kick=np.sin(ph)*np.exp(-t*16)*0.95+0.4*np.exp(-t*150)*np.random.randn(N)*0.25
write_wav('/workspace/samples/kick.wav', kick)
dur=0.20; N=int(SR*dur); t=np.arange(N)/SR
snare=noise(N,2)*np.exp(-t*28)*0.8+np.sin(2*np.pi*180*t)*np.exp(-t*20)*0.5
write_wav('/workspace/samples/snare.wav', snare)
dur=0.04; N=int(SR*dur); t=np.arange(N)/SR
write_wav('/workspace/samples/hatc.wav', noise(N,3)*np.exp(-t*120))
dur=0.18; N=int(SR*dur); t=np.arange(N)/SR
write_wav('/workspace/samples/hato.wav', noise(N,3)*np.exp(-t*18))
print("samples ok")
