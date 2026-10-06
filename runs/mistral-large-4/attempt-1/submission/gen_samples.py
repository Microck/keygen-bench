import numpy as np, wave
sr=44100
def save(x,name):
    x=np.clip(x,-1,1)
    w=wave.open(name,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((x*32767).astype('<i2').tobytes()); w.close()

F0=290.3444104355438   # calibrated base frequency (plays in tune at note C-4)
NH=60                  # harmonics in additive saw

def additive(f0, dur, nh=NH, decay=0.0, attack=0.005, release=0.08, amp=0.8, phase0=0.0):
    n=int(dur*sr); t=np.arange(n)/sr
    y=np.zeros(n)
    for k in range(1,nh+1):
        y+=(1.0/k)*np.sin(2*np.pi*k*f0*t+phase0)
    y/=np.abs(y).max()
    env=np.ones(n)
    A=int(attack*sr); R=int(release*sr)
    if A>0: env[:A]=np.linspace(0,1,A)**1.5
    if R>0: env[-R:]=np.linspace(1,0,R)**1.5
    if decay>0: env*=np.exp(-t*decay)
    return y*env*amp

def pulse(f0, dur, duty=0.25, nh=NH, attack=0.005, release=0.08, amp=0.8):
    n=int(dur*sr); t=np.arange(n)/sr
    y=np.zeros(n)
    for k in range(1,nh+1):
        if k%2==1: y+=(1.0/k)*np.sin(2*np.pi*k*f0*t)
    # add even harmonics with duty-cycle weighting: sin(pi*k*duty)/(pi*k)
    y2=np.zeros(n)
    for k in range(1,nh+1):
        y2+=(np.sin(np.pi*k*duty)/(np.pi*k))*np.sin(2*np.pi*k*f0*t)
    y2/=np.abs(y2).max()
    env=np.ones(n)
    A=int(attack*sr); R=int(release*sr)
    env[:A]=np.linspace(0,1,A)**1.5; env[-R:]=np.linspace(1,0,R)**1.5
    return y2*env*amp

def square(f0,dur,**kw): return pulse(f0,dur,duty=0.5,**kw)
def organ(f0,dur,**kw):
    # hollow: odd harmonics only, softer
    n=int(dur*sr); t=np.arange(n)/sr
    y=np.zeros(n)
    for k in [1,3,5,7,9]: y+=(1.0/k)*np.sin(2*np.pi*k*f0*t)
    y/=np.abs(y).max()
    env=np.ones(n); A=int(0.005*sr); R=int(0.08*sr)
    env[:A]=np.linspace(0,1,A)**1.5; env[-R:]=np.linspace(1,0,R)**1.5
    return y*env*kw.get('amp',0.7)

def noise(dur, amp=0.6, seed=1, lp=1.0):
    rng=np.random.default_rng(seed)
    n=int(dur*sr)
    x=rng.standard_normal(n)
    # simple lowpass
    if lp<1.0:
        k=int(1/lp)
        ker=np.hanning(k*2+1); ker/=ker.sum()
        x=np.convolve(x,ker,mode='same')
    x/=np.abs(x).max()
    env=np.ones(n); A=int(0.002*sr); R=int(0.05*sr)
    env[:A]=np.linspace(0,1,A); env[-R:]=np.linspace(1,0,R)
    return x*env*amp

def kick(dur=0.35, f0=120, amp=0.9):
    n=int(dur*sr); t=np.arange(n)/sr
    f=f0*np.exp(-t*18)+40
    ph=2*np.pi*np.cumsum(f)/sr
    y=np.sin(ph)*np.exp(-t*9)
    y+=0.4*np.sin(2*np.pi*60*t)*np.exp(-t*25)
    y/=np.abs(y).max()
    return y*amp

def snare(dur=0.22, amp=0.8, seed=7):
    rng=np.random.default_rng(seed)
    n=int(dur*sr); t=np.arange(n)/sr
    x=rng.standard_normal(n)*np.exp(-t*22)
    tri=0.5*np.sin(2*np.pi*190*t)*np.exp(-t*14)
    y=0.7*x+0.5*tri
    y/=np.abs(y).max()
    env=np.ones(n); A=int(0.001*sr)
    env[:A]=np.linspace(0,1,A)
    return y*env*amp

def hat(dur=0.09, amp=0.5, seed=3, hp=True):
    rng=np.random.default_rng(seed)
    n=int(dur*sr)
    x=rng.standard_normal(n)
    # highpass-ish: differentiate
    x=np.diff(x,prepend=x[0])
    x/=np.abs(x).max()
    env=np.exp(-t*0 if False else -np.arange(n)/ (0.012*sr))
    return x*env*amp

def clap(dur=0.3, amp=0.7, seed=11):
    rng=np.random.default_rng(seed)
    n=int(dur*sr); t=np.arange(n)/sr
    # three short bursts
    y=np.zeros(n)
    for bt in [0.0,0.012,0.024]:
        i0=int(bt*sr); L=int(0.02*sr)
        seg=rng.standard_normal(L)*np.exp(-np.arange(L)/(0.004*sr))
        y[i0:i0+L]+=seg
    y+=0.3*np.sin(2*np.pi*1100*t)*np.exp(-t*30)
    y/=np.abs(y).max()
    env=np.exp(-t*12)
    return y*env*amp

def zap(f0, dur=0.12, amp=0.7, down=True):
    n=int(dur*sr); t=np.arange(n)/sr
    f=f0*(np.exp(-t*12) if down else np.exp(t*8))
    ph=2*np.pi*np.cumsum(f)/sr
    y=np.zeros(n)
    for k in range(1,8): y+=(1.0/k)*np.sin(ph*k)
    y/=np.abs(y).max()
    env=np.exp(-t*10)
    return y*env*amp

def bass_saw(f0,dur,amp=0.75):
    return additive(f0,dur,nh=40,attack=0.004,release=0.05,amp=amp)

# ---- Build all samples ----
# 1. LEAD saw (bright, medium decay) - used for melody
save(additive(F0,0.9,nh=NH,attack=0.004,release=0.12,amp=0.85),'s_lead.wav')
# 2. PLUCK (fast decay) - arpeggios
save(additive(F0,0.45,nh=NH,attack=0.002,release=0.02,decay=6.0,amp=0.85),'s_pluck.wav')
# 3. PULSE lead (hollow square) - alternate lead
save(pulse(F0,0.8,duty=0.22,nh=NH,attack=0.003,release=0.10,amp=0.8),'s_pulse.wav')
# 4. ORGAN pad (soft odd harmonics, long) - pad chords
save(organ(F0,1.4,amp=0.75),'s_pad.wav')
# 5. BASS saw (fewer harmonics, punchy)
save(bass_saw(F0,0.5,amp=0.9),'s_bass.wav')
# 6. KICK
save(kick(),'s_kick.wav')
# 7. SNARE
save(snare(),'s_snare.wav')
# 8. CLAP
save(clap(),'s_clap.wav')
# 9. HAT (closed)
save(hat(0.07,amp=0.45,seed=5),'s_hat.wav')
# 10. HAT (open)
save(hat(0.22,amp=0.4,seed=9),'s_hat_open.wav')
# 11. NOISE sweep (riser)
save(noise(1.2,amp=0.5,seed=21,lp=0.3),'s_rise.wav')
# 12. ZAP down (laser)
save(zap(2400,0.14,amp=0.6,down=True),'s_zap.wav')
# 13. ZAP up
save(zap(300,0.18,amp=0.6,down=False),'s_zapup.wav')
# 14. TOM low
save(additive(110,0.3,nh=20,attack=0.002,release=0.03,decay=8,amp=0.8),'s_tom.wav')
# 15. Noise burst (crash-ish / percussion texture)
save(noise(0.5,amp=0.55,seed=33,lp=0.15),'s_crash.wav')
print("samples done")
