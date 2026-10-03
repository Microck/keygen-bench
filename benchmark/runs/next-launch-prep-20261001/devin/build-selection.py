#!/usr/bin/env python3
"""Select only verified Devin routes in requested order, preserving frozen conditions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/ubuntu/keygen-full.OGHjBAkO/devin-20261004')
CAMPAIGN_ID = 'next-max-tier-prompt-v2-devin-20261004'
PACKING = {'type': 'default', 'attempts_per_vm': 3, 'linger_seconds': 120, 'ttl_seconds': 14400}


def build(root, control):
    frozen = json.loads((HERE / 'frozen-settings.json').read_text())
    selection = copy.deepcopy(frozen)
    selection['campaign_id'] = CAMPAIGN_ID
    selection['transport']['boat'].update(PACKING)
    selection['concurrency']['providers'].update(google=1, devin=2)
    selection['concurrency']['workers'] = 2
    selection['concurrency']['key_pools'] = {}
    plan = json.loads((control / 'qualification-plan.json').read_text())
    summary = json.loads((root / 'qualification/devin-qualify-1-summary.json').read_text())
    results = {row['id']: row for row in summary['results']}
    if len(results) != len(plan['items']) or set(results) != {item['id'] for item in plan['items']}:
        raise ValueError('Qualification did not produce exactly one result for every requested model')
    models, skipped = [], {}
    for item in plan['items']:
        model = json.loads((control / 'specs' / (item['id'] + '.json')).read_text())['model']
        result = results[model['id']]
        if result.get('driver_error') or result.get('result_read_error'):
            raise ValueError('Qualification controller failure for ' + model['id'])
        out = root / 'qualification/out' / model['id']
        readiness = json.loads((out / 'readiness.json').read_text())
        if readiness['status'] != 'verified':
            skipped[model['id']] = readiness.get('blocker') or readiness['status']
            continue
        if result.get('returncode') != 0:
            raise ValueError('Verified readiness with failed subprocess for ' + model['id'])
        raw = (out / 'proof.json').read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        target = control / 'collected-proofs' / model['id'] / sha / 'proof.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / 'proof.json', target)
        model['readiness'] = {'status': 'verified', 'verified_at': readiness['verified_at'],
                              'evidence': {'evidence_path': str(target.relative_to(control)), 'artifact_sha256': sha,
                                           'provider_received_settings_verified': False}}
        models.append(model)
    report = {'selected': [model['id'] for model in models], 'skipped': skipped,
              'policy': 'Highest listed tier only; exact identity plus transmitted control proof required; no downgrade'}
    (control / 'selection-report.json').write_text(json.dumps(report, indent=2) + '\n')
    if not models:
        raise ValueError('No Devin model passed readiness; campaign will not launch')
    selection['models'] = models
    (control / 'devin-selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--control', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.control or args.root / 'control')))


if __name__ == '__main__':
    main()
