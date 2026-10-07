import numpy as np, sys, json
sys.path.insert(0,'/workspace')
from dsp import *
from ft import b64i, batch
from song import INSTVOL

SAMPLES = {}   # inst -> dict(data, rel, fine, vol, name, loop_start, loop_len, flags, pan)

def reg(inst, name, data, design_note=49, fine=0, vol=64, pan=128, loop=None, peak=0.95, tilt=None):
    d = np.asarray(data, dtype=np.float64)
    if tilt:
        if loop:   # keep loop phase continuity: filter the tiled signal
            ls, ll = loop
            pre = d[ls:ls+ll]
            d2 = onepole_lp(np.concatenate([pre, d]), tilt)[len(pre):]
            d = d2
        else:
            d = onepole_lp(d, tilt)
    d = norm(d, peak)
    e = dict(name=name, data=d, rel=73-design_note, fine=fine, vol=vol, pan=pan)
    if loop: e['loop_start'], e['loop_len'] = loop
    else: e['loop_start'], e['loop_len'] = 0,0
    SAMPLES[inst] = e

# ---------------- drums ----------------
# 1 KICK
t = tarr(0.34)
f = 48 + 170*np.exp(-t/0.022) + 600*np.exp(-t/0.0035)
ph = 2*np.pi*np.cumsum(f)/SR
body = np.sin(ph)*np.exp(-t/0.085)
click = onepole_hp(noise(len(t)),4000)*np.exp(-t/0.0035)*0.5
k = np.tanh((body*1.5+click)*1.6)
k *= np.minimum(1.0, np.linspace(0,1,len(t))*400)
k = fadeends(k, 300)
reg(1,'kick', k, 49, vol=64)

# 2 SNARE
t = tarr(0.26)
n = noise(len(t))
n = onepole_hp(n, 900)
tone = (np.sin(2*np.pi*186*t)+0.7*np.sin(2*np.pi*279*t))*np.exp(-t/0.045)
body = svf_lp(n, 6500, 0.4)*np.exp(-t/0.075) + n*np.exp(-t/0.12)*0.55
s = np.tanh((tone*0.9 + body*0.9)*1.3)
s = fadeends(s, 200)
reg(2,'snare', s, 49, vol=54, tilt=None)

# 3 CLAP
t = tarr(0.33)
n = noise(len(t))
bp = svf_lp(onepole_hp(n,1100), 3400, 0.6)
env = np.zeros(len(t))
for off,a in [(0.0,1.0),(0.011,0.9),(0.022,0.85),(0.034,0.8)]:
    i = int(off*SR)
    env[i:] = np.maximum(env[i:], a*np.exp(-(t[:len(t)-i])/0.011))
env += 0.5*np.exp(-t/0.16)*(t>0.034)
c = bp*env
c = fadeends(c, 200)
reg(3,'clap', c, 49, vol=46, tilt=None)

# 4 HHC
t = tarr(0.075)
n = onepole_hp(noise(len(t)), 4200)
n = svf_lp(n, 11000, 0.4)
h = n*np.exp(-t/0.0125)
h = fadeends(h, 80)
reg(4,'hhc', h, 49, vol=30, tilt=None)

# 5 HHO
t = tarr(0.42)
n = svf_lp(onepole_hp(noise(len(t)), 4000), 10500, 0.4)
h = n*(np.exp(-t/0.13)*0.95+0.05)*np.minimum(1,t*600)
h *= np.linspace(1,0,len(t))**0.5
h = fadeends(h, 300)
reg(5,'hho', h, 49, vol=28, tilt=None)

# 6 CRASH
t = tarr(1.5)
n = svf_lp(onepole_hp(noise(len(t)), 3000), 12000, 0.4)
res = np.zeros(len(t))
for fr in [3100,4300,5700,7900,9300,11500]:
    res += np.sin(2*np.pi*fr*t + rng.uniform(0,6))*0.12
c = (n + res*0.4)*np.exp(-t/0.45)*np.minimum(1,t*2000)
c *= np.linspace(1,0,len(t))**0.6
c = fadeends(c, 400)
reg(6,'crash', c, 49, vol=38, tilt=None)

