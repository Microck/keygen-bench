// PROTOTYPE: data access for the site.
import { parseXM } from "./xm.js";

export async function loadData(base = "./dist/") {
  const res = await fetch(base + "data.json");
  if (!res.ok) throw new Error("Run `python web/prototype/build.py` first (dist/data.json missing)");
  const data = await res.json();
  data.base = base;
  data.spend = await fetch(base + "spend.json").then((r) => (r.ok ? r.json() : null)).catch(() => null);
  groupAttempts(data);
  const byMaker = new Map();
  for (const r of data.runs) {
    if (!byMaker.has(r.maker)) byMaker.set(r.maker, []);
    byMaker.get(r.maker).push(r);
  }
  data.makers = [...byMaker.entries()]
    .map(([name, runs]) => ({ name, runs, best: Math.max(...runs.map((r) => r.score)) }))
    .sort((a, b) => b.best - a.best);
  data.bySlug = Object.fromEntries(data.runs.map((r) => [r.slug, r]));
  return data;
}

// "gpt-5.5 (max-tier, attempt 2)" -> "gpt-5.5". The tier is the same for every row of a cohort, so it is
// shown once in the run details instead of in every name.
const baseName = (name) => name.replace(/\s*\([^)]*\btier\b[^)]*\)\s*$/i, "");

// One model = all its attempts. The ranked row is the model's best-scoring attempt; every row carries the
// model's attempt list (including failed and unstarted slots from the repetition group) for the
// consistency marker. Older snapshots (one run per model, `rank` already set) pass through unchanged.
function groupAttempts(data) {
  const groups = Object.fromEntries((data.repetition_groups ?? []).map((g) => [g.model_key, g]));
  const byModel = new Map();
  for (const r of data.runs) {
    r.label = baseName(r.name);
    r.attempt = r.provenance?.attempt_ordinal ?? 1;
    const key = r.model_key ?? r.slug;
    if (!byModel.has(key)) byModel.set(key, []);
    byModel.get(key).push(r);
  }
  const models = [...byModel.entries()].map(([key, runs]) => {
    const scored = runs.filter((r) => !r.failed).sort((a, b) => a.attempt - b.attempt);
    const g = groups[key];
    // Slots: the group's declared attempts when it has one, else just the published runs.
    const slots = g ? g.attempts.map((a) => ({ ordinal: a.ordinal, score: a.eligible ? a.score : null, slug: a.slug ?? null,
      state: a.eligible ? "ok" : a.status === "RUNNING" || a.queue_pending || (!a.attempted && !a.stopped_by && g.pending) ? "pending" : a.attempted ? "failed" : "skipped",
      status: a.failure_category ?? a.status }))
      : scored.map((r) => ({ ordinal: r.attempt, score: r.score, slug: r.slug, state: "ok", status: r.status }));
    const scores = scored.map((r) => r.score);
    const mean = scores.reduce((s, v) => s + v, 0) / (scores.length || 1);
    const sd = Math.sqrt(scores.reduce((s, v) => s + (v - mean) ** 2, 0) / (scores.length || 1));
    const best = scored.reduce((b, r) => (!b || r.score > b.score ? r : b), null) ?? runs[0];
    const model = { key, runs: scored, slots, best, n: scores.length, declared: slots.length,
      min: Math.min(...scores), max: Math.max(...scores), mean, sd };
    for (const r of runs) { r.model = model; r.isBest = r === best; }
    return model;
  });
  data.byModel = Object.fromEntries(models.map((m) => [m.key, m]));
  if (data.runs.some((r) => r.rank)) return; // legacy snapshot: keep its ranks
  models.filter((m) => !m.best.failed && !m.best.exhibition).sort((a, b) => b.best.score - a.best.score)
    .forEach((m, i) => { m.best.rank = i + 1; });
}

const xmCache = new Map();
export function loadXM(data, run) {
  if (!run.media.xm) return Promise.resolve(null);
  if (!xmCache.has(run.slug)) {
    xmCache.set(run.slug, fetch(data.base + run.media.xm).then((r) => r.arrayBuffer()).then(parseXM));
  }
  return xmCache.get(run.slug);
}

export const mediaUrl = (data, path) => data.base + path;

export const money = (v) => (v == null ? "n/a" : v < 0.01 ? "<$0.01" : "$" + v.toFixed(2));
export const usd = (v) => "$" + Math.round(v).toLocaleString("en-US");
export const tokens = (v) => (v == null ? "n/a" : v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? Math.round(v / 1e3) + "k" : String(v));
export const mmss = (s) => (s == null ? "--:--" : `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`);
