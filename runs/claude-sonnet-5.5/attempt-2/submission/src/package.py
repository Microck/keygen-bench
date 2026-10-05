"""Build -> FT2 round-trip save -> validate -> preview render -> manifest. Re-runnable, deterministic."""
import os, sys, shutil, hashlib, json, time
sys.path.insert(0, '.'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import build as B
from ft2run import ft2, render, read_wav
from validate import validate_xm, sha256, qa_pitch

SUB = os.environ.get('TUNE_OUT', '/workspace/submission')      # delivery directory
WORK = os.environ.get('TUNE_WORK', '/workspace/work')          # scratch directory (renders)
os.makedirs(SUB, exist_ok=True)
os.makedirs(WORK, exist_ok=True)
log = []


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    log.append(s)


say('build', time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
src_xm = f'{WORK}/tune_src.xm'
n = B.build(src_xm)
say('generator wrote', os.path.basename(src_xm), n, 'bytes')
say('toolchain: python', sys.version.split()[0], '| numpy', np.__version__, '| engine: ft2-clone via MCP bridge')

# round-trip through the real FT2 engine so the delivered file is an FT2-saved module
ft2('module_load', {'path': src_xm})
ft2('module_save', {'path': f'{SUB}/tune.xm', 'format': 'xm'})
o, errs = validate_xm(f'{SUB}/tune.xm')
say('XM structure check:', 'OK' if not errs else errs[:5])
say(f"title={o['name']!r} channels={o['nch']} patterns={o['npat']} orders={o['songlen']} restart={o['restart']} instruments={o['ninst']} bpm={o['bpm']} speed={o['speed']} bytes={o['filesize']}")

worst, detail = qa_pitch(WORK)
say(f'tuning QA (pitched instruments vs 12-TET, FFT peak): worst |error| = {worst:.1f} cents  [{detail}]')

# renders: generator file vs. FT2-saved file must be sample-identical
render(src_xm, f'{WORK}/r_src.wav', bits=16)
render(f'{SUB}/tune.xm', f'{SUB}/preview.wav', bits=16)
a, sr = read_wav(f'{WORK}/r_src.wav')
b, _ = read_wav(f'{SUB}/preview.wav')
say('render equality (generator XM vs FT2-saved XM): max abs diff =', float(np.abs(a - b).max()))
rf = f'{WORK}/r_float.wav'
render(f'{SUB}/tune.xm', rf, bits=32)
x, _ = read_wav(rf)
pk = np.abs(x).max()
say(f'duration {len(x)/sr:.2f}s  peak {20*np.log10(pk):.2f} dBFS  rms {20*np.log10(np.sqrt((x**2).mean())):.2f} dBFS  clipped(16-bit) {(np.abs(b) >= 0.99997).sum()}  DC {x.mean():+.6f}')
# loop seam: render starting at the restart order and compare with the tail of the full render
render(f'{SUB}/tune.xm', f'{WORK}/r_loop.wav', bits=32, start=o['restart'])
y, _ = read_wav(f'{WORK}/r_loop.wav')
say('restart-order render == tail of full render: max abs diff =', float(np.abs(x[-len(y):] - y).max()))
say(f'seam: last frame {x[-1].tolist()}  first restart frame {y[0].tolist()}  last 50ms rms {np.sqrt((x[-2205:]**2).mean()):.5f}')

# sources + docs
os.makedirs(f'{SUB}/src', exist_ok=True)
for f in ['synth.py', 'bank.py', 'compose.py', 'build.py', 'mixer.py', 'xmwriter.py', 'ft2run.py', 'validate.py', 'package.py', 'xmparse.py', 'README_template.md']:
    shutil.copy(f, f'{SUB}/src/{f}')
shutil.rmtree(f'{SUB}/src/__pycache__', ignore_errors=True)
readme = open('README_template.md').read().format(nch=o['nch'], npat=o['npat'], ninst=o['ninst'], bpm=o['bpm'], speed=o['speed'], restart=o['restart'], dur=len(x) / sr)
readme += "\n## Final artefact digests (SHA-256)\n"
readme += f"* tune.xm      {sha256(f'{SUB}/tune.xm')}\n* preview.wav  {sha256(f'{SUB}/preview.wav')}\n"
open(f'{SUB}/README.md', 'w').write(readme)

# directory limits (counting the two files still to be written: build_log.txt, MANIFEST.sha256)
tot = 0
cnt = 2
for root, dirs, files in os.walk(SUB):
    for fn in files:
        p_ = os.path.join(root, fn)
        assert os.path.isfile(p_) and not os.path.islink(p_)
        if fn in ('build_log.txt', 'MANIFEST.sha256'):
            continue                                   # rewritten below; already counted
        tot += os.path.getsize(p_)
        cnt += 1
say(f'submission dir: {cnt} files, {tot/1048576:.1f} MiB (limits: 4096 files, 128 MiB), regular files only')
open(f'{SUB}/build_log.txt', 'w').write('\n'.join(log) + '\n')

# manifest last: nothing may change after it is computed
lines = []
for root, _, files in os.walk(SUB):
    for fn in sorted(files):
        p_ = os.path.join(root, fn)
        if fn == 'MANIFEST.sha256':
            continue
        lines.append(f'{sha256(p_)}  {os.path.relpath(p_, SUB)}')
open(f'{SUB}/MANIFEST.sha256', 'w').write('\n'.join(sorted(lines, key=lambda l: l.split('  ')[1])) + '\n')
