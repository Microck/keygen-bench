import numpy as np, base64, json, os

SR = 16726
rng = np.random.default_rng(42)

def to_b64(arr):
    return base64.b64encode((np.clip(arr,-1,1)*32767).astype(np.int16).tobytes()).decode()

NM = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(n,o): return o*12+NM[n]+1
OFF = 97

# ═══════════════════ WAVEFORM GENERATION ═══════════════════

def make_looped(cycle, att_n, loop_n, rel_n, att_shape='linear'):
    c = len(cycle)
    att = np.tile(cycle, att_n)
    if att_shape == 'linear':
        att *= np.linspace(0,1,c*att_n)
    else:
        att *= 1 - np.exp(-np.linspace(0,5,c*att_n))
    loop = np.tile(cycle, loop_n)
    rel = np.tile(cycle, rel_n) * np.linspace(1,0,c*rel_n)
    smp = np.concatenate([att, loop, rel])
    ls = c*att_n*2; ll = c*loop_n*2
    return smp, ls, ll

cyc = int(round(SR / 261.63))
t = np.linspace(0,1,cyc,endpoint=False)

# 1) LEAD
lead_w = np.zeros(cyc)
for h in range(1,22):
    lead_w += np.sin(2*np.pi*h*t)/h*(0.93**h)
lead_w = lead_w/np.max(np.abs(lead_w))*0.72
lead_smp, lead_ls, lead_ll = make_looped(lead_w, 3, 8, 30)

# 2) BASS
bass_w = np.where(t<0.38, 0.55, -0.45) + np.sin(2*np.pi*t)*0.45
bass_w = bass_w/np.max(np.abs(bass_w))*0.78
bass_smp, bass_ls, bass_ll = make_looped(bass_w, 2, 6, 20)

# 3) ARP
arp_w = np.where(t<0.22, 0.75, -0.75)
arp_smp, arp_ls, arp_ll = make_looped(arp_w, 1, 4, 15)

# 4) PAD
pad_w = np.zeros(cyc)
for h in range(1,7):
    pad_w += np.sin(2*np.pi*h*t)/(h**2.3)
pad_w = pad_w/np.max(np.abs(pad_w))*0.50
pad_smp, pad_ls, pad_ll = make_looped(pad_w, 20, 8, 30, 'exp')

# 5) PLUCK
plk_w = np.zeros(cyc)
for h in range(1,10):
    plk_w += np.sin(2*np.pi*h*t)*((-1)**(h+1))/(h**2)
plk_w = plk_w/np.max(np.abs(plk_w))*0.65
pluck_smp = np.tile(plk_w,40)*np.exp(-np.linspace(0,5.5,cyc*40))

# 6) KICK
nk=int(SR*0.25); tk=np.arange(nk)/SR
freq_k=260*np.exp(-tk*18)+40
kick=np.sin(np.cumsum(freq_k/SR)*2*np.pi)*np.exp(-tk*12)*0.92
cl=min(int(0.004*SR),nk)
kick[:cl]+=rng.uniform(-0.4,0.4,cl)*np.linspace(1,0,cl)
kick=np.clip(kick,-1,1)

# 7) SNARE
ns=int(SR*0.18); ts=np.arange(ns)/SR
snare=(rng.uniform(-1,1,ns)*0.55+np.sin(2*np.pi*195*ts)*0.45)*np.exp(-ts*16)*0.82

# 8) CHH
nh=int(SR*0.04); th=np.arange(nh)/SR
chh=(rng.uniform(-1,1,nh)*0.45+np.sin(2*np.pi*7800*th)*0.3+np.sin(2*np.pi*10500*th)*0.2)*np.exp(-th*55)*0.52

# 9) OHH
noh=int(SR*0.22); toh=np.arange(noh)/SR
ohh=(rng.uniform(-1,1,noh)*0.45+np.sin(2*np.pi*7800*toh)*0.3+np.sin(2*np.pi*10500*toh)*0.2)*np.exp(-toh*7)*0.48

