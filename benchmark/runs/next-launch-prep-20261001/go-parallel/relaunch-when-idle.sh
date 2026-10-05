#!/bin/sh
# Run on Paris. Waits until both go-parallel queues have nothing in flight (3 reads, 20 s apart),
# then cancels, waits for the terminal guard, swaps in make-launch-plan.next.py and relaunches.
# Never interrupts an attempt: cancel is written only when nothing is running.
R=/home/ubuntu/keygen-full.eALj54bh/go-parallel-20261002
PY=/home/ubuntu/keygen-full.eALj54bh/runtime/bin/python3.11
TAG=${1:?launch attempt tag}
cd $R || exit 1
idle=0
while [ $idle -lt 3 ]; do
  n=$(python3 -c "
import json,glob
print(sum(len(json.load(open(p)).get('inflight') or {}) for p in glob.glob('results/*/queue-state.json')))")
  if [ "$n" = 0 ]; then idle=$((idle+1)); else idle=0; fi
  sleep 20
done
echo "operator: idle relaunch ($TAG)" > control/cancel.request
until python3 -c "import json,sys;sys.exit(json.load(open('control/terminal-guard-state.json')).get('status')!='COMPLETED')"; do sleep 10; done
cd control
A=launch-attempt-$TAG
mkdir -m 700 $A
for f in cancel.request supervisor-state.json terminal-guard-state.json runner-main.private.log runner-addon.private.log supervisor.private.log terminal-guard.private.log supervisor-metrics.jsonl owned-child-identities.json owned-child-cleanup.json terminal-boat-cleanup.json terminal-boat-cleanup terminal-archive-recovery-result.json; do
  [ -e $f ] && mv $f $A/
done
mv make-launch-plan.py $A/make-launch-plan.previous.py
mv make-launch-plan.next.py make-launch-plan.py
cd $R
$PY -I control/make-launch-plan.py > control/$A/make-launch-plan.out
umask 077
setsid -f $PY -I control/launch-driver.py supervise control/launch-plan.json > control/supervisor.private.log 2>&1 < /dev/null
sleep 5
SP=$(python3 -c "import json;print(json.load(open('control/supervisor-state.json'))['supervisor_pid'])")
setsid -f $PY -I control/terminal-guard.py control/launch-plan.json $SP > control/terminal-guard.private.log 2>&1 < /dev/null
sleep 4
python3 -c "import json;print(json.load(open('control/terminal-guard-state.json'))['guard_pid'])" > control/$A/new-guard-pid
