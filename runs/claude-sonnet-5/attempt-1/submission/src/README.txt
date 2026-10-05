Keygen tune - source notes
===========================

Build order (run with the FT2 MCP bridge/socket live at /tmp/keygen-ft2.sock):
  1. python3 synth.py              # (optional) renders instrument previews to wav
  2. python3 load_instruments.py   # (optional) sanity-loads instruments alone
  3. python3 compose.py            # builds the whole module in the live FT2 session
  4. use ft2 call module_save / module_render, or analyze.py on a rendered wav

Design summary
--------------
- Key: A natural minor (Am-F-C-G, i-VI-III-VII), 150 BPM, speed 6, 16 rows/bar,
  64-row (4-bar) patterns.
- All samples are synthesized from scratch with numpy (additive/harmonic
  synthesis for tonal voices, shaped noise for drums/risers) -- no external
  samples. theory.calibrate() works out the relative_note/finetune pair so
  that FT2 note C-4 reproduces each sample's own generation sample-rate
  exactly, so normal note names in the patterns play the intended pitches.
- Arrangement: intro -> verse -> chorusA -> chorusB -> verse2 -> chorusA2
  (bigger) -> chorusB -> breakdown -> build -> drop -> outro, then the order
  list (loop_start=0) repeats from the top. The outro's last bar fades the
  pad/arp down, plays a snare-roll fill and a downward FX "downlifter" sweep
  so the restart into the soft intro reads as an intentional reset.

IMPORTANT ENGINE QUIRK discovered & worked around
--------------------------------------------------
This FT2-clone build's *volume column* mixes back incorrectly: a cell volume
V actually plays at max(0, V-16), and any V in 1..15 falls back to a fixed
level instead of being quiet (V=16 is dead silence). Verified with isolated
single-note renders sweeping V. The effect-column "set volume" command
(effect 12, i.e. Cxx) renders perfectly linearly across 0..64, so every note
in compose.py is written using effect=12/effect_param=<volume> instead of
the volume column. Likewise the hi-hat "ping-pong" panning uses two
pre-panned instrument copies (HatClosedA/B) rather than a per-note panning
effect, so the single effect slot stays free for the volume command.
If you extend this module, keep using note_at()/hits()/shape() (they do
this for you) rather than passing a raw "volume" to pattern_set_cell.

SECOND ENGINE QUIRK discovered & worked around
-----------------------------------------------
module_render's "amp" argument defaults to a fixed x16 gain when omitted (it
is NOT auto-normalizing) -- confirmed by byte-for-byte identical output
between an unspecified-amp render and an explicit amp=16 render, and by
exact x16 sample ratios against an amp=1 render. A full 14-channel mix
clipped hard under that default. MASTER_GAIN in compose.py (0.50) scales
every note's volume down so the densest section (the drop) still peaks at
~76% of full scale at the default amp=16 (and stays clip-free up to about
amp=20), while staying essentially untouched at lower amps. If you change
the arrangement, re-check headroom with analyze.py before/after using
module_render with NO amp argument (that's what a from-scratch renderer is
most likely to do).
