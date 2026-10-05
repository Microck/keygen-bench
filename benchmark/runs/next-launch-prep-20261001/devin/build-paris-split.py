#!/usr/bin/env python3
"""Freeze a Paris follow-up of the Ashburn devin-go-also queue for a subset of its models.

User 2026-10-05: parallelize Devin while Go waits for its 5-hour window. Paris (idle) takes
PARIS_MODELS; the Ashburn queue is drained and relaunched with those models held, so no ordinal can
start on both machines. Chain logic is the same as the go follow-up builders: each ordinal keeps its
frozen origin and earlier reruns, then every attempt the Ashburn queue ran for it becomes a frozen
`reruns` link. Environment unchanged (local arm64, identical image IDs), so links compare the same
way; `cross_environment` is kept because the chains start on Boat x86.
Run on Ashburn -> control/devin-paris-selection.json, control/devin-paris-plan.json
"""
import hashlib
import json
from pathlib import Path
import sys

A = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = A / "devin-20261004"
CONTROL = ROOT / "control"
QUEUE_ID = "next-max-tier-prompt-v2-devin-go-also-arm64-20261005"
QUEUE_ROOT = ROOT / "results" / QUEUE_ID
CAMPAIGN_ID = "next-max-tier-prompt-v2-devin-go-also-paris-20261005"
PARIS_MODELS = ["devin-grok-4-6", "devin-grok-4-7", "devin-glm-5-3-flash"]
sys.path.insert(0, str(ROOT / "repo-dense/benchmark"))
import report  # noqa: E402


def main():
    config, config_hash, fingerprint = report.open_cohort(QUEUE_ROOT, QUEUE_ROOT / "campaign.lock.json")
    cohort = report.campaign_cohort(config)
    models = {m["id"]: m for m in config["models"]}
    plan = {}
    for model_id in PARIS_MODELS:
        followed = []
        for entry in config["policies"]["plan"][model_id]:
            links, reruns = report.entry_links(entry), list(entry.get("reruns") or [])
            if report.entry_reruns(entry):
                index, previous = report.entry_next_index(entry), (links[-1]["attempt_id"] if links else None)
                while (QUEUE_ROOT / report.queue_chain_id(model_id, entry["repetition"], index)).exists():
                    attempt_id = report.queue_chain_id(model_id, entry["repetition"], index)
                    row = report.attempt_row(QUEUE_ROOT, attempt_id, (models[model_id], entry["repetition"]),
                                             fingerprint, config_hash, cohort, retry_of=previous)
                    if row["status"] in report.PENDING_STATUSES or row["outcome"] not in {"SUCCESS", "FAILURE"}:
                        raise SystemExit(f"{attempt_id}: {row['status']}/{row['outcome']}; not freezable yet")
                    reruns.append({"campaign_id": QUEUE_ID, "attempt_id": attempt_id, "status": row["status"],
                                   "status_sha256": hashlib.sha256((QUEUE_ROOT / attempt_id / "status.json").read_bytes()).hexdigest(),
                                   "outcome": row["outcome"],
                                   "failure_category": row["failure_category"] if row["outcome"] == "FAILURE" else None})
                    previous, index = attempt_id, index + 1
            item = {"repetition": entry["repetition"], "origin": entry["origin"]}
            if reruns:
                item["reruns"] = reruns
            followed.append(item)
        plan[model_id] = followed
    selection = json.loads((CONTROL / "devin-go-also-selection.json").read_text())
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = [m for m in selection["models"] if m["id"] in PARIS_MODELS]
    (CONTROL / "devin-paris-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (CONTROL / "devin-paris-plan.json").write_text(json.dumps(
        {"max_queue_attempts": config["policies"]["max_queue_attempts"], "cross_environment": True, "models": plan},
        indent=2) + "\n")
    print(json.dumps({m: [e["repetition"] for e in es if report.entry_reruns(e)] for m, es in plan.items()}))


if __name__ == "__main__":
    main()
