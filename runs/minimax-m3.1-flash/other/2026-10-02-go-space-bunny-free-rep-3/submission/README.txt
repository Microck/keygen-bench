LICENSE GENERATOR ZERO
=======================
an original keygen tune for Fast Tracker II (ft2-clone)

file          tune.xm        16 patterns x 64 rows, 10 channels, 150 BPM, speed 6
preview       preview.wav    102.4 s stereo render (loops back to the top)

tempo / form
------------
150 BPM, 16th-note rows (speed 6).  16 patterns = 64 bars.
Key of A minor (harmonic minor dominant, E7 = E G# B D).

  0  INTRO A        pad swell, sparse arp, hat build, reverse cymbal
  1  INTRO B        + bass, full arp
  2  THEME A        Am  F  C6 E7 : drums, reese bass, supersaw arp, chord pad
  3  THEME B        Am  Dm F  E7 : variation + octave-up counter arp
  4  LEAD 1         melody A, sparse arp
  5  LEAD 2         melody B
  6  BREAK 1        pad + arp, no kick, snare roll into the build
  7  BUILD          noise riser, snare roll, fast ascending E7 run
  8  THEME C        F  C6 Dm E7 : plucks + counter arp
  9  THEME D        Am F  G  E7 : adds a lead tag over the dominant
 10  LEAD 3         melody C
 11  LEAD 4         melody B + fill
 12  DRUM BREAK     drums + bass + lead riff, tom fill
 13  THEME FINAL    everything
 14  LEAD FINAL     melody an octave up, full arrangement
 15  OUTRO          pad/arp decay back into the intro - loops cleanly

instruments (all samples synthesised from scratch with numpy)
-------------------------------------------------------------
 1 ARP    looped 3-voice detuned supersaw wavetable (period-locked loops)
 16 ARP R  same sample, hard right
 2 BASS   looped reese bass (3 detuned saws + square sub, saturated)
 3 KICK   pitch-sweep sine with click
 4 SNARE  two-tone body + band-passed noise
 5 CLAP   three-burst clap
 6 HAT    6-square 808 style metal, 7.4 kHz high-pass
 7 OHAT   open hat
 8/17 PAD looped string pad (wide chorus), panned L/R
 9 PLUCK  bright one-shot stab
10 LEAD   one-shot lead with pitch drift
11 CRASH  noise + metal, 2 s
12 RISE   3.2 s noise/tone riser
13 TOM    pitch-sweep tom
14 REV    reverse cymbal

sources
-------
synth.py        generates every sample (44100 Hz, 16 bit mono wav)
compose.py      harmony, melodies, drums and the arrangement -> pattern data
build_calls.py  turns the pattern data into FT2 tool calls (ft2 batch) and
                writes submission/tune.xm
run.sh          NOTE_GAIN=0.30 ./run.sh   rebuild + save + render
