import json, sys, os

W = '/workspace/work'
NM = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def nn(s):
    s = s.strip()
    return NM.index(s[:-1]) + 12 * (int(s[-1]) - 1) + 1

SMP = os.listdir(f'{W}/smp')

# instruments
I_KICK, I_SNARE, I_HATC, I_HATO = 1, 2, 3, 4
I_BASS, I_LEAD, I_ARP, I_PAD, I_CRASH = 5, 6, 7, 8, 9
NAMES = {1:('kick',0),2:('snare',0),3:('hatc',0),4:('hato',0),5:('bass',32),
         6:('lead',32),7:('arp',32),8:('pad',64),9:('crash',0)}
REL = {5:0, 6:12, 7:12, 8:12}
DRUMNOTE = 78

calls = []
VOLSCALE = 0.75

def cs(**kw):
    if 'volume' in kw and kw['volume']:
        kw['volume'] = max(1, int(round(kw['volume'] * VOLSCALE)))
    calls.append({"name": "pattern_set_cell", "arguments": kw})

def load_module():
    calls.append({"name":"module_new","arguments":{"name":"MIDNIGHT KEYGEN","channels":8}})
    calls.append({"name":"song_set","arguments":{"name":"MIDNIGHT KEYGEN","bpm":100,"speed":4,
                  "length":NPATT,"loop_start":LOOP0}})
    for p in range(NPATT):
        calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
        calls.append({"name":"order_set","arguments":{"position":p,"pattern":p}})
    for i in sorted(NAMES):
        nm, loop = NAMES[i]
        a = {"instrument": i, "sample": 0, "name": nm[:20],
             "loop_start": 0, "volume": 64, "panning": 128,
             "relative_note": REL.get(i, 0), "finetune": 0,
             "flags": 1 if loop else 0}
        if loop:
            a["loop_length"] = loop
        calls.append({"name":"sample_load","arguments":{"path":f'{W}/smp/{nm}.wav',
                  "instrument":i,"sample":0}})
        calls.append({"name":"sample_set","arguments":a})
        calls.append({"name":"instrument_set","arguments":{"instrument":i,
                     "name":nm.upper()[:20]}})

# ---------------- music data ----------------
CH = {
 'Am': dict(r=nn('A2'), pool=[nn('A3'),nn('C4'),nn('E4'),nn('A4')],
            arp=[nn('A3'),nn('E4'),nn('A4'),nn('C5'),nn('A4'),nn('E4'),
                 nn('C5'),nn('E5'),nn('A5'),nn('E5'),nn('C5'),nn('E5'),
                 nn('A5'),nn('E5'),nn('C5'),nn('A4')]),
 'F':  dict(r=nn('F2'), pool=[nn('F3'),nn('A3'),nn('C4'),nn('F4')],
            arp=[nn('F3'),nn('C4'),nn('F4'),nn('A4'),nn('C5'),nn('A4'),
                 nn('F4'),nn('C4'),nn('A4'),nn('C5'),nn('F5'),nn('C5'),
                 nn('A4'),nn('C5'),nn('F5'),nn('C5')]),
 'C':  dict(r=nn('C3'), pool=[nn('C4'),nn('E4'),nn('G4'),nn('C5')],
            arp=[nn('C4'),nn('G4'),nn('C5'),nn('E5'),nn('G5'),nn('E5'),
                 nn('C5'),nn('G4'),nn('E4'),nn('G4'),nn('C5'),nn('E5'),
                 nn('G5'),nn('E5'),nn('C5'),nn('G4')]),
 'G':  dict(r=nn('G2'), pool=[nn('G3'),nn('B3'),nn('D4'),nn('G4')],
            arp=[nn('G3'),nn('D4'),nn('G4'),nn('B4'),nn('D5'),nn('B4'),
                 nn('G4'),nn('D4'),nn('B3'),nn('D4'),nn('G4'),nn('B4'),
                 nn('D5'),nn('B4'),nn('G4'),nn('D4')]),
 'Dm': dict(r=nn('D3'), pool=[nn('D4'),nn('F4'),nn('A4'),nn('D5')],
            arp=[nn('D4'),nn('A4'),nn('D5'),nn('F5'),nn('A5'),nn('F5'),
                 nn('D5'),nn('A4'),nn('F4'),nn('A4'),nn('D5'),nn('F5'),
                 nn('A5'),nn('F5'),nn('D5'),nn('A4')]),
 'E':  dict(r=nn('E2'), pool=[nn('E3'),nn('G#3'),nn('B3'),nn('E4')],
            arp=[nn('E4'),nn('B4'),nn('E5'),nn('G#5'),nn('B5'),nn('G#5'),
                 nn('E5'),nn('B4'),nn('G#4'),nn('B4'),nn('E5'),nn('G#5'),
                 nn('B5'),nn('G#5'),nn('E5'),nn('B4')]),
}

