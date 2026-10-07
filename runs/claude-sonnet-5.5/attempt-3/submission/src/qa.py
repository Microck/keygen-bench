"""QA gate for the final module: structure, loop seam, levels, clipping, integrity."""
import sys, json, hashlib, os
sys.path.insert(0, '/workspace/work')
from ft2lib import *

def read_xm_header(path):
    b = open(path, 'rb').read()
    assert b[:17] == b'Extended Module: '
    ver = int.from_bytes(b[58:60], 'little')
    hsz = int.from_bytes(b[60:64], 'little')
    slen, rst, nch, npat, nins, flags, spd, bpm = [int.from_bytes(b[64 + 2 * i:66 + 2 * i], 'little') for i in range(8)]
    order = list(b[80:80 + slen])
    return dict(version=hex(ver), header_size=hsz, song_length=slen, restart=rst, channels=nch, patterns=npat,
                instruments=nins, linear_freq=bool(flags & 1), speed=spd, bpm=bpm, order=order, bytes=len(b))

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''): h.update(ch)
    return h.hexdigest()

def run(xm, wav):
    info = read_xm_header(xm)
    call("module_load", path=xm)
    mi = json.loads(call("module_info"))
    call("module_render", path=wav)
    a, sr = read_wav(wav)
    pk = float(np.abs(a).max()); rms = float(np.sqrt((a ** 2).mean()))
    res = dict(xm=info, tool_info=mi, render=dict(rate=sr, seconds=round(len(a) / sr, 2), peak=round(pk, 4),
               peak_dbfs=round(20 * np.log10(pk), 2), rms_dbfs=round(20 * np.log10(rms), 2),
               clipped_samples=int((np.abs(a) >= 0.9999).sum()), dc_offset=[round(float(x), 6) for x in a.mean(0)]))
    # loop seam: end of last pattern -> restart pattern
    last = info['song_length'] - 1; rst = info['restart']
    call("module_render", path=wav + ".end.wav", start=last)
    call("module_render", path=wav + ".rst.wav", start=rst, stop=rst)
    e, _ = read_wav(wav + ".end.wav"); s, _ = read_wav(wav + ".rst.wav")
    w = int(0.25 * sr)
    sp = np.concatenate([e[-w:], s[:w]])
    d = np.abs(np.diff(sp, axis=0)).max(axis=1)
    k = w - 1
    loc = float(np.sqrt((d[k - 2000:k + 2000] ** 2).mean()))
    def rdb(x): return round(float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)), 1)
    res['loop_seam'] = dict(step_at_seam=round(float(d[k]), 5), local_rms_step=round(loc, 5),
                            last_1s_rms_db=rdb(e[-sr:]), restart_first_1s_rms_db=rdb(s[:sr]))
    res['sha256'] = sha256(xm)
    for p in (wav + ".end.wav", wav + ".rst.wav"): os.remove(p)
    # level at other mixer rates
    peaks = {}
    for rate in (48000, 96000):
        call("module_render", path=wav + ".r.wav", rate=rate)
        ar, _ = read_wav(wav + ".r.wav"); peaks[str(rate)] = round(float(np.abs(ar).max()), 4)
    os.remove(wav + ".r.wav")
    res['peak_at_other_rates'] = peaks
    # re-save through the tracker -> identical audio
    call("module_load", path=xm)
    call("module_save", path=wav + ".resave.xm", format="xm")
    call("module_load", path=wav + ".resave.xm"); call("module_render", path=wav + ".r2.wav")
    a2, _ = read_wav(wav + ".r2.wav")
    res['tracker_resave_identical_render'] = bool(a2.shape == a.shape and np.array_equal(a, a2))
    os.remove(wav + ".r2.wav"); os.remove(wav + ".resave.xm")
    call("module_load", path=xm)
    return res

if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1], sys.argv[2]), indent=1))
