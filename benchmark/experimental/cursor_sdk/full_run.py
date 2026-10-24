"""Three private, scored Cursor/mini attempts; never a frozen/ranked submission."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'benchmark'))
sys.path.insert(0, str(REPO / 'benchmark/contrib'))
from validate_bundle import LIMITS, contract
import campaign

CONDITION = 'cursor-sdk-experimental-not-frozen'
ATTEMPTS = ('attempt-1', 'attempt-2', 'attempt-3')


def write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
    temporary.replace(path)


def configuration():
    return {'limits': dict(LIMITS), 'prompts': campaign.prompt_manifest(LIMITS),
            'storage': {'reserve_bytes': 1024**3, 'peak_bytes_per_attempt': 2 * 1024**3}}


def experiment(model, effort=None):
    return {'condition': CONDITION, 'model': model, 'requested_effort': effort,
            'model_identity': 'requested-only-unverified', 'frozen_eligible': False,
            'leaderboard_eligible': False, 'cost_known': False, 'dollar_cost': None,
            'sdk_version': '1.0.40', 'attempts': 3, 'automatic_retries': False,
            'differences': ['Cursor upstream agent loop and MCP wrapping remain',
                            'Effective upstream prompt/tool equivalence is unverified',
                            'Output and sampling controls use provider defaults',
                            'No dollar cap or reliable provider billing measurement',
                            '8 MiB bridge request-body limit; no silent history truncation']}


def private_path(value):
    path = Path(value)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Use an absolute private directory without symlink components')
    path = path.resolve()
    if path == REPO or REPO in path.parents or path.exists():
        raise ValueError('Use a NEW private directory outside the checkout; attempts are never overwritten')
    return path


def child_environment(home, extra=None):
    # No unrelated provider keys, user config, PYTHONPATH, NODE_OPTIONS or shell startup.
    env = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'LANG', 'LC_ALL',
           'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS') if key in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), XDG_CONFIG_HOME=str(home / 'config'),
               XDG_DATA_HOME=str(home / 'data'), XDG_CACHE_HOME=str(home / 'cache'),
               MSWEA_GLOBAL_CONFIG_DIR=str(home / 'mini'), MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT='1',
               LITELLM_LOCAL_MODEL_COST_MAP='True', LITELLM_MODE='PRODUCTION', NO_PROXY='127.0.0.1,localhost')
    env.update(extra or {})
    return env


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)


def preflight(args, config):
    """Finish all offline prerequisites before starting any Cursor inference."""
    import run
    import score
    from score_playback import renderer_identity
    from artifacts import ArtifactStore
    if importlib.metadata.version('mini-swe-agent') != run.MINI_VERSION:
        raise ValueError('Install the pinned benchmark requirements')
    docker = run.docker_command()
    image = json.loads(run.shell(docker + ['image', 'inspect', args.agent_image]).stdout)[0]
    base = json.loads(run.shell(docker + ['image', 'inspect', contract()['base_image']]).stdout)[0]
    if image['RootFS']['Layers'][:len(base['RootFS']['Layers'])] != base['RootFS']['Layers']:
        raise ValueError('Agent image must descend from the benchmark pinned base')
    if image['Id'] != args.agent_image:
        raise ValueError('Agent image must be supplied by immutable sha256 ID')
    if not (HERE / 'node_modules/@cursor/sdk/package.json').is_file():
        raise ValueError('Run npm ci --ignore-scripts in benchmark/experimental/cursor_sdk')
    sdk = json.loads((HERE / 'node_modules/@cursor/sdk/package.json').read_text())
    if sdk['version'] != '1.0.40':
        raise ValueError('Cursor SDK version mismatch')
    subprocess.run(['node', '--check', str(HERE / 'server.mjs')], check=True, capture_output=True)
    identity = renderer_identity()
    listener = score.listener_identity()
    capacity = ArtifactStore(config['storage']).preflight(args.work, 3)
    return docker, {'image': image['Id'], 'architecture': image['Architecture'],
                    'analysis_renderer': identity, 'listener': listener, 'storage': capacity}


def worker(spec_path):
    """Separate mini process: the upstream Cursor credential must not enter here."""
    import run
    from minisweagent.agents.default import DefaultAgent
    from benchmark.experimental.cursor_sdk.model import CursorMiniModel
    spec_path = Path(spec_path)
    spec = json.loads(spec_path.read_text())
    directory, config = spec_path.parent, spec['config']
    token = os.environ['KEYGEN_CURSOR_BRIDGE_TOKEN']
    model = None
    agent = None
    result = {'exit_status': 'WorkerNotStarted', 'failure_category': 'INFRA'}
    try:
        model = CursorMiniModel(model_name=spec['model'], bridge_url=spec['bridge_url'],
                                request_timeout_seconds=config['limits']['request_seconds'],
                                allow_credit_usage=True, accept_experimental_condition=True)
        agent = DefaultAgent(model, run.Sandbox(spec['docker'], spec['container'], config['limits']['command_seconds']),
                             system_template='{{ frozen_system }}', instance_template='{{ task }}',
                             step_limit=config['limits']['steps'], cost_limit=0,
                             wall_time_limit_seconds=config['limits']['wall_seconds'],
                             max_consecutive_format_errors=1,
                             output_path=directory / 'mini-home/trajectory.private.json')
        result = agent.run(task=config['prompts']['task'], frozen_system=config['prompts']['system'])
        if result.get('exit_status') not in {'Submitted', 'LimitsExceeded', 'TimeExceeded', 'Terminated', 'FormatError', 'RepeatedFormatError'}:
            result['failure_category'] = 'INFRA'
    except Exception as error:
        result = {'exit_status': type(error).__name__, 'failure_category': 'INFRA'}
    finally:
        if agent is not None:
            write_json(directory / 'trajectory.json', run.redact_credentials(agent.serialize(), [token]))
        write_json(directory / 'worker-result.json', run.redact_credentials(result, [token]))
        if model is not None:
            try:
                model.close()
            except Exception:
                pass  # Parent owns process termination and records cleanup separately.


def start_bridge(directory, model, effort, token, cursor_key):
    home = directory / 'bridge-home'
    home.mkdir(mode=0o700)
    ready = directory / 'bridge-ready.json'
    command = ['node', str(HERE / 'server.mjs'), '--model', model, '--port', '0',
               '--ready-file', str(ready), '--request-timeout-seconds', str(LIMITS['request_seconds']),
               '--allow-credit-usage', '--accept-experimental-condition']
    if effort:
        command += ['--effort', effort]
    process = subprocess.Popen(command, cwd=home, start_new_session=True,
        env=child_environment(home, {'CURSOR_API_KEY': cursor_key, 'KEYGEN_CURSOR_BRIDGE_TOKEN': token,
                                     'KEYGEN_CURSOR_ISOLATED_HOME': '1'}),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Cursor bridge startup failed; no fallback attempted')
            if ready.exists():
                try:
                    info = json.loads(ready.read_text())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    time.sleep(0.05)
                    continue
                port = info['port']
                if type(port) is not int or not 1024 <= port <= 65535:
                    raise ValueError('Invalid bridge readiness port')
                return process, f'http://127.0.0.1:{port}/v1'
            time.sleep(0.05)
        raise TimeoutError('Cursor bridge did not become ready')
    except BaseException:
        stop_process(process)
        raise


def score_experiment(directory):
    """Use the trusted scorer, then separate artifact evaluation from route eligibility."""
    # NumPy memory-mapped captures load this stdlib DSO lazily. Initialize it
    # before the scorer fingerprints loaded libraries; do not bypass its guard.
    import mmap  # noqa: F401
    import score
    profile = score.profile_attempt(directory, force=True)
    if profile is None:
        return None
    profile['artifact_evaluation_eligible'] = profile.get('eligible', False)
    profile.update(eligible=False, frozen_eligible=False, leaderboard_eligible=False,
                   experimental_condition=CONDITION)
    write_json(directory / 'profile.json', profile)
    location = profile.get('evaluation_location')
    if location:
        write_json(directory / location / 'profile.json', profile)
    return profile


def run_attempt(directory, args, config, docker, cursor_key):
    import run
    started = time.monotonic()
    container = 'keygen-cursor-' + uuid.uuid4().hex[:16]
    bridge = process = None
    status = {'status': 'RUNNING', 'attempt_id': directory.name, 'model': {'model': args.model},
              'eligible': False, 'experiment': experiment(args.model, args.effort),
              'collection': 'not_attempted', 'render': 'not_attempted', 'failure_category': None}
    write_json(directory / 'status.json', status)
    try:
        from artifacts import ArtifactStore
        ArtifactStore(config['storage']).preflight(directory, 1)
        run.start_container(docker, args.agent_image, container)
        token = secrets.token_urlsafe(32)
        bridge, url = start_bridge(directory, args.model, args.effort, token, cursor_key)
        home = directory / 'mini-home'
        home.mkdir(mode=0o700)
        spec = {'model': args.model, 'config': config, 'docker': docker, 'container': container, 'bridge_url': url,
                'experiment': experiment(args.model, args.effort)}
        write_json(directory / 'spec.json', spec)
        process = subprocess.Popen([sys.executable, '-I', str(HERE / 'full_run.py'), '--worker', str(directory / 'spec.json')],
                    cwd=home, env=child_environment(home, {'KEYGEN_CURSOR_BRIDGE_TOKEN': token}),
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            process.wait(timeout=config['limits']['wall_seconds'])
        except subprocess.TimeoutExpired:
            status['termination'] = {'exit_status': 'WallTimeExceeded'}
            stop_process(process)
        finally:
            stop_process(bridge)
        private_trajectory = home / 'trajectory.private.json'
        if not (directory / 'trajectory.json').exists() and private_trajectory.exists():
            try:
                write_json(directory / 'trajectory.json', run.redact_credentials(json.loads(private_trajectory.read_text()), [token, cursor_key]))
            except (ValueError, OSError):
                status['trajectory_recovery'] = 'unavailable'
        receipt = directory / 'worker-result.json'
        if receipt.exists():
            status['termination'] = json.loads(receipt.read_text())
            status['failure_category'] = status['termination'].get('failure_category')
        elif 'termination' not in status:
            status.update(failure_category='INFRA', termination={'exit_status': 'WorkerExitedWithoutResult'})
        run.shell(docker + ['pause', container])
        try:
            status['submission_extras'] = run.collect_submission(docker, container, directory, config['limits']['artifact_bytes'])
            status['collection'] = 'ok'
        except ValueError:
            status.update(status='MODEL_FAILED', collection='missing', model_failure=True)
        else:
            run.remove_container(docker, container)
            try:
                status['audio'] = run.render(docker, args.agent_image, directory, config)
                status.update(status='RENDERED_UNSCORED', render='ok')
                status['artifact_sha256'] = hashlib.sha256((directory / 'submission/tune.xm').read_bytes()).hexdigest()
            except ValueError:
                status.update(status='MODEL_FAILED', render='invalid', model_failure=True)
    except KeyboardInterrupt:
        status.update(status='INTERRUPTED', failure_category='INFRA')
        raise
    except Exception as error:
        status.update(status='INFRA_ERROR', failure_category='INFRA', error_type=type(error).__name__)
    finally:
        for child in (process, bridge):
            try:
                stop_process(child)
            except Exception as error:
                status.update(status='INFRA_ERROR', failure_category='INFRA', cleanup_error=type(error).__name__)
        try:
            run.remove_container(docker, container)
        except Exception as error:
            status.update(status='INFRA_ERROR', failure_category='INFRA', cleanup_error=type(error).__name__)
        status['wall_seconds'] = time.monotonic() - started
        write_json(directory / 'status.json', status)
    try:
        profile = score_experiment(directory)
        if profile and (profile.get('evaluation_error') or {}).get('category') == 'EVAL':
            status['failure_category'] = 'EVAL'
            status['evaluation_error'] = profile['evaluation_error']
    except Exception as error:
        profile = {'eligible': False, 'frozen_eligible': False, 'leaderboard_eligible': False,
                   'experimental_condition': CONDITION, 'evaluation_status': 'error',
                   'evaluation_error': {'category': 'EVAL', 'error_type': type(error).__name__},
                   'craft': {'craft_score': None}}
        write_json(directory / 'profile.json', profile)
        status['failure_category'] = 'EVAL'
    write_json(directory / 'status.json', status)
    return status, profile


def report(root):
    rows = []
    for name in ATTEMPTS:
        directory = root / name
        status = json.loads((directory / 'status.json').read_text())
        profile_path = directory / 'profile.json'
        profile = json.loads(profile_path.read_text()) if profile_path.exists() else {}
        rows.append({'attempt': name, 'status': status['status'], 'score': (profile.get('craft') or {}).get('craft_score'),
                     'artifact_evaluation_eligible': profile.get('artifact_evaluation_eligible', False),
                     'failure_category': status.get('failure_category'), 'frozen_eligible': False})
    result = {'schema': 'keygen-cursor-private-experiment-1', 'condition': CONDITION,
              'leaderboard_eligible': False, 'cost_known': False, 'dollar_cost': None, 'attempts': rows,
              'note': 'All planned slots retained, including failures and unstarted slots. No automatic retry or public submission.'}
    scores = [row['score'] for row in rows if row['score'] is not None]
    result['scored_attempts'] = len(scores)
    result['best_score'] = max(scores) if scores else None
    result['mean_score'] = sum(scores) / 3 if len(scores) == 3 else None
    write_json(root / 'experimental-results.json', result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', help='Exact optional Cursor catalogue effort value')
    parser.add_argument('--agent-image', required=True, help='Already built pinned FT2 agent image sha256:...')
    parser.add_argument('--work', type=Path, required=True, help='NEW private output directory outside the checkout')
    parser.add_argument('--plan', action='store_true', help='Print the experiment contract; no model calls or Docker access')
    parser.add_argument('--allow-credit-usage', action='store_true')
    parser.add_argument('--accept-experimental-condition', action='store_true')
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', args.model):
        parser.error('Use an exact model ID')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', args.agent_image):
        parser.error('Use an immutable local agent image ID')
    args.work = private_path(args.work)
    config = configuration()
    if args.plan:
        print(json.dumps({'experiment': experiment(args.model, args.effort), 'config': config}, indent=2))
        return
    if not args.allow_credit_usage or not args.accept_experimental_condition:
        parser.error('Explicit credit-use and experimental-condition consent required; no enforced dollar cap')
    key = os.environ.pop('CURSOR_API_KEY', '')
    if not key:
        parser.error('Provide the authorized Cursor key privately in CURSOR_API_KEY; it is passed only to the SDK bridge')
    os.environ.pop('KEYGEN_CURSOR_BRIDGE_TOKEN', None)
    docker, identity = preflight(args, config)
    os.umask(0o077)
    args.work.mkdir(parents=True, mode=0o700)
    write_json(args.work / 'experiment.json', {'experiment': experiment(args.model, args.effort),
                                              'config': config, 'preflight': identity})
    for name in ATTEMPTS:
        (args.work / name).mkdir(mode=0o700)
        write_json(args.work / name / 'status.json', {'status': 'NOT_STARTED', 'eligible': False})
    try:
        for name in ATTEMPTS:
            status, _ = run_attempt(args.work / name, args, config, docker, key)
            if status.get('failure_category') in {'INFRA', 'AUTH', 'TRANSPORT', 'PROTOCOL', 'EVAL'}:
                break  # Do not repeatedly spend after a transport/entitlement failure.
    finally:
        report(args.work)
    print('Private experimental results saved. Scores are not leaderboard-qualified; cost remains unknown.')


if __name__ == '__main__':
    sys.path.insert(0, str(REPO))
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        worker(sys.argv[2])
    else:
        def terminate(_signum, _frame):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, terminate)
        main()
