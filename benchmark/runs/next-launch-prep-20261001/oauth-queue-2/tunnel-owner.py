#!/usr/bin/env python3
"""Own the OAuth reverse tunnel (controller 127.0.0.1:8417 -> local CLIProxyAPI) for one campaign.

`tunnel-owner.py PLAN` starts the reverse forward as its own child, restarts it if it exits while
the campaign is live, and closes it once the remote terminal guard reports COMPLETED (or FAILED
after the supervisor finished). Only the tunnel PID plus start tick it spawned is ever signalled;
the shared bridge is never restarted or mutated. Logs hold ssh diagnostics only, never keys.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

CHECK = """import json,pathlib,sys
c=pathlib.Path(sys.argv[1])
def read(name):
    p=c/name
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except ValueError:
        return {}
g=read('terminal-guard-state.json').get('status')
s=read('supervisor-state.json')
print(json.dumps({'guard':g,'supervisor':s.get('status'),'supervisor_finished':'finished_at' in s}))
"""


def identity(pid):
    try:
        fields = Path('/proc/%s/stat' % pid).read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except (OSError, IndexError):
        return None


def main():
    plan_path = Path(sys.argv[1]).resolve()
    plan = json.loads(plan_path.read_text())
    state_path = plan_path.parent / 'tunnel-owner-state.json'
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    stop = False

    def request_stop(signum, frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    state = {'status': 'STARTING', 'owner_pid': os.getpid(), 'owner_start_ticks': identity(os.getpid()),
             'started_at': time.time(), 'restarts': [], 'forward': plan['forward'],
             'shared_bridge_mutated': False}

    def publish():
        temporary = state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=2) + '\n')
        temporary.replace(state_path)
    tunnel_command = ['ssh', '-N', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                      '-o', 'ConnectTimeout=15', '-o', 'ExitOnForwardFailure=yes',
                      '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=4',
                      '-R', plan['forward'], plan['host']]
    check_command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', plan['host'],
                     'python3', '-', plan['remote_control']]
    log = (plan_path.parent / 'tunnel-owner.private.log').open('ab')
    tunnel = None

    def spawn():
        nonlocal tunnel
        tunnel = subprocess.Popen(tunnel_command, stdin=subprocess.DEVNULL, stdout=log,
                                  stderr=subprocess.STDOUT, start_new_session=True)
        state.update(status='MONITORING', tunnel_pid=tunnel.pid, tunnel_start_ticks=identity(tunnel.pid),
                     tunnel_started_at=time.time())
        publish()
    spawn()
    deadline = time.monotonic() + plan['deadline_seconds']
    next_check = time.monotonic() + 60
    while not stop:
        if time.monotonic() >= deadline:
            state['stop_reason'] = 'owned_tunnel_deadline'
            break
        if tunnel.poll() is not None:
            state['restarts'].append({'at': time.time(), 'exited_pid': tunnel.pid,
                                      'returncode': tunnel.returncode})
            publish()
            time.sleep(10)
            spawn()
        if time.monotonic() >= next_check:
            next_check = time.monotonic() + 60
            try:
                result = subprocess.run(check_command, input=CHECK, text=True, capture_output=True, timeout=45)
                remote = json.loads(result.stdout) if result.returncode == 0 else None
            except (subprocess.TimeoutExpired, ValueError):
                remote = None
            state['last_check'] = {'at': time.time(), 'remote': remote}
            publish()
            if remote and (remote['guard'] == 'COMPLETED'
                           or (remote['guard'] == 'FAILED' and remote['supervisor_finished'])):
                state['stop_reason'] = 'owned_campaign_and_terminal_cleanup_finished'
                break
        time.sleep(2)
    if stop and 'stop_reason' not in state:
        state['stop_reason'] = 'authorized_owner_stop'
    if tunnel.poll() is None and identity(tunnel.pid) == state['tunnel_start_ticks']:
        tunnel.terminate()
        try:
            tunnel.wait(timeout=30)
        except subprocess.TimeoutExpired:
            tunnel.kill()
            tunnel.wait()
    state.update(status='CLOSED', finished_at=time.time(), tunnel_alive=False)
    publish()


if __name__ == '__main__':
    main()
