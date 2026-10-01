#!/usr/bin/env python3
"""Write launch-addon/launch-plan.json on Paris: frozen fingerprints of the deployed add-on.

Run on the controller after compile: `make-launch-plan.py` (no arguments, no credentials read).
"""
import hashlib
import json
from pathlib import Path

PARIS = Path("/home/ubuntu/keygen-full.eALj54bh")
ROOT = PARIS / "next-addon-20261001"
CONTROL = ROOT / "launch-addon"
CAMPAIGN_ID = "next-max-tier-prompt-v2-paris-addon-20261001"
HELPERS = ("launch-addon/archive-only.py", "launch-addon/launch-driver.py",
           "launch-addon/launch-status.py", "launch-addon/terminal-guard.py")
SOURCES = ("MODEL-TEST-PLAN.oauth-first.json", "benchmark/Dockerfile", "benchmark/__init__.py",
           "benchmark/artifacts.py", "benchmark/boat.py", "benchmark/boat_api.py",
           "benchmark/boat_transport.py", "benchmark/bridge.py", "benchmark/campaign.py",
           "benchmark/drive.py", "benchmark/native_models.py", "benchmark/native_readiness.py",
           "benchmark/prompts/system.txt", "benchmark/prompts/task.txt", "benchmark/report.py",
           "benchmark/report_page.py", "benchmark/requirements.txt", "benchmark/run.py",
           "benchmark/score.py", "benchmark/score_audio.py", "benchmark/score_loop.py",
           "benchmark/score_mix.py", "benchmark/score_playback.py", "benchmark/score_structure.py",
           "benchmark/visualize.sh", "benchmark/runs/next-launch-prep-20261001/tier-spec.json")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    campaign = CONTROL / "paris-addon-campaign.json"
    python = PARIS / "runtime/bin/python3.11"
    plan = {
        "schema": "keygen-launch-supervisor-plan-1",
        "campaign_id": CAMPAIGN_ID,
        "root": str(ROOT),
        "control": str(CONTROL),
        "helpers": "launch-addon/launch-driver.py",
        "python": str(python),
        "env_file": str(PARIS / ".private/controller.env.json"),
        "rclone_config": str(PARIS / ".private/rclone.conf"),
        "analysis": str(PARIS / "analysis"),
        "controller_lock": str(PARIS / "launch-control/controller.lock"),
        "pacing_roots": [str(PARIS / "results"), str(ROOT / "results")],
        "campaign": str(campaign),
        "campaign_sha256": digest(campaign),
        "manifest_sha256": json.loads(campaign.read_text())["sha256"],
        "out": str(ROOT / "results" / CAMPAIGN_ID),
        "workers": 3,
        # 3 models x up to 3 attempts over 3 workers; each attempt <= 7200 s wall plus evaluation.
        "deadline_seconds": 64800,
        "guards": {"sample_seconds": 15, "mem_available_bytes_min": 1073741824, "pressure_samples": 3,
                   "disk_free_bytes_min": 2147483648, "resolver_bytes_max": 65536,
                   "resolver_rss_bytes_max": 536870912},
        "source_sha256": {**{name: digest(ROOT / name) for name in HELPERS},
                          **{"repo/" + name: digest(ROOT / "repo" / name) for name in SOURCES}},
        "runtime_sha256": {str(python): digest(python)},
        "minecraft_restoration": "forbidden",
        "service_restoration": "forbidden (Paris: no service is started or restored by this launch)",
    }
    (CONTROL / "launch-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({"campaign_sha256": plan["campaign_sha256"], "manifest_sha256": plan["manifest_sha256"]}))


if __name__ == "__main__":
    main()
