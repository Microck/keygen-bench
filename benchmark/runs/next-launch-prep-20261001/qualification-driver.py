#!/usr/bin/env python3
"""Run one qualification phase (long-generation probes or readiness pilots) on a controller.

Each item is an isolated `native_readiness.py` subprocess with only its provider's credential.
Provider concurrency is bounded; Go items draw one member of the four-key pool per item and
bind it to the spec's declared OPENCODE_GO_API_KEY name. Never prints credential values.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

PROVIDER_KEY = {"codex_oauth": "CODEX_BRIDGE_API_KEY", "anthropic_oauth": "ANTHROPIC_BRIDGE_API_KEY",
                "nim": "NVIDIA_NIM_API_KEY", "google": "GEMINI_API_KEY", "devin": "DEVIN_BRIDGE_API_KEY"}


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def main():
    plan = json.loads(Path(sys.argv[1]).read_text())
    control = Path(plan["control"])
    private = Path(plan["env_file"])
    if private.stat().st_mode & 0o077:
        raise SystemExit("private environment file permissions too broad")
    credentials = json.loads(private.read_text())
    base = {"PATH": str(Path(plan["python"]).parent) + ":/usr/local/bin:/usr/bin:/bin",
            "HOME": str(Path.home()), "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1",
            "XDG_RUNTIME_DIR": "/run/user/%s" % os.getuid()}
    limits = {name: threading.BoundedSemaphore(n) for name, n in plan["concurrency"].items()}
    pool_lock = threading.Lock()
    pool_use = {name: 0 for name in plan["go_pool"]}
    lock = threading.Lock()
    results = []
    label = plan["label"]
    state_path = control / (label + "-state.json")
    events = control / (label + "-events.jsonl")
    (control / "logs").mkdir(exist_ok=True)

    def event(**record):
        with lock, events.open("a") as stream:
            stream.write(json.dumps({"at": time.time(), **record}) + "\n")

    def acquire_go():
        while True:
            with pool_lock:
                name = min(pool_use, key=lambda key: pool_use[key])
                if pool_use[name] < plan["go_per_key"]:
                    pool_use[name] += 1
                    return name
            time.sleep(1)

    def one(item):
        provider = item["provider"]
        with limits[provider]:
            env = dict(base)
            member = None
            if provider == "go":
                member = acquire_go()
                env["OPENCODE_GO_API_KEY"] = credentials[member]
            else:
                env[PROVIDER_KEY[provider]] = credentials[PROVIDER_KEY[provider]]
            command = [plan["python"], "-I", plan["readiness"], "--spec", item["spec"], "--out", item["out"]]
            if item.get("probe"):
                command += ["--probe", "long-generation"]
            if provider in {"codex_oauth", "anthropic_oauth", "devin"}:
                command += ["--bridge-executable", plan["bridge"]]
            started = time.time()
            event(event="start", id=item["id"], key_member=member)
            code = None
            try:
                with (control / "logs" / (label + "-" + item["id"] + ".log")).open("wb") as log:
                    proc = subprocess.run(command, env=env, cwd=plan["control"], stdout=log,
                                          stderr=subprocess.STDOUT, timeout=item["timeout"])
                code = proc.returncode
                error = None
            except subprocess.TimeoutExpired:
                error = "controller_timeout"
            except Exception as exc:
                error = type(exc).__name__
            finally:
                if member is not None:
                    with pool_lock:
                        pool_use[member] -= 1
        row = {"id": item["id"], "provider": provider, "returncode": code, "driver_error": error,
               "key_member": member, "started_at": started, "finished_at": time.time(),
               "out": item["out"], "probe": bool(item.get("probe"))}
        out = Path(item["out"])
        try:
            if item.get("probe"):
                probe = json.loads((out / "probe.json").read_text())
                row["outcome"] = probe["outcome"]
            else:
                readiness = json.loads((out / "readiness.json").read_text())
                row["status"] = readiness["status"]
            transport = out / "transport.jsonl"
            if transport.exists():
                # run.bound_content_filter records one content_filter_block per blocked send.
                row["content_filter_blocks"] = sum(json.loads(line).get("event") == "content_filter_block"
                                                   for line in transport.read_text().splitlines())
        except (OSError, ValueError, KeyError) as exc:
            row["result_read_error"] = type(exc).__name__
        event(event="finish", **row)
        with lock:
            results.append(row)
            save(control / (label + "-summary.json"), {"label": label, "results": results})
        return row

    save(state_path, {"status": "RUNNING", "pid": os.getpid(), "started_at": time.time(),
                      "items": len(plan["items"])})
    with ThreadPoolExecutor(max_workers=len(plan["items"])) as executor:
        list(executor.map(one, plan["items"]))
    save(state_path, {"status": "COMPLETED", "pid": os.getpid(), "finished_at": time.time(),
                      "items": len(plan["items"]), "results": len(results)})


if __name__ == "__main__":
    main()
