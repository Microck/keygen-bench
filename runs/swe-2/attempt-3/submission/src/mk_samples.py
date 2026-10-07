import numpy as np, wave, os, json

SR = 8372.0          # FT2 C-4 base rate: C-4 plays sample at this rate
NT = 256             # wavetable size
os.makedirs('work/smp', exist_ok=True)

def wrt(name, x, fade=True):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    if fade:
        n=min(len(x),168); x[-n:]*=np.linspace(1,0,n)  # safety fade end
    x = np.clip(x, -1, 1)
    d = (x*32767).astype('<i2')
    with wave.open('work/smp/%s.wav'%name,'wb') as f:
        f.setparams((1,2,int(SR),len(d),'NONE',''))
        f.writeframes(d.tobytes())
    return len(d)

def tab_saw(nh=14):
    t = np.arange(NT)/NT
    s = np.zeros(NT)
    for k in range(1,nh+1):
        s += np.sin(2*np.pi*k*t)/k
    s-=s.mean(); return s/np.max(np.abs(s))

def tab_pulse(duty):
    t = np.arange(NT)/NT
    s = np.where(t < duty, 1.0, -1.0); s-=s.mean()
    return s

def tab_tri():
    t = np.arange(NT)/NT
    return 4*np.abs(t-0.5)-1

def tab_sine(nh=None, amps=None):
    t = np.arange(NT)/NT
    s = np.zeros(NT)
    if nh is None: nh=[1]
    if amps is None: amps=[1.0]*len(nh)
    for h,a in zip(nh,amps): s += a*np.sin(2*np.pi*h*t)
    return s/np.max(np.abs(s))

def mix(*pairs):
    s = np.zeros(NT)
    for tab,a in pairs: s += a*tab
    s-=s.mean()
    return s/np.max(np.abs(s))

T_SAW  = tab_saw(14)
T_SAW6 = tab_saw(6)
T_SQ   = tab_pulse(0.5)
T_P25  = tab_pulse(0.25)
T_TRI  = tab_tri()
T_SIN  = tab_sine()
T_SOFT = tab_sine([1,2,3,4,5],[1,.32,.15,.07,.03])
T_LEAD = mix((T_P25,.55),(T_SAW,.5))
T_BASS = mix((T_SAW6,.8),(T_P25,.45))
T_STAB = mix((T_SAW,.8),(T_P25,.35))
T_ARP  = mix((T_SQ,.6),(T_SAW,.4))
T_SUB  = tab_sine([1,2],[1,.12])

def lut(tab, ph):
    return tab[(np.rint(ph).astype(np.int64)) % NT]

def gen_sustain(tabA, tabB, head_s, loop_len, vib_depth=0.0, vib_period=None,
                attack=0.01, decay_to=1.0, decay_tau=None,
                bright_ms=None, pitch_drop=0.0, pitch_tau=0.012, amp=1.0):
    """Looped sustaining patch. Head rounded up to multiple of 32 samples so the
       loop starts on an integer carrier cycle; envelope frozen at head end so the
       loop region is exactly periodic."""
    head = int(np.ceil(head_s*SR/32))*32
    if vib_period is None: vib_period = loop_len
    n = head + 2*loop_len          # generate extra cycle to verify periodicity
    ph = 0.0; out = np.zeros(n)
    bright_n = int((bright_ms or 0)*SR/1000)
    for i in range(n):
        t = i/SR
        tenv = min(t, head/SR)            # freeze envelope at loop start
        d = vib_depth*min(1.0, i/max(1,head))
        rel = i-head
        ph += 8.0*(1.0 + (d*np.sin(2*np.pi*rel/vib_period) if rel>=0 else 0.0)
                   + pitch_drop*np.exp(-t/pitch_tau))
        m = 0.0
        if bright_n>0 and i < bright_n:
            m = 1.0 - i/bright_n
        v = (1-m)*lut(tabA,ph) + m*lut(tabB,ph)
        a = min(1.0, tenv/attack) if attack>0 else 1.0
        if decay_tau:
            a *= decay_to + (1.0-decay_to)*np.exp(-tenv/decay_tau)
        out[i] = v*a*amp
    md = np.abs(out[head+loop_len:head+2*loop_len]-out[head:head+loop_len]).max()
    assert md < 1e-6, 'loop not periodic: %g' % md
    out = out[:head+loop_len]
    mu = out[head:].mean(); out -= mu   # zero DC over loop region
    return out, head, loop_len

