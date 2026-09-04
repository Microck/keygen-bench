# Sound design and size optimization

## The “chip” sound without a chip

Many keygen tunes are called chiptunes even when the delivery file is an XM, MOD, S3M, or IT module mixed in software from PCM samples.

The chip-like impression can arise from:

- simple periodic waveforms;
- narrow sample bandwidth;
- short loops;
- limited simultaneous voices;
- abrupt envelopes;
- quantization noise;
- strong pitch modulation;
- rapid arpeggios;
- repetitive, tightly synchronized patterns.

## Tiny looped waveforms

A looped waveform can replace a long sustained recording. Examples include a square-like lead, saw-like bass, noisy loop, or short sampled chord transposed across notes.

Advantages:

- minimal sample storage;
- indefinitely sustained notes;
- fast transposition;
- easy envelope control.

## Tracker effects as synthesis controls

Effects acted like a compact control stream:

- arpeggio for implied chords;
- portamento and pitch slides;
- vibrato and tremolo;
- retrigger, cut, and delay;
- sample offset;
- panning and delayed channel duplication.

## Sample economy

Common byte-saving techniques:

- crop silence and unused tails;
- loop stable sections;
- downsample where acceptable;
- prefer mono;
- use 8-bit samples where quality permits;
- share samples across multiple musical roles;
- remove unused patterns, instruments, and samples;
- strip unsupported effects from a song-specific player.

MiniFMOD historically supported compiling out unused XM effects, while uFMOD included XMStrip for reducing XM data.

## Why modules beat rendered PCM for this use

44.1 kHz, 16-bit stereo PCM consumes about 176,400 bytes per second before compression. A module instead stores reusable samples plus event data, so playback duration is not directly proportional to file size.

## Compatibility optimization

A final module had to be tested in its actual replay engine. Potential differences include effect memory, interpolation, panning, clipping, envelope timing, and malformed-file tolerance.
