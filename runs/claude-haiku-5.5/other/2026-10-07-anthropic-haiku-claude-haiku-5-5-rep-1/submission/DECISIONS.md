# Decision and change log: Chrome Cathedral

Records design decisions and the defects found and fixed during the build. Each entry gives the
cause, the fix, and how it was verified. Kept for change-management and audit purposes.

## Design decisions
1. **Original audio only.** All 12 instruments are synthesized in code (`source/synth.py`). No third-party or recorded material is used.
2. **Deterministic, offline build.** Fixed seeds and no network access. The rebuild from source gives a byte-identical `tune.xm`.
3. **Independent verification after every build.** `source/verify.py` re-reads the XM and checks samples, cells, the order list and the loop against the score.
4. **16-bit PCM only,** passed inline through the FT2 API (`sample_create_from_pcm`, int16). No external sample files are read, which avoids the WAV misreading below.
5. **Tuning convention:** one-shots use relative note 28 at a 42147 Hz data rate; looped voices use relative note 36 (256 samples), 60 (bass, 1024 samples), or 36 (harmony, 257 samples for detune).
6. **No envelopes.** Dynamics come from sample shapes and volume effects (A0F fades, volume-column levels), as the build requires.
7. **Loop-first arrangement.** Restart at bar 5, with the cadence E to Am at the seam. Intro bars 1-4 play once.
8. **Headroom:** master is trimmed so the render peaks at about 0.89 with no clipping.

## Defects found and fixed
| # | Found in | Symptom | Cause | Fix | Verified by |
|---|---|---|---|---|---|
| 1 | Sample loading | Waveform was noise | WAV via `sample_load` was read as 8-bit | Use `sample_create_from_pcm` (int16) | Bit-exact check of all samples |
| 2 | Single-channel probe | Lead and harmony silent at high notes | FT2 goes silent when note + relative note > ~118 (1024-sample loops used relative 60) | 256-sample loops, relative 36; bass kept at 1024 (max effective note 107) | Isolated probe at A5/C6/A6; render check |
| 3 | Mix check | Breakdown not quieter; volume settings ignored | Volume column was never written to the batch | Send the `volume` field | Cell-by-cell verify (volume included) |
| 4 | Band analysis | Harmony note rang through the breakdown | Fade was placed only before the next note on the channel, not at the note's end | Fade at the note's natural end or the next note, whichever is first | Per-bar RMS: breakdown now about 7 dB below the sections |
| 5 | Click check | Possible steps at kick and arp retriggers | One-shot tails were still live when the next note retriggered | Tails shaped to zero before the next trigger | Sample end values = 0; click scan |
| 6 | Mix check | Peaks at 1.0 with clipping | Too many loud sustained layers | Per-instrument volume trim | Peak 0.89, 0 clipped samples |
| 7 | Probe harness | Single-note tests showed the full song | Order list still played other patterns | Set order to one pattern for probes | Re-measured probes |
| 8 | Seam check | Possible click at restart | Notes still sounding at the end of the song | Final notes faded at the seam; seam sample step 0.0017 vs median 0.010 | Loop-region render analysis |
