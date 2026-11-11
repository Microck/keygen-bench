#!/usr/bin/env python3
"""Offline comparison with the authoritative Python sandbox command construction."""
import ast
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[3]
source = (root / 'benchmark' / 'run.py').read_text()
module = ast.parse(source)
function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'start_container')
# Extract the function rather than importing provider SDKs or executing a campaign.
code = compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(root / 'benchmark' / 'run.py'), 'exec')
commands = []
class Result:
    returncode = 0

def shell(args, **kwargs):
    commands.append(args)
    return Result()

ns = {'shell': shell}
exec(code, ns)
ns['start_container'](['docker', '--host', 'unix:///var/run/docker.sock'], 'sha256:fixture', 'fixture')
helper = next(c[1:] for c in commands if 'create' in c and 'fixture-files' in c and 'container' not in c)
agent = next(c[1:] for c in commands if 'create' in c and 'fixture' in c and 'fixture-files' not in c and 'volume' not in c)
if len(sys.argv) < 2:
    raise SystemExit('usage: test_parity.py BEND [compiler-prefix-args ...]')
out = subprocess.check_output([*sys.argv[1:], str(root / 'benchmark/experimental/bend2/sandbox.bend')], text=True)
first, second = out.strip().split('\n---\n')
assert first.splitlines() == helper, (first.splitlines(), helper)
assert second.splitlines() == agent, (second.splitlines(), agent)
print('sandbox create argv matches Python for synthetic fixture')
