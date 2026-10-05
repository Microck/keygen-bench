import numpy as np
import wave

SAMPLE_RATE = 44100
length = int(SAMPLE_RATE * 1.5)
nz = np.random.uniform(-1, 1, size=length)
# highpass
hi = np.diff(np.concatenate(([0], nz))) * 0.8
# envelope: fast attack, long decay
env = np.exp(-np.arange(length) * 0.004)
crash = hi * env
# lowpass slightly
crash = np.convolve(crash, np.ones(2)/2, mode='same')
crash = np.clip(crash * 0.6, -1, 1)
data16 = (crash * 32767).astype(np.int16)
with wave.open('/workspace/samples/crash.wav','wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SAMPLE_RATE)
    w.writeframes(data16.tobytes())
print("Crash generated")
