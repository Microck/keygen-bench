# Keygen benchmark: mini-swe-agent + CLIProxyAPI

This is the inference and artifact-collection foundation. It uses the actual
`minisweagent.agents.default.DefaultAgent` from mini-swe-agent 2.4.6, not a
look-alike agent loop. Every model uses mini's default action protocol (one declared
`bash` function tool), the same frozen creative prompt, resource budget, and offline
FT2 environment.

There are no Codex CLI or Claude Code backends. No skills, hooks, plugins,
AGENTS.md discovery, saved conversations, or per-model system prompts are loaded
by this runner. CLIProxyAPI is the transport, not the agent.

```text
mini-swe-agent DefaultAgent (host, clean Python worker)
    -> Chat Completions adapter (one retry on upstream 5xx)
    -> CLIProxyAPI (host, operator-configured upstream)
    -> model
    -> bash tool calls run in an offline FT2 container
    -> tool results back to the same agent
```

## What this adds, and what it does not

One reserved attempt per model. Within that single trajectory the model may
compose, render and revise. Submission, a resource limit, or a terminal error
ends the attempt. The last workspace artifact is frozen; there is no best-of-N,
second attempt, post-submission editing, or automatic task restart.

A fresh, trusted FT2 process renders the saved XM. This is independent of the
agent's process and preview WAV, not an independent replay engine. Entirely
silent or invalid output fails the validity gate. Duration, RMS, peak, DC offset,
and full-scale sample counts are reported as technical observations only.

After the canonical render, a second trusted container records the FT2 clone GUI
playing the module: Xvfb at 1280x960, the tracker's 1264x800 window stretched to
4:3 the way FT2 filled a CRT, 30 fps H.264. The audio track is what the mixer
played in real time through SDL's disk driver at 48 kHz, aligned to the frame the
grab started on. It is presentation; canonical.wav is the artifact a later evaluator would use.
Capture length is capped by `video_seconds`, and a capture failure is recorded in
`status.json` without changing the attempt's status.

There is deliberately no invented music-quality score. `RENDERED_UNSCORED`
means the trusted FT2 process rendered a non-silent WAV from the file, nothing
more. No ordering of models follows from it. The previously
claimed scoring package was not present in the reviewed repository. Domain-fit,
structural, originality, and aesthetic ranking are not implemented in this PR.
The collection records are intended for a separate frozen artifact evaluator.

## Setup

Run from the repository root on a machine with a local Docker daemon and
Python 3.10 or newer. Use a dedicated virtual environment.

```sh
python3 -m venv benchmark/.venv
. benchmark/.venv/bin/activate
python -m pip install -r benchmark/requirements.txt
python -m unittest discover -s benchmark/tests -v

docker build -f benchmark/Dockerfile --target agent -t keygen-ft2-benchmark:local .
docker build -f benchmark/Dockerfile --target visualizer -t keygen-ft2-visualizer:local .
cp benchmark/config/cliproxyapi.example.yaml benchmark/config/cliproxyapi.local.yaml
cp benchmark/config/campaign.example.json benchmark/config/campaign.local.json
```

The Docker build runs the repository's native FT2 acceptance checker and fails
if author/edit/save/reload/render does not pass. The final runtime image contains
only its transport portion, not its demonstration notes or the repository's
creative prompts. The FT2 source revision is pinned by the existing build script.
The base OS/package repositories are not bit-for-bit locked: build once and reuse
the resulting images. The runner locks both immutable image IDs, source hashes,
Python/package versions, prompts, parameters, and proxy-config digest per campaign.

The requirements pin mini itself. Transitive Python dependencies are recorded,
not a complete reproducible-install lock. Keep the same virtual environment for
the campaign; changing a dependency or image prevents a mixed-condition resume.

## Configure the proxy and models

