# Muse Wonder Full access investigation

Checked 2026-10-23. Status: requested, access investigation only. No budget estimate,
fundraising target, funded run, subscription purchase, or frozen-provider approval.
The support page deliberately does not show $0 or a progress bar for this request.

## Identity and entitlement

[Meta's model documentation](https://dev.meta.ai/docs/models) distinguishes regular
`muse-wonder-1.0` from Wonder Full. Full is subscription-only in Muse Code's Power
Usage and Maximum Usage plans, not the public pay-as-you-go Model API. Selecting
max reasoning on regular Wonder does not select Full. Discover the exact entitled
ID and supported effort from the authenticated host's `model/list`; never silently
fall back to regular Wonder or infer entitlement from a display name.

## A supported way to automate it

The official [Muse Code SDK](https://github.com/meta-models/muse-code-sdk) drives
an installed Muse Code host over MSP. Its [quickstart](https://meta-models.github.io/muse-code-sdk/1.4/guides/quickstart/)
covers starting sessions, turns, approvals, cancellation and resume. This is a
concrete automation route for Muse Code, not a raw inference API or a verified
Wonder Full benchmark integration. No live account has been tested here.

A candidate mini-swe-agent transport is:

1. Start an isolated, version-pinned Muse Code host with authorized subscription
   authentication kept outside the benchmark container.
2. Select the exact Full model via `model/list` and `session/start`, recording the
   schema fingerprint, binary version, effort and Standard/Contributor mode.
3. Expose a single local MCP Bash tool. Hold its response while a transport adapter
   returns the call to mini; mini executes it in the offline benchmark Docker
   environment and supplies the observation, which resolves the pending MCP call.
4. Keep one host session per attempt, with strict call IDs, exact observations,
   cancellation and no hidden retries, fallback models or cross-attempt history.

[MCP tools run outside Muse Code's own sandbox](https://meta-models.github.io/muse-code-sdk/1.4/guides/extend/mcp-servers/).
The MCP server must only relay calls to the benchmark sandbox, never execute model
commands on the host. This held-call design is a hypothesis to prototype, not an
implemented or tested adapter in this PR. An approval response alone is not a tool
result injection API.

## What prevents a frozen-equivalence claim

- The documented [session/start schema](https://meta-models.github.io/muse-code-sdk/1.4/generated/msp/methods/session-start/)
  exposes model selection and MCP configuration, not full system-prompt replacement.
  No supported equivalent to Cursor's `systemPrompt` was established. Adding an
  AGENTS.md or a user instruction is not replacement of the harness prompt.
- [Host options](https://meta-models.github.io/muse-code-sdk/1.4/guides/host-operations/)
  can disable native shell/write execution. That does not prove native tool schemas,
  built-in instructions, memory, skills, reminders or auxiliary model calls disappear.
- The bridge would still run Muse Code's upstream loop. A working MCP round trip
  alone does not make mini the only harness or establish prompt/tool equivalence.
- [VulcanBench's firsthand run notes](https://github.com/morganlinton/VulcanBench/blob/main/docs/DECISIONS.md)
  report Muse Code 1.4.9 reminder observers using Spark 1.3 despite Full being the
  main model. This is a reported version-specific finding, not independently
  reproduced here; audit all inference, not just the main model field.
- Verify every required generation limit and reasoning setting, plus complete
  model identity and usage provenance. Unknown cost is not zero, and regular
  Wonder API prices are not Full's actual subscription bill.

If these controls cannot be made equivalent, an automated Muse Code run can still
be useful as a separately labelled, non-ranked harness experiment. Do not add it
silently to the native-provider whitelist or compare it as a frozen mini run.

## Before a live pilot

Obtain explicit quota/spending authorization and secure login. Use Standard mode
unless the contributor explicitly accepts training use: [Meta documents](https://dev.meta.ai/docs/models)
that subscriptions default to Contributor mode, which permits training on prompts,
code, files and responses. Do not copy subscription tokens into a generic API
client or claim that SDK support authorizes private-endpoint impersonation.

First prove a synthetic multi-turn Bash round trip, identity, cancellation,
isolation, prompt/tool inventory and absence (or complete disclosure) of auxiliary
inference. Then verify the pinned FT2 render/scoring flow. Keep all results outside
the ranked condition until the contract is demonstrably met. No credentials,
account inspection, live model calls or spending were involved in this research.
