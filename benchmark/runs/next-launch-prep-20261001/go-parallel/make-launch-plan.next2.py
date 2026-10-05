#!/usr/bin/env python3
"""Write control/launch-plan.json on Paris: frozen fingerprints of the deployed go-exclusive launch.

Run on the controller after both compiles: `make-launch-plan.py` (no arguments, no credentials
read). Two runners share one supervisor, one controller lock and the ONE Go key OPENCODE_GO_API_KEY_3
(user rule: one Go attempt at a time, only key _3, only the 12 Go-exclusive models):
- main:  follows the go-three main queue (17 Go routes), engine repo-main/ (native_models.py pinned
         to the main campaign's frozen source so every frozen readiness proof still verifies);
- addon: follows the Paris add-on queue (glm-5.2, glm-5.3, minimax-m2.7), engine repo-addon/
         (current native_models.py with the approved GLM history-key removal).
The 8 Devin-available Go models are deferred with `--hold` (ordinals stay pending, never probed or
started). `--key-gate-fresh-seconds 0` probes key _3 with one tiny request before every start.
"""
import hashlib
import json
from pathlib import Path

PARIS = Path("/home/ubuntu/keygen-full.eALj54bh")
ROOT = PARIS / "go-parallel-20261002"
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
# Held for later (available on Devin): never probed or started by this launch. go-hy4-preview is
# also held (Main, 16:48 UTC): its rep-1-retry-1 died on an empty gateway BadRequestError at ~142k
# prompt tokens after 83.5 min and the next probe on its route timed out, so it must not head the
# queue or burn another attempt; it runs, if at all, after every other model's attempts 1-3.
HOLDS = {"main": ["go-deepseek-v4-pro", "go-deepseek-v4.1-flash", "go-glm-5.3-flash", "go-grok-4.6",
                  "go-grok-4.7", "go-hy4-preview", "go-kimi-k3",
                  # Costlier Go-exclusive models released 2026-10-02 night (user: finish every Go model).
                  # Muse Spark (held 20:52Z on a workspace privacy 400) released 22:2xZ after the user
                  # enabled training-data endpoints for key _3; both answered 200.
                  ],
         "addon": ["go-glm-5.2-chat", "go-glm-5.3-chat"]}
RUNS = (("main", "repo-main", "next-max-tier-prompt-v2-go-parallel-20261002", "go-parallel-main-campaign.json"),
        ("addon", "repo-addon", "next-max-tier-prompt-v2-paris-addon-go-parallel-20261002",
         "go-parallel-addon-campaign.json"))
GO_KEYS = ["OPENCODE_GO_API_KEY_3"]
# Queue options: a usage-limited key is re-probed after 30 min (6 h for a weekly window, engine
# rule); other probe failures after 5 min; key _3 is probed before every start; no start may leave
# less than 10 h of Boat machine time after every running attempt's TTL.
QUEUE_ARGS = ["--probe-interval", "1800", "--retry-interval", "300", "--boat-reserve-seconds", "36000",
              "--key-gate-fresh-seconds", "0"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    python = PARIS / "runtime/bin/python3.11"
    runs, sources = [], {}
    for name, repo, campaign_id, manifest in RUNS:
        campaign = CONTROL / manifest
        config = json.loads(campaign.read_text())
        concurrency = config["campaign"]["concurrency"]
        if config["campaign"]["campaign_id"] != campaign_id:
            raise SystemExit(f"{manifest}: unexpected campaign ID")
        if (concurrency["key_pools"] != {"OPENCODE_GO_API_KEY": {"OPENCODE_GO_API_KEY_3": 3}}
                or concurrency["workers"] != 3 or concurrency["providers"]["go"] != 3):
            raise SystemExit(f"{manifest}: not the key-_3-only, three-worker pool")
        models = [model["id"] for model in config["campaign"]["models"]]
        if not set(HOLDS[name]) < set(models):
            raise SystemExit(f"{manifest}: held models missing")
        out = ROOT / "results" / campaign_id
        holds = [arg for model_id in HOLDS[name] for arg in ("--hold", model_id)]
        runs.append({"name": name, "repo": repo, "campaign_id": campaign_id, "campaign": str(campaign),
                     "campaign_sha256": digest(campaign), "manifest_sha256": config["sha256"],
                     "out": str(out), "workers": 3, "holds": HOLDS[name],
                     "runs_models": [model_id for model_id in models if model_id not in HOLDS[name]],
                     "command_args": ["queue", "--campaign", str(campaign), "--out", str(out),
                                      "--workers", "3", *QUEUE_ARGS, *holds]})
        sources.update({f"{repo}/{source}": digest(ROOT / repo / source) for source in SOURCES})
    plan = {
        "schema": "keygen-launch-supervisor-plan-2",
        "launch_id": "go-parallel-20261002",
        "root": str(ROOT),
        "control": str(CONTROL),
        "helpers": "control/launch-driver.py",
        "python": str(python),
        "env_file": str(PARIS / ".private/controller.env.json"),
        "rclone_config": str(PARIS / ".private/rclone.conf"),
        "analysis": str(PARIS / "analysis"),
        "controller_lock": str(PARIS / "launch-control/controller.lock"),
        "pacing_roots": [str(PARIS / "results"), str(PARIS / "next-addon-20261001/results"),
                         str(PARIS / "oauth-repeats-20261001/results"), str(PARIS / "go-three-20261002/results"), str(PARIS / "go-exclusive-20261002/results"),
                         str(ROOT / "results")],
        "go_keys": GO_KEYS,
        "runs": runs,
        # 32 queued Go-exclusive attempts, one at a time, plus 5-hour and weekly usage-window waits.
        "deadline_seconds": 604800,
        "archive_copy_timeout_seconds": 1800,
        "guards": {"sample_seconds": 15, "mem_available_bytes_min": 1073741824, "pressure_samples": 3,
                   "disk_free_bytes_min": 2147483648, "resolver_bytes_max": 65536,
                   "resolver_rss_bytes_max": 536870912},
        "source_sha256": {**{name: digest(ROOT / name) for name in HELPERS}, **sources,
                          **{f"control/{name}": digest(CONTROL / name) for name in
                             ("ashburn-campaign.json", "go-three-campaign.json", "paris-addon-campaign.json",
                              "go-exclusive-main-campaign.json", "go-exclusive-addon-campaign.json")}},
        "runtime_sha256": {str(python): digest(python)},
        "minecraft_restoration": "forbidden",
        "service_restoration": "forbidden (Paris: no service is started or restored by this launch)",
    }
    (CONTROL / "launch-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({run["name"]: {"campaign_sha256": run["campaign_sha256"], "manifest_sha256": run["manifest_sha256"],
                                    "holds": run["holds"], "runs_models": run["runs_models"]} for run in runs}))


if __name__ == "__main__":
    main()
