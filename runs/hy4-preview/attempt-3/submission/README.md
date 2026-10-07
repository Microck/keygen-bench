# "Keystream" - original keygen-loop tune (FT2 / XM)

* `tune.xm`       - the module (14 channels, 12 patterns x 64 rows, 150 BPM / speed 6, restart position 0)
* `preview.wav`   - stereo 44.1 kHz render of one full loop (76.8 s)
* `src/`          - the Python/NumPy sources used to synthesise the samples and write the patterns

## How it was made

Everything (samples and patterns) was generated programmatically, then written into the
tracker through the exposed FT2 tools:

1. `src/synth.py`  - small DSP kit (biquad filters, band-limited harmonic stacks, looped-tone
   builder incl. baked-in vibrato/tremolo that stays seamless across the loop, percussion
   builders for kick / snare / clap / hats / cymbal / riser).
2. `src/mkinstr.py`- builds the 12 instruments: KICK, SNARE, CLAP, CHAT, OHAT, CRASH, SWEEP,
   BASS, ARP, LEAD, LEADDET (detuned doubling voice), PAD.  Each melodic instrument is a
   short attack section followed by a seamless sustain loop, so notes are shaped with
   pattern-level note-offs and per-row volumes (there are no envelopes in this build).
3. `src/music.py`  - the score: chord tables, arpeggio/bass/drum templates, three melodies
   (theme A, theme A-variation, theme B) and the 48-bar arrangement
   (intro | A1 | A2 | B1 | B2 | breakdown | finale).
4. `src/compose.py`- turns the score into tracker cells, emits the tool batch
   (`ft2 batch`) and saves/renders the module.
5. `src/xmdump.py` - XM reader used to verify what actually ended up in the file.

Key: A minor (with the harmonic-minor E at the end of each 8-bar phrase), 150 BPM.

## Tuning / notes

Sample playback takes the standard XM path: every instrument carries
`relative_note = 29`, `finetune = -24` and its own base frequency, so the written note names
map to equal-tempered pitches (~-3 cents overall).  All stored note values lie between 37
and 81, so no value collides with the note-off code (97).

Because this FT2 build exposes no volume envelope, dynamics come from per-row volume
columns and explicit note-off cells (a note-off cell carries *no* instrument - with an
instrument the cell re-triggers instead of releasing).

The loop is clean: the last bar ends with a fill plus a crash and an arpeggio note that
runs straight into the restarting intro; every sustaining voice is released on the final row
except that arpeggio, so nothing is left dangling across the seam.
