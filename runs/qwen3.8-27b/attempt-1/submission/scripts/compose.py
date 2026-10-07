import json

PC = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def midi(name):
    p, o = name.split('-')
    return 12*(int(o)+1) + PC[p]

SM = {'bass':45, 'arp':69, 'pad':57, 'lead':69, 'sub':33}
def nn(name, inst):
    return 46 + (midi(name) - SM[inst])

chords = {
 'Am': dict(bass='A-1', pass_='C-2', arp=['A-3','C-4','E-4','A-4'], pad=['A-2','C-3','E-3']),
 'F' : dict(bass='F-1', pass_='A-1', arp=['F-3','A-3','C-4','F-4'], pad=['F-2','A-2','C-3']),
 'C' : dict(bass='C-2', pass_='E-2', arp=['C-4','E-4','G-4','C-5'], pad=['C-3','E-3','G-3']),
 'G' : dict(bass='G-1', pass_='B-1', arp=['G-3','B-3','D-4','G-4'], pad=['G-2','B-2','D-3']),
}
PROG = ['Am','F','C','G']
def chord_at(gbar): return PROG[gbar % 4]

CH = dict(kick=0, snare=1, hat=2, openhat=3, bass=4, sub=5, arp=6, pad0=7, pad1=8, pad2=9, lead=10, riser=11)
INST = dict(kick=1, snare=2, hat=3, openhat=4, bass=5, sub=10, arp=6, pad=7, lead=8, riser=9)

calls = []
def setlen(pat, rows): calls.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":rows}})
def clear(pat): calls.append({"name":"pattern_clear","arguments":{"pattern":pat}})
def cell(pat, row, ch, note, inst, vol, effect=0, eparam=0):
    calls.append({"name":"pattern_set_cell","arguments":{"pattern":pat,"row":row,"channel":ch,
        "note":note,"instrument":inst,"volume":vol,"effect":effect,"effect_param":eparam}})

def drums(pat, bar, openhat=False, snare=True, hatvol=30):
    r = bar*16
    for b in (0,4,8,12):
        cell(pat, r+b, CH['kick'], 46, INST['kick'], 52)
    if snare:
        for b in (4,12):
            cell(pat, r+b, CH['snare'], 46, INST['snare'], 42)
    for b in range(0,16,2):
        cell(pat, r+b, CH['hat'], 46, INST['hat'], hatvol if b%4 else hatvol+6)
    if openhat:
        cell(pat, r+14, CH['openhat'], 46, INST['openhat'], 28)

def bass8(pat, bar, chord, oct_jump=False):
    r = bar*16
    c = chords[chord]
    root = nn(c['bass'],'bass')
    for i in range(8):
        row = r + i*2
        note = root
        if i == 7: note = nn(c['pass_'],'bass')
        elif oct_jump and i == 6: note = root + 12
        cell(pat, row, CH['bass'], note, INST['bass'], 48)

def sub8(pat, bar, chord):
    r = bar*16
    root = nn(chords[chord]['bass'],'sub')
    for i in range(8):
        cell(pat, r+i*2, CH['sub'], root, INST['sub'], 40)

def arp16(pat, bar, chord):
    r = bar*16
    seq = chords[chord]['arp']
    for i in range(16):
        note = nn(seq[i % 4], 'arp')
        vol = 38 if i % 4 == 0 else 32
        cell(pat, r+i, CH['arp'], note, INST['arp'], vol)

def pad_bar(pat, bar, chord, vol=28):
    r = bar*16
    for j, n in enumerate(chords[chord]['pad']):
        cell(pat, r, CH['pad0']+j, nn(n,'pad'), INST['pad'], vol)

def lead_bar(pat, bar, events):
    r = bar*16
    for (off, name, vol) in events:
        cell(pat, r+off, CH['lead'], nn(name,'lead'), INST['lead'], vol)

HOOK = [
 [(0,'A-4',50),(4,'C-4',44),(6,'E-4',44),(8,'A-4',50)],
 [(0,'G-4',50),(4,'E-4',44),(6,'D-4',44),(8,'C-4',46)],
 [(0,'A-3',46),(4,'C-4',44),(6,'E-4',44),(8,'G-4',50)],
 [(0,'E-4',48),(4,'D-4',44),(6,'C-4',44),(8,'A-3',46)],
]
HOOK2 = [
 [(0,'A-4',50),(4,'C-4',44),(6,'E-4',44),(8,'A-4',50),(12,'C-5',46)],
 [(0,'G-4',50),(4,'E-4',44),(6,'D-4',44),(8,'C-4',46)],
 [(0,'F-4',48),(4,'A-4',44),(6,'C-5',46),(8,'A-4',50)],
 [(0,'G-4',48),(4,'E-4',44),(6,'D-4',44),(8,'C-4',46)],
]

