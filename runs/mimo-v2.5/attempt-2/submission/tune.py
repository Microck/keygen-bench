"""KEYGEN TUNE - 'Neon Cipher'. 8 channels, A minor, 160 BPM (row = 16th note)."""
import xm, numpy as np, sounds, sys, os

ROWS, BAR = 64, 16
# channel map
LEAD, LEAD2, ARP, CHD, PAD, BASS, DR1, DR2 = range(8)

# ---------------- harmony ----------------
CH = {  # chord name -> (bass root, arp note set, stab root, arpeggio param)
 'Am': ('A-1', ['A-3','C-4','E-4','A-4'], 'A-3', 0x37),
 'F' : ('F-1', ['F-3','A-3','C-4','F-4'], 'F-3', 0x47),
 'C' : ('C-2', ['G-3','C-4','E-4','G-4'], 'C-4', 0x47),
 'G' : ('G-1', ['G-3','B-3','D-4','G-4'], 'G-3', 0x47),
 'Dm': ('D-2', ['A-3','D-4','F-4','A-4'], 'D-3', 0x37),
 'E' : ('E-1', ['G#-3','B-3','E-4','G#-4'],'E-3', 0x47),
}
ARP_PAT = {
 'updn' : [0,1,2,3, 2,1,0,1, 0,1,2,3, 2,3,2,1],
 'up'   : [0,1,2,3, 0,1,2,3, 0,1,2,3, 0,1,2,3],
 'zig'  : [0,2,1,2, 3,2,1,2, 0,2,1,2, 3,1,2,1],
 'wave' : [0,1,2,3, 2,1,2,3, 3,2,1,0, 1,2,3,2],
 'oct'  : [0,2,1,3, 0,2,1,3, 0,2,1,3, 2,3,2,1],
}

KEEP = None   # optional channel mask (for stem renders)

def put(s, p, row, ch, note, instr=None, vol=None, fx=None, fxp=None):
    if row >= ROWS: return
    if KEEP is not None and ch not in KEEP: return
    s.set(p, row, ch, note=note, instr=instr, vol=vol, fx=fx, fxp=fxp)

def note_len(s, p, row, ch, note, dur, instr=None, vol=None, fx=None, fxp=None, off=True):
    """place a note and cut it with NOTE OFF (no envelopes in this renderer -> hard cut)"""
    put(s, p, row, ch, note, instr, vol, fx, fxp)
    if off and dur and row+dur < ROWS:
        put(s, p, row+dur, ch, 'OFF')

# ---------------- part writers ----------------
def w_arp(s, p, bars, style='updn', vol=44, accent=True):
    for b, ch_name in enumerate(bars):
        notes = CH[ch_name][1]; pat = ARP_PAT[style]
        for r in range(BAR):
            n = notes[pat[r]]
            v = vol if (r % 4 == 0) else max(1, vol-14)
            put(s, p, b*BAR+r, ARP, n, 3, v)

def w_bass(s, p, bars, style='drive', vol=58):
    for b, ch_name in enumerate(bars):
        R = CH[ch_name][0]; base = b*BAR
        o = xm.ni(R); up = xm.name_of(o+12)
        if style == 'whole':
            note_len(s, p, base, BASS, R, 15, 6, vol, off=True)
        elif style == 'drive':
            seq = [(0,R),(2,R),(4,up),(6,R),(8,R),(10,up),(12,R),(14,up)]
            for r, n in seq:
                note_len(s, p, base+r, BASS, n, 2, 6, vol if r%4==0 else vol-8)
        elif style == 'push':
            seq = [(0,R),(2,R),(3,up),(4,R),(6,up),(8,R),(10,R),(11,up),(12,up),(14,R)]
            for r, n in seq:
                note_len(s, p, base+r, BASS, n, 2 if r not in (3,11) else 1, 6, vol if r%4==0 else vol-8)
        elif style == 'half':
            seq = [(0,R),(4,up),(8,R),(10,R),(12,up),(14,R)]
            for r, n in seq:
                note_len(s, p, base+r, BASS, n, 4 if r in (0,4) else 2, 6, vol)

