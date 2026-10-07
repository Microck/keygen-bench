neon keyring  -  an original keygen-style tracker tune (FastTracker II XM)

Format   : XM, 14 channels, 13 patterns x 64 rows, 150 BPM / speed 6, linear frequency table
Length   : 83.2 s per pass; song restarts at order position 2 (the intro plays once,
           then verse -> chorus -> break -> build -> final chorus -> post-chorus loop forever).
Key      : E minor.  Verse  Em | C | G | D,  bridge  Am | Em | C | D(B7),
           chorus  Em | C | G | D  and  Em | C | D | B7,  break  Am | C | Em | D,  build  C | D | B7.
Sound    : every sample is synthesized from scratch with NumPy (src/synth.py):
           PWM pulse lead, detuned saw stack, 25% pulse arps, plucked filtered bass,
           three-saw pad with a baked-in swell, drum kit (kick/snare/hats/clap/crash/zap/riser).
           No instrument envelopes are used; all shaping lives in the sample data,
           the volume column and effects (0xy arpeggios, 3xx slides, 4xy vibrato, E9x hat rolls).
Build    : python3 src/synth.py && python3 src/compose.py && ft2 batch build.json
           (compose.py emits the FT2 tool calls; the module is saved by FT2 itself).
Preview  : preview.wav is one pass rendered by the FT2 clone (44.1 kHz, 16 bit).
