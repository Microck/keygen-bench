import numpy as np, struct, os
SR=22050
K1=0.4728      # one-shot playback rate factor at note 48
KL=0.9454      # looped playback rate factor at note 48
def nf(note):  # musical freq of tracker note (48=C4)
    return 440.0*2**((note-69)/12.0)
def wav(path,x,sr=SR):
    v=np.clip(np.round(np.asarray(x)*127),-128,127).astype(np.int16)<<8
    d=v.tobytes()
    hdr=b'RIFF'+struct.pack('<I',36+len(d))+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16)+b'data'+struct.pack('<I',len(d))
    open(path,'wb').write(hdr+d)
    return len(v)
def env(n,att,dec,sus=None,rel=0):
    e=np.ones(n)
    a=max(1,int(att*SR))
    e[:a]=np.linspace(0,1,a)
    d=int(dec*SR)
    e[a:]=np.exp(-np.arange(n-a)/max(1,d)*4.0)
    return e
def lowpass(x,fc):
    # simple 1-pole
    a=np.exp(-2*np.pi*fc/SR); y=np.zeros_like(x); s=0.0
    for i in range(len(x)):
        s=(1-a)*x[i]+a*s; y[i]=s
    return y
def harm_table(L,amps,phases=None):
    t=np.arange(L); x=np.zeros(L)
    for k,a in enumerate(amps):
        if k==0: continue
        ph=0.0 if phases is None else phases[k-1]
        x+=a*np.sin(2*np.pi*k*t/L+ph)
    return x
def soft(x,drive=1.0):
    return np.tanh(x*drive)/np.tanh(drive)
# ---------------- percussion (one-shots, pitch-compensated by K1) -------------
def kick():
    n=int(0.30*SR); t=np.arange(n)/SR
    f=(230.0-135.0*np.exp(-t*45))/K1        # 230->95 Hz in file space == 110->45 Hz out
    ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)*np.exp(-t*11)
    click=np.exp(-t*260)*0.5*np.sin(2*np.pi*2600*t/SR)
    x=soft(body*1.5+click,1.4)*0.9
    return x
def snare():
    n=int(0.22*SR); t=np.arange(n)/SR
    nz=np.random.RandomState(7).randn(n)
    nz=nz-np.convolve(nz,np.ones(64)/64,mode='same')
    nz*=np.exp(-t*26)*0.85
    body=(np.sin(2*np.pi*399*t/SR)+0.6*np.sin(2*np.pi*520*t/SR))*np.exp(-t*30)*0.5
    return soft(nz+body,1.2)*0.95
def hat(dur):
    n=int(dur*SR); t=np.arange(n)/SR
    r=np.random.RandomState(11+int(dur*100)).randn(n)
    # metallic ring: high partials
    ring=sum(np.sin(2*np.pi*f*t/SR+ph) for f,ph in ((7600,0.3),(9400,1.1),(11800,2.2),(14300,0.7)))*0.12
    hi=(r-ring*0.5)*np.exp(-t/(0.016 if dur<0.1 else 0.10))
    # one-pole highpass (gentler than a raw difference)
    a=np.exp(-2*np.pi*3500.0/SR); s=0.0; lp=np.zeros_like(hi)
    for i in range(len(hi)):
        s=(1-a)*hi[i]+a*s; lp[i]=s
    x=(hi-lp)*1.25
    return np.clip(x/(np.abs(x).max()+1e-9)*0.75,-1,1)
def tom():
    n=int(0.20*SR); t=np.arange(n)/SR
    f=300.0*np.exp(-t*12)/K1
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*16)
    return x*0.85
# ---------------- pitched wavetables -----------------------------------------
def table(L,amps):
    x=harm_table(L,amps)
    x/= (np.max(np.abs(x))+1e-9)
    return x
def bass_tab():
    L=pick_len(55.0,33)   # A1-ish reference
    amps=[0]+[1.0/(k**1.15) for k in range(1,11)]
    x=table(L,amps)
    # add sub
    x=0.85*x+0.45*np.sin(2*np.pi*np.arange(L)/L)
    x=soft(x*1.3,1.25)
    return x/max(np.abs(x))
def lead_tab():
    L=pick_len(440.0,69)
    amps=[0]+[1.0/(k**0.95) for k in range(1,16)]
    amps[1]*=1.1; amps[4]*=1.25; amps[6]*=1.15
    x=table(L,amps)
    return soft(x*1.1,1.1)*0.95
def arp_tab():
    L=pick_len(440.0,69)
    amps=[0]+[1.0/(k**0.85) for k in range(1,19)]
    amps[2]*=1.3
    x=table(L,amps)
    return soft(x*1.25,1.2)*0.95
