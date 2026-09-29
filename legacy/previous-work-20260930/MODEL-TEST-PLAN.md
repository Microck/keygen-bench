# Model test plan

Updated: 2026-09-30T09:44:23.301227+00:00

Planned tests only; no campaigns launched. Native upstream mini-swe-agent integration remains pending. Anthropic candidates require successful OAuth and individual model probes.

One provider per model; Kimi K3 and Qwen3.8 Flash use Go, not Vercel. No automatic provider fallback.

The local Kimi pool is excluded by user instruction. Its historical readiness probe does not authorize future use. The supplied Go key is stored only in the private proxy configuration, not in this manifest.

## Models and providers

| Model | Provider | Readiness |
| --- | --- | --- |
| `gpt-5.5` | codex-oauth | tool-verified-existing-transport |
| `gpt-5.6-sol` | codex-oauth | tool-verified-existing-transport |
| `gpt-5.6-terra` | codex-oauth | tool-verified-existing-transport |
| `gpt-5.6-luna` | codex-oauth | tool-verified-existing-transport |
| `gpt-6-sol` | codex-oauth | tool-verified-existing-transport |
| `gpt-6-astra` | codex-oauth | tool-verified-existing-transport |
| `gpt-6-luna` | codex-oauth | tool-verified-existing-transport |
| `gpt-6.1-sol` | codex-oauth | tool-verified-existing-transport |
| `hy4-preview` | opencode-go | tool-verified-replacement-key |
| `kimi-k3` | opencode-go | tool-verified-replacement-key |
| `glm-5.3` | opencode-go | tool-verified-replacement-key |
| `glm-5.3-flash` | opencode-go | tool-verified-replacement-key |
| `minimax-m3` | opencode-go | tool-verified-replacement-key |
| `qwen3.8-max` | opencode-go | tool-verified-replacement-key |
| `qwen3.8-flash` | opencode-go | tool-verified-replacement-key |
| `mimo-v2.6-pro` | opencode-go | tool-verified-replacement-key |
| `longcat-2.0` | opencode-go | tool-verified-replacement-key |
| `deepseek-v4-pro` | opencode-go | tool-verified-replacement-key |
| `grok-4.7` | opencode-go | tool-verified-replacement-key |
| `stepfun/step-5-preview` | vercel-ai-gateway | tool-verified-existing-transport |
| `stepfun/step-3.7-flash` | vercel-ai-gateway | tool-verified-existing-transport |
| `inception/mercury-2.5` | vercel-ai-gateway | tool-verified-existing-transport |
| `arcee-ai/trinity-large-thinking` | vercel-ai-gateway | tool-verified-existing-transport |
| `nvidia/nemotron-3-super-120b-a12b` | vercel-ai-gateway | tool-verified-existing-transport |
| `google/gemma-4-31b-it` | vercel-ai-gateway | tool-verified-existing-transport |
| `claude-sonnet-5-5` | anthropic-oauth | pending-login-and-model-probes |
| `claude-sonnet-5` | anthropic-oauth | pending-login-and-model-probes |
| `claude-opus-5-5` | anthropic-oauth | pending-login-and-model-probes |
| `claude-opus-5` | anthropic-oauth | pending-login-and-model-probes |
| `claude-opus-4-8` | anthropic-oauth | pending-login-and-model-probes |
| `claude-fable-5-1` | anthropic-oauth | pending-login-and-model-probes |
| `claude-fable-5` | anthropic-oauth | pending-login-and-model-probes |

## Authentication and protocol requirements

- All 11 selected Go models passed HTTP 200 and the expected bash tool call using the replacement key. Grok 4.7 requires Responses; the generic Go Chat Completions route does not work for it.
- Codex and Vercel readiness comes from the earlier live smoke checks saved in `AUTH-READINESS.json`.
- The installed bridge's Claude OAuth login command was exercised, but timed out waiting for browser consent. The user will run the command interactively. Authentication is still pending. Bridge support does not imply Anthropic approval of third-party subscription-funded inference. Respect account eligibility and explicit service denials.
- Run on the benchmark server: `/home/ubuntu/cliproxyapi-keygen/cli-proxy-api -config /home/ubuntu/workspace/keygen-benchmark/benchmark/config/cliproxyapi.local.yaml -claude-login -no-browser`. Follow the URL and callback instructions printed by the command.
- The seven Claude models are candidates advertised by the existing catalog, not a guarantee the account can use them. Probe each after login before launching tests.
- Native upstream mini-swe-agent implementations still need integration and smoke verification. These provider probes do not certify that migration.
- Current Vercel token expires 2026-09-30T15:59:37Z; refresh before later runs.

## Excluded routes and models

No local Kimi pool, Cursor, Zen, xAI Build, Devin, Gemini bridge, or privacy-blocked Muse route will be used in this selection. No privacy settings have been changed and no provider fallback is planned.

Evidence and exact model IDs are preserved in `MODEL-TEST-PLAN.json`.
