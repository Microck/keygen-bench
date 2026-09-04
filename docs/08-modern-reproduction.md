# Modern legal reproduction workflow

This chapter reconstructs the music-production method without using protected scene binaries, copyrighted modules, or license-bypass code.

## Choose the target format first

### FT2-like result

Use MilkyTracker and save XM. It provides an FT2-style workflow, instruments and envelopes, sample editing, generators, and module cleanup.

### ProTracker-like result

Use MilkyTracker's ProTracker modes or `pt2-clone` and save a conservative four-channel MOD.

### IT/S3M or broader inspection

Use OpenMPT and save with compatibility constraints appropriate to the intended replay engine.

## Define a byte budget

Set separate budgets for module data, replay code, and the rest of the application. Avoiding long stereo recordings forces the reuse-oriented techniques that shaped tracker music.

## Build a lawful sample palette

| Role | Construction |
|---|---|
| Kick | Short synthesized sine sweep with a click transient |
| Snare | Short noise burst plus a pitched body |
| Hi-hat | Very short high-passed noise |
| Bass | One-cycle or few-cycle saw/square-like loop |
| Lead | Bright looped waveform with envelope/vibrato |
| Chord | Original sampled chord or layered waveform |
| Effect | Original noise sweep or short impact |

Trim silence, convert to mono where practical, and use the lowest sample rate and bit depth that still serve the sound.

## Tune and loop

For sustained waveforms:

1. find a stable cycle;
2. set a forward loop;
3. remove DC offset where possible;
4. tune the base note;
5. test across the intended pitch range;
6. listen in the target replayer, not only the editor.

## Compose patterns

A compact arrangement can use drums, syncopated bass, a short melodic hook, a counterline, arpeggio for implied harmony, portamento, vibrato, retrigger, and note-cut effects.

## Design a seamless loop

Example order list:

```text
00 intro
01 main A
02 main B
01 main A
03 variation and turnaround
```

Test for hanging notes, envelope discontinuities, delay tails, effect-memory surprises, tempo resets, and clicks at the seam.

## Optimize

- delete unreachable patterns;
- remove unused instruments and samples;
- crop sample tails;
- shorten loops;
- convert stereo samples to mono if appropriate;
- downsample cautiously;
- remove unsupported effects;
- use compatibility export;
- inspect final header/count metadata.

## Test with more than one player

At minimum compare the authoring tracker with the intended runtime player. libopenmpt or libxmp can provide an independent modern reference.

## Inspect metadata

```text
python tools/module_probe.py path/to/song.xm
```

The script reports format, title, selected header fields, file size, and SHA-256. It does not identify a composer or runtime player.

## Rights and provenance

Record sample licenses, composition authorship, tracker/version, export tools, replay library, and hashes of final artifacts. Public availability of an archived module does not grant reuse rights.