HOOK = [
 [('A5',0),('G5',2),('E5',4),('D5',6),('C5',8),('E5',10),('A5',12)],
 [('G5',0),('F5',2),('C5',4),('F5',6),('G5',8),('A5',10),('C5',12)],
 [('C5',0),('E5',2),('G5',4),('E5',6),('C5',8),('E5',10),('G5',12),('A5',14)],
 [('B4',0),('D5',2),('G5',4),('D5',6),('B4',8),('D5',10),('G5',12),('B4',14)],
]
HOOK2 = [
 [('E5',0),('A5',2),('G5',4),('E5',6),('D5',8),('C5',10),('A4',12)],
 [('F5',0),('C5',2),('A4',4),('C5',6),('F5',8),('G5',10),('A5',12)],
 [('E5',0),('G5',2),('C6',4),('G5',6),('E5',8),('C5',10),('G5',12)],
 [('D5',0),('G5',2),('B5',4),('G5',6),('D5',8),('B4',10),('G5',12),('E5',14)],
]

def kickbar(p, row0, rows):
    for r in rows: cs(pattern=p, row=row0+r, channel=0, note=DRUMNOTE,
                      instrument=I_KICK, volume=64)

def snarebar(p, row0, rows, inst=I_SNARE, vol=64):
    for r in rows: cs(pattern=p, row=row0+r, channel=1, note=DRUMNOTE,
                      instrument=inst, volume=vol)

def hatbar(p, row0, rows, inst=I_HATC, vol=52):
    for r in rows: cs(pattern=p, row=row0+r, channel=2, note=DRUMNOTE,
                      instrument=inst, volume=vol)

def bassbar(p, row0, ch, root, style, vol=58):
    if style == 'a':   rows = [0,2,4,6,8,10,12,14]; oc=[0,0,12,0,0,0,12,0]
    elif style == 'b': rows = [0,1,2,3,4,6,8,9,10,11,12,14]; oc=[0,0,0,12,0,0,0,0,0,12,0,0]
    elif style == 'c': rows = [0,3,4,6,8,11,12,14]; oc=[0,0,12,0,0,0,12,0]
    elif style == 'd': rows = [0,4,8,12]; oc=[0,0,0,0]
    elif style == 'e': rows = list(range(16)); oc=[0,0,12,0]*4
    for r, o in zip(rows, oc):
        cs(pattern=p, row=row0+r, channel=ch, note=root+o, instrument=I_BASS,
           volume=vol)

def stabbar(p, row0, chd, rows, vol=56):
    pool = chd['pool']; notes=[pool[0], pool[1], pool[2], pool[3]]
    for i, r in enumerate(rows):
        cs(pattern=p, row=row0+r, channel=6, note=notes[i % 4], instrument=I_PAD,
           volume=vol)
        cs(pattern=p, row=row0+r, channel=7, note=notes[(i+1) % 4]+12,
           instrument=I_PAD, volume=vol)

def arpbar(p, row0, chd, vol=48):
    for k, n in enumerate(chd['arp']):
        cs(pattern=p, row=row0+k, channel=5, note=n, instrument=I_ARP, volume=vol)

def leadbar(p, row0, phrase, vol=58):
    for nm, r in phrase:
        cs(pattern=p, row=row0+r, channel=4, note=nn(nm), instrument=I_LEAD,
           volume=vol)

# ---------------- arrangement ----------------
NPATT = 12
LOOP0 = 1
PROG = [['Am','F','C','G'],['Am','F','C','G'],['Am','F','C','G'],
        ['Dm','G','C','Am'],['Am','F','C','G'],['C','G','Am','F'],
        ['Dm','Am','F','G'],['Am','F','C','G'],['C','G','Am','F'],
        ['Am','F','C','G'],['C','G','Am','F'],['Am','F','G','Am']]

def full(pat, row0, c, b, lead=None, bass='a', arp=True, kickrows=(0,4,8,12),
         leadvol=58,
         hatopen=True, stab=(0,6,10,12), kickv=64, snarv=62, hatv=64,
         arpv=44, stabv=50):
    kickbar(pat, row0, list(kickrows))
    snarebar(pat, row0, [4,12], vol=snarv)
    rows = list(range(0, 16, 2))
    hatbar(pat, row0, rows, vol=hatv)
    if hatopen:
        hatbar(pat, row0, [6, 14], inst=I_HATO, vol=58)
    bassbar(pat, row0, 3, c['r'], bass)
    stabbar(pat, row0, c, list(stab), vol=stabv)
    if arp: arpbar(pat, row0, c, vol=arpv)
    if lead: leadbar(pat, row0, lead[b], vol=leadvol)

