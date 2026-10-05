# Native model integration

The active benchmark now uses original upstream mini-swe-agent 2.4.6 model implementations. The previous proposal and implementation are preserved under `legacy/previous-work-20260930/`.

## Canonical implementation

`benchmark/native_models.py` constructs upstream `LitellmModel` for native Chat Completions and Anthropic Messages, and upstream `LitellmResponseModel` for Responses. `benchmark/run.py` uses upstream `DefaultAgent`. The custom `benchmark/proxy.py` adapter was removed. There is no model subclass, query wrapper, alternative parser or replacement agent loop.

Chat tools, Messages thinking signatures and Responses reasoning items remain in their native upstream history. Codex uses the authorized loopback Responses bridge rather than LiteLLM's chatgpt helper, which injects instructions and drops output limits. Anthropic uses the authorized loopback Messages bridge. The declared bridge URL remains `/v1`; the Anthropic SDK receives the origin because it appends `/v1/messages` itself.

The observation template reports remaining wall time on tool results and handles omitted optional exception fields. This template does not alter the native parser or history formatter.

## Route policy

Approved provider identifiers are `go`, `vercel`, `anthropic_oauth` and `codex_oauth`. Direct Go uses the paid endpoint. OpenCode Zen, Gemini bridge and the local Kimi pool are excluded. Devin remains held until quota renewal. No approved raw route for actual Cursor Composer 2.5 was found. No xAI-labelled Composer substitution or coding-agent wrapper is allowed.

`MODEL-TEST-PLAN.json` is an inventory. `benchmark/campaign.py` compiles an explicit selection into an immutable executable campaign and rejects held, excluded, unverified and unsupported entries before inference.

## Readiness and experimental conditions

A real multi-turn readiness artifact must match the exact route, effective settings, source identity and backend provenance. It includes native trajectory and transport audit evidence with a successfully executed tool result before a subsequent model response. Compilation verifies the saved proof and freezes it with the campaign.

Requested settings and native SDK transformations are recorded separately from provider-side delivery. A client configuration or acknowledged response does not prove all requested effort/output settings reached the hidden upstream model. Unknown delivery and alias checkpoint identity remain explicit.

The objective is `declared_native_configurations_fixed_resources`. Every model has three independent predetermined repetitions. Prompts, images, limits, installed implementations, route, effective generation parameters and retry policy are frozen. Failed repetitions remain visible; recovery attempts cannot replace them.

## Credentials and evidence

Only the trusted controller resolves keys. Each isolated worker receives the native SDK variable needed for its selected route. No credential home or token/configuration file is mounted in the offline command container or uploaded to Boat. Native SDK response/error echoes are redacted before persistence. Readiness compilation and artifact export reject detected secrets.

Targeted runtime evidence is under `benchmark/runs/setup-verification/`. A local SDK peer test proves implementation behavior, not live account access. Live failures remain failed evidence and do not make a route ready. A full campaign remains unauthorized until its actual readiness, storage and transport gates pass.

See `benchmark/README.md` for executable commands, storage/Boat lifecycle and auxiliary scoring/publication contracts.
