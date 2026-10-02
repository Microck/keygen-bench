#!/usr/bin/env python3
"""Drain the Paris go-exclusive launch without interrupting an attempt, to relaunch it wider.

`go-drain.py ROOT` on Paris. Holds every lease lock of key OPENCODE_GO_API_KEY_3
(/tmp/keygen-benchmark-<uid>-resources/key-OPENCODE_GO_API_KEY_3-<i>.lock), taking each as soon as
its running attempt releases it, so neither queue can start another attempt. Once no queue under
ROOT/results has anything in flight (two reads 10 s apart), writes ROOT/control/cancel.request,
waits for the supervisor to finish, then releases the locks. Never signals a process.
"""
import fcntl
import glob
import json
import os
from pathlib import Path
import sys
import time

KEY = "OPENCODE_GO_API_KEY_3"


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


root = Path(sys.argv[1])
control = root / "control"
locks = Path(f"/tmp/keygen-benchmark-{os.getuid()}-resources")
handles = [open(path, "a") for path in sorted(glob.glob(str(locks / f"key-{KEY}-*.lock")))]
state = control / "go-drain-state.json"
held, quiet, cancelled, log = set(), 0, False, []


def save(phase):
    state.write_text(json.dumps({"phase": phase, "held": sorted(held), "locks": len(handles), "events": log}, indent=2))


save("holding")
while True:
    for index, handle in enumerate(handles):
        if index not in held:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.add(index)
                log.append({"at": time.time(), "event": "lock_held", "lock": index})
                save("holding")
            except BlockingIOError:
                pass
    supervisor = load(control / "supervisor-state.json") or {}
    if cancelled:
        if supervisor.get("finished_at"):
            break
    else:
        inflight = [name for path in glob.glob(str(root / "results/*/queue-state.json"))
                    for name in ((load(path) or {}).get("inflight") or {})]
        quiet = quiet + 1 if not inflight else 0
        if quiet >= 20:
            (control / "cancel.request").write_text("operator: relaunch Go with cheap models in parallel on key _3, "
                                                    "per user; nothing in flight\n")
            cancelled = True
            log.append({"at": time.time(), "event": "cancel_requested"})
            save("cancelled")
    time.sleep(0.5)
for index in sorted(held):
    fcntl.flock(handles[index], fcntl.LOCK_UN)
log.append({"at": time.time(), "event": "released"})
held.clear()
save("done")
