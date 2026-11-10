"""Builds the module through the FT2 tool (ft2 batch), saves tune.xm and a WAV preview."""
import base64, json, subprocess, sys, os
import numpy as np
import synth, song

OUT = os.environ.get('OUT', '/workspace/submission')
WORK = '/workspace/work'
MASTER = float(os.environ.get('MASTER', '1.0'))
TITLE = 'registration fever'


def make_calls(mute=None, extra_loop=False):
    S, I = synth.build_samples()
    sg, total_rows, restart_bar = song.build(I)
    calls = []

    def C(tool, **a):
        calls.append({'name': tool, 'arguments': a})

    C('module_new', channels=song.NCH, name=TITLE)
    for i, smp in enumerate(S):
        ins = i + 1
        data = np.clip(np.round(smp['data'].astype(np.float64) * MASTER), -32768, 32767).astype('<i2')
        C('sample_create_from_pcm', instrument=ins, sample=0, pcm=base64.b64encode(data.tobytes()).decode(),
          encoding='int16', name=smp['name'][:22])
        a = dict(instrument=ins, sample=0, name=smp['name'][:22], volume=smp['vol'], panning=smp['pan'],
                 finetune=smp['fine'], relative_note=smp['rel'])
        if smp['loop']:
            a.update(loop_start=smp['loop'][0], loop_length=smp['loop'][1], flags=0x11)
        else:
            a.update(loop_start=0, loop_length=0, flags=0x10)
        C('sample_set', **a)
        C('instrument_set', instrument=ins, name=smp['name'][:22])

    # slice the timeline into 64-row patterns, reuse identical ones
    npat = total_rows // 64
    pats, order, seen = [], [], {}
    for p in range(npat):
        cells = []
        for (row, ch), c in sorted(sg.cells.items()):
            if p * 64 <= row < (p + 1) * 64:
                if mute and ch in mute:
                    continue
                if c[0] == 0 and c[1] == 0 and c[2] == 0 and c[3] is None:
                    continue
                cells.append((row - p * 64, ch, c[0], c[1], c[2], c[3] or 0, c[4] if c[3] is not None else 0))
        key = tuple(cells)
        if key not in seen:
            seen[key] = len(pats)
            pats.append(cells)
        order.append(seen[key])
    for pi, cells in enumerate(pats):
        C('pattern_set_length', pattern=pi, rows=64)
        for (row, ch, note, ins, vol, fx, fxp) in cells:
            C('pattern_set_cell', pattern=pi, row=row, channel=ch, note=note, instrument=ins, volume=vol,
              effect=fx, effect_param=fxp)
    restart = restart_bar // 2
    if extra_loop:                       # test build: append the looped part once more
        order = order + order[restart:]
    for pos, p in enumerate(order):
        C('order_set', position=pos, pattern=p)
    C('song_set', name=TITLE, length=len(order), loop_start=restart, bpm=140, speed=3)
    return calls, order, len(pats), restart


def run(calls, tag):
    path = os.path.join(WORK, tag + '.json')
    json.dump(calls, open(path, 'w'))
    r = subprocess.run(['ft2', 'batch', path], capture_output=True, text=True)
    errs = [l for l in r.stdout.splitlines() if '"isError": true' in l]
    return r, errs


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'final'
    os.makedirs(WORK, exist_ok=True)
    if mode == 'final':
        calls, order, npat, restart = make_calls()
        calls.append({'name': 'module_save', 'arguments': {'path': os.path.join(OUT, 'tune.xm'), 'format': 'xm'}})
        calls.append({'name': 'module_render', 'arguments': {'path': os.path.join(OUT, 'preview.wav')}})
        calls.append({'name': 'module_info', 'arguments': {}})
        r, errs = run(calls, 'final')
        print('calls', len(calls), 'patterns', npat, 'order', order, 'restart', restart)
        print('errors', len(errs), errs[:5])
        print(r.stdout.splitlines()[-3:], r.stderr[-300:])
    elif mode == 'loop':
        calls, order, npat, restart = make_calls(extra_loop=True)
        # NB: always save before rendering -- saving makes FT2 re-prepare the loop points
        calls.append({'name': 'module_save', 'arguments': {'path': os.path.join(WORK, 'looptest.xm'), 'format': 'xm'}})
        calls.append({'name': 'module_render', 'arguments': {'path': os.path.join(WORK, 'looptest.wav')}})
        r, errs = run(calls, 'loop')
        print('errors', len(errs), errs[:5], r.stdout.splitlines()[-1:])
    elif mode == 'stem':
        keep = [int(x) for x in sys.argv[2].split(',')]
        mute = [c for c in range(song.NCH) if c not in keep]
        calls, order, npat, restart = make_calls(mute=mute)
        calls.append({'name': 'module_save', 'arguments': {'path': os.path.join(WORK, 'stem.xm'), 'format': 'xm'}})
        calls.append({'name': 'module_render', 'arguments': {'path': os.path.join(WORK, 'stem_%s.wav' % sys.argv[3])}})
        r, errs = run(calls, 'stem')
        print('errors', len(errs), errs[:5], r.stdout.splitlines()[-1:])
