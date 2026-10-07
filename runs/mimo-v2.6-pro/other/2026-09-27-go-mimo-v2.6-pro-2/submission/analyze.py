import numpy as np, wave, sys
def readwav(f):
    w=wave.open(f); sr=w.getframerate(); n=w.getnframes(); ch=w.getnchannels(); sw=w.getsampwidth()
    raw=w.readframes(n)
    x=np.frombuffer(raw,dtype='<i2').astype(float)/32768 if sw==2 else (np.frombuffer(raw,dtype=np.uint8).astype(float)-128)/128
    x=x.reshape(-1,ch)
    return x, sr
x,sr=readwav(sys.argv[1])
L,R=x[:,0],x[:,1]
print("dur %.2fs  peak %.4f  rms %.4f  clipped %d"%(len(L)/sr, np.abs(x).max(), np.sqrt((x**2).mean()), (np.abs(x)>0.999).sum()))
mono=(L+R)/2
# per-pattern (6.4s) energy
pat=6.4
npat=int(len(mono)/sr/pat)
print("pattern energies (rms) and peak:")
for i in range(npat):
    seg=mono[int(i*pat*sr):int((i+1)*pat*sr)]
    print("  P%02d rms %.4f peak %.3f"%(i, np.sqrt((seg**2).mean()), np.abs(seg).max()))
