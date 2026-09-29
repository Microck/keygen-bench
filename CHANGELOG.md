# Changelog

## [Unreleased]

### Added
- Independent systemd campaign watchdogs with persistent progress/issue records, owned-process supervisor-loss recovery and post-run Paris service restoration checks
- Host a current-results HTTPS preview with verified public media, retained cohort/artifact provenance, native first-success diagnostics and isolated static-file serving
- Continue unfinished native work in separate immutable campaigns using remaining original attempt ordinals, with owned resource/terminal guards and Minecraft restoration forbidden
- Declare each model's reasoning tier from a per-model tier spec; the compiler (`--tier-spec`) rejects missing tiers, blocked/unknown tiers and generations lacking the spec's reasoning control, and readiness fails unless that control appears in every recorded transmitted request
- Balance OpenCode Go attempts across a frozen key pool: each attempt holds one least-loaded key under its per-key cap for the whole model run, and status records only the key name
- NVIDIA NIM Chat route with per-model `chat_template_kwargs` through the SDK's `extra_body` pass-through; Go Anthropic Messages route with top-level thinking/effort
- Draft maximum-tier selections, pilot specs and a qualification plan for the next campaign under `benchmark/runs/next-launch-prep-20261001/` (not launched)
- Long-generation probe (`native_readiness.py --probe long-generation`, one per route family in the next-launch qualification plan) that checks a single non-streaming request survives more than 32k output tokens or 10 minutes; it is never readiness evidence
- Bounded transport-only retries: `native.retries` 0–2 drives LiteLLM's `retry_policy` (timeouts, HTTP 500/503); `status.totals.transport_retries` counts re-sent requests

### Changed
- Prompt v2 (`prompts.version`): `system.txt` states only operational harness facts (command limit and exit code, output truncation, `<time_left>` on every result, submission limits with dropped extras, collection at timeout) and drops "judged as a file"; `task.txt` unchanged
- Quota, funds, usage-limit and 429 failures are infrastructure `QUOTA`; a `QUOTA`/`AUTH` attempt stops the model's sequence and leaves later slots `RESERVED` instead of consuming them
- Collect `tune.xm` independently; oversize or irregular optional extras are dropped with a recorded note instead of failing the attempt
- Readiness pilot permits several tool calls per reply and requires one two-call turn
- Format errors say when the output cap cut a reply off
- Output cap rule: when a documented output limit is not separate from the context window, cap at half the window (Grok 250k, Kimi K2.7 Code 131,072, and others); next-launch OAuth providers bounded to 4 concurrent attempts each
- Report and site label rows by cohort ("highest declared tier: max, 128k output" vs "provider default effort, 32k output", plus prompt version), show one table per cohort, count `QUOTA` as infrastructure, and disclose that each score is one quality sample
- Replace the pinned LiteLLM capability-map gate for xhigh/max with the declared tier; reject routes whose effort the SDK would drop, alter, refuse or reroute (e.g. GPT-5.4+ Chat silently bridged to Responses)
- Campaign schema `keygen-native-campaign-3`: models carry `tier`, concurrency carries `key_pools` and a `nim` provider bound
- Default future campaign compilation to OAuth-only GPT/Claude routing; preserve historical mappings and visibly block exact identities unavailable in the approved OAuth bridge registry
- Prefer qualified OpenCode Go routes for non-OAuth models, retain Vercel pending funding, and exclude Cloudflare AI Gateway
- Use original upstream mini-swe-agent model implementations and native Chat, Responses and Anthropic Messages history instead of the custom model adapter
- Compile inventory selections into immutable campaigns with up to three sequential attempts per model, stopping at first eligible success, approved-route policy, exact settings and recorded multi-turn readiness evidence
- Archive allowlisted result bundles to dedicated verified storage before bulk eviction; restore verified artifacts for later evaluation
- Keep craft-v7 explicitly auxiliary and publish every executed attempt and skipped-after-success slot within exact experimental conditions
- Replace workflow and raw-count scoring bonuses with deterministic artifact-only craft-v7 tonal-development evidence
- Score audio-derived tonal organization, retained-motif development and dynamics; apply signal, sustained-noise and bounded loop-continuity multipliers instead of additive delivery bonuses
- Apply a uniform duration-sufficiency factor below 30 audible first-pass seconds, informed by a reproducible 256-module historical sample; no length bonus above the threshold
- Calibrate tonal-fraction, diatonic-concentration, sustained-noise, DC-offset and restart level/timbre bounds against 256 archived keygen XMs, with a hash-split calibration half and held-out validation; genuine tracks no longer lose most of their points to a-priori thresholds
- Use pinned continuous FT2 playback for loop scoring and source-separated mix analysis, with exact transition timestamps and lossless listening excerpts
- Extend reference stem analysis through 22.05 kHz and retain uncertain selected-lead masking as a diagnostic, not an aggregate scoring input
- Remove order-table-rewriting listening packets; profiling now produces actual-runtime loop previews
- Publish content subtotals, multipliers, full-band spectral evidence and explicit musical-quality limitations without model-specific rules or per-run adjustments
- Keep runtime transition continuity and lossless loop previews while limiting their whole-score effect to a 0.75–1 multiplier
- Display Muse Spark 1.2 and 1.3 without Contributor billing-tier suffixes; retain original attempt identities and pricing evidence
- Finalize the Support introduction and donation instructions
- Publish the Codex-auth GPT-6.1 Sol result and its official API list-price estimate

### Fixed
- Restrict watchdog heartbeat-stall alerts to running campaigns; graceful shutdown legitimately pauses resource sampling while workers drain
- Keep infrastructure, provider and evaluator failures out of musical scores with explicit null values and failure denominators
- Allow verified artifact export with non-secret `KEYGEN_FT2_ANALYSIS` configuration while retaining credential-name and split-block leak detection
- Preserve the full Boat startup budget across individual readiness waits instead of prematurely timing out verified image-bundle transfers
- Preserve interrupted reservations and separate retry identities; publish campaign and attempt metadata atomically
- Include actual SciPy and numerical implementation fingerprints; reuse current profiles and preserve forced evaluation generations
- Bound inference by provider and separate render, video and scoring concurrency with storage and memory admission
- Export paused tmpfs-backed Boat workspaces through a live read-only helper instead of Docker cp; retain verified cleanup and binary transport evidence
- Preserve opposite-polarity stereo energy when detecting silence
- Calculate clipping from the actual sample count and ignore unused samples when applying baked-audio caps
- Respect nonzero restart positions and carried playback state instead of treating WAV export endpoints as loop points
- Prevent silent boundaries and brief clear melodic fragments from receiving misleadingly high loop or mix scores
- Match FT2's 64-row normalization of entirely empty patterns
- Prevent clean repeated noise from receiving free audio and loop points; distinguish sustained noise from short percussion without blanket 8-bit or bright-waveform penalties
- Require changed parts to retain their own motifs; repeating accompaniment cannot certify arbitrary melody changes as development
- Prevent repeated exports and silent padding from supplying missing first-pass duration; retain legitimate short loops without a hard eligibility cutoff
- Load historical XMs the way the pinned FT2 loader does: orders naming absent patterns play empty 64-row patterns, and instruments missing from a truncated file are empty

## 1.0.0 — 2026-09-04

- Added structured English research on historical authoring programs.
- Separated tracker modules from procedural-synth workflows.
- Documented composition, sample design, effects, looping, optimization, and runtime replay.
- Added a source register and confidence methodology.
- Added public archive metadata case studies without redistributing music.
- Added machine-readable tool, claim, and archive-example data.
- Added a dependency-free XM/IT/S3M/MOD header inspector and synthetic tests.
