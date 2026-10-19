# Keygen Storm — an original tracker (keygen) tune

**tune.xm** — FastTracker II module: 10 channels, 18 patterns of 64 rows,
BPM 150, speed 6 (16th-note grid), 115.2 s per loop (1:55).
The song loops from the end of pattern 17 back to pattern 0
(`loop_start = 0`, order length 18). The last pattern stutter-fades to silence
and the loop opens on the same Am chord it ends on, so the seam is
click-free (verified: pass-1/pass-2 waveform correlation 0.99998, sample-to-
sample step across the loop point 0.016).

**preview.wav** — render of `tune.xm` (44.1 kHz, 16-bit, stereo, peak −2 dBFS).

## Music
Key: **A harmonic minor** (the G# of the E7 dominant chord gives the classic
keygen colour). Chord plan per 4-bar pattern:
* main theme:  Am – F – C – E7   (i – VI – III – V)
* drive/peak:  Am – F – Dm – E7   (i – VI – iv – V)
* break:       F  – C – Dm – E7

| pat | section |
|-----|---------|
| 0 | intro: pad + 16th arpeggio + soft bass, opens on Am |
| 1 | intro + bass, hats, bell counter-line, riser |
| 2 | main theme A (hook), crash |
| 3 | main theme A', snare fill |
| 4 | main theme B (lead an octave up) |
| 5 | main theme B' |
| 6 | break: pad + FM bell |
| 7 | break build: snare roll, riser |
| 8 | drive 1 (16th bass, fast arp) |
| 9 | drive 2 |
| 10 | drive 3 (peak), fill |
| 11 | reprise A + plucked counter-melody |
| 12 | reprise B + plucked counter-melody |
| 13 | soft breakdown |
| 14 | build: roll + riser |
| 15 | peak |
| 16 | outro |
| 17 | final build + Am chord, stutter fade into the loop point |

Lead hook (A4 C5 B4 A4 E4 G4 A4 | F5 E5 C5 A4 C5 | G4 A4 C5 E5 D5 C5 |
B4 D5 G#4 F5 E5), doubled a row later an octave up by the FM bell.

## Sound design — every sample is synthesised from scratch in NumPy
* **bass** – looped single-cycle wavetable (pulse + sub, tanh saturation)
* **lead** – looped saw wavetable, 15 harmonics, formant bump on h4/h6
* **arp** – looped bright pulse-ish wavetable, 18 harmonics
* **pad** – looped soft saw wavetable, 12 harmonics, played as 3 voices/chord
* **bell** – one-shot FM bell (2.76 / 5.4 inharmonic partials, 1.6 s tail)
* **pluck** – one-shot decaying harmonic pluck
* **kick** – pitch-swept sine (110→45 Hz) + click
* **snare** – band-passed noise + tuned body
* **hat / open hat** – high-passed noise with metallic partials
* **tom**, **crash**, **riser** – one-shot synthesis
* **stab_am / stab_f / stab_c / stab_e** – one-shot chord stabs, one
  instrument per chord, triggered on every chord change

All pitched samples are generated with a loop frequency that compensates for
the player's pitch ratio, so the module is in tune inside the tracker
(measured: wavetable voices within ~4 cents of equal temperament across
three octaves).

## src/ (reproducible build)
* `synth.py`  – NumPy synthesis of every sample → `samples/*.wav`
* `compose.py`– arrangement: harmony, melodies, drum/bass/arp generators
* `build.py`  – emits the FT2 tool-call batch that builds the module
* `make_all.sh`– `synth → build → module_new → batches → save tune.xm →
  load → render preview.wav` (byte-identical on re-run)
