# ASCII DREAMS — a keygen tune

A loop-friendly chiptune/demoscene-style track composed directly as a
FastTracker II (XM) module. Music only, built from first principles:
every instrument is an original waveform synthesized in Python/NumPy
(no borrowed/third-party samples of any kind), then assembled into
patterns and arranged entirely with this FT2 toolset.

## Specs
- Key: A minor, 150 BPM, 4/4 (16 rows/bar, speed 6)
- 12 channels, 12 original instruments, 6 patterns
- Length: ~13 s intro + a ~58 s loop section (repeats forever)

## Instruments (all synthesized from scratch, see `src/synth.py`)
Lead Pulse, Lead Soft, Arp Pluck, Sub Bass, Warm Pad (chorused triangle
stack), Kick, Snare, Clap, Hat Closed, Hat Open, Ride/Perc, Crash —
pulse/saw/triangle waveforms built with additive synthesis (exact
harmonic control via FFT analysis of an oversampled ideal waveform,
then resynthesized at the actual sample rate), plus FFT-shaped noise for the
percussion. All amplitude/decay shaping is baked directly into the
sample data (this FT2 build has no envelopes), and every instrument is
calibrated so that XM note 49 reproduces middle C (261.6256 Hz) to
within a fraction of a cent, so standard equal-tempered pitches apply
across the whole kit.

## Arrangement
`Intro -> Groove A -> Groove B -> Groove A (variant) -> Groove B
(variant) -> Turnaround -> (loops back to Groove A)`

Two 8-bar lead motifs over an Am-F-C-G / Am-Em-F-G progression, a
16th-note arpeggiated chord part, a syncopated bassline, a full drum
kit with fills, gentle delayed vibrato on sustained lead notes, and a
couple of classic chip-style `0xy` arpeggio chord stabs. The
turnaround ends with a breakdown and a rising scale run that lands
exactly on the Groove-A downbeat.

## Looping
The XM "restart position" (song_set `loop_start`) is set to the first
Groove-A pattern, so a player looping on end-of-song skips the intro
and repeats only the groove/turnaround section, forever. The loop
splice was verified sample-accurately (render the loop section twice
back to back and inspect the join): the waveform crosses zero exactly
at the splice with no discontinuity, and the join lands squarely on a
strong downbeat. See `preview_loop_seam_x2.wav`.

## Files
- `tune.xm` — the final editable module (the required submission)
- `preview_full.wav` — one pass through the whole arrangement
- `preview_loop_seam_x2.wav` — the loop section rendered twice in a
  row, to audibly/visually check the seamless loop point in the middle
- `src/` — the Python build scripts (synthesis, music theory, pattern
  generation). Running `python3 build_song.py` from inside `src/` (with the `ft2`
  CLI on PATH) regenerates `tune.xm` byte-for-byte.

Everything here is original and generated entirely offline from the
scripts in `src/`, with no network access and no third-party audio
content, so the whole chain is deterministic and auditable end to end.
