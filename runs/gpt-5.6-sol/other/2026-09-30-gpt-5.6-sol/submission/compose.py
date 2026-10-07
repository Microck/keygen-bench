import json, os
calls=[]
def call(name,**args): calls.append({'name':name,'arguments':args})
def cell(p,r,ch,note=None,inst=None,vol=None,fx=None,param=None):
    d={'pattern':p,'row':r,'channel':ch}
    if note is not None:d['note']=note
    if inst is not None:d['instrument']=inst
    if vol is not None:d['volume']=vol
    if fx is not None:d['effect']=fx
    if param is not None:d['effect_param']=param
    call('pattern_set_cell',**d)

def nt(n,octv): return f'{n}{octv}'
# conventional note strings flats avoided
# patterns 0 intro 32r, 1-9 are 64, 10 ending 32
for p in range(11):
    call('pattern_clear',pattern=p)
    call('pattern_set_length',pattern=p,rows=32 if p in (0,10) else 64)
    call('order_set',position=p,pattern=p)

# chord information: each item root, triad/pad, arp notes, bass motif notes
chords={
 'Bm':  (['B3','D4','F#4'], ['B4','F#5','D5','A5']),
 'G':   (['G3','B3','D4'],  ['G4','D5','B4','F#5']),
 'D':   (['D3','F#3','A3'], ['D4','A4','F#4','E5']),
 'A':   (['A3','C#4','E4'], ['A4','E5','C#5','B5']),
 'Em':  (['E3','G3','B3'],  ['E4','B4','G4','D5']),
 'F#m': (['F#3','A3','C#4'],['F#4','C#5','A4','E5']),
}
# Sections/chords by pattern, 4 chunks/pattern
prog={
 0:['Bm','Bm'], # intro half-chunks
 1:['Bm','G','D','A'],
 2:['Bm','G','D','A'],
 3:['Bm','G','D','A'],
 4:['Bm','G','D','A'],
 5:['Em','G','D','A'],
 6:['Em','G','Bm','A'],
 7:['G','A','F#m','Bm'],
 8:['G','A','F#m','Bm'],
 9:['Bm','G','D','A'],
 10:['Bm','G']
}
# Intro: atmospheric chord hits + motif tease and riser
# pad chord onset and explicit note-offs to make controlled phrasing
for idx,key in enumerate(prog[0]):
    st=idx*16
    tri=chords[key][0]
    for j,n in enumerate(tri): cell(0,st,3+j,n,4+j,21)
    # melodic bell sparkle
for r,n,v in [(0,'B5',24),(6,'F#5',20),(12,'D6',22),(16,'A5',21),(22,'B5',22),(28,'F#6',18)]:
    cell(0,r,9,n,12,v)
# filtered-feel pulse ticks
for r,n in [(8,'B4'),(12,'D5'),(20,'F#5'),(24,'A5')]:cell(0,r,8,n,10,25)
cell(0,0,12,'B3',3,28)
cell(0,16,12,'G3',3,30)
cell(0,24,15,'C4',20,24)
# kick heartbeat toward entry
for r,v in [(16,35),(24,42),(28,47)]:cell(0,r,10,'C4',13,v)
# tempo effect explicit only opening
cell(0,0,15,fx=15,param=150)
# chord note off before pattern end, except one-shot channels
for ch in [3,4,5,12]:cell(0,31,ch,'OFF')

# melodic material, relative names already in B minor / D major.
leadA=[
 ('B4',2),('D5',1),('F#5',1),('A5',2),('F#5',1),('D5',1),
 ('G5',2),('F#5',1),('D5',1),('B4',2),('D5',1),('E5',1),
 ('F#5',2),('A5',1),('D6',2),('C#6',1),('A5',1),('F#5',1),
 ('E5',2),('C#5',1),('A4',1),('C#5',1),('E5',1),('F#5',1),('A5',1)]
# each duration in 2-row units; totals 32 units = 64 rows verify
leadB=[
 ('D5',1),('F#5',1),('A5',2),('B5',1),('A5',1),('F#5',1),('D5',1),
 ('B4',1),('D5',1),('G5',2),('F#5',1),('E5',1),('D5',2),
 ('F#5',1),('A5',1),('D6',1),('E6',1),('D6',1),('A5',1),('F#5',2),
 ('E5',1),('C#5',1),('E5',1),('A5',1),('G5',1),('E5',1),('C#5',2)]
