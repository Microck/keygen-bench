# Chromatic Dawn -- an original keygen tune

FastTracker II (XM) module, 125 BPM, speed 6, 12 channels, 8 patterns (32 bars,
~61 s), written to loop seamlessly back to order 0.

## Files
* `tune.xm`       -- the module (the actual submission)
* `preview.wav`   -- 44.1 kHz stereo render of one full loop
* `gen_samples.py`-- synthesises every instrument from scratch with NumPy
                     (additive saws, FM bell, Karplus-Strong pluck, synthesized
                     drums, noise riser ...) and writes them as WAV files
* `xmwrite.py`    -- a small XM writer (header, packed patterns, instruments,
                     delta-encoded 16-bit samples)
* `compose.py`    -- the arrangement: builds the 8 patterns and writes tune.xm

To regenerate: `python3 gen_samples.py && python3 compose.py`

## Sound set
lead saw (baked vibrato, dual detuned saw), pulse echo, pulse harmony,
4-voice detuned pad (looped samples, one voice per channel), pluck arpeggio,
saw+sub bass, kick, snare (3 pre-mixed levels for the rolls), closed/open hats,
FM bell, chord stab, noise riser, crash, sub drop.

## Arrangement
0 hook A (light) - 1 hook A (+pad, +bell) - 2 break - 3 build - 4 hook B -
5 hook B (+bell, fill) - 6 hook A reprise (+harmony, +stabs, 16th hats) -
7 hook B climax + snare-roll/riser build that resolves on the loop point.

Harmony: A minor. Hook A over Am-F-C-G, hook B over Am-G-F-E (the dominant
E major resolves back to Am on the restart).
