import numpy as np, base64, json

SR = 4181.5   # design sample rate (C-4 playback rate of this FT2 build)

def save_int16(x, peak=0.85):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m > 0:
        x = x * (peak * 32767 / m)
    return base64.b64encode(np.clip(x, -32767, 32767).astype(np.int16).tobytes()).decode()

def bl_saw(freq, n_samples, harmonics=8, sr=SR):
    """band-limited saw: harmonics 1..H, 1/n amplitude"""
    t = np.arange(n_samples) / sr
    out = np.zeros(n_samples)
    hmax = min(harmonics, int((sr/2)/freq))
    for n in range(1, hmax+1):
        out += np.sin(2*np.pi*n*freq*t) / n
    return out

def bl_square(freq, n_samples, harmonics=8, sr=SR):
    t = np.arange(n_samples) / sr
    out = np.zeros(n_samples)
    hmax = min(harmonics, int((sr/2)/freq))
    for n in range(1, hmax+1, 2):
        out += np.sin(2*np.pi*n*freq*t) / n
    return out

def fft_filter(x, lo=None, hi=None, smooth=40):
    """simple zero-phase FFT band filter"""
    n = len(x)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1/SR)
    mask = np.ones(len(freqs))
    if lo is not None:
        k = np.where(freqs < lo)[0]
        mask[k] = 0.5 - 0.5*np.cos(np.pi*np.clip((lo-freqs[k])/smooth, 0, 1))
    if hi is not None:
        k = np.where(freqs > hi)[0]
        mask[k] *= 0.5 - 0.5*np.cos(np.pi*np.clip((freqs[k]-hi)/smooth, 0, 1))
    return np.fft.irfft(spec * mask, n)

# ---------------- drums (one-shots; input length = 2 * dur * SR at trigger note) ----------------
rng = np.random.default_rng(7)

# Kick: 0.18s at C-4
n = int(2*0.18*SR)
t = np.arange(n)/SR
f = 40 + 115*np.exp(-t*26)
ph = 2*np.pi*np.cumsum(f)/SR
kick = np.sin(ph)*np.exp(-t*21) + 0.10*rng.standard_normal(n)*np.exp(-t*90)
kick = np.tanh(kick*2.4)

# Snare: 0.22s at C-4
n = int(2*0.22*SR)
t = np.arange(n)/SR
noise = rng.standard_normal(n)
snr = fft_filter(noise, lo=900, hi=2200)*np.exp(-t*24)
snr += 0.9*np.sin(2*np.pi*185*t)*np.exp(-t*16)
snr += 0.3*np.sin(2*np.pi*330*t)*np.exp(-t*25)
snr[:40] += rng.standard_normal(40)*1.2

# Clap: 0.20s at C-5
n = int(2*0.20*SR*2)  # trigger at C-5: rate 8363
t = np.arange(n)/(SR*2)
noise = rng.standard_normal(n)
clap = np.zeros(n)
for off, g in [(0.0,1.0),(0.012,0.8),(0.026,0.65),(0.040,0.5)]:
    k = int(off*(SR*2))
    e = np.exp(-np.maximum(t-k/(SR*2),0)*34)
    clap += noise*g*np.roll(e, k)
clap = fft_filter(clap, lo=700, hi=2400)

# HatC: 0.05s at C-5
n = int(2*0.05*SR*2)
t = np.arange(n)/(SR*2)
noise = rng.standard_normal(n)
hatc = fft_filter(noise, lo=3200, hi=10500, smooth=200)*np.exp(-t*110)

# HatO: 0.30s at C-5
n = int(2*0.30*SR*2)
t = np.arange(n)/(SR*2)
noise = rng.standard_normal(n)
hato = fft_filter(noise, lo=2800, hi=9500, smooth=200)*np.exp(-t*14)

# Crash: 1.5s at C-5
n = int(2*1.5*SR*2)
t = np.arange(n)/(SR*2)
noise = rng.standard_normal(n)
crash = fft_filter(noise, lo=1800, hi=11500, smooth=300)*np.exp(-t*3.0)
for f, g in [(3150,0.06),(4870,0.045),(6230,0.03)]:
    crash += g*np.sin(2*np.pi*f*t)*np.exp(-t*4.0)
crash[0] = 0.0