def pad_tab():
    L=pick_len(220.0,57)
    amps=[0]+[1.0/(k**1.3) for k in range(1,13)]
    amps[1]*=1.2; amps[2]*=1.3
    x=table(L,amps)
    return soft(x*0.9,1.05)*0.9
def bell():
    n=int(1.6*SR); t=np.arange(n)/SR
    fc=440.0/K1
    m=np.exp(-t*2.2)
    y=(np.sin(2*np.pi*fc*t+3.2*m)*np.exp(-t*2.0)+0.5*np.sin(2*np.pi*fc*2.76*t)*np.exp(-t*3.2)
       +0.3*np.sin(2*np.pi*fc*5.4*t)*np.exp(-t*5.0))
    y*=np.exp(-t*1.1)
    y/=np.max(np.abs(y))
    return y
def crash():
    n=int(1.4*SR); t=np.arange(n)/SR
    r=np.random.RandomState(23).randn(n)
    r=np.diff(np.concatenate([[0],r]))*4.0
    metal=sum(np.sin(2*np.pi*f*t/SR+ph) for f,ph in ((5200,0.2),(7100,1.4),(9300,2.6),(12400,0.9),(15700,3.3)))*0.10
    x=(r*0.5+metal)*np.exp(-t*3.2)*(1-np.exp(-t*900))
    return np.clip(x/max(np.abs(x))*0.95,-1,1)
def riser():
    n=int(1.2*SR); t=np.arange(n)/SR
    r=np.random.RandomState(31).randn(n)
    band=np.cumsum(r); band=band-band.mean()
    x=band*np.exp(-t*1.2)*(t/1.2)**2
    f=(300+2600*(t/1.2)**2)/K1
    tone=np.sin(2*np.pi*np.cumsum(f)/SR)*(t/1.2)**3*0.4
    y=x/max(np.abs(x))+tone
    return np.clip(y/max(np.abs(y))*0.98,-1,1)
def pluck():
    n=int(0.7*SR); t=np.arange(n)/SR
    fc=440.0/K1
    y=sum(np.sin(2*np.pi*fc*k*t)*np.exp(-t*(3.0+1.6*k)) for k in range(1,9))
    y*=np.exp(-t*3.0)
    return y/np.max(np.abs(y))*0.9
def stab(chord,semitones=(0,3,7,12),dur=0.38):
    n=int(dur*SR); t=np.arange(n)/SR
    y=np.zeros(n)
    base=220.0/K1
    for s in semitones:
        f=base*2**(s/12.0)
        for h,a in ((1,1.0),(2,0.55),(3,0.33),(4,0.20),(5,0.12),(6,0.07)):
            y+=a*np.sin(2*np.pi*f*h*t+0.4*h)*np.exp(-t*(6.0+2.0*h))
    y*=np.exp(-t*7.0)
    y=soft(y*0.8,1.4)
    return y/max(np.abs(y))*0.95
def pick_len(f_target,note_ref):
    # choose integer L so that the loop tone lands as close as possible
    ft=f_target/(KL*2**((note_ref-48)/12.0))
    best=None
    for L in range(64,513):
        e=abs(np.log2((SR/L)/ft))
        if best is None or e<best[1]: best=(L,e)
    return best[0]
if __name__=='__main__':
    import sys
    os.makedirs('/workspace/work/samples',exist_ok=True)
    D='/workspace/work/samples/'
    wav(D+'kick.wav',kick()); wav(D+'snare.wav',snare())
    wav(D+'hat.wav',hat(0.045)); wav(D+'ohat.wav',hat(0.30))
    wav(D+'tom.wav',tom())
    wav(D+'bass.wav',bass_tab(),SR)
    wav(D+'lead.wav',lead_tab(),SR)
    wav(D+'arp.wav',arp_tab(),SR)
    wav(D+'pad.wav',pad_tab(),SR)
    wav(D+'bell.wav',bell()); wav(D+'pluck.wav',pluck())
    wav(D+'crash.wav',crash()); wav(D+'riser.wav',riser())
    wav(D+'stab_am.wav',stab((0,3,7)))
    wav(D+'stab_f.wav',stab((0,4,7)))
    wav(D+'stab_c.wav',stab((0,4,7,12)))
    wav(D+'stab_e.wav',stab((0,4,7,10)))
    import json
    man={'kick':(0,0),'snare':(0,0),'hat':(0,0),'ohat':(0,0),'tom':(0,0),
         'bell':(0,0),'pluck':(0,0),'crash':(0,0),'riser':(0,0),
         'stab_am':(0,0),'stab_f':(0,0),'stab_c':(0,0),'stab_e':(0,0),
         'bass':(len(bass_tab()),1),'lead':(len(lead_tab()),1),'arp':(len(arp_tab()),1),'pad':(len(pad_tab()),1)}
    json.dump(man,open('/workspace/work/manifest.json','w'),indent=1)
    print(man)
