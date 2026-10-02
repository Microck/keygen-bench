#!/usr/bin/env python3
"""Build one go-parallel follow-up rerun queue from the stopped go-exclusive queue, on the controller.

Same as go-exclusive/build-followup.py except: follows go-exclusive, and the user-approved cheap-model
parallelism (key _3 only, up to 3 attempts at once: workers 3, Go bound 3, pool {_3: 3}).

usage: build-followup.py NAME QUEUE_ROOT SELECTION OUT_DIR   (deployed repo benchmark/ on PYTHONPATH)

NAME is `main` (follows next-max-tier-prompt-v2-go-three-20261002) or `addon` (follows
next-max-tier-prompt-v2-paris-addon-20261001). For every ordinal of the stopped queue's frozen plan
it keeps the frozen origin and earlier reruns and appends each attempt that queue ran for it as a
frozen `reruns` link (status, status.json sha256, outcome and failure category from
benchmark.report.attempt_row, the report's own classification), so the chain and its attempt
numbering continue here. Every model and every frozen route, proof and setting stay as the stopped
queue froze them; only operational fields change: campaign ID, workers 1, Go bound 1 and the key
pool {OPENCODE_GO_API_KEY_3: 1} (user rule: one Go attempt at a time, on key _3 only). The 8
Devin-available Go models are deferred with `run.py queue --hold` (make-launch-plan.py), not here.
Writes go-exclusive-NAME-selection.json and go-exclusive-NAME-plan.json and copies the selection's
collected-proofs/ into OUT_DIR. Reads no credentials.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import report  # deployed repo benchmark/ is on sys.path (PYTHONPATH)

FOLLOWS = {"main": ("next-max-tier-prompt-v2-go-exclusive-20261002", "next-max-tier-prompt-v2-go-parallel-20261002"),
           "addon": ("next-max-tier-prompt-v2-paris-addon-go-exclusive-20261002",
                     "next-max-tier-prompt-v2-paris-addon-go-parallel-20261002")}
GO_POOL = {"OPENCODE_GO_API_KEY_3": 3}
WORKERS = 3


def main():
    name = sys.argv[1]
    root, selection_path, out = (Path(value) for value in sys.argv[2:5])
    previous_id, campaign_id = FOLLOWS[name]
    config, config_hash, fingerprint = report.open_cohort(root, root / "campaign.lock.json")
    if config["campaign_id"] != previous_id:
        raise SystemExit(f"{root}: not the {previous_id} root")
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
                        raise SystemExit(f"{attempt_id}: {row['status']}; recover the stopped queue before freezing it")
                    outcome = row["outcome"]
                    if outcome not in {"SUCCESS", "FAILURE"}:
                        raise SystemExit(f"{attempt_id}: outcome {outcome} needs review")
                    link = {"campaign_id": config["campaign_id"], "attempt_id": attempt_id, "status": row["status"],
                            "status_sha256": hashlib.sha256((root / attempt_id / "status.json").read_bytes()).hexdigest(),
                            "outcome": outcome, "failure_category": row["failure_category"] if outcome == "FAILURE" else None}
                    if outcome == "FAILURE" and not link["failure_category"]:
                        raise SystemExit(f"{attempt_id}: failure without category")
                    reruns.append(link)
                    previous = attempt_id
                    index += 1
            item = {"repetition": entry["repetition"], "origin": entry["origin"]}
            if reruns:
                item["reruns"] = reruns
            followed.append(item)
        plan[model_id] = followed
        summary[model_id] = [(item["repetition"], [link["attempt_id"].rsplit("-rep-", 1)[1] + ":" + link["outcome"]
                                                   + (f"/{link['failure_category']}" if link["failure_category"] else "")
                                                   for link in report.entry_links(item)], report.entry_reruns(item))
                             for item in followed]
    selection = json.loads(selection_path.read_text())
    if selection["campaign_id"] != previous_id or [model["id"] for model in selection["models"]] != list(models):
        raise SystemExit("selection is not the stopped queue's frozen selection")
    selection["campaign_id"] = campaign_id
    selection["concurrency"] = {**selection["concurrency"], "workers": WORKERS,
                                "providers": {**selection["concurrency"]["providers"], "go": WORKERS},
                                "key_pools": {"OPENCODE_GO_API_KEY": dict(GO_POOL)}}
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(selection_path.parent / "collected-proofs", out / "collected-proofs", dirs_exist_ok=True)
    (out / f"go-parallel-{name}-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (out / f"go-parallel-{name}-plan.json").write_text(json.dumps(
        {"max_queue_attempts": config["policies"]["max_queue_attempts"], "models": plan}, indent=2) + "\n")
    print(json.dumps({"campaign_id": campaign_id, "follows": previous_id, "ordinals": summary}, indent=1))


if __name__ == "__main__":
    main()
