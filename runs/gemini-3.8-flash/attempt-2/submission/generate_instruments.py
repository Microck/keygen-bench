import numpy as np
import wave

sr = 44100
f_c4 = 440.0 * (2.0 ** (-9.0 / 12.0)) # 261.6255653005986 Hz

def save_wav(filename, samples):
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767.0).astype(np.int16)
    with wave.open(filename, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(data.tobytes())
    print(f"Saved {filename}: {len(samples)} samples ({len(samples)/sr*1000:.1f}ms), max={np.max(np.abs(samples)):.2f}")

def biquad_filter(samples, f_center, Q, filter_type='bandpass', sr=44100):
    w0 = 2 * np.pi * f_center / sr
    alpha = np.sin(w0) / (2 * Q)
    cos_w0 = np.cos(w0)
    
    if filter_type == 'bandpass':
        b0 = alpha; b1 = 0; b2 = -alpha
        a0 = 1 + alpha; a1 = -2 * cos_w0; a2 = 1 - alpha
    elif filter_type == 'lowpass':
        b0 = (1 - cos_w0) / 2; b1 = 1 - cos_w0; b2 = (1 - cos_w0) / 2
        a0 = 1 + alpha; a1 = -2 * cos_w0; a2 = 1 - alpha
    elif filter_type == 'highpass':
        b0 = (1 + cos_w0) / 2; b1 = -(1 + cos_w0); b2 = (1 + cos_w0) / 2
        a0 = 1 + alpha; a1 = -2 * cos_w0; a2 = 1 - alpha
        
    b0, b1, b2, a1, a2 = b0/a0, b1/a0, b2/a0, a1/a0, a2/a0
    y = np.zeros_like(samples)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(samples)):
        x0 = samples[i]
        out = b0*x0 + b1*x1 + b2*x2 - a1*y1 - a2*y2
        y[i] = out
        x2, x1 = x1, x0
        y2, y1 = y1, out
    return y

def make_crossfade_loop(raw, l_start, l_len, xfade=1500):
    buf = raw.copy()
    fade_tail = np.linspace(0, 1, xfade)
    buf[l_start : l_start + xfade] = (1 - fade_tail) * raw[l_start + l_len : l_start + l_len + xfade] + fade_tail * raw[l_start : l_start + xfade]
    return buf[:l_start + l_len]

# 1. KICK (Inst 1)
dur_k = 0.18
t_k = np.linspace(0, dur_k, int(sr * dur_k), endpoint=False)
f_k = 175.0 * np.exp(-t_k * 32.0) + 48.0
phase_k = 2 * np.pi * np.cumsum(f_k) / sr
env_k = np.exp(-t_k * 18.0)
click_k = np.random.uniform(-1, 1, len(t_k)) * np.exp(-t_k * 150.0) * 0.4
kick = np.tanh((np.sin(phase_k) * env_k + click_k) * 1.6)
save_wav('inst1_kick.wav', kick)

# 2. SNARE (Inst 2)
dur_s = 0.20
t_s = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False)
f_s = 250.0 * np.exp(-t_s * 28.0) + 130.0
phase_s = 2 * np.pi * np.cumsum(f_s) / sr
tone_s = np.sin(phase_s) * np.exp(-t_s * 25.0)
noise_raw = np.random.uniform(-1, 1, len(t_s))
noise_filtered = biquad_filter(noise_raw, 3400.0, 1.8, 'bandpass')
env_noise = np.exp(-t_s * 18.0)
snare = np.tanh((tone_s * 0.5 + noise_filtered * env_noise * 1.2) * 1.5)
save_wav('inst2_snare.wav', snare)

# 3. CLOSED HI-HAT (Inst 3)
dur_hc = 0.045
t_hc = np.linspace(0, dur_hc, int(sr * dur_hc), endpoint=False)
metal_freqs = [263.0, 400.0, 421.0, 474.0, 587.0, 845.0]
metal_hc = np.zeros_like(t_hc)
for f in metal_freqs:
    metal_hc += np.sign(np.sin(2 * np.pi * f * t_hc))
metal_hc = metal_hc / len(metal_freqs) + np.random.uniform(-0.6, 0.6, len(t_hc))
hat_cl_filt = biquad_filter(metal_hc, 8500.0, 2.5, 'bandpass')
hat_cl = hat_cl_filt * np.exp(-t_hc * 95.0)
hat_cl = hat_cl / np.max(np.abs(hat_cl)) * 0.95
save_wav('inst3_hat_cl.wav', hat_cl)

# 4. OPEN HI-HAT (Inst 4)
dur_ho = 0.22
t_ho = np.linspace(0, dur_ho, int(sr * dur_ho), endpoint=False)
metal_ho = np.zeros_like(t_ho)
for f in metal_freqs:
    metal_ho += np.sign(np.sin(2 * np.pi * f * t_ho))
