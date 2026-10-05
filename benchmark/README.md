# Native mini-swe-agent benchmark

Historical code, configurations, reports, web assets and runs are preserved under `../legacy/previous-work-20260930/`. Do not modify historical results or publish private archived configurations. Campaigns compiled from now on use prompt v2 (`campaign.PROMPT_VERSION`, recorded as `prompts.version`); earlier campaigns, which have no `version`, ran prompt v1. Prompt v2 changes only operational harness facts in `prompts/system.txt`: the per-command limit (exit code 124, or 137 if killed), output truncation over 20,000 bytes, `<time_left>` on every tool result, submission limits with dropped extras, and collection of the saved `tune.xm` when time runs out. It also drops "the module is judged as a file". `prompts/task.txt` is unchanged. The command limit and submission MiB are substituted from the frozen limits.

## Execution contract

The runner uses upstream mini-swe-agent 2.4.6 `DefaultAgent` and its original `LitellmModel` or `LitellmResponseModel`. There is no custom ProxyModel, replacement agent loop, parser, history truncation or coding-client wrapper. Native provider history, including signed thinking and encrypted Responses reasoning, remains in the upstream trajectory. Controller credentials never enter the offline model-command sandbox.

The one model subclass is `GoStrictHistoryLitellmModel`, declared per route in `native_models.HISTORY_KEY_REMOVALS` (user-approved 2026-10-01) for Go Chat `glm-5.2` and `glm-5.3` only. The pinned OpenAI SDK adds `refusal: null` to every parsed Chat reply, LiteLLM wraps it as the assistant message's `provider_specific_fields`, and `LitellmModel` echoes that key on the next request; the strict upstream behind these GLM models rejects it with HTTP 400 (`runs/next-launch-prep-20261001/go-blockers-investigation.md`). The subclass drops that key from outgoing copies only when its value is exactly the SDK-synthesized `{"refusal": null}` (any other value raises), so the request carries the assistant message as Go returned it. Native history, content, tool calls and echoed `reasoning_content` are unchanged. The route's effective settings record `history_key_removal`, and readiness requires the trajectory's `model_type` to name the subclass. Every other route, including other Go Chat models, keeps the original `LitellmModel` and its wire bytes.

Future GPT/OpenAI configurations require Codex OAuth through the authorized loopback Responses bridge. Claude/Anthropic configurations require Anthropic OAuth through the authorized loopback Messages bridge. Use the existing approved CLIProxyAPI executable and exact model IDs, with no Vercel fallback or checkpoint substitution. For other model families, prefer OpenCode Go wherever the exact identity is supported and native-qualified; retain Vercel AI Gateway for remaining approved models pending funding. Cloudflare AI Gateway is excluded. Go is the paid `/zen/go/v1` endpoint, not OpenCode Zen. Gemini bridge and local Kimi pool routes are excluded. Devin has a native route for reset-campaign preparation but remains held until quota renewal and scheduled qualification. Actual Cursor Composer 2.5 is not available through an approved raw inference route; an xAI model with a Composer label is not a substitute.

`MODEL-TEST-PLAN.json` preserves historical inventory mappings. Both the campaign compiler and driver now default to `MODEL-TEST-PLAN.oauth-first.json`; neither file is executable campaign configuration. The prospective inventory keeps all 74 identities, blocks exact OAuth checkpoints absent from the authenticated catalog, and blocks Claude Opus 5.5's failed native qualification. The route audit is `runs/oauth-route-audit-20261001.json`. Default CLI compilation rejects the four old OpenAI Vercel selections before inference without requiring an explicit inventory flag. Native readiness proof is still required for catalog-present models. Only CLI defaults changed, so the native proof fingerprints remain valid; new campaign provenance records the changed compiler/driver hashes. Historical frozen execution requires retained original controller source. No historical campaign, proof or result is rewritten, and no cancelled campaign is resumed. `config/campaign.example.json` intentionally has pending readiness and cannot be run as a verified campaign.

The four formerly Vercel-routed OpenAI checkpoints were requested by exact ID through the original native three-turn offline-tool workflow. All four failed on their first local Responses request with `NotFoundError` and `provider_request_error`. The actual body is CLIProxyAPI's `unknown provider for model <ID>` / `model_not_found` registry rejection before upstream execution, not a Codex account entitlement rejection. No fallback or successful model response occurred. `runs/oauth-exact-qualification-20261001/summary.json` retains the results and removed-sandbox evidence; `exact-model-registration-investigation.json` in that directory explains supported configuration and static-bearer risks. The models remain blocked on the current bridge. Their upstream OAuth availability is unknown.

The precise blocker is missing approved-bridge OAuth registration for these exact IDs. Self-alias configuration does not register them; aliasing a different model would substitute a checkpoint. The investigated static OAuth-bearer API-key-kind path was declined. Do not duplicate tokens, change headers/auth lifecycle, restart the shared bridge or substitute models. Upstream account entitlement remains UNTESTED, and the existing 18 qualified OAuth routes are unchanged.

The replacement Go credential is installed privately on both trusted controllers. The existing native three-turn offline-tool qualification for `qwen3.8-flash` passed; `runs/full-launch-20260930/new-go-key-validation.json` links its proof and states the limited scope. This does not establish the remaining balance. The user subsequently authorized history-preserving continuation of runnable unfinished Go/OAuth work and requested a hosted preview of available results. The original cancelled campaigns remain historical evidence. Do not rerun already eligible model inference or reset the three-attempt budget. Vercel work remains held pending funding; no Cloudflare route is authorized. Minecraft must remain stopped, and Paris's old restoration watchdog remains disabled.

