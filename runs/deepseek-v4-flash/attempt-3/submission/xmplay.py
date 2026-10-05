"""Minimal standard-XM renderer (NumPy) used as a reference preview."""
import numpy as np
import sys
sys.path.insert(0, '/workspace')
from xmwrite import parse_xm

PERIOD_C4 = 428.0

def render_xm(xm_bytes, rate=44100, normalize=True, mask=None, stereo=False):
    m = parse_xm(xm_bytes)
    channels = m['channels']
    speed = m['speed'] or 6
    bpm = m['bpm'] or 125
    order = m['order']
    tick_len = int(round(rate * 2.5 / bpm))
    played = [order[i % len(order)] for i in range(len(order))]
    total_ticks = sum(m['patterns'][p][0] * speed for p in played)
    if stereo:
        out = np.zeros((int(total_ticks * tick_len) + tick_len * 2, 2), dtype=np.float64)
    else:
        out = np.zeros(int(total_ticks * tick_len) + tick_len * 2, dtype=np.float64)

    def new_state():
        return {'pos': 0.0, 'note': 0, 'inst': 0, 'vol': 0, 'period': 0.0,
                'vib_phase': 0.0, 'vib_speed': 0, 'vib_depth': 0, 'volslide': 0,
                'active': False, 'sample': None, 'pan': 128,
                'porta_target': None, 'porta_speed': 0, 'arp': None,
                'note_on_tick': 0, 'inst_vol': 64}
    st = [new_state() for _ in range(channels)]

    evs = {}
    for pidx, (rows, cells) in enumerate(m['patterns']):
        evs[pidx] = {}
        for (r, c, note, inst, vol, fx, fxp) in cells:
            evs[pidx].setdefault((r, c), []).append((note, inst, vol, fx, fxp))

    def chan_buf(st, n, rate):
        buf = np.zeros(n)
        if not st['active'] or st['sample'] is None:
            return buf
        sd = st['sample']['data']
        L = sd.shape[0]
        ls = st['sample']['loop_start']
        ll = st['sample']['loop_len']
        freq = 8363.0 * (PERIOD_C4 / max(st['period'], 1e-6))
        step = freq / rate
        pos = st['pos']
        positions = pos + np.arange(n, dtype=np.float64) * step
        idx = np.floor(positions).astype(np.int64)
        frac = positions - idx
        if ll > 0:
            i0 = idx % ll + ls
            i1 = (idx + 1) % ll + ls
            buf = sd[i0] * (1 - frac) + sd[i1] * frac
        else:
            i0 = np.clip(idx, 0, L - 1)
            i1 = np.clip(idx + 1, 0, L - 1)
            buf = sd[i0] * (1 - frac) + sd[i1] * frac
            buf[positions >= L - 1] = 0.0
        st['pos'] = positions[-1] + step
        return buf

    def apply_tick(pat, row, tick, cur_speed):
        for ch in range(channels):
            s = st[ch]
            for (note, inst, vol, fx, fxp) in evs[pat].get((row, ch), []):
                if note == 97:
                    s['active'] = False
                    s['arp'] = None
                    continue
                if note:
                    s['note'] = note
                    s['target_note'] = note
                    s['active'] = True
                    s['pos'] = 0.0
                    if inst:
                        s['inst'] = inst
                        idata = m['instruments'][inst - 1]
                        s['sample'] = idata['samples'][0]
                        s['pan'] = s['sample']['pan']
                        s['inst_vol'] = s['sample']['vol']
                    if s['sample'] is not None:
                        rel = s['sample'].get('rel', 0)
                        s['period'] = PERIOD_C4 / (2 ** ((note + rel - 49) / 12.0))
                        s['vib_phase'] = 0.0
                    if fx != 3:
                        s['porta_target'] = None
                    if not vol:
                        s['vol'] = 64
                    s['note_on_tick'] = tick
                if inst and not note:
                    s['inst'] = inst
                    s['sample'] = m['instruments'][inst - 1]['samples'][0]
                    s['pan'] = s['sample']['pan']
                    s['inst_vol'] = s['sample']['vol']
                if vol:
                    if 0x10 <= vol <= 0x50:
                        s['vol'] = vol - 0x10
                    elif 0x60 <= vol <= 0x6F:
                        s['vol'] = max(0, s['vol'] - (vol & 0xF))
                    elif 0x70 <= vol <= 0x7F:
                        s['vol'] = min(64, s['vol'] + (vol & 0xF))
                if fx == 0:
                    s['arp'] = (fxp >> 4, fxp & 0xF)
                elif fx == 3:
                    if note:
                        s['porta_target'] = note + (s['sample'].get('rel', 0) if s['sample'] else 0)
                    s['porta_speed'] = fxp
                elif fx == 4:
                    s['vib_speed'] = fxp >> 4
                    s['vib_depth'] = fxp & 0xF
                elif fx == 0xA:
                    s['volslide'] = fxp
                elif fx == 0xC:
                    s['vol'] = fxp
        for ch in range(channels):
            s = st[ch]
            if not s['active'] or s['sample'] is None:
                continue
            period = s['period']
            if tick > 0 and s['arp']:
                offs = s['arp']
                n = offs[0] if tick % 3 == 1 else (offs[1] if tick % 3 == 2 else 0)
                if n:
                    period = PERIOD_C4 / (2 ** ((s['note'] + n - 49) / 12.0))
            if s['porta_target'] is not None and s['porta_speed']:
                tgt = PERIOD_C4 / (2 ** ((s['porta_target'] - 49) / 12.0))
                r = s['porta_speed'] / 16.0
                if period > tgt:
                    period = max(tgt, period - r)
                else:
                    period = min(tgt, period + r)
            if s['vib_speed']:
                s['vib_phase'] += s['vib_speed'] / 16.0
                depth = s['vib_depth'] / 128.0
                period *= 1.0 + depth * np.sin(2 * np.pi * s['vib_phase'])
            if s['volslide']:
                x = s['volslide'] >> 4
                y = s['volslide'] & 0xF
                if y:
                    s['vol'] = min(64, s['vol'] + y)
                elif x:
                    s['vol'] = max(0, s['vol'] - x)
            s['period'] = max(1.0, period)

    pos = 0
    cur_speed = speed
    for pidx in played:
        rows = m['patterns'][pidx][0]
        for row in range(rows):
            for tick in range(cur_speed):
                apply_tick(pidx, row, tick, cur_speed)
                n = tick_len
                if stereo:
                    mixL = np.zeros(n)
                    mixR = np.zeros(n)
                else:
                    mix = np.zeros(n)
                for ch in range(channels):
                    if mask is not None and ch not in mask:
                        continue
                    s = st[ch]
                    buf = chan_buf(s, n, rate)
                    v = (s['vol'] / 64.0) * (s['inst_vol'] / 64.0)
                    pan = s['pan'] / 255.0
                    fl = np.sqrt(1.0 - pan)
                    fr = np.sqrt(pan)
                    if stereo:
                        mixL += buf * v * fl
                        mixR += buf * v * fr
                    else:
                        mix += buf * v * (fl + fr)
                if stereo:
                    out[pos:pos + n, 0] += mixL
                    out[pos:pos + n, 1] += mixR
                else:
                    out[pos:pos + n] += mix
                pos += n
    out = out[:pos]
    if normalize and np.abs(out).max() > 0:
        out = out / np.abs(out).max() * 0.85
    return out, rate