metal_ho = metal_ho / len(metal_freqs) + np.random.uniform(-0.6, 0.6, len(t_ho))
hat_op_filt = biquad_filter(metal_ho, 8000.0, 2.2, 'bandpass')
hat_op = hat_op_filt * np.exp(-t_ho * 18.0)
hat_op = hat_op / np.max(np.abs(hat_op)) * 0.95
save_wav('inst4_hat_op.wav', hat_op)

# 5. CRASH CYMBAL (Inst 5)
dur_cr = 0.85
t_cr = np.linspace(0, dur_cr, int(sr * dur_cr), endpoint=False)
metal_cr = np.zeros_like(t_cr)
for f in [205.3, 304.4, 369.2, 522.7, 540.0, 812.0, 1100.0]:
    metal_cr += np.sign(np.sin(2 * np.pi * f * t_cr))
metal_cr = metal_cr / 7.0 + np.random.uniform(-1.0, 1.0, len(t_cr))
crash_filt = biquad_filter(metal_cr, 6500.0, 1.2, 'highpass')
crash = crash_filt * np.exp(-t_cr * 4.8)
crash = crash / np.max(np.abs(crash)) * 0.95
save_wav('inst5_crash.wav', crash)

# 6. BASS PLUCK / SLAP BASS (Inst 6)
dur_b = 0.40
t_b = np.linspace(0, dur_b, int(sr * dur_b), endpoint=False)
saw_b = 2.0 * ((t_b * f_c4) % 1.0) - 1.0
pulse_b = np.where((t_b * f_c4) % 1.0 < 0.35, 1.0, -1.0)
raw_b = 0.55 * saw_b + 0.45 * pulse_b
cutoff_env = 2600.0 * np.exp(-t_b * 30.0) + 250.0
bass_filtered = np.zeros_like(raw_b)
y_prev = 0.0
for i in range(len(raw_b)):
    fc = cutoff_env[i]
    k = 2 * np.pi * fc / sr
    a = k / (k + 1.0)
    y_prev = y_prev + a * (raw_b[i] - y_prev)
    bass_filtered[i] = y_prev
env_b = np.exp(-t_b * 7.5)
bass = np.tanh(bass_filtered * env_b * 2.2) * 0.95
save_wav('inst6_bass_plk.wav', bass)

# 7. SUB / ACID BASS (Inst 7)
dur_sub = 0.65
t_sub = np.linspace(0, dur_sub, int(sr * dur_sub), endpoint=False)
sub_wave = np.sin(2 * np.pi * f_c4 * t_sub) + 0.35 * np.sin(4 * np.pi * f_c4 * t_sub) + 0.15 * np.sin(6 * np.pi * f_c4 * t_sub)
env_sub = np.exp(-t_sub * 4.5)
sub_bass = np.tanh(sub_wave * env_sub * 1.5) * 0.95
save_wav('inst7_bass_sub.wav', sub_bass)

# 8. CHIPTUNE GLASS ARP PLUCK (Inst 8)
dur_arp = 0.25
t_arp = np.linspace(0, dur_arp, int(sr * dur_arp), endpoint=False)
pulse_125 = np.where((t_arp * f_c4) % 1.0 < 0.125, 1.0, -1.0)
pulse_sparkle = biquad_filter(pulse_125, 2000.0, 1.0, 'highpass')
env_arp = np.exp(-t_arp * 14.0)
arp_pluck = np.tanh((pulse_125 * 0.6 + pulse_sparkle * 0.4) * env_arp * 1.8) * 0.95
save_wav('inst8_arp_plk.wav', arp_pluck)

# 9. MELODIC PULSE LEAD (Inst 9)
# Use steady-state multi-period block!
n_cycles = 16
loop_len = 2697 # exactly 16 cycles
f_exact_lead = sr * (n_cycles / loop_len)
total_blocks = 6
t_total = np.linspace(0, (loop_len * total_blocks) / sr, loop_len * total_blocks, endpoint=False)
raw_lead = 0.7 * np.where((t_total * f_exact_lead) % 1.0 < 0.30, 1.0, -1.0) + \
           0.3 * np.where((t_total * f_exact_lead) % 1.0 < 0.50, 1.0, -1.0)
filt_lead = biquad_filter(raw_lead, 5500.0, 1.0, 'lowpass')
# Take 1 block for attack, 2 blocks for loop
l_start_9 = loop_len
l_len_9 = loop_len
lead_9_samples = filt_lead[:loop_len * 2].copy()
# Smooth attack in the first 250 samples
lead_9_samples[:250] *= np.linspace(0, 1, 250)
lead_9_samples = lead_9_samples / np.max(np.abs(lead_9_samples)) * 0.90
save_wav('inst9_lead_pulse.wav', lead_9_samples)
print(f"Lead Pulse: loop_start={l_start_9}, loop_len={l_len_9}")

