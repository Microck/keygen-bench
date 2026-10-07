import numpy as np
SR=44100
def freq_of_note(n):        # fork naming: 49=C-4 (MIDI C5=261.63), 57=A-4=440
    return 440.0*2**((n-57)/12.0)
def to16(x, amp=0.45):
    x=np.asarray(x,dtype=float)
    x-=np.mean(x)
    m=np.abs(x).max()
    if m>0: x=x/m*amp
    return (np.clip(x,-1,1)*32767).astype('<i2')
def sawish(F, kmax=30, rolloff=0.9, extra=None):
    n=int(SR*0.9); t=np.arange(n)/SR
    kmax=min(kmax, int(19000/max(F,1)))
    x=np.zeros(n)
    for k in range(1,kmax+1):
        x+=np.sin(2*np.pi*F*k*t+0.11*k)/k**rolloff
    if extra: x+=extra(t)
    return x,t,n
def adsr(n, a, d, s, r, sus):
    e=np.ones(n)*sus
    A=int(n*a); D=int(n*d); R=int(n*r)
    R=min(R, n-max(A+D,0))
    if A>0: e[:A]=np.linspace(0,1,A)**1.3
    if D>0: e[A:A+D]=np.linspace(1,sus,D)
    if R>0:
        s0=n-R; e[s0:]*=np.linspace(1,0.0,R)**1.4
    return e
