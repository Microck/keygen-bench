"""Instrument bank: builds the XM instruments (sample data + tuning + default pan/volume)."""
import numpy as np
import synth as S
from xmwriter import Sample, Instrument


def i16(x):
    return np.round(np.clip(x, -1, 1) * 32767).astype(np.int16)


def build_bank():
    inst = []        # list of Instrument
    idx = {}         # name -> 1-based index

    def add(name, sample):
        inst.append(Instrument(name, sample))
        idx[name] = len(inst)

    def drum(name, x, vol=64, pan=128, n_ref=49):
        r, ft = S.drum_tuning(n_ref)
        add(name, Sample(i16(x), name=name, volume=vol, panning=pan, rel=r, finetune=ft))

    def looped(name, tup, n_ref, pan=128, vol=64):
        d, ls, ll, f0 = tup
        r, ft = S.tuning_for(f0, n_ref)
        add(name, Sample(i16(d), name, vol, pan, r, ft, ls, ll, 1))

    def oneshot(name, d, f0, n_ref, pan=128, vol=64):
        r, ft = S.tuning_for(f0, n_ref)
        add(name, Sample(i16(d), name, vol, pan, r, ft))

    drum("KICK", S.make_kick())
    # kicks tuned to the chord roots (A1 G1 F1 E1 / C2 D2): the sub of the kick and the bass reinforce, no beating
    for nm, f1 in (("A", 55.0), ("G", 49.0), ("F", 43.65), ("E", 41.2), ("C", 65.4), ("D", 73.4)):
        drum("KICK_" + nm, S.make_kick(f1=f1))
    drum("SNARE", S.make_snare())
    drum("CLAP", S.make_clap(), pan=120)
    hc = S.make_hat(0.10, 0.028)
    ho = S.make_hat(0.40, 0.11, bright=0.85)
    drum("HAT_C", hc, pan=150)
    drum("HAT_O", ho, pan=140)
    drum("HAT_C_L", hc, pan=96)
    drum("HAT_C_R", hc, pan=176)
    drum("HAT_O_L", ho, pan=100)
    drum("HAT_O_R", ho, pan=172)
    drum("TOM", S.make_tom(), pan=128)
    drum("RIM", S.make_rim(), pan=100)
    drum("CRASH", S.make_crash(), pan=150)

    looped("BASS", S.make_bass(), 22)                   # reference note A-1 = 55 Hz
    looped("SUB", S.make_sub(), 22)

    ss = S.make_supersaw(H=22, tilt=1.25)
    looped("LEAD", ss, 58)
    looped("LEAD_R", ss, 58, pan=205)
    looped("LEAD_L", ss, 58, pan=50)
    hi = S.make_supersaw(H=12, tilt=1.1)
    looped("LEAD_HI", hi, 58)
    looped("LEAD_HI_L", hi, 58, pan=50)
    looped("LEAD_HI_R", hi, 58, pan=205)
    # decorrelated stereo twins of the supersaw (same notes on two channels = wide lead)
    looped("LEAD_W1", S.make_supersaw(H=22, tilt=1.25, seed=101), 58, pan=70)
    looped("LEAD_W2", S.make_supersaw(H=22, tilt=1.25, seed=202), 58, pan=186)
    looped("LEAD_HI_W1", S.make_supersaw(H=12, tilt=1.1, seed=103), 58, pan=70)
    looped("LEAD_HI_W2", S.make_supersaw(H=12, tilt=1.1, seed=204), 58, pan=186)
    pw = S.make_pwm()
    looped("PWM", pw, 58)
    looped("PWM_HI", S.make_pwm(H=10), 58)
    looped("PWM_L", pw, 58, pan=70)
    looped("PWM_R", pw, 58, pan=186)

    d, f0 = S.make_pluck()
    oneshot("PLUCK_L", d, f0, 61, pan=70)
    oneshot("PLUCK_R", d, f0, 61, pan=186)
    oneshot("PLUCK", d, f0, 61, pan=128)
    for tag, mul in (("M", 0.6), ("D", 0.3)):          # 'filter-open' steps for intros / builds
        d, f0 = S.make_pluck(cut_mul=mul)
        oneshot(f"PLUCK_{tag}_L", d, f0, 61, pan=70)
        oneshot(f"PLUCK_{tag}_R", d, f0, 61, pan=186)
    d, f0 = S.make_bell()
    oneshot("BELL", d, f0, 61)
    oneshot("BELL_R", d, f0, 61, pan=190)

    # darker pad variants (cut-off 800 / 1500 Hz) used to 'open the filter' across intros and builds
    for tag, cut in (("D", 800.0), ("M", 1500.0)):
        for qn, ch in (("MIN", S.CH_MIN), ("MAJ", S.CH_MAJ)):
            looped(f"PAD_{qn}_L_{tag}", S.make_pad(ch, seed=7, cutoff=cut), 46, pan=40)
            looped(f"PAD_{qn}_R_{tag}", S.make_pad(ch, seed=19, cutoff=cut), 46, pan=216)
    looped("PAD_MIN_L", S.make_pad(S.CH_MIN, seed=7), 46, pan=40)
    looped("PAD_MIN_R", S.make_pad(S.CH_MIN, seed=19), 46, pan=216)
    looped("PAD_MAJ_L", S.make_pad(S.CH_MAJ, seed=7), 46, pan=40)
    looped("PAD_MAJ_R", S.make_pad(S.CH_MAJ, seed=19), 46, pan=216)

    sm = S.make_stab([0, 3, 7, 12], 220.0)
    sM = S.make_stab([0, 4, 7, 12], 220.0)
    oneshot("STAB_MIN", sm, 220.0, 46, pan=118)
    oneshot("STAB_MAJ", sM, 220.0, 46, pan=118)
    oneshot("STAB_MIN_L", sm, 220.0, 46, pan=85)
    oneshot("STAB_MIN_R", sm, 220.0, 46, pan=171)
    oneshot("STAB_MAJ_L", sM, 220.0, 46, pan=85)
    oneshot("STAB_MAJ_R", sM, 220.0, 46, pan=171)
    looped("VOX", S.make_vox(), 46)

    for nm, mk in (("RISER", S.make_riser), ("IMPACT", S.make_impact), ("REVCRASH", S.make_revcrash)):
        drum(nm, mk())
    return inst, idx


if __name__ == "__main__":
    inst, idx = build_bank()
    tot = 0
    for k, v in idx.items():
        s = inst[v - 1].sample
        tot += len(s.data) * 2
        print(v, k, len(s.data), s.loop_start, s.loop_len, s.rel, s.finetune, s.panning)
    print("total sample bytes", tot)
