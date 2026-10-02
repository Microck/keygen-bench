#!/usr/bin/env python3
"""Keep Paris systemd-resolved below the launch guard's resolver RSS bound during the go-three Go launch.

Paris resolves boat.dev through a systemd-resolved <-> tailscaled (100.100.100.100) forwarding loop
(~15k queries/s observed 2026-10-01 22:55 UTC), so resolved's RSS grows ~2.3 MB/min. The launch
guard stops the owned runner at 512 MiB. Every 120 s this checks the resolver RSS over SSH and,
above THRESHOLD, restarts only systemd-resolved (a stateless cache, back in <1 s). Nothing else on
Paris is touched. Exits after the go-three terminal guard reports a terminal state or the deadline.
Log: resolver-watchdog.log (JSON lines).
"""
import json
from pathlib import Path
import subprocess
import time

HOST = "oracle-paris"
CONTROL = "/home/ubuntu/keygen-full.eALj54bh/go-three-20261002/control"
THRESHOLD = 400 * 1024 * 1024
DEADLINE = time.monotonic() + 50 * 3600
LOG = Path(__file__).resolve().parent / "resolver-watchdog.log"
PROBE = ("ps -C systemd-resolved -o rss= | awk '{s+=$1} END {print s*1024}'; "
         "python3 -c \"import json;print(json.load(open('" + CONTROL + "/terminal-guard-state.json')).get('status'))\"")


def ssh(command):
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, command],
                          capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL)


def log(**record):
    with LOG.open("a") as stream:
        stream.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}) + "\n")


def main():
    log(event="start", threshold_bytes=THRESHOLD)
    while time.monotonic() < DEADLINE:
        try:
            result = ssh(PROBE)
            lines = result.stdout.split()
            rss, guard = int(lines[0]), lines[1] if len(lines) > 1 else None
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            log(event="probe_failed")
            time.sleep(120)
            continue
        if guard in ("COMPLETED", "FAILED"):
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
