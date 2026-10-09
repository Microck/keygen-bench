# Scoring review

The score measures pitched clarity, development and dynamics, with signal and loop checks. It is not a validated measure of musical quality. The contract is in [the benchmark guide](../benchmark/README.md#evaluate-and-report).

## Decision and scope

- Development compares related changed voices across 4, 8 and 16 beats. Exact copies cannot establish transformation; the same voice must supply relationship and contrast. Voices have equal weight rather than note-density weighting.
- Pitched clarity contributes up to 50 points. Captured harmonic power receives full credit at 0.50, the reference bound. Whole-recording key concentration, tuning and pitch variety are diagnostics, not point multipliers.
- Signal integrity and bounded loop continuity multiply content points. Artifact caps limit the result. Duration and sustained noise are diagnostics. Noise-like music can earn fewer pitched-clarity points; the score is not stylistically neutral.
- Mel self-similarity is not used as development credit. It adds timbral sensitivity but does not by itself distinguish an evolving composition from a repeated cycle. The current method uses the XM's symbolic note information.

## Provenance and coverage

All 79 models and 237 ranked slots from the existing run snapshot are represented: 208 scored attempts and 29 unscored outcomes. No attempt was moved, replaced, deleted or rerun. `other/` remains excluded. Every scored XM and restored canonical WAV matched the source profile's SHA-256.

The [ranked-attempt evidence](../data/craft-v9-runs.json) recomputes spectral evidence from verified PCM and structural development from the submitted XM. It retains recorded signal, dynamics, mix and loop measurements, verifies unchanged mix/loop/playback source hashes, and records source-profile and current scorer hashes. It is a review rescore, not a fresh profile generation. Original profiles and evaluation generations are unchanged.

The [reference evidence](../data/craft-v9-reference.json) covers all 256 pinned reference XMs. It records the native renderer identity and analyzes first-pass PCM up to the first native return or authored F00 stop: 251 returns and 5 stops. Development includes all sequenced channels. These are descriptive distributions, not controlled listener validation.

The separate review website contains all 198 playable attempts from the inspected published snapshot, matched by both XM and canonical WAV hashes. Its 71 scored models differ from the 74 scored models in the full committed corpus. Historical profiles and the live leaderboard remain untouched.

## Terra and Mercury

| Model | Attempt | development /40 | total |
| --- | ---: | ---: | ---: |
| gpt-5.6-terra | 1 | 15.55 | 56.70 |
| gpt-5.6-terra | 2 | 10.75 | 70.60 |
| gpt-5.6-terra | 3 | 9.35 | 50.90 |
| mercury-2.5 | 1 | 0.27 | 52.40 |
| mercury-2.5 | 2 | 17.69 | 40.30 |
| mercury-2.5 | 3 | unscored | unscored |

Mercury's short repeated first attempt receives 0.27/40 development points and 50/50 pitched-clarity points, for a total of 52.4. It outranks Mercury's developed second attempt at 40.3, and Terra's third attempt at 50.9.

Terra's best is attempt 2 at 70.6, ranked 19 in the full corpus. The score was not tuned to favor Terra or demote Mercury.

## Saturation and ranking risk

**82 of 208 scored attempts receive exactly 50.00/50 pitched-clarity points. So do 132 of 256 reference modules.** A clean sustained tone also earns full clarity credit. This component measures pitched sound rather than melodic merit. The 50/40/10 weights can let clear but repetitive music outrank developed noisier music, as the Mercury attempts demonstrate.

The results do not establish agreement with listeners. Release claims must describe the score as a diagnostic, not validated musical fairness.

## Reference component distributions

| Subset | Count | clarity median /50 | development median /40 | development p90 /40 |
| --- | ---: | ---: | ---: | ---: |
| all | 256 | 50.000 | 11.350 | 18.850 |
| calibration | 113 | 50.000 | 11.420 | 19.162 |
| held_out | 108 | 50.000 | 10.830 | 16.941 |
| additional references | 35 | 50.000 | 12.520 | 19.902 |

## Remaining limitations

- The reference corpus is one genre, not listener judgments. No constants were fitted to these rankings or distributions.
- Fixed beat windows and exact onset matching can miss expressive timing. Handoffs inside a passage split voices. Equal voice weighting is not perceptual loudness weighting.
- Symbolic development can miss timbral and through-composed development. Squared overlap and the three timescales remain policy choices.
- The pitch detector can miss weak fundamentals, absorb harmonically related simultaneous notes, and mistake periodic corruption for instruments. Noise-like composition is not a defect, yet earns less pitched credit.
- Signal integrity and loop rules have stylistic assumptions. The score does not claim to remove every preference or gaming opportunity.

## Verification

- 275 benchmark tests, 25 repository tests and 9 frontend tests passed. The 31 contributor tests also passed after checking bootstrap without site packages.
- Focused Ruff correctness checks passed for all changed Python code. No separate project type-check command is configured.
- Controlled spectral tests cover natural/harmonic minor, chromatic and stationary pitch, slow notes, loop rotations below saturation, noise, quantization, tuning, gain and channel polarity. Aggregate tests verify that duration and noise diagnostics do not discount content.
- A fresh synthetic local Docker submission passed sandbox collection, trusted FT2 rendering and craft-v9 profiling at 45.3. Zero provider requests; owned containers and volumes removed.
- All 208 eligible attempts rescored, and all 256 reference modules rendered and analyzed. Current scorer hashes match the evidence.
- The separate review site displayed the scoring explanation and two-factor calculator. Mercury selected attempt 1 at 52.4; Terra selected attempt 2 at 70.6. Mercury audio playback advanced and Stop worked. Browser error logs were empty.
- The release export smoke checked scorer-version rejection, verified synthetic media and a fresh collector/builder publication. The release preserves all 198 published attempts, matched against source-profile, XM and WAV hashes. Browser playback advanced; the scoring formula and donation QR assets rendered correctly.
- Static export generated 147 routes and 72 preview images with all 198 attempts and 594 existing hosted-media URLs. External playback traces and donation QR images are preserved.
- Code-reuse, quality and efficiency simplification checks ran inline, not as independent reviewers. No additional refactor was needed; bounded window processing and memory-mapped review PCM remain.

## Reproduce

Use the pinned Python environment and install `flac`. Run from the repository root, choosing new output paths:

```sh
python benchmark/rescore.py runs --root runs --output /tmp/craft-v9-runs.json
python benchmark/rescore.py references --modules /absolute/reference-xms --output /tmp/craft-v9-reference.json
```

Reference modules must be named `<git_blob_sha>.xm` and match `data/keygen-duration-reference.json`. These commands perform no network fetch, inference or publication.

## Every model

Ranks cover the 74 scored models in the full committed snapshot. Ties use model name for table order only; best-score ties select the lowest ordinal. Unscored slots remain null, not zero.

| Model | Scored slots | rank | best | ordinal |
| --- | ---: | ---: | ---: | ---: |
| grok-4.6 | 3/3 | 1 | 76.3 | 3 |
| glm-5.3 | 3/3 | 2 | 75.5 | 2 |
| claude-sonnet-5.5 | 3/3 | 3 | 75.4 | 1 |
| gpt-6-sol | 3/3 | 4 | 75.4 | 1 |
| mimo-v2.6-pro | 3/3 | 5 | 75.3 | 1 |
| gpt-5.6-sol | 3/3 | 6 | 74.6 | 1 |
| glm-5.2 | 3/3 | 7 | 73.5 | 3 |
| claude-fable-5.1 | 3/3 | 8 | 73.0 | 3 |
| gpt-6.1-sol | 3/3 | 9 | 72.7 | 3 |
| claude-fable-5 | 3/3 | 10 | 72.4 | 2 |
| grok-4.7 | 3/3 | 11 | 72.3 | 1 |
| claude-opus-4.7 | 3/3 | 12 | 72.1 | 3 |
| claude-opus-5 | 3/3 | 13 | 72.1 | 1 |
| gemini-3.5-flash | 3/3 | 14 | 72.1 | 1 |
| deepseek-v4.1-flash | 3/3 | 15 | 72.0 | 2 |
| claude-opus-5.5 | 3/3 | 16 | 71.6 | 2 |
| gpt-6-astra | 3/3 | 17 | 71.6 | 1 |
| claude-opus-4.8 | 3/3 | 18 | 70.8 | 2 |
| gpt-5.6-terra | 3/3 | 19 | 70.6 | 2 |
| claude-opus-4.6 | 3/3 | 20 | 70.5 | 3 |
| gpt-5.5 | 3/3 | 21 | 70.5 | 2 |
| gpt-6-luna | 3/3 | 22 | 70.5 | 3 |
| step-3.7-flash | 3/3 | 23 | 70.5 | 1 |
| kimi-k3 | 3/3 | 24 | 70.3 | 1 |
| claude-haiku-5.5 | 3/3 | 25 | 70.2 | 2 |
| deepseek-v4-pro | 3/3 | 26 | 69.8 | 1 |
| muse-spark-1.3-contributor | 3/3 | 27 | 69.8 | 1 |
| claude-sonnet-5 | 3/3 | 28 | 69.6 | 1 |
| mistral-large-4 | 3/3 | 29 | 69.6 | 2 |
| gemini-3.7-flash | 3/3 | 30 | 69.4 | 1 |
| grok-4.5 | 3/3 | 31 | 69.2 | 3 |
| hy4-preview | 2/3 | 32 | 68.8 | 3 |
| claude-haiku-4.5 | 3/3 | 33 | 67.8 | 1 |
| deepseek-v4-flash | 3/3 | 34 | 67.7 | 1 |
| kimi-k2.7-code | 3/3 | 35 | 67.2 | 3 |
| swe-2 | 3/3 | 36 | 67.1 | 3 |
| hy3 | 3/3 | 37 | 66.9 | 3 |
| gemini-3-flash | 3/3 | 38 | 66.7 | 3 |
| gpt-5.4 | 3/3 | 39 | 66.2 | 2 |
| gemini-3.8-flash | 3/3 | 40 | 66.1 | 3 |
| swe-1.7-lightning | 3/3 | 41 | 65.9 | 1 |
| gemini-3.6-flash | 3/3 | 42 | 65.3 | 2 |
| gpt-5.6-luna | 3/3 | 43 | 64.8 | 1 |
| gpt-5.3-codex | 3/3 | 44 | 64.0 | 1 |
| minimax-m3 | 3/3 | 45 | 62.4 | 1 |
| muse-glimmer-30b | 3/3 | 46 | 61.9 | 1 |
| claude-sonnet-4.6 | 3/3 | 47 | 61.5 | 1 |
| glm-5.3-flash | 2/3 | 48 | 61.3 | 3 |
| qwen3.5-397b-a17b | 3/3 | 49 | 58.8 | 1 |
| kimi-k2.6 | 3/3 | 50 | 57.5 | 2 |
| hermes-4-405b | 2/3 | 51 | 57.0 | 2 |
| space-bunny-free | 3/3 | 52 | 55.9 | 2 |
| nemotron-3-ultra-550b-a55b | 3/3 | 53 | 55.3 | 2 |
| command-a-plus-05-2026 | 3/3 | 54 | 55.1 | 3 |
| north-mini-code | 3/3 | 55 | 54.2 | 1 |
| command-a-reasoning-08-2025 | 1/3 | 56 | 53.8 | 2 |
| mercury-2.5 | 2/3 | 57 | 52.4 | 1 |
| claude-opus-4.5 | 3/3 | 58 | 43.6 | 3 |
| minimax-m2.7 | 3/3 | 59 | 43.6 | 2 |
| qwen3.7-plus | 3/3 | 60 | 41.1 | 3 |
| gpt-5.4-mini | 3/3 | 61 | 40.9 | 2 |
| inkling | 3/3 | 62 | 38.1 | 2 |
| gemini-3.1-pro-preview | 3/3 | 63 | 36.2 | 3 |
| kimi-k2.7 | 3/3 | 64 | 34.4 | 1 |
| qwen3.8-flash | 3/3 | 65 | 34.4 | 1 |
| gpt-oss-120b | 2/3 | 66 | 33.9 | 3 |
| gpt-oss-20b | 2/3 | 67 | 33.8 | 1 |
| qwen3.8-27b | 1/3 | 68 | 33.2 | 2 |
| nemotron-3.5-lightning | 2/3 | 69 | 31.2 | 3 |
| nemotron-3-super-120b-a12b | 3/3 | 70 | 30.0 | 3 |
| swe-1.6 | 3/3 | 71 | 28.3 | 2 |
| muse-spark-1.2-contributor | 3/3 | 72 | 25.3 | 2 |
| gemma-4-31b-it | 1/3 | 73 | 9.4 | 1 |
| command-a-03-2025 | 2/3 | 74 | 0.0 | 2 |
| apodex-1.1-mini | 0/3 | - | - | - |
| dots-3-note-preview | 0/3 | - | - | - |
| ling-3.0-flash-sante | 0/3 | - | - | - |
| nemotron-3-nano-omni-30b-a3b-reasoning | 0/3 | - | - | - |
| qwen3.8-max | 0/3 | - | - | - |
