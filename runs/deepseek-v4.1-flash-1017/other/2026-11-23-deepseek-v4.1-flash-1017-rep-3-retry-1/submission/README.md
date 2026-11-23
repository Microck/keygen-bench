# "keygen" — original keygen-style chiptune for FastTracker II

`tune.xm` is a real, fully editable FastTracker II module (XM, version 0x0104,
linear frequency table):

* 18 channels, 150 BPM, speed 6, 10 patterns x 64 rows = 40 bars (~64 s),
  loop start = order 0, so it loops end->start seamlessly.
* 41 instruments, every sample synthesised from scratch with NumPy:
  band-limited pulse/saw loops for leads & arpeggios, long additive pads
  (8 chords, decorrelated L/R pairs), chord stabs, additive bell, a
  pitch-dropping bass one-shot, and synthesised kick / snare / closed & open
  hats / crash / tom / rim / riser. No external audio is used.
* Music is carried by pattern data and tracker effects only: chord-tone
  harmony voice under the lead (3rd/4th/5th below), vibrato (4xx), panning
  (8xx) incl. alternating hat placement, the volume column for accents, note
  off (97), note cut (ECx) and tempo/speed on the song level.
* XM 16-bit samples are delta-encoded; every sample is verified to stay inside
  int16 after cumulative decoding (no wraparound distortion).

## Arrangement (1 pattern = 4 bars, 16 rows/bar)

| # | Section | Harmony |
|---|---------|---------|
| 0 | Intro — pads, bell motif, rising arps, swell | Am F C G |
| 1 | Theme A | Am F C G |
| 2 | Theme A' — 16th hats, octave bass, double arps | Am F C G |
| 3 | Theme B | Dm Bb F E |
| 4 | Breakdown — bells, hook answer, "modem" sparkle run | Am F C G |
| 5 | Theme A full | Am F C G |
| 6 | Theme B peak | Dm Bb F E |
| 7 | Theme C | F G Em Am |
| 8 | Theme A final chorus | Am F C G |
| 9 | Outro / turnaround -> loops back to Am intro | Am F C G |

Section gains (applied to pattern volumes) give a build from intro through the
breakdown dip to the final chorus; the last bar resolves to A minor and decays
into the intro's Am pad, so the restart is musically seamless.

## Sources (rebuild with `python3 final_song.py`)

* `synth2.py`        — all sample synthesis
* `deltafix.py`      — keeps 16-bit delta-encoded samples inside int16
* `xm.py`            — XM file writer
* `final4.py`        — composition primitives, melodic themes, effects helper
* `compose_final.py` — instrument bank, group gains, pan/volume tables
* `final_song.py`    — full arrangement -> tune.xm
* `lib2.py`          — FT2 render helper
* `tune_preview.wav` — 44.1 kHz / 16-bit stereo preview (peak -1.1 dBFS)
