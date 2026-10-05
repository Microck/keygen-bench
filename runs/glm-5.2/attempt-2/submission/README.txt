SERIAL SUNRISE  -  an original keygen tune (FastTracker II / XM)
================================================================

Module   : tune.xm      (12 channels, 16 song positions, 16 patterns of 64 rows)
Length   : ~1:41 before it loops back (song restart = order position 2)
Tempo    : 152 BPM, speed 6  (one pattern row = one 16th note)
Key      : A minor, with harmonic-minor V and the Andalusian descent (Am-G-F-E)
Preview  : preview.wav (one pass through the module, 44.1 kHz stereo)

Form (order position -> pattern)
--------------------------------
 00  00  intro       8th->16th arpeggio build, kick + hats, noise riser
 01  01  intro 2     full groove + tom/snare fill
 02  02  groove      LOOP START: 4-on-the-floor, offbeat stabs, 16th arps
 03  03  theme A     the main hook (lead) + a delayed echo
 04  04  theme A'    hook variation over Am-F-Dm-E + bell counter
 05  05  theme A     full arrangement
 06  06  break       drums out: pad bed, sparse bass, bell melody
 07  15  break 2     bell line rises, arps/bass/hats wake up again
 08  07  build       rising hats, snare roll, noise riser
 09  08  theme B     descending Andalusian theme (Am-G-F-E)
 10  09  theme B'    variation + bell counter
 11  10  double      hook with an octave lead double
 12  11  double 2    theme B with a fifth double
 13  12  climax      doubled hook, densest drums, tom fill
 14  13  outro       groove with the hook once more
 15  14  final       groove + big tom roll + crash  ->  loops back to 02

Sound
-----
All 13 distinct samples are synthesised from scratch with Python/NumPy
(additive synthesis with per-partial damping, FFT-shaped noise, a
state-variable filter for the riser, tanh saturation on kick/lead/stab).
Every tonal sample is written at concert middle C, so pattern notes read
as concert pitch (C-4 = 261.63 Hz) and the module is effectively tuned
to A4 = 440 Hz.  Because this FT2 build exposes no envelopes, amplitude
envelopes, pluck damping, chorus detune and tremolo are baked into the
sample data itself; dynamics, swells, vibrato (E41) and stereo placement
come from the pattern data.

Sources: src/mkall.py  (sample synthesis)
         src/compose.py (the whole arrangement, written as FT2 tool calls)
         src/ft2py.py  (small bridge helper for the FT2 command line tools)
