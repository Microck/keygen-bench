#!/usr/bin/env python3
import sys, numpy as np
sys.path.insert(0, '/workspace')
from rw import read_wav
path = sys.argv[1] if len(sys.argv)>1 else '/workspace/build/tune.wav'
d, sr = read_wav(path)
n = len(d)
print(f"{path}  {n} samples  {n/sr:.2f}s  sr={sr}")
print("peak %.3f  rms %.4f  dBFS peak %.1f  clipped %d" % (np.max(np.abs(d)), np.sqrt((d**2).mean()),
      20*np.log10(np.max(np.abs(d))+1e-9), int((np.abs(d)>0.999).sum())))
# per-second rms
sec = sr
nb = n//sec
r = np.sqrt((d[:nb*sec].reshape(nb,sec)**2).mean(1))
pk = np.abs(d[:nb*sec].reshape(nb,sec)).max(1)
print("\nsec  rms    peak   bar")
for i in range(nb):
    bars = "#"*int(r[i]*140)
    print(f"{i:4d} {r[i]:.3f} {pk[i]:.3f} {bars}")
# loop seam: compare around the loop point (halfway)
loop = n//2
pre = d[loop-22050:loop]; post = d[loop:loop+22050]
print("\nseam: rms before %.4f after %.4f ; end-of-loop tail %.4f ; start rms %.4f" % (
    np.sqrt((pre**2).mean()), np.sqrt((post**2).mean()),
    np.sqrt((d[loop-4410:loop]**2).mean()), np.sqrt((post[:4410]**2).mean())))
# spectral balance
f = np.fft.rfftfreq(4096, 1/sr)
S = np.abs(np.fft.rfft(d[loop:loop+8192]*np.hanning(8192)))
bands = [(0,100),(100,300),(300,1000),(1000,3000),(3000,7000),(7000,12000)]
tot = S.sum()
print("spectral bands:", {f"{a}-{b}Hz": round(float(S[(f>=a)&(f<b)].sum()/tot),3) for a,b in bands})
