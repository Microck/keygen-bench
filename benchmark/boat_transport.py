"""Controller-only raw Docker transport. No API command/output encoding is involved."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import sys


def ssh_command(connection: dict, argv: list[str]) -> list[str]:
    """Keep every Docker argument one shell word; disable tunnels and credential forwarding."""
    if not argv or any("\x00" in word for word in argv):
        raise ValueError("a nonempty, NUL-free command is required")
    return [
        "ssh", "-F", "/dev/null", "-T", "-p", str(connection["port"]),
        "-i", connection["identity"],
        "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={connection['known_hosts']}",
        "-o", "GlobalKnownHostsFile=/dev/null", "-o", "ConnectTimeout=15",
        "-o", "ConnectionAttempts=1", "-o", "ServerAliveInterval=10",
        "-o", "ServerAliveCountMax=3", "-o", "ForwardAgent=no",
        "-o", "ClearAllForwardings=yes", "-o", "LogLevel=ERROR",
        f"{connection['user']}@{connection['host']}",
        "exec " + shlex.join(argv),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-config", type=Path, required=True)
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    # The prefix is private controller metadata, never mounted in an agent container.
    connection = json.loads(args.ssh_config.read_text())
    command = ssh_command(connection, ["docker", "--host", "unix:///var/run/docker.sock", *argv])
    # Replacing the helper makes caller deadlines terminate the SSH client itself.
    # A timeout does NOT establish that remote Docker/exec has stopped; caller must
    # freeze/export/remove its container, and the session must stop the VM.
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
