# Neon Genesis Key -- original keygen tune

* E minor, 150 BPM, speed 6 (4 rows/beat, 16 rows/bar)
* 8 channels, 14 instruments, 18 patterns = 72 bars = 1:55, loops cleanly to order 0
* real tracker module: pattern data, note-offs, chip arpeggio (effect 0xy) on the
  chord voices, hand-programmed drums; every sample synthesised from scratch

Form:
  bars  1-4   P00        intro: arpeggio + chip-arp pad + hats
  bars  5-8   P01        bass + half time beat, lead pickup lick
  bars  9-16  P02-P03    theme A (hook) over Em - C - G - D
  bars 17-24  P04-P05    theme A + diatonic counter melody
  bars 25-40  P06-P09    theme B over Am - Em - C - D / Am - Em - C - Bmaj
  bars 41-48  P10-P11    breakdown: pads, sub bass, long tones, snare roll build
  bars 49-64  P12-P15    theme A again: octave arps, clap layer, biggest drums
  bars 65-72  P16-P17    outro thins out, tom fill leads back to the intro

Instruments (synth.py): LEAD (band limited saw), LEAD2 (pulse), PLUCK (arp),
PAD, BASS (saw + sub octave), SUB, KICK, SNARE, CLAP, CHAT, OHAT, TOM, ZAP, CRASH.
Samples are seamless additive loops / shaped one shots generated at the XM
reference rate, so C-4 = 261.6 Hz and the whole keyboard is in tune.

Files: synth.py = waveforms, compose.py = the composition, xmread.py = XM dumper,
melody_check.py = pitch track analysis, tune.wav = 44.1 kHz preview render.
