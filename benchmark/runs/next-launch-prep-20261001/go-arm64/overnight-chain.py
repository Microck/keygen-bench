#!/usr/bin/env python3
"""Unattended Go run on Paris after the key-3 weekly reset (user 2026-10-04, asleep overnight).

1. Wait until START, then send one tiny request on the Go key (KEY; key 4 since 2026-10-05) every 30 minutes until it
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
LAST = ["go-qwen3.8-max-messages"]  # smallest monthly allowance ($15), most attempts left: runs last
# User 2026-10-05: key 3 hit its monthly limit; continue on key 4 (follow-up go-key4 queues).
KEY = "OPENCODE_GO_API_KEY_4"
RUNS = {"main": ("repo-main", "next-max-tier-prompt-v2-go-key4-20261005"),
        "addon": ("repo-addon", "next-max-tier-prompt-v2-paris-addon-go-key4-20261005")}
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
    selection = json.loads((CONTROL / "go-key4-main-selection.json").read_text())
    model = next(m for m in selection["models"] if m["id"] == "go-qwen3.7-plus-messages")
    sys.path.insert(0, str(ROOT / "repo-main/benchmark"))
    import run  # frozen engine's own probe: same request shape, headers and classification
    return run.probe_provider(model, env[KEY])


def queue(name, holds, env):
    repo, campaign_id = RUNS[name]
    command = [PYTHON, "-I", "benchmark/run.py", "queue", "--campaign", str(CONTROL / f"go-key4-{name}-campaign.json"),
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
    deadline = time.time() + 35 * 24 * 3600  # monthly window: keep checking until it reopens
    while True:
        result = probe(env)
        state.setdefault("probes", []).append({"at": time.time(), "http_status": result.get("http_status"),
                                               "category": result.get("category")})
        state["probes"] = state["probes"][-50:]
        save(status="PROBING")
        if result.get("category") == "ok":
            break
        if time.time() > deadline:
            save(status="FAILED", reason="key 3 did not recover within 35 days")
            return 1
        time.sleep(1800)
    # User 2026-10-05: biggest monthly allowance first. $60/$30 Go-only models (and GLM-5.2, which
    # failed Devin qualification), then Hy4 ($30), then Qwen3.8 Max ($15) last. GLM-5.3 and the
    # other Devin-available models run on Devin and stay held here.
    codes = phase("A1_larger_allowance", {"main": DEVIN_AVAILABLE + HELD_ALWAYS + LAST,
                                          "addon": ["go-glm-5.3-chat"]}, env)
    if any(codes.values()):
        save(status="FAILED", reason=f"phase A1 queue exited {codes}")
        return 1
    sys.path.insert(0, str(CONTROL))
    import hy4_fix
    hy4_fix.HY4.mkdir(exist_ok=True)
    record = {"started_at": time.time()}
    save(status="HY4_MEASURING")
    record["outcome"] = outcome = hy4_fix.measure(env, record)
    (hy4_fix.HY4 / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    release_hy4 = False
    if outcome == "TOTAL_LIMIT":
        save(status="HY4_REQUALIFYING")
        process = hy4_fix.capped_campaign(env, record)
        (hy4_fix.HY4 / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        if process is None:
            state["hy4"] = "capped campaign did not qualify/compile/doctor; see hy4/record.json"
        else:
            state["steps"].append({"phase": "hy4_cap32k", "started_at": time.time(), "pids": {"hy4": process.pid}})
            save(status="RUNNING_hy4_cap32k")
            state["steps"][-1].update(finished_at=time.time(), returncodes={"hy4": process.wait()})
    elif outcome == "NOT_REPRODUCED":
        release_hy4 = True
    else:
        state["hy4"] = f"not run: {outcome} (see hy4/record.json)"
    holds = DEVIN_AVAILABLE + ([] if release_hy4 else HELD_ALWAYS)
    codes = phase("A2_qwen38max" + ("_and_hy4" if release_hy4 else ""), {"main": holds}, env)
    save(status="FAILED" if any(codes.values()) else "COMPLETED",
         reason=f"phase A2 queue exited {codes}" if any(codes.values()) else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
