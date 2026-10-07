# Keygen Anthem — original chiptune (XM, 8 channels, 9 patterns)

* `tune.xm` — FastTracker II module. 150 BPM, speed 6, 8 channels, 11 instruments,
  9 patterns of 64 rows (57.6 s per pass), restart position 0.
* `preview_keygen_anthem.wav` — 44.1 kHz / 16-bit render of `tune.xm` (one pass,
  57.6 s). Peak 0.68, RMS 0.14, DC offset ~0, no clipped samples.
* `src/` — Python sources: sample synthesis (`sound.py`), composition (`compose.py`),
  XM byte writer (`xmwrite.py`), and the analysis/verification helpers.

## Music
A minor, 4/4. Each pattern = 4 bars = 6.4 s. The tune loops from the outro (an
E7 turnaround that is cut cleanly on the last row) back into the intro (Am).

| # | section | harmony   | content |
|---|---------|-----------|---------|
| 0 | intro   | Am F C G  | pad + arp; hats, then kick enter; rising lead pickup + snare fill |
| 1 | verse 1 | Am F C G  | theme A, drive bass, 16th-note arps, full kit |
| 2 | verse 2 | Am F C G  | theme A with bell doubling and busier drums |
| 3 | bridge  | Dm G C F  | circle-of-fifths walk, new melodic line |
| 4 | hook 1  | F G Am E7 | theme B (high and syncopated), crash accents |
| 5 | break   | Am F C G  | pad/bell drop, then riser + snare-roll build |
| 6 | hook 2  | F G Am E7 | theme B on square lead + bell doubling |
| 7 | verse 3 | Am F C G  | theme A on the thin pulse, off-beat chord stabs, 16th run |
| 8 | outro   | Am Am G E7| turnaround, fill, clean cut at the loop point |

Lead melody always outlines the current chord (verified by FFT of the render);
bass is F-2..E-3, lead E-5..A-6, arps in the chord's mid register.

## Sounds (all synthesised with NumPy — no sampled music anywhere)
* `LEAD PULSE 25%`, `LEAD PULSE 12%`, `LEAD SQUARE` — pulse waves, 4-period
  loops, relative note +12 (so C-4 plays at 16.7 kHz: bright chip leads).
* `CHIP BASS` — saw + square blend, 4-period loop at 8363 Hz.
* `SOFT PAD` — additive partials with a 0.38 s attack ramp, clean 16-cycle loop.
  All waveforms are DC-free (so the mix has no offset and no thumps).
* `BELL` — FM bell (decaying modulator at 3.47x), 0.9 s one-shot.
* `KICK`, `SNARE`, `HAT CLOSED`, `HAT OPEN`, `CRASH` — synthesised one-shots.
Every sample is short (largest: the 1.1 s crash, 73 kB); all musical work is in
the patterns.

## File-layout note
The FT2 tool in this workspace reads each instrument's sample headers from after
the instrument-header block, while the file also carries a canonical copy of the
headers at the standard offset (`xmwrite.py` writes both, with the standard copy's
length/loop shifted by one 40-byte header so a standard reader still loops the
true region). Sample data is 16-bit delta-encoded; type 0x10 = 16-bit,
0x01 = forward loop.
