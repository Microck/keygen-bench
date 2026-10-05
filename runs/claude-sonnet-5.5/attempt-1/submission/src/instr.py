import numpy as np
import sounds as S
from sounds import SR, rel_ft, note_freq
from xmw import Sample, Instrument

BPM = 140
ROW_S = 6 * 2.5 / BPM          # seconds per row at speed 6
BAR_S = 16 * ROW_S

def build():
    S.rng = np.random.default_rng(20240607)
    ins = []     # list of Instrument
    idx = {}
    def add(key, inst):
        ins.append(inst); idx[key] = len(ins)    # 1-based

    # ---------------- drums
    add('kick', S.oneshot('Kick', S.make_kick(), vol=64))
    add('snare', S.oneshot('Snare', S.make_snare(), vol=64))
    add('clap', S.oneshot('Clap', S.make_clap(), vol=64, pan=128))
    add('hatc', S.oneshot('Hat closed', S.make_hat(0.12, 0.028), vol=64, pan=176))
    add('hato', S.oneshot('Hat open', S.make_hat(0.55, 0.16), vol=64, pan=176))
    add('shaker', S.oneshot('Shaker', S.make_shaker(), vol=64, pan=78))
    add('tom', S.oneshot('Tom', S.make_tom(), vol=64, pan=128))
    add('crash', S.oneshot('Crash', S.make_crash(), vol=64, pan=128))
    add('riser2', S.oneshot('Riser 2 bars', S.make_riser(2 * BAR_S), vol=64, pan=128,
                            pan_env=[(0, 10), (60, 22), (192, 54)]))
    add('riser1', S.oneshot('Riser 1 bar', S.make_riser(BAR_S), vol=64, pan=128,
                            pan_env=[(0, 12), (30, 22), (96, 52)]))
    add('impact', S.oneshot('Impact', S.make_impact(), vol=64, pan=128))

    # ---------------- bass: filtered saw + fundamental
    def bass_loop(k, H, N):
        a = S.saw_amps(H, tilt=1.0, hc=7.0 + 3 * k)
        a = a.copy(); a[0] *= 1.8
        return S.unison_loop(N, 1, [0], a)
    add('bass', S.zone_instrument('Bass', [0, 1, 2, 3], bass_loop, N=512, vol=64, pan=128,
                                  vol_env=[(0, 64), (1, 62), (4, 0)], vol_sus=1))
    def sub_loop(k, H, N):
        a = np.zeros(4); a[0] = 1.0; a[1] = 0.12
        return S.unison_loop(N, 1, [0], a)
    add('sub', S.zone_instrument('Sub', [0, 1, 2, 3], sub_loop, N=256, vol=64, pan=128,
                                 vol_env=[(0, 0), (2, 64), (20, 64), (24, 0)], vol_sus=2))

    # ---------------- supersaw lead (+ echo twin) and stab
    def ss_loop(k, H, N):
        a = S.saw_amps(H, tilt=0.95)
        return S.unison_loop(N, 192, [-2, -1, 0, 1, 2], a, [0.55, 0.85, 1.0, 0.85, 0.55], seed=k)
    lead_env = dict(vol_env=[(0, 0), (2, 64), (10, 58), (17, 0)], vol_sus=2, vib=(0, 22, 7, 26))
    add('lead', S.zone_instrument('Lead SS', [3, 4, 5, 6, 7], ss_loop, N=256, vol=64, pan=96, **lead_env))
    add('leadE', S.zone_instrument('Lead echo', [3, 4, 5, 6, 7], ss_loop, N=256, vol=64, pan=222, **lead_env))

    # ---------------- pads (three pans) in three brightness variants: warm / bright ('b') / dark ('d')
    def pad_factory(hc):
        def pad_loop(k, H, N):
            a = S.saw_amps(H, tilt=1.0, hc=hc)
            return S.unison_loop(N, 192, [-3, -1, 0, 2, 3], a, [0.6, 0.9, 1.0, 0.9, 0.6], seed=10 + k)
        return pad_loop
    pad_env = dict(vol_env=[(0, 0), (7, 64), (24, 60), (38, 0)], vol_sus=2)
    for suffix, hc, label in (('', 5.0, 'warm'), ('b', 12.0, 'bright'), ('d', 2.5, 'dark')):
        for nm, pn in (('padL', 34), ('padC', 128), ('padR', 222)):
            extra = {}
            if nm == 'padC':   # slow auto-pan on the centre voice
                extra = dict(pan_env=[(0, 32), (30, 22), (60, 32), (90, 42), (120, 32)], pan_loop=(0, 4))
            add(nm + suffix, S.zone_instrument('Pad %s %s' % (nm[-1], label), [2, 3, 4, 5], pad_factory(hc), N=256,
                                               vol=64, pan=pn, **pad_env, **extra))

    # ---------------- pluck arp (+ echo twin) and bell (+ echo)
    rel_env = dict(vol_env=[(0, 64), (1, 64), (4, 0)], vol_sus=1)
    pl_env = dict(vol_env=[(0, 64), (2, 64), (7, 0)], vol_sus=1)
    add('pluck', S.oneshot_zone_instrument('Pluck', [3, 4, 5, 6, 7], S.pluck_note, vol=64, pan=52, **pl_env))
    add('pluckE', S.oneshot_zone_instrument('Pluck echo', [3, 4, 5, 6, 7], S.pluck_note, vol=64, pan=204, **pl_env))
    add('bell', S.oneshot_zone_instrument('Bell', [3, 4, 5, 6, 7], S.bell_note, vol=64, pan=196, **rel_env))
    add('bellE', S.oneshot_zone_instrument('Bell echo', [3, 4, 5, 6, 7], S.bell_note, vol=64, pan=58, **rel_env))
    add('epiano', S.oneshot_zone_instrument('E-Piano', [2, 3, 4, 5, 6], S.epiano_note, vol=64, pan=164, **rel_env))
    def chip_loop(k, H, N):
        return S.unison_loop(N, 1, [0], S.pulse_amps(H, 0.25))
    add('chip', S.zone_instrument('Chip pulse', [3, 4, 5, 6], chip_loop, N=256, vol=64, pan=204, spread=2.1,
                                  vol_env=[(0, 64), (1, 60), (3, 0)], vol_sus=1))
    return ins, idx

if __name__ == '__main__':
    ins, idx = build()
    tot = sum(len(s.data) * 2 for i in ins for s in i.samples)
    print(len(ins), 'instruments', tot / 1e6, 'MB', idx)
