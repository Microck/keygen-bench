# Benchmark setup review

Reviewed: 2026-09-30T10:55:12.881010+00:00

## Repair implementation

The findings below describe the pre-repair state at the review timestamp. Active repairs are in `benchmark/native_models.py`, `campaign.py`, `run.py`, `artifacts.py`, the scoring modules and `report.py`. The old custom model adapter is removed. The original prompt files match their archived SHA256 hashes.

Real setup verification has exercised native multi-turn model calls and the cloud artifact upload, hash verification, eviction and byte-identical restoration path. Proofs are retained under `benchmark/runs/setup-verification/`. The cloud test is a storage fixture, not musical evidence.

Boat verification exposed Docker cp omitting tmpfs workspace files; export now streams through a read-only helper sharing the live volume. Specific warm restores failed with missing provider image files. The installed CLI is the latest official production 1.0.36, byte-identical to a fresh download. Fresh allocation with a verified Docker-save bundle passed exact image loading, native FT2, binary paused export, command deadline and archived cleanup.

The repaired harness passed 184 benchmark tests (one opt-in local-Docker skip) and 22 repository tests. Five live native multi-turn protocols are qualified. `benchmark/config/campaign.verified.json` freezes those exact five representative configurations and three original repetitions each; its launch doctor passed storage, memory, provenance and routing gates. This is not the full inventory or maximum-effort qualification. The two bounded original-task smokes ended in a Go transport timeout and a Mercury ten-step model failure; neither is a successful musical result.

## Approved full-launch status

The user approved launch of the 57 exact-qualified configurations from the 66 runnable candidates in `benchmark/runs/setup-verification/full-launch-candidates.json`, subject to a successful end-to-end musical pilot first. The qualified scope is 18 OAuth, 16 OpenCode Go and 23 Vercel configurations. Nine candidates remain blocked and explicitly retained. Held or excluded inventory entries outside these 66 candidates are not part of this approval.

Original qualification evidence is retained under `benchmark/runs/full-launch-20260930/`. The approved scope merges `oauth-qualification-summary.json` with `oauth-qualification-v2-summary.json`, retains the 16 original successes in `ashburn-qualification-summary.json`, and merges `paris-qualification-summary.json` with `paris-qualification-v2-summary.json` and `paris-qualification-v3-summary.json`. Each summary records its proof paths. `ashburn-deployment.json` and `paris-deployment.json` identify the trusted controllers and remote roots.

Fresh source-provenance qualification subsequently passed for all 33 configurations in `benchmark/runs/full-launch-20260930/ashburn-qualification-v4-summary.json`. `benchmark/runs/full-launch-20260930/collected-proofs/index-current-provenance.json` records the current proofs for all 57 qualified configurations, including immutable hashes, collected paths and controller origins. Original summaries and proof files remain unchanged.

The eight blocked Go proof files remain on the Ashburn controller under `/home/ubuntu/keygen-full.OGHjBAkO/qualification/`. The blocked OAuth proof remains local under `benchmark/runs/full-launch-20260930/qualification-v2/`.

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

Each qualified model gets up to three sequential attempts, stopping at its first eligible success. All attempted outcomes remain visible; unneeded later slots become `SKIPPED_AFTER_SUCCESS`. The 57-model scope permits at most 171 executed attempts, not three independent trials per model. The declared output cap is 32,768 tokens except Vercel Command A at its exact-qualified 8,192-token cap. No universal-maximum-capability claim follows from these settings.

Both controllers stopped gracefully after confirmed provider funding failures: Vercel required a positive gateway credit balance, and multiple Go models explicitly reported insufficient account funds. Terminal verification retained 30 eligible evaluated results, 67 archive roundtrips and all 53 owned Boat VMs archived; Minecraft is active/running. Four unarchived attempt directories remain safely retained locally. No top-up, substitution or inference rerun was performed. One unaffected OAuth Opus5 attempt was interrupted by authorized controller-wide cancellation; its trajectory is preserved, not scored as a music failure. Evidence is `benchmark/runs/full-launch-20260930/{ashburn,paris}-night-watch-terminal.json`. Original review findings, timestamp and historical results remain unchanged.

The initial actual musical pilot failed before inference on all three attempts when image loading exceeded the 120-second startup deadline. All three Boat VMs were confirmed archived. `benchmark/runs/full-launch-20260930/live-pilot-failed-statuses.json` retains the original `FINALIZATION_ERROR` / `TimeoutExpired` outcomes with `model_failure: false`.

A separate ArtifactStore scanner defect matched the nonsecret `KEYGEN_FT2_ANALYSIS` setting as a credential. The classification fix passed nine artifact tests. The actual failed-pilot cloud archive then passed SHA256 verification, recorded in `benchmark/runs/full-launch-20260930/archive-scanner-runtime-smoke.json`; the original failed status remains unchanged. This proves archive behavior, not musical success.

