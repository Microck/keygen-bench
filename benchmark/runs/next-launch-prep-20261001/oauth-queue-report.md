# OAuth rerun queue report (interim, 2026-10-02 12:47 UTC)

Status: **RUNNING**. No new attempt has finished yet. This report records what has launched, what is pending and how to finish. The v7 site snapshot has not been published: it needs the queue's results.

## Goal

Every Claude and GPT max-tier model ends with exactly 3 scored attempts under the frozen main condition (prompt v2, max tier, same limits). Infrastructure failures don't count and are rerun as separate linked attempts. Scored outcomes and model failures are never rerun, and no existing outcome is rewritten.

## Requalification (Ashburn, 11:53 UTC, owned tunnel)

Readiness engine: `next-launch-20261001/repo` (d3ae5963 content: one tool call per reply accepted, 3-send content-filter bound). Max tier: 128k output, adaptive thinking, effort max. Specs, plan, summary and proofs are in `oauth-queue/requalify/`.

| Model | Result |
|---|---|
| claude-opus-5-5 | **verified**: 3 identity-matched turns, 0 content-filter blocks, proof `943fcd8c…` |
| claude-opus-5 | **blocked**: content filter on all 3 sends of turn 1 (0 output tokens). Stays excluded. |

### Why claude-opus-5-5 was excluded before

Its only earlier readiness pilots ran at provider default (32,768 tokens, no reasoning control): 2026-09-30 `full-launch-20260930/qualification-v2` and 2026-10-01 `continuation-20261001`. Both ended `RepeatedFormatError`. The provider content filter returned empty `finish_reason: content_filter` replies: 3 of 3 turns in the first pilot, 4 of 5 in the second. That was a provider block, not a model formatting fault, and both pilots predate the 3-send content-filter bound. The inventory row stayed `blocked-native-qualification`, so the max-tier qualification plan never selected it (`selected_in_draft: false`) and no launch roster included it. The row is now `pending-exact-native-proof`, with a note recording the requalification.

## Engine

- **9e3d185d**: new campaign policy `independent_repetitions_infrastructure_reruns`.
  - The plan freezes each model's ordinal origins: the linked slot, its status sha256 and its outcome.
  - `run.py queue` runs rerun chains `<model>-rep-<n>-retry-<k>`, each with `status.retry_of` and a `retry-<id>.json` record.
  - Before each provider's work, and after every non-model failure, one probe (16 tokens) must succeed. A usage-limit reply re-probes every 30 min without spending an attempt.
  - Boat reserve: each start must still leave 10 h after the worst case of all running attempts.
  - The report verifies each origin hash and each rerun link.
- **a4f44a7f** (for follow-up queues, not deployed in the running queue): per-model gates on non-pooled routes, so a Fable quota error never blocks other Claude models; the `--hold MODEL_ID` deferral; and plan-entry `reruns`, so a follow-up queue continues the first queue's chains. Full suite: 273 OK.

## Running queue: `next-max-tier-prompt-v2-oauth-queue-20261002`

- Ashburn, launched 12:28 UTC. Config `8d10c170…`, manifest file `bcac6c4b…`, launch record `oauth-queue-launch-record.json`.
- PIDs: supervisor 171854, runner 171856, terminal guard 171871; local tunnel owner 1045149.
- Concurrency: codex 4, anthropic 2.
- First probes returned 200 for both providers. Claude was serving at launch, even though it had been reported exhausted.

19 queued ordinals:

| Model | Queued (origin outcome) |
|---|---|
| opus-4-6, opus-4-7, opus-4-8, sonnet-4-6, sonnet-5 | rep 2 (QUOTA), rep 3 (unstarted) |
| sonnet-5-5 | rep 2, rep 3 (TRANSPORT `auth_unavailable`) |
| gpt-6-sol | rep 2 (PROTOCOL), rep 3 (TRANSPORT) |
| fable-5, fable-5-1 | rep 3 (QUOTA): **deferred by the user** |
| opus-5-5 | reps 1-3 (new) |

Rep 1 of every linked model, and rep 2 of both Fable models, are kept as scored.

In flight at 12:47 UTC: opus-5-5 rep-1, opus-4-6 rep-2-retry-1, gpt-6-sol rep-2-retry-1, gpt-6-sol rep-3-retry-1.

### Fable deferral without interrupting runs

The running engine orders starts by (repetition, model). After the 6 remaining Claude rep-2 starts, the next two Claude starts would be Fable rep 3. Their quota error would then block the Claude rep-3 starts behind them, because the probe uses the head-of-line model. `oauth-queue/fable-stop.py` (Ashburn, PID 174394, state `control/fable-stop-state.json`) handles this:

1. Once every non-Fable Claude rep-2 has started, it holds the anthropic slot locks as they free. `run_one` takes that lock before any Boat VM or model request, so an admitted Fable attempt waits as RESERVED: no VM, no request.
2. When nothing else is in flight, it writes `cancel.request`.
3. After the supervisor reports STOPPING, it releases the locks. Any blocked Fable attempt then records INTERRUPTED/infra with zero requests.

## Remaining steps

1. **Follow-up queue.** After queue 1 stops (supervisor and terminal guard COMPLETED), run `oauth-queue/build-followup.py QUEUE1_ROOT QUEUE1_CONTROL OUT_CONTROL` on Ashburn with a repo deployed from a4f44a7f (`native_models.py` pinned to d3ae5963). Then compile `next-max-tier-prompt-v2-oauth-queue-2-20261002`: `--queue-plan oauth-queue-2-plan.json`, plus `--linked-campaign` for main, repeats and queue 1, as each is referenced. Launch with `--hold anthropic_oauth-claude-fable-5 --hold anthropic_oauth-claude-fable-5-1` (add it to the launch-driver command) and a new tunnel owner. Relaunch later without `--hold` once Fable has quota.
2. **v7 site.** Subagent `QueueOAuth.SiteV7Pipeline` is building the v7 pipeline: the queue group supersedes the repeats group, opus-5-5 is ranked from its attempt 1, and reruns are labelled. It also does a dry run; its output is at `agent://QueueOAuth.SiteV7Pipeline`. Publish v7 once the queues finish, using its final commands.
3. Finish this report with the final per-model attempts.
