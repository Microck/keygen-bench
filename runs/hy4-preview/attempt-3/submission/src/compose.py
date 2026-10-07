import sys, json
sys.path.insert(0,'/workspace/work')
import numpy as np, music, mkinstr
from music import CH, INSTS, DRUMS, ROOTS, PADS, ARPS, ARP_T, BASS_T, GROOVE, SONG, nstr, NCH

BPM, SPEED = 150, 6
NPAT = (music.NBARS + 3)//4
cells = {}

def put(pat, row, ch, instname, midi=None, vol=None, note=None):
    idx, shift = INSTS[instname]
    args = {"pattern": pat, "row": row, "channel": CH[ch] if isinstance(ch, str) else ch}
    if midi is not None:
        note = nstr(midi + 12*shift - 12)   # shift written notes down an octave (rel.note +12 compensates)
    if note is not None: args["note"] = note
    if note != '===':
        args["instrument"] = idx
    if note == '===':
        vol = None
    if vol is not None:
        # XM volume column: byte V means "set volume to V-0x10"; keep V in 0x14..0x50 range
        # (values < 0x10 are undefined and would blast at full level)
        args["volume"] = max(24, min(80, int(round(vol))))
    key = (pat, row, args["channel"])
    if key in cells:
        # later writes merge (keep note/inst unless new given)
        cells[key].update({k:v for k,v in args.items() if k not in ('pattern','row','channel')})
    else:
        cells[key] = args

DRUMNOTE = nstr(60)   # 'C-4'  (with relative_note 29 this plays back near the source rate)
LEVELS = dict(BASS=44, ARP=42, LEAD=53, LEADDET=47, PAD=24)

def write_line(pat, base, chname, instname, notes, level, octv=0, delay=0, volscale=1.0):
    if not notes: return
    for i,(r,d,m) in enumerate(notes):
        row = base + r + delay
        lvl = level*volscale
        if r == 0: lvl = min(64, lvl*1.08)
        if delay and octv: lvl *= 0.72
        put(pat, row, chname, instname, m+octv, vol=lvl)
        end = r + d + delay
        if end < 16 and base+end < 64:
            covered = any((rr+delay) <= end < (rr+dd+delay) for (rr,dd,mm) in notes)
            if not covered:
                put(pat, base+end, chname, instname, note='===')

def bar_cutoff(pat, base, chname, instname):
    put(pat, base, chname, instname, note='===')

