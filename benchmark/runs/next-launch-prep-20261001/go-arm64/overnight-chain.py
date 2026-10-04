#!/usr/bin/env python3
"""Unattended Go run on Paris after the key-3 weekly reset (user 2026-10-04, asleep overnight).

1. Wait until START, then send one tiny request on OPENCODE_GO_API_KEY_3 every 10 minutes until it
   answers (give up after 12 h, recorded).
2. Phase A: the main arm64 queue with every Devin-available model and Hy4 Preview held, so only the
   OpenCode-Go-exclusive models run (user priority). It exits once nothing more can start.
3. Hy4: measure Go's real context limit and apply the matching fix (hy4_fix.py), then run it.
The Go models also available on Devin are NOT run (user 2026-10-04: wait until Hy4 is sorted).
Every step is recorded in chain-state.json and control/hy4/record.json.
"""
import calendar
import json
import os
from pathlib import Path
import subprocess
import sys
import time

P = Path("/home/ubuntu/keygen-full.eALj54bh")
ROOT = P / "go-arm64-20261005"
CONTROL = ROOT / "control"
PYTHON = str(P / "runtime/bin/python3.11")
START = calendar.timegm(time.strptime("2026-10-05T00:01:00", "%Y-%m-%dT%H:%M:%S"))  # UTC
DEVIN_AVAILABLE = ["go-deepseek-v4-pro", "go-deepseek-v4.1-flash", "go-glm-5.3-flash", "go-grok-4.6",
                   "go-grok-4.7", "go-kimi-k3"]
HELD_ALWAYS = ["go-hy4-preview"]
RUNS = {"main": ("repo-main", "next-max-tier-prompt-v2-go-arm64-20261005"),
        "addon": ("repo-addon", "next-max-tier-prompt-v2-paris-addon-go-arm64-20261005")}
STATE = CONTROL / "chain-state.json"
state = {"status": "WAITING", "pid": os.getpid(), "start_at": START, "steps": []}


def save(**update):
    state.update(update, updated_at=time.time())
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def environment():
    private = P / ".private/controller.env.json"
    if private.stat().st_mode & 0o077:
        raise SystemExit("private environment file permissions too broad")
    credentials = json.loads(private.read_text())
    env = {"PATH": str(Path(PYTHON).parent) + ":/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()),
           "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "KEYGEN_FT2_ANALYSIS": str(P / "analysis/ft2-analysis"), "LD_LIBRARY_PATH": str(P / "analysis/lib"),
           "RCLONE_CONFIG": str(P / ".private/rclone.conf"), "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}
    env.update({key: value for key, value in credentials.items() if isinstance(value, str)})
    return env


def probe(env):
    selection = json.loads((CONTROL / "go-arm64-main-selection.json").read_text())
    model = next(m for m in selection["models"] if m["id"] == "go-qwen3.7-plus-messages")
    sys.path.insert(0, str(ROOT / "repo-main/benchmark"))
    import run  # frozen engine's own probe: same request shape, headers and classification
    return run.probe_provider(model, env["OPENCODE_GO_API_KEY_3"])


def queue(name, holds, env):
    repo, campaign_id = RUNS[name]
    command = [PYTHON, "-I", "benchmark/run.py", "queue", "--campaign", str(CONTROL / f"go-arm64-{name}-campaign.json"),
               "--out", str(ROOT / "results" / campaign_id)]
    for model_id in holds:
        command += ["--hold", model_id]
    log = (CONTROL / f"queue-{name}.private.log").open("ab")
    return subprocess.Popen(command, cwd=ROOT / repo, env=env, stdout=log, stderr=subprocess.STDOUT)


def phase(label, runs, env):
    started = time.time()
    processes = {name: queue(name, holds, env) for name, holds in runs.items()}
    state["steps"].append({"phase": label, "started_at": started, "pids": {n: p.pid for n, p in processes.items()}})
    save(status=f"RUNNING_{label}")
    codes = {name: process.wait() for name, process in processes.items()}
    state["steps"][-1].update(finished_at=time.time(), returncodes=codes)
    save()
    return codes


def main():
    env = environment()
    save()
    while time.time() < START:
        time.sleep(30)
    deadline = time.time() + 12 * 3600
    while True:
        result = probe(env)
        state.setdefault("probes", []).append({"at": time.time(), "http_status": result.get("http_status"),
                                               "category": result.get("category")})
        save(status="PROBING")
        if result.get("category") == "ok":
            break
        if time.time() > deadline:
            save(status="FAILED", reason="key 3 did not recover within 12 h of START")
            return 1
        time.sleep(600)
    codes = phase("A_go_exclusive", {"main": DEVIN_AVAILABLE + HELD_ALWAYS}, env)
    if any(codes.values()):
        save(status="FAILED", reason=f"phase A queue exited {codes}")
        return 1
    sys.path.insert(0, str(CONTROL))
    import hy4_fix
    hy4_fix.HY4.mkdir(exist_ok=True)
    record = {"started_at": time.time()}
    save(status="HY4_MEASURING")
    record["outcome"] = outcome = hy4_fix.measure(env, record)
    (hy4_fix.HY4 / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    if outcome == "TOTAL_LIMIT":
        save(status="HY4_REQUALIFYING")
        process = hy4_fix.capped_campaign(env, record)
        (hy4_fix.HY4 / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        if process is None:
            save(status="FAILED", reason="Hy4 capped campaign did not qualify/compile/doctor; see hy4/record.json")
            return 1
        state["steps"].append({"phase": "hy4_cap32k", "started_at": time.time(), "pids": {"hy4": process.pid}})
        save(status="RUNNING_hy4_cap32k")
        code = process.wait()
        state["steps"][-1].update(finished_at=time.time(), returncodes={"hy4": code})
    elif outcome == "NOT_REPRODUCED":
        code = phase("hy4_unchanged", {"main": DEVIN_AVAILABLE}, env)["main"]
    else:
        save(status="COMPLETED", reason=f"Hy4 not run: {outcome} (see hy4/record.json)")
        return 0
    save(status="FAILED" if code else "COMPLETED", reason=f"Hy4 exit {code}" if code else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
