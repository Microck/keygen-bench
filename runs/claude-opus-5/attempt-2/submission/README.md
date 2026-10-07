# "Neon Keymaker" — original keygen tune (FastTracker II module)

* **File:** `tune.xm` — 12-channel XM module, 18 patterns, 17 instruments, 22 order positions
* **Preview:** `tune_preview.wav` (44.1 kHz / 16-bit stereo, one pass of the song, 2:21)
* **Tempo:** 150 BPM, speed 6 (64-row patterns = 4 bars of 4/4, 1 row = 1/16 note)
* **Key:** A minor (uplifting i–VI–III–VII style harmony)
* **Loop:** song length 22, **restart position 2** — the two intro patterns play once, then the
  track loops seamlessly from the outro turnaround (ends on G) back into the verse (starts on Am).

## Arrangement

| pos | pattern | section | chords |
|----|----|----|----|
| 0–1 | 0,1 | intro: arps + pad, then bass/kick/stabs + fill | Am F C G |
| 2–3 | 2,3 | verse, full beat (+ bell counter-line) | Am F C G |
| 4–5 | 4,5 | theme — main lead melody | Am F C G |
| 6–7 | 6,7 | chorus (big supersaw lead + delayed echo voice) | F G Am Am / F G C E |
| 8–9 | 8,9 | breakdown (pad + bell), then build: 16th hats, snare roll, riser | Am F C G / Am F G G |
| 10–11 | 6,10 | chorus 2 (+ bell octave counter) | F G Am Am / F G C Am |
| 12–13 | 11,12 | bridge | Dm F C G / Dm F E E |
| 14–15 | 13,14 | lead solo (16th runs) | Am F C G |
| 16–17 | 4,15 | theme reprise (+ bell octaves) | Am F C G |
| 18–19 | 6,10 | chorus 3 | F G Am Am / F G C Am |
| 20 | 16 | final chorus (everything + bell octave doubling) | F G Am Am |
| 21 | 17 | outro turnaround → loops back to position 2 | Am F C G |

## Channels

0 kick · 1 snare · 2 hats · 3 crash/clap/tom/FX · 4 bass · 5 arp (left) · 6 arp delay (right)
· 7 stab/pad · 8 pad · 9 lead (left, −6 finetune) · 10 lead (right, +7 finetune) · 11 bell / lead echo

## Instruments

Every sample is synthesised from scratch with NumPy — no external material.

* **Drums** — additive/filtered-noise kick, snare, clap, closed+open hats, crash, tom; FFT-domain
  filtering, soft saturation for loudness, and ~5 ms of pre-delay so the engine's anti-click volume
  ramp does not eat the transients. All play at a native rate of ~44.7 kHz (relative note +41) so no
  resampler images fall into the audible band.
* **Bass** — resonant band-limited saw, 512-frame cycle, bright transient + seamless 4-cycle loop.
* **Arp pluck** — band-limited pulse with per-harmonic exponential decay (highs die first), two
  copies panned hard L/R and finetuned ±5 for a stereo 16th-note delay.
* **Lead** — 5-voice "supersaw": detuned saws whose detune is exactly ±1/128 and ±2/128 of the
  fundamental so a 128-cycle buffer loops phase-continuously; played on two channels with opposite
  finetune/panning, vibrato (4xy) on the long notes.
* **Pad** — same technique, wider detune, heavy harmonic roll-off, 28-cycle fade-in attack.
* **Bell** — inharmonic partial stack with per-partial decay. **Stab** — chip organ used with the
  arpeggio effect (0xy) for minor/major triads.
* **Riser / zap** — swept band-pass noise and pitch-sweep FX for the build and the drop.

## Rebuilding

```
python3 src/mkinstr.py   # writes 8-bit sample WAVs + instr.json (ft2 batch instr.json)
python3 src/compose.py   # writes song.json  (ft2 batch song.json)
```
