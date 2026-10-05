import wave, numpy as np, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/workspace/preview.wav'
w = wave.open(path, 'rb')
n = w.getnframes(); data = w.readframes(n); sr = w.getframerate()
ch = w.getnchannels()
arr = np.frombuffer(data, dtype='<i2').reshape(-1, ch).astype(np.float64)
print("file", path, "frames", n, "dur", n/sr, "ch", ch, "sr", sr)
print("peak", np.max(np.abs(arr)), "clip>=32760", np.sum(np.abs(arr) >= 32760))
mono = arr.mean(axis=1)

sec = sr
nsec = len(mono)//sec
rms = [np.sqrt(np.mean(mono[i*sec:(i+1)*sec]**2)) for i in range(nsec)]
print("rms per second:")
print(' '.join(str(int(v)) for v in rms))

# loop seam check (self-concat)
join = np.concatenate([arr, arr], axis=0)
idx = n
window = 300
seg = join[idx-window:idx+window]
d = np.abs(np.diff(seg, axis=0))
print("seam max abs diff:", d.max(), " track 99.9pct diff:", np.percentile(np.abs(np.diff(arr,axis=0)),99.9))
print("last frame", arr[-1], "first frame", arr[0])
