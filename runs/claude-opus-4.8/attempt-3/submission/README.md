# "KEYGEN A-MINOR" — an original keygen tune (FastTracker II / XM)

Uplifting melodic chiptune-trance keygen loop, composed from scratch.

## Musical facts
- Key: A minor.  Tempo: 140 BPM (FT2 speed 6, 16 rows = 1 bar).
- Chord loop: Am – F – C – G  (i – VI – III – VII), one chord per bar.
- Format: 10-channel XM, 8 patterns of 64 rows (4 bars each).

## Arrangement (order 0..7, restart/loop position = 2)
- P0  Intro      : pad + sweeping arpeggio (atmosphere)
- P1  Build      : + four-on-floor kick, 16th hats, octave bass, riser
- P2  Main A     : full groove + lead melody A (+ crash on the drop)
- P3  Main A'    : lead A with an end-of-phrase lift
- P4  Break      : drums/bass drop out; pad + arp + sparse lead + riser
- P5  Main B     : climax, higher lead melody B
- P6  Main B'    : lead B variation
- P7  Pre-loop   : groove + snare fill that leads back to the restart
Intro (P0–P1) plays once; the body (P2–P7, 24 bars) loops forever.
Every pattern is a complete Am–F–C–G cycle, so the end (G + fill) always
resolves cleanly into the restart (Am + crash).

## Sound design (all synthesized with NumPy, no external samples)
Instruments are baked as one-shot 44.1 kHz samples with amplitude envelopes
and loaded into FT2 (`sample_load`):
- bass : band-limited saw+square+sub, soft-clipped
- lead : two detuned saws + pulse; played with a stereo ping-pong delay
- arp  : bright narrow pulse, ping-pong panned, wide up/down sweep
- stab : saw+square chord hits   | pad: additive warm pad
- kick : pitch-swept sine + click | snare/clap/hats/crash/riser: shaped noise

Stereo: ping-pong arpeggio, ping-pong lead delay, L/R pad & stab spread.

## Files
- `tune.xm`      — the editable module (this is the deliverable)
- `preview.wav`  — rendered preview
- `src/synth.py` — instrument/sample synthesis
- `src/compose.py` — pattern/arrangement generator
