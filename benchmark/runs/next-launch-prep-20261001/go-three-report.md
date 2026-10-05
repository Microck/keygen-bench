# Go three attempts (go-three-20261002): status report, 2026-10-02 ~14:15 UTC

**State: running on Paris, new starts PAUSED (operator), and two of the four Go keys are exhausted on the weekly limit.** The two in-flight attempts are still running. The goal is not finished: one of the 15 missing attempt-1 results has a score (minimax-m2.7). No site update was published, because attempt 1 is not complete for every Go model.

## What runs

There is one supervisor, one terminal guard and two rerun-queue runners (policy `independent_repetitions_infrastructure_reruns`). They run on oracle-paris, root `/home/ubuntu/keygen-full.eALj54bh/go-three-20261002`. The launch record is `go-three-launch-record.json`.

| Runner | Campaign | Config sha256 | Models | Queued repetitions |
|---|---|---|---|---|
| main | `next-max-tier-prompt-v2-go-three-20261002` | `9030c599…` | 17 main-campaign Go routes, condition linked to `next-max-tier-prompt-v2-ashburn-20261001` (`fd287193…`) | 46: 12 rep-1 retries of the main QUOTA slots + 34 new reps 2-3 |
| addon | `next-max-tier-prompt-v2-paris-addon-20261001` | `11224605…` | glm-5.2, glm-5.3 (GLM history fix), minimax-m2.7 | 9 |

- **Rep 1 of the 5 completed models** (deepseek-v4.1-flash, grok-4.6, hy3, qwen3.7-plus, space-bunny-free) is the main campaign's own slot, kept unchanged.
- **The 12 quota-stopped models** each rerun rep 1 as `<model>-rep-1-retry-1`. Each rerun has `retry_of` set to the main QUOTA slot and a `retry-<id>.json` record. The original QUOTA outcomes are not rewritten.
- **Engines.** `repo-main` is commit 98301c67 plus the probe-header hunk (run.py `fe0f9718…`), with native_models pinned to d3ae5963 so the frozen proofs still verify. `repo-addon` uses the same run.py with the current native_models (`147efb63…`).

## Qualification of the Paris add-ons (12:00-12:02 UTC)

| Route | Pilot | Result |
|---|---|---|
| glm-5.3-chat | addon-pilots-2 (key _2) | verified, proof `c8c27e62…` |
| minimax-m2.7-messages | addon-pilots-2 (key _3) | verified, proof `ff95eb9e…` |
| glm-5.2-chat | addon-pilots-2 (key _1) | blocked. The model wrote the marker without its newline, so the native proof was rejected. 3 turns, all identity_match. |
| glm-5.2-chat | addon-pilots-3 (key _1) | verified, proof `aa26ff15…` |

## Engine work, all in benchmark/run.py

- **Controller-wide key leases (`KeyLease`, `try_key_lease`).** One attempt per key holds across both queues.
- **Controller-wide Boat pacing.** Starts from both queues on Paris are spaced together.
- **`KeyGates`.** Per-key probe gates live in one controller file. A key is probed once, on its own credential, before it is used. A QUOTA closes only that key.
- **Cross-queue demand records.** No rep-2 starts on a provider while another live queue still waits on a rep-1. The Boat reserve check counts the running attempts of every queue.
- **Committed fix (98301c67).** The engine probe now sends a User-Agent and, for Go, `x-opencode-session`. Without them Go returned HTTP 403.
- **Uncommitted, tests pending (see below).**
  - Leases the queue holds are now released by `RerunQueue.reap`, after the outcome is classified. Before, they were released when the worker exited.
  - A weekly usage limit (`"limitName":"weekly"` in the error or probe body) backs the key off to a re-probe every 6 h.

## Events

