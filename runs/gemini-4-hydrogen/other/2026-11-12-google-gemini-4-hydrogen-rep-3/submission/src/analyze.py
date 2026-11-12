import wave
import numpy as np

def load_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch)
    return sr, data.astype(np.float64) / 32768.0

sr, x = load_wav("/workspace/submission/preview.wav")
n_frames = len(x)
dur = n_frames / sr
print(f"Duration: {dur:.3f}s, frames={n_frames}, sr={sr}")

peak = np.max(np.abs(x))
clips = np.sum(np.abs(x) >= 32767.0 / 32768.0)
rms = np.sqrt(np.mean(x ** 2))
dc = np.mean(x, axis=0)
l_rms = np.sqrt(np.mean(x[:, 0] ** 2))
r_rms = np.sqrt(np.mean(x[:, 1] ** 2))
mid = 0.5 * (x[:, 0] + x[:, 1])
side = 0.5 * (x[:, 0] - x[:, 1])
side_ratio = np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-12)
corr = np.corrcoef(x[:, 0], x[:, 1])[0, 1]

print(f"Peak: {20*np.log10(peak+1e-12):.2f} dBFS ({peak:.4f}), clipped samples: {clips}")
print(f"Overall RMS: {20*np.log10(rms+1e-12):.2f} dBFS, Crest: {20*np.log10(peak/(rms+1e-12)):.2f} dB")
print(f"DC offset: L={dc[0]:.6f}, R={dc[1]:.6f}")
print(f"L RMS: {20*np.log10(l_rms+1e-12):.2f} dB, R RMS: {20*np.log10(r_rms+1e-12):.2f} dB, corr={corr:.3f}, side/mid={side_ratio:.3f}")

# Per-pattern analysis (18 patterns)
pat_frames = n_frames // 18
print("\nPer-position breakdown:")
print("Pos |  RMS dB | Peak dB | Clips | Sub(<160) | Mid(160-2.5k) | High(>2.5k) | Side/Mid")
for p in range(18):
    seg = x[p * pat_frames : (p + 1) * pat_frames]
    prms = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)
    ppk = 20 * np.log10(np.max(np.abs(seg)) + 1e-12)
    pclip = np.sum(np.abs(seg) >= 32767.0 / 32768.0)
    mono = 0.5 * (seg[:, 0] + seg[:, 1])
    sd = 0.5 * (seg[:, 0] - seg[:, 1])
    s_m = np.sqrt(np.mean(sd ** 2)) / (np.sqrt(np.mean(mono ** 2)) + 1e-12)
    freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
    mag2 = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    tot = np.sum(mag2) + 1e-12
    sub = np.sum(mag2[freqs < 160]) / tot
    midb = np.sum(mag2[(freqs >= 160) & (freqs < 2500)]) / tot
    hi = np.sum(mag2[freqs >= 2500]) / tot
    print(f"{p:3d} | {prms:7.2f} | {ppk:7.2f} | {pclip:5d} | {sub*100:7.1f}%  | {midb*100:10.1f}%   | {hi*100:9.1f}%  | {s_m:8.3f}")

# Check start and end of file
print(f"\nFirst 5ms max: {np.max(np.abs(x[:int(0.005*sr)])):.4f}")
print(f"Last 50ms RMS: {20*np.log10(np.sqrt(np.mean(x[-int(0.05*sr):]**2))+1e-12):.2f} dBFS")
