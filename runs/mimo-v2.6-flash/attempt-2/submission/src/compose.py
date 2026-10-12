"""Compose the keygen tune: patterns, order list, song settings."""
import sys, json, subprocess
sys.path.insert(0, "/workspace/src"); sys.path.insert(0, "/workspace")
from lib import call, batch
from synth import nn
import instruments

# ------------------------------------------------------------------ layout
CH = {"bass":0, "lead":1, "harm":2, "arp":3, "padA":4,
      "kick":5, "snare":6, "hats":7, "perc":8, "padB":9}
I  = {"bass":1, "lead":2, "harm":3, "arp":4, "pad":5,
      "kick":6, "snare":7, "hatc":8, "hato":9, "crash":10, "tom":11}
NCH = 10
ROWS = 64
BAR  = 16                      # 16 rows = one 4/4 bar at speed 6 / 150 BPM

# effects
ARP, PORTAUP, PORTADOWN, TONEPORTA, VIB, TREMOR = 0,1,2,3,4,5
VIBVOL, TREMPAN, PAN, OFFSET, VOLSLIDE = 6,7,8,9,10
JUMP, SETVOL, BREAK, EXT, SPEED = 11,12,13,14,15

# ------------------------------------------------------------------ chords
def C(base, offs):
    return [nn(base) + o for o in offs]

CHORDS = {
    # name : pad root, pad third, bass root, arp figure (4 tones), arpeggio-fx note+param
    "Am": dict(padA=nn("A-3"), padB=nn("C-4"), bass=nn("A-2"),
               tones=C("A-4",[0,3,7,12]), fx=(nn("A-4"), 0x37)),
    "F":  dict(padA=nn("F-3"), padB=nn("A-3"), bass=nn("F-2"),
               tones=C("F-4",[0,4,7,12]), fx=(nn("F-4"), 0x47)),
    "C":  dict(padA=nn("C-4"), padB=nn("E-4"), bass=nn("C-3"),
               tones=C("C-5",[0,4,7,12]), fx=(nn("C-5"), 0x47)),
    "G":  dict(padA=nn("G-3"), padB=nn("B-3"), bass=nn("G-2"),
               tones=C("G-4",[0,4,7,12]), fx=(nn("G-4"), 0x47)),
    "Dm": dict(padA=nn("D-4"), padB=nn("F-4"), bass=nn("D-3"),
               tones=C("D-4",[0,3,7,12]), fx=(nn("D-4"), 0x37)),
    "E":  dict(padA=nn("E-3"), padB=nn("G#4"), bass=nn("E-2"),
               tones=C("E-4",[0,4,7,12]), fx=(nn("E-4"), 0x48)),
    "Em": dict(padA=nn("E-3"), padB=nn("G-4"), bass=nn("E-2"),
               tones=C("E-4",[0,3,7,12]), fx=(nn("E-4"), 0x37)),
}

# ------------------------------------------------------------------ builder
class Cells:
    """collects pattern_set_cell calls"""
    def __init__(self):
        self.items = []
    def put(self, pat, row, ch, note=None, inst=None, vol=None, fx=None, px=None):
        assert 0 <= row < ROWS and 0 <= ch < NCH, (pat, row, ch)
        a = {"pattern": pat, "row": row, "channel": ch}
        if note is not None: a["note"] = note
        if inst is not None: a["instrument"] = inst
        if vol is not None: a["volume"] = 16 + int(vol)     # XM volume column byte
        if fx   is not None: a["effect"]   = fx
        if px   is not None: a["effect_param"] = px
        self.items.append(("pattern_set_cell", a))
    def flush(self):
        for i in range(0, len(self.items), 400):
            batch(self.items[i:i+400])
        n = len(self.items); self.items = []
        return n

