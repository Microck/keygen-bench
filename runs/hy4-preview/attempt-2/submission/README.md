# "keygen loop" - FastTracker II XM module

`tune.xm` is a 14-channel XM (FastTracker II) module: an original, self-contained
keygen-style chiptune loop (A minor, 168 BPM, 4 rows per beat, speed 6).

* length: 18 patterns x 64 rows = 72 bars = 1:42.9 (loops seamlessly back to order 0)
* instruments: all sounds are synthesised from scratch (see `src/synth.py`)
  - kick, snare, clap, closed hat, open hat, tom, riser (one-shot percussion)
  - bass, lead (pulse), harmony lead (triangle), pluck melody voice, pad (loopedtones)
* 8-bit samples so every sample length/loop field is identical in samples and bytes
* per-channel panning is set with effect 8 on row 0 of every pattern
* note levels come from the XM volume column; a few instruments use volume envelopes

Arrangement (4-bar units, one pattern each):
0 intro (drums+bass+pad) 1 +arp 2 full theme + melody 3 variation 4 variation
5 breakdown (Dm Am E Am) 6 build (riser) 7-9 B-section (Am G F E) 10 breakdown (riser)
11-13 theme variations 14 mini-break (riser) 15-17 final stretch -> loops to the intro

Files:
* `tune.xm`      - the editable tracker module
* `preview.wav`  - stereo 44.1 kHz render (1 loop) produced by `ft2 module_render`
* `src/`         - the python sources that build everything (no external data needed)

Rebuild with: `python3 src/make.py`