# ═══════════════════ BUILD FT2 COMMANDS ═══════════════════
cmds = []
cmds.append({"name":"module_new","arguments":{"channels":10,"name":"KEYGEN BY CLAUDE"}})
cmds.append({"name":"song_set","arguments":{"bpm":138,"speed":6,"length":10,"loop_start":2}})

REL = 12
inst_defs = [
    (lead_smp,1,lead_ls,lead_ll,REL,40,"Lead Synth",1,128),
    (bass_smp,2,bass_ls,bass_ll,REL,50,"Bass",1,128),
    (arp_smp,3,arp_ls,arp_ll,REL,30,"Arp Chip",1,128),
    (pad_smp,4,pad_ls,pad_ll,REL,20,"Pad",1,96),
    (pluck_smp,5,0,0,REL,34,"Pluck",0,160),
    (kick,6,0,0,REL,64,"Kick",0,128),
    (snare,7,0,0,REL,50,"Snare",0,128),
    (chh,8,0,0,REL,28,"CHH",0,100),
    (ohh,9,0,0,REL,34,"OHH",0,156),
]

for (smp,inst,ls,ll,rn,vol,nm,flg,pan) in inst_defs:
    b=to_b64(smp)
    cmds.append({"name":"sample_create_from_pcm","arguments":{"instrument":inst,"sample":0,"pcm":b,"encoding":"int16","name":nm}})
    sa={"instrument":inst,"sample":0,"volume":vol,"relative_note":rn,"finetune":0,"panning":pan}
    if flg: sa["loop_start"]=ls; sa["loop_length"]=ll; sa["flags"]=1
    else: sa["flags"]=0
    cmds.append({"name":"sample_set","arguments":sa})
    cmds.append({"name":"instrument_set","arguments":{"instrument":inst,"name":nm}})

cells = []

# Chord: Am | F | C | G
BASS = [('A',3),('F',3),('C',4),('G',3)]

def drums(pat, style='full'):
    c=[]
    for bar in range(4):
        o=bar*16
        if style=='build':
            kr=[0,8] if bar<2 else [0,4,8,12] if bar<3 else list(range(0,16,2))
            for r in kr: c.append((pat,o+r,0,N('C',4),6,0x10+min(48,20+bar*8+r),0,0))
            for r in range(0,16,4): c.append((pat,o+r,2,N('C',4),8,None,0,0))
            if bar>=2:
                for r in [4,12]: c.append((pat,o+r,1,N('C',4),7,None,0,0))
            continue
        if style=='half':
            c.append((pat,o,0,N('C',4),6,None,0,0))
            for r in range(0,16,4): c.append((pat,o+r,2,N('C',4),8,None,0,0))
            if bar%2==1: c.append((pat,o+4,1,N('C',4),7,None,0,0))
            continue
        if style=='break':
            for r in range(0,16,4): c.append((pat,o+r,2,N('C',4),8,0x10+18,0,0))
            if bar==3:
                for i,r in enumerate(range(8,16,2)):
                    c.append((pat,o+r,1,N('C',4),7,min(0x10+20+i*6,0x40),0,0))
            continue
        # full
        kr=[0,8]; 
        if bar%2==1: kr.append(6)
        for r in kr: c.append((pat,o+r,0,N('C',4),6,None,0,0))
        for r in [4,12]: c.append((pat,o+r,1,N('C',4),7,None,0,0))
        for r in range(0,16,2):
            hi=9 if r==14 else 8
            c.append((pat,o+r,2,N('C',4),hi,None,0,0))
        if bar%2==0: c.append((pat,o+10,1,N('C',4),7,0x10+12,0,0))
    return c

