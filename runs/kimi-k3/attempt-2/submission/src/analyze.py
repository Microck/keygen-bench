import numpy as np, wave, sys
from numpy.fft import rfft, rfftfreq

path = sys.argv[1] if len(sys.argv)>1 else "tune.wav"
w = wave.open(path,"rb"); sr=w.getframerate()
d = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64).reshape(-1,2)
mono = d.mean(axis=1)
one = 12*64*6*2.5/140.0  # seconds per full song
print(f"len={len(d)/sr:.3f}s  one_loop={one:.3f}s  peak={np.abs(d).max():.0f} ({np.abs(d).max()/32768:.3f} FS)")

# clipping fraction
clip = (np.abs(d) > 32000).mean()*100
print(f"clip_samples={clip:.4f}%")

# energy per pattern (12 sections per loop)
rowdur = 6*2.5/140; pat = 64*rowdur
print("\nsection energy (loop 1):")
for p in range(12):
    seg = mono[int(p*pat*sr):int((p+1)*pat*sr)]
    print(f"  pat{p:2d}: rms={np.sqrt((seg**2).mean()):7.1f}  peak={np.abs(seg).max():6.0f}")

# loop seam
nloops = round(len(d)/sr / one)
seam = int(one*sr)
print(f"\npasses in file: {nloops}")
if len(mono) > seam+4096:
    a = mono[seam-3072:seam]; c = mono[:3072]
    print(f"seam xcorr tail-vs-head rmsdiff={np.sqrt(((a-c[:len(a)])**2).mean()):.3f}")
# where do clipped samples occur?
ix = np.where(np.abs(d).max(axis=1) >= 32767)[0]
if len(ix):
    tt = ix/sr
    import collections
    cnt = collections.Counter((tt//one*12).astype(int))
    print("clipped frames per pattern:", dict(sorted(cnt.items())))

# low band (kick/bass) and pitch sanity at the theme (loop1, pattern2 bar1)
from numpy.fft import rfftfreq
def topfreq(t0,t1,fmin=40,fmax=4000,n=12):
    seg = mono[int(t0*sr):int(t1*sr)]; seg = seg-np.mean(seg)
    win = len(seg)
    sp = np.abs(rfft(seg*np.hanning(win))); fr = rfftfreq(win,1/sr)
    m = (fr>=fmin)&(fr<=fmax)
    idx = np.argsort(sp[m])[::-1][:n]
    fr2=fr[m]; sp2=sp[m]
    return [(round(fr2[i],1), int(sp2[i])) for i in idx]

print("\npat2 bar1 (Dm theme) top freqs 0.5-2.0s:", topfreq(2*pat+0.5, 2*pat+2.0, 40, 1200, 8))
print("pat8 bar1 (gap stabs Bb):", topfreq(8*pat+0.2, 8*pat+1.5, 60, 1600, 8))
print("pat5 bar1 (breakdown):", topfreq(5*pat+0.3, 5*pat+1.6, 40, 2000, 8))

# melody pitch tracking on pattern 2 (theme A1), 16th grid, 80ms windows
print("\npitch track pat2 (expect theme Dm):")
names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def n2name(f, off):
    m = int(round(69+12*np.log2(f/440.0)))
    return names[m%12]+str(m//12-off)
OUT=[]
for r in range(64):
    t0 = 2*pat + r*rowdur + 0.02
    n0=int(t0*sr); n1=n0+int(0.09*sr)
    seg = mono[n0:n1]*np.hanning(n1-n0)
    sp = np.abs(rfft(seg, 16384)); fr = rfftfreq(16384,1/sr)
    m=(fr>300)&(fr<1600)
    if sp[m].max()< sp.max()*0.03: OUT.append(f"{r:2d} .."); continue
    f = fr[m][np.argmax(sp[m])]
    OUT.append(f"{r:2d} {f:7.1f} {n2name(f,1)}")
    # note: true pitch names are one octave above FT2 display; off=1 to show FT2-ish
print(" | ".join(OUT[0:16]))
print(" | ".join(OUT[16:32]))
print(" | ".join(OUT[32:48]))
print(" | ".join(OUT[48:64]))

# arpeggio effect check: energy at stab root/third/fifth in pattern 8 bars 0-3
def band_e(t0,t1,f):
    seg = mono[int(t0*sr):int(t1*sr)]
    n=len(seg); seg=seg*np.hanning(n)
    sp=np.abs(rfft(seg)); fr=rfftfreq(n,1/sr)
    i=np.argmin(np.abs(fr-f)); return sp[max(0,i-3):i+4].sum()
for bar,ch in [(0,'Bb'),(1,'F'),(2,'Gm'),(3,'A')]:
    t0=8*pat+bar*16*rowdur; t1=t0+16*rowdur*0.9
    tgts = {'Bb':[466.2,587.3,698.5],'F':[698.5,880.0,1046.5],'Gm':[392.0,466.2,587.3],'A':[440.0,554.4,659.3]}
    es = [round(band_e(t0,t1,f)/1e6) for f in tgts[ch]]
    print(f"pat8 bar{bar} {ch}: R/3rd/5th energies = {es}")
