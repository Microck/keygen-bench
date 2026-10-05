# "Midnight Serial" – original keygen tune (FastTracker II XM)

* **tune.xm**: FT2 XM v1.04, 12 channels, 13 instruments, 14 orders, **restart position 2**,
  140 BPM / speed 6, linear frequency table, A minor. Saved by ft2-clone (`module_save`).
* First pass 1:36. Orders 2–13 (1:22) then loop. The last order ends on E major with the same
  lead pickup as the intro, so the jump back to order 2 resolves V → i with no break.
* **preview.wav**: one pass rendered by ft2-clone at its default settings (44.1 kHz, 16-bit).

| Order | Section | Chords (1 bar each) | What happens |
|---|---|---|---|
| 0 | Intro 1 | Am F C G | soft square arpeggios fade in, supersaw pads, swept noise riser |
| 1 | Intro 2 | Am F G E | four-on-the-floor beat, octave bass, plucked arps, lead pickup |
| 2–3 | A (loop target) | Am F C G / Am F G E | PWM lead hook (3-3-2 rhythm) plus a 3-row echo channel |
| 4–5 | B | Dm G C F / Dm E Am E | circle-of-fifths theme, 16th-gated arps, open-hat offbeats |
| 6–7 | A' | as A | ornamented lead with slides, sidechain-style "pumping" pads |
| 8 | Breakdown | Am F C G | FM bell restates the hook, pads, no drums |
| 9 | Build | Am F G E | snare roll crescendo, porta-swept noise riser |
| 10–11 | A'' | as A | lead with bell doubling an octave below, busier hats |
| 12–13 | B'' | as B | full arrangement, then back to order 2 |

Tracker techniques: arpeggios (0xy), tone portamento (3xx), delayed vibrato (4xy), a noise riser
swept with 1xx and volume-column crescendos, volume-column gating and pumping, pad panning (8xx),
explicit Fxx tempo at the loop target. No envelopes are used. Attack, decay and filter sweeps are
built into the sample data.

## Provenance (originality / IP)
* Every sample is synthesized from scratch in `src/synth.py`: band-limited PWM pulse, pluck
  pulse, resonant saw bass, detuned supersaw with a loop that closes exactly, FM bell, and
  synthesized kick, snare, hats, crash and noise.
  No third-party audio, sample packs or network resources were used.
* Melody, harmony and arrangement were composed for this piece (`src/build.py`).

## Reproducibility and change control
1. `python3 src/build.py out.xm` writes the module. The output is deterministic (fixed RNG seed,
   identical SHA-256 on repeated builds).
2. Load `out.xm` in ft2-clone and save it as `tune.xm`. The render of `tune.xm` is
   sample-identical to the render of `out.xm`.

## Verification performed (scripts in `src/`)
* Levels (`analyze.py`, `bands.py`, `solo.py`): peak 0.85 FS, no clipped samples, DC offset < 0.0002.
  Per-channel level checks show the lead about 5–7 dB above the accompaniment.
* Tuning (`pitch.py`): lead, bass, bell and pad notes measure within ±6 cents of the written notes.
* Loop seam (`seam.py`): rendered the song with orders 2 and 3 appended, which is exactly what
  playback does at the loop. After 1.5 s the looped section is sample-identical to the first pass.
  The level 0.5 s before and after the seam differs by 0.08 dB. All sample loops were checked for
  wrap discontinuities.
* `MANIFEST.sha256` lists checksums of all delivered files.
