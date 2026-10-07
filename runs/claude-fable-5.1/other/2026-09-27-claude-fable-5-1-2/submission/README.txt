keygen tune - original XM module (FastTracker II format)

  tune.xm            the module (14 channels, 10 patterns, 13 instruments, 150 BPM / speed 6)
  tune_preview.wav   render made with the FT2 tool (default settings)
  src/               NumPy synthesis of every sample (synth.py), the composition (compose.py)
                     and the XM writer (xmwrite.py). Rebuild with: python3 src/compose.py tune.xm

Form (each pattern = 4 bars of 4/4 at 150 BPM, 6.4 s):
  P0 intro (pads, arp, bell motif, riser)          -> played once
  P1 groove in (kick, bass, pluck, pickup run)     <- loop restart position
  P2-P3 main theme A (PWM lead, echo, vibrato/slides)
  P4-P5 bridge (soft lead, chip chord stabs, pluck ostinato, build)
  P6 16th-note solo run over stabs
  P7 breakdown (bell melody, pluck arps, sustained bass, snare roll + riser)
  P8-P9 theme reprise with harmony voice; final bar rolls into the loop back to P1
Key: A minor (Am F C G / Am F Dm E / F G Am Em / F G E).
