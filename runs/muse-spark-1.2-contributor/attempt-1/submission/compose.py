import numpy as np, wave, os, json, subprocess, random

sr=44100

# synthesis same as before (reuse definitions shortened)
def gen_kick():
    dur=0.45
    n=int(sr*dur)
    t=np.arange(n)/sr
    f0=160; f1=42
    freq = f1 + (f0-f1)*np.exp(-t*38)
    phase=2*np.pi*np.cumsum(freq)/sr
    amp=np.exp(-t*14)
    wave=np.sin(phase)*amp
    click_n=int(sr*0.004)
    click=0.35*np.sin(2*np.pi*1200*np.arange(click_n)/sr)*np.exp(-np.arange(click_n)/(sr*0.001))
    wave[:click_n]+=click
    wave=np.tanh(wave*1.45)*0.92
    fade=int(sr*0.03)
    wave[-fade:]*=np.linspace(1,0,fade)
    return (wave*32767).astype(np.int16)

def gen_snare():
    dur=0.38
    n=int(sr*dur)
    t=np.arange(n)/sr
    tone=0.55*np.sin(2*np.pi*180*t)*np.exp(-t*20)+0.25*np.sin(2*np.pi*330*t)*np.exp(-t*35)
    np.random.seed(0)
    noise=np.random.randn(n)
    fc_lp=1200
    alpha_lp=2*np.pi*fc_lp/sr; alpha_lp=min(0.3,alpha_lp)
    lpf=np.zeros_like(noise)
    lpf[0]=noise[0]*alpha_lp
    for i in range(1,n):
        lpf[i]=lpf[i-1]*(1-alpha_lp)+noise[i]*alpha_lp
    noise_hp=noise - lpf
    env=0.9*np.exp(-t*18)+0.6*np.exp(-t*85)*(t<0.04)
    env[0:int(sr*0.008)]*=2.0
    noise_comp=noise_hp*env*0.75
    wave=tone*0.7+noise_comp
    wave=wave/np.max(np.abs(wave))*0.88
    fade=int(sr*0.02)
    wave[-fade:]*=np.linspace(1,0,fade)
    return (wave*32767).astype(np.int16)

def gen_hclosed():
    dur=0.09
    n=int(sr*dur)
    t=np.arange(n)/sr
    np.random.seed(1)
    noise=np.random.randn(n)
    fc_hp=5500
    alpha_hp=1/(1+2*np.pi*fc_hp/sr)
    hp=np.zeros(n); hp[0]=noise[0]
    for i in range(1,n):
        hp[i]=alpha_hp*(hp[i-1]+noise[i]-noise[i-1])
    fc_lp=12000
    alpha_lp=2*np.pi*fc_lp/sr/(1+2*np.pi*fc_lp/sr)
    lp=np.zeros_like(hp); lp[0]=hp[0]*alpha_lp
    for i in range(1,n):
        lp[i]=lp[i-1]*(1-alpha_lp)+hp[i]*alpha_lp
    wave=lp*np.exp(-t*80)*1.6
    wave=np.clip(wave,-1.2,1.2)
    wave=wave/np.max(np.abs(wave))*0.52
    fade=int(sr*0.01)
    wave[-fade:]*=np.linspace(1,0,fade)
    return (wave*32767).astype(np.int16)

def gen_hopen():
    dur=0.42
    n=int(sr*dur)
    t=np.arange(n)/sr
    np.random.seed(2)
    noise=np.random.randn(n)
    fc_hp=4800
    alpha_hp=1/(1+2*np.pi*fc_hp/sr)
    hp=np.zeros(n); hp[0]=noise[0]
    for i in range(1,n):
        hp[i]=alpha_hp*(hp[i-1]+noise[i]-noise[i-1])
    fc_lp=11000
    alpha_lp=2*np.pi*fc_lp/sr/(1+2*np.pi*fc_lp/sr)
    lp=np.zeros_like(hp); lp[0]=hp[0]*alpha_lp
    for i in range(1,n):
        lp[i]=lp[i-1]*(1-alpha_lp)+hp[i]*alpha_lp
    wave=lp*np.exp(-t*9)*1.2
    wave=np.clip(wave,-1.2,1.2)
    wave=wave/np.max(np.abs(wave))*0.46
    fade=int(sr*0.02)
    wave[-fade:]*=np.linspace(1,0,fade)
    return (wave*32767).astype(np.int16)

