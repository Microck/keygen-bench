# Neon Cipher

An original keygen-style chiptune made in FastTracker II.

- Tempo: 145 BPM, speed 6
- Key: A minor
- Channels: 8
- Samples: synthesized from scratch in Python/NumPy (kick, snare, hihat, saw bass, square lead, pulse arp pad, FM bell)

## Structure
- Pattern 0: Intro (sparse drums → bass → arp → lead build)
- Pattern 1: Main A (Am | F | C | Am)
- Pattern 2: Main B variation (Am | Dm | C | Am → loops back to Pattern 1)

The song loops cleanly from the end of Pattern 2 to the start of Pattern 1 (loop_start = order position 1).

## Files
- `tune.xm` - final editable module
- `preview.wav` - normalized render of one play-through
- `build_tune.py` - Python script that builds the patterns/order/song via the FT2 batch API
- `generate_samples.py` - Python script that synthesizes the raw WAV samples
