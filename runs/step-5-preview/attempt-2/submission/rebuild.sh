#!/bin/bash
cd /workspace
ft2 batch build/batch/setup.json >/dev/null 2>&1
for p in 0 1 2 3 4 5 6; do ft2 batch build/batch/pat$p.json >/dev/null 2>&1; done
ft2 call module_save '{"path":"submission/tune.xm","format":"xm"}'
