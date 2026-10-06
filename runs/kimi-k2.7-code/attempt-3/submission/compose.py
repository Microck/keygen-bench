import json

batch = []
def cell(pattern, row, channel, **kwargs):
    args = {"pattern": pattern, "row": row, "channel": channel}
    args.update(kwargs)
    batch.append({"name":"pattern_set_cell", "arguments": args})

def drums(pat, full=False, hat=True):
    for r in [0,16,32,48]:
        cell(pat, r, 0, note="C-4", instrument=1, volume=26)
    if full:
        for r in [8,24,40,56]:
            cell(pat, r, 1, note="C-4", instrument=2, volume=26)
    if hat:
        for r in range(4,64,4):
            cell(pat, r, 2, note="C-4", instrument=3, volume=26)

def measure_bass(pat, start, seq, vol=26):
    for i,n in enumerate(seq):
        cell(pat, start+i*4, 3, note=n, instrument=4, volume=vol)
        cell(pat, start+i*4+2, 3, note=n, instrument=4, volume=vol-6)

def lead_notes(pat, notes, vol=38):
    for r,n in notes:
        cell(pat, r, 4, note=n, instrument=5, volume=vol)

def arp_line(pat, notes, vol=26):
    for r,n,arp in notes:
        cell(pat, r, 5, note=n, instrument=6, volume=vol, effect=0, effect_param=arp)

def pad_chord(pat, chord, vol=22):
    root, root5 = chord
    cell(pat, 0, 6, note=root, instrument=7, volume=vol)
    cell(pat, 0, 7, note=root5, instrument=7, volume=vol)

chords = {
    'Am': ('A2','E3'),
    'F': ('F2','C3'),
    'C': ('C3','G3'),
    'G': ('G2','D3'),
    'Dm': ('D2','A2'),
    'E': ('E2','B2'),
}

# Pattern 0 intro
drums(0, full=False, hat=True)
cell(0,32,3,note='A2',instrument=4,volume=26)
cell(0,40,3,note='E2',instrument=4,volume=26)

# Pattern 1 build
drums(1, full=True, hat=True)
measure_bass(1,0,['A2','A2','C3','E2'])
measure_bass(1,32,['G2','G2','B2','D3'])
lead_notes(1, [(24,'E5'),(28,'G5'),(32,'A5'),(40,'B5'),(56,'C6')], vol=26)

# Pattern 2 loop A
for p in [2,4,6]:
    drums(p, full=True, hat=True)
    measure_bass(p,0,['A2','A2','C3','E2'])
    measure_bass(p,16,['F2','F2','A2','C3'])
    measure_bass(p,32,['C2','C2','E2','G2'])
    measure_bass(p,48,['G2','G2','B2','D3'])

def lead_A(pat):
    n = [
        (0,'A5'),(2,'E5'),(4,'A5'),(6,'B5'),
        (8,'C6'),(10,'B5'),(12,'A5'),(14,'G5'),
        (16,'F5'),(18,'C5'),(20,'F5'),(22,'A5'),
        (24,'G5'),(26,'F5'),(28,'E5'),(30,'D5'),
        (32,'E5'),(34,'C5'),(36,'E5'),(38,'G5'),
        (40,'A5'),(42,'G5'),(44,'E5'),(46,'C5'),
        (48,'B4'),(50,'D5'),(52,'E5'),(54,'G5'),
        (56,'A5'),(58,'B5'),(60,'C6'),(62,'E6'),
    ]
    lead_notes(pat, n)
lead_A(2); lead_A(4); lead_A(6)

def arp_A(pat):
    arp=[]
    for m,base,ap in [(0,'A4',0x37),(1,'F4',0x47),(2,'C4',0x47),(3,'G4',0x37)]:
        for i in range(8):
            arp.append((m*16+i*2, base, ap))
    arp_line(pat, arp)
arp_A(2); arp_A(4); arp_A(6)

for p in [2,4,6]:
    for m,ch in enumerate(['Am','F','C','G']):
        pad_chord(p, chords[ch])

# Pattern 3 loop B
for p in [3,5]:
    drums(p, full=True, hat=True)
    measure_bass(p,0,['D2','D2','F2','A2'])
    measure_bass(p,16,['G2','G2','B2','D3'])
    measure_bass(p,32,['C2','C2','E2','G2'])
    measure_bass(p,48,['E2','E2','G#2','B2'])

def lead_B(pat):
    n = [
        (0,'D5'),(1,'F5'),(2,'A5'),(3,'C6'),
        (4,'A5'),(6,'F5'),(8,'D5'),(10,'A4'),
        (12,'G4'),(14,'B4'),(16,'D5'),(18,'G5'),
        (20,'B5'),(22,'D6'),(24,'B5'),(26,'G5'),
        (28,'D5'),(30,'B4'),
        (32,'C5'),(33,'E5'),(34,'G5'),(35,'C6'),
        (36,'G5'),(38,'E5'),(40,'C5'),(42,'G4'),
        (44,'E4'),(46,'G4'),(48,'B4'),(50,'E5'),
        (52,'G#5'),(54,'B5'),(56,'E6'),(58,'B5'),(60,'G#5'),(62,'E5'),
    ]
    lead_notes(pat, n)
lead_B(3); lead_B(5)

def arp_B(pat):
    arp=[]
    for m,base,ap in [(0,'D4',0x37),(1,'G4',0x37),(2,'C4',0x47),(3,'E4',0x47)]:
        for i in range(8):
            arp.append((m*16+i*2, base, ap))
    arp_line(pat, arp)
arp_B(3); arp_B(5)

for p in [3,5]:
    for m,ch in enumerate(['Dm','G','C','E']):
        pad_chord(p, chords[ch])

# Pattern 7 transition/outro
drums(7, full=True, hat=True)
measure_bass(7,0,['A2','A2','C3','E2'])
measure_bass(7,16,['F2','F2','A2','C3'])
measure_bass(7,32,['G2','G2','B2','D3'])
for i,n in enumerate(['E2','D2','C2','A1']):
    cell(7,48+i*4,3,note=n,instrument=4,volume=26)
    cell(7,48+i*4+2,3,note=n,instrument=4,volume=34)
lead_notes(7, [
    (0,'A5'),(2,'E5'),(4,'C5'),(6,'A4'),
    (8,'F5'),(10,'C5'),(12,'A4'),(14,'F4'),
    (16,'G4'),(18,'B4'),(20,'D5'),(22,'G5'),
    (24,'F5'),(26,'E5'),(28,'D5'),(30,'C5'),
    (32,'B4'),(34,'C5'),(36,'D5'),(38,'E5'),
    (40,'A4'),(42,'B4'),(44,'C5'),(46,'D5'),
    (48,'E5'),(50,'G5'),(52,'A5'),(54,'C6'),
    (56,'B5'),(58,'A5'),(60,'G5'),(62,'E5'),
])
arp_7=[]
for m,base,ap in [(0,'A4',0x37),(1,'F4',0x47),(2,'G4',0x37),(3,'A4',0x47)]:
    for i in range(8):
        arp_7.append((m*16+i*2, base, ap))
arp_line(7, arp_7)
for m,ch in enumerate(['Am','F','G','Am']):
    pad_chord(7, chords[ch])

for pos,pat in enumerate([0,1,2,3,4,5,6,7]):
    batch.append({"name":"order_set","arguments":{"position":pos,"pattern":pat}})

with open('compose_batch.json','w') as f:
    json.dump(batch, f)
print("pattern batch entries:", len(batch))
