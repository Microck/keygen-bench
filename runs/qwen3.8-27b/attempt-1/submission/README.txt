Keygen - original FastTracker II (XM) keygen tune
==================================================

- 150 BPM, 4/4, key of A minor
- Progression: Am - F - C - G (i - VI - III - VII)
- ~89.6 seconds, loops cleanly (Am -> Am)

Structure:
  P0 Intro      (8 bars) pad + arp, bass enters
  P1 Main A     (8 bars) full: drums + bass + sub + arp + pad
  P2 Main B     (8 bars) drums + bass + lead + pad
  P3 Breakdown  (8 bars) lead-focused, sparse drums
  P4 Build       (4 bars) riser + snare roll + rising bass
  P5 Drop       (8 bars) full, open hats
  P6 Main B2    (8 bars) drums + bass + lead + pad
  P7 Outro      (4 bars) pad + bass, resolves to Am

All 10 instruments are original, synthesized from scratch with
NumPy (no external samples):
  Kick, Snare, Hat, OpenHat, Bass (saw pluck), Sub (sine),
  Arp (square pluck), Pad (detuned saws), Lead (saw + vibrato),
  Riser (noise sweep)

Files:
  tune.xm          - the editable FastTracker II module
  preview.wav      - 44.1 kHz render of tune.xm
  scripts/compose.py       - generates the pattern/order JSON
  scripts/gen_samples.py   - synthesizes the drum/bass/arp/pad samples

Note on this FT2 build's pitch model (empirically derived):
  output_freq = sample_freq * 2^((note + relative_note - 89)/12)
  so with relative_note=43, note = 46 + (target_midi - sample_midi).