# ------------------------------------------------------------------ parts
def bass_bar(cs, pat, bar, root, style="drive"):
    off = bar * BAR
    if style == "drive":
        seq = [(0,0),(2,0),(4,0),(6,0),(8,0),(10,0),(12,0),(14,7)]
    elif style == "drive2":
        seq = [(0,0),(2,0),(4,0),(6,0),(8,0),(10,0),(12,0),(14,0)]
    elif style == "oct":
        seq = [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,0),(14,12)]
    elif style == "push":
        seq = [(0,0),(2,0),(4,0),(6,0),(8,0),(10,0),(12,12),(14,7)]
    elif style == "half":
        seq = [(0,0),(8,0)]
    elif style == "whole":
        seq = [(0,0)]
    elif style == "sparse":
        for r in (0,):
            cs.put(pat, off + r, CH["bass"], note=root, inst=I["bass"], vol=58)
        cs.put(pat, off + 8, CH["bass"], note="OFF")
        return
    else:
        raise ValueError(style)
    for r, semi in seq:
        cs.put(pat, off + r, CH["bass"], note=root + semi, inst=I["bass"], vol=60)

IDX_UP   = [0,1,2,3, 2,1,2,3, 0,1,2,3, 2,3,2,1]
IDX_DOWN = [3,2,1,0, 1,2,1,2, 3,2,1,0, 1,0,1,2]

def arp_run_bar(cs, pat, bar, tones, vol=44):
    off = bar * BAR
    idx = IDX_UP if bar % 2 == 0 else IDX_DOWN
    for r in range(BAR):
        cs.put(pat, off + r, CH["arp"], note=tones[idx[r]], inst=I["arp"], vol=vol)

def arp_fx_bar(cs, pat, bar, chord, vol=42, retrigger=False):
    """Trigger once and let the arpeggio effect run through the bar."""
    off = bar * BAR
    n, px = chord["fx"]
    cs.put(pat, off, CH["arp"], note=n, inst=I["arp"], vol=vol, fx=ARP, px=px)
    for r in range(1, BAR):
        if retrigger:
            cs.put(pat, off + r, CH["arp"], note=n, inst=I["arp"], vol=vol, fx=ARP, px=px)
        else:
            cs.put(pat, off + r, CH["arp"], fx=ARP, px=px)

def pad_bar(cs, pat, bar, chord, vol=34):
    off = bar * BAR
    cs.put(pat, off, CH["padA"], note=chord["padA"], inst=I["pad"], vol=vol, fx=PAN, px=0x30)
    cs.put(pat, off, CH["padB"], note=chord["padB"], inst=I["pad"], vol=max(1, vol-2), fx=PAN, px=0xD8)

def hats_bar(cs, pat, bar, style="full"):
    off = bar * BAR
    if style == "off":
        return
    if style == "soft":
        for r in (0,2,4,6,8,10,12,14):
            cs.put(pat, off + r, CH["hats"], note="C-4", inst=I["hatc"], vol=26)
        return
    if style == "full":
        rows = [(0,36),(2,34),(4,36),(6,48),(8,36),(10,34),(12,36),(14,48)]
        for r, v in rows:
            inst = I["hato"] if v == 48 else I["hatc"]
            cs.put(pat, off + r, CH["hats"], note="C-4", inst=inst, vol=v)
        return
    if style == "16":
        for r in range(BAR):
            if r in (6,14):
                cs.put(pat, off + r, CH["hats"], note="C-4", inst=I["hato"], vol=48)
            else:
                cs.put(pat, off + r, CH["hats"], note="C-4", inst=I["hatc"],
                       vol=38 if r % 4 == 0 else 30)
        return
    raise ValueError(style)

def kick_bar(cs, pat, bar, extra=()):
    off = bar * BAR
    for r in (0,4,8,12):
        cs.put(pat, off + r, CH["kick"], note="C-4", inst=I["kick"], vol=64)
    for r in extra:
        cs.put(pat, off + r, CH["kick"], note="C-4", inst=I["kick"], vol=56)

