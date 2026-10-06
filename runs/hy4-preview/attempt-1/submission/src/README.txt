Keygen Drive - FT2 (XM) module
===============================

tune.xm        : the editable FastTracker II module (12 instruments, 16 channels,
                 11 patterns x 64 rows, 145 BPM, speed 6 -> rows are 1/16 notes,
                 44 bars, ~1:12.8 loop)
preview.wav    : render of the module (ft2-clone, 44.1 kHz stereo)

Build
-----
src/waves.py    : playback-rate helpers and band-limited single-cycle synthesis
src/gen.py      : synthesises every instrument sample (src/wav/*.wav)
src/compose.py  : musical data + part writers (drums, bass, chords, arp, melody)
src/build.py    : arrangement -> FT2 tool calls -> tune.xm
src/build_calls.json : the exact tool calls used to build the module
src/analyze.py, src/chroma.py, src/xmcheck.py : offline checks used while writing
src/solotest.sh : renders one instrument alone

How it is put together
----------------------
All tonal instruments are one sample each: a single-cycle wavetable of 32 stored
samples, looped.  In XM a note consumes samples at 8363*2^((note-49)/12) Hz, so a
32-sample cycle sounds at concert pitch for the written note name (A-4 = 439.5 Hz),
which makes every instrument mutually in tune.  Each wavetable is additively
resynthesised with only the harmonics that stay below Nyquist at the top note of
its register, so nothing aliases.

Drums are one-shot samples authored at the rate they are played back at C-4, so
they are triggered with the note C-4 and keep the timbre they were designed with.

No envelopes are used (the tool set exposes none), so every shape is made by the
patterns themselves: volume-column shaping, note cuts (EC0) for the staccato
parts, and the last row of the song cuts every sustaining voice so the loop
restarts clean.

Structure (1 bar = 16 rows)
---------------------------
intro 4 bars | theme A 8 bars (Am F C G / Am F Dm E) | part B 8 bars
(F G Am Am / F G Dm E) | breakdown 4 bars | theme A' 8 bars | part B' 8 bars |
coda 4 bars with a hat roll into the loop point.
