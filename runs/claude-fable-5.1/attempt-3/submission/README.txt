serial sunrise - original keygen tune (FastTracker II .XM)
==========================================================
Format : XM, 12 channels, 18 instruments (16-bit samples), linear frequency table
Tempo  : 140 BPM, speed 6 (one row = one 16th note), 64-row patterns (4 bars each)
Key    : A minor
Form   : order 0..9, restart position 1
         P0      intro (plays once: pad swell, arps, bass/hats enter, fill + riser)
         P1-P2   theme A   (Am F C G | Am F Dm E)
         P3-P4   theme A'  (variation, syncopated bass, octave doubling, drum drop-out bar)
         P5-P6   bridge    (C G/B Am Em/G | F C/E Dm E, descending bass, square lead, slides)
         P7      breakdown (Am Am F E, half-time, swelling arps, riser)
         P8-P9   reprise   (theme A + chord-locked second voice, driving bass, arp lift)
Loop   : end of P9 -> P1. The last bar of P9 and the last bar of the intro are identical in
         drums/bass walk-up (E-F-G# -> A) and lead pickup, so the delayed-echo channel baked into
         P1 lines up whichever way P1 is entered. Second-voice/FX channels are keyed off at the seam.
Sound  : every sample is synthesized in NumPy (src/synth.py): band-limited PWM pulse lead,
         square voice, 25%/12.5% pulse arps, saw+square chip bass with baked pluck + sustain loop,
         sine-sweep kick, noise snare/hats/crash/clap, detuned-saw chord pads (minor/major),
         looped noise riser. No envelopes are used; dynamics come from the volume column and
         effects (0xy arpeggio, 3xx tone portamento, 4xy vibrato, 1xx slide).
Build  : python3 src/song.py  -> writes the XM (src/xmwrite.py); the submitted tune.xm was then
         loaded and re-saved by the FT2 clone (module_load / module_save) and verified to render
         bit-identically. preview.wav is the FT2 render of one pass (intro + loop body).
