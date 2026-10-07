"""Independent structural + audio validation of the final module (audit evidence)."""
import sys, os, hashlib, struct
sys.path.insert(0, '.'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from xmparse import parse_xm
from ft2run import render, read_wav


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_xm(path):
    o = parse_xm(path)
    errs = []
    if o['filesize'] != o['parsed_end']:
        errs.append(f"trailing/short data: file {o['filesize']} parsed {o['parsed_end']}")
    if not (0 <= o['restart'] < o['songlen']):
        errs.append('restart out of range')
    if max(o['orders']) >= o['npat']:
        errs.append('order refers to missing pattern')
    for pi, p in enumerate(o['patterns']):
        for r in range(p['rows']):
            for c in range(o['nch']):
                n, i, v, e, par = p['data'][r][c]
                if n > 97: errs.append(f'P{pi} r{r} c{c}: note {n}')
                if i > o['ninst']: errs.append(f'P{pi} r{r} c{c}: inst {i}')
                if v and not (0x10 <= v <= 0xFF): errs.append(f'P{pi} r{r} c{c}: vol {v:#x}')
                if v in range(0x51, 0x60): errs.append(f'P{pi} r{r} c{c}: undefined vol col {v:#x}')
                if e > 0x23: errs.append(f'P{pi} r{r} c{c}: effect {e}')
                if n and n != 97 and not i: pass
    for k, ins in enumerate(o['instruments']):
        for s in ins['samples']:
            if s['type'] & 3 and s['loop_start'] + s['loop_len'] > s['len']:
                errs.append(f'inst {k+1} loop outside sample')
            if s['len'] % 2: errs.append(f'inst {k+1} odd 16-bit length')
    return o, errs


if __name__ == '__main__':
    path = sys.argv[1]
    o, errs = validate_xm(path)
    print('XM structure:', 'OK' if not errs else errs[:10])
    print(f"  title={o['name']!r} tracker={o['tracker']!r} channels={o['nch']} patterns={o['npat']} orders={o['songlen']} restart={o['restart']} instruments={o['ninst']} bpm={o['bpm']} speed={o['speed']} size={o['filesize']}")
    print('  sha256', sha256(path))


def qa_pitch(work='/tmp'):
    """Render a short test module that plays each pitched instrument once and report the tuning error
    (evidence that every instrument plays in tune at 12-TET, A4 = 440 Hz)."""
    from xmwriter import Pattern, write_xm
    from bank import build_bank
    inst, idx = build_bank()
    tests = [("BASS", 22, 55.0), ("SUB", 22, 55.0), ("LEAD", 58, 440.0), ("LEAD_HI", 70, 880.0), ("LEAD_W1", 58, 440.0),
             ("PWM", 58, 440.0), ("PLUCK", 61, 523.25), ("BELL", 61, 523.25), ("PAD_MIN_L", 46, 220.0),
             ("PAD_MAJ_R", 41, 164.81), ("VOX", 46, 220.0), ("STAB_MIN", 46, 220.0)]
    rows_each = 8
    p = Pattern(rows_each * len(tests), 8)
    for k, (nm, note, f) in enumerate(tests):
        p.set(k * rows_each, 0, note=note, inst=idx[nm], vol=0x50)
        p.set(k * rows_each + rows_each - 1, 0, vol=0x10)
    xm = os.path.join(work, 'qa_pitch.xm')
    wav = os.path.join(work, 'qa_pitch.wav')
    write_xm(xm, 'qa', 8, [0], 0, 150, 6, [p], inst)
    render(xm, wav, bits=32)
    x, sr = read_wav(wav)
    m = x.mean(axis=1)
    out = []
    worst = 0.0
    for k, (nm, note, f) in enumerate(tests):
        a = int((k * rows_each + 1) * 0.1 * sr)
        b = int((k * rows_each + 6) * 0.1 * sr)
        seg = m[a:b] * np.hanning(b - a)
        sp = np.abs(np.fft.rfft(seg, 1 << 19))
        fr = np.fft.rfftfreq(1 << 19, 1 / sr)
        sel = (fr > f * 0.94) & (fr < f * 1.06)
        pk = fr[sel][np.argmax(sp[sel])]
        cents = 1200 * np.log2(pk / f)
        worst = max(worst, abs(cents))
        out.append(f"{nm}:{cents:+.1f}c")
    return worst, ' '.join(out)
