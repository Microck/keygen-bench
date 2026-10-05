import json

CH = {'kick':0,'snare':1,'hihat':2,'bass':3,'lead':4,'arp':5,'pad':6,'fx':7}
NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def note(n):
    name = n[:2]
    oct = int(n[2])
    return NOTE_NAMES.index(name) + oct*12

events = {}

def add(pat, row, ch, nt=None, ins=None, vol=None, eff=None, effp=None):
    events.setdefault(pat, []).append((row, ch, nt, ins, vol, eff, effp))

# Pattern 0 Intro
for row in range(0,64,4):
    if row >= 36:
        add(0, row, CH['hihat'], 'F-4', 3, 40)
for row in [0,16,32,48]:
    add(0, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(0, row, CH['snare'], 'C-2', 2)
for n,r in [('A-2',0),('F-2',16),('C-3',32),('G-2',48)]:
    add(0, r, CH['bass'], n, 4, 48)
    add(0, r+4, CH['bass'], None, None, None, 0xA, 0x0B)
for n,r in [('A-3',0),('F-3',16),('E-3',32),('G-3',48)]:
    add(0, r, CH['pad'], n, 7, 32)

# Pattern 1 Build
for row in range(0,64,4):
    add(1, row, CH['hihat'], 'F-4', 3, 36)
for row in [0,16,32,48]:
    add(1, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(1, row, CH['snare'], 'C-2', 2)
for n,r in [('A-2',0),('F-2',16),('C-3',32),('G-2',48)]:
    add(1, r, CH['bass'], n, 4, 48)
    add(1, r+4, CH['bass'], None, None, None, 0xA, 0x0B)
for bar,(root,base_r) in enumerate([('A-4',0),('F-4',16),('C-5',32),('G-4',48)]):
    for i in range(4):
        r = base_r + i*4
        add(1, r, CH['arp'], root, 6, 44, 0, 0x37)
lead1 = [('A-4',32),('C-5',34),('E-5',36),('D-5',38),('C-5',40),('A-4',42),('G-4',44),('A-4',46),
         ('G-4',48),('C-5',50),('E-5',52),('D-5',54),('C-5',56),('G-4',58),('F-4',60),('E-4',62)]
for n,r in lead1:
    add(1, r, CH['lead'], n, 5, 48)

# Pattern 2 Main A
for row in range(0,64,4):
    add(2, row, CH['hihat'], 'F-4', 3, 40 if row%8==0 else 28)
for row in [0,16,32,48]:
    add(2, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(2, row, CH['snare'], 'C-2', 2)
for n,r in [('A-2',0),('F-2',16),('C-3',32),('G-2',48)]:
    add(2, r, CH['bass'], n, 4, 52)
    add(2, r+4, CH['bass'], None, None, None, 0xA, 0x0B)
for bar,(root,base_r) in enumerate([('A-4',0),('F-4',16),('C-5',32),('G-4',48)]):
    for i in range(4):
        r = base_r + i*4
        add(2, r, CH['arp'], root, 6, 40, 0, 0x37)
lead2 = [('A-4',0),('C-5',2),('E-5',4),('D-5',6),('C-5',8),('A-4',10),('G-4',12),('A-4',14),
         ('G-4',16),('C-5',18),('E-5',20),('D-5',22),('C-5',24),('G-4',26),('F-4',28),('E-4',30),
         ('F-4',32),('A-4',34),('C-5',36),('D-5',38),('C-5',40),('A-4',42),('F-4',44),('E-4',46),
         ('E-4',48),('G-4',50),('B-4',52),('A-4',54),('G-4',56),('E-4',58),('D-4',60),('C-4',62)]
for n,r in lead2:
    add(2, r, CH['lead'], n, 5, 52)
for n,r in [('A-3',0),('F-3',16),('E-3',32),('G-3',48)]:
    add(2, r, CH['pad'], n, 7, 32)

# Pattern 3 Main A variation
for row in range(0,64,4):
    add(3, row, CH['hihat'], 'F-4', 3, 32 if row%8==4 else 24)
for row in [0,16,32,48]:
    add(3, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(3, row, CH['snare'], 'C-2', 2)
for n,r in [('A-2',0),('F-2',16),('C-3',32),('G-2',48)]:
    add(3, r, CH['bass'], n, 4, 52)
    add(3, r+4, CH['bass'], None, None, None, 0xA, 0x0A)
for bar,(root,base_r) in enumerate([('A-4',0),('F-4',16),('C-5',32),('G-4',48)]):
    for i in range(4):
        r = base_r + i*4
        add(3, r, CH['arp'], root, 6, 36, 0, 0x37)
lead3 = [('A-5',0),('C-6',2),('E-6',4),('D-6',6),('C-6',8),('A-5',10),('G-5',12),('A-5',14),
         ('G-5',16),('C-6',18),('E-6',20),('D-6',22),('C-6',24),('G-5',26),('F-5',28),('E-5',30),
         ('F-5',32),('A-5',34),('C-6',36),('D-6',38),('C-6',40),('A-5',42),('F-5',44),('E-5',46),
         ('E-5',48),('G-5',50),('B-5',52),('A-5',54),('G-5',56),('E-5',58),('D-5',60),('C-5',62)]
for n,r in lead3:
    add(3, r, CH['lead'], n, 5, 48)
for n,r in [('A-3',0),('F-3',16),('E-3',32),('G-3',48)]:
    add(3, r, CH['pad'], n, 7, 28)

# Pattern 4 Main B
bass4 = [('D-3',0),('A-2',16),('F-2',32),('C-3',48)]
pad4 = [('D-4',0),('A-3',16),('F-3',32),('E-4',48)]
for row in range(0,64,4):
    add(4, row, CH['hihat'], 'F-4', 3, 36)
for row in [0,16,32,48]:
    add(4, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(4, row, CH['snare'], 'C-2', 2)
for n,r in bass4:
    add(4, r, CH['bass'], n, 4, 52)
    add(4, r+4, CH['bass'], None, None, None, 0xA, 0x0B)
for bar,(root,base_r) in enumerate([('D-4',0),('A-3',16),('F-4',32),('C-5',48)]):
    for i in range(4):
        r = base_r + i*4
        add(4, r, CH['arp'], root, 6, 40, 0, 0x37)
lead4 = [('D-5',0),('F-5',2),('A-5',4),('G-5',6),('F-5',8),('D-5',10),('C-5',12),('D-5',14),
         ('C-5',16),('E-5',18),('A-5',20),('G-5',22),('E-5',24),('C-5',26),('B-4',28),('A-4',30),
         ('A-4',32),('C-5',34),('F-5',36),('G-5',38),('F-5',40),('C-5',42),('A-4',44),('G-4',46),
         ('G-4',48),('C-5',50),('E-5',52),('D-5',54),('C-5',56),('G-4',58),('F-4',60),('E-4',62)]
for n,r in lead4:
    add(4, r, CH['lead'], n, 5, 52)
for n,r in pad4:
    add(4, r, CH['pad'], n, 7, 32)

# Pattern 5 Breakdown
for row in [0,16,32,48]:
    add(5, row, CH['kick'], 'C-2', 1)
for row in [8,40]:
    add(5, row, CH['snare'], 'C-2', 2)
for row in range(56,64):
    add(5, row, CH['snare'], 'C-2', 2)
for row in [4,12,20,28,36,44,52,60]:
    add(5, row, CH['hihat'], 'F-4', 3, 24)
bass5 = [('E-2',0),('G-2',16),('D-3',32),('A-2',48)]
for n,r in bass5:
    add(5, r, CH['bass'], n, 4, 44)
pad5 = [('B-3',0),('D-4',16),('A-4',32),('C-5',48)]
for n,r in pad5:
    add(5, r, CH['pad'], n, 7, 28)
for bar,(root,base_r) in enumerate([('E-4',0),('G-4',16),('D-4',32),('A-4',48)]):
    for i in [0,2]:
        r = base_r + i*4
        add(5, r, CH['arp'], root, 6, 32, 0, 0x37)
lead5 = [('E-4',0),('G-4',8),('B-4',16),('D-5',24),('E-5',32),('G-5',40),('B-5',48),('E-6',56)]
for n,r in lead5:
    add(5, r, CH['lead'], n, 5, 40)
    add(5, r+2, CH['lead'], None, None, None, 0x4, 0x8A)

# Pattern 6 Main A return
for row in range(0,64,4):
    add(6, row, CH['hihat'], 'F-4', 3, 40)
for row in [0,16,32,48]:
    add(6, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(6, row, CH['snare'], 'C-2', 2)
add(6, 0, CH['fx'], 'C-2', 8, 32)
for n,r in [('A-2',0),('F-2',16),('C-3',32),('G-2',48)]:
    add(6, r, CH['bass'], n, 4, 56)
    add(6, r+4, CH['bass'], None, None, None, 0xA, 0x0B)
for bar,(root,base_r) in enumerate([('A-4',0),('F-4',16),('C-5',32),('G-4',48)]):
    for i in range(4):
        r = base_r + i*4
        add(6, r, CH['arp'], root, 6, 44, 0, 0x37)
for n,r in lead2:
    add(6, r, CH['lead'], n, 5, 56)
for n,r in [('A-3',0),('F-3',16),('E-3',32),('G-3',48)]:
    add(6, r, CH['pad'], n, 7, 34)

# Pattern 7 Main B climax
for row in range(0,64,4):
    add(7, row, CH['hihat'], 'F-4', 3, 44 if row%4==0 else 32)
for row in [0,16,32,48]:
    add(7, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(7, row, CH['snare'], 'C-2', 2)
for n,r in bass4:
    add(7, r, CH['bass'], n, 4, 56)
    add(7, r+4, CH['bass'], None, None, None, 0xA, 0x0B)
for bar,(root,base_r) in enumerate([('D-4',0),('A-3',16),('F-4',32),('C-5',48)]):
    for i in range(4):
        r = base_r + i*4
        add(7, r, CH['arp'], root, 6, 44, 0, 0x37)
lead7 = [('D-6',0),('F-6',2),('A-6',4),('G-6',6),('F-6',8),('D-6',10),('C-6',12),('D-6',14),
         ('C-6',16),('E-6',18),('A-6',20),('G-6',22),('E-6',24),('C-6',26),('B-5',28),('A-5',30),
         ('A-5',32),('C-6',34),('F-6',36),('G-6',38),('F-6',40),('C-6',42),('A-5',44),('G-5',46),
         ('G-5',48),('C-6',50),('E-6',52),('D-6',54),('C-6',56),('G-5',58),('F-5',60),('E-5',62)]
for n,r in lead7:
    add(7, r, CH['lead'], n, 5, 56)
for n,r in pad4:
    add(7, r, CH['pad'], n, 7, 34)

# Pattern 8 Outro
for row in [0,16,32,48]:
    add(8, row, CH['kick'], 'C-2', 1)
for row in [8,24,40,56]:
    add(8, row, CH['snare'], 'C-2', 2)
for row in range(0,64,8):
    add(8, row, CH['hihat'], 'F-4', 3, 24)
for n,r in [('A-2',0),('F-2',16),('C-3',32),('G-2',48)]:
    add(8, r, CH['bass'], n, 4, 44)
add(8, 0, CH['pad'], 'A-3', 7, 28)
add(8, 16, CH['pad'], 'F-3', 7, 28)
add(8, 32, CH['pad'], 'C-3', 7, 28)
add(8, 48, CH['pad'], 'A-3', 7, 28)
add(8, 56, CH['fx'], 'C-2', 8, 24)

# generate batch
batch = [{'name':'song_set','arguments':{'loop_start':2}}]
for pat in sorted(events.keys()):
    for (row,ch,nt,ins,vol,eff,effp) in events[pat]:
        cell = {'pattern':pat,'row':row,'channel':ch}
        if nt is not None:
            cell['note'] = nt
        if ins is not None:
            cell['instrument'] = ins
        if vol is not None:
            cell['volume'] = vol
        if eff is not None:
            cell['effect'] = eff
            cell['effect_param'] = effp
        batch.append({'name':'pattern_set_cell','arguments':cell})

with open('patterns.json','w') as f:
    json.dump(batch, f, indent=2)
print('total cells', len(batch))
