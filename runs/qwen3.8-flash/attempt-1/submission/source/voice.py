"""Final sample material. Static periodic waveforms (period P samples, exact integer)
   + synthesized percussion. Engine law: f = (SR/P)*2^((note-61)/12), so one P for all
   tonal instruments keeps everything mutually in tune."""
import numpy as np, os, wave, json
SR=44100.0
OUT='/workspace/samples'; os.makedirs(OUT,exist_ok=True)
rng=np.random.RandomState(20240107)
P=169          # 44100/169 = 260.9 Hz at note 61 (C-5); A4 = note 58
def save(name,x,peak=0.9):
    x=np.asarray(x,float); m=np.max(np.abs(x)) or 1.0
    xi=np.int16(np.clip(np.round(x/m*peak*32767),-32768,32767))
    with wave.open(os.path.join(OUT,name+'.wav'),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(int(SR));f.writeframes(xi.tobytes())
    return int(xi.size)
def lpf(x,c):
    y=np.empty_like(x); a=0.0
    for i in range(x.size):
        a+=c*(x[i]-a); y[i]=a
    return y
def hpf(x,c): return x-lpf(x,c)
def svf_low(x,f0,res=0.4):
    F=min(2*np.sin(np.pi*float(np.clip(f0,20,SR*0.45))/SR),0.9); d=2*(1-res)
    low=0.0; band=0.0; out=np.empty_like(x)
    for i in range(x.size):
        high=x[i]-low-d*band
        band=F*high+band; low=F*band+low; out[i]=low
    return out
def svf_band(x,f0,Q=0.8):
    F=min(2*np.sin(np.pi*float(np.clip(f0,20,SR*0.45))/SR),0.9); d=1.0/max(Q,0.5)
    low=0.0; band=0.0; out=np.empty_like(x)
    for i in range(x.size):
        high=x[i]-low-d*band
        band=F*high+band; low=F*band+low; out[i]=band*0.6
    return out
def nz(n): return rng.randn(int(n))
def steady(harm, period=P, ops=None, cycles=64, settle=8, phases=None):
    tt=np.arange(cycles*period)
    x=np.zeros(tt.size)
    for k,a in harm.items():
        if a: x+=a*np.sin(2*np.pi*k*tt/period+(phases or {}).get(k,0.0))
    for op in (ops or []):
        t0=op[0]
        if t0=='lp': x=lpf(x,op[1])
        elif t0=='hp': x=hpf(x,op[1])
        elif t0=='tanh': x=np.tanh(op[1]*x)
        elif t0=='lpl': x=svf_low(x,op[1],op[2] if len(op)>2 else 0.4)
        elif t0=='bp': x=svf_band(x,op[1],op[2] if len(op)>2 else 0.8)
    nc=cycles-settle
    loop=x[settle*period:][:nc*period].reshape(nc,period).mean(0)
    loop-=loop.mean()
    return loop
def loopfile(name, loop, ncyc, peak=0.9):
    sig=np.tile(loop,int(ncyc))
    save(name,sig,peak)
    return dict(file=name+'.wav', len=int(sig.size), ls=0, ll=int(sig.size), ncyc=int(ncyc),
                period=P, rel=0, peak=peak)

# ---------------- tonal timbres ----------------
def tonal():
    T={}
    saw=lambda rolloff, kmax=26: {k:(1.0/k)*np.exp(-k/rolloff) for k in range(1,kmax+1)}
    # 1 BASS: fat lowpassed saw + sub emphasis
    h=saw(7.5); h[1]*=1.25; h[2]*=1.15
    lb=steady(h,ops=[('lp',0.38),('lp',0.52),('tanh',2.2)],cycles=72)
    T['bass']=loopfile('b_fat',lb,30)
    # 2 SUBBASS: sine + slight 2nd (for breakdown / pickups)
    h={1:1.0,2:0.22,3:0.06}
    ls=steady(h,ops=[('lp',0.30)],cycles=72)
    T['sub']=loopfile('b_sub',ls,30)
    # 3 LEAD: bright rich saw, doubled phase
    h=saw(6.0); h[2]*=1.1
    l1=steady(h,ops=[('lp',0.55),('lp',0.72),('tanh',1.7)],cycles=72)
    l2=steady(h,ops=[('lp',0.5),('lp',0.7)],cycles=72,phases={k:0.35*np.sin(k) for k in h})
    loop=0.62*l1+0.62*l2
    T['lead']=loopfile('l_fat',loop,26)
    # 4 SOFT/FLUTE lead (sine+few) for counters & bridge
    h={1:1.0,2:0.30,3:0.10,4:0.04}
    l1=steady(h,ops=[('lp',0.35)],cycles=72)
    l2=steady(h,ops=[('lp',0.3)],cycles=72,phases={2:0.8,3:1.6})
    T['soft']=loopfile('l_soft',0.6*l1+0.6*l2,26)
    # 5 PAD: heavily lowpassed saw, long cycles
    h=saw(4.5); h[1]*=1.3
    lp=steady(h,ops=[('lp',0.16),('lp',0.24),('lp',0.4)],cycles=80)
    lp2=steady(h,ops=[('lp',0.14),('lp',0.22)],cycles=80,phases={k:0.6*k for k in h})
    T['pad']=loopfile('p_soft',0.6*lp+0.6*lp2,44)
    # 6 SYNC/ACID: resonant lowpass saw (bridge drive)
    h={k:1.0/k for k in range(1,24)}
    for k in [3,5,7,9]: h[k]*1.7
    l=steady(h,ops=[('lpl',520,0.9),('tanh',2.6),('lp',0.7)],cycles=72)
    T['sync']=loopfile('b_sync',l,30)
    # 7 STEEL/metallic pluck layer (odd partials) for arp/bridge
    h={1:1.0,3:0.55,5:0.36,7:0.26,9:0.18,11:0.13,13:0.09,15:0.07,17:0.05,19:0.035,21:0.025}
    l=steady(h,ops=[('lp',0.6),('tanh',1.5)],cycles=72)
    T['steel']=loopfile('m_steel',l,34)
    # 8 HARPSI: plucky loop with fast-decaying upper partials
    h={k:(1.0/k)*np.exp(-k/6.0)*(2.0 if k in (2,3) else 1.0) for k in range(1,20)}
    l=steady(h,ops=[('lp',0.45),('tanh',2.0)],cycles=72)
    T['harpsi']=loopfile('h_harpsi',l,26)
    return T

# ---------------- shots (single wave files) ----------------
def i16(y,peak=0.9):
    y=np.asarray(y,float); m=np.max(np.abs(y)) or 1.0
    return np.int16(np.clip(np.round(y/m*peak*32767),-32768,32767))
def shots():
    S={}
    def wfile(name,y,peak=0.9):
        xi=i16(y,peak)
        with wave.open(os.path.join(OUT,name+'.wav'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(int(SR));f.writeframes(xi.tobytes())
        S[name]=int(xi.size)
    F0=SR/P
    # ARP pluck
    n=int(0.46*SR); t=np.arange(n)/SR
    o=np.zeros(n)
    for k in range(1,25):
        a=(1.0/k)*np.exp(-k/11.0)*(1.4 if k in (2,3) else 1.0)
        o+=a*np.sin(2*np.pi*k*F0*t)*np.exp(-t/(0.052/(k**0.9)))
    o+=0.35*np.sin(2*np.pi*F0*t)*np.exp(-t/0.093)
    o=lpf(o,0.62)
    wfile('s_arp',o,0.9)
    # BRASS STAB
    n=int(0.44*SR); t=np.arange(n)/SR
    base=np.zeros(n)
    for k in range(1,22):
        base+=(1.0/k)*np.exp(-k/5.0)*np.sin(2*np.pi*k*F0*t)
    base=lpf(base,0.5); base=lpf(base,0.62); base=np.tanh(1.6*base)
    att=int(0.010*SR); rel=int(0.17*SR); hold=max(0,n-att-rel)
    e=np.concatenate([np.linspace(0,1,att)**0.7, np.full(hold,0.93), (1-np.linspace(0,1,rel+1))[1:]**1.2])
    wfile('s_stab',base*e,0.9)
    # SOFT PAD shot (slow swell 1 bar)
    n=int(1.7*SR); t=np.arange(n)/SR
    b=np.zeros(n)
    for k in range(1,13):
        b+=(1.0/k)*np.exp(-k/4.0)*np.sin(2*np.pi*k*F0*t)
    b=lpf(b,0.2); b=lpf(b,0.3)
    e=(np.sin(np.pi*np.linspace(0,1,n))**1.4)
    wfile('s_swell',b*e,0.85)
    # TROTB tuned shot for fills (higher pitched tom)
    n=int(0.5*SR); t=np.arange(n)/SR
    f=300*np.exp(-t/0.22)+150
    ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)+0.3*np.sin(2*ph)
    nzr=svf_band(nz(n),2400,0.9)*0.22
    wfile('s_tom',body*np.exp(-t/0.18)+nzr*np.exp(-t/0.05),0.9)
    # LOW TOM
    n=int(0.6*SR); t=np.arange(n)/SR
    f=150*np.exp(-t/0.2)+80
    ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)+0.35*np.sin(2*ph)
    nzr=svf_band(nz(n),1400,0.9)*0.2
    wfile('s_ltom',body*np.exp(-t/0.2)+nzr*np.exp(-t/0.05),0.9)
    return S

# ---------------- drums ----------------
def drums():
    D={}
    def wfile(name,y,peak=0.95):
        xi=i16(y,peak)
        with wave.open(os.path.join(OUT,name+'.wav'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(int(SR));f.writeframes(xi.tobytes())
        D[name]=int(xi.size)
    # KICK
    n=int(0.23*SR); t=np.arange(n)/SR
    k=17.0; f0=178.0; fe=43.0
    ph=2*np.pi*(fe*t+(f0-fe)/k*(1-np.exp(-k*t)))
    body=np.sin(ph)*np.exp(-t/0.098)
    cl=lpf(nz(n),0.44)
    y=body+0.5*cl*np.exp(-t/0.0045)+0.18*np.sin(2*np.pi*720*t)*np.exp(-t/0.012)
    nf=int(0.0015*SR); y[:nf]*=np.linspace(0,1,nf); y[-nf:]*=np.linspace(1,0,nf)
    wfile('d_kick',y,0.98)
    # SNARE
    n=int(0.36*SR); t=np.arange(n)/SR
    s=svf_band(nz(n),1800,0.7)+0.55*svf_band(nz(n),3600,0.9)
    tone=np.sin(2*np.pi*192*t)*0.6*np.exp(-t/0.033)+np.sin(2*np.pi*290*t)*0.33*np.exp(-t/0.05)
    y=1.35*s*np.exp(-t/0.078)+tone
    nf=int(0.0015*SR); y[:nf]*=np.linspace(0,1,nf); y[-nf:]*=np.linspace(1,0,nf)
    wfile('d_snare',y,0.92)
    # CLAP
    n=int(0.30*SR); t=np.arange(n)/SR
    src=svf_band(nz(n),1250,0.7)+0.4*svf_band(nz(n),2600,1.0)
    o=np.zeros(n)
    for off,amp in [(0.0,1.0),(0.010,0.9),(0.020,0.74),(0.033,0.95)]:
        d=np.maximum(t-off,0); o+=amp*src*np.exp(-d/0.045)*(t>=off)
    y=o+0.25*np.sin(2*np.pi*900*t)*np.exp(-t/0.03)
    nf=int(0.002*SR); y[:nf]*=np.linspace(0,1,nf); y[-nf:]*=np.linspace(1,0,nf)
    wfile('d_clap',y,0.9)
    # HATS
    def hat(dur,dec,f1,f2,mix):
        n=int(dur*SR); t=np.arange(n)/SR
        y=(svf_band(nz(n),f1,0.9)+mix*svf_band(nz(n),f2,1.1))*np.exp(-t/dec)
        nf=int(0.001*SR); y[:nf]*=np.linspace(0,1,nf); y[-nf:]*=np.linspace(1,0,nf)
        return y
    wfile('d_hatc',hat(0.07,0.0105,8600,13000,0.55),0.6)
    wfile('d_fato',hat(0.52,0.14,6500,10000,0.6),0.6)
    wfile('d_shak',hat(0.13,0.030,5200,9200,0.85),0.5)
    # CRASH
    n=int(2.8*SR); t=np.arange(n)/SR
    s=svf_band(nz(n),4800,0.55)+0.5*svf_band(nz(n),8600,0.8)+lpf(nz(n),0.10)
    y=s*np.exp(-t/0.9)*(1+0.3*np.sin(2*np.pi*2.9*t))+0.12*np.sin(2*np.pi*1250*t)*np.exp(-t/0.5)
    nf=int(0.003*SR); y[:nf]*=np.linspace(0,1,nf); y[-nf:]*=np.linspace(1,0,nf)
    wfile('d_crash',y,0.72)
    # RISER (2 bars = 1.714 s at bpm140 speed2 => 12 rows*? ) make 2.0 s
    n=int(1.9*SR); t=np.arange(n)/SR
    o=np.zeros(n)
    nch=48; step=n//nch
    for c in range(nch):
        a=c*step; z=min(n,(c+1)*step)
        o[a:z]=svf_band(nz(z-a),300+4400*((a/n)**1.7),0.8)
    f=180+1300*(t/t.max())**2
    tone=np.sin(2*np.pi*np.cumsum(f)/SR)*0.3
    y=(o+tone)*(t/t.max())**1.9
    wfile('d_riser',y,0.8)
    # NOISE HIT / perc stab
    n=int(0.16*SR); t=np.arange(n)/SR
    y=svf_band(nz(n),3000,0.6)*np.exp(-t/0.035)
    nf=int(0.001*SR); y[:nf]*=np.linspace(0,1,nf)
    wfile('d_hit',y,0.55)
    return D

def manifest():
    import numpy as np
    T=tonal(); S=shots(); D=drums()
    # write shot/drums wav already done inside funcs; build unified manifest
    out={'tonal':{},'shot':{},'drum':{}}
    for k,v in T.items():
        out['tonal'][k]=v
    # shots() returns name->len
    for k,v in S.items():
        out['shot'][k]=dict(file=k+'.wav',len=v,rel=0,peak=0.9)
    for k,v in D.items():
        out['drum'][k]=dict(file=k+'.wav',len=v,rel=0,peak=0.95)
    json.dump(out,open('/workspace/build/manifest.json','w'),indent=1)
    return out

if __name__=='__main__':
    m=manifest()
    print(json.dumps(m,indent=1)[:3000])