def bassline(pat, style='normal'):
    c=[]
    for bar,(bn,bo) in enumerate(BASS):
        o=bar*16
        if style=='normal':
            c+=[(pat,o,3,N(bn,bo),2,None,0,0),(pat,o+4,3,N(bn,bo),2,None,0,0),
                (pat,o+6,3,OFF,0,None,0,0),(pat,o+8,3,N(bn,bo),2,None,0,0),
                (pat,o+10,3,N(bn,max(bo-1,2)),2,None,0,0),(pat,o+14,3,OFF,0,None,0,0)]
        elif style=='pump':
            for r in [0,4,8,12]:
                c+=[(pat,o+r,3,N(bn,bo),2,None,0,0),(pat,o+r+2,3,OFF,0,None,0,0)]
        elif style=='sparse':
            c+=[(pat,o,3,N(bn,bo),2,None,0,0),(pat,o+12,3,OFF,0,None,0,0)]
    return c

ARP_D=[(N('A',4),0x37),(N('F',4),0x47),(N('C',5),0x47),(N('G',4),0x47)]
def arps(pat, style='full'):
    c=[]
    for bar,(note,ae) in enumerate(ARP_D):
        o=bar*16
        if style=='full':
            for r in range(0,16,2): c.append((pat,o+r,5,note,3,None,0,ae))
            c.append((pat,o+15,5,OFF,0,None,0,0))
        elif style=='gated':
            for r in [0,2,4,8,10,12]: c.append((pat,o+r,5,note,3,None,0,ae))
            c+=[(pat,o+6,5,OFF,0,None,0,0),(pat,o+14,5,OFF,0,None,0,0)]
        elif style=='sparse':
            for r in [0,8]: c.append((pat,o+r,5,note,3,None,0,ae))
            c.append((pat,o+12,5,OFF,0,None,0,0))
    return c

def pads(pat):
    c=[]
    for n,r in [(N('A',3),0),(N('F',3),16),(N('C',4),32),(N('G',3),48)]:
        c.append((pat,r,6,n,4,None,0,0))
    for n,r in [(N('E',4),0),(N('C',4),16),(N('G',4),32),(N('D',4),48)]:
        c.append((pat,r,7,n,4,None,0,0))
    return c

def lead_A(pat):
    m=[(0,N('E',5)),(3,N('D',5)),(4,N('C',5)),(6,N('A',4)),(8,N('C',5)),
       (10,N('B',4)),(12,N('A',4)),
       (16,N('F',4)),(18,N('A',4)),(20,N('C',5)),(22,N('A',4)),(24,N('G',4)),
       (26,N('F',4)),(28,N('E',4)),(30,N('D',4)),
       (32,N('E',4)),(34,N('G',4)),(36,N('A',4)),(38,N('C',5)),
       (40,N('B',4)),(44,N('G',4)),
       (48,N('G',4)),(50,N('B',4)),(52,N('D',5)),(54,N('C',5)),
       (56,N('B',4)),(58,N('A',4)),(60,N('G',4)),(63,N('A',4))]
    return [(pat,r,4,n,1,None,0,0) for r,n in m]

def lead_B(pat):
    m=[(0,N('A',4)),(1,N('C',5)),(2,N('E',5)),(4,N('E',5)),(6,N('D',5)),
       (7,N('C',5)),(8,N('A',4)),(10,N('C',5)),(12,N('E',5)),(14,N('D',5)),
       (16,N('C',5)),(18,N('F',5)),(20,N('E',5)),(22,N('C',5)),
       (24,N('A',4)),(26,N('C',5)),(28,N('A',4)),(30,N('G',4)),
       (32,N('G',4)),(33,N('A',4)),(34,N('C',5)),(36,N('E',5)),
       (38,N('G',5)),(40,N('F',5)),(42,N('E',5)),(44,N('D',5)),(46,N('C',5)),
       (48,N('B',4)),(50,N('D',5)),(52,N('G',5)),(54,N('E',5)),
       (56,N('D',5)),(58,N('C',5)),(60,N('B',4)),(62,N('A',4))]
    return [(pat,r,4,n,1,None,0,0) for r,n in m]

