neon cascade - keygen
=====================
An original FastTracker II module written for looping playback.

  tune.xm             the module (18 channels, 15 patterns, 21 instruments)
  tune_preview.wav    44.1 kHz stereo render of one full pass (128 s)
  synth.py            DSP helpers (filters, additive wavetable builders)
  instruments.py      builds all 21 samples from scratch with NumPy
  compose.py          harmony, patterns, arrangement -> writes the module
  loadins.py          loads the generated samples into FT2

Music
-----
D natural minor, 142 BPM, speed 6, 64-row patterns (16th-note grid).
Chord cycles:  A = Dm - Bb - F - C      (verse / groove)
               B = Bb - F - C - Dm      (chorus, resolves onto the tonic)
               C = Gm - Dm - Bb - C     (break / bridge)
               E = Bb - F - C - C       (final turnaround into the loop)

Arrangement (19 positions, restart position 3):
  0-2   intro: pad and pluck, arpeggio enters, four-on-the-floor build
  3-6   groove A, lead melody, two chorus hooks
  7-8   break on Gm, second build with a snare roll
  9-13  groove variations, harmonised chorus, bridge
  14-18 16th-note solo, reprise, final chorus that turns around to Dm

Looping
-------
Restart position 3 skips the intro, so the loop body is positions 3-18
(108 s). The final pattern ends on C, the dominant preparation for the Dm
that opens position 3, so the harmony closes the circle. Voices that are
not retriggered at the loop point are faded with Axx and cut on the last
row, leaving a sample-level step of ~250 LSB against a ~9500 LSB typical
inter-sample delta, i.e. no audible click at the wrap.

Sound design
------------
Every sample is synthesised in NumPy, all 16-bit.
  drums     analytic kick (pitch-swept sine + click + beater band), snare,
            ghost snare, clap (4 taps), closed/open hats, crash, tom,
            reverse-noise riser and a downsweep.
  tonal     single-cycle-derived wavetables with a non-looping "head"
            region whose spectrum morphs into a steady looping tail, so
            each note has an attack transient without needing envelopes.
            Bass, sub, arp, lead, pad, pluck and stab are built this way.
Stereo comes from paired L/R instruments that are panned apart and
finetuned a few cents against each other, plus a stereo-canon arpeggio
and a two-tap lead delay on its own channel pair.

Because this FT2 build exposes no envelopes and no note-to-sample mapping,
all shaping lives in the sample data and in pattern effects (Axx volume
slides, 4xx vibrato, ECx cuts, EDx delays, Cxx volume).
