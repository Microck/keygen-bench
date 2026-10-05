"""Build the module using a dedicated FT2 process (avoids the crashed persistent server)."""
import subprocess, json, threading, queue, time, os, sys, re, wave
import numpy as np
sys.path.insert(0, '/workspace/work')

class MCP:
    def __init__(self):
        env = dict(os.environ); env['SDL_AUDIODRIVER'] = 'dummy'
        env['HOME'] = '/workspace/isolated-home'
        env['XDG_CONFIG_HOME'] = '/workspace/isolated-home/.config'
        self.p = subprocess.Popen(['/usr/local/bin/ft2-clone', '--mcp'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
        self.q = queue.Queue()
        threading.Thread(target=self._r, daemon=True).start()
        threading.Thread(target=self._e, daemon=True).start()
        self.n = 0
    def _r(self):
        for line in self.p.stdout: self.q.put(line)
    def _e(self):
        for line in self.p.stderr: print('STDERR:', line.strip(), flush=True)
    def call(self, name, args):
        self.n += 1
        msg = json.dumps({'jsonrpc': '2.0', 'id': self.n, 'method': 'tools/call',
                          'params': {'name': name, 'arguments': args}})
        self.p.stdin.write(msg + '\n'); self.p.stdin.flush()
        try:
            line = self.q.get(timeout=120); r = json.loads(line)
        except queue.Empty:
            raise RuntimeError('timeout in ' + name)
        if 'error' in r: raise RuntimeError(str(r['error']))
        c = r['result']['content']
        if r['result'].get('isError'): raise RuntimeError(c[0]['text'])
        return c[0]['text']

SMP = '/workspace/work/smp'
NOTE_BASE = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(name):
    m = re.match(r'^([A-G]#?)[-]?(\d+)$', name)
    return 49 + 12*(int(m.group(2))-4) + NOTE_BASE[m.group(1)]
BASE_RATE = 8323.284269808079
def rel_for(bn):
    target = 12*np.log2(44100.0/BASE_RATE); val = target - (bn - 49)
    rel = int(round(val)); return rel, int(round((val-rel)*128))

INSTRUMENTS = [
    (1, 'lead_c4.wav', 'C-5', False, 'lead', 128),
    (2, 'bass_c3.wav', 'C-4', False, 'bass', 128),
    (3, 'bell_c5.wav', 'C-6', False, 'bell', 158),
    (4, 'pluck_c4.wav', 'C-5', False, 'pluck', 98),
    (5, 'pulse_c5.wav', 'C-6', False, 'pulse', 88),
    (6, 'kick.wav', 'C-4', False, 'kick', 128),
    (7, 'snare.wav', 'C-4', False, 'snare', 128),
    (8, 'hat.wav', 'C-4', False, 'hat', 152),
    (9, 'ohat.wav', 'C-4', False, 'ohat', 104),
    (10, 'pad_am.wav', 'C-5', True, 'pad-am', 72),
    (11, 'pad_fm.wav', 'C-5', True, 'pad-fm', 72),
    (12, 'pad_gm.wav', 'C-5', True, 'pad-gm', 72),
    (13, 'pad_em.wav', 'C-5', True, 'pad-em', 72),
    (14, 'pad_am_r.wav', 'C-5', True, 'pad-am-r', 184),
    (15, 'pad_fm_r.wav', 'C-5', True, 'pad-fm-r', 184),
    (16, 'pad_gm_r.wav', 'C-5', True, 'pad-gm-r', 184),
    (17, 'pad_em_r.wav', 'C-5', True, 'pad-em-r', 184),
]

def main(out='/workspace/submission/tune.xm', wav=None):
    from patterns import build, ORDER, LOOP_START
    m = MCP()
    m.call('module_new', {'channels': 12, 'name': 'serenity.keygen'})
    for num, fname, basenote, loop, iname, pan in INSTRUMENTS:
        m.call('sample_load', {'path': os.path.join(SMP, fname), 'instrument': num, 'sample': 0})
        rel, ft = rel_for(N(basenote))
        s = {'instrument': num, 'sample': 0, 'flags': 16, 'volume': 64, 'panning': pan,
             'relative_note': rel, 'finetune': ft}
        if loop:
            w = wave.open(os.path.join(SMP, fname)); ln = w.getnframes(); w.close()
            s['loop_start'] = 0; s['loop_length'] = ln; s['flags'] = 16 | 1
        m.call('sample_set', s)
        m.call('instrument_set', {'instrument': num, 'name': iname})
    P = build()
    for p in sorted(P):
        m.call('pattern_clear', {'pattern': p})
        if p == 0:
            m.call('pattern_set_length', {'pattern': 0, 'rows': 32})
        for (row, ch, note, ins, vol, eff, effp) in P[p]:
            c = {'pattern': p, 'row': row, 'channel': ch}
            if note is not None: c['note'] = note
            if ins is not None: c['instrument'] = ins
            if vol is not None: c['volume'] = vol
            if eff is not None: c['effect'] = eff
            if effp is not None: c['effect_param'] = effp
            m.call('pattern_set_cell', c)
    m.call('song_set', {'bpm': 140, 'speed': 6, 'length': len(ORDER), 'loop_start': LOOP_START})
    for i, p in enumerate(ORDER):
        m.call('order_set', {'position': i, 'pattern': p})
    m.call('module_save', {'path': out, 'format': 'xm'})
    # verify by reloading and rendering
    m.call('module_load', {'path': out})
    info = m.call('module_info', {})
    print('info:', info)
    if wav:
        print(m.call('module_render', {'path': wav, 'rate': 44100}))
    m.p.stdin.close(); m.p.wait(timeout=30)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/workspace/submission/tune.xm')
    ap.add_argument('--wav', default='/workspace/work/preview.wav')
    a = ap.parse_args()
    main(a.out, a.wav)
