import wave
import numpy as np
import sys
sys.path.insert(0, "/workspace")
from build.ft2_client import FT2Client

wav_path = "/workspace/build/render.wav"
with wave.open(wav_path, "rb") as w:
    ch = w.getnchannels()
    sr = w.getframerate()
    nframes = w.getnframes()
    raw = np.frombuffer(w.readframes(nframes), dtype=np.int16).reshape(-1, ch)

print(f"Loaded {wav_path}: {nframes} frames ({nframes/sr:.3f}s), {ch} channels @ {sr} Hz")

peak = np.max(np.abs(raw))
peak_db = 20 * np.log10(peak / 32767.0 + 1e-12)
rms = np.sqrt(np.mean(raw.astype(np.float64) ** 2))
rms_db = 20 * np.log10(rms / 32767.0 + 1e-12)
clipped = np.sum(np.abs(raw) >= 32767)
dc_l, dc_r = np.mean(raw[:, 0]), np.mean(raw[:, 1])

print(f"Global Peak: {peak} ({peak_db:.2f} dBFS), Clipped samples: {clipped}")
print(f"Global RMS : {rms:.1f} ({rms_db:.2f} dBFS), Crest factor: {peak_db - rms_db:.2f} dB")
print(f"DC Offset  : L={dc_l:+.2f}, R={dc_r:+.2f}")

frames_per_order = int(round(6.40 * sr)) # 282240
print("\n--- PER-ORDER PROFILE (Orders 0..15) ---")
print("Ord | Pat | PeakdB | RMSdB  | L-R dB | Corr  | Sub%  Low%  Mid%  High% | Centroid")
order_pats = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 6, 12, 13, 14]
for ord_idx in range(16):
    s0 = ord_idx * frames_per_order
    s1 = s0 + frames_per_order
    seg = raw[s0:s1].astype(np.float64)
    p_db = 20 * np.log10(np.max(np.abs(seg)) / 32767.0 + 1e-12)
    r_db = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) / 32767.0 + 1e-12)
    rms_l = np.sqrt(np.mean(seg[:, 0] ** 2))
    rms_r = np.sqrt(np.mean(seg[:, 1] ** 2))
    lr_db = 20 * np.log10((rms_l + 1e-9) / (rms_r + 1e-9))
    corr = np.corrcoef(seg[:, 0], seg[:, 1])[0, 1]

    mono = 0.5 * (seg[:, 0] + seg[:, 1])
    spec = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
    tot_e = np.sum(spec) + 1e-12
    e_sub = 100.0 * np.sum(spec[(freqs >= 20) & (freqs < 120)]) / tot_e
    e_low = 100.0 * np.sum(spec[(freqs >= 120) & (freqs < 500)]) / tot_e
    e_mid = 100.0 * np.sum(spec[(freqs >= 500) & (freqs < 4000)]) / tot_e
    e_hi  = 100.0 * np.sum(spec[freqs >= 4000]) / tot_e
    centroid = np.sum(freqs * spec) / np.sum(spec)
    print(f" {ord_idx:2d} |  {order_pats[ord_idx]:2d} | {p_db:6.2f} | {r_db:6.2f} | {lr_db:+6.2f} | {corr:+5.2f} | {e_sub:4.1f}% {e_low:4.1f}% {e_mid:4.1f}% {e_hi:4.1f}% | {centroid:6.0f} Hz")

# Now test real-time loop transition Order 15 -> Order 0 by temporarily setting length=17, order[16]=0
client = FT2Client()
client.call("song_set", {"length": 17, "loop_start": 0})
client.call("order_set", {"position": 16, "pattern": 0})
loop_wav = "/workspace/build/render_loop_check.wav"
client.call("module_render", {"path": loop_wav, "rate": 44100, "bits": 16})
# Restore song length to 16 immediately and re-save tune.xm
client.call("song_set", {"length": 16, "loop_start": 0})
client.call("module_save", {"path": "/workspace/submission/tune.xm", "format": "xm"})

with wave.open(loop_wav, "rb") as w:
    raw_loop = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2)

seam = 16 * frames_per_order
print(f"\n--- REAL-TIME LOOP SEAM CHECK (Order 15 -> Order 0 at frame {seam}, t={seam/sr:.3f}s) ---")
step_at_seam_l = abs(int(raw_loop[seam, 0]) - int(raw_loop[seam - 1, 0]))
step_at_seam_r = abs(int(raw_loop[seam, 1]) - int(raw_loop[seam - 1, 1]))
local_steps_l = np.abs(np.diff(raw_loop[seam - 4410:seam + 4410, 0].astype(np.int32)))
local_steps_r = np.abs(np.diff(raw_loop[seam - 4410:seam + 4410, 1].astype(np.int32)))
print(f"Seam step L={step_at_seam_l} (local max={np.max(local_steps_l)}, p99={np.percentile(local_steps_l, 99):.0f})")
print(f"Seam step R={step_at_seam_r} (local max={np.max(local_steps_r)}, p99={np.percentile(local_steps_r, 99):.0f})")

diff_after_row0 = np.max(np.abs(raw_loop[4410:frames_per_order].astype(np.int32) - raw_loop[seam + 4410:seam + frames_per_order].astype(np.int32)))
print(f"Max sample difference between Order 0 (Initial) and Order 16 (Looped Order 0) after Row 0: {diff_after_row0}")
