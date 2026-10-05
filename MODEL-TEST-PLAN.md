# Full model test inventory

Updated: 2026-09-30T10:30:16.966023+00:00

74 mapped model identities remain in the plan, including five Devin models held until renewal. Three rejected historical route records are retained separately, and actual Cursor Composer 2.5 is a separate candidate without an approved route. These counts describe the inventory, not campaign readiness.

The native implementation is active. Historical inventory statuses describe earlier transport access, not current native readiness. `benchmark/campaign.py` requires exact multi-turn native proof before freezing an executable selection. Campaigns allow up to three sequential attempts and stop after the first eligible success. Neither an inventory nor a catalog entry authorizes inference.

## Restrictions

- No Gemini bridge. The user reports there is no usable Gemini bridge.
- No OpenCode Zen.
- No local Kimi pool. Kimi K3 uses OpenCode Go with the supplied key.
- Devin is held until quota renewal. No quota polling or retries are scheduled.
- Actual Cursor Composer 2.5 is not the xAI Grok-labelled model. No substitution or Cursor agent wrapper will be used.
- Future GPT/OpenAI routes must use Codex OAuth Responses. Future Claude/Anthropic routes must use Anthropic OAuth Messages through the existing approved CLIProxyAPI bridge. Do not fall back to Vercel or substitute a different checkpoint.
- Prefer OpenCode Go for supported, native-qualified exact non-OAuth models. Keep Vercel AI Gateway for remaining approved identities pending funding. Cloudflare AI Gateway is excluded.

## Composer availability

