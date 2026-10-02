#!/bin/sh
# Run on Paris. After the Muse relaunch (phase 2) is live, stage the phase-3 plan (costly Go-exclusive
# models released) and wait for the next idle point to relaunch with it.
C=/home/ubuntu/keygen-full.eALj54bh/go-parallel-20261002/control
until [ -s $C/launch-attempt-2-muse-release/new-guard-pid ]; do sleep 30; done
cp $C/make-launch-plan.next2.py $C/make-launch-plan.next.py
exec sh $C/relaunch-when-idle.sh 3-costly-release
