# Changelog

## [Unreleased]

### Changed
- Replace workflow and raw-count scoring bonuses with deterministic artifact-only craft-v7 tonal-development evidence
- Score audio-derived tonal organization, retained-motif development and dynamics; apply signal, sustained-noise and bounded loop-continuity multipliers instead of additive delivery bonuses
- Apply a uniform duration-sufficiency factor below 30 audible first-pass seconds, informed by a reproducible 256-module historical sample; no length bonus above the threshold
- Calibrate tonal-fraction, diatonic-concentration, sustained-noise, DC-offset and restart level/timbre bounds against 256 archived keygen XMs, with a hash-split calibration half and held-out validation; genuine tracks no longer lose most of their points to a-priori thresholds
- Use pinned continuous FT2 playback for loop scoring and source-separated mix analysis, with exact transition timestamps and lossless listening excerpts
- Extend reference stem analysis through 22.05 kHz and retain uncertain selected-lead masking as a diagnostic, not an aggregate scoring input
- Remove order-table-rewriting listening packets; profiling now produces actual-runtime loop previews
- Publish content subtotals, multipliers, full-band spectral evidence and explicit musical-quality limitations without model-specific rules or per-run adjustments
- Keep runtime transition continuity and lossless loop previews while limiting their whole-score effect to a 0.75–1 multiplier
- Display Muse Spark 1.2 and 1.3 without Contributor billing-tier suffixes; retain original attempt identities and pricing evidence
- Finalize the Support introduction and donation instructions
- Publish the Codex-auth GPT-6.1 Sol result and its official API list-price estimate

### Fixed
- Preserve opposite-polarity stereo energy when detecting silence
- Calculate clipping from the actual sample count and ignore unused samples when applying baked-audio caps
- Respect nonzero restart positions and carried playback state instead of treating WAV export endpoints as loop points
- Prevent silent boundaries and brief clear melodic fragments from receiving misleadingly high loop or mix scores
- Match FT2's 64-row normalization of entirely empty patterns
- Prevent clean repeated noise from receiving free audio and loop points; distinguish sustained noise from short percussion without blanket 8-bit or bright-waveform penalties
- Require changed parts to retain their own motifs; repeating accompaniment cannot certify arbitrary melody changes as development
- Prevent repeated exports and silent padding from supplying missing first-pass duration; retain legitimate short loops without a hard eligibility cutoff
- Load historical XMs the way the pinned FT2 loader does: orders naming absent patterns play empty 64-row patterns, and instruments missing from a truncated file are empty

## 1.0.0 — 2026-09-04

- Added structured English research on historical authoring programs.
- Separated tracker modules from procedural-synth workflows.
- Documented composition, sample design, effects, looping, optimization, and runtime replay.
- Added a source register and confidence methodology.
- Added public archive metadata case studies without redistributing music.
- Added machine-readable tool, claim, and archive-example data.
- Added a dependency-free XM/IT/S3M/MOD header inspector and synthetic tests.
