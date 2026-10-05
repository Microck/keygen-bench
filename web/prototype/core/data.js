// PROTOTYPE: data access for the site.
import { parseXM } from "./xm.js";

export async function loadData(base = "./dist/") {
  const res = await fetch(base + "data.json");
  if (!res.ok) throw new Error("Run `python web/prototype/build.py` first (dist/data.json missing)");
  const data = await res.json();
  data.base = base;
  // Unranked later attempts (attempt_of: their ranked row's slug) are reached through that row's attempt switcher.
  data.listed = data.runs.filter((r) => !r.attempt_of);
  const byMaker = new Map();
  for (const r of data.listed) {
    if (!byMaker.has(r.maker)) byMaker.set(r.maker, []);
    byMaker.get(r.maker).push(r);
  }
  data.makers = [...byMaker.entries()]
    .map(([name, runs]) => ({ name, runs, best: Math.max(...runs.map((r) => r.score)) }))
    .sort((a, b) => data.dataset_kind === "native-first-success" ? a.name.localeCompare(b.name) : b.best - a.best);
  data.bySlug = Object.fromEntries(data.runs.map((r) => [r.slug, r]));
  return data;
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
