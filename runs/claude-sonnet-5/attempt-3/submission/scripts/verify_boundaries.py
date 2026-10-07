import sys
sys.path.insert(0, "/workspace/scripts")
import importlib
import verify_notes as V
importlib.reload(V)
import song_data as SD
from ft2util import call
import numpy as np, wave

def last_and_first(pattern_events_by_pattern, order_seq):
    """pattern_events_by_pattern: dict pat_label-> list of (row,timbre,note,vol) sorted
       returns list of (from_label,to_label,last_event,first_event)"""
    out = []
    for i in range(len(order_seq)):
        frm = order_seq[i]
        to = order_seq[(i+1) % len(order_seq)]
        evs_from = pattern_events_by_pattern[frm]
        evs_to = pattern_events_by_pattern[to]
        if not evs_from or not evs_to:
            continue
        out.append((frm, to, evs_from[-1], evs_to[0]))
    return out

def events_for(lead_dict):
    ev = []
    for bi, bar in enumerate(SD.BARS):
        row0 = bi*16
        for row, nk, vol in lead_dict.get(bar, []):
            ev.append((row0+row, nk, vol))
    ev.sort()
    return ev

def arp_events_for(order_fn):
    ev=[]
    for bi,bar in enumerate(SD.BARS):
        row0=bi*16
        tones = SD.CHORD[bar]["arp"]
        order = order_fn(bar,bi)
        for row, idx, vol in SD.arp_pattern(order):
            ev.append((row0+row, tones[idx], vol))
    ev.sort(); return ev

def arp_sparse_events():
    ev=[]
    for bi,bar in enumerate(SD.BARS):
        row0=bi*16
        tones = SD.CHORD[bar]["arp"]
        for row, idx, vol in SD.arp_pattern_sparse((0,1,2,1)):
            ev.append((row0+row, tones[idx], vol))
    ev.sort(); return ev

def bass_events_for(main_even):
    ev=[]
    for bi,bar in enumerate(SD.BARS):
        row0=bi*16
        chord=SD.CHORD[bar]
        kind_note={"root":chord["bass"],"fifth":SD.BASS_FIFTH[bar],"oct":SD.BASS_OCT[bar]}
        bp = SD.bass_pattern_main() if (bi%2==0)==main_even else SD.bass_pattern_alt()
        for row,kind,vol in bp:
            ev.append((row0+row, kind_note[kind], vol))
    ev.sort(); return ev

def bass_events_C():
    ev=[]
    for bi,bar in enumerate(SD.BARS):
        row0=bi*16
        chord=SD.CHORD[bar]
        kind_note={"root":chord["bass"],"fifth":SD.BASS_FIFTH[bar],"oct":SD.BASS_OCT[bar]}
        for row,kind,vol in SD.bass_pattern_main():
            ev.append((row0+row, kind_note[kind], vol))
    ev.sort(); return ev

def harm_events():
    return [(bi*16, SD.HARMONY[bar], 28) for bi,bar in enumerate(SD.BARS)]

CHANNELS = {
    "LEAD": {
        "A": [(r,"LEAD",nk,v) for r,nk,v in events_for(SD.LEAD_A)],
        "B": [(r,"LEAD",nk,v) for r,nk,v in events_for(SD.LEAD_B)],
        "C": [(r,"LEAD",nk,v) for r,nk,v in events_for(SD.LEAD_C)],
    },
    "ARP": {
        "A": [(r,"ARP",nk,v) for r,nk,v in arp_events_for(lambda bar,bi:(0,1,2,1) if bar in ("Am","C") else (2,1,0,1))],
        "B": [(r,"ARP",nk,v) for r,nk,v in arp_events_for(lambda bar,bi:(2,1,0,1) if bar in ("Am","C") else (0,1,2,1))],
        "C": [(r,"ARP",nk,v) for r,nk,v in arp_sparse_events()],
    },
    "BASS": {
        "A": [(r,"BASS",nk,v) for r,nk,v in bass_events_for(True)],
        "B": [(r,"BASS",nk,v) for r,nk,v in bass_events_for(False)],
        "C": [(r,"BASS",nk,v) for r,nk,v in bass_events_C()],
    },
    "HARM": {
        "A": [(r,"ARP",nk,v) for r,nk,v in harm_events()],
        "B": [(r,"ARP",nk,v) for r,nk,v in harm_events()],
        "C": [(r,"ARP",nk,v) for r,nk,v in harm_events()],
    },
}
ORDER_SEQ = ["A","B","A","C"]

def test_transition(label, last_ev, first_ev):
    # place last_ev's note at row0, first_ev's note at row6 (0.6s gap, plenty of settle+measure time)
    row, timbre, nk, vol = last_ev
    call("pattern_set_length", {"pattern":3, "rows":20})
    call("pattern_clear", {"pattern":3})
    V_set = __import__("compose_util").set_cell
    V_set(3, 0, 5, timbre, nk, vol)
    row2, timbre2, nk2, vol2 = first_ev
    V_set(3, 6, 5, timbre2, nk2, vol2)
    call("order_set", {"position":0,"pattern":3})
    call("song_set", {"length":1,"bpm":150,"speed":6})
    call("module_render", {"path":f"/tmp/trans_{label}.wav","rate":44100,"bits":16,"amp":8,"loops":0})
    w = wave.open(f"/tmp/trans_{label}.wav","rb"); sr=w.getframerate(); n=w.getnframes()
    arr = np.frombuffer(w.readframes(n), dtype='<i2').reshape(-1,2)[:,0].astype(float)
    f1 = V.measure(arr, sr, 0, 6, max_dur=0.3)
    f2 = V.measure(arr, sr, 6, 20, max_dur=0.3)
    t1 = V.TUNING[nk]['target']; t2 = V.TUNING[nk2]['target']
    e1 = abs(f1-t1)/t1*100 if t1 else 0
    e2 = abs(f2-t2)/t2*100 if t2 else 0
    ok = e1<1.5 and e2<1.5
    print(f"{label:28s} last={timbre}_{nk:3s}({t1:7.2f}->{f1:7.2f},{e1:5.2f}%) "
          f"first={timbre2}_{nk2:3s}({t2:7.2f}->{f2:7.2f},{e2:5.2f}%) {'OK' if ok else '<<BAD'}")
    return ok

if __name__ == "__main__":
    all_ok = True
    for chname, pats in CHANNELS.items():
        trans = last_and_first(pats, ORDER_SEQ)
        for frm,to,last_ev,first_ev in trans:
            label = f"{chname}_{frm}to{to}"
            ok = test_transition(label, last_ev, first_ev)
            all_ok = all_ok and ok
    print("ALL OK" if all_ok else "SOME FAILED")