# Riser: 1.6s at C-4, swept bandpass noise
n = int(2*1.6*SR)
t = np.arange(n)/SR
noise = rng.standard_normal(n)
# per-block biquad bandpass sweep
block = 256
out = np.zeros(n)
f0s = 250*(4200/250)**(np.arange(n)/n)
state = np.zeros(4)
prev_b = None; prev_a = None
for i in range(0, n, block):
    seg = noise[i:i+block]
    f0 = f0s[min(i+block//2, n-1)]
    w0 = 2*np.pi*f0/SR
    Q = 5.0
    alpha = np.sin(w0)/(2*Q)
    b = np.array([alpha, 0, -alpha])
    a = np.array([1+alpha, -2*np.cos(w0), 1-alpha])
    # zero-state filtering per block with edge fade to avoid clicks
    if prev_b is not None:
        b = 0.5*prev_b + 0.5*b
        a = 0.5*prev_a + 0.5*a
    y = np.zeros(len(seg))
    x1=x2=y1=y2=0.0
    for j in range(len(seg)):
        y[j] = (b[0]*seg[j] + b[1]*x1 + b[2]*x2 - a[1]*y1 - a[2]*y2)/a[0]
        x2=x1; x1=seg[j]; y2=y1; y1=y[j]
    out[i:i+block] = y
    prev_b = b; prev_a = a
riser = out * (t/1.6)**2.2
riser = fft_filter(riser, lo=120, hi=9000, smooth=250)

# Downlifter: descending sweep, 1.6s at C-4
n = int(2*1.6*SR)
t = np.arange(n)/SR
noise = rng.standard_normal(n)
out = np.zeros(n)
f0s = 4200*(250/4200)**(np.arange(n)/n)
state = np.zeros(4)
prev_b=None; prev_a=None
for i in range(0, n, block):
    seg = noise[i:i+block]
    f0 = f0s[min(i+block//2, n-1)]
    w0 = 2*np.pi*f0/SR
    Q = 5.0
    alpha = np.sin(w0)/(2*Q)
    b = np.array([alpha, 0, -alpha])
    a = np.array([1+alpha, -2*np.cos(w0), 1-alpha])
    if prev_b is not None:
        b = 0.5*prev_b + 0.5*b
        a = 0.5*prev_a + 0.5*a
    y = np.zeros(len(seg))
    x1=x2=y1=y2=0.0
    for j in range(len(seg)):
        y[j] = (b[0]*seg[j] + b[1]*x1 + b[2]*x2 - a[1]*y1 - a[2]*y2)/a[0]
        x2=x1; x1=seg[j]; y2=y1; y1=y[j]
    out[i:i+block] = y
    prev_b=b; prev_a=a
down = out * np.exp(-t*0.5)
down = fft_filter(down, lo=120, hi=9000, smooth=250)

# Zap: laser 0.5s at C-4
n = int(2*0.5*SR)
t = np.arange(n)/SR
f = 300 + 1900*np.exp(-t*7)
ph = 2*np.pi*np.cumsum(f)/SR
zap = np.sin(ph)*np.exp(-t*6)
zap += 0.4*np.sin(1.013*ph)*np.exp(-t*7)
zap[:30] += rng.standard_normal(30)*0.5

# ---------------- pitched loops ----------------
C4 = 261.3428

# Bass pluck (one-shot): saw, decay, designed 0.10s at C-4
n = int(2*0.10*SR)
t = np.arange(n)/SR
basspl = bl_saw(C4, n, 8) * np.exp(-t*30)
basspl = fft_filter(basspl, hi=2600, smooth=300)

# Sub: sine loop; stored 512 (input 1024), 32 cycles stored
n = 1024
sub = np.sin(2*np.pi*64*np.arange(n)/n)

# Arp: square loop; stored 512, input 1024, 64 cycles
n = 1024
arp = bl_square(C4, n, 8)

# Lead supersaw: stored 2048 (input 4096), voices c 126..130
L = 4096
t = np.arange(L)/SR
lead = np.zeros(L)
for c, g in [(126,0.55),(127,0.75),(128,0.9),(129,0.75),(130,0.55)]:
    f = SR*c/L*2  # cycles in input: 2*c ; fundamental of input = SR*2c/L... verify below
    lead += g * bl_saw(f, L, 8)
# fundamental of input = f = SR*(2c)/L -> after decimation stored L/2, cycles c, f_C4 = SR*c/(L/2) = SR*2c/L = f. Good.

# Pad: soft saw, stored 2048 (input 4096), 2 voices c 127/128
L = 4096
pad = np.zeros(L)
for c, g in [(127,0.6),(128,0.6)]:
    f = SR*2*c/L
    pad += g * bl_saw(f, L, 5)
pad = fft_filter(pad, hi=1400, smooth=200)

# assemble sample list: (instr, name, data, loop_on, vol, pan, trigger_note_hint)
samples = [
 (1,  "kick",   kick,  False, 64, 128),
 (2,  "snare",  snr,   False, 58, 128),
 (3,  "clap",   clap,  False, 46, 132),
 (4,  "hatc",   hatc,  False, 34, 152),
 (5,  "hato",   hato,  False, 30, 168),
 (6,  "bass",   basspl,False, 42, 128),
 (7,  "sub",    sub,   True,  40, 128),
 (8,  "lead",   lead,  True,  38, 112),
 (9,  "arp",    arp,   True,  30, 96),
 (10, "pada",   pad,   True,  30, 64),
 (11, "padb",   pad,   True,  30, 192),
 (12, "riser",  riser, False, 46, 128),
 (13, "down",   down,  False, 46, 128),
 (14, "crash",  crash, False, 44, 128),
 (15, "zap",    zap,   False, 46, 128),
 (16, "leadr",  lead,  True,  38, 176),
]

calls = [ {"name":"module_new","arguments":{"channels":14,"name":"hexline"}} ]
meta_out = {}
for instr, name, data, loop, vol, pan in samples:
    L_in = len(data)
    L_st = L_in//2
    pcm = save_int16(data)
    calls.append({"name":"sample_create_from_pcm","arguments":{"instrument":instr,"sample":0,"pcm":pcm,"encoding":"int16","name":name}})
    args = {"instrument":instr,"sample":0,"volume":vol,"panning":pan,"finetune":2}
    if loop:
        args["loop_start"] = 0
        args["loop_length"] = L_st
        args["flags"] = 1
    else:
        args["flags"] = 0
    calls.append({"name":"sample_set","arguments":args})
    calls.append({"name":"instrument_set","arguments":{"instrument":instr,"name":name}})
    meta_out[name] = (L_in, L_st)

json.dump(calls, open('/workspace/work/samples_batch.json','w'))
print("samples written:")
for k,v in meta_out.items():
    print(" ", k, v)