def w_chords(s, p, bars, rows=(2,6,10,14), vol=32, instr=4):
    for b, ch_name in enumerate(bars):
        _, _, stab, arp = CH[ch_name]
        for r in rows:
            put(s, p, b*BAR+r, CHD, stab, instr, vol, fx=0, fxp=arp)

def w_pad(s, p, bars, vol=26, oct_=1):
    for b, ch_name in enumerate(bars):
        R = CH[ch_name][0]
        note_len(s, p, b*BAR, PAD, xm.name_of(xm.ni(R)+12*oct_), 15, 5, vol)

def w_drums(s, p, kick=(0,8), snare=(4,12), hats=True, hat_rows=None, openat=(6,14),
            dvol=64, svol=52, hvol=30, ohvol=26, extra_kick=(), fill=None):
    for b in range(4):
        base = b*BAR
        for r in kick: put(s, p, base+r, DR1, 'C-4', 7, dvol)
        for r in extra_kick: put(s, p, base+r, DR1, 'C-4', 7, dvol-10)
        for r in snare: put(s, p, base+r, DR1, 'D-4', 8, svol)
        if fill and base <= fill < base+BAR:
            for i, r in enumerate(range(fill-base, BAR, 2)):
                put(s, p, base+r, DR1, 'C-4' if i%2==0 else 'E-4', 11, 44+i*4)
        if hats:
            for r in (hat_rows if hat_rows is not None else range(BAR)):
                if r in openat: continue
                put(s, p, base+r, DR2, 'C#4', 9, hvol if r%4==0 else hvol-12)
            for r in openat:
                put(s, p, base+r, DR2, 'D#4', 10, ohvol)

def w_lead(s, p, line, vol=54, instr=1, ch=LEAD, off=True, vib=False):
    for (r, n, d) in line:
        fx, fxp = (4, 0x24) if (vib and d >= 4) else (None, None)
        note_len(s, p, r, ch, n, d, instr, vol, fx=fx, fxp=fxp, off=off)

def w_counter(s, p, line, vol=34):
    for (r, n, d) in line:
        note_len(s, p, r, LEAD2, n, d, 2, vol)

# ---------------- melodies ----------------
THEME_TEASER = [(0,'E-4',3),(3,'C-4',3),(6,'A-3',2),(8,'B-3',3),(11,'C-4',3),(14,'E-4',2),(16,'F-4',3),(19,'E-4',3),(22,'C-4',2),(24,'A-3',4),(28,'C-4',4),(32,'E-4',3),(35,'G-4',3),(38,'E-4',2),(40,'C-4',4),(44,'D-4',4),(48,'D-4',3),(51,'B-3',3),(54,'G-3',2),(56,'A-3',4),(60,'B-3',4)]

THEME_A = [
 (0,'E-5',3),(3,'C-5',3),(6,'A-4',2),(8,'B-4',3),(11,'C-5',3),(14,'E-5',2),
 (16,'F-5',3),(19,'E-5',3),(22,'C-5',2),(24,'A-4',4),(28,'C-5',4),
 (32,'E-5',3),(35,'G-5',3),(38,'E-5',2),(40,'C-5',4),(44,'D-5',4),
 (48,'D-5',3),(51,'B-4',3),(54,'G-4',2),(56,'A-4',4),(60,'B-4',4)]
THEME_A2 = [
 (0,'E-5',3),(3,'A-5',3),(6,'G-5',2),(8,'E-5',4),(12,'C-5',4),
 (16,'F-5',3),(19,'A-5',3),(22,'G-5',2),(24,'F-5',4),(28,'E-5',4),
 (32,'E-5',3),(35,'G-5',3),(38,'C-6',2),(40,'B-5',4),(44,'G-5',4),
 (48,'A-5',3),(51,'F#-5',3),(54,'D-5',2),(56,'E-5',4),(60,'D-5',4)]
THEME_B = [
 (0,'D-5',3),(3,'F-5',3),(6,'A-5',2),(8,'G-5',4),(12,'F-5',4),
 (16,'E-5',3),(19,'C-5',3),(22,'A-4',2),(24,'B-4',4),(28,'C-5',4),
 (32,'F-5',3),(35,'A-5',3),(38,'G-5',2),(40,'F-5',4),(44,'E-5',4),
 (48,'E-5',3),(51,'G#-5',3),(54,'B-5',2),(56,'G#-5',4),(60,'E-5',4)]