def snare_bar(cs, pat, bar, vol=56):
    off = bar * BAR
    for r in (4,12):
        cs.put(pat, off + r, CH["snare"], note="C-4", inst=I["snare"], vol=vol)

def fill_snare(cs, pat, bar=3, start=12, ramp=(46,62), tom_end=True):
    """quick 16th pickup at the end of a bar (rows are bar relative)"""
    off = bar * BAR
    rows = list(range(start, BAR))
    v0, v1 = ramp
    for i, r in enumerate(rows):
        v = v0 + int((v1 - v0) * i / max(1, len(rows) - 1))
        if tom_end and r == BAR - 1:
            cs.put(pat, off + r, CH["perc"], note="A-3", inst=I["tom"], vol=58)
        else:
            cs.put(pat, off + r, CH["snare"], note="C-4", inst=I["snare"], vol=v)

def fill_tom(cs, pat, bar=3):
    off = bar * BAR
    seq = [(8,"A-3",50),(10,"G-3",52),(12,"F-3",54),
           (13,"E-3",56),(14,"D-3",58),(15,"C-3",62)]
    for r, n, v in seq:
        cs.put(pat, off + r, CH["perc"], note=n, inst=I["tom"], vol=v)

def crash(cs, pat, vol=52):
    cs.put(pat, 0, CH["perc"], note="C-4", inst=I["crash"], vol=vol)

def melody(cs, pat, ch, inst, notes, vol=62):
    """notes: (bar, row, note, dur_rows) - long notes get a running vibrato"""
    for bar, r, n, d in notes:
        off = bar * BAR + r
        if d and d >= 8:
            cs.put(pat, off, ch, note=n, inst=inst, vol=vol, fx=VIB, px=0x52)
            for k in range(1, d):
                if off + k < (bar + 1) * BAR:
                    cs.put(pat, off + k, ch, fx=VIB, px=0x52)
        else:
            cs.put(pat, off, ch, note=n, inst=inst, vol=vol)

