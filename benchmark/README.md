# Keygen benchmark: mini-swe-agent + CLIProxyAPI

This is the inference and artifact-collection foundation. It uses the actual
`minisweagent.agents.default.DefaultAgent` from mini-swe-agent 2.4.6, not a
look-alike agent loop. Every model uses the same frozen text-action protocol,
creative prompt, resource budget, and offline FT2 environment.

There are no Codex CLI or Claude Code backends. No skills, hooks, plugins,
AGENTS.md discovery, saved conversations, or per-model system prompts are loaded
by this runner. CLIProxyAPI is the transport, not the agent.

```text
mini-swe-agent DefaultAgent (host, clean Python worker)
    -> no-retry Chat Completions adapter
    -> CLIProxyAPI (host, operator-configured upstream)
    -> model
    -> one bash action in an offline FT2 container
    -> text observation back to the same agent
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

There is deliberately no invented music-quality score. `PLAYABLE_UNSCORED`
means the artifact rendered, not that its composition is good. The previously
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

docker build -f benchmark/Dockerfile -t keygen-ft2-benchmark:local .
cp benchmark/config/cliproxyapi.example.yaml benchmark/config/cliproxyapi.local.yaml
cp benchmark/config/campaign.example.json benchmark/config/campaign.local.json
```

The Docker build runs the repository's native FT2 acceptance checker and fails
if author/edit/save/reload/render does not pass. The final runtime image contains
only its transport portion, not its demonstration notes or the repository's
creative prompts. The FT2 source revision is pinned by the existing build script.
The base OS/package repositories are not bit-for-bit locked: build once and reuse
the resulting image. The runner locks its immutable image ID, source hashes,
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

All models use the campaign's common `generation` object. Unsupported parameters
cause a failure rather than silent parameter removal or fallback. Choose settings
supported by the intended models before freezing the campaign. There is no price-
based stopping rule; subscription billing is not inferable from an API response.

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

`doctor` checks configuration, installed mini version, Docker image, and the
proxy's model list. It makes no completion request. It does not certify an active
proxy is using the supplied config file; start that instance explicitly.

Reissuing the same `run` command skips every reserved model, including failed or
interrupted ones. A changed prompt, dependency set, generation setting, image,
proxy config, or model list is refused for that output directory. There is no
`--redo` flag. An operator can always create a new directory; publish the original
campaign rather than silently cherry-picking a later one.

The default budgets are examples, not musical requirements. No tempo, key,
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
    worker-result.json
    status.json
    submission/tune.xm
    canonical/canonical.wav
```

`transport.jsonl` records exact outbound request hashes, reported model IDs, usage,
and response metadata. The trajectory preserves visible messages and executed
actions. Authentication headers and API keys are never placed in prompts or
serialized model config. Keep these local audit files private unless reviewed.
No automatic leaderboard or aesthetic ranking is emitted.

Statuses distinguish `FAILED`, `INFRA_ERROR`, `EVALUATION_ERROR`, `INTERRUPTED`,
and `PLAYABLE_UNSCORED`. A worker timing out may leave a playable final artifact;
its termination reason is retained separately. A render/infrastructure error is
not silently turned into a zero musical score. None causes a second model attempt.

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
one HTTP request per turn. It does not import LiteLLM routing or its retry layer.
It sends the visible messages unchanged, with no native function-tool definitions
or auxiliary prompts. A reply without exactly one action block gets mini's standard
format-error message back; three in a row end the attempt as `RepeatedFormatError`.
An HTTP error terminates the worker.
Rendering supplies files and numerical observations, not audio listening.

Containers share the host kernel. For hostile workloads use a dedicated VM or
stronger sandbox, and treat a custom image as trusted infrastructure that requires
review. Isolation is not a claim that upstream model/provider internals are visible.

## Tests and verification

```sh
python -m unittest discover -s benchmark/tests -v
python -m py_compile benchmark/run.py benchmark/proxy.py benchmark/bridge.py
```

Offline tests cover raw outbound prompt preservation, authentication separation,
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
- [mini text-action adapter](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/models/litellm_textbased_model.py)
- [CLIProxyAPI configuration inspected at a fixed revision](https://github.com/router-for-me/CLIProxyAPI/blob/5208aec703b5ce7e3445f6e9d91cc13b3e78003a/config.example.yaml)
- [Existing FT2 workflow and limitations](../docs/10-agent-xm-workflow.md)
- [Existing native acceptance checker](../tools/ft2_smoke.py)
- [Docker copy limitations](https://docs.docker.com/reference/cli/docker/container/cp/)
- [Docker-managed volumes](https://docs.docker.com/engine/storage/volumes/)
