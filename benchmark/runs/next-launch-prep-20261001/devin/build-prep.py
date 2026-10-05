#!/usr/bin/env python3
"""Freeze catalog choices and build readiness inputs. No inference or credential reads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ASHBURN = Path('/home/ubuntu/keygen-full.OGHjBAkO')
ROOT = ASHBURN / 'devin-20261004'
ORDER = [
    ('DeepSeek V4 Pro', 'deepseek-v4-pro'), ('DeepSeek V4.1 Flash', 'deepseek-v4-1-flash'),
    ('GLM-5.2', 'glm-5-2'), ('GLM-5.3', 'glm-5-3'), ('GLM-5.3 Flash', 'glm-5-3-flash'),
    ('Grok 4.6', 'grok-4-6'), ('Grok 4.7', 'grok-4-7'), ('Kimi K3', 'kimi-k3'),
    ('Grok 4.5', 'grok-4-5'), ('Inkling', 'inkling'), ('Nemotron 3 Ultra', 'nemotron-3-ultra'),
    ('Kimi K2.6', 'kimi-k2-6'), ('Kimi K2.7', 'kimi-k2-7'), ('GPT-5.3 Codex', 'gpt-5-3-codex'),
    ('GPT-5.4', 'gpt-5-4'), ('GPT-5.4 Mini', 'gpt-5-4-mini'), ('Claude Opus 5', 'claude-opus-5'),
    ('DeepSeek V4 Flash', 'deepseek-v4-flash'), ('SWE-1.6', 'swe-1-6'),
    ('SWE-1.7 Lightning', 'swe-1-7-lightning'), ('SWE-2', 'swe-2'),
]
RANK = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max']


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def build(control, root, bridge_record, repo):
    sys.path.insert(0, str(repo / 'benchmark'))
    import native_models
    catalog_path = HERE / 'catalog-20261003.json'
    catalog = {entry['id']: entry for entry in json.loads(catalog_path.read_text())['devin']}
    bridge_info = json.loads(bridge_record.read_text())
    bridge = bridge_info['bridge']
    base_url = bridge_info.get('base_url', 'http://127.0.0.1:8417/v1')
    entries, decisions, rows = [], [], []
    for index, (name, catalog_id) in enumerate(ORDER):
        entry = catalog.get(catalog_id)
        if entry is None:
            decisions.append({'name': name, 'catalog_id': catalog_id, 'included': False,
                              'reason': 'Exact requested model absent from frozen Devin catalog'})
            continue
        levels = entry.get('thinking', {}).get('levels', [])
        if any(level not in RANK for level in levels):
            raise ValueError('Unknown catalog thinking level for ' + catalog_id)
        tier = max(levels, key=RANK.index) if levels else 'none-available'
        if tier == 'none':
            raise ValueError('Only disabled reasoning listed for ' + catalog_id)
        reasoning = {'reasoning_effort': tier} if levels else {}
        identity = 'devin-' + catalog_id
        request = 'devin/' + catalog_id
        response = bridge_info.get('response_prefix', '') + catalog_id
        output_key = 'max_completion_tokens' if catalog_id in {'gpt-5-3-codex', 'gpt-5-4', 'gpt-5-4-mini'} else 'max_tokens'
        generation = {output_key: 64000, **reasoning}
        entries.append({'identity': identity, 'model': request, 'response_model': response,
                        'provider': 'devin', 'api': 'chat', 'base_url': base_url, 'tier': tier,
                        'reasoning': reasoning, 'generation': generation,
                        'limits': {'model_max_output_tokens': entry['max_completion_tokens'], 'run_output_cap': 64000}})
        override = native_models.CAPABILITY_OVERRIDES.get(('devin', 'chat', request))
        if override:
            entries[-1]['capability_override'] = override
        decisions.append({'name': name, 'catalog_id': catalog_id, 'included': True,
                          'catalog_levels': levels, 'chosen_tier': tier, 'priority': index,
                          'reason': 'Highest listed Devin thinking level' if levels else 'Catalog exposes no thinking levels',
                          'launch_condition': 'Exact identity and transmitted controls must pass readiness; never downgrade'})
        rows.append({'model': identity, 'display_name': name, 'provider': 'Devin',
                     'status': 'pending-exact-native-proof', 'upstream_model': response,
                     'proxy_request_model': request, 'catalog_id': catalog_id})
    tier_spec = {'schema': 'keygen-tier-spec-1', 'scope': 'Requested Devin route models, frozen 2026-10-03',
                 'catalog_url': 'https://raw.githubusercontent.com/router-for-me/models/refs/heads/main/devin_models.json',
                 'catalog_sha256': hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
                 'tier_semantics': 'Highest listed catalog level; no level only when catalog lists none; no downgrade',
                 'entries': entries}
    save(control / 'tier-spec-devin.json', tier_spec)
    sha = hashlib.sha256((control / 'tier-spec-devin.json').read_bytes()).hexdigest()
    frozen = json.loads((HERE / 'frozen-settings.json').read_text())
    items, pending_models = [], []
    for entry in entries:
        model = {'id': entry['identity'], 'inventory_id': entry['identity'], 'model': entry['model'],
                 'response_model': entry['response_model'], 'provider': 'devin', 'api': 'chat',
                 'base_url': base_url, 'api_key_env': 'DEVIN_BRIDGE_API_KEY', 'generation': entry['generation'],
                 'tier': {'level': entry['tier'], 'reasoning': entry['reasoning'], 'spec_sha256': sha},
                 'backend_provenance': {'service_revision': None, 'bridge': bridge}}
        save(control / 'specs' / (model['id'] + '.json'),
             {'model': model, 'config': {'native': frozen['native']}, 'image': frozen['image'],
              'limits': {'steps': 5, 'wall_seconds': 1800, 'command_seconds': 15}})
        items.append({'id': model['id'], 'provider': 'devin', 'spec': str(root / 'control/specs' / (model['id'] + '.json')),
                      'out': str(root / 'qualification/out' / model['id']), 'timeout': 2400})
        pending_models.append({**model, 'readiness': {'status': 'pending-reset-qualification',
                                                     'verified_at': None, 'evidence': None}})
    save(control / 'inventory-devin.json', {'scope': 'Separate Devin routes; no Go results mixed', 'models': rows})
    save(control / 'model-decisions.json', {'models': decisions, 'excluded_families': {'Gemini': 'Already completed via Google'},
                                         'unrequested_catalog_models': 'Not added; requested identities only'})
    save(control / 'qualification-plan.json', {'control': str(root / 'qualification'),
         'env_file': str(ASHBURN / '.private/controller.env.json'), 'python': str(ASHBURN / 'runtime/bin/python3.11'),
         'readiness': str(root / 'repo/benchmark/native_readiness.py'), 'concurrency': {'devin': 2},
         'go_pool': [], 'go_per_key': 0, 'label': 'devin-qualify-1', 'items': items,
         'bridge': bridge_info['executable']})
    frozen['campaign_id'] = 'next-max-tier-prompt-v2-devin-20261004'
    frozen['transport']['boat'].update(type='default', attempts_per_vm=3, linger_seconds=120, ttl_seconds=14400)
    frozen['concurrency']['providers'].update(google=1, devin=2)
    frozen['concurrency'].update(workers=2, key_pools={})
    frozen['models'] = pending_models
    save(control / 'selection-pending.json', frozen)
    return {'models': len(items), 'tier_spec_sha256': sha, 'requests_sent': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, default=HERE)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--bridge-record', type=Path, default=HERE / 'bridge-record.json')
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.control, args.root, args.bridge_record, args.repo)))


if __name__ == '__main__':
    main()
