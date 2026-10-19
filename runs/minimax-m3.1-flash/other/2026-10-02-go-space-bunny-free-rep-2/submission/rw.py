"""Read WAV files produced by the renderer (its header claims half the true length)."""
import numpy as np

def read_wav(path):
    data = open(path, 'rb').read()
    assert data[:4] == b'RIFF' and data[8:12] == b'WAVE'
    pos, fmt, pcm = 12, None, None
    while pos < len(data) - 8:
        cid = data[pos:pos+4]
        sz = int.from_bytes(data[pos+4:pos+8], 'little')
        body = data[pos+8:pos+8+sz]
        if cid == b'fmt ':
            fmt = dict(fmt=int.from_bytes(body[0:2],'little'),
                       ch=int.from_bytes(body[2:4],'little'),
                       sr=int.from_bytes(body[4:8],'little'),
                       bits=int.from_bytes(body[14:16],'little'))
        elif cid == b'data':
            pcm = body
        pos += 8 + sz + (sz & 1)
    if fmt['bits'] == 16:
        n = len(pcm)//2
        x = np.frombuffer(pcm[:n*2], dtype='<i2').astype(np.float32)/32768
    else:
        x = (np.frombuffer(pcm, dtype=np.uint8).astype(np.float32)-128)/128
    if fmt['ch'] == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    return x, fmt['sr']
