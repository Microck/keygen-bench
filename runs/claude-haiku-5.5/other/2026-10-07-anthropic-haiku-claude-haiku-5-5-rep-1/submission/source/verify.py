"""Independent verification of tune.xm against the source score and synthesized samples.
Usage: python3 verify.py path/to/tune.xm
Checks: XM header (restart, speed, BPM, channels), every instrument's sample PCM (bit-exact),
loop flags and tuning fields, every pattern cell (note, instrument, volume column, effect),
and the order list (= the arrangement)."""
import json, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth, compose

def read_xm(path):
    d = open(path, 'rb').read()
    assert d[:17] == b'Extended Module: '
    version, hdr_size = struct.unpack_from('<HI', d, 58)
    song_len, restart, nch, npat, nins, flags, speed, bpm = struct.unpack_from('<HHHHHHHH', d, 64)
    order = list(d[80:80 + song_len])
    off = 60 + hdr_size
    patterns = []
    for _ in range(npat):
        plen, _, rows, psize = struct.unpack_from('<IBHH', d, off)
        off += plen
        data = d[off:off + psize]; off += psize
        grid = [[None] * nch for _ in range(rows)]
        i = 0
        for r in range(rows):
            for c in range(nch):
                b = data[i]
                if b & 0x80:
                    i += 1; vals = [0] * 5
                    for k in range(5):
                        if b & (1 << k):
                            vals[k] = data[i]; i += 1
                else:
                    vals = list(data[i:i + 5]); i += 5
                grid[r][c] = tuple(vals)
        assert i == len(data)
        patterns.append(dict(rows=rows, grid=grid))
    instruments = []
    for _ in range(nins):
        ihs = struct.unpack_from('<I', d, off)[0]
        nsmp = struct.unpack_from('<H', d, off + 27)[0]
        ins = dict(samples=[], keymap=set(d[off + 33:off + 33 + 96]) if nsmp else set())
        if nsmp:
            shs = struct.unpack_from('<I', d, off + 29)[0]
            sh_base = off + ihs
            shdrs = []
            for s in range(nsmp):
                so = sh_base + s * shs
                length, lstart, llen = struct.unpack_from('<III', d, so)
                vol, ftune, stype, pan, relnote = struct.unpack_from('<BbBBb', d, so + 12)
                shdrs.append(dict(length=length, loop_start=lstart, loop_len=llen, volume=vol,
                                  finetune=ftune, type=stype, pan=pan, relnote=relnote))
            dstart = sh_base + nsmp * shs
            for sh in shdrs:
                raw = d[dstart:dstart + sh['length']]; dstart += sh['length']
                if sh['type'] & 16:
                    deltas = np.frombuffer(raw, dtype='<i2').astype(np.int64)
                    x = np.cumsum(deltas) % 65536
                    x = np.where(x >= 32768, x - 65536, x).astype(np.int32)
                else:
                    raise ValueError("8-bit sample found; expected 16-bit")
                sh['data'] = x
                ins['samples'].append(sh)
            off = dstart
        else:
            off += ihs
        instruments.append(ins)
    return dict(restart=restart, nch=nch, npat=npat, speed=speed, bpm=bpm, order=order,
                patterns=patterns, instruments=instruments, song_len=song_len)

def main(path):
    m = read_xm(path)
    report = []
    def check(name, ok, detail=""):
        report.append(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
        return ok
    ok = True
    ok &= check("song length / restart", m['song_len'] == compose.NBARS and m['restart'] == compose.RESTART_BAR - 1,
                f"(length={m['song_len']} orders, restart=order {m['restart']} = bar {m['restart'] + 1})")
    ok &= check("tempo / speed", m['bpm'] == compose.BPM and m['speed'] == compose.SPEED,
                f"(bpm={m['bpm']}, speed={m['speed']})")
    ok &= check("channels", m['nch'] == compose.NCH, f"({m['nch']})")
    bad = []
    for idx, name, builder, rel, vol, pan, loop in synth.INSTRUMENTS:
        ins = m['instruments'][idx - 1]
        s = ins['samples'][0]
        want = synth.to_int16(builder()).astype(np.int32)
        good = (len(want) == len(s['data']) and np.array_equal(want, s['data'])
                and ins['keymap'] == {0} and s['volume'] == vol and s['pan'] == pan
                and s['relnote'] == rel and s['finetune'] == 0
                and (s['type'] & 3) == (1 if loop else 0)
                and s['loop_len'] // 2 == (len(want) if loop else 0))
        if not good: bad.append(name)
    ok &= check("instruments (PCM bit-exact, loops, tuning, volume, pan)", not bad,
                f"({len(m['instruments']) - len(bad)}/{len(m['instruments'])} ok{'; bad: ' + ', '.join(bad) if bad else ''})")
    ev = compose.add_release_effects(compose.build_events())
    pats, key_to, bar_pat = [], {}, {}
    for b in range(1, compose.NBARS + 1):
        cells = compose.pattern_cells(ev, b)
        key = json.dumps(cells, sort_keys=True)
        if key not in key_to:
            key_to[key] = len(pats); pats.append(cells)
        bar_pat[b] = key_to[key]
    mism = 0; checked = 0
    for p, cells in enumerate(pats):
        grid = m['patterns'][p]['grid']
        expect = {(c['row'], c['channel']): (c.get('note', 0), c.get('inst', 0), c.get('vol', 0),
                                             c.get('fx', 0), c.get('fxp', 0)) for c in cells}
        for r in range(32):
            for chn in range(m['nch']):
                got = grid[r][chn]; want = expect.get((r, chn), (0,) * 5); checked += 1
                if got[:4] != want[:4] or (got[4] if want[3] else 0) != (want[4] if want[3] else 0):
                    mism += 1
    ok &= check("pattern cells (note, instrument, volume column, effect)", mism == 0,
                f"({checked} cells, {mism} mismatches, {len(pats)} patterns)")
    ok &= check("order list = arrangement", m['order'] == [bar_pat[b] for b in range(1, compose.NBARS + 1)])
    print("\n".join(report))
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'tune.xm')))
