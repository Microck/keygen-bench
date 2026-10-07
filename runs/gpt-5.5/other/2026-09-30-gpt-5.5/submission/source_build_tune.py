import numpy as np, base64, json, math, os, random

SR = 8363.0  # FT2 C-4 sample playback rate (approx)
C4 = 261.625565
rng = np.random.default_rng(1337)

# ---------- sample generation ----------
def norm(x, peak=0.85, remove_dc=True):
    x = np.asarray(x, dtype=np.float32)
    if remove_dc:
        x = x - np.mean(x)
    m = np.max(np.abs(x))
    if m > 0:
        x = x / m * peak
    return x.astype(np.float32)

def b64f(x):
    return base64.b64encode(np.asarray(x, dtype=np.float32).tobytes()).decode('ascii')

def saw_phase(ph):
    # -1..1 saw, periodic at integer phase
    return 2.0*(ph - np.floor(ph + 0.5))

def tri_phase(ph):
    return 2.0*np.abs(2.0*(ph - np.floor(ph + 0.5))) - 1.0

def pulse_phase(ph, duty=0.5):
    return np.where((ph % 1.0) < duty, 1.0, -1.0)

def one_cycle_lead(N=32):
    n = np.arange(N)
    ph = n/N
    x = 0.58*saw_phase(ph) + 0.30*pulse_phase(ph+0.03, 0.42) + 0.18*np.sin(2*np.pi*3*ph+0.4)
    x = np.tanh(1.35*x)
    return norm(x, 0.82)

def one_cycle_saw_echo(N=32):
    n = np.arange(N)
    ph = n/N
    x = 0.45*saw_phase(ph+0.12) + 0.30*tri_phase(ph) + 0.20*np.sin(2*np.pi*2*ph)
    x = np.tanh(1.2*x)
    return norm(x, 0.80)

def one_cycle_bass(N=32):
    n = np.arange(N)
    ph = n/N
    x = 0.72*np.sin(2*np.pi*ph) + 0.28*np.sin(2*np.pi*2*ph+0.2) + 0.20*pulse_phase(ph, 0.55)
    x = np.tanh(1.7*x)
    return norm(x, 0.88)

def one_cycle_pad(N=32):
    n = np.arange(N)
    ph = n/N
    x = 0.55*tri_phase(ph+0.02) + 0.22*np.sin(2*np.pi*2*ph+1.1) + 0.13*np.sin(2*np.pi*5*ph)
    for _ in range(2):
        x = (np.roll(x,1)+2*x+np.roll(x,-1))/4
    return norm(x, 0.70)

def fade_edges(x, attack_s=0.002, release_s=0.020, sr=SR):
    x = np.array(x, dtype=np.float32, copy=True)
    a = min(len(x), int(attack_s*sr))
    r = min(len(x), int(release_s*sr))
    if a > 0:
        x[:a] *= np.linspace(0,1,a,endpoint=False)
    if r > 0:
        x[-r:] *= np.linspace(1,0,r,endpoint=False)
    return x

def make_pluck(dur=0.48):
    N = int(SR*dur)
    t = np.arange(N)/SR
    ph = C4*t
    osc = 0.52*saw_phase(ph) + 0.30*tri_phase(ph*1.003) + 0.18*pulse_phase(ph+0.07, 0.36)
    env = np.exp(-7.5*t) * (1 - np.exp(-650*t))
    noise = rng.normal(0,1,N)
    noise_env = np.exp(-85*t)
    x = osc*env + 0.08*noise*noise_env
    x *= np.linspace(1,0,N)**0.35
    return norm(fade_edges(x,0.001,0.030), 0.82)

def make_chip_bleep(dur=0.20):
    N = int(SR*dur)
    t = np.arange(N)/SR
    env = np.exp(-18*t)*(1-np.exp(-900*t))
    ph = C4*t + 18*t*t
    x = (0.65*pulse_phase(ph,0.25) + 0.35*np.sin(2*np.pi*(C4*2.01)*t))*env
    return norm(fade_edges(x,0.001,0.020), 0.76)

def make_kick(dur=0.34):
    N = int(SR*dur)
    t = np.arange(N)/SR
    f = 48 + 112*np.exp(-24*t) + 24*np.exp(-4*t)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)
    env = np.exp(-10.5*t)*(1-np.exp(-800*t))
    click = rng.normal(0,1,N)*np.exp(-250*t)
    x = 1.05*body*env + 0.12*click
    x *= np.linspace(1,0,N)**0.25
    return norm(fade_edges(x,0.0005,0.040), 0.92)

