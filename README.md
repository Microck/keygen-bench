# Keygen Bench

A benchmark for language models composing tracker music with FastTracker II. A model gets one Bash tool in an offline Docker sandbox, creates an XM module, and submits it for independent rendering and scoring.

This repository contains the runner, pinned container build, evaluator, results website and community submission tools. It contains no keygens, cracks or license-bypass code.

## Run a model

Start with [Contributing runs](CONTRIBUTING-RUNS.md). The guided CLI builds the environment, configures a provider, checks prerequisites and runs a smoke attempt or the three-attempt submission workflow. API-key presets include OpenAI and Anthropic; custom services can use compatible Chat Completions, Responses or Messages endpoints. OAuth routes use your own authorized local bridge.

Model requests can cost money. Credentials stay outside the model's sandbox and must never be committed. Keep your own working runs outside the repository; publish only reviewed bundles.

For campaign configuration, evaluation and reporting, see [the benchmark guide](benchmark/README.md).

## Results and scoring

The evaluator renders the submitted XM in a fresh FT2 process. Craft-v7 measures tonal organization, development and dynamics, with audio, loop and duration adjustments. It is an auxiliary diagnostic, not a validated measure of musical quality. Listen to the music before interpreting a score as a preference.

Community submissions remain labelled separately until the maintainer verifies their provenance and re-renders and re-scores the module. A bundle validator cannot prove which model produced a file or that no undisclosed attempts occurred.

The [website guide](web/classic/README.md) explains how to export a reviewed local snapshot, build the FT2-style site and generate link previews. Deployed sites are generated outputs, not repository source.

Every attempt behind the published results is in [`runs/`](runs/README.md): one folder per model with its three ranked attempts and everything else (failed, retried and older runs) under `other/`. Videos are omitted and audio is stored as lossless FLAC.

## Repository layout

| Path | Purpose |
| --- | --- |
| `benchmark/` | Campaign runner, provider adapters, prompts, container build and evaluator |
| `benchmark/contrib/` | Community-run packaging and validation |
| `benchmark/tests/`, `tests/` | Offline regression tests and synthetic fixtures |
| `scripts/`, `tools/` | Pinned FT2 builds and native acceptance checks |
| `runs/` | Every recorded attempt of the maintainer campaigns, by model |
| `data/` | Scoring calibration metadata, without archived music |
| `web/classic/` | Results frontend and local publication tools |
| `submissions/` | Reviewed community bundles |

## Development

For code or documentation changes, follow [AGENTS.md](AGENTS.md). It links the task-specific guides and defines privacy, experiment provenance and verification requirements.

Use the pinned requirements and build instructions in the benchmark guide. Tests do not require paid model calls:

```sh
python -m unittest discover -s benchmark/tests
python -m unittest discover -s tests
node --test tests/test_classic_player.mjs tests/test_classic_rankings.mjs
```

Some integration tests require the pinned dependencies or a native FT2 build. Passing offline tests does not establish provider access, musical quality or production readiness.

Read [NOTICE.md](NOTICE.md) for third-party attribution and [the public-launch checklist](PUBLIC-LAUNCH.md) before publishing a formerly private checkout.
