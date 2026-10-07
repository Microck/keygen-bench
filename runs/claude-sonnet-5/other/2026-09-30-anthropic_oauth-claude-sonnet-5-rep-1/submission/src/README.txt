KEYGEN GROOVE - source notes
=============================
tune.xm is an 8-channel FastTracker II module built entirely from
numpy-synthesized samples (no external audio used).

Instruments (all generated in synth.py):
  1 Kick         - pitch-swept sine + noise click, one-shot
  2 Snare        - noise + tone burst, one-shot
  3 HihatClosed  - double-differentiated noise, short decay
  4 HihatOpen    - same noise, longer decay (also reused pitched down
                   as an "open hat swell" in the outro)
  5 Clap         - layered noise bursts with slight delays
  6 Bass         - 32-sample looped soft sawtooth wavetable
  7 Lead         - 32-sample looped 25%-duty pulse wavetable
  8 Pad          - 32-sample looped sine+harmonics wavetable (chords)
  9 Lead2        - 32-sample looped bright triangle (counter-melody)

Arrangement (order list, 150 BPM, speed 6, loop_start = position 1):
  0 Intro   (4 bars) - pad chords, then bass, then drums build up
  1 Main A  (4 bars) - full groove, Am-F-C-G, straight arpeggio lead
  2 Main B  (4 bars) - same progression, syncopated lead + counter-melody
  3 Main A  (repeat)
  4 Main B  (repeat)
  5 Outro   (2 bars) - strips back down, ends on G (dominant) with an
                       open-hat swell that resolves into Main A (Am)
                       when the song loops from loop_start (position 1),
                       giving a clean, musical loop back into the groove.

compose.py generates every pattern_set_cell call (notes, volumes, and
channel panning) as a single JSON batch consumed by `ft2 batch`.
synth.py contains all waveform/drum synthesis. The *_flags fix scripts
correct the XM sample "16-bit" flag bit that must stay set alongside
the loop-type bits when calling sample_set.