def highpass_noise(N, amount=0.995):
    n = rng.normal(0,1,N)
    lp = np.zeros(N)
    a = amount
    for i in range(1,N):
        lp[i] = a*lp[i-1] + (1-a)*n[i]
    return n - lp

def make_snare(dur=0.26):
    N = int(SR*dur)
    t = np.arange(N)/SR
    noise = highpass_noise(N, 0.990)
    envn = np.exp(-18*t)*(1-np.exp(-500*t))
    tone = np.sin(2*np.pi*(185 - 45*t)*t) * np.exp(-18*t)
    snap = rng.normal(0,1,N)*np.exp(-120*t)
    x = 0.62*noise*envn + 0.30*tone + 0.12*snap
    x *= np.linspace(1,0,N)**0.4
    return norm(fade_edges(x,0.0005,0.035), 0.86)

def make_clap(dur=0.30):
    N = int(SR*dur)
    t = np.arange(N)/SR
    noise = highpass_noise(N, 0.985)
    env = np.zeros(N)
    for dt,amp in [(0.000,1.0),(0.018,0.8),(0.037,0.65),(0.062,0.45)]:
        env += amp*np.exp(-95*np.maximum(0,t-dt))*(t>=dt)
    env *= np.exp(-2.5*t)
    x = noise*env
    x *= np.linspace(1,0,N)**0.5
    return norm(fade_edges(x,0.0005,0.035), 0.82)

def make_hat(dur=0.075):
    N = int(SR*dur)
    t = np.arange(N)/SR
    noise = highpass_noise(N, 0.975)
    metal = (np.sin(2*np.pi*2650*t) + np.sin(2*np.pi*3430*t+0.7) + np.sin(2*np.pi*4470*t+1.9))/3
    env = np.exp(-65*t)*(1-np.exp(-2000*t))
    x = (0.62*noise + 0.38*metal)*env
    return norm(fade_edges(x,0.0003,0.010), 0.70)

def make_open_hat(dur=0.32):
    N = int(SR*dur)
    t = np.arange(N)/SR
    noise = highpass_noise(N, 0.988)
    metal = (np.sin(2*np.pi*2140*t) + np.sin(2*np.pi*3010*t+0.5) + np.sin(2*np.pi*3940*t+2.0))/3
    env = np.exp(-10*t)*(1-np.exp(-900*t))
    x = (0.70*noise + 0.30*metal)*env
    x *= np.linspace(1,0,N)**0.35
    return norm(fade_edges(x,0.0005,0.040), 0.68)

def make_crash(dur=0.82):
    N = int(SR*dur)
    t = np.arange(N)/SR
    noise = highpass_noise(N, 0.993)
    shimmer = (np.sin(2*np.pi*1750*t+0.4*np.sin(2*np.pi*3*t)) + np.sin(2*np.pi*2680*t+1.3) + np.sin(2*np.pi*3920*t+0.2))/3
    env = np.exp(-4.2*t)*(1-np.exp(-600*t))
    x = (0.80*noise + 0.25*shimmer)*env
    x *= np.linspace(1,0,N)**0.18
    return norm(fade_edges(x,0.001,0.080), 0.72)

def make_riser(dur=1.95):
    N = int(SR*dur)
    t = np.arange(N)/SR
    f0, f1 = 220.0, 2200.0
    f = f0*(f1/f0)**(t/dur)
    ph = np.cumsum(f)/SR
    pulse = pulse_phase(ph, 0.18)
    noise = highpass_noise(N, 0.995)
    env = (t/dur)**1.2
    env *= np.minimum(1, (dur-t)/0.10)
    env = np.clip(env,0,1)
    x = (0.48*pulse + 0.52*noise)*env
    return norm(fade_edges(x,0.010,0.100), 0.70)

samples = {
    'lead': one_cycle_lead(),
    'saw': one_cycle_saw_echo(),
    'bass': one_cycle_bass(),
    'pad': one_cycle_pad(),
    'pluck': make_pluck(),
    'bleep': make_chip_bleep(),
    'kick': make_kick(),
    'snare': make_snare(),
    'clap': make_clap(),
    'hat': make_hat(),
    'openhat': make_open_hat(),
    'crash': make_crash(),
    'riser': make_riser(),
}

