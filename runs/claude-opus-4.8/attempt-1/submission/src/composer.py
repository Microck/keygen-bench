import json
# ---------- note helpers ----------
LET={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def nn(name):
    if name is None: return None
    if name=='off': return 97
    s=name.strip().upper()
    letter=s[0]; acc=0; idx=1
    if len(s)>1 and s[1] in '#B-':
        c=s[1]; acc=1 if c=='#' else (-1 if c=='B' else 0); idx=2
    return 1+int(s[idx:])*12+LET[letter]+acc
def tr(name,semi):
    v=nn(name); return v+semi if v is not None else None

# instruments
LEAD,BASS,ARPL,PAD,KICK,SNARE,HAT,OHAT,LEAD2,SUB,CLAP,CRASH,ARPR,PADL,PADR=range(1,16)
# channels
CH_KICK,CH_SNARE,CH_HAT,CH_PERC,CH_BASS,CH_SUB,CH_LEAD,CH_LEAD2,CH_ARP1,CH_ARP2,CH_PADA,CH_PADB=range(12)

CH={
 'Am':{'root':'A3','q':0x37,'bass':'A2','arp':['A4','C5','E5','A5']},
 'F' :{'root':'F3','q':0x47,'bass':'F2','arp':['F4','A4','C5','F5']},
 'C' :{'root':'C4','q':0x47,'bass':'C2','arp':['C5','E5','G5','C6']},
 'G' :{'root':'G3','q':0x47,'bass':'G2','arp':['G4','B4','D5','G5']},
 'Dm':{'root':'D3','q':0x37,'bass':'D2','arp':['D4','F4','A4','D5']},
 'E' :{'root':'E3','q':0x47,'bass':'E2','arp':['E4','G#4','B4','E5']},
}
A_CHORDS=['Am','F','C','G']; B_CHORDS=['Dm','F','C','E']

cells={}
def setc(pat,row,ch,note=None,inst=None,vol=None,eff=None,par=None):
    d={'pattern':pat,'row':row,'channel':ch}
    if note is not None: d['note']=note if isinstance(note,int) else nn(note)
    if inst is not None: d['instrument']=inst
    if vol is not None: d['volume']=vol
    if eff is not None: d['effect']=eff
    if par is not None: d['effect_param']=par
    cells[(pat,row,ch)]=d
def bars_chords(ch4):
    o=[]
    for c in ch4: o+=[c]*16
    return o

def place_pad(pat,chords,vol=26):
    cr=bars_chords(chords)
    for bar in range(4):
        c=cr[bar*16]; root=CH[c]['root']
        setc(pat,bar*16,CH_PADA,note=root,inst=PADL,vol=vol)
        setc(pat,bar*16,CH_PADB,note=tr(root,7),inst=PADR,vol=vol)  # fifth

def place_arp(pat,chords,vol=32,arp2=True,patt1=(0,1,2,3),patt2=(2,3,0,1)):
    cr=bars_chords(chords)
    for r in range(64):
        c=cr[r]; tones=CH[c]['arp']
        setc(pat,r,CH_ARP1,note=tones[patt1[r%4]],inst=ARPL,vol=vol,eff=10,par=8)
        if arp2:
            setc(pat,r,CH_ARP2,note=tones[patt2[r%4]],inst=ARPR,vol=max(20,vol-10),eff=10,par=8)

BASS_RIFF={0:0,2:0,3:12,6:0,8:0,10:0,11:12,14:0}
BASS_SIMPLE={0:0,8:0}
def place_bass(pat,chords,riff,accent=(0,8),sub=False,vol_lo=42):
    cr=bars_chords(chords)
    for bar in range(4):
        c=cr[bar*16]; root=CH[c]['bass']
        for step,off in riff.items():
            r=bar*16+step
            setc(pat,r,CH_BASS,note=tr(root,off),inst=BASS,vol=(54 if step in accent else vol_lo))
        if sub:
            setc(pat,bar*16,CH_SUB,note=root,inst=SUB,vol=22)
            setc(pat,bar*16+8,CH_SUB,note=root,inst=SUB,vol=18)

def place_drums(pat,kick,snare,hat,ohat,clap=None,rng=range(4)):
    for bar in rng:
        b=bar*16
        for s,v in kick.items(): setc(pat,b+s,CH_KICK,note='C-4',inst=KICK,vol=v)
        for s,v in snare.items(): setc(pat,b+s,CH_SNARE,note='C-4',inst=SNARE,vol=v)
        for s,v in hat.items(): setc(pat,b+s,CH_HAT,note='C-4',inst=HAT,vol=v)
        for s,v in ohat.items(): setc(pat,b+s,CH_HAT,note='C-4',inst=OHAT,vol=v)
        if clap:
            for s,v in clap.items(): setc(pat,b+s,CH_SNARE,note='C-4',inst=CLAP,vol=v)
def crash_at(pat,row,vol=30): setc(pat,row,CH_PERC,note='C-4',inst=CRASH,vol=vol)

def place_melody(pat,ch,inst,mel,base_vol=52,vib=True):
    rows=sorted(mel.keys())
    for idx,r in enumerate(rows):
        note=mel[r]
        if note=='off': setc(pat,r,ch,note=97); continue
        v=base_vol+2 if (r%16 in (0,8)) else base_vol-6
        setc(pat,r,ch,note=note,inst=inst,vol=v,eff=(4 if vib else None),par=(0x34 if vib else None))
        if vib:
            nxt=rows[idx+1] if idx+1<len(rows) else r+4
            for rr in range(r+1,min(nxt,64)):
                setc(pat,rr,ch,eff=4,par=0x00)
def mel_shift(mel,semi):
    return {r:('off' if n=='off' else nn(n)+semi) for r,n in mel.items()}

# drum kits
K_MAIN={0:64,6:30,8:58,14:34}; S_MAIN={4:56,12:60}
H_MAIN={0:12,2:22,4:13,6:26,8:12,10:22,12:13}; O_MAIN={14:30}
K_FULL={0:60,3:22,6:26,8:58,11:22,14:30}; S_FULL={4:60,12:62}
H_FULL={0:14,1:8,2:24,3:8,4:15,5:8,6:27,7:8,8:14,9:8,10:24,11:8,12:15,13:8}
O_FULL={6:22,14:30}; CLAP_FULL={4:34,12:36}

# melodies
LEAD_A={0:'A5',4:'C6',6:'B5',8:'A5',12:'E5', 16:'F5',20:'A5',22:'G5',24:'F5',28:'E5',
        32:'E5',36:'G5',38:'E5',40:'C6',44:'G5', 48:'D6',52:'B5',54:'G5',56:'A5',58:'B5',60:'D6'}
LEAD_A2={0:'E6',4:'D6',6:'C6',8:'B5',12:'A5', 16:'A5',20:'C6',24:'A5',28:'G5',
         32:'G5',36:'C6',40:'E6',44:'D6', 48:'B5',52:'D6',56:'B5',58:'A5',60:'G5'}
LEAD_B={0:'F5',2:'A5',4:'D6',8:'A5',12:'F5', 16:'A5',20:'C6',24:'A5',28:'G5',
        32:'E5',36:'G5',40:'C6',44:'G5', 48:'B5',52:'G#5',56:'E5',58:'G#5',60:'B5'}
LEAD_B2={0:'A5',4:'E5',8:'C6',12:'A5', 16:'C6',20:'A5',24:'F5',28:'A5',
         32:'G5',36:'E5',40:'G5',44:'C6', 48:'D6',52:'B5',56:'G5',60:'B5'}
LEAD_C={0:'E6',8:'A5',12:'C6', 16:'C6',24:'A5',28:'G5',
        32:'G5',40:'E6',44:'D6', 48:'D6',56:'B5',60:'D6'}   # soaring chorus
LEAD_C2={0:'C6',8:'B5',12:'A5', 16:'A5',24:'C6',28:'A5',
         32:'G5',40:'C6',44:'E6', 48:'D6',56:'B5',58:'A5',60:'G5'}  # chorus answer

def groove(pat,chords,lead,full=False,climax=False):
    place_pad(pat,chords,vol=(30 if climax else 26))
    place_bass(pat,chords,BASS_RIFF,sub=True)
    place_arp(pat,chords,vol=(30 if climax else 27))
    if full or climax:
        place_drums(pat,K_FULL,S_FULL,H_FULL,O_FULL,clap=(CLAP_FULL if climax else None))
    else:
        place_drums(pat,K_MAIN,S_MAIN,H_MAIN,O_MAIN)
    place_melody(pat,CH_LEAD,LEAD,lead,base_vol=(62 if climax else 61))
    if climax:
        place_melody(pat,CH_LEAD2,LEAD2,mel_shift(lead,-12),base_vol=30,vib=False)

def build():
    setc(0,0,CH_HAT,eff=16,par=57)   # global volume headroom for final render
    # P0 intro: sustained pad + sub + soft kick (sparse)
    place_pad(0,A_CHORDS,vol=24)
    place_bass(0,A_CHORDS,BASS_SIMPLE,accent=(0,),sub=True,vol_lo=40)
    for bar in range(4): setc(0,bar*16,CH_KICK,note='C-4',inst=KICK,vol=36)
    # arp gently enters second half as a build
    for r in range(32,64):
        c=bars_chords(A_CHORDS)[r]; tones=CH[c]['arp']
        setc(0,r,CH_ARP1,note=tones[(0,1,2,3)[r%4]],inst=ARPL,vol=(18 if r<48 else 24),eff=10,par=8)
    crash_at(0,0,32)
    # P1 intro: + bass riff + arp1 + hats (build)
    place_pad(1,A_CHORDS,vol=26)
    place_bass(1,A_CHORDS,BASS_RIFF,sub=True)
    place_arp(1,A_CHORDS,vol=30,arp2=False)
    place_drums(1,{0:56,8:52},{},{2:20,6:26,10:20,14:28},{})
    for i,r in enumerate([56,58,60,62]): setc(1,r,CH_SNARE,note='C-4',inst=SNARE,vol=26+i*8)
    # P2..P5 main
    groove(2,A_CHORDS,LEAD_A)
    groove(3,A_CHORDS,LEAD_A2)
    for i,r in enumerate([58,60,62]): setc(3,r,CH_SNARE,note='C-4',inst=SNARE,vol=40+i*6)
    groove(4,B_CHORDS,LEAD_B)
    groove(5,A_CHORDS,LEAD_B2)
    for i,r in enumerate([60,62]): setc(5,r,CH_SNARE,note='C-4',inst=SNARE,vol=46+i*8)
    # P8,P9 climax
    groove(8,A_CHORDS,LEAD_C,full=True,climax=True); crash_at(8,0,30)
    groove(9,A_CHORDS,LEAD_C2,full=True,climax=True); crash_at(9,0,30)
    for i,r in enumerate([56,58,60,62]): setc(9,r,CH_SNARE,note='C-4',inst=SNARE,vol=32+i*7)
    # P6 break: pad + soft arp1 + sparse kick + lead phrase
    place_pad(6,A_CHORDS,vol=24)
    place_arp(6,A_CHORDS,vol=26,arp2=False)
    place_bass(6,A_CHORDS,BASS_SIMPLE,accent=(0,),sub=True,vol_lo=40)
    for bar in range(4):
        setc(6,bar*16,CH_KICK,note='C-4',inst=KICK,vol=40)
        setc(6,bar*16+2,CH_HAT,note='C-4',inst=HAT,vol=16)
        setc(6,bar*16+10,CH_HAT,note='C-4',inst=HAT,vol=16)
    crash_at(6,0,40)
    place_melody(6,CH_LEAD,LEAD,{0:'A5',8:'E5',16:'F5',24:'C6',32:'E5',40:'G5',48:'D5',56:'E5'},base_vol=42)
    # P7 build: riser into loop
    setc(7,0,CH_LEAD,note=97)
    place_pad(7,A_CHORDS,vol=26)
    place_arp(7,A_CHORDS,vol=32)
    place_bass(7,A_CHORDS,BASS_RIFF,sub=True)
    for bar in range(4):
        setc(7,bar*16,CH_KICK,note='C-4',inst=KICK,vol=58)
        if bar<3: setc(7,bar*16+8,CH_KICK,note='C-4',inst=KICK,vol=52)
    rr=sorted(set(list(range(32,48,2))+list(range(48,64))))
    for r in rr:
        setc(7,r,CH_SNARE,note='C-4',inst=SNARE,vol=int(22+(r-32)/32.0*36))
    for r in range(0,32,4): setc(7,r,CH_HAT,note='C-4',inst=OHAT,vol=24)
    crash_at(7,0,40)

build()
calls=[]
for p in range(10):
    calls.append({"name":"pattern_clear","arguments":{"pattern":p}})
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
for k in sorted(cells): calls.append({"name":"pattern_set_cell","arguments":cells[k]})
json.dump(calls,open("/workspace/work/batch_song.json","w"))
order=[0,1,2,3,4,5,8,9,6,7]
meta=[{"name":"order_set","arguments":{"position":i,"pattern":p}} for i,p in enumerate(order)]
meta.append({"name":"song_set","arguments":{"name":"midnight keygen","bpm":140,"speed":6,"length":len(order),"loop_start":2}})
json.dump(meta,open("/workspace/work/batch_meta.json","w"))
print("cells",len(cells),"order",order)
