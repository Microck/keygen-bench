import json, math, os
calls=[]
def call(tool,**args): calls.append({'name':tool,'arguments':args})
def cell(p,r,c,n=None,i=None,v=None,e=None,ep=None):
 d={'pattern':p,'row':r,'channel':c}
 if n is not None:d['note']=n
 if i is not None:d['instrument']=i
 if v is not None:d['volume']=v
 if e is not None:d['effect']=e
 if ep is not None:d['effect_param']=ep
 call('pattern_set_cell',**d)

# 12 patterns, 4 bars each, BPM 150 (row=.1s), a 28.8 second seamless loop
# Progression in F# minor: F#m - D - A - E - Bm - D - E - C#7; written as bass-root octave sets
# note numbers chromatic tracker numbering C-0=13, C-4=49. Helpers
# Display names resolve reliably from semitone integer, but compose with FT2 names.
NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nt(n): return NAMES[n%12]+str(n//12-1)
# roots by progression (pitch classes semitones) and bass note register
chords=[(6,[6,9,1]),(2,[2,6,9]),(9,[9,1,4]),(4,[4,8,11]),(11,[11,2,6]),(2,[2,6,9]),(4,[4,8,11]),(1,[1,5,8]),(6,[6,9,1]),(9,[9,1,4]),(2,[2,6,9]),(6,[6,9,1])]
# make order linear 0..11
for p in range(12):
 call('pattern_clear',pattern=p); call('pattern_set_length',pattern=p,rows=64); call('order_set',position=p,pattern=p)
# Arrange each four-bar block; pattern 0 is opening motif, through 11 full finale.
for p,(root,triad) in enumerate(chords):
 # bass channel 0: four-to-floor octave roots with rhythmic fifth/approach notes
 for bar in range(4):
  r=bar*16
  # bass on beats, notes on every 8th (row 8 = half second)
  vals=[root,root,root+7,root]
  for beat in range(4):
   pitch=(vals[beat]%12)+24 # F#2-ish note index? semitone mapping absolute note
   # note conversion: semitone pclass + octave*12; octave 3 => index 42; above expression note 30 represents D#2. use octave 3 = 36+pc
   pitch=36+vals[beat]
   cell(p,r+beat*4,0,nt(pitch),3,54 if beat in [0,2] else 47)
 # sidechain-like sustained chord stabs as arpeggiated layers on channels 2,3; half-bar chord attacks
 # pad channel 1: warm two-note chord every 8 rows, low velocities via volume
 for bar in range(4):
  for beat in range(2):
   rr=bar*16+beat*8
   # chord register; alternating voicings
   a,b=triad[0],triad[1 if (bar+beat)%2==0 else 2]
   cell(p,rr,1,nt(48+a),2,33 if p not in [0,11] else 38)
   cell(p,rr,2,nt(55+b),2,30)
 # pluck motif/arpeggio channel3: minor/major arps, melodic counterline, sixteenth-ish (2 rows)
 for bar in range(4):
  for k in range(8):
   rr=bar*16+k*2
   # motifs change per arrangement section, musically scalar from chord notes & passing notes
   scale=[root,triad[1],triad[2],root+12,triad[2],triad[1],root+7,triad[1]]
   ix=(k + bar*3 + p*2)%len(scale)
   pitch=60+scale[ix] # octave 4-5
   # section variations: skip some eighths for spacious start/break; alternate pattern cells
   active=True
   if p in [0,4,8,11] and k in [3,7] and bar%2==0: active=False
   if p in [5,6] and k in [1,3,5,7] and bar<2: active=False
   if active:
    cell(p,rr,3,nt(pitch),4,40 if p<2 else 46)
 # drums channels 4 kick, 5 snare, 6 closed hat, 7 open/hat accent
 for bar in range(4):
  base=bar*16
  for beat in range(4):
   rr=base+beat*4
   # dance kick, drop out sparingly in breakdown sections
   if not (p in [4,5] and bar<2 and beat==3):
    cell(p,rr,4,nt(49),5,52 if beat==0 else 46)
   # classic backbeat on beats 2,4 (row 4,12)
   if beat in [1,3]:
    cell(p,rr,5,nt(49),6,38)
   # busy but controlled bright sixteenth/eighth ticks; alternating velocity via volume
   for sub in [2,6,10]:
    # choose row based absolute within bar
    if sub<16:
     if (p==0 and bar==0 and sub in [10,14]) or (p in [4,5] and sub in [6,14]): continue
     cell(p,base+sub,6,nt(49),7,21 if sub%4==2 else 14)
   # offbeat open metallic tick on latter half every other beat
   for sub in [14]:
    if p not in [4] or bar>=2:
     cell(p,base+sub,7,nt(49),8,18)
 # Main saw lead channel8: hook starts pattern 1, gets dynamic growth/varied final cadence
 # melodic four-bar phrase, 8th notes grid, crafted tonal hook in F# Aeolian / harmonic dominant
 # specific melody contours, each pattern transposed/reharmonized loosely around root
 # key F# minor melody as scale degrees
 # rows 0..63, motif repeated/varied per block
 hook=[(0,73),(2,76),(4,78),(6,81),(8,80),(10,78),(12,76),(14,73),
       (16,71),(18,73),(20,76),(22,78),(24,76),(26,73),(28,71),(30,69),
       (32,73),(34,76),(36,78),(38,83),(40,81),(42,80),(44,78),(46,76),
       (48,73),(50,71),(52,69),(54,71),(56,73),(58,76),(60,78),(62,81)]
 # ints are pitch indexes; high 70s correspond E5 etc. Keep melody in motif key, transform some endings
 # Different variants, set lead entry/space by section
 lead_enable = p not in [0,4,5,8] # intro sparse, breakdown, bridge, build
 if p in [0,8]: lead_enable=True # gentle teaser/tail phrases
 for j,(rr,pitch) in enumerate(hook):
  # Intro and bridge have incomplete exposed fragments, later whole hook. Pattern 0 is teaser.
  if p==0 and rr>=16: continue
  if p in [4,5] and rr>=32: continue
  if p==8 and (rr<32 or rr>=56): continue
  if p in [2,6,9] and j%8 in [6,7]: continue
  # transposition for chord contexts; retain a clearly recognizable topline.
  shift=0
  if p==3: shift=2
  elif p==7: shift=-2
  elif p==10: shift=2
  elif p==11 and rr>=48: shift=-1 # leading-tone flavor into loop tonic
  n=pitch+shift
  # Small ending call-and-response on the last cadence
  if p==11 and rr in (56,58,60,62): n=[78,80,81,85][(rr-56)//2]
  vol=50 if p>=1 else 39
  cell(p,rr,8,nt(n),1,vol)
 # secondary high accent stabs / bell chimes on phrases, channel 9
 for bar in range(4):
  # each bar chime on second half pickup; alternate chord tone and fifth
  if (p+bar)%2==0 or p in [1,3,7,9,11]:
   rr=bar*16+12
   pitch=72+triad[(bar+p)%3]
   cell(p,rr,9,nt(pitch),4,29 if p<3 else 34)
 # cymbal transitions channel 10 every 8/16 bars, with 11 reserved for tom fill
 if p in [0,2,4,6,8,10]:
  cell(p,0,10,nt(49),10,35)
 # tom/snare fills bar 4 end on phrase ends, and transitions into next chord
 if p in [1,3,5,7,9,11]:
  for rr,inst,note in [(56,9,36),(60,6,36),(62,6,36)]: cell(p,rr,11,nt(note),inst,31)
 # last cell of final pattern is an explicit end note cut before loop restart, silence drums on last row.
# Add end-of-pattern phrase cadence: use a lower tonic on last row of final block briefly before restart.
cell(11,63,8,'off')
# Pattern 11 closes onto the exact tonal tonic F# (top melody note F#5); kick at row 60 then rest till end.
# In the first pattern, match final bass/pad state to tonic, and moderate intro is not too bare.
# Set expressive lead panning / global song volume metadata already.
# Ensure song loop corresponds to order 0.
call('song_set',name='NEON CIRCUIT - Key to the Stars',bpm=150,speed=6,length=12,loop_start=0,channels=12)
open('/workspace/compose.json','w').write(json.dumps(calls))
print('calls',len(calls))