# ---------- drums ----------
def kick():
    n = int(0.26*SR); t = np.arange(n)/SR
    f = 44 + 150*np.exp(-t/0.018)
    ph = np.cumsum(2*np.pi*f/SR)
    y = np.sin(ph)*np.exp(-t/0.085)
    y += 0.18*np.sin(ph*2.02)*np.exp(-t/0.09)
    c = np.random.RandomState(7).randn(int(0.004*SR))
    y[:len(c)] += c*0.25*np.exp(-np.arange(len(c))/(SR*0.001))
    return np.tanh(y*1.5)*0.95

def snare():
    n = int(0.20*SR); t=np.arange(n)/SR
    rng = np.random.RandomState(3)
    no = rng.randn(n)
    hp=np.zeros(n); lp=np.zeros(n)
    a1=np.exp(-2*np.pi*1200/SR); a2=np.exp(-2*np.pi*6500/SR)
    for i in range(1,n):
        hp[i]=a1*(hp[i-1]+no[i]-no[i-1]); lp[i]=a2*lp[i-1]+(1-a2)*hp[i]
    f = 175+40*np.exp(-t/0.02)
    tone=np.sin(np.cumsum(2*np.pi*f/SR))*np.exp(-t/0.055)
    y=0.5*tone+1.4*lp*np.exp(-t/0.05)
    return np.tanh(y*1.2)*0.9

def clap():
    n=int(0.28*SR); t=np.arange(n)/SR
    rng=np.random.RandomState(5); no=rng.randn(n)
    a1=np.exp(-2*np.pi*800/SR); a2=np.exp(-2*np.pi*3800/SR)
    hp=np.zeros(n); bp=np.zeros(n)
    for i in range(1,n):
        hp[i]=a1*(hp[i-1]+no[i]-no[i-1]); bp[i]=a2*bp[i-1]+(1-a2)*hp[i]
    env=np.zeros(n)
    for toff,a in [(0,1.0),(.011,.75),(.023,.55),(.035,.4)]:
        i0=int(toff*SR); env[i0:]+=a*np.exp(-np.arange(n-i0)/(SR*0.006))
    env+=0.4*np.exp(-t/0.05)
    return np.tanh(bp*env*2.2)*0.8

def hat(decay, bright=1.0):
    n=int(max(0.05,decay*4)*SR); t=np.arange(n)/SR
    rng=np.random.RandomState(11); no=rng.randn(n)
    hp=np.zeros(n); a=np.exp(-2*np.pi*5500/SR)
    for i in range(1,n): hp[i]=a*(hp[i-1]+no[i]-no[i-1])
    sq=sum(np.sign(np.sin(2*np.pi*f*t+p)) for f,p in
           [(740,0),(1123,.7),(1860,1.9),(2720,.3),(3590,2.6)])
    sq*=0.13*bright
    y=(0.8*hp+sq)*np.exp(-t/decay)
    return np.tanh(y*1.6)*0.85

def agogo():
    n=int(0.14*SR); t=np.arange(n)/SR
    f=830+160*np.exp(-t/0.008)
    y=np.sin(np.cumsum(2*np.pi*f/SR))*np.exp(-t/0.045)
    y+=0.4*np.sin(np.cumsum(2*np.pi*f*2.76/SR))*np.exp(-t/0.02)
    return np.tanh(y*1.4)*0.8

