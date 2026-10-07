import sys, json
sys.path.insert(0,'/workspace')
from ft import batch, call

PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def N(s):
    s = s.strip()
    if s[1] in '#b': pc, oc = PC[s[:2]], int(s[2])
    else: pc, oc = PC[s[0]], int(s[1:].lstrip('-'))
    return 12*oc + pc + 1
def V(v): return 0x10 + max(0,min(64,int(v)))

INSTVOL = {1:36,2:50,3:46,4:56,5:56,6:60,7:34,8:26,9:46,10:22,11:38,12:24,13:24,
           14:58,15:58,16:50,17:48,18:44,19:48,20:48}
MASTER = 0.82
def VV(inst, vel):
    return max(1, min(64, int(round(INSTVOL.get(inst,64)*vel/64.0*MASTER))))

ROWS = 64
NCH = 14
CH_KICK,CH_SNR,CH_HAT,CH_PERC,CH_BASS,CH_SUB,CH_ARPL,CH_ARPR,CH_STAB,CH_LEAD,CH_LEAD2,CH_PAD,CH_LEAD3,CH_FX = range(14)
PAN = {CH_KICK:128,CH_SNR:128,CH_HAT:146,CH_PERC:96,CH_BASS:128,CH_SUB:128,
       CH_ARPL:22,CH_ARPR:234,CH_STAB:178,CH_LEAD:106,CH_LEAD2:152,CH_PAD:128,
       CH_LEAD3:128,CH_FX:128}
I_KICK,I_SNR,I_CLAP,I_HHC,I_HHO,I_CRASH,I_BASS,I_SUB,I_PLUCK,I_LEADP,I_LEADS,I_PADMIN,I_PADMAJ,I_STABMIN,I_STABMAJ,I_BELL,I_SWEEP,I_ZAP,I_REV,I_TOM = range(1,21)

class Pat:
    def __init__(self, idx, rows=ROWS):
        self.idx=idx; self.rows=rows; self.c={}
    def set(self, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None, pan=True):
        if row<0 or row>=self.rows: return
        d = self.c.setdefault((row,ch),{})
        if (pan and note is not None and fx is None and 'effect' not in d
                and PAN.get(ch,128)!=128 and note!=97):
            d['effect']=8; d['effect_param']=PAN[ch]
        if note is not None: d['note']=note if isinstance(note,int) else N(note)
        if inst is not None: d['instrument']=inst
        if vol  is not None:
            ii = inst if inst is not None else d.get('instrument')
            d['volume']=V(VV(ii,vol) if ii is not None else vol)
        if fx   is not None: d['effect']=fx
        if fxp  is not None: d['effect_param']=fxp
    def has_fx(self, row, ch):
        return 'effect' in self.c.get((row,ch),{})
    def calls(self):
        out=[{"name":"pattern_set_length","arguments":{"pattern":self.idx,"rows":self.rows}}]
        # panning: ensure each channel gets an 8xx early
        for ch in range(NCH):
            if any(self.c.get((r,ch),{}).get('effect')==8 for r in range(0,16)): continue
            for r in range(0,16):
                if not self.has_fx(r,ch):
                    self.set(r,ch,fx=8,fxp=PAN[ch]); break
        for (row,ch),d in sorted(self.c.items()):
            a={"pattern":self.idx,"row":row,"channel":ch}; a.update(d)
            out.append({"name":"pattern_set_cell","arguments":a})
        return out
