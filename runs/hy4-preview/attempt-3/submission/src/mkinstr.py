import sys; sys.path.insert(0,'/workspace/work')
import numpy as np, synth, json, wave
from synth import SR

INST = {}

def add(name, x, ls, ll, **kw):
    INST[name] = dict(pcm=synth.to_b64(x), loop_start=ls, loop_length=ll, **kw)

# ---- drums (played at note C-5 -> ~natural rate) ----
k,_ ,_ = synth.mk_kick(); add('KICK', k, 0, 0, flags=16, vol=64, pan=128, rel=29, finetune=-24, shift=0)
s,_ ,_ = synth.mk_snare(); add('SNARE', s, 0, 0, flags=16, vol=64, pan=128, rel=29, finetune=-24, shift=0)
c,_ ,_ = synth.mk_clap(); add('CLAP', c, 0, 0, flags=16, vol=64, pan=140, rel=29, finetune=-24, shift=0)
h,_ ,_ = synth.mk_hat(0.045, 0.011, seed=51); add('CHAT', h, 0, 0, flags=16, vol=64, pan=100, rel=29, finetune=-24, shift=0)
o,_ ,_ = synth.mk_hat(0.30, 0.075, base=2100.0, hp_f=5200, noise=0.75, seed=53)
add('OHAT', o, 0, 0, flags=16, vol=64, pan=100, rel=29, finetune=-24, shift=0)
cr,_,_ = synth.mk_cymbal(1.4, 0.62); add('CRASH', cr, 0, 0, flags=16, vol=64, pan=156, rel=29, finetune=-24, shift=0)
sw,_,_ = synth.mk_sweep(1.6, True); add('SWEEP', sw, 0, 0, flags=16, vol=64, pan=128, rel=29, finetune=-24, shift=0)

# ---- pitched instruments ----
# theoretical base: content base freq = 524.11 / 2^oct_shift
BASE = 524.11
def base_for(shift): return BASE/2**shift

# BASS: shift 2 -> f0 ~131.0 Hz
f0 = base_for(2)
x, atk, L = synth.build_tone(f0, cycles=8,
        spec_fn=lambda f: synth.spec_saw(nmax=40, cut=1400, roll=1.4, f0=f, tilt=0.85),
        attack_cycles=1, attack_amp=1.7, sub=0.9, hp_cut=25, lp_cut=3500, peak=0.9)
add('BASS', x, atk, L, flags=17, vol=64, pan=128, rel=29, finetune=-24, shift=2)
print('BASS f0', 8*SR/L, 'len', len(x), 'atk', atk, 'poop', L)

# ARP: pulse 25%, shift 1 -> f0 ~262 Hz
f0 = base_for(1)
x, atk, L = synth.build_tone(f0, cycles=6,
        spec_fn=lambda f: synth.spec_pulse(duty=0.28, nmax=40, cut=5200, roll=1.0, f0=f),
        attack_cycles=1, attack_amp=1.5, trem_hz=None, lp_cut=9000, peak=0.85)
add('ARP', x, atk, L, flags=17, vol=64, pan=100, rel=29, finetune=-24, shift=1)
print('ARP f0', 6*SR/L, 'len', len(x), atk, L)

# LEAD: rich pulse/saw melody voice, shift 0 -> f0 ~524 Hz, baked vibrato
f0 = base_for(0)

def lead_spec(f):
    a = synth.spec_pulse(duty=0.42, nmax=44, cut=7000, roll=1.0, f0=f)
    b = synth.spec_saw(nmax=44, cut=3200, roll=1.2, f0=f, tilt=1.0)
    d = dict(a)
    for h, v in b: d[h] = d.get(h, 0.0) + 0.45*v
    return sorted(d.items())
x, atk, L = synth.build_tone(f0, cycles=105, spec_fn=lead_spec,
        attack_cycles=2, attack_amp=1.35, vib_hz=5.0, vib_cents=7.0,
        trem_hz=None, hp_cut=90, lp_cut=9500, peak=0.85)
add('LEAD', x, atk, L, flags=17, vol=64, pan=128, rel=29, finetune=-24, shift=0)
print('LEAD f0', 105*SR/L, 'len', len(x), atk, L)

# LEADDET: slightly detuned copy of the lead (baked +6 cents) -> chorus when doubled
f0 = base_for(0)*1.0035
x2, atk2, L2 = synth.build_tone(f0, cycles=105, spec_fn=lead_spec,
        attack_cycles=2, attack_amp=1.35, vib_hz=5.0, vib_cents=7.0,
        hp_cut=90, lp_cut=9500, peak=0.85)
add('LEADDET', x2, atk2, L2, flags=17, vol=64, pan=128, rel=29, finetune=-24, shift=0)
print('LEADDET f0', 105*SR/L2, 'len', len(x2), atk2, L2)

# PAD: soft sustaining chord voice, shift 1
f0 = base_for(1)
def pad_spec(f):
    d = {1: 1.0, 2: 0.32, 3: 0.20, 4: 0.10, 5: 0.055, 6: 0.026}
    out = [(h, v/np.sqrt(1+(h*f/1800.0)**2)) for h, v in d.items()]
    return out
x, atk, L = synth.build_tone(f0, cycles=92, spec_fn=pad_spec,
        attack_cycles=4, attack_amp=1.0, vib_hz=4.0, vib_cents=5.0,
        trem_hz=4.0, trem_depth=0.05, hp_cut=60, lp_cut=2600, peak=0.8)
add('PAD', x, atk, L, flags=17, vol=64, pan=128, rel=29, finetune=-24, shift=1)
print('PAD f0', 92*SR/L, 'len', len(x), atk, L)

if __name__ == '__main__':
    for name, d in INST.items():
        x = np.frombuffer(__import__('base64').b64decode(d['pcm']), dtype='<i2').astype(float)/32768
        w = wave.open(f'/workspace/work/snd_{name}.wav','w')
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x*32767).astype('<i2').tobytes()); w.close()
        print(f'{name:8s} len={len(x):6d} ({len(x)/SR*1000:7.1f} ms) peak={np.abs(x).max():.3f} rms={x.std():.3f} loop=({d["loop_start"]},{d["loop_length"]})')
