import sys; sys.path.insert(0,'/workspace/work')
import numpy as np, json
import final4 as F
from final4 import *
import compose_final as CF
from compose_final import INS, DATA, CH
CH=dict(CH)
CH['arpHL']=16; CH['arpHR']=17
from final4 import BASS_ROOT, tr, arp_bars as arp_bar, pad_bar, bass_bar, kick_bar, snare_bar, hat_bar, drums, fill, crash_row, riser_row, bell_row, rim_row, spark_row, melody, hookA, hookA2, hookB, hookB2, hookC, hookOut, N, Tr, XM

PROG_A=['Am','F','C','G']
PROG_B=['Dm','Bb','F','E']
PROG_C=['F','G','Em','Am']
PROG_O=['Am','F','C','G']

def stabs(T,bar,chord,vol=40,rows=(2,6,10,14)):
    inst=INS['stab'+chord]
    for r in rows:
        T.note(bar*16+r,CH['stab'],'C-4',inst,vol)

def arp_hi(T,bar,chord,vol=22,mode='down'):
    base=[nm(N(x)+24) for x in ARP[chord]]
    if mode=='down': seq=base[::-1]
    elif mode=='up': seq=base
    else: seq=base+base[-2:0:-1]
    row0=bar*16
    for i in range(0,16,2):
        chn=CH['arpHL'] if (i//2)%2==0 else CH['arpHR']
        inst=INS['arpL'] if chn==CH['arpHL'] else INS['arpR']
        T.note(row0+i,chn,seq[(i//2)%len(seq)],inst,vol if i%4==0 else vol-8)

def theme_arp(T,base,notes,inst=None,vol=46):
    inst=INS['spark'] if inst is None else inst
    for row,n,v in notes:
        T.note(base+row,CH['spark'],n,inst,v if v is not None else vol)

# ============ patterns ============
def p_intro():
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=54 if b==0 else 50)
    # bell motif (Am pentatonic) + rising intro run
    for r,n,v in [(0,'A-4',40),(3,'C-5',36),(6,'E-5',40),(9,'A-5',44),
                  (12,'C-6',40),(14,'E-6',44),(16,'F-5',38),(20,'C-6',42),
                  (24,'A-5',38),(28,'E-6',42),(32,'G-5',40),(36,'D-6',44),
                  (40,'B-5',40),(44,'G-5',36),(48,'A-5',44),(52,'C-6',42),(56,'E-6',46),(60,'A-6',50)]:
        T.note(r,CH['fx2'],n,INS['bell'],min(62,v+8))
    # pad hit right on the loop point (matches the ringing Am at the end of the outro)
    T.note(0,CH['padL'],'C-4',INS['padAmL'],54)
    T.note(0,CH['padR'],'C-4',INS['padAmR'],54)
    # arps building
    arp_bar(T,1,'F',vol=32,step=2,mode='updown'); arp_bar(T,2,'C',vol=38,step=2,mode='updown'); arp_bar(T,3,'G',vol=46,mode='updown')
    # first bar arp too
    for i in range(0,8,2):
        ch=CH['arpL'] if i%2==0 else CH['arpR']
        seq=['A-4','C-5','E-5','A-5']
        T.note(i,ch,seq[(i//2)%4],INS['arpL' if ch==CH['arpL'] else 'arpR'],30)
    hat_bar(T,0,'sparse',vol=24); hat_bar(T,1,'sparse',vol=30); hat_bar(T,2,'off',vol=38); hat_bar(T,3,'8ths',vol=46)
    kick_bar(T,1,[0,8],vol=42); kick_bar(T,2,[0,8],vol=50); kick_bar(T,3,[0,4,8,12],vol=56)
    snare_bar(T,3,[4,12],vol=48)
    crash_row(T,0,vol=34); riser_row(T,32,vol=38)
    rim_row(T,16,vol=24); rim_row(T,48,vol=28)
    return T.p

def p_mainA(theme_fn, sparkle=False):
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=36); bass_bar(T,b,ch,vol=60); arp_bar(T,b,ch,vol=40,mode='updown')
        stabs(T,b,ch,vol=34)
        drums(T,b,'basic','8ths')
    crash_row(T,0,vol=44)
    melody(T,theme_fn(),INS['lead'],vol=56,harm=True,chords=PROG_A,harm_vol=32)
    fill(T,3,'snare',vol=42,start=14)
    if sparkle:
        for i in range(2,16,4): spark_row(T,i,vol=24)
    return T.p

def p_varA():
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=36); bass_bar(T,b,ch,vol=60,style='oct' if b==1 else '8ths')
        arp_bar(T,b,ch,vol=38,mode='updown'); stabs(T,b,ch,vol=32)
        drums(T,b,'drive' if b in (1,3) else 'basic','16ths' if b==3 else '8ths')
    crash_row(T,0,vol=44); crash_row(T,32,vol=36)
    melody(T,hookA2(),INS['lead'],vol=56,harm=True,chords=PROG_A,harm_vol=32)
    fill(T,3,'mix',vol=44)
    return T.p

def p_mainB(theme_fn, full=False):
    T=Tr()
    for b,ch in enumerate(PROG_B):
        pad_bar(T,b,ch,vol=40 if full else 38); bass_bar(T,b,ch,vol=62); arp_bar(T,b,ch,vol=38,mode='up')
        stabs(T,b,ch,vol=36 if full else 34)
        drums(T,b,'four' if full else 'basic','8ths')
    crash_row(T,0,vol=46); crash_row(T,32,vol=38)
    melody(T,theme_fn(),INS['lead'],vol=58,harm=True,chords=PROG_B,harm_vol=34)
    fill(T,3,'snare',vol=44,start=14)
    return T.p

def p_break():
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=54); arp_bar(T,b,ch,vol=28,mode='updown' if b%2 else 'up')
    crash_row(T,0,vol=32)
    for r,n,v in [(0,'A-5',42),(6,'C-6',38),(12,'E-6',42),(16,'F-5',38),(22,'A-5',36),
                  (28,'C-6',40),(32,'G-5',38),(38,'B-5',36),(44,'D-6',40),(48,'E-5',34),
                  (54,'G-5',36),(60,'B-5',38)]:
        T.note(r,CH['fx2'],n,INS['bell'],min(62,v+8))
    bass_bar(T,2,'C',vol=48,style='sparse'); bass_bar(T,3,'G',vol=48,style='sparse')
    hat_bar(T,2,'sparse',vol=24); hat_bar(T,3,'sparse',vol=28)
    kick_bar(T,3,[0,8],vol=44); snare_bar(T,3,[12],vol=40)
    riser_row(T,48,vol=42)
    fill(T,3,'toms',vol=42,start=12)
    # soft lead answer in the second half of the break
    for r,n,v in [(32,'E-6',42),(36,'C-6',38),(40,'A-5',40),(44,'E-5',36),(48,'A-5',42),(50,'C-6',40),(52,'E-6',44),(54,'A-6',46)]:
        T.note(r,CH['lead'],n,INS['lead2'],v)
        T.note(r+2,CH['harm'],n if r%8==0 else nm(N(n)-3),INS['leadR'],max(24,v-8))
    T.note(56,CH['lead'],'A-6',INS['lead2'],48)
    T.note(56,CH['harm'],'E-6',INS['leadR'],36)
    # keygen "modem" sparkle run at the end of the breakdown
    for i,n in enumerate(['A-4','E-5','A-5','C-6','E-6','A-6','E-6','C-6']):
        T.note(56+i,CH['spark'],n,INS['spark'],34 if i%2==0 else 28)
    for i,n in enumerate(['E-5','A-5','C-6','E-6']):
        T.note(60+i,CH['fx2'],n,INS['bell'],32)
    return T.p

def bass16(T,bar,chord,vol=60):
    r=BASS_ROOT[chord]; r12=tr(r,12); fifth=tr(r,7)
    row0=bar*16
    seq=[r,r,r12,r,fifth,r,fifth,r12,r,r,r12,r,fifth,r12,fifth,r]
    for i,n in enumerate(seq):
        T.note(row0+i,CH['bass'],n,INS['bass'],vol if i%4==0 else vol-8)

def spark_run(T,bar,chord,base_note,start=56,vol=30):
    b=N(base_note)
    seq=[nm(b+d) for d in (0,7,12,7,0,12,19,12)]
    for i in range(8):
        r=start+i
        if r>=64: break
        T.note(r,CH['spark'],seq[i],INS['spark'],vol if i%2==0 else vol-8)

def p_fullA(theme_fn, peak=False, use_lead2=False):
    T=Tr()
    for b,ch in enumerate(PROG_A):
        pad_bar(T,b,ch,vol=40)
        if peak and b in (1,3): bass16(T,b,ch,vol=62)
        else: bass_bar(T,b,ch,vol=62,style='8ths' if b==3 else ('push' if b==1 else '8ths'))
        arp_bar(T,b,ch,vol=38,mode='updown')
        arp_hi(T,b,ch,vol=24,mode='down')
        stabs(T,b,ch,vol=38 if peak else 34)
        drums(T,b,'push' if peak else 'four','16ths' if peak else '8ths')
    crash_row(T,0,vol=46); crash_row(T,32,vol=38)
    inst=INS['lead2'] if use_lead2 else INS['lead']
    melody(T,theme_fn(),inst,vol=58,harm=True,chords=PROG_A,harm_vol=38)
    for i in range(0,16,4): spark_row(T,i,vol=24)
    if peak:
        spark_run(T,3,PROG_A[3],'D-6',56,32)
    fill(T,3,'mix',vol=48)
    return T.p

def p_fullB(theme_fn, peak=False):
    T=Tr()
    for b,ch in enumerate(PROG_B):
        pad_bar(T,b,ch,vol=42)
        if peak and b in (1,3): bass16(T,b,ch,vol=62)
        else: bass_bar(T,b,ch,vol=62)
        arp_bar(T,b,ch,vol=36,mode='up')
        arp_hi(T,b,ch,vol=22,mode='down')
        stabs(T,b,ch,vol=38 if peak else 34)
        drums(T,b,'push' if peak else 'four','16ths' if peak else '8ths')
    crash_row(T,0,vol=46); crash_row(T,32,vol=40)
    melody(T,theme_fn(),INS['lead'],vol=58,harm=True,chords=PROG_B,harm_vol=38)
    for i in range(2,16,4): spark_row(T,i,vol=22)
    if peak:
        spark_run(T,3,PROG_B[3],'B-5',56,30)
    fill(T,3,'snare16',vol=48,start=8)
    return T.p

def p_C():
    T=Tr()
    for b,ch in enumerate(PROG_C):
        pad_bar(T,b,ch,vol=40); bass_bar(T,b,ch,vol=60,style='oct' if b<2 else '8ths')
        arp_bar(T,b,ch,vol=38,mode='skip' if b%2 else 'updown')
        stabs(T,b,ch,vol=34)
        drums(T,b,'drive' if b%2 else 'basic','8ths' if b%2 else '16ths')
    crash_row(T,0,vol=44); crash_row(T,32,vol=38)
    melody(T,hookC(),INS['lead2'],vol=58,harm=True,chords=PROG_C,harm_vol=34)
    for i in range(2,16,4): spark_row(T,i,vol=22)
    fill(T,3,'mix',vol=46)
    return T.p

def p_outro():
    T=Tr()
    for b,ch in enumerate(PROG_O):
        pad_bar(T,b,ch,vol=44); 
        if b<3: bass_bar(T,b,ch,vol=56,style='8ths' if b!=1 else 'push')
        arp_bar(T,b,ch,vol=34,mode='updown'); stabs(T,b,ch,vol=30)
        if b<3: drums(T,b,'basic','8ths')
    crash_row(T,0,vol=40)
    melody(T,hookOut(),INS['lead'],vol=56,harm=True,chords=PROG_O,harm_vol=34)
    # final bar: Am resolution + decaying tail that hands over to the intro
    p=T.p
    for (r,ch) in list(p.cells):
        if r>=48: del p.cells[(r,ch)]
    p.cells[(48,CH['padL'])]={'note':N('C-4'),'inst':INS['padAmL'],'vol':52}
    p.cells[(48,CH['padR'])]={'note':N('C-4'),'inst':INS['padAmR'],'vol':52}
    p.cells[(48,CH['bass'])]={'note':N('A-2'),'inst':INS['bass'],'vol':58}
    p.cells[(48,CH['kick'])]={'note':N('C-4'),'inst':INS['kick'],'vol':58}
    p.cells[(48,CH['snare'])]={'note':N('C-4'),'inst':INS['snare'],'vol':52}
    p.cells[(48,CH['fx'])]={'note':N('C-4'),'inst':INS['crash'],'vol':40}
    p.cells[(48,CH['hats'])]={'note':N('C-4'),'inst':INS['hatC'],'vol':48}
    p.cells[(48,CH['stab'])]={'note':N('C-4'),'inst':INS['stabAm'],'vol':34}
    for i,n in enumerate(['A-4','C-5','E-5','A-5']):
        p.cells[(48+i,CH['fx2'])]={'note':N(n),'inst':INS['bell'],'vol':34+i*3}
    for r,n in [(48,'A-5'),(52,'E-5'),(54,'G-5'),(56,'A-5')]:
        p.cells[(r,CH['lead'])]={'note':N(n),'inst':INS['lead'],'vol':54}
        p.cells[(r+2,CH['lead'])]={'note':97}
    p.cells[(59,CH['lead'])]={'eff':0x0E,'par':0xC0}
    p.cells[(48,CH['harm'])]={'note':N('E-5'),'inst':INS['leadR'],'vol':34}
    p.cells[(51,CH['harm'])]={'note':97}
    p.cells[(56,CH['harm'])]={'note':N('C-5'),'inst':INS['leadR'],'vol':32}
    p.cells[(59,CH['harm'])]={'note':97}
    p.cells[(48,CH['echo'])]={'note':N('A-5'),'inst':INS['echo'],'vol':24}
    p.cells[(49,CH['echo'])]={'note':97}
    p.cells[(52,CH['echo'])]={'note':N('E-5'),'inst':INS['echo'],'vol':22}
    p.cells[(53,CH['echo'])]={'note':97}
    for r,n,v in [(56,'C-4',44),(58,'E-4',40),(60,'G-4',42),(62,'A-4',34)]:
        p.cells[(r,CH['perc'])]={'note':N(n),'inst':INS['tom'],'vol':v}
    # let an Am pad ring across the loop point into the intro
    p.cells[(56,CH['padL'])]={'note':N('C-4'),'inst':INS['padAmL'],'vol':46}
    p.cells[(56,CH['padR'])]={'note':N('C-4'),'inst':INS['padAmR'],'vol':46}
    p.cells[(60,CH['fx2'])]={'note':N('A-5'),'inst':INS['bell'],'vol':30}
    p.cells[(62,CH['fx2'])]={'note':N('E-6'),'inst':INS['bell'],'vol':26}
    return p

# per-pattern (section) level trim -> gives the arrangement a build
SECTION_GAIN=[1.00, 0.94, 1.00, 0.94, 0.80, 1.02, 1.08, 1.02, 1.10, 0.96]

def apply_section_gains(xm):
    for pi,p in enumerate(xm.patterns):
        g=SECTION_GAIN[pi] if pi<len(SECTION_GAIN) else 1.0
        if abs(g-1.0)<0.01: continue
        for c in p.cells.values():
            v=c.get('vol')
            if v is not None:
                c['vol']=int(round(max(1,min(64,v*g))))

def build_song():
    xm=XM('keygen',channels=18,bpm=150,speed=6,restart=0)
    pats=[p_intro(),
          p_mainA(hookA),
          p_varA(),
          p_mainB(hookB),
          p_break(),
          p_fullA(hookA, peak=False),
          p_fullB(hookB2, peak=True),
          p_C(),
          p_fullA(hookA2, peak=True),
          p_outro()]
    for p in pats: xm.add_pattern(p)
    xm.order=list(range(len(pats)))
    for I in CF.make_instruments_patched():
        xm.add_instrument([dict(data=I['data'],name=I['name'],volume=I['vol'],panning=I['pan'],
                                finetune=0,relnote=I['relnote'],loop=((0,len(I['data'])) if I['loop'] else None),bits=16)],I['name'])
    apply_section_gains(xm)
    # hat panning animation
    for p in xm.patterns:
        for r in range(0,64,4):
            key=(r,CH['hats'])
            if key not in p.cells:
                p.cells[key]={'eff':0x08,'par':0x58 if (r//4)%2==0 else 0xA8}
    return xm

if __name__=='__main__':
    xm=build_song(); xm.save('work/fs.xm')
    L,R=render_xm(xm,'fs')
    print('dur %.2f peak %.3f rms %.4f corr %.3f side/mid %.3f'%(len(L)/44100,max(np.abs(L).max(),np.abs(R).max()),
        np.sqrt(((L**2).mean()+(R**2).mean())/2),np.corrcoef(L,R)[0,1],
        np.sqrt((((L-R)/2)**2).mean())/np.sqrt((((L+R)/2)**2).mean())))