def crash():
    n=int(1.7*SR); t=np.arange(n)/SR
    rng=np.random.RandomState(9); no=rng.randn(n)
    lp=np.zeros(n); hp=np.zeros(n)
    a=np.exp(-2*np.pi*4500/SR); a2=np.exp(-2*np.pi*1800/SR)
    for i in range(1,n):
        lp[i]=a*lp[i-1]+(1-a)*no[i]; hp[i]=a2*(hp[i-1]+lp[i]-lp[i-1])
    sq=sum(np.sign(np.sin(2*np.pi*f*t+p))*np.exp(-t/0.18) for f,p in
           [(4020,0),(5370,1.2),(6210,2.1),(7400,.5),(4930,2.8)])*0.05
    env=np.exp(-t/0.5)*np.minimum(1,t/0.004)
    return np.tanh((0.9*hp+sq)*env*1.7)*0.8

def riser():
    n=int(2.60*SR); t=np.arange(n)/SR
    rng=np.random.RandomState(13); x=rng.randn(n)
    y=np.zeros(n); prev=0.0; yp=0.0
    fc=350+5200*(t/t[-1])**2; a=np.exp(-2*np.pi*fc/SR)
    for i in range(1,n):
        y[i]=a[i]*(yp+x[i]-x[i-1]); yp=y[i]
    env=(t/t[-1])**2.4
    sw=np.sin(np.cumsum(2*np.pi*(260+1900*(t/t[-1])**2)/SR))*0.10*env
    out=y*env+sw
    return np.tanh(out*1.5)*0.85

def tom():
    n=int(0.19*SR); t=np.arange(n)/SR
    f=196+60*np.exp(-t/0.02)
    y=np.sin(np.cumsum(2*np.pi*f/SR))*np.exp(-t/0.05)
    y+=0.3*np.sin(np.cumsum(2*np.pi*f*1.49/SR))*np.exp(-t/0.03)
    return np.tanh(y*1.5)*0.85

specs={}
for nm,fn in [('kick',kick),('snare',snare),('clap',clap),('agogo',agogo),
              ('crash',crash),('riser',riser),('tom',tom)]:
    specs[nm]=(fn(),0,0)
specs['hhc']=(hat(0.011),0,0)
specs['hho']=(hat(0.085,1.2),0,0)

d,ls,ll=gen_sustain(T_BASS,T_SAW,0.05,128,attack=0.004,pitch_drop=0.10,pitch_tau=0.010,bright_ms=35)
specs['bass']=(d,ls,ll)
d,ls,ll=gen_sustain(T_LEAD,T_SAW,0.085,1664,vib_depth=0.0075,attack=0.006,decay_to=0.94,decay_tau=0.35,bright_ms=55)
specs['lead']=(d,ls,ll)
d,ls,ll=gen_sustain(T_SOFT,T_TRI,0.09,1280,vib_depth=0.006,attack=0.030,decay_to=0.85,decay_tau=0.5)
specs['soft']=(d,ls,ll)
d,ls,ll=gen_sustain(T_ARP,T_SAW,0.30,64,attack=0.003,decay_to=0.26,decay_tau=0.065,bright_ms=90)
specs['arp']=(d,ls,ll)
d,ls,ll=gen_sustain(T_STAB,T_SAW,0.28,64,attack=0.002,decay_to=0.15,decay_tau=0.10,bright_ms=70)
specs['stab']=(d,ls,ll)
d,ls,ll=gen_sustain(T_SOFT,T_SAW6,0.42,1664,vib_depth=0.004,attack=0.34,decay_to=0.72,decay_tau=1.2,bright_ms=200)
specs['pad']=(d,ls,ll)
d,ls,ll=gen_sustain(T_SUB,T_SUB,0.02,64,attack=0.006)
specs['sub']=(d,ls,ll)

SCALE={'kick':1.12,'snare':0.95,'clap':0.9,'hhc':0.85,'hho':0.9,'agogo':0.85,
'crash':1.15,'riser':2.6,'tom':0.9,'bass':0.75,'lead':0.95,'soft':0.55,
'arp':0.6,'stab':0.6,'pad':0.55,'sub':0.7}
meta={}
for name,(d,ls,ll) in specs.items():
    L=wrt(name,d*SCALE.get(name,1.0),fade=(ll==0)); meta[name]=(L,ls,ll)
    print(f'{name:7s} len={L:6d} loop=({ls},{ll}) dur={L/SR:.3f}s dc={d.mean():.5f}')
json.dump(meta,open('work/smp/meta.json','w'))
