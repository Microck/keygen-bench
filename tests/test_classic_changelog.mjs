import assert from 'node:assert/strict';
import { test } from 'node:test';
import { MODEL_HISTORY, modelChangelog } from '../web/classic/core/changelog.js';

const model = (key, label = key) => ({ key, best: { label, slug: key } });

test('history uses verified UTC dates and has no repeated model keys', () => {
  const keys = MODEL_HISTORY.flatMap((entry) => entry.keys);
  assert.equal(new Set(keys).size, keys.length);
  for (const entry of MODEL_HISTORY) {
    assert.match(entry.date, /^\d{4}-\d{2}-\d{2}$/);
    assert.ok(Number.isInteger(entry.pr) && entry.pr > 0);
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
