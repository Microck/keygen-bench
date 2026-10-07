import sys, json
sys.path.insert(0, "/workspace/scripts")
from calibrate2 import build_once, set_note, render, measure_freq, expected_rate

CANDIDATES = [20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
              41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,
              59,60,61,64,65,68,71,72,77,80,81,82,83,85,87,89,90,91,92,95,96,
              97,99,100,102,103,104,106,111,113,114,115,116,117]

def note_relative_for_sum(s):
    if s <= 96:
        return s, 0
    return 96, s - 96

def rate_const(sum_, finetune=0):
    return expected_rate(sum_, finetune)

def try_combo(sum_, L, finetune, target):
    note, rel = note_relative_for_sum(sum_)
    if rel < -48 or rel > 71 or note < 1 or note > 96 or L < 8:
        return None
    set_note(note, L, rel, finetune)
    render()
    exp_freq = rate_const(sum_, finetune) / L
    fmax = min(19500, exp_freq*2.5+80)
    fmin = max(4, exp_freq*0.4)
    f = measure_freq('/tmp/cal.wav', fmin=fmin, fmax=fmax)
    if f <= 0:
        return None
    err = abs(f - target) / target
    return f, err

def calibrate_note(target, tol=0.005, prefer_L=(150,900), max_tries=40, verbose=False):
    plans = []
    for s in CANDIDATES:
        rc = rate_const(s, 0)
        L = round(rc / target)
        if L < 16:
            continue
        plans.append((s, L))
    def pref_key(sl):
        s, L = sl
        lo, hi = prefer_L
        if lo <= L <= hi:
            return (0, abs(L-350))
        return (1, min(abs(L-lo), abs(L-hi)))
    plans.sort(key=pref_key)
    tries = 0
    best = None
    for s, L in plans:
        for ft in (0, 8, -8, 16, -16, 24, -24, -4, 4, 12, -12, 20, -20):
            tries += 1
            res = try_combo(s, L, ft, target)
            if res is not None:
                f, err = res
                if verbose:
                    print(f"  sum={s} L={L} ft={ft} f={f:.3f} err={err*100:.3f}%")
                if best is None or err < best[0]:
                    note, rel = note_relative_for_sum(s)
                    best = (err, dict(target=target, measured=f, err_pct=err*100,
                                       note=note, relative_note=rel, loop_length=L,
                                       finetune=ft, sum=s))
                if err < tol:
                    return best[1]
            if tries >= max_tries:
                return best[1] if best else None
    return best[1] if best else None

if __name__ == "__main__":
    build_once()
    targets = json.load(open("/tmp/targets.json"))
    out = {}
    import time
    t0=time.time()
    for name, f in targets.items():
        r = calibrate_note(f, verbose=False)
        out[name] = r
        print(name, round(f,2), "->", r)
    json.dump(out, open("/tmp/tuning_final.json","w"), indent=2)
    print("total time", time.time()-t0)
