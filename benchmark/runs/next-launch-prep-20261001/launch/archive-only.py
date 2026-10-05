#!/usr/bin/env python3
"""Export retained outputs from new staging without changing historical attempts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    plan = json.loads(Path(sys.argv[1]).read_text())
    root = Path(plan['root'])
    spec = importlib.util.spec_from_file_location('approved_helpers', root / plan['helpers'])
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    os.environ.clear()
    os.environ.update(helpers.environment(plan))
    sys.path.insert(0, str(root / 'repo/benchmark'))
    import run
    from artifacts import ArtifactStore
    config = json.loads(Path(plan['original_manifest']).read_text())['campaign']
    upload_timeout = plan.get('archive_copy_timeout_seconds', 600)
    if type(upload_timeout) is not int or not 600 <= upload_timeout <= 1800:
        raise ValueError('Archive upload must retain a finite approved deadline')
    class BoundedArchiveStore(ArtifactStore):
        def _command(self, *args, timeout=600):
            if args and args[0] == 'copyto':
                timeout = max(timeout, upload_timeout)
            return super()._command(*args, timeout=timeout)
    store = BoundedArchiveStore(config['storage'])
    output = Path(plan['recovery_root'])
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    results = []
    for attempt_id in plan['attempts']:
        source = Path(plan['original_out']) / attempt_id
        stage = output / attempt_id
        stage.mkdir(mode=0o700)
        original = {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}
        for path in store._files(source):
            relative = path.relative_to(source)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        status = json.loads((stage / 'status.json').read_text())
        profile = json.loads((stage / 'profile.json').read_text())
        reconstructed = False
        if status['status'] == 'FINALIZATION_ERROR':
            candidate = dict(status)
            candidate.pop('finalization_error', None)
            candidate.update(status=profile['status'], eligible=profile['eligible'],
                             failure_category=profile.get('run_failure_category'))
            payload = json.dumps(candidate, indent=2, allow_nan=False) + '\n'
            expected = profile['inputs']['artifacts']['status.json']
            if hashlib.sha256(payload.encode()).hexdigest() != expected:
                raise ValueError('Original evaluation status reconstruction is not hash-proven')
            (stage / 'status.json').write_text(payload)
            status = candidate
            reconstructed = True
        metadata = store.archive_attempt(stage)
        run.write_json(stage / 'archive.json', metadata)
        with tempfile.TemporaryDirectory(prefix='archive-recovery-roundtrip-', dir=output) as temporary:
            store.restore_attempt(metadata, Path(temporary) / 'attempt')
        if original != {str(p.relative_to(source)): digest(p) for p in source.rglob('*') if p.is_file()}:
            raise RuntimeError('Historical attempt changed during read-only export')
        record = {'attempt_id': attempt_id, 'source': str(source), 'staging': str(stage),
                  'historical_status_sha256': original['status.json'],
                  'reconstructed_prearchive_status': reconstructed,
                  'recovered_status_sha256': digest(stage / 'status.json'),
                  'eligible_success': run.attempt_succeeded(status, profile),
                  'archive_generation': metadata['generation'], 'archive': metadata['remote'],
                  'archive_sha256': metadata['sha256'], 'archive_roundtrip_verified': True,
                  'historical_files_unchanged': True, 'model_requests': 0}
        results.append(record)
        run.write_json(output / 'recovery-records.json', {'results': results})
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
