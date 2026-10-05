import assert from "node:assert/strict";
import test from "node:test";
import { loadData, rankingRows } from "../web/classic/core/data.js";

const run = (key, ordinal, score, extra = {}) => ({
  slug: `${key}-${ordinal}`, model_key: key, name: `${key} (attempt ${ordinal})`, maker: "Maker",
  score, provenance: { attempt_ordinal: ordinal }, usage: { completion_tokens: ordinal * 100, wall_minutes: ordinal },
  cost_usd: ordinal, ...extra,
});
const group = (key, scores) => ({
  model_key: key, declared: scores.length, pending: scores.filter((s) => s == null).length,
  attempts: scores.map((score, i) => ({ ordinal: i + 1, eligible: score != null, score,
    slug: score == null ? null : `${key}-${i + 1}`, status: score == null ? "NOT_STARTED" : "SUCCESS", attempted: score != null,
    superseded: [{ score: 100, eligible: true }],
  })),
});
async function dataset(groups, extras = []) {
  const source = {
    repetition_groups: groups,
    runs: groups.flatMap((g) => g.attempts.filter((a) => a.eligible).map((a) => run(g.model_key, a.ordinal, a.score))).concat(extras),
  };
  const previousFetch = globalThis.fetch;
  globalThis.fetch = async (url) => url.endsWith("data.json") && !url.endsWith("metadata.json")
    ? Response.json(source) : new Response(null, { status: 404 });
  try { return await loadData("/synthetic/"); }
  finally { globalThis.fetch = previousFetch; }
}

test("average uses scored ordinal slots including zero, not retry or outside-condition scores", async () => {
  const data = await dataset([group("zero", [0, 30, 60])], [run("zero", 4, 100)]);
  const model = data.byModel.zero;
  assert.equal(model.averageScore, 30);
  assert.equal(model.scoredSlots, 3);
  assert.equal(model.declared, 3);
  assert.equal(model.averageComplete, true);
  assert.equal(model.averageRank, 1);
  const [row] = rankingRows(data, { mode: "average" });
  assert.equal(row.score, 100);
  assert.equal(row.rank, 1);
  assert.equal(data.bySlug["zero-4"].score, 100);
  assert.equal(model.max - model.min, 100);
});

test("complete average ranks use means and deterministic ties, incomplete models cannot win", async () => {
  const data = await dataset([
    group("peak", [100, 0, 20]), group("steady-b", [50, 50, 50]), group("steady-a", [40, 50, 60]),
    group("incomplete", [99, null, null]),
  ], [run("exhibition", 1, 100, { exhibition: true })]);
  const rows = rankingRows(data, { mode: "average", exhibitions: false });
  assert.deepEqual(rows.map((r) => r.model.key), ["steady-a", "steady-b", "peak", "incomplete"]);
  assert.deepEqual(rows.map((r) => r.rank), [1, 2, 3, null]);
  assert.equal(rows.at(-1).model.scoredSlots, 1);
  assert.equal(rows.at(-1).model.averageComplete, false);
  assert.deepEqual(rankingRows(data, { mode: "average", exhibitions: false, asc: true }).map((r) => r.model.key),
    ["peak", "steady-a", "steady-b", "incomplete"]);
  for (const asc of [false, true]) {
    assert.equal(rankingRows(data, { mode: "average", exhibitions: false, sort: "name", asc }).at(-1).model.key, "incomplete");
    assert.equal(rankingRows(data, { mode: "average", exhibitions: false, sort: "rank", asc }).at(-1).model.key, "incomplete");
  }
});

test("average preserves each attempt view, score and individual usage", async () => {
  const data = await dataset([group("model", [10, 70, 40])], [run("exhibition", 1, 100, { exhibition: true })]);
  for (const view of ["best", "first", "all"]) {
    const before = rankingRows(data, { view }).map((r) => [r.slug, r.score, r.cost_usd, r.usage.completion_tokens]).sort();
    const after = rankingRows(data, { mode: "average", view }).map((r) => [r.slug, r.score, r.cost_usd, r.usage.completion_tokens]).sort();
    assert.deepEqual(after, before);
  }
  assert.deepEqual(rankingRows(data, { mode: "average", view: "all" }).filter((r) => !r.exhibition).map((r) => r.slug),
    ["model-2", "model-3", "model-1"]);
});

test("unknown usage and consistency stay last in either direction", async () => {
  const data = await dataset([group("steady", [10, 12]), group("spread", [0, 80]), group("single", [50])]);
  data.byModel.single.best.cost_usd = null;
  data.byModel.single.totalCost.cost_usd = null;
  data.byModel.single.best.usage.completion_tokens = null;
  data.byModel.single.best.usage.wall_minutes = null;
  for (const sort of ["cons", "cost", "out", "min"]) {
    for (const asc of [false, true]) {
      assert.equal(rankingRows(data, { mode: "average", sort, asc }).at(-1).model.key, "single");
      assert.equal(rankingRows(data, { sort, asc }).at(-1).model.key, "single");
    }
  }
  assert.deepEqual(rankingRows(data, { sort: "cons", asc: true }).map((r) => r.model.key), ["steady", "spread", "single"]);
  assert.deepEqual(rankingRows(data, { sort: "cons", asc: false }).map((r) => r.model.key), ["spread", "steady", "single"]);
});

test("ordinal totals include known failed costs, sum bounds and flag missing costs", async () => {
  const g = group("cost", [10, 20, null]);
  g.attempts[2].attempted = true;
  g.attempts[2].cost_usd = 4;
  let data = await dataset([g], [run("cost", 4, 100, { cost_usd: 99 })]);
  assert.equal(data.byModel.cost.totalCost.cost_usd, 7);
  assert.equal(data.byModel.cost.totalCost.partial, false);
  delete g.attempts[2].cost_usd;
  g.attempts[2].cost_range_usd = { min: 2, max: 4 };
  data = await dataset([g]);
  assert.deepEqual([data.byModel.cost.totalCost.cost_range_usd.min, data.byModel.cost.totalCost.cost_range_usd.max], [5, 7]);
  delete g.attempts[2].cost_range_usd;
  data = await dataset([g]);
  assert.equal(data.byModel.cost.totalCost.cost_usd, 3);
  assert.equal(data.byModel.cost.totalCost.partial, true);
  g.attempts[2].cost_usd = 0;
  data = await dataset([g]);
  assert.equal(data.byModel.cost.totalCost.cost_usd, 3);
  assert.equal(data.byModel.cost.totalCost.partial, false);
});

test("cost ordering uses the single displayed upper estimate", async () => {
  const wide = group("wide", [30, 20, null]);
  wide.attempts[2].attempted = true;
  wide.attempts[2].cost_range_usd = { min: 1, max: 10 };
  const data = await dataset([wide, group("exact", [10, 20, 30])]);
  assert.deepEqual(rankingRows(data, { sort: "cost", asc: true }).map((r) => r.model.key), ["exact", "wide"]);
  assert.deepEqual(rankingRows(data, { sort: "cost", asc: false }).map((r) => r.model.key), ["wide", "exact"]);
});
