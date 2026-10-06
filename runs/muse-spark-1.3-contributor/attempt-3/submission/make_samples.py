import numpy as np, wave, os

SR=44100
C4=261.6255653005986

def write_wav(path, data, sr=SR):
    # data float -1..1
    data = np.clip(data, -1, 1)
    ints = (data*32767).astype(np.int16)
    with wave.open(path,'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(ints.tobytes())
    print(f"wrote {path} len {len(data)} ({len(data)/sr:.3f}s) max {np.max(np.abs(data)):.3f}")

def find_loop_points(data, sr, freq, start_time, end_time):
    # find zero-crossing rising near start_time and end_time that are integer cycles apart
    # Convert times to sample indices, then search for rising zero cross
    def nearest_rising_zero(idx):
        # search +-200 samples for rising zero (negative to positive)
        best=None
        best_dist=1e9
        for i in range(int(idx-200), int(idx+200)):
            if i<1 or i>=len(data)-1: continue
            if data[i-1] < 0 and data[i] >=0:
                # interpolate? just use i
                dist=abs(i-idx)
                if dist<best_dist:
                    best_dist=dist
                    best=i
        return best
    s_idx=int(start_time*sr)
    e_idx=int(end_time*sr)
    s_loop=nearest_rising_zero(s_idx)
    e_loop=nearest_rising_zero(e_idx)
    # ensure loop length contains integer cycles? For sine-like, any rising zero to rising zero is integer cycles.
    # Check: distance should be near N*period
    print(f"  loop search {s_idx}->{s_loop}, {e_idx}->{e_loop}, len {e_loop-s_loop}")
    return s_loop, e_loop - s_loop

# 1 LEAD: bright square-ish, 2 sec
def make_lead():
    dur=2.0
    t=np.arange(int(SR*dur))/SR
    f=C4
    # additive square-ish: odd harmonics + even small
    # amplitudes: 1, 0.25, 0.4, 0.15, 0.25, 0.1, 0.15, 0.08 ...
    harmonics=[(1,1.0),(2,0.25),(3,0.45),(4,0.15),(5,0.28),(6,0.10),(7,0.18),(8,0.07),(9,0.12),(11,0.08)]
    data=np.zeros_like(t)
    for mult,amp in harmonics:
        data+=amp*np.sin(2*np.pi*f*mult*t)
    # normalize
    data/=np.max(np.abs(data))
    data*=0.85
    # envelope: attack 8ms linear, sustain flat (no decay), slight fade at very end? But loop will sustain, so keep flat after attack
    atk=int(0.008*SR)
    env=np.ones_like(data)
    env[:atk]=np.linspace(0,1,atk)
    # add subtle trem? no
    data*=env
    # gentle lowpass? Already bandlimited
    write_wav("/workspace/samples/lead.wav", data)
    # loop from 0.5s to 2.0s
    s,l=find_loop_points(data, SR, f, 0.5, 2.0-0.01)
    # need to ensure loop end doesn't include fade? Our data has no fade at end, flat, so okay but need to avoid click at end/start due to attack? Loop is sustain region flat amplitude, phase-aligned via zero-cross, should be okay.
    return s,l

# 2 ARP: thin pluck, 0.9 sec, decay, no loop
def make_arp():
    dur=0.9
    t=np.arange(int(SR*dur))/SR
    f=C4
    harmonics=[(1,1.0),(2,0.3),(3,0.35),(4,0.12),(5,0.18),(7,0.10)]
    data=np.zeros_like(t)
    for mult,amp in harmonics:
        data+=amp*np.sin(2*np.pi*f*mult*t)
    data/=np.max(np.abs(data))
    data*=0.85
    # envelope: attack 3ms, exponential decay to 0.001 at 0.9s? For pluck, fast decay
    atk=int(0.003*SR)
    env=np.exp(-t*6.0)  # decay constant 6 => at 0.9s ~0.004
    env[:atk]=np.linspace(0,1,atk)  # attack? Actually need to blend: attack then decay
    # fix: first atk samples ramp, rest decay from 1
    # recompute: env2
    env2=np.exp(-t*6.0)
    env2[:atk]=np.linspace(0,1,atk)
    # ensure env2 at atk ~1? exp(-0.003*6)=0.98 close to 1, okay
    data*=env2
    write_wav("/workspace/samples/arp.wav", data)
    return None

# 3 BASS: punchy, 1.2 sec, with click, decay but loop sustain? Let's make looped sustain for held notes, with attack click
def make_bass():
    dur=1.5
    t=np.arange(int(SR*dur))/SR
    f=C4
    # bass harmonics: strong fundamental + 2nd + 3rd, plus sub?
    harmonics=[(1,1.0),(2,0.35),(3,0.20),(4,0.12),(5,0.08)]
    data=np.zeros_like(t)
    for mult,amp in harmonics:
        data+=amp*np.sin(2*np.pi*f*mult*t + 0.1*mult)  # slight phase?
    data/=np.max(np.abs(data))
    data*=0.9
    # envelope: attack 5ms, decay to sustain 0.7, sustain flat
    atk=int(0.005*SR)
    dec=int(0.08*SR)
    env=np.ones_like(t)*0.75
    env[:atk]=np.linspace(0,1,atk)
    # decay from 1 to 0.75 over dec?
    env[atk:atk+dec]=np.linspace(1,0.75,dec)
    # add click: short highfreq at start 5ms?
    click_len=int(0.008*SR)
    click=np.sin(2*np.pi*1200*t[:click_len])*np.exp(-t[:click_len]*800)*0.4
    data[:click_len]+=click
    data*=env
    # normalize again? Keep
    data/=np.max(np.abs(data))
    data*=0.9
    write_wav("/workspace/samples/bass.wav", data)
    s,l=find_loop_points(data, SR, f, 0.4, 1.5-0.01)
    return s,l

# 4 PAD: soft detuned, 3 sec, slow attack, loop
def make_pad():
    dur=3.0
    t=np.arange(int(SR*dur))/SR
    f=C4
    # two detuned saws-ish: f*1.003 and f*0.997 chorus
    data=np.zeros_like(t)
    for det in [0.997, 1.0, 1.003]:
        # soft saw: sum 1/n up to 12 harmonics with lowpass
        for mult in range(1,13):
            amp=0.5/mult * (0.8 if mult>6 else 1.0)
            data+=amp*np.sin(2*np.pi*f*det*mult*t)
    data/=np.max(np.abs(data))
    data*=0.7
    # envelope: attack 0.4s, sustain flat, release? No release, looped
    atk=int(0.35*SR)
    env=np.ones_like(t)
    env[:atk]=np.linspace(0,1,atk)**1.5  # smooth
    # add slow amplitude LFO? subtle
    lfo=0.9+0.1*np.sin(2*np.pi*4*t)  # 4Hz
    data=data*env*lfo
    # normalize after?
    data/=np.max(np.abs(data))
    data*=0.65
    write_wav("/workspace/samples/pad.wav", data)
    # loop from 1.0 to 3.0? Need zero-cross? With detune, loop won't be perfect (beating). Choose loop that is long to minimize click, or crossfade?
    # Detuned loop will click slightly due to beating phase mismatch. Alternative: make pad without detune for clean loop, add chorus via tracker? But we baked detune, loop click may be audible.
    # Instead, make loop points at zero-cross of fundamental, beating mismatch will still cause click but low amplitude? Let's try.
    s,l=find_loop_points(data, SR, f, 1.0, 3.0-0.05)
    return s,l

# 5 KICK: 0.4 sec
def make_kick():
    dur=0.45
    t=np.arange(int(SR*dur))/SR
    # pitch envelope: 160->45 Hz exponential
    f0=160
    f1=44
    # instantaneous freq: f(t)=f1+(f0-f1)*exp(-t*30)
    # phase = 2pi * integral f dt
    # integral: f1*t + (f0-f1)*(1-exp(-t*30))/30
    phase=2*np.pi*(f1*t + (f0-f1)*(1-np.exp(-t*30))/30)
    data=np.sin(phase)
    # envelope: attack instant, decay exp
    env=np.exp(-t*9)
    # add click: first 10ms highfreq?
    click_len=int(0.015*SR)
    click=np.sin(2*np.pi*2500*t[:click_len])*np.exp(-t[:click_len]*300)*0.5
    data=data*env
    data[:click_len]+=click[:click_len]*env[:click_len]
    data/=np.max(np.abs(data))
    data*=0.95
    write_wav("/workspace/samples/kick.wav", data)
    return None

# 6 SNARE: 0.35 sec
def make_snare():
    dur=0.35
    t=np.arange(int(SR*dur))/SR
    # tone 190Hz + noise
    tone=np.sin(2*np.pi*190*t)*0.6
    # noise: white
    np.random.seed(1)
    noise=np.random.randn(len(t))
    # bandpass? simple highpass via diff? Just use noise with envelope
    # envelopes: tone decay fast, noise decay medium
    env_tone=np.exp(-t*18)
    env_noise=np.exp(-t*12)
    # attack?
    data=tone*env_tone + noise*env_noise*0.55
    # add snap: first 5ms boost noise?
    data/=np.max(np.abs(data))
    data*=0.9
    # highpass noise slightly? Apply simple one-pole highpass for hats? For snare keep full
    write_wav("/workspace/samples/snare.wav", data)
    return None

# 7 HAT closed: 0.08 sec highpass noise
def make_hat_closed():
    dur=0.09
    t=np.arange(int(SR*dur))/SR
    np.random.seed(2)
    noise=np.random.randn(len(t))
    # highpass: differentiate? y[n]=x[n]-x[n-1] approx highpass, then normalize
    hp=np.zeros_like(noise)
    hp[1:]=noise[1:]-0.98*noise[:-1]  # crude
    # envelope exp fast
    env=np.exp(-t*90)
    data=hp*env
    data/=np.max(np.abs(data))
    data*=0.55  # hats quieter
    write_wav("/workspace/samples/hat_closed.wav", data)
    return None

def make_hat_open():
    dur=0.35
    t=np.arange(int(SR*dur))/SR
    np.random.seed(3)
    noise=np.random.randn(len(t))
    hp=np.zeros_like(noise)
    hp[1:]=noise[1:]-0.98*noise[:-1]
    env=np.exp(-t*14)
    data=hp*env
    data/=np.max(np.abs(data))
    data*=0.5
    write_wav("/workspace/samples/hat_open.wav", data)
    return None

# 8 PLUCK2? extra lead octave? Let's make square blip for fills
def make_pluck2():
    dur=0.6
    t=np.arange(int(SR*dur))/SR
    f=C4
    # square 50%: sign(sin)
    # use bandlimited: sum odd harmonics
    data=np.zeros_like(t)
    for mult in [1,3,5,7,9,11]:
        data+=(1/mult)*np.sin(2*np.pi*f*mult*t)
    data/=np.max(np.abs(data))
    data*=0.8
    env=np.exp(-t*8)
    atk=int(0.002*SR)
    env[:atk]=np.linspace(0,1,atk)
    data*=env
    write_wav("/workspace/samples/pluck.wav", data)
    return None

# 9 SWEEP: noise sweep for transitions, 1.2 sec
def make_sweep():
    dur=1.2
    t=np.arange(int(SR*dur))/SR
    np.random.seed(4)
    noise=np.random.randn(len(t))
    # bandpass sweep? Simple: amplitude envelope up, filter sweep via? We'll just do amplitude swell with highpass that opens?
    # For simplicity, white noise with swell and pitch? Use filtered noise with moving cutoff approximated by cumulative? Easier: use sine sweep + noise?
    # Let's make: noise * envelope swell + sine sweep 200->4000
    env=np.linspace(0,1,len(t))**2  # swell
    # crude filter: lowpass with increasing cutoff? We'll approximate by mixing lowpass version?
    # Just use noise*env*0.5 + sweep sine
    sweep_phase=2*np.pi*(200*t + (4000-200)*t**2/(2*dur))
    sweep=np.sin(sweep_phase)*env*0.4
    data=noise*env*0.35 + sweep
    # fade out at end? For transition, need decay at end? Keep swell then cut? We'll make up then down? Actually for fill before drop, riser should swell then stop.
    # Keep as riser: swell to max then cut. That's fine for one-shot before pattern.
    data/=np.max(np.abs(data))
    data*=0.6
    write_wav("/workspace/samples/sweep.wav", data)
    return None


if __name__=="__main__":
    import json
    loops={}
    loops['lead']=make_lead()
    loops['arp']=make_arp()
    loops['bass']=make_bass()
    loops['pad']=make_pad()
    make_kick(); make_snare(); make_hat_closed(); make_hat_open(); make_pluck2(); make_sweep()
    print(loops)
    open("/workspace/samples/loops.json","w").write(json.dumps(loops,indent=2))

