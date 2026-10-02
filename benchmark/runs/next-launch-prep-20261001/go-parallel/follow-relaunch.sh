#!/bin/sh
# Local. Waits for relaunch-when-idle.sh on Paris to record the new guard PID, then moves the
# resolver watchdog to it.
TAG=${1:?tag}
D=$(dirname "$0")
F=/home/ubuntu/keygen-full.eALj54bh/go-parallel-20261002/control/launch-attempt-$TAG/new-guard-pid
until G=$(ssh -o BatchMode=yes -o ConnectTimeout=15 oracle-paris "cat $F 2>/dev/null") && [ -n "$G" ]; do sleep 30; done
pkill -f "[r]esolver-watchdog.py"
cd "$D" && setsid nohup python3 resolver-watchdog.py "$G" > /dev/null 2>&1 < /dev/null &
echo "watchdog moved to guard $G"
