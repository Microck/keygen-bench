# "Crimson Serial" (original keygen tune, FastTracker II XM)

* **File:** `tune.xm` (XM 1.04, saved by the FT2 clone itself), 12 channels, 20 instruments, 14 patterns
* **Tempo:** speed 6, 140 BPM, 4/4, 64-row patterns (4 bars each)
* **Key:** A minor (harmonic-minor V chord, E major)
* **Length:** 95.9 s on the first pass. After the last order position (13) it
  wraps to **restart position 1**, so each loop is 89 s.
* **Preview:** `preview.wav` is the default FT2 render (44.1 kHz/16-bit), one pass, no clipping (peak 0.87, about -17 dBFS RMS in the full sections)

## Arrangement (order list = patterns 0..13)
| pos | section | chords (1 bar each) | what happens |
|---|---|---|---|
| 0 | Intro | Am F Dm E | pads swell in, PWM arps fade in, bell plays the theme as a music box, hats, bass and riser come in |
| 1 | Groove (loop target) | Am F Dm E | full drums, octave bass, arps with stereo echo, riser, snare fill |
| 2-3 | Theme A | Am F C G / Am F Dm E | PWM lead plus a dotted-8th echo (left), tom fill |
| 4-5 | Theme B (chorus) | F G Em Am / Dm G C E | 16th arps, rolling bass, open hats, pumping pads, lead glides |
| 6-7 | SID solo | Am G F E (x2) | bright square solo in 16th runs, echo on the right, tom fill |
| 8-9 | Breakdown, then build | F G Am Am / F G E E | bell arps, soft lead with a long echo, then snare/kick roll and riser, short pause before the drop |
| 10-11 | Theme A again | as 2-3 | the bells add a 3-against-4 counter-figure |
| 12-13 | Theme B again | as 4-5 | lead harmony a third below on the right, big fill, then back to pos 1 |

Channels: 0 kick, 1 snare/toms, 2 hats, 3 bass, 4 arp L, 5 arp echo R, 6 lead,
7 lead echo, 8 counter (bell/harmony), 9-10 pad L/R, 11 crash/riser.

## Sound design
Every sample is synthesized from scratch in `src/sounds.py` with NumPy and a fixed seed. No
third-party audio is used. Envelopes and key maps are off, so all shaping is
baked into the sample data and done with pattern effects:
* tonal waveforms are additive and band-limited, with integer-period loops
  (128 samples at relnote +24, or 256 at +36). PWM, detune and chord voices are
  periodic over the loop, so the loops are seamless;
* pluck decays (arp, bass filter sweep, lead accent) sit in the part before the loop, and the
  sustain lives in the loop;
* the pad chords are chord samples (minor/major) with 3 detuned voices per tone,
  two independently generated copies hard-panned for width;
* drums are synthesized one-shots: sine-sweep kick, tone plus noise snare, metallic hats,
  crash, tom, filtered-noise riser;
* the pattern effects used are arpeggio 0xy, vibrato 4xy, tone portamento 3xx, volume
  slides A0x, volume-column slides for sidechain-style pumping, and key-off.

## Rebuild / verify
```
sh src/build.sh          # make_tune.py -> FT2 load/save -> preview.wav -> loop check -> SHA256SUMS
```
* `src/make_tune.py`: composition, arrangement and mix (per-channel gains plus master headroom)
* `src/xmwrite.py`: a small XM writer. FT2 loads its output and re-saves it as `tune.xm`
* `src/analyze.py`: level, clipping and band-balance report for a render
* `src/loopcheck.py`: renders the order `[0..13, 1, 2]` to check the wrap. After the jump
  back, pattern 1 matches its first pass bit for bit from row 4 on. Rows 0-2 differ only by
  the natural decay tails of the preceding fill.

## Engineering controls (traceability and integrity)
* **Deterministic:** the same scripts produce the same module bytes, with a fixed RNG seed and no
  network access or external inputs.
* **Integrity:** `SHA256SUMS` lists the hashes of `tune.xm` and `preview.wav` as built.
* **Verification:** each build checks the round trip (my XM, then FT2 save, then reload and
  render), checks for clipping, and checks the loop seam.
* **Data:** the module contains music data only, with no personal or confidential data and no
  executable payloads.
