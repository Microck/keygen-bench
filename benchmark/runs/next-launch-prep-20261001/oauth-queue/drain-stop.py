#!/usr/bin/env python3
"""Drain an OAuth rerun queue without interrupting a model attempt, so it can be relaunched wider.

`drain-stop.py PLAN` on the controller, beside the running queue:
1. immediately takes each anthropic_oauth provider slot lock (results/.resource-locks/anthropic_oauth-<i>.lock,
   which run.run_one acquires BEFORE any Boat VM or model request) as soon as it is free, and holds it;
   an attempt the queue admits meanwhile stays RESERVED inside slot(): no VM, no request;
2. once every in-flight attempt is such a blocked RESERVED attempt (or nothing is in flight), on reads
   10 s apart, writes control/cancel.request;
3. after the supervisor reports it stopped, releases the locks: a blocked attempt then acquires its slot,
   sees STOP and records INTERRUPTED (infra) before any VM or request.
Codex attempts are never blocked. Never signals a process; never touches Boat, the bridge or another campaign.
"""
import fcntl
import json
from pathlib import Path
import sys
import time


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def main():
    plan = load(sys.argv[1])
    control, out = Path(plan["control"]), Path(plan["out"])
    config = load(plan["campaign"])["campaign"]
    count = config["concurrency"]["providers"]["anthropic_oauth"]
    state_path = control / "drain-stop-state.json"
    record = {"phase": "holding", "started_at": time.time(), "held": [], "events": []}

    def save(**update):
        record.update(update)
        state_path.write_text(json.dumps(record, indent=2) + "\n")

    def note(event, **fields):
        record["events"].append({"at": time.time(), "event": event, **fields})
        save()

    save()
    handles = [(out / ".resource-locks" / f"anthropic_oauth-{index}.lock").open("a") for index in range(count)]
    held, quiet, cancelled = set(), 0, False
    while True:
        for index, handle in enumerate(handles):
            if index in held:
                continue
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.add(index)
                note("slot_held", slot=index)
                save(held=sorted(held))
            except BlockingIOError:
                pass
        if not cancelled:
            state = load(out / "queue-state.json") or {}
            if state.get("status") != "RUNNING":
                note("queue_not_running", status=state.get("status"))
                break
            inflight = state.get("inflight") or []
            blocked = all((load(out / name / "status.json") or {}).get("status") == "RESERVED"
                          and not (out / name / "transport").exists() for name in inflight)
            quiet = quiet + 1 if blocked else 0
            if quiet >= 200:
                (control / "cancel.request").write_text("operator: drain to relaunch with higher anthropic concurrency "
                                                        "and Fable released, per user; nothing running in flight\n")
                cancelled = True
                note("cancel_requested", inflight=inflight)
        else:
            supervisor = load(control / "supervisor-state.json") or {}
            if supervisor.get("status") != "RUNNING" or supervisor.get("finished_at"):
                break
        time.sleep(0.05)
    time.sleep(3)
    for index in sorted(held):
        fcntl.flock(handles[index], fcntl.LOCK_UN)
    note("slots_released")
    while not (load(control / "supervisor-state.json") or {}).get("finished_at"):
        time.sleep(2)
    note("supervisor_finished")
    save(phase="done")


if __name__ == "__main__":
    main()
