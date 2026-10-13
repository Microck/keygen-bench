import sys, tune as T, build_api, numpy as np, wave
keep=[int(x) for x in sys.argv[1].split(',')]
T.KEEP=set(keep)
out='/workspace/build/stem_%s.xm'%sys.argv[1].replace(',','')
build_api.build(out, instruments=__import__('sounds').build())
from tlib import Builder
b=Builder('s',8); b.add('module_load',path=out)
b.add('module_render',path='/workspace/build/stem.wav',rate=44100,start=0,stop=11,loops=1); b.run()
d=open('/workspace/build/stem.wav','rb').read()
import numpy as np, wave as W
w=W.open('/workspace/build/stem.wav','rb'); n=w.getnframes()
a=np.frombuffer(w.readframes(n),dtype='<i2').astype(float).reshape(-1,2)/32768.0
print('stem %s rms %.4f peak %.3f  L %.4f R %.4f'%(keep, a.mean(axis=1).std(), np.abs(a).max(), a[:,0].std(), a[:,1].std()))
np.save('/workspace/build/stem_%s.npy'%sys.argv[1].replace(',',''), a)