def build():
    for b, spec in enumerate(SONG):
        pat = b//4; base = (b%4)*16
        vs = spec.get('volscale', 1.0)
        ch = spec['chord']
        # --- drums
        g = GROOVE[spec['groove']]
        for dname, rows in g.items():
            for r in rows:
                lvl = DRUMS[dname]*vs
                if dname in ('CHAT','OHAT'):
                    lvl = lvl*(1.12 if r % 4 == 0 else 0.82)
                put(pat, base+r, CH[dname], dname, note=DRUMNOTE, vol=lvl)
        if spec.get('endcrash'):
            put(pat, base+spec['endcrash'], CH['CRASH'], 'CRASH', note=DRUMNOTE, vol=DRUMS['CRASH']*vs)
        if spec.get('crash'):
            put(pat, base, CH['CRASH'], 'CRASH', note=DRUMNOTE, vol=DRUMS['CRASH']*vs)
        if spec.get('sweep'):
            put(pat, base, CH['SWEEP'], 'SWEEP', note=DRUMNOTE, vol=DRUMS['SWEEP']*vs)
        # --- bass
        for (r, off) in BASS_T[spec['bass']]:
            lvl = LEVELS['BASS']*vs*(1.1 if r == 0 else 1.0)
            put(pat, base+r, CH['BASS'], 'BASS', ROOTS[ch]+off, vol=lvl)
        # --- arp
        tpl = ARP_T[spec['arp']]
        notes_ar = ARPS[ch]
        for r in range(16):
            if r % spec.get('arp_every', 1): continue
            i = tpl[r % len(tpl)]
            lvl = LEVELS['ARP']*vs*(1.15 if r % 4 == 0 else 0.9)
            put(pat, base+r, CH['ARP'], 'ARP', notes_ar[i]+spec.get('arp_oct', 0), vol=lvl)
        # melody + doubling/echo
        mel = spec.get('melody')
        nxt = None
        if b+1 < music.NBARS:
            nm = SONG[b+1].get('melody')
            nxt = bool(nm) and nm[0][0] == 0
        if mel:
            write_line(pat, base, 'LEAD', 'LEAD', mel, LEVELS['LEAD'], 0, 0, vs)
            if spec.get('echo'):
                write_line(pat, base, 'LEADDET', 'LEADDET', mel, LEVELS['LEADDET'], 12,
                           spec['echo'], vs)
            elif spec.get('dbl'):
                write_line(pat, base, 'LEADDET', 'LEADDET', mel, LEVELS['LEADDET'], 0, 0, vs)
        if mel:
            last_end = max(r+d for (r,d,m) in mel)
            if last_end >= 16 and b+1 < music.NBARS:
                nxt = SONG[b+1].get('melody')
                if not nxt or nxt[0][0] != 0:
                    bar_cutoff((b+1)//4, ((b+1)%4)*16, CH['LEAD'], 'LEAD')
                if spec.get('dbl') or spec.get('echo'):
                    bar_cutoff((b+1)//4, ((b+1)%4)*16, CH['LEADDET'], 'LEADDET')
        # --- pads
        if spec.get('pad', True):
            padnotes = PADS[ch]
            pv = LEVELS['PAD']*vs*spec.get('padvol', 1.0)
            for i, m in enumerate(padnotes):
                put(pat, base, CH['PAD1']+i, 'PAD', m, vol=pv)
    # ensure clean loop point: cut sustaining voices on the very last row
    last = (NPAT-1, 63)
    for cname in ('BASS','LEAD','LEADDET','PAD1','PAD2','PAD3'):
        key = (NPAT-1, 63, CH[cname])
        if key not in cells or 'note' not in cells[key]:
            put(NPAT-1, 63, CH[cname], 'PAD' if cname.startswith('PAD') else cname, note='===')

if __name__ == '__main__':
    build()
    calls = [{"name":"module_new","arguments":{"name":"Keystream","channels":NCH}},
             {"name":"song_set","arguments":{"name":"Keystream","bpm":BPM,"speed":SPEED,
                                             "length":NPAT,"loop_start":0}}]
    for i in range(NPAT):
        calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
    order = []
    for nm, d in mkinstr.INST.items():
        idx = INSTS[nm][0]
        order.append((idx, nm, d))
    order.sort()
    for idx, nm, d in order:
        calls.append({"name":"instrument_set","arguments":{"instrument":idx,"name":nm}})
        calls.append({"name":"sample_create_from_pcm",
                      "arguments":{"instrument":idx,"sample":0,"pcm":d['pcm'],
                                   "encoding":"int16","name":nm[:8]}})
        ss = {"instrument":idx, "sample":0,
              "loop_start":d['loop_start'], "loop_length":d['loop_length'],
              "flags":d['flags'], "panning":d['pan'], "volume":d.get('vol',64)}
        if 'rel' in d:
            ss["relative_note"] = d['rel']; ss["finetune"] = d['finetune']
        calls.append({"name":"sample_set","arguments":ss})
    for key in sorted(cells):
        cells[key]["pattern"] = key[0]; cells[key]["row"] = key[1]; cells[key]["channel"] = key[2]
        calls.append({"name":"pattern_set_cell","arguments":cells[key]})
    import os
    solo = os.environ.get('SOLO')
    if solo:
        keep = set(int(v) for v in solo.split(','))
        if keep:
            calls = [c for c in calls if c['name'] != 'pattern_set_cell' or c['arguments']['channel'] in keep]
    out_xml = os.environ.get('OUTXM','/workspace/work/tune.xm')
    out_wav = os.environ.get('OUTWAV','/workspace/work/tune.wav')
    calls.append({"name":"module_save","arguments":{"path":out_xml}})
    calls.append({"name":"module_render","arguments":{"path":out_wav,"rate":44100,"loops":int(os.environ.get('LOOPS','1'))}})
    json.dump(calls, open('/workspace/work/batch.json','w'))
    print('patterns', NPAT, 'cells', len(cells), 'calls', len(calls))