New campaigns use `keygen-native-campaign-3` (revision 2 cohorts remain readable for reports), `max_attempts: 3` and `attempt_selection: first_success_up_to_three_attempts`. Each model's attempts run sequentially and stop after the first eligible success. First attempts for different models can run concurrently within the frozen worker and provider limits. Every attempted outcome remains visible. Predetermined later slots become `SKIPPED_AFTER_SUCCESS`, link to the selected attempt and have null scores and usage. The retained numeric `repetition` field is an attempt ordinal, not an independent-repetition claim. This adaptive experiment does not support three-trial medians, ranges or musical-quality rankings. Previously compiled campaign artifacts remain unchanged.

`attempt_selection: independent_repetitions` restores the original design of three independent predetermined repetitions per model. `policies.repetitions` lists the ordinals the campaign runs; each runs regardless of earlier success or failure, and `QUOTA`/`AUTH`/`CONTENT_FILTER` still stop the sequence and leave later slots `RESERVED`. A campaign may declare only some ordinals when `policies.linked_condition` names another frozen campaign (ID, config SHA-256, its ordinals) and freezes each model's `report.condition_fingerprint`: the frozen model entry (route, generation, tier, readiness proof, effective settings, bridge), its inventory row, prompts, limits, native settings, images and Boat resource class. Campaign ID, roster, concurrency, key pools, storage, controller paths and engine provenance are operational and excluded. A linked first-success campaign contributes only ordinal 1, the only slot it ran unconditionally. Compile with `campaign.py --repetitions 2,3 --linked-campaign /absolute/first-campaign.json`; the compiler rejects any model whose condition differs. `report.py --linked ROOT COHORT` combines the linked repetitions into one condition per model with the median and range of eligible repetitions; the linked campaign's other slots (skipped, cancelled, reserved, retries) stay listed as attempts outside the condition.

The same declaration continues an unfinished first-success campaign: `campaign.py --attempt-selection first_success_up_to_three_attempts --repetitions 2,3 --linked-campaign /absolute/first-campaign.json` compiles a campaign that runs only the remaining ordinals after the linked campaign's consumed ones (for example after a `QUOTA` stop on ordinal 1), with the same per-model condition fingerprint check. It keeps first-success selection within its own ordinals, and its report declares only those ordinals. The linked campaign's reserved slots stay unchanged there; the continuation's attempts carry their original ordinal numbers.

`attempt_selection: independent_repetitions_infrastructure_reruns` (a rerun queue) finishes independent repetitions whose slots failed for a non-model reason or never started. `campaign.py --queue-plan PLAN.json --linked-campaign A.json [--linked-campaign B.json ...]` freezes, for every model and ordinal, its origin: a linked campaign's `<model>-rep-<n>` slot with its recorded status, status SHA-256 and outcome (`SUCCESS`, `FAILURE` plus category, or `UNATTEMPTED`), or none for an ordinal run here first. Linked models must share the condition fingerprint. Only ordinals with no origin, an unstarted origin or a non-model failure (`INFRA`, `AUTH`, `QUOTA`, `CONTENT_FILTER`, `TRANSPORT`, `PROTOCOL`, `EVAL`) run; scored outcomes and model failures are never rerun. `run.py queue` runs each such ordinal as a chain of separate attempts `<model>-rep-<n>[-retry-<k>]`. Each rerun records `status.retry_of` and a `retry-<id>.json` record naming the attempt it reruns and that attempt's campaign. A chain continues only while its last attempt is rerunnable by the report's own classification, up to `max_queue_attempts`. Before a provider's work starts, and again after any of its attempts ends in a non-model failure, one minimal probe request must succeed. A usage-limit reply (HTTP 429, quota, rate limit, `auth_unavailable`) re-probes after `--probe-interval` (default 1800 s) without starting an attempt; any other probe failure re-probes after `--retry-interval`. Before each start the Boat balance must still cover `--boat-reserve-seconds` (default 36000) after the frozen TTL of every running attempt and the new one; otherwise the queue starts nothing more and stops once running attempts finish. `queue-state.json` and `queue-events.jsonl` in the root record gates, probes (category and HTTP status only) and starts. The report verifies every origin's status hash and every rerun link. It reports each ordinal's last chain attempt as its sample and lists superseded attempts beside it.

Gates are per model for non-pooled routes, so one separately metered model hitting its usage limit (for example Fable) never closes the gate of another model on the same provider; pooled routes gate per key. `run.py queue --hold MODEL_ID` (repeatable) defers a model: its ordinals are never probed or started and stay pending (`held` in `queue-state.json`, final status `COMPLETED_WITH_HOLDS`), and a later `run.py queue` without the hold resumes them. A follow-up queue campaign can continue an earlier queue's chains: a plan entry's optional `reruns` lists the earlier queue's frozen rerun attempts after the origin (each with status, status SHA-256 and outcome, only after unstarted or non-model outcomes). New reruns continue at the next `retry-<k>`, and the report verifies every link and lists every superseded attempt.

The experiment is `declared_native_configurations_fixed_resources`, not a claim of universally maximum provider capability. Explicit generation parameters, exact API route, returned identity, backend provenance, request timeout, retry policy, native model class and effective settings are frozen. Unknown provider-side handling is recorded, not asserted as verified.

## Failures, retries and submissions

