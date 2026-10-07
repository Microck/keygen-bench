import numpy as np, wave
sr=44100
freq_c4=261.63
def saw_wave(phase, h=16):
    s=np.zeros_like(phase,float)
    for n in range(1,h+1):
        s+=np.sin(2*np.pi*n*phase)/n
    return s*2/np.pi
def square_wave(phase,h=8):
    s=np.zeros_like(phase,float)
    for n in range(1,h*2,2):
        s+=np.sin(2*np.pi*n*phase)/n
    return s*4/np.pi
def write_wav(path,data):
    p=(np.clip(data,-1,1)*32767).astype(np.int16)
    import wave
    with wave.open(path,"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr)
        w.writeframes(p.tobytes())
    print(f"wrote {path} {len(p)/sr:.4f}s")

def make_looped_exact(path, dur_attack, dur_loop_target, freq=freq_c4, hsaw=16, hsqr=8, msaw=0.6, msqr=0.3, msine=0.3):
    k_loop=int(round(dur_loop_target*freq))
    L_loop=int(round(k_loop*sr/freq))
    freq_actual=k_loop*sr/L_loop
    print(f"{path}: k={k_loop} L={L_loop} freq {freq_actual:.4f} detune {1200*np.log2(freq_actual/freq):.4f} cents dur {L_loop/sr:.4f}s")
    L_attack=int(sr*dur_attack)
    L_total=L_attack+L_loop
    phase=np.arange(L_total)*freq_actual/sr %1.0
    saw=saw_wave(phase,hsaw); sqr=square_wave(phase,hsqr); sine=np.sin(2*np.pi*phase)
    y=saw*msaw+sqr*msqr+sine*msine
    y=y/np.max(np.abs(y))*0.8
    if L_attack>0:
        y[:L_attack]*=np.linspace(0,1,L_attack)**0.8
    write_wav(path,y)
    return freq_actual, L_attack, L_loop

import os
os.makedirs("/workspace/samples",exist_ok=True)
make_looped_exact("/workspace/samples/lead.wav",0.015,1.0,hsaw=24,hsqr=10,msaw=0.6,msqr=0.25,msine=0.25)
make_looped_exact("/workspace/samples/harm.wav",0.015,1.0,hsaw=8,hsqr=12,msaw=0.3,msqr=0.6,msine=0.2)
make_looped_exact("/workspace/samples/pad.wav",0.15,1.5,hsaw=8,hsqr=4,msaw=0.5,msqr=0.2,msine=0.4)
