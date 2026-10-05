serial sunrise - an original keygen tune
========================================

  format   : FastTracker II module (XM), 12 channels, 9 patterns, 20 instruments
  tempo    : 150 BPM, speed 6 (one row = 1/16 note)
  key      : A minor
  length   : 11 song positions (~70 s per pass)
  looping  : song restart position = 2, so the 12.8 s intro plays once and the
             body (positions 2..10) repeats forever; the last pattern ends on a
             snare fill that lands on the crash/downbeat of the restart pattern.

arrangement
  pos 0  intro      pad + half-time arp
  pos 1  intro 2    + bass, hats, lead teaser, reverse cymbal into the drop
  pos 2  A1         <-- loop restart: four-on-the-floor, main hook   (Am F C G)
  pos 3  A2         + stabs, rolling bass, snare fill
  pos 4  B1         new melody, claps                                (Dm F G Am)
  pos 5  B2         climax: rolling bass, chord-tone harmony line    (Dm F G E)
  pos 6  break      drums drop out, build: riser + 16-row snare crescendo
  pos 7  A1         reprise
  pos 8  A3         descending arp variation, tom fill
  pos 9  B1v       variation of B1: new melody, descending tom fill
  pos 10 B3         final: harmony line + turnaround fill back to pos 2

sound
  Every sample is synthesised from scratch with NumPy (no external material):
  - drums: swept-sine kick with click, noise+body snare, 4-burst clap,
    metallic hats, crash, reverse cymbal, noise riser
  - bass: additive saw with a per-harmonic decay (filter sweep) + pitch thump
  - pluck/lead: band-limited pulse; lead is two saws detuned by 13 cents, built
    in the frequency domain so its 16512-sample sustain loop is seamless
  - pads/stabs: equal-tempered 4-note chord waveforms (minor/major), the pad
    loop (27520 samples) places every partial exactly on an FFT bin, so it is
    click-free and in tune with the lead (<3 cents)
  Pads are "sidechained" to the kick with volume-column steps, the lead uses
  vibrato (4xx), the echo channel is a 3-row delay of the lead (a harmony line
  in the climax patterns), and channels are spread with 8xx panning.

files
  tune.xm       the module (the actual submission)
  preview.wav   44.1 kHz render of one pass
  src/synth.py  NumPy sample synthesis -> base64 PCM tool calls
  src/compose.py patterns, arrangement, mix levels
  src/build.py  glues both into one ft2 batch, saves and renders
