Crackme Anthem  --  an original keygen/cracktro chiptune in FastTracker II XM format
================================================================================

* 10 channels, 10 patterns (64 rows each), 40 bars, ~57 seconds per pass.
* Loops cleanly from order position 1 (the intro plays once, the body loops).
* Tempo 140 (XM), speed 5  ->  16th-note rows at ~168 BPM.

Instruments (all samples synthesised from scratch in Python, band-limited):
  KICK / SNARE / HAT closed+open / CRASH / TOM / SWEEP riser   (one-shots)
  STAB  (transposable root+fifth+octave chord stab)
  BASS  (saw+square+sub sine chip bass, seamless loop)
  ARP   (25% pulse with slow PWM sweep, seamless loop)
  PAD   (detuned "fifth pad", seamless loop)
  LEAD  (detuned pulse pair with baked-in vibrato, seamless loop)
  SUB   (pure sine sub bass for the break, seamless loop)

Structure:
  P0 intro      | P1 theme A (no lead) | P2 theme A + melody 1
  P3 A' + melody 2 (G# turnaround) | P4 B-section + melody 3
  P5 break (sub bass, pad, sparse drums, riser) | P6 theme A + melody 5
  P7 B' + melody 3 octave echo | P8 climax (higher registers, stabs)
  P9 outro (melody 1 variant, long ring-out) -> loops to P1

Harmony: A minor. Am-F-C-G / Am-F-G-E / Dm-Am-E-Am / C-G-Am-F.

Files:
  tune.xm       the module (editable in FastTracker II)
  preview.wav   one full pass rendered at 44.1 kHz 16-bit stereo
  src/          Python sources that generate the samples and the module
  samples/      the generated 16-bit instrument WAVs

Reproduce:  python3 src/make_samples.py && python3 src/build.py
