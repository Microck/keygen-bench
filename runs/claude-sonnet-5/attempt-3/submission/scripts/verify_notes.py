import sys, json
sys.path.insert(0, "/workspace/scripts")
import numpy as np, wave
from ft2util import call
from compose_util import set_cell, INSTR, TUNING
import song_data as SD

ROWS_PER_BAR = 16
row_dur = 6*2.5/150

def measure(arr, sr, row_start, row_end, guard=0.015, tail=0.004, max_dur=0.35):
    start = int((row_start*row_dur+guard)*sr)
    end = int((row_end*row_dur-tail)*sr)
    if end <= start+40:
        end = start+40
    if end - start > max_dur*sr:
        end = start + int(max_dur*sr)
    seg = arr[start:end]
    seg = seg - seg.mean()
    if np.abs(seg).max() < 5:
        return 0.0
    ac = np.correlate(seg, seg, mode='full')[len(seg)-1:]
    ac /= (ac[0]+1e-9)
    lo, hi = int(sr/2200), min(int(sr/35), len(ac)-2)
    if hi <= lo:
        return 0.0
    peak = np.argmax(ac[lo:hi])+lo
    if 0 < peak < len(ac)-1:
        y0,y1,y2 = ac[peak-1],ac[peak],ac[peak+1]
        den = (y0-2*y1+y2)
        delta = 0.5*(y0-y2)/den if den != 0 else 0.0
    else:
        delta = 0.0
    return sr/(peak+delta)

def build_solo(pattern_idx, events, rows_total):
    """events: list of (row, timbre, notename, vol)"""
    call("pattern_set_length", {"pattern": pattern_idx, "rows": rows_total})
    call("pattern_clear", {"pattern": pattern_idx})
    for row, timbre, nk, vol in events:
        set_cell(pattern_idx, row, 5, timbre, nk, vol)
    call("order_set", {"position": 0, "pattern": pattern_idx})
    call("song_set", {"length": 1, "bpm": 150, "speed": 6})

def gather_events(lead_dict, bar_list, timbre):
    events = []
    for bi, bar in enumerate(bar_list):
        row0 = bi*ROWS_PER_BAR
        for row, nk, vol in lead_dict[bar]:
            events.append((row0+row, timbre, nk, vol))
    events.sort()
    return events

def gather_bass_events(bar_list, pattern_fn_even, pattern_fn_odd):
    events = []
    for bi, bar in enumerate(bar_list):
        row0 = bi*ROWS_PER_BAR
        chord = SD.CHORD[bar]
        kind_note = {"root": chord["bass"], "fifth": SD.BASS_FIFTH[bar], "oct": SD.BASS_OCT[bar]}
        bp = pattern_fn_even() if bi % 2 == 0 else pattern_fn_odd()
        for row, kind, vol in bp:
            events.append((row0+row, "BASS", kind_note[kind], vol))
    events.sort()
    return events

def gather_arp_events(bar_list, orders):
    events = []
    for bi, bar in enumerate(bar_list):
        row0 = bi*ROWS_PER_BAR
        tones = SD.CHORD[bar]["arp"]
        order = orders(bar, bi)
        for row, idx, vol in SD.arp_pattern(order):
            events.append((row0+row, "ARP", tones[idx], vol))
    events.sort()
    return events

def verify_events(name, events, rows_total=64):
    build_solo(3, events, rows_total)
    call("module_render", {"path": f"/tmp/verify_{name}.wav", "rate":44100,"bits":16,"amp":8,"loops":0})
    w = wave.open(f"/tmp/verify_{name}.wav", 'rb')
    sr = w.getframerate(); n = w.getnframes()
    arr = np.frombuffer(w.readframes(n), dtype='<i2').reshape(-1,2)[:,0].astype(float)
    bad = []
    for i, (row, timbre, nk, vol) in enumerate(events):
        nxt = events[i+1][0] if i+1 < len(events) else rows_total
        f = measure(arr, sr, row, nxt)
        tgt = TUNING[nk]['target']
        err = abs(f-tgt)/tgt*100 if tgt else 0
        if err > 1.5:
            bad.append((row, timbre, nk, tgt, f, err))
    return bad

if __name__ == "__main__":
    all_bad = {}
    # LEAD channels across patterns A,B,C
    for label, d in [("A", SD.LEAD_A), ("B", SD.LEAD_B), ("C", SD.LEAD_C)]:
        ev = gather_events(d, SD.BARS, "LEAD")
        if not ev:
            continue
        bad = verify_events(f"LEAD_{label}", ev)
        if bad: all_bad[f"LEAD_{label}"] = bad
        print(f"LEAD_{label}: {len(ev)} notes, bad={len(bad)}")

    # ARP for pattern A/B (order variants) and sparse for C
    evA = gather_arp_events(SD.BARS, lambda bar,bi: (0,1,2,1) if bar in ("Am","C") else (2,1,0,1))
    badA = verify_events("ARP_A", evA)
    print(f"ARP_A: {len(evA)} notes, bad={len(badA)}")
    if badA: all_bad["ARP_A"] = badA

    evB = gather_arp_events(SD.BARS, lambda bar,bi: (2,1,0,1) if bar in ("Am","C") else (0,1,2,1))
    badB = verify_events("ARP_B", evB)
    print(f"ARP_B: {len(evB)} notes, bad={len(badB)}")
    if badB: all_bad["ARP_B"] = badB

    # BASS for pattern A and B (variant assignment differs)
    evBassA = gather_bass_events(SD.BARS, SD.bass_pattern_main, SD.bass_pattern_alt)
    badBassA = verify_events("BASS_A", evBassA)
    print(f"BASS_A: {len(evBassA)} notes, bad={len(badBassA)}")
    if badBassA: all_bad["BASS_A"] = badBassA

    evBassB = gather_bass_events(SD.BARS, SD.bass_pattern_alt, SD.bass_pattern_main)
    badBassB = verify_events("BASS_B", evBassB)
    print(f"BASS_B: {len(evBassB)} notes, bad={len(badBassB)}")
    if badBassB: all_bad["BASS_B"] = badBassB

    # Harmony (one note per bar, both pattern variants use same notes, different vol only)
    evHarm = [(bi*16, "ARP", SD.HARMONY[bar], 28) for bi,bar in enumerate(SD.BARS)]
    badHarm = verify_events("HARM", evHarm)
    print(f"HARM: {len(evHarm)} notes, bad={len(badHarm)}")
    if badHarm: all_bad["HARM"] = badHarm

    print()
    print("=== SUMMARY OF BAD NOTES ===")
    for k,v in all_bad.items():
        print(k)
        for row,timbre,nk,tgt,f,err in v:
            print(f"   row{row} {timbre}_{nk} target={tgt:.2f} measured={f:.2f} err={err:.1f}%")
    json.dump({k:[(r,t,n,tg,f,e) for r,t,n,tg,f,e in v] for k,v in all_bad.items()},
               open('/tmp/bad_notes.json','w'), indent=2)
