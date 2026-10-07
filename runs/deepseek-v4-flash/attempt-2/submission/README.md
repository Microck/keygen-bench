# Neon Skyline Keygen

A 16-channel FastTracker II keygen tune in A minor, 160 BPM (speed 6),
~48.7 seconds, looping cleanly from the outro back to the intro.

## Structure
- P0 intro (2 bars): pad + 16th arps, riser into the groove
- P1 verse groove (Am F C G), played twice
- P2 verse B: groove + lead riff A with 3rds harmony
- P3 chorus 1 (F G Am E): full 16th drums, anthemic lead
- P4 verse C: groove + riff B
- P5 chorus 2: 8th-note variation of the chorus lead
- P6 break (Dm / Am): half-time, riser into the finale
- P7 final chorus: full arrangement + sub octave doubling
- P8 outro: final Am stab, cut to silence -> clean loop

## Instruments (all synthesized with NumPy)
1 kick, 2 snare, 3 closed hat, 4 open hat, 5 bass (looped driven saw),
6 lead (looped driven square), 7 pluck (arps), 8 pad (looped saw, slow attack),
9 crash, 10 riser, 11 impact, 12 sub (sine), 13 click.

## Files
- tune.xm      final editable module (save this)
- preview.wav  render of tune.xm (44.1 kHz / 16-bit stereo)
- compose.py   builds the module via the ft2 batch API
- gen_samples.py generates the sample WAVs from NumPy
