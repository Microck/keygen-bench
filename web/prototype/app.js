// PROTOTYPE router: ?page=viewer|ranking|scoring|support&run=<slug>
import { loadData } from "./core/data.js";
import { loadFonts } from "./core/fb.js";
import { mount } from "./site.js";

const app = document.getElementById("app");
let data, site = null;

function params() {
  const q = new URLSearchParams(location.search);
  const page = q.get("page") || "viewer";
  // A main row shown as repetition 1 of a repetition group keeps its old ?run= link.
  let run = data.run_aliases?.[q.get("run")] ?? q.get("run");
  if (!data.bySlug[run]) run = data.runs[0].slug;
  return { page, run };
}

function go(next, { replace = false } = {}) {
  const q = new URLSearchParams(location.search);
  for (const [k, v] of Object.entries(next)) v == null ? q.delete(k) : q.set(k, v);
  history[replace ? "replaceState" : "pushState"](null, "", "?" + q.toString());
  render();
}

async function render() {
  const p = params();
  if (site) { site.update(p); return; }
  app.replaceChildren();
  site = await mount(app, { data, ...p, go });
}

addEventListener("popstate", render);

try {
  [data] = await Promise.all([loadData("./dist/"), loadFonts(), document.fonts.load('10px "FT2"'), document.fonts.load('20px "FT2 Big"'), document.fonts.load('7px "FT2 Tiny"')]);
  await render();
} catch (err) {
  app.innerHTML = `<div id="boot">${String(err.message || err)}</div>`;
  throw err;
}
