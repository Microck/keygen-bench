serial dreams — an original keygen tune (FastTracker II XM)
===========================================================

Module:   tune.xm  (10 channels, 16 instruments, 11 positions, 150 BPM, speed 6)
Loop:     song restart position = 2; the last pattern's E7 walk-up + drum fill
          resolves onto the A-minor downbeat of position 2, so it loops cleanly.
Preview:  preview.wav (one full pass; in a player the song then loops from pos 2)

Music:    A minor. Main progression Am-F-C-G; B section + turnaround Am-G-F-E
          with an E7 (G#/D) pull back to Am at the loop point.
          Classic keygen furniture: 16th-note chord-arp plucks with a 2-row
          stereo echo channel, chip-pulse and detuned dual-saw leads with a
          3-row (dotted-8th) echo channel, arpeggio-effect (0x37/0x47) pad
          chords, octave bass, four-on-the-floor kit, break + noise-riser build.

Build:    All sounds synthesized from scratch with NumPy (src/gen.py):
          band-limited pulse/saw single-cycle loops, baked-decay plucks/bass,
          additive bell, sine-sweep kick, filtered-noise kit. No envelopes are
          used; dynamics live in the sample data and the volume column.
          src/compose.py writes every pattern cell through the ft2 tool API;
          src/levels.py bakes mix gains into the PCM so the module renders
          without clipping at default amplification; src/verify.py decodes the
          saved XM and checks all 3,526 cells + sample headers byte-exactly.
