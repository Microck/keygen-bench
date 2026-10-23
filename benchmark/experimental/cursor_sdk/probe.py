"""Explicitly paid, unscored Cursor/mini transport diagnostic in offline Docker."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, help='Exact Cursor catalogue model ID')
    parser.add_argument('--image', required=True, help='Already-built immutable local Docker image sha256:...')
    parser.add_argument('--bridge-url', default='http://127.0.0.1:8320/v1')
    parser.add_argument('--out', type=Path, required=True, help='New private diagnostic JSON outside the checkout')
    parser.add_argument('--allow-credit-usage', action='store_true', help='Real model calls may spend credits; NOT a price cap')
    parser.add_argument('--accept-experimental-condition', action='store_true')
    args = parser.parse_args()
    if not args.allow_credit_usage or not args.accept_experimental_condition:
        parser.error('Both explicit consent flags are required; this is not a frozen benchmark run')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.image):
        parser.error('Use an immutable local image ID, not a tag')
    out = args.out.resolve()
    repo = Path(__file__).resolve().parents[3]
    if out.is_relative_to(repo) or out.exists():
        parser.error('Output must be a new private file outside the checkout')
    subprocess.run(['docker', 'image', 'inspect', args.image], check=True, stdout=subprocess.DEVNULL)
    os.environ['MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT'] = '1'
    os.environ['LITELLM_MODE'] = 'PRODUCTION'
    os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments.docker import DockerEnvironment
    from .model import CursorMiniModel, CONDITION
    model = CursorMiniModel(model_name=args.model, bridge_url=args.bridge_url,
                            allow_credit_usage=True, accept_experimental_condition=True)
    environment = None
    try:
        environment = DockerEnvironment(image=args.image, cwd='/workspace', executable='docker',
            env={}, forward_env=[], timeout=10, container_timeout='180s',
            run_args=['--rm', '--network', 'none', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                      '--memory', '1g', '--cpus', '1', '--pids-limit', '128'])
        agent = DefaultAgent(model, environment, cost_limit=0, step_limit=3, wall_time_limit_seconds=150,
            system_template='Use only the bash tool. This is a transport diagnostic, not a music benchmark. Do not access the network.',
            instance_template="First run printf 'KEYGEN_CURSOR_PILOT_OK'. After seeing its output, finish with printf 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\\npilot complete\\n'.")
        failure = None
        try:
            result = agent.run()
        except Exception as error:
            failure = error
            result = {'exit_status': type(error).__name__, 'submission': ''}
        record = agent.serialize()
        record['diagnostic'] = {'condition': CONDITION, 'eligible_submission': False,
                                'live_provider_verified': False, 'dollar_cost': None,
                                'result': result, 'image': args.image}
        out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(record, stream, indent=2)
        print('Private diagnostic saved. This is NOT model-identity, billing or fairness certification.')
        if failure:
            raise RuntimeError('Cursor diagnostic failed; inspect the private redacted receipt') from None
    finally:
        try:
            model.close()
        finally:
            if environment and environment.container_id:
                subprocess.run(['docker', 'rm', '-f', environment.container_id], check=False, capture_output=True)
                environment.container_id = None


if __name__ == '__main__':
    main()
