KEYGEN DREAM  -  original keygen-style tracker tune
=====================================================

File      : tune.xm   (FastTracker II module, 12 channels, 150 BPM, speed 4)
Length    : 46.9 s, 11 patterns x 4 bars (order loops back to position 0)
Preview   : tune_preview.wav (rendered with the workspace FT2 clone, 2 passes)

Instruments (all samples are synthesised from scratch in samples_lib.py and
stored as 8-bit samples as this FT2 build expects):
  1 LEAD   supersaw loop (5 detuned saws)      - main melody
  2 LEAD2  3-osc detuned saw                   - harmony / second voice
  3 ARP    30% pulse loop                      - 16th-note arpeggios
  4 BASS   pulse + square + sub sine loop      - bassline
  5 SUB    sine-ish bass                       - bottom octave
  6 STAB   power-chord stack one shot         - hits
  7 PAD    slow detuned pad                    - breakdown chords
  8 KICK   9 SNARE  10 HATC  11 HATO  12 CRASH  13 RISER

Arrangement
  0 intro      : kick/snare/hats + bass
  1 intro 2    : + stabs, busier beat
  2 build      : + riser, arpeggios, first lead hints
  3 main A     : melody A, full drums, stabs, crash
  4 main A'    : melody A2 + drum fill
  5 break      : drums drop out, pad chords + lead
  6 main B     : melody B (16th note activity), biggest kit
  7 main B'    : melody B2 + fill
  8 break 2    : pad + arp, riser into the return
  9 main C     : melody B an octave up, crash, full power
  10 ending    : melody END, fill leading straight back into pattern 0

Mix/level notes: this FT2 clone ignores the instrument "volume" field, so the
balance is baked into each sample's peak amplitude (MIX table in arrange.py)
and the pattern volume column (016..0..15 = full, 0x10..0x40 = ramp down).
Panning: 0x80 = centre.

The note-to-rate ladder of this build was measured directly (render a 4 s
440 Hz sample at each note) and the t() helper in tune.py maps traditional
note names onto it, so C4/A4/E5 land on their usual frequencies.

Source: dsp.py, samples_lib.py, tune.py, xmwrite.py, arrange.py
Rebuild: python3 arrange.py   (writes /workspace/submission/tune.xm)
