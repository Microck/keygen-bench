import numpy as np, math, sys, json
sys.path.insert(0,'/workspace/work')
import synth, xm, score
from score import V
from score import fr, CHORDS, PROG, INST, CH, NCH, PAN, V, drum_bar, bass_bar, arp_bar, MELODIES

SPEED, BPM = 6, 168
ROWS = 64

# ------------- samples -------------
def build_instruments():
    import numpy as np
    def clean(x):
        x = x - x.mean()
        return synth.norm(x)
    lead  = clean(synth.pulse(L_LEAD, 0.16, 19))
    lead2 = clean(synth.norm(0.75*synth.tri(L_LEAD2, 15) + 0.45*synth.pulse(L_LEAD2, 0.5, 15)))
    pluk  = clean(synth.norm(0.8*synth.pulse(L_PLUCK, 0.34, 19) + 0.30*synth.saw(L_PLUCK, 8)))
    padw  = clean(synth.norm(0.55*synth.pulse(L_PAD, 0.25, 26) + 0.5*synth.tri(L_PAD, 20) + 0.25*synth.saw(L_PAD, 8)))
    bassw = clean(synth.norm(0.72*synth.saw(L_BASS, 64) + 0.5*synth.pulse(L_BASS, 0.42, 40) + 0.55*synth.tri(L_BASS, 4)))
    S = {}
    def mksamp(name, data, loop=False, ll=None, bits=8, vol=64, ft=0):
        return xm.Sample(name, data, loop=loop, loop_length=ll, bits=bits, volume=vol, finetune=ft)
    S['KICK'] = mksamp('kick',   synth.kick(), vol=48)
    S['SNARE']= mksamp('snare',  synth.snare(), vol=50)
    S['CLAP'] = mksamp('clap',   synth.clap(), vol=42)
    S['CHAT'] = mksamp('ch-hat', synth.hat(0.055, 0.011), vol=44)
    S['OHAT'] = mksamp('op-hat', synth.hat(0.40, 0.085), vol=42)
    S['TOM']  = mksamp('tom',    synth.tom(), vol=46)
    S['RISR'] = mksamp('riser',  synth.riser(1.40), vol=52)
    S['BASS'] = mksamp('bass',   bassw, loop=True, ll=L_BASS, ft=synth.finetune_for(L_BASS,110.0), vol=50)
    S['LEAD'] = mksamp('lead',   lead,  loop=True, ll=L_LEAD, ft=synth.finetune_for(L_LEAD,440.0), vol=50)
    S['LEAD2']= mksamp('lead2',  lead2, loop=True, ll=L_LEAD2, ft=synth.finetune_for(L_LEAD2,440.0), vol=46)
    S['PLUK'] = mksamp('pluck',  pluk,  loop=True, ll=L_PLUCK, ft=synth.finetune_for(L_PLUCK,440.0), vol=50)
    S['PAD']  = mksamp('pad',    padw,  loop=True, ll=L_PAD, ft=synth.finetune_for(L_PAD,261.63), vol=46)
    env_note = [(0,0),(1,64),(3,58),(9,54)]
    env_pluk = [(0,64),(1,60),(5,46),(12,34),(24,22)]
    env_pad  = [(0,0),(5,40),(13,62),(26,56)]
    env_bass = [(0,0),(1,64),(4,58),(11,52)]
    off = dict(vol_type=0, vol_points=xm.DEF_VOLENV[:6], vol_sustain=2,
               pan_points=xm.DEF_PANENV[:6])
    I = {}
    NAMES = {'KICK':'Nine Inch Kick','SNARE':'Snappy Snare','CLAP':'Wide Clap','CHAT':'Closed Hat',
             'OHAT':'Open Hat','TOM':'Tom','RISR':'Noise Riser','BASS':'Saw Bass','LEAD':'Pulse Lead',
             'LEAD2':'Tri Harmony','PLUK':'Pluck Melody','PAD':'Pad Stack'}
    for k in ['KICK','SNARE','CLAP','CHAT','OHAT','TOM','RISR']:
        I[k] = xm.Instrument(NAMES[k][:22],[S[k]], **off)
    I['BASS'] = xm.Instrument(NAMES['BASS'],[S['BASS']], vol_type=1, vol_points=env_bass, vol_sustain=3, vol_loop=(0,0))
    I['LEAD'] = xm.Instrument(NAMES['LEAD'],[S['LEAD']], vol_type=1, vol_points=env_note, vol_sustain=3, vol_loop=(0,0))
    I['LEAD2']= xm.Instrument(NAMES['LEAD2'],[S['LEAD2']], vol_type=1, vol_points=env_note, vol_sustain=3, vol_loop=(0,0))
    I['PLUK'] = xm.Instrument(NAMES['PLUK'],[S['PLUK']], vol_type=1, vol_points=env_pluk, vol_sustain=4, vol_loop=(0,0))
    I['PAD']  = xm.Instrument(NAMES['PAD'],[S['PAD']], vol_type=1, vol_points=env_pad, vol_sustain=3, vol_loop=(0,0))
    return I, S

