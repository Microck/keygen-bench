import numpy as np, wave, sys
path = sys.argv[1] if len(sys.argv)>1 else '/workspace/preview.wav'
w=wave.open(path); d=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
sr=44100; row=0.1
print('dur',len(d)/sr,'peak',round(np.max(np.abs(d)),3),'rms',round(float(np.sqrt((d**2).mean())),4))
# per pattern (64 rows = 6.4 s)
for p in range(5):
    seg=d[int(p*6.4*sr):int((p+1)*6.4*sr)]
    print(' pattern',p,'peak',round(np.max(np.abs(seg)),3),'rms',round(float(np.sqrt((seg**2).mean())),4))
# per bar rms
bars=[]
for b in range(20):
    seg=d[int(b*1.6*sr):int((b+1)*1.6*sr)]
    bars.append(round(float(np.sqrt((seg**2).mean())),3))
print(' bar rms',bars)
def pitch_at(t, dur=0.08):
    a=int(t*sr); seg=d[a:a+int(dur*sr)]
    if len(seg)<256: return 0,0
    seg=seg*np.hanning(len(seg))
    sp=np.abs(np.fft.rfft(seg)); f=np.fft.rfftfreq(len(seg),1/sr)
    k=int(np.argmax(sp))
    return round(float(f[k]),1), round(float(sp[k]/np.max(sp)),2)
# lead melody check in pattern 1 (starts at 6.4 s)
print('--- lead pitches in P1 (expect E5=659, A5=880, G5=784, ...)')
for (rowi,expect) in [(0,659.3),(4,880.0),(6,784.0),(8,659.3),(16,698.5),(20,880.0),(24,1046.5),(32,659.3),(40,587.3),(48,523.3)]:
    t=6.4+rowi*0.1
    f,amp=pitch_at(t)
    print('  row',rowi,'t',round(t,2),'pitch',f,'want',expect,'rel',amp)
print('--- bass pitches in P1 bar 0 (A2=110, E3=164.8, A3=220)')
for rowi,expect in [(0,110.0),(4,164.8),(14,220.0)]:
    f,amp=pitch_at(6.4+rowi*0.1,0.06)
    print('  row',rowi,'pitch',f,'want',expect)
