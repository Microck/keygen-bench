// PROTOTYPE results site: full screen and chunky. Built from FT2 parts (raised panels,
// sunken wells, pushbuttons, PATTEXT on black) in FT2 pixel units, laid out on a stage of
// (viewport / k) and zoomed by an integer k, so text, buttons and logos render at FT2's size x k.
// Every page fills the viewport; only inner wells scroll.
import { FB, PAL } from "./core/fb.js";
import { drawPatternFit, drawScopes } from "./core/pattern.js";
import { Player } from "./core/player.js";
import { loadXM, money, usd, tokens, mmss } from "./core/data.js";
import { h, badge, dropdown, makerItems, modelItems, scoreColor } from "./core/ui.js";
import { SCORING, SCORING_NOTES, DISCLAIMER, KEYGEN, OVERVIEW, SUPPORT, SITE, PAGES } from "./core/content.js";
import { fmt } from "./core/xm.js";
import { slide, TRANSITION_CSS } from "./core/transitions.js";

const SHORT = { SUSTAINED_NOISE: "NOISE", PHRASE_SAMPLE: "PHRASE", SAMPLE_HEAVY: "SMP", TAIL_SILENCE: "TAIL", MASKED: "MASK", SILENCE: "SIL" };

const CSS = `
.vb { position: fixed; left: 0; top: 0; transform-origin: 0 0; display: flex; flex-direction: column; gap: 1px; padding: 1px; background: var(--desktop); overflow: hidden; }
.vb .bar { flex: none; display: flex; align-items: center; height: 24px; padding: 0 3px; gap: 2px; }
.vb .logo { display: flex; align-items: baseline; gap: 6px; padding-left: 3px; min-width: 0; overflow: hidden; }
.vb .logo b { font-family: "FT2 Big"; font-size: 20px; line-height: 20px; font-weight: normal; color: #fff; text-shadow: 1px 1px 0 var(--dsktop2); white-space: nowrap; }
.vb .logo small { color: var(--dim); min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vb .tabs { display: flex; gap: 1px; margin-left: auto; }
.vb .tabs .btn { height: 18px; min-width: 62px; }
.vb .page { flex: 1; min-height: 0; display: grid; gap: 1px; }
.vb .panel { padding: 3px; min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: 2px; }
.vb .panel > h2 { margin: 0; padding: 1px 1px 0; font-size: 10px; line-height: 11px; font-weight: normal; color: #fff; text-shadow: 1px 1px 0 var(--dsktop2); white-space: nowrap; overflow: hidden; }
.vb .well { padding: 3px 4px; color: #fff; overflow: auto; min-height: 0; }
.vb .well p { margin: 0 0 7px; max-width: 86ch; }
.vb .row { display: flex; gap: 3px; align-items: center; min-width: 0; }
.vb .grow { flex: 1; min-width: 0; }
.vb .kv { display: grid; grid-template-columns: auto 1fr; gap: 1px 8px; margin: 0; padding: 3px 4px; align-content: start; }
.vb .kv dt { color: var(--pattext); white-space: nowrap; }
.vb .kv dd { margin: 0; color: #fff; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vb .meter { height: 7px; position: relative; }
.vb .meter i { position: absolute; left: 1px; top: 1px; bottom: 0; background: var(--pattext); }
.vb canvas.px { display: block; image-rendering: pixelated; }
.vb .fill { position: relative; flex: 1; min-height: 0; min-width: 0; }
.vb .fill > canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
.vb table.lb { width: 100%; border-collapse: collapse; table-layout: fixed; }
.vb table.lb td.nm { overflow: hidden; }
.vb table.lb .nmc { display: flex; gap: 4px; align-items: center; min-width: 0; }
.vb table.lb .nmt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 0 1 auto; }
.vb table.lb .flag { flex: none; }
.vb table.lb col.c-rank { width: 28px; } .vb table.lb col.c-score { width: 72px; } .vb table.lb col.c-cost { width: 52px; } .vb table.lb col.c-out { width: 50px; } .vb table.lb col.c-min { width: 34px; }
.vb .att { display: grid; grid-template-columns: auto minmax(0,1fr) auto; gap: 1px 5px; align-items: center; padding: 3px 4px; }
.vb .att > span { white-space: normal; }
.vb .att .btn { height: 14px; }
.vb .attsw { flex-wrap: wrap; gap: 3px; }
.vb .attsw .btn { height: 14px; }
.vb .off { color: var(--dim); white-space: nowrap; }
.vb .unranked, .vb .note.unranked { color: #FFAA00; }
.vb table.lb td.num, .vb table.lb th.num { padding-right: 6px; }
.vb table.lb th { position: sticky; top: 0; z-index: 1; background: var(--desktop); color: #fff; text-shadow: 1px 1px 0 var(--dsktop2); font-weight: normal; text-align: left; padding: 2px 4px; cursor: pointer; white-space: nowrap; box-shadow: inset 0 -1px 0 var(--dsktop2); }
.vb table.lb th.num, .vb table.lb td.num { text-align: right; }
.vb table.lb th[aria-sort] { color: var(--pattext); }
.vb table.lb td { padding: 0 4px; height: 18px; color: var(--pattext); white-space: nowrap; }
.vb table.lb td .badge { vertical-align: -4px; }
.vb table.lb tbody tr { cursor: pointer; }
.vb table.lb tbody tr:hover td { background: var(--blckmrk); }
.vb table.lb tbody tr.sel td { background: var(--desktop); color: #fff; }
.vb table.lb tr.exh td { color: var(--dim); }
.vb .sbar { display: inline-block; height: 7px; vertical-align: 0; margin-right: 4px; }
.vb .flag { color: #FFAA00; cursor: help; }
.vb .flag:hover { color: #FFFF55; text-decoration: underline; }
.vb .big { font-family: "FT2 Big"; font-size: 20px; line-height: 20px; color: #fff; text-shadow: 1px 1px 0 var(--looppin); }
.vb .toc .btn { justify-content: flex-start; height: 24px; width: 100%; padding-left: 5px; }
.vb .toc { gap: 2px; }
.vb pre.formula { margin: 0 0 7px; color: var(--pattext); font: inherit; }
.vb table.plain { border-collapse: collapse; margin-bottom: 7px; }
.vb table.plain td { padding: 0 10px 0 0; color: var(--pattext); }
.vb table.plain tr:first-child td { color: #fff; }
.vb .cta { height: 22px; min-width: 120px; }
.vb .dd { height: 14px; }
.vb .dd-pop { max-height: 60vh; }
.vb .dd-pop .list-row { height: 17px; line-height: 17px; }
.vb .dd-face .badge, .vb .dd-pop .badge { width: 12px !important; height: 12px !important; }
.vb .list-row { height: 10px; line-height: 10px; }
.vb .tbtn { height: 16px; }
.vb .detail > section { flex: none; }
.vb .note { margin: 0; padding: 0 2px; color: var(--dim); white-space: normal; }
.vb .card-name { white-space: normal; overflow-wrap: anywhere; }
.vb .kv dd.wrap { white-space: normal; }
.vb .pod-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vb .seek > i::after { content: ""; position: absolute; right: -1px; top: -1px; bottom: 0; width: 2px; background: #fff; }
.vb .seek:hover { box-shadow: inset 1px 1px 0 var(--dsktop2), inset -1px -1px 0 var(--dsktop1), inset 0 0 0 1px var(--looppin); }
/* Fixed-width readouts: font1 digits are 7px, ':' 3px; min-width in ch + tabular glyphs => no jitter. */
.vb .lcd { flex: none; height: 14px; padding: 2px 0 0; white-space: nowrap; color: #fff; display: inline-flex; justify-content: center; overflow: hidden; }
.vb .lcd .c { display: inline-block; width: 8px; text-align: center; }
.vb .lcd .c.n { width: 4px; }
.vb .page { position: relative; }

/* Hover note: anchored to its row (position: relative) so it spans the row and stays inside the well. */
.vb .hint { color: #FFFF55; cursor: help; padding: 0 2px; outline: none; }
/* Wanted table: one grid for header and rows so the columns line up. Each model is two lines:
   logo, name, price, estimate; then a full-width funding bar under the name. */
.vb .wanted { display: grid; grid-template-columns: 16px minmax(0, 1fr) 72px 44px; gap: 1px 4px; align-items: center; position: relative; }
.vb .wanted + .wanted { margin-top: 5px; }
.vb .wanted > .badge { grid-row: span 2; align-self: start; margin-top: 1px; }
.vb .wanted .wn { white-space: nowrap; line-height: 14px; }
.vb .wanted .we { text-align: right; }
.vb .wanted .fund { grid-column: 2 / -1; }
/* Funding bar: sunken well, PATTEXT fill, amount printed on top (like FT2's sample-editor readouts). */
.vb .fund { position: relative; height: 12px; overflow: hidden; }
.vb .fund i { position: absolute; left: 1px; top: 1px; bottom: 1px; background: var(--pattext); max-width: calc(100% - 2px); }
.vb .fund b { position: relative; display: block; font-weight: normal; line-height: 12px; text-align: center; color: #fff; text-shadow: 1px 1px 0 #000; white-space: nowrap; overflow: hidden; }
/* Fold-out note: summary is a pushbutton with a play-arrow; body text white, headings PATTEXT blue. */
.vb .fold { margin-top: 8px; }
.vb .fold > summary { list-style: none; display: inline-flex; height: 16px; padding: 0 5px; gap: 4px; }
.vb .fold > summary::-webkit-details-marker { display: none; }
.vb .fold > summary::before { content: "\\25B6"; font-size: 7px; }
.vb .fold[open] > summary::before { content: "\\25BC"; }
.vb .fold[open] > summary { box-shadow: inset 1px 1px 0 var(--button2); padding: 1px 4px 0 6px; }
.vb .fold-h { color: var(--pattext); margin: 8px 0 2px; }
.vb .fold p { margin: 0 0 4px; }
/* Last rows: open the note upward so the well's bottom edge doesn't cut it off. */
.vb .wanted:nth-last-of-type(-n+2) .hint:hover::after, .vb .wanted:nth-last-of-type(-n+2) .hint:focus::after { top: auto; bottom: 17px; }
.vb .hint.goal { color: #fff; padding: 0; text-decoration: underline dotted; text-underline-offset: 2px; }
.vb .hint:hover::after, .vb .hint:focus::after { content: attr(data-tip); position: absolute; left: 18px; right: 0; top: 17px; z-index: 60; white-space: normal; padding: 3px 4px; background: var(--buttons); color: #000; box-shadow: inset 1px 1px 0 var(--btnlght, #fff), inset -1px -1px 0 var(--btnshdw, #000), 0 0 0 1px #000; line-height: 11px; text-align: left; }
.vb .tabs .btn[aria-current="page"] { animation: vb-tab 260ms steps(4, end); }
@keyframes vb-tab { 0% { background: #fff; } 50% { background: var(--dsktop1); } 100% { background: var(--buttons); } }
`;

