#!/bin/sh
# Run on Ashburn. The reset chain and bridge do not depend on the SSH client.
set -eu
A=/home/ubuntu/keygen-full.OGHjBAkO
R=$A/devin-20261004
umask 077
cd "$R/repo"
setsid nohup "$A/runtime/bin/python3.11" -I "$R/control/reset-chain.py" > "$R/control/chain.private.log" 2>&1 < /dev/null &
echo "Reset chain started with pid $!; status $R/control/status.json"
