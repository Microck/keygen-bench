#!/usr/bin/env python3
"""Build the go-three rerun-queue plans (policy independent_repetitions_infrastructure_reruns).

usage: build-queue.py MAIN_ROOT_COPY

main  (go-three-plan.json): the 17 main-campaign Go routes (go-three-selection.json). Repetition 1
      is the main campaign's own first slot: kept when it holds a scored outcome, rerun as a linked
      retry when it failed for a non-model reason (QUOTA). Repetitions 2 and 3 are new independent
      repetitions run here; the main campaign's first-success later slots (SKIPPED_AFTER_SUCCESS or
      RESERVED behind a QUOTA stop) were conditional slots and stay untouched there.
addon (paris-addon-plan.json): glm-5.2, glm-5.3, minimax-m2.7 have no earlier campaign attempt, so
      all three repetitions run fresh.

Origins are classified by benchmark.report.attempt_row on a read-only metadata copy of the main
results root and frozen with their status.json sha256.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
sys.path.insert(0, str(PREP.parents[2] / "benchmark"))
import report  # noqa: E402

MAIN_ID = "next-max-tier-prompt-v2-ashburn-20261001"
# A chain may hold the ordinal's own attempt plus reruns of non-model failures; Go usage-window
# QUOTA stops are expected, so allow up to six attempts per repetition before giving up.
MAX_QUEUE_ATTEMPTS = 6


def classify(root: Path, attempt_id: str, repetition: int) -> dict:
    config, config_hash, fingerprint = report.open_cohort(root, root / "campaign.lock.json")
    if config["campaign_id"] != MAIN_ID:
        raise SystemExit("not the main campaign root")
    model_id = attempt_id.rsplit("-rep-", 1)[0]
    model = next(model for model in config["models"] if model["id"] == model_id)
    row = report.attempt_row(root, attempt_id, (model, repetition), fingerprint, config_hash, report.campaign_cohort(config))
    if row["status"] == "RESERVED":
        outcome = "UNATTEMPTED"
    elif row["outcome"] in {"SUCCESS", "FAILURE"}:
        outcome = row["outcome"]
    else:
        raise SystemExit(f"{attempt_id}: outcome {row['outcome']} needs review before it can be an origin")
    return {"campaign_id": config["campaign_id"], "attempt_id": attempt_id, "status": row["status"],
            "status_sha256": hashlib.sha256((root / attempt_id / "status.json").read_bytes()).hexdigest(),
            "outcome": outcome, "failure_category": row["failure_category"] if outcome == "FAILURE" else None}


def main():
    main_root = Path(sys.argv[1])
    selection = json.loads((HERE / "go-three-selection.json").read_text())
    plan = {}
    for model in selection["models"]:
        plan[model["id"]] = [{"repetition": 1, "origin": classify(main_root, f"{model['id']}-rep-1", 1)},
                             {"repetition": 2, "origin": None}, {"repetition": 3, "origin": None}]
    (HERE / "go-three-plan.json").write_text(json.dumps({"max_queue_attempts": MAX_QUEUE_ATTEMPTS, "models": plan}, indent=2) + "\n")
    addon = json.loads((PREP / "paris-addon" / "paris-addon-selection.json").read_text())
    addon_plan = {model["id"]: [{"repetition": n, "origin": None} for n in (1, 2, 3)] for model in addon["models"]}
    (PREP / "paris-addon" / "paris-addon-plan.json").write_text(
        json.dumps({"max_queue_attempts": MAX_QUEUE_ATTEMPTS, "models": addon_plan}, indent=2) + "\n")
    for model_id, entries in {**plan, **addon_plan}.items():
        print(model_id, [(entry["repetition"], (entry["origin"] or {}).get("outcome", "NEW"),
                          (entry["origin"] or {}).get("failure_category"), report.origin_reruns(entry["origin"]))
                         for entry in entries])


if __name__ == "__main__":
    main()
