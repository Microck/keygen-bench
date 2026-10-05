# Model integration change

Current authentication/model readiness is recorded in [AUTH-READINESS.md](AUTH-READINESS.md), with sanitized catalogs and live tool-call probe outcomes in [AUTH-READINESS.json](AUTH-READINESS.json). These are existing-transport smoke checks, not proof the upstream-model migration is complete.

## Cursor credits and gateway research

Research date: 2026-09-30. No Cursor authentication, model requests, or benchmark runs were performed.

[Cursor's Python SDK documentation](https://cursor.com/docs/sdk/python.md) says SDK runs use the same pricing, request pools and Privacy Mode rules as IDE and Cloud Agent runs. It supports account API keys and local or cloud agent runtimes. This provides a documented way to consume the account's applicable Cursor usage allocation programmatically, subject to plan limits and any additional billed usage. It does not establish the remaining allowance on our account.

[Cursor's API overview](https://cursor.com/docs/api) explicitly says its Cloud Agents API and SDKs run Cursor agent workflows, not standalone model inference or Chat Completions. The Python SDK also states Cursor does not currently document a raw Router endpoint for arbitrary model calls. Cursor Router is therefore not an AI gateway replacement for upstream mini-swe-agent's model provider.

Decision:

- User decision: exclude Cursor from this integration plan because no suitable raw-model API was established.
- Do not add a Cursor SDK/CLI wrapper or a separate Cursor-agent benchmark.
- Preserve this research as the rationale for exclusion, not as planned implementation work.
- Composer access through another provider is separate from Cursor credits and does not change this decision.

Source artifacts: `/tmp/cursor-credit-gateway-research.json`. Durable sources are the linked Cursor documentation above.

## Intended migration, clarified by the user

The intended change is to use upstream mini-swe-agent's original model implementations, with provider configuration and authentication around them. It is not to keep expanding the benchmark's custom `ProxyModel`. The fix documented below is historical interim work, not the target architecture. No runtime migration has been performed by this documentation update.

Use upstream `LitellmModel` for supported Chat Completions and Anthropic Messages providers, and upstream `LitellmResponseModel` for Responses providers. Keep the upstream agent, tool parsing, model-message history and observation handling. Remove the custom model path once every supported caller has migrated and verification passes. Keep benchmark artifact collection and provider evidence outside the model's message transformation.

Online evidence:

- [Upstream LitellmModel](https://mini-swe-agent.com/latest/reference/models/litellm/) calls LiteLLM with the native bash tool, retains the complete assistant message, and removes only local `extra` metadata before forwarding history.
- [Upstream LitellmResponseModel](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/models/litellm_response_model.py) calls `litellm.responses`, preserves response output items across turns and uses the upstream Responses tool parser.

### Provider integration plan

| Provider | Intended integration | Verified documentation and limits |
| --- | --- | --- |
| OpenCode Go | API key, model-specific native protocol and base URL | [Go documentation](https://opencode.ai/docs/go/) lists Chat Completions, Messages and Responses endpoints under `https://opencode.ai/zen/go/v1`. Use the model's documented protocol, not a universal Chat Completions conversion. Send our own identifiable User-Agent and a stable `x-opencode-session` per conversation. |
| OpenCode Zen | API key and model-specific native protocol | [Zen documentation](https://opencode.ai/docs/zen/) publishes model-specific endpoints under `https://opencode.ai/zen/v1`. Treat Zen and Go as separate provider configurations. |
| Vercel AI Gateway | API key or Vercel OIDC, using the appropriate upstream model class | [Vercel Python documentation](https://vercel.com/docs/ai-gateway/sdks-and-apis/python) supports Chat Completions, Responses and Anthropic Messages. OpenAI-compatible base URL is `https://ai-gateway.vercel.sh/v1`; the Anthropic SDK example uses `https://ai-gateway.vercel.sh`. |
| Codex / ChatGPT OAuth | Prefer upstream Responses model with LiteLLM's documented `chatgpt/` provider | [LiteLLM ChatGPT subscription documentation](https://docs.litellm.ai/docs/providers/chatgpt) describes device-flow OAuth, local token storage and Responses support. Compatibility with our pinned dependency versions and existing Codex credential files still needs verification; do not promise automatic credential reuse. |
| Anthropic API access | Upstream Anthropic provider with API key or an authorized supported provider | [Anthropic authentication policy](https://code.claude.com/docs/en/legal-and-compliance) distinguishes API access from native-application subscription OAuth. |
| Anthropic subscription OAuth | Requested, but not an unconditionally supported third-party integration | [Anthropic's current policy](https://code.claude.com/docs/en/legal-and-compliance) reserves subscription OAuth for ordinary native-application use and restricts third-party credential intermediation. Do not impersonate Claude Code, bypass access denials, or substitute its full native agent for mini-swe-agent. Establish permission before implementing this route. |

### Benchmark constraints to resolve before implementation

1. Pin a mini-swe-agent and LiteLLM version that actually contains the required upstream provider/model features. Current online documentation is not proof our installed versions support them.
2. Preserve provider reasoning items, signatures, tool calls and tool results through native protocol handling. Avoid a replacement hand-written message allowlist.
3. LiteLLM's documented ChatGPT subscription provider strips token-limit fields because its backend rejects them. A configured output-token cap must not be reported as enforced on this route. Record the limitation rather than claiming identical generation conditions.
4. Keep retries, time limits, model identity evidence and billing estimates explicit. Upstream retry behavior and cost tracking are not automatically identical to the custom benchmark adapter.
5. Verify each provider with a real two-turn tool-call conversation, including reasoning-history preservation and credential lifecycle. These migration checks have not yet been run. Do not resume benchmark campaigns as part of this research.

The older routing table below records the user's prior preference. This clarified plan additionally includes OpenCode Go/Zen and makes the Anthropic OAuth restriction explicit.

## Anthropic OAuth research for the existing benchmark

Research date: 2026-09-30. Research and documentation only; no authentication attempts, credential changes, migration, or benchmark runs were performed.

### Candidate that preserves upstream mini-swe-agent

[CLIProxyAPI's published documentation](https://pkg.go.dev/github.com/router-for-me/CLIProxyAPI/v7@v7.2.7) explicitly advertises Claude Code OAuth, Claude-compatible APIs and function/tool calling. The benchmark already has this bridge configured on loopback port 8417 in `benchmark/config/cliproxyapi.local.yaml`.

[INFERENCE] The smallest architectural change is to keep upstream mini-swe-agent's `LitellmModel` and put the existing OAuth bridge behind its provider configuration. The bridge would own authentication and protocol compatibility; mini-swe-agent would continue to own model messages, bash tool parsing and its agent loop. This is a candidate, not a verified working migration.

Prefer testing the bridge's Anthropic Messages interface rather than forcing every Claude request through Chat Completions. Confirm the installed bridge's endpoint support, native thinking/signature handling and exact model routing before choosing that configuration. Do not reuse a static, expired OAuth token as a permanent provider key. Previously observed empty CLI credentials and proxy refresh HTTP 403 remain blockers, not evidence this candidate is currently usable.

The current local configuration includes a Claude Code fingerprint profile. Its presence is not proof of permission or compatibility. This research does not provide or endorse client impersonation, fingerprint evasion, or bypassing an explicit access denial.

### Alternative gateway evidence

[LiteLLM documents Claude Code Max subscription passthrough](https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription), with separate gateway authentication and forwarded upstream OAuth authentication. Its documented client is Claude Code. The guide establishes a gateway capability; it does not establish that arbitrary mini-swe-agent traffic is accepted, that LiteLLM independently manages the OAuth lifecycle, or that Anthropic permits this use.

Treat this as a second compatibility candidate, not a reason to replace the existing bridge before testing. Keep gateway credentials and provider credentials separate, and do not log either.

### Official SDK evidence changes the earlier blanket statement

[Anthropic's help-center article](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) has a June 15 update saying the announced billing change was paused and that Agent SDK, `claude -p`, and third-party app usage still draw from subscription limits. The previously announced separate monthly credits are not available. Do not repeat the outdated credit table as current policy.

However, the [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) says it runs the Claude Code binary and its agent loop, and separately requires prior approval for third-party products offering Claude.ai login or subscription rate limits. [Anthropic's legal/authentication documentation](https://code.claude.com/docs/en/legal-and-compliance) also restricts third-party credential intermediation. These sources describe different scopes. Subscription-funded native SDK use is not proof of unrestricted raw Messages API access from our own model adapter.

Using the SDK or `claude -p` could supply a separate Claude-native-agent experiment. It must not be silently substituted for the requested upstream mini-swe-agent benchmark, because it adds Claude Code's own agent runtime. Any proposal to use it only as a model transport would first need evidence that its prompts, context, tools and control loop remain equivalent.

### Reported technical failure relevant to our bash tool

[Hermes issue 15080](https://github.com/NousResearch/hermes-agent/issues/15080) reports that OAuth text requests succeeded while tool-bearing requests failed with an overage error on the reporter's account. This is a community observation, not a reproduced result for our account or a universal Anthropic rule. It shows why a successful text-only request cannot verify benchmark compatibility.

### Decision and acceptance criteria

Keep the existing bridge as the first unofficial candidate for an upstream-model migration. Current technical compatibility and provider permission remain unverified. Do not claim a working Anthropic OAuth integration based solely on published gateway support.

Before implementation or campaign use:

1. Obtain usable credentials through the provider's own authorized flow. Stop on an explicit access denial; do not work around it.
2. Confirm the installed bridge exposes the chosen native protocol and routes to the intended Claude model without a silent provider/model fallback.
3. Exercise a real two-turn bash-tool conversation through the upstream mini-swe-agent model class, including thinking/signature and tool-result history.
4. Check credential expiry and refresh behavior without exposing credentials or substituting a different billing route.
5. Record this as an unofficial transport with its failure and billing provenance. Keep original results unchanged and do not claim parity until verified.

Saved search artifacts: `/tmp/anthropic-oauth-benchmark-research.json` and `/tmp/anthropic-oauth-bridge-options.json`. The linked primary and community sources above are the durable reference; temporary search files may not persist.

## Historical interim implementation

`benchmark/proxy.py` now preserves provider reasoning state across assistant tool-call turns.

Previously, the adapter retained assistant content and tool calls but discarded provider reasoning fields. The next model request therefore lacked the reasoning state returned on the previous turn. This was a benchmark integration defect, not evidence of poor model capability.

The implemented change:

- Defines `REASONING_FIELDS = ("reasoning_content", "reasoning", "reasoning_details")`.
- Includes those fields in the assistant-message forwarding allowlist.
- Copies each field present in the provider response into the assistant message returned by `ProxyModel.query()`.
- Preserves field values rather than converting or reconstructing them.
- Keeps mini-swe-agent's local `extra` metadata out of upstream message history.

The existing exact `response_model` guard, bash function-tool contract, full response recording, request audit records and retry policy remain in place. Do not weaken the identity guard to accommodate gateway error envelopes or silently accept a different model.

## Required provider routing

The user's routing choice is:

| Model maker | Authorized integration |
| --- | --- |
| OpenAI | Codex OAuth. Do not substitute Vercel for an unavailable native model. |
| Anthropic | Claude OAuth. Do not substitute Vercel for unavailable Claude authentication. |
| Other makers | Vercel AI Gateway is authorized. |

Use exact model identities and preserve the original campaign's prompts, generation parameters and limits when making controlled repeats. Record provider changes explicitly. An exact returned model name does not prove the underlying checkpoint, delivered reasoning effort or absence of upstream fallback.

Muse Spark 1.2 and 1.3 should appear without the public display label `Contributor`. Preserve original route identifiers and billing evidence in machine-readable records.

## Verification already observed

- A two-turn real Kimi K3 tool-call smoke preserved `reasoning` and `reasoning_details` into the second request and produced the requested second tool action.
- The benchmark contract suite passed 34 tests after the adapter change in the prior session.
- A separate Kimi K3 repeat produced a collected and reference-rendered artifact scoring 40.9/100 with craft-v7. Its original score remains 5.8/100.
- The Kimi repeat used Vercel instead of Devin and ended on a command timeout. It is not a controlled measurement of the reasoning-history fix alone.

Kimi evidence is in `benchmark/runs/kimi-k3-retest/profiles.md` and `benchmark/runs/kimi-k3-retest/kimi-k3/profile.json`.

## Integration failures and limits

- Claude CLI credentials most recently inspected had empty access and refresh tokens. The benchmark proxy had stored Claude tokens, but they were expired. Refresh at the canonical OAuth endpoint returned HTTP 403, Cloudflare error 1010. Do not bypass that denial or claim Claude is ready.
- Native GPT-5.5, GPT-5.6 Sol and GPT-5.6 Luna accepted real bash tool-call probes with matching returned identities. Older GPT-5.4, GPT-5.4 mini and GPT-5.3 Codex native requests previously returned model-not-found errors.
- Cohere Command A's first attempt received an HTTP 200 gateway error envelope for an invalid JSON response. Its missing model field triggered the local identity guard; no alternate model was actually observed.
- Cohere's second attempt declared submission without a collected `submission/tune.xm`. Neither attempt produced a scored artifact.
- The archived Composer 2.5 fast probe returned HTTP 402 for exhausted Grok Build usage. The later authenticated proxy catalog contained no Composer route. Cursor's native agent wrapper is not an equivalent raw-model benchmark integration.

## Retest provenance and stop instruction

Original results must not be replaced with whichever repeat scores higher. Preserve failed and protocol-confounded attempts as well.

The repeat records are under `benchmark/runs/low-score-retests-20260929/`. The full 39-model audit is in `benchmark/runs/low-score-audit.md` with supporting `low-score-audit.json`.

The campaign owner's final report confirms 26 attempts across 23 original identities had completed before the stop instruction: 25 rendered artifacts, 16 protocol-eligible attempts, and 10 initially protocol-confounded attempts. Completed outcomes are saved in `outcomes.json` and `repeat-table.md` under the repeat directory. Nine initial repeats changed the system prompt; three used a 180-second request timeout instead of the original 600 seconds, with two overlapping the prompt-confounded set. Separate exact-limit corrections remain preserved without best-of selection. Protocol eligibility does not establish upstream checkpoint or reasoning-effort equivalence.

The user instructed all work to stop. The campaign owner confirmed no assignment campaign or orchestration processes remained and launched nothing further. Both delegated agents stopped. Existing artifacts are preserved. Do not resume work without a new user instruction.
