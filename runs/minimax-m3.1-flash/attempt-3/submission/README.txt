KEYGEN SEQUENCE  -  an original tracker keygen tune
====================================================

tune.xm        the module (FastTracker II / XM, 8 channels, 18 patterns)
tune_preview.wav   rendered preview (44.1 kHz stereo, 1:55, loops seamlessly)
src/           the scripts that generated everything

THE TUNE
--------
Key            D minor
Tempo          150 BPM, speed 6 (rows = 1/16 note, 4/4, 64-row patterns)
Length         18 patterns = 1 min 55 s, restart position 0 (plays in a loop)
Progression    Dm - Bb - F - C   /   Dm - Bb - Gm - Am   /   F - C - Dm - Bb
               Dm - Gm - Am - Am  (A major only in the intro, so the dominant
               colour arrives later on)

ARRANGEMENT
  0-1   intro        arpeggio + bass + pad, light drums
  2-3   build        lead enters, bass gets busier, 16th hats
  4-7   theme A/B/C  full arrangement, counter-melody, vibrato on held notes
  8-9   break        organ chords, walking bass, half-time drums
  10-13 theme again denser drums and off-beat chord stabs
  14-15 peak         everything, fast vibrato, crash on the downbeat
  16-17 outro        lead dissolves, arp + bass + pad, crash and blips, ends
        on a Dm chord so the loop returns into the intro cleanly

CHANNELS / INSTRUMENTS (all samples synthesised from scratch with numpy,
8-bit mono, 44100 Hz, then placed in the tracker as real instruments)
  1 lead      25% pulse, bitcrushed - main melody
  2 harm      12.5% pulse - syncopated counter line
  3 arp       50% pulse, played with the XM arpeggio effect (0xy)
  4 bass      soft saw/buzz, distorted, octave-jumping 8th-note riff
  5 pad       filtered saw drone, slow attack
  6 chord     short 50% pulse stabs (arpeggiated chords)
  7 organ     stacked pulse "organ" for the break
  8-14 drums  kick, snare, hat, open hat, crash, zap, tom

Every instrument is a one-shot waveform with the attack/decay baked into the
sample data (no envelopes available in this tracker build); note releases are
smoothed with volume slides (effect A) and sustained notes use the arpeggio
effect, so everything is played with notes, instruments and pattern data
rather than a single rendered waveform.

src/gen_instruments.py  synthesises the instrument samples
src/tune_data.py       chord table, melody and counter-line phrases
src/build_tune.py      arrangement -> FT2 batch file (notes, effects, volumes)
src/batch.json         the generated tracker calls (what was fed to ft2)
src/lib_samples.py     small waveform/envelope helpers
src/ft2lib.py, xmwalk.py, analyze_audio.py   tooling / file inspection

REPRODUCING
-----------
    cd src
    python3 gen_instruments.py        # writes src/inst/*.wav (8-bit mono, 44100 Hz)
    python3 -c "import build_tune as B; B.build_batch(B.build_all(), 'batch.json')"
    ft2 batch batch.json               # builds the module in the tracker
    ft2 call module_save '{"path":"tune.xm"}'

The rebuild is byte-identical to the submitted tune.xm.

NOTE ON THE FILE FORMAT
-----------------------
The module is written by the tracker itself (samples, 18 patterns, the order
table and the tempo live in the file; nothing is a pre-rendered waveform).
Sample type bytes are left at 0 (plain 8-bit mono, no loop points): every
instrument is a one-shot waveform whose attack/decay is baked into the sample
data, so no loop flag is needed and the file stays unambiguous for any player.