# P0 intro (8 bars): pad+arp, bass+sub enter bar4
clear(0); setlen(0,128)
for b in range(8):
    g=b
    pad_bar(0,b,chord_at(g))
    arp16(0,b,chord_at(g))
    if b>=4:
        bass8(0,b,chord_at(g)); sub8(0,b,chord_at(g))

# P1 main A (8 bars): full
clear(1); setlen(1,128)
for b in range(8):
    g=8+b
    drums(1,b,openhat=(b%2==1))
    bass8(1,b,chord_at(g),oct_jump=(b%2==1)); sub8(1,b,chord_at(g))
    arp16(1,b,chord_at(g)); pad_bar(1,b,chord_at(g))

# P2 main B (8 bars): drums+bass+lead+pad
clear(2); setlen(2,128)
for b in range(8):
    g=16+b
    drums(2,b,openhat=(b%2==1))
    bass8(2,b,chord_at(g)); sub8(2,b,chord_at(g))
    pad_bar(2,b,chord_at(g)); lead_bar(2,b,HOOK[b%4])

# P3 breakdown (8 bars): lead-focused, sparse drums, no sub
clear(3); setlen(3,128)
for b in range(8):
    g=24+b
    r=b*16
    for bb in range(0,16,2):
        cell(3,r+bb,CH['hat'],46,INST['hat'],18)
    cell(3,r,CH['kick'],46,INST['kick'],30)
    if b%2==1:
        cell(3,r+8,CH['kick'],46,INST['kick'],26)
    # lighter bass: root on quarters only
    root=nn(chords[chord_at(g)]['bass'],'bass')
    for q in range(4):
        cell(3,r+q*4,CH['bass'],root,INST['bass'],40)
    pad_bar(3,b,chord_at(g),vol=34); lead_bar(3,b,HOOK2[b%4])

# P4 build (4 bars): riser + snare roll + kick + rising bass
clear(4); setlen(4,64)
rise = ['A-1','A#-1','B-1','C-2','C#-2','D-2','D#-2','E-2','F-2','F#-2','G-2','G#-2','A-2','A#-2','B-2','C-3']
for b in range(4):
    g=32+b
    pad_bar(4,b,chord_at(g),vol=24)
    r=b*16
    for bb in (0,4,8,12):
        cell(4,r+bb,CH['kick'],46,INST['kick'],48)
    if b<2:
        for bb in range(0,16,2):
            cell(4,r+bb,CH['snare'],46,INST['snare'],18+10*b)
    else:
        for bb in range(0,16,2):
            cell(4,r+bb,CH['snare'],46,INST['snare'],34)
        for bb in (2,6,10,14):
            cell(4,r+bb,CH['snare'],46,INST['snare'],28)
    # rising bass line (quarter notes)
    for q in range(4):
        cell(4,r+q*4,CH['bass'],nn(rise[b*4+q],'bass'),INST['bass'],44)
cell(4,0,CH['riser'],46,INST['riser'],52)

# P5 main A2 (8 bars): full + openhat everywhere (the drop)
clear(5); setlen(5,128)
for b in range(8):
    g=36+b
    drums(5,b,openhat=True,hatvol=32)
    bass8(5,b,chord_at(g),oct_jump=True); sub8(5,b,chord_at(g))
    arp16(5,b,chord_at(g)); pad_bar(5,b,chord_at(g))

# P6 main B2 (8 bars): drums+bass+lead+pad
clear(6); setlen(6,128)
for b in range(8):
    g=44+b
    drums(6,b,openhat=(b%2==1))
    bass8(6,b,chord_at(g),oct_jump=(b%2==1)); sub8(6,b,chord_at(g))
    pad_bar(6,b,chord_at(g)); lead_bar(6,b,HOOK2[b%4])

# P7 outro (4 bars): pad+bass, end on Am
clear(7); setlen(7,64)
outro_chords=['Am','F','C','Am']
for b in range(4):
    pad_bar(7,b,outro_chords[b],vol=30)
    bass8(7,b,outro_chords[b]); sub8(7,b,outro_chords[b])
    r=b*16
    for bb in range(0,16,4):
        cell(7,r+bb,CH['hat'],46,INST['hat'],18)
    if b<3:
        for bb in (0,4,8,12):
            cell(7,r+bb,CH['kick'],46,INST['kick'],36)

order=[0,1,2,3,4,5,6,7]
for i,p in enumerate(order):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":p}})
calls.append({"name":"song_set","arguments":{"name":"Keygen","bpm":150,"speed":3,"length":len(order),"loop_start":0}})
open('/workspace/scripts/patterns.json','w').write(json.dumps(calls))
print("total cells:", len(calls))
