#!/usr/bin/env python3
"""Write control/launch-plan.json on Paris: frozen fingerprints of the deployed go-three launch.

Run on the controller after both compiles: `make-launch-plan.py` (no arguments, no credentials
read). Two runners share one supervisor, one controller lock and the four Go keys:
- main:  the 17 main-campaign Go routes, engine repo-main/ (native_models.py pinned to the main
         campaign's frozen source so every frozen readiness proof still verifies);
- addon: glm-5.2, glm-5.3 and minimax-m2.7, engine repo-addon/ (current native_models.py with the
         approved GLM history-key removal their proofs were made with).
"""
import hashlib
import json
from pathlib import Path

PARIS = Path("/home/ubuntu/keygen-full.eALj54bh")
ROOT = PARIS / "go-three-20261002"
CONTROL = ROOT / "control"
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
RUNS = (("main", "repo-main", "next-max-tier-prompt-v2-go-three-20261002", "go-three-campaign.json"),
        ("addon", "repo-addon", "next-max-tier-prompt-v2-paris-addon-20261001", "paris-addon-campaign.json"))
GO_KEYS = ["OPENCODE_GO_API_KEY", "OPENCODE_GO_API_KEY_1", "OPENCODE_GO_API_KEY_2", "OPENCODE_GO_API_KEY_3"]
# Queue options: a usage-limited key is re-probed every 30 min; other probe failures after 5 min;
# no start may leave less than 10 h of Boat machine time after every running attempt's TTL.
QUEUE_ARGS = ["--probe-interval", "1800", "--retry-interval", "300", "--boat-reserve-seconds", "36000"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    python = PARIS / "runtime/bin/python3.11"
    runs, sources = [], {}
    for name, repo, campaign_id, manifest in RUNS:
        campaign = CONTROL / manifest
        config = json.loads(campaign.read_text())
        if config["campaign"]["campaign_id"] != campaign_id:
            raise SystemExit(f"{manifest}: unexpected campaign ID")
        if sorted(config["campaign"]["concurrency"]["key_pools"]["OPENCODE_GO_API_KEY"]) != GO_KEYS:
            raise SystemExit(f"{manifest}: key pool differs from the four Go keys")
        out = ROOT / "results" / campaign_id
        workers = config["campaign"]["concurrency"]["workers"]
        runs.append({"name": name, "repo": repo, "campaign_id": campaign_id, "campaign": str(campaign),
                     "campaign_sha256": digest(campaign), "manifest_sha256": config["sha256"],
                     "out": str(out), "workers": workers,
                     "command_args": ["queue", "--campaign", str(campaign), "--out", str(out),
                                      "--workers", str(workers), *QUEUE_ARGS]})
        sources.update({f"{repo}/{source}": digest(ROOT / repo / source) for source in SOURCES})
    plan = {
        "schema": "keygen-launch-supervisor-plan-2",
        "launch_id": "go-three-20261002",
        "root": str(ROOT),
        "control": str(CONTROL),
        "helpers": "control/launch-driver.py",
        "python": str(python),
        "env_file": str(PARIS / ".private/controller.env.json"),
        "rclone_config": str(PARIS / ".private/rclone.conf"),
        "analysis": str(PARIS / "analysis"),
        "controller_lock": str(PARIS / "launch-control/controller.lock"),
        "pacing_roots": [str(PARIS / "results"), str(PARIS / "next-addon-20261001/results"),
                         str(PARIS / "oauth-repeats-20261001/results"), str(ROOT / "results")],
        "go_keys": GO_KEYS,
        "runs": runs,
        # 55 queued Go attempts over 4 keys (one attempt per key), plus usage-window waits.
        "deadline_seconds": 172800,
        "archive_copy_timeout_seconds": 1800,
        "guards": {"sample_seconds": 15, "mem_available_bytes_min": 1073741824, "pressure_samples": 3,
                   "disk_free_bytes_min": 2147483648, "resolver_bytes_max": 65536,
                   "resolver_rss_bytes_max": 536870912},
        "source_sha256": {**{name: digest(ROOT / name) for name in HELPERS}, **sources,
                          "control/ashburn-campaign.json": digest(CONTROL / "ashburn-campaign.json")},
        "runtime_sha256": {str(python): digest(python)},
        "minecraft_restoration": "forbidden",
        "service_restoration": "forbidden (Paris: no service is started or restored by this launch)",
    }
    (CONTROL / "launch-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({run["name"]: {"campaign_sha256": run["campaign_sha256"], "manifest_sha256": run["manifest_sha256"]}
                      for run in runs}))


if __name__ == "__main__":
    main()
