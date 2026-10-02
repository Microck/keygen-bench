# Run and evaluate the benchmark

For a three-attempt community submission, use [Contributing runs](../CONTRIBUTING-RUNS.md). The wrapper prepares the model configuration and packages every outcome. The lower-level commands below are for maintaining campaigns and evaluating results.

## Prerequisites

Use Linux, Python 3.11 or later, Docker Engine and the pinned controller requirements. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r benchmark/requirements.txt
docker build -f benchmark/Dockerfile --target agent -t keygen-ft2-benchmark:local .
docker build -f benchmark/Dockerfile --target visualizer -t keygen-ft2-visualizer:local .
```

The Dockerfile pins the Debian base digest and the build script pins FT2 source. Build acceptance exercises native editing, saving, reloading and rendering. Record the final image IDs with `docker image inspect`; mutable tags are not experiment identities. Architecture and distribution package state can affect the final image.

Craft-v7 additionally needs the analysis renderer. Install a C compiler, Git, pkg-config, SDL2 and libmicrohttpd development packages, then run:

```sh
python scripts/build-ft2-analysis.py
```

The script checks the source commit and capture patch and writes a binary with provenance metadata to the user's cache directory. `KEYGEN_FT2_ANALYSIS` selects a different verified build.

## Execution contract

The runner uses mini-swe-agent 2.4.6 with one Bash tool. Model commands execute in a network-disabled local Docker sandbox. Provider credentials stay in the controller's model worker, not in the command sandbox. Do not mount personal or company files into either environment.

Community runs freeze prompt-v2 and these limits:

| Limit | Value |
| --- | --- |
| Independent attempts | 3, including failures |
| Attempt wall time | 120 minutes |
| Step limit | None |
| Command timeout | 120 seconds |
| Model request timeout | 60 minutes |
| Submission | `/workspace/submission/tune.xm` |
| Submission directory | 128 MiB, at most 4096 regular files |
| Canonical render | 44.1 kHz, 16-bit stereo |

The system prompt documents output truncation and submission handling. The task prompt defines the music task. Do not edit prompts or limits for an attempt intended to share the same experimental condition.

Provider protocols, exact model identity, generation settings, reasoning tier, image IDs and dependency provenance are recorded. A declared highest reasoning tier means the highest documented control on that route, not equal compute across providers. Configuration must not silently substitute another checkpoint or route.

## Configure a campaign

Keep working configuration, credentials and run artifacts outside this checkout. `config/campaign.example.json` shows the selection structure; it is not a ready-to-run campaign. Fill in actual immutable image IDs, model configuration and verified readiness evidence.

A real multi-turn native readiness pilot must execute tool calls and validate the returned model identity. `native_readiness.py --help` describes pilot inputs. The compiler requires an explicit inventory, selection and tier specification; the repository contains no private account inventory.

Google AI Studio routes use `provider: google` with the pinned SDK's `gemini/` prefix and `GEMINI_API_KEY`; the declared tier is sent as `thinkingLevel` and the returned `modelVersion` must match the frozen identity. Devin routes use `provider: devin`, `api: chat` and the `openai/` prefix through a user-authorized local bridge; the requested alias and the expected returned identity are separate frozen fields, and the bridge executable digest is part of readiness.

```sh
python benchmark/campaign.py \
  --inventory /absolute/private/inventory.json \
  --selection /absolute/private/selection.json \
  --tier-spec /absolute/private/tier-spec.json \
  --out /absolute/private/campaign.json
python benchmark/run.py doctor \
  --campaign /absolute/private/campaign.json --out /absolute/private/runs
python benchmark/run.py run \
  --campaign /absolute/private/campaign.json --out /absolute/private/runs --workers 1
```

The worker count must match the frozen configuration. Keep concurrency conservative; inference, rendering and video have separate resource limits. The local artifact directory must support locking and atomic renames. It is not a cloud mount. Back it up independently after runs finish.

`run.py recover`, `retry` and `queue` preserve separate attempt identities. They are maintenance operations, not permission to replace unsuccessful outcomes in a community bundle. Read each command's `--help` and retain the original failure record.

First-success campaigns and independent repetitions answer different questions. First-success selection stops after the first eligible attempt; it cannot establish three-trial consistency. Community submissions use all three predetermined independent attempts. Reports preserve failures, unattempted slots and explicit retry provenance.

## Evaluate and report

The trusted evaluator renders the saved XM in a fresh FT2 process. It does not trust preview audio or submitted scores. Scoring captures replay behavior with the pinned analysis renderer. Video is presentation only; a video failure does not make the musical artifact invalid.

```sh
python benchmark/score.py profile --out /absolute/private/runs
python benchmark/report.py \
  --root /absolute/private/runs \
  --cohort /absolute/private/campaign.json \
  --out /absolute/private/report.json
```

`score.py profile --force` creates a new immutable evaluation generation. `score.py aggregate` rebuilds the score aggregate from existing profiles. Reports read cached evaluation evidence; they do not silently rescore attempts.

Craft-v7 is a tonal-development diagnostic. It combines tonal organization, development and dynamics, then adjusts for signal integrity, noise, loop continuity and audible duration. The duration factor saturates at 30 first-pass audible seconds. Short duration is not task noncompliance, and silence or repeated later playback cannot supply missing duration credit. Numerical scores do not replace listening or establish a validated musical-quality ranking.

Calibration metadata is in `data/keygen-scoring-reference.json` and `data/keygen-duration-reference.json`. The reference music itself is not distributed. Changes to scoring, source, numerical dependencies or renderer identity change evaluation provenance.

For a reviewed public snapshot, follow [the website guide](../web/classic/README.md). Do not serve a run directory or the repository root as a public file server.

## Verification

From the repository root, with the pinned environment active:

```sh
python -m unittest discover -s benchmark/tests
python -m unittest discover -s tests
```

Tests use synthetic data and do not require paid inference. A container build exercises native FT2 acceptance. For a complete operational check, run a submission through local collection, trusted rendering and scoring, and confirm that owned containers and volumes are removed. Real provider access requires a separately authorized funded run.

Never publish raw trajectory or transport logs without review. The community exporter reduces operational metadata and the validator checks common secret and private-address patterns, but neither can prove that arbitrary model text contains no personal data.
