"nightdrive keygen" - original keygen tune, 136 BPM, A minor
=============================================================
FastTracker II module (XM), 12 channels, 9 patterns, 17 instruments.
All samples synthesized from scratch with NumPy (gen_samples.py):
kick/snare/clap/hats/crash (noise+partials), single-cycle chip waves
(bass, sub, 25%-pulse arps), PWM lead with seamless baked loop,
detuned-saw pad with crossfaded loop, FM bell, filtered-noise riser.

Arrangement (order list, pattern length 64 rows, speed 6):
  pos0 P0 intro (arps, sub, bell teaser)
  pos1 P1 drums+bass enter, snare roll
  pos2 P2 full groove        <- LOOP RESTART (header restart pos = 2)
  pos3 P3 verse lead 1
  pos4 P4 verse lead 2 (fill)
  pos5 P2 groove
  pos6 P5 chorus (pads, octave-bounce arps, clap)
  pos7 P6 chorus 2
  pos8 P7 breakdown (bells, pads, ghost-pumped arps)
  pos9 P8 build (riser, snare roll, arp climb) -> loops back to pos2

Tricks: classic 0xy arpeggio chords on two ping-pong panned channels,
faked sidechain pump via per-row volume column, lead echo channel
(+3 rows, detuned, opposite pan), 4xy vibrato on held lead notes,
chromatic bass approach fills, per-sample default panning for stereo.
Loop verified sample-identical (corr 1.0) across the P8->P2 seam.

Build: python3 gen_samples.py && python3 compose.py && ft2 batch build.json
