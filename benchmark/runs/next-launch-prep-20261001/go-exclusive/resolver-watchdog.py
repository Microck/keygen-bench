#!/usr/bin/env python3
"""Keep Paris systemd-resolved below the launch guard's resolver RSS bound during the go-exclusive launch.

usage: resolver-watchdog.py GUARD_PID

Same helper and rule as the go-three launch: Paris resolves boat.dev through a systemd-resolved <->
tailscaled forwarding loop, so resolved's RSS grows ~2.3 MB/min and the supervisor stops at 512 MiB.
Every 2 min this samples the RSS over SSH and, above THRESHOLD (400 MiB), restarts only
systemd-resolved (a stateless cache, back in <1 s). Nothing else on Paris is touched. It exits only
when the terminal guard with GUARD_PID reports a terminal state (the go-three watchdog exited at
start on a stale earlier guard state), or at the deadline. Log: resolver-watchdog.log (JSON lines).
"""
import json
from pathlib import Path
import subprocess
import sys
import time

HOST = "oracle-paris"
CONTROL = "/home/ubuntu/keygen-full.eALj54bh/go-exclusive-20261002/control"
THRESHOLD = 400 * 1024 * 1024
DEADLINE = time.monotonic() + 7 * 24 * 3600 + 3600
LOG = Path(__file__).resolve().parent / "resolver-watchdog.log"
PROBE = ("ps -C systemd-resolved -o rss= | awk '{s+=$1} END {print s*1024}'; "
         "python3 -c \"import json;s=json.load(open('" + CONTROL + "/terminal-guard-state.json'));"
         "print(s.get('guard_pid'), s.get('status'))\"")


def ssh(command):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, command],
                          capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL)


def log(**record):
    with LOG.open("a") as stream:
        stream.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}) + "\n")


def main():
    guard_pid = sys.argv[1]
    log(event="start", threshold_bytes=THRESHOLD, guard_pid=int(guard_pid))
    while time.monotonic() < DEADLINE:
        try:
            lines = ssh(PROBE).stdout.split()
            rss, pid, guard = int(lines[0]), lines[1] if len(lines) > 2 else None, lines[2] if len(lines) > 2 else None
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            log(event="probe_failed")
            time.sleep(120)
            continue
        if pid == guard_pid and guard in ("COMPLETED", "FAILED"):
            log(event="exit", reason="terminal guard " + guard, rss_bytes=rss)
            return
        if rss > THRESHOLD:
            restart = ssh("sudo -n systemctl restart systemd-resolved && sleep 2 && ps -C systemd-resolved -o rss= | awk '{s+=$1} END {print s*1024}'")
            log(event="restarted_systemd_resolved", rss_before_bytes=rss, returncode=restart.returncode,
                rss_after_bytes=restart.stdout.strip())
        time.sleep(120)
    log(event="exit", reason="deadline")


if __name__ == "__main__":
    main()
