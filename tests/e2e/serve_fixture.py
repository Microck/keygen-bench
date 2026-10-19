"""Assemble only canonical frontend assets and synthetic data in a disposable directory."""
import functools
import http.server
import json
import math
from pathlib import Path
import shutil
import signal
import struct
import sys
import tempfile
import wave
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/classic'))
from serve import Handler

def stop(*_):
    raise KeyboardInterrupt
signal.signal(signal.SIGTERM, stop)
with tempfile.TemporaryDirectory(prefix='keygen-browser-fixture-') as temp:
    root = Path(temp)
    for name in ['index.html', 'app.js', 'site.js', 'crypto.html']:
        shutil.copy2(ROOT / 'web/classic' / name, root / name)
    shutil.copytree(ROOT / 'web/classic/core', root / 'core')
    dist = root / 'dist'
    dist.mkdir()
    xm = bytearray(345)
    xm[:17] = b'Extended Module: '
    xm[17:17+9] = b'Synthetic'
    xm[37] = 0x1a
    struct.pack_into('<H', xm, 58, 0x104)
    struct.pack_into('<I', xm, 60, 276)
    for offset, value in [(64,1),(68,4),(70,1),(74,1),(76,6),(78,125)]:
        struct.pack_into('<H', xm, offset, value)
    struct.pack_into('<I', xm, 336, 9)
    struct.pack_into('<H', xm, 341, 64)
    (dist / 'fixture.xm').write_bytes(xm)
    with wave.open(str(dist / 'fixture.wav'), 'wb') as out:
        out.setparams((1,2,44100,0,'NONE','not compressed'))
        out.writeframes(b''.join(struct.pack('<h', int(500*math.sin(2*math.pi*440*i/44100))) for i in range(44100*4)))
    runs=[]
    for ordinal,score in [(1,60),(2,80)]:
        runs.append({'slug':f'synthetic-{ordinal}','model_key':'synthetic','name':f'Synthetic (attempt {ordinal})',
          'maker':'Test','score':score,'uncapped':score,'failed':False,'exhibition':False,'tier':'synthetic fixture',
          'listener':{'content_enjoyment':score/10,'production_quality':5,'content_usefulness':5,'production_complexity':5},
          'caps':[],'flags':[],'loop':{'quality':1,'first_pass_audible_seconds':4},
          'audio':{'duration':4,'lufs':-20,'peak':0.1},
          'module':{'name':'Synthetic','channels':4,'bpm':125,'speed':6,'song_length':1,'loop_start':0,'patterns':1,'instruments':0,'samples':0},
          'usage':{'completion_tokens':100,'wall_minutes':1},'cost_usd':0,
          'media':{'xm':'fixture.xm','audio':'fixture.wav','wav':'fixture.wav'},
          'trace':[[0,0,0,0],[44100,0,1,0]],'provenance':{'attempt_ordinal':ordinal}})
    (dist / 'data.json').write_text(json.dumps({'runs':runs,'repetition_groups':[],'limitations':[],'campaigns':[],'flag_rules':{}}))
    server = http.server.ThreadingHTTPServer(('127.0.0.1',4179),functools.partial(Handler,directory=str(root)))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
