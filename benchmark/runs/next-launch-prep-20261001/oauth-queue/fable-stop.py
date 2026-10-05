#!/usr/bin/env python3
"""Stop the first OAuth queue without interrupting a model attempt, deferring Fable rep 3.

`fable-stop.py PLAN` on the controller, beside the running queue:
1. waits until every non-Fable anthropic_oauth rep-2 ordinal has started (queue-state.json), then 1 s;
2. takes each anthropic_oauth provider slot lock (results/.resource-locks/anthropic_oauth-<i>.lock,
   the lock run.run_one acquires BEFORE any Boat VM or model request) as soon as it is free and holds
   it, so a Fable attempt the queue admits stays RESERVED inside slot(): no VM, no request;
3. once the queue's in-flight set holds only such blocked Fable attempts (or nothing), on two reads
   10 s apart, writes control/cancel.request;
4. after the supervisor reports STOPPING (runner SIGTERMed, STOP set), releases the locks: a blocked
   attempt then acquires its slot, sees STOP and records INTERRUPTED (infra) before any VM/request.
Never signals a process and never touches Boat, the bridge or another campaign.
"""
import fcntl
import json
from pathlib import Path
import sys
import time

FABLE = ("anthropic_oauth-claude-fable-5", "anthropic_oauth-claude-fable-5-1")


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
    state_path = control / "fable-stop-state.json"
    record = {"phase": "waiting_for_rep2_starts", "started_at": time.time(), "held": [], "events": []}

    def save(**update):
        record.update(update)
        state_path.write_text(json.dumps(record, indent=2) + "\n")

    def note(event, **fields):
        record["events"].append({"at": time.time(), "event": event, **fields})
        save()

    save()
    while True:
        state = load(out / "queue-state.json") or {}
        if state.get("status") != "RUNNING":
            note("queue_not_running", status=state.get("status"))
            return
        ordinals = state.get("ordinals") or []
        if any(item["model_id"] in FABLE and item["state"] != "next" for item in ordinals):
            note("fable_already_admitted_before_hold")  # still hold: blocks it if it waits for a slot
            break
        if not [item for item in ordinals if item["model_id"].startswith("anthropic_oauth")
                and item["model_id"] not in FABLE and item["repetition"] == 2 and item["state"] == "next"]:
            note("all_non_fable_rep2_started")
            break
        time.sleep(2)
    time.sleep(1.0)
    save(phase="holding")
    handles = [(out / ".resource-locks" / f"anthropic_oauth-{index}.lock").open("a") for index in range(count)]
    held = set()
    quiet = 0
    cancelled = False
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
            inflight = state.get("inflight") or []
            blocked = all(any(name.startswith(model + "-rep-3") for model in FABLE)
                          and (load(out / name / "status.json") or {}).get("status") == "RESERVED"
                          and not (out / name / "transport").exists() for name in inflight)
            quiet = quiet + 1 if blocked and state.get("status") == "RUNNING" else 0
            if quiet >= 200:  # two consistent reads 10 s apart at 0.05 s polling
                (control / "cancel.request").write_text("operator: defer claude-fable-5/fable-5-1 rep 3 per user; "
                                                        "nothing else in flight; follow-up queue holds Fable\n")
                cancelled = True
                note("cancel_requested", inflight=inflight)
        else:
            supervisor = load(control / "supervisor-state.json") or {}
            if supervisor.get("status") != "RUNNING" or supervisor.get("finished_at"):
                time.sleep(3)
                for index in sorted(held):
                    fcntl.flock(handles[index], fcntl.LOCK_UN)
                note("slots_released", supervisor=supervisor.get("status"))
                save(phase="released", held=[])
                while not (load(control / "supervisor-state.json") or {}).get("finished_at"):
                    time.sleep(2)
                note("supervisor_finished")
                save(phase="done")
                return
        time.sleep(0.05)


if __name__ == "__main__":
    main()