leadC=[
 ('B4',1),('D5',1),('F#5',1),('B5',1),('A5',1),('F#5',1),('D5',1),('F#5',1),
 ('G5',1),('B5',1),('D6',1),('B5',1),('A5',1),('G5',1),('F#5',1),('D5',1),
 ('A5',1),('F#5',1),('D6',1),('A5',1),('F#5',1),('E5',1),('D5',1),('A4',1),
 ('C#5',1),('E5',1),('A5',1),('B5',1),('A5',1),('E5',1),('C#5',1),('A4',1)]
leadBridge=[
 ('E5',2),('G5',1),('B5',1),('D6',2),('B5',1),('G5',1),
 ('D5',2),('G5',1),('B5',1),('A5',2),('F#5',1),('E5',1),
 ('F#5',2),('A5',1),('C#6',1),('E6',2),('C#6',1),('A5',1),
 ('E5',1),('C#5',1),('A4',2),('C#5',1),('E5',1),('F#5',2)]
leadClimax=[
 ('G5',1),('B5',1),('D6',2),('E6',1),('D6',1),('B5',1),('G5',1),
 ('A5',1),('C#6',1),('E6',2),('F#6',1),('E6',1),('C#6',1),('A5',1),
 ('F#5',1),('A5',1),('C#6',1),('E6',1),('F#6',2),('E6',1),('C#6',1),
 ('B5',1),('F#5',1),('D6',1),('B5',1),('A5',1),('F#5',1),('D5',1),('B4',1)]

def lead_phrase(p,seq,start=0,scale=2,inst=1,vol=44,echo=True,orn=False):
    r=start
    alt=False
    for i,(n,d) in enumerate(seq):
        if r>=64: break
        vv=vol + (3 if i%4==0 else 0) - (2 if i%7==3 else 0)
        # light vibrato on selected sustained notes: effect 4, speed/depth 0x24
        usefx = (d>=2 and i%3==0)
        cell(p,r,0,n,inst,vv,4 if usefx else None,0x24 if usefx else None)
        # restrained tracker echo on channel 1, delayed 3 rows and quieter
        if echo and r+3<64 and (i%2==0 or d>=2):
            cell(p,r+3,1,n,2,max(15,vv-19))
        # occasional grace octave sparkle separate ch 2
        if orn and i%8==7 and r+1<64:
            # retrigger same pitch quickly with bellish pluck
            cell(p,r+1,2,n,10,21)
        r+=d*scale
    return r

# bass generator, dense syncopated octave pattern
rootnotes={'Bm':('B2','B3','F#3'),'G':('G2','G3','D3'),'D':('D3','D4','A3'),'A':('A2','A3','E3'),'Em':('E2','E3','B2'),'F#m':('F#2','F#3','C#3')}
def bass_chunk(p,st,key,busy=1):
    root,octv,fifth=rootnotes[key]
    if busy==0: hits=[(0,root,40),(8,octv,34)]
    elif busy==1: hits=[(0,root,48),(3,root,35),(6,octv,39),(8,root,45),(11,fifth,37),(14,octv,40)]
    else: hits=[(0,root,50),(2,octv,36),(4,root,43),(6,fifth,37),(8,root,48),(10,octv,39),(12,fifth,38),(14,octv,42)]
    for off,n,v in hits: cell(p,st+off,12,n,3,v)

# pads with controlled chord retriggers (instrument volumes quiet)
def pad_chunk(p,st,key,mode='full'):
    tri=chords[key][0]
    if mode=='none':return
    if mode=='stab':
        for off in [0,8]:
            for j,n in enumerate(tri): cell(p,st+off,3+j,n,4+j,18 if off else 22)
    else:
        for j,n in enumerate(tri):cell(p,st,3+j,n,4+j,19 if mode=='soft' else 23)
        # re-articulation half-way to prevent static drone
        if mode=='full':
            for j,n in enumerate(tri):cell(p,st+8,3+j,n,4+j,18)

