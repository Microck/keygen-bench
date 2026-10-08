"""Build tune.xm from the synthesis and composition scripts."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import synth, xmwrite, compose

def to_i16(x, peak=0.92):
    x = np.clip(x, -1.0, 1.0) * peak
    return np.round(x * 32767).astype(np.int16)

def build(out_path):
    s = synth.make_all()
    rel_d, ft_d = synth.pitch_for_rate(synth.RATE_DRUM)
    rel_t, ft_t = synth.pitch_for_rate(synth.C4_HZ * synth.N_LOOP)
    spec = [  # (xm name, key, loop?, relnote, finetune, volume)
        ("Kick", "kick", False, rel_d, ft_d, 60),
        ("Snare", "snare", False, rel_d, ft_d, 46),
        ("Hat Closed", "hat_c", False, rel_d, ft_d, 30),
        ("Hat Open", "hat_o", False, rel_d, ft_d, 26),
        ("Crash", "crash", False, rel_d, ft_d, 30),
        ("Riser", "riser", False, rel_d, ft_d, 30),
        ("Arp Pluck", "arp", False, rel_t, ft_t, 30),
        ("Bass Saw", "bass", True, rel_t, ft_t, 36),
        ("Lead Pulse", "lead", True, rel_t, ft_t, 34),
        ("Harmony Thin", "harm", True, rel_t, ft_t, 26),
        ("Pad Saw", "pad", True, rel_t, ft_t, 24),
        ("Lead Hi", "lead_hi", True, rel_t, ft_t, 30),
    ]
    instruments = []
    for (name, key, loop, rel, ft, vol) in spec:
        d = s[key]["data"]
        if loop:
            data, ls, ll = synth.looped_with_attack(d, cycles=2)
        else:
            data, ls, ll = d, 0, 0
        smp = dict(data=to_i16(data), loop_type=1 if loop else 0,
                   loop_start=ls, loop_len=ll,
                   volume=compose.scaled(vol), finetune=ft, relnote=rel, name=name)
        instruments.append((name, smp))
    plan, uniq, order = compose.main()
    patterns = [(compose.ROWS, p) for p in uniq]
    n = xmwrite.write_xm(out_path, "CIPHER DAWN", "FT2 keygen builder", compose.NCH,
                         patterns, order, instruments, speed=6, bpm=150, restart=0, flags=1)
    return n, len(order), len(uniq)

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "tune.xm"
    n, norders, npats = build(out)
    print("wrote", out, n, "bytes; orders", norders, "patterns", npats)
