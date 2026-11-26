# Neon Cipher

An original keygen-style chiptune module for FastTracker II.

- **Tempo:** 150 BPM, speed 6
- **Key:** A minor
- **Length:** 96 seconds (15 order entries, 12 patterns of 64 rows)
- **Loop:** restart position 0, designed to loop back into the intro

## Arrangement

Intro -> build -> main A -> main A2 -> chorus B -> chorus B2 -> breakdown -> build 2 -> climax C -> climax C2 -> bridge -> chorus reprise -> climax reprise -> outro

## Instruments

All 16 instruments use original mono 16-bit PCM samples generated with NumPy:

1. Kick
2. Snare
3. Closed hat
4. Open hat
5. Crash
6. Bass
7. Sub bass
8. Lead (short)
9. Lead 2 / harmony
10. Pad
11. Pluck / arpeggio
12. Stab
13. Bell
14. Riser
15. Reverse crash
16. Lead (long)

## Files

- `tune.xm` — final editable tracker module
- `preview.wav` — 44.1 kHz / 16-bit stereo preview of one loop
- `make_samples.py` — sample-generation source
- `compose.py` — composition source (the final XM also includes mix adjustments and a long-lead instrument)
