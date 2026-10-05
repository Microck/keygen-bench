import numpy as np
import wave, os, subprocess, json, struct

sr = 44100
os.makedirs('/workspace/samples', exist_ok=True)
os.makedirs('/workspace/submission', exist_ok=True)

def write_wav(path, data, sr=44100):
    data = np.clip(data, -1.0, 1.0)
    data_int16 = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data_int16.tobytes())

print("Synthesizing refined instruments with 0 DC offset and clean looping...")

# 1. Kick (44.1 kHz, 0.22s)
t_k = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
f_k = 48.0 + 200.0 * np.exp(-t_k / 0.026)
phase_k = 2 * np.pi * np.cumsum(f_k) / sr
click_k = np.exp(-t_k / 0.0025) * np.sin(2 * np.pi * 1500 * t_k) * 0.6
body_k = np.sin(phase_k) * np.exp(-t_k / 0.065)
kick = np.tanh((body_k + click_k) * 1.5)
kick = kick - np.mean(kick)
kick = (kick / np.max(np.abs(kick))) * 0.85
write_wav('/workspace/samples/01_kick.wav', kick)

# 2. Snare (44.1 kHz, 0.22s)
t_sn = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
sn_tone = np.sin(2 * np.pi * (190.0 * np.exp(-t_sn / 0.02) + 125.0) * t_sn) * np.exp(-t_sn / 0.04) * 0.6
noise = np.random.uniform(-1, 1, len(t_sn))
noise = np.diff(noise, prepend=0)
noise_env = np.exp(-t_sn / 0.055) + 0.25 * np.exp(-t_sn / 0.11)
snare = np.tanh((sn_tone + noise * noise_env * 0.8) * 1.3)
snare = snare - np.mean(snare)
snare = (snare / np.max(np.abs(snare))) * 0.85
write_wav('/workspace/samples/02_snare.wav', snare)

# 3. Hat Closed (44.1 kHz, 0.05s)
t_ch = np.linspace(0, 0.05, int(sr * 0.05), endpoint=False)
metal_ch = sum(np.sin(2 * np.pi * f * t_ch) for f in [420, 630, 850, 1170, 1530]) / 5.0
noise_ch = np.diff(np.random.uniform(-1, 1, len(t_ch)), prepend=0)
hat_c = (0.5 * metal_ch + 0.5 * noise_ch) * np.exp(-t_ch / 0.012)
hat_c = hat_c - np.mean(hat_c)
write_wav('/workspace/samples/03_hat_closed.wav', (hat_c / np.max(np.abs(hat_c))) * 0.65)

# 4. Hat Open (44.1 kHz, 0.28s)
t_oh = np.linspace(0, 0.28, int(sr * 0.28), endpoint=False)
metal_oh = sum(np.sin(2 * np.pi * f * t_oh) for f in [420, 630, 850, 1170, 1530, 2400]) / 6.0
noise_oh = np.diff(np.random.uniform(-1, 1, len(t_oh)), prepend=0)
hat_o = (0.4 * metal_oh + 0.6 * noise_oh) * np.exp(-t_oh / 0.075)
hat_o = hat_o - np.mean(hat_o)
write_wav('/workspace/samples/04_hat_open.wav', (hat_o / np.max(np.abs(hat_o))) * 0.70)

# 5. Crash (44.1 kHz, 1.1s)
t_cr = np.linspace(0, 1.1, int(sr * 1.1), endpoint=False)
metal_cr = sum(np.sin(2 * np.pi * f * t_cr) for f in [310, 520, 780, 990, 1340, 1850, 2600, 3700]) / 8.0
noise_cr = np.diff(np.random.uniform(-1, 1, len(t_cr)), prepend=0)
crash = (0.35 * metal_cr + 0.65 * noise_cr) * np.exp(-t_cr / 0.28)
crash = crash - np.mean(crash)
write_wav('/workspace/samples/05_crash.wav', (crash / np.max(np.abs(crash))) * 0.80)

# 6. Chip Bass Pluck (44.1 kHz, 0.38s)
f0 = 261.625565
t_b = np.linspace(0, 0.38, int(sr * 0.38), endpoint=False)
saw_b = 2.0 * ((f0 * t_b) % 1.0) - 1.0
sub_b = np.sign(np.sin(2 * np.pi * (f0 / 2.0) * t_b))
raw_bass = 0.65 * saw_b + 0.35 * sub_b

fc_env = 220.0 + 2600.0 * np.exp(-t_b / 0.045)
filtered_bass = np.zeros_like(raw_bass)
y1, y2 = 0.0, 0.0
for i in range(len(raw_bass)):
    fc = fc_env[i] / sr
    al = min(0.92, 2 * np.pi * fc)
    y1 += al * (raw_bass[i] - y1)
    y2 += al * (y1 - y2)
    filtered_bass[i] = y2

amp_env_b = np.exp(-t_b / 0.12)
bass_chip = np.tanh(filtered_bass * amp_env_b * 2.0)
bass_chip = bass_chip - np.mean(bass_chip)
write_wav('/workspace/samples/06_bass_chip.wav', (bass_chip / np.max(np.abs(bass_chip))) * 0.85)

# 7. Sub Bass Looped (8428 samples = 50 cycles at 261.6279 Hz)
K = 50
L = 8428
f0_exact = K * sr / L
t_s = np.arange(L) / sr
phase_s = 2 * np.pi * f0_exact * t_s
sub_wave = 0.7 * np.sin(phase_s) + 0.25 * np.sin(2 * phase_s) + 0.15 * np.sign(np.sin(phase_s))
sub_wave = sub_wave - np.mean(sub_wave)
write_wav('/workspace/samples/07_bass_sub.wav', (sub_wave / np.max(np.abs(sub_wave))) * 0.80)