# ------------------------------------------------------------------ melodies
# Theme A : | Am | F | C | G |
MEL_A = [
 (0, 0,"E-5",2),(0, 2,"A-5",2),(0, 4,"G-5",2),(0, 6,"E-5",2),
 (0, 8,"C-5",2),(0,10,"D-5",2),(0,12,"E-5",4),
 (1, 0,"F-5",2),(1, 2,"A-5",2),(1, 4,"G-5",2),(1, 6,"F-5",2),
 (1, 8,"C-5",2),(1,10,"D-5",2),(1,12,"C-5",4),
 (2, 0,"E-5",2),(2, 2,"G-5",2),(2, 4,"E-5",2),(2, 6,"C-5",2),
 (2, 8,"D-5",2),(2,10,"E-5",2),(2,12,"G-5",4),
 (3, 0,"D-5",2),(3, 2,"B-4",2),(3, 4,"D-5",2),(3, 6,"G-5",2),
 (3, 8,"F-5",1),(3, 9,"E-5",1),(3,10,"D-5",2),(3,12,"B-4",2),(3,14,"D-5",2),
]
HAR_A = [
 (0, 0,"C-5",2),(0, 2,"E-5",2),(0, 4,"E-5",2),(0, 6,"C-5",2),
 (0, 8,"A-4",2),(0,10,"B-4",2),(0,12,"C-5",4),
 (1, 0,"C-5",2),(1, 2,"F-5",2),(1, 4,"E-5",2),(1, 6,"C-5",2),
 (1, 8,"A-4",2),(1,10,"A-4",2),(1,12,"A-4",4),
 (2, 0,"C-5",2),(2, 2,"E-5",2),(2, 4,"C-5",2),(2, 6,"G-4",2),
 (2, 8,"B-4",2),(2,10,"C-5",2),(2,12,"E-5",4),
 (3, 0,"B-4",2),(3, 2,"G-4",2),(3, 4,"B-4",2),(3, 6,"D-5",2),
 (3, 8,"D-5",1),(3, 9,"C-5",1),(3,10,"B-4",2),(3,12,"G-4",2),(3,14,"B-4",2),
]
# Theme B : | Dm | Am | F | E |
MEL_B = [
 (0, 0,"D-5",2),(0, 2,"F-5",2),(0, 4,"A-5",2),(0, 6,"F-5",2),
 (0, 8,"E-5",2),(0,10,"D-5",2),(0,12,"F-5",4),
 (1, 0,"A-5",2),(1, 2,"G-5",2),(1, 4,"E-5",2),(1, 6,"C-5",2),
 (1, 8,"D-5",2),(1,10,"E-5",2),(1,12,"C-5",4),
 (2, 0,"F-5",2),(2, 2,"A-5",2),(2, 4,"G-5",2),(2, 6,"F-5",2),
 (2, 8,"E-5",2),(2,10,"D-5",2),(2,12,"C-5",4),
 (3, 0,"E-5",2),(3, 2,"D-5",2),(3, 4,"C-5",2),(3, 6,"B-4",2),
 (3, 8,"C-5",2),(3,10,"D-5",2),(3,12,"E-5",4),
]
HAR_B = [
 (0, 0,"A-4",2),(0, 2,"D-5",2),(0, 4,"F-5",2),(0, 6,"D-5",2),
 (0, 8,"C-5",2),(0,10,"A-4",2),(0,12,"D-5",4),
 (1, 0,"E-5",2),(1, 2,"E-5",2),(1, 4,"C-5",2),(1, 6,"A-4",2),
 (1, 8,"B-4",2),(1,10,"C-5",2),(1,12,"A-4",4),
 (2, 0,"C-5",2),(2, 2,"F-5",2),(2, 4,"E-5",2),(2, 6,"C-5",2),
 (2, 8,"C-5",2),(2,10,"A-4",2),(2,12,"A-4",4),
 (3, 0,"B-4",2),(3, 2,"B-4",2),(3, 4,"G#4",2),(3, 6,"G#4",2),
 (3, 8,"G#4",2),(3,10,"B-4",2),(3,12,"B-4",4),
]
# slow lead for the break
MEL_BREAK = [
 (0, 0,"E-5",8),(0, 8,"D-5",8),
 (1, 0,"C-5",8),(1, 8,"E-5",8),
 (2, 0,"F-5",8),(2, 8,"E-5",8),
 (3, 0,"D-5",8),(3, 8,"B-4",8),
]
# rising build line (bar 2-3 of the build pattern)
MEL_BUILD = [
 (2, 8,"B-4",2),(2,10,"D-5",2),(2,12,"E-5",2),(2,14,"F-5",2),
 (3, 0,"B-4",2),(3, 2,"C-5",2),(3, 4,"D-5",2),(3, 6,"E-5",2),
 (3, 8,"F-5",2),(3,10,"G#5",2),(3,12,"A-5",2),(3,14,"B-5",2),
]
# pickup at the end of the intro
MEL_PICKUP = [(3,8,"B-4",2),(3,10,"D-5",2),(3,12,"E-5",2),(3,14,"G-5",2)]
# turnaround ending (bars 0-2 = theme A, bar 3 = descending line)
MEL_TURN = [m for m in MEL_A if m[0] < 3] + [
 (3, 0,"F-5",2),(3, 2,"E-5",2),(3, 4,"D-5",2),(3, 6,"C-5",2),
 (3, 8,"B-4",2),(3,10,"C-5",2),(3,12,"D-5",2),(3,14,"E-5",2),
]
HAR_TURN = [m for m in HAR_A if m[0] < 3] + [
 (3, 0,"D-5",2),(3, 2,"B-4",2),(3, 4,"B-4",2),(3, 6,"G#4",2),
 (3, 8,"G#4",2),(3,10,"G#4",2),(3,12,"B-4",2),(3,14,"B-4",2),
]

