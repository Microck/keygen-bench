// Router. Clean paths:
//   /tracker[/<model>[/<attempt>]]   /rankings[/<model>[/<attempt>]]   /scoring   /support
// <model> is the model key (e.g. gpt-5.5); without <attempt> it means the model's best attempt. "/" is the tracker.
import { loadData } from "./core/data.js";
import { loadFonts } from "./core/fb.js";
import { mount } from "./site.js";

const app = document.getElementById("app");
let data, site = null;

const SEG = { viewer: "tracker", ranking: "rankings", scoring: "scoring", support: "support" };
const PAGE = Object.fromEntries(Object.entries(SEG).map(([k, v]) => [v, k]));

function params() {
  const [seg, model, attempt] = location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const page = PAGE[seg] ?? "viewer";
  const m = data.byModel[model];
  const run = (m && (attempt ? m.runs.find((r) => String(r.attempt) === attempt) : m.best)) ?? data.runs.find((r) => r.rank === 1) ?? data.runs[0];
  return { page, run: run.slug };
}

// Path for a page + run. Model-specific only on the pages that show one run.
export function pathFor(page, slug) {
  const r = data.bySlug[slug];
  const base = "/" + SEG[page];
  if (!r || (page !== "viewer" && page !== "ranking")) return base;
  return `${base}/${encodeURIComponent(r.model.key)}${r.isBest ? "" : "/" + r.attempt}`;
}

// next: { page?, run? }. replace: rewrite the URL without a history entry. silent: URL only, no re-render.
function go(next, { replace = false, silent = false } = {}) {
  const cur = params();
  const page = next.page ?? cur.page, run = next.run ?? cur.run;
  history[replace ? "replaceState" : "pushState"](null, "", pathFor(page, run));
  if (!silent) render();
}

async function render() {
  const p = params();
  if (site) { site.update(p); return; }
  app.replaceChildren();
  site = await mount(app, { data, ...p, go, pathFor });
}

addEventListener("popstate", render);

try {
  [data] = await Promise.all([loadData("/dist/"), loadFonts(), document.fonts.load('10px "FT2"'), document.fonts.load('20px "FT2 Big"'), document.fonts.load('7px "FT2 Tiny"')]);
  await render();
} catch (err) {
  app.innerHTML = `<div id="boot">${String(err.message || err)}</div>`;
  throw err;
}