Start a dedicated CLIProxyAPI instance with the local YAML file. Set its local
client API key to a newly generated random value. Configure only upstream access
you are authorized to use. Authentication, subscription eligibility, OAuth login,
and token extraction are outside this package. It neither launches native coding
clients nor implements subscription authentication or bypasses provider controls.

Set the same local client key in the host environment, not in the campaign JSON:

```sh
export CLIPROXY_CLIENT_KEY='your-local-proxy-client-key'
curl --fail --silent http://127.0.0.1:8317/v1/models \
  -H "Authorization: Bearer $CLIPROXY_CLIENT_KEY"
```

Replace every `REPLACE_...` value in the campaign and proxy files. Record the
installed CLIProxyAPI version or commit. Add one object per exact model ID:

```json
{"id": "model-a", "model": "exact-request-model-id", "response_model": "exact-response-model-id"}
```

`response_model` is checked against the completion response. Some gateways use
a different canonical response name; verify that mapping in a separate transport
check before starting the official campaign. This check cannot authenticate the
true weights behind a proxy-reported name.

All models use the campaign's common `generation` object. Reasoning models spend
completion tokens on thinking before the tool call, so keep `max_tokens` generous. Unsupported parameters
cause a failure rather than silent parameter removal or fallback. Choose settings
supported by the intended models before freezing the campaign. There is no price-
based stopping rule; subscription billing is not inferable from an API response.

The adapter retries a request once, after 5 s, when the proxy answers 5xx or the
connection fails; 4xx answers (auth, quota, rate limit) end the attempt. Both requests
are audited in `transport.jsonl`, the first marked `retried`. Each step's last observation
carries a `<time_left>` tag with the minutes left on the wall clock.

The proxy settings explicitly disable additional retry rounds, credential
failover within a round, quota-based model switches, global Claude prompt cloaking,
model-list cloaking, image-tool injection, plugins, and payload overrides. These
are a configuration check, not proof of the provider-facing payload. Per-credential
settings, aliases inside upstream definitions, proxy translation, and provider-side
instructions can still change a request. Use a dedicated, fixed route per model;
audit the upstream payload without publishing credentials. The report retains
`upstream_payload_verified: false` rather than claiming otherwise.

No rotating accounts, auto-model names, model fallbacks, or native CLI agent
scaffolds belong in a ranked campaign. This package does not configure them.

## Run

```sh
python -I benchmark/run.py doctor --campaign benchmark/config/campaign.local.json
python -I benchmark/run.py run --campaign benchmark/config/campaign.local.json \
  --out benchmark/runs/official
```

`doctor` checks configuration, installed mini version, both Docker images, and the
proxy's model list. It makes no completion request. It does not certify an active
proxy is using the supplied config file; start that instance explicitly.

To run a roster selection (one row per model and tier, as exported by the roster page)
as one campaign per tier, in order, with a results table at the end:

```sh
python -I benchmark/drive.py plan --selection benchmark/config/selection.local.json
python -I benchmark/drive.py run  --selection benchmark/config/selection.local.json --out benchmark/runs/official
```

Each tier gets `campaign-<tier>.local.json` and `runs/official/<tier>/`. Tiers that are not a
`reasoning_effort` value run with no parameter. The driver refreshes a Vercel OIDC token
between campaigns when it has under six hours left; credential values are excluded from the
proxy-config digest, so a rotated key does not count as a changed condition.

Reissuing the same `run` command skips every reserved model, including failed or
interrupted ones. A changed prompt, dependency set, generation setting, image,
proxy config, or model list is refused for that output directory. There is no
`--redo` flag. An operator can always create a new directory; publish the original
campaign rather than silently cherry-picking a later one.

The default budgets are examples, not musical requirements. `steps: 0` removes the
step limit and leaves the wall clock as the only budget. No tempo, key,
instrument palette, form, or target tune duration is prescribed. Resource bounds
still limit storage, request time, rendering time, CPU, and memory. Wall-clock
limits include provider latency. Adjust budgets before starting, not per model.