# 8. Pulse Lead Looped (8428 samples, 25% duty pulse with zero DC offset)
phase_p = (f0_exact * t_s) % 1.0
raw_pulse = np.where(phase_p < 0.25, 0.75, -0.75)
# Warm up filter cyclically
pulse_rep = np.tile(raw_pulse, 2)
p_filt_rep = np.zeros_like(pulse_rep)
for i in range(1, len(pulse_rep)):
    p_filt_rep[i] = 0.45 * p_filt_rep[i-1] + 0.55 * pulse_rep[i]
p_filt = p_filt_rep[L:].copy()
p_clean = p_filt - np.mean(p_filt)
write_wav('/workspace/samples/08_lead_pulse.wav', (p_clean / np.max(np.abs(p_clean))) * 0.75)

# 9. Supersaw Lead Looped (28665 samples, detuned saws with crossfade loop)
dur_ss = 0.8
N_ss = int(sr * dur_ss)
t_ss = np.arange(N_ss) / sr
saw_sum = np.zeros(N_ss)
for c in [-6.5, 0.0, 6.5]:
    f_det = f0 * (2.0 ** (c / 1200.0))
    saw_sum += (2.0 * ((f_det * t_ss) % 1.0) - 1.0)
saw_sum /= 3.0
fade_len = int(sr * 0.15)
loop_ss = saw_sum[:-fade_len].copy()
fade_in = np.linspace(0, 1, fade_len)
loop_ss[:fade_len] = np.sqrt(1 - fade_in**2) * saw_sum[-fade_len:] + fade_in * loop_ss[:fade_len]
loop_ss = loop_ss - np.mean(loop_ss)
write_wav('/workspace/samples/09_lead_saw.wav', (loop_ss / np.max(np.abs(loop_ss))) * 0.75)

# 10. Bell Chime Pluck (0.65s, FM bell)
t_bell = np.linspace(0, 0.65, int(sr * 0.65), endpoint=False)
f_mod = 2.76 * f0
mod_index = 2.8 * np.exp(-t_bell / 0.065)
modulator = np.sin(2 * np.pi * f_mod * t_bell)
carrier = np.sin(2 * np.pi * f0 * t_bell + mod_index * modulator)
bell = carrier * np.exp(-t_bell / 0.16)
bell = bell - np.mean(bell)
write_wav('/workspace/samples/10_pluck_bell.wav', (bell / np.max(np.abs(bell))) * 0.75)

# 11. Chip Pluck (0.25s, 12.5% pulse with zero DC offset)
t_cp = np.linspace(0, 0.25, int(sr * 0.25), endpoint=False)
phase_cp = (f0 * t_cp) % 1.0
raw_cp = np.where(phase_cp < 0.125, 0.8, -0.8)
raw_cp = raw_cp - np.mean(raw_cp)
cp_wave = raw_cp * np.exp(-t_cp / 0.055)
cp_wave = cp_wave - np.mean(cp_wave)
write_wav('/workspace/samples/11_pluck_chip.wav', (cp_wave / np.max(np.abs(cp_wave))) * 0.80)

# 12. Lush Pad Looped (28665 samples, warm strings)
dur_pad = 0.8
N_pad = int(sr * dur_pad)
t_pad = np.arange(N_pad) / sr
pad_sum = np.zeros(N_pad)
for c in [-9.0, -3.0, 3.0, 9.0]:
    f_det = f0 * (2.0 ** (c / 1200.0))
    pad_sum += (2.0 * ((f_det * t_pad) % 1.0) - 1.0)
pad_filt = np.zeros_like(pad_sum)
for i in range(1, len(pad_sum)):
    pad_filt[i] = 0.85 * pad_filt[i-1] + 0.15 * pad_sum[i]
fade_pad = int(sr * 0.15)
pad_loop = pad_filt[:-fade_pad].copy()
fade_p = np.linspace(0, 1, fade_pad)
pad_loop[:fade_pad] = np.sqrt(1 - fade_p**2) * pad_filt[-fade_pad:] + fade_p * pad_loop[:fade_pad]
pad_loop = pad_loop - np.mean(pad_loop)
write_wav('/workspace/samples/12_pad_lush.wav', (pad_loop / np.max(np.abs(pad_loop))) * 0.65)

# 13. FX Laser Zap (0.12s)
t_zap = np.linspace(0, 0.12, int(sr * 0.12), endpoint=False)
f_zap = 2400.0 * np.exp(-t_zap / 0.02) + 80.0
zap_phase = 2 * np.pi * np.cumsum(f_zap) / sr
zap = np.sin(zap_phase) * np.exp(-t_zap / 0.035)
zap = zap - np.mean(zap)
write_wav('/workspace/samples/13_fx_zap.wav', (zap / np.max(np.abs(zap))) * 0.75)

# 14. FX Riser (0.55s)
t_rise = np.linspace(0, 0.55, int(sr * 0.55), endpoint=False)
noise_r = np.random.uniform(-1, 1, len(t_rise))
f_sweep = 350.0 * np.exp(np.log(6500.0 / 350.0) * (t_rise / 0.55))
rise_env = (t_rise / 0.55) ** 1.5
rise_out = np.zeros_like(noise_r)
r_y1, r_y2 = 0.0, 0.0
for i in range(len(noise_r)):
    al = min(0.9, 2 * np.pi * f_sweep[i] / sr)
    r_y1 += al * (noise_r[i] - r_y1)
    r_y2 += al * (r_y1 - r_y2)
    rise_out[i] = (r_y1 - r_y2) * rise_env[i]
rise_out = rise_out - np.mean(rise_out)
write_wav('/workspace/samples/14_fx_riser.wav', (rise_out / np.max(np.abs(rise_out))) * 0.80)

print("Synthesized all waveforms.")
