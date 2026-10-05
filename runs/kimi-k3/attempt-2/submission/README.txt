neoncrypt.keygen
================

An original keygen-style chiptune module in FastTracker II XM format.
Music only; composed, synthesized and rendered entirely with Python/NumPy +
the provided FT2 tool in this workspace (no external samples).

- Format....... ProTracker-compatible XM ("FastTracker II"), 8 channels
- Key / mode... D minor (harmonic dominant turns, Gm->A bridges)
- Tempo........ 140 BPM, speed 6, 64-row patterns
- Length....... 12 order positions (~82 s), loops seamlessly back to position 0
- Title........ "neoncrypt.keygen"

Structure:
  00  intro     arps + pads, riser
  01  intro B   kick/bass/hats enter
  02  theme A1  square lead hook
  03  theme A2  saw echo answers
  04  bridge B  Gm -> A, call/response claps + arpeggio-fx stabs
  05  breakdown half-time drums, pluck melody
  06  theme A3  third-harmony lead, offbeat stabs
  07  theme A4  octave-up climax
  08  gap       syncopated stab groove + snare roll build
  09  final D1  full stack
  10  final D2  resolve home
  11  outro     strips back to the intro texture -> seamless loop

Instruments (13, all synthesized here):
  kick, snare, clap, closed/open hats, square-saw bass, 25% pulse lead,
  saw lead, pluck (arp), detuned pad, chord stab, crash, riser.
  Chord shimmer stabs use XM effect 0 (arpeggio); lead vibrato via effect 4.

Files:
  tune.xm          the module (submission)
  tune_preview.wav full-length render (single pass, 44.1kHz/16-bit)
  src/             generators: samples.py (sound design), compose.py (score),
                   analyze.py (verification harness used during writing)
