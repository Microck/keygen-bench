import numpy as np, base64, json, os

SR = 8363.0  # FT2 C-4 playback rate
RENDER_SR = 44100

def norm(x, peak=0.92):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x))
    if m > 1e-9:
        x = x / m * peak
    return x

def to_i16(x):
    return np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')

def b64(x):
    return base64.b64encode(to_i16(x).tobytes()).decode()

samples = {}  # name -> (pcm float array, sample_rate_for_synth)

# ---------- 1. KICK (triggered C-4 => 8363 Hz) ----------
fs = SR
dur = 0.38
n = int(fs * dur)
t = np.arange(n) / fs
# pitch sweep 160 -> 45 Hz
f0, f1, tau = 160.0, 44.0, 0.055
f = f1 + (f0 - f1) * np.exp(-t / tau)
ph = 2 * np.pi * np.cumsum(f) / fs
kick = np.sin(ph) * np.exp(-t / 0.16)
# click transient
click_n = int(fs * 0.004)
kick[:click_n] += np.sin(2*np.pi*900*t[:click_n]) * np.exp(-t[:click_n]/0.0009) * 0.35
# soft saturate + body thump
kick = np.tanh(kick * 1.4)
kick *= np.exp(-t / 0.32)
kick = norm(kick, 0.95)
samples['kick'] = kick

# ---------- 2. SNARE (triggered C-5 => 16726 Hz) ----------
fs5 = SR * 2
dur = 0.25
n = int(fs5 * dur)
t = np.arange(n) / fs5
rng = np.random.default_rng(7)
noise = rng.standard_normal(n)
# bandpass-ish: diff + one-pole highpass
hp = np.diff(noise, prepend=0)
lp = hp - 0.62 * np.concatenate([[0], hp[:-1]])
noise_body = lp * np.exp(-t / 0.045)
# tonal components
tone = (np.sin(2*np.pi*196*t) * np.exp(-t/0.030)
        + 0.6*np.sin(2*np.pi*392*t) * np.exp(-t/0.022)
        + 0.3*np.sin(2*np.pi*98*t) * np.exp(-t/0.05))
snare = 1.15 * noise_body + 0.8 * tone
snare = np.tanh(snare * 1.2)
snare *= np.exp(-t / 0.20)
snare = norm(snare, 0.92)
samples['snare'] = snare

# ---------- 3. HAT CLOSED (triggered C-6 => 33452 Hz) ----------
fs6 = SR * 4
dur = 0.055
n = int(fs6 * dur)
t = np.arange(n) / fs6
rng = np.random.default_rng(11)
noise = rng.standard_normal(n)
hp = np.diff(noise, prepend=0)
hp = hp - 0.5 * np.concatenate([[0], hp[:-1]])
hat = hp * np.exp(-t / 0.011)
hat = norm(hat, 0.85)
samples['hatc'] = hat

# ---------- 4. HAT OPEN (C-6) ----------
dur = 0.30
n = int(fs6 * dur)
t = np.arange(n) / fs6
rng = np.random.default_rng(13)
noise = rng.standard_normal(n)
hp = np.diff(noise, prepend=0)
hp = hp - 0.45 * np.concatenate([[0], hp[:-1]])
# metallic partials
metal = (0.35*np.sin(2*np.pi*5220*t) + 0.25*np.sin(2*np.pi*6950*t) + 0.2*np.sin(2*np.pi*8230*t))
hat = (hp * 1.3 * np.exp(-t / 0.075) + metal * np.exp(-t / 0.10))
hat = norm(hat, 0.80)
samples['hato'] = hat

# ---------- 5. CLAP (C-5) ----------
dur = 0.30
n = int(fs5 * dur)
t = np.arange(n) / fs5
rng = np.random.default_rng(17)
noise = rng.standard_normal(n)
hp = np.diff(noise, prepend=0)
clap = np.zeros(n)
for off in (0.0, 0.011, 0.023):
    i0 = int(off * fs5)
    seg = np.exp(-t[:-i0] / 0.016) if i0 else np.exp(-t / 0.016)
    clap[i0:] += hp[:n-i0] * seg
clap = np.tanh(clap * 1.1)
clap = norm(clap, 0.88)
samples['clap'] = clap

# ---------- 6. CRASH (C-5) ----------
dur = 1.3
n = int(fs5 * dur)
t = np.arange(n) / fs5
rng = np.random.default_rng(19)
noise = rng.standard_normal(n)
hp = np.diff(noise, prepend=0)
hp = hp - 0.55 * np.concatenate([[0], hp[:-1]])
shim = (0.5*np.sin(2*np.pi*4186*t) + 0.4*np.sin(2*np.pi*5230*t) + 0.3*np.sin(2*np.pi*6600*t))
crash = hp * 1.2 * np.exp(-t / 0.35) + shim * np.exp(-t / 0.55)
crash = norm(crash, 0.82)
samples['crash'] = crash

# ---------- 7. BASS: looped saw+square single cycle, 32 samples @ C-4 ----------
# 32 samples = one cycle of 261.63 Hz when played at C-4 (8363/32)
L = 32
ph = np.arange(L) / L
saw = 2 * ph - 1
sq = np.where(ph < 0.5, 1.0, -1.0)
wave = 0.78 * saw + 0.30 * sq
wave = np.tanh(wave * 1.1)
wave = norm(wave, 0.85)
samples['bass'] = wave  # 32-sample loop

