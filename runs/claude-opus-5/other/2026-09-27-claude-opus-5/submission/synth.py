import numpy as np

E = 2.0*8363.0          # engine playback rate for note 61, rel=0, ft=0 (this build)
SR = 32000.0            # design rate for percussion / one-shots

def relft(x):
    x = float(x)
    rel = int(np.floor(x+0.5)); ft = int(round((x-rel)*128))
    if ft > 127: ft -= 128; rel += 1
    if ft < -128: ft += 128; rel -= 1
    return rel, ft

def rf_rate(sr):
    """rel,ft so that tracker note 61 plays the sample back at rate sr."""
    return relft(12.0*np.log2(sr/E))

def rf_period(P):
    """rel,ft so that tracker note m+1 plays a P-frame wavetable at midi pitch m."""
    return relft(12.0*np.log2(440.0*P/E) - 9.0)

def norm(x, peak):
    m = float(np.max(np.abs(x)))
    return np.zeros_like(x) if m < 1e-12 else x*(peak/m)

def i16(x):
    return np.clip(np.round(x), -32767, 32767).astype('<i2')

# ---------- one pole / biquad ----------
def onepole_lp(x, fc, sr=SR):
    a = np.exp(-2*np.pi*fc/sr); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1-a)*x[i] + a*acc; y[i] = acc
    return y

def _bq(x, b0,b1,b2,a1,a2):
    y = np.empty_like(x); x1=x2=y1=y2=0.0
    for i in range(len(x)):
        v = b0*x[i]+b1*x1+b2*x2-a1*y1-a2*y2
        x2=x1; x1=x[i]; y2=y1; y1=v; y[i]=v
    return y

def hp(x, fc, sr=SR, q=0.707):
    w0=2*np.pi*fc/sr; a=np.sin(w0)/(2*q); c=np.cos(w0); a0=1+a
    return _bq(x,(1+c)/2/a0,-(1+c)/a0,(1+c)/2/a0,-2*c/a0,(1-a)/a0)

def lp(x, fc, sr=SR, q=0.707):
    w0=2*np.pi*fc/sr; a=np.sin(w0)/(2*q); c=np.cos(w0); a0=1+a
    return _bq(x,(1-c)/2/a0,(1-c)/a0,(1-c)/2/a0,-2*c/a0,(1-a)/a0)

def bp(x, fc, sr=SR, q=2.0):
    w0=2*np.pi*fc/sr; a=np.sin(w0)/(2*q); c=np.cos(w0); a0=1+a
    return _bq(x,a/a0,0.0,-a/a0,-2*c/a0,(1-a)/a0)

def sat(x, d=1.0):
    return np.tanh(x*d)/np.tanh(d)

# ---------- wavetable builders ----------
def rolloff(h, hc, order=2.5):
    return 1.0/(1.0+(h/float(hc))**order)

def sawspec(H, hc, order=2.5, odd=False, pw=None, tilt=1.0):
    a = {}
    for h in range(1, H+1):
        if odd and h % 2 == 0: continue
        base = abs(np.sin(np.pi*h*pw))/h if pw is not None else 1.0/h
        a[h] = base*rolloff(h, hc, order)*(h**(1.0-tilt) if tilt != 1.0 else 1.0)
    return a

def render_spec(P, n, spec, phases=None, t0=0.0):
    t = np.arange(n, dtype=np.float64) + t0
    out = np.zeros(n)
    rng = np.random.default_rng(1234)
    for h, a in sorted(spec.items()):
        f = h/float(P)
        if f >= 0.49 or a == 0.0: continue
        ph = phases[h] if (phases is not None and h in phases) else 0.0
        out += a*np.sin(2*np.pi*f*t + ph)
    return out

def head_loop(P, head_cycles, loop_cycles, spec_head, spec_loop, env_head=None,
              peak=15000, phases=None, morph_pow=1.0):
    """Continuous signal: head (morphing spectrum) then perfectly-looping tail."""
    Lh = int(head_cycles*P); Ll = int(loop_cycles*P); n = Lh+Ll
    t = np.arange(n, dtype=np.float64)
    m = np.clip(t/max(Lh,1), 0, 1)**morph_pow
    out = np.zeros(n)
    hs = sorted(set(list(spec_head)+list(spec_loop)))
    for h in hs:
        f = h/float(P)
        if f >= 0.49: continue
        a0 = spec_head.get(h,0.0); a1 = spec_loop.get(h,0.0)
        ph = phases[h] if (phases is not None and h in phases) else 0.0
        out += (a0+(a1-a0)*m)*np.sin(2*np.pi*f*t+ph)
    if env_head is not None and Lh > 0:
        e = np.ones(n); e[:Lh] = env_head(np.linspace(0,1,Lh)); out = out*e
    return i16(norm(out, peak)), Lh, Ll

def stack(Pe, k, blocks, voices, spec_fn, peak=13000, seed=3, head_env=None):
    """Detuned stack; loop length L=k*Pe frames, voice d has k+d cycles -> loops exactly."""
    L = k*Pe; n = L*blocks; head = L*(blocks-1)
    t = np.arange(n, dtype=np.float64)
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    for d, w in voices:
        kk = k+d; f0 = kk/float(L)
        spec = spec_fn(d)
        ph0 = rng.uniform(0, 2*np.pi)
        for h, a in sorted(spec.items()):
            f = f0*h
            if f >= 0.49: continue
            out += w*a*np.sin(2*np.pi*f*t + ph0*h**0.5 + rng.uniform(0,0.3))
    if head_env is not None and head > 0:
        e = np.ones(n); e[:head] = head_env(np.linspace(0,1,head)); out = out*e
    return i16(norm(out, peak)), head, L