- **Account faults (QUOTA, AUTH).** Quota, funds, usage-limit and HTTP 429 failures are classified as `QUOTA` (status `QUOTA_ERROR`), an infrastructure category. This holds under any SDK error class: `Insufficient account funds`, `usage limit exceeded`/`GoUsageLimitError` and `positive credit balance` bodies all count. A `QUOTA` or `AUTH` attempt stops that model's sequence. Later slots stay `RESERVED`, and `<model>-attempts.json` records `stopped_after` and `reserved`. Fix the account, then `recover` and run an explicit `retry`.
- **Transport retries.** `native.retries` (0–2; the drafts use 2) sets LiteLLM's own transport-only `retry_policy` per HTTP request. Timeouts, HTTP 500 (connection resets map here) and 503 are re-sent. 4xx responses (429 included), 502 and unmapped errors never start a retry. LiteLLM decides from the first error only; once a retry has started, a later re-send counts toward the same bound whatever its error. mini's own query retry is always off, and a failed request produces no observation. `status.totals.transport_retries` counts re-sent requests.
- **Content-filter blocks (CONTENT_FILTER).** On `anthropic_oauth` routes, a reply Anthropic's output content filter blocks outright (HTTP 200 `finish_reason` `content_filter` with neither text nor tool call, or HTTP 400 `Output blocked by content filtering policy`) carries no content, so it never enters native history and the identical request is re-sent, at most 3 sends in total. Qualification pilots, probes and campaign attempts share this bound. Each block is a `content_filter_block` record in `transport.jsonl`, and `status.totals.content_filter_blocks` counts them. A third block fails the attempt as `CONTENT_FILTER` (status `CONTENT_FILTER_ERROR`; probe/pilot category `content_filter`), an infrastructure category that stops the sequence like `QUOTA`, leaving later slots `RESERVED`.
- **Submission collection.** `tune.xm` is collected on its own. Optional extras are then collected only if the whole `submission/` directory fits the limits (`artifact_bytes`, 4096 regular files, no links). Otherwise they are dropped and `status.submission_extras` records the reason. A missing, irregular or oversize `tune.xm` is still a model failure.
- **Truncated replies.** When a reply ends at the output cap with no valid tool call (`finish_reason` `length`), the format-error message says so.
- **Output caps.** When a model's documented output limit is not separate from its context window (at least 95% of it), `run_output_cap` is `min(documented, context // 2)`. The rule is in `tier-spec.json` `run_output_cap_rule`.
- **OAuth concurrency.** The drafts bound `codex_oauth` and `anthropic_oauth` to 4 concurrent attempts each. Go stays at 12 across four keys (3 per key), NIM at 3.
- **Cohort labels.** Reports and the site label each row with its cohort and tier. Max-tier rows read "highest declared tier: <level>, <cap> output" and schema-2 rows read "provider default effort, 32k output", each with its prompt version. Every cohort gets its own table and is never ranked together with another. The highest declared tier is the highest documented reasoning control on that exact route, not equal compute. Each published score is one quality sample, the first valid attempt.

## Declared tiers

Every model declares `tier: {level, reasoning, spec_sha256}` taken from a per-model tier spec (`runs/next-launch-prep-20261001/tier-spec.json`). `level` is an effort (`minimal`…`max`), `thinking-on` (boolean thinking switch), `thinking-budget` (budget-only thinking) or `none-available`; `reasoning` is exactly the generation's reasoning fields. There is no default tier. `campaign.py --tier-spec` refuses to compile a model whose spec entry is missing, `blocked-unknown` or for another protocol, whose tier or spec digest differs, or whose generation lacks the reasoning control the entry requires. The declared tier replaces the pinned LiteLLM capability map as the xhigh/max gate.

