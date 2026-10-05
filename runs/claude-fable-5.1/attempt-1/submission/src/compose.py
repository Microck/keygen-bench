"""Keygen tune composer: builds the song as FT2 tool calls (batch JSON)."""
import json, os, sys

SAMPLES = "/workspace/samples"
info = json.load(open(os.path.join(SAMPLES, "info.json")))

BPM, SPEED, ROWS = 150, 6, 64
NCH = 14
KICK, SNARE, HAT, BASS, ARP, LEAD, ECHO, PADL, PADR, ARP2, FX, ECHO2, CRASH, HARM = range(14)

# ---------------------------------------------------------------- instruments
# (number, sample-file, volume, panning)
INSTR = {
    "lead":   (1, "lead",  40, 128),
    "lead2":  (2, "lead2", 54, 128),
    "arp":    (3, "arp",   29, 96),
    "arp2":   (4, "arp2",  20, 170),
    "bass":   (5, "bass",  46, 128),
    "padL":   (6, "pad",   24, 40),
    "kick":   (7, "kick",  56, 128),
    "snare":  (8, "snare", 44, 128),
    "hat":    (9, "hat",   40, 150),
    "ohat":   (10, "ohat", 26, 150),
    "crash":  (11, "crash", 32, 128),
    "clap":   (12, "clap", 34, 110),
    "zap":    (13, "zap",  36, 128),
    "echo":   (14, "lead", 40, 60),
    "echo2":  (15, "lead2", 54, 196),
    "padR":   (16, "pad",  24, 216),
    "echoB":  (17, "lead", 40, 196),
    "echoB2": (18, "lead2", 54, 60),
    "harm":   (19, "lead2", 42, 90),
    "harm1":  (20, "lead", 32, 90),
    "riser":  (21, "riser", 40, 128),
}
GLOBAL = 0.84
INSTR = {k: (num, f, int(round(vol * GLOBAL)), pan) for k, (num, f, vol, pan) in INSTR.items()}
def I(name): return INSTR[name][0]
LEVEL = {num: vol for (num, f, vol, pan) in INSTR.values()}

NOTE_NAMES = {"C":0, "C#":1, "D":2, "D#":3, "E":4, "F":5, "F#":6, "G":7, "G#":8, "A":9, "A#":10, "B":11}
def N(s):
    """'C-4' -> 49 ; 'F#5' ; 'off' -> 97"""
    if s == "off": return 97
    name = s[:2].replace("-", ""); octv = int(s[2])
    return 12 * octv + NOTE_NAMES[name] + 1
def T(note, semis):
    if note == 97: return 97
    return note + semis
def V(v):  # musical level 0..64 (scaled per instrument when written into the volume column)
    return max(0, min(64, int(v)))

# ---------------------------------------------------------------- chords
# bass root (octave 2), arp base note, arp xy, pad voices
CHORDS = {
    "Em": dict(bass="E-2", arp="E-4", xy=0x37, inv="G-4", ixy=0x49, pad=("E-3", "G-4")),
    "C":  dict(bass="C-2", arp="C-4", xy=0x47, inv="E-4", ixy=0x38, pad=("C-3", "E-4")),
    "G":  dict(bass="G-2", arp="G-4", xy=0x47, inv="B-4", ixy=0x38, pad=("G-3", "B-3")),
    "D":  dict(bass="D-2", arp="D-4", xy=0x47, inv="F#4", ixy=0x38, pad=("D-3", "F#4")),
    "Am": dict(bass="A-2", arp="A-3", xy=0x37, inv="C-4", ixy=0x49, pad=("A-3", "C-4")),
    "B7": dict(bass="B-2", arp="B-3", xy=0x47, inv="D#4", ixy=0x38, pad=("B-3", "D#4")),
    "Bm": dict(bass="B-2", arp="B-3", xy=0x37, inv="D-4", ixy=0x49, pad=("B-3", "D-4")),
}
TONES = {"Em": {4, 7, 11}, "C": {0, 4, 7}, "G": {7, 11, 2}, "D": {2, 6, 9}, "Am": {9, 0, 4}, "B7": {11, 3, 6, 9}, "Bm": {11, 2, 6}}

