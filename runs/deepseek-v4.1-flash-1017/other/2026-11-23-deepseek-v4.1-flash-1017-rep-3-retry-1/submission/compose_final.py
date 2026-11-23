import sys; sys.path.insert(0,'/workspace/work')
import numpy as np, json, os
import synth2 as S2
import final4 as F
from final4 import *

RATE=16726.0; DRATE=33452.0; F0=261.6256

# ---------------- extra synth: short bright chord stab ----------------
def stab(root, intervals, dur=0.30, amp=0.75, rate=RATE, nharm=14):
    n=int(dur*rate); t=np.arange(n)/rate
    x=np.zeros(n)
    for iv in intervals:
        f=root*2**(iv/12)
        for d in (-0.006,0.0,0.006):
            ff=f*(1+d)
            for k in range(1,nharm+1):
                if ff*k>rate/2*0.9: break
                x+=(1.0/k**0.9)*np.sin(2*np.pi*k*ff*t+k*0.3)
    x=S2.hp(x,320,rate,1); x=S2.lp(x,5200,rate,1)
    e=np.exp(-t/0.075)
    a=int(0.004*rate); e[:a]*=np.linspace(0,1,a)
    x*=e
    return S2.norm(S2.fe(x,10),amp)

def make_data():
    ins=[]
    def add(name,data,relnote,loop=False):
        ins.append(dict(name=name,data=data,relnote=relnote,loop=loop))
    add('lead',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.25,nharm=10,cycles=32,amp=0.92),12,True)
    add('leadR', S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=9,cycles=40,amp=0.88),12,True)
    add('lead2', S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=9,cycles=40,amp=0.88),12,True)
    add('echo',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.25,nharm=7,cycles=32,amp=0.85),12,True)
    add('arpL',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=8,cycles=48,amp=0.8),12,True)
    add('arpR',  S2.pulse_loop(rate=RATE,f0=F0,duty=0.125,nharm=8,cycles=48,amp=0.8),12,True)
    add('spark', S2.pulse_loop(rate=RATE,f0=F0,duty=0.0625,nharm=6,cycles=96,amp=0.65),12,True)
    add('bass',  S2.bass_oneshot(rate=RATE,f0=F0,dur=0.42,amp=0.95,decay=0.17),12)
    add('kick',  S2.kick(rate=RATE,dur=0.34,f0=195,f1=48,decay=0.10,click=0.55),12)
    add('snare', S2.snare(rate=RATE,dur=0.24,tone=200),12)
    add('hatC',  S2.hat(rate=DRATE,dur=0.05,decay=0.011,fc=7600),24)
    add('hatO',  S2.openhat(rate=DRATE,dur=0.24,decay=0.055,fc=6400),24)
    add('crash', S2.crash(rate=DRATE,dur=1.4,decay=0.42),24)
    add('tom',   S2.tom(rate=RATE,dur=0.26,f0=340,f1=140),12)
    add('rim',   S2.zap(rate=RATE,dur=0.09,amp=0.6),12)
    add('riser', S2.riser(rate=RATE,dur=1.7),12)
    add('bell',  S2.bell(rate=RATE,f=F0,dur=1.1,amp=0.7),12)
    for ch,(root,ivs) in PADS.items():
        pl=S2.pad(root,ivs,rate=RATE,dur=1.60,amp=0.72,det=0.0040,release=0.40)
        pr=S2.pad(root,ivs,rate=RATE,dur=1.60,amp=0.72,det=-0.0052,release=0.40)
        rl=np.sqrt((pl**2).mean()); rr=np.sqrt((pr**2).mean()); tgt=(rl+rr)/2
        add('pad'+ch+'L', pl*(tgt/rl),12)
        add('pad'+ch+'R', pr*(tgt/rr),12)
        add('stab'+ch, stab(root,ivs),12)
    return ins

DATA=make_data()
NAMES=[d['name'] for d in DATA]
INS={n:i+1 for i,n in enumerate(NAMES)}

# group gains (measured/balanced) -- defaults to 1.0; balanced in balance_final.py
G=dict(lead=1.0,echo=1.0,arp=1.0,bass=1.0,kick=1.0,snare=1.0,hats=1.0,pad=1.0,
       fx=1.0,perc=1.0,spark=1.0)