// Integer zoom (the FT2 screen is 632x400 at k x). A 1280x640 laptop viewport still gets 2x (640x320 FT2 px stage).
function pickScale() {
  return Math.max(1, Math.floor(Math.min(innerWidth / 600, innerHeight / 320)));
}

export async function mount(root, ctx) {
  const { data } = ctx;
  const native = data.dataset_kind === "native-best-of-three";
  const bestOfThree = data.ranking_policy === "best of 3" || data.repetition_groups?.some((g) => g.ranking_policy === "best of 3");
  let { page, run: slug } = ctx;
  root.append(h("style", {}, CSS + TRANSITION_CSS));
  const main = h("main", { class: "page" });
  const tabs = h("nav", { class: "tabs", "aria-label": "Pages" });
  const bar = h("header", { class: "bar raised" },
    h("div", { class: "logo", title: data.limitations?.join("\n") }, h("b", {}, "KEYGEN BENCH"), h("small", {}, data.publication_note || SITE.tagline)), tabs);
  const shell = h("div", { class: "ft2 vb" }, bar, main);
  root.append(shell);
  let raf = 0, k = 1;
  const S = { sort: native && !bestOfThree ? "name" : "score", asc: native && !bestOfThree, maker: "All", sel: slug, exh: true, scoringTab: "keygen", cohort: data.bySlug[slug]?.cohort?.key ?? data.cohorts?.[0]?.key };
  const cohortOf = (key) => (data.cohorts ?? []).find((c) => c.key === key);

  const fit = () => {
    k = pickScale();
    shell.style.zoom = k;
    shell.style.width = innerWidth / k + "px";
    shell.style.height = innerHeight / k + "px";
    shell.dataset.scale = k;
  };
  fit();
  addEventListener("resize", fit);

  function renderTabs() {
    tabs.replaceChildren(...PAGES.map((p) => h("button", { class: "btn", "aria-current": p.id === page ? "page" : null, onclick: () => ctx.go({ page: p.id }) }, native && p.id === "ranking" ? "Results" : p.label)));
  }
  const meter = (v, max, color) => h("div", { class: "meter sunken" }, h("i", { style: { width: `calc(${Math.max(0, Math.min(1, v / max)) * 100}% - 1px)`, background: color ?? "var(--pattext)" } }));
  // A group's ranked run is its best eligible predetermined ordinal. Other eligible ordinals remain playable.
  const groups = data.repetition_groups ?? [];
  const groupOf = Object.fromEntries(groups.flatMap((g) => g.attempts.filter((a) => a.slug).map((a) => [a.slug, g])));
  const modelName = (r) => groupOf[r.slug]?.name ?? r.name;
  const eligibleCount = (g) => g.eligible ?? g.attempts.filter((a) => a.eligible).length;
  const scoredCount = (g) => `${eligibleCount(g)}/${g.declared} scored`;
  const bestOrdinal = (g) => g.best_ordinal ?? g.attempts.find((a) => a.ranked)?.ordinal;
  const pendingKey = (g) => `pending:${g.cohort_key}:${g.model_key}`;
  const pendingGroup = (key) => groups.find((g) => !g.ranked_slug && !g.attempts.some((a) => a.ranked) && pendingKey(g) === key);
  const alternateAttempt = (r) => bestOfThree ? r.ranked === false : !!r.attempt_of;
  const attemptProvenance = (a) => a.provenance ?? data.bySlug[a.slug]?.provenance ?? {};
  const attemptTransport = (a) => a.transport ?? attemptProvenance(a).transport;
  const transportText = (transport) => transport
    ? `VM cpuset ${Array.isArray(transport.cpuset) ? transport.cpuset.join(",") : transport.cpuset ?? "not recorded"} | slot ${transport.slot ?? "not recorded"} | attempts/VM ${transport.attempts_per_vm ?? "not recorded"}`
    : "VM cpuset, slot and attempts/VM not recorded";
  const attemptMetadata = (a) => {
    const provenance = attemptProvenance(a);
    return [provenance.provider, provenance.tier ? `highest declared tier: ${provenance.tier}` : null,
      provenance.output_cap == null ? null : `output cap ${provenance.output_cap} tokens`, transportText(attemptTransport(a))].filter(Boolean).join(" | ");
  };
  const sc = (v) => (v == null ? "--" : v.toFixed(1));
  const reason = (cat) => String(cat ?? "pending").toLowerCase().replaceAll("_", " ");
  const why = (x) => reason(x.failure_category ?? x.status);
  // A rerun-queue attempt is the last run of its chain; the runs it superseded are labels without media.
  const supersededCause = (s) => s.attempted ? why(s) : s.stopped_by ? reason(s.stopped_by) : "not run";
  const rerunNote = (a) => a.superseded?.length ? `rerun after ${[...new Set(a.superseded.map(supersededCause))].join(", ")}` : null;
  const supersededLabel = (s, i) => `${i ? `rerun ${i}` : "first run"} ${s.attempted ? `failed (${why(s)})` : `not run${s.stopped_by ? ` (${reason(s.stopped_by)})` : ""}`}, rerun`;
  const attemptState = (a) => {
    const rerun = rerunNote(a);
    if (a.eligible) return [rerun, a.ranked ? (bestOfThree ? "best, ranked" : "ranked") : "not ranked"].filter(Boolean).join(", ");
    if (a.status === "RUNNING") return rerun ? `running (${rerun})` : "running";
    if (a.queue_pending) {
      const last = a.attempted ? a : a.superseded?.at(-1) ?? (a.stopped_by ? a : null);
      return last ? `pending rerun (${supersededCause(last)})` : "queued, not started";
    }
    const state = a.attempted ? `failed (${why(a)})` : `not run${a.stopped_by ? ` (${reason(a.stopped_by)})` : ""}`;
    return rerun ? `${state}, ${rerun}` : state;
  };
  const attemptLabel = (a) => a.eligible ? `Attempt ${a.ordinal} (${attemptState(a)})` : `Attempt ${a.ordinal}: ${attemptState(a)}`;
  const attemptTitle = (a) => `${attemptLabel(a)} | ${a.status}${a.failure_category && a.status !== "RUNNING" ? " / " + a.failure_category : ""} | ${a.source}${a.eligible && a.slug ? "" : " | no media"}${a.superseded?.length ? " | " + a.superseded.map(supersededLabel).join("; ") : ""}`;
  const SOURCE_NOTE = { "main campaign": "Main-campaign", "independent repeats campaign": "Repetition-campaign", "rerun queue": "Rerun-queue" };
  const outsideNote = (o) => `${SOURCE_NOTE[o.source] ?? "Unpublished-campaign"} attempt ${o.ordinal ?? "?"} (${[o.status, o.failure_category].filter(Boolean).join(" / ")})${o.operator_cancelled ? " was cancelled by the operator. It" : ""} is outside the frozen condition: not a repetition, never counted or replaced.`;
  const attemptedOutside = (g) => (g.outside_condition ?? []).filter((o) => o.attempted);
  const attemptOf = (r) => groupOf[r.slug]?.attempts.find((a) => a.slug === r.slug);
  const pendingReason = (g) => g.attempts.filter((a) => !a.eligible).map((a) => `Attempt ${a.ordinal}: ${attemptState(a)}`).join("; ");
  const selection = (r) => {
    const g = groupOf[r.slug];
    if (bestOfThree && g) return `${r.ranked ? `rank ${r.rank}, best of 3` : "not ranked"} | attempt ${attemptOf(r)?.ordinal ?? r.provenance.attempt_ordinal} of ${g.declared} | ${scoredCount(g)}`;
    if (!native) return r.rank ? `${r.rank} of ${data.runs.filter((x) => x.rank && x.cohort?.key === r.cohort?.key).length}` : r.failed ? "failed" : "exhibition";
    const rerun = attemptOf(r) ? rerunNote(attemptOf(r)) : null;
    if (r.attempt_of) return `attempt ${r.provenance.attempt_ordinal} of ${groupOf[r.slug].declared}: independent repetition${rerun ? ` (${rerun})` : ""}, not ranked`;
    if (r.provenance.roster_addition) return `rerun queue: attempt 1${rerun ? ` (${rerun})` : ""}; added to the roster after requalification`;
    return `${r.provenance.scope}: first valid at attempt ${r.provenance.attempt_ordinal}; ${r.usage.attempts}/3 slots attempted`;
  };
  const unrankedNote = (r) => {
    const g = groupOf[r.slug], ranked = data.bySlug[r.attempt_of];
    return bestOfThree
      ? `Not ranked. Attempt ${attemptOf(r)?.ordinal ?? r.provenance.attempt_ordinal} remains playable. Best of 3 selects attempt ${bestOrdinal(g)} (${sc(ranked?.score)}); ties select the lowest ordinal.`
      : `Not ranked. Independent predetermined repetition ${r.provenance.attempt_ordinal} under the same frozen condition; the ranked score is attempt 1's (${sc(ranked.score)}).`;
  };

  function scoreCard(r, { compact = false } = {}) {
    const parts = [["Tonal", r.parts.tonal_organization, 50], ["Develop.", r.parts.development, 40], ["Dynamics", r.parts.dynamics, 10]];
    const f = r.factors;
    return [
      h("div", { class: "row", style: { gap: "4px", padding: "1px 1px 0" } },
        badge(r.maker), alternateAttempt(r) ? h("span", { class: "unranked", title: unrankedNote(r) }, "NOT RANKED") : null, h("span", { class: "grow" }), h("span", { class: "big" }, r.score.toFixed(1))),
      h("div", { class: "shadow-text card-name", style: { padding: "0 1px" } }, modelName(r)),
      h("div", { class: "sunken", style: { padding: "3px 4px", display: "grid", gridTemplateColumns: "auto 1fr auto", gap: "2px 6px", alignItems: "center" } },
        ...parts.flatMap(([kk, v, m]) => [h("span", { class: "muted" }, kk), meter(v, m), h("span", { style: { textAlign: "right" } }, `${v.toFixed(1)}/${m}`)]),
        ...[["Signal", f.signal_integrity], ["Noise", f.noise_integrity], ["Loop", f.loop_continuity], ["Duration", f.duration_sufficiency]]
          .flatMap(([kk, v]) => [h("span", { class: "muted" }, kk), meter(v, 1, v < 0.8 ? "#FFAA00" : null), h("span", { style: { textAlign: "right" } }, "x" + v.toFixed(3))])),
      compact ? null : h("dl", { class: "kv sunken" },
        h("dt", {}, native && !bestOfThree ? "Selection" : "Rank"), h("dd", {}, selection(r)),
        h("dt", {}, "Est. cost"), h("dd", {}, money(r.cost_usd)),
        h("dt", {}, "Wall time"), h("dd", {}, r.usage.wall_minutes + " min"),
        h("dt", {}, "Flags"), h("dd", { style: { color: r.flags.length ? "#FFAA00" : "#fff" } }, r.flags.length ? r.flags.map((x) => SHORT[x.id] ?? x.id).join(" ") : "none")),
    ];
  }

  // ---------------- Tracker ----------------
  // Built once; switching tunes swaps data in place (no DOM teardown, no blank frame).
  let V = null;
  function buildViewer() {
    const playBtn = h("button", { class: "btn tbtn", style: { width: "44px" } }, "Play");
    const stopBtn = h("button", { class: "btn tbtn", style: { width: "40px" } }, "Stop");
    const time = h("span", { class: "sunken lcd", style: { width: "44px" } });
    const pos = h("span", { class: "sunken lcd", title: "Position : pattern : row", style: { width: "64px" } });
    const seek = h("div", { class: "sunken seek", style: { flex: "1", minWidth: "40px", height: "14px", position: "relative", cursor: "pointer", touchAction: "none" } });
    const seekFill = h("i", { style: { position: "absolute", left: "1px", top: "1px", bottom: "0", width: "0", background: "var(--pattext)" } });
    seek.append(seekFill);
    const chL = h("button", { class: "btn tbtn", style: { width: "18px" }, "aria-label": "Scroll channels left" }, "<");
    const chR = h("button", { class: "btn tbtn", style: { width: "18px" }, "aria-label": "Scroll channels right" }, ">");
    const chLbl = h("span", { class: "sunken lcd", style: { width: "72px" } });
    const scopeC = h("canvas", { class: "px", "aria-label": "Channel scopes" });
    const patC = h("canvas", { class: "px", "aria-label": "Pattern editor" });
    const orderList = h("div", { class: "sunken ft2-scroll", style: { flex: "1", minHeight: "0", overflowY: "auto", padding: "1px" } });
    const insList = h("div", { class: "sunken ft2-scroll", style: { flex: "1", minHeight: "0", overflowY: "auto", padding: "1px" } });
    const pickHost = h("div", { class: "row", style: { gap: "4px" } });
    const attHost = h("div", { class: "row attsw", role: "group", "aria-label": "Attempts" });
    const infoHost = h("div", { class: "sunken", style: { width: "clamp(120px, 34%, 200px)", padding: "3px 4px", display: "grid", alignContent: "center", gap: "2px", whiteSpace: "nowrap", overflow: "hidden" } });
    const cardHost = h("section", { class: "panel raised" });
    const side = h("div", { style: { gridColumn: "2", gridRow: "1 / span 3", display: "grid", gridTemplateRows: "auto minmax(0,1fr) minmax(0,1fr)", gap: "1px", minHeight: "0" } },
      cardHost,
      h("section", { class: "panel raised" }, h("h2", {}, "Instruments"), insList),
      h("section", { class: "panel raised" }, h("h2", {}, "Order list"), orderList));
    const nodes = [
      h("section", { class: "panel raised", style: { gridColumn: "1" } }, pickHost, attHost),
      h("section", { class: "panel raised", style: { gridColumn: "1" } },
        h("div", { class: "row" }, playBtn, stopBtn, time, pos, seek, chL, chLbl, chR),
        h("div", { class: "row", style: { alignItems: "stretch", gap: "3px" } }, h("div", { class: "fill", style: { height: "64px" } }, scopeC), infoHost)),
      h("section", { class: "panel raised", style: { gridColumn: "1", padding: "0" } }, h("div", { class: "fill" }, patC)),
      side,
    ];
    const v = { nodes, playBtn, stopBtn, time, pos, seek, seekFill, chL, chR, chLbl, scopeC, patC, orderList, insList, pickHost, attHost, infoHost, cardHost,
      first: 0, shown: 0, patFB: null, scopeFB: null, lastOrder: -1, lastLbl: "", lastTime: "", lastPos: "", run: null, song: null, player: null, loadToken: 0 };
    playBtn.onclick = () => v.player?.toggle();
    stopBtn.onclick = () => v.player?.stop();
    chL.onclick = () => { v.first = Math.max(0, v.first - 1); };
    chR.onclick = () => { v.first = Math.min((v.song?.channels ?? 1) - v.shown, v.first + 1); };
    // Click or drag anywhere on the timeline to jump there (works paused or playing).
    const seekTo = (e) => {
      if (!v.player) return;
      const b = seek.getBoundingClientRect();
      const dur = v.player.audio.duration || v.run.audio.duration || 0;
      const t = Math.max(0, Math.min(dur - 0.05, ((e.clientX - b.left) / b.width) * dur));
      v.player.audio.currentTime = t;
      v.seekT = t; // show the target immediately, before the media element reports seeked
    };
    seek.addEventListener("pointerdown", (e) => { seek.setPointerCapture(e.pointerId); v.seeking = true; seekTo(e); });
    seek.addEventListener("pointermove", (e) => { if (v.seeking) seekTo(e); });
    const endSeek = () => { v.seeking = false; };
    seek.addEventListener("pointerup", endSeek); seek.addEventListener("pointercancel", endSeek);
    seek.setAttribute("role", "slider"); seek.setAttribute("aria-label", "Playback position"); seek.tabIndex = 0;
    seek.addEventListener("keydown", (e) => { if (!v.player) return; const d = e.key === "ArrowRight" ? 5 : e.key === "ArrowLeft" ? -5 : 0; if (d) { e.preventDefault(); e.stopPropagation(); v.player.audio.currentTime = Math.max(0, v.player.audio.currentTime + d); } });
    patC.addEventListener("wheel", (e) => {
      const song = v.song; if (!song) return; e.preventDefault();
      const d = Math.sign(e.deltaX || (e.shiftKey ? e.deltaY : 0));
      if (d) v.first = Math.max(0, Math.min(song.channels - v.shown, v.first + d));
      else if (e.deltaY) v.player.seekOrder(Math.max(0, Math.min(song.songLength - 1, v.player.state().order + Math.sign(e.deltaY))));
    }, { passive: false });
    return v;
  }
  const sized = (fbo, c) => { const w = Math.max(40, Math.floor(c.parentElement.clientWidth)), hh = Math.max(20, Math.floor(c.parentElement.clientHeight)); return fbo && fbo.w === w && fbo.h === hh ? fbo : new FB(c, w, hh); };
  // Readouts: one fixed 8px cell per glyph (font1 digits are 7px, A-F 8px), ':'/'-'/'/' get 4px. Box width is
  // fixed too, so nothing next to it moves when the numbers change.
  function setText(el, key, val) {
    if (V[key] === val) return;
    V[key] = val;
    el.replaceChildren(...[...val].map((ch) => h("span", { class: /[:\-/ ]/.test(ch) ? "c n" : "c" }, ch)));
  }
  function drawViewer() {
    const v = V, player = v.player, song = v.song;
    const st = player ? player.state() : { time: 0, duration: v.run?.audio.duration ?? 0, playing: false, order: 0, pattern: song?.orders[0] ?? 0, row: 0, traceIndex: -1 };
    v.playBtn.textContent = st.playing ? "Pause" : "Play";
    v.playBtn.classList.toggle("pressed", st.playing);
    setText(v.time, "lastTime", mmss(st.time));
    v.time.title = mmss(st.time) + " / " + mmss(st.duration);
    setText(v.pos, "lastPos", `${fmt.hex2(st.order)}:${fmt.hex2(st.pattern)}:${fmt.hex2(st.row)}`);
    const shownT = v.seeking && v.seekT != null ? v.seekT : st.time;
    if (!v.seeking) v.seekT = null;
    v.seekFill.style.width = `calc(${(shownT / (st.duration || 1)) * 100}% - 1px)`;
    if (st.order !== v.lastOrder) {
      v.orderList.querySelector(".sel")?.classList.remove("sel");
      const el = v.orderList.querySelector(`[data-o="${st.order}"]`);
      el?.classList.add("sel"); el?.scrollIntoView({ block: "nearest" });
      v.lastOrder = st.order;
    }
    v.scopeFB = sized(v.scopeFB, v.scopeC);
    v.scopeFB.fill(0, 0, v.scopeFB.w, v.scopeFB.h, PAL.desktop);
    if (player) drawScopes(v.scopeFB, player, st, 0, 0, v.scopeFB.w, v.scopeFB.h); else v.scopeFB.frame(0, 0, v.scopeFB.w - 1, v.scopeFB.h - 1, 1);
    v.scopeFB.flush();
    v.patFB = sized(v.patFB, v.patC);
    if (song) {
      const out = drawPatternFit(v.patFB, song, st.pattern, st.row, v.patFB.w, v.patFB.h, { firstChannel: v.first });
      v.first = out.first; v.shown = out.chans;
      setText(v.chLbl, "lastLbl", out.chans >= song.channels ? `${song.channels}ch` : `${out.first + 1}-${out.first + out.chans}/${song.channels}`);
      v.chL.disabled = out.first <= 0; v.chR.disabled = out.first + out.chans >= song.channels;
    } else if (v.run && !v.run.media.xm) {
      v.patFB.fill(0, 0, v.patFB.w, v.patFB.h, PAL.desktop);
      v.patFB.frame(0, 0, v.patFB.w - 1, v.patFB.h - 1, 1);
      v.patFB.text(20, v.patFB.h >> 1, "No module: this run failed to produce one.", PAL.forgrnd);
      setText(v.chLbl, "lastLbl", "--"); v.chL.disabled = v.chR.disabled = true;
    }
    v.patFB.flush();
  }
  function viewerChrome(r) {
    const m = r.module;
    V.pickHost.replaceChildren(
      h("span", { class: "shadow-text" }, "Company"),
      dropdown({ label: "Company", items: makerItems(data), value: r.maker, width: 120, onChange: (mk) => ctx.go({ run: data.makers.find((x) => x.name === mk).runs[0].slug }) }),
      h("span", { class: "shadow-text" }, "Model"),
      dropdown({ label: "Model", items: bestOfThree ? modelItems(data, r.maker).map((item) => ({ ...item, label: modelName(data.bySlug[item.value]) })) : modelItems(data, r.maker), value: r.attempt_of ?? r.slug, width: 170, onChange: (s2) => ctx.go({ run: s2 }) }),
      h("span", { class: "grow" }),
      r.media.xm ? h("a", { class: "btn", href: data.base + r.media.xm, download: r.slug + ".xm", style: { height: "14px" } }, ".XM") : null,
      r.media.audio ? h("a", { class: "btn", href: data.base + r.media.audio, download: r.slug + ".mp3", title: "Listening derivative of canonical evaluation audio", style: { height: "14px" } }, ".MP3") : null,
      r.media.wav ? h("a", { class: "btn", href: data.base + r.media.wav, download: r.slug + ".wav", title: "Original canonical evaluation audio", style: { height: "14px" } }, ".WAV") : null,
      r.media.evaluation ? h("a", { class: "btn", href: data.base + r.media.evaluation, download: r.slug + ".json", title: "Sanitized evaluation summary and artifact hashes", style: { height: "14px" } }, ".JSON") : null);
    // Attempt switcher: every declared attempt of this model; eligible ones load in place, the others are labels.
    const g = groupOf[r.slug];
    V.attHost.style.display = g ? "" : "none";
    V.attHost.replaceChildren(...(g ? g.attempts.map((a) => a.eligible && a.slug
      ? h("button", { class: "btn", "aria-pressed": String(a.slug === r.slug), title: attemptTitle(a), onclick: () => { if (a.slug !== r.slug) ctx.go({ run: a.slug }); } }, attemptLabel(a))
      : h("span", { class: "off", title: attemptTitle(a) }, attemptLabel(a))) : []));
    V.infoHost.replaceChildren(
      h("div", { style: { color: "#fff", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, `"${m.name || "untitled"}"`),
      h("div", { class: "muted" }, `${m.channels ?? "-"} ch | ${m.bpm ?? "-"} bpm | spd ${m.speed ?? "-"}`),
      h("div", { class: "muted" }, `${m.song_length ?? "-"} pos | ${(r.audio.duration ?? 0).toFixed(1)}s | ${r.audio.lufs ?? "-"} LU`),
      h("div", { class: "muted", title: r.cohort?.label, style: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, `${r.maker} | ${r.tier}`));
    V.cardHost.replaceChildren(...scoreCard(r));
  }
  // Switch the viewer to run `s`. Keeps the old tune on screen until the new module is parsed, then swaps
  // everything in the same frame. If the old tune was playing (or was started while loading), the new one plays.
  async function loadRun(s2) {
    const r = data.bySlug[s2];
    const tok = ++V.loadToken;
    const wasPlaying = !!V.player?.playing;
    const song = r.media.xm ? await loadXM(data, r).catch(() => null) : null;
    const next = new Player(data, r, song ?? { channels: 0, instruments: [], patterns: [], orders: [0] });
    if (tok !== V.loadToken) { next.destroy(); return; }
    if (wasPlaying && r.media.audio) await new Promise((ok) => { if (next.audio.readyState >= 2) ok(); else { next.audio.addEventListener("canplay", ok, { once: true }); setTimeout(ok, 1500); } });
    if (tok !== V.loadToken) { next.destroy(); return; }
    const playing = wasPlaying || !!V.player?.playing;
    V.player?.destroy();
    V.player = next; V.song = song; V.run = r; V.first = 0; V.lastOrder = -1;
    viewerChrome(r);
    const orders = song ? song.orders.slice(0, song.songLength) : [];
    V.orderList.replaceChildren(...orders.map((p, i) => h("div", { class: "list-row", "data-o": i, onclick: () => V.player.seekOrder(i) }, fmt.hex2(i) + "  " + fmt.hex2(p))));
    V.insList.replaceChildren(...(song?.instruments ?? []).map((ins, i) => h("div", { class: "list-row", style: { color: "var(--pattext)" } }, fmt.hex2(i + 1) + " " + (ins.name || ""))));
    drawViewer();
    if (playing) next.play().catch(() => {});
  }
  function viewer() {
    main.style.gridTemplateColumns = "minmax(0,1fr) clamp(150px, 28%, 220px)";
    main.style.gridTemplateRows = "auto auto minmax(0,1fr)";
    if (!V) V = buildViewer();
    main.replaceChildren(...V.nodes);
    if (V.run?.slug !== slug) {
      if (!V.run) { V.run = data.bySlug[slug]; viewerChrome(V.run); }
      loadRun(slug);
    }
    const loop = () => { drawViewer(); raf = requestAnimationFrame(loop); };
    cancelAnimationFrame(raf);
    loop();
  }

  // ---------------- Rankings ----------------
  const COLS = [
    { k: "rank", l: native && !bestOfThree ? "Try" : "#", num: true, v: (r) => native && !bestOfThree ? r.provenance.attempt_ordinal : r.rank ?? 999, cell: (r) => native && !bestOfThree ? String(r.provenance.attempt_ordinal) : (r.rank ?? (r.failed ? "--" : "EX")), cls: "rk" },
    { k: "name", l: "Model", v: modelName, cls: "nm", cell: (r) => h("div", { class: "nmc", title: modelName(r) }, badge(r.maker), h("span", { class: "nmt" }, modelName(r) + (r.exhibition ? " *" : ""))) },
    { k: "score", l: bestOfThree ? "Best of 3" : "Score", num: true, v: (r) => r.score, cell: (r) => [h("span", { class: "sbar", style: { width: Math.round(r.score * 0.34) + "px", background: scoreColor(r.score) } }), r.score.toFixed(1)] },
    ...(bestOfThree ? [
      { k: "ordinal", l: "Try", num: true, width: 30, v: (r) => attemptOf(r)?.ordinal ?? r.provenance.attempt_ordinal, cell: (r) => String(attemptOf(r)?.ordinal ?? r.provenance.attempt_ordinal) },
      { k: "scored", l: "Scored", num: true, width: 44, v: (r) => groupOf[r.slug] ? eligibleCount(groupOf[r.slug]) : 1, cell: (r) => groupOf[r.slug] ? `${eligibleCount(groupOf[r.slug])}/${groupOf[r.slug].declared}` : "1/1" },
    ] : []),
    { k: "cost", l: "Cost", num: true, v: (r) => r.cost_usd ?? 1e9, cell: (r) => money(r.cost_usd) },
    { k: "out", l: "Out tok", num: true, v: (r) => r.usage.completion_tokens ?? 1e12, cell: (r) => (r.usage.completion_tokens == null ? "n/a" : tokens(r.usage.completion_tokens)) },
    { k: "min", l: "Min", num: true, v: (r) => r.usage.wall_minutes ?? 1e9, cell: (r) => Math.round(r.usage.wall_minutes ?? 0) },
  ];
  // Eligible ordinals switch the score breakdown; noneligible and superseded runs have labels without media.
  const attemptsPanel = (g, current, onShow) => h("section", { class: "panel raised", "data-model": g.model_key }, h("h2", {}, bestOfThree ? `Attempts | ${scoredCount(g)}` : "Attempts"),
    h("div", { class: "att sunken" }, ...g.attempts.flatMap((a) => [
      a.eligible && a.slug ? h("button", { class: "btn", "data-attempt": a.ordinal, "aria-pressed": String(a.slug === current), title: attemptTitle(a), onclick: () => onShow(a.slug) }, `Attempt ${a.ordinal}`)
        : h("span", { class: "off", "data-attempt": a.ordinal, title: attemptTitle(a) }, `Attempt ${a.ordinal}`),
      h("span", { class: a.eligible && a.slug ? (a.ranked ? null : "unranked") : "off", title: attemptTitle(a) }, attemptState(a)),
      h("span", { style: { textAlign: "right", color: "#fff" } }, a.eligible && a.slug ? sc(a.score) : ""),
      ...(bestOfThree ? [h("span", { class: "off", style: { gridColumn: "1 / -1", whiteSpace: "normal" } }, attemptMetadata(a))] : []),
      ...(a.superseded ?? []).flatMap((s, i) => [h("span", {}), h("span", { class: "off", style: { gridColumn: "2 / -1", whiteSpace: "normal" } }, supersededLabel(s, i))])])),
    ...attemptedOutside(g).map((o) => h("p", { class: "note" }, outsideNote(o))),
    g.rerun_queue ? h("p", { class: "note" }, "Provider-limit, infrastructure and unstarted attempts were rerun in a later rerun queue. Each ordinal shows its last run; superseded runs have no media and do not add attempts.") : null,
    h("p", { class: "note" }, bestOfThree
      ? "Best of 3 ranks the highest eligible score from the three predetermined ordinals. Ties select the lowest ordinal. Pick any scored attempt to show its breakdown; Open in tracker plays it. VM placement is provenance only and has no ranking effect."
      : "Ranked by attempt 1 only. Later attempts are independent predetermined repetitions under the same frozen condition, never ranked or combined with attempt 1. Pick an attempt to show it; Open in tracker plays it."));
  function ranking() {
    main.style.gridTemplateColumns = "minmax(0,1fr) clamp(160px, 27%, 200px)";
    main.style.gridTemplateRows = "auto auto minmax(0,1fr)";
    if (bestOfThree && !data.bySlug[S.sel] && !pendingGroup(S.sel)) {
      const firstPending = groups.find((g) => g.cohort_key === S.cohort && eligibleCount(g) === 0);
      S.sel = data.listed.find((r) => r.cohort?.key === S.cohort)?.slug ?? (firstPending ? pendingKey(firstPending) : S.sel);
    }
    // Alternate-attempt links select the model's ranked row while keeping the requested attempt in detail.
    if (alternateAttempt(data.bySlug[S.sel] ?? {})) { S.shown = S.sel; S.sel = data.bySlug[S.sel].attempt_of; }
    const makerDD = dropdown({ label: "Maker", items: [{ value: "All", label: "All makers" }, ...(bestOfThree ? [...new Set([...data.makers.map((m) => m.name), ...groups.map((g) => g.maker)])].sort().map((maker) => ({ value: maker, label: maker, badge: maker })) : makerItems(data))], value: S.maker, width: 130, onChange: (mk) => { S.maker = mk; renderTable(); } });
    // The toggle only filters pilot/exhibition rows; without any it would advertise a cohort that is not published.
    const exh = data.runs.some((r) => r.exhibition) ? h("button", { class: "btn", "aria-pressed": String(S.exh), style: { height: "14px" }, onclick: (e) => { S.exh = !S.exh; e.currentTarget.setAttribute("aria-pressed", String(S.exh)); renderTable(); } }, native ? "Pilot" : "Exhibitions") : null;
    // One table per cohort: max-tier and provider-default results are never listed or ranked together.
    const cohorts = data.cohorts ?? [];
    const cohortHead = h("h2", {});
    const cohortDD = cohorts.length > 1 ? dropdown({ label: "Cohort", items: cohorts.map((c) => ({ value: c.key, label: c.label })), value: S.cohort, width: 260, onChange: (key) => {
      S.cohort = key;
      if (data.bySlug[S.sel]?.cohort?.key !== key) {
        const pending = groups.find((g) => g.cohort_key === key && eligibleCount(g) === 0);
        S.sel = data.listed.find((r) => r.cohort?.key === key)?.slug ?? (pending ? pendingKey(pending) : S.sel);
        S.shown = null;
      }
      renderTable(); renderDetail();
    } }) : null;
    const tbody = h("tbody"), thead = h("thead"), colgroup = h("colgroup");
    const counts = (c) => bestOfThree ? `${data.listed.filter((r) => r.ranked && (!S.cohort || r.cohort?.key === S.cohort)).length} ranked | best of 3 | ${groups.filter((g) => !g.attempts.some((a) => a.eligible) && (!S.cohort || g.cohort_key === S.cohort)).length} pending` : native ? `${[`${c.main_first_successes} original`, c.native_continuation_successes ? `${c.native_continuation_successes} new` : null, c.archive_only_recoveries ? `${c.archive_only_recoveries} recovery` : null, c.rerun_queue_additions ? `${c.rerun_queue_additions} added in rerun queue` : null].filter(Boolean).join(" + ")} | 1 quality sample each | diagnostics, not ranks` : `${data.runs.filter((r) => r.rank).length} ranked | 1 attempt per model`;
    const countsText = h("span", { class: "shadow-text", style: { whiteSpace: "nowrap" }, title: data.limitations?.join("\n") });
    const detail = h("div", { class: "ft2-scroll detail", style: { gridColumn: "2", gridRow: "1 / span 3", display: "flex", flexDirection: "column", gap: "1px", minHeight: "0", overflowY: "auto" } });
    const top3 = h("section", { style: { gridColumn: "1", display: "grid", gridTemplateColumns: "repeat(3, minmax(0,1fr))", gap: "1px" } });
    main.replaceChildren(
      h("section", { class: "panel raised", style: { gridColumn: "1" } },
        h("div", { class: "row", style: { gap: "4px" } }, h("span", { class: "shadow-text" }, "Maker"), makerDD, exh, h("span", { class: "grow" }),
          countsText),
        cohortDD ? h("div", { class: "row", style: { gap: "4px" } }, h("span", { class: "shadow-text" }, "Cohort"), cohortDD) : null),
      top3,
      h("section", { class: "panel raised", style: { gridColumn: "1" } }, cohortHead, h("div", { class: "sunken ft2-scroll", style: { flex: "1", minHeight: "0", overflow: "auto" } }, h("table", { class: "lb" }, colgroup, thead, tbody))),
      detail);
    const select = (s2) => { S.sel = s2; S.shown = null; renderTable(); renderDetail(); };
    function renderTable() {
      const cohort = cohortOf(S.cohort);
      const col = COLS.find((c) => c.k === S.sort) ?? COLS[1];
      cohortHead.textContent = cohort ? `${cohort.label}${cohort.main_model_roster ? ` | ${cohort.results}/${cohort.main_model_roster + (cohort.roster_additions ?? 0)} with ${bestOfThree ? "an eligible" : "a valid"} result` : ""}` : "";
      countsText.textContent = counts(cohort?.selection_counts ?? data.selection_counts);
      const runs = data.listed.filter((r) => (S.maker === "All" || r.maker === S.maker) && (S.exh || !r.exhibition) && (!cohort || r.cohort?.key === cohort.key));
      const list = runs.slice().sort((a, b) => { const x = col.v(a), y = col.v(b); const d = x < y ? -1 : x > y ? 1 : 0; return (S.asc ? d : -d) || b.score - a.score; });
      colgroup.replaceChildren(...COLS.map((c) => h("col", { class: "c-" + c.k, style: c.width ? { width: c.width + "px" } : null })));
      thead.replaceChildren(h("tr", {}, ...COLS.map((c) => h("th", {
        class: c.num ? "num" : null, "aria-sort": c.k === S.sort ? (S.asc ? "ascending" : "descending") : null,
        onclick: () => { if (S.sort === c.k) S.asc = !S.asc; else { S.sort = c.k; S.asc = ["rank", "name", "cost", "min", "out"].includes(c.k); } renderTable(); },
      }, c.l + (c.k === S.sort ? (S.asc ? " \u25B2" : " \u25BC") : "")))));
      tbody.replaceChildren(...list.map((r) => h("tr", { class: (r.slug === S.sel ? "sel " : "") + (r.exhibition ? "exh" : ""), onclick: () => select(r.slug), ondblclick: () => ctx.go({ page: "viewer", run: r.slug }) },
        ...COLS.map((c) => h("td", { class: [c.num ? "num" : "", c.cls ?? ""].join(" ") }, c.cell ? c.cell(r) : c.v(r))))));
      if (bestOfThree) tbody.append(...groups.filter((g) => !g.attempts.some((a) => a.eligible) && (S.maker === "All" || g.maker === S.maker) && (!cohort || g.cohort_key === cohort.key)).map((g) =>
        h("tr", { class: pendingKey(g) === S.sel ? "sel" : "", "data-pending-model": g.model_key, title: pendingReason(g), onclick: () => select(pendingKey(g)) },
          ...COLS.map((c) => h("td", { class: [c.num ? "num" : "", c.cls ?? ""].join(" ") },
            c.k === "name" ? h("div", { class: "nmc" }, badge(g.maker), h("span", { class: "nmt" }, g.name))
              : c.k === "score" ? "Pending" : c.k === "scored" ? `${eligibleCount(g)}/${g.declared}` : "--")))));
      top3.replaceChildren(...list.filter((r) => !r.exhibition && !r.failed).sort((a, b) => bestOfThree ? a.rank - b.rank : 0).slice(0, 3).map((r, i) => h("div", { class: "panel raised", style: { flexDirection: "row", alignItems: "center", gap: "5px", cursor: "pointer" }, onclick: () => select(r.slug) },
        h("div", { class: "grow", style: { display: "grid", gap: "2px", minWidth: "0" } },
          h("div", { class: "row", style: { gap: "4px" } },
            h("span", { class: "big" }, native && !bestOfThree ? "A" + r.provenance.attempt_ordinal : String(r.rank ?? i + 1)),
            h("img", { class: "badge", src: badge(r.maker).src, style: { width: "20px", height: "20px" }, alt: "" }),
            h("span", { class: "grow" }), h("span", { class: "big" }, r.score.toFixed(1))),
          h("div", { class: "shadow-text pod-name" }, modelName(r)),
          h("div", { style: { color: "var(--dim)", whiteSpace: "nowrap" } }, `${money(r.cost_usd)} | ${Math.round(r.usage.wall_minutes)} min`)))));
    }
    function renderDetail() {
      const pending = pendingGroup(S.sel);
      if (pending) {
        detail.replaceChildren(
          h("section", { class: "panel raised" }, h("h2", {}, pending.name), h("p", { class: "note" }, `Pending | ${scoredCount(pending)}. No eligible result; no score or media.`), h("p", { class: "note" }, pendingReason(pending)), h("p", { class: "note" }, pending.tier)),
          attemptsPanel(pending, null, () => {}));
        return;
      }
      const r = data.bySlug[S.shown ?? S.sel];
      const g = groupOf[r.slug];
      const w = r.loop.worst;
      const kv = (pairs) => h("dl", { class: "kv sunken" }, ...pairs.flatMap(([a, b]) => [h("dt", {}, a), h("dd", { title: typeof b === "string" ? b : null }, b ?? "-")]));
      const nf = (v) => (v == null ? "n/a" : "$" + v);
      detail.replaceChildren(
        h("section", { class: "panel raised" }, ...scoreCard(r, { compact: true }),
          h("button", { class: "btn", style: { height: "16px" }, onclick: () => ctx.go({ page: "viewer", run: r.slug }) }, "Open in tracker")),
        ...(g ? [attemptsPanel(g, r.slug, (s2) => { S.shown = s2 === S.sel ? null : s2; renderDetail(); })] : []),
        h("section", { class: "panel raised" }, h("h2", {}, "Run"),
          kv([
            [native && !bestOfThree ? "Selection" : "Rank", selection(r)],
            ["Maker", r.maker], ["Condition", r.tier], ["Cohort", r.cohort?.label], ["Wall time", r.usage.wall_minutes + " min"],
            ["Provider", r.provenance?.provider], ["Output cap", r.provenance?.output_cap == null ? null : `${r.provenance.output_cap} tokens`],
            ...(g ? [["Attempt", `${attemptOf(r).ordinal}/${g.declared}`], ["Scored", scoredCount(g)]] : []),
            ...(bestOfThree ? [["VM placement", transportText(r.provenance?.transport ?? attemptTransport(attemptOf(r) ?? {}))]] : []),
            ...(r.exhibition ? [["Chat turns", r.usage.turns], ["Commands", r.usage.commands]] : [["Requests", r.usage.requests], ["Commands", r.usage.commands]]),
            ["In tokens", tokens(r.usage.prompt_tokens)], ["- cached", tokens(r.usage.cached_tokens)],
            ["Out tokens", tokens(r.usage.completion_tokens)], ["- reasoning", tokens(r.usage.reasoning_tokens)],
            ["Est. cost", money(r.cost_usd)],
          ]),
          alternateAttempt(r) ? h("p", { class: "note unranked" }, unrankedNote(r)) : null,
          r.exhibition ? h("p", { class: "note" }, native ? "Separate musical pilot. Excluded from main-campaign counts. Its number is an auxiliary diagnostic, not a rank." : "Run by hand in the chat app: it reports no token counts and has no per-token price. Not ranked.") : null,
          r.provenance?.recovery_note ? h("p", { class: "note" }, r.provenance.recovery_note) : null,
          r.provenance?.continuation_note ? h("p", { class: "note" }, r.provenance.continuation_note) : null,
          r.provenance?.status_note ? h("p", { class: "note" }, r.provenance.status_note) : null,
          r.provenance?.queue_note ? h("p", { class: "note" }, r.provenance.queue_note) : null),
        h("section", { class: "panel raised" }, h("h2", {}, "Price & loop"),
          kv([
            ["$/M in", nf(r.price.input_usd_per_m)], ["$/M cached", nf(r.price.cached_input_usd_per_m)], ["$/M out", nf(r.price.output_usd_per_m)],
            ["Loop quality", (r.loop.quality ?? 0).toFixed(3)],
            ["Worst restart", w ? `${w.seconds?.toFixed(1)}s` : "none"],
          ]),
          w ? h("div", { class: "sunken", style: { padding: "2px 4px", display: "flex", justifyContent: "space-between", color: "#fff" } }, h("span", { class: "muted" }, "Pos:row"),
            `${fmt.hex2(w.from_order ?? 0)}:${fmt.hex2(w.from_row ?? 0)} > ${fmt.hex2(w.to_order ?? 0)}:${fmt.hex2(w.to_row ?? 0)}`) : null,
          r.price.source_url ? h("a", { href: r.price.source_url, target: "_blank", rel: "noopener", style: { color: "#fff", padding: "0 2px" } }, "Price source") : null));
    }
    renderTable(); renderDetail();
    tbody.querySelector("tr.sel")?.scrollIntoView({ block: "nearest" });
  }

  // ---------------- Scoring ----------------
  // Help-screen layout (like FT2's Help): a few big subject buttons on the left; the right well shows
  // only the chosen subject.
  function scoring() {
    main.style.gridTemplateColumns = "150px minmax(0,1fr)";
    main.style.gridTemplateRows = "minmax(0,1fr)";
    const body = h("div", { class: "well sunken ft2-scroll", style: { flex: "1" } });
    const title = h("h2", {}, "");
    const head = (text) => h("h2", { class: "big", style: { fontSize: "20px", margin: "8px 0 6px", fontWeight: "normal" } }, text);
    const para = (t) => h("p", {}, t);
    const measure = (m) => [head(m.kind === "points" ? `${m.title} (${m.max} points)` : m.title), para(m.plain),
      h("table", { class: "plain" },
        h("tr", {}, h("td", { style: { color: "#55FF55", whiteSpace: "nowrap", verticalAlign: "top" } }, "Scores well"), h("td", { style: { color: "#fff" } }, m.good)),
        h("tr", {}, h("td", { style: { color: "#FFAA00", whiteSpace: "nowrap", verticalAlign: "top" } }, "Loses points"), h("td", { style: { color: "#fff" } }, m.bad))),
      h("p", { class: "muted" }, m.details)];
    const exampleRun = () => (data.bySlug[slug].failed ? data.runs.find((r) => r.name === "minimax-m3") ?? data.runs[0] : data.bySlug[slug]);
    const subjects = [
      { id: "keygen", label: "What is a keygen?", render: () => [head(KEYGEN.title), ...KEYGEN.lines.map(para), ...(native ? [head("Current native snapshot"), ...data.limitations.map(para)] : []), head(DISCLAIMER.title), ...DISCLAIMER.lines.map(para)] },
      { id: "overview", label: "How it works", render: () => [head("How it works"), ...OVERVIEW.map(para),
        h("pre", { class: "formula" }, ["score = music points (up to 100)", "        x clean sound", "        x no broken samples", "        x clean loop", "        x long enough"].join("\n"))] },
      { id: "points", label: "Music points", render: () => SCORING.filter((m) => m.kind === "points").flatMap(measure) },
      { id: "checks", label: "Checks", render: () => SCORING.filter((m) => m.kind !== "points").flatMap(measure) },
      { id: "example", label: "Worked example", render: () => [head("Worked example"), para("Every run's score, step by step. Pick any run."), worked(exampleRun())] },
      { id: "notes", label: "Fine print", render: () => SCORING_NOTES.flatMap((n) => [head(n.title), para(n.text),
        n.url ? h("p", {}, h("a", { href: n.url, target: "_blank", rel: "noopener" }, "Microck/keygen-bench#21")) : null,
        n.id === "flags" ? h("table", { class: "plain" }, ...Object.entries(data.flag_rules).filter(([kk]) => kk !== "RAW_XM").map(([kk, v]) => h("tr", {}, h("td", { style: { color: "#FFAA00", whiteSpace: "nowrap", verticalAlign: "top" } }, SHORT[kk] ?? kk), h("td", { style: { color: "#fff" } }, v)))) : null]) },
    ];
    const toc = h("nav", { class: "panel raised toc", "aria-label": "Sections" }, h("h2", {}, "Help subjects"));
    const show = (id) => {
      const sub = subjects.find((x) => x.id === id) ?? subjects[0];
      S.scoringTab = sub.id;
      title.textContent = sub.label;
      body.replaceChildren(...sub.render().filter(Boolean));
      body.scrollTop = 0;
      toc.querySelectorAll(".btn").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.s === sub.id)));
    };
    toc.append(...subjects.map((t) => h("button", { class: "btn", "data-s": t.id, onclick: () => show(t.id) }, t.label)));
    main.replaceChildren(toc, h("section", { class: "panel raised" }, title, body));
    show(S.scoringTab);
  }
  function worked(r0) {
    const holder = h("div", { style: { marginBottom: "8px" } });
    const render = (run) => {
      const f = run.factors;
      const rows = [
        ["Tonal structure", `${run.parts.tonal_organization.toFixed(1)} / 50`],
        ["Development", `${run.parts.development.toFixed(1)} / 40`],
        ["Dynamics", `${run.parts.dynamics.toFixed(1)} / 10`],
        ["= music points", `${run.content.toFixed(1)} / 100`],
        ["Clean sound", "x" + f.signal_integrity.toFixed(2)],
        ["No broken samples", "x" + f.noise_integrity.toFixed(2)],
        ["Clean loop", "x" + f.loop_continuity.toFixed(2)],
        ["Long enough", "x" + f.duration_sufficiency.toFixed(2) + ` (${(run.audio.duration ?? 0).toFixed(0)} s)`],
        ["= score", run.score.toFixed(1) + (run.caps.length ? " (capped)" : "")],
      ];
      holder.replaceChildren(
        h("div", { class: "row", style: { gap: "4px", margin: "2px 0 6px" } }, h("span", {}, "Pick a run:"),
          dropdown({ label: "Example run", items: data.runs.filter((x) => !x.failed).map((x) => ({ value: x.slug, label: modelName(x) + (groupOf[x.slug] ? `, attempt ${attemptOf(x).ordinal}` : "") + (x.attempt_of ? ", not ranked" : ""), badge: x.maker, right: x.score.toFixed(1) })), value: run.slug, width: 220, onChange: (s2) => render(data.bySlug[s2]) })),
        h("table", { class: "plain" }, ...rows.map(([a, b]) => h("tr", {},
          h("td", { style: { color: a.startsWith("=") ? "#fff" : null } }, a),
          h("td", { style: { color: "#fff", textAlign: "right" } }, b)))));
    };
    render(r0);
    return holder;
  }

  function currentSupport() {
    main.style.gridTemplateColumns = "minmax(0,1fr) minmax(0,1fr)";
    main.style.gridTemplateRows = groups.length ? "auto minmax(0,1.2fr) minmax(0,1fr)" : "auto minmax(0,1fr)";
    // Rosters, availability and pending states are counted within each cohort, never across cohorts.
    const cohorts = (data.cohorts?.length ? data.cohorts : [{ key: undefined, label: "", selection_counts: data.selection_counts }]);
    const inCohort = (key, cohortKey) => cohortKey === undefined || key === cohortKey;
    const pilots = data.runs.filter((run) => run.provenance.scope === "pilot");
    const states = cohorts.map((cohort) => {
      // Models a rerun queue added after requalification join the main roster's pending and available counts.
      const roster = data.campaigns.flatMap((campaign) => campaign.roster.filter((model) => campaign.scope === "main" || model.roster_addition)).filter((model) => inCohort(model.cohort_key, cohort.key));
      const members = data.runs.filter((run) => inCohort(run.cohort?.key, cohort.key));
      const available = new Set(members.filter((run) => run.provenance.scope !== "pilot").map((run) => run.model_key));
      const retainedPilot = new Set(members.filter((run) => run.provenance.scope === "pilot").map((run) => run.model_key));
      const excluded = (data.excluded_models ?? []).filter((model) => inCohort(model.cohort_key, cohort.key));
      return { cohort, roster, excluded, pending: bestOfThree ? groups.filter((g) => inCohort(g.cohort_key, cohort.key) && eligibleCount(g) === 0) : roster.filter((model) => !available.has(model.model_key) && !retainedPilot.has(model.model_key)) };
    });
    const named = states.length > 1;
    main.replaceChildren(
      h("section", { class: "panel raised", style: { gridColumn: "1 / -1" } },
        h("h2", {}, "Current campaign snapshot"),
        h("div", { class: "well sunken" },
          ...states.map(({ cohort, roster, pending, excluded }) => {
            if (bestOfThree) {
              const members = groups.filter((g) => inCohort(g.cohort_key, cohort.key));
              const ranked = members.filter((g) => eligibleCount(g) > 0).length;
              const pendingCount = members.length - ranked;
              return h("p", {}, `${named ? cohort.label + ": " : ""}${ranked}/${members.length} models have an eligible result, ranked best of 3. ${pendingCount} ${pendingCount === 1 ? "model is" : "models are"} pending. Scored counts and the reason for every unscored ordinal appear in each model's attempts.`);
            }
            const c = cohort.selection_counts ?? data.selection_counts;
            const items = [`${c.main_first_successes} original first successes`, c.native_continuation_successes ? `${c.native_continuation_successes} native continuation results` : null,
              c.archive_only_recoveries ? `${c.archive_only_recoveries} archive-only ${c.archive_only_recoveries === 1 ? "recovery" : "recoveries"}` : null,
              c.rerun_queue_additions ? `${c.rerun_queue_additions} rerun-queue ${c.rerun_queue_additions === 1 ? "addition" : "additions"}` : null].filter(Boolean);
            const list = items.length > 1 ? `${items.slice(0, -1).join(", ")} and ${items.at(-1)}` : items[0];
            const withheld = excluded.length ? `; ${excluded.length} more ${excluded.length === 1 ? "model was" : "models were"} excluded before launch` : "";
            const added = cohort.roster_additions ? ` plus ${cohort.roster_additions} ${cohort.roster_additions === 1 ? "model" : "models"} added in the rerun queue after requalification` : "";
            return h("p", {}, `${named ? cohort.label + ": " : ""}${list} are available from the ${roster.length - (cohort.roster_additions ?? 0)}-model main roster${added}. ${pending.length} models have no eligible published output${withheld}.`); }),
          ...cohorts.filter((cohort) => cohort.repetitions).map((cohort) => {
            const n = cohort.repetitions, q = n.rerun_queue;
            return h("p", {}, bestOfThree
              ? `${named ? cohort.label + ": " : ""}Best of 3 ranks each model's highest eligible score from three predetermined ordinals. All eligible ordinals remain playable with separate score breakdowns. Infrastructure reruns replace an ordinal, never add an attempt.`
              : `${named ? cohort.label + ": " : ""}Ranked by attempt 1 only. ${n.models} models also ran later predetermined independent repetitions under the same frozen condition; ${n.unranked_playable_attempts} of those later attempts are eligible and playable from the attempt switcher, labeled not ranked.${q ? ` A later rerun queue reran provider-limit, infrastructure and unstarted attempts of ${q.models} models: ${q.rerun_attempts} ${q.rerun_attempts === 1 ? "attempt shows its" : "attempts show their"} rerun; ${q.pending_reruns} ${q.pending_reruns === 1 ? "is" : "are"} still running or awaiting a run.` : ""}`);
          }),
          ...pilots.map((run) => h("p", {}, `${run.name} is retained as a pilot-only result, outside main counts. This preview does not request another attempt for it.`)),
          h("p", {}, "No donation totals or confirmed payment links are published in this preview. Funding and availability can block unfinished work; no missing model receives a fabricated zero score."))),
      ...(groups.length ? [h("section", { class: "panel raised", style: { gridColumn: "1 / -1" } }, h("h2", {}, bestOfThree ? "Every attempt | best of 3" : "Every attempt (only attempt 1 is ranked)"),
        h("div", { class: "well sunken ft2-scroll" }, ...groups.flatMap((g) => [
          h("p", { style: { margin: attemptedOutside(g).length ? "0" : null } }, h("span", { style: { color: "#fff" } }, `${g.name}${bestOfThree ? ` (${scoredCount(g)})` : ""}: `), g.attempts.map((a) => `${attemptLabel(a)}${a.eligible && a.slug ? " " + sc(a.score) : ""}${a.superseded?.length ? ` [${a.superseded.map(supersededLabel).join("; ")}]` : ""}`).join(" | ")),
          ...attemptedOutside(g).map((o, i, all) => h("p", { class: "muted", style: { margin: i === all.length - 1 ? null : "0" } }, outsideNote(o)))])))] : []),
      h("section", { class: "panel raised" }, h("h2", {}, "Pending: no eligible result"),
        h("div", { class: "well sunken ft2-scroll" }, ...states.flatMap(({ cohort, pending, excluded }) => [
          named && (pending.length || excluded.length) ? h("p", { style: { color: "#fff" } }, `${cohort.label} (state at metadata capture)`) : null,
          ...pending.map((model) => h("p", {}, `${model.name}: ${bestOfThree ? `${scoredCount(model)}; ${model.reason ?? pendingReason(model)}` : model.reason ?? `original ${model.state}, ${model.attempts} historical attempts`}`)),
          ...excluded.map((model) => h("p", {}, `${model.name}: excluded before launch, ${model.reason}`))]))),
      h("section", { class: "panel raised" }, h("h2", {}, "Publication limits"),
        h("div", { class: "well sunken ft2-scroll" }, ...data.limitations.map((note) => h("p", {}, note)))));
  }

  // ---------------- Support ----------------
  function support() {
    if (native || bestOfThree) { currentSupport(); return; }
    main.style.gridTemplateColumns = "minmax(0,1fr) minmax(0,1fr)";
    main.style.gridTemplateRows = "auto auto minmax(0,1fr)";
    const priced = data.runs.filter((r) => r.cost_usd != null);
    const total = priced.reduce((a, r) => a + r.cost_usd, 0);
    main.replaceChildren(
      h("section", { class: "panel raised", style: { gridColumn: "1 / -1" } },
        h("div", { class: "big", style: { textAlign: "center", padding: "6px 0 4px" } }, SUPPORT.heading.toUpperCase()),
        h("div", { class: "well sunken" }, ...SUPPORT.paragraphs.map((p) => h("p", { style: { margin: "0 auto 7px" } }, p)))),
      h("section", { class: "panel raised" }, h("h2", {}, "Fund a specific model"),
        h("div", { class: "well sunken" }, h("p", {}, "Pick a model from the wanted list and name it in your donation note."),
          h("div", { class: "row" }, h("a", { class: "btn cta", href: SITE.sponsors, target: "_blank", rel: "noopener" }, "GitHub Sponsors"), h("a", { class: "btn cta", href: SITE.kofi, target: "_blank", rel: "noopener" }, "Ko-fi")))),
      h("section", { class: "panel raised" }, h("h2", {}, "Keep future runs going"),
        h("div", { class: "well sunken" }, h("p", {}, "Monthly support pays for testing each new release as it ships."),
          h("div", { class: "row" }, h("a", { class: "btn cta", href: SITE.sponsors, target: "_blank", rel: "noopener" }, "Sponsor monthly"), h("a", { class: "btn cta", href: SITE.kofi, target: "_blank", rel: "noopener" }, "One-off on Ko-fi")))),
      h("section", { class: "panel raised" }, h("h2", {}, "Wanted: untested models"),
        h("div", { class: "sunken ft2-scroll", style: { flex: "1", padding: "2px", overflow: "auto" } },
          h("div", { class: "muted wanted" }, h("span", { style: { gridColumn: "1 / span 2" } }, "Model"), h("span", {}, "Price in/out"), h("span", { class: "we" }, "Est.")),
          ...SUPPORT.wanted.map((w) => {
            const range = `Typical run ${usd(w.typical)}. Long run ${usd(w.est)} (the estimate). Heavy run ${usd(w.heavy)}.`;
            const pct = Math.min(100, (w.raised / w.est) * 100);
            const raised = `${usd(w.raised)} of ${usd(w.est)} raised`;
            return h("div", { class: "wanted" },
              badge(w.maker),
              h("span", { class: "wn" }, w.model,
                w.tip ? h("span", { class: "hint", tabindex: "0", "aria-label": w.tip, "data-tip": w.tip }, "*") : null),
              h("span", { class: "muted" }, w.price),
              h("span", { class: "hint goal we", tabindex: "0", "aria-label": range, "data-tip": range }, usd(w.est)),
              h("span", { class: "fund sunken", role: "progressbar", "aria-label": raised, "aria-valuemin": "0", "aria-valuemax": String(w.est), "aria-valuenow": String(w.raised), title: raised },
                h("i", { style: { width: pct + "%" } }),
                h("b", {}, raised)));
          }),
          h("details", { class: "fold" },
            h("summary", { class: "btn" }, SUPPORT.costHelp.summary),
            ...SUPPORT.costHelp.sections.flatMap((g) => [
              h("div", { class: "fold-h" }, g.title),
              ...g.lines.map((l) => h("p", {}, l)),
            ])))),
      h("section", { class: "panel raised" }, h("h2", {}, `Spent so far: ${money(total)} (${priced.length} runs, list price)`),
        h("div", { class: "sunken ft2-scroll", style: { flex: "1", overflow: "auto", padding: "2px" } },
          ...priced.slice().sort((a, b) => b.cost_usd - a.cost_usd).map((r) => h("div", { class: "row", style: { height: "18px" } }, badge(r.maker), h("span", { class: "grow muted" }, r.name), h("span", {}, money(r.cost_usd)))))));
  }

  function renderPage() {
    cancelAnimationFrame(raf);
    renderTabs();
    if (page === "viewer") viewer();
    else if (page === "ranking") ranking();
    else if (page === "scoring") scoring();
    else support();
  }
  // Page change: freeze the old page as a ghost over the new one, then run the slide-deck transition
  // (core/transitions.js) on both panel lists. A new change mid-transition cancels the old one.
  let lastPage = page, fxRun = 0;
  const topPanels = (root) => [...root.querySelectorAll(".panel, .toc")].filter((el) => !el.parentElement.closest(".panel, .toc"))
    .map((el) => ({ el, r: el.getBoundingClientRect() }))
    .sort((a, b) => (Math.abs(a.r.top - b.r.top) < 4 ? a.r.left - b.r.left : a.r.top - b.r.top)).map((x) => x.el);
  function transition(forceDir) {
    const dir = forceDir ?? (PAGES.findIndex((p) => p.id === page) >= PAGES.findIndex((p) => p.id === lastPage) ? 1 : -1);
    lastPage = page;
    const my = ++fxRun;
    shell.querySelectorAll(".ghost").forEach((g) => g.remove());
    main.querySelectorAll("[class*=' t-'], [class^='t-']").forEach((el) => [...el.classList].filter((c) => c.startsWith("t-")).forEach((c) => el.classList.remove(c)));
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { renderPage(); return; }
    const ghost = main.cloneNode(true);
    ghost.classList.add("ghost");
    const srcC = main.querySelectorAll("canvas");
    ghost.querySelectorAll("canvas").forEach((c, i) => { const s2 = srcC[i]; if (s2?.width) { c.width = s2.width; c.height = s2.height; c.getContext("2d").drawImage(s2, 0, 0); } });
    ghost.style.cssText = main.style.cssText + `;position:absolute;left:${main.offsetLeft}px;top:${main.offsetTop}px;width:${main.offsetWidth}px;height:${main.offsetHeight}px;`;
    shell.append(ghost);
    renderPage();
    const total = slide({ outs: topPanels(ghost), ins: topPanels(main), dir, root: main });
    setTimeout(() => {
      if (my !== fxRun) return;
      ghost.remove();
      for (const el of main.querySelectorAll("*")) for (const c of [...el.classList]) if (c.startsWith("t-")) el.classList.remove(c);
    }, total);
  }
  renderPage();
  return {
    update(p) {
      const pageChanged = p.page !== page, runChanged = p.run !== slug;
      page = p.page; slug = p.run;
      if (pageChanged) transition();
      else if (runChanged && page === "viewer") loadRun(slug);
      else if (runChanged) renderPage();
    },
    destroy() { cancelAnimationFrame(raf); V?.player?.destroy(); removeEventListener("resize", fit); },
  };
}