```text
benchmark/runs/official/
  campaign.lock.json
  model-a/
    spec.json
    trajectory.json
    transport.jsonl
    responses.jsonl
    worker-result.json
    status.json
    submission/tune.xm
    canonical/canonical.wav
    visualizer/visualizer.mp4
```

`transport.jsonl` records, per request: outbound request hash, requested and reported
model IDs, usage, start time, latency, response size, prompt message count, and the
rate-limit headers the proxy passed through. `responses.jsonl` keeps each whole
upstream body, reasoning fields included. Tool results carry the sandbox time of
their command. `status.json` adds attempt start and end times and per-attempt totals
(requests, failed requests, requests with unknown usage, prompt/cached/completion/
reasoning tokens, model seconds, sandbox seconds, commands). A request that fails
still gets a transport line with its error and elapsed time. The trajectory preserves visible messages and executed
actions. Authentication headers and API keys are never placed in prompts or
serialized model config. Keep these local audit files private unless reviewed.
No automatic leaderboard or aesthetic ranking is emitted.

Statuses distinguish `FAILED`, `INFRA_ERROR`, `EVALUATION_ERROR`, `INTERRUPTED`,
and `RENDERED_UNSCORED`. Beside the status, `termination` says how the agent
ended, `collection` whether a submission was found, `render` whether the file
rendered (`ok`, `invalid`, `error`), and `module` what FT2 reports about it
(channels, patterns, instruments). A worker timing out may leave a renderable
final artifact; its termination reason is retained separately. A render/infrastructure error is
not silently turned into a zero musical score. None causes a second model attempt.

## Profiles and listening packets (no score)

`score.py` is the automatic layer that runs over collected attempts. It never ranks
and never excludes; it produces evidence columns and blind listening material.

```sh
python -I benchmark/score.py profile --out benchmark/runs/official
python -I benchmark/score.py packets --out benchmark/runs/official
```

`profile` writes `profile.json` per attempt and `profiles.{json,md}` at the root:
XM structure (channels used, distinct patterns in the order, note-ons, instruments,
sample seconds at root pitch, sample versus pattern bytes, effects, jumps), canonical
audio metrics (BS.1770 integrated loudness, true peak, silence map, tail silence,
block RMS range, seam jump across end to start), process tags from the trajectory
(FT2 tools used, XM written directly, preview rendered, inspected, edited after
inspection), and craft flags. Every flag rule is disclosed in `FLAG_RULES` and in
the table footer. A flag is a reason for a human to look, not a verdict; the known
gaming vector (one long pre-rendered sample) shows up as `PHRASE_SAMPLE` and
`SAMPLE_HEAVY` and is adjudicated by a person against the prompt's rule.

`packets` renders each tune again with its restart sequence appended to the order
table, so FT2 plays a real restart with carried tempo, volume and effect state
(disclosed limitation: with a nonzero restart position the tail wraps to order 0
after the end). The first part of the render must be byte-identical to
`canonical.wav` or no packet is written. The packet gets one constant gain to
-18 LUFS with a -1 dBTP ceiling and no limiter, a 50 ms end fade, and
`packet.json` with hashes, gain, and any loudness shortfall. Packets are what a
blind listener hears; `canonical.wav` stays the reference artifact.

`craft` is the one number: 0 to 100, weights fixed in `CRAFT_WEIGHTS` (loop 25,
audio 20, silence 10, structure 30, dynamics 5, length 5, process 5), every input a
column from the same table, every band disclosed in `craft_score()`. Full credit is
set at what a strong keygen module has (8 channels and instruments in use, 8 distinct
patterns, four kinds of effect commands, samples under 2 s, a clean seam within
1.5 dB, 60 to 180 s), so a first attempt lands in the middle, not at 100. It measures
tracker discipline and render integrity. A clean-looping, well-levelled,
multi-channel module scores high whether or not the music is any good; a
one-sample playback of pre-rendered audio scores low on structure whatever it
sounds like, and when the sample evidence says pre-rendered playback (longest sample
over 8 s or sample seconds over half the song) the score is capped at 40 until a
person adjudicates. Rows sort by it. Treat it as "how well was the tracker used", never
as "how good is the tune".

