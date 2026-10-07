import sys, numpy as np, base64, wave, math
sys.path.insert(0, "/workspace/scripts")
from ft2util import call

def make_square(L):
    t = np.arange(L)
    wave_data = np.sign(np.sin(2*np.pi*t/L + 1e-9))
    return (wave_data*20000).astype('<i2')

_cache_module = {"built": False}

def build_once():
    call("module_new", {"channels":2,"name":"CAL"})
    call("pattern_set_length", {"pattern":0,"rows":24})
    call("order_set", {"position":0,"pattern":0})
    call("song_set", {"bpm":125,"speed":3,"length":1,"loop_start":0})

def set_note(note, L, relative_note=0, finetune=0):
    pcm = make_square(L)
    b64 = base64.b64encode(pcm.tobytes()).decode()
    call("sample_create_from_pcm", {"instrument":1,"sample":0,"pcm":b64,"encoding":"int16","name":"cal"})
    call("sample_set", {"instrument":1,"sample":0,"volume":64,"panning":128,
                         "finetune":finetune,"relative_note":relative_note,
                         "loop_start":0,"loop_length":L,"flags":1})
    call("pattern_set_cell", {"pattern":0,"row":0,"channel":0,"note":note,"instrument":1,"volume":64})

def render():
    call("module_render", {"path":"/tmp/cal.wav","rate":44100,"bits":16,"amp":8,"loops":0})

def measure_freq(path, fmin=15, fmax=18000):
    w = wave.open(path,'rb')
    n = w.getnframes()
    data = w.readframes(n)
    arr = np.frombuffer(data, dtype='<i2')
    if w.getnchannels()==2:
        arr = arr.reshape(-1,2)[:,0].astype(float)
    sr = w.getframerate()
    start = int(len(arr)*0.3)
    seg = arr[start:].astype(float)
    seg = seg - seg.mean()
    if np.abs(seg).max() < 1:
        return 0.0
    lag_min = max(1,int(sr/fmax))
    lag_max = min(len(seg)-2, int(sr/fmin))
    ac = np.correlate(seg, seg, mode='full')[len(seg)-1:]
    ac /= (ac[0]+1e-9)
    window = ac[lag_min:lag_max]
    if len(window)==0:
        return 0.0
    peak = int(np.argmax(window))+lag_min
    if 0<peak<len(ac)-1:
        y0,y1,y2 = ac[peak-1],ac[peak],ac[peak+1]
        denom=(y0-2*y1+y2)
        delta = 0.5*(y0-y2)/denom if denom!=0 else 0.0
    else:
        delta=0.0
    true_lag = peak+delta
    return sr/true_lag

def expected_rate(sum_, finetune=0):
    realnote = sum_ - 1
    period = 7680 - realnote*64 - finetune/2
    freq = 8363 * 2**((4608 - period)/768)
    return freq

def note_relative_for_sum(s):
    if s <= 96:
        return s, 0
    else:
        return 96, s-96

def test_sum(s, finetune=0, L=2048):
    note, rel = note_relative_for_sum(s)
    if rel < -48 or rel > 71 or note<1 or note>96:
        return None
    set_note(note, L, rel, finetune)
    render()
    exp_rate = expected_rate(s, finetune)
    exp_freq = exp_rate / L
    fmax = min(19000, exp_freq*3+50)
    fmin = max(5, exp_freq*0.3)
    f = measure_freq('/tmp/cal.wav', fmin=fmin, fmax=fmax)
    ratio = f/exp_freq if exp_freq else float('nan')
    return f, exp_freq, ratio

if __name__ == "__main__":
    build_once()
    import sys as _s
    ft = int(_s.argv[1]) if len(_s.argv)>1 else 8
    lo = int(_s.argv[2]) if len(_s.argv)>2 else 1
    hi = int(_s.argv[3]) if len(_s.argv)>3 else 167
    results = []
    for s in range(lo, hi+1):
        r = test_sum(s, finetune=ft, L=2048)
        if r is None:
            continue
        f, exp, ratio = r
        clean = abs(ratio-1.0) < 0.01
        results.append((s, f, exp, ratio, clean))
        print(f"sum={s:4d} ft={ft:4d} measured={f:12.3f} expected={exp:12.3f} ratio={ratio:8.4f} {'CLEAN' if clean else ''}")
    cleans = [s for s,f,exp,ratio,clean in results if clean]
    print("CLEAN sums:", cleans)
