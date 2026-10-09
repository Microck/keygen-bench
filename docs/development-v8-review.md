# Craft-v8 development review

This review changes development scoring only. It does not establish that craft-v8 agrees with listener preference. The scoring contract and formula are in [the benchmark guide](../benchmark/README.md#evaluate-and-report).

## Scope and provenance

- Base source and run snapshot: commit `55e23478`.
- Every ranked `attempt-N` folder in that snapshot is represented: 79 models, 237 slots, 208 scored attempts and 29 unscored outcomes. All 198 playable attempts in the inspected published snapshot matched a rescored XM hash.
- Historical `other/` attempts are excluded. No attempts were moved, substituted, deleted or rerun.
- Every scored XM and restored canonical WAV matched its source profile's SHA-256. The rescorer verified unchanged audio, mix, loop and playback source hashes and reproduced every old aggregate before replacing development.
- Existing audio/mix/loop measurements were reused, not re-rendered for the comparison. Original profiles and evaluation generations remain unchanged. The review JSON is not a replacement profile generation or a deployment dataset.
- The [attempt evidence](../data/development-v8-runs.json) includes component changes, retained factors, hashes and best-attempt selection. The [reference evidence](../data/development-v8-reference.json) includes all 256 pinned reference XMs and the existing split labels.

## Decision

Use symbolic self-similarity at 4, 8 and 16 beats. Compare each voice's onset/pitch content with other passages, independent of instrument and channel labels. An exact voice copy supplies no transformation evidence. A voice must itself supply the relationship and contrast; a repeated accompaniment cannot certify an unrelated melody. Voices receive equal weight, not weight proportional to note density.

Mel self-similarity remains a useful listening aid, but is not used as development credit. It adds sensitivity to timbral changes without resolving whether a repeated cycle develops. This revision uses the XM's exact symbolic information and keeps audio measurements unchanged to isolate the score change.

## Terra and Mercury

| Model | Attempt | v7 development /40 | v8 development /40 | v7 total | v8 total |
| --- | --- | ---: | ---: | ---: | ---: |
| gpt-5.6-terra | 1 | 21.91 | 15.55 | 55.9 | 51.2 |
| gpt-5.6-terra | 2 | 13.53 | 10.75 | 72.4 | 69.7 |
| gpt-5.6-terra | 3 | 12.41 | 9.35 | 52.8 | 50.5 |
| mercury-2.5 | 1 | 28.28 | 0.27 | 30.3 | 16.5 |
| mercury-2.5 | 2 | 4.00 | 17.69 | 19.2 | 30.8 |
| mercury-2.5 | 3 | unscored | unscored | unscored | unscored |

The rule was not tuned to increase Terra's absolute score. Mercury's repeated short first attempt loses development credit; its longer second attempt becomes its best. The three ordinal slots remain the same.

Across all scored attempts, 156 totals decrease, 36 increase and 16 stay unchanged. Twelve models select a different best ordinal. Do not compare a v7 total against a v8 total as if they used the same scale.

## Human reference distribution

These are development points, not human quality ratings.

| Subset | Count | v7 median | v8 median | v7 p90 | v8 p90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 256 | 14.77 | 11.35 | 26.74 | 18.85 |
| calibration | 113 | 14.6 | 11.42 | 26.434 | 19.162 |
| held_out | 108 | 15.405 | 10.83 | 26.805 | 16.941 |
| unscored_in_v6 | 35 | 13.94 | 12.52 | 26.278 | 19.902 |

Only 13 of the 256 archived v7 development values meet or exceed Mercury attempt 1's former 28.28 points. That is evidence of the old metric's behavior, not proof that the archive defines musical merit.

The reference comparison has an important limitation: the archived v7 values used rendered audibility filtering, while this development-only v8 reference pass includes all sequenced channels. It verifies coverage and gives context for the scale, but is not a paired audibility-controlled listener validation. Constants were not fitted to these distributions. The original calibration and held-out labels are retained; this review does not turn them into preference labels.

## Known limitations

- Fixed 4/8/16-beat windows are not inferred musical phrase boundaries. Exact onset matching and first-note normalization can miss expressive timing and ornamented starts.
- Channel handoffs between passages can match. Handoffs inside a passage still split voices.
- Equal voice weighting is not perceptual loudness weighting. Sparse, timbral and through-composed music remain difficult cases.
- Squared overlap and the three timescales are explicit policy choices, not listener-derived weights. The new reference median is lower; no rescaling was added to recover the old range.
- This fixes measured failure modes, not every possible way to optimize a heuristic. Blind listening is still needed before calling the ranking fairer in aesthetic terms.
- The preserved tonal, noise, duration and loop policies retain their existing stylistic assumptions.

## Verification

- 276 benchmark tests passed, including the native evaluator tests and new development/rescore boundary coverage.
- 23 repository tests and 9 frontend tests passed.
- Focused Ruff correctness checks passed for every changed Python implementation and test file. No separate project type-check command is configured.
- A synthetic offline submission passed the actual local Docker collection, trusted FT2 rendering and full craft-v8 evaluation. No model/provider requests ran. Its containers and volumes were removed.
- The isolated local website displayed the revised development explanation and recalculated rankings. Terra selected attempt 2 at 69.7; Mercury selected attempt 2 at 30.8 and retained its failed third slot. Browser errors were empty. No live site files were changed.
- Initial native verification failed resource admission while the shared host was swapping. After memory became available, the full suite and Docker smoke passed without changing resource guards.

## Reproduce

Use the pinned Python environment and install `flac`. Run from the repository root, choosing new output paths:

```sh
python benchmark/rescore.py runs --root runs --output /tmp/craft-v8-runs.json
python benchmark/rescore.py references --modules /absolute/reference-xms --output /tmp/craft-v8-reference.json
```

Reference modules must be named `<git_blob_sha>.xm` and match the pinned URLs and SHA-256 values in `data/keygen-duration-reference.json`. The commands perform no network fetch, inference or publication.

## Every model

Ranks here cover all 74 scored models in the committed run snapshot, including records not present in the 71-model published listening view. Ties use model name for table order only. Best-score ties select the lowest ordinal. Unscored slots remain null, not zero.

| Model | Scored slots | v7 rank | v8 rank | v7 best | v8 best | v7 ordinal | v8 ordinal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpt-6-sol | 3/3 | 12 | 1 | 77.4 | 75.3 | 1 | 1 |
| glm-5.3 | 3/3 | 1 | 2 | 83.3 | 72.8 | 2 | 2 |
| mimo-v2.6-pro | 3/3 | 10 | 3 | 77.8 | 72.6 | 3 | 1 |
| gpt-6.1-sol | 3/3 | 23 | 4 | 74.1 | 71.6 | 3 | 1 |
| grok-4.6 | 3/3 | 6 | 5 | 79.5 | 71.4 | 3 | 3 |
| gpt-6-astra | 3/3 | 20 | 6 | 74.8 | 70.7 | 3 | 1 |
| grok-4.7 | 3/3 | 38 | 7 | 67.0 | 70.2 | 1 | 1 |
| gpt-5.6-terra | 3/3 | 29 | 8 | 72.4 | 69.7 | 2 | 2 |
| gpt-5.6-sol | 3/3 | 33 | 9 | 70.8 | 69.5 | 3 | 1 |
| gpt-6-luna | 3/3 | 36 | 10 | 68.4 | 69.4 | 3 | 3 |
| claude-fable-5.1 | 3/3 | 18 | 11 | 75.1 | 69.2 | 2 | 3 |
| claude-opus-5 | 3/3 | 9 | 12 | 78.1 | 69.1 | 2 | 1 |
| claude-sonnet-5 | 3/3 | 8 | 13 | 78.5 | 68.8 | 1 | 1 |
| claude-opus-4.7 | 3/3 | 28 | 14 | 72.7 | 68.4 | 2 | 3 |
| claude-opus-4.6 | 3/3 | 16 | 15 | 75.8 | 68.2 | 3 | 3 |
| claude-opus-5.5 | 3/3 | 22 | 16 | 74.3 | 68.2 | 2 | 2 |
| muse-spark-1.3-contributor | 3/3 | 4 | 17 | 79.7 | 68.0 | 1 | 1 |
| hy4-preview | 2/3 | 37 | 18 | 67.5 | 67.9 | 3 | 3 |
| claude-sonnet-5.5 | 3/3 | 41 | 19 | 63.5 | 67.3 | 1 | 1 |
| deepseek-v4.1-flash | 3/3 | 13 | 20 | 76.8 | 67.3 | 2 | 2 |
| grok-4.5 | 3/3 | 21 | 21 | 74.7 | 67.3 | 3 | 3 |
| kimi-k3 | 3/3 | 7 | 22 | 79.4 | 67.0 | 1 | 1 |
| swe-2 | 3/3 | 2 | 23 | 80.3 | 67.0 | 3 | 3 |
| claude-haiku-5.5 | 3/3 | 25 | 24 | 73.3 | 66.8 | 2 | 2 |
| step-3.7-flash | 3/3 | 35 | 25 | 68.6 | 66.7 | 1 | 1 |
| deepseek-v4-flash | 3/3 | 15 | 26 | 76.2 | 66.1 | 1 | 1 |
| gpt-5.5 | 3/3 | 34 | 27 | 69.0 | 65.4 | 2 | 2 |
| glm-5.2 | 3/3 | 30 | 28 | 72.3 | 64.8 | 2 | 3 |
| claude-opus-4.8 | 3/3 | 14 | 29 | 76.3 | 64.7 | 3 | 3 |
| gpt-5.6-luna | 3/3 | 3 | 30 | 79.7 | 64.3 | 1 | 1 |
| gpt-5.4 | 3/3 | 32 | 31 | 71.6 | 64.2 | 2 | 2 |
| deepseek-v4-pro | 3/3 | 5 | 32 | 79.6 | 63.6 | 2 | 1 |
| kimi-k2.7-code | 3/3 | 31 | 33 | 72.0 | 63.3 | 2 | 2 |
| hy3 | 3/3 | 19 | 34 | 75.1 | 63.1 | 3 | 3 |
| gemini-3.5-flash | 3/3 | 11 | 35 | 77.5 | 62.2 | 2 | 1 |
| gemini-3.8-flash | 3/3 | 40 | 36 | 65.1 | 60.6 | 3 | 3 |
| gemini-3.6-flash | 3/3 | 24 | 37 | 73.5 | 59.5 | 2 | 2 |
| mistral-large-4 | 3/3 | 44 | 38 | 58.5 | 59.0 | 2 | 2 |
| gemini-3.7-flash | 3/3 | 42 | 39 | 61.0 | 58.8 | 1 | 1 |
| claude-haiku-4.5 | 3/3 | 48 | 40 | 54.4 | 58.6 | 1 | 1 |
| claude-fable-5 | 3/3 | 43 | 41 | 60.3 | 58.1 | 2 | 2 |
| kimi-k2.6 | 3/3 | 27 | 42 | 72.9 | 57.0 | 2 | 2 |
| gemini-3-flash | 3/3 | 17 | 43 | 75.4 | 56.1 | 1 | 1 |
| qwen3.5-397b-a17b | 3/3 | 26 | 44 | 73.2 | 54.3 | 1 | 1 |
| gpt-5.3-codex | 3/3 | 46 | 45 | 55.0 | 54.1 | 1 | 1 |
| claude-sonnet-4.6 | 3/3 | 39 | 46 | 65.8 | 52.6 | 1 | 1 |
| space-bunny-free | 3/3 | 45 | 47 | 56.2 | 52.6 | 2 | 2 |
| glm-5.3-flash | 2/3 | 47 | 48 | 54.7 | 49.8 | 3 | 3 |
| minimax-m2.7 | 3/3 | 50 | 49 | 48.4 | 41.3 | 2 | 2 |
| qwen3.7-plus | 3/3 | 49 | 50 | 50.7 | 40.8 | 3 | 3 |
| muse-glimmer-30b | 3/3 | 51 | 51 | 47.3 | 37.4 | 1 | 1 |
| swe-1.7-lightning | 3/3 | 52 | 52 | 43.0 | 37.3 | 3 | 1 |
| inkling | 3/3 | 55 | 53 | 37.2 | 32.8 | 2 | 2 |
| mercury-2.5 | 2/3 | 58 | 54 | 30.3 | 30.8 | 1 | 2 |
| claude-opus-4.5 | 3/3 | 56 | 55 | 36.8 | 30.0 | 3 | 3 |
| gemini-3.1-pro-preview | 3/3 | 53 | 56 | 42.5 | 30.0 | 3 | 3 |
| minimax-m3 | 3/3 | 57 | 57 | 34.9 | 29.6 | 1 | 1 |
| swe-1.6 | 3/3 | 64 | 58 | 16.5 | 24.9 | 2 | 2 |
| nemotron-3-ultra-550b-a55b | 3/3 | 61 | 59 | 22.8 | 21.4 | 2 | 2 |
| qwen3.8-flash | 3/3 | 60 | 60 | 23.0 | 21.0 | 3 | 3 |
| kimi-k2.7 | 3/3 | 59 | 61 | 27.3 | 20.0 | 2 | 2 |
| hermes-4-405b | 2/3 | 54 | 62 | 38.5 | 15.3 | 2 | 2 |
| command-a-plus-05-2026 | 3/3 | 62 | 63 | 19.4 | 14.6 | 3 | 3 |
| north-mini-code | 3/3 | 63 | 64 | 18.8 | 14.2 | 1 | 1 |
| gpt-5.4-mini | 3/3 | 65 | 65 | 12.1 | 12.5 | 1 | 1 |
| qwen3.8-27b | 1/3 | 67 | 66 | 9.0 | 7.6 | 2 | 2 |
| gpt-oss-120b | 2/3 | 68 | 67 | 6.5 | 7.2 | 2 | 2 |
| nemotron-3-super-120b-a12b | 3/3 | 66 | 68 | 10.5 | 4.8 | 2 | 2 |
| muse-spark-1.2-contributor | 3/3 | 69 | 69 | 5.8 | 4.5 | 2 | 2 |
| gpt-oss-20b | 2/3 | 70 | 70 | 4.1 | 4.1 | 3 | 3 |
| nemotron-3.5-lightning | 2/3 | 71 | 71 | 3.9 | 4.0 | 3 | 3 |
| command-a-reasoning-08-2025 | 1/3 | 72 | 72 | 2.2 | 2.2 | 2 | 2 |
| gemma-4-31b-it | 1/3 | 73 | 73 | 0.2 | 0.2 | 1 | 1 |
| command-a-03-2025 | 2/3 | 74 | 74 | 0.0 | 0.0 | 2 | 2 |
| apodex-1.1-mini | 0/3 | - | - | unscored | unscored | - | - |
| dots-3-note-preview | 0/3 | - | - | unscored | unscored | - | - |
| ling-3.0-flash-sante | 0/3 | - | - | unscored | unscored | - | - |
| nemotron-3-nano-omni-30b-a3b-reasoning | 0/3 | - | - | unscored | unscored | - | - |
| qwen3.8-max | 0/3 | - | - | unscored | unscored | - | - |
