import numpy as np, base64, json, socket, math, re

def ft2_call(name, args):
    import json, socket
    raw=json.dumps({"op":"call","name":name,"arguments":args}).encode()+b"\n"
    s=socket.socket(socket.AF_UNIX)
    s.connect("/tmp/keygen-ft2.sock")
    s.sendall(raw)
    with s.makefile("rb") as r:
        line=r.readline(240*1024+1)
    s.close()
    reply=json.loads(line)
    if "error" in reply:
        raise RuntimeError(reply["error"])
    txt=reply["result"]["content"][0]["text"] if reply["result"]["content"] else ""
    try:
        return json.loads(txt)
    except:
        return txt

def b64_pcm(pcm):
    i16=(np.clip(pcm,-1,1)*32767).astype(np.int16)
    return base64.b64encode(i16.tobytes()).decode()

def note_num(name):
    m=re.match(r"([A-G])([#b]?)[- ]?(\d)", name.strip())
    if not m: raise ValueError(f"bad note {name}")
    letter, acc, octv=m.groups()
    octv=int(octv)
    semitones={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
    semi=semitones[letter]
    if acc=="#": semi+=1
    elif acc=="b": semi-=1
    semi%=12
    return octv*12 + semi +1

raw_rate=8363
ref_tone=523.2511306

def make_bass():
    tone=ref_tone
    dur_total=1.0
    attack=0.018
    N_total=int(raw_rate*dur_total)
    N_attack=int(raw_rate*attack)
    phase=np.arange(N_total)*(tone/raw_rate)
    saw=2*(phase%1)-1
    sub=np.sin(2*np.pi*phase*0.5)
    pcm=saw*0.35 + sub*0.55
    alpha=0.35
    y=np.zeros_like(pcm)
    y[0]=pcm[0]
    for i in range(1,len(pcm)):
        y[i]=alpha*pcm[i] + (1-alpha)*y[i-1]
    pcm=y
    env=np.ones(N_total)
    env[:N_attack]=np.linspace(0,1,N_attack)
    env[N_attack:]=0.85 + 0.15*np.exp(-np.arange(N_total-N_attack)/(raw_rate*0.15))
    pcm=pcm*env*0.9
    pcm=pcm/np.max(np.abs(pcm))*0.85
    loop_start=N_attack
    cycle_len=raw_rate/tone
    best=loop_start
    minp=1
    for i in range(loop_start, min(loop_start+int(cycle_len)+5, N_total)):
        ph=phase[i]%1
        dist=min(ph,1-ph)
        if dist<minp:
            minp=dist
            best=i
            if dist<0.02: break
    loop_start=best
    loop_len=N_total-loop_start
    cycles=int(loop_len/cycle_len)
    loop_len=int(cycles*cycle_len)
    return pcm, loop_start, loop_len

def make_lead():
    tone=ref_tone
    dur_total=1.2
    attack=0.006
    N_total=int(raw_rate*dur_total)
    N_attack=int(raw_rate*attack)
    detune=7
    ratio=2**(detune/1200)
    phase1=np.arange(N_total)*(tone/ratio/raw_rate)
    phase2=np.arange(N_total)*(tone*ratio/raw_rate)
    saw1=2*(phase1%1)-1
    saw2=2*(phase2%1)-1
    sq=np.where((phase1%1)<0.3,1,-1)*0.3
    pcm=saw1*0.35 + saw2*0.35 + sq*0.3
    env=np.ones(N_total)
    env[:N_attack]=np.linspace(0,1,N_attack)
    env[N_attack:]=0.85 + 0.15*np.exp(-np.arange(N_total-N_attack)/(raw_rate*0.4))
    pcm=pcm*env
    pcm=np.tanh(pcm*1.2)*0.85
    pcm=pcm/np.max(np.abs(pcm))*0.82
    loop_start=N_attack+int(raw_rate*0.02)
    phase_avg=(phase1+phase2)/2
    best=loop_start
    minp=1
    for i in range(loop_start, min(loop_start+20, N_total)):
        ph=phase_avg[i]%1
        dist=min(ph,1-ph)
        if dist<minp:
            minp=dist
            best=i
            if dist<0.02: break
    loop_start=best
    cycle_len=raw_rate/tone
    loop_len=N_total-loop_start
    cycles=int(loop_len/cycle_len)
    loop_len=int(cycles*cycle_len)
    return pcm, loop_start, loop_len

def make_pad():
    tone=ref_tone
    dur_total=2.0
    attack=0.18
    N_total=int(raw_rate*dur_total)
    N_attack=int(raw_rate*attack)
    cents=[-6,0,7]
    pcm=np.zeros(N_total)
    for c in cents:
        ratio=2**(c/1200)
        phase=np.arange(N_total)*(tone*ratio/raw_rate)
        saw=2*(phase%1)-1
        pcm+=saw*(0.33)
    phase_sub=np.arange(N_total)*(tone*0.5/raw_rate)
    pcm+=np.sin(2*np.pi*phase_sub)*0.15
    alpha=0.22
    y=np.zeros_like(pcm)
    y[0]=pcm[0]
    for i in range(1,len(pcm)):
        y[i]=alpha*pcm[i] + (1-alpha)*y[i-1]
    pcm=y
    env=np.ones(N_total)
    env[:N_attack]=np.linspace(0,1,N_attack)**1.5
    env[N_attack:]=0.75 + 0.25*np.exp(-np.arange(N_total-N_attack)/(raw_rate*1.0))
    pcm=pcm*env*0.9
    pcm=pcm/np.max(np.abs(pcm))*0.78
    loop_start=N_attack
    phase=np.arange(N_total)*(tone/raw_rate)
    best=loop_start
    minp=1
    for i in range(loop_start, min(loop_start+20, N_total)):
        ph=phase[i]%1
        dist=min(ph,1-ph)
        if dist<minp:
            minp=dist
            best=i
            if dist<0.02: break
    loop_start=best
    cycle_len=raw_rate/tone
    loop_len=N_total-loop_start
    cycles=int(loop_len/cycle_len)
    loop_len=int(cycles*cycle_len)
    return pcm, loop_start, loop_len

def make_arp():
    tone=ref_tone
    dur_total=0.9
    attack=0.002
    N_total=int(raw_rate*dur_total)
    N_attack=int(raw_rate*attack)
    phase=np.arange(N_total)*(tone/raw_rate)
    sq=np.where((phase%1)<0.5,1,-1)
    sq2=np.where(((phase*2)%1)<0.5,1,-1)*0.25
    pcm=sq*0.6 + sq2*0.2
    pcm+=np.sin(2*np.pi*phase)*0.15
    env=np.ones(N_total)
    env[:N_attack]=np.linspace(0,1,N_attack)
    decay_len=int(raw_rate*0.12)
    env[N_attack:N_attack+decay_len]=np.linspace(1,0.32,decay_len)
    env[N_attack+decay_len:]=0.32
    pcm=pcm*env
    pcm=np.tanh(pcm*1.1)*0.85
    pcm=pcm/np.max(np.abs(pcm))*0.8
    loop_start=N_attack+decay_len
    best=loop_start
    minp=1
    for i in range(loop_start, min(loop_start+20, N_total)):
        ph=phase[i]%1
        dist=min(ph,1-ph)
        if dist<minp:
            minp=dist
            best=i
            if dist<0.02: break
    loop_start=best
    cycle_len=raw_rate/tone
    loop_len=N_total-loop_start
    cycles=int(loop_len/cycle_len)
    loop_len=int(cycles*cycle_len)
    return pcm, loop_start, loop_len

def make_kick():
    dur=0.28
    N=int(raw_rate*dur)
    t=np.arange(N)/raw_rate
    env=np.exp(-t/0.12)
    click_env=np.exp(-t/0.006)
    f_start=165
    f_end=42
    freq=f_end + (f_start-f_end)*np.exp(-t/0.065)
    phase=np.cumsum(freq/raw_rate)
    pcm=np.sin(2*np.pi*phase)*env
    pcm+=np.sin(2*np.pi*1200*t)*click_env*0.25
    pcm=np.tanh(pcm*1.3)*0.95
    fade=int(raw_rate*0.02)
    pcm[-fade:]*=np.linspace(1,0,fade)
    pcm=pcm/np.max(np.abs(pcm))*0.92
    return pcm

def make_snare():
    dur=0.32
    N=int(raw_rate*dur)
    t=np.arange(N)/raw_rate
    np.random.seed(1)
    noise=np.random.uniform(-1,1,N)
    alpha=0.25
    lp=np.zeros(N)
    lp[0]=noise[0]
    for i in range(1,N):
        lp[i]=alpha*noise[i] + (1-alpha)*lp[i-1]
    hp=noise - lp*0.8
    env_noise=np.exp(-t/0.09)
    env_noise[:int(raw_rate*0.005)]=np.linspace(0,1,int(raw_rate*0.005))
    tone_freq=185
    tone=np.sin(2*np.pi*tone_freq*t)*np.exp(-t/0.15)
    tone+=np.sin(2*np.pi*360*t)*np.exp(-t/0.12)*0.25
    pcm=hp*env_noise*0.65 + tone*0.55
    pcm=np.tanh(pcm*1.1)*0.9
    fade=int(raw_rate*0.015)
    pcm[-fade:]*=np.linspace(1,0,fade)
    pcm=pcm/np.max(np.abs(pcm))*0.88
    return pcm

def make_hat_closed():
    dur=0.13
    N=int(raw_rate*dur)
    t=np.arange(N)/raw_rate
    np.random.seed(2)
    noise=np.random.uniform(-1,1,N)
    alpha=0.12
    lp=np.zeros(N)
    lp[0]=noise[0]
    for i in range(1,N):
        lp[i]=alpha*noise[i] + (1-alpha)*lp[i-1]
    hp=noise - lp
    metallic_freqs=[820,1230,1750,2400,3100,3800]
    metallic=np.zeros(N)
    for f in metallic_freqs:
        if f < raw_rate/2:
            metallic+=np.sin(2*np.pi*f*t)*np.exp(-t/0.07)*0.18
    pcm=hp*0.55*np.exp(-t/0.045) + metallic*0.35
    env=np.exp(-t/0.055)
    pcm=pcm*env
    pcm=np.tanh(pcm*1.2)*0.85
    fade=int(raw_rate*0.008)
    pcm[-fade:]*=np.linspace(1,0,fade)
    pcm=pcm/np.max(np.abs(pcm))*0.75
    return pcm

def make_hat_open():
    dur=0.42
    N=int(raw_rate*dur)
    t=np.arange(N)/raw_rate
    np.random.seed(3)
    noise=np.random.uniform(-1,1,N)
    alpha=0.12
    lp=np.zeros(N)
    lp[0]=noise[0]
    for i in range(1,N):
        lp[i]=alpha*noise[i] + (1-alpha)*lp[i-1]
    hp=noise - lp
    metallic_freqs=[820,1230,1750,2400,3100,3800]
    metallic=np.zeros(N)
    for f in metallic_freqs:
        if f < raw_rate/2:
            metallic+=np.sin(2*np.pi*f*t)*np.exp(-t/0.18)*0.18
    pcm=hp*0.5*np.exp(-t/0.12) + metallic*0.4
    env=np.exp(-t/0.18)
    pcm=pcm*env
    pcm=np.tanh(pcm*1.15)*0.85
    fade=int(raw_rate*0.02)
    pcm[-fade:]*=np.linspace(1,0,fade)
    pcm=pcm/np.max(np.abs(pcm))*0.72
    return pcm

# Create module
print("Creating module")
ft2_call("module_new", {"channels":10, "name":"KEYGEN LOOP"})
ft2_call("song_set", {"bpm":138, "speed":6, "loop_start":0, "length":4})
# set order
for i in range(4):
    ft2_call("order_set", {"position":i, "pattern":i})
for pat in range(4):
    ft2_call("pattern_set_length", {"pattern":pat, "rows":64})

# Instruments: 1 kick, 2 snare, 3 hat closed, 4 hat open, 5 bass, 6 lead, 7 pad, 8 arp
instruments = [
    (1, "Kick", make_kick(), None, 44, 128),
    (2, "Snare", make_snare(), None, 44, 128),
    (3, "HatClosed", make_hat_closed(), None, 30, 180),
    (4, "HatOpen", make_hat_open(), None, 30, 180),
]
# melodic with loops
bass_pcm, bass_start, bass_len = make_bass()
lead_pcm, lead_start, lead_len = make_lead()
pad_pcm, pad_start, pad_len = make_pad()
arp_pcm, arp_start, arp_len = make_arp()
instruments += [
    (5, "Bass", bass_pcm, (bass_start, bass_len), 42, 128),
    (6, "Lead", lead_pcm, (lead_start, lead_len), 38, 120),
    (7, "Pad", pad_pcm, (pad_start, pad_len), 28, 128),
    (8, "Arp", arp_pcm, (arp_start, arp_len), 26, 128),
]

import os
os.makedirs("/workspace/submission", exist_ok=True)

for inst, name, pcm, loop, vol, pan in instruments:
    b64=b64_pcm(pcm)
    print(f"Creating instrument {inst} {name} len {len(pcm)} loop {loop}")
    ft2_call("sample_create_from_pcm", {"instrument":inst, "pcm":b64, "encoding":"int16", "name":name})
    ft2_call("instrument_set", {"instrument":inst, "name":name})
    if loop:
        start,length=loop
        ft2_call("sample_set", {"instrument":inst, "sample":0, "loop_start":start, "loop_length":length, "flags":1, "volume":vol, "panning":pan})
    else:
        ft2_call("sample_set", {"instrument":inst, "sample":0, "loop_start":0, "loop_length":0, "flags":0, "volume":vol, "panning":pan})

# Helper to set cell
def put(pat,row,ch,note_name,inst,vol=0,eff=0,par=0):
    n=note_num(note_name) if isinstance(note_name,str) else note_name
    args={"pattern":pat,"row":row,"channel":ch,"note":n,"instrument":inst}
    if vol: args["volume"]=vol
    if eff: args["effect"]=eff
    if par: args["effect_param"]=par
    ft2_call("pattern_set_cell", args)

def put_drum(pat,row,ch,inst):
    # drums at C-5 61 to preserve
    put(pat,row,ch,"C-5",inst)

# Define chords
chord_notes = {
    "Fm": ["F-3","Ab3","C-4"],
    "Db": ["Db3","F-3","Ab3"],
    "Ab": ["Ab3","C-4","Eb4"],
    "Eb": ["Eb3","G-3","Bb3"],
}
bass_roots = {"Fm":"F-2","Db":"Db2","Ab":"Ab2","Eb":"Eb2"}

pattern_chords = [
    ["Fm","Db"],
    ["Ab","Eb"],
    ["Fm","Db"],
    ["Ab","Eb"],
]

# Drum pattern filling
# For each pattern, fill 64 rows with drums
for pat in range(4):
    for row in range(64):
        bar = row //16
        row_in_bar=row%16
        # hats: every 2 rows (8th notes)
        if row_in_bar%2==0:
            # decide open vs closed: open on some positions (e.g., row_in_bar 14 in certain bars)
            # Use open hat at row 14 of bars 1 and 3, else closed
            # Also occasional open at row 6
            is_open=False
            # open hat pattern: bars 1,3? we make open at bar ends
            if row_in_bar==14 and bar in [1,3]:
                # open hat open (instr 4) else closed
                # for pattern 3 last bar (bar3 of pat3) use open more?
                if pat==3 and bar==3 and row==62:
                    is_open=True
                elif bar%2==1:
                    is_open=True
            if row_in_bar==6 and pat==2 and bar==2:
                is_open=True
            if is_open:
                put_drum(pat,row,2,4) # hat open on channel2
            else:
                # hat closed
                put_drum(pat,row,2,3)
        # kick
        # kick positions: rows 0,8 per bar, plus ghost 6 and 14 variations
        kick_pos=False
        if row_in_bar in [0,8]:
            kick_pos=True
        # add ghost kick at row 6 for funk in some bars
        if row_in_bar==6 and pat in [0,2] and bar in [0,2]:
            kick_pos=True
        if row_in_bar==14 and pat==1 and bar==3:
            kick_pos=True # fill
        if kick_pos:
            put_drum(pat,row,0,1)
        # snare at 4,12 per bar
        snare_pos=False
        if row_in_bar in [4,12]:
            snare_pos=True
        # fill variations: add snare at row 10 for some bars
        if row_in_bar==10 and pat==3 and bar==3:
            snare_pos=True
        if row_in_bar==11 and pat==3 and bar==3:
            # roll
            put_drum(pat,row,1,2)
            continue
        if snare_pos:
            put_drum(pat,row,1,2)

# Now pads: sustained chords
for pat in range(4):
    chords=pattern_chords[pat]
    for seg_idx, chord in enumerate(chords):
        base_row=seg_idx*32
        notes=chord_notes[chord]
        # Pad voices on channels 5,6,7 (index 5,6,7)
        for v, n in enumerate(notes):
            ch=5+v
            put(pat, base_row, ch, n, 7)
            # optional: set panning effect for stereo spread on first row of each chord
            # Use effect 8 panning: 0x40 left, 0x80 center, 0xC0 right
            # We'll set effect 8 via same cell? But we already placed note; need to set effect param separately? The cell includes effect.
            # For pad we can add effect 8 after placement: we already have note; we can set effect via separate call? pattern_set_cell will overwrite.
            # So we need to set effect at same time as note.
            # Let's create separate logic to set panning via effect 8 on first row.
            # We'll redo with effect.
            pan_vals=[64,128,192] # left, center, right (0-255)
            # effect 8 param is panning 0-255 decimal? Use same.
            # We'll set effect 8 for each pad voice at base_row
            # So need to re-put with effect
            ft2_call("pattern_set_cell", {"pattern":pat,"row":base_row,"channel":ch,"note":note_num(n),"instrument":7,"effect":8,"effect_param":pan_vals[v]})

# Bass
# Bass pattern per chord segment, playing root and movement
bass_patterns = {
    "Fm": [("F-2",0),("F-3",4),("C-3",8),("F-2",12),("Ab2",16),("C-3",20),("F-2",24),("Eb2",28)],
    "Db": [("Db2",0),("Ab2",8),("Db2",12),("F-2",16),("Ab2",20),("Db3",24),("C-3",28)],
    "Ab": [("Ab2",0),("Eb3",8),("Ab2",12),("C-3",16),("Eb3",20),("Ab2",24),("G-2",28)],
    "Eb": [("Eb2",0),("Bb2",8),("Eb2",12),("G-2",16),("Bb2",20),("Eb3",24),("D-3",28)],
    # Could also define variations for pattern2/3?
}
# For pattern2/3 variations, we could slightly vary last segment
for pat in range(4):
    chords=pattern_chords[pat]
    for seg_idx, chord in enumerate(chords):
        base=seg_idx*32
        seq=bass_patterns[chord]
        for n, offset in seq:
            row=base+offset
            if row<64:
                put(pat,row,3,n,5) # bass chan3 inst5

# Arp: fast arpeggio per segment, every 2 rows 16 notes
arp_chord_notes = {
    "Fm": ["F-4","Ab4","C-5","Ab4"],
    "Db": ["Db4","F-4","Ab4","F-4"],
    "Ab": ["Ab4","C-5","Eb5","C-5"],
    "Eb": ["Eb4","G-4","Bb4","G-4"],
}
for pat in range(4):
    chords=pattern_chords[pat]
    for seg_idx, chord in enumerate(chords):
        base=seg_idx*32
        seq=arp_chord_notes[chord]
        for i in range(16): # 16 notes over 32 rows => every 2 rows
            row=base+i*2
            if row>=64: continue
            note_seq=seq[i%len(seq)]
            put(pat,row,8,note_seq,8) # channel 8 arp inst8

# Lead: melody
# Define lead melodies per segment (8 segments total, but we map pat+seg)
# We'll define per pattern
lead_segments = {
    # pat0 seg Fm
    (0,0): [("F-4",0),("Ab4",4),("C-5",8),("Bb4",12),("Ab4",16),("G-4",20),("F-4",24),("Eb4",28)],
    (0,1): [("Db5",0),("C-5",4),("Bb4",8),("Ab4",12),("F-4",16),("Ab4",20),("G-4",24),("F-4",28)],
    (1,0): [("Ab4",0),("C-5",4),("Eb5",8),("C-5",12),("Bb4",16),("Ab4",20),("G-4",24),("Eb4",28)],
    (1,1): [("Eb5",0),("G-4",4),("Bb4",8),("G-4",12),("Eb4",16),("F-4",20),("G-4",24),("Ab4",28)],
    (2,0): [("F-4",0),("G-4",2),("Ab4",6),("C-5",10),("Bb4",14),("Ab4",18),("G-4",22),("F-4",26),("Eb4",30)],
    (2,1): [("Db5",0),("C-5",4),("Bb4",8),("Ab4",12),("F-4",16),("Ab4",20),("G-4",24),("F-4",28)],
    (3,0): [("Ab4",0),("C-5",4),("Eb5",8),("C-5",12),("Bb4",16),("Ab4",20),("G-4",24),("Eb4",28)],
    (3,1): [("Eb4",0),("G-4",4),("Bb4",8),("Ab4",12),("G-4",16),("F-4",20),("Eb4",24),("D-4",28),("F-4",31)], # last holds to loop
}
for (pat, seg), seq in lead_segments.items():
    base=seg*32
    for n, offset in seq:
        row=base+offset
        if row>=64: continue
        put(pat,row,4,n,6)

# Now save and render
print("Saving")
ft2_call("module_save", {"path":"/workspace/submission/tune.xm","format":"xm"})
print("Rendering")
ft2_call("module_render", {"path":"/tmp/preview.wav","rate":44100})
print("Done")

