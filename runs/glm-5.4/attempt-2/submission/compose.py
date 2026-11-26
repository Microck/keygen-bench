import json, os, math

SHARP={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def nn(name):
    if name == 'OFF': return 'OFF'
    if name[1]=='#':
        p=name[:2]; octv=int(name[2]); semi=SHARP[p]
    else:
        p=name[0]; octv=int(name[2]); semi=SHARP[p]
    return 1 + octv*12 + semi

class C:
    def __init__(self): self.calls=[]
    def cell(self,pat,row,ch,note=None,ins=None,vol=None,eff=None,param=None):
        if row<0 or row>63: return
        a={"pattern":pat,"row":row,"channel":ch}
        if note is not None: a["note"]=nn(note) if isinstance(note,str) else note
        if ins is not None: a["instrument"]=ins
        if vol is not None: a["volume"]=vol
        if eff is not None: a["effect"]=eff
        if param is not None: a["effect_param"]=param
        self.calls.append({"name":"pattern_set_cell","arguments":a})
    def note(self,pat,row,ch,note,ins,vol=64,dur=None,eff=None,param=None,fade=False):
        self.cell(pat,row,ch,note,ins,vol,eff,param)
        if dur:
            end=min(63,row+dur)
            if fade and end-1>row:
                self.cell(pat,end-1,ch,None,None,None,0xA,0x0F)
            self.cell(pat,end,ch,'OFF')
    def lead_line(self,pat,notes,ins=8,vol=58,fade=True,long_ins=16):
        # notes: list of (name, start, dur)
        notes=sorted(notes,key=lambda x:x[1])
        for i,(name,start,dur) in enumerate(notes):
            if start<0 or start>63: continue
            self.cell(pat,start,6,name,long_ins if dur>2 else ins,vol)
            end=start+dur
            # vibrato on longer notes
            if dur >= 6:
                for rr in range(start+1, min(end-1,64)):
                    self.cell(pat,rr,6,None,None,None,4,0x42)
            nxt=notes[i+1][1] if i+1<len(notes) else 999
            if end < nxt:
                if fade and end-1>start:
                    self.cell(pat,min(63,end-1),6,None,None,None,0xA,0x0F)
                if end < 64: self.cell(pat,end,6,'OFF')
            elif end == nxt and fade and end-1>start:
                self.cell(pat,end-1,6,None,None,None,0xA,0x0F)

CHORDS={
 'Am': dict(root='A-2', third='C-3', fifth='E-3', sub='A-1', pad=['A-3','C-4','E-4'], arp=['A-4','C-5','E-5','A-5'], minor=True),
 'F':  dict(root='F-2', third='A-2', fifth='C-3', sub='F-1', pad=['F-3','A-3','C-4'], arp=['F-4','A-4','C-5','F-5'], minor=False),
 'C':  dict(root='C-3', third='E-3', fifth='G-3', sub='C-2', pad=['C-4','E-4','G-4'], arp=['C-5','E-5','G-5','C-6'], minor=False),
 'G':  dict(root='G-2', third='B-2', fifth='D-3', sub='G-1', pad=['G-3','B-3','D-4'], arp=['G-4','B-4','D-5','G-5'], minor=False),
 'Dm': dict(root='D-3', third='F-3', fifth='A-3', sub='D-2', pad=['D-3','F-3','A-3'], arp=['D-5','F-5','A-5','D-6'], minor=True),
 'E':  dict(root='E-2', third='G#2', fifth='B-2', sub='E-1', pad=['E-3','G#3','B-3'], arp=['E-4','G#4','B-4','E-5'], minor=False),
 'Em': dict(root='E-2', third='G-2', fifth='B-2', sub='E-1', pad=['E-3','G-3','B-3'], arp=['E-4','G-4','B-4','E-5'], minor=True),
}

def drums(c,pat,bar,style='normal',crash=False,fill=False,roll=False,roll_start=48):
    b=bar*16
    # KICK
    if style in ('soft','half'):
        for r in [0,8]:
            c.cell(pat,b+r,0,'C-4',1,52 if style=='soft' else 60)
        if style=='half': c.cell(pat,b+14,0,'C-4',1,48)
    elif style=='climax':
        for r in [0,4,8,12,14,15]:
            c.cell(pat,b+r,0,'C-4',1,64 if r in (0,4,8,12) else 52)
    else:
        for r in [0,4,8,12]:
            c.cell(pat,b+r,0,'C-4',1,64)
        c.cell(pat,b+14,0,'C-4',1,50)
        if style=='hard': c.cell(pat,b+15,0,'C-4',1,42)
    # SNARE
    if style=='soft':
        c.cell(pat,b+12,1,'C-4',2,38)
    elif style=='half':
        c.cell(pat,b+8,1,'C-4',2,56)
        c.cell(pat,b+15,1,'C-4',2,30)
    else:
        c.cell(pat,b+4,1,'C-4',2,62)
        c.cell(pat,b+12,1,'C-4',2,62)
        c.cell(pat,b+15,1,'C-4',2,30 if style=='normal' else 42)
        if style=='hard': c.cell(pat,b+14,1,'C-4',2,30)
    # HATS
    if style in ('soft','half'):
        for i,r in enumerate(range(0,16,2)):
            c.cell(pat,b+r,2,'C-4',3,26 if i%2==0 else 18)
        for r in [2,6,10,14]:
            c.cell(pat,b+r,3,'C-4',4,20 if style=='soft' else 26)
    else:
        for r in range(0,16,1):
            c.cell(pat,b+r,2,'C-4',3,34 if r%4==0 else (24 if r%2==0 else 18))
        for r in [2,6,10,14]:
            c.cell(pat,b+r,3,'C-4',4,30)
    # crash
    if crash:
        c.cell(pat,b,1,'C-4',5,58)
    # fill
    if fill:
        for i,r in enumerate(range(12,16)):
            c.cell(pat,b+r,1,'C-4',2,40+i*5)
    # roll
    if roll:
        for i,r in enumerate(range(roll_start,64)):
            c.cell(pat,r,1,'C-4',2,min(64,20+i*3))
            if r%2==0:
                c.cell(pat,r,2,'C-4',3,26)

def bass(c,pat,bar,ch,style='normal'):
    b=bar*16; n=nn(ch['root']); third=3 if ch['minor'] else 4
    if style=='soft':
        for r,d in [(0,4),(8,4),(12,4)]:
            c.cell(pat,b+r,4,n,6,50)
    elif style=='half':
        c.cell(pat,b,4,n,6,52)
        c.cell(pat,b+8,4,n+7,6,46)
    elif style=='climax':
        pattern=[0,0,12,0,7,0,12,7,0,12,0,7,third,7,0,12]
        for i,s in enumerate(pattern):
            c.cell(pat,b+i,4,n+s,6,60 if i%4==0 else 52)
    else:
        pattern=[0,12,0,7,0,12,third,7]
        for i,s in enumerate(pattern):
            c.cell(pat,b+i*2,4,n+s,6,58 if i%2==0 else 52)

def sub(c,pat,bar,ch,style='normal'):
    b=bar*16; n=nn(ch['sub'])
    if style in ('soft','half'):
        c.cell(pat,b,5,n,7,48)
    elif style=='climax':
        c.cell(pat,b,5,n,7,54)
        c.cell(pat,b+8,5,n,7,48)
    else:
        c.cell(pat,b,5,n,7,52)

def pad(c,pat,bar,ch,style='normal'):
    b=bar*16
    vol={'soft':52,'normal':44,'hard':48,'half':50,'build':46,'climax':50}.get(style,44)
    for j,note in enumerate(ch['pad']):
        c.cell(pat,b,8+j,note,10,vol,8,[64,128,192][j])

def arp(c,pat,bar,ch,style='16th',channel=7):
    b=bar*16
    if style=='off': return
    notes=ch['arp']
    if style=='8th':
        seq=[0,1,2,3,2,1,3,2]
        for i,r in enumerate(range(0,16,2)):
            c.cell(pat,b+r,channel,notes[seq[i]],11,30 if i%2==0 else 24)
    elif style=='16th':
        seq=[0,1,2,3,2,1,3,2,0,2,1,3,2,1,0,2]
        for i,r in enumerate(range(0,16,1)):
            c.cell(pat,b+r,channel,notes[seq[i]],11,32 if r%4==0 else (24 if r%2==0 else 18))
    elif style=='climax':
        seq=[0,2,1,3,2,0,3,1,2,3,1,2,0,1,3,2]
        for i,r in enumerate(range(0,16,1)):
            c.cell(pat,b+r,channel,notes[seq[i]],11,34 if r%4==0 else 22)

def fx(c,pat,row,kind='reverse',vol=55):
    if kind=='reverse': c.cell(pat,row,11,'C-4',15,vol)
    elif kind=='riser': c.cell(pat,row,11,'C-4',14,vol)
    elif kind=='crash': c.cell(pat,row,11,'C-4',5,vol)

def compose_pattern(pat, section):
    c=C()
    # section is a list of 4 chord names, plus style info
    chords=section['chords']; drum_style=section.get('drums','normal'); bass_style=section.get('bass','normal')
    arp_style=section.get('arp','16th'); pad_style=section.get('pad','normal'); sub_style=section.get('sub','normal')
    lead=section.get('lead'); harmony=section.get('harmony'); bell=section.get('bell')
    crash=section.get('crash',True); fill=section.get('fill',False); roll=section.get('roll',False); roll_start=section.get('roll_start',48)
    for bar in range(4):
        ch=CHORDS[chords[bar]]
        drums(c,pat,bar,drum_style,crash=(crash and bar==0),fill=(fill and bar==3),roll=roll,roll_start=roll_start)
        bass(c,pat,bar,ch,bass_style)
        sub(c,pat,bar,ch,sub_style)
        pad(c,pat,bar,ch,pad_style)
        arp(c,pat,bar,ch,arp_style,section.get('arp_channel',7))
    if lead:
        c.lead_line(pat,lead,ins=section.get('lead_ins',8),vol=section.get('lead_vol',58),fade=True)
    if harmony:
        # harmony on channel 7, use lead2
        c.lead_line(pat,harmony,ins=section.get('harm_ins',9),vol=section.get('harm_vol',48),fade=True)
        # Oops: lead_line always channel 6. Need a separate harmony function.
    if bell:
        # bell on channel 11
        for name,start,dur in bell:
            c.cell(pat,start,11,name,13,45)
            if start+dur < 64: c.cell(pat,start+dur,11,'OFF')
    # FX
    if section.get('echo'):
        for name,start,dur in lead:
            if start+2 <= 63:
                c.cell(pat,start+2,11,name,16 if dur>2 else 8,24,8,176)
                if start+2+dur < 64:
                    c.cell(pat,start+2+dur,11,'OFF')
    for row,kind,vol in section.get('fx',[]):
        fx(c,pat,row,kind,vol)
    return c.calls

# --- define sections ---
sections={}
# P0 Intro
sections[0]=dict(chords=['Am','F','C','G'],drums='soft',bass='soft',sub='soft',arp='8th',pad='soft',
    lead=[('E-5',48,4),('D-5',52,2),('C-5',54,2),('A-4',56,8)],
    bell=[('A-5',32,4),('E-5',40,4),('C-5',48,4),('A-4',56,8)],
    fx=[],crash=True)
# P1 Build
sections[1]=dict(chords=['Am','F','C','G'],drums='build',bass='normal',sub='normal',arp='16th',pad='build',
    lead=[('A-4',0,4),('C-5',4,4),('E-5',8,4),('A-5',12,4),('G-5',16,4),('F-5',20,4),('E-5',24,4),('C-5',28,4),('D-5',32,4),('E-5',36,4),('G-5',40,4),('A-5',44,4),('B-5',48,8),('E-6',56,8)],
    fx=[(32,'riser',55),(56,'reverse',50)],crash=True,roll=True,roll_start=48)
# P2 Main A1
sections[2]=dict(chords=['Am','F','C','G'],drums='normal',bass='normal',sub='normal',arp='16th',pad='normal',
    lead=[('E-5',0,4),('C-5',4,2),('D-5',6,2),('E-5',8,4),('A-5',12,4),
          ('F-5',16,4),('E-5',20,2),('C-5',22,2),('A-4',24,4),('C-5',28,4),
          ('E-5',32,2),('G-5',34,2),('E-5',36,2),('C-5',38,2),('D-5',40,4),('E-5',44,4),
          ('D-5',48,4),('B-4',52,2),('D-5',54,2),('G-5',56,4),('B-5',60,4)],
    fx=[],crash=True,echo=True,fill=True)
# P3 Main A2
sections[3]=dict(chords=['Am','F','C','E'],drums='hard',bass='normal',sub='normal',arp='16th',pad='normal',
    lead=[('A-5',0,2),('E-5',2,2),('C-5',4,2),('E-5',6,2),('A-5',8,4),('G-5',12,2),('E-5',14,2),
          ('F-5',16,4),('C-5',20,2),('A-4',22,2),('C-5',24,4),('F-5',28,4),
          ('G-5',32,2),('E-5',34,2),('C-5',36,2),('E-5',38,2),('G-5',40,4),('A-5',44,4),
          ('B-4',48,4),('G#4',52,2),('B-4',54,2),('E-5',56,4),('G#5',60,4)],
    fx=[],crash=True,fill=True,echo=True)
# P4 Chorus B1
sections[4]=dict(arp_channel=11,chords=['F','G','Am','Am'],drums='hard',bass='normal',sub='normal',arp='16th',pad='hard',
    lead=[('A-5',0,2),('G-5',2,2),('F-5',4,4),('E-5',8,2),('F-5',10,2),('A-5',12,4),
          ('G-5',16,2),('F-5',18,2),('E-5',20,4),('D-5',24,2),('E-5',26,2),('G-5',28,4),
          ('A-5',32,4),('E-5',36,2),('C-5',38,2),('D-5',40,4),('E-5',44,4),
          ('A-5',48,2),('B-5',50,2),('C-6',52,4),('B-5',56,2),('A-5',58,2),('E-5',60,4)],
    harmony=[('F-4',0,8),('A-4',8,8),('G-4',16,8),('B-4',24,8),('A-4',32,8),('E-5',40,8),('C-5',48,8),('A-4',56,8)],
    fx=[],crash=True,fill=True)
# P5 Chorus B2
sections[5]=dict(arp_channel=11,chords=['F','G','C','E'],drums='hard',bass='normal',sub='normal',arp='16th',pad='hard',
    lead=[('F-5',0,4),('A-5',4,2),('C-6',6,2),('A-5',8,4),('G-5',12,4),
          ('G-5',16,4),('B-5',20,2),('D-6',22,2),('B-5',24,4),('A-5',28,4),
          ('C-6',32,2),('B-5',34,2),('G-5',36,2),('E-5',38,2),('G-5',40,4),('C-6',44,4),
          ('B-5',48,4),('G#5',52,2),('E-5',54,2),('B-4',56,4),('E-5',60,4)],
    harmony=[('A-4',0,8),('C-5',8,8),('B-4',16,8),('D-5',24,8),('G-4',32,8),('E-5',40,8),('G-4',48,8),('B-4',56,8)],
    fx=[],crash=True,fill=True)
# P6 Breakdown
sections[6]=dict(chords=['Dm','Am','E','E'],drums='half',bass='half',sub='half',arp='8th',pad='half',
    lead=[('D-5',0,8),('F-5',8,8),('E-5',16,8),('C-5',24,8),('B-4',32,8),('G#5',40,8),('E-5',48,16)],
    bell=[('D-5',0,8),('F-5',8,8),('E-5',16,8),('C-5',24,8),('B-4',32,8),('G#5',40,8),('E-5',48,16)],
    fx=[],crash=True,fill=True)
# P7 Build 2
sections[7]=dict(chords=['Dm','Am','E','E'],drums='build',bass='normal',sub='normal',arp='16th',pad='build',
    lead=[('A-4',0,4),('D-5',4,4),('F-5',8,4),('A-5',12,4),('G-4',16,4),('C-5',20,4),('E-5',24,4),('A-5',28,4),('B-4',32,4),('E-5',36,4),('G#5',40,4),('B-5',44,4),('E-5',48,2),('E-5',50,2),('G#5',52,2),('B-5',54,2),('E-6',56,8)],
    fx=[(32,'riser',55),(56,'reverse',50)],crash=True,roll=True,roll_start=32)
# P8 Climax C1
sections[8]=dict(arp_channel=11,chords=['F','G','Em','Am'],drums='climax',bass='climax',sub='climax',arp='climax',pad='climax',
    lead=[('F-5',0,2),('A-5',2,2),('C-6',4,4),('A-5',8,2),('G-5',10,2),('F-5',12,4),
          ('G-5',16,2),('B-5',18,2),('D-6',20,4),('B-5',24,2),('A-5',26,2),('G-5',28,4),
          ('E-5',32,2),('G-5',34,2),('B-5',36,4),('E-6',40,4),('D-6',44,2),('B-5',46,2),
          ('C-6',48,4),('B-5',52,2),('A-5',54,2),('E-5',56,4),('A-5',60,4)],
    harmony=[('A-4',0,8),('C-5',8,8),('B-4',16,8),('D-5',24,8),('G-4',32,8),('B-4',40,8),('A-4',48,8),('E-5',56,8)],
    fx=[],crash=True,fill=True)
# P9 Climax C2
sections[9]=dict(arp_channel=11,chords=['F','G','C','E'],drums='climax',bass='climax',sub='climax',arp='climax',pad='climax',
    lead=[('A-5',0,2),('C-6',2,2),('F-6',4,4),('C-6',8,2),('A-5',10,2),('F-5',12,4),
          ('B-5',16,2),('D-6',18,2),('G-6',20,4),('D-6',24,2),('B-5',26,2),('G-5',28,4),
          ('C-6',32,2),('E-6',34,2),('G-6',36,4),('E-6',40,2),('C-6',42,2),('G-5',44,4),
          ('B-5',48,4),('G#5',52,2),('E-5',54,2),('B-4',56,4),('E-5',60,4)],
    harmony=[('F-4',0,8),('A-4',8,8),('G-4',16,8),('B-4',24,8),('E-4',32,8),('G-4',40,8),('G-4',48,8),('B-4',56,8)],
    fx=[],crash=True,fill=True)
# P10 Bridge
sections[10]=dict(chords=['Am','F','C','G'],drums='soft',bass='soft',sub='soft',arp='8th',pad='soft',
    lead=[('E-5',0,4),('A-5',4,4),('C-6',8,4),('B-5',12,4),
          ('A-5',16,4),('F-5',20,4),('C-5',24,4),('A-4',28,4),
          ('G-5',32,4),('E-5',36,4),('C-5',40,4),('E-5',44,4),
          ('D-5',48,4),('B-4',52,4),('G-4',56,4),('B-4',60,4)],
    bell=[('A-5',32,4),('G-5',36,4),('E-5',40,4),('D-5',44,4)],
    fx=[(48,'reverse',45)],crash=True,fill=True)
# P11 Outro
sections[11]=dict(chords=['Am','F','C','Am'],drums='normal',bass='normal',sub='normal',arp='8th',pad='soft',
    lead=[('A-5',0,4),('E-5',4,2),('C-5',6,2),('A-4',8,8),
          ('F-5',16,4),('C-5',20,4),('A-4',24,8),
          ('E-5',32,4),('G-5',36,4),('C-5',40,8),
          ('A-5',48,4),('E-5',52,4),('A-4',56,8)],
    bell=[('A-4',56,8)],
    fx=[(48,'reverse',50)],crash=True,fill=True)

# fix harmony channel: our lead_line always channel 6, so define a separate harmony function in compose_pattern
def compose_pattern(pat, section):
    c=C()
    chords=section['chords']; drum_style=section.get('drums','normal'); bass_style=section.get('bass','normal')
    arp_style=section.get('arp','16th'); pad_style=section.get('pad','normal'); sub_style=section.get('sub','normal')
    lead=section.get('lead'); harmony=section.get('harmony'); bell=section.get('bell')
    crash=section.get('crash',True); fill=section.get('fill',False); roll=section.get('roll',False); roll_start=section.get('roll_start',48)
    for bar in range(4):
        ch=CHORDS[chords[bar]]
        drums(c,pat,bar,drum_style,crash=(crash and bar==0),fill=(fill and bar==3),roll=roll,roll_start=roll_start)
        bass(c,pat,bar,ch,bass_style)
        sub(c,pat,bar,ch,sub_style)
        pad(c,pat,bar,ch,pad_style)
        arp(c,pat,bar,ch,arp_style,section.get('arp_channel',7))
    if lead:
        c.lead_line(pat,lead,ins=section.get('lead_ins',8),vol=section.get('lead_vol',58),fade=True)
    if harmony:
        # place on channel 7 with same fade logic
        notes=sorted(harmony,key=lambda x:x[1])
        for i,(name,start,dur) in enumerate(notes):
            c.cell(pat,start,7,name,section.get('harm_ins',9),section.get('harm_vol',48))
            end=start+dur; nxt=notes[i+1][1] if i+1<len(notes) else 999
            if end < nxt:
                if end-1>start: c.cell(pat,min(63,end-1),7,None,None,None,0xA,0x0F)
                c.cell(pat,min(63,end),7,'OFF')
            elif end == nxt and end-1>start:
                c.cell(pat,end-1,7,None,None,None,0xA,0x0F)
    if bell:
        for name,start,dur in bell:
            c.cell(pat,start,11,name,13,45)
            if start+dur < 64: c.cell(pat,start+dur,11,'OFF')
    if section.get('echo'):
        for name,start,dur in lead:
            if start+2 <= 63:
                c.cell(pat,start+2,11,name,16 if dur>2 else 8,24,8,176)
                if start+2+dur < 64:
                    c.cell(pat,start+2+dur,11,'OFF')
    for row,kind,vol in section.get('fx',[]):
        fx(c,pat,row,kind,vol)
    return c.calls

for p in range(12):
    calls=compose_pattern(p,sections[p])
    with open(f'/workspace/work/pat_{p}.json','w') as f: json.dump(calls,f)
    print(p,len(calls))
