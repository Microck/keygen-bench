import pickle, sys
sys.path.insert(0, '/workspace/src')
from xmwrite import Pattern, write_xm, N

I = dict(kick=1, snare=2, hat=3, ohat=4, crash=5, bass=6, lead=7, arp=8, saw=9, pluck=10, pad=11, sub=12)
KICK, SNR, HAT, BASS, ARP, LEAD, CHD, AUX = range(8)   # channels
OFF = 97
def V(v): return 0x10 + max(0, min(64, v))            # volume column

# chords: name -> (root note number at octave 4, intervals)
CH = {'Am': (N('A-3'), [0,3,7]), 'F': (N('F-3'), [0,4,7]), 'C': (N('C-4'), [0,4,7]), 'G': (N('G-3'), [0,4,7]),
      'Dm': (N('D-4'), [0,3,7]), 'E': (N('E-3'), [0,4,7]), 'Em': (N('E-3'), [0,3,7])}
PROG_A = ['Am', 'F', 'C', 'G']
PROG_B = ['Dm', 'F', 'E', 'E']

# ---------------- building blocks ----------------
def drums(p, kick=True, snare=True, hats=True, fill_end=False, bars=range(4), kick_extra=True, hat_vol=44, hat16=False):
    for b in bars:
        r0 = b * 16
        if kick:
            for r in (0, 4, 8, 12):
                p.put(r0 + r, KICK, 'C-4', I['kick'], V(64))
            if kick_extra and b % 2 == 1:
                p.put(r0 + 14, KICK, 'C-4', I['kick'], V(44))
        if snare:
            for r in (4, 12):
                p.put(r0 + r, SNR, 'C-4', I['snare'], V(60))
        if hats:
            for r in range(0, 16, 2):
                if r % 4 == 2:
                    p.put(r0 + r, HAT, 'C-4', I['ohat'], V(hat_vol - 4))
                else:
                    p.put(r0 + r, HAT, 'C-4', I['hat'], V(hat_vol if r % 8 == 0 else hat_vol - 12))
            if hat16 and b == 3:
                for r in (9, 11, 13):
                    p.put(r0 + r, HAT, 'C-4', I['hat'], V(hat_vol - 18))
    if fill_end:
        # snare fill rows 56..63 rising, last row kick+snare
        vols = [30, 34, 38, 42, 46, 50, 56, 62]
        for i, r in enumerate(range(56, 64)):
            p.put(r, SNR, 'C-4', I['snare'], V(vols[i]))
        p.put(60, KICK, 'C-4', I['kick'], V(64))
        p.put(62, KICK, 'C-4', I['kick'], V(60))
        for r in range(56, 64, 2):
            p.put(r, HAT, 'C-4', I['ohat'], V(36))

def bassline(p, prog, style=0, vol=60):
    for b, name in enumerate(prog):
        root, _ = CH[name]
        r0 = b * 16
        if style == 0:
            # bouncing octaves
            seq = [(0, 0), (2, 0), (4, 12), (6, 0), (8, 0), (10, 12), (12, 0), (14, 12)]
            for r, iv in seq:
                p.put(r0 + r, BASS, root - 12 + iv, I['bass'], V(vol if iv == 0 else vol - 10))
                p.put(r0 + r + 1, BASS, OFF)
            # tiny pickup to next root on row 15
            p.put(r0 + 15, BASS, root - 12 + 7, I['bass'], V(vol - 16))
        elif style == 1:
            # driving 8ths root, with fifth
            seq = [(0, 0), (2, 0), (4, 0), (6, 7), (8, 0), (10, 0), (12, 12), (14, 7)]
            for r, iv in seq:
                p.put(r0 + r, BASS, root - 12 + iv, I['bass'], V(vol if iv == 0 else vol - 8))
                p.put(r0 + r + 1, BASS, OFF)
        elif style == 2:
            # sustained sub
            p.put(r0, BASS, root - 12, I['sub'], V(vol))
            p.put(r0 + 15, BASS, OFF)

def arp(p, prog, octave_shift=0, vol=36, pan=None, pattern=None, ch=ARP, inst='arp'):
    # 16-step up/down arpeggio over 2 octaves of chord tones
    steps = pattern or [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5]
    for b, name in enumerate(prog):
        root, iv = CH[name]
        tones = [root + 12 + octave_shift + x for x in iv] + [root + 24 + octave_shift + x for x in iv]
        for r in range(16):
            n = tones[steps[r] % len(tones)]
            v = vol if r % 4 == 0 else vol - 8
            cell = dict(note=n, inst=I[inst], vol=V(v))
            if pan is not None and b == 0 and r == 0:
                cell.update(fx=0x8, par=pan)
            p.put(b * 16 + r, ch, **cell)

