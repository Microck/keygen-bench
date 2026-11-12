import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MODEL_HISTORY, modelChangelog, groupChangelogDates } from '../web/classic/core/changelog.js';

const model = (key, label = key) => ({ key, best: { label, slug: key } });

test('history uses verified UTC dates and has no repeated model keys', () => {
  const keys = MODEL_HISTORY.flatMap((entry) => entry.keys);
  assert.equal(new Set(keys).size, keys.length);
  for (const entry of MODEL_HISTORY) {
    assert.match(entry.date, /^\d{4}-\d{2}-\d{2}$/);
    assert.ok((Number.isInteger(entry.pr) && entry.pr > 0) || (entry.kind === 'repository' && entry.commits.length > 0));
  }
  assert.deepEqual(MODEL_HISTORY.map((entry) => entry.date), [...MODEL_HISTORY.map((entry) => entry.date)].sort().reverse());
});

test('changelog shows only present models and retains undated models', () => {
  const byModel = { 'kimi-k3.1-pro': model('kimi-k3.1-pro', 'Kimi'), unknown: model('unknown', 'Unknown'), future: model('future', 'Future') };
  const result = modelChangelog(byModel);
  assert.deepEqual(result.dated.map((entry) => [entry.date, entry.models.map((item) => item.key)]),
    [['2026-10-28', ['kimi-k3.1-pro']]]);
  assert.deepEqual(result.undated.map((item) => item.key), ['future', 'unknown']);
});

test('duplicate or absent history entries never duplicate a displayed model', () => {
  const byModel = { x: model('x') };
  const result = modelChangelog(byModel, [
    { date: '2026-01-02', pr: 2, keys: ['x', 'missing'] },
    { date: '2026-01-01', pr: 1, keys: ['x'] },
  ]);
  assert.equal(result.dated.length, 1);
  assert.deepEqual(result.dated[0].models, [byModel.x]);
  assert.deepEqual(result.undated, []);
});

test('historical snapshot presence is distinct from a first-addition date', () => {
  const result = modelChangelog({ 'gpt-5.5': model('gpt-5.5') });
  assert.equal(result.dated[0].date, '2026-10-01');
  assert.equal(result.dated[0].kind, 'snapshot');
  assert.match(result.dated[0].note, /first addition dates are unverified/);
});

test('repository milestones retain their archive evidence', () => {
  const result = modelChangelog({ 'swe-2': model('swe-2'), 'north-mini-code': model('north-mini-code') });
  assert.deepEqual(result.dated.map((entry) => [entry.date, entry.kind]), [['2026-10-06', 'repository'], ['2026-10-05', 'repository']]);
  assert.deepEqual(result.undated, []);
});

test('groups separate same-day events without losing models or changing order', () => {
  const events = modelChangelog({ a: model('a'), b: model('b'), c: model('c') }, [
    { date: '2026-11-10', keys: ['a'] },
    { date: '2026-11-09', keys: ['c'] },
    { date: '2026-11-10', keys: ['b'] },
  ]).dated;
  assert.deepEqual(groupChangelogDates(events).map(({ date, models }) => [date, models.map((item) => item.key)]), [
    ['2026-11-10', ['a', 'b']], ['2026-11-09', ['c']],
  ]);
});

test('untested GPT Pro estimates use the disclosed planning scenarios', async () => {
  const { SUPPORT } = await import('../web/classic/core/content.js');
  const scenarios = [[80_000, 16_000], [130_000, 22_400], [200_000, 40_000]];
  for (const name of ['gpt-5.5-pro', 'gpt-5.4-pro', 'gpt-5.2-pro']) {
    const entry = SUPPORT.wanted.find((item) => item.model === name);
    const [input, output] = entry.price.replaceAll('$', '').split('/').map(Number);
    const estimates = scenarios.map(([prompt, completion]) => Math.ceil((3 * (prompt * input + completion * output) / 1_000_000) / 5) * 5);
    assert.deepEqual([entry.typical, entry.est, entry.heavy], estimates);
  }
  assert.ok(!SUPPORT.wanted.some((item) => item.model === 'gpt-5-pro'));
});


test('retired wanted models do not have funding goals', async () => {
  const { SUPPORT } = await import('../web/classic/core/content.js');
  for (const name of ['o1-pro', 'claude-3-opus']) {
    const entry = SUPPORT.wanted.find((item) => item.model === name);
    assert.equal(entry.accessOnly, true);
    assert.equal(entry.est, undefined);
    assert.ok(entry.accessLabel);
  }
});
