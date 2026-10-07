"""Build the module, round-trip it through FT2 (native writer), render a preview and publish to /workspace/submission."""
import os, shutil, subprocess, sys
import numpy as np
from ftlib import call
from analyze import load_wav, report
import compose

SUB = '/workspace/submission'
os.makedirs(SUB, exist_ok=True)
T, ins, idx = compose.build_song()
n, order, nu = compose.finalize(T, ins, '/workspace/work/song.xm')
print('built', n, 'bytes; patterns', nu)
# round-trip through FT2's own writer
call('module_load', path='/workspace/work/song.xm')
call('module_save', path='/workspace/work/song_ft2.xm', format='xm')
# verify the FT2-saved file renders identically to mine
call('module_load', path='/workspace/work/song.xm')
call('module_render', path='/workspace/work/r_mine.wav')
call('module_load', path='/workspace/work/song_ft2.xm')
call('module_render', path='/workspace/work/r_ft2.wav')
a, sr = load_wav('/workspace/work/r_mine.wav'); b, _ = load_wav('/workspace/work/r_ft2.wav')
print('render identical:', a.shape == b.shape and np.abs(a - b).max() == 0, 'maxdiff', np.abs(a - b).max() if a.shape == b.shape else 'shape')
shutil.copy('/workspace/work/song_ft2.xm', SUB + '/tune.xm')
shutil.copy('/workspace/work/r_ft2.wav', SUB + '/preview.wav')
report(b, sr)