The live [Vercel public model catalog](https://ai-gateway.vercel.sh/v1/models) advertised 395 models at 2026-09-30T10:28:41.070093+00:00. No entry contained Cursor or Composer. Actual Cursor Composer 2.5 is therefore not advertised on that public catalog; no approved raw-inference route is selected. This does not establish anything about private contractual access.

## Preserved previous work

Previous work remains at `legacy/previous-work-20260930/`. Historical runs were moved there; code, configs, docs and web assets were copied into their original layout. Active code and credential paths remain intact. All 2,528 moved run files and 165 stored profiles were verified. Private configs are included; do not publish the archive.

## Prospective OAuth-first routing

`MODEL-TEST-PLAN.oauth-first.json` is the default inventory for both `benchmark/campaign.py` and `benchmark/drive.py`. It preserves all 74 original identities under the current OAuth-first, Go-preferred policy. `MODEL-TEST-PLAN.json` and all original full-launch manifests, selections, proofs, results and controller sources remain historical evidence. New campaign provenance captures the current inventory and compiler/driver source hashes; historical execution requires the retained original controller source. Native proof fingerprints are unchanged because the native model, qualification workflow, sandbox and upstream SDK source did not change. Moving an identity from Vercel to Go still requires a new exact native route qualification.

The prospective inventory now maps Muse Spark 1.2/1.3 Contributor to OpenCode Go. Their Chat requests were protocol-rejected, but each exact identity passed the original native `LitellmResponseModel` three-turn workflow with `max_output_tokens: 32768` and matching returned IDs. No privacy settings, native histories or checkpoints were changed. Historical Vercel mappings remain preserved; unfinished inference can use only remaining original attempt ordinals.

The authenticated approved bridge catalog returned HTTP 200 on 2026-10-01 with 497 entries. The table below tests exact unprefixed IDs owned by OpenAI or Anthropic, not Vercel-prefixed aliases. Catalog visibility does not prove a live completion or native tool readiness. The operational evidence and exact observation time are in `benchmark/runs/oauth-route-audit-20261001.json`.

| Exact model identity | Required future route | Exact OAuth catalog ID | Retained native qualification |
| --- | --- | --- | --- |
| `gpt-5.5` | Codex Responses | Present | Verified |
| `gpt-5.6-luna` | Codex Responses | Present | Verified |
| `gpt-5.6-sol` | Codex Responses | Present | Verified |
| `gpt-5.6-terra` | Codex Responses | Present | Verified |
| `gpt-6-astra` | Codex Responses | Present | Verified |
| `gpt-6-luna` | Codex Responses | Present | Verified |
| `gpt-6-pro` | Codex Responses | Absent, blocked | None |
| `gpt-6-sol` | Codex Responses | Present | Verified |
| `gpt-6.1-sol` | Codex Responses | Present | Verified |
| `gpt-5.3-codex` | Codex Responses | Absent, blocked | Exact OAuth first request failed with `NotFoundError` |
| `gpt-5.4` | Codex Responses | Absent, blocked | Exact OAuth first request failed with `NotFoundError` |
| `gpt-5.4-mini` | Codex Responses | Absent, blocked | Exact OAuth first request failed with `NotFoundError` |
| `gpt-oss-120b` | No qualified approved OAuth route | Absent, blocked | Exact OAuth first request failed with `NotFoundError` |
| `claude-3-opus-20240229` | Anthropic Messages | Absent, blocked | None |
| `claude-fable-5` | Anthropic Messages | Present | Verified |
| `claude-fable-5-1` | Anthropic Messages | Present | Verified |
| `claude-opus-4-5-20251101` | Anthropic Messages | Present | Verified |
| `claude-opus-4-6` | Anthropic Messages | Present | Verified |
| `claude-opus-4-7` | Anthropic Messages | Present | Verified |
| `claude-opus-4-8` | Anthropic Messages | Present | Verified |
| `claude-opus-5` | Anthropic Messages | Present | Verified |
| `claude-opus-5-5` | Anthropic Messages | Present | Blocked after `RepeatedFormatError` |
| `claude-sonnet-4-6` | Anthropic Messages | Present | Verified |
| `claude-sonnet-5` | Anthropic Messages | Present | Verified |
| `claude-sonnet-5-5` | Anthropic Messages | Present | Verified |

Retained qualification is bound to its recorded protocol, generation settings, executable hashes and returned identity. The 18 verified OAuth models are candidates for a separately authorized new campaign, not permission to resume the cancelled campaign. Claude Opus 5.5 remains blocked until a separately authorized native three-turn tool qualification succeeds.

The four previously Vercel-routed GPT models were requested by exact ID through the approved local Responses bridge using the original native three-turn offline-tool workflow. Each made one request, then failed with `NotFoundError` and `provider_request_error`. The retained trajectory identifies the actual error as `unknown provider for model <ID>` with code `model_not_found`, from CLIProxyAPI's model registry before upstream execution. No upstream Codex model/account availability was tested. No successful response or fallback occurred, and all owned sandboxes were removed. `benchmark/runs/oauth-exact-qualification-20261001/summary.json` links the original native artifacts; `exact-model-registration-investigation.json` in the same directory records this distinction and the supported-configuration investigation. The absent `gpt-6-pro` and old Claude Opus 3 entries were not re-probed. No musical inference ran.

The approved bridge's file-backed OAuth path registers its upstream-maintained plan catalog only. OAuth aliases rename or fork already registered models; a same-ID alias cannot add an absent checkpoint. Aliasing a different model would substitute its upstream checkpoint and is prohibited. The investigated static OAuth-bearer `codex-api-key.models` path would change credential kind, refresh and account-header handling, so it was declined and not applied. No token was duplicated and no shared bridge configuration, header, auth lifecycle or process changed. The precise blocker for the four exact IDs is missing approved-bridge OAuth registration; upstream account entitlement remains UNTESTED.

The old plan moved GPT 5.3 Codex, GPT 5.4 and GPT 5.4 Mini from historical Devin IDs to Vercel IDs. Its notes explicitly deny checkpoint or score equivalence. GPT-OSS-120B already had a Vercel profile and retained that route. The old policy allowed one approved provider per identity but did not require OAuth by family. The compiler checked that mapping, rather than inferring a provider from a model's name. The exact four checkpoints are absent from the current approved OAuth catalog; this explains the route distinction but does not establish the author's undocumented intent.

Actual deployed campaign locks confirm eight Codex and ten Claude configurations on Ashburn's OAuth bridge and the four OpenAI configurations on Paris's direct Vercel endpoint. No Claude configuration used Vercel in the full launch. None of the 31 Claude profiles among the 165 retained historical profiles names a Vercel route either. Vercel Claude aliases exist in the broad proxy catalog, but catalog/config presence is not evidence that they ran. Historical Devin Claude results remain labeled Devin.

GPT-OSS-120B is the original open-weight model, not a Codex checkpoint or another GPT generation. It remains visible and blocked under the prospective policy; renaming a different model or retaining a paid Vercel fallback would violate that policy.

## Historical mapped models

### Codex OAuth (9)

| Model identity | Upstream request ID | Status |
| --- | --- | --- |
| `gpt-5.5` | `gpt-5.5` | tool-verified-existing-transport |
| `gpt-5.6-luna` | `gpt-5.6-luna` | tool-verified-existing-transport |
| `gpt-5.6-sol` | `gpt-5.6-sol` | tool-verified-existing-transport |
| `gpt-5.6-terra` | `gpt-5.6-terra` | tool-verified-existing-transport |
| `gpt-6-astra` | `gpt-6-astra` | tool-verified-existing-transport |
| `gpt-6-luna` | `gpt-6-luna` | tool-verified-existing-transport |
| `gpt-6-pro` | `gpt-6-pro` | blocked-not-in-saved-catalog |
| `gpt-6-sol` | `gpt-6-sol` | tool-verified-existing-transport |
| `gpt-6.1-sol` | `gpt-6.1-sol` | tool-verified-existing-transport |

### Anthropic OAuth (12)

| Model identity | Upstream request ID | Status |
| --- | --- | --- |
| `claude-3-opus-20240229` | `claude-3-opus-20240229` | blocked-not-in-saved-catalog |
| `claude-fable-5` | `claude-fable-5` | pending-model-smoke |
| `claude-fable-5-1` | `claude-fable-5-1` | pending-model-smoke |
| `claude-opus-4-5-20251101` | `claude-opus-4-5-20251101` | pending-model-smoke |
| `claude-opus-4-6` | `claude-opus-4-6` | pending-model-smoke |
| `claude-opus-4-7` | `claude-opus-4-7` | pending-model-smoke |
| `claude-opus-4-8` | `claude-opus-4-8` | pending-model-smoke |
| `claude-opus-5` | `claude-opus-5` | pending-model-smoke |
| `claude-opus-5-5` | `claude-opus-5-5` | pending-model-smoke |
| `claude-sonnet-4-6` | `claude-sonnet-4-6` | pending-model-smoke |
| `claude-sonnet-5` | `claude-sonnet-5` | pending-model-smoke |
| `claude-sonnet-5-5` | `claude-sonnet-5-5` | pending-model-smoke |

### OpenCode Go (25)

| Model identity | Upstream request ID | Status |
| --- | --- | --- |
| `deepseek-v4-flash` | `deepseek-v4-flash` | blocked-original-checkpoint-unproven |
| `deepseek-v4-pro` | `deepseek-v4-pro` | tool-verified-supplied-key |
| `deepseek-v4.1-flash` | `deepseek-v4.1-flash` | pending-model-smoke |
| `glm-5.2` | `glm-5.2` | pending-model-smoke |
| `glm-5.3` | `glm-5.3` | tool-verified-supplied-key |
| `glm-5.3-flash` | `glm-5.3-flash` | tool-verified-supplied-key |
| `grok-4.6` | `grok-4.6` | pending-model-smoke |
| `grok-4.7` | `grok-4.7` | tool-verified-supplied-key |
| `hy3` | `hy3` | pending-model-smoke |
| `hy4-preview` | `hy4-preview` | tool-verified-supplied-key |
| `kimi-k2.6` | `kimi-k2.6` | pending-model-smoke |
| `kimi-k2.7-code` | `kimi-k2.7-code` | pending-model-smoke |
| `kimi-k3` | `kimi-k3` | tool-verified-supplied-key |
| `longcat-2.0` | `longcat-2.0` | tool-verified-supplied-key |
| `mimo-v2.6-pro` | `mimo-v2.6-pro` | tool-verified-supplied-key |
| `minimax-m2.5` | `minimax-m2.5` | pending-model-smoke |
| `minimax-m2.7` | `minimax-m2.7` | pending-model-smoke |
| `minimax-m3` | `minimax-m3` | tool-verified-supplied-key |
| `omen-alpha` | `omen-alpha` | pending-model-smoke |
| `qwen3.6-plus` | `qwen3.6-plus` | pending-model-smoke |
| `qwen3.7-max` | `qwen3.7-max` | pending-model-smoke |
| `qwen3.7-plus` | `qwen3.7-plus` | pending-model-smoke |
| `qwen3.8-flash` | `qwen3.8-flash` | tool-verified-supplied-key |
| `qwen3.8-max` | `qwen3.8-max` | tool-verified-supplied-key |
| `space-bunny-free` | `space-bunny-free` | pending-model-smoke |

### Vercel AI Gateway (23)

| Model identity | Upstream request ID | Status |
| --- | --- | --- |
| `command-a` | `cohere/command-a` | pending-model-smoke |
| `gemini-3-flash` | `google/gemini-3-flash` | pending-model-smoke |
| `gemini-3.1-pro-preview` | `google/gemini-3.1-pro-preview` | pending-model-smoke |
| `gemini-3.5-flash` | `google/gemini-3.5-flash` | pending-model-smoke |
| `gemini-3.6-flash` | `google/gemini-3.6-flash` | pending-model-smoke |
| `gemini-3.7-flash` | `google/gemini-3.7-flash` | pending-model-smoke |
| `gemini-3.8-flash` | `google/gemini-3.8-flash` | pending-model-smoke |
| `gemma-4-31b-it` | `google/gemma-4-31b-it` | tool-verified-existing-transport |
| `gpt-5.3-codex` | `openai/gpt-5.3-codex` | pending-model-smoke |
| `gpt-5.4` | `openai/gpt-5.4` | pending-model-smoke |
| `gpt-5.4-mini` | `openai/gpt-5.4-mini` | pending-model-smoke |
| `gpt-oss-120b` | `openai/gpt-oss-120b` | pending-model-smoke |
| `grok-4.5` | `spacexai/grok-4.5` | pending-model-smoke |
| `inkling` | `thinkingmachines/inkling` | pending-model-smoke |
| `mercury-2.5` | `inception/mercury-2.5` | tool-verified-existing-transport |
| `mistral-medium-3.5` | `mistral/mistral-medium-3.5` | pending-model-smoke |
| `muse-spark-1.2-contributor` | `meta/muse-spark-1.2-contributor` | pending-model-smoke |
| `muse-spark-1.3-contributor` | `meta/muse-spark-1.3-contributor` | pending-model-smoke |
| `nemotron-3-super-120b-a12b` | `nvidia/nemotron-3-super-120b-a12b` | tool-verified-existing-transport |
| `nemotron-3-ultra-550b-a55b` | `nvidia/nemotron-3-ultra-550b-a55b` | pending-model-smoke |
| `step-3.7-flash` | `stepfun/step-3.7-flash` | tool-verified-existing-transport |
| `step-5-preview` | `stepfun/step-5-preview` | tool-verified-existing-transport |
| `trinity-large-thinking` | `arcee-ai/trinity-large-thinking` | tool-verified-existing-transport |

### Devin (5)

| Model identity | Upstream request ID | Status |
| --- | --- | --- |
| `kimi-k2.7` | `devin/kimi-k2-7` | held-until-devin-renewal |
| `swe-1.6` | `devin/swe-1-6` | held-until-devin-renewal |
| `swe-1.7` | `devin/swe-1-7` | held-until-devin-renewal |
| `swe-1.7-lightning` | `devin/swe-1-7-lightning` | held-until-devin-renewal |
| `swe-2` | `devin/swe-2` | held-until-devin-renewal |

## Excluded historical route records

| Historical model | Rejected route | Reason |
| --- | --- | --- |
| `gemini-3.1-pro` | Gemini bridge | User reports no Gemini bridge and explicitly prohibits its use. Exact non-preview model has no approved replacement route. |
| `grok-composer-2.5-fast` | xAI OAuth | User means actual Cursor Composer 2.5. The xAI Grok-labelled model is not an established equivalent and must not be substituted. |
| `nemotron-3.5-lightning-free` | OpenCode Zen | User explicitly prohibits OpenCode Zen. |

These records are evidence only, not scheduled tests. Gemini 3.1 Pro non-preview has no approved replacement route; it will not be substituted with Pro Preview.

## Unroutable requested model

- Actual Cursor Composer 2.5: held until an approved raw-model route exists. No provider selected.

## Remaining verification

Current exact catalog availability and forward actions are recorded above and in `benchmark/runs/oauth-route-audit-20261001.json`. Native tool proofs are separate from catalog visibility. The original full launch is cancelled, and this policy does not authorize a retry, top-up or musical inference run.

Exact historical aliases, source files, per-model notes and earlier probes remain in `MODEL-TEST-PLAN.json`. New selections must compile against `MODEL-TEST-PLAN.oauth-first.json`; exact absent checkpoints and failed native qualifications remain blocked.
