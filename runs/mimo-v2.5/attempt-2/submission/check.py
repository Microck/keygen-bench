from tlib import *
import numpy as np, sys, wave
path = sys.argv[1] if len(sys.argv)>1 else '/workspace/build/tune.xm'
out  = sys.argv[2] if len(sys.argv)>2 else '/workspace/build/tune.wav'
pats = int(sys.argv[3]) if len(sys.argv)>3 else 11
b=Builder('r',8); b.add('module_load', path=path)
b.add('module_render', path=out, rate=44100, start=0, stop=pats, loops=1); b.run()
w=wave.open(out,'rb'); n=w.getnframes(); sr=w.getframerate()
d=np.frombuffer(w.readframes(n),dtype='<i2').astype(np.float64).reshape(-1,2)/32768.0
mono=d.mean(axis=1); ROW=2.5*6/160.0
bars=min(int(len(mono)/(ROW*16)), pats*4)
print('duration %.2f s | rows %.0f/%d | patterns %.1f'%(n/sr, n/sr/ROW, pats*64, n/sr/6.0))
print('peak L %.3f R %.3f | rms %.4f | clip %d'%(np.abs(d).max(), np.abs(d[:,1]).max(), mono.std(), int(np.sum(np.abs(d)>0.999))))
prof=[float(mono[int(b*16*ROW*sr):int((b+1)*16*ROW*sr)].std()) for b in range(bars)]
print('bar rms:', ' '.join('%.3f'%v for v in prof))
np.save('/workspace/build/tune.npy', d)
