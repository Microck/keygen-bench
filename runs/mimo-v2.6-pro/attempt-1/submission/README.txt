Licensed To Thrill -- an original keygen / chiptune module
===========================================================

tune.xm      FastTracker II module (14 channels, 19 instruments, 24 patterns)
preview.wav  44.1 kHz 16-bit stereo render of the whole song (2:34)
src/         the generators used to build the module

Style
-----
Eurodance-flavoured keygen tune in A minor, 150 BPM, speed 6
(1 pattern = 4 bars = 6.4 s, 64 rows at 4 rows/beat).

Form (pattern numbers = order positions):
  0-2    intro: arpeggio + pad, then bass/kick, then full band + pickup
  3-10   main hook, four statements of theme A (Am F C G | Am F G Am),
         the fourth one melodically varied
  11-14  B theme (Dm G C F | Dm E Am Am), two statements
  15-16  breakdown and build (F G E E, rising lead, snare roll, riser)
  17-20  drop: theme A in octaves with harmony + counter-melody
  21-22  coda: long anthemic line over the same changes
  23     outro, thinning out and leading back into the intro

The song's order restart position is 0; the last bar (G) resolves into the
first bar (Am), so the module loops cleanly.

Instrument design
-----------------
All samples are synthesised with numpy (src/synth.py) and baked into the
module -- one sample per instrument, no loops, envelopes shaped in the
sample data.

* Tonal samples are built at 8363 Hz with their fundamental at C-4
  (261.63 Hz), so the note you write is the note you hear.
* Percussion is built at 33452 Hz with relative_note +24 and triggered at
  C-4, giving full-bandwidth hats, snares and cymbals.
* Notes are articulated with note-cut (EC0) and the volume column; the
  leads get vibrato (4xy) on long notes.

Verification
------------
Every melodic note of the finished module (lead, harmony, counter, arpeggio,
three chord voices, bass: 3741 notes) was rendered in isolation and checked
against the score with an FFT pitch tracker.  The mix peaks at 0.92 with no
clipping at FastTracker II's default render gain.