Validation is fail-closed against the pinned SDK: a route is rejected if LiteLLM would drop, alter or refuse the declared control (for example `output_config` xhigh/max on non-Claude names) or silently reroute Chat to Responses (GPT-5.4+ with tools and reasoning). Wire forms: Chat `reasoning_effort`; Responses `reasoning.effort`; Anthropic Messages top-level `thinking` and `output_config.effort` (Go Messages adds LiteLLM's `allowed_openai_params` opt-in for non-Claude thinking); NVIDIA NIM `extra_body.chat_template_kwargs` (or a documented top-level `reasoning_effort`). The audit records `extra_body` expanded as sent, and readiness fails unless the tier's reasoning control is present in every recorded request. Output caps are each model's documented maximum, clamped to the route catalog; budget-thinking models reserve 16,384 tokens for the answer.

`native_models.CAPABILITY_OVERRIDES` declares exact route capabilities missing from the SDK model map. The user-approved 2026-10-01 Go Messages declarations cover `qwen3.8-flash` and `qwen3.8-max` at documented `output_config.effort` `xhigh`. Catalog-backed Devin Chat declarations cover `devin/gpt-5-4`, `devin/gpt-5-4-mini` and `devin/gpt-5-3-codex` at `reasoning_effort` `xhigh`. `validate_model` registers only `supports_xhigh_reasoning_effort` and the native provider/mode for those exact aliases through LiteLLM's `register_model`, so the unmodified SDK gate accepts and transmits the declared effort. Transmission is not patched. Each tier-spec entry mirrors its declaration as `capability_override`, and `validate-tier-spec.py`/`build-drafts.py` reject any entry whose field differs from the code. The same aliases on another route or at another effort are rejected. Effective settings record the declaration as `sdk_capability_override`.

NVIDIA NIM (`https://integrate.api.nvidia.com/v1`, `NVIDIA_NIM_API_KEY`) is used only for exact models Go cannot serve at their tier, or as Go overflow. Its account limit (~40 RPM) is shared, so the provider bound is 3.

Devin uses `provider: devin`, `api: chat` and the pinned SDK's `openai/` model prefix through the approved CLIProxyAPI bridge at `http://127.0.0.1:8417/v1`. `DEVIN_BRIDGE_API_KEY` is resolved only by the trusted controller. Like OAuth credentials, it may target only explicit HTTP loopback URLs on `127.0.0.1` with a port and `/v1`; remote hosts, `localhost`, credential-bearing URLs, queries and fragments are rejected. New selections declare a `devin` concurrency bound, with 2 in the reset preparation helper and 1 in the generic example.

The Devin request alias and expected returned identity are separate frozen fields. The requested model must match the approved inventory's `proxy_request_model`, and `response_model` must match its `upstream_model`. Responses are checked against that exact expected identity; missing identities, errors and substitutions do not establish readiness. `reasoning_effort` and the output cap pass through the existing native SDK mapping and wire audit. The three GPT aliases use the catalog-backed xhigh declarations above and declare `max_completion_tokens`, because the SDK would rename `max_tokens`; other aliases use `max_tokens`. Models with no catalog thinking levels use `none-available` with no reasoning fields, not an invented effort. The reset campaign declares 64,000 output tokens and the highest catalog effort where one exists. A mocked-wire smoke proves request formatting and native tool history only, not upstream delivery or quota availability.

Devin qualification and compilation require the bridge's exact implementation, version and executable SHA-256 in `backend_provenance.bridge`, and qualification hashes the actual `--bridge-executable`. The inspected approved executable is CLIProxyAPI 7.3.16, commit `c404af96`, SHA-256 `9a7cb93be4b21953c9d90e66453d04581e02287e8324eae01f0ec7bbdc1cb720`. The quota resets at `2026-10-04T08:00:00Z`; no real Devin inference is allowed before the scheduled `2026-10-04T08:05:00Z` qualification. Catalog presence and offline validation are not readiness evidence.

## Go key pool

`concurrency.key_pools` maps a route's declared `api_key_env` to member key names and per-key caps, e.g. `{"OPENCODE_GO_API_KEY": {"OPENCODE_GO_API_KEY": 3, "OPENCODE_GO_API_KEY_1": 3, …}}`. Each attempt takes the least-loaded member under its cap (ties in declared order) before its sandbox starts, uses only that key for the whole model run and releases it when the worker exits; keys never switch mid-attempt, so native history and billing provenance stay with one credential. `status.json` records only `credential_env` (the key name). Caps must sum to at least the provider bound, so an admitted attempt never waits for a key; the drafts split the Go bound of 12 evenly over four keys (3 each). Locks are per controller, so run every Go route from one controller. Keys live only in the controller's private `ROOT/.private/controller.env.json` (mode 600).

## Readiness and campaign compilation

Readiness must come from a real multi-turn native protocol pilot with an executed tool result, not a catalog entry or one-turn completion. The saved nonsecret proof binds the route, native effective settings, backend implementation and upstream source hashes to its native trajectory and request/response audit. Compilation verifies its artifact digest and freezes the proof. Changing settings, route or native executable source requires another exact readiness gate. Historical proof hashes are never rewritten to match new code.

`native_models.build_probe_model` bootstraps qualification through the same upstream constructors, callbacks, parser and native history as production. It does not pretend that an unqualified model has verified readiness. Production `build_model` still requires verified readiness, and the compiler checks the actual recorded proof.

The reusable pilot CLI accepts a sanitized JSON object with `model`, `config` containing only `native`, an immutable Docker `image`, and optional `limits` containing `steps`, `wall_seconds` and `command_seconds`. The model declares the exact route, generation settings, credential environment variable name and `backend_provenance`. Set only that route's credential in the controller environment. For OAuth and Devin, pass the actual bridge executable with `--bridge-executable`; its file digest must match the declared backend provenance.

```sh
benchmark/.venv/bin/python -I benchmark/native_readiness.py \
  --spec /absolute/pilot-spec.json --out /absolute/new-proof-directory
```

The pilot uses a credential-free, network-disabled, read-only 128 MiB Docker workspace with a private tmpfs volume and a 32 MiB read-only export helper. Use an immutable minimal image with Bash, GNU tar and sleep, such as the approved Python slim image. This is a protocol test, not FT2 acceptance. Only the isolated upstream model worker receives the route's canonical API credential. Other controller environment variables and credential files are not inherited. Default pilot bounds are five turns, 180 wall seconds and 15 command seconds. The declared native request timeout stays unchanged; the controller kills a hung worker at the outer wall deadline.

A successful pilot writes a unique file on its first turn. It then reads the file back and tests it with two bash tool calls, preferably in one reply because real campaigns allow several tool calls per reply; one call per reply (as Codex does) is equally valid. It then submits, exports the exact file and confirms removal of all owned containers and the volume. `proof.json` contains the compiler-validated native trajectory and wire audit. `readiness.json` contains the selection-ready readiness object, including the actual proof-file SHA256 and immutable payload. Success requires exact returned identities, complete alternating native wire exchanges (a transport-retried request is not a clean proof; content-filter-blocked sends are set aside), at least three tool calls answered by their own successful executed results, the declared reasoning control in every transmitted request, and exact transmitted settings. Endpoint-delivery knowledge remains explicitly unknown. `pilot-spec.json`, `runtime-provenance.json`, `sandbox.json`, `sandbox-preflight.json`, `worker-result.json`, `trajectory.json`, `transport.jsonl`, `worker.log`, `submission/readiness.txt` and `cleanup.json` retain the nonsecret evidence that was reached. Early failures may lack files for stages they never reached. Any setup, API, protocol, task, provenance or cleanup failure writes a nonverified `proof.json`, `readiness.json` and `blocker.json`; it never switches models or routes. Private SDK history and logs are redacted before export and then removed.

`--probe long-generation` runs a separate probe with the same spec form and exactly `steps` 3, `wall_seconds` 3600, `command_seconds` 60. One reply asks for a long literal file. It writes only `probe.json`, never readiness evidence. The outcome is `pass` when a response has more than 32,768 output tokens or more than 600 s latency with the exact settings, and `fail` on a transport drop, retry, timeout or gateway error. Anything else is `inconclusive`. The qualification plan lists one probe per route family under `pilot-specs/long-generation/`. A failing family's caps drop to 64,000. Streaming is not an option: mini-swe-agent 2.4.6 calls the SDK without `stream`.

The bootstrap constructor change invalidates the five earlier native proofs for current execution. Those immutable artifacts remain historical evidence and require real requalification before a new campaign can use the changed native source.

Install the pinned Python requirements into `benchmark/.venv`. Build images with `benchmark/Dockerfile` once and use their immutable SHA256 IDs. Image builds run the native FT2 author/edit/save/reload/render acceptance checker. The Debian base digest and FT2 source revision are pinned; actual image, binary and package identities are recorded. Do not treat mutable image tags as campaign identities.

Run these commands from the repository root, with explicit absolute paths:

```sh
benchmark/.venv/bin/python -I benchmark/campaign.py \
  --inventory /absolute/MODEL-TEST-PLAN.oauth-first.json \
  --selection /absolute/verified-selection.json \
  --tier-spec /absolute/tier-spec.json \
  --out /absolute/campaign.json
benchmark/.venv/bin/python -I benchmark/run.py doctor \
  --campaign /absolute/campaign.json --out /absolute/local-spool
benchmark/.venv/bin/python -I benchmark/run.py run \
  --campaign /absolute/campaign.json --out /absolute/local-spool --workers 1
benchmark/.venv/bin/python -I benchmark/drive.py summary --out /absolute/local-spool
```

The worker count must equal the frozen campaign. Doctor checks route eligibility, installed provenance, immutable images and resource/storage readiness before inference. The local spool supports atomic publication and file locks; do not use a cloud FUSE mount as the live attempt directory. Global and provider-specific inference limits are independent of render and video limits. Use conservative concurrency on a constrained controller; model waiting time is not evidence that sandbox memory can be overcommitted.

`config/campaign.verified.json` freezes five live-qualified protocol representatives and fifteen original attempts: Go Qwen Chat, Go Grok Responses, Vercel Mercury Chat, Codex Responses and Anthropic Messages. Its exact readiness settings use 1,024 output tokens (Anthropic 512; Codex low reasoning), not maximum-effort configurations or the full inventory. It freezes one worker, 100 steps, 1,800 agent seconds and a fresh Boat VM loading the verified local image bundle. Doctor passed with 800,382,976 available RAM bytes against the 536,870,912-byte controller reserve. Supply approved credential environment variables before running it; the private YAML is not a campaign input.

Credentials are supplied by the controller through each model's declared environment variable. Native SDK canonical variables exist only in the isolated worker environment. Do not put key values, token files or private proxy YAML contents in campaign JSON, proofs or exported artifacts. SDK echoes and trajectories are sanitized before persistence. Bridge provenance identifies the executable implementation and digest; it does not prove which hidden upstream checkpoint an alias serves.

## Reservations and recovery

Campaign and attempt publication is atomic and locked. A reservation has enough model/cohort metadata to be summarized before a worker starts. Interrupted reservations and running attempts remain visible as infrastructure states with unknown usage, not zero-score musical failures. Recovery preserves the original outcome. An explicit retry has a separate identity and cannot replace a predetermined campaign slot or its selected first success. An existing campaign cannot silently acquire different prompts, limits, dependencies, settings or image IDs.

## Artifact storage

`benchmark/artifacts.py` supports dedicated local storage and verified rclone storage. The configured remote is `gdrive2:keygen-benchmark-artifacts`. Live work stays on the local spool. Admission accounts for a local reserve and each simultaneous attempt's declared peak, plus remote capacity.

Terminal attempts are scored before export. Bundles include allowlisted result metadata, trajectories, submitted modules, canonical audio, previews and immutable evaluation generations. Controller homes, private configurations and credential files are excluded. Content manifests and compressed-file hashes are checked against the remote object before local bulk eviction. Failed verification retains local data. Eviction cannot modify legacy work.

`archive.json` is retained separately from the hashed bundle. Evaluation can restore a verified bundle when bulk data is needed, create a new evaluation generation, re-export and evict again. Reporting reads retained metadata and never silently downloads, renders or rescores. Remote archival is not a substitute for checking available local staging space.

## Private data layout

Raw runs, inputs and generated sites live outside every checkout, in one private root on the operator laptop:

```text
~/keygen-data/                       private, not a git checkout
  runs/<model>/attempt-1..3/         the three attempts the leaderboard ranks (best of 3)
  runs/<model>/other/<date>-<id>/    everything else: failed, retried, quota, legacy, other services
  runs/index.json                    every attempt: slot, status, score, route, source
  _store/<host>/<path>/              verified mirror of every source run root (audit copy)
  inputs/                            prices, attempt usage, model metadata
  snapshots/<YYYY-MM-DD>-<name>/     collect_public.py --output
  publications/<YYYY-MM-DD>-<name>/  build.py --publish-root (what serve.py serves)
```

Campaigns run on a controller's local disk (file locks and atomic renames; never a cloud mount). `benchmark/runs/organize/organize.py` mirrors every run root from Ashburn, Paris and the laptop into `_store/`, verifies every file's SHA-256 against the source and never modifies the source; laptop sources are hard-linked. It then rebuilds `runs/` from `_store/` as hard links, so rerunning it after new attempts moves a newly ranked retry into its slot. Model folders use the plain model name; when several services served one model, the ranked route is the first with three attempts in the showcased condition (vendor, then Devin, Go, Vercel). Credentials, private logs and isolated homes are not copied. Bulk media evicted after archiving stays in `gdrive2:keygen-benchmark-artifacts` and is referenced by each attempt's `archive.json`. Community submissions are the only run data in git (`submissions/`).

## Boat execution

`benchmark/boat.py` provisions credential-free Boat VMs with explicit TTL, pinned SSH host keys and controller-only private keys. Commands use direct SSH with binary stdin/stdout and native exit status, not the API execution timeout. Only the five allowlisted build sources are uploaded during image preparation. Provider credentials are not uploaded or mounted.

Use a runtime-verified warm snapshot or a fresh VM loading a verified image bundle. Boat configuration declares `backend: boat`, explicit `ttl_seconds`, immutable `images.agent` and `images.visualizer`, and its exact allocation source. A VM stop is verified and recorded. TTL is a deadman for abrupt controller loss; killing SSH alone does not prove the remote command stopped.

The agent has a writable tmpfs-backed workspace. A separate export helper mounts the same live volume read-only. After the agent is frozen, export streams GNU tar through the helper. Docker cp cannot reliably collect tmpfs-mounted workspace data and is not used. Archive paths, expanded sizes, deadlines and binary bytes are checked. Containers and owned volumes are removed before the VM is stopped.

```sh
benchmark/.venv/bin/python -m benchmark.boat prepare \
  --config /absolute/prepare-transport.json --audit-dir /absolute/preparation \
  --verify --snapshot keygen-ft2-native-amd64
benchmark/.venv/bin/python -m benchmark.boat smoke \
  --config /absolute/warm-transport.json --audit-dir /absolute/transport-proof
```

Boat snapshots are not canonical result storage. Actual warm restoration reported missing provider image files even after a clean stopped snapshot. Do not treat a healthy/provisioned flag or snapshot completion as restored image readiness.

The alternative is a fresh VM with a verified Docker-save image bundle. Preparation can export both immutable images with `--image-bundle-out /absolute/native-images.tar`. Preserve the returned `controller_path`, SHA256, byte count and exact image-ID pair. Configure `transport.boat.mode: new`, no snapshot, and `transport.boat.image_bundle` with that metadata. The controller checks bytes and hash before allocation, streams the bundle through raw SSH Docker load, checks remote disk capacity and verifies both installed image IDs before inference. Rclone credentials stay on the controller; never upload them to the VM.

amd64 Boat images and arm64 local images are different experimental conditions. Native acceptance does not establish cross-architecture bit-identical replay.

## Evaluation and publication

A fresh trusted FT2 process renders the saved XM. This is independent of the agent process and its preview audio, not an independent replay engine. Video is presentation; canonical audio is the evaluation input. A video failure does not change the musical artifact's validity.

Craft-v7 is an auxiliary tonal-development heuristic, not a musical-quality ranking or task-compliance score. Its numeric formula is unchanged. The original task lets the model choose duration freely. The heuristic's duration factor saturates at 30 first-pass audible seconds; short duration is an auxiliary preference, not noncompliance. Silence and repeated later playback do not add duration credit. Human/listener validation is still required before aesthetic claims.

Infrastructure, provider transport and evaluator failures have null craft values and explicit categories. Genuine model-produced invalid artifacts are distinct model failures. Reports retain all predetermined slots and expose eligibility and failure denominators. Skipped slots are not attempts, failures or zero-score evaluations. Publication selects the earliest matching predetermined attempt with `render: ok`, status eligibility, a valid eligible cached profile and no protocol, infrastructure, evaluation or finalization error. A craft score of zero can still be an eligible success; there is no craft threshold. Later successes and extra retry artifacts remain visible but cannot replace the first success. Every model shows its attempted count and a success, exhausted, interrupted or pending state. Unknown or missing slots are never inferred to have succeeded.

Archive export is not part of an attempt's outcome. The runner first evaluates the attempt; only an evaluation failure records `FINALIZATION_ERROR`. A failed or interrupted cloud export after evaluation leaves `status.json` and `profile.json` unchanged, keeps all local files, and writes `archive-error.json`. The export is retried after the campaign's sequences finish and on every `recover`. rclone copy deadlines scale with bundle size: 600 seconds plus the time needed at a sustained 128 KiB/s. The old fixed 600-second bound timed out a roughly 95 MB Google Drive upload; other 85–142 MB bundles took 20–480 seconds. Older runners overwrote the status after an upload failure. Publication counts such an attempt as evaluated only when rebuilding the overwritten status reproduces the SHA-256 that its profile pinned; the original finalization record is kept as `post_evaluation_finalization_error`. An `operator-cancellation.json` beside an attempt reports that attempt as operator-cancelled `INFRA`, never as the `AUTH`/`QUOTA` category that the frozen runner needed in order to stop the sequence.

Report schema `keygen-cohort-report-2` binds exact configuration IDs, routes, resource settings and campaign fingerprints. Each row retains its evaluator fingerprint, even when another attempt used a different evaluator generation. In a first-success cohort the selected attempt exposes its own auxiliary craft-v7 diagnostic, not an aggregate median or range. Malformed skip links and attempts after a success are reported as policy errors rather than silently discarded. An independent-repetitions cohort selects nothing: each model group lists every repetition with its source campaign and reports `median_craft`, `min_craft`, `max_craft` and `craft_range` over its `eligible_repetitions`.

The scoring fingerprint includes actual NumPy and SciPy implementations, loaded numerical libraries, Python/CPU identity, reference inputs, renderer and ffmpeg identities. An unchanged valid profile is reused. A changed dependency or `--force` creates another immutable evaluation generation; historical previews, traces and profiles are retained. `profile.json` is only the latest alias.

```sh
benchmark/.venv/bin/python -m benchmark.score profile --out /absolute/local-spool --workers 1
benchmark/.venv/bin/python -m benchmark.score profile --out /absolute/local-spool --force
benchmark/.venv/bin/python -m benchmark.score aggregate --out /absolute/local-spool
```

`aggregate` uses cached profiles only. Scoring workers are separately bounded by RAM, disk and trace size. Provenance has a 120-second budget; a complete evaluation has a 3,600-second budget, and subprocesses respect the remaining deadline. There is one aggregate writer per output root. No scoring command reruns model inference.

Publication reads retained metadata only. It never restores archives, renders or rescores. Audio, video and download links appear only for files that exist locally; there are no replacement media assets.

```sh
benchmark/.venv/bin/python -m benchmark.report \
  --root /absolute/local-spool \
  --cohort /absolute/local-spool/campaign.lock.json \
  --out /absolute/publication/report.json \
  --html /absolute/publication/index.html
```


## Verification evidence

Targeted setup proofs are retained under `runs/setup-verification/`. A test passing against a local protocol peer does not establish live provider readiness. A successful image build does not establish working binary export. Require each actual runtime proof before enabling its route or transport. The setup review records implementation and runtime gates separately. No full campaign is authorized by the setup repair itself.

Final verification passed 184 benchmark tests (one opt-in local-Docker skip) and 22 repository tests. Boat 1.0.36 matches the current official production binary byte-for-byte. Fresh image-bundle loading, native FT2, binary paused export, command deadline and archived cleanup passed. Two bounded original-task smokes produced a Go transport timeout and a Mercury ten-step model failure, not successful music submissions. Evidence is retained without replacing original outcomes.

## Approved full-launch status

The user approved the 57 exact-qualified configurations from the 66 runnable candidates in `runs/setup-verification/full-launch-candidates.json`. The qualified scope is 18 OAuth, 16 OpenCode Go and 23 Vercel configurations. Nine candidates remain blocked and visible; they are not silently omitted or replaced. Entries held or excluded outside these 66 candidates are not authorized by this approval.

The original qualification scope merges the OAuth summary with `runs/full-launch-20260930/oauth-qualification-v2-summary.json`, the original Ashburn summary's 16 Go successes, and the original Paris summary with its v2 and v3 overrides. All summaries remain under `runs/full-launch-20260930/`; successful and blocked proof files remain at the paths each summary records. Controller locations are retained in `ashburn-deployment.json` and `paris-deployment.json` in that directory.

Fresh source-provenance qualification subsequently passed for all 33 configurations in `runs/full-launch-20260930/ashburn-qualification-v4-summary.json`. The current 57-model proof roster is `runs/full-launch-20260930/collected-proofs/index-current-provenance.json`, which records immutable proof hashes, collected paths and controller origins. Original proof files and summaries remain unchanged.

The blocked Go proofs are on the trusted Ashburn controller under `/home/ubuntu/keygen-full.OGHjBAkO/qualification/`. The blocked OAuth proof is local under `runs/full-launch-20260930/qualification-v2/`.

| Blocked configuration | Recorded native outcome | Retained proof path relative to the stated root |
| --- | --- | --- |
| `go-glm-5.2` | `BadRequestError`, `provider_request_error` | `go-glm-5.2/proof.json` |
| `go-glm-5.3` | `BadRequestError`, `provider_request_error` | `go-glm-5.3/proof.json` |
| `go-kimi-k2.6` | `APIError`, `native_model_error` | `go-kimi-k2.6/proof.json` |
| `go-minimax-m2.5` | `APIError`, `native_model_error` | `go-minimax-m2.5/proof.json` |
| `go-minimax-m2.7` | `BadRequestError`, `provider_request_error` | `go-minimax-m2.7/proof.json` |
| `go-omen-alpha` | `APIError`, `native_model_error` | `go-omen-alpha/proof.json` |
| `go-qwen3.6-plus` | `APIError`, `native_model_error` | `go-qwen3.6-plus/proof.json` |
| `go-qwen3.7-max` | `APIError`, `native_model_error` | `go-qwen3.7-max/proof.json` |
| `anthropic_oauth-claude-opus-5-5` | `RepeatedFormatError`, `artifact_export_error` | `anthropic_oauth-claude-opus-5-5/proof.json` |

The launch policy is up to three sequential attempts per model, stopping at the first eligible success. This permits at most 171 executed attempts across the 57 qualified configurations, not three independent repetitions. Every attempted outcome and later `SKIPPED_AFTER_SUCCESS` slot remains visible. The declared output cap is 32,768 tokens except Vercel Command A, whose exact-qualified cap is 8,192. These are declared native settings, not universally maximum provider capability.

Both controllers stopped after provider funding failures: Vercel required a positive gateway credit balance, and multiple Go models explicitly reported insufficient account funds. The main campaign has 29 end-to-end completed models: 17 on Ashburn and 12 on Paris. Ashburn also has one eligible result without a cloud archive, producing the earlier total of 30 eligible results rather than 30 fully completed models. There are 67 verified attempt archive roundtrips and all 53 owned Boat VMs are archived. Four unarchived attempt directories remain locally retained. Minecraft was restored during shutdown, then stopped at the user's request; the Paris watchdog was disabled to prevent automatic benchmark restoration. Do not start or restore Minecraft without a new explicit user request. No top-up, provider substitution or inference rerun was performed. All 57 main-campaign model statuses are in `runs/full-launch-20260930/model-status-list.json`; terminal evidence is `{ashburn,paris}-night-watch-terminal.json` in the same directory.

The initial actual musical pilot failed before inference on all three attempts when image loading exceeded the 120-second startup deadline. All three Boat VMs were confirmed archived. `runs/full-launch-20260930/live-pilot-failed-statuses.json` retains the original `FINALIZATION_ERROR` / `TimeoutExpired` outcomes with `model_failure: false`.

A separate ArtifactStore scanner error treated the nonsecret `KEYGEN_FT2_ANALYSIS` setting as a credential. The classification fix passed nine artifact tests. An actual failed-pilot cloud archive then passed SHA256 verification; `runs/full-launch-20260930/archive-scanner-runtime-smoke.json` records that proof and the unchanged original `FINALIZATION_ERROR` status. This is archive evidence, not musical success.

The immutable revision-4 manifests in `runs/full-launch-20260930/qualified-manifest-index-v4.json` freeze a 600-second startup deadline, 120-second stop deadline, 10,800-second Boat TTL and at least 121 seconds between allocations per controller. The Boat startup fix prevents an individual readiness wait from shortening the shared image-loading deadline. The integrated suite passed 205 tests on Ashburn, with one opt-in local-Docker skip (`runs/full-launch-20260930/integrated-tests-remote.log`).

The revision-4 Qwen3.8 Flash pilot succeeded on its first attempt; later slots were `SKIPPED_AFTER_SUCCESS`. `runs/full-launch-20260930/live-pilot-acceptance-v4.json` records the verified 985,003-byte XM, 116.497-second nonzero trusted PCM, eligible evaluation, 117.035-second H.264 video at 1280×960, normal Boat archival and SHA256-verified cloud restoration. Its auxiliary craft diagnostic is 56.6, not a listener quality judgment.

Both supervisors and original runners were observed alive in `RUNNING` state; `ashburn-main-observed-v4.json` and `paris-main-observed-v4.json` retain that evidence. Resource sampling runs every 15 seconds. Guards stop owned work for sustained available RAM below 1 GiB, disk below 2 GiB, excessive resolver memory/configuration, cancellation or the campaign deadline. Paris records its Minecraft restoration obligation and restores the service after its owned runner terminates. Restoration has not yet occurred for this running campaign.

Inspect either persistent controller with:

```sh
python3 benchmark/runs/full-launch-20260930/launch-supervisor.py status \
  --plan benchmark/runs/full-launch-20260930/ashburn-supervisor-plan-v4.json
python3 benchmark/runs/full-launch-20260930/launch-supervisor.py status \
  --plan benchmark/runs/full-launch-20260930/paris-supervisor-plan-v4.json
```

### Overnight monitoring

Each controller was equipped with the user service `keygen-full-20260930-night-watch.service` and lingering enabled. The independent watchdog checked progress every 60 seconds alongside the original 15-second resource guard. Both watchdogs exited successfully after terminal verification. Paris's watchdog is now disabled at the user's request to prevent automatic Minecraft restoration; Ashburn's unit remains enabled but inactive.

Controller-local evidence is under `ROOT/launch-control/night-watch/`: `snapshot.json` for current progress, `health.json` for the latest monitor heartbeat and `alerts.jsonl` for retained issues. Installation and two advancing live heartbeats were verified in `runs/full-launch-20260930/{ashburn,paris}-night-watch-installed.json`. Request/scoring boundary checks are recorded in `night-watch-boundary-smoke.json`.

The watchdog safely finalizes a lost supervisor using owned PID/start-time checks, requests a safe stop for repeated finalization failures across distinct models, and verifies or retries Paris Minecraft restoration only after the owned runner stops. It does not change prompts, native history, settings or the three-attempt policy, and does not rerun completed inference. Both monitoring agents finished after terminal cleanup verification. Alerts are retained here; no phone, email or other out-of-band notification channel is configured.

Remaining work requires restoring the Go/Vercel funding prerequisites and explicit history-preserving recovery. One unaffected OAuth Opus5 attempt was interrupted by authorized Ashburn-wide cancellation; its trajectory remains archived and the interruption is not a musical failure. The campaign-owned OAuth reverse tunnel is stopped. Final VPS checks confirmed healthy available memory and Minecraft active; Paris's growing resolver was restarted after workload shutdown, dropping RSS from 459,411,456 to 13,615,104 bytes, with provider DNS resolution verified (`final-host-health.json`).

The original deployed watchdog recorded an expected heartbeat gap during Ashburn's orderly `STOPPING` phase, when the supervisor pauses sampling while draining workers. No extra kill or recovery was applied. Future watchdog deployments restrict heartbeat-stall detection to `RUNNING`; transition boundaries passed the actual predicate smoke in `night-watch-shutdown-smoke.json`. Original deployed watcher files and alert history remain unchanged.


## Hosted current-results preview

The public HTTPS preview is [Keygen Bench](https://tailnet.example/?page=ranking). It publishes an immutable current-results snapshot, not a live campaign dashboard. The final published snapshot contains 38 playable rows: 30 original main first successes, six native continuation successes, one archive-only GPT-5.4 recovery and one separately labeled Qwen3.8 Flash musical pilot. Main availability is 37/57; the retained pilot stays outside that numerator. The continuation cutoff is 2026-10-01 11:08:25 UTC on Ashburn and 11:08:27 UTC on Paris. Later outcomes require an explicit refresh. Original routing remains in private evidence; the public projection preserves model/cohort/artifact provenance without exposing access routes.

The tracker serves original XM and canonical WAV downloads, derived listening MP3s, and sanitized evaluation summaries. Public browser verification exercised Results-to-Tracker navigation, real audio playback, midpoint seeking and Stop. All 38 XMs matched hashes and parsed through the actual website parser; all 152 download links returned correct byte ranges with HTTP 206. Anonymous public ingress returned the exact final snapshot hash. Controller credentials, source files and directory listings were inaccessible. Initial and recovery-view parent evidence is `runs/preview-hosting-20261001/parent-browser-smoke.json`; final snapshot, system-scoped service and browser evidence is `../web/prototype/publication-20261001.json`. Minecraft must remain stopped.

## Authorized history-preserving continuation

The user authorized continuation on 2026-10-01 with OpenCode Go preferred wherever the exact non-OAuth model is supported and qualified. `runs/continuation-20261001/` retains frozen selections, manifests, original-history ledgers, qualification outcomes and recovery records. `continuation-20261001-ashburn-native-v1` launches twelve unfinished Go identities and Anthropic OAuth Claude Opus 5 using 24 remaining original attempt ordinals. `continuation-20261001-paris-muse-go-v1` launches the two exact Muse Spark Contributor identities through newly qualified native Go Responses, using only their original third ordinals. No completed model inference or compatible Qwen3.8 Flash musical pilot is rerun.

The orchestration calls the immutable original native runner. Model histories, original creative prompts, image/runtime provenance and generation settings remain frozen. The supervisors enforce resource and deadline guards; independent terminal guards identify owned processes by PID/start ticks, clean owned detached workers and Boat machines, and make bounded archive-only recovery attempts. The owned OAuth reverse tunnel closes after terminal cleanup. All continuation plans forbid Minecraft restoration.

The four previously missing historical archives were recovered in separate staging with verified roundtrips and zero model requests. Original statuses, profiles and selected outcomes remain unchanged, including GPT-6 Astra's original second-attempt selection. GPT-5.4 recovery reconstructs only its profile-pinned prearchive status and remains labeled historical Vercel inference, not a new OAuth run.

Go-blocked exact models with retained Vercel catalog candidates remain held for funding and exact native qualification; see `runs/continuation-20261001/pending-vercel-candidates.json`. No Vercel funding probes, Cloudflare requests, model substitution or automatic provider fallback ran.

