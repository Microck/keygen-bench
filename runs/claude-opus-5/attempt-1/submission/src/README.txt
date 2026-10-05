"neon velocity" - original keygen tune (FastTracker II module)
==============================================================
tune.xm           the module (14 channels, 20 instruments, 15 patterns)
tune_preview.wav  one full pass rendered at 44.1 kHz / 16 bit (96 s)

Form (4 bars per pattern, 150 BPM, speed 6, 64 rows, loops from the end
back to position 0):

  00-01  intro          pad + stereo arp, 8-bar drum build
  02-03  verse          four-on-the-floor, octave bass, bell motif + echo
  04-05  chorus A       PWM lead on the 3+3+2 hook   (Am F C G)
  06-07  chorus B       lead doubled an octave down  (Dm Am F E)
  08     break          no kick, pad + bell theme, reverse cymbal
  09     build          snare crescendo + noise riser, silence on the last beat
  10-11  chorus A'      supersaw lead + chord-tone harmony + octave stack
  12-13  chorus B'      climax, busiest bass, pitch-dive ending
  14     outro          turnaround + tom fill back into the intro

Everything is synthesised from scratch with NumPy (no external samples):
drums are modelled (pitch-swept sine kick, filtered noise snare/claps),
the bass is a resonant-filtered saw, the leads are a band-limited PWM pulse
and a 5-voice supersaw built on an FFT grid so their loops are exactly
phase continuous; pads and stabs are single-sample minor/major chords.

Source files
  dsp.py         oscillators, ZDF state-variable filter, loop helpers
  mk_samples.py  builds the 20 instruments and uploads them (16-bit)
  song.py        pattern/cell model, panning, instrument-relative volumes
  compose.py     generators: drums, bass, arps, stabs, pads, melodies
  build.py       the arrangement itself  (python3 build.py)
  solo.py/dump.py  mixing + pattern inspection tools used while composing

Rebuild:  ft2 call module_new '{"channels":14,"name":"neon velocity"}'
          python3 mk_samples.py && python3 build.py
          ft2 call module_save '{"path":"tune.xm","format":"xm"}'