def gen_bass():
    dur=1.1
    n=int(sr*dur)
    t=np.arange(n)/sr
    freq=261.63
    phase=(t*freq)%1.0
    saw=2*phase-1
    fc=900
    alpha=2*np.pi*fc/sr/(1+2*np.pi*fc/sr)
    lpf=np.zeros_like(saw); lpf[0]=saw[0]*alpha
    for i in range(1,n):
        lpf[i]=lpf[i-1]*(1-alpha)+saw[i]*alpha
    sub=np.sin(2*np.pi*freq*0.5*t)*0.45
    square=np.sign(saw)*0.15
    wave=lpf*0.65+sub*0.6+square*0.12
    attack=int(sr*0.008); decay=int(sr*0.07); release=int(sr*0.14)
    sustain=0.78
    env=np.ones(n)
    env[:attack]=np.linspace(0,1,attack)
    env[attack:attack+decay]=np.linspace(1,sustain,decay)
    env[-release:]=np.linspace(sustain,0,release)
    wave=wave*env
    wave=np.tanh(wave*1.12)
    wave=wave/np.max(np.abs(wave))*0.92
    return (wave*32767).astype(np.int16)

def gen_lead():
    dur=1.6
    n=int(sr*dur)
    t=np.arange(n)/sr
    base=261.63
    cents=[-20,-12,-7,0,7,12,20]
    wave=np.zeros(n)
    for c in cents:
        f=base*(2**(c/1200))
        phase=(t*f)%1.0
        saw=2*phase-1
        wave+=saw*(0.48 if c==0 else 0.22)
    wave/=2.5
    fc=3800
    alpha=2*np.pi*fc/sr/(1+2*np.pi*fc/sr)
    lpf=np.zeros_like(wave); lpf[0]=wave[0]*alpha
    for i in range(1,n):
        lpf[i]=lpf[i-1]*(1-alpha)+wave[i]*alpha
    wave=lpf
    attack=int(sr*0.012); decay=int(sr*0.06); release=int(sr*0.18)
    sustain=0.82
    env=np.ones(n)
    env[:attack]=np.linspace(0,1,attack)
    env[attack:attack+decay]=np.linspace(1,sustain,decay)
    env[-release:]=np.linspace(sustain,0,release)
    wave=wave*env
    wave=np.tanh(wave*1.32)
    wave=wave/np.max(np.abs(wave))*0.86
    return (wave*32767).astype(np.int16)

def gen_bell():
    dur=1.7
    n=int(sr*dur)
    t=np.arange(n)/sr
    base=261.63
    mod_env=np.exp(-t*3.2)*4.0
    phase_mod=np.sin(2*np.pi*base*t)*mod_env
    carrier=np.sin(2*np.pi*base*t+phase_mod)
    mod2_env=np.exp(-t*8)*1.2
    phase_mod2=np.sin(2*np.pi*base*3*t)*mod2_env
    carrier2=np.sin(2*np.pi*base*2*t+phase_mod2)*np.exp(-t*2.5)*0.35
    wave=carrier*0.65+carrier2*0.22
    wave+=0.18*np.sin(2*np.pi*base*t)*np.exp(-t*1.1)
    env=np.exp(-t*1.9)
    attack=int(sr*0.002)
    env[:attack]=np.linspace(0,1,attack)
    wave=wave*env*1.4
    wave=np.tanh(wave*0.9)
    wave=wave/np.max(np.abs(wave))*0.82
    release=int(sr*0.12)
    wave[-release:]*=np.linspace(1,0,release)
    return (wave*32767).astype(np.int16)

def gen_pad():
    dur=2.3
    n=int(sr*dur)
    t=np.arange(n)/sr
    base=261.63
    waves=[]
    for det in [-7,7]:
        f=base*(2**(det/1200))
        phase=(t*f)%1.0
        saw=2*phase-1
        waves.append(saw)
    saw_mix=(waves[0]+waves[1])/2*0.55
    sub=np.sin(2*np.pi*base*0.5*t)*0.38
    square=np.sign(saw_mix)*0.08
    wave=saw_mix+sub+square
    fc=1450
    alpha=2*np.pi*fc/sr/(1+2*np.pi*fc/sr)
    lpf=np.zeros_like(wave); lpf[0]=wave[0]*alpha
    for i in range(1,n):
        lpf[i]=lpf[i-1]*(1-alpha)+wave[i]*alpha
    wave=lpf
    lfo=np.sin(2*np.pi*0.7*t)*0.08+1
    wave=wave*lfo
    attack=int(sr*0.12); decay=int(sr*0.35); release=int(sr*0.30)
    sustain=0.86
    env=np.ones(n)
    env[:attack]=np.linspace(0,1,attack)
    env[attack:attack+decay]=np.linspace(1,sustain,decay)
    env[-release:]=np.linspace(sustain,0,release)
    wave=wave*env
    wave=np.tanh(wave*1.0)
    wave=wave/np.max(np.abs(wave))*0.80
    return (wave*32767).astype(np.int16)

