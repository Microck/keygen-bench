# Chrome Cathedral: original keygen tune (FastTracker II module)

**Deliverable:** `tune.xm` (FastTracker II module, XM format 1.04; 14 channels, 12 instruments, 37 patterns, 44-bar order list).
**Preview:** `tune_preview.wav` (44.1 kHz, 16-bit stereo, one full pass, 66.0 s), rendered from the saved `tune.xm`.
**Sources:** `source/` (sound design, score, build and verification scripts). `source/build.sh` regenerates `tune.xm` from them.

## Music
- **Tempo / grid:** 160 BPM (XM speed 3, BPM 160). 8 rows per beat, 32 rows per bar, 4/4.
- **Harmony:** A minor (i-VI-III-VII, with V and V-to-i cadences). The C section modulates to D minor.
- **Length:** 44 bars, about 66 s for one pass. The loop region (bars 5-44) is 60 s.
- **Rhythm:** four-on-the-floor kick, backbeat snare, 16th-note closed hats with accents, offbeat open hats, 16th-note bass with octave bounce, 16th-note pluck arps (32nd-note arps in section C).

| Bars | Section | Chords | Content |
|---|---|---|---|
| 1-4 | Intro | Am F C G | pads, arps and bass enter, riser at bar 3, kick enters bar 4 |
| 5-12 | A | Am F C G / Am F E E | full groove, lead hook, harmony from bar 9, snare fill at bar 12 |
| 13-20 | B (breakdown, then build) | F G Em Am / F G C E | drums drop out, lead and pads quieter, bass returns at 15, drums and snare roll build from 16 |
| 21-28 | A' | Am F C G / Am F E E | full groove with second arp layer and harmony, riser at bar 28 |
| 29-36 | C (D minor) | Dm Bb F C / Dm Bb C E | modulated hook, octave-down harmony, 32nd-note arps in bars 33-36 |
| 37-44 | A'' (finale) | Am F C G / Am F E E | full groove, both arp layers, snare roll and riser into the loop |

## Loop
- **Restart position:** order 4 (bar 5). The song plays bars 1-44 once, then loops bars 5-44 indefinitely.
- **Join:** bar 44 ends on E (the dominant) and bar 5 opens on Am with a crash and kick, so the cadence resolves into the restart.
- **Click-free seam:** every sustained note fades to zero before its next note, and any note still sounding at the end of the song is faded at the seam. Drum and pluck tails reach zero before they can be retriggered. The sample step at the seam is 0.0017 of full scale, against a median step of 0.010.

## Sound design (all synthesized in code; see `source/synth.py`)

| # | Instrument | Type | Relative note | Volume | Pan |
|---|---|---|---|---|---|
| 1 | Kick | one-shot | 28 | 52 | 128 |
| 2 | Snare | one-shot | 28 | 46 | 124 |
| 3 | HatClosed | one-shot | 28 | 36 | 186 |
| 4 | HatOpen | one-shot | 28 | 30 | 70 |
| 5 | Bass | looped | 60 | 32 | 128 |
| 6 | Lead | looped | 36 | 24 | 112 |
| 7 | Lead Harm | looped | 36 | 20 | 150 |
| 8 | Pluck16 | one-shot | 28 | 42 | 88 |
| 9 | Pluck32 | one-shot | 28 | 36 | 168 |
| 10 | Pad | looped | 36 | 22 | 128 |
| 11 | Riser | one-shot | 28 | 34 | 128 |
| 12 | Crash | one-shot | 28 | 34 | 128 |

- Looped voices use band-limited cycles: a saw for the bass (1024-sample cycle), a soft square for the lead (256 samples), a detuned saw for the harmony (257 samples, about 7 cents flat), and a triangle for the pads (256 samples).
- One-shots are kick (pitch-drop sine with click), snare (tone plus band-passed noise), closed and open hats, a riser, a crash, and two plucks (16th and 32nd).
- The module contains no envelopes. Dynamics come from sample shapes and tracker volume effects (A0F fades and volume-column values).

## Verification (`source/verify.py`, all PASS for the submitted file)
- Restart position, length, speed, BPM and channel count match the score.
- All 12 instrument samples are bit-exact against the synthesis output, including loop flags, relative note, volume and pan.
- All 16,576 pattern cells (37 patterns x 32 rows x 14 channels, of which 3,831 are filled) match the score: note, instrument, volume column and effect. The order list matches the arrangement.
- Rebuilding from `source/` reproduces `tune.xm` byte for byte (same SHA-256).
- Preview: peak 0.892, no clipped samples, RMS -15 dB (about 0.17).

## Reproduce
```
sh source/build.sh /absolute/path/to/tune.xm   # needs the ft2 bridge; writes batches/, saves, verifies
python3 source/verify.py /absolute/path/to/tune.xm
```

## Caveats
- The lead's effective note range is limited to 118 (note plus relative note). Above that this FT2 build goes silent, so loops are 256 samples with relative note 36 (1024 for the bass, which stays under 107).
- Tuning: C-4 is 261.34 Hz (A4 about 439.5 Hz, 2 cents flat of 440). The harmony voice is deliberately 7 cents flat for a chorus effect.
- The preview comes from the FT2 renderer in this sandbox. A different renderer or interpolation setting may change fine detail, but not the notes, timing or loop.

## Provenance and compliance
- **Originality / IP:** no third-party samples, loops, recordings, or melodies. The waveforms and noise are computed in `synth.py` from sine, noise, and filter math with fixed seeds. The melodies and patterns were written for this tune in `compose.py`. The i-VI-III-VII progression is a common harmonic framework, not protected expression.
- **Integrity:** `SHA256SUMS.txt` lists hashes for the deliverables and sources. The rebuild check above shows the same inputs give the same bytes.
- **Auditability:** `source/batches/` holds the exact FT2 calls used to build the module, `source/manifest.json` the score summary, and `DECISIONS.md` the decision and defect log.
- **Data handling:** offline build, no network access, no personal data. The XM file is data-only (no scripts or macros).
