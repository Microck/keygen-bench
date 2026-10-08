"""Verify a saved XM against its generating sources: header/order/restart, and that every
sample decodes (XM stores delta-coded samples) to exactly the WAV it was generated from."""
import struct, wave, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xmcheck

SAMPLE_DIR = sys.argv[2] if len(sys.argv) > 2 else '/workspace/build/samples'
WAVS = {1: 'i01_lead_saw', 2: 'i02_harm_pulse', 3: 'i03_pluck', 4: 'i04_pad', 5: 'i05_bass', 6: 'i06_kick',
        7: 'i07_snare', 8: 'i08_hat_closed', 9: 'i09_hat_open', 10: 'i10_riser', 11: 'i11_crash', 12: 'i12_bass16'}

def main(path):
    h, pats, ins = xmcheck.parse(path)
    assert h['song_len'] == 7 and h['restart'] == 1, h
    assert h['orders'] == [0, 1, 2, 3, 1, 4, 5], h['orders']
    assert h['channels'] == 12 and h['patterns'] == 6 and h['instruments'] == 12
    assert all(p['rows'] == 64 for p in pats)
    b = open(path, 'rb').read()
    off = 60 + struct.unpack_from('<I', b, 60)[0]
    for _ in range(h['patterns']):
        plen = struct.unpack_from('<I', b, off)[0]; psize = struct.unpack_from('<H', b, off + 7)[0]
        off += plen + psize
    ok = True
    for k in range(h['instruments']):
        isz = struct.unpack_from('<I', b, off)[0]
        nsm = struct.unpack_from('<H', b, off + 27)[0]
        shs = struct.unpack_from('<I', b, off + 29)[0] if nsm else 0
        sh = off + isz
        data_off = sh + nsm * shs
        for s in range(nsm):
            base = sh + s * shs
            length = struct.unpack_from('<I', b, base)[0]
            typ = b[base + 14]
            if typ & 16:
                raw = np.frombuffer(b, dtype='<i2', count=length // 2, offset=data_off).astype(np.int64)
                dec = np.cumsum(raw) % 65536
                dec = np.where(dec >= 32768, dec - 65536, dec)
            else:
                raw = np.frombuffer(b, dtype='<i1', count=length, offset=data_off).astype(np.int64)
                dec = np.cumsum(raw) % 256
                dec = np.where(dec >= 128, dec - 256, dec)
            ref = np.frombuffer(wave.open(os.path.join(SAMPLE_DIR, WAVS[k + 1] + '.wav')).readframes(10**7), dtype='<i2').astype(np.int64)
            same = len(ref) == len(dec) and np.array_equal(ref, dec)
            ok &= same
            print('instrument %2d %-18s samples %6d  loop %-5s  matches source: %s' % (
                k + 1, ins[k]['name'], len(dec), 'yes' if typ & 3 else 'no', same))
            data_off += length
        off = data_off
    print('ALL OK' if ok else 'MISMATCH')
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