print("gen wavs")
os.makedirs("/tmp/instr", exist_ok=True)
wavs={}
for name, fn in [("kick",gen_kick),("snare",gen_snare),("hclosed",gen_hclosed),("hopen",gen_hopen),("bass",gen_bass),("lead",gen_lead),("bell",gen_bell),("pad",gen_pad)]:
    pcm=fn()
    path=f"/tmp/instr/{name}.wav"
    with wave.open(path,"w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    wavs[name]=path
    print(name, pcm.shape)

def ft2call(name, args):
    import subprocess, json
    c=["ft2","call",name,json.dumps(args)]
    r=subprocess.run(c, capture_output=True, text=True)
    print(f"{name} ok? {r.stdout[:250]}")
    return r

ft2call("module_new", {"channels":8,"name":"Keygen Dream v1"})
ft2call("song_set", {"bpm":148,"speed":6,"name":"Keygen Dream | Cracktro 2025"})
for p in range(8):
    ft2call("pattern_set_length", {"pattern":p,"rows":64})

# lower volumes to avoid clipping
instr_map=[
    (1, wavs["kick"], "Kick", 56, 128),
    (2, wavs["snare"], "Snare", 38, 128),
    (3, wavs["hclosed"], "HatCls", 28, 80), # more left
    (4, wavs["hopen"], "HatOpen", 26, 176), # more right
    (5, wavs["bass"], "Bass", 48, 128),
    (6, wavs["lead"], "Lead", 42, 128),
    (7, wavs["bell"], "Bell", 36, 128),
    (8, wavs["pad"], "Pad", 30, 128),
]
for instr, path, name, vol, pan in instr_map:
    ft2call("sample_load", {"path":path,"instrument":instr,"sample":0})
    ft2call("instrument_set", {"instrument":instr,"name":name})
    ft2call("sample_set", {"instrument":instr,"sample":0,"volume":vol,"panning":pan,"flags":0,"loop_start":0,"loop_length":0})

ft2call("song_set", {"length":8,"loop_start":1}) # loop from 1 to keep intro once
for pos in range(8):
    ft2call("order_set", {"position":pos,"pattern":pos})

batch=[]
def add_batch(name, args):
    batch.append({"name":name,"arguments":args})

pc_map={"C":0,"C#":1,"D":2,"D#":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}
pc_names_sharp=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def parse_note(s):
    if "-" in s:
        parts=s.split("-"); pc=parts[0]; octv=int(parts[1])
    else:
        i=0
        while i<len(s) and not s[i].isdigit():
            i+=1
        pc=s[:i]; octv=int(s[i:])
    return pc, octv
def note_to_midi(s):
    pc,octv=parse_note(s); return octv*12+pc_map[pc]
def midi_to_note(midi):
    octv=midi//12; pc=midi%12; name=pc_names_sharp[pc]
    return f"{name}{octv}" if "#" in name else f"{name}-{octv}"
def place(pattern,row,channel,note_str,instr,vol=0):
    d={"pattern":pattern,"row":row,"channel":channel,"note":note_str,"instrument":instr}
    if vol: d["volume"]=vol
    add_batch("pattern_set_cell",d)

chord_prog=[
    {"name":"Em7","bass_root":"E-2","pad1":"E-4","pad2":"B-4"},
    {"name":"Cmaj7","bass_root":"C-3","pad1":"C-4","pad2":"B-4"},
    {"name":"D7","bass_root":"D-3","pad1":"D-4","pad2":"C-5"},
    {"name":"B7","bass_root":"B-2","pad1":"B-3","pad2":"A-4"},
]
pattern_chords=[chord_prog for _ in range(8)]

def fill_drums(pattern):
    base_kicks=[0,16,32,48]
    extra=[]
    if pattern==0:
        extra=[]
    elif pattern%2==0:
        extra=[12,28,44,60]
    else:
        extra=[8,24,40,56]
    if pattern in [3,6]:
        extra=[10,26,42,58]
    kicks=base_kicks+extra
    for r in kicks:
        place(pattern,r,0,"C-4",1)
    snares=[]
    if pattern==0:
        snares=[16,48]
    elif pattern in [1,2,4,5]:
        snares=[16,48]
        if pattern%2==1:
            snares+=[24,56]
    else:
        snares=[16,48,32]
        if pattern==6:
            snares=[16,48,30,46]
    for r in snares:
        place(pattern,r,1,"C-4",2)
    # main hats on every 4 rows (beats)
    main_rows=list(range(0,64,4))
    # we will place closed/open as before but now handle choking better
    for r in main_rows:
        is_open=(r%16==12)
        if pattern in [2,4,6]:
            if r%16==4:
                is_open=True
        if is_open:
            place(pattern,r,2,"C-4",4)
        else:
            place(pattern,r,2,"C-4",3)
    # ghost hats only if not right after open
    if pattern not in [0]:
        # ghost positions are 2 rows after main beat (e.g., r+2) but skip if previous main was open
        for base in [0,16,32,48]:
            for off in [2,6,10]: # skip 14 which is 2 after open at 12
                r=base+off
                if r>=64: continue
                # check if previous main row at r-2 was open? That would be ghost after open, skip
                prev_main = r-2  # if ghost at 14, prev_main 12 open
                is_prev_open=False
                if prev_main%16==12:
                    is_prev_open=True
                if pattern in [2,4,6] and prev_main%16==4:
                    is_prev_open=True
                if is_prev_open:
                    continue
                # place ghost with lower volume
                place(pattern,r,2,"C-4",3, vol=24) # quieter

def fill_bass_and_pads(pattern):
    chords=pattern_chords[pattern]
    for bar in range(4):
        chord=chords[bar]
        bar_row=bar*16
        pad1=chord["pad1"]; pad2=chord["pad2"]
        place(pattern,bar_row,5,pad1,8)
        place(pattern,bar_row,6,pad2,8)
        root_str=chord["bass_root"]
        if chord["name"]=="Em7":
            intervals=[0,3,5,7,10,7]; rows=[0,4,6,10,12,14]
        elif chord["name"]=="Cmaj7":
            intervals=[0,4,7,11,7,4]; rows=[0,4,6,10,12,14]
        elif chord["name"]=="D7":
            intervals=[0,4,7,10,7,4]; rows=[0,4,7,10,12,14]
        elif chord["name"]=="B7":
            intervals=[0,4,7,10,6,4]; rows=[0,3,6,10,12,14]
        else:
            intervals=[0,7,12]; rows=[0,8,12]
        root_midi=note_to_midi(root_str)
        for interval, roff in zip(intervals, rows):
            r=bar_row+roff
            if r>=64: continue
            new_midi=root_midi+interval
            new_note=midi_to_note(new_midi)
            place(pattern,r,3,new_note,5)

def fill_lead(pattern):
    if pattern==0:
        for r,n in [(8,"E-5"),(24,"G-5"),(40,"A-5"),(56,"B-5")]:
            place(pattern,r,4,n,6)
        return
    elif pattern in [1,4]:
        bar_melodies=[
            [(0,"E-5"),(4,"G-5"),(6,"B-5"),(10,"A-5"),(12,"G-5"),(14,"E-5")],
            [(16,"C-6"),(20,"G-5"),(22,"E-5"),(26,"D-5"),(28,"C-5"),(30,"B-4")],
            [(32,"D-5"),(36,"F#5"),(38,"A-5"),(42,"C-6"),(44,"A-5"),(46,"F#5")],
            [(48,"B-4"),(52,"D#5"),(54,"F#5"),(58,"A-5"),(60,"F#5"),(62,"D#5")],
        ]
    elif pattern in [2,5]:
        bar_melodies=[
            [(0,"B-5"),(3,"A-5"),(6,"G-5"),(8,"E-6"),(12,"D-6"),(14,"B-5")],
            [(16,"E-6"),(19,"D-6"),(22,"C-6"),(24,"G-5"),(28,"E-5"),(30,"G-5")],
            [(32,"A-5"),(35,"F#5"),(38,"D-6"),(40,"C-6"),(44,"A-5"),(46,"G-5")],
            [(48,"F#5"),(51,"D#5"),(54,"B-5"),(56,"A-5"),(60,"F#5"),(62,"B-4")],
        ]
    elif pattern==3:
        bar_melodies=[
            [(0,"A-5"),(8,"C-6"),(12,"E-6")],
            [(16,"F-5"),(24,"A-5"),(28,"C-6")],
            [(32,"G-5"),(40,"B-5"),(44,"D-6")],
            [(48,"E-5"),(52,"G#5"),(56,"B-5"),(60,"E-6")],
        ]
    elif pattern==6:
        bar_melodies=[
            [(0,"E-5"),(6,"G-5"),(12,"B-5")],
            [(16,"C-6"),(22,"E-6"),(28,"G-5")],
            [(32,"D-6"),(38,"A-5"),(44,"F#5")],
            [(48,"B-5"),(54,"A-5"),(60,"F#5")],
        ]
    elif pattern==7:
        bar_melodies=[
            [(0,"E-6"),(2,"D-6"),(4,"B-5"),(6,"G-5"),(8,"E-5"),(10,"G-5"),(12,"B-5"),(14,"E-6")],
            [(16,"C-6"),(18,"B-5"),(20,"G-5"),(22,"E-5"),(24,"G-5"),(26,"B-5"),(28,"C-6"),(30,"E-6")],
            [(32,"D-6"),(34,"C-6"),(36,"A-5"),(38,"F#5"),(40,"A-5"),(42,"C-6"),(44,"D-6"),(46,"F#6")],
            [(48,"B-5"),(50,"A-5"),(52,"F#5"),(54,"D#5"),(56,"F#5"),(58,"A-5"),(60,"B-5"),(62,"D#6")],
        ]
    else:
        bar_melodies=[[] for _ in range(4)]
    for bar in range(4):
        for off, n in bar_melodies[bar]:
            r_abs=bar*16 + (off %16)
            place(pattern,r_abs,4,n,6)

def fill_bell(pattern):
    m={"Em7":["E-5","G-5","B-5","D-6"],"Cmaj7":["C-5","E-5","G-5","B-5"],"D7":["D-5","F#5","A-5","C-6"],"B7":["B-4","D#5","F#5","A-5"]}
    chords=pattern_chords[pattern]
    if pattern==0:
        for bar in range(4):
            chord=chords[bar]; notes=m[chord["name"]][:3]; base=bar*16
            for i,n in enumerate(notes):
                place(pattern,base+i*2,7,n,7)
        return
    if pattern in [1,2,4,5,7]:
        for bar in range(4):
            chord=chords[bar]; notes=m[chord["name"]]; base=bar*16
            positions=[6,10,14] if pattern%2==0 else [8,12,14]
            for pos,n in zip(positions, notes):
                place(pattern,base+pos,7,n,7)
    elif pattern in [3,6]:
        for bar in range(4):
            chord=chords[bar]; notes=m[chord["name"]][:2]; base=bar*16
            place(pattern,base,7,notes[0],7)
            place(pattern,base+8,7,notes[1],7)

for p in range(8):
    fill_drums(p)
    fill_bass_and_pads(p)
    fill_lead(p)
    fill_bell(p)

print(f"batch {len(batch)}")
with open("/tmp/batch_pat.json","w") as f:
    json.dump(batch,f)
import subprocess, json as js
proc=subprocess.run(["ft2","batch","/tmp/batch_pat.json"], capture_output=True, text=True)
print(proc.stdout[:5000])
print(proc.stderr[:2000])
proc=subprocess.run(["ft2","call","module_info",js.dumps({})], capture_output=True, text=True)
print(proc.stdout)
proc=subprocess.run(["ft2","call","module_save",js.dumps({"path":"/tmp/tune.xm","format":"xm"})], capture_output=True, text=True)
print(proc.stdout)
proc=subprocess.run(["ft2","call","module_render",js.dumps({"path":"/tmp/tune.wav","rate":44100})], capture_output=True, text=True)
print(proc.stdout)

import wave, numpy as np
with wave.open("/tmp/tune.wav") as w:
    print(w.getparams())
    n=w.getnframes()
    data=w.readframes(n)
    arr=np.frombuffer(data,dtype=np.int16).reshape(-1,2)
    print("max",np.max(np.abs(arr)), "rms",np.sqrt(np.mean((arr/32768)**2)))
    for sec in range(min(12, n//44100)):
        seg=arr[sec*44100:(sec+1)*44100]
        rms=np.sqrt(np.mean((seg/32768)**2))
        peak=np.max(np.abs(seg))
        print(f"sec {sec:2d} rms {rms:.3f} peak {peak}")
    # look at loop transition: find correlation between start and end
    # also render single loop vs double?
    # Check clip count
    clip=np.sum(np.abs(arr)>=32700)
    print(f"clipped samples {clip}/{arr.size} ({clip/arr.size*100:.3f}%)")
    # analyze histogram of peaks to see headroom
    # more detailed: examine moment where all hits together at pattern starts row 0: kick+snare? Actually row 0 has kick+pad+bass etc
    # Estimate dc offset
    print("DC offset",np.mean(arr))