L_LEAD, L_LEAD2, L_PLUCK, L_PAD, L_BASS = 38, 25, 38, 76, 168
NOTE_L = {9:L_LEAD, 10:L_LEAD2, 11:L_PLUCK, 12:L_PAD, 8:L_BASS}

# ------------- pattern builder -------------
class Pat:
    def __init__(self, rows=ROWS):
        self.cells = {}
        self.rows = rows
    def add(self, row, ch, **kw):
        r = row % self.rows
        c = list(self.cells.get((r,ch), [0,0,0,0,0]))
        if 'note' in kw or 'freq' in kw:
            if 'freq' in kw:
                L = NOTE_L[kw['inst']]
                c[0] = synth.noteval(L, kw['freq'])
            else:
                c[0] = kw['note']
            c[1] = kw['inst']
        if 'vol' in kw and kw['vol'] is not None: c[2] = kw['vol']
        if 'fx' in kw:  c[3] = kw['fx']
        if 'fxp' in kw: c[4] = kw['fxp']
        self.cells[(r,ch)] = tuple(c)

# ------------- arrangement -------------
def D(s): return [s]*4
ARR = [
 # 0 intro
 dict(prog='PA', drums=['intro1','intro1','intro2','intro2'], bass='four', arp=None, arp2=None, gain=[0.86,0.88,0.90,0.92],
      mel=None, pad=True, padvol=12, fill=[0,0,0,1]),
 # 1 intro2
 dict(prog='PA', drums=['intro2','intro2','intro2','four'], bass='oct8', arp='tri6', arp2=None, gain=[0.94,0.96,0.98,1.0],
      mel=None, pad=True, padvol=13, arpvol=38, fill=[0,0,0,1]),
 # 2 full A
 dict(prog='PA', drums=D('four'), bass='oct8', arp='up4', arp2='oct4', mel='A',
      pad=True, padvol=14, fill=[0,0,0,1]),
 # 3 variation
 dict(prog='PA', drums=D('drive'), bass='sixteen', arp='tri6', arp2='tri6', mel='A',
      pad=True, padvol=14, arpvol=42, arp2vol=32, fill=[0,0,0,1]),
 # 4 variation 2
 dict(prog='PA', drums=['four','four','four','four'], bass='oct8', arp='oct4', arp2='up4',
      mel='A2', pad=True, padvol=15, fill=[0,0,0,1]),
 # 5 breakdown
 dict(prog='PD', drums=['none','none','half','four'], bass='whole', arp=None, arp2=None, gain=[0.70,0.72,0.80,0.90],
      mel='C', pad=True, padvol=16, fill=[0,0,0,1]),
 # 6 build
 dict(prog='PA', drums=['half','four','drive','drive'], bass=['whole','four','oct8','sixteen'], gain=[0.80,0.90,0.98,1.05],
      arp='sync', arp2='up4', mel='A', pad=True, padvol=14, arpvol=42, riser=True,
      fill=[0,0,0,1]),
 # 7 B section
 dict(prog='PC', drums=D('four'), bass='oct8', arp='tri6', arp2='oct4', mel='B',
      pad=True, padvol=14, fill=[0,0,0,1]),
 # 8
 dict(prog='PC', drums=D('drive'), bass='sixteen', arp='up4', arp2='tri6', mel='B',
      pad=True, padvol=15, arp2vol=34, fill=[0,0,0,1]),
 # 9
 dict(prog='PC', drums=['four','drive','four','four'], bass='oct8', arp='tri6', arp2=None,
      mel='B', meloct=0, pad=True, padvol=15, fill=[0,0,0,1]),
 # 10 breakdown 2
 dict(prog='PB', drums=['none','none','half','four'], bass='whole', arp='oct4', arp2=None, gain=[0.68,0.72,0.82,0.92],
      mel='D', pad=True, padvol=16, arpvol=30, fill=[0,0,0,1], riser=True),
 # 11 rebuild
 dict(prog='PA', drums=D('four'), bass='oct8', arp='up4', arp2='tri6', mel='A',
      pad=True, padvol=14, fill=[0,0,0,1]),
 # 12
 dict(prog='PA', drums=D('drive'), bass='sixteen', arp='tri6', arp2='oct4', mel='A2',
      pad=True, padvol=15, fill=[0,0,0,1]),
 # 13
 dict(prog='PA', drums=['four','four','drive','drive'], bass='oct8', arp='sync', arp2='up4',
      mel='A', pad=True, padvol=14, fill=[0,0,0,1]),
 # 14 mini break
 dict(prog='PD', drums=['none','half','four','four'], bass=['whole','whole','oct8','oct8'], gain=[0.66,0.76,0.88,0.96],
      arp='oct4', arp2=None, mel=None, pad=True, padvol=16, arpvol=30, fill=[0,0,0,1], riser=True),
 # 15
 dict(prog='PA', drums=D('four'), bass='oct8', arp='up4', arp2='tri6', mel='E',
      pad=True, padvol=14, meloct=0, fill=[0,0,0,1]),
 # 16
 dict(prog='PA', drums=D('drive'), bass='sixteen', arp='oct4', arp2='up4', mel='A2',
      pad=True, padvol=15, fill=[0,0,0,1]),
 # 17 outro -> loop
 dict(prog='PA', drums=['four','four','drive','four'], bass='oct8', arp='tri6', arp2='oct4', gain=[1.0,1.0,1.0,0.92],
      mel='A', pad=True, padvol=14, fill=[0,0,0,1], outro=True),
]