try:
    import os
    if os.path.exists('/workspace/work/groupgains.json'):
        G.update(json.load(open('/workspace/work/groupgains.json')))
except Exception:
    pass
GAIN=dict(lead=1.00, leadR=0.55, lead2=0.90, echo=1.00, arpL=1.00, arpR=1.00, spark=1.00,
          bass=1.00, kick=1.00, snare=1.00, hatC=1.00, hatO=0.92, crash=0.85, tom=1.00,
          rim=0.85, riser=3.60, bell=1.30, padL=1.00, padR=1.00, stab=0.75)
MASTER=0.60
def _master():
    try:
        import os
        if os.path.exists('/workspace/work/master.json'):
            return float(json.load(open('/workspace/work/master.json'))['master'])
    except Exception:
        pass
    return MASTER
VOL2=dict(lead=54,leadR=30,lead2=46,echo=26,arpL=40,arpR=38,spark=30,bass=60,kick=60,
          snare=60,hatC=50,hatO=46,crash=44,tom=46,rim=36,riser=64,bell=42,padL=44,padR=44,
          stab=38)
PAN2=dict(lead=82,leadR=166,lead2=74,echo=158,arpL=52,arpR=204,spark=96,bass=128,kick=128,
          snare=136,hatC=128,hatO=128,crash=92,tom=58,rim=198,riser=128,bell=160,
          padL=64,padR=192,stab=128)

def group_of(name):
    if name.startswith('pad'): return 'pad'
    if name.startswith('stab'): return 'pad'
    return dict(lead='lead',leadR='lead',lead2='lead',echo='echo',arpL='arp',arpR='arp',
                spark='spark',bass='bass',kick='kick',snare='snare',hatC='hats',hatO='hats',
                crash='fx',riser='fx',bell='fx',tom='perc',rim='perc')[name]

def make_instruments_patched():
    from deltafix import fit_delta
    out=[]
    hicut={}
    try:
        if os.path.exists('/workspace/work/hicut.json'):
            hicut=json.load(open('/workspace/work/hicut.json'))
    except Exception:
        hicut={}
    for it in DATA:
        nm=it['name']
        gk=nm if nm in GAIN else ('padL' if nm.endswith('L') else ('padR' if nm.endswith('R') else 'stab'))
        g=G[group_of(nm)]*GAIN[gk]*_master()
        dat=it['data']
        if nm in hicut:
            hz=float(hicut[nm])
            if hz>100:
                dat=S2.lp(dat, hz, RATE if it['relnote']==12 else DRATE, 2)
        vk=nm if nm in VOL2 else ('padL' if nm.endswith('L') else ('padR' if nm.endswith('R') else 'stab'))
        d=np.clip(dat*g,-0.999,0.999)
        v=VOL2[vk]
        d,v,_=fit_delta(d, v)
        out.append(dict(name=nm, relnote=it['relnote'], loop=it['loop'],
                        vol=v, pan=PAN2[vk], data=d))
    return out

F.make_instruments=make_instruments_patched
F.CH=dict(lead=0,harm=1,echo=2,arpL=3,arpR=4,bass=5,kick=6,snare=7,hats=8,
          padL=9,padR=10,fx=11,fx2=12,spark=13,perc=14,stab=15)
CH=F.CH
F.INS=INS

# ---------------- composition helpers on top of final4 ----------------
A=['Am','F','C','G']; B=['Dm','Bb','F','E']; Cc=['F','G','Em','Am']; O=['Am','F','C','G']

def stabs(T,bar,chord,vol=40,rows=(2,6,10,14),inst=None):
    inst=INS['stab'+chord]
    for r in rows:
        T.note(bar*16+r,CH['stab'],'C-4',inst,vol)

def arp_vol(T,bar,chord,vol=44,mode='updown',step=1,octv=0,volR=None):
    F.arp_bars(T,bar,chord,vol=vol,mode=mode,step=step,octv=octv,vol2=volR)

def build():
    xm=F.build.__wrapped__() if hasattr(F.build,'__wrapped__') else None
    return xm