What this layer cannot do is judge music. A ranking needs blind listening by a
person (the protocol in `docs/12-scoring-ideation-2026-09-24.md` is the current
plan); an audio-language judge would have to be validated against those labels
first.

## Isolation details

The worker runs Python with `-I` and an allowlisted environment. Its HOME, XDG
config and `MSWEA_GLOBAL_CONFIG_DIR` are new directories. This matters because
mini's package initializer loads a global `.env` even when using its Python API.
We instantiate DefaultAgent directly with two explicit templates; no mini CLI
configuration merging or native-client configuration occurs.

The model executes commands only inside a non-root, network-disabled, read-only
container with bounded writable tmpfs storage. The workspace is a private,
tmpfs-backed Docker-managed volume, not a host directory. A non-agent, read-only
export helper keeps it mounted and reads files while the agent is paused; ordinary
`docker cp` cannot reliably copy tmpfs data. Helpers and volumes are removed after
collection. No repository, host home,
Docker socket, API keys, proxy auth directory, evaluator, reference music, or
skill folder is bind-mounted. Bash runs with `--noprofile --norc` and disabled
BASH_ENV/ENV startup files. Only the FT2 session and workspace persist within one
attempt. Files from another model never enter that workspace.

The adapter is small because it implements mini's Model protocol directly using
one HTTP request per turn, two when the first fails transiently. It does not import LiteLLM routing or its retry layer.
It sends the conversation unchanged and declares exactly one tool, mini's stock
`bash` function, the protocol the shipped SWE-bench configs use. No other tools or
auxiliary prompts. A reply with no tool call or an unknown tool gets mini's standard
format-error message back; three in a row end the attempt as `RepeatedFormatError`.
An HTTP error terminates the worker. The legacy single-code-block text protocol was
tried first: current codex-backend models answer it with a whole imagined session of
commands in one reply, and Kimi K3 leaks tool-call tokens into the text.
Rendering supplies files and numerical observations, not audio listening.

Containers share the host kernel. For hostile workloads use a dedicated VM or
stronger sandbox, and treat a custom image as trusted infrastructure that requires
review. Isolation is not a claim that upstream model/provider internals are visible.

## Tests and verification

```sh
python -m unittest discover -s benchmark/tests -v
python -m py_compile benchmark/run.py benchmark/proxy.py benchmark/bridge.py
```

Offline tests cover outbound message and tool preservation, authentication separation,
HTTP retries/redirects, response-model mismatch, contaminated environment removal,
container flags, duplicate model rejection, one-attempt reservation, campaign
locking, archive validation, and technical audio observations. The real DefaultAgent
contract test runs only when mini-swe-agent is installed; a skip is not a pass.
See [VALIDATION.md](VALIDATION.md) for what was actually run during preparation.

## Primary implementation references

Source inspection date: 2026-09-05. These are implementation references, not
endorsements of subscription credential reuse.

- [mini DefaultAgent 2.4.6](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/agents/default.py)
- [mini initialization and Model/Environment protocols](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/__init__.py)
- [mini tool-call model and bash tool](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/models/litellm_model.py)
- [CLIProxyAPI configuration inspected at a fixed revision](https://github.com/router-for-me/CLIProxyAPI/blob/5208aec703b5ce7e3445f6e9d91cc13b3e78003a/config.example.yaml)
- [Existing FT2 workflow and limitations](../docs/10-agent-xm-workflow.md)
- [Existing native acceptance checker](../tools/ft2_smoke.py)
- [Docker copy limitations](https://docs.docker.com/reference/cli/docker/container/cp/)
- [Docker-managed volumes](https://docs.docker.com/engine/storage/volumes/)
