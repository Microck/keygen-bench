import copy
import numpy as np
from synth import *

# instrument indices (1-based as in XM)
KICK, SNARE, CLAP, HATC, HATO, CRASH, TOM, BASS, LEADP, LEADS, PADMIN, PADMAJ, STABMIN, STABMAJ, \
PLUCK, ARPL, ARPR, BELL, RISER, REVC, ACID, ECHO, SAWECHO, LEADSR, SHAKER = range(1, 26)

def env(points, sustain=None, loop=None):
    return dict(points=points, sustain=sustain, loop=loop)

def with_pan(ins, pan, name=None):
    c = copy.deepcopy(ins)
    for s in c.samples: s.pan = pan
    if name: c.name = name
    return c

def oneshot_inst(sample, name):
    s = sample
    return Instrument(name, [s], [0] * 96, None, None, (0, 0, 0, 0), 0)

def build_all(riser_seconds, revc_seconds):
    I = {}
    I[KICK] = oneshot_inst(make_kick(), "Kick")
    I[SNARE] = oneshot_inst(make_snare(), "Snare")
    I[CLAP] = oneshot_inst(make_clap(), "Clap")
    I[HATC] = oneshot_inst(make_hat(False), "HatClosed")
    I[HATO] = oneshot_inst(make_hat(True), "HatOpen")
    I[CRASH] = oneshot_inst(make_crash(), "Crash")
    I[TOM] = oneshot_inst(make_tom(), "Tom")
    I[SHAKER] = oneshot_inst(make_shaker(), "Shaker")
    I[RISER] = oneshot_inst(make_riser(riser_seconds), "Riser")
    I[REVC] = oneshot_inst(make_revcrash(revc_seconds), "ReverseCrash")

    bass_groups = [(1, 33, 29), (34, 45, 40), (46, 64, 52)]
    I[BASS] = make_group_instrument("SawBass", bass_groups, lambda r, h: gen_bass(r, h),
        vol_env=env([(0, 64), (1, 64), (5, 0)], sustain=1), peak=0.95)

    lead_groups = [(1, 52, 46), (53, 60, 54), (61, 66, 60), (67, 72, 66), (73, 78, 72), (79, 86, 79), (87, 96, 88)]
    I[LEADP] = make_group_instrument("PWMLead", lead_groups, lambda r, h: gen_pwm(r, h),
        vol_env=env([(0, 0), (1, 64), (2, 64), (7, 0)], sustain=2), vib=(0, 14, 6, 30))
    I[ECHO] = with_pan(I[LEADP], 200, "PWMEcho")
    I[LEADS] = make_group_instrument("SuperSaw", lead_groups, lambda r, h: gen_supersaw(r, h),
        vol_env=env([(0, 0), (1, 64), (2, 64), (10, 0)], sustain=2), vib=(0, 16, 6, 28))
    I[SAWECHO] = with_pan(I[LEADS], 56, "SawEcho")
    I[LEADSR] = make_group_instrument("SuperSawR", lead_groups,
        lambda r, h: gen_supersaw(r, h, deltas=(-3, -1, 0, 1, 3), weights=(0.6, 0.95, 1.0, 0.95, 0.6), seed=77),
        vol_env=env([(0, 0), (1, 64), (2, 64), (10, 0)], sustain=2), vib=(0, 16, 6, 28), pan=176)
    for s_ in I[LEADS].samples: s_.pan = 80

    pad_groups = [(1, 40, 28), (41, 52, 40), (53, 64, 52), (65, 96, 64)]
    # chord bins for K=128: minor [128,152,192,256] ; major [128,161,192,256]
    I[PADMIN] = make_group_instrument("PadMinor", pad_groups,
        lambda r, h: gen_chord(r, h, [128, 152, 192, 256], fc=2000.0),
        vol_env=env([(0, 0), (16, 64), (17, 64), (34, 0)], sustain=2), peak=0.9)
    I[PADMAJ] = make_group_instrument("PadMajor", pad_groups,
        lambda r, h: gen_chord(r, h, [128, 161, 192, 256], seed=23, fc=2000.0),
        vol_env=env([(0, 0), (16, 64), (17, 64), (34, 0)], sustain=2), peak=0.9)
    I[STABMIN] = make_group_instrument("StabMinor", pad_groups,
        lambda r, h: gen_chord(r, h, [128, 152, 192, 256], fc=5200.0, tilt=1.0, seed=31),
        vol_env=env([(0, 64), (3, 50), (8, 18), (16, 0)]), peak=0.9)
    I[STABMAJ] = make_group_instrument("StabMajor", pad_groups,
        lambda r, h: gen_chord(r, h, [128, 161, 192, 256], fc=5200.0, tilt=1.0, seed=33),
        vol_env=env([(0, 64), (3, 50), (8, 18), (16, 0)]), peak=0.9)

    pluck_groups = [(1, 56, 46), (57, 68, 58), (69, 80, 70), (81, 96, 82)]
    I[PLUCK] = make_group_instrument("Pluck", pluck_groups, lambda r, h: gen_pluck(r, h),
        vol_env=env([(0, 64), (1, 64), (4, 0)], sustain=1), peak=0.9)

    arp_groups = [(1, 60, 52), (61, 72, 64), (73, 84, 76), (85, 96, 88)]
    I[ARPL] = make_group_instrument("ChipArpL", arp_groups, lambda r, h: gen_chipwave(r, h, 0.25),
        vol_env=env([(0, 0), (1, 64), (2, 64), (6, 0)], sustain=2), pan=60)
    I[ARPR] = make_group_instrument("ChipArpR", arp_groups, lambda r, h: gen_chipwave(r, h, 0.125, tri=0.2),
        vol_env=env([(0, 0), (1, 64), (2, 64), (6, 0)], sustain=2), pan=196)

    bell_groups = [(1, 60, 52), (61, 72, 64), (73, 96, 76)]
    I[BELL] = make_group_instrument("FMBell", bell_groups, lambda r, h: gen_fmbell(r, h),
        vol_env=env([(0, 64), (1, 64), (14, 0)], sustain=1), peak=0.9)

    acid_groups = [(1, 40, 26), (41, 96, 38)]
    I[ACID] = make_group_instrument("AcidBass", acid_groups, lambda r, h: gen_acid(r, h),
        vol_env=env([(0, 64), (1, 64), (3, 0)], sustain=1), peak=0.95)
    return I
