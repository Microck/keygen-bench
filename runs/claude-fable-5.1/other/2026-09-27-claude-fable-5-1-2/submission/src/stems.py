"""Render each channel separately (via filtered XM copies) and report levels."""
import sys, subprocess, json, numpy as np
sys.path.insert(0, '/workspace/src')
from xmwrite import write_xm, read_wav

def render(xm, wav, amp=None, extra=None):
    args = {"path": wav}
    if amp: args["amp"] = amp
    if extra: args.update(extra)
    subprocess.run(['ft2', 'call', 'module_load', json.dumps({"path": xm})], check=True, capture_output=True)
    r = subprocess.run(['ft2', 'call', 'module_render', json.dumps(args)], check=True, capture_output=True, text=True)
    return r.stdout

def stems(name, nch, pats, order, instruments, bpm, speed, restart, channels=None, tag='stem'):
    res = {}
    for ch in (channels if channels is not None else range(nch)):
        fp = [(rows, {k: v for k, v in cells.items() if k[1] == ch}) for rows, cells in pats]
        xm = f'/tmp/{tag}_{ch}.xm'; wav = f'/tmp/{tag}_{ch}.wav'
        write_xm(xm, name, nch, fp, order, instruments, bpm=bpm, speed=speed, restart=restart)
        render(xm, wav)
        d, sr = read_wav(wav)
        import os; os.remove(wav); os.remove(xm)
        m = d.mean(axis=1)
        res[ch] = (np.abs(d).max(), np.sqrt((m**2).mean()), d, sr)
    return res