def echo_notes(notes, delay=3, vol=26):
    """dotted-8th delay copy of a melody on the harmony channel"""
    out = []
    for bar, r, n, d in notes:
        rr = r + delay
        if rr < BAR:
            out.append((bar, rr, n, d))
    return out

# ------------------------------------------------------------------ sections
def _per(x, n=4):
    return x if isinstance(x, list) else [x] * n

SECTIONS = [
    dict(name="intro1", chords=["Am","Am","F","F"],
         bass=[None]*4, arp="fx", pad=True, kick=[0]*4, snare=[0]*4,
         hats=["off"]*4, crash=True, crashvol=44, fill=None, mel=None,
         har=None, ghosts=False),
    dict(name="intro2", chords=["Am","F","C","G"],
         bass=["half"]*4, arp="fx", pad=True, kick=[0]*4, snare=[0]*4,
         hats=["off","off","soft","soft"], crash=False, fill=None,
         mel=MEL_PICKUP, har=None, ghosts=False),
    dict(name="groove", chords=["Am","F","C","G"],
         bass=["drive"]*4, arp="run", pad=True, kick=[1]*4, snare=[1]*4,
         hats=["full"]*4, crash=True, fill=None, mel=None, har=None),
    dict(name="A1", chords=["Am","F","C","G"],
         bass=["drive"]*4, arp="run", pad=True, kick=[1]*4, snare=[1]*4,
         hats=["full"]*4, crash=True, crashvol=44, fill=None,
         mel=MEL_A, har=None, echo=(MEL_A, 3, 26)),
    dict(name="A2", chords=["Am","F","C","G"],
         bass=["drive","drive","push","drive"], arp="run", pad=True,
         kick=[1]*4, snare=[1]*4, hats=["full"]*4, crash=False,
         fill="snare", mel=MEL_A, har=HAR_A),
    dict(name="B1", chords=["Dm","Am","F","E"],
         bass=["drive"]*4, arp="run", pad=True, kick=[1]*4, snare=[1]*4,
         hats=["full"]*4, crash=True, fill=None, mel=MEL_B, har=None,
         echo=(MEL_B, 3, 26)),
    dict(name="B2", chords=["Dm","Am","F","E"],
         bass=["drive","drive","push","drive"], arp="run", pad=True,
         kick=[1]*4, snare=[1]*4, hats=["full"]*4, crash=False,
         fill="tom", mel=MEL_B, har=HAR_B),
    dict(name="break", chords=["Am","Am","F","E"],
         bass=[None,None,"sparse","sparse"], arp=[None,None,"fx","fx"],
         arpvol=34, pad=True, padvol=27, kick=[0]*4, snare=[0]*4,
         hats=["off","off","soft","soft"], crash=True, crashvol=42,
         fill=None, mel=MEL_BREAK, har=None, ghosts=False),
    dict(name="build", chords=["Am","F","G","E"],
         bass=["drive"]*4, arp="run", pad=True, kick=[0,1,1,1],
         snare=[0,1,1,1], hats=["soft","full","full","16"], crash=True,
         fill="big", mel=MEL_BUILD, har=None, ghosts=False),
    dict(name="A3", chords=["Am","F","C","G"],
         bass=["oct","drive","push","drive"], arp="run", pad=True,
         kick=[1]*4, snare=[1]*4, hats=["16"]*4, crash=True, fill=None,
         mel=MEL_A, har=HAR_A),
    dict(name="turn", chords=["Am","F","C","E"],
         bass=["drive"]*4, arp="run", pad=True, kick=[1]*4, snare=[1]*4,
         hats=["full"]*4, crash=False, fill="big", mel=MEL_TURN, har=HAR_TURN),
]

