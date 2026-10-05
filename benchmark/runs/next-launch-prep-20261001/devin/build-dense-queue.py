#!/usr/bin/env python3
"""Build the dense Devin rerun queue (policy independent_repetitions_infrastructure_reruns).

User 2026-10-04: use Boat as efficiently as possible. The 6-wide Devin-only campaign (3 attempts
per default VM, video on) is drained; its unrun ordinals continue in this queue with 6 attempts
per default VM and no presentation video. Neither setting is part of the condition fingerprint
(report.condition_fingerprint: route, settings, prompts, limits, images, Boat type and TTL), so
each model's three attempts stay one condition across both campaigns.

Run on Ashburn after drain-stop reports done:
  build-dense-queue.py  -> control/devin-dense-selection.json, control/devin-dense-plan.json
Origins are classified with benchmark.report.attempt_row exactly as the OAuth queues were.
"""
import hashlib
import json
from pathlib import Path
import sys

A = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = A / "devin-20261004"
CONTROL = ROOT / "control"
WIDE_ID = "next-max-tier-prompt-v2-devin-only-wide-20261004"
WIDE_ROOT = ROOT / "results" / WIDE_ID
CAMPAIGN_ID = "next-max-tier-prompt-v2-devin-dense-20261004"
MAX_QUEUE_ATTEMPTS = 4
sys.path.insert(0, str(ROOT / "repo/benchmark"))
import report  # noqa: E402


def classify(attempt_id: str, repetition: int) -> dict:
    config, config_hash, fingerprint = report.open_cohort(WIDE_ROOT, WIDE_ROOT / "campaign.lock.json")
    model = next(m for m in config["models"] if m["id"] == attempt_id.rsplit("-rep-", 1)[0])
    row = report.attempt_row(WIDE_ROOT, attempt_id, (model, repetition), fingerprint, config_hash,
                             report.campaign_cohort(config))
    if row["status"] == "RESERVED":
        outcome = "UNATTEMPTED"
    elif row["outcome"] in {"SUCCESS", "FAILURE"}:
        outcome = row["outcome"]
    else:
        raise SystemExit(f"{attempt_id}: outcome {row['outcome']} needs review before it can be an origin")
    return {"campaign_id": WIDE_ID, "attempt_id": attempt_id, "status": row["status"],
            "status_sha256": hashlib.sha256((WIDE_ROOT / attempt_id / "status.json").read_bytes()).hexdigest(),
            "outcome": outcome, "failure_category": row["failure_category"] if outcome == "FAILURE" else None}


def main():
    selection = json.loads((CONTROL / "devin-only-wide-selection.json").read_text())
    plan, models = {}, []
    for model in selection["models"]:
        origins = [classify(f"{model['id']}-rep-{n}", n) for n in (1, 2, 3)]
        if any(report.origin_reruns(origin) for origin in origins):
            models.append(model)
            plan[model["id"]] = [{"repetition": n, "origin": origin} for n, origin in enumerate(origins, 1)]
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = models
    selection["transport"]["boat"].update(attempts_per_vm=6, record_video=False)
    selection["concurrency"]["workers"] = 6
    selection["concurrency"]["providers"]["devin"] = 6
    (CONTROL / "devin-dense-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (CONTROL / "devin-dense-plan.json").write_text(
        json.dumps({"max_queue_attempts": MAX_QUEUE_ATTEMPTS, "models": plan}, indent=2) + "\n")
    print(json.dumps({model_id: [(e["repetition"], e["origin"]["outcome"], e["origin"]["failure_category"],
                                  report.origin_reruns(e["origin"])) for e in entries]
                      for model_id, entries in plan.items()}, indent=1))


if __name__ == "__main__":
    main()