Immutable revision-4 manifests in `benchmark/runs/full-launch-20260930/qualified-manifest-index-v4.json` freeze startup at 600 seconds, stop at 120 seconds, Boat TTL at 10,800 seconds and allocations at least 121 seconds apart per controller. The Boat startup fix prevents a readiness wait from shortening the shared image-loading deadline. The integrated suite passed 205 tests on Ashburn, with one opt-in local-Docker skip (`benchmark/runs/full-launch-20260930/integrated-tests-remote.log`).

Both controllers were actively monitored through terminal shutdown by independent systemd watchdogs and dedicated agents. Both original runners/supervisors exited, the watchdogs finished successfully, Minecraft restoration was verified, and the campaign-owned OAuth tunnel was stopped. Paris resolver growth was reclaimed after workload shutdown; actual provider DNS resolution and host health are recorded in `benchmark/runs/full-launch-20260930/final-host-health.json`. Remaining work requires restoring Go/Vercel funding prerequisites and explicit history-preserving recovery.


## Original review verdict

At the original review timestamp, the harness migration and operational/fairness gates were incomplete. The findings below are retained as baseline evidence, not descriptions of current code. The implementation repairs and the five-model qualified campaign are complete; the full inventory still requires exact configuration qualification before launch.

No zero-rerun guarantee is possible with evolving providers and stochastic models. Avoid invalid cohorts by freezing the complete experiment and proving its critical paths before inference.

## What is sound

- Prompts are short, music-only and open-ended; they state real tools, offline limitations, persistence, exact submission path and finish command. Direct XM construction is explicitly allowed while a baked long-sample shortcut is disallowed.
- Agent containers are isolated, non-root, network-none and resource-limited; submission is frozen before bounded, read-only export and checked extraction.
- Final XM is rendered in a fresh trusted FT2 process rather than trusting an agent preview.
- Image IDs, prompt/config contents and package versions enter campaign provenance. Originals and every repeat are preserved.
- Scoring does not use provider/model identity or tool-use bonuses and exposes component measurements. It remains a provisional heuristic.

## Findings

### 1. Native model integration [launch blocker]

Current execution still instantiates ProxyModel and always sends Chat Completions; the approved upstream-native model migration is not implemented.

Evidence: `benchmark/run.py:389-395`, `benchmark/proxy.py:103-111`.

Recommended action: Finish native constructors/call paths and verify complete tool-result/history round trips for each protocol before a new cohort.

### 2. Executable campaign and routing [launch blocker]

The approved inventory is metadata, not an executable frozen campaign. Runner validation does not enforce excluded/held provider policy.

Evidence: `benchmark/run.py:83-115,553-560`, `MODEL-TEST-PLAN.json`.

Recommended action: Generate an explicit executable cohort from approved routes; reject excluded and deferred entries before inference. Freeze exact prompts, backend/settings, images, limits, repeats and failure policy.

### 3. Storage [launch blocker]

Only a few GiB remain on the host; archived historical runs alone occupy 6357125162 bytes. A full cohort with PCM, previews and analysis intermediates risks exhausting storage.

Evidence: `Local df and disk_usage observations`, `legacy/PRESERVATION.json`.

Recommended action: Provision dedicated artifact storage, estimate peak usage and enforce a reserve. Do not prune legacy results or unrelated Docker images.

### 4. Failure classification [high]

HTTP-200 gateway error objects are mislabeled as possible identity fallback; missing artifacts from infrastructure/evaluation failures receive numeric zero craft and enter sorted profile output.

Evidence: `benchmark/proxy.py:125-138`, `benchmark/score.py:474-476,507-509`, `benchmark/README.md:197-203`.

Recommended action: Keep identity checks strict; separate transport/auth/protocol/evaluator failures from valid musical artifacts. Use explicit eligibility and failure denominators rather than musical zeros for infrastructure failure.

### 5. Interrupted attempts [high]

A RESERVED directory can remain permanently skipped, and the summary CLI raises KeyError:model on that valid interrupted state.

Evidence: `benchmark/run.py:432-435,577-579`, `benchmark/drive.py:95`.

Recommended action: Record identity on reservation, finalize interrupted outcomes and make summary robust. Preserve original attempts; recovery must be an explicitly separate attempt, not overwrite or silent retry.

### 6. Prompt versus metric [high]

Task lets models choose length freely, while craft applies a 30-second duration preference and favors tonal/static supported development. This measures a disclosed heuristic, not musical quality or task compliance.

