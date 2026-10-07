import wave
import numpy as np

with wave.open("/workspace/tune_v2.wav", "rb") as w:
    params = w.getparams()
    print("WAV Parameters:", params)
    frames = w.readframes(params.nframes)
    data = np.frombuffer(frames, dtype=np.int16)
    
if params.nchannels == 2:
    left = data[::2]
    right = data[1::2]
else:
    left = data
    right = data

max_left = np.max(np.abs(left))
max_right = np.max(np.abs(right))
print(f"Max Amplitude: Left={max_left} ({max_left/32768:.3f}), Right={max_right} ({max_right/32768:.3f})")

pat_samples = int(7.3846 * 44100)
for i in range(5):
    start = i * pat_samples
    end = min(start + pat_samples, len(left))
    segment = left[start:end]
    rms = np.sqrt(np.mean(segment.astype(np.float64)**2))
    max_val = np.max(np.abs(segment))
    print(f"Pattern Segment {i} (Pattern {i % 5}): RMS={rms:.1f} ({rms/32768:.3f}), Max={max_val} ({max_val/32768:.3f})")

