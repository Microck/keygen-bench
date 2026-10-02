#!/usr/bin/env python3
"""Build OAuth rerun queue 3 from the stopped queue 2 (same frozen routes; anthropic bound 4, workers 8), on the controller.

`build-followup.py QUEUE1_ROOT QUEUE1_CONTROL OUT_CONTROL` (run with the follow-up repo's benchmark/ on
sys.path). For every ordinal of queue 1's frozen plan it keeps the frozen origin and appends each attempt
queue 1 ran for it as a frozen `reruns` link (status, status.json sha256, outcome and failure category
from benchmark.report.attempt_row, the report's own classification). Models whose every ordinal now
holds a scored outcome or a model failure are dropped; the rest keep their exact frozen route,
proof and settings from queue 1's selection. Only campaign ID changes. Writes oauth-queue-2-selection.json,
oauth-queue-2-plan.json and copies collected-proofs/ into OUT_CONTROL.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import report  # follow-up repo benchmark/ is on sys.path (PYTHONPATH)

CAMPAIGN_ID = "next-max-tier-prompt-v2-oauth-queue-3-20261002"
ANTHROPIC = 4  # user, 2026-10-02: run Claude a bit more in parallel


def main():
    root, control, out = (Path(value) for value in sys.argv[1:4])
    config, config_hash, fingerprint = report.open_cohort(root, root / "campaign.lock.json")
    cohort = report.campaign_cohort(config)
    models = {model["id"]: model for model in config["models"]}
    plan, summary = {}, {}
    for model_id, entries in config["policies"]["plan"].items():
        followed = []
        for entry in entries:
            links = report.entry_links(entry)
            reruns = list(entry.get("reruns") or [])
            if report.entry_reruns(entry):
                index = report.entry_next_index(entry)
                previous = links[-1]["attempt_id"] if links else None
                while (root / report.queue_chain_id(model_id, entry["repetition"], index)).exists():
                    attempt_id = report.queue_chain_id(model_id, entry["repetition"], index)
                    row = report.attempt_row(root, attempt_id, (models[model_id], entry["repetition"]), fingerprint,
                                             config_hash, cohort, retry_of=previous)
                    if row["status"] in report.PENDING_STATUSES:
                        raise SystemExit(f"{attempt_id}: {row['status']}; recover queue 1 before freezing it")
                    outcome = row["outcome"]
                    if outcome not in {"SUCCESS", "FAILURE"}:
                        raise SystemExit(f"{attempt_id}: outcome {outcome} needs review")
                    link = {"campaign_id": config["campaign_id"], "attempt_id": attempt_id, "status": row["status"],
                            "status_sha256": hashlib.sha256((root / attempt_id / "status.json").read_bytes()).hexdigest(),
                            "outcome": outcome, "failure_category": row["failure_category"] if outcome == "FAILURE" else None}
                    if not link["failure_category"] and outcome == "FAILURE":
                        raise SystemExit(f"{attempt_id}: failure without category")
                    reruns.append(link)
                    previous = attempt_id
                    index += 1
            item = {"repetition": entry["repetition"], "origin": entry["origin"]}
            if reruns:
                item["reruns"] = reruns
            followed.append(item)
        if any(report.entry_reruns(item) for item in followed):
            plan[model_id] = followed
        summary[model_id] = [(item["repetition"], [link["attempt_id"].rsplit("-rep-", 1)[1] + ":" + link["outcome"]
                                                   + (f"/{link['failure_category']}" if link["failure_category"] else "")
                                                   for link in report.entry_links(item)], report.entry_reruns(item))
                             for item in followed]
    selection = json.loads((control / "oauth-queue-2-selection.json").read_text())
    selection["models"] = [model for model in selection["models"] if model["id"] in plan]
    selection["campaign_id"] = CAMPAIGN_ID
    selection["concurrency"] = {**selection["concurrency"], "workers": 8,
                                "providers": {**selection["concurrency"]["providers"], "anthropic_oauth": ANTHROPIC}}
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(control / "collected-proofs", out / "collected-proofs", dirs_exist_ok=True)
    (out / "oauth-queue-3-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (out / "oauth-queue-3-plan.json").write_text(json.dumps({"max_queue_attempts": config["policies"]["max_queue_attempts"],
                                                             "models": plan}, indent=2) + "\n")
    print(json.dumps({"models": sorted(plan), "ordinals": summary}, indent=1))


if __name__ == "__main__":
    main()
