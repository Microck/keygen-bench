import sys; sys.path.insert(0,'/workspace/src')
from xmcheck import read_xm
NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nn(n):
    if n == 0: return '...'
    if n == 97: return '==='
    n -= 1
    return f"{NAMES[n%12]}{n//12}"
ch_names = ['LEAD','LEAD2','ARP','BASS','KICK','SNR','HAT','PAD1','PAD2','PAD3','FX','OPEN']
def dump(path, pat, rows=range(0,64), chans=range(12)):
    m = read_xm(path)
    P = m['patterns'][pat]
    print('PATTERN', pat, 'rows', P['rows'])
    for r in rows:
        cells = []
        for c in chans:
            n, ins, vol, fx, fp = P['grid'][r][c]
            s = f"{nn(n):3s}" + (f"{ins:02d}" if ins else "  ")
            if vol: s += f" v{vol:02x}"
            else: s += "    "
            if fx: s += f" {fx:X}{fp:02X}"
            else: s += "    "
            cells.append(s)
        print(f"{r:02d} | " + " | ".join(cells[i] for i in range(len(chans))))
if __name__ == '__main__':
    path = sys.argv[1]; pat = int(sys.argv[2])
    r0, r1 = int(sys.argv[3]), int(sys.argv[4])
    chans = [int(x) for x in sys.argv[5].split(',')] if len(sys.argv) > 5 else list(range(12))
    dump(path, pat, range(r0, r1), chans)