# flags: FT2 loop flag + 16-bit flag (17). Non-loop samples use 16-bit flag only (16).
inst_specs = [
    (1, 'lead',   'NEON PULSE LEAD', 38, 116, True),
    (2, 'saw',    'RAZOR ECHO LEAD', 32, 184, True),
    (3, 'bass',   'SUB PULSE BASS',  48, 128, True),
    (4, 'pluck',  'GLASS PLUCK L',   34,  70, False),
    (5, 'pluck',  'GLASS PLUCK R',   32, 190, False),
    (6, 'pad',    'CHIP PAD L',      22,  82, True),
    (7, 'pad',    'CHIP PAD C',      20, 128, True),
    (8, 'pad',    'CHIP PAD R',      22, 174, True),
    (9, 'kick',   'TIGHT KICK',      56, 128, False),
    (10,'snare',  'NOISE SNARE',     45, 136, False),
    (11,'clap',   'BYTE CLAP',       38, 160, False),
    (12,'hat',    'CLOSED HAT',      27,  76, False),
    (13,'openhat','OPEN HAT',        25, 190, False),
    (14,'crash',  'PIXEL CRASH',     34, 180, False),
    (15,'riser',  'ASCENT RISER',    28, 128, False),
    (16,'bleep',  'SYNC BLEEP',      28, 128, False),
]

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nt(m):
    return NOTE_NAMES[m%12] + str(m//12 - 1)

CH = {
    'Em': {'bass':40, 'fifth':47, 'pad':[52,55,59], 'arp':[64,67,71,76,79,83], 'lead':64},
    'C':  {'bass':36, 'fifth':43, 'pad':[48,52,55], 'arp':[60,64,67,72,76,79], 'lead':60},
    'D':  {'bass':38, 'fifth':45, 'pad':[50,54,57], 'arp':[62,66,69,74,78,81], 'lead':62},
    'Bm': {'bass':35, 'fifth':42, 'pad':[47,50,54], 'arp':[59,62,66,71,74,78], 'lead':59},
    'B7': {'bass':35, 'fifth':42, 'pad':[47,51,57], 'arp':[59,63,66,69,75,78], 'lead':59},
    'G':  {'bass':43, 'fifth':50, 'pad':[55,59,62], 'arp':[67,71,74,79,83,86], 'lead':67},
    'Am': {'bass':33, 'fifth':40, 'pad':[45,48,52], 'arp':[57,60,64,69,72,76], 'lead':57},
}
pattern_chords = {
    0: ['Em','C','D','Bm'],
    1: ['Em','C','D','B7'],
    2: ['G','D','Em','C'],
    3: ['G','D','C','B7'],
    4: ['Em','C','Am','B7'],
    5: ['Em','G','D','B7'],
    6: ['G','D','Em','C'],
    7: ['Am','C','D','B7'],
}
melodies = {
0: [(0,76),(2,79),(4,83),(6,88),(8,86),(10,83),(12,79),(14,83),
    (16,84),(18,83),(20,79),(22,76),(24,79),(26,76),(28,74),(30,71),
    (32,74),(34,78),(36,81),(38,86),(40,84),(42,81),(44,78),(46,81),
    (48,83),(50,81),(52,78),(54,74),(56,78),(58,83),(60,81),(62,78)],
1: [(0,76),(2,79),(4,83),(6,86),(7,88),(10,86),(12,83),(14,79),
    (16,76),(18,79),(20,84),(22,88),(24,86),(26,84),(28,83),(30,79),
    (32,78),(34,81),(36,86),(38,88),(40,86),(42,81),(44,78),(46,74),
    (48,75),(50,78),(52,83),(54,81),(56,78),(58,75),(60,71),(62,69)],
2: [(0,79),(2,83),(4,86),(6,83),(8,81),(10,79),(12,83),(14,86),
    (16,81),(18,78),(20,74),(22,78),(24,81),(26,86),(28,84),(30,81),
    (32,83),(34,79),(36,76),(38,79),(40,83),(42,88),(44,86),(46,83),
    (48,84),(50,79),(52,76),(54,79),(56,84),(58,88),(60,86),(62,83)],
3: [(0,86),(2,83),(4,79),(6,86),(8,88),(10,86),(12,83),(14,81),
    (16,78),(18,81),(20,86),(22,90),(24,88),(26,86),(28,81),(30,78),
    (32,88),(34,86),(36,84),(38,79),(40,76),(42,79),(44,84),(46,86),
    (48,87),(50,83),(52,81),(54,78),(56,75),(58,78),(60,81),(62,83)],
4: [(0,76),(8,71),(16,72),(24,67),(32,69),(40,72),(48,75),(54,78),(58,81),(62,83)],
5: [(0,76),(2,79),(4,83),(6,79),(8,76),(10,83),(12,88),(14,83),
    (16,79),(18,83),(20,86),(22,91),(24,86),(26,83),(28,79),(30,83),
    (32,78),(34,81),(36,86),(38,81),(40,78),(42,86),(44,90),(46,86),
    (48,71),(50,75),(52,78),(54,81),(56,83),(58,87),(60,90),(61,93),(62,95),(63,99)],
6: [(0,79),(2,83),(4,86),(6,91),(8,90),(10,86),(12,83),(14,79),
    (16,81),(18,86),(20,90),(22,93),(24,91),(26,90),(28,86),(30,81),
    (32,83),(34,88),(36,91),(38,95),(40,93),(42,91),(44,88),(46,83),
    (48,84),(50,88),(52,91),(54,96),(56,95),(58,91),(60,88),(62,84)],
7: [(0,81),(2,84),(4,88),(6,84),(8,83),(10,81),(12,76),(14,79),
    (16,84),(18,88),(20,91),(22,88),(24,86),(26,84),(28,79),(30,76),
    (32,86),(34,81),(36,78),(38,81),(40,84),(42,86),(44,88),(46,84),
    (48,83),(50,81),(52,78),(54,75),(56,78),(58,81),(60,83),(62,75)],
}

calls=[]
def call(name,args): calls.append({'name':name,'arguments':args})
call('module_new', {'channels':16, 'name':'NEON KEYVAULT'})
call('song_set', {'name':'NEON KEYVAULT', 'bpm':160, 'speed':6, 'length':8, 'loop_start':0, 'channels':16})
for inst,key,name,vol,pan,looped in inst_specs:
    x=samples[key]
    call('instrument_set', {'instrument':inst, 'name':name})
    call('sample_create_from_pcm', {'instrument':inst, 'sample':0, 'pcm':b64f(x), 'encoding':'float32', 'name':name[:22]})
    flags = 16 | (1 if looped else 0)
    meta={'instrument':inst,'sample':0,'name':name[:22],'volume':vol,'panning':pan,'finetune':0,'relative_note':0,'loop_start':0,'loop_length':(len(x) if looped else 0),'flags':flags}
    call('sample_set', meta)
for p in range(8):
    call('pattern_clear', {'pattern':p})
    call('pattern_set_length', {'pattern':p,'rows':64})
    call('order_set', {'position':p,'pattern':p})

cells={}
def set_cell(p,r,ch,note=None,instrument=None,volume=None,effect=None,effect_param=None):
    if not (0 <= r < 64): return
    key=(p,r,ch); c=cells.setdefault(key, {'pattern':p,'row':r,'channel':ch})
    if note is not None: c['note']=note if isinstance(note,str) else nt(note)
    if instrument is not None: c['instrument']=instrument
    if volume is not None: c['volume']=int(volume)
    if effect is not None: c['effect']=int(effect)
    if effect_param is not None: c['effect_param']=int(effect_param)
CH_KICK=0; CH_SNARE=1; CH_HAT=2; CH_OPEN=3; CH_BASS=4; CH_BASS2=5; CH_LEAD=6; CH_ECHO=7; CH_HARM=8; CH_ARP_L=9; CH_ARP_R=10; CH_PAD_L=11; CH_PAD_C=12; CH_PAD_R=13; CH_FX=14; CH_CLAP=15
PAN={CH_KICK:128,CH_SNARE:136,CH_HAT:76,CH_OPEN:190,CH_BASS:128,CH_BASS2:130,CH_LEAD:116,CH_ECHO:190,CH_HARM:78,CH_ARP_L:58,CH_ARP_R:202,CH_PAD_L:82,CH_PAD_C:128,CH_PAD_R:174,CH_FX:128,CH_CLAP:160}

def add_pad(p,chords,vol=18):
    for b,cname in enumerate(chords):
        row=b*16; pads=CH[cname]['pad']; v=vol+(2 if cname=='B7' else 0)
        set_cell(p,row,CH_PAD_L,pads[0],6,v)
        set_cell(p,row,CH_PAD_C,pads[1],7,max(1,v-2))
        set_cell(p,row,CH_PAD_R,pads[2],8,v)

def add_bass(p,chords,mode='full'):
    for b,cname in enumerate(chords):
        row=b*16; c=CH[cname]; root=c['bass']; fifth=c['fifth']
        if cname=='B7': lead=51
        elif cname=='D': lead=48
        elif cname=='C': lead=47
        elif cname=='G': lead=54
        elif cname=='Am': lead=48
        else: lead=root+10
        if mode=='break' and b<2:
            offs=[0,8,12]; notes=[root,root+12,fifth]; vols=[34,28,30]
        elif mode=='build' and b==3:
            offs=[0,2,4,6,8,10,12,13,14,15]; notes=[root,root+12,fifth,root+12,root,root+12,fifth,lead,root+12,lead]; vols=[43,34,38,34,43,34,38,33,36,32]
        else:
            offs=[0,2,4,6,8,10,12,14]; notes=[root,root+12,fifth,root+12,root,root+12,fifth,lead]; vols=[43,34,38,34,43,34,38,32]
            if mode=='break': vols=[max(22,v-8) for v in vols]
        for off,n,v in zip(offs,notes,vols): set_cell(p,row+off,CH_BASS,n,3,v)
        if mode in ('intense','build'):
            for off in [7,15]: set_cell(p,row+off,CH_BASS2,root+24,16,16)

def add_drums(p,mode='full',crash=False,fill=False):
    if crash: set_cell(p,0,CH_OPEN,'C-4',14,28)
    for b in range(4):
        base=b*16
        if mode=='sparse' and b<2:
            kick_offs=[0,8]; snare_offs=[12]; hat_step=4
        elif mode=='break' and b<2:
            kick_offs=[] if b==0 else [0,8]; snare_offs=[12] if b==1 else []; hat_step=4
        else:
            kick_offs=[0,4,8,12]
            if (mode in ('intense','build') or fill) and b==3: kick_offs += [14]
            snare_offs=[4,12]; hat_step=1 if mode in ('intense','build') else 2
        for off in kick_offs:
            set_cell(p,base+off,CH_KICK,'C-4',9,51 if off in (0,8) else 45)
        for off in snare_offs:
            set_cell(p,base+off,CH_SNARE,'C-4',10,38)
            set_cell(p,base+off,CH_CLAP,'C-4',11,25)
        for off in range(0,16,hat_step):
            if mode=='break' and b==0 and off not in (8,12): continue
            v=18 if off%4 else 22
            if hat_step==1 and off%2==1: v=12
            if mode=='sparse': v=max(10,v-4)
            set_cell(p,base+off,CH_HAT,'C-4',12,v)
        if not (mode=='break' and b==0):
            for off in [6,14]:
                vv=19 if off==14 else 15
                if mode in ('intense','build'): vv+=2
                set_cell(p,base+off,CH_OPEN,'C-4',13,vv)
    if fill or mode=='build':
        for i,r in enumerate(range(48,64)):
            if mode=='build' or r%2==0:
                v=16+int(20*i/15); note='C-4' if i%2==0 else 'D-4'
                set_cell(p,r,CH_SNARE,note,10,v)
        set_cell(p,60,CH_CLAP,'C-4',11,28); set_cell(p,62,CH_CLAP,'C-4',11,22)

def add_arps(p,chords,intensity='normal'):
    seq=[0,1,2,1,3,2,1,2,0,1,2,4,3,2,1,2]
    seq2=[3,2,1,0,2,3,4,2,1,2,3,5,4,3,2,1]
    for b,cname in enumerate(chords):
        base=b*16; arp=CH[cname]['arp']
        if intensity=='break': rows=range(0,16,2); volL=10; volR=8
        elif intensity=='sparse': rows=range(0,16,2); volL=11; volR=8
        elif intensity=='intense': rows=range(0,16,1); volL=13; volR=10
        elif intensity=='build': rows=range(0,16,1); volL=12+b; volR=9+b
        else: rows=range(0,16,1); volL=12; volR=9
        for off in rows:
            n=arp[seq[off%16]%len(arp)]
            set_cell(p,base+off,CH_ARP_L,n,4,volL+(1 if off%4==0 else 0))
            if intensity in ('intense','build') or off%2==1:
                n2=arp[seq2[off%16]%len(arp)]
                set_cell(p,base+off,CH_ARP_R,n2,5,volR)

def add_melody(p,sparse=False,harmony=False,break_style=False):
    for r,n in melodies[p]:
        if break_style:
            instr=4 if (r//8)%2==0 else 5; vol=22 if r%16==0 else 18
            set_cell(p,r,CH_LEAD,n,instr,vol)
            if r in (48,54,58,62): set_cell(p,r,CH_FX,n+12,16,13)
        else:
            vol=32 if r%4==0 else 28
            if p in (5,6): vol+=2
            if p==7 and r>=48: vol+=2
            set_cell(p,r,CH_LEAD,n,1,vol)
            if r+2<64 and not sparse: set_cell(p,r+2,CH_ECHO,n,5,11 if r%4 else 13)
        if harmony and r%4==0:
            set_cell(p,r,CH_HARM,n-12,2,15 if p!=7 else 16)
    if p in (2,3,6,7):
        extras=[]
        if p in (2,6): extras=[(14,74),(15,76),(30,78),(31,81),(46,79),(47,83),(60,81),(61,83),(62,86)]
        elif p==3: extras=[(14,83),(15,86),(30,81),(31,78),(46,84),(47,86),(60,81),(61,83),(62,87)]
        elif p==7: extras=[(14,76),(15,79),(30,79),(31,84),(46,84),(47,86),(60,78),(61,75),(62,71)]
        for r,n in extras: set_cell(p,r,CH_HARM,n,2,14)

def add_break_decor(p):
    for r,n,v in [(4,88,12),(12,83,10),(20,84,12),(28,79,10),(36,81,12),(44,84,10)]: set_cell(p,r,CH_FX,n,16,v)
    set_cell(p,48,CH_OPEN,'C-4',14,18); set_cell(p,32,CH_FX,'C-4',15,16)

def add_build_fx(p):
    set_cell(p,32,CH_FX,'C-4',15,20)
    for r,n in zip(range(32,64,4), [76,78,79,81,83,86,87,90]): set_cell(p,r,CH_FX,n,16,14+(r-32)//8)

for p in range(8):
    chords=pattern_chords[p]
    if p==0:
        add_drums(p,'full',crash=True); add_bass(p,chords,'full'); add_pad(p,chords,18); add_arps(p,chords,'normal'); add_melody(p,harmony=False)
    elif p==1:
        add_drums(p,'full',fill=True); add_bass(p,chords,'full'); add_pad(p,chords,18); add_arps(p,chords,'normal'); add_melody(p,harmony=False)
    elif p==2:
        add_drums(p,'intense',crash=True); add_bass(p,chords,'intense'); add_pad(p,chords,17); add_arps(p,chords,'intense'); add_melody(p,harmony=True)
    elif p==3:
        add_drums(p,'intense',fill=True); add_bass(p,chords,'intense'); add_pad(p,chords,18); add_arps(p,chords,'intense'); add_melody(p,harmony=True)
    elif p==4:
        add_drums(p,'break'); add_bass(p,chords,'break'); add_pad(p,chords,16); add_arps(p,chords,'break'); add_melody(p,sparse=True,break_style=True); add_break_decor(p)
    elif p==5:
        add_drums(p,'build',fill=True); add_bass(p,chords,'build'); add_pad(p,chords,17); add_arps(p,chords,'build'); add_melody(p,harmony=True); add_build_fx(p)
    elif p==6:
        add_drums(p,'intense',crash=True); add_bass(p,chords,'intense'); add_pad(p,chords,18); add_arps(p,chords,'intense'); add_melody(p,harmony=True)
    elif p==7:
        add_drums(p,'intense',fill=True); add_bass(p,chords,'intense'); add_pad(p,chords,18); add_arps(p,chords,'intense'); add_melody(p,harmony=True); set_cell(p,48,CH_FX,'C-4',15,18)
for p in range(8):
    for ch,pan in PAN.items():
        if (p,0,ch) not in cells: set_cell(p,0,ch,effect=8,effect_param=pan)
for key in sorted(cells.keys()): call('pattern_set_cell', cells[key])
os.makedirs('/workspace/submission', exist_ok=True)
call('module_save', {'path':'/workspace/submission/tune.xm','format':'xm'})
with open('/workspace/tune_batch.json','w') as f: json.dump(calls,f)
with open('/workspace/tune_summary.txt','w') as f:
    f.write('NEON KEYVAULT - original FT2 keygen tune v2 (16-bit samples)\n')
    f.write('8 patterns x 64 rows, speed 6, BPM 160, loop_start 0.\n')
    f.write(f'Pattern cells: {len(cells)}, calls: {len(calls)}\n')
    for spec in inst_specs: f.write(str(spec)+'\n')
print(f'wrote /workspace/tune_batch.json with {len(calls)} calls, {len(cells)} cells')
