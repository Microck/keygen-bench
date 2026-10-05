import sys, numpy as np
sys.path.insert(0, '/workspace/src')
from xmwrite import read_wav
def summary(path, seg_s=1.6):
    d, sr = read_wav(path)
    print(path, 'dur %.1f peak %.3f rms %.3f clipped %d' % (len(d)/sr, np.abs(d).max(), np.sqrt((d**2).mean()), (np.abs(d) >= 0.999).sum()))
    seg = int(sr*seg_s)
    pk = [np.abs(d[i:i+seg]).max() for i in range(0, len(d), seg)]
    rms = [np.sqrt((d[i:i+seg]**2).mean()) for i in range(0, len(d), seg)]
    print(' peaks:', ' '.join('%.2f' % x for x in pk))
    print(' rms:  ', ' '.join('%.2f' % x for x in rms))
    return d, sr
if __name__ == '__main__':
    summary(sys.argv[1])
