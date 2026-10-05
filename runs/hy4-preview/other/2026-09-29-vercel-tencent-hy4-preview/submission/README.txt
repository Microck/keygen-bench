KEYGEN DRIVE  v1.0  -- FastTracker II XM module
===============================================
Format : XM, 14 channels, 13 instruments, 12 patterns, 64 rows each
Tempo  : 148 BPM / speed 6, song loops from the restart position (order 0)
Length : 47 bars, ~77.8 s (looping)

Instruments (all raw-synthesised in numpy, no external samples):
 1 Pulse Lead      - band-limited pulse wave (duty 0.28) character of the 16th arps
 2 Lead Echo       - narrower pulse, delayed copy of the lead (panned right)
 3 Saw Pluck       - soft band-limited saw for offbeat chord stabs
 4 FM Bell         - additive bell (partials 1 / 2 / 3.01 / 4.2 / 5.4 / 6.8) for the melody
 5 Sub Saw Bass    - sine-weighted saw with sub octave
 6 Saw Pad         - 6x detuned saw ensemble, swell envelope (retriggers every bar)
 7 Kick            - pitch-swept sine + click
 8 Snare / Clap    - three burst clap + snare body, soft-saturated
 9 Closed Hat, 10 Open Hat, 11 Zap Perc, 12 Ride Tick  - filtered noise, saturated
13 Bell Harmony    - same bell material, harmony line a diatonic third below the melody

Arrangement (every pattern = one 4 bar cycle of | Am | F | C | G | in A natural minor):
  P0  intro      pad + sparse offbeat arp
  P1  groove     + kick, bass and hats
  P2  main       theme A enters with bell harmony
  P3  variation  bouncing arp, 16th hats, ride
  P4  variation  theme B, skip arp, octave bass
  P5  main       theme A, snare roll fill
  P6  breakdown  no drums, sparse arp, bass returns in the second half
  P7  build      hats and drums escalate into a snare roll
  P8  drop       full groove, theme A
  P9  variation  theme B, grooving arp, 16th bass
  P10 variation  walking arp, theme A
  P11 outro      drums thin out, loops back into the intro

Scripts: gen_samples.py (synthesises the WAV instruments), build.py (composes the
patterns and writes the XM batch), analyse tools measure per-channel levels of the
render to balance the mix.  preview.wav is rendered straight from tune.xm.
