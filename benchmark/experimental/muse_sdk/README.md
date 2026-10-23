# Experimental Muse Code → mini transport

This is executable integration code, not a native raw-model provider. mini owns
Bash execution; Muse Code still owns the upstream conversation and system prompt.
**All runs are non-ranked and non-frozen.** No Muse subscription has been exercised
by this PR. See [the access investigation](../../../docs/muse-wonder-full-access.md).

## Components

- `server.mjs`: authenticated loopback Chat Completions endpoint, one attempt per
  server process; requires explicit usage and experimental-condition consent.
- `runtime.mjs`: official `@muse-code/sdk` 1.4.12, paired with the same Muse Code host
  version and schema; exact live catalog model/effort selection and read-back.
- `relay.mjs`: stdio MCP tool server. It forwards a pending Bash call to mini and
  waits for mini's observation. It never evaluates or executes the command itself.
- `model.py`: opt-in `MuseMiniModel`, using pinned mini/LiteLLM. Credential-redacted
  serialization marks cost unknown and the upstream harness retained.
- `probe.py`: explicit three-step synthetic diagnostic in an immutable local Docker
  image, with no container network, no forwarded credentials and a private receipt.

## Prerequisites

1. Install pinned benchmark Python requirements and run `npm ci --ignore-scripts`
   in this directory. Node >=22.19 is required by this adapter.
2. Have official Muse Code **1.4.12** and a dedicated private HOME already signed
   in with a subscription entitled to Wonder Full. Use the actual binary, not an
   auto-updating launcher. A different version/schema stops before generation.
   This adapter does not install Muse Code, mint credentials, change your account,
   buy a subscription or copy subscription credentials into a generic API client.
3. Authorize quota consumption separately. The consent flags and timeouts are NOT
   dollar caps. No budget on the wanted list does not mean free or unlimited use.
4. Use a fresh dedicated profile without personal rules, skills, plugins, hooks or
   memory, rather than your everyday HOME. Muse's built-in context may remain.
   Keep that profile and its retained logs private and outside this repository.

## Start the bridge

In a private controller shell, set `KEYGEN_MUSE_BRIDGE_TOKEN` to a fresh random
local token (at least 24 characters). Do not reuse your Meta credential as this
bearer. Start:

```sh
node benchmark/experimental/muse_sdk/server.mjs \
  --muse-bin /absolute/path/to/muse \
  --profile-home /absolute/private/muse-profile \
  --model muse-wonder-full-1.0 --effort max \
  --allow-credit-usage --accept-experimental-condition
```

The process overrides `MUSE_CONTRIBUTOR_MODE=0` in the owned host environment.
Contributor IDs require `--accept-contributor-training`, which enables the per-run
training override. [Meta documents what that consent means](https://dev.meta.ai/docs/muse-code/subscriptions).
No saved setting is edited. Verify effective mode on the installed host before
sending real work; a mock cannot prove provider-side data policy.

Native shell/write, web fetch/search, artifact tools, automatic workflows and
user-input requests are disabled with verified host options. Agent capacity is
one. These controls reduce the harness surface; background observers remain
unverified. Session-scoped MCP config requires the negotiated sessionMcp capability,
and an unexpected ambient MCP server aborts before generation. Only the exact relay tool can
receive an automatic one-shot approval; native, child-agent and persistent grants
are denied. This is **not** evidence that all other native schemas/tools or
background inference are disabled. Use only synthetic/public tasks in this
experimental route until that remaining host behavior is audited.

## Run a Docker diagnostic

In a separate Python process with only the local bridge token (not Meta/API
credentials), from the repository root:

```sh
export MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT=1
python -m benchmark.experimental.muse_sdk.probe \
  --model muse-wonder-full-1.0 --image sha256:YOUR_LOCAL_IMAGE_DIGEST \
  --out /absolute/private/pilot.json \
  --allow-credit-usage --accept-experimental-condition
```

The image must already exist locally and contain Bash. The diagnostic performs a
simple printf, receives the observation and submits the pilot marker. It is not
an FT2/music acceptance test. For a separate non-ranked experiment, instantiate
`MuseMiniModel` in an independent mini runner with the required sandbox and task;
do not add it to the ranked provider catalog. Start a fresh bridge per attempt.

Ctrl-C closes the owned host and outstanding callbacks. `model.close()` closes the
session, not a reusable attempt. A timeout, unsupported generation field, changed
transcript, unknown effort, unavailable model or terminal without a tool call
stops the attempt; it never repairs the prompt or selects a different model.

## Known differences and verification

The benchmark system text is visibly supplied as **user-level context**. It is not
a replacement system prompt. The tool appears upstream as an MCP tool, not the
identical mini Bash schema/name. Muse may retain built-in guidance, reminders,
compaction and auxiliary inference. The adapter never claims otherwise.
Requested/selected catalog identity is not provider-attested inference identity;
unknown token/dollar usage is never presented as free. The numeric mini cost
accumulator is a compatibility placeholder only, with `cost_known: false`.

Offline verification:

```sh
node --test benchmark/experimental/muse_sdk/*.test.mjs
python -m unittest benchmark.experimental.muse_sdk.test_model
```

Tests use the actual bridge, MCP relay and pinned mini agent with a synthetic Muse
SDK/backend. They check callback continuation, rejection, catalog/effort/host pins,
authentication, credential redaction and approval restrictions. The SDK import is real. An optional `MUSE_TEST_BIN=/absolute/muse node --test
benchmark/experimental/muse_sdk/host.test.mjs` check starts the real pinned host
with an empty HOME and echo provider, registers the session MCP relay and attaches
the SDK facade without sending any model turn. This passed locally against the
checksum-verified official 1.4.12-R6909.1 Linux binary. No authenticated Muse host
or model request is run by these tests. Provider
entitlement, live tool execution, prompt equivalence, billing,
Docker/FT2 rendering and scoring remain unverified until a separately authorized
live acceptance run.
