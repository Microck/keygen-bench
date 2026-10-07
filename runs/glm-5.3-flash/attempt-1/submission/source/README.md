# "Cracked Perfection" - an original keygen tune (XM)

## Files
- `../tune.xm`       - the FastTracker II module (14 channels, 15 instruments, 9 patterns)
- `../preview.wav`   - 44.1 kHz stereo render of one full pass (57.6 s), loops back to order 2

## How it is put together
`gen_samples.py` synthesises every instrument from scratch with NumPy and writes
16-bit WAV files in `../samples/`.  All samples are rendered at an 8363 Hz design
rate; with `relative_note = 0` the tracker plays them at their written pitch at
note C-5, so pattern notes are ordinary scientific pitch names.

| instrument | sound |
|------------|-------|
| LEAD / LEAD2 | 9-harmonic saw/pulse hybrid, looped sustain, LEAD2 is the same sample detuned +12 finetune for a unison chorus |
| ECHO   | same waveform as a one-shot with a 0.34 s decay, used for a dotted-eighth tempo echo |
| ARP    | 25 % duty pulse pluck, 0.13 s decay |
| PADL/PADR | soft 12-harmonic saw, looped, detuned +/-7 and panned wide |
| BASS   | saw + pitch-dropped attack, 0.22 s pluck |
| KICK / SNARE / CLAP / HATC / OHAT / CRASH / RISER | synthesised percussion |

`build.py` writes every pattern cell (2342 of them) and emits a JSON batch that is
executed with `ft2 batch`.  Note endings are done with volume-column fade slides
(0x6F) so nothing is cut abruptly; held lead notes get a vibrato row on every row.

## Music
- A minor, 150 BPM (speed 6), one row = one sixteenth.
- A section: Am - F - C - G.  B section: F - G - Am - E.
- Order: intro / groove build / A1 / A2+counter / B1 / B2 / A3 / breakdown / climax,
  then it loops back to order 2 (the full groove), so the intro is heard once.
