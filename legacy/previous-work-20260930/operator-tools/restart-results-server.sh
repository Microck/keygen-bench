#!/bin/bash
# Serve benchmark/runs (results page + media) on the tailscale address only.
# http-server supports byte ranges so video seeking works; python -m http.server does not.
for p in $(pgrep -f "http-server . -p 8480"); do kill $p 2>/dev/null; done
sleep 1
cd /home/ubuntu/workspace/keygen-benchmark/benchmark/runs
export PATH=/home/ubuntu/.nvm/versions/node/v24.13.0/bin:$PATH
nohup npx --yes http-server . -p 8480 -a 100.124.44.113 -s -c-1 > /home/ubuntu/cliproxyapi-keygen/tools/serve-results.log 2>&1 &
echo "started pid $!"