- **12:38.** The supervisor's guard stopped the launch: systemd-resolved RSS was 632 MB, over the 512 MiB limit. I restarted it and started the earlier resolver watchdog (`go-three/resolver-watchdog.py`). No attempt had been made.
- **12:40.** The 4 engine probes got HTTP 403, so I cancelled. I fixed the headers and recompiled. The aborted roots are in `results-aborted-probe-403-20261002/`.
- **12:42.** Launch. 12:45-12:47: one probe per key, each HTTP 200. Four rep-1 attempts started.
- **13:05.** go-minimax-m2.7-messages-rep-1 reached **RENDERED_UNSCORED** in 10.4 min.
- **13:22-13:23.** go-glm-5.3-chat-rep-1 (key _1, 33.7 min) and go-glm-5.2-chat-rep-1 (base key, 36.8 min) ended with **QUOTA_ERROR**: `GoUsageLimitError`, `limitName "weekly"`. They are recorded as infrastructure failures and will be rerun.
- **Bug.** Each key had been released when its worker exited, before the queue had classified the QUOTA. So go-grok-4.7-rep-1-retry-1 (_1) and go-glm-5.3-chat-rep-1-retry-1 (base) started on the just-exhausted keys and hit QUOTA on their first request. Both are recorded as infra.
- **13:53 and 13:55.** Re-probes of base and _1 returned 429 quota. Both keys are waiting.
- **~14:05.** New starts paused with an operator demand record, `queue-demand-operator-pause.json`. It is held by a `sleep` process, PID 1270425, and declares a waiting rep 0, so both queues defer. In-flight attempts continue: go-deepseek-v4-pro-rep-1-retry-1 on _2 and go-glm-5.3-flash-rep-1-retry-1 on _3, each over 60 min at 14:05.

## When the weekly window resets

- The Go docs (https://opencode.ai/docs/go) say only: "5-hour — 20% of the monthly limit; weekly — 50%; monthly — 100%." They give no reset time. Each model's monthly dollar limit weights how its usage counts toward the plan allowance.
- The error metadata carries only `limitName: "weekly"` and a workspace ID.
- [INFERENCE] The weekly window is a fixed calendar week, not a rolling one:
  - A third-party usage tool (https://github.com/sixiang-world/opencode-go-usage) shows `weekly.resets_at` at a Monday 00:00 (+08:00).
  - opencode issue #24473 reports "Resets in 1 day 14 hours".
- That puts the next reset for base and _1 around Monday 2026-10-05 00:00 (+08:00), which is Sun 2026-10-04 16:00 UTC. It could be Monday 00:00 UTC instead; this is unverified.
- The free model space-bunny-free should still be usable on exhausted keys, per the docs. The per-key gate blocks it anyway.

## Boat

- 207,244 s (57.6 h) at launch; the queues stop starting if a start would leave less than 36,000 s.
- Each attempt's VM runs only until it ends; every attempt has its own fresh VM.

## Handoff (what remains)

1. **Run the full test suite once** with the lease fix. The 20 ModelSequenceTests pass. Then commit `benchmark/run.py` and `benchmark/tests/test_benchmark.py`.
2. **When both in-flight attempts are terminal** (`launch-status.py` shows no RUNNING attempts):
   - `touch control/cancel.request` and let the supervisor and terminal guard complete.
   - Archive the control files into `control/launch-attempt-3-…`.
   - Copy the committed run.py into `repo-main` and `repo-addon`.
   - Recompile both campaigns: run.py provenance changes, and the roots need a new lock. Either move the roots aside as in attempt 2, or keep them and use `campaign.py` `reruns` links (a4f44a7f) so attempt numbering continues.
   - Run `make-launch-plan.py` and relaunch the supervisor and guard.
   - Then kill pause PID 1270425 and delete `queue-demand-operator-pause.json`.
3. **Priority, per Main.** Rep 1 for all 15 missing models runs on _2/_3 first. The cross-queue demand rule already blocks rep-2/3 until every rep-1 is done. If _2/_3 also hit the weekly limit, the 6-hour back-off parks all Go work until the reset.
4. **Publish v8** (v6 conventions, new immutable root) when attempt 1 is complete for all Go models, and again at the end. Use QueueOAuth's v7 queue-scope pipeline in `web/prototype` and pass the go-three roots as `--scope repetitions` snapshots, linked to the main campaign.
