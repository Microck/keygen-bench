#!/usr/bin/env python3
"""Write control/launch-plan.json on Ashburn: frozen fingerprints of the deployed follow-up OAuth queue.

Run on the controller after compile: `make-launch-plan.py [--hold MODEL_ID ...]` (no credentials read).
Held models (operator deferral) are passed to `run.py queue --hold`: never probed or started.
"""
import hashlib
import json
from pathlib import Path
import sys

ASHBURN = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = ASHBURN / "oauth-queue-2-20261002"
CONTROL = ROOT / "control"
CAMPAIGN_ID = "next-max-tier-prompt-v2-oauth-queue-2-20261002"
HELPERS = ("control/archive-only.py", "control/launch-driver.py",
           "control/launch-status.py", "control/terminal-guard.py")
SOURCES = ("MODEL-TEST-PLAN.oauth-first.json", "benchmark/Dockerfile", "benchmark/__init__.py",
           "benchmark/artifacts.py", "benchmark/boat.py", "benchmark/boat_api.py",
           "benchmark/boat_transport.py", "benchmark/bridge.py", "benchmark/campaign.py",
           "benchmark/drive.py", "benchmark/native_models.py", "benchmark/native_readiness.py",
           "benchmark/prompts/system.txt", "benchmark/prompts/task.txt", "benchmark/report.py",
           "benchmark/report_page.py", "benchmark/requirements.txt", "benchmark/run.py",
           "benchmark/score.py", "benchmark/score_audio.py", "benchmark/score_loop.py",
           "benchmark/score_mix.py", "benchmark/score_playback.py", "benchmark/score_structure.py",
           "benchmark/visualize.sh")
FROZEN = ("control/tier-spec-c8cba354.json", "control/ashburn-campaign.json",
          "control/oauth-repeats-campaign.json", "control/oauth-queue-campaign.json",
          "control/oauth-queue-2-plan.json", "control/oauth-queue-2-selection.json")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    args = sys.argv[1:]
    if len(args) % 2 or any(flag != "--hold" for flag in args[::2]):
        raise SystemExit("usage: make-launch-plan.py [--hold MODEL_ID ...]")
    holds = args[1::2]
    campaign = CONTROL / "oauth-queue-2-campaign.json"
    models = {model["id"] for model in json.loads(campaign.read_text())["campaign"]["models"]}
    if not set(holds) <= models:
        raise SystemExit("held models must belong to the campaign")
    python = ASHBURN / "runtime/bin/python3.11"
    plan = {
        "schema": "keygen-launch-supervisor-plan-1",
        "campaign_id": CAMPAIGN_ID,
        "root": str(ROOT),
        "control": str(CONTROL),
        "helpers": "control/launch-driver.py",
        "python": str(python),
        "env_file": str(ASHBURN / ".private/controller.env.json"),
        "rclone_config": str(ASHBURN / ".private/rclone.conf"),
        "analysis": str(ASHBURN / "analysis"),
        "controller_lock": str(ASHBURN / "launch-control/controller.lock"),
        # Carry the newest Boat start on this controller forward (main campaign, queue 1, this queue).
        "pacing_roots": [str(ASHBURN / "next-launch-20261001/results"),
                         str(ASHBURN / "oauth-queue-20261002/results"), str(ROOT / "results")],
        "campaign": str(campaign),
        "campaign_sha256": digest(campaign),
        "manifest_sha256": json.loads(campaign.read_text())["sha256"],
        "out": str(ROOT / "results" / CAMPAIGN_ID),
        "workers": 6,
        "queue": {"probe_interval_seconds": 1800, "retry_interval_seconds": 300, "boat_reserve_seconds": 36000,
                  "holds": holds},
        # Remaining Claude ordinals (anthropic 2 at a time) plus usage-limit waits re-probed every 30 min.
        "deadline_seconds": 252000,
        "archive_copy_timeout_seconds": 1800,
        "guards": {"sample_seconds": 15, "mem_available_bytes_min": 1073741824, "pressure_samples": 3,
                   "disk_free_bytes_min": 2147483648, "resolver_bytes_max": 65536,
                   "resolver_rss_bytes_max": 536870912},
        "source_sha256": {**{name: digest(ROOT / name) for name in HELPERS},
                          **{"repo/" + name: digest(ROOT / "repo" / name) for name in SOURCES},
                          **{name: digest(ROOT / name) for name in FROZEN}},
        "runtime_sha256": {str(python): digest(python)},
        "minecraft_restoration": "forbidden",
        "service_restoration": "forbidden (no service is started or restored by this launch)",
    }
    (CONTROL / "launch-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({"campaign_sha256": plan["campaign_sha256"], "manifest_sha256": plan["manifest_sha256"],
                      "holds": holds}))


if __name__ == "__main__":
    main()
