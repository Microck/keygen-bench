#!/usr/bin/env python3
"""Rebuild the deliverables from source (deterministic):

    python3 src/make_submission.py

  1. compose.py synthesises the samples and writes the XM bytes,
  2. the FT2 clone loads that file and saves it again as ../tune.xm
     (so the shipped module is a file FastTracker itself wrote),
  3. the same FT2 instance renders ../preview.wav (one full pass),
  4. the loop is exercised for real (order list played intro+body+body):
     the second pass is compared with the first, the result and the mix
     statistics go to ../build_report.json, and the 8 bars around the loop
     point are saved as ../loop_seam_demo.wav,
  5. SHA-256 checksums of every shipped file go to ../MANIFEST.sha256.
"""
import hashlib
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compose  # noqa: E402


def ft2(name, **args):
    r = subprocess.run(['ft2', 'call', name, json.dumps(args)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout.strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def wav_data(path):
    b = open(path, 'rb').read()
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(b):
        cid, size = b[pos:pos + 4], struct.unpack('<I', b[pos + 4:pos + 8])[0]
        if cid == b'fmt ':
            fmt = b[pos + 8:pos + 8 + size]
        elif cid == b'data':
            data = b[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
    return fmt, data


def write_wav(path, fmt, data):
    with open(path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 4 + 8 + len(fmt) + 8 + len(data)) + b'WAVE')
        f.write(b'fmt ' + struct.pack('<I', len(fmt)) + fmt)
        f.write(b'data' + struct.pack('<I', len(data)) + data)


def main():
    raw = os.path.join(OUT, 'src', '_raw.xm')
    info = compose.export(raw)
    tune = os.path.join(OUT, 'tune.xm')
    ft2('module_load', path=raw)
    ft2('module_save', path=tune, format='xm')
    os.remove(raw)
    ft2('module_load', path=tune)
    print(ft2('module_info'))
    print(ft2('module_render', path=os.path.join(OUT, 'preview.wav')))
    # Loop check + seam demo.  A scratch copy of the module with the order
    # list written out twice (intro, body, body) makes the FT2 replayer run
    # straight through the loop point with its real channel state.
    import numpy as np
    n_ord, restart = len(info['order']), info['restart']
    raw_mod = bytearray(open(tune, 'rb').read())
    twice = list(raw_mod[80:80 + n_ord]) + list(raw_mod[80 + restart:80 + n_ord])
    struct.pack_into('<H', raw_mod, 64, len(twice))
    raw_mod[80:80 + 256] = bytes(twice) + bytes(256 - len(twice))
    scratch_xm = os.path.join(OUT, 'src', '_loop.xm')
    scratch_wav = os.path.join(OUT, 'src', '_loop.wav')
    with open(scratch_xm, 'wb') as f:
        f.write(bytes(raw_mod))
    ft2('module_load', path=scratch_xm)
    ft2('module_render', path=scratch_wav)
    fmt, data = wav_data(scratch_wav)
    os.remove(scratch_xm)
    os.remove(scratch_wav)
    ft2('module_load', path=tune)                 # leave the real module loaded
    pcm = np.frombuffer(data, dtype='<i2').reshape(-1, 2)
    _, one = wav_data(os.path.join(OUT, 'preview.wav'))
    one = np.frombuffer(one, dtype='<i2').reshape(-1, 2)
    n_once = len(one)
    n_body = len(pcm) - n_once
    n_intro = n_once - n_body
    first, second = pcm[n_intro:n_once].astype(np.int32), pcm[n_once:].astype(np.int32)
    bar = n_body * 2 // (len(info['order']) - restart) // 4      # frames per bar (2 bars per pattern)
    seam = pcm[n_once - 4 * bar:n_once + 4 * bar].astype(np.float64)
    n = min(len(seam), 44100 * 3 // 4)
    seam[-n:] *= np.linspace(1.0, 0.0, n)[:, None]   # demo file only: fade its cut-off end
    seam[:441] *= np.linspace(0.0, 1.0, 441)[:, None]  # ... and its cut-in start (10 ms)
    write_wav(os.path.join(OUT, 'loop_seam_demo.wav'), fmt, np.round(seam).astype('<i2').tobytes())
    x = one.astype(np.float64) / 32768.0
    report = {
        'title': compose.TITLE,
        'channels': compose.NCH, 'bpm': compose.BPM, 'speed': compose.SPEED,
        'orders': n_ord, 'restart_order': restart, 'patterns': info['patterns'],
        'one_pass_seconds': round(n_once / 44100.0, 3),
        'peak': round(float(np.abs(x).max()), 4),
        'rms': round(float(np.sqrt((x ** 2).mean())), 4),
        'dc_offset': round(float(x.mean()), 6),
        'full_scale_samples': int((np.abs(one.astype(np.int32)) >= 32767).sum()),
        'first_frame': one[0].tolist(), 'last_frame': one[-1].tolist(),
        'loop_second_pass_vs_first_pass_max_diff_lsb': int(np.abs(first - second).max()),
        'silent_frames_before_loop_point': int(np.argmax(np.abs(pcm[:n_once][::-1]).max(axis=1) > 1)),
    }
    with open(os.path.join(OUT, 'build_report.json'), 'w') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(report, sort_keys=True))
    files = []
    for root, _, names in os.walk(OUT):
        for n in sorted(names):
            p = os.path.join(root, n)
            rel = os.path.relpath(p, OUT)
            if rel == 'MANIFEST.sha256' or '__pycache__' in rel:
                continue
            files.append(rel)
    with open(os.path.join(OUT, 'MANIFEST.sha256'), 'w') as f:
        for rel in sorted(files):
            f.write('%s  %s\n' % (sha256(os.path.join(OUT, rel)), rel))
    print(json.dumps({k: info[k] for k in ('size', 'patterns', 'restart', 'rows', 'seconds')}))


if __name__ == '__main__':
    main()
