"""Compose the keygen tune: samples -> instruments -> patterns -> order."""
import sys, json, base64, subprocess, os
import numpy as np
sys.path.insert(0, '/workspace/src')
import samples as SMP

SR = 44100
WS = '/workspace'
TITLE = 'SERAPHIM KEYGEN'

# ------------------------------------------------------------------ ft2 io
def ft(name, args):
    r = subprocess.run(['ft2', 'call', name, json.dumps(args)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(name + ' -> ' + r.stdout + r.stderr)
    return r.stdout.strip()

def batch(calls, path=WS + '/t/b.json'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump([{'name': n, 'arguments': a} for n, a in calls], f)
    r = subprocess.run(['ft2', 'batch', path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('batch failed: ' + r.stdout[-2000:] + r.stderr[-2000:])
    return r.stdout

# ------------------------------------------------------------------ notes
def nm(s):
    s = s.strip()
    oct_ = int(s[-1])
    body = s[:-1].rstrip('-')
    m = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,
         'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    return 12*oct_ + m[body] + 1

# ------------------------------------------------------------------ levels
L = dict(kick=49, snare=45, hat=32, ohat=33, bass=42, arp=26,
         pad=19, lead=44, bell=26, sweep=30, harm=30)

# ------------------------------------------------------------------ instruments
# (ins#, sample, base note, panning, loop?, name)
INSTR = [
    (1,  'kick',  49, 128, 'KICK 909ISH'),
    (2,  'snare', 49, 128, 'SNARE 909ISH'),
    (3,  'hat',   49, 176, 'HAT CLOSED'),
    (4,  'ohat',  49, 168, 'HAT OPEN'),
    (5,  'bass',  27, 128, 'BASS PLUCK D2'),
    (6,  'arp',   61,  96, 'ARP PULSE C5'),
    (7,  'padL',  49,  76, 'PAD SAW L'),
    (8,  'padC',  49, 128, 'PAD SAW C'),
    (9,  'padR',  49, 180, 'PAD SAW R'),
    (10, 'lead',  61, 128, 'LEAD SAW C5'),
    (11, 'bell',  73, 220, 'BELL FM C6'),
    (12, 'sweep', 49, 128, 'NOISE RISER'),
    (13, 'lead',  61,  96, 'LEAD HARMONY'),
]

def tune(base_note):
    """relative note / finetune so that `base_note` plays at 44100 Hz."""
    total = 77.6 - base_note
    rel = int(round(total)); ftn = int(round((total - rel)*128))
    while ftn > 64:  rel += 1; ftn -= 128
    while ftn < -64: rel -= 1; ftn += 128
    return rel, ftn

# ------------------------------------------------------------------ harmony
CH = {
 'Dm': dict(root='D-2',  arp=['D-5','F-5','A-5','D-6'],   pad=['D-4','F-4','A-4']),
 'Bb': dict(root='Bb-1', arp=['D-5','F-5','Bb-5','D-6'],  pad=['D-4','F-4','Bb-4']),
 'F':  dict(root='F-2',  arp=['C-5','F-5','A-5','C-6'],   pad=['C-4','F-4','A-4']),
 'C':  dict(root='C-2',  arp=['C-5','E-5','G-5','C-6'],   pad=['C-4','E-4','G-4']),
 'Gm': dict(root='G-1',  arp=['D-5','G-5','Bb-5','D-6'],  pad=['D-4','G-4','Bb-4']),
 'A7': dict(root='A-1',  arp=['C#-5','E-5','A-5','C#-6'], pad=['C#-4','E-4','A-4']),
}
CHN = {k: dict(root=nm(v['root']),
               arp=[nm(x) for x in v['arp']],
               pad=[nm(x) for x in v['pad']]) for k, v in CH.items()}

# ------------------------------------------------------------------ channels
CH_KICK, CH_SN, CH_HAT, CH_OHAT = 0, 1, 2, 3
CH_BASS, CH_ARP = 4, 5
CH_PAD = (6, 7, 8)
CH_LEAD, CH_BELL, CH_SWEEP = 9, 10, 11
CH_HARM = 11                      # shares the sweep channel (never simultaneous)
DRUM_NOTE = 49                     # drums always triggered at C-4
ARP_SEQ16 = [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3]
ARP_SEQ8  = [0,1,2,3,2,1,0,1]

# ------------------------------------------------------------------ pattern holder
class Pat:
    def __init__(self, num):
        self.num = num
        self.cells = {}             # (row,ch) -> dict
    def put(self, row, ch, note=None, ins=None, vol=None, eff=None, prm=None):
        if row < 0 or row > 63: return
        c = self.cells.setdefault((row, ch), {})
        if note is not None: c['note'] = note
        if ins  is not None: c['ins']  = ins
        if vol  is not None: c['vol']  = vol
        if eff  is not None: c['eff']  = eff; c['prm'] = prm
    def calls(self):
        out = [('pattern_clear', {'pattern': self.num})]
        for (row, ch), c in sorted(self.cells.items()):
            a = {'pattern': self.num, 'row': int(row), 'channel': int(ch)}
            for k, key in (('note','note'), ('ins','instrument'), ('vol','volume'),
                           ('eff','effect'), ('prm','effect_param')):
                if k in c: a[key] = int(c[k])
            out.append(('pattern_set_cell', a))
        return out

# ------------------------------------------------------------------ parts
def beat_groove(p, bar, hats8=True, kick2=False):
    b = bar*16
    p.put(b+0,  CH_KICK, DRUM_NOTE, 1, L['kick'])
    p.put(b+8,  CH_KICK, DRUM_NOTE, 1, L['kick'])
    if kick2: p.put(b+10, CH_KICK, DRUM_NOTE, 1, L['kick']-4)
    p.put(b+4,  CH_SN,  DRUM_NOTE, 2, L['snare'])
    p.put(b+12, CH_SN,  DRUM_NOTE, 2, L['snare'])
    for r in (0,2,4,6,8,10,12,14):
        p.put(b+r, CH_HAT, DRUM_NOTE, 3, L['hat'] if r % 4 == 2 else L['hat']-4)
    if bar % 2 == 1:
        p.put(b+14, CH_OHAT, DRUM_NOTE, 4, L['ohat'])

def beat_full(p, bar):
    b = bar*16
    p.put(b+0,  CH_KICK, DRUM_NOTE, 1, L['kick'])
    p.put(b+8,  CH_KICK, DRUM_NOTE, 1, L['kick'])
    if bar % 2 == 1: p.put(b+10, CH_KICK, DRUM_NOTE, 1, L['kick']-3)
    p.put(b+4,  CH_SN,  DRUM_NOTE, 2, L['snare'])
    p.put(b+12, CH_SN,  DRUM_NOTE, 2, L['snare'])
    for r in range(16):
        p.put(b+r, CH_HAT, DRUM_NOTE, 3, L['hat']+2 if r % 2 == 0 else L['hat']-7)
    p.put(b+(6 if bar % 2 == 0 else 14), CH_OHAT, DRUM_NOTE, 4, L['ohat'])

def beat_half(p, bar):
    b = bar*16
    p.put(b+0,  CH_KICK, DRUM_NOTE, 1, L['kick']-6)
    p.put(b+8,  CH_SN,  DRUM_NOTE, 2, L['snare']-6)
    for r in (4, 12): p.put(b+r, CH_HAT, DRUM_NOTE, 3, L['hat']-6)

def beat_build(p, bar):
    b = bar*16
    p.put(b+0, CH_KICK, DRUM_NOTE, 1, L['kick']-2)
    if bar <= 1: p.put(b+8, CH_KICK, DRUM_NOTE, 1, L['kick']-4)
    for r in range(0, 16, 2):
        p.put(b+r, CH_HAT, DRUM_NOTE, 3, L['hat']-4+bar)
    if bar >= 1:
        step = 4 if bar == 1 else 2
        for i, r in enumerate(range(0, 16, step)):
            p.put(b+r, CH_SN, DRUM_NOTE, 2, L['snare']-14+i*3)
    if bar == 3:
        for i, r in enumerate(range(16)):
            p.put(b+r, CH_SN, DRUM_NOTE, 2, L['snare']-8+int(i*0.8))

def fill_snare(p, bar=3):
    b = bar*16
    for r, v in ((8, L['snare']-8), (10, L['snare']-6), (12, L['snare']-4),
                 (13, L['snare']-2), (14, L['snare']), (15, L['snare']+4)):
        p.put(b+r, CH_SN, DRUM_NOTE, 2, min(64, v))
    p.put(b+8, CH_OHAT, DRUM_NOTE, 4, L['ohat']-4)

def fill_stutter(p, bar=3):
    """machine-gun roll accelerating into the loop restart (E9x retrigger)"""
    b = bar*16
    p.put(b+8,  CH_SN, DRUM_NOTE, 2, L['snare']-8)
    p.put(b+10, CH_SN, DRUM_NOTE, 2, L['snare']-6)
    p.put(b+12, CH_SN, DRUM_NOTE, 2, L['snare']-4, eff=14, prm=0x93)
    p.put(b+14, CH_SN, DRUM_NOTE, 2, L['snare']-2, eff=14, prm=0x92)
    p.put(b+15, CH_SN, DRUM_NOTE, 2, L['snare'],   eff=14, prm=0x91)
    p.put(b+8,  CH_OHAT, DRUM_NOTE, 4, L['ohat']-4)

def crash(p, row=0, dv=0):
    p.put(row, CH_OHAT, DRUM_NOTE, 4, min(64, L['ohat']+6+dv))

def bass_eighth(p, chord, bar, pickup=None, dv=0):
    b = bar*16
    R = CHN[chord]['root']
    seq = [R, R, R+12, R, R, R+12, R, R+12]
    for i, r in enumerate(range(0, 16, 2)):
        p.put(b+r, CH_BASS, seq[i], 5, L['bass']+dv if i % 4 == 0 else L['bass']-4+dv)
    if pickup is not None:
        p.put(b+15, CH_BASS, pickup, 5, L['bass']-6)

def bass_sixteenth(p, chord, bar, dv=0):
    b = bar*16
    R = CHN[chord]['root']
    for i, r in enumerate(range(16)):
        n = R if i % 4 != 3 else R+12
        p.put(b+r, CH_BASS, n, 5, (L['bass']+dv) if i % 4 == 0 else L['bass']-7+dv)

def bass_half(p, chord, bar):
    b = bar*16
    R = CHN[chord]['root']
    p.put(b+0,  CH_BASS, R, 5, L['bass'])
    p.put(b+8,  CH_BASS, R, 5, L['bass']-6)

def arp_part(p, chord, bar, style='8th', dv=0):
    b = bar*16
    notes = CHN[chord]['arp']
    seq = ARP_SEQ16 if style == '16th' else ARP_SEQ8
    rows = range(16) if style == '16th' else range(0, 16, 2)
    for i, r in enumerate(rows):
        v = L['arp']+dv if i % 2 == 0 else L['arp']-3+dv
        p.put(b+r, CH_ARP, notes[seq[i]], 6, v)

def pad_chord(p, chord, bar, dv=0):
    b = bar*16
    for j, n in enumerate(CHN[chord]['pad']):
        p.put(b, CH_PAD[j], n, 7+j, L['pad']+dv)
    for ch in CH_PAD:
        p.put(b+13, ch, vol=int((L['pad']+dv)*0.72))
        p.put(b+14, ch, vol=int((L['pad']+dv)*0.46))
        p.put(b+15, ch, vol=int((L['pad']+dv)*0.20))

def pad_stop(p, bar=3):
    """kill the pad tail so it does not drone into pad-less patterns"""
    for ch in CH_PAD:
        p.put(bar*16+14, ch, vol=6)
        p.put(bar*16+15, ch, vol=0, note=97)

def mel_part(p, bars, ch, ins, vol, stop=False, dv=0):
    """bars: list per bar of (row, notename, dur_rows)."""
    events = []
    for bi, mel in enumerate(bars):
        for (r, name, dur) in mel:
            events.append((bi*16+r, nm(name) if isinstance(name, str) else name, dur))
    prev_on = prev_end = None
    for row, note, dur in events:
        if prev_end is not None and prev_end == row:      # fade out old note
            fs = max(prev_on+1, row-2)
            n = row - fs
            for i2, r in enumerate(range(fs, row)):
                p.put(r, ch, vol=int(vol*(0.66-0.50*(i2+1)/n)))
        p.put(row, ch, note, ins, vol)
        prev_on, prev_end = row, row+dur
    if prev_end is not None:                              # phrase tail
        end = min(64, prev_end)
        fs = max(prev_on+1, end-3)
        n = end - fs
        for i2, r in enumerate(range(fs, end)):
            p.put(r, ch, vol=int(vol*(0.66-0.50*(i2+1)/n)))
        if stop:
            p.put(min(end, 63), ch, note=97)

def lead_part(p, bars, dv=0, stop=False):
    mel_part(p, bars, CH_LEAD, 10, L['lead']+dv, stop=stop)

def harmonize(mel, chord):
    """chord-tone harmony 3-9 semitones below each melody note"""
    tones = CHN[chord]['arp']
    opts = [t-24 for t in tones] + [t-12 for t in tones] + list(tones)
    out = []
    for (r, name, dur) in mel:
        n = nm(name) if isinstance(name, str) else name
        below = [t for t in opts if 3 <= n-t <= 9]
        out.append((r, max(below) if below else n-5, dur))
    return out

def bell_ping(p, chord, bar, dv=0):
    p.put(bar*16, CH_BELL, CHN[chord]['arp'][3], 11, L['bell']+dv)

def bell_sparkle(p, chord, bar, dv=0):
    b = bar*16
    notes = CHN[chord]['arp']
    seq = [notes[3], notes[1]+12, notes[2]+12, notes[1]+12]
    for i, r in enumerate((2, 6, 10, 14)):
        p.put(b+r, CH_BELL, seq[i], 11, L['bell']+dv-(2 if i % 2 else 0))

def bell_musicbox(p, chord, bar, dv=0):
    b = bar*16
    notes = [n+24 for n in CHN[chord]['pad']]
    seq = [notes[0], notes[1], notes[2], notes[1]]*2
    for i, r in enumerate(range(0, 16, 2)):
        p.put(b+r, CH_BELL, seq[i], 11, L['bell']+dv-(3 if i % 2 else 0))

# ------------------------------------------------------------------ melodies
MEL_A = [
 [(0,'D-5',3),(3,'F-5',3),(6,'A-5',2),(8,'D-6',3),(11,'A-5',3),(14,'F-5',2)],
 [(0,'F-5',6),(6,'D-5',4),(10,'C-5',2),(12,'D-5',2),(14,'F-5',2)],
 [(0,'A-5',3),(3,'G-5',3),(6,'F-5',2),(8,'C-5',3),(11,'F-5',3),(14,'A-5',2)],
 [(0,'E-5',4),(4,'G-5',4),(8,'A-5',2),(10,'G-5',2),(12,'E-5',4)],
]
MEL_A2 = [
 [(0,'A-5',3),(3,'F-5',3),(6,'D-5',2),(8,'F-5',3),(11,'A-5',3),(14,'D-6',2)],
 [(0,'Bb-5',6),(6,'G-5',4),(10,'F-5',2),(12,'D-5',2),(14,'F-5',2)],
 [(0,'G-5',3),(3,'Bb-5',3),(6,'D-6',2),(8,'Bb-5',3),(11,'G-5',3),(14,'D-5',2)],
 [(0,'E-5',4),(4,'C#-5',4),(8,'A-4',4),(12,'C#-5',4)],
]
MEL_B = [
 [(0,'A-5',4),(4,'C-6',4),(8,'F-5',2),(10,'G-5',2),(12,'A-5',4)],
 [(0,'G-5',4),(4,'E-5',4),(8,'C-6',2),(10,'D-6',2),(12,'C-6',4)],
 [(0,'D-6',6),(6,'C-6',2),(8,'A-5',2),(10,'F-5',2),(12,'D-5',4)],
 [(0,'Bb-5',3),(3,'A-5',3),(6,'G-5',2),(8,'F-5',4),(12,'D-5',4)],
 [(0,'G-5',4),(4,'Bb-5',4),(8,'D-6',4),(12,'Bb-5',2),(14,'A-5',2)],
 [(0,'A-5',4),(4,'G-5',2),(6,'E-5',2),(8,'C#-5',4),(12,'E-5',2),(14,'G-5',2)],
 [(0,'D-6',4),(4,'A-5',4),(8,'F-5',4),(12,'D-5',4)],
 [(0,'D-5',6),(6,'E-5',2),(8,'F-5',2),(10,'G-5',2),(12,'A-5',2),(14,'Bb-5',2)],
]
MEL_B_RUN = [(0,'D-5',2),(2,'E-5',2),(4,'F-5',2),(6,'A-5',2),(8,'Bb-5',2),
             (10,'C#-5',2),(12,'D-6',4)]
MEL_TURN = [
 [(0,'A-5',4),(4,'F-5',4),(8,'D-5',8)],
 [(0,'D-5',2),(2,'E-5',2),(4,'F-5',2),(6,'A-5',2),(8,'D-6',8)],
 [(0,'D-6',4),(4,'Bb-5',4),(8,'F-5',8)],
 [(0,'E-5',4),(4,'C#-5',4),(8,'A-4',4),(12,'C#-5',4)],
]

# ------------------------------------------------------------------ patterns
def pat_P0():
    p = Pat(0); chs = ['Dm','Dm','Bb','C']
    # bar0: sparse
    p.put(0, CH_KICK, DRUM_NOTE, 1, L['kick']-4); p.put(8, CH_KICK, DRUM_NOTE, 1, L['kick']-4)
    for r in (2,6,10,14): p.put(r, CH_HAT, DRUM_NOTE, 3, L['hat']-4)
    arp_part(p, 'Dm', 0, '8th', dv=-8)
    bell_ping(p, 'Dm', 0, dv=-2)
    # bar1
    p.put(16, CH_KICK, DRUM_NOTE, 1, L['kick']-2); p.put(24, CH_KICK, DRUM_NOTE, 1, L['kick']-2)
    p.put(20, CH_SN, DRUM_NOTE, 2, L['snare']-6); p.put(28, CH_SN, DRUM_NOTE, 2, L['snare']-6)
    for r in (2,6,10,14): p.put(16+r, CH_HAT, DRUM_NOTE, 3, L['hat']-2)
    arp_part(p, 'Dm', 1, '8th', dv=-4)
    bell_ping(p, 'Dm', 1)
    # bar2 (Bb): busier, bass + pad enter
    p.put(32, CH_KICK, DRUM_NOTE, 1, L['kick']); p.put(38, CH_KICK, DRUM_NOTE, 1, L['kick']-4)
    p.put(40, CH_KICK, DRUM_NOTE, 1, L['kick'])
    p.put(36, CH_SN, DRUM_NOTE, 2, L['snare']-2); p.put(44, CH_SN, DRUM_NOTE, 2, L['snare']-2)
    for r in range(0,16,2): p.put(32+r, CH_HAT, DRUM_NOTE, 3, L['hat']-(2 if r % 4 else 0))
    arp_part(p, 'Bb', 2, '16th', dv=-3)
    bass_eighth(p, 'Bb', 2, dv=-3)
    pad_chord(p, 'Bb', 2, dv=-2)
    # bar3 (C): full, fill
    beat_full(p, 3)
    arp_part(p, 'C', 3, '16th')
    bass_eighth(p, 'C', 3)
    pad_chord(p, 'C', 3, dv=-2)
    fill_snare(p, 3)
    pad_stop(p, 3)
    return p

def pat_P1():
    p = Pat(1); chs = ['Dm','Bb','F','C']
    for bar, c in enumerate(chs):
        beat_groove(p, bar, kick2=(bar == 3))
        arp_part(p, c, bar, '8th')
        bass_eighth(p, c, bar)
        if bar in (0, 2): bell_ping(p, c, bar, dv=-3)
    fill_snare(p, 3)
    return p

def pat_P2():
    p = Pat(2); chs = ['Dm','Bb','F','C']
    for bar, c in enumerate(chs):
        beat_groove(p, bar, kick2=(bar == 3))
        arp_part(p, c, bar, '8th', dv=2)
        bass_eighth(p, c, bar)
    lead_part(p, MEL_A, dv=0)
    fill_snare(p, 3)
    return p

def pat_P3():
    p = Pat(3); chs = ['Dm','Bb','Gm','A7']
    for bar, c in enumerate(chs):
        beat_groove(p, bar, kick2=True)
        arp_part(p, c, bar, '16th', dv=1)
        bass_eighth(p, c, bar, pickup=(nm('C#-2') if c == 'A7' else None))
    lead_part(p, MEL_A2, dv=2)
    fill_snare(p, 3)
    return p

def pat_P4():
    p = Pat(4); chs = ['F','C','Dm','Bb']
    crash(p, 0)
    for bar, c in enumerate(chs):
        beat_full(p, bar)
        arp_part(p, c, bar, '16th', dv=3)
        bass_eighth(p, c, bar)
        pad_chord(p, c, bar, dv=3)
        bell_sparkle(p, c, bar, dv=1)
    lead_part(p, MEL_B[0:4], dv=3)
    return p

def pat_P5():
    p = Pat(5); chs = ['Gm','A7','Dm','Dm']
    crash(p, 0)
    for bar, c in enumerate(chs):
        beat_full(p, bar)
        arp_part(p, c, bar, '16th', dv=3)
        bass_eighth(p, c, bar, pickup=(nm('C#-2') if c == 'A7' else None))
        pad_chord(p, c, bar, dv=3)
        bell_sparkle(p, c, bar, dv=1)
    mel = MEL_B[4:7] + [MEL_B_RUN]
    lead_part(p, mel, dv=3, stop=True)
    fill_snare(p, 3)
    return p

def pat_P6():
    p = Pat(6); chs = ['Dm','C','Bb','A7']
    for bar, c in enumerate(chs):
        beat_half(p, bar)
        arp_part(p, c, bar, '8th', dv=-6)
        bass_half(p, c, bar)
        pad_chord(p, c, bar, dv=6)
        bell_musicbox(p, c, bar, dv=2)
    return p

def pat_P7():
    p = Pat(7); chs = ['Dm','Dm','Gm','A7']
    for bar, c in enumerate(chs):
        beat_build(p, bar)
        if bar < 2:
            arp_part(p, c, bar, '16th', dv=-2+bar*2)
            bass_eighth(p, c, bar) if bar == 0 else bass_sixteenth(p, c, bar)
        else:
            arp_part(p, c, bar, '16th', dv=2+bar)
            bass_sixteenth(p, c, bar, dv=2)
        pad_chord(p, c, bar, dv=2)
        bell_musicbox(p, c, bar, dv=-2+bar*3)
    p.put(28, CH_SWEEP, DRUM_NOTE, 12, L['sweep'])
    return p

def pat_P8():
    p = Pat(8); chs = ['Dm','Dm','Bb','A7']
    for bar, c in enumerate(chs):
        beat_full(p, bar)
        arp_part(p, c, bar, '16th', dv=1)
        bass_eighth(p, c, bar, pickup=(nm('C#-2') if c == 'A7' else None))
        pad_chord(p, c, bar, dv=2)
        if bar in (0, 2): bell_ping(p, c, bar)
    lead_part(p, MEL_TURN, dv=1, stop=True)
    fill_stutter(p, 3)
    pad_stop(p, 3)
    return p

def pat_P9():
    p = Pat(9); chs = ['F','C','Dm','Bb']
    crash(p, 0)
    for bar, c in enumerate(chs):
        beat_full(p, bar)
        arp_part(p, c, bar, '16th', dv=3)
        bass_eighth(p, c, bar)
        pad_chord(p, c, bar, dv=3)
        bell_sparkle(p, c, bar, dv=1)
    lead_part(p, MEL_B[0:4], dv=3)
    mel_part(p, [harmonize(MEL_B[i], chs[i]) for i in range(4)],
             CH_HARM, 13, L['harm'], stop=True)
    return p

def pat_P10():
    p = Pat(10); chs = ['Gm','A7','Dm','Dm']
    crash(p, 0)
    for bar, c in enumerate(chs):
        beat_full(p, bar)
        arp_part(p, c, bar, '16th', dv=3)
        bass_eighth(p, c, bar, pickup=(nm('C#-2') if c == 'A7' else None))
        pad_chord(p, c, bar, dv=3)
        bell_sparkle(p, c, bar, dv=1)
    mel = MEL_B[4:7] + [MEL_B_RUN]
    lead_part(p, mel, dv=3, stop=True)
    mel_part(p, [harmonize(mel[i], chs[i]) for i in range(4)],
             CH_HARM, 13, L['harm'], stop=True)
    fill_snare(p, 3)
    return p

ORDER = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 8]   # 11 positions, loop starts at 1

# ------------------------------------------------------------------ build
WAVDIR = WS + '/t/wav'

def write_wav(path, pcm, base_note):
    """declare a wav 'sample rate' so that `base_note` plays the data at 44100"""
    rate = int(round(SR * 2.0**((49 - base_note)/12.0)))
    with open(path, 'wb') as f:
        f.write(b'RIFF')
        n = (len(pcm)*2)
        f.write((36+n).to_bytes(4, 'little'))
        f.write(b'WAVEfmt ')
        f.write((16).to_bytes(4, 'little'))
        f.write((1).to_bytes(2, 'little'))     # PCM
        f.write((1).to_bytes(2, 'little'))     # mono
        f.write(rate.to_bytes(4, 'little'))
        f.write((rate*2).to_bytes(4, 'little'))
        f.write((2).to_bytes(2, 'little'))
        f.write((16).to_bytes(2, 'little'))
        f.write(b'data')
        f.write(n.to_bytes(4, 'little'))
        f.write(pcm.tobytes())
    return rate

def build():
    smp = SMP.build_all()
    os.makedirs(WAVDIR, exist_ok=True)
    ft('module_new', {'channels': 12, 'name': TITLE})
    ft('song_set', {'name': TITLE, 'bpm': 150, 'speed': 6,
                    'length': len(ORDER), 'loop_start': 1, 'channels': 12})
    calls = []
    for (num, sname, base, pan, iname) in INSTR:
        data = smp['pad'] if sname.startswith('pad') else smp[sname]
        path = '%s/i%02d_%s.wav' % (WAVDIR, num, sname)
        rate = write_wav(path, data['pcm'], base)
        calls.append(('sample_load', {'path': path, 'instrument': num, 'sample': 0}))
        a = {'instrument': num, 'sample': 0, 'volume': 64, 'panning': pan,
             'loop_start': 0, 'loop_length': 0}
        if data['loop']:
            a['loop_start'] = int(data['loop'][0])
            a['loop_length'] = int(data['loop'][1])
            a['flags'] = 17
        calls.append(('sample_set', a))
        calls.append(('instrument_set', {'instrument': num, 'name': iname}))
    pats = [pat_P0(), pat_P1(), pat_P2(), pat_P3(), pat_P4(),
            pat_P5(), pat_P6(), pat_P7(), pat_P8(), pat_P9(), pat_P10()]
    for p in pats:
        calls.extend(p.calls())
    for pos, pn in enumerate(ORDER):
        calls.append(('order_set', {'position': pos, 'pattern': pn}))
    calls.append(('song_set', {'name': TITLE, 'bpm': 150, 'speed': 6,
                               'length': len(ORDER), 'loop_start': 1, 'channels': 12}))
    print('total batch calls:', len(calls))
    for i in range(0, len(calls), 300):
        batch(calls[i:i+300])
    ft('module_save', {'path': WS + '/submission/tune.xm', 'format': 'xm'})
    print('saved', WS + '/submission/tune.xm')

if __name__ == '__main__':
    build()

# ------------------------------------------------------------------ dump
NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nname(n):
    if n == 97: return '==='
    if n == 0: return '...'
    return '%s%d' % (NOTE_NAMES[(n-1) % 12], (n-1)//12)

def dump(p, chans=range(12)):
    hdr = '     ' + ''.join('%-9s' % ('CH%d' % c) for c in chans)
    print(hdr)
    for row in range(64):
        line = '%03d  ' % row
        for ch in chans:
            c = p.cells.get((row, ch), {})
            n = nname(c.get('note', 0)) if c.get('note') else '...'
            i = ('%02d' % c['ins']) if 'ins' in c else '--'
            v = ('%02d' % c['vol']) if 'vol' in c else '--'
            e = ''
            if 'eff' in c: e = '%X%02X' % (c['eff'], c.get('prm', 0))
            line += '%s%s%s%s ' % (n, i, v, e.ljust(3))
        print(line)

def dump_all():
    for f in (pat_P0, pat_P1, pat_P2, pat_P3, pat_P4, pat_P5, pat_P6, pat_P7, pat_P8):
        p = f()
        print('=== PATTERN %d ===' % p.num)
        dump(p)
