# neon scroller — keygen tune

A chip-trance keygen tune for FastTracker II.

| Property          | Value                                   |
|-------------------|-----------------------------------------|
| Key               | A natural minor                         |
| Tempo             | 142 BPM, speed 6 (16 rows per bar)      |
| Length per loop   | ~67.6 s intro + ~60.8 s loop body       |
| Channels          | 10                                      |
| Chords (main)     | Am · F · C · G (vi–IV–I–V in C)         |
| Chords (bridge)   | Am · G · F · E (andalusian cadence)     |

## Arrangement

| Pos | Pattern         | Notes                                    |
|----:|-----------------|------------------------------------------|
| 0   | Intro           | bass pulse, pad swell, hat buildup, FX   |
| 1   | Verse           | basic beat + arp + driving bass          |
| 2   | Verse + hook    | main 4-bar melody introduced             |
| 3   | Chorus          | octave bass, chord stabs, rich lead      |
| 4   | Chorus var      | busy drums + counter-melody on pad ch    |
| 5   | Break           | no kick/snare, pad + lead solo, riser    |
| 6   | Bridge          | darker Am-G-F-E, dramatic descending     |
| 7   | Big chorus      | climax: higher lead, double stabs, crash |
| 8   | Chorus var      | repeats                                  |
| 9   | Outro           | thinned down toward the loop             |

Playback restarts at position **1** (verse), so the intro plays only
on the very first iteration — subsequent loops run Verse → Outro.

## Sounds

All samples synthesised on the fly in Python/NumPy at 22050 Hz, mono.

- `kick`  pitch-swept sine with click + sub-tone
- `snare` highpassed noise burst + 220/330 Hz body
- `clap`  multi-attack noise through 900–2500 Hz band
- `hat_c` closed hihat: short highpassed noise burst
- `hat_o` open hihat: longer noise with decay
- `crash` dual-band metallic noise, long tail
- `bass`  double-saw with dynamic LP sweep + pluck env
- `pluck` saw+square short stab
- `lead`  hollow saw+square+5th harmonic, period-exact 2-cycle loop
- `pad`   5-voice detuned supersaw, crossfaded 8-cycle loop
- `arp`   bright square+saw pluck
- `stab`  PWM chord stab
- `zap`   downsweep sine
- `sweep` white-noise riser
- `rev`   reverse cymbal

Pan: hats and arps are spread off-centre (sample `panning` field);
kick/snare/bass/lead/pad stay centred.

Effects used in patterns: 4xy (vibrato) on sustained lead notes, EDx
(note delay) on 16-th hats and arps for a 1-tick swing, 8xy (set pan)
reserved for occasional dynamic stab panning.

## Files

```
tune.xm                — the editable module (FastTracker II format)
preview.wav            — single-iteration render, 44.1 kHz 16-bit stereo
preview_loop.wav       — 2-iteration render that shows the loop seam
src/samples.py         — NumPy sample generators
src/build_tune.py      — pattern/instrument composer that drives FT2
src/build_batch.json   — JSON op-list for `ft2 batch`
```
