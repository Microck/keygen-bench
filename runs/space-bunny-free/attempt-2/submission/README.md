# NEON LICENCE — an original keygen tune

A FastTracker II XM module: **16 patterns, 12 channels, 15 instruments, 3601 note
events, 1:42 at 150 BPM** (16 rows per bar, speed 6, restart position 0 so it
loops straight back into the intro).  All sound comes from the instrument
samples played by the pattern data — there is no baked-in audio in the module.

## Files
| file | what it is |
|---|---|
| `tune.xm` | the module (the deliverable) |
| `preview.wav` | one pass rendered by the tracker (102.4 s, stereo, 44.1 kHz) |
| `gen_samples.py` | synthesises the 15 original instrument samples with NumPy |
| `music.py` | musical material: chords, arpeggio/bass/drum patterns, melodies |
| `xmwrite.py` | minimal XM (v1.04) writer used to emit `tune.xm` |
| `tune_build.py` | the arrangement — turns the material into the 16 patterns |
| `analyze.py`, `rw.py` | render analysis helpers used to check the result |

Rebuild: `python3 gen_samples.py && python3 tune_build.py`

## Key / harmony
A minor.  Main cycle **Am – F – C – G**; a darker variant **Am – Dm – E7 – Am**
for theme A's later statements and for theme B; a chromatic bridge
**Dm – B♭ – F – E7**.

## Form (64 bars)
| bars | section | content |
|---|---|---|
| 0–3   | A   intro | 16th-note arpeggio alone, rising to an arpeggio run; pad and sub creep in |
| 4–7   | A2  | driving 16th bass + kick/snare/hat, fill at the end of bar 4 |
| 8–11  | B   | **theme A** enters on the pulse lead |
| 12–15 | B2  | theme A answered (A♭-free variation), chord stabs |
| 16–19 | B3  | theme A over Am–Dm–E7–Am, tom fill |
| 20–23 | C   | **theme B** on the pluck |
| 24–27 | C2  | theme B doubled an octave up on the lead, bells |
| 28–31 | D   | breakdown: pad + slow arpeggio |
| 32–35 | D2  | breakdown with the pluck melody and half-note bass |
| 36–39 | E   | build: warm arpeggio, bass, drums, rising run into the peak |
| 40–43 | F   | peak: theme A, full band |
| 44–47 | F2  | theme A + octave pluck doubling, stabs, tom fill |
| 48–51 | G   | theme B with the full band |
| 52–55 | H   | chromatic bridge over Dm–B♭–F–E7 |
| 56–59 | I   | climax (theme A3) ending in a snare roll |
| 60–63 | J   | outro strips back to the intro arpeggio |

The last row of the module is empty, so the loop point falls in silence: the
outro's final bar is thinned out (arpeggio stops at row 11, one long bass note)
and the intro's first arpeggio note lands exactly on the loop point.

## Instruments
`PULSE LEAD` (25 % pulse, two detuned copies), `PULSE ARP` (12.5 % pulse, 125 ms),
`WARM ARP` (50 % pulse), `SAW BASS` (saw + sub, soft clipped), `SUB`, `KICK`
(pitch-swept sine + click), `SNARE` (noise band + tuned body), `HAT CL`, `HAT OP`,
`TOM`, `PAD L` / `PAD R` (three detuned saws through a 3.8 kHz one-pole, hard
panned), `PLUCK`, `STAB`, `BELL` (five inharmonic partials with per-partial
decays).  Every sample is synthesised from scratch with additive/Fourier
band-limited waveforms and filtered noise, normalised and tuned so C-5 sounds
at C-5.

## Mixing
12 channels with per-instrument panning; the arpeggio sits right, the warm arpeggio
and pluck left, the pad is split hard L/R, so the breakdowns are wide while the
lead/bass stay centred.  Rendered peak −3.6 dBFS, no clipping.

## Note on tuning
The tracker this module was produced with computes sample periods from a table
offset by 16¾ semitones, so every instrument carries `relative note = +16` and
`fine tune = +96/128`, which makes the note numbers sound at their real pitch
there (verified to within ±0.2 cents across the range).  In a renderer with the
standard XM period table those two header fields should both be 0 instead.
