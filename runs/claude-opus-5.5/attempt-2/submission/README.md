# Serial Lights — original keygen tune (FastTracker II XM)

Deliverable: `tune.xm` (FT2 Extended Module, saved by the FT2 build in this workspace).
Optional companions: `preview.wav` (one pass, 44.1 kHz/16-bit stereo, rendered by FT2's renderer), `src/` (build scripts), `MANIFEST.sha256` (integrity hashes).

## Module facts
| Item | Value |
|---|---|
| Format | XM v1.04, linear frequency table |
| Channels / patterns / instruments | 12 / 14 / 16 (one 16-bit sample each) |
| Tempo | 140 BPM, speed 6 (one row = a 16th note) |
| Song length | 14 orders × 64 rows ≈ 1:36 per pass |
| Restart position | order 2 (theme A), so the intro plays once and the loop goes from A2x back to A1 |
| Key | A minor (harmonic-minor E at cadences), middle section in C major |

## Arrangement (order: section, chords per bar)
0 intro1 (Am F C G) pad fades in, pumping arps, hats ·
1 intro2 (Am F Dm E) kick, bass, a soft pluck previews the hook, riser + snare roll ·
2–3 A1/A2 main hook (PWM lead + dotted-8th echo, gated arps, octave bass) ·
4–5 B1/B2 (F G Em Am / F G Dm E) long lead notes with slides, offbeat bass, open hats ·
6–7 A1h/A2h hook + harmony a third below ·
8–9 D1/D2 (C G Am F / C G F E) second theme in the relative major ·
10 C1 (Dm Am F C) breakdown: half-time drums, 16th pluck riff with echo ·
11 C2 (Dm Am Bb E) build: lead, riser, rolling snare ·
12–13 A1x/A2x final hook with harmony, octave-down square double, pad, rolling bass → loops to order 2.

## How the sound was made (provenance)
Every sample was synthesized from scratch in `src/samples.py` (additive band-limited
waveforms, plus noise from NumPy's seeded generator). No third-party samples, loops or code
were used, and the workspace had no network access. This FT2 build has no envelopes, so the
amplitude and brightness shapes are part of the sample data. The acid bass is a run of
filter-swept cycles that ends in a loop, the soft pluck has its decay built in, and the PWM
lead is a 192-cycle duty sweep. Patterns and effects handle articulation: arpeggio 0xy,
vibrato 4xy, tone portamento 3xx, porta-up risers 1xx, retrigger E9x, and key-off.

## Reproduce
`src/make_submission.sh` builds the samples, writes the XM, loads and re-saves it through FT2
(`module_load` → `module_save`), renders the preview and writes the hashes. The build is
deterministic because the RNGs are seeded.

## Checks performed
* Render at default settings: peak about -1.2 dBFS, no clipped samples.
* Loop test (`src/looptest.py`): a copy of the song with the restart patterns appended was
  rendered. After the first row, the second pass of A1/A2 matches the first pass sample for
  sample, so no voices hang over the loop point.
* Harmony scan (`src/harmcheck.py`): the only clashes are short passing tones.
* The XM saved by FT2 renders identically to the generated XM.
