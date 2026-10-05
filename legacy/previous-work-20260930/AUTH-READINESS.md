# Authentication and model readiness

Checked: 2026-09-30T08:56:10.132337+00:00

Current test selection: [MODEL-TEST-PLAN.md](MODEL-TEST-PLAN.md). The user excludes the local Kimi pool from all future requests; its earlier probe below is historical evidence, not permission to use it. Kimi K3 will use OpenCode Go.

On 2026-09-30, the supplied replacement Go key was installed in the private proxy configuration. All 11 Go models in the current test plan passed authenticated bash-tool probes with that key. Evidence is in `MODEL-TEST-PLAN.json`. Claude OAuth login is awaiting user browser authorization.

## Scope

One-turn authenticated bash-tool smoke requests; no commands executed and no campaigns launched. Upstream mini-swe-agent migration not exercised.
A successful request proves the route accepted authentication and generated the expected bash tool call. It does not prove checkpoint provenance, long-run quota, reasoning-effort delivery, multi-turn history correctness, or migration readiness.

## Ready models, exercised now

| Authentication route | Request model | Returned model | Protocol |
| --- | --- | --- | --- |
| Codex OAuth | `gpt-5.5` | `gpt-5.5` | chat-completions |
| Codex OAuth | `gpt-5.6-sol` | `gpt-5.6-sol` | chat-completions |
| Codex OAuth | `gpt-5.6-terra` | `gpt-5.6-terra` | chat-completions |
| Codex OAuth | `gpt-5.6-luna` | `gpt-5.6-luna` | chat-completions |
| Codex OAuth | `gpt-6-sol` | `gpt-6-sol` | chat-completions |
| Codex OAuth | `gpt-6-astra` | `gpt-6-astra` | chat-completions |
| Codex OAuth | `gpt-6-luna` | `gpt-6-luna` | chat-completions |
| Codex OAuth | `gpt-6.1-sol` | `gpt-6.1-sol` | chat-completions |
| OpenCode Go API key | `go-hy4-preview` | `hy4-preview` | chat-completions |
| OpenCode Go API key | `go-kimi-k3` | `kimi-k3` | chat-completions |
| Vercel OIDC | `vercel-moonshotai/kimi-k3` | `moonshotai/kimi-k3` | chat-completions |
| Vercel OIDC | `vercel-alibaba/qwen3.8-flash` | `alibaba/qwen3.8-flash` | chat-completions |
| Local Kimi pool | `kimi-k3-modal` | `moonshotai/Kimi-K3` | chat-completions |
| OpenCode Go API key | `go-glm-5.3` | `glm-5.3` | chat-completions |
| OpenCode Go API key | `go-glm-5.3-flash` | `glm-5.3-flash` | chat-completions |
| OpenCode Go API key | `go-minimax-m3` | `minimax-m3` | chat-completions |
| OpenCode Go API key | `go-qwen3.8-max` | `qwen3.8-max` | chat-completions |
| OpenCode Go API key | `go-qwen3.8-flash` | `qwen3.8-flash` | chat-completions |
| OpenCode Go API key | `go-mimo-v2.6-pro` | `mimo-v2.6-pro` | chat-completions |
| OpenCode Go API key | `go-longcat-2.0` | `longcat-2.0` | chat-completions |
| OpenCode Go API key | `go-deepseek-v4-pro` | `deepseek-v4-pro` | chat-completions |
| Vercel OIDC | `vercel-arcee-ai/trinity-large-thinking` | `arcee-ai/trinity-large-thinking` | chat-completions |
| Vercel OIDC | `vercel-google/gemma-4-31b-it` | `google/gemma-4-31b-it` | chat-completions |
| Vercel OIDC | `vercel-inception/mercury-2.5` | `inception/mercury-2.5` | chat-completions |
| Vercel OIDC | `vercel-nvidia/nemotron-3-super-120b-a12b` | `nvidia/nemotron-3-super-120b-a12b` | chat-completions |
| Vercel OIDC | `vercel-stepfun/step-3.7-flash` | `stepfun/step-3.7-flash` | chat-completions |
| Vercel OIDC | `vercel-stepfun/step-5-preview` | `stepfun/step-5-preview` | chat-completions |
| OpenCode Go API key | `grok-4.7` | `grok-4.7` | responses |

## Blockers and caveats

- Anthropic OAuth: Claude Sonnet 5.5 probe returned proxy HTTP 500 with upstream profile HTTP 401. Canonical CLI access/refresh tokens are empty; the inspected proxy credential expiry is stale. Not ready.
- OpenCode Zen: paid Kimi K3 request returned HTTP 402, insufficient account funds. The free Nemotron 3.5 Lightning route returned HTTP 403, free tier restricted to OpenCode. The public model catalog is not evidence of usable balance. Not ready for external benchmark requests tested here.
- xAI / Grok Build OAuth: both Grok 4.7 and Composer 2.5 Fast returned HTTP 402, exhausted usage balance. Not ready on this billing route. Go Grok 4.7 separately succeeded via Responses.
- Go Grok 4.7: current Chat Completions alias failed HTTP 400, unsupported protocol. Direct documented Go Responses succeeded. Use a Responses-capable upstream model path after migration, not the old generic Chat Completions route.
- Go Muse Spark 1.3: workspace privacy settings reject endpoints that train on request data. No privacy setting was changed. Not ready on this route.
- Gemini bridge: Star Gemini 3 Flash returned HTTP 200 but no bash tool call. Authentication/response worked; benchmark tool compatibility was not demonstrated.
- Kiro and Z.ai Coding Plan credentials are stored but were not exercised. Do not mark them ready based on file presence.
- Devin: last observed quota exhaustion remains the known blocker; it was not rechecked in this inventory.
- Cursor: excluded by user decision.

## Credential lifetime

- Codex proxy credential metadata expires 2026-10-06T12:12:54Z.
- Current Vercel OIDC token expires 2026-09-30T15:59:37Z. Refresh is needed before that token expires for later runs.

## Advertised versus verified

The live main proxy advertised 418 models. The local Vercel configuration has 264 model mappings, and Go has 35. These are catalog/configuration counts, not a claim every model is available or tested. Full IDs and all sanitized probe outcomes are saved in `AUTH-READINESS.json`.

No credentials are included in either readiness file.
