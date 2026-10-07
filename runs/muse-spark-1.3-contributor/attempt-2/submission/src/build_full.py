import numpy as np, base64, json, os
Fs=33452
def bandlimited_square(N, cycles, harmonics=11):
    n=np.arange(N)
    x=np.zeros(N, dtype=float)
    for k in range(1, harmonics+1, 2):
        x += (1/k)*np.sin(2*np.pi*k*cycles*n/N)
    x = x/np.max(np.abs(x))*0.85
    return x.astype(np.float32)
def bandlimited_saw(N, cycles, harmonics=12):
    n=np.arange(N)
    x=np.zeros(N, dtype=float)
    for k in range(1, harmonics+1):
        x += (1/k)*np.sin(2*np.pi*k*cycles*n/N)
    x = x/np.max(np.abs(x))*0.85
    return x.astype(np.float32)
def bandlimited_pulse(N, cycles, duty=0.25, harmonics=16):
    n=np.arange(N)
    phase=(cycles*n/N)%1.0
    naive=np.where(phase<duty,1.0,-1.0)
    spec=np.fft.rfft(naive)
    spec_trunc=np.zeros_like(spec)
    max_bin=harmonics*cycles
    spec_trunc[:max_bin+1]=spec[:max_bin+1]
    spec_trunc[0]=0
    filtered=np.fft.irfft(spec_trunc, n=N)
    filtered=filtered/np.max(np.abs(filtered))*0.8
    return filtered.astype(np.float32)

N=512; cycles=4
sq=bandlimited_square(N,cycles,11)
sw=bandlimited_saw(N,cycles,12)
pad_core=bandlimited_saw(N,cycles,6)
# pulse not needed? arp uses pluck, not pulse loop
# bass
n=np.arange(N)
bass=np.zeros(N, dtype=float)
for k in range(1,13):
    bass+= (1/k)*np.sin(2*np.pi*4*k*n/N)*0.6
