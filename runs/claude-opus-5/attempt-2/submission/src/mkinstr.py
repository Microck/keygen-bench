import sys, json, base64, numpy as np
sys.path.insert(0,'/workspace/build')
from synth import *

calls = []
SAMPLES = []
def b64(x): return base64.b64encode(np.asarray(np.clip(x,-1,1), dtype='<f4').tobytes()).decode()

import wave as _wave, os
os.makedirs('/workspace/build/smp',exist_ok=True)
VSCALE=0.78
def add(idx, name, data, rel, fine=0, vol=64, pan=128, loop=None, slot=0):
    vol=int(round(vol*VSCALE))
    path='/workspace/build/smp/%02d_%s.wav'%(idx,name.replace(' ','_').replace('/','_'))
    x=np.clip(np.asarray(data,dtype=np.float64),-1,1)
    q=np.clip(np.round(x*127.0),-127,127).astype(np.int16)+128
    w=_wave.open(path,'wb'); w.setnchannels(1); w.setsampwidth(1); w.setframerate(44100)
    w.writeframes(q.astype(np.uint8).tobytes()); w.close()
    SAMPLES.append((idx,slot,x.copy()))
    calls.append({"name":"sample_load","arguments":{"path":path,"instrument":idx,"sample":slot}})
    a = {"instrument":idx,"sample":slot,"relative_note":rel,"finetune":fine,"volume":vol,"panning":pan,"name":name[:21]}
    if loop: a["loop_start"],a["loop_length"],a["flags"] = loop[0],loop[1],1
    else:    a["loop_start"],a["loop_length"],a["flags"] = 0,0,0
    calls.append({"name":"sample_set","arguments":a})
    calls.append({"name":"instrument_set","arguments":{"instrument":idx,"name":name[:21]}})

def predelay(x, ms=5.4):
    n=int(SRD*ms/1000.0)
    return np.concatenate([np.zeros(n), np.asarray(x)])

L = 128; RELP = rel_for_L(L)   # 36
LB = 512; RELB = rel_for_L(LB)
LP = 256; RELP2 = rel_for_L(LP)

# ---- drums / one shots ----
add(1,"kick",       predelay(kick()),        REL_D, 0, 62, 128)
add(2,"snare",      predelay(snare()),       REL_D, 0, 64, 128)
add(3,"clap",       predelay(clap()),        REL_D, 0, 58, 134)
add(4,"hat closed", predelay(hat(0.055,7000,0.011,0.25)), REL_D, 0, 64, 148)
add(5,"hat open",   predelay(hat(0.30,6000,0.085,0.26)),  REL_D, 0, 48, 112)
add(6,"crash",      predelay(crash(1.6)),    REL_D, 0, 52, 128)
add(7,"tom",        predelay(tom(165,0.32)), REL_D, 0, 50, 110)
add(13,"riser",     riser(1.8),    REL_D, 0, 48, 128)
add(14,"zap",       predelay(zap(0.6)),      REL_D, 0, 48, 128)

# ---- bass ----
bp_ = []
for k in range(1,25):
    a = 1.0/k
    a *= 1.0/np.sqrt(1.0+(k/4.2)**6)
    a *= 1.0 + 1.7*np.exp(-((k-4.0)/1.3)**2)
    bp_.append((float(k), a, 0.0))
bp_[0] = (1.0, 1.25, 0.0)
bs, ls_, ll_ = make_sustain(LB, 4, bp_, atk_cycles=2, curve=1.0)
# brighter attack chunk prepended
atkp = [(float(k), (1.0/k)*1.0/np.sqrt(1.0+(k/13.0)**4), 0.0) for k in range(1,25)]
atk = harm_sum(LB,2,atkp); atk = atk/np.max(np.abs(atk))*0.9*np.linspace(0,1,2*LB)**0.6
bsmp = np.concatenate([atk, bs])
add(8,"bass", norm(bsmp,0.92), RELB, 0, 44, 128, loop=(2*LB+ls_, ll_))

# ---- pluck / arp ----
pp = saw_partials(1.0, 20, 5.5, pw=0.32)
pw_ = pluck_wave(LP, 96, pp, tau0=20.0, tau_fall=0.07)
add(9,"arp pluck L", pw_, RELP2, -4, 44, 46)
add(16,"arp pluck R", pw_, RELP2, 5, 44, 210)

# ---- lead supersaw ----
C = 128
lp_ = []
for det,g,ph in [(0.0,1.0,0.0),(1.0/C,0.85,0.31),(-1.0/C,0.85,0.63),(2.0/C,0.5,0.11),(-2.0/C,0.5,0.87)]:
    lp_ += saw_partials(1.0+det, 18, 7.0, amp=g, ph0=ph)
lp_ += [(2.0, 0.22, 0.4)]
lsmp, lls, lll = make_sustain(L, C, lp_, atk_cycles=6, curve=1.4)
add(10,"lead saw L", lsmp, RELP, -6, 52, 62, loop=(lls,lll))
add(17,"lead saw R", lsmp, RELP, 7, 52, 194, loop=(lls,lll))

# ---- pad ----
pd = []
for det,g,ph in [(0.0,1.0,0.0),(1.0/C,0.8,0.5),(-1.0/C,0.8,1.1),(3.0/C,0.6,2.0),(-3.0/C,0.6,2.7)]:
    pd += saw_partials(1.0+det, 16, 3.0, amp=g, ph0=ph)
pd += [(2.0,0.3,0.2),(3.0,0.14,1.4)]
psmp, pls, pll = make_sustain(LP, C, pd, atk_cycles=28, curve=2.2)
add(11,"pad", psmp, RELP2, 0, 26, 128, loop=(pls,pll))

# ---- bell ----
bell_p = [(1.0,1.0,0.0),(2.0,0.55,0.9),(3.01,0.42,1.7),(4.18,0.3,0.4),(5.62,0.13,2.3),
          (7.24,0.08,1.1),(9.11,0.05,0.2),(11.4,0.03,2.8)]
bell = pluck_wave(L, 256, bell_p, tau0=95.0, tau_fall=0.33)
add(12,"bell", bell, RELP, 0, 44, 128)

# ---- stab (chip organ) ----
sp = saw_partials(1.0, 14, 4.5, pw=0.5) + [(2.0,0.35,0.5),(4.0,0.12,1.0)]
stab = pluck_wave(LP, 72, sp, tau0=45.0, tau_fall=0.04)
add(15,"stab", stab, RELP2, 0, 40, 128)

json.dump(calls, open('/workspace/build/instr.json','w'))
print("calls", len(calls))
