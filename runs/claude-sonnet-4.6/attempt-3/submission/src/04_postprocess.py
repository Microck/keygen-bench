#!/usr/bin/env python3
"""Apply DC-block high-pass (f_cutoff=5Hz) and gentle peak normalize to preview WAV"""
import numpy as np, wave, sys

def dc_block(x, sr, fc=5.0):
    """First-order high-pass IIR filter (DC blocker)"""
    alpha = 1.0 - (2*np.pi*fc/sr)
    y = np.zeros_like(x)
    prev_x = prev_y = 0.0
    for i in range(len(x)):
        cur = x[i]
        y[i] = cur - prev_x + alpha * prev_y
        prev_x, prev_y = cur, y[i]
    return y

src = sys.argv[1] if len(sys.argv)>1 else '/workspace/src/render3.wav'
dst = sys.argv[2] if len(sys.argv)>2 else '/workspace/submission/tune_preview.wav'

with wave.open(src) as f:
    sr=f.getframerate(); ch=f.getnchannels(); nf=f.getnframes()
    raw=f.readframes(nf)

data = np.frombuffer(raw, np.int16).astype(np.float32)/32768.0
stereo = ch==2
if stereo:
    data = data.reshape(-1,2)
    L = dc_block(data[:,0], sr)
    R = dc_block(data[:,1], sr)
    out = np.column_stack([L,R])
else:
    out = dc_block(data[:,np.newaxis].flatten(), sr)
    out = out[:,np.newaxis]

# Normalize to 95% of full scale
peak = np.max(np.abs(out))
out = out * (0.95 / peak)

out_int = np.clip(out, -1, 1)
out_int = (out_int * 32767).astype(np.int16)

with wave.open(dst, 'w') as f:
    f.setnchannels(ch); f.setsampwidth(2); f.setframerate(sr)
    f.writeframes(out_int.tobytes())

# Verify
flat = out.flatten()
print(f"DC after filter: {np.mean(flat):.6f}")
print(f"Peak:  {np.max(np.abs(flat)):.4f}")
print(f"RMS:   {np.sqrt(np.mean(flat**2)):.4f}")
print(f"Saved: {dst}")
