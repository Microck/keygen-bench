PHOSPHOR TRACE - an original keygen tune (FastTracker II XM)
============================================================
168 BPM, speed 6 (rows are 16th notes), 8 channels, 11 patterns of
64 rows (4 bars each). Order 0..10 with restart position 2, so the
tune plays the intro once and then loops the main body forever.
First pass ~1:03, loop ~0:51, and the loop seam is sample-exact.

All sounds are synthesised from scratch and shaped in the sample
data itself (no envelopes, no note->sample maps, as this build has
none): additive loop-perfect waveforms with baked attacks, plucks,
vibrato, filter tilts, resonant bumps and pad swells.

Instruments:
  1 KICK    2 SNARE   3 HAT     4 OHAT    5 CRASH
  6 TOM     7 ZAP (pitch-sweep fx)
  8 BASS    pulse + sub sine loop, tuned to A-2
  9 BASS2   harder square-ish loop for the climax
 10 LEAD    34% pulse loop, baked 5.5 Hz vibrato + attack scoop
 11 LEAD2   bright saw loop for the top octave / harmony
 12 PLUCK   decaying harmonic pluck (also the arpeggio voice)
 13/14 PAD L/R - three detuned saws with a slow baked swell

Channel layout: 0 kick/snare/tom/zap, 1 hats/crash, 2 bass, 3 lead,
4 octave double / pluck melody, 5 arpeggio, 6-7 pad.

Sections (pattern numbers):
  0-1   intro   - four-on-the-floor build, arps/pads enter, theme teaser
  2-4   theme   - main 8th-note hook over Am F G E7, answer phrase,
                 then a 16th-note root/5th/octave sequence with 0xy arps
  5     break   - half-time, plucked melody over Dm Am Dm E7
  6     build   - rising line, snare roll, zap
  7-9   climax  - hook an octave up with doubling, answer phrase, then
                 the 16th sequence as a finale
 10    outro   - the hook thins out, snare roll leads back to the loop

samples.py  - sample synthesis (additive loops + drum one-shots)
song.py     - note/pattern material (chords, melodies, progressions)
build.py    - drives the FT2 tools, writes patterns and saves tune.xm