def soft(pat, row0, c, b, lead=None, bass='c', arp=True):
    hatbar(pat, row0, list(range(0, 16, 2)), vol=44)
    bassbar(pat, row0, 3, c['r'], bass)
    stabbar(pat, row0, c, [0, 8], vol=44)
    if arp: arpbar(pat, row0, c, vol=40)
    if lead: leadbar(pat, row0, lead[b], vol=54)

def make():
    load_module()
    # p0 intro: 4 bar build
    for b in range(4):
        row0 = b * 16; c = CH[PROG[0][b]]
        hatbar(0, row0, [2, 6, 10, 14], vol=58)
        stabbar(0, row0, c, [0, 8], vol=46)
        if b >= 1: bassbar(0, row0, 3, c['r'], 'd', vol=52)
        if b == 3:
            kickbar(0, row0, [0, 4, 8, 12]); arpbar(0, row0, c, vol=42)
            snarebar(0, row0, [12], vol=54)
        elif b == 2:
            kickbar(0, row0, [0, 8])
    # p1 MAIN A1
    for b in range(4): full(1, b*16, CH[PROG[1][b]], b, lead=HOOK, leadvol=50)
    snarebar(1, 0, [0], inst=I_CRASH, vol=64)
    snarebar(2, 60, [12, 13, 14, 15], vol=56)
    snarebar(3, 60, [12, 13, 14, 15], vol=56)
    # p2 MAIN A2 with hook
    for b in range(4): full(2, b*16, CH[PROG[2][b]], b, lead=HOOK)
    # p3 BREAK
    for b in range(4): soft(3, b*16, CH[PROG[3][b]], b, lead=HOOK2, bass='c')
    # p4 MAIN B1: 16th bass, crash on bar0
    for b in range(4):
        full(4, b*16, CH[PROG[4][b]], b, bass='b' if b < 3 else 'a', lead=HOOK2, leadvol=52)
        if b == 0: snarebar(4, 0, [0], inst=I_CRASH, vol=64)
    # p5 MAIN B2: hook2 lead, different prog
    for b in range(4): full(5, b*16, CH[PROG[5][b]], b, lead=HOOK2, bass='b')
    snarebar(5, 0, [0], inst=I_CRASH, vol=64)
    snarebar(5, 60, [12, 13, 14, 15], vol=56)
    # p6 BREAK2
    for b in range(4): soft(6, b*16, CH[PROG[6][b]], b, lead=HOOK, bass='a')
    # p7 MAIN C1
    for b in range(4): full(7, b*16, CH[PROG[7][b]], b, lead=HOOK, bass='e')
    snarebar(7, 0, [0], inst=I_CRASH, vol=64)
        # arp brighter
    # p8 MAIN C2
    for b in range(4): full(8, b*16, CH[PROG[8][b]], b, lead=HOOK2, bass='e')
    # p9 MAIN D1
    for b in range(4): full(9, b*16, CH[PROG[9][b]], b, lead=HOOK, bass='b')
    snarebar(9, 0, [0], inst=I_CRASH, vol=64)
    # p10 MAIN D2
    for b in range(4): full(10, b*16, CH[PROG[10][b]], b, lead=HOOK2, bass='e')
    snarebar(10, 0, [0], inst=I_CRASH, vol=64)
    snarebar(10, 60, [12, 13, 14, 15], vol=56)
    # p11 OUTRO: 2 bars full, bar2 soft, bar3 fill
    full(11, 0, CH[PROG[11][0]], 0, bass='e')
    full(11, 16, CH[PROG[11][1]], 1, bass='b')
    soft(11, 32, CH[PROG[11][2]], 2, lead=HOOK2, bass='c')
    f = CH[PROG[11][3]]
    bassbar(11, 48, 3, f['r'], 'a', vol=56)
    stabbar(11, 48, f, [0, 8], vol=48)
    arpbar(11, 48, f, vol=42)
    leadbar(11, 48, HOOK2[3], vol=56)
    for r in [0,2,3,4,6,8,9,10,12,14,15]:
        cs(pattern=11, row=48+r, channel=1, note=DRUMNOTE, instrument=I_SNARE,
           volume=62)
    snarebar(11, 48, [0], inst=I_CRASH, vol=64)
    return calls

if __name__ == '__main__':
    calls = make()
    open(f'{W}/calls.json', 'w').write(json.dumps(calls))
    print('calls', len(calls))