def fill_big(cs, pat):
    """full-bar-ending roll: 16ths through the second half, tom into the loop"""
    off = 3 * BAR
    kick_bar(cs, pat, 3)
    cs.put(pat, off + 4, CH["snare"], note="C-4", inst=I["snare"], vol=54)
    for i, r in enumerate(range(8, 15)):
        cs.put(pat, off + r, CH["snare"], note="C-4", inst=I["snare"],
               vol=44 + 3 * i)
    cs.put(pat, off + 15, CH["perc"], note="A-3", inst=I["tom"], vol=64)

def render_section(cs, pat, spec):
    chords = spec["chords"]
    for b, cname in enumerate(chords):
        ch = CHORDS[cname]
        if spec.get("pad"):
            pad_bar(cs, pat, b, ch, vol=spec.get("padvol", 34))
        st = _per(spec["bass"])[b]
        if st:
            bass_bar(cs, pat, b, ch["bass"], st)
        amode = _per(spec.get("arp"))[b]
        if amode == "fx":
            arp_fx_bar(cs, pat, b, ch, vol=spec.get("arpvol", 40))
        elif amode == "run":
            arp_run_bar(cs, pat, b, ch["tones"], vol=spec.get("arpvol", 44))
        if _per(spec["kick"])[b]:
            kick_bar(cs, pat, b)
        if _per(spec["snare"])[b]:
            snare_bar(cs, pat, b)
        hats_bar(cs, pat, b, _per(spec["hats"])[b])
    if spec.get("ghosts", True):
        for b in range(3):
            cs.put(pat, b * BAR + 15, CH["snare"], note="C-4",
                   inst=I["snare"], vol=24)
    if spec.get("crash"):
        crash(cs, pat, vol=spec.get("crashvol", 52))
    if spec.get("mel"):
        melody(cs, pat, CH["lead"], I["lead"], spec["mel"], vol=62)
    if spec.get("har"):
        melody(cs, pat, CH["harm"], I["harm"], spec["har"], vol=48)
    if spec.get("echo"):
        src, delay, ev = spec["echo"]
        melody(cs, pat, CH["harm"], I["harm"], echo_notes(src, delay, ev), vol=ev)
    if spec.get("fill") == "snare":
        fill_snare(cs, pat, ramp=(40,62))
    elif spec.get("fill") == "tom":
        fill_tom(cs, pat)
    elif spec.get("fill") == "big":
        fill_big(cs, pat)

# ------------------------------------------------------------------ main
def main(save_path="/workspace/submission/tune.xm", gain=1.0, new=True):
    save_path = str(save_path); gain = float(gain); new = bool(int(new))
    if new:
        call("module_new", {"channels": NCH, "name": "KEYGEN NEON CASCADE"})
        instruments.load(gain=gain)
    call("song_set", {"bpm": 150, "speed": 6, "length": len(SECTIONS),
                      "loop_start": 3, "name": "KEYGEN NEON CASCADE"})
    for p in range(len(SECTIONS)):
        call("pattern_set_length", {"pattern": p, "rows": ROWS})
        call("pattern_clear", {"pattern": p})
    cs = Cells()
    for p, spec in enumerate(SECTIONS):
        render_section(cs, p, spec)
    # cut any note that would otherwise sustain across a pattern boundary
    starts = set()
    for name, a in cs.items:
        if name == "pattern_set_cell" and a["row"] == 0 and "note" in a:
            starts.add((a["pattern"], a["channel"]))
    for p in range(len(SECTIONS)):
        for ch in (CH["bass"], CH["lead"], CH["harm"], CH["arp"]):
            if (p, ch) not in starts:
                cs.items.append(("pattern_set_cell",
                                 {"pattern": p, "row": 0, "channel": ch, "note": "OFF"}))
    n = cs.flush()
    print("cells:", n)
    for pos in range(len(SECTIONS)):
        call("order_set", {"position": pos, "pattern": pos})
    call("module_save", {"path": save_path, "format": "xm"})
    print("saved", save_path)

if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])
