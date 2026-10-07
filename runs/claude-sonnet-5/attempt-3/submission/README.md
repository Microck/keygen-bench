# "Keygen Dreams" — original FT2 keygen tune

A loop-friendly, upbeat chiptune in the classic keygen/demoscene style,
built as a real FastTracker II module (`tune.xm`) — instruments and
patterns do the work, nothing is a pre-rendered sample of the whole song.

## Overview
- **Key / progression:** A natural minor, i–VI–III–VII (Am–F–C–G), one bar
  per chord, 4 bars per pattern.
- **Tempo:** 150 BPM, speed 6 (16 rows/bar, 64 rows/pattern).
- **Form:** patterns A, B, A, C in the order list (loop_start = 0), ~25.6s
  per loop. A = main theme, B = energetic variation with an echoed lead
  and high sparkle accents, C = a quieter breakdown that builds back up
  (busier kick/hat + snare pickup) into a clean loop back to A.
- **Channels (8):** kick, snare/clap, hi-hat, bass, chord arpeggio, lead
  melody, sustained harmony pad, and a delayed lead "sparkle" echo.

## Instruments (92 total, all synthesized from scratch with NumPy)
- **LEAD** — soft-edged ~28% duty pulse, bright hook/arpeggio voice.
- **ARP**  — thinner ~16% duty pulse for fast chord arpeggios / pad.
- **BASS** — ~50% duty pulse blended with triangle for a rounder low end.
- **KICK / SNARE / HATCLOSED / HATOPEN** (+ a spare **CLAP** instrument,
  built but unused) — one-shot percussive samples with envelopes and
  (for the kick) a pitch sweep, all shaped directly in the sample data
  (no tracker envelopes used).

Each of the 29 pitches used (A1..A5, natural-minor scale) gets its own
per-pitch instrument per timbre: a single-cycle waveform is generated at
exactly the loop length needed so the tracker's own pitch engine
reproduces the right frequency (verified by rendering + FFT, each note
tuned to within ~0.5% / a few cents).

## How it was made
See `scripts/`: `sounds.py` generates the waveforms, `build_tune.py`
creates every instrument via the FT2 MCP tool, `song_data.py` holds the
chords/bass/arp/melody/drum data, and `arrange.py` writes the patterns
and order list. `calibrate2.py` / `tuning2.py` were used to empirically
verify, for every pitch, an exact (note, relative_note, finetune,
loop_length) combination that reproduces the intended frequency.

`tune_preview.wav` is a rendered preview of one full loop.

## Verification
`verify_notes.py` and `verify_boundaries.py` solo-render every distinct
(timbre, note) combination actually used in the final patterns —
including sustained notes checked at multiple points across their full
hold time — and compare the measured pitch (autocorrelation with parabolic interpolation) against the
target frequency. This caught and fixed two specific (note, loop-length)
pairs that the tracker's pitch engine mis-rendered (an octave/fifth off)
only in certain contexts. `verify_boundaries.py` additionally checks
every pattern-to-pattern transition used by the order list, including
the loop seam (end of the last pattern back to the restart position),
so the note that is still sounding right before the loop and the note
that starts it both measure correctly. Every pitch used in the final
`tune.xm` measures within ~0.5% (a few cents) of its intended
frequency, stable for as long as it is held.
