# experimental Cursor → mini-swe-agent bridge

This is a diagnostic integration, **not an eligible frozen benchmark provider**.
It uses official `@cursor/sdk` 1.0.40. No private Cursor endpoints, token scraping,
model substitutions or system-prompt-as-user-message fallbacks are used.

## who executes what

mini-swe-agent → local Chat Completions bridge → Cursor SDK inference

Cursor's sole custom Bash tool creates a pending callback. The bridge returns a
normal `bash` tool call to mini; mini executes it in its environment. Its next
request resolves the callback with the exact observation. Cursor never executes
that Bash command on the controller. One live Cursor run stays attached to one
mini attempt; transcript rewrites, resumed/forked histories and session reuse are
rejected instead of being flattened into prose.

The adapter requests genuine SDK `systemPrompt` replacement, an MCP-only toolset
with one Bash callback, no subagents or inline external MCP servers, empty settings
sources, a temporary empty working directory and no agent transport/stall retries.
A missing account entitlement fails the first send; it is not worked around.
Run the controller under a dedicated empty HOME as well. A declared empty cwd
alone does not prove that ambient context has been removed.

## why this cannot enter the ranked pipeline yet

- Cursor still owns the upstream agent loop and MCP wrapping. System-prompt
  replacement does not remove all ambient context or prove final wire equivalence.
- Output caps, sampling controls, `tool_choice` and request-level reasoning controls
  are rejected, not accepted and ignored. The experimental condition uses provider
  defaults. Optional `--effort` is an explicit SDK `effort` model parameter; verify
  the exact value against your account's live catalogue first.
- Returned model IDs are labelled requested-only, not verified response identity.
- SDK cost is not reliably known here. Mini's numeric accumulator uses zero only
  to satisfy its interface; `cost_known: false` and `dollar_cost: null` disclose
  this. Never interpret that zero as free inference or a spending limit.
- No automatic transcript recovery, format repair, retry, alias fallback, scoring
  or public submission packaging is provided. One bridge process per attempt.
- The canonical runner/provider allowlist and all frozen prompts/limits are
  unchanged. Do not call this route `custom` to bypass their restrictions.

## setup (no model requests)

Use Node 22.19+ and the Python dependencies pinned in `benchmark/requirements.txt`.
From this directory, `npm ci --ignore-scripts` installs the pinned official SDK.
Run `node server.mjs --help`. From the repository root, run:

```sh
python -m benchmark.experimental.cursor_sdk.probe --help
node --test benchmark/experimental/cursor_sdk/bridge.test.mjs
python -m unittest benchmark.experimental.cursor_sdk.test_model
```

These tests use a synthetic SDK runtime. They do not authenticate to Cursor or
verify billing, system-prompt entitlements, real model identity or fairness.
The Python test runs only fixed synthetic commands in a disposable local folder;
it is not a Docker/FT2 acceptance test.

## live diagnostic (separate explicit approval required)

First establish an exact model, available reasoning parameter, Cursor credit-pool
eligibility and billing limits. Do not start under an approved dollar ceiling
unless it can actually be enforced: the timeout and consent flags are not dollar
caps, and in-flight work can still be charged after cancellation.

Have the owner configure an official Cursor User API key privately in the bridge
controller's `CURSOR_API_KEY` environment. Do not paste keys into chat, command
arguments, source or logs. This code does not mint, save or revoke credentials.
Use a separate local bearer in `KEYGEN_CURSOR_BRIDGE_TOKEN` in both processes.
The Python mini process must NOT receive `CURSOR_API_KEY`. Never share the bridge
port beyond loopback. Use an isolated OS account/container HOME and set
`KEYGEN_CURSOR_ISOLATED_HOME=1` only after establishing that isolation.

After explicit approval, run in the bridge terminal:

```sh
node server.mjs --model EXACT_CATALOG_ID --allow-credit-usage --accept-experimental-condition
```

Optionally pass `--effort EXACT_CATALOG_VALUE`. The bridge is loopback-only on
port 8320, non-streaming, and limits each request to 8 MiB and 120 seconds. Those
are diagnostic limits, not the benchmark's frozen limits.

In the mini terminal, after configuring ONLY the local bearer, run from repo root:

```sh
python -m benchmark.experimental.cursor_sdk.probe \
  --model EXACT_CATALOG_ID --image sha256:LOCAL_IMMUTABLE_IMAGE_ID \
  --out /absolute/private/cursor-pilot.json \
  --allow-credit-usage --accept-experimental-condition
```

Supply an already-built local Linux image with Bash and `/workspace`; the image
must be identified by its 64-hex SHA-256 ID. The probe executes only in a temporary
network-disabled Docker container, forwards no credentials, permits at most three
mini steps, closes the SDK session afterward and removes only its own container.
Stop the bridge process after the diagnostic. It cannot be reused for a new attempt.

Review the private trajectory and provider-side billing separately. A successful
pilot is evidence of tool transport, NOT permission to spend the remaining credit
balance or include the result in a frozen community/ranked submission.

## sources and verification limits

- [Cursor SDK](https://cursor.com/docs/sdk/typescript): genuine system replacement
  is local-only/account-gated; rules/skills/ambient context need separate controls.
- [SDK callback-handoff reference](https://github.com/Sunnyender-org/cursor-sdk2api/blob/main/src/core/tool-bridge.ts): a pending custom-tool promise can be resolved by an external client's result. This PR contains an original narrow implementation, not that project's runtime.
- [Cursor staff on private-client proxies](https://forum.cursor.com/t/does-using-oh-my-pi-s-cursor-provider-or-an-openai-compatible-proxy-to-the-same-endpoints-violate-cursor-s-tos/167778/5): private endpoints are not a supported substitute for the SDK.

Local verification: Node contract tests and real pinned mini/LiteLLM against this
bridge's mocked SDK runtime. No funded Cursor inference or Docker/FT2 rendering
was run while preparing this change. Account enablement, exact effective tools,
ambient context, provider-side model identity and billing remain unverified.
