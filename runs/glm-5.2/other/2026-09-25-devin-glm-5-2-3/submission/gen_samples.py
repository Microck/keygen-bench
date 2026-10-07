import numpy as np, wave, os
os.makedirs("samps", exist_ok=True)
SR = 22050
def write_wav(path, data, sr=SR):
    d = np.clip(data, -1, 1)
    i16 = (d * 32767).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(i16.tobytes())

# ---- KICK ----
def make_kick():
    N=int(0.4*SR); t=np.arange(N)/SR
    f=140*np.exp(-t*11)+45
    ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)
    amp=np.exp(-t*5.5)
    click=np.random.RandomState(1).randn(N)*np.exp(-t*220)*0.4
    x=body*amp*0.95+click
    write_wav("samps/kick.wav",x)
make_kick()
# ---- SNARE ----
def make_snare():
    N=int(0.22*SR); t=np.arange(N)/SR
    rs=np.random.RandomState(7); noise=rs.randn(N)
    tone=np.sin(2*np.pi*190*t)+0.5*np.sin(2*np.pi*380*t)
    amp=np.exp(-t*14)
    k=30; hp=noise-np.convolve(noise,np.ones(k)/k,mode='same')
    x=(hp*0.8+tone*0.4)*amp
    write_wav("samps/snare.wav",x)
make_snare()
# ---- CLOSED HAT ----
def make_hat():
    N=int(0.05*SR); t=np.arange(N)/SR
    noise=np.random.RandomState(3).randn(N)
    k=8; hp=noise-np.convolve(noise,np.ones(k)/k,mode='same')
    lp=np.convolve(hp,np.array([0.25,0.5,0.25]),mode='same')
    x=lp*np.exp(-t*55)*0.9
    write_wav("samps/hat.wav",x)
make_hat()
# ---- OPEN HAT ----
def make_ohat():
    N=int(0.3*SR); t=np.arange(N)/SR
    noise=np.random.RandomState(11).randn(N)
    k=8; hp=noise-np.convolve(noise,np.ones(k)/k,mode='same')
    lp=np.convolve(hp,np.array([0.25,0.5,0.25]),mode='same')
    x=lp*np.exp(-t*8)*0.65
    write_wav("samps/ohat.wav",x)
make_ohat()
# ---- BASS: single cycle, fundamental-dominant (saw, no strong 2nd harmonic emphasis) ----
def make_bass():
    L=64
    phase=np.linspace(0,2*np.pi,L,endpoint=False)
    # saw wave - fundamental is the strongest harmonic
    saw=2*(phase/(2*np.pi))-1
    # add a bit of sine fundamental to reinforce
    w=0.75*saw+0.35*np.sin(phase)
    w=w/(np.max(np.abs(w))+1e-9)*0.9
    rep=np.tile(w,4)
    write_wav("samps/bass.wav",rep)
make_bass()
# ---- LEAD ----
def make_lead():
    L=256
    phase=np.linspace(0,2*np.pi,L,endpoint=False)
    saw=2*(phase/(2*np.pi))-1
    sq=np.where(phase<np.pi,1.0,-1.0)
    tri=2*np.abs(2*(phase/(2*np.pi))-1)-1
    w=0.55*saw+0.25*sq+0.15*tri+0.12*np.sin(3*phase)+0.06*np.sin(5*phase)
    w=w/(np.max(np.abs(w))+1e-9)*0.9
    write_wav("samps/lead.wav",w)
make_lead()
# ---- PAD ----
def make_pad():
    L=512
    phase=np.linspace(0,2*np.pi,L,endpoint=False)
    w=np.zeros(L)
    for h in range(1,9): w+=(1.0/h)*np.sin(h*phase)*0.5
    w=w/(np.max(np.abs(w))+1e-9)*0.9
    write_wav("samps/pad.wav",w)
make_pad()
# ---- PLUCK ----
def make_pluck():
    L=64
    phase=np.linspace(0,2*np.pi,L,endpoint=False)
    saw=2*(phase/(2*np.pi))-1
    sq=np.where(phase<np.pi,1.0,-1.0)
    wf=0.6*saw+0.4*sq; wf/=np.max(np.abs(wf))
    N=512
    rep=np.tile(wf,int(np.ceil(N/L)))[:N]
    t=np.arange(N)/SR
    amp=np.exp(-t*35)
    atk=int(0.001*SR); amp[:atk]*=np.linspace(0,1,min(atk,N))
    x=rep*amp*0.85
    write_wav("samps/pluck.wav",x)
make_pluck()
print("done")
