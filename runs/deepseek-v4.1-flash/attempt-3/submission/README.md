# ACTIVATION CODE — an original keygen tune (FastTracker II / XM)

A 64-second looping chiptune / keygen track.  12 channels, 150 BPM, speed 6,
A natural minor with a harmonic-minor lift (E major) in the break and solo.

## Structure  (order list; each pattern = 4 bars of 16th notes = 6.4 s)

| # | section                | harmony |
|---|------------------------|---------|
| 0 | intro (build)          | Am Am F G      (bell arpeggio, pad, bass, kick/hats enter) |
| 1 | theme A                | Am F C G       |
| 2 | theme A' (variation)   | Am F C G       |
| 3 | theme B (chorus)       | F G Am Am      |
| 4 | theme B'               | F G Am E       (chromatic bass walk-up) |
| 5 | solo                   | Am Dm E Am     (16th-note lead solo) |
| 6 | breakdown + build      | Am F Dm E      (drums drop out, riser + snare roll build) |
| 7 | theme A (reprise)      | Am F C G       |
| 8 | theme B (climax)       | F G Am E       (16th hats, bell doubling) |
| 9 | outro / turnaround     | Am F C E       -> riser + roll back into order 0 |

Restart position = 0: the module loops from the end of order 9 straight back to
the intro; the last bar is a build that resolves into the intro's downbeat.

## Instruments (all original, synthesized with NumPy at 44100 Hz, 16-bit)

| # | name  | what it is |
|---|-------|------------|
| 1 | LEAD  | two detuned band-limited saws (12 harmonics), forward sustain loop |
| 2 | ARP   | 30 % pulse + saw, short loop — the 16th-note arpeggio texture |
| 3 | BASS  | decaying saw + sub with a pick click |
| 4 | PAD   | three detuned saws, slow attack, sustain loop (3 channels) |
| 5 | KICK  | exponential pitch sweep 228->58 Hz + click |
| 6 | SNARE | band-passed noise + 1750/620/330 Hz tones |
| 7 | HAT   | 7-16 kHz noise burst |
| 8 | OHAT  | open hat |
| 9 | CRASH | 3-16 kHz noise wash + shimmer partials |
| 10 | BELL | inharmonic chime (2.76 / 5.40 / 8.93 partials), long decay |
| 11 | RISER | filtered-noise sweep, used for the build-ups |
| 12 | BLIP  | short 2.9 kHz blip for accents |

## Mix

Per-note volume column drives the balance; panning is constant-power: arp a
little left, pad spread over three channels, hats/blip right, crash left.
Final render peaks at about -1.9 dBFS (no clipping).

## Files

- `tune.xm`         — the module (the deliverable)
- `preview.wav`     — 44100 Hz / 16-bit stereo render of `tune.xm` (64 s)
- `make_samples.py` — generates every sample WAV with NumPy
- `make_tune.py`    — emits the ft2 batch that builds the module
