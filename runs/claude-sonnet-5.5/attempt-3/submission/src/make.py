import sys, os, hashlib, json, time
sys.path.insert(0, '/workspace/work')
from compose import *
from ft2lib import call, read_wav, write_wav

def build(path, only=None, mute=None, npat=16):
    t0 = time.time()
    I = build_all(31.4 * ROW_S, 14.4 * ROW_S)
    for k, ins in I.items():
        for smp in ins.samples:
            smp.volume = int(round(64 * TRIM.get(k, 1.0)))
    insts = [I[k] for k in sorted(I)]
    assert [k for k in sorted(I)] == list(range(1, len(I) + 1))
    S = build_song(npat)
    hang = hanging_notes(S)
    if hang: print('WARNING hanging notes at loop point on channels', hang)
    if only is not None or mute is not None:
        for key in list(S.cells):
            ch = key[1]
            if (only is not None and ch not in only) or (mute is not None and ch in mute):
                del S.cells[key]
    if CLAMPED and not os.environ.get('QUIET'): print('note: %d volume-column values clamped to 64 (kick/accents at full level)' % len(CLAMPED))
    pats = S.patterns()
    # de-duplicate identical patterns
    uniq = []; order = []; seen = {}
    for rows, cells in pats:
        sig = hashlib.md5(json.dumps(sorted((k, (c.note, c.inst, c.vol, c.fx, c.fxp)) for k, c in cells.items())).encode()).hexdigest()
        if sig not in seen:
            seen[sig] = len(uniq); uniq.append((rows, cells))
        order.append(seen[sig])
    write_xm(path, "Neon Serial", NCH, order, uniq, insts, restart=RESTART, speed=SPEED, bpm=BPM)
    return order, time.time() - t0

def render(xm, wav, amp=None):
    call("module_load", path=xm)
    kw = dict(path=wav)
    if amp: kw['amp'] = amp
    call("module_render", **kw)
    return read_wav(wav)

def analyze(a, sr, label=""):
    mono = a.mean(1)
    pk = np.abs(a).max(); rms = np.sqrt((a ** 2).mean())
    print(f"{label} dur {len(a)/sr:.2f}s peak {pk:.3f} ({20*np.log10(pk+1e-12):.1f} dBFS) rms {20*np.log10(rms+1e-12):.1f} dBFS  clip>0.999: {(np.abs(a)>0.999).sum()}  dc {a.mean(0)}")
    return pk, rms

if __name__ == "__main__":
    order, dt = build("/workspace/work/tune.xm")
    print("order", order, "build s", round(dt, 1), "size", os.path.getsize("/workspace/work/tune.xm"))
    a, sr = render("/workspace/work/tune.xm", "/workspace/work/tune.wav")
    analyze(a, sr, "mix")
    # per-pattern rms
    pl = int(ROWS * ROW_S * sr)
    for p in range(len(a) // pl):
        seg = a[p * pl:(p + 1) * pl]
        print(p, f"peak {np.abs(seg).max():.2f} rms {20*np.log10(np.sqrt((seg**2).mean())+1e-12):.1f}")