Evidence: `benchmark/prompts/task.txt:2`, `benchmark/README.md:344-348`, `benchmark/score.py:352-403`.

Recommended action: Keep the short original-composition prompt and publish craft components as auxiliary indicators. Do not claim a music-quality leaderboard without independent listener validation. A craft-optimization task would be a distinct, explicitly disclosed prompt/cohort.

### 7. Budgets and repetitions [high]

Historical effort labels and mixed budgets do not define effective native settings, controlled prospective repeats or statistically comparable model measurements.

Evidence: `benchmark/drive.py:29-42`, `MODEL-TEST-PLAN.json`, `legacy/previous-work-20260930/benchmark/runs/low-score-audit.md`.

Recommended action: Predeclare capacity-versus-fixed-resource objective, per-model effective effort/output settings, limits and repeat count. For a ranking use fixed independent repeats and report distributions; otherwise label single-attempt examples.

### 8. Scoring provenance and reuse [medium]

SciPy is pinned in requirements but absent from scoring profile inputs. Existing profile_current checks are not used to skip unchanged expensive capture/analysis.

Evidence: `benchmark/score.py:419-423,426-445,507-508`, `benchmark/score_audio.py:13-14`, `benchmark/requirements.txt:5`.

Recommended action: Include actual SciPy and other numerical/playback dependencies in provenance; reuse verified current profiles, with explicit force-recompute mode. Scorer changes need local artifact rescore, not model rerun.

### 9. Concurrency and remote execution [medium]

Workers are supported, but no provider-aware limiter exists; tier driver remains sequential, external lock publication can race, and Boat execution is not integrated or benchmark-tested.

Evidence: `benchmark/run.py:530-537,571-587`, `benchmark/drive.py:84-85`, `BOAT-FEASIBILITY.json`.

Recommended action: Publish locks atomically and bound per-provider/run/render concurrency. Keep auth on controller; prove remote offline container lifecycle, freeze/export and cleanup before using Boat for a full campaign.

## Safe runtime checks performed

1. Offline native FT2 acceptance passed in the existing agent image: create sample/pattern, edit/readback, save/reload XM and render a 1.92-second stereo 44.1-kHz WAV. No clipping. This did not prove independent replay, listening quality or source-pin identity.
2. The actual current runner rejected `MODEL-TEST-PLAN.json` at its campaign schema check before inference. This confirms the inventory is not an executable campaign, not a parser defect.
3. The actual summary CLI failed with `KeyError: model` on a temporary RESERVED-state directory. Temporary files were removed; no historical attempt was touched.
4. Docker/images are present. Disk checks showed only a few GiB available on a 290-GiB volume near capacity. Native model history and actual Boat FT2 images were not exercised.

## Freeze and acceptance gate

Before a full campaign:

- Freeze a hashed model × approved route × native backend × effective settings × resource limits × repetition-index roster, exact substituted prompts, immutable image/binary/package identities and architecture.
- Specify artifact eligibility, submission/timeout behavior, independent-attempt selection and transport-versus-model failure policy.
- Prove two or more real model/tool/history turns for each intended protocol, with sanitized requested/effective configuration and returned model identity evidence. A one-turn tool-call probe is insufficient.
- Exercise submission collection, declared completion with missing file, interruption/export, summary recovery and concurrent startup on safe local scenarios.
- Run a small end-to-end pilot producing an XM, trusted PCM, trajectory/status/audits and profile. Measure storage, request/rate behavior, deadlines and costs before increasing concurrency.
- Verify same-environment replay repeatability and reference/preview checks. If using Boat, prove compatible images, offline execution, bounded binary export and stop-on-all-paths.
- Freeze or separately version scoring. Validate numerical provenance/cache invalidation, failure eligibility, and unchanged-profile reuse before publishing a cohort.

## Changes that do not need model reruns

Scorer changes, failure-classification/reporting fixes and new analysis components generally require only existing XM/WAV/status/trajectory artifacts, sometimes fresh local reference playback. Preserve prior profile versions instead of overwriting history.

Changing the prompt, model transport/history, provider/checkpoint, effective effort/output budget or task limits creates a new experimental condition for affected cases. Keep that cohort separate. Do not replace original scores with the best repeat.

## Decisions needed before freezing

- Original open-ended composition with heuristic diagnostics, or a disclosed craft-optimization task. Recommendation: retain the original prompt; do not turn hidden scoring preferences into retroactive compliance rules.
- Fixed-resource comparison or model-supported maximum-capacity comparison. Do not describe those as equivalent.
- Predetermined repeated trials for comparative rankings, or single-attempt demonstrations. Do not choose repeats after seeing scores.

Full structured findings and repair evidence: `SETUP-REVIEW.json`. No full inference campaign was launched during the repairs.