def stabs(p, prog, vol=40, rows=(2, 6, 10, 14), length=2, inst='saw', ch=CHD, arp_fx=True):
    for b, name in enumerate(prog):
        root, iv = CH[name]
        for r in rows:
            cell = dict(note=root + 12, inst=I[inst], vol=V(vol))
            if arp_fx:
                cell.update(fx=0x0, par=(iv[1] << 4) | iv[2])
            p.put(b * 16 + r, ch, **cell)
            if arp_fx:
                for k in range(1, length):
                    p.put(b * 16 + r + k, ch, fx=0x0, par=(iv[1] << 4) | iv[2])
            p.put(b * 16 + r + length, ch, OFF)

def sustained_chords(p, prog, inst='pad', ch=CHD, vol=40, voice=0, pan=None):
    # one voice of chord per channel (voice index selects chord tone)
    for b, name in enumerate(prog):
        root, iv = CH[name]
        n = root + 12 + iv[voice % 3] + 12 * (voice // 3)
        cell = dict(note=n, inst=I[inst], vol=V(vol))
        if pan is not None and b == 0:
            cell.update(fx=0x8, par=pan)
        p.put(b * 16, ch, **cell)

def melody(p, events, ch=LEAD, inst='lead', vol=48, vib=0x63, echo=None, echo_vol=20, echo_delay=3,
           echo_pan=0xB0, echo_inst=None):
    """events: list of (row, note, length). Adds note offs, vibrato on long notes, optional echo channel."""
    ends = []
    for k, (r, n, ln) in enumerate(events):
        p.put(r, ch, n, I[inst], V(vol))
        if ln >= 4:
            for rr in range(r + 2, r + ln):
                p.put(rr, ch, fx=0x4, par=vib)
        nxt = events[k + 1][0] if k + 1 < len(events) else 999
        if r + ln < nxt:
            p.put(r + ln, ch, OFF)
        if echo is not None:
            ei = I[echo_inst or inst]
            er = r + echo_delay
            if er < p.rows:
                cell = dict(note=n, inst=ei, vol=V(echo_vol))
                if k == 0: cell.update(fx=0x8, par=echo_pan)
                p.put(er, echo, **cell)
                if r + ln + echo_delay < nxt + echo_delay and r + ln + echo_delay < p.rows:
                    p.put(r + ln + echo_delay, echo, OFF)

def n_(s): return N(s)

# ---------------- melodies ----------------
LEAD1 = [(0,'A-5',2),(2,'C-6',2),(4,'E-6',4),(8,'D-6',2),(10,'C-6',2),(12,'B-5',4),
         (16,'A-5',6),(22,'C-6',2),(24,'F-6',4),(28,'E-6',2),(30,'C-6',2),
         (32,'G-5',2),(34,'C-6',2),(36,'E-6',6),(42,'D-6',2),(44,'C-6',4),
         (48,'B-5',4),(52,'D-6',2),(54,'G-6',6),(60,'E-6',2),(62,'D-6',2)]
LEAD2 = [(0,'E-6',4),(4,'C-6',2),(6,'A-5',2),(8,'B-5',4),(12,'C-6',2),(14,'D-6',2),
         (16,'C-6',4),(20,'A-5',2),(22,'F-5',2),(24,'A-5',4),(28,'C-6',2),(30,'D-6',2),
         (32,'E-6',6),(38,'G-6',2),(40,'E-6',4),(44,'D-6',2),(46,'C-6',2),
         (48,'D-6',4),(52,'B-5',2),(54,'G-5',2),(56,'A-5',4),(60,'B-5',4)]
LEAD3 = [(0,'D-6',4),(4,'F-6',2),(6,'E-6',2),(8,'D-6',4),(12,'A-5',4),
         (16,'C-6',4),(20,'A-5',2),(22,'C-6',2),(24,'F-6',8),
         (32,'G#5',4),(36,'B-5',2),(38,'E-6',6),(44,'D-6',2),(46,'B-5',2),
         (48,'G#5',8),(56,'B-5',2),(58,'C-6',2),(60,'D-6',2),(62,'E-6',2)]
LEAD4 = [(0,'F-6',4),(4,'E-6',2),(6,'D-6',2),(8,'A-6',4),(12,'F-6',2),(14,'E-6',2),
         (16,'F-6',4),(20,'A-6',2),(22,'G-6',2),(24,'F-6',2),(26,'E-6',2),(28,'C-6',4),
         (32,'B-5',4),(36,'E-6',6),(42,'D-6',2),(44,'C-6',2),(46,'B-5',2),
         (48,'G#5',4),(52,'B-5',4),(56,'E-6',8)]
# breakdown pluck melody (A prog), sparse & lyrical
PLUCK1 = [(0,'E-5',4),(4,'A-5',4),(8,'C-6',6),(14,'B-5',2),
          (16,'A-5',8),(24,'F-5',4),(28,'A-5',4),
          (32,'G-5',4),(36,'C-6',4),(40,'E-6',8),
          (48,'D-6',4),(52,'B-5',4),(56,'G-5',4),(60,'B-5',4)]
# counter line for P7 (pluck, answers the lead)
COUNTER = [(1,'A-4',1),(3,'C-5',1),(5,'E-5',1),(7,'A-5',1),(9,'E-5',1),(11,'C-5',1),(13,'A-4',1),(15,'E-4',1),
           (17,'F-4',1),(19,'A-4',1),(21,'C-5',1),(23,'F-5',1),(25,'C-5',1),(27,'A-4',1),(29,'F-4',1),(31,'C-4',1),
           (33,'C-4',1),(35,'E-4',1),(37,'G-4',1),(39,'C-5',1),(41,'G-4',1),(43,'E-4',1),(45,'C-4',1),(47,'G-4',1),
           (49,'G-4',1),(51,'B-4',1),(53,'D-5',1),(55,'G-5',1),(57,'D-5',1),(59,'B-4',1),(61,'G-4',1),(63,'D-5',1)]

def build():
    pats = [Pattern(64, 8) for _ in range(8)]
    # ---- P0 intro ----
    p = pats[0]
    p.put(0, AUX, 'C-4', I['crash'], V(48))
    arp(p, PROG_A, vol=22, pan=0x60)
    # arp swell: raise volumes per bar via volume overwrite
    for b in range(4):
        for r in range(16):
            v = 22 + b * 5
            p.put(b * 16 + r, ARP, vol=V(v if r % 4 == 0 else v - 8))
    sustained_chords(p, PROG_A, inst='pad', ch=CHD, vol=34, voice=0)
    sustained_chords(p, PROG_A, inst='pad', ch=LEAD, vol=30, voice=2, pan=0x40)
    sustained_chords(p, PROG_A, inst='pad', ch=SNR, vol=30, voice=4, pan=0xC0)   # snare channel idle in intro
    drums(p, kick=False, snare=False, hats=True, bars=range(1, 4), hat_vol=34)
    drums(p, kick=True, snare=False, hats=False, bars=range(2, 4), kick_extra=False)
    bassline(p, PROG_A, style=2, vol=44)
    # build roll in last bar (aux channel, snare inst)
    vols = [20, 22, 26, 30, 34, 38, 42, 46, 50, 52, 54, 56, 58, 60, 62, 64]
    for i, r in enumerate(range(48, 64)):
        p.put(r, AUX, 'C-4', I['snare'], V(vols[i]), **(dict(fx=0x8, par=0x80) if i == 0 else {}))
    p.put(60, SNR, OFF); p.put(60, LEAD, OFF); p.put(60, CHD, OFF)

    # ---- P1 groove A ----
    p = pats[1]
    p.put(0, HAT, 'C-4', I['crash'], V(50))
    p.put(0, LEAD, OFF); p.put(0, AUX, OFF)   # kill tails from the previous pattern (loop point)
    drums(p, fill_end=False)
    bassline(p, PROG_A, style=0)
    arp(p, PROG_A, vol=36, pan=0x60)
    stabs(p, PROG_A, vol=50)

    # ---- P2 A + lead 1 ----
    p = pats[2]
    drums(p, hat16=True)
    bassline(p, PROG_A, style=0)
    arp(p, PROG_A, vol=32, pan=0x60)
    stabs(p, PROG_A, vol=46)
    melody(p, LEAD1, echo=AUX, echo_vol=18)

    # ---- P3 A + lead 2 ----
    p = pats[3]
    drums(p, fill_end=True)
    bassline(p, PROG_A, style=0)
    arp(p, PROG_A, vol=32, pan=0x60)
    stabs(p, PROG_A, vol=46)
    melody(p, LEAD2, echo=AUX, echo_vol=18)

    # ---- P4 B + lead 3 ----
    p = pats[4]
    p.put(0, HAT, 'C-4', I['crash'], V(44))
    drums(p, hat16=True)
    bassline(p, PROG_B, style=1)
    arp(p, PROG_B, vol=34, pan=0x60)
    stabs(p, PROG_B, vol=48, rows=(0, 3, 6, 9, 12), length=2)
    melody(p, LEAD3, echo=AUX, echo_vol=18)

    # ---- P5 B + lead 4 (climax) ----
    p = pats[5]
    drums(p, fill_end=True)
    bassline(p, PROG_B, style=1)
    arp(p, PROG_B, octave_shift=12, vol=34, pan=0x60,
        pattern=[0, 2, 1, 3, 2, 4, 3, 5, 4, 3, 5, 2, 4, 1, 3, 0])
    stabs(p, PROG_B, vol=48, rows=(0, 3, 6, 9, 12), length=2)
    melody(p, LEAD4, echo=AUX, echo_vol=18)
    # long final note: fade a bit with vibrato deeper
    for r in range(58, 64):
        p.put(r, LEAD, fx=0x4, par=0x85)

    # ---- P6 breakdown ----
    p = pats[6]
    p.put(0, HAT, 'C-4', I['crash'], V(40))
    sustained_chords(p, PROG_A, inst='pad', ch=CHD, vol=40, voice=0)
    sustained_chords(p, PROG_A, inst='pad', ch=LEAD, vol=34, voice=2, pan=0x40)
    sustained_chords(p, PROG_A, inst='pad', ch=SNR, vol=34, voice=4, pan=0xC0)
    bassline(p, PROG_A, style=2, vol=48)
    arp(p, PROG_A, vol=20, pan=0x60)
    drums(p, kick=False, snare=False, hats=True, hat_vol=30)
    melody(p, PLUCK1, ch=AUX, inst='pluck', vol=52, vib=0x42)
    for r, n, ln in PLUCK1[:1]:
        p.put(r, AUX, fx=0x8, par=0x90)
    # roll into P7 on kick channel + rising snare on AUX end
    vols = [24, 30, 36, 42, 48, 54, 60, 64]
    for i, r in enumerate(range(56, 64)):
        p.put(r, KICK, 'C-4', I['snare'], V(vols[i]))
    for r in (48, 52, 56, 60): p.put(r, HAT, 'C-4', I['kick'], V(50))
    p.put(60, SNR, OFF); p.put(60, LEAD, OFF); p.put(60, CHD, OFF)

    # ---- P7 A groove + lead 1 + pluck counter ----
    p = pats[7]
    p.put(0, HAT, 'C-4', I['crash'], V(50))
    drums(p, fill_end=True)
    bassline(p, PROG_A, style=0)
    arp(p, PROG_A, vol=30, pan=0x60)
    stabs(p, PROG_A, vol=44)
    melody(p, LEAD1, vol=48)
    melody(p, COUNTER, ch=AUX, inst='pluck', vol=40, vib=0)
    p.put(1, AUX, fx=0x8, par=0xA0)

    order = [0, 1, 2, 3, 4, 5, 6, 7, 2, 3]
    return pats, order

GAIN = dict(kick=0.75, snare=0.65, hat=0.9, ohat=0.9, crash=0.55, bass=0.55, lead=0.78, arp=0.5,
            saw=0.9, pluck=0.8, pad=0.9, sub=0.8)

def get_instruments():
    import numpy as np
    inst = pickle.load(open('/workspace/samples/inst.pkl', 'rb'))
    out = []
    for i in sorted(inst):
        d = inst[i]
        pcm = np.clip(d['pcm16'].astype(np.float64) * GAIN[d['name']], -32768, 32767).astype(np.int16)
        out.append(dict(name=d['name'], pcm16=pcm, loop=d['loop'], vol=d['vol'], pan=d['pan'],
                        relnote=d['relnote'], finetune=d['finetune']))
    return out

if __name__ == '__main__':
    pats, order = build()
    out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/submission/tune.xm'
    n = write_xm(out, 'keyflow', 8, pats, order, get_instruments(), speed=6, bpm=140, restart=1)
    print('wrote', out, n, 'bytes')