# 10. SINGING SAW LEAD (Inst 10)
dur_saw = 1.0
t_saw = np.linspace(0, dur_saw, int(sr * dur_saw), endpoint=False)
detune_cents = 4.0
f_saw1 = f_c4 * (2.0 ** (detune_cents / 1200.0))
f_saw2 = f_c4 * (2.0 ** (-detune_cents / 1200.0))
saw1 = 2.0 * ((t_saw * f_saw1) % 1.0) - 1.0
saw2 = 2.0 * ((t_saw * f_saw2) % 1.0) - 1.0
saw_mix = biquad_filter(0.5 * saw1 + 0.5 * saw2, 5000.0, 1.0, 'lowpass')
att_s = 300
saw_mix[:att_s] *= np.linspace(0, 1, att_s)
l_start_10 = 4410
l_len_10 = 22050
saw_looped = make_crossfade_loop(saw_mix, l_start_10, l_len_10, xfade=2000)
saw_looped = saw_looped / np.max(np.abs(saw_looped)) * 0.90
save_wav('inst10_lead_saw.wav', saw_looped)
print(f"Lead Saw: loop_start={l_start_10}, loop_len={l_len_10}")

# 11. CHORD STAB / SYNTH BRASS (Inst 11)
dur_stab = 0.32
t_stab = np.linspace(0, dur_stab, int(sr * dur_stab), endpoint=False)
saw_s1 = 2.0 * ((t_stab * f_c4 * 1.002) % 1.0) - 1.0
saw_s2 = 2.0 * ((t_stab * f_c4 * 0.998) % 1.0) - 1.0
pulse_s = np.where((t_stab * f_c4) % 1.0 < 0.4, 1.0, -1.0)
stab_raw = (saw_s1 + saw_s2 + pulse_s) / 3.0
stab_filt = np.zeros_like(stab_raw)
cf_env = 4500.0 * np.exp(-t_stab * 15.0) + 400.0
y_p = 0.0
for i in range(len(stab_raw)):
    k = 2 * np.pi * cf_env[i] / sr
    a = k / (k + 1.0)
    y_p = y_p + a * (stab_raw[i] - y_p)
    stab_filt[i] = y_p
env_stab = np.exp(-t_stab * 8.5)
chord_stab = np.tanh(stab_filt * env_stab * 2.0) * 0.92
save_wav('inst11_chord_stab.wav', chord_stab)

# 12. SYNTH STRINGS / WARM PAD (Inst 12)
dur_pad = 1.0
t_pad = np.linspace(0, dur_pad, int(sr * dur_pad), endpoint=False)
pad1 = 2.0 * ((t_pad * f_c4 * 1.003) % 1.0) - 1.0
pad2 = 2.0 * ((t_pad * f_c4 * 0.997) % 1.0) - 1.0
pad_mix = biquad_filter(0.5 * pad1 + 0.5 * pad2, 2800.0, 1.2, 'lowpass')
att_p = int(sr * 0.04)
pad_mix[:att_p] *= np.linspace(0, 1, att_p)
l_start_12 = 4410
l_len_12 = 22050
pad_looped = make_crossfade_loop(pad_mix, l_start_12, l_len_12, xfade=2000)
pad_looped = pad_looped / np.max(np.abs(pad_looped)) * 0.85
save_wav('inst12_pad_str.wav', pad_looped)
print(f"Pad Strings: loop_start={l_start_12}, loop_len={l_len_12}")

# 13. FX LASER / DOWN-ZAP (Inst 13)
dur_z = 0.10
t_z = np.linspace(0, dur_z, int(sr * dur_z), endpoint=False)
f_z = 3200.0 * np.exp(-t_z * 40.0) + 80.0
phase_z = 2 * np.pi * np.cumsum(f_z) / sr
zap = np.tanh(np.sign(np.sin(phase_z)) * np.exp(-t_z * 25.0) * 1.5) * 0.85
save_wav('inst13_fx_zap.wav', zap)

# 14. FX NOISE RISER (Inst 14)
dur_r = 1.82
t_r = np.linspace(0, dur_r, int(sr * dur_r), endpoint=False)
noise_r = np.random.uniform(-1, 1, len(t_r))
riser_filt = np.zeros_like(noise_r)
y1 = y2 = x1 = x2 = 0.0
cf_r = 400.0 * ((6500.0 / 400.0) ** (t_r / dur_r))
for i in range(len(noise_r)):
    w0 = 2 * np.pi * cf_r[i] / sr
    alpha = np.sin(w0) / (2 * 2.0)
    cos_w0 = np.cos(w0)
    b0 = alpha; b1 = 0; b2 = -alpha
    a0 = 1 + alpha; a1 = -2 * cos_w0; a2 = 1 - alpha
    b0, b1, b2, a1, a2 = b0/a0, b1/a0, b2/a0, a1/a0, a2/a0
    x0 = noise_r[i]
    out = b0*x0 + b1*x1 + b2*x2 - a1*y1 - a2*y2
    riser_filt[i] = out
    x2, x1 = x1, x0
    y2, y1 = y1, out
env_r = (t_r / dur_r) ** 1.8
riser = np.tanh(riser_filt * env_r * 2.5) * 0.90
save_wav('inst14_fx_riser.wav', riser)
