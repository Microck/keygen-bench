import numpy as np, wave, sys
w=wave.open('out.wav'); sr=w.getframerate(); n=w.getnframes()
d=np.frombuffer(w.readframes(n),dtype='<i2').astype(float).reshape(-1,2)
print("dur %.2f peak %d clip %d"%(n/sr, np.abs(d).max(), (np.abs(d)>=32700).sum()))
mono=d.mean(axis=1)
one=mono
blk=int(0.25*sr)
m=n//blk*blk
rms=np.sqrt((one[:m].reshape(-1,blk)**2).mean(axis=1))
mx=rms.max()
for i in range(0,len(rms)):
    print(f"{i*0.25:6.2f} {rms[i]:7.0f} {'#'*int(60*rms[i]/mx)}")
