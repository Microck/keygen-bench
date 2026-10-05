import numpy as np, wave, os
os.makedirs('/workspace/samples', exist_ok=True)
SR=8363
rng=np.random.default_rng(424242)

def save(name,x,sr=SR):
    x=np.asarray(x,float)
    x=np.clip(x,-1,1)
    # remove DC and tiny fade for one-shots if desired externally
    data=(x*32767).astype('<i2').tobytes()
    with wave.open('/workspace/samples/'+name+'.wav','wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data)

def wavetable(kind, cycles=8, size=256):
    t=np.arange(size)/size*cycles
    ph=2*np.pi*t
    if kind=='lead':
        # bright hollow pulse, bandlimited additive waveform
        d=.25
        x=np.zeros(size)
        for n in range(1,13):
            x += (2*np.sin(np.pi*n*d)/(np.pi*n))*np.cos(n*ph-np.pi*n*d)
        x += .18*np.sin(ph*2+0.3)+.08*np.sin(ph*5+1.1)
        x=np.tanh(1.35*x)
    elif kind=='bass':
        x=.70*np.sin(ph)+.25*np.sin(2*ph+.25)+.12*np.sin(3*ph+.5)+.06*np.sin(5*ph)
        x=np.tanh(1.5*x)
    elif kind=='organ':
        x=.72*np.sin(ph)+.26*np.sin(2*ph)+.12*np.sin(3*ph)+.07*np.sin(4*ph)+.05*np.sin(6*ph)
    elif kind=='square':
        x=np.zeros(size)
        for n in range(1,16,2): x += np.sin(n*ph)/n
        x=np.tanh(1.1*x)
    elif kind=='triangle':
        x=np.zeros(size)
        for k,n in enumerate(range(1,16,2)): x += ((-1)**k)*np.sin(n*ph)/(n*n)
    # guarantee no DC and scale
    x-=np.mean(x); x/=np.max(np.abs(x))+1e-9
    return .85*x

save('neon_lead',wavetable('lead'))
save('sub_bass',wavetable('bass'))
save('velvet_organ',wavetable('organ'))
save('chip_square',wavetable('square'))
save('soft_triangle',wavetable('triangle'))

# Pluck tuned to tracker C-4: 261.34 Hz (8 samples cycles / 256 table relation)
def pluck(name, dur=.34, bright=1.0):
    n=int(SR*dur); t=np.arange(n)/SR; f=SR/32
    x=np.zeros(n)
    phases=[0,.4,1.0,.2,2.1,1.2]
    amps=[1,.65,.43,.28,.19,.12]
    for h,(a,p) in enumerate(zip(amps,phases),1):
        x += a*np.sin(2*np.pi*f*h*t+p)*np.exp(-t*(7+3*h/bright))
    x += .15*rng.standard_normal(n)*np.exp(-t*35)
    # fast attack / smooth tail
    x*=np.minimum(1,t/.004)*np.exp(-t*2.2)
    x/=np.max(np.abs(x))+1e-9
    save(name,.82*x)
pluck('pixel_pluck',.32,1.15)

# Bell / glass one-shot
def bell():
    dur=1.15; n=int(SR*dur); t=np.arange(n)/SR; f=SR/32
    ratios=[1,2.01,2.99,4.12,5.43,6.77]
    amps=[.75,.40,.27,.20,.12,.08]
    x=sum(a*np.sin(2*np.pi*f*r*t+0.2*r)*np.exp(-t*(2.0+.35*i)) for i,(r,a) in enumerate(zip(ratios,amps)))
    x*=np.minimum(1,t/.003)
    x/=np.max(np.abs(x))+1e-9
    save('glass_bell',.72*x)
bell()

# kick
def kick():
    dur=.38;n=int(SR*dur);t=np.arange(n)/SR
    f0,f1=155,43
    phase=2*np.pi*(f1*t+(f0-f1)*(1-np.exp(-t*28))/28)
    body=np.sin(phase)*np.exp(-t*10.5)
    click=(rng.standard_normal(n)*.25 + np.sin(2*np.pi*1100*t)*.18)*np.exp(-t*75)
    x=(body+click)*np.minimum(1,t/.001)
    x/=np.max(np.abs(x))+1e-9
    save('kick',.95*x)
kick()

# snare
def snare():
    dur=.34;n=int(SR*dur);t=np.arange(n)/SR
    noise=rng.standard_normal(n)
    # highpass-ish differenced noise
    hp=np.concatenate([[noise[0]],np.diff(noise)])
    hp/=np.max(np.abs(hp))+1e-9
    tonal=np.sin(2*np.pi*185*t+0.4)*np.exp(-t*18)+.45*np.sin(2*np.pi*335*t)*np.exp(-t*24)
    x=.75*hp*np.exp(-t*15)+.45*tonal
    x*=np.minimum(1,t/.0015);x/=np.max(np.abs(x))+1e-9
    save('snare',.78*x)
snare()

# clap layered noise bursts
def clap():
    dur=.36;n=int(SR*dur);t=np.arange(n)/SR
    noise=rng.standard_normal(n); hp=np.concatenate([[noise[0]],np.diff(noise)])
    env=np.zeros(n)
    for d,a in [(0,1),(.018,.85),(.037,.7),(.066,.55)]:
        z=np.maximum(t-d,0); env += a*np.exp(-z*42)*(t>=d)
    env += .25*np.exp(-t*8)
    x=hp*env; x*=np.minimum(1,t/.001);x/=np.max(np.abs(x))+1e-9
    save('clap',.65*x)
clap()

# hats
def hat(name,dur,decay,openhat=False):
    n=int(SR*dur);t=np.arange(n)/SR
    noise=rng.standard_normal(n)
    hp=np.concatenate([[noise[0]],np.diff(noise)])
    metal=sum(np.sin(2*np.pi*f*t+rng.uniform(0,6.28)) for f in [1900,2370,2810,3370])
    env=np.exp(-t*decay)
    if openhat: env*=.65+.35*np.exp(-t*3)
    x=(.72*hp+.22*metal)*env*np.minimum(1,t/.0008)
    x/=np.max(np.abs(x))+1e-9
    save(name,.58*x)
hat('closed_hat',.10,38)
hat('open_hat',.42,8.5,True)

# crash cymbal / noise tail
def crash():
    dur=1.2;n=int(SR*dur);t=np.arange(n)/SR
    noise=rng.standard_normal(n)
    hp=np.concatenate([[noise[0]],np.diff(noise)])
    metals=sum(np.sin(2*np.pi*f*t+rng.uniform(0,6.28)) for f in [1083,1319,1667,2137,2789,3221])
    x=(.7*hp+.14*metals)*np.exp(-t*2.9)*np.minimum(1,t/.002)
    x/=np.max(np.abs(x))+1e-9
    save('crash',.62*x)
crash()

# reverse swell/riser
def riser():
    dur=.78;n=int(SR*dur);t=np.arange(n)/SR
    noise=rng.standard_normal(n)
    # colored moving noise using cumulative / differentiation blend
    hp=np.concatenate([[noise[0]],np.diff(noise)])
    chirp=np.sin(2*np.pi*(350*t+1700*t*t))
    env=(t/dur)**1.8
    x=(.55*hp+.22*chirp)*env
    # fade endpoints
    x*=np.minimum(1,t/.01)*np.minimum(1,(dur-t)/.01)
    x/=np.max(np.abs(x))+1e-9
    save('riser',.55*x)
riser()
print('made',len(os.listdir('/workspace/samples')),'samples')
