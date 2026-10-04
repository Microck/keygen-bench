#!/usr/bin/env python3
"""Build the Ashburn arm64 Devin rerun queue (cross_environment) for the ordinals Boat could not run.

User 2026-10-04 ~16:40Z: Boat credit ran low; fill only the missing Devin ordinals on Ashburn's own
Docker (native arm64 images built from the same Dockerfile), mixing environments within a model's
best of three; every attempt keeps its environment record (transport backend and image IDs).
Parity check: the arm64 render of a Boat-rendered module differs by at most 1 LSB in 0.012% of
samples (FT2 render validation tolerates two LSBs). qemu x86 emulation was rejected: 25x slower.

Origins: each ordinal's frozen origin from the dense Boat queue's plan (wide campaign slots), plus
the dense queue's reruns of that ordinal, classified with benchmark.report.attempt_row.
Run on Ashburn -> control/devin-arm-selection.json, control/devin-arm-plan.json
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

A = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = A / "devin-20261004"
CONTROL = ROOT / "control"
DENSE_ID = "next-max-tier-prompt-v2-devin-dense-20261004"
DENSE_ROOT = ROOT / "results" / DENSE_ID
CAMPAIGN_ID = "next-max-tier-prompt-v2-devin-arm64-20261004"
AGENT, VISUALIZER = "keygen-ft2-benchmark:arm64-agent", "keygen-ft2-visualizer:arm64"
# Local workers reserve 512 MiB + a 2 GiB sandbox cap each: 3 fit Ashburn's ~10 GiB available.
WORKERS = 3
sys.path.insert(0, str(ROOT / "repo-dense/benchmark"))
import report  # noqa: E402


def image_id(tag: str) -> str:
    return subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", tag], check=True,
                          capture_output=True, text=True).stdout.strip()


def classify(attempt_id: str, repetition: int) -> dict:
    config, config_hash, fingerprint = report.open_cohort(DENSE_ROOT, DENSE_ROOT / "campaign.lock.json")
    model = next(m for m in config["models"] if m["id"] == attempt_id.rsplit("-rep-", 1)[0])
    row = report.attempt_row(DENSE_ROOT, attempt_id, (model, repetition), fingerprint, config_hash,
                             report.campaign_cohort(config))
    if row["outcome"] not in {"SUCCESS", "FAILURE"}:
        raise SystemExit(f"{attempt_id}: outcome {row['outcome']} needs review before it can be a rerun link")
    return {"campaign_id": DENSE_ID, "attempt_id": attempt_id, "status": row["status"],
            "status_sha256": hashlib.sha256((DENSE_ROOT / attempt_id / "status.json").read_bytes()).hexdigest(),
            "outcome": row["outcome"], "failure_category": row["failure_category"] if row["outcome"] == "FAILURE" else None}


def main():
    dense_plan = json.loads((CONTROL / "devin-dense-plan.json").read_text())["models"]
    selection = json.loads((CONTROL / "devin-dense-selection.json").read_text())
    plan, models = {}, []
    for model in selection["models"]:
        entries = []
        for entry in dense_plan[model["id"]]:
            n, reruns, index = entry["repetition"], [], 1
            while (DENSE_ROOT / report.queue_chain_id(model["id"], n, index) / "status.json").exists():
                reruns.append(classify(report.queue_chain_id(model["id"], n, index), n))
                index += 1
            entries.append({"repetition": n, "origin": entry["origin"], **({"reruns": reruns} if reruns else {})})
        if any(report.origin_reruns((e.get("reruns") or [e["origin"]])[-1]) for e in entries):
            models.append(model)
            plan[model["id"]] = entries
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = models
    selection["transport"] = {"backend": "local"}
    selection["image"], selection["visualizer_image"] = image_id(AGENT), image_id(VISUALIZER)
    selection["concurrency"] = {**selection["concurrency"], "workers": WORKERS, "key_pools": {}}
    selection["concurrency"]["providers"]["devin"] = WORKERS
    (CONTROL / "devin-arm-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (CONTROL / "devin-arm-plan.json").write_text(json.dumps(
        {"max_queue_attempts": 4, "cross_environment": True, "models": plan}, indent=2) + "\n")
    runs = {model_id: [e["repetition"] for e in entries if report.origin_reruns((e.get("reruns") or [e["origin"]])[-1])]
            for model_id, entries in plan.items()}
    print(json.dumps({"models": len(models), "ordinals_to_run": sum(map(len, runs.values())), "runs": runs}))


if __name__ == "__main__":
    main()
