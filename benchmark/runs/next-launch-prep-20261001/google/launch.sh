#!/bin/sh
# Run on Ashburn. Starts the frozen Google campaign: 6 Gemini models x 3 independent attempts,
# 6 at a time on shared Boat VMs (3 attempts per default VM), detached. Credentials come from
# the private controller env file.
set -eu
A=/home/ubuntu/keygen-full.OGHjBAkO
R=$A/google-20261003
OUT=$R/results/next-max-tier-prompt-v2-google-20261003
cd "$R/repo"
umask 077
setsid nohup "$A/runtime/bin/python3.11" -I - "$A" "$R" "$OUT" > "$R/control/run.private.log" 2>&1 <<'EOF' &
import json, os, sys
A, R, OUT = sys.argv[1:4]
env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.environ["HOME"], "LANG": "C.UTF-8",
       "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "RCLONE_CONFIG": A + "/.private/rclone.conf"}
env.update(json.load(open(A + "/.private/controller.env.json")))
# The FT2 analysis binary scores each attempt; same layout as the launch-driver plans.
env.update(KEYGEN_FT2_ANALYSIS=A + "/analysis/ft2-analysis", LD_LIBRARY_PATH=A + "/analysis/lib")
python = A + "/runtime/bin/python3.11"
os.execve(python, [python, "-I", "benchmark/run.py", "run", "--campaign", R + "/control/google-campaign-packed.json",
                   "--out", OUT], env)
EOF
echo "started pid $!; log $R/control/run.private.log"
