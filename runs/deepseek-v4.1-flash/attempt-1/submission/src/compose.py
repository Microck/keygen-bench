"""Build the keygen tune as a real XM module."""
import sys, os
import numpy as np, wave
sys.path.insert(0, '/workspace/work')
from xmlib import Sample, Instrument, n, write_xm

SR = 22050
SAMP = '/workspace/samples'
NCH = 10

# channel indices
CH_LEAD, CH_LEAD2, CH_ARP, CH_BASS, CH_KICK, CH_SNARE, CH_HAT, CH_PAD, CH_PAD2, CH_FX = range(10)

def load_wav(name):
    p = os.path.join(SAMP, name)
    with wave.open(p, 'rb') as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        d = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
    return d/32767.0

SAMPLE_VOL = 56      # uniform (some renderers ignore this; balance lives in the volume column)
MIX = 0.52           # global scale applied to every note-volume value
# instrument table: (name, wav, volume, pan, relnote, finetune)
REL, FINE = 16, 104   # 22050 Hz sample convention (standard XM: 8363*2^(16/12)*2^(104/1536)=22084)
INSTS = [
    ('lead',  'lead.wav',  50, 170),
    ('lead2', 'lead2.wav', 40,  86),
    ('arp',   'arp.wav',   38,  50),
    ('bass',  'bass.wav',  56, 128),
    ('kick',  'kick.wav',  64, 128),
    ('snare', 'snare.wav', 52, 146),
    ('clap',  'clap.wav',  46, 110),
    ('hat',   'hat.wav',   34, 196),
    ('ohat',  'ohat.wav',  30,  60),
    ('pad',   'pad.wav',   40,  70),
    ('pad2',  'pad2.wav',  40, 186),   # duplicate of the pad sample, hard-panned
    ('crash', 'crash.wav', 40, 128),
    ('zap',   'zap.wav',   42, 128),
    ('tom',   'tom.wav',   50, 128),
]
# actual instrument numbers (1-based)
I = {}
for idx, (nm, wav, vol, pan) in enumerate(INSTS, start=1):
    I[nm] = idx

def make_instruments():
    out = []
    for nm, wav, vol, pan in INSTS:
        if wav == 'pad2.wav':
            data = load_wav('pad.wav')
        else:
            data = load_wav(wav)
        s = Sample(nm, data, volume=SAMPLE_VOL, pan=pan, relnote=REL, finetune=FINE, bits=16)
        out.append(Instrument(nm, [s]))
    return out

# ---------------------------------------------------------------- helpers
def new_pat():
    return [[None]*NCH for _ in range(64)]