# arpeggio on ch6/ch7 alternating stereo
arporder=[0,1,2,1,3,2,1,2]
def arp_chunk(p,st,key,density=2,vol=25):
    arr=chords[key][1]
    if density==0:return
    step=2 if density==1 else 1
    for off in range(0,16,step):
        n=arr[arporder[(off//step)%len(arporder)]%len(arr)]
        ch=6 if (off//step)%2==0 else 7
        inst=10 if ch==6 else 11
        vv=vol + (3 if off%4==0 else 0)
        cell(p,st+off,ch,n,inst,vv)

# drums use channels 10 kick, 11 snare/clap, 13 hats, 14 perc/open/crash, 15 fx
def drums(p,style='full',fills=False,crash=False):
    if crash:cell(p,0,14,'C4',19,29)
    if style=='none':return
    if style=='half':
        kicks=[0,8,16,24,32,40,48,56]
        snares=[16,48]
        hats=list(range(4,64,8))
    elif style=='break':
        kicks=[0,7,16,22,32,39,48,54,58]
        snares=[12,28,44,60]
        hats=list(range(2,64,4))
    else:
        kicks=[0,8,16,24,32,40,48,56]
        # syncopations selected
        kicks += [14,30,46,62] if style=='full' else []
        snares=[8,24,40,56]
        hats=list(range(2,64,4))
    for r in kicks:
        if r<64:cell(p,r,10,'C4',13,51 if r%16==0 else 44)
    for r in snares:
        if r<64:
            cell(p,r,11,'C4',14,38)
            if style=='full':cell(p,r,14,'C4',15,24)
    for i,r in enumerate(hats):
        cell(p,r,13,'C4',16 if i%2==0 else 17,23 if i%2==0 else 18)
    # open hats on offbeat before next half-bar
    if style in ('full','break'):
        for r in [14,30,46,62]:cell(p,r,14,'C4',18,20)
    if fills:
        for r,v in [(58,22),(60,27),(62,32),(63,35)]:cell(p,r,11,'C4',14,v)

# all full patterns base arrangement
# P1: groove establishes (sparser melody from row 16)
for i,k in enumerate(prog[1]):
    pad_chunk(1,i*16,k,'soft'); arp_chunk(1,i*16,k,1,22); bass_chunk(1,i*16,k,1)
drums(1,'full',False,True)
# motif enters after 1 bar, custom 48 rows
seq1=[('B4',2),('D5',1),('F#5',1),('A5',2),('F#5',1),('D5',1),('G5',2),('F#5',1),('D5',1),('B4',2),('D5',1),('E5',1),('F#5',2),('A5',1),('D6',1),('C#6',1),('A5',1),('F#5',2)]
lead_phrase(1,seq1,16,2,1,42,True)

# P2 A full
for i,k in enumerate(prog[2]):pad_chunk(2,i*16,k,'full');arp_chunk(2,i*16,k,2,24);bass_chunk(2,i*16,k,2)
drums(2,'full',True,False);lead_phrase(2,leadA,0,2,1,45,True,True)
# extra counter punctuations on channel 2
for r,n in [(14,'B5'),(30,'G5'),(46,'A5'),(62,'E5')]:cell(2,r,2,n,12,20)

# P3 A variation, sharper arps and alternate lead
for i,k in enumerate(prog[3]):pad_chunk(3,i*16,k,'soft');arp_chunk(3,i*16,k,2,25);bass_chunk(3,i*16,k,2)
drums(3,'full',True,False);lead_phrase(3,leadB,0,2,1,44,True,True)
# octave pulse response
for r,n in [(12,'F#5'),(28,'D5'),(44,'A5'),(60,'E5')]:cell(3,r,2,n,7,19,0,0x37)

# P4 breakdown: no main drums first half, organ/pulse stabs, sparse bass, melody stripped
for i,k in enumerate(prog[4]):
    pad_chunk(4,i*16,k,'stab');arp_chunk(4,i*16,k,1 if i>=2 else 0,21);bass_chunk(4,i*16,k,0 if i<2 else 1)
# tiny percussion and latter half halftime
for r in [0,16,32,48]:cell(4,r,10,'C4',13,39)
for r in [12,28,44,60]:cell(4,r,11,'C4',14,29)
for r in range(34,64,4):cell(4,r,13,'C4',17,16)
# call response lead with gaps
breakmel=[(0,'B5',40),(4,'F#5',36),(8,'D5',37),(14,'A5',38),(18,'G5',39),(22,'D5',35),(28,'E5',36),(32,'F#5',41),(36,'A5',38),(42,'D6',42),(48,'C#6',39),(54,'A5',37),(60,'E5',35)]
for j,(r,n,v) in enumerate(breakmel):
    cell(4,r,0,n,1,v,4 if j in (0,7) else None,0x23 if j in (0,7) else None)
    if r+3<64:cell(4,r+3,1,n,2,v-19)
cell(4,56,15,'C4',20,22)

# P5 bridge, driving but new harmony
for i,k in enumerate(prog[5]):pad_chunk(5,i*16,k,'full');arp_chunk(5,i*16,k,2,24);bass_chunk(5,i*16,k,1)
drums(5,'break',True,True);lead_phrase(5,leadBridge,0,2,1,44,True,True)
# chiptune pulse counter line
counter5=[(8,'B4'),(12,'D5'),(24,'G4'),(28,'B4'),(40,'A4'),(44,'C#5'),(56,'E5'),(60,'C#5')]
for i,(r,n) in enumerate(counter5):cell(5,r,2,n,7 if i%2==0 else 8,20)

# P6 bridge variation, more space in lead then climb
for i,k in enumerate(prog[6]):pad_chunk(6,i*16,k,'soft');arp_chunk(6,i*16,k,2,25);bass_chunk(6,i*16,k,2)
drums(6,'full',True,False)
var6=[('E5',1),('G5',1),('B5',2),('D6',1),('B5',1),('G5',2),('D5',1),('G5',1),('B5',1),('A5',1),('G5',1),('F#5',1),('E5',2),('B4',1),('D5',1),('F#5',1),('B5',1),('D6',1),('B5',1),('A5',2),('C#6',1),('E6',1),('C#6',1),('B5',1),('A5',1),('E5',1),('C#5',2)]
lead_phrase(6,var6,0,2,1,45,True,True)

# P7 climax I
for i,k in enumerate(prog[7]):pad_chunk(7,i*16,k,'full');arp_chunk(7,i*16,k,2,27);bass_chunk(7,i*16,k,2)
drums(7,'full',True,True);lead_phrase(7,leadClimax,0,2,1,48,True,True)
# harmony lead thirds approximated, selective to avoid clutter
harm7=[(4,'B5'),(12,'G5'),(20,'C#6'),(28,'A5'),(36,'A5'),(44,'C#6'),(52,'F#5'),(60,'D5')]
for r,n in harm7:cell(7,r,2,n,12,22)

# P8 climax II / varied rapid line
for i,k in enumerate(prog[8]):pad_chunk(8,i*16,k,'full');arp_chunk(8,i*16,k,2,27);bass_chunk(8,i*16,k,2)
drums(8,'full',True,False);lead_phrase(8,leadC,0,2,1,47,True,True)
# pulse ostinato in gaps
for r,n in [(7,'D6'),(15,'E6'),(23,'C#6'),(31,'B5'),(39,'D6'),(47,'A5'),(55,'F#5'),(63,'B5')]: cell(8,r,2,n,8,18)

# P9 reprise: original hook, energy then transition to intro
for i,k in enumerate(prog[9]):pad_chunk(9,i*16,k,'full');arp_chunk(9,i*16,k,2,25);bass_chunk(9,i*16,k,2 if i<3 else 1)
drums(9,'full',True,True);lead_phrase(9,leadA,0,2,1,46,True,True)
# rising lead fill at very end
for r,n in [(56,'B5'),(58,'D6'),(60,'E6'),(62,'F#6')]:cell(9,r,2,n,12,23)

# P10 outro/turnaround 32: reduce to chord, hook fragment, then exact breathing room
for i,k in enumerate(prog[10]):
    pad_chunk(10,i*16,k,'soft');arp_chunk(10,i*16,k,1,21);bass_chunk(10,i*16,k,0)
# light kick and hats
for r in [0,8,16,24]:cell(10,r,10,'C4',13,39 if r else 48)
for r in [8,24]:cell(10,r,11,'C4',14,31)
for r in range(2,28,4):cell(10,r,13,'C4',16,16)
# last melodic cadence designed to hand into intro's B bell
out=[(0,'B5',44),(4,'F#5',38),(8,'D5',39),(12,'F#5',40),(16,'G5',41),(20,'D5',36),(24,'A4',34),(28,'F#4',29)]
for r,n,v in out:
    cell(10,r,0,n,1,v)
    if r+3<32:cell(10,r+3,1,n,2,v-19)
# shorten sustained channels and bass at very end for clean restart
for ch in [0,1,2,3,4,5,6,7,12]:cell(10,31,ch,'OFF')

# Add pattern section names impossible metadata; instrument names carry character.
# Save JSON
with open('/workspace/song_calls.json','w') as f:json.dump(calls,f)
print('calls',len(calls))
print('lead totals',sum(d for _,d in leadA),sum(d for _,d in leadB),sum(d for _,d in leadC),sum(d for _,d in leadBridge),sum(d for _,d in leadClimax))
