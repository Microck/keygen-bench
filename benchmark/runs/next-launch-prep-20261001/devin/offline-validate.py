#!/usr/bin/env python3
"""Validate every generated Devin spec and tier without sending any requests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--control', type=Path, default=HERE)
    args = parser.parse_args()
    os.environ['LITELLM_LOCAL_MODEL_COST_MAP'] = 'True'
    sys.path.insert(0, str(args.repo.resolve() / 'benchmark'))
    import campaign
    import native_models
    tier_path = args.control / 'tier-spec-devin.json'
    tier = json.loads(tier_path.read_text())
    rows = []
    models = []
    for entry in tier['entries']:
        spec = json.loads((args.control / 'specs' / (entry['identity'] + '.json')).read_text())
        model = spec['model']
        models.append(model)
        row = {'id': model['id'], 'model': model['model'], 'tier': model['tier']['level']}
        try:
            effective = native_models.validate_model(spec['config'], model)
            if effective['expected_transmitted_generation'] != entry['generation']:
                raise ValueError('SDK wire generation differs from frozen maximum-tier settings')
            row.update(status='pass', transmitted_generation=effective['expected_transmitted_generation'],
                       transmitted_reasoning=effective['transmitted_reasoning'])
        except Exception as error:
            row.update(status='rejected', reason=str(error))
        rows.append(row)
    campaign.check_tier_spec(models, tier_path)
    report = {'requests_sent': 0, 'tier_spec_sha256': hashlib.sha256(tier_path.read_bytes()).hexdigest(),
              'native_models_sha256': hashlib.sha256((args.repo / 'benchmark/native_models.py').read_bytes()).hexdigest(),
              'counts': {status: sum(row['status'] == status for row in rows) for status in ('pass', 'rejected')},
              'models': rows}
    (args.control / 'offline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['counts']))
    raise SystemExit(bool(report['counts']['rejected']))


if __name__ == '__main__':
    main()