THEME_B2 = [
 (0,'A-5',3),(3,'F-5',3),(6,'D-5',2),(8,'E-5',4),(12,'F-5',4),
 (16,'G-5',3),(19,'E-5',3),(22,'C-5',2),(24,'A-4',4),(28,'B-4',4),
 (32,'C-5',3),(35,'F-5',3),(38,'A-5',2),(40,'C-6',4),(44,'A-5',4),
 (48,'B-5',2),(50,'A-5',2),(52,'G#-5',2),(54,'F#-5',2),(56,'E-5',4),(60,'D-5',2),(62,'C-5',2)]
OUTRO = [
 (0,'E-5',3),(3,'C-5',3),(6,'A-4',10),
 (16,'F-5',4),(20,'E-5',4),(24,'C-5',10),
 (32,'B-4',4),(36,'G#-4',4),(40,'E-4',10),
 (48,'A-4',12)]

C_A  = ['Am','F','C','G']
C_B  = ['Dm','Am','F','E']
C_X  = ['Am','F','C','E']
C_O  = ['Am','F','E','Am']

def compose(s):
    s.bpm, s.speed, s.restart = 160, 6, 0
    P = {}
    def pat():
        p = s.new_pattern(ROWS); return p

    # ---- P0 intro: arp + pad ----
    P[0] = pat()
    w_arp(s, P[0], C_A, 'updn', vol=42)
    w_pad(s, P[0], C_A, vol=26)
    put(s, P[0], 0, DR2, 'C#4', 12, 22)
    # ---- P1 intro 2: + bass, kick, hats ----
    P[1] = pat()
    w_arp(s, P[1], C_A, 'zig', vol=40)
    w_pad(s, P[1], C_A, vol=22)
    w_bass(s, P[1], C_A, 'half', vol=48)
    w_drums(s, P[1], kick=(0,8), snare=(), openat=(6,14), dvol=54, hvol=22, ohvol=18)
    w_lead(s, P[1], THEME_TEASER, vol=42)
    # ---- P2 theme A full ----
    P[2] = pat()
    w_arp(s, P[2], C_A, 'updn', vol=46)
    w_bass(s, P[2], C_A, 'drive', vol=58)
    w_chords(s, P[2], C_A, vol=30)
    w_pad(s, P[2], C_A, vol=22)
    w_drums(s, P[2], kick=(0,8,11), snare=(4,12), dvol=64, svol=50, hvol=30, ohvol=26)
    w_lead(s, P[2], THEME_A, vol=54, vib=False)
    put(s, P[2], 0, DR2, 'C-5', 12, 30)
    # ---- P3 theme A2 ----
    P[3] = pat()
    w_arp(s, P[3], C_A, 'wave', vol=46)
    w_bass(s, P[3], C_A, 'push', vol=58)
    w_chords(s, P[3], C_A, rows=(2,6,10,14), vol=30)
    w_pad(s, P[3], C_A, vol=22)
    w_drums(s, P[3], kick=(0,8,11), snare=(4,12), dvol=64, svol=50, hvol=30, ohvol=26, fill=52)
    w_lead(s, P[3], THEME_A2, vol=52)
    w_counter(s, P[3], [(0,'C-5',14),(16,'A-4',14),(32,'G-4',14),(48,'B-4',14)], vol=26)
    # ---- P4 theme B ----
    P[4] = pat()
    w_arp(s, P[4], C_B, 'oct', vol=46)
    w_bass(s, P[4], C_B, 'push', vol=58)
    w_chords(s, P[4], C_B, vol=30)
    w_pad(s, P[4], C_B, vol=22)
    w_drums(s, P[4], kick=(0,8,11), snare=(4,12), dvol=64, svol=50, hvol=30, ohvol=26)
    w_lead(s, P[4], THEME_B, vol=54)
    put(s, P[4], 0, DR2, 'C-5', 12, 30)
    # ---- P5 theme B2 ----
    P[5] = pat()
    w_arp(s, P[5], C_B, 'up', vol=46)
    w_bass(s, P[5], C_B, 'push', vol=58)
    w_chords(s, P[5], C_B, vol=30)
    w_pad(s, P[5], C_B, vol=22)
    w_drums(s, P[5], kick=(0,8), snare=(4,12), dvol=64, svol=50, hvol=30, ohvol=26, fill=48)
    w_lead(s, P[5], THEME_B2, vol=52)
    put(s, P[5], 63, DR1, 'OFF')
    # ---- P6 breakdown ----
    P[6] = pat()
    w_arp(s, P[6], C_X, 'updn', vol=24)
    w_pad(s, P[6], C_X, vol=26)
    w_lead(s, P[6], [(0,'E-5',6),(8,'C-5',6),(16,'A-4',10),(32,'G-4',6),(40,'E-4',6),
                     (48,'G#-4',8),(56,'B-4',8)], vol=36, ch=LEAD)
    w_counter(s, P[6], [(0,'A-3',14),(16,'F-3',14),(32,'E-4',14),(48,'E-3',14)], vol=26)
    put(s, P[6], 0, DR2, 'C-4', 12, 20)
    # ---- P7 build ----
    P[7] = pat()
    w_arp(s, P[7], C_A, 'up', vol=42)
    w_bass(s, P[7], C_A, 'half', vol=52)
    w_pad(s, P[7], C_A, vol=24)
    w_drums(s, P[7], kick=(0,8), snare=(12,), openat=(14,), dvol=58, svol=42, hvol=24, ohvol=20)
    w_lead(s, P[7], [(48,'A-4',3),(51,'B-4',3),(54,'C-5',2),(56,'D-5',4),(60,'E-5',4)], vol=48)
    # ---- P8 climax theme A ----
    P[8] = pat()
    w_arp(s, P[8], C_A, 'updn', vol=48)
    w_bass(s, P[8], C_A, 'push', vol=58)
    w_chords(s, P[8], C_A, vol=32)
    w_pad(s, P[8], C_A, vol=24)
    w_drums(s, P[8], kick=(0,8,11), snare=(4,12), dvol=64, svol=52, hvol=32, ohvol=28)
    w_lead(s, P[8], THEME_A, vol=56, vib=True)
    w_counter(s, P[8], [(r, xm.name_of(xm.ni(n)-12), d) for (r,n,d) in THEME_A], vol=24)
    put(s, P[8], 0, DR2, 'D#4', 10, 30)
    put(s, P[8], 0, DR2, 'C-5', 12, 34)
    # ---- P9 climax A2 ----
    P[9] = pat()
    w_arp(s, P[9], C_A, 'wave', vol=48)
    w_bass(s, P[9], C_A, 'push', vol=58)
    w_chords(s, P[9], C_A, vol=32)
    w_pad(s, P[9], C_A, vol=24)
    w_drums(s, P[9], kick=(0,8,11), snare=(4,12), dvol=64, svol=52, hvol=32, ohvol=28, fill=56)
    w_lead(s, P[9], THEME_A2, vol=56, vib=True)
    w_counter(s, P[9], [(0,'C-5',14),(16,'A-4',14),(32,'G-4',14),(48,'B-4',14)], vol=28)
    # ---- P10 outro ----
    P[10] = pat()
    w_arp(s, P[10], C_O, 'updn', vol=40)
    w_bass(s, P[10], C_O, 'half', vol=52)
    w_chords(s, P[10], C_O, rows=(2,6,10,14), vol=28)
    w_pad(s, P[10], C_O, vol=26)
    w_drums(s, P[10], kick=(0,8), snare=(4,), dvol=58, svol=46, hvol=26, ohvol=20)
    w_lead(s, P[10], OUTRO, vol=52)
    put(s, P[10], 48, DR1, 'C-4', 7, 60)
    put(s, P[10], 48, DR2, 'D#4', 10, 30)
    s.order = [P[i] for i in range(11)]
    return s

def build(instruments=None):
    s = xm.Song('Neon Cipher', channels=8)
    s.instruments = instruments if instruments is not None else sounds.build()
    compose(s)
    return s

if __name__ == '__main__':
    s = build()
    out = sys.argv[1] if len(sys.argv)>1 else '/workspace/submission/tune.xm'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print('bytes', xm.save(out, s))