bass+=0.8*np.sin(2*np.pi*2*n/N)
bass=bass/np.max(np.abs(bass))*0.9
bass=bass.astype(np.float32)
# pad with attack: attack 1536 (12 cycles? 1536/128=12 cycles?) + loop 512
attack_len=1536
attack=np.tile(pad_core[:128], attack_len//128)[:attack_len] * np.linspace(0,1,attack_len)  # fade-in using first cycle repeated? Actually pad_core is 512 with 4 cycles, first 128 is 1 cycle. Tile it.
# Better: tile pad_core's single cycle? pad_core 512/4: single cycle 128. Use that.
single_cycle=pad_core[:128]
attack=np.tile(single_cycle, attack_len//128)[:attack_len] * np.linspace(0,1,attack_len)
pad_attack=np.concatenate([attack, pad_core]).astype(np.float32)
print("pad_attack len",len(pad_attack), "loop start",attack_len, "loop len",N)
# one-shots
# kick
dur=0.35; Nk=int(Fs*dur); t=np.arange(Nk)/Fs
f_start=160; f_end=42; k=np.log(f_end/f_start)/dur; freq=f_start*np.exp(k*t); phase=2*np.pi*np.cumsum(freq)/Fs
kick=np.sin(phase)*np.exp(-t*9)*(1-np.exp(-t*200))
click_len=int(Fs*0.005); kick[:click_len]+= np.random.randn(click_len)*np.exp(-np.arange(click_len)/(Fs*0.001))*0.6
kick=kick/np.max(np.abs(kick))*0.95
kick=kick.astype(np.float32)
# snare
dur=0.22; Ns=int(Fs*dur); t=np.arange(Ns)/Fs
tone=np.sin(2*np.pi*190*t)*np.exp(-t*18)*0.6
noise=np.random.randn(Ns)
spec=np.fft.rfft(noise); freqs=np.fft.rfftfreq(Ns,1/Fs); spec[freqs<800]=0; spec[freqs>12000]=0
filt=np.fft.irfft(spec, n=Ns); filt=filt/np.max(np.abs(filt))*0.8
snare=(filt*np.exp(-t*22)+tone); snare=snare/np.max(np.abs(snare))*0.9; snare=snare.astype(np.float32)
# hats
dur=0.06; Nh=int(Fs*dur); t=np.arange(Nh)/Fs; noise=np.random.randn(Nh)
spec=np.fft.rfft(noise); freqs=np.fft.rfftfreq(Nh,1/Fs); spec[freqs<7000]=0; hp=np.fft.irfft(spec, n=Nh); hp=hp/np.max(np.abs(hp))*0.7
chat=(hp*np.exp(-t*90)).astype(np.float32)
dur=0.35; No=int(Fs*dur); t=np.arange(No)/Fs; noise=np.random.randn(No)
spec=np.fft.rfft(noise); freqs=np.fft.rfftfreq(No,1/Fs); spec[freqs<6500]=0; hp=np.fft.irfft(spec, n=No); hp=hp/np.max(np.abs(hp))*0.65
ohat=(hp*np.exp(-t*12)).astype(np.float32)
# bell
dur=1.2; Nb=int(Fs*dur); t=np.arange(Nb)/Fs; f0=261.63; mod_idx=4.0*np.exp(-t*4)
carrier=np.sin(2*np.pi*f0*t + mod_idx*np.sin(2*np.pi*f0*3.01*t)); env=np.exp(-t*4)*(1-np.exp(-t*80)); bell=(carrier*env*0.85).astype(np.float32)
# arp pluck: use pulse single cycle tiled with decay? Generate pulse single cycle 128 then tile?
pulse_single=bandlimited_pulse(128,1,0.25,16)
dur_pluck=0.30; Np=int(Fs*dur_pluck); repeats=Np//len(pulse_single)+1; tiled=np.tile(pulse_single, repeats)[:Np]
t2=np.arange(len(tiled))/Fs; env2=np.exp(-t2*14)*(1-np.exp(-t2*300)); arp_pluck=(tiled*env2); arp_pluck=arp_pluck/np.max(np.abs(arp_pluck))*0.85; arp_pluck=arp_pluck.astype(np.float32)
print("one-shots",len(kick),len(snare),len(chat),len(ohat),len(bell),len(arp_pluck))

# Build batch for module creation
def b64(arr):
    return base64.b64encode(arr.tobytes()).decode()

samples_info=[
 (1, "lead square", sq, 0, 512, 1, 50, 128),
 (2, "saw harm", sw, 0, 512, 1, 42, 96),
 (3, "bass", bass, 0, 512, 1, 56, 128),
 (4, "arp pluck", arp_pluck, 0, 0, 0, 30, 48),
 (5, "kick", kick, 0, 0, 0, 64, 128),
 (6, "snare", snare, 0, 0, 0, 52, 128),
 (7, "chat", chat, 0, 0, 0, 26, 200),
 (8, "ohat", ohat, 0, 0, 0, 26, 200),
 (9, "pad", pad_attack, attack_len, 512, 1, 36, 170),
 (10,"bell", bell, 0, 0, 0, 40, 128),
]
batch=[
 {"name":"module_new","arguments":{"channels":8,"name":"KEYGEN - Neon Cracktro"}},
]
for inst, name, arr, ls, ll, fl, vol, pan in samples_info:
    batch.append({"name":"instrument_set","arguments":{"instrument":inst,"name":name}})
    batch.append({"name":"sample_create_from_pcm","arguments":{"instrument":inst,"sample":0,"pcm":b64(arr),"encoding":"float32","name":name}})
    batch.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,"volume":vol,"panning":pan,"loop_start":ls,"loop_length":ll,"flags":fl,"relative_note":24}})
batch.append({"name":"song_set","arguments":{"bpm":150,"speed":6}})
for p in range(8):
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
for pos in range(8):
    batch.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})
batch.append({"name":"song_set","arguments":{"length":8,"loop_start":0}})

open("/tmp/create.json","w").write(json.dumps(batch))
print(f"create batch {len(batch)} size {len(json.dumps(batch))//1024}KB")
# Save samples for preview? Also save script?
