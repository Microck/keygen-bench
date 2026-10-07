NEON CITADEL - original keygen tune for FastTracker II
======================================================

Module : submission/tune.xm   (16 channels, 17 patterns x 64 rows, BPM 140, speed 6,
                               global volume 64, song loop position 0 -> loops cleanly)
Length : 116.5 s (one pass of the song; the module is written to repeat forever)
Key    : A minor (A natural / harmonic minor: the E major chord supplies the G# leading tone)
Feel   : driving 4/4 "turbo" keygen EBM - four-on-the-floor kick, off-beat acid bass,
         saw-stack lead with baked vibrato, 16th pluck arps, warm pads, bell counters.

Everything you hear is synthesised from scratch (tools/synth.py, NumPy): additive
band-limited saw stacks, an in-line resonant filter sweep for the acid bass, FM for
the bell/tom, filtered noise for the drums.  Because this build has no volume
envelopes, every ADSR is baked into the sample data, and each sample's pitch/time
base is pre-warped so that its reference note plays back exactly as designed
(the engine's sample root note is the label C-5).

Instrument list (14):
  01 KICK D909   02 CLAP HD     03 HAT C    04 HAT OPEN   05 CRASH   06 TOM FM
  07 RISE FX     08 ACID BASS   09 SUB BAS  10 KEY LEAD   11 SAW STAB
  12 FP2 PLUCK   13 BELL CALL   14 PAD WARM

Channel map:  0 kick | 1 clap | 2 closed hat | 3 open hat | 4 acid bass | 5 sub bass
              6-7 pluck arpeggios | 8 lead | 9 third-above harmony | 10-11 pads
              12 chord stabs / pad fifth | 13 bell counter-melody | 14 toms | 15 FX

Arrangement (each pattern = 4 bars):
  P0  intro       Am  F  G  E   pad + soft arps + bell preview of the hook + riser
  P1  build       Am  F  G  E   kick/clap/hats, 8th bass, 16th arps, lead pickup
  P2  theme A     Am  F  G  E   main lead statement, drive bass
  P3  theme A'    Am  F  G  E   variation, 3rd harmony, tom fill + scale run
  P4  theme B     Dm  Am F  E   answering phrase, gallop bass, echo arps
  P5  theme B'    Dm  Am F  E   harmony added, snare roll into the breakdown
  P6  breakdown   Am  G  F  E   no drums: pads, sub, bell melody, riser
  P7  rebuild     Am  G  F  E   bell answer phrases, accelerating roll, crash
  P8  chorus      Am  F  G  E   hook restated, off-beat bass, chord stabs
  P9  chorus 2    Am  F  G  E   + third harmony, hat roll / run fill
  P10 lift        F   G  C  Em   new melody, 16th bass
  P11 lift 2      F   G  C  Em   harmony in 6ths, roll into the bridge
  P12 bridge      Am  G  F  E   half-beat groove, tom run, lead calls
  P13 finale      Am  F  G  E   climax melody an octave up + pluck sparkle + harmony
  P14 finale 2    Am  F  G  E   cadence, sub, crash, hat roll
  P15 outro       Am  F  G  Am  drums drop out, held lead, arps
  P16 tail        Am  F  G  Am  bell fragment, pads dying away, riser -> loops to P0

Files:
  tune.xm              the module (submit this)
  tune_preview.wav     44.1 kHz stereo render of one complete pass
  src/synth.py         sample synthesis (run first, writes samples/*.wav)
  src/song.py          tracker composition: patterns, order, emits the FT2 tool batch
  src/wav.py anal.py   render analysis helpers used while mixing
