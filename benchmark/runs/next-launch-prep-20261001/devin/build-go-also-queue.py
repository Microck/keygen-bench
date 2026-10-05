#!/usr/bin/env python3
"""Build the Ashburn arm64 Devin rerun queue for the Go models that are also on Devin.

User 2026-10-05: Go key 3 is at its monthly limit, so run these on Devin now. The 7 models are the
ones qualified on Devin on 2026-10-04 (GLM-5.2 failed Devin qualification twice and stays on Go).
Origins are the slots of the first Devin campaign (next-max-tier-prompt-v2-devin-20261004, Boat x86),
where DeepSeek V4 Pro and V4.1 Flash already have a scored attempt 1; their attempt 2 was
interrupted (infra) and is rerun. The plan declares `cross_environment`; attempts run on Ashburn's
local arm64 Docker exactly like the Devin arm64 fill. These Devin attempts are a separate route and
never enter any Go best-of-three.
Run on Ashburn -> control/devin-go-also-selection.json, control/devin-go-also-plan.json
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

A = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = A / "devin-20261004"
CONTROL = ROOT / "control"
FIRST_ID = "next-max-tier-prompt-v2-devin-20261004"
FIRST_ROOT = ROOT / "results" / FIRST_ID
CAMPAIGN_ID = "next-max-tier-prompt-v2-devin-go-also-arm64-20261005"
MODELS = ["devin-deepseek-v4-pro", "devin-deepseek-v4-1-flash", "devin-glm-5-3", "devin-glm-5-3-flash",
          "devin-grok-4-6", "devin-grok-4-7", "devin-kimi-k3"]
AGENT, VISUALIZER = "keygen-ft2-benchmark:arm64-agent", "keygen-ft2-visualizer:arm64"
WORKERS = 3
sys.path.insert(0, str(ROOT / "repo-dense/benchmark"))
import report  # noqa: E402


def image_id(tag):
    return subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], check=True,
                          capture_output=True, text=True).stdout.strip()


def classify(attempt_id, repetition):
    config, config_hash, fingerprint = report.open_cohort(FIRST_ROOT, FIRST_ROOT / "campaign.lock.json")
    model = next(m for m in config["models"] if m["id"] == attempt_id.rsplit("-rep-", 1)[0])
    row = report.attempt_row(FIRST_ROOT, attempt_id, (model, repetition), fingerprint, config_hash,
                             report.campaign_cohort(config))
    if row["status"] == "RESERVED":
        outcome = "UNATTEMPTED"
    elif row["outcome"] in {"SUCCESS", "FAILURE"}:
        outcome = row["outcome"]
    else:
        raise SystemExit(f"{attempt_id}: outcome {row['outcome']} needs review before it can be an origin")
    return {"campaign_id": FIRST_ID, "attempt_id": attempt_id, "status": row["status"],
            "status_sha256": hashlib.sha256((FIRST_ROOT / attempt_id / "status.json").read_bytes()).hexdigest(),
            "outcome": outcome, "failure_category": row["failure_category"] if outcome == "FAILURE" else None}


def main():
    selection = json.loads((CONTROL / "devin-selection.json").read_text())
    by_id = {m["id"]: m for m in selection["models"]}
    missing = [m for m in MODELS if m not in by_id]
    if missing:
        raise SystemExit(f"not qualified in the first Devin selection: {missing}")
    plan = {m: [{"repetition": n, "origin": classify(f"{m}-rep-{n}", n)} for n in (1, 2, 3)] for m in MODELS}
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = [by_id[m] for m in MODELS]
    selection["transport"] = {"backend": "local"}
    selection["image"], selection["visualizer_image"] = image_id(AGENT), image_id(VISUALIZER)
    selection["concurrency"] = {**selection["concurrency"], "workers": WORKERS, "key_pools": {}}
    selection["concurrency"]["providers"]["devin"] = WORKERS
    (CONTROL / "devin-go-also-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (CONTROL / "devin-go-also-plan.json").write_text(json.dumps(
        {"max_queue_attempts": 4, "cross_environment": True, "models": plan}, indent=2) + "\n")
    print(json.dumps({m: [(e["repetition"], e["origin"]["outcome"], e["origin"]["failure_category"],
                           report.origin_reruns(e["origin"])) for e in entries] for m, entries in plan.items()}))


if __name__ == "__main__":
    main()
