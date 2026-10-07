"unlocked" - an original keygen-style chiptune for FastTracker II (XM)

  tune.xm           the module (16 channels, 15 instruments, 10 patterns, 140 BPM / speed 6, loops to position 0)
  tune_preview.wav  render of one pass (68.5 s) made with the ft2-clone renderer
  src/              everything used to build it:
      synth.py      all sample material synthesized from scratch with NumPy (drums, PWM lead, 3-saw pad, pulses, bell...)
      make_tune.py  the composition: harmony, melodies, drum programming, echo/harmony generation, arrangement
      xmwrite.py    small XM writer (envelopes + auto-vibrato are set directly in the instrument headers)
      analyze.py / pitchcheck.py / dump.py / render.sh  verification helpers

Key: E minor (with B7 dominant and a Neapolitan F in the bridge).
Form: intro (2x4 bars) - theme - theme w/ harmony - half-time bridge - build-up - full theme - turnaround into the loop.