# ---------- 8. PLUCK (one-shot, C-4 base) ----------
fs = SR
dur = 0.34
n = int(fs * dur)
t = np.arange(n) / fs
f = 261.63
ph1 = 2*np.pi*f*t
# two detuned saws
saw1 = 2*((ph1/(2*np.pi)) % 1.0) - 1
saw2 = 2*((ph1*1.006/(2*np.pi)) % 1.0) - 1
pluck = (0.7*saw1 + 0.5*saw2) * np.exp(-t/0.045)
pluck += 0.25*np.sin(ph1*2) * np.exp(-t/0.02)
pluck = np.tanh(pluck * 1.0)
pluck = norm(pluck, 0.80)
samples['pluck'] = pluck

# ---------- 9. PAD minor7 chord (one-shot, root C-4 base) ----------
fs = SR
dur = 2.6
n = int(fs * dur)
t = np.arange(n) / fs
rng = np.random.default_rng(23)
def tone(freq, detune=0.0, amp=1.0):
    tt = t
    f = freq * (1 + detune)
    ph = 2*np.pi*f*tt
    tri = 2*np.abs(2*((ph/(2*np.pi)) % 1.0) - 1) - 1  # triangle
    return tri * amp
# E minor7-ish chord relative: root, m3, 5, m7 (E G B D)
freqs = [261.63, 311.13, 392.0, 466.16]
pad = (tone(freqs[0], 0.001, 0.5) + tone(freqs[0], -0.001, 0.5)
     + tone(freqs[1], 0.0007, 0.42) + tone(freqs[2], -0.0006, 0.38)
     + tone(freqs[3], 0.0008, 0.30))
env = np.minimum(t / 0.35, 1.0) * np.exp(-np.maximum(t-1.8, 0) / 0.55)
pad = pad * env
pad = np.tanh(pad * 0.8)
pad = norm(pad, 0.55)
samples['padm'] = pad

# ---------- 10. PAD major chord (root, M3, 5, octave) ----------
freqs = [261.63, 329.63, 392.0, 523.25]
pad2 = (tone(freqs[0], 0.0012, 0.5) + tone(freqs[0], -0.0012, 0.5)
      + tone(freqs[1], 0.0008, 0.40) + tone(freqs[2], -0.0007, 0.36)
      + tone(freqs[3], 0.0006, 0.22))
pad2 = pad2 * env
pad2 = np.tanh(pad2 * 0.8)
pad2 = norm(pad2, 0.5)
samples['padM'] = pad2

# ---------- 11. LEAD: saw+square loop with built-in attack ----------
# 2-cycle attack (64 samples fade-in) + 32-sample loop
L = 32
ph = np.arange(L) / L
saw = 2 * ph - 1
lead_loop = 0.6 * saw + 0.55 * np.where(ph < 0.5, 1.0, -1.0)
lead_loop = np.tanh(lead_loop * 1.15)
# build attack as fade-in of the same wave (2 cycles)
att = np.tile(lead_loop, 2) * np.linspace(0.0, 1.0, 64)**1.5
lead = np.concatenate([att, lead_loop])
lead = norm(lead, 0.88)
samples['lead'] = lead  # 96 samples: loop at 64..95

# ---------- 12. ARP BLIP: bright short square blip for accents ----------
fs = SR
dur = 0.09
n = int(fs * dur)
t = np.arange(n) / fs
blip = np.sin(2*np.pi*523.25*t) * np.exp(-t/0.012) + 0.5*np.sin(2*np.pi*1046.5*t)*np.exp(-t/0.008)
blip = norm(blip, 0.7)
samples['blip'] = blip

# Save individual b64 files and batch json
os.makedirs('/workspace/work', exist_ok=True)
inst_of = {
 'kick':1,'snare':2,'hatc':3,'hato':4,'clap':5,'crash':6,'bass':7,'pluck':8,
 'padm':9,'padM':10,'lead':11,'blip':12
}
batch = []
for name, x in samples.items():
    inst = inst_of[name]
    path = f'/workspace/work/{name}.b64'
    open(path,'w').write(b64(x))
    batch.append({"name":"sample_create_from_pcm","arguments":{
        "instrument":inst,"sample":0,"pcm":b64(x),"encoding":"int16","name":name}})

# metadata: (inst, vol, pan, loop_start, loop_len, flags)
meta = {
 1: (64, 128, 0, 0, 16),     # kick
 2: (60, 128, 0, 0, 16),     # snare
 3: (44, 176, 0, 0, 16),     # hat closed
 4: (40, 176, 0, 0, 16),     # hat open
 5: (48, 80,  0, 0, 16),     # clap
 6: (36, 128, 0, 0, 16),     # crash
 7: (56, 128, 0, 32, 17),    # bass loop
 8: (44, 112, 0, 0, 16),     # pluck
 9: (40, 144, 0, 0, 16),     # pad minor
 10:(38, 144, 0, 0, 16),     # pad major
 11:(54, 128, 64, 32, 17),   # lead loop w/ attack
 12:(40, 96,  0, 0, 16),     # blip
}
for inst,(vol,pan,ls,ll,flags) in meta.items():
    batch.append({"name":"sample_set","arguments":{
        "instrument":inst,"sample":0,"volume":vol,"panning":pan,
        "loop_start":ls,"loop_length":ll,"flags":flags}})
for inst,name in inst_of.items():
    pass
json.dump(batch, open('/workspace/work/sample_batch.json','w'))
print('samples:', {k: len(v) for k,v in samples.items()})
print('batch size', len(batch))
