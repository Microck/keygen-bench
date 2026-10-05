#!/usr/bin/env python3
"""Wait for the wide Devin campaign's drain, then build, compile, doctor and start the dense queue.

Runs on Ashburn from the separate repo-dense tree (shared-VM bound 6, record_video option,
shared-VM-aware Boat reserve); the wide campaign keeps running its own loaded code until it stops.
Writes dense-state.json beside itself; any failing step stops with a recorded reason.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

A = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = A / "devin-20261004"
CONTROL = ROOT / "control"
REPO = ROOT / "repo-dense"
PYTHON = str(A / "runtime/bin/python3.11")
CAMPAIGN_ID = "next-max-tier-prompt-v2-devin-dense-20261004"
STATE = CONTROL / "dense-state.json"
# Worst case is already charged per running attempt; keep a small margin for VM stop/linger.
BOAT_RESERVE_SECONDS = 600


def save(**state):
    STATE.write_text(json.dumps({"at": time.time(), **state}, indent=2) + "\n")


def environment():
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
           "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "RCLONE_CONFIG": str(A / ".private/rclone.conf"),
           "KEYGEN_FT2_ANALYSIS": str(A / "analysis/ft2-analysis"), "LD_LIBRARY_PATH": str(A / "analysis/lib")}
    env.update(json.loads((A / ".private/controller.env.json").read_text()))
    return env


def main():
    os.umask(0o077)
    while json.loads((CONTROL / "drain-state.json").read_text()).get("phase") != "done":
        save(phase="waiting_for_drain")
        time.sleep(30)
    env, done = environment(), []
    manifest, output = CONTROL / "devin-dense-campaign.json", ROOT / "results" / CAMPAIGN_ID
    steps = [("build", [PYTHON, "-I", str(CONTROL / "build-dense-queue.py")]),
             ("compile", [PYTHON, "-I", "benchmark/campaign.py", "--inventory", str(CONTROL / "inventory-devin.json"),
                          "--selection", str(CONTROL / "devin-dense-selection.json"),
                          "--tier-spec", str(CONTROL / "tier-spec-devin.json"),
                          "--queue-plan", str(CONTROL / "devin-dense-plan.json"),
                          "--linked-campaign", str(CONTROL / "devin-only-wide-campaign-packed.json"),
                          "--out", str(manifest)]),
             ("doctor", [PYTHON, "-I", "benchmark/run.py", "doctor", "--campaign", str(manifest), "--out", str(output)])]
    for name, command in steps:
        with (CONTROL / f"dense-{name}.private.log").open("wb") as log:
            result = subprocess.run(command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        if result.returncode:
            save(phase="failed", step=name, returncode=result.returncode, done=done)
            raise SystemExit(1)
        done.append(name)
    log = (CONTROL / "dense-campaign.private.log").open("wb")
    process = subprocess.Popen([PYTHON, "-I", "benchmark/run.py", "queue", "--campaign", str(manifest), "--out", str(output),
                                "--boat-reserve-seconds", str(BOAT_RESERVE_SECONDS)],
                               cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    save(phase="launched", pid=process.pid, campaign_id=CAMPAIGN_ID, done=done,
         manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