class Pattern:
    def __init__(self, idx):
        self.idx = idx
        self.cells = {}
    def put(self, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
        if row < 0 or row >= ROWS: return
        c = self.cells.setdefault((row, ch), {})
        if note is not None: c["note"] = note
        if inst is not None: c["instrument"] = inst
        if vol is not None:
            ins = inst if inst is not None else c.get("instrument")
            lvl = LEVEL.get(ins, 64) if ins is not None else 64
            c["volume"] = 0x10 + max(0, min(64, int(round(vol * lvl / 64.0))))
        if fx is not None: c["effect"] = fx; c["effect_param"] = fxp or 0
    def get(self, row, ch):
        return self.cells.get((row, ch), {})

patterns = [Pattern(i) for i in range(13)]

# ---------------------------------------------------------------- building blocks
def drums(p, kick_rows=(), snare_rows=(), hat_rows=(), ohat_rows=(), kick_vol=64, snare_vol=64, hat_vols=None,
          bars=range(4), clap=False):
    for b in bars:
        base = b * 16
        for r in kick_rows: p.put(base + r, KICK, N("C-4"), I("kick"), V(kick_vol))
        for r in snare_rows:
            p.put(base + r, SNARE, N("C-4"), I("snare"), V(snare_vol))
            if clap: p.put(base + r, FX, N("C-4"), I("clap"), V(48))
        for r in hat_rows:
            hv = 64 if hat_vols is None else hat_vols[r % 16]
            if hv: p.put(base + r, HAT, N("C-4"), I("hat"), V(hv))
        for r in ohat_rows: p.put(base + r, HAT, N("C-4"), I("ohat"), V(56))

def ghosts(p, rows=(15,), vol=22, bars=range(4)):
    for b in bars:
        for r in rows:
            if (b * 16 + r, SNARE) not in p.cells:
                p.put(b * 16 + r, SNARE, N("C-4"), I("snare"), V(vol))

def fill(p, kind="A"):
    """snare fill in the last bar (rows 48..63)"""
    if kind == "A":
        hits = [(56, 36), (58, 42), (60, 50), (61, 54), (62, 58), (63, 64)]
    elif kind == "B":
        hits = [(52, 34), (54, 40), (56, 46), (58, 52), (60, 58), (61, 60), (62, 62), (63, 64)]
    elif kind == "C":  # big: 16ths over the last half bar + zap
        hits = [(56 + i, 36 + i * 4) for i in range(8)]
    for r, v in hits:
        p.put(r, SNARE, N("C-4"), I("snare"), V(v))
    if kind == "C":
        p.put(60, FX, N("C-4"), I("zap"), V(44))
        p.put(62, FX, N("C-4"), I("zap"), V(52))
        for r in range(60, 64):   # hi-hat roll: retrigger every 2 ticks
            p.put(r, HAT, N("C-4"), I("hat"), V(40 + (r - 60) * 6), 0xE, 0x92)

BASS_GROOVE = [(0, 0, 64), (2, 12, 46), (3, 0, 56), (6, 0, 60), (8, 0, 62), (10, 12, 46), (11, 0, 54), (14, 0, 60), (15, 12, 46)]
BASS_SIMPLE = [(0, 0, 64), (2, 12, 48), (4, 0, 60), (6, 12, 48), (8, 0, 62), (10, 12, 48), (12, 0, 60), (14, 12, 48)]
BASS_HALF = [(0, 0, 64), (6, 0, 56), (8, 12, 50), (11, 0, 56)]

def bassline(p, chords, groove=BASS_GROOVE, bars=range(4), oct_shift=0):
    for b in bars:
        root = N(CHORDS[chords[b]]["bass"]) + oct_shift
        for r, t, v in groove:
            p.put(b * 16 + r, BASS, root + t, I("bass"), V(v))

def arps(p, chords, mode="eighths", bars=range(4), vol=64, ch=ARP, inst="arp", oct_shift=0):
    for b in bars:
        c = CHORDS[chords[b]]
        base = N(c["arp"]) + oct_shift
        if mode == "eighths":
            # alternate root position and first inversion every 8th note
            for r in range(0, 16, 2):
                inv = (r % 4 == 2)
                n = (N(c["inv"]) + oct_shift) if inv else base
                xy = c["ixy"] if inv else c["xy"]
                v = vol if r % 8 == 0 else int(vol * 0.8)
                p.put(b * 16 + r, ch, n, I(inst), V(v), 0x0, xy)
                p.put(b * 16 + r + 1, ch, fx=0x0, fxp=xy)
        elif mode == "sixteenths":
            for r in range(16):
                n = base + (12 if r % 2 == 1 else 0)
                v = vol if r % 4 == 0 else int(vol * 0.78)
                p.put(b * 16 + r, ch, n, I(inst), V(v), 0x0, c["xy"])
        elif mode == "sustain":
            p.put(b * 16, ch, base, I(inst), V(vol), 0x0, c["xy"])
            for r in range(1, 16):
                p.put(b * 16 + r, ch, fx=0x0, fxp=c["xy"])
        elif mode == "offbeat":  # 8th-note offbeats, octave up
            for r in range(2, 16, 4):
                p.put(b * 16 + r, ch, base + 12, I(inst), V(vol), 0x0, c["xy"])
                p.put(b * 16 + r + 1, ch, fx=0x0, fxp=c["xy"])
                p.put(min(b * 16 + r + 2, ROWS - 1), ch, 97)

def pad(p, chords, bars=range(4), vol=64, retrig_each_bar=True):
    for b in bars:
        lo, hi = CHORDS[chords[b]]["pad"]
        p.put(b * 16, PADL, N(lo), I("padL"), V(vol))
        p.put(b * 16, PADR, N(hi), I("padR"), V(vol))

SCALE = [4, 6, 7, 9, 11, 0, 2]   # E natural minor pitch classes
def harmony_below(note, degrees=2):
    """diatonic third below in E minor (chromatic fallback for non-scale tones)"""
    if note == 97: return 97
    pc = (note - 1) % 12
    if pc not in SCALE:
        return note - 4
    i = SCALE.index(pc)
    j = (i - degrees) % 7
    down = (SCALE[i] - SCALE[j]) % 12
    return note - down

def chord_harmony(note, chord):
    """nearest chord tone at least a minor third below the lead note"""
    if note == 97: return 97
    tones = TONES[chord]
    for d in range(3, 13):
        if (note - 1 - d) % 12 in tones:
            return note - d
    return note - 12

def melody(p, events, inst="lead", vol=60, vib=(0x6, 0x3), vib_delay=2, echo=True, echo_inst=None,
           echo_vol=None, echo2=True, ch=LEAD, spill=None, transpose=0, harm=False, harm_vol=None, chords=None):
    """events: list of (row, notename[, 'slide' or slide-speed]). Holds until next event.
    Vibrato starts vib_delay rows after onset. Echo copies to ECHO (+3 rows) and ECHO2 (+6 rows).
    Events past the pattern end are returned (spill)."""
    ev = sorted(events, key=lambda e: e[0])
    spill_out = []
    echo_inst = echo_inst or ("echo" if inst == "lead" else "echo2")
    echo_inst2 = "echoB" if inst == "lead" else "echoB2"
    echo_vol = echo_vol if echo_vol is not None else int(vol * 0.42)
    echo_vol2 = int(vol * 0.22)
    harm_inst = "harm" if inst == "lead2" else "harm1"
    harm_vol = harm_vol if harm_vol is not None else int(vol * 0.7)
    prev_note = None
    for k, e in enumerate(ev):
        row, name = e[0], e[1]
        slide = e[2] if len(e) > 2 else None
        note = T(N(name), transpose)
        nxt = ev[k + 1][0] if k + 1 < len(ev) else ROWS
        if note == 97:
            p.put(row, ch, 97)
            if harm: p.put(row, HARM, 97)
        else:
            if slide and prev_note is not None and prev_note != 97:
                # tone portamento: glide from the previous note; speed so it lands in ~1.5 rows
                dist = abs(note - prev_note) * 64
                rows_ = 1.5 if slide is True else slide
                spd = max(1, min(0xFF, int(round(dist / (20.0 * rows_)))))
                p.put(row, ch, note, I(inst), V(vol), 0x3, spd)
                p.put(row + 1, ch, fx=0x3, fxp=spd)
                start_vib = row + 2
            else:
                p.put(row, ch, note, I(inst), V(vol))
                start_vib = row + 1
            if harm:
                hn = chord_harmony(note, chords[min(row // 16, 3)]) if chords else harmony_below(note)
                p.put(row, HARM, hn, I(harm_inst), V(harm_vol))
            for r in range(start_vib, min(nxt, ROWS)):
                if r - row >= vib_delay and vib:
                    p.put(r, ch, fx=0x4, fxp=(vib[0] << 4) | vib[1])
                    if harm: p.put(r, HARM, fx=0x4, fxp=(vib[0] << 4) | vib[1])
        prev_note = note
        if echo:
            for off, ei, evol, ech in ((3, echo_inst, echo_vol, ECHO), (6, echo_inst2, echo_vol2, ECHO2)):
                if not echo2 and off == 6: continue
                rr = row + off
                if rr >= ROWS:
                    spill_out.append((rr - ROWS, ech, note, I(ei), evol))
                elif note == 97:
                    p.put(rr, ech, 97)
                else:
                    p.put(rr, ech, note, I(ei), V(evol))
    return spill_out

def apply_spill(p, spill):
    for row, ch, note, inst, vol in spill:
        if note == 97: p.put(row, ch, 97)
        else: p.put(row, ch, note, inst, V(vol))

# ---------------------------------------------------------------- themes
THEME_A = [(0,'E-5'),(3,'G-5'),(4,'F#5'),(6,'E-5'),(8,'B-4'),(11,'off'),(12,'D-5'),(14,'E-5'),
           (16,'G-5'),(20,'E-5'),(22,'D-5'),(24,'C-5'),(27,'D-5'),(28,'E-5',True),(31,'off'),
           (32,'D-5'),(35,'G-5'),(36,'F#5'),(38,'G-5'),(40,'B-5',True),(43,'off'),(44,'A-5'),(46,'G-5'),
           (48,'F#5'),(52,'D-5'),(54,'E-5'),(56,'F#5',True),(59,'off'),(60,'G-5'),(62,'F#5')]
THEME_A2 = THEME_A[:15] + [
           (32,'D-5'),(35,'G-5'),(36,'A-5'),(38,'B-5'),(40,'D-6'),(43,'off'),(44,'B-5'),(46,'A-5'),
           (48,'G-5'),(52,'F#5'),(54,'D-5'),(56,'E-5'),(59,'off'),(60,'F#5'),(62,'D-5'),(63,'off')]
THEME_B = [(0,'C-5'),(4,'E-5'),(6,'D-5'),(8,'C-5'),(11,'off'),(12,'B-4'),(14,'C-5'),
           (16,'B-4'),(22,'off'),(24,'G-5'),(28,'F#5',True),(30,'E-5'),
           (32,'D-5'),(36,'E-5'),(38,'G-5'),(40,'A-5',True),(43,'off'),(44,'G-5'),(46,'E-5'),
           (48,'F#5'),(52,'D-5'),(54,'F#5'),(56,'A-5',True),(59,'off'),(60,'B-5'),(62,'A-5')]
THEME_B2 = THEME_B[:19] + [
           (48,'F#5'),(52,'D#5'),(54,'F#5'),(56,'B-5'),(59,'off'),(60,'A-5'),(62,'F#5'),(63,'off')]
CHORUS = [(0,'B-5'),(6,'G-5'),(8,'E-5',True),(11,'off'),(12,'F#5'),(14,'G-5'),
          (16,'E-5'),(22,'G-5'),(24,'A-5',True),(27,'off'),(28,'G-5'),(30,'E-5'),
          (32,'D-5'),(36,'G-5'),(38,'B-5'),(40,'D-6',True),(43,'off'),(44,'B-5'),(46,'G-5'),
          (48,'A-5'),(52,'F#5'),(54,'A-5'),(56,'B-5',True),(59,'off'),(60,'A-5'),(62,'F#5')]
CHORUS2 = CHORUS[:12] + [
          (32,'F#5'),(36,'A-5'),(38,'B-5'),(40,'D-6'),(43,'off'),(44,'A-5'),(46,'B-5'),
          (48,'B-5'),(52,'A-5'),(54,'F#5'),(56,'D#5'),(59,'off'),(60,'F#5'),(62,'B-5'),(63,'off')]
BREAK_MOTIF = [(0,'E-5'),(6,'off'),(8,'C-5'),(14,'off'),(16,'G-5'),(22,'off'),(24,'E-5'),(30,'off'),
               (32,'B-4'),(38,'off'),(40,'E-5'),(46,'off'),(48,'F#5'),(54,'off'),(56,'A-5'),(62,'off')]
BUILD_LINE = [(0,'C-5'),(8,'D-5'),(16,'E-5'),(24,'F#5'),(32,'G-5'),(40,'A-5'),(48,'B-5'),(56,'off')]
POST = [(0,'E-5'),(3,'G-5'),(4,'F#5'),(6,'E-5'),(8,'B-4'),(11,'off'),(12,'D-5'),(14,'E-5'),
        (16,'G-5'),(20,'E-5'),(22,'D-5'),(24,'C-5'),(27,'D-5'),(28,'E-5'),(31,'off'),
        (32,'D-5'),(35,'G-5'),(36,'F#5'),(38,'G-5'),(40,'B-5'),(47,'off'),
        (48,'A-5'),(52,'F#5'),(56,'D-5'),(59,'off')]

PROG_A = ["Em", "C", "G", "D"]
PROG_B = ["Am", "Em", "C", "D"]
PROG_B2 = ["Am", "Em", "C", "B7"]
PROG_C2 = ["Em", "C", "D", "B7"]
PROG_BREAK = ["Am", "C", "Em", "D"]
PROG_BUILD = ["C", "D", "B7", "B7"]

VERSE_KICK, VERSE_SNARE = (0, 8, 10), (4, 12)
VERSE_HATS = (0, 2, 4, 8, 10, 12)
VERSE_OHATS = (6, 14)
VERSE_HVOL = [52, 0, 40, 0, 44, 0, 0, 0, 52, 0, 40, 0, 44, 0, 0, 0]
HAT8_VOLS = [52, 0, 40, 0, 52, 0, 40, 0, 52, 0, 40, 0, 52, 0, 40, 0]
OFF8_VOLS = [0, 0, 44, 0, 0, 0, 44, 0, 0, 0, 44, 0, 0, 0, 44, 0]
CHORUS_KICK, CHORUS_SNARE = (0, 4, 8, 12), (4, 12)
HAT16_VOLS = [60, 34, 46, 34, 60, 34, 46, 34, 60, 34, 46, 34, 60, 34, 46, 40]

spills = {}
def build():
    P = patterns
    # ---- P0: intro 1 : arp + pad + hats
    p = P[0]
    for b, v in enumerate((34, 40, 46, 52)): arps(p, PROG_A, "eighths", vol=v, bars=[b])
    pad(p, PROG_A, vol=50)
    drums(p, hat_rows=(2, 6, 10, 14), hat_vols=OFF8_VOLS)
    for b in (2, 3): bassline(p, PROG_A, BASS_HALF, bars=[b])
    p.put(60, FX, N("C-4"), I("zap"), V(40)); p.put(62, FX, N("C-4"), I("zap"), V(48))
    # ---- P1: intro 2 : groove enters
    p = P[1]
    arps(p, PROG_A, "eighths", vol=56)
    pad(p, PROG_A, vol=46)
    bassline(p, PROG_A)
    drums(p, VERSE_KICK, VERSE_SNARE, VERSE_HATS, VERSE_OHATS, hat_vols=VERSE_HVOL)
    fill(p, "A")
    spills[2] = melody(p, [(56,'B-4'),(58,'C-5'),(60,'D-5'),(62,'D#5')], "lead", vol=50, vib=None, echo2=False)
    # ---- P2: theme A
    p = P[2]
    p.put(0, CRASH, N("C-4"), I("crash"), V(52))
    arps(p, PROG_A, "eighths", vol=56)
    pad(p, PROG_A, vol=40)
    bassline(p, PROG_A)
    drums(p, VERSE_KICK, VERSE_SNARE, VERSE_HATS, VERSE_OHATS, hat_vols=VERSE_HVOL)
    spills[3] = melody(p, THEME_A, "lead", vol=58, vib=(0x6, 0x2))
    ghosts(p, (15,))
    # ---- P3: theme A'
    p = P[3]
    arps(p, PROG_A, "eighths", vol=56)
    pad(p, PROG_A, vol=40)
    bassline(p, PROG_A)
    drums(p, VERSE_KICK, VERSE_SNARE, VERSE_HATS, VERSE_OHATS, hat_vols=VERSE_HVOL)
    spills[4] = melody(p, THEME_A2, "lead", vol=58, vib=(0x6, 0x2))
    ghosts(p, (7, 15), bars=range(3))
    drums(p, (0, 6, 8, 10), (4, 12), VERSE_HATS, VERSE_OHATS, hat_vols=VERSE_HVOL, bars=[2])
    fill(p, "A")
    # ---- P4: theme B
    p = P[4]
    arps(p, PROG_B, "eighths", vol=56)
    pad(p, PROG_B, vol=44)
    bassline(p, PROG_B)
    drums(p, VERSE_KICK, VERSE_SNARE, VERSE_HATS, VERSE_OHATS, hat_vols=VERSE_HVOL)
    spills[5] = melody(p, THEME_B, "lead", vol=58, vib=(0x6, 0x2))
    ghosts(p, (15,))
    # ---- P5: theme B'
    p = P[5]
    arps(p, PROG_B2, "eighths", vol=56)
    pad(p, PROG_B2, vol=44)
    bassline(p, PROG_B2)
    drums(p, VERSE_KICK, VERSE_SNARE, VERSE_HATS, VERSE_OHATS, hat_vols=VERSE_HVOL, bars=range(3))
    drums(p, (0, 4, 8, 12), (4, 12), (0, 2, 4, 6, 8, 10, 12, 14), (), hat_vols=HAT8_VOLS, bars=[3])
    spills[6] = melody(p, THEME_B2, "lead", vol=58, vib=(0x6, 0x2))
    ghosts(p, (7, 15), bars=range(3))
    fill(p, "C")
    p.put(48, CRASH, N("C-4"), I("riser"), V(56))
    # ---- P6: chorus 1
    p = P[6]
    p.put(0, CRASH, N("C-4"), I("crash"), V(56))
    arps(p, PROG_A, "sixteenths", vol=58)
    arps(p, PROG_A, "offbeat", vol=44, ch=ARP2, inst="arp2", oct_shift=-24)
    pad(p, PROG_A, vol=46)
    bassline(p, PROG_A, BASS_SIMPLE)
    drums(p, CHORUS_KICK, CHORUS_SNARE, tuple(range(16)), (), hat_vols=HAT16_VOLS, clap=True)
    spills[7] = melody(p, CHORUS, "lead2", vol=60)
    melody(p, CHORUS, "harm1", vol=40, vib=(0x6, 0x2), echo=False, ch=HARM, transpose=-12)   # octave double
    # ---- P7: chorus 2
    p = P[7]
    arps(p, PROG_C2, "sixteenths", vol=58)
    arps(p, PROG_C2, "offbeat", vol=44, ch=ARP2, inst="arp2", oct_shift=-24)
    pad(p, PROG_C2, vol=46)
    bassline(p, PROG_C2, BASS_SIMPLE)
    drums(p, CHORUS_KICK, CHORUS_SNARE, tuple(range(16)), (), hat_vols=HAT16_VOLS, clap=True)
    spills[8] = melody(p, CHORUS2, "lead2", vol=60)
    melody(p, CHORUS2, "harm1", vol=40, vib=(0x6, 0x2), echo=False, ch=HARM, transpose=-12)
    fill(p, "B")
    # ---- P8: break
    p = P[8]
    p.put(0, CRASH, N("C-4"), I("crash"), V(44))
    arps(p, PROG_BREAK, "sustain", vol=40)
    pad(p, PROG_BREAK, vol=64)
    bassline(p, PROG_BREAK, BASS_HALF)
    drums(p, (0, 8), (), (), (), kick_vol=50)
    spills[9] = melody(p, BREAK_MOTIF, "lead", vol=46, vib=(0x5, 0x4), vib_delay=1)
    # ---- P9: build
    p = P[9]
    arps(p, PROG_BUILD, "eighths", vol=50)
    pad(p, PROG_BUILD, vol=56)
    bassline(p, PROG_BUILD, BASS_SIMPLE)
    drums(p, (0, 8), (4, 12), (2, 6, 10, 14), (), hat_vols=OFF8_VOLS, bars=[0])
    drums(p, (0, 4, 8, 12), (4, 12), (0, 2, 4, 6, 8, 10, 12, 14), (), hat_vols=HAT8_VOLS, bars=[1])
    drums(p, (0, 4, 8, 12), (0, 2, 4, 6, 8, 10, 12, 14), tuple(range(16)), (), hat_vols=HAT16_VOLS, snare_vol=44, bars=[2])
    for r in range(16):
        p.put(48 + r, SNARE, N("C-4"), I("snare"), V(40 + int(r * 1.6)))
        p.put(48 + r, HAT, N("C-4"), I("hat"), V(HAT16_VOLS[r]))
        p.put(48 + r, KICK, N("C-4"), I("kick"), V(64) if r % 4 == 0 else None) if r % 4 == 0 else None
    p.put(56, FX, N("C-4"), I("zap"), V(40)); p.put(60, FX, N("C-4"), I("zap"), V(48)); p.put(62, FX, N("C-4"), I("zap"), V(56))
    spills[10] = melody(p, BUILD_LINE, "lead", vol=54, vib=(0x6, 0x4), vib_delay=3)
    p.put(48, CRASH, N("C-4"), I("riser"), V(64))
    # ---- P10: chorus 3
    p = P[10]
    p.put(0, CRASH, N("C-4"), I("crash"), V(56))
    arps(p, PROG_A, "sixteenths", vol=58)
    arps(p, PROG_A, "offbeat", vol=44, ch=ARP2, inst="arp2", oct_shift=-24)
    pad(p, PROG_A, vol=46)
    bassline(p, PROG_A, BASS_SIMPLE)
    drums(p, CHORUS_KICK, CHORUS_SNARE, tuple(range(16)), (), hat_vols=HAT16_VOLS, clap=True)
    spills[11] = melody(p, CHORUS, "lead2", vol=60, harm=True, chords=PROG_A)
    # ---- P11: chorus 4
    p = P[11]
    arps(p, PROG_C2, "sixteenths", vol=58)
    arps(p, PROG_C2, "offbeat", vol=44, ch=ARP2, inst="arp2", oct_shift=-24)
    pad(p, PROG_C2, vol=46)
    bassline(p, PROG_C2, BASS_SIMPLE)
    drums(p, CHORUS_KICK, CHORUS_SNARE, tuple(range(16)), (), hat_vols=HAT16_VOLS, clap=True)
    spills[12] = melody(p, CHORUS2, "lead2", vol=60, harm=True, chords=PROG_C2)
    fill(p, "C")
    # ---- P12: post-chorus (half time), leads back into theme A
    p = P[12]
    p.put(0, CRASH, N("C-4"), I("crash"), V(50))
    arps(p, PROG_A, "eighths", vol=54)
    pad(p, PROG_A, vol=50)
    bassline(p, PROG_A, BASS_HALF)
    drums(p, (0, 10), (8,), (0, 2, 4, 6, 8, 10, 12, 14), (), hat_vols=[50, 0, 36, 0, 50, 0, 36, 0, 50, 0, 36, 0, 50, 0, 36, 0], bars=range(3))
    drums(p, (0, 4, 8, 12), (4, 12), (0, 2, 4, 6, 8, 10, 12, 14), (), hat_vols=HAT8_VOLS, bars=[3])
    spills[2] = spills.get(2, []) + melody(p, POST, "lead", vol=56, vib=(0x6, 0x2))   # loop goes 12 -> 2
    fill(p, "B")
    # bass walk-up into the loop restart (D -> E minor)
    for r, nname, v in ((56, "D-2", 60), (58, "A-2", 50), (60, "B-2", 56), (62, "D-3", 56), (63, "D#3", 60)):
        p.put(r, BASS, N(nname), I("bass"), V(v))
    # apply echo spills (tail of pattern k-1 echoes into pattern k)
    for k, sp in spills.items():
        apply_spill(P[k], sp)

build()

ORDER = list(range(13))
LOOP_START = 2
if os.environ.get("SEAM_TEST"):
    ORDER = [11, 12, 2, 3]
    LOOP_START = 0

# ---------------------------------------------------------------- emit tool calls
calls = [{"name": "module_new", "arguments": {"channels": NCH, "name": "neon keyring"}}]
for name, (num, f, vol, pan) in INSTR.items():
    inf = info[f]
    calls.append({"name": "sample_load", "arguments": {"path": f"{SAMPLES}/{f}.wav", "instrument": num, "sample": 0}})
    meta = {"instrument": num, "sample": 0, "name": name, "volume": vol, "panning": pan,
            "relative_note": inf["rel"], "finetune": inf["fine"]}
    if inf["loop"]:
        meta.update(loop_start=inf["loop"][0], loop_length=inf["loop"][1], flags=17)
    else:
        meta.update(loop_start=0, loop_length=0, flags=16)
    calls.append({"name": "sample_set", "arguments": meta})
    calls.append({"name": "instrument_set", "arguments": {"instrument": num, "name": name}})
ncell = 0
ONLY = os.environ.get("ONLY_CH")
ONLY = None if ONLY is None else set(int(x) for x in ONLY.split(","))
RENDER_PATH = os.environ.get("RENDER_PATH", "/workspace/render.wav")
SAVE_PATH = os.environ.get("SAVE_PATH", "/workspace/submission/tune.xm")
for p in patterns:
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": p.idx, "rows": ROWS}})
    for (row, ch), c in sorted(p.cells.items()):
        if ONLY is not None and ch not in ONLY: continue
        a = {"pattern": p.idx, "row": row, "channel": ch}
        a.update(c)
        calls.append({"name": "pattern_set_cell", "arguments": a}); ncell += 1
calls.append({"name": "song_set", "arguments": {"name": "neon keyring", "bpm": BPM, "speed": SPEED, "length": len(ORDER), "loop_start": LOOP_START}})
for i, pt in enumerate(ORDER):
    calls.append({"name": "order_set", "arguments": {"position": i, "pattern": pt}})
calls.append({"name": "module_save", "arguments": {"path": SAVE_PATH, "format": "xm"}})
calls.append({"name": "module_render", "arguments": {"path": RENDER_PATH, "rate": 44100, "bits": 16, "loops": 1}})
json.dump(calls, open("/workspace/build.json", "w"))
print("cells:", ncell, "calls:", len(calls))
