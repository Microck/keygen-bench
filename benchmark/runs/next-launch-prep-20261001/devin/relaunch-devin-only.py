#!/usr/bin/env python3
"""Compile, doctor and launch the Devin-only campaign once drain-stop has stopped the first one.

User decision 2026-10-04: any model with a Go route waits for Go quota. The Devin-only campaign
keeps the first campaign's frozen settings and reuses its verified readiness proofs; it drops
the 7 Go-routable models (DeepSeek V4 Pro, DeepSeek V4.1 Flash, GLM-5.3, GLM-5.3 Flash, Grok 4.6,
Grok 4.7, Kimi K3). Kimi K2.6 (retired on Go) and DeepSeek V4 Flash (Go checkpoint unproven) stay.
Run on Ashburn: waits for drain-state phase "done", then compiles, doctors and starts run.py
detached. Writes relaunch-state.json beside itself; any failure stops with a recorded reason.
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
CAMPAIGN_ID = "next-max-tier-prompt-v2-devin-only-20261004"
GO_ROUTABLE = {"devin-deepseek-v4-pro", "devin-deepseek-v4-1-flash", "devin-glm-5-3", "devin-glm-5-3-flash",
               "devin-grok-4-6", "devin-grok-4-7", "devin-kimi-k3"}
STATE = CONTROL / "relaunch-state.json"
PYTHON = str(A / "runtime/bin/python3.11")


def save(**state):
    STATE.write_text(json.dumps({"at": time.time(), **state}, indent=2) + "\n")


def environment():
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
           "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "RCLONE_CONFIG": str(A / ".private/rclone.conf"),
           "KEYGEN_FT2_ANALYSIS": str(A / "analysis/ft2-analysis"), "LD_LIBRARY_PATH": str(A / "analysis/lib")}
    env.update(json.loads((A / ".private/controller.env.json").read_text()))
    return env


def main():
    os.umask(0o077)
    while json.loads((CONTROL / "drain-state.json").read_text()).get("phase") != "done":
        save(phase="waiting_for_drain")
        time.sleep(30)
    selection = json.loads((CONTROL / "devin-selection.json").read_text())
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = [m for m in selection["models"] if m["id"] not in GO_ROUTABLE]
    path = CONTROL / "devin-only-selection.json"
    path.write_text(json.dumps(selection, indent=2) + "\n")
    manifest, output = CONTROL / "devin-only-campaign-packed.json", ROOT / "results" / CAMPAIGN_ID
    env, repo = environment(), ROOT / "repo"
    steps = [("compile", [PYTHON, "-I", "benchmark/campaign.py", "--inventory", str(CONTROL / "inventory-devin.json"),
                          "--selection", str(path), "--tier-spec", str(CONTROL / "tier-spec-devin.json"),
                          "--repetitions", "1,2,3", "--out", str(manifest)]),
             ("doctor", [PYTHON, "-I", "benchmark/run.py", "doctor", "--campaign", str(manifest), "--out", str(output)])]
    done = []
    for name, command in steps:
        with (CONTROL / f"devin-only-{name}.private.log").open("wb") as log:
            result = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        if result.returncode:
            save(phase="failed", step=name, returncode=result.returncode, done=done)
            raise SystemExit(1)
        done.append(name)
    log = (CONTROL / "devin-only-campaign.private.log").open("wb")
    process = subprocess.Popen([PYTHON, "-I", "benchmark/run.py", "run", "--campaign", str(manifest), "--out", str(output)],
                               cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    save(phase="launched", pid=process.pid, campaign_id=CAMPAIGN_ID, models=[m["id"] for m in selection["models"]],
         manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(), done=done)


if __name__ == "__main__":
    main()