# ---------------- bass ----------------
# 7 BASS  design C-2 = 65.406
f0 = 65.40639
t = tarr(0.40)
w = saw(f0, t, K=90)*0.8 + square(f0*2, t, 0.5, K=45)*0.25
cut = 380 + 4500*np.exp(-t/0.06)
b = svf_lp(w, cut, 0.62)
b += np.sin(2*np.pi*f0*t)*0.55*np.exp(-t/0.13)
b *= np.exp(-t/0.17)*np.minimum(1, np.linspace(0,1,len(t))*600)
b = np.tanh(b*1.5)
b = fadeends(b, 200)
reg(7,'bass', b, 25, vol=58)

# 8 SUB  design C-2
t = tarr(0.5)
sb = np.sin(2*np.pi*f0*t + 0.9*np.sin(2*np.pi*f0*t)*np.exp(-t/0.02))
sb *= np.exp(-t/0.22)*np.minimum(1, np.linspace(0,1,len(t))*500)
sb = fadeends(sb, 200)
reg(8,'sub', sb, 25, vol=50)

# 9 PLUCK  design C-5 = 523.25
f1 = 523.2511
t = tarr(0.30)
w = square(f1,t,0.42,K=18)*0.9 + saw(f1*1.005,t,K=14)*0.35 + saw(f1*0.995,t,K=14)*0.35
cut = 2600+9500*np.exp(-t/0.05)
p = svf_lp(w, cut, 0.5)*np.exp(-t/0.085)
p *= np.minimum(1, np.linspace(0,1,len(t))*2000)
p = fadeends(p, 120)
reg(9,'pluck', p, 61, vol=44)

# ---------------- looped leads ----------------
L = 16384
F0 = SR/L
base = 256  # 522.69 Hz
fine_lead = finetune_for(523.2511, base*F0)

# 10 LEADP : PWM pulse
tt = np.arange(L)/SR
duty = 0.5 + 0.16*np.sin(2*np.pi*np.arange(L)/L)
lw = np.zeros(L)
fb = base*F0
K = int(9000/fb)
for k in range(1,K+1):
    lw += (2.0/(np.pi*k))*np.sin(np.pi*k*duty)*np.cos(2*np.pi*k*fb*tt)
lw += 0.12*np.sin(2*np.pi*fb*0.5*tt)   # sub octave (bin 128, integer -> loops fine)
lw = norm(lw,0.95)
head = lw*np.minimum(1.0, np.arange(L)/ (0.004*SR))
data = np.concatenate([head, lw])
reg(10,'leadpwm', data, 61, fine=fine_lead, vol=46, loop=(L, L))

# 11 LEADS : supersaw
parts=[]
Kmax = int(9000/fb)
for k in range(1,Kmax+1):
    a = 1.0/k
    parts += [(base*k, a), ((base-2)*k, a*0.8), ((base+2)*k, a*0.8), ((base-5)*k, a*0.45), ((base+5)*k,a*0.45)]
lw2 = harm_loop(L, parts, seed=11)
lw2 = norm(np.tanh(lw2*1.3),0.95)
head2 = lw2*np.minimum(1.0, np.arange(L)/(0.006*SR))
reg(11,'leadsaw', np.concatenate([head2, lw2]), 61, fine=fine_lead, vol=40, loop=(L,L))

# ---------------- pads (chord loops) ----------------
LP = 16384
F0p = SR/LP
rootbin = 128  # 261.34
fine_pad = finetune_for(261.6256, rootbin*F0p)
def pad_chord(intervals, seed):
    parts=[]
    for iv in intervals:
        b0 = rootbin*(2**(iv/12.0))
        for k in range(1,int(7000/(b0*F0p))+1):
            a = 1.0/(k**1.35)
            for d,w in [(-1,0.7),(0,1.0),(1,0.7)]:
                parts.append((round(b0*k)+d*k, a*w))
    w = harm_loop(LP, parts, seed=seed)
    return norm(w,0.95)
for inst,(name,ivs,sd) in {12:('padmin',[0,3,7,12,19],21),13:('padmaj',[0,4,7,12,19],22)}.items():
    lwp = pad_chord(ivs, sd)
    headp = lwp*np.minimum(1.0, np.arange(LP)/(0.35*SR))
    reg(inst,name, np.concatenate([headp, lwp]), 49, fine=fine_pad, vol=26, loop=(LP,LP))

