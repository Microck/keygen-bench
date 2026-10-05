"""Write benchmark/runs/index.html: one row per model with its final attempt's tune, video and records.
Reads final.json from aggregate.py. Media is served from the runs dir itself (restart-results-server.sh),
so every link is relative."""
import html
import json
import math
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, "/home/ubuntu/workspace/keygen-benchmark/benchmark")
import score

T = Path(__file__).parent
RUNS = Path("/home/ubuntu/workspace/keygen-benchmark/benchmark/runs")
rows = json.loads((T / "final.json").read_text())

FILES = [("original WAV", "canonical/canonical.wav"), ("video", "visualizer/visualizer.mp4"), ("xm", "submission/tune.xm"),
         ("playback trace", "playback/trace.jsonl"), ("trajectory", "trajectory.json"), ("status", "status.json"),
         ("profile / score evidence", "profile.json"), ("worker.log", "worker.log")]

def finite_json(value):
    """JSON null represents unavailable or nonfinite measurements."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json(v) for v in value]
    return value


def rounded(value, digits=0):
    return round(value, digits) if isinstance(value, (int, float)) and math.isfinite(value) else None


def artifact_url(directory, run_dir, relative):
    """Only link existing artifacts inside this attempt; encode paths as URLs."""
    path = (directory / relative).resolve()
    if not path.is_relative_to(directory.resolve()) or not path.is_file():
        return None
    return quote(f"{run_dir}/{path.relative_to(directory.resolve()).as_posix()}", safe="/")


def row_data(r):
    if r.get("score_version") != score.SCORE_VERSION:
        raise ValueError(f"{r['run_dir']}: stale score version; run aggregate.py before building the page")
    d = RUNS / r["run_dir"]
    loop = r.get("loop") or {}
    preview = loop.get("preview") or {}
    artifacts = [("loop excerpt (lossless)", preview["path"])] if preview.get("path") else []
    artifacts += FILES
    for name, field in (("loop trace", "trace_path"), ("loop evidence", "evidence_path")):
        if loop.get(field):
            artifacts.append((name, loop[field]))
    files = {name: url for name, rel in artifacts if (url := artifact_url(d, r["run_dir"], rel))}
    # the model's own scripts, so a listener can see how the tune was built
    sub = d / "submission"
    scripts = sorted(p.name for p in sub.iterdir() if p.is_file() and p.suffix in (".py", ".sh", ".txt", ".md", ".json")) if sub.exists() else []
    st, au, pr = r.get("structure") or {}, r.get("audio") or {}, r.get("process") or {}
    craft, mix = r.get("craft") or {}, r.get("mix") or {}
    if craft.get("version") != score.SCORE_VERSION:
        raise ValueError(f"{r['run_dir']}: craft version does not match {score.SCORE_VERSION}")
    wall_seconds = r.get("wall_seconds")
    return {"model": r["model"], "tier": r["tier"], "budget": r["budget"], "status": r["status"], "craft": craft.get("craft_score"),
            "score_version": r["score_version"], "parts": craft.get("parts") or {}, "weights": score.CRAFT_WEIGHTS,
            "capped": craft.get("capped", False), "caps": craft.get("caps") or [], "uncapped": craft.get("uncapped"), "score_note": craft.get("note") or "",
            "content_score": craft.get("content_score"), "factors": craft.get("factors") or {}, "spectral": au.get("spectral") or {},
            "mix": mix, "mix_error": r.get("mix_error") or "", "loop": loop, "loop_error": r.get("loop_error") or "", "flags": r.get("flags") or [],
            "dur": rounded(au.get("duration_seconds"), 1), "lufs": rounded(au.get("lufs_integrated"), 1),
            "chans": st.get("channels_used"), "patterns": st.get("distinct_patterns_in_order"), "instr": st.get("instruments_used"), "samples": st.get("samples"),
            "steps": (r.get("totals") or {}).get("requests"), "min": rounded(wall_seconds / 60) if wall_seconds is not None else None, "attempts": r.get("attempts"),
            "ft2": pr.get("used_ft2_tools"), "raw_xm": pr.get("wrote_xm_directly"), "error": r.get("error") or "",
            "files": files, "scripts": [quote(f"{r['run_dir']}/submission/{n}", safe="/") for n in scripts], "run_dir": r["run_dir"]}

data = finite_json([row_data(r) for r in rows])
n_rendered = sum(d["status"] == "RENDERED_UNSCORED" for d in data)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keygen bench results</title>
<style>
:root{color-scheme:dark}
body{margin:0;padding:12px 16px;background:#000;color:#fff;font:13px/1.35 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
h1{font-size:15px;font-weight:600;margin:0 0 8px}
.bar{display:flex;gap:12px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
input{background:#000;color:#fff;border:1px solid #444;padding:4px 6px;font:inherit;width:220px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid #222;white-space:nowrap;vertical-align:top}
th{cursor:pointer;color:#bbb;font-weight:500;user-select:none}
th.on{color:#fff}
tr.r{cursor:pointer}
tr.r:hover td{background:#111}
td.num{text-align:right;padding-right:14px}
.ok{color:#fff}.fail{color:#f66}.blk{color:#fc6}.cap{color:#fc6}
tr.d td{white-space:normal;padding:8px 0 14px;border-bottom:1px solid #333}
.det{display:grid;grid-template-columns:minmax(320px,640px) 1fr;gap:16px}
video{width:100%;max-width:640px;background:#000;display:block}
audio{width:100%;display:block;margin:0 0 8px}
.loop-controls{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.loop-controls button{background:#111;color:#fff;border:1px solid #444;padding:8px;font:inherit;min-height:40px;text-align:left;cursor:pointer}
.loop-controls button:hover{border-color:#bbb}
.loop-controls button:focus-visible{outline:2px solid #8cf;outline-offset:2px}
.loop-controls button:disabled{color:#bbb;cursor:wait}
.loop-controls button small{display:block;color:#bbb;font:inherit}
.evidence{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;margin:6px 0 12px}
.transitions{padding-left:20px}
.transitions li{margin-bottom:8px}
.det a{color:#8cf;text-decoration:none;margin-right:12px}
.det a:hover{text-decoration:underline}
.kv{margin:0 0 8px}.kv b{color:#bbb;font-weight:500}
.parts span{margin-right:10px}
@media (max-width:900px){.det{grid-template-columns:1fr}}
</style></head><body>
<h1>Keygen bench, highest thinking tier per model</h1>
<p class="kv">Deterministic __SCORE_VERSION__, 0-100. Provisional tonal-development indicator, not a validated musical-quality rating.<br>
Content weights: __CRAFT_WEIGHTS__. Multiply content points by signal integrity, sustained-noise integrity, bounded loop continuity and duration sufficiency; artifact caps apply.
Duration factor = min(1, first-pass audible seconds / __DURATION_SUFFICIENT_SECONDS__). Later playback and silence add no duration credit; longer tunes earn no bonus. No human or LLM judges; no process points.<br>
Full-band audio supplies tonal and sustained-noise evidence. Mix clarity is diagnostic only.
Loop previews play the continuous reference FT2 recording used to measure runtime transitions.
Tonal, noise, DC and restart level/timbre bounds give full credit at the level of typical archived keygen music (<a href="scoring-reference.json">calibration and held-out validation</a>); clean-loop click, gap and rhythm bounds are unchanged.
The short-duration policy uses a <a href="duration-reference.json">256-module historical reference sample</a>, not a claim that short loops are inauthentic.
Original canonical WAVs and videos remain available. Latest attempt per model; exhibitions are separate.</p>
<div class="bar"><input id="q" placeholder="filter model" autocomplete="off"><span id="count"></span><span>click a row for tune, video and files</span></div>
<table><thead><tr>
<th data-k="model">model</th><th data-k="tier">tier</th><th data-k="status">status</th><th data-k="craft" class="on">craft</th><th data-k="dur">len s</th><th data-k="lufs">LUFS</th><th data-k="chans">ch</th><th data-k="patterns">pat</th><th data-k="instr">ins</th><th data-k="steps">steps</th><th data-k="min">min</th><th>flags</th>
</tr></thead><tbody id="tb"></tbody></table>
<script>
const DATA=__DATA__;
const NUM=new Set(["craft","dur","lufs","chans","patterns","instr","steps","min"]);
let sortK="craft",sortAsc=false,open=new Set();
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cls=s=>s==="RENDERED_UNSCORED"?"ok":s.startsWith("BLOCKED")?"blk":"fail";
const short=s=>s==="RENDERED_UNSCORED"?"rendered":s.toLowerCase();
const fmt=(v,digits=3)=>typeof v==="number"&&Number.isFinite(v)?v.toFixed(digits):"?";
const evidence=v=>esc(JSON.stringify(v,null,2));
function loopControls(loop){
  const preview=loop.preview??{},start=preview.start_seconds,duration=preview.duration_seconds;
  if(!Number.isFinite(start)||!Number.isFinite(duration))return "";
  return (preview.markers_seconds??[]).filter(marker=>Number.isFinite(marker)&&marker>=0&&marker<duration).map(marker=>{
    const seconds=start+marker;
    const transition=(loop.transitions??[]).find(t=>Number.isFinite(t.seconds)&&Math.abs(t.seconds-seconds)<=1/44100);
    const kind=transition?.kind??"transition";
    return `<button type="button" data-loop-seek="${esc(Math.max(0,marker-3))}">Listen across loop at ${esc(fmt(marker,6))} s<small>${esc(kind)}; runtime ${esc(fmt(transition?.seconds??seconds,6))} s${Number.isInteger(transition?.frame)?`, frame ${esc(transition.frame)}`:""}</small></button>`;
  }).join("");
}
function detail(d){
  const f=d.files,links=[];
  for(const [k,v] of Object.entries(f)) links.push(`<a href="${esc(v)}" ${["xm","original WAV","video","loop excerpt (lossless)"].includes(k)?"download":'target="_blank" rel="noopener"'}>${esc(k)}</a>`);
  const scripts=d.scripts.map(p=>`<a href="${esc(p)}" target="_blank" rel="noopener">${esc(decodeURIComponent(p.split("/").pop()))}</a>`).join("");
  const parts=Object.entries(d.parts).map(([k,v])=>`<span>${esc(k)} ${esc(fmt(v))}</span>`).join("");
  const weights=Object.entries(d.weights).map(([k,v])=>`<span>${esc(k)} ${esc(v??"?")}</span>`).join("");
  const factors=Object.entries(d.factors).map(([k,v])=>`<span>${esc(k)} ${esc(fmt(v,6))}</span>`).join("");
  const caps=d.caps.map(c=>`<span class="cap">ceiling ${esc(c.ceiling??"?")}: ${esc(c.reason)}</span>`).join("; ");
  const mix=d.mix,lead=(mix.lead_channels??[]).filter(Number.isInteger).map(c=>c+1).join(", ");
  const loop=d.loop,preview=loop.preview??{},previewURL=f["loop excerpt (lossless)"];
  const transitions=(loop.transitions??[]).map(t=>`<li>${esc(t.kind??"transition")} at runtime ${esc(fmt(t.seconds,6))} s, PCM frame ${esc(t.frame??"?")}${t.from_order!=null?`; order ${esc(t.from_order)}, row ${esc(t.from_row??"?")} to order ${esc(t.to_order??"?")}, row ${esc(t.to_row??"?")}`:""}${t.metrics?`<pre class="evidence">${evidence(t.metrics)}</pre>`:""}${t.components?`<pre class="evidence">${evidence(t.components)}</pre>`:""}</li>`).join("");
  const audioURL=previewURL??f["original WAV"];
  const media=audioURL?`<div class="loop-player"><p class="kv"><b>${previewURL?"Loop excerpt (lossless)":"Original canonical audio; scored loop excerpt unavailable"}</b></p><audio controls preload="none" src="${esc(audioURL)}"></audio>${previewURL?`<p class="kv">An excerpt of the scored continuous FT2 capture, not a stitched restart. It begins at runtime ${esc(fmt(preview.start_seconds,6))} s and lasts ${esc(fmt(preview.duration_seconds,6))} s. Buttons start up to 3 s before each marked transition.</p><div class="loop-controls">${loopControls(loop)}</div><p class="kv playback-status" role="status" aria-live="polite"></p>`:""}</div>`:"<div>no audio render</div>";
  return `<div class="det"><div>${media}${f.video?`<p class="kv"><b>Original video</b></p><video controls preload="none" src="${esc(f.video)}"></video>`:""}</div><div>
  <p class="kv"><b>files</b> ${links.join("")}</p>
  ${scripts?`<p class="kv"><b>submission</b> ${scripts}</p>`:""}
  <p class="kv"><b>score</b> ${esc(d.score_version)}, ${esc(d.craft??"?")}/100${d.uncapped!=null?`, uncapped ${esc(d.uncapped)}`:""}</p>
  <p class="kv"><b>content points</b> ${esc(fmt(d.content_score,2))}/100; <span class="parts">${parts||"none"}</span></p>
  <p class="kv"><b>weights</b> <span class="parts">${weights||"none"}</span></p>
  <p class="kv"><b>multiplicative factors</b> <span class="parts">${factors||"none"}</span></p>
  <p class="kv"><b>duration evidence</b> ${esc(fmt(loop.first_pass_audible_seconds,3))} audible seconds in the ${esc(fmt(loop.analysis_duration_seconds,3))} s first pass; full duration credit at __DURATION_SUFFICIENT_SECONDS__ s. This is a sufficiency policy, not a minimum length for authentic keygen music. Authored repetitions within the first pass still count.</p>
  <p class="kv"><b>caps</b> ${caps||"none"}</p>
  ${d.score_note?`<p class="kv"><b>score note</b> ${esc(d.score_note)}</p>`:""}
  ${Object.keys(d.spectral).length?`<details><summary>Full-band tonal and sustained-noise evidence</summary><pre class="evidence">${evidence(d.spectral)}</pre></details>`:""}
  <p class="kv"><b>loop evidence</b> quality ${esc(fmt(loop.quality_score))}/1; status ${esc(loop.status??"unavailable")}. This measures recorded transition continuity, not musical resolution.</p>
  <p class="kv"><b>reference renderer</b> ${esc(loop.renderer??"unavailable")}</p>
  ${loop.provenance?`<details><summary>Native renderer provenance</summary><pre class="evidence">${evidence(loop.provenance)}</pre></details>`:""}
  ${loop.components?`<p class="kv"><b>loop components</b></p><pre class="evidence">${evidence(loop.components)}</pre>`:""}
  ${loop.evidence?`<details><summary>Loop measurements</summary><pre class="evidence">${evidence(loop.evidence)}</pre></details>`:""}
  ${transitions?`<details><summary>Recorded transitions (${esc(loop.transitions.length)})</summary><ol class="transitions">${transitions}</ol></details>`:""}
  ${d.loop_error?`<p class="kv"><b>loop analysis error</b> ${esc(d.loop_error)}</p>`:""}
  <p class="kv"><b>mix diagnostic, not scored</b> clarity ${esc(fmt(mix.clarity_score))}/1, masking fraction ${esc(fmt(mix.masking_fraction))}/1, candidate lead channels ${esc(lead||"none")}. Channels are numbered from 1; musical roles remain uncertain.</p>
  <p class="kv"><b>mix analysis</b> ${esc(mix.method||"unavailable")}; renderer ${esc(mix.renderer_version||"unavailable")}; analyzed ${esc(fmt(mix.analysis_duration_seconds,1))} s</p>
  ${mix.evidence?`<details><summary>Mix measurements</summary><pre class="evidence">${evidence(mix.evidence)}</pre></details>`:""}
  ${d.mix_error?`<p class="kv"><b>mix analysis error</b> ${esc(d.mix_error)}</p>`:""}
  <p class="kv"><b>process, not scored</b> ft2 tools ${esc(d.ft2??"?")}, raw xm ${esc(d.raw_xm??"?")}, samples ${esc(d.samples??"?")}, attempts ${esc(d.attempts??"?")}, budget ${esc(d.budget)}</p>
  ${d.error?`<p class="kv"><b>note</b> ${esc(d.error)}</p>`:""}
  <p class="kv"><b>dir</b> ${esc(d.run_dir)}</p></div></div>`;
}
let playbackRequest=null;
function render(){
  playbackRequest?.abort();
  const q=document.getElementById("q").value.toLowerCase();
  let rows=DATA.filter(d=>d.model.toLowerCase().includes(q));
  rows.sort((a,b)=>{let x=a[sortK],y=b[sortK];if(NUM.has(sortK)){x=x??-1e9;y=y??-1e9;return sortAsc?x-y:y-x}x=String(x);y=String(y);return sortAsc?x.localeCompare(y):y.localeCompare(x)});
  document.getElementById("count").textContent=`${rows.length} of ${DATA.length} models, __RENDERED__ rendered`;
  const h=[];
  for(const d of rows){
    h.push(`<tr class="r" data-m="${esc(d.model)}"><td>${esc(d.model)}</td><td>${esc(d.tier)}</td><td class="${cls(d.status)}">${esc(short(d.status))}</td><td class="num">${esc(d.craft??"")}</td><td class="num">${esc(d.dur??"")}</td><td class="num">${esc(d.lufs??"")}</td><td class="num">${esc(d.chans??"")}</td><td class="num">${esc(d.patterns??"")}</td><td class="num">${esc(d.instr??"")}</td><td class="num">${esc(d.steps??"")}</td><td class="num">${esc(d.min??"")}</td><td>${esc(d.flags.join(" "))||"-"}</td></tr>`);
    if(open.has(d.model)) h.push(`<tr class="d"><td colspan="12">${detail(d)}</td></tr>`);
  }
  document.getElementById("tb").innerHTML=h.join("");
  document.querySelectorAll("th[data-k]").forEach(t=>t.classList.toggle("on",t.dataset.k===sortK));
}
document.getElementById("tb").addEventListener("click",e=>{const tr=e.target.closest("tr.r");if(!tr)return;const m=tr.dataset.m;open.has(m)?open.delete(m):open.add(m);render()});
document.getElementById("tb").addEventListener("click",async e=>{
  const button=e.target.closest("button[data-loop-seek]");
  if(!button||button.disabled)return;
  const player=button.closest(".loop-player"),audio=player.querySelector("audio"),status=player.querySelector(".playback-status");
  const buttons=player.querySelectorAll("button[data-loop-seek]");
  buttons.forEach(control=>{control.disabled=true;});
  playbackRequest?.abort();
  const request=new AbortController();
  playbackRequest=request;
  request.signal.addEventListener("abort",()=>{audio.pause();status.textContent="Playback stopped.";},{once:true});
  status.textContent="Loading loop excerpt...";
  try{
    if(audio.readyState<1)await new Promise((resolve,reject)=>{
      const cleanup=()=>{audio.removeEventListener("loadedmetadata",loaded);audio.removeEventListener("error",failed);request.signal.removeEventListener("abort",cancelled);};
      const loaded=()=>{cleanup();resolve();};
      const failed=()=>{cleanup();reject(new Error("Audio could not be loaded."));};
      const cancelled=()=>{cleanup();reject(new DOMException("Superseded playback request","AbortError"));};
      request.signal.addEventListener("abort",cancelled,{once:true});
      audio.addEventListener("loadedmetadata",loaded,{once:true});
      audio.addEventListener("error",failed,{once:true});
      audio.load();
    });
    if(request.signal.aborted||!player.isConnected)return;
    document.querySelectorAll("audio,video").forEach(other=>{if(other!==audio)other.pause();});
    audio.currentTime=Number(button.dataset.loopSeek);
    await audio.play();
  }catch{
    if(request.signal.aborted)return;
    status.textContent="Could not play the loop excerpt. Try the audio controls or download the lossless excerpt.";
  }finally{
    buttons.forEach(control=>{control.disabled=false;});
  }
});
for(const event of ["playing","pause","ended"]){
  document.getElementById("tb").addEventListener(event,e=>{
    if(!e.target.matches(".loop-player audio"))return;
    e.target.closest(".loop-player").querySelector(".playback-status").textContent=
      event==="ended"?"Playback ended.":event==="pause"?"Playback paused.":"Playing audio.";
  },true);
}
document.querySelectorAll("th[data-k]").forEach(t=>t.addEventListener("click",()=>{const k=t.dataset.k;if(sortK===k)sortAsc=!sortAsc;else{sortK=k;sortAsc=!NUM.has(k)}render()}));
document.getElementById("q").addEventListener("input",render);
render();
</script></body></html>
"""
out = RUNS / "index.html"
data_dir = RUNS.parent.parent / "data"
duration_reference = (data_dir / "keygen-duration-reference.json").read_bytes()
if json.loads(duration_reference)["policy"]["full_credit_audible_seconds"] != score.DURATION_SUFFICIENT_SECONDS:
    raise ValueError("published duration reference and scorer threshold disagree")
scoring_reference = (data_dir / "keygen-scoring-reference.json").read_bytes()
if json.loads(scoring_reference)["score_version"] != score.SCORE_VERSION:
    raise ValueError("published scoring reference and scorer version disagree")
for name, content in (("duration-reference.json", duration_reference), ("scoring-reference.json", scoring_reference)):
    pending = (RUNS / name).with_suffix(".json.tmp")
    pending.write_bytes(content)
    pending.replace(RUNS / name)
payload = json.dumps(data, allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
temporary = out.with_suffix(".html.tmp")
weights = ", ".join(f"{name.replace('_', ' ')} {weight:g}" for name, weight in score.CRAFT_WEIGHTS.items())
temporary.write_text(PAGE.replace("__RENDERED__", str(n_rendered)).replace("__SCORE_VERSION__", html.escape(score.SCORE_VERSION)).replace("__CRAFT_WEIGHTS__", html.escape(weights)).replace("__DURATION_SUFFICIENT_SECONDS__", f"{score.DURATION_SUFFICIENT_SECONDS:g}").replace("__DATA__", payload))
temporary.replace(out)
print(f"{len(data)} rows, {sum('video' in d['files'] for d in data)} with video -> {out}")