def put(pat, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
    row = max(0, min(63, row))
    cell = pat[row][ch] or {}
    if note is not None: cell['note'] = note
    if inst is not None: cell['inst'] = inst
    if vol is not None: cell['vol'] = vol
    if fx is not None: cell['fx'] = fx
    if param is not None: cell['param'] = param
    pat[row][ch] = cell

def V(v):   # XM volume column: 0x10..0x50
    return 0x10 + max(0, min(64, int(round(v*MIX))))

def rm(pat, row, ch):
    row = max(0, min(63, row))
    pat[row][ch] = None

def drum(pat, row, ch, inst, vol, fx=None, param=None):
    put(pat, row, ch, note=n('C-4'), inst=inst, vol=V(vol), fx=fx, param=param)

# ---------------------------------------------------------------- chords
CHORDS = {
    'Am': dict(root='A-1', arp=['A-3','C-4','E-4','A-4'], padlo='A-2', padhi=['C-4','E-4']),
    'F' : dict(root='F-1', arp=['F-3','A-3','C-4','F-4'], padlo='F-2', padhi=['A-3','C-4']),
    'C' : dict(root='C-2', arp=['G-3','C-4','E-4','G-4'], padlo='C-3', padhi=['E-4','G-4']),
    'G' : dict(root='G-1', arp=['G-3','B-3','D-4','G-4'], padlo='G-2', padhi=['B-3','D-4']),
    'Dm': dict(root='D-2', arp=['A-3','D-4','F-4','A-4'], padlo='D-3', padhi=['F-4','A-4']),
    'E' : dict(root='E-2', arp=['E-3','G#3','B-3','E-4'], padlo='E-2', padhi=['G#3','B-3']),
}
# chord tone above the root, in the octave above (for bass fills)
FIFTH = {'Am':'E-2','F':'C-2','C':'G-2','G':'D-2','Dm':'A-2','E':'B-2'}

# ---------------------------------------------------------------- builders
def add_pad(pat, chords, vol_lo=34, vol_hi=30, inst=I['pad']):
    for b, ch_name in enumerate(chords):
        base = b*16
        c = CHORDS[ch_name]
        put(pat, base, CH_PAD,  note=n(c['padlo']), inst=inst, vol=V(vol_lo))
        for k, hn in enumerate(c['padhi']):
            chn = CH_PAD2 if k == 0 else CH_ARP
            ins = I['pad2'] if k == 0 else inst
            put(pat, base, chn, note=n(hn), inst=ins, vol=V(vol_hi))

def add_bass(pat, chords, style='drive', vol=50):
    for b, ch_name in enumerate(chords):
        base = b*16
        r = n(CHORDS[ch_name]['root'])
        f = n(FIFTH[ch_name])
        if style == 'drive':
            seq = [(0, r, 62), (2, r, 56), (4, r, 60), (6, r+12, 58),
                   (8, r, 62), (10, r, 56), (12, r+12, 60), (14, f, 58)]
        elif style == 'oct':
            seq = [(0, r, 62), (3, r, 54), (4, r, 60), (6, r+12, 58),
                   (8, r, 62), (11, r, 54), (12, r, 60), (14, f, 58)]
        elif style == 'push':
            seq = [(0, r, 62), (2, r, 56), (4, r, 60), (6, r+12, 58),
                   (8, r, 62), (10, r+12, 58), (12, r, 60), (13, r, 52), (14, f, 58)]
        else:  # 'sparse'
            seq = [(0, r, 60), (4, r, 56), (8, r, 60), (12, f, 56)]
        for row, note, v in seq:
            put(pat, base+row, CH_BASS, note=note, inst=I['bass'], vol=V(v))

def add_arp(pat, chords, vol=28, mode='up', step=1):
    for b, ch_name in enumerate(chords):
        base = b*16
        tones = [n(x) for x in CHORDS[ch_name]['arp']]
        seq = tones + tones[::-1][1:-1]
        for k in range(0, 16, step):
            idx = k % len(seq)
            put(pat, base+k, CH_ARP, note=seq[idx], inst=I['arp'], vol=V(vol))

def add_drums(pat, kick_rows=(0,4,8,12), snare_rows=(4,12), clap_rows=(12,),
              hat=True, ohat_rows=(2,6,10,14), bars=(0,1,2,3),
              kick_vol=64, snare_vol=56, clap_vol=48, hat_vol=35):
    for b in bars:
        base = b*16
        for r in kick_rows:
            drum(pat, base+r, CH_KICK, I['kick'], kick_vol)
        for r in snare_rows:
            drum(pat, base+r, CH_SNARE, I['snare'], snare_vol)
        for r in clap_rows:
            drum(pat, base+r, CH_SNARE, I['clap'], clap_vol)
        if hat:
            for r in range(0, 16, 2):
                drum(pat, base+r, CH_HAT, I['hat'], hat_vol if r % 4 == 0 else int(hat_vol*0.62))
        for r in ohat_rows:
            drum(pat, base+r, CH_HAT, I['ohat'], int(hat_vol*0.55))

def add_fill(pat, start=56, kind='snare', vol=44):
    if kind == 'snare':
        for k, r in enumerate(range(start, 64, 2)):
            drum(pat, r, CH_SNARE, I['snare'], vol + k*3)
        drum(pat, 63, CH_SNARE, I['clap'], vol+8)
    elif kind == 'tom':
        drum(pat, 56, CH_FX, I['tom'], 52)
        drum(pat, 58, CH_FX, I['tom'], 50)
        drum(pat, 60, CH_FX, I['tom'], 54)
        drum(pat, 61, CH_FX, I['tom'], 52)
        drum(pat, 62, CH_FX, I['tom'], 56)

def add_lead(pat, seq, inst=None, vol=48, ch=CH_LEAD, vib=None):
    """seq: list of (row, note, vol) ; vib: list of rows that get vibrato"""
    inst = inst or I['lead']
    for row, note, v in seq:
        nv = n(note) if isinstance(note, str) else note
        put(pat, row, ch, note=nv, inst=inst, vol=V(v if v else vol))
    if vib:
        for row in vib:
            cell = pat[row][ch]
            if cell:
                cell['fx'] = 4; cell['param'] = 0x47

# ---------------------------------------------------------------- melodies
MEL_A1 = [(0,'A-4',52),(2,'C-5',46),(4,'E-5',50),(8,'A-5',50),(10,'G-5',46),(12,'E-5',50),
          (16,'F-5',52),(18,'A-5',46),(20,'C-6',50),(24,'A-5',50),(26,'G-5',46),(28,'F-5',50),
          (32,'E-5',52),(34,'G-5',46),(36,'C-6',50),(40,'B-5',48),(42,'G-5',46),(44,'E-5',50),
          (48,'D-5',52),(50,'G-5',46),(52,'B-5',50),(56,'A-5',48),(58,'G-5',46),(60,'D-5',50)]
MEL_A2 = [(0,'E-5',52),(2,'A-5',46),(4,'C-6',50),(6,'E-6',48),(8,'C-6',50),(10,'A-5',46),(12,'E-5',50),
          (16,'F-5',52),(18,'C-6',48),(20,'A-5',46),(22,'F-5',46),(24,'A-5',50),(28,'C-6',50),
          (32,'G-5',52),(34,'E-5',46),(36,'C-5',48),(38,'E-5',46),(40,'G-5',50),(44,'E-5',50),
          (48,'D-5',52),(50,'G-5',46),(52,'B-5',50),(56,'D-6',50),(58,'B-5',46),(60,'G-5',50)]
MEL_B1 = [(0,'D-5',52),(4,'F-5',48),(6,'A-5',48),(8,'D-6',52),(12,'C-6',50),
          (16,'A-5',50),(18,'C-6',46),(20,'A-5',50),(24,'F-5',48),(26,'G-5',46),(28,'A-5',50),
          (32,'G-5',52),(34,'E-5',46),(36,'C-5',50),(40,'E-5',48),(42,'G-5',46),(44,'C-6',52),
          (48,'B-5',52),(50,'G#5',48),(52,'B-5',50),(56,'E-6',54),(60,'D-6',50)]
MEL_B2 = [(0,'A-5',52),(2,'D-6',50),(4,'F-6',52),(8,'D-6',50),(10,'A-5',46),(12,'F-5',50),
          (16,'C-6',52),(18,'A-5',46),(20,'F-5',50),(24,'A-5',48),(26,'C-6',46),(28,'F-6',52),
          (32,'E-6',52),(34,'C-6',48),(36,'G-5',50),(40,'C-6',50),(42,'E-6',48),(44,'G-6',52),
          (48,'E-6',52),(52,'D-6',48),(54,'B-5',46),(56,'G#5',50),(60,'B-5',52)]
MEL_OUT = [(0,'A-5',52),(4,'G-5',48),(6,'E-5',46),(8,'C-5',50),(12,'E-5',50),
           (16,'F-5',52),(18,'A-5',46),(20,'C-6',50),(24,'A-5',50),(28,'F-5',48),
           (32,'G-5',52),(34,'B-5',48),(36,'D-6',50),(40,'B-5',48),(42,'G-5',46),(44,'D-5',50),
           (48,'E-5',52),(50,'G#5',48),(52,'B-5',50),(56,'E-6',56)]
MEL_BREAK = [(0,'A-4',46),(4,'C-5',44),(8,'E-5',48),(12,'A-5',46),
             (16,'A-4',46),(20,'C-5',44),(24,'F-5',48),(28,'A-5',46),
             (32,'A-4',46),(36,'D-5',46),(40,'F-5',48),(44,'A-5',48),
             (48,'B-4',46),(52,'E-5',48),(56,'G#5',50)]

def chord_seq(names):
    return names

# ---------------------------------------------------------------- sections
def build():
    pats = []

    # ---- P0 : intro A : pad + arp + hats
    p = new_pat()
    ch = ['Am','F','C','G']
    add_pad(p, ch, 33, 28)
    add_arp(p, ch, vol=24)
    add_drums(p, kick_rows=(), snare_rows=(), clap_rows=(), hat=True,
              ohat_rows=(), bars=(2,3), hat_vol=22)
    drum(p, 0, CH_FX, I['crash'], 42)
    drum(p, 62, CH_HAT, I['ohat'], 18)
    # pickup phrase into the first main section
    add_lead(p, [(52,'E-5',42),(54,'G-5',40),(56,'A-5',44),(60,'B-5',44),(62,'C-6',46)], vol=44)
    pats.append(p)

    # ---- P1 : intro B : + bass, kick, snare
    p = new_pat()
    add_pad(p, ch, 35, 30)
    add_arp(p, ch, vol=26)
    add_bass(p, ch, 'sparse', vol=48)
    add_drums(p, bars=(1,2), kick_vol=56, hat_vol=26, ohat_rows=(6,14))
    add_drums(p, bars=(3,), kick_rows=(0,4,8,12), snare_rows=(4,12), clap_rows=(12,),
              hat_vol=28, ohat_rows=(2,6,10,14))
    add_fill(p, 56, 'snare', 40)
    drum(p, 0, CH_FX, I['crash'], 40)
    pats.append(p)

    # ---- P2 : main A1
    p = new_pat()
    add_pad(p, ch, 36, 29)
    add_arp(p, ch, vol=35)
    add_bass(p, ch, 'drive')
    add_drums(p, kick_rows=(0,4,8,12,14), ohat_rows=(2,6,10,14))
    add_lead(p, MEL_A1, vib=[8,20,36,52,60])
    drum(p, 0, CH_FX, I['crash'], 44)
    add_fill(p, 60, 'tom')
    pats.append(p)

    # ---- P3 : main A2
    p = new_pat()
    add_pad(p, ch, 36, 29)
    add_arp(p, ch, vol=35)
    add_bass(p, ch, 'oct')
    add_drums(p, kick_rows=(0,4,8,12), ohat_rows=(2,6,10,14))
    add_lead(p, MEL_A2, vib=[4,24,36,52])
    rm(p, 60, CH_KICK); rm(p, 60, CH_HAT)
    drum(p, 61, CH_KICK, I['kick'], 60)
    drum(p, 63, CH_KICK, I['kick'], 60)
    drum(p, 44, CH_FX, I['tom'], 50)
    drum(p, 46, CH_FX, I['tom'], 52)
    add_fill(p, 56, 'snare', 42)
    pats.append(p)

    # ---- P4 : B1
    chb = ['Dm','F','C','E']
    p = new_pat()
    add_pad(p, chb, 36, 29)
    add_arp(p, chb, vol=35)
    add_bass(p, chb, 'push')
    add_drums(p, kick_rows=(0,4,8,12), ohat_rows=(2,6,10,14), snare_vol=50)
    add_lead(p, MEL_B1, vib=[8,28,44,56])
    drum(p, 0, CH_FX, I['crash'], 44)
    pats.append(p)

    # ---- P5 : B2
    p = new_pat()
    add_pad(p, chb, 36, 29)
    add_arp(p, chb, vol=27, mode='down')
    add_bass(p, chb, 'drive')
    add_drums(p, kick_rows=(0,4,8,12), ohat_rows=(2,6,10,14))
    add_lead(p, MEL_B2, vib=[4,28,44,60])
    drum(p, 32, CH_FX, I['crash'], 34)
    drum(p, 63, CH_KICK, I['kick'], 60)
    add_fill(p, 56, 'snare', 44)
    drum(p, 62, CH_FX, I['tom'], 52)
    pats.append(p)

    # ---- P6 : break
    chbr = ['Am','F','Dm','E']
    p = new_pat()
    add_pad(p, chbr, 34, 28)
    add_arp(p, chbr, vol=26)
    add_lead(p, MEL_BREAK, vol=44, vib=[8,28,56])
    add_bass(p, chbr, 'sparse', vol=46)
    # bars 3-4: drums return
    add_drums(p, kick_rows=(0,4,8,12), snare_rows=(12,), clap_rows=(4,), bars=(2,3),
              hat=True, ohat_rows=(6,14), kick_vol=58, snare_vol=48, clap_vol=42, hat_vol=28)
    drum(p, 32, CH_FX, I['crash'], 36)
    for k, r in enumerate(range(48, 64, 2)):
        drum(p, r, CH_SNARE, I['snare'], 32 + k*3)
    drum(p, 63, CH_SNARE, I['clap'], 48)
    drum(p, 63, CH_KICK, I['kick'], 58)
    # dip the first two bars of the break (softer pad / arp / lead)
    for r in range(0, 32):
        for chn in (CH_LEAD, CH_ARP, CH_PAD, CH_PAD2):
            cell = p[r][chn]
            if cell and 'vol' in cell:
                v = cell['vol'] - 0x10
                cell['vol'] = 0x10 + max(1, int(round(v*0.72)))
    pats.append(p)

    # ---- P7 : A1 reprise with lead double
    p = new_pat()
    add_pad(p, ch, 38, 31)
    add_arp(p, ch, vol=36)
    add_bass(p, ch, 'push')
    add_drums(p, kick_rows=(0,4,8,12,14), ohat_rows=(2,6,10,14), hat_vol=36)
    add_lead(p, MEL_A1, vib=[8,20,36,52,60])
    add_lead(p, MEL_A1, inst=I['lead2'], vol=40, ch=CH_LEAD2)
    drum(p, 0, CH_FX, I['crash'], 44)
    drum(p, 32, CH_FX, I['crash'], 34)
    add_fill(p, 60, 'tom')
    pats.append(p)

    # ---- P8 : A2 reprise
    p = new_pat()
    add_pad(p, ch, 38, 31)
    add_arp(p, ch, vol=36)
    add_bass(p, ch, 'oct')
    add_drums(p, kick_rows=(0,4,8,12), ohat_rows=(2,6,10,14), hat_vol=36)
    add_lead(p, MEL_A2, vib=[4,24,36,52])
    add_lead(p, MEL_A2, inst=I['lead2'], vol=40, ch=CH_LEAD2)
    # high echo answers on the off-beats of bars 2 and 4
    for row, note in [(20,'A-6'),(24,'C-7'),(28,'A-6'),(52,'B-6'),(56,'D-7'),(60,'B-6')]:
        put(p, row, CH_FX, note=n(note), inst=I['arp'], vol=V(26))
    add_fill(p, 56, 'snare', 44)
    pats.append(p)

    # ---- P9 : B1 reprise
    p = new_pat()
    add_pad(p, chb, 38, 31)
    add_arp(p, chb, vol=28)
    add_bass(p, chb, 'drive')
    add_drums(p, kick_rows=(0,4,8,12), ohat_rows=(2,6,10,14), snare_vol=52, hat_vol=36)
    add_lead(p, MEL_B1, vib=[8,28,44,56])
    add_lead(p, MEL_B1, inst=I['lead2'], vol=40, ch=CH_LEAD2)
    drum(p, 0, CH_FX, I['crash'], 46)
    drum(p, 22, CH_FX, I['tom'], 48)
    drum(p, 30, CH_FX, I['tom'], 50)
    for r in range(48, 64):
        if r % 2 == 1:
            drum(p, r, CH_HAT, I['hat'], 20)
    pats.append(p)

    # ---- P10 : B2 reprise (big)
    p = new_pat()
    add_pad(p, chb, 38, 31)
    add_arp(p, chb, vol=36, mode='down')
    add_bass(p, chb, 'push')
    add_drums(p, kick_rows=(0,4,8,12,14), ohat_rows=(2,6,10,14), snare_vol=52, hat_vol=36)
    add_lead(p, MEL_B2, vib=[4,28,44,60])
    add_lead(p, MEL_B2, inst=I['lead2'], vol=40, ch=CH_LEAD2)
    for r in [30, 46]:
        drum(p, r, CH_SNARE, I['snare'], 46)
    drum(p, 32, CH_FX, I['crash'], 38)
    add_fill(p, 56, 'snare', 46)
    drum(p, 62, CH_FX, I['tom'], 54)
    pats.append(p)

    # ---- P11 : outro / turnaround
    cho = ['Am','F','G','E']
    p = new_pat()
    add_pad(p, cho, 36, 29)
    add_arp(p, cho, vol=35)
    add_bass(p, cho, 'drive')
    add_drums(p, kick_rows=(0,4,8,12), ohat_rows=(2,6,10,14))
    add_lead(p, MEL_OUT, vib=[24,52,56])
    add_lead(p, MEL_OUT, inst=I['lead2'], vol=38, ch=CH_LEAD2)
    drum(p, 0, CH_FX, I['crash'], 44)
    drum(p, 60, CH_FX, I['zap'], 44)
    for k, r in enumerate([58,60,62]):
        drum(p, r, CH_SNARE, I['snare'], 44 + k*4)
    drum(p, 63, CH_FX, I['crash'], 44)
    drum(p, 63, CH_KICK, I['kick'], 58)
    pats.append(p)

    orders = list(range(len(pats)))
    return pats, orders

def main():
    insts = make_instruments()
    pats, orders = build()
    out = '/workspace/submission/tune.xm'
    os.makedirs('/workspace/submission', exist_ok=True)
    write_xm(out, 'Keygen Bounce', orders, pats, insts, speed=6, bpm=150,
             restart=0, linear=True, tracker='FastTracker II clone')
    print("wrote", out, "patterns:", len(pats), "orders:", orders)

if __name__ == '__main__':
    main()
