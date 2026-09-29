# How tracker composition works

A tracker module combines score/event data with reusable sound material. Time moves down rows, channels run across columns, and each cell can contain a note, instrument, volume value, and effect command.

## Pattern grid

Example XM-style cell:

```text
C-5 01 40 037
```

| Field | Meaning |
|---|---|
| `C-5` | Note |
| `01` | Instrument |
| `40` | Volume-column value |
| `037` | Effect command and parameter |

Patterns are arranged in an order list. Reusing a pattern saves space because the pattern is stored once and referenced multiple times.

## Samples and instruments

Samples are PCM waveforms. Common operations included loading, cropping, resampling, volume changes, waveform generation, and defining forward or ping-pong loops.

A very short loop can behave like an oscillator. Longer one-shot samples can provide drums, vocals, or effects.

XM instruments can map samples across notes and add volume/panning envelopes, vibrato, sustain, loops, and fadeout. IT instruments add more advanced note handling and mapping.

## Effects

Compact tracker effects provided movement without storing extra audio:

- arpeggio;
- pitch slide;
- tone portamento;
- vibrato;
- tremolo;
- volume slide;
- panning;
- sample offset;
- retrigger;
- note cut/delay;
- pattern break/jump/loop;
- tempo and speed changes.

## Typical workflow

1. Choose a target format/player.
2. Assemble a small sample palette.
3. Tune and loop samples.
4. Enter drum, bass, melody, and harmony patterns.
5. Add effects and envelopes.
6. Arrange a seamless loop.
7. Remove unused patterns, samples, and instruments.
8. Test in the exact target replayer.

The final runtime sound could differ between trackers and replay engines because of effect timing, interpolation, clipping, panning, and envelope behavior.
