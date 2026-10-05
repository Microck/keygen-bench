"""Generate all instrument samples and Instrument objects with perfectly calibrated headroom."""
import numpy as np
from compose_keygen import Instrument

def create_all_instruments():
    instruments = []
    
    # -------------------------------------------------------------
    # 1. Lead 1: Pulse 12.5% (Sharp, penetrating, fast attack, slight decay to sustain)
    # -------------------------------------------------------------
    inst_lead1 = Instrument("Lead Pulse 12%")
    t32 = np.arange(32) / 32
    pulse12_pcm = np.where(t32 < 0.125, 115, -115).astype(np.int8)
    inst_lead1.set_vol_envelope([(0, 64), (3, 64), (8, 52), (24, 0)], sustain_pt=1)
    inst_lead1.fadeout = 250
    inst_lead1.vib_type = 0 # sine
    inst_lead1.vib_sweep = 20
    inst_lead1.vib_depth = 2
    inst_lead1.vib_rate = 32
    inst_lead1.add_sample(pulse12_pcm, "Pulse 12%", finetune=2, loop=True, loop_start=0, loop_len=32, vol=40, pan=110)
    instruments.append(inst_lead1)

    # -------------------------------------------------------------
    # 2. Lead 2: Pulse 25% (Vibrant, bright, melodic lead)
    # -------------------------------------------------------------
    inst_lead2 = Instrument("Lead Pulse 25%")
    pulse25_pcm = np.where(t32 < 0.25, 115, -115).astype(np.int8)
    inst_lead2.set_vol_envelope([(0, 64), (4, 64), (10, 54), (28, 0)], sustain_pt=1)
    inst_lead2.fadeout = 250
    inst_lead2.vib_type = 0
    inst_lead2.vib_sweep = 16
    inst_lead2.vib_depth = 2
    inst_lead2.vib_rate = 34
    inst_lead2.add_sample(pulse25_pcm, "Pulse 25%", finetune=2, loop=True, loop_start=0, loop_len=32, vol=40, pan=146)
    instruments.append(inst_lead2)

    # -------------------------------------------------------------
    # 3. Echo / Delay Lead: Square 50% with short plucked envelope
    # -------------------------------------------------------------
    inst_echo = Instrument("Echo Square")
    square_pcm = np.where(t32 < 0.50, 110, -110).astype(np.int8)
    inst_echo.set_vol_envelope([(0, 64), (2, 50), (6, 30), (14, 0)])
    inst_echo.fadeout = 400
    inst_echo.add_sample(square_pcm, "Square 50%", finetune=2, loop=True, loop_start=0, loop_len=32, vol=32, pan=175)
    instruments.append(inst_echo)

    # -------------------------------------------------------------
    # 4. Arp Synth: Sawtooth (Buzzy, bright, continuous sustain for arpeggios)
    # -------------------------------------------------------------
    inst_arp = Instrument("Arp Sawtooth")
    saw_pcm = np.round((1.0 - 2.0 * t32) * 115).astype(np.int8)
    inst_arp.set_vol_envelope([(0, 64), (12, 60), (32, 0)], sustain_pt=1)
    inst_arp.fadeout = 300
    inst_arp.add_sample(saw_pcm, "Sawtooth", finetune=2, loop=True, loop_start=0, loop_len=32, vol=34, pan=95)
    instruments.append(inst_arp)

    # -------------------------------------------------------------
    # 5. Arp 2 / Countermelody: Pulse 37% (Slightly narrower than square)
    # -------------------------------------------------------------
    inst_arp2 = Instrument("Arp Pulse 37%")
    pulse37_pcm = np.where(t32 < 0.375, 110, -110).astype(np.int8)
    inst_arp2.set_vol_envelope([(0, 64), (10, 56), (28, 0)], sustain_pt=1)
    inst_arp2.fadeout = 300
    inst_arp2.add_sample(pulse37_pcm, "Pulse 37%", finetune=2, loop=True, loop_start=0, loop_len=32, vol=34, pan=160)
    instruments.append(inst_arp2)

    # -------------------------------------------------------------
    # 6. Chip Bass: Warm triangle + square blend, punchy envelope
    # -------------------------------------------------------------
    inst_bass = Instrument("Chip Bass")
    tri = 2.0 * np.abs(2.0 * (t32 - np.floor(t32 + 0.5))) - 1.0
    sq = np.where(t32 < 0.5, 1.0, -1.0)
    bass_blend = 0.65 * tri + 0.35 * sq + 0.15 * np.sin(4 * np.pi * t32)
    bass_blend = np.tanh(bass_blend * 1.5)
    bass_pcm = np.round(bass_blend / np.max(np.abs(bass_blend)) * 120).astype(np.int8)
    inst_bass.set_vol_envelope([(0, 64), (2, 64), (6, 52), (18, 0)], sustain_pt=1)
    inst_bass.fadeout = 350
    inst_bass.add_sample(bass_pcm, "Chip Bass", finetune=2, loop=True, loop_start=0, loop_len=32, vol=40, pan=128)
    instruments.append(inst_bass)

    # -------------------------------------------------------------
    # 7. Flute / Triangle: Sweet pure countermelody
    # -------------------------------------------------------------
    inst_tri = Instrument("Triangle Chiptune")
    tri_pcm = np.round(tri * 120).astype(np.int8)
    inst_tri.set_vol_envelope([(0, 50), (4, 64), (16, 56), (36, 0)], sustain_pt=2)
    inst_tri.fadeout = 200
    inst_tri.vib_type = 0
    inst_tri.vib_sweep = 24
    inst_tri.vib_depth = 2
    inst_tri.vib_rate = 30
    inst_tri.add_sample(tri_pcm, "Triangle", finetune=2, loop=True, loop_start=0, loop_len=32, vol=36, pan=135)
    instruments.append(inst_tri)

    # -------------------------------------------------------------
    # 8. Kick Drum: Punchy chiptune kick (one-shot)
    # -------------------------------------------------------------
    inst_kick = Instrument("Chiptune Kick")
    rate = 8363
    dur_k = 0.20
    t_k = np.linspace(0, dur_k, int(rate * dur_k), False)
    f_k = 42.0 + 210.0 * np.exp(-t_k * 38.0)
    phase_k = 2.0 * np.pi * np.cumsum(f_k) / rate
    click_k = np.exp(-t_k * 140.0) * np.sin(2.0 * np.pi * 950.0 * t_k)
    k_sig = np.sin(phase_k) * np.exp(-t_k * 16.0) + 0.35 * click_k
    k_pcm = np.round(np.tanh(k_sig * 1.8) * 122).astype(np.int8)
    inst_kick.add_sample(k_pcm, "Kick", loop=False, vol=42, pan=128)
    instruments.append(inst_kick)

    # -------------------------------------------------------------
    # 9. Snare Drum: Snappy chiptune snare (one-shot)
    # -------------------------------------------------------------
    inst_snare = Instrument("Chiptune Snare")
    dur_s = 0.18
    t_s = np.linspace(0, dur_s, int(rate * dur_s), False)
    f_s = 130.0 + 160.0 * np.exp(-t_s * 34.0)
    phase_s = 2.0 * np.pi * np.cumsum(f_s) / rate
    body_s = np.sin(phase_s) * np.exp(-t_s * 26.0)
    np.random.seed(1337)
    raw_n = np.random.uniform(-1.0, 1.0, len(t_s))
    noise_s = np.zeros_like(raw_n)
    for i in range(1, len(raw_n)):
        noise_s[i] = 0.72 * (noise_s[i-1] + raw_n[i] - raw_n[i-1])
    noise_env = np.exp(-t_s * 18.0)
    s_sig = 0.45 * body_s + 0.70 * noise_s * noise_env
    s_pcm = np.round(np.tanh(s_sig * 1.7) * 122).astype(np.int8)
    inst_snare.add_sample(s_pcm, "Snare", loop=False, vol=38, pan=128)
    instruments.append(inst_snare)

    # -------------------------------------------------------------
    # 10. Closed Hi-Hat: Crisp 40ms chiptune tick
    # -------------------------------------------------------------
    inst_hat = Instrument("Closed HiHat")
    dur_h = 0.04
    t_h = np.linspace(0, dur_h, int(rate * dur_h), False)
    np.random.seed(2024)
    raw_h = np.random.uniform(-1.0, 1.0, len(t_h))
    ring_h = (np.sign(np.sin(2 * np.pi * 3200 * t_h)) + 
              np.sign(np.sin(2 * np.pi * 4350 * t_h)) + 
              np.sign(np.sin(2 * np.pi * 6100 * t_h))) / 3.0
    h_sig = (0.5 * raw_h + 0.5 * ring_h) * np.exp(-t_h * 80.0)
    h_pcm = np.round(np.clip(h_sig * 1.5, -1.0, 1.0) * 120).astype(np.int8)
    inst_hat.add_sample(h_pcm, "Closed HiHat", loop=False, vol=30, pan=152)
    instruments.append(inst_hat)

    # -------------------------------------------------------------
    # 11. Open Hi-Hat: Sizzling 160ms open hat
    # -------------------------------------------------------------
    inst_ohat = Instrument("Open HiHat")
    dur_oh = 0.16
    t_oh = np.linspace(0, dur_oh, int(rate * dur_oh), False)
    np.random.seed(777)
    raw_oh = np.random.uniform(-1.0, 1.0, len(t_oh))
    ring_oh = (np.sign(np.sin(2 * np.pi * 3200 * t_oh)) + 
               np.sign(np.sin(2 * np.pi * 4350 * t_oh)) + 
               np.sign(np.sin(2 * np.pi * 6100 * t_oh))) / 3.0
    oh_sig = (0.5 * raw_oh + 0.5 * ring_oh) * np.exp(-t_oh * 22.0)
    oh_pcm = np.round(np.clip(oh_sig * 1.4, -1.0, 1.0) * 120).astype(np.int8)
    inst_ohat.add_sample(oh_pcm, "Open HiHat", loop=False, vol=32, pan=152)
    instruments.append(inst_ohat)

    # -------------------------------------------------------------
    # 12. Crash Cymbal: 0.55s chiptune explosion/wash
    # -------------------------------------------------------------
    inst_crash = Instrument("Crash Cymbal")
    dur_cr = 0.55
    t_cr = np.linspace(0, dur_cr, int(rate * dur_cr), False)
    np.random.seed(9999)
    raw_cr = np.random.uniform(-1.0, 1.0, len(t_cr))
    cr_sig = raw_cr * np.exp(-t_cr * 7.5) * 1.2
    cr_pcm = np.round(np.clip(cr_sig, -1.0, 1.0) * 120).astype(np.int8)
    inst_crash.add_sample(cr_pcm, "Crash Cymbal", loop=False, vol=36, pan=100)
    instruments.append(inst_crash)

    return instruments
