# A-MINOR KEYGEN  (tune.xm)

An original FastTracker II (XM) keygen-style chiptune, written from scratch.

* **Tempo**      : 165 BPM, speed 6  (1 row = 1/16 note, 64 rows = 4 bars = 5.82 s)
* **Key / mode** : A minor with harmonic-minor colouring (G# over the E major chord)
* **Length**     : 10 patterns / 40 bars / 58.2 s, then it loops
* **Loop**       : restart position 2 - the intro plays once, the main body loops forever
* **Channels**   : 10 (kick, snare, hats, bass, lead, arpeggio, stabs/pads, sub, FX, 2nd lead)
* **Instruments**: 15 hand-built 16-bit samples (all synthesised in NumPy, no envelopes or
  note-mapping used - every amplitude contour, PWM sweep and vibrato is baked into the
  sample data itself; dynamics/panning/fades are done with the volume column and effects).

## Arrangement
| pattern | bars        | section |
|---------|-------------|---------|
| 0 | Am Am Am Am        | intro  - 16th arpeggio + pads, noise riser, sub enters |
| 1 | Am Am F  G         | intro  - groove comes in, lead teaser phrase |
| 2 | Am G  F  E         | MAIN A - Andalusian progression, lead theme 1  <- loop start |
| 3 | Am G  F  E         | MAIN A variation, answer phrase up to G#5 |
| 4 | Am Am F  G         | build  - rising line, 16th run, snare roll, risers |
| 5 | Dm Am E  Am        | bridge - half-time pads, sub bass, legato melody |
| 6 | Am F  G  Am        | MAIN B - anthem melody |
| 7 | Am F  G  Am        | MAIN B - melody one octave up + octave counter-line |
| 8 | Am G  F  E         | final  - theme 1 doubled over two octaves |
| 9 | Am Am Am Am        | outro  - drums drop, pads fade, bass + arp roll into the loop |

## Files
* `tune.xm`      - the module (submit this)
* `preview.wav`  - 44.1 kHz stereo render of one pass
* `src/`         - `synth.py` (DSP helpers), `mkinst.py` (instrument design),
                  `score.py` (the composition -> FT2 batch calls), `ft2lib.py` (tool wrapper)

Everything (drums, bass, lead, arps, pads, sweeps) is played by the module's own
instruments and patterns - no pre-rendered audio tracks.
