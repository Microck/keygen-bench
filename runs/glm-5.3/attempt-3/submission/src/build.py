"""Build tune.xm via the ft2 batch interface, then render a preview."""
import json, os, subprocess, sys
sys.path.insert(0, '/workspace/src')
import compose as C

BATCH = '/workspace/src/batch.json'

def main():
    batch = []
    batch.append({'name': 'module_new',
                  'arguments': {'channels': C.NCH, 'name': 'Crackme Anthem'}})
    batch.append({'name': 'song_set',
                  'arguments': {'bpm': C.TEMPO, 'speed': C.SPEED,
                                'length': C.NPAT, 'loop_start': 1}})
    for key, wav, vol, pan, loop in C.SAMPLES:
        ins = C.IN[key]
        batch.append({'name': 'sample_load',
                      'arguments': {'path': f'/workspace/samples/{wav}.wav',
                                    'instrument': ins, 'sample': 0}})
        args = {'instrument': ins, 'sample': 0, 'name': key,
                'volume': vol, 'panning': pan,
                'flags': 16 if loop is None else 17}
        if loop:
            args['loop_start'] = loop[0]
            args['loop_length'] = loop[1]
        batch.append({'name': 'sample_set', 'arguments': args})
    pats = C.build()
    for p in range(C.NPAT):
        for (r, ch), cell in sorted(pats[p].items()):
            args = {'pattern': p, 'row': r, 'channel': ch}
            if cell.get('inst') is not None:
                args['instrument'] = cell['inst']
            if cell.get('note') is not None:
                args['note'] = cell['note']
            if cell.get('vol') is not None:
                args['volume'] = cell['vol']
            if cell.get('fx') is not None:
                args['effect'] = cell['fx']
                args['effect_param'] = cell['param']
            batch.append({'name': 'pattern_set_cell', 'arguments': args})
    for i in range(C.NPAT):
        batch.append({'name': 'order_set', 'arguments': {'position': i, 'pattern': i}})
    batch.append({'name': 'module_save',
                  'arguments': {'path': '/workspace/submission/tune.xm', 'format': 'xm'}})
    json.dump(batch, open(BATCH, 'w'))
    print('batch entries:', len(batch))
    r = subprocess.run(['ft2', 'batch', BATCH], capture_output=True, text=True)
    out = r.stdout.strip().splitlines()
    print('batch rc', r.returncode, 'lines', len(out))
    errs = [l for l in out if 'isError' in l and 'true' in l]
    print('errors:', len(errs))
    for e in errs[:10]:
        print(e)
    if r.stderr:
        print('STDERR', r.stderr[:2000])

if __name__ == '__main__':
    main()
