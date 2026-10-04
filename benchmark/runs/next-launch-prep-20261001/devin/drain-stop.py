#!/usr/bin/env python3
"""Stop the Devin campaign after its in-flight attempts finish, without interrupting any attempt.

User decision 2026-10-04: models with a Go route wait for Go quota instead of running on Devin.
`drain-stop.py RESULTS_DIR RUN_PID` on Ashburn:
1. takes each devin provider slot lock (RESULTS_DIR/.resource-locks/devin-<i>.lock, acquired by
   run.run_one BEFORE any Boat VM or model request) as soon as it is free, and holds it, so no new
   attempt can start;
2. once every slot is held (nothing in flight), sends SIGTERM to RUN_PID (verified as this
   campaign's run.py) and releases the locks: a sequence waiting for a slot then records its
   attempt INTERRUPTED (infra) before any VM or request.
Writes drain-state.json beside this script. Never touches Boat, the bridge or another campaign.
"""
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
STATE = HERE / "drain-state.json"


def save(**state):
    STATE.write_text(json.dumps({"at": time.time(), **state}, indent=2) + "\n")


def main():
    results, pid = Path(sys.argv[1]), int(sys.argv[2])
    command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
    if "benchmark/run.py run" not in command or "devin-20261004" not in command:
        raise SystemExit("PID is not this Devin campaign's run.py")
    locks = sorted((results / ".resource-locks").glob("devin-*.lock"))
    handles, held = [path.open("a") for path in locks], set()
    save(phase="holding", held=[], slots=len(locks))
    while len(held) < len(handles):
        for index, handle in enumerate(handles):
            if index in held:
                continue
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.add(index)
                save(phase="holding", held=sorted(held), slots=len(locks))
            except BlockingIOError:
                pass
        time.sleep(1)
    time.sleep(10)  # a sequence that was between slots is now blocked inside slot()
    os.kill(pid, signal.SIGTERM)
    save(phase="terminated", held=sorted(held), slots=len(locks), pid=pid)
    time.sleep(5)
    for handle in handles:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()
    for _ in range(600):
        if not Path(f"/proc/{pid}").exists():
            break
        time.sleep(1)
    save(phase="done", run_exited=not Path(f"/proc/{pid}").exists(), pid=pid)


if __name__ == "__main__":
    main()
