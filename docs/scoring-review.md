# Scoring review

The listener-v1 score is 10 x the content-enjoyment rating that an AI listener, [Meta Audiobox Aesthetics](https://github.com/facebookresearch/audiobox-aesthetics), gives each tune's canonical FT2 render. Silent renders score 0 and baked-sample tunes are capped at 40. The contract is in [the benchmark guide](../benchmark/README.md#the-score).

## Why the score changed

The previous score (craft-v7 to craft-v10) added pitched clarity, development and dynamics, then multiplied by signal integrity and loop continuity. Its top-scoring tunes did not sound like the best ones. Three problems showed up in the data:

- Pitched clarity saturated: 82 of 208 attempts scored exactly 50/50, as did 132 of 256 human reference tunes. A clean sustained tone earned full credit.
- Dynamics saturated: 148 of 208 attempts scored at least 9.9/10.
- Development counted single held notes as recurring ideas, because every one-note voice had the same shape after transposition (fixed here, but the formula stayed a set of fixed rules that no one had checked against listening).

Over all 241 scored attempts, the old craft total and the listener agree (Spearman +0.80), because both mark broken tunes low. Among the old formula's top 20 they are unrelated (Spearman +0.02), so the old formula could not separate good tunes from great ones. After listening to the listener's ranking, the maintainer preferred it.

## How the listener works

The model was trained on about 97,000 speech, sound and music clips, each rated 1 to 10 by trained raters, 158 people in total ([Tjandra et al. 2025](https://arxiv.org/abs/2502.05139)). It predicts four ratings: content enjoyment, production quality, content usefulness and production complexity. Only enjoyment is scored. `benchmark/score_listener.py` resamples the first 120 seconds of the render to 16 kHz mono, rates 10-second windows with a WavLM-based transformer and averages them by window length.

It runs in its own environment (`benchmark/requirements-listener.txt`) on the CPU, with model revision `9b1dd8e5df9af7216e836a98974fe3b82c56ded6` and weights SHA-256 `a5a3c241…d014e` verified before every rating. The ranked-run evidence was computed on an Apple M5; an earlier Linux aarch64 CPU pass of all 241 attempts gave the same enjoyment ratings to within 1e-4.

Listener provenance also records the operating system, CPU architecture and Python version. These describe the execution environment, not a guarantee of bit-identical predictions across hosts.

## Provenance and coverage

[Ranked-attempt evidence](../data/listener-v1-runs.json): every `runs/<model>/attempt-N` slot on main f8ecfbf, 90 models and 270 slots, 241 scored and 29 unscored. No attempt was moved, replaced, deleted or rerun, and `other/` is excluded. Every XM and canonical WAV matched its source profile's SHA-256, and the scorer hashes in the file match this branch. It is review evidence, not a replacement profile generation.

[Reference evidence](../data/listener-v1-reference.json): all 256 pinned human keygen XMs. `render-references` rendered each native first pass on Linux aarch64; `references` verified those hashes and rated them. Caps are not applied to references.

Both evidence files were regenerated after preserving full listener-rating precision, fixing rescores of listener-v1 source profiles and adding listener host provenance. The latest run records Darwin arm64 with Python 3.14.6. All 241 attempt scores, model ranks and reference scores are unchanged. The stored enjoyment rating reproduces each uncapped attempt score exactly with `round(10 * rating, 1)`.

## Results

| | Ranked attempts (241) | Human references (256) |
| --- | ---: | ---: |
| 10th percentile | 24.5 | 52.0 |
| Median | 47.5 | 60.7 |
| 90th percentile | 65.6 | 70.5 |
| Maximum | 73.7 | 76.2 |

The calibration and held-out reference halves have medians of 60.4 and 61.7. The best model attempts reach the upper part of the human range; the median attempt sits below the 10th percentile of human tunes.

Seven attempts are capped, all for effectively silent renders. No ranked attempt hit the baked-sample cap.

Attempts by the same model agree more than attempts by different models: across the 74 models with three scored attempts, the variance between model means is 170 and the mean variance within a model is 90. The listener separates models, but one attempt is noisy, which is one reason ranking uses the best of three.

## Limitations

- The listener predicts human ratings; it is not a person. Its paper reports enjoyment predictions correlating about 0.66 to 0.75 with human ratings of music.
- It was not trained specifically on tracker or keygen music.
- On this corpus it leans toward longer tunes (Spearman +0.51 with duration) and slightly toward quieter ones (-0.31 with integrated loudness). The benchmark does not correct for either.
- Scores within a few points are effectively tied.
- The listener rates only the first 120 seconds. Later material cannot change its rating, but can change the final score through artifact caps, which use whole-render silence and sequencing measurements.
- The craft measurements remain as diagnostics in `craft.craft_diagnostics`. They explain construction; they do not move the score.

## Verification

- Score, mix, report and repository tests pass (102 tests and 54 subtests, offline, with a fake listener that exercises the real subprocess contract). Regression coverage includes serialized ratings at a rounding boundary, read-only rescores from craft-v7, craft-v9 and listener-v1 profiles, and rejection of pre-listener public snapshots before publication.
- An end-to-end native profile produces an eligible listener-v1 score, and the same attempt is marked unscored, not zero, when no listener environment is configured.
- Focused Ruff checks pass on changed Python. Frontend tests pass.

## Reproduce

Follow the listener setup in [the benchmark guide](../benchmark/README.md#prerequisites), then:

```sh
export KEYGEN_LISTENER_PYTHON="$PWD/.venv-listener/bin/python"
python benchmark/rescore.py runs --root runs --output /tmp/listener-v1-runs.json
python benchmark/rescore.py render-references --modules /absolute/reference-xms --out /tmp/reference-first-passes
python benchmark/rescore.py references --modules /absolute/reference-xms \
  --first-passes /tmp/reference-first-passes --output /tmp/listener-v1-reference.json
```

Reference modules must be named `<git_blob_sha>.xm` and match `data/keygen-duration-reference.json`. `render-references` needs the Linux FT2 analysis build. Rating takes minutes per tune on a 2-core machine; use a faster host for the listening steps.

## Every model

Best attempt per model by listener-v1 score; ties use model name for order only. The last column is the rank on the live site before this change (craft-v9); `-` means unranked there.

| Rank | Model | Best | Attempt | Live (craft-v9) rank |
| ---: | --- | ---: | ---: | ---: |
| 1 | gpt-6-sol | 73.7 | 1 | 5 |
| 2 | gpt-6.1-sol | 71.9 | 1 | 11 |
| 3 | mimo-v2.6-pro | 71.7 | 1 | 6 |
| 4 | deepseek-v4.1-flash | 70.8 | 2 | 18 |
| 5 | gpt-6-astra | 70.1 | 1 | 20 |
| 6 | claude-opus-5 | 69.8 | 1 | 15 |
| 7 | gemini-4-argon | 68.5 | 2 | 35 |
| 8 | glm-5.2 | 68.3 | 1 | 9 |
| 9 | gpt-5.6-sol | 67.2 | 1 | 7 |
| 10 | claude-fable-5.1 | 67.0 | 2 | 10 |
| 11 | claude-sonnet-5.5 | 66.5 | 1 | 4 |
| 12 | claude-sonnet-5 | 66.2 | 1 | 31 |
| 13 | hy4-preview | 65.7 | 3 | 17 |
| 14 | claude-haiku-5.5 | 65.5 | 2 | 28 |
| 15 | glm-5.3 | 64.6 | 1 | 3 |
| 16 | gpt-5.4 | 64.4 | 1 | 43 |
| 17 | hy3 | 64.3 | 3 | 41 |
| 18 | grok-4.6 | 64.0 | 1 | 2 |
| 19 | deepseek-v4-pro | 63.7 | 1 | 29 |
| 20 | gpt-5.6-terra | 63.4 | 2 | 22 |
| 21 | claude-opus-5.5 | 63.2 | 1 | 19 |
| 22 | mimo-v2.6-flash | 63.2 | 3 | 8 |
| 23 | claude-opus-4.7 | 62.5 | 3 | 14 |
| 24 | glm-5.3-flash | 62.2 | 3 | 53 |
| 25 | gpt-5.5 | 62.1 | 2 | 24 |
| 26 | claude-opus-4.8 | 61.9 | 3 | 21 |
| 27 | gpt-6-luna | 61.9 | 3 | 25 |
| 28 | kimi-k3 | 61.7 | 3 | 27 |
| 29 | step-5-preview | 61.6 | 3 | 1 |
| 30 | muse-spark-1.3-contributor | 61.4 | 3 | 30 |
| 31 | longcat-2.5-preview | 61.3 | 3 | 63 |
| 32 | grok-4.5 | 61.1 | 3 | 34 |
| 33 | qwen3.7-plus | 60.8 | 3 | 67 |
| 34 | deepseek-v4-flash | 60.7 | 1 | 37 |
| 35 | gemini-3.8-flash | 60.7 | 3 | 44 |
| 36 | space-bunny-free | 60.7 | 2 | - |
| 37 | claude-fable-5 | 60.4 | 1 | 12 |
| 38 | gemini-3-flash | 60.2 | 1 | 42 |
| 39 | grok-4.7 | 59.8 | 1 | 13 |
| 40 | qwen3.5-397b-a17b | 59.7 | 3 | 54 |
| 41 | gemini-3.7-flash | 59.3 | 1 | 33 |
| 42 | claude-sonnet-4.6 | 58.8 | 1 | 52 |
| 43 | grok-4.20-0309-reasoning | 57.9 | 3 | 51 |
| 44 | kimi-k2.6 | 57.7 | 2 | 55 |
| 45 | swe-2 | 56.6 | 1 | 40 |
| 46 | claude-opus-4.6 | 56.3 | 3 | 23 |
| 47 | grok-composer-2.5-fast | 55.5 | 1 | 38 |
| 48 | minimax-m2.7 | 54.3 | 1 | 65 |
| 49 | gpt-5.6-luna | 53.7 | 1 | 47 |
| 50 | minimax-m3 | 53.3 | 2 | 49 |
| 51 | gemini-3.1-pro-preview | 52.2 | 3 | 72 |
| 52 | gpt-5.4-mini | 52.1 | 2 | 68 |
| 53 | kimi-k2.7-code | 51.7 | 2 | 39 |
| 54 | command-a-plus-05-2026 | 51.5 | 3 | 59 |
| 55 | gemini-3.5-flash | 51.5 | 1 | 16 |
| 56 | gpt-5.3-codex | 51.5 | 1 | 48 |
| 57 | gemini-3.6-flash | 49.5 | 2 | 46 |
| 58 | hermes-4-405b | 49.0 | 2 | 56 |
| 59 | claude-opus-4.5 | 48.8 | 1 | 64 |
| 60 | swe-1.7-lightning | 48.2 | 3 | 45 |
| 61 | muse-glimmer-30b | 47.6 | 1 | 50 |
| 62 | mistral-large-4 | 47.2 | 2 | 32 |
| 63 | inkling | 47.1 | 1 | 70 |
| 64 | north-mini-code | 47.1 | 1 | 60 |
| 65 | step-3.7-flash | 45.4 | 2 | 26 |
| 66 | kimi-k2.7 | 45.3 | 1 | 73 |
| 67 | mimo-v2.5 | 42.4 | 2 | 57 |
| 68 | qwen3.8-flash | 42.2 | 2 | 74 |
| 69 | nemotron-3-ultra-550b-a55b | 40.5 | 2 | 58 |
| 70 | grok-4.3 | 38.4 | 2 | 69 |
| 71 | swe-1.6 | 37.9 | 2 | 81 |
| 72 | gpt-oss-120b | 36.8 | 2 | 75 |
| 73 | claude-haiku-4.5 | 36.6 | 1 | 36 |
| 74 | gpt-oss-20b | 36.2 | 1 | 76 |
| 75 | grok-build-0.1 | 33.6 | 2 | 71 |
| 76 | muse-spark-1.2-contributor | 33.1 | 3 | 82 |
| 77 | qwen3.8-27b | 32.9 | 2 | 77 |
| 78 | mercury-2.5 | 30.7 | 2 | 62 |
| 79 | gemma-4-31b-it | 29.7 | 1 | - |
| 80 | grok-4.20-0309-non-reasoning | 26.6 | 3 | 66 |
| 81 | grok-build | 25.3 | 2 | 79 |
| 82 | nemotron-3-super-120b-a12b | 24.7 | 2 | 80 |
| 83 | command-a-reasoning-08-2025 | 22.2 | 2 | 61 |
| 84 | nemotron-3.5-lightning | 20.7 | 3 | 78 |
| 85 | command-a-03-2025 | 0.0 | 2 | - |
| - | apodex-1.1-mini | - | - | - |
| - | dots-3-note-preview | - | - | - |
| - | ling-3.0-flash-sante | - | - | - |
| - | nemotron-3-nano-omni-30b-a3b-reasoning | - | - | - |
| - | qwen3.8-max | - | - | - |
