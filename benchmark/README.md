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

Scoring additionally needs the analysis renderer and the AI listener. For the renderer, install a C compiler, Git, pkg-config, SDL2 and libmicrohttpd development packages, then run:

```sh
python scripts/build-ft2-analysis.py
```

The script checks the source commit and capture patch and writes a binary with provenance metadata to the user's cache directory. `KEYGEN_FT2_ANALYSIS` selects a different verified build.

The listener runs in its own environment, because PyTorch must not load inside the evaluator and the controller pins a different `huggingface_hub`:

```sh
python3 -m venv .venv-listener
.venv-listener/bin/pip install -r benchmark/requirements-listener.txt
export KEYGEN_LISTENER_PYTHON="$PWD/.venv-listener/bin/python"
.venv-listener/bin/python benchmark/score_listener.py identity
```

The identity command downloads the pinned model revision once (about 415 MB) and verifies the weights' SHA-256. Without `KEYGEN_LISTENER_PYTHON`, evaluation marks attempts unscored, never zero.

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

## Provider routes

Use the [guided contributor CLI](../CONTRIBUTING-RUNS.md#guided-setup-and-run) for setup and private model configuration.

| Provider | Protocol | Endpoint |
| --- | --- | --- |
| `openai` | Chat Completions or Responses | `https://api.openai.com/v1` |
| `anthropic` | Messages | `https://api.anthropic.com/v1` |
| `go` | Chat Completions, Responses or Messages | `https://opencode.ai/zen/go/v1` |
| `vercel` | Chat Completions or Responses | `https://ai-gateway.vercel.sh/v1` |
| `nim` | Chat Completions | `https://integrate.api.nvidia.com/v1` |
| `mistral` | Chat Completions | `https://api.mistral.ai/v1` |
| `cohere` | Chat Completions | `https://api.cohere.ai/compatibility/v1` |
| `custom` | Chat Completions, Responses or Messages | User-selected public HTTPS endpoint |
| `google` / setup alias `gemini` | Native Gemini | `https://generativelanguage.googleapis.com/v1beta` |
| setup alias `xai` | Existing `custom` native transport | `https://api.x.ai/v1` |
| setup aliases `openrouter`, `deepseek`, `groq` | Existing `custom` native transport | Provider-specific public endpoint |

Run `python benchmark/contrib/cli.py login PROVIDER` for local CLIProxyAPI OAuth
with Codex/OpenAI, Anthropic or xAI. Use `--method api-key` explicitly for key
setup, including custom OpenAI-compatible endpoints. Login does not select a
model or authorize inference. See the [credential lifecycle and OAuth limits](../CONTRIBUTING-RUNS.md#oauth-login-with-api-keys-as-an-explicit-alternative).

New contributor smoke/runs through `anthropic_oauth` and `codex_oauth` bridges
are blocked: no-cloak does not preserve all frozen generation controls. We retain
historical route definitions and validation so existing evidence remains readable.
The advanced `xai_oauth` Responses route remains available with a user-authorized
loopback bridge and exact model catalog check, but neither this check nor the
bridge digest certifies final-upstream prompt/settings preservation or provider
permission. The login command orchestrates xAI device login through the selected bridge. Never enable a
compatibility prompt or injected tool to make a frozen run succeed.

The public OpenAI ChatGPT OAuth flow is distinct from a Codex bridge, but its
current unsupported output caps prevent a drop-in under this condition. It is
not implemented. OAuth login and API-key setup are separate from frozen-route eligibility. Details
and official sources are in the [contributor guide](../CONTRIBUTING-RUNS.md#authentication-is-not-benchmark-qualification).

## Configure a campaign

Keep working configuration, credentials and run artifacts outside this checkout. `config/campaign.example.json` shows the selection structure; it is not a ready-to-run campaign. Fill in actual immutable image IDs, model configuration and verified readiness evidence.

A real multi-turn native readiness pilot must execute tool calls and validate the returned model identity. The guided contributor commands run one automatically before every smoke or three-attempt run, using the exact configured route and settings. This pilot makes provider requests and may incur cost; its proof stays in the private work directory, and a failed pilot starts no benchmark attempt. Each invocation runs a fresh pilot. The maintainer campaign compiler still requires an explicit inventory, selection and tier specification; the repository contains no private account inventory. `native_readiness.py --help` describes pilot inputs.

Google AI Studio routes use `provider: google` with the pinned SDK's `gemini/` prefix and `GEMINI_API_KEY`; the declared tier is sent as `thinkingLevel` and the returned `modelVersion` must match the frozen identity. Mistral routes use `provider: mistral`, `api: chat`, `https://api.mistral.ai/v1` and `MISTRAL_API_KEY` through LiteLLM's native Mistral provider (it parses Mistral's thinking content chunks; the OpenAI-compatible path rejects them). That provider lists `reasoning_effort` only for Magistral names and replaces it with a system prompt there, so a declared `reasoning_effort` is sent unaltered with LiteLLM's documented `allowed_openai_params` opt-in. Devin routes use `provider: devin`, `api: chat` and the `openai/` prefix through a user-authorized local bridge; the requested alias and the expected returned identity are separate frozen fields, and the bridge executable digest is part of readiness. Cohere routes use `provider: cohere` on Cohere's compatibility endpoint with `COHERE_API_KEY`; they always send `strict_tools: true`, because without it Cohere rejects a whole reply (HTTP 400, "all generated tool calls were hallucinated") when the model calls a function that is not declared. Routes with a per-minute cap per account are paced: Cohere trial keys and OpenRouter `:free` endpoints (20 requests a minute) start a request at most every 60/18 s, and `api.cerebras.ai` also spaces requests by estimated input size under its 150k tokens-a-minute cap. A 429 ends an attempt as QUOTA and is never retried, so pacing keeps a rate limit from ending it; the schedule is shared through a locked file per account in `/tmp/keygen-request-pacing`, the wait counts toward wall time, and effective settings record it as `request_pacing`. Cerebras rejects the assistant-history keys `reasoning_content` and `provider_specific_fields`, so that host drops them from outgoing history (recorded as `history_key_removal`).

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

### The score

The listener-v1 score is 10 x the content-enjoyment rating that [Meta Audiobox Aesthetics](https://github.com/facebookresearch/audiobox-aesthetics) gives the canonical render, rounded to 0.1. The model predicts how people would rate a clip from 1 to 10. It was trained on about 97,000 speech, sound and music clips rated by 158 people ([Tjandra et al. 2025](https://arxiv.org/abs/2502.05139)); its weights are CC-BY-4.0. `benchmark/score_listener.py` resamples the first 120 seconds to 16 kHz mono, rates 10-second windows and averages them by length. Inference runs on the CPU with a pinned model revision and verified weights, so a given render always gets the same rating. Profiles record the four ratings (content enjoyment, production quality, content usefulness and production complexity); only enjoyment is scored.

Two artifact caps still apply, because the listener cannot tell how the audio was made: an effectively silent render scores 0, and a long used sample with sparse sequencing, which looks like a pre-rendered song, is capped at 40. The serialized score keeps its historical key, `craft.craft_score`.

The listener rates only the first 120 seconds. Artifact caps use whole-render silence and sequencing measurements, so material after 120 seconds can still change the final score.

Listener provenance records the operating system, CPU architecture and Python version alongside the pinned model, weights and inference package versions. Small numerical differences between execution environments are possible.

The listener replaced the fixed craft formula after the formula's top 20 attempts turned out to be uncorrelated with the listener (Spearman +0.02), and the maintainer preferred the listener's ranking after listening to it. It has limits: it was not trained specifically on tracker music, it leans toward longer and slightly quieter tunes on this corpus, and differences of a few points are within its noise. See the [scoring review](../docs/scoring-review.md).

### Craft diagnostics

`craft.craft_diagnostics` keeps the previous formula as a diagnostic: pitched clarity (50), development (40) and dynamics (10), multiplied by signal integrity and loop continuity. These measurements explain how a tune is built. They do not change the score.

Listener ratings retain the full prediction precision so `round(10 * craft.listener.content_enjoyment, 1)` reproduces the uncapped score.

Pitched clarity is the active-duration mean captured harmonic-power fraction, with full credit at 0.50. A stationary tone can reach the full 50; the serialized component is `tonal_organization`.

At 4, 8 and 16 beats, each passage contains its distinct sequenced voices. A voice is a set of onset-tick/pitch pairs, independent of channel and instrument indices. Exact duplicate voices count once. One beat is 24 FT2 ticks. Each voice is compared with other passages: transposition-normalized Jaccard overlap measures its strongest relationship to a changed voice; absolute-pitch overlap measures its mean contrast. An exact copy supplies no transformation evidence, and a voice with one onset in a passage has no shape, so it cannot relate to another voice. Its contribution is `recurrence² * contrast`, averaged across voices, passages and the three timescales.

Calibration metadata is in `data/keygen-scoring-reference.json` and `data/keygen-duration-reference.json`. The reference music itself is not distributed. Changes to scoring source, the listener identity, numerical dependencies or renderer identity change evaluation provenance.

For a read-only review rescore without changing source profiles, including historical craft-v7/craft-v9 and listener-v1 profiles:

```sh
export KEYGEN_LISTENER_PYTHON="$PWD/.venv-listener/bin/python"
python benchmark/rescore.py runs --root runs --output /tmp/listener-v1-runs.json
python benchmark/rescore.py render-references --modules /absolute/reference-xms --out /tmp/reference-first-passes
python benchmark/rescore.py references --modules /absolute/reference-xms \
  --first-passes /tmp/reference-first-passes --output /tmp/listener-v1-reference.json
```

The listener is slow on small machines (minutes per tune on 2 cores). `render-references` needs the Linux FT2 analysis build; copy its output directory to a faster host for the two listening commands, and check that the scorer file hashes match there.

The first command covers every `runs/<model>/attempt-N` directory, preserves unscored outcomes, checks XM and canonical WAV hashes, rates the verified canonical WAV with the listener, recomputes craft diagnostics, and retains the unchanged signal, dynamics and loop measurements with their source provenance. Install `flac` to restore archived WAV bytes with foreign metadata. The output is review evidence, not a replacement profile generation. `other/` remains historical and unranked. Reference modules must be named `<git_blob_sha>.xm` and match `data/keygen-duration-reference.json`; `render-references` renders each first pass with the pinned native renderer and records its hash; `references` verifies those hashes and rates each first pass with the listener, without caps.

The [scoring review](../docs/scoring-review.md) contains the model table, reference distributions, verification results and limitations.

For a reviewed public snapshot, follow [the website guide](../web/classic/README.md). Do not serve a run directory or the repository root as a public file server.

## Verification

From the repository root, with the pinned environment active:

```sh
python -m unittest discover -s benchmark/tests
python -m unittest discover -s tests
```

Tests use synthetic data and do not require paid inference. A container build exercises native FT2 acceptance. For a complete operational check, run a submission through local collection, trusted rendering and scoring, and confirm that owned containers and volumes are removed. Real provider access requires a separately authorized funded run.

Never publish raw trajectory or transport logs without review. The community exporter reduces operational metadata and the validator checks common secret and private-address patterns, but neither can prove that arbitrary model text contains no personal data.


## experimental transports

See the [Cursor SDK / mini diagnostic](experimental/cursor_sdk/README.md). It retains mini-side Bash execution but is not accepted by the frozen native provider validator. SDK tool wrapping, ambient context, generation controls, model identity and billing still require independent qualification.
