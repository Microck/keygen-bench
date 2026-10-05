#!/usr/bin/env python3
"""Build one go-key4 follow-up rerun queue from the stopped go-arm64 queue, on Paris.

User 2026-10-05: key 3 is at its monthly limit; continue on the new key OPENCODE_GO_API_KEY_4.

Same chain logic as go-parallel/build-followup.py (frozen origin and earlier reruns, then every
attempt the stopped queue ran appended as a frozen `reruns` link). Operational changes only:
- user 2026-10-04: Boat credit is spent, so attempts run in Paris's local Docker on the arm64
  images built from the same Dockerfile (identical image IDs to Ashburn's Devin arm64 fill);
  the plan declares `cross_environment` so links compare the environment-free fingerprint and
  each attempt keeps its own environment record (transport backend, image IDs);
- key _3 only, up to 3 attempts at once (workers 3, Go bound 3, pool {_3: 3}).
Every model, frozen route, proof and setting stays as the stopped queue froze them.

usage: build-followup.py NAME QUEUE_ROOT SELECTION OUT_DIR AGENT_IMAGE_ID VISUALIZER_IMAGE_ID
(deployed repo benchmark/ on PYTHONPATH). Reads no credentials.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import report  # deployed repo benchmark/ is on sys.path (PYTHONPATH)

FOLLOWS = {"main": ("next-max-tier-prompt-v2-go-arm64-20261005", "next-max-tier-prompt-v2-go-key4-20261005"),
           "addon": ("next-max-tier-prompt-v2-paris-addon-go-parallel-20261002",  # go-arm64 addon never ran
                     "next-max-tier-prompt-v2-paris-addon-go-key4-20261005")}
GO_POOL = {"OPENCODE_GO_API_KEY_4": 3}
WORKERS = 3


def main():
    name = sys.argv[1]
    root, selection_path, out = (Path(value) for value in sys.argv[2:5])
    agent, visualizer = sys.argv[5:7]
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
        summary[model_id] = [item["repetition"] for item in followed if report.entry_reruns(item)]
    selection = json.loads(selection_path.read_text())
    if selection["campaign_id"] != previous_id or [model["id"] for model in selection["models"]] != list(models):
        raise SystemExit("selection is not the stopped queue's frozen selection")
    selection["campaign_id"] = campaign_id
    selection["transport"] = {"backend": "local"}
    selection["image"], selection["visualizer_image"] = agent, visualizer
    selection["concurrency"] = {**selection["concurrency"], "workers": WORKERS,
                                "providers": {**selection["concurrency"]["providers"], "go": WORKERS},
                                "key_pools": {"OPENCODE_GO_API_KEY": dict(GO_POOL)}}
    out.mkdir(parents=True, exist_ok=True)
    if selection_path.parent.resolve() != out.resolve():  # proofs are already in place when following go-arm64
        shutil.copytree(selection_path.parent / "collected-proofs", out / "collected-proofs", dirs_exist_ok=True)
    (out / f"go-key4-{name}-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (out / f"go-key4-{name}-plan.json").write_text(json.dumps(
        {"max_queue_attempts": config["policies"]["max_queue_attempts"], "cross_environment": True,
         "models": plan}, indent=2) + "\n")
    print(json.dumps({"campaign_id": campaign_id, "follows": previous_id, "to_run": summary}))


if __name__ == "__main__":
    main()
