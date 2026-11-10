# Prime Number Party — an original keygen-style chiptune (FastTracker II XM)

`tune.xm` is the deliverable: a 16-channel XM module, 147 BPM / speed 3
(8 rows per beat), F# minor, 30 patterns of 64 rows (2 bars each),
about 98 s per pass. Music only — the "keygen" in the brief is the
*musical genre* (demoscene chiptune); nothing here generates, checks or
circumvents software licences.

| file | what it is |
|------|------------|
| `tune.xm` | the editable module (written by the FT2 clone itself: `module_load` → `module_save`) |
| `preview.wav` | one pass rendered by the same FT2 clone with default settings (44.1 kHz / 16 bit) |
| `loop_seam_demo.wav` | the 8 bars around the loop point (last 4 bars → first 4 bars at the restart position), cut from a render that really plays through the loop; the demo file alone gets a 10 ms fade-in and a short fade-out at its cut ends |
| `build_report.json` | mix statistics and the loop check written by the build |
| `src/synth.py` | every sample, synthesised with NumPy from maths + a fixed-seed RNG |
| `src/xmlib.py` | small XM container writer |
| `src/compose.py` | the composition / arrangement (patterns, effects, mix) |
| `src/make_submission.py` | one-command deterministic rebuild + checksums |
| `MANIFEST.sha256` | SHA-256 of every shipped file |

## Form and loop

    order 0-1   intro (4 bars, heard once: hook hinted on a soft square lead)
    order 2-5   A   main theme, break-beat groove, ping-pong arps      <- restart position
    order 6-9   A2  theme with mordents, harmony, pluck sequencer
    order 10-13 B   half-time bridge, square lead with glides, pads
    order 14-17 C   chorus: four-on-the-floor, rising hook, high arps
    order 18-21 D   16th-note arpeggio solo (twin-lead harmony in its second half)
    order 22-25 BR  breakdown and two-bar build
    order 26-29 C2  final chorus (harmony voice, driving bass) -> turnaround into A

The song restart position is order 2, so the intro plays once and the body
(A … C2, 56 bars) repeats. The loop is made clean on purpose:

* the last bar is a dominant (V) turnaround with a tom fill and a melodic
  run that resolves onto the first note of A;
* the final row of the song *and* the final row of the intro cut every
  channel on the last tick (`EC2`), so both ways into A start from the same
  silent channel state, and a one-pass render ends on digital silence
  (first and last frame are 0 — no click whether the module or the WAV is looped);
* echoes never spill across the loop entry; tempo/speed never change.

Verified by the build (`build_report.json`): playing intro + body + body
straight through the loop point, the second pass matches the first to
within 2 LSB, i.e. every pass of the loop sounds the same as the first.

## How the sounds are made (no envelopes, no key-maps)

Each instrument is a single sample whose shape is baked into the PCM:
PWM lead with a duty-sweep attack and a long PWM loop, hollow square lead,
25 % / 12.5 % pulse loops for `0xy` arpeggios, decaying pulse pluck,
saw+square bass with a baked resonant filter "pluck", triangle bass,
detuned three-saw pad, and synthesised kick / snare / clap / hats / crash /
toms / reverse swell / zap. Dynamics and articulation are tracker work:
volume column, arpeggio `0xy`, vibrato `4xy`, tone portamento `3xx`
(glides and legato mordents), `E2x`+`1xx` scoops, held notes that dissolve
into a `0xy` chord, note cut `ECx`, a dotted-8th / dotted-quarter stereo
delay (6 and 12 rows) played by two extra channels, left/right ping-pong arps, and beat-synced volume
"pumping" on the pad.

## Mix facts (FT2 clone, default amp)

sample peak ≈ 0.87 (-1.2 dBFS), 4x-oversampled true peak ≈ -1 dBTP,
0 full-scale samples, RMS ≈ -15.6 dBFS, DC ≈ 0.

## Provenance and controls (SOC 2 / ISO 27001 context)

* **Original work, traceable origin** – melody, harmony, arrangement and all
  PCM data were created in this workspace from the included source; no
  third-party samples, modules or code, so there is no licence or
  supplier exposure to track.
* **Reproducible and integrity-checked** – the build is deterministic
  (fixed RNG seed, no clock or host input); `MANIFEST.sha256` lets a
  reviewer confirm the shipped files match a rebuild.
* **No sensitive data** – the module, WAV and sources contain no personal
  data, credentials, hostnames or environment details; instrument-name
  text is limited to a short description of the tune.
* **Contained** – built offline with only the provided tools, inside the
  workspace; the deliverables are data plus plain-text Python.

Rebuild: `python3 src/make_submission.py` (needs the `ft2` tool and NumPy).