def build_patterns(I):
    pats = []
    for pi, spec in enumerate(ARR):
        p = Pat()
        prog = PROG[spec['prog']]
        for ch in range(NCH):
            p.add(0, ch, fx=8, fxp=PAN[ch])
        for bar in range(4):
            g = spec.get('gain', 1.0)
            score.GAIN = g[bar] if isinstance(g, (list, tuple)) else g
            chord = prog[bar]
            base = bar*16
            def put(row, chan, instnum=None, instkey=None, **kw):
                if instnum is not None: kw['inst'] = instnum
                if instnum is not None and instnum <= 7 and 'freq' not in kw and 'note' not in kw:
                    kw['note'] = synth.NOTE78
                p.add(base+row, CH[chan], **kw)
            # drums
            dsty = spec['drums'][bar]
            drum_bar(put, dsty, bar, fill=bool(spec['fill'][bar]))
            # bass
            bstyle = spec['bass'][bar] if isinstance(spec['bass'], list) else spec['bass']
            bass_bar(put, bstyle, chord, bar)
            # arps
            if spec.get('arp'):
                arp_bar(put,'arp',spec['arp'],chord,bar,inst='LEAD',
                        vol=spec.get('arpvol',48))
            if spec.get('arp2'):
                arp_bar(put,'arp2',spec['arp2'],chord,bar,inst='LEAD2',
                        shift=12, vol=spec.get('arp2vol',38))
            # pad
            if spec.get('pad'):
                for i, nm in enumerate(CHORDS[chord]['pad']):
                    put(0,['pad','pad2','pad3'][i], inst=INST['PAD'], freq=fr(nm),
                        vol=V(spec.get('padvol',30)))
            # melody (+ echo)
            if spec.get('mel'):
                oct_shift = spec.get('meloct',0)
                for (r,d,nm) in MELODIES[spec['mel']][bar]:
                    f0 = fr(nm)*2**(oct_shift/12.0)
                    put(r,'mel', inst=INST['PLUK'], freq=f0, vol=V(54))
                    if oct_shift==0 and r+3 < 16:
                        put(r+3,'echo', inst=INST['PLUK'], freq=f0, vol=V(22))
        # riser
        if spec.get('riser'):
            p.add(48, CH['fx'], note=synth.NOTE78, inst=INST['RISR'], vol=V(44))
        pats.append((ROWS, p.cells))
    return pats

def main(out='/workspace/submission/tune.xm', mute=()):
    I, S = build_instruments()
    keys = ['KICK','SNARE','CLAP','CHAT','OHAT','TOM','RISR','BASS','LEAD','LEAD2','PLUK','PAD']
    insts = [I[k] for k in keys]
    pats = build_patterns(I)
    if mute:
        pats = [(r, {k:v for k,v in c.items() if k[1] not in mute}) for r,c in pats]
    order = list(range(len(pats)))
    xm.write_xm(out, 'keygen loop', NCH, SPEED, BPM, order, pats, insts, restart=0)
    print('patterns', len(pats), 'orders', len(order))
    cells = sum(len(c) for _, c in pats)
    print('cells', cells)

if __name__ == '__main__':
    main()