def lead_C(pat):
    m=[(0,N('A',4)),(4,N('E',5)),(8,N('C',5)),(14,OFF),
       (16,N('F',4)),(20,N('C',5)),(24,N('A',4)),(30,OFF),
       (32,N('E',4)),(36,N('G',4)),(40,N('C',5)),(44,N('E',5)),
       (48,N('D',5)),(52,N('B',4)),(56,N('G',4)),(60,N('A',4))]
    c=[]
    for r,n in m:
        inst=1 if n!=OFF else 0
        c.append((pat,r,4,n,inst,None,4 if n!=OFF else 0,0x36 if n!=OFF else 0))
    return c

def pluck_ct(pat):
    m=[(2,N('E',4)),(6,N('A',4)),(10,N('C',5)),(14,N('E',4)),
       (18,N('F',4)),(22,N('A',4)),(26,N('C',5)),(30,N('F',4)),
       (34,N('G',4)),(38,N('E',4)),(42,N('G',4)),(46,N('C',5)),
       (50,N('B',4)),(54,N('D',5)),(58,N('B',4)),(62,N('G',4))]
    return [(pat,r,8,n,5,None,0,0) for r,n in m]

# ═══════════════════ PATTERNS ═══════════════════
# 0: Intro
cells+=drums(0,'build')
cells+=[(0,32,3,N('C',4),2,None,0,0),(0,36,3,N('C',4),2,None,0,0),
        (0,40,3,N('C',4),2,None,0,0),
        (0,48,3,N('G',3),2,None,0,0),(0,52,3,N('G',3),2,None,0,0),
        (0,56,3,N('A',3),2,None,0,0),(0,60,3,N('A',3),2,None,0,0)]
for r in range(48,64,2):
    cells.append((0,r,5,N('A',4),3,None,0,0x37))
cells.append((0,63,5,OFF,0,None,0,0))

# 1: Theme A
cells+=drums(1,'full'); cells+=bassline(1); cells+=lead_A(1)

# 2: Full (loop target)
cells+=drums(2,'full'); cells+=bassline(2); cells+=lead_A(2)
cells+=arps(2,'full'); cells+=pads(2)

# 3: Theme B
cells+=drums(3,'full'); cells+=bassline(3,'pump')
cells+=lead_B(3); cells+=arps(3,'gated')

# 4: Breakdown
cells+=drums(4,'break'); cells+=bassline(4,'sparse')
cells+=pads(4); cells+=lead_C(4)

# 5: Climax
cells+=drums(5,'full'); cells+=bassline(5,'pump')
cells+=lead_B(5); cells+=arps(5,'full'); cells+=pads(5); cells+=pluck_ct(5)

# 6: Bridge (reconnects to loop)
cells+=drums(6,'full'); cells+=bassline(6); cells+=arps(6,'full'); cells+=pads(6)
cells+=[(6,32,4,N('E',4),1,None,0,0),(6,36,4,N('G',4),1,None,0,0),
        (6,40,4,N('A',4),1,None,0,0),(6,44,4,N('B',4),1,None,0,0),
        (6,48,4,N('C',5),1,None,0,0),(6,52,4,N('D',5),1,None,0,0),
        (6,56,4,N('E',5),1,None,4,0x26),(6,62,4,N('E',5),1,None,0,0)]

# Convert
for (pat,row,ch,note,inst,vol,eff,ep) in cells:
    c={"pattern":pat,"row":row,"channel":ch}
    if note is not None: c["note"]=note
    if inst: c["instrument"]=inst
    if vol is not None: c["volume"]=vol
    if eff is not None and ep is not None and (eff or ep):
        c["effect"]=eff; c["effect_param"]=ep
    cmds.append({"name":"pattern_set_cell","arguments":c})

for i,p in enumerate([0,1,2,3,4,5,2,3,5,6]):
    cmds.append({"name":"order_set","arguments":{"position":i,"pattern":p}})

os.makedirs("/workspace/submission",exist_ok=True)
cmds.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
cmds.append({"name":"module_render","arguments":{"path":"/workspace/submission/preview.wav","rate":44100,"loops":2}})

with open("/workspace/batch_final.json","w") as f:
    json.dump(cmds, f)
print(f"Generated {len(cmds)} commands")