# ---------------- stabs (chord plucks) ----------------
def stab(ivs):
    t = tarr(0.45)
    w = np.zeros(len(t))
    for iv in ivs:
        f = 261.6256*2**(iv/12.0)
        w += saw(f*1.004,t,K=int(9000/f))*0.5 + saw(f*0.996,t,K=int(9000/f))*0.5
    cut = 1700+8000*np.exp(-t/0.06)
    w = svf_lp(w, cut, 0.55)*np.exp(-t/0.11)
    w *= np.minimum(1, np.linspace(0,1,len(t))*1500)
    return fadeends(w,150)
reg(14,'stabmin', stab([0,3,7,12]), 49, vol=40)
reg(15,'stabmaj', stab([0,4,7,12]), 49, vol=40)

# ---------------- extras ----------------
# 16 BELL (FM) design C-5
t = tarr(0.9)
f1 = 523.2511
mod = np.sin(2*np.pi*f1*3.5*t)*np.exp(-t/0.12)*4.0
bl = np.sin(2*np.pi*f1*t + mod)*np.exp(-t/0.28)
bl += 0.3*np.sin(2*np.pi*f1*2*t)*np.exp(-t/0.14)
bl *= np.minimum(1, np.linspace(0,1,len(t))*3000)
reg(16,'bell', fadeends(bl,200), 61, vol=38, tilt=None)

# 17 SWEEP riser (noise bandpass sweeping up) 2.4 s
t = tarr(2.4)
n = noise(len(t))
cut = 300*np.exp(t/0.62)
sw = svf_lp(onepole_hp(n,200), np.clip(cut,200,12000), 0.92)
sw *= (np.linspace(0,1,len(t))**2.2)
sw = fadeends(sw, 400)
reg(17,'sweep', sw, 49, vol=34)

# 18 ZAP  (downward pitch blip)
t = tarr(0.22)
f = 1800*np.exp(-t/0.05)+90
ph = 2*np.pi*np.cumsum(f)/SR
z = square(1,np.zeros(1))  # dummy
z = np.sign(np.sin(ph))*0.6 + np.sin(ph)*0.5
z = svf_lp(z, 6000, 0.4)*np.exp(-t/0.06)
reg(18,'zap', fadeends(z,120), 49, vol=36)

# 19 REVERSE CRASH
t = tarr(1.3)
n = onepole_hp(noise(len(t)),2500)
rc = n*(np.linspace(0,1,len(t))**2.5)
rc = svf_lp(rc, 200+9000*np.linspace(0,1,len(t))**1.5, 0.5)
reg(19,'revcym', fadeends(rc,300), 49, vol=36)

# 20 TOM  design C-3
t = tarr(0.33)
f = 160*np.exp(-t/0.09)+72
ph = 2*np.pi*np.cumsum(f)/SR
tm = np.sin(ph)*np.exp(-t/0.11) + onepole_hp(noise(len(t)),2000)*np.exp(-t/0.012)*0.25
reg(20,'tom', fadeends(np.tanh(tm*1.3),200), 49, vol=46)

if __name__ == '__main__':
    calls=[]
    for inst in sorted(SAMPLES):
        e = SAMPLES[inst]
        calls.append({"name":"sample_create_from_pcm","arguments":{"instrument":inst,"sample":0,
            "pcm": b64i(e['data']), "encoding":"int16", "name": e['name']}})
        args = {"instrument":inst,"sample":0,"relative_note":e['rel'],"finetune":e['fine'],
                "volume":INSTVOL.get(inst,e['vol']),"panning":e['pan']}
        if e['loop_len']>0:
            args.update({"loop_start":e['loop_start'],"loop_length":e['loop_len'],"flags":17})
        else:
            args.update({"loop_start":0,"loop_length":0,"flags":16})
        calls.append({"name":"sample_set","arguments":args})
        calls.append({"name":"instrument_set","arguments":{"instrument":inst,"name":e['name']}})
    out = batch(calls,'build/_samples.json')
    print(out[-200:])
    for inst in sorted(SAMPLES):
        e=SAMPLES[inst]
        d=e['data']
        print(f"{inst:3d} {e['name']:9s} n={len(d):6d} rel={e['rel']:3d} fine={e['fine']:3d} vol={INSTVOL.get(inst,0):3d} "
              f"loop={e['loop_start']},{e['loop_len']} peak={np.abs(d).max():.3f} rms={np.sqrt((d**2).mean()):.4f} "
              f"nan={int(np.isnan(d).any())}")
