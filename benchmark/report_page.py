"""Existing results-page layout for the explicit cohort report."""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keygen bench results</title>
<style>
:root{color-scheme:dark}
body{margin:0;padding:12px 16px;background:#000;color:#fff;font:13px/1.35 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
h1{font-size:15px;font-weight:600;margin:0 0 8px}
h2{font-size:14px;font-weight:600;margin:18px 0 6px}
.bar{display:flex;gap:12px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
input{background:#000;color:#fff;border:1px solid #444;padding:4px 6px;font:inherit;width:220px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:3px 8px 3px 0;border-bottom:1px solid #222;white-space:nowrap;vertical-align:top}
th{cursor:pointer;color:#bbb;font-weight:500;user-select:none}
th.on{color:#fff}
.row-toggle,.sort{background:none;color:inherit;border:0;padding:0;font:inherit;cursor:pointer;text-align:left}
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
<h1>Keygen bench, adaptive campaign attempts</h1>
<p class="kv">Cached artifact diagnostics only. Craft is an auxiliary tonal-development heuristic, not a musical-quality ranking.
Each model gets up to three sequential attempts, stopping after its first eligible success. All attempted outcomes and unused slots remain visible.
Skipped slots have null scores and usage, not failure scores. This adaptive experiment has no independent-trial median, range or ranking claim.
Exact routes, effective settings, evaluator identities and cohort fingerprints remain separate. Exhibitions are not comparative native runs.
No archives are restored for publication. Artifact links exist only when a local file is present.</p>
<p class="kv"><b>Cohorts</b> __TIER_NOTE__</p>
<p class="kv"><b>One quality sample</b> __SAMPLE_NOTE__</p>
<details><summary>Campaign counts and first-success selections</summary><pre class="evidence">__SUMMARY__</pre></details>
<div class="bar"><label for="q">Filter model</label><input id="q" name="model-filter" type="search" autocomplete="off"><span id="count" role="status" aria-live="polite"></span><span>activate a model for tune, video and files</span></div>
<div id="tables"></div>
<script>
const DATA=__DATA__;
const COHORTS=__COHORTS__;
const NUM=new Set(["craft","dur","lufs","chans","patterns","instr","steps","min"]);
const COLS=[["model","model"],["attempt_id","attempt / cohort"],["tier","tier / output cap"],["status","status"],["selection_state","selection / attempted"],["craft","craft diagnostic"],["dur","len s"],["lufs","LUFS"],["chans","ch"],["patterns","pat"],["instr","ins"],["steps","steps"],["min","min"],[null,"flags"]];
let sortK="attempt_id",sortAsc=true,open=new Set();
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cls=d=>d.selected?"ok":d.status==="SKIPPED_AFTER_SUCCESS"||["MISSING","RESERVED","RUNNING"].includes(d.status)?"blk":d.eligible?"ok":"fail";
const short=s=>s==="RENDERED_UNSCORED"?"rendered":s.toLowerCase().replaceAll("_"," ");
const selection=d=>d.selection_state==="not_in_campaign"?"not in campaign; not selectable":`${d.selected?`FIRST SUCCESS, valid on attempt ${d.repetition}`:d.selection_state}; ${d.campaign_attempted_count}/3 attempted${d.first_success_attempt_id&&!d.selected?`; selected ${d.first_success_attempt_id}`:""}`;
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
  const factors=Object.entries(d.factors).map(([k,v])=>`<span>${esc(k)} ${esc(fmt(v,6))}</span>`).join("");
  const caps=d.caps.map(c=>`<span class="cap">ceiling ${esc(c.ceiling??"?")}: ${esc(c.reason)}</span>`).join("; ");
  const mix=d.mix,lead=(mix.lead_channels??[]).filter(Number.isInteger).map(c=>c+1).join(", ");
  const loop=d.loop,preview=loop.preview??{},previewURL=f["loop excerpt (lossless)"];
  const transitions=(loop.transitions??[]).map(t=>`<li>${esc(t.kind??"transition")} at runtime ${esc(fmt(t.seconds,6))} s, PCM frame ${esc(t.frame??"?")}${t.from_order!=null?`; order ${esc(t.from_order)}, row ${esc(t.from_row??"?")} to order ${esc(t.to_order??"?")}, row ${esc(t.to_row??"?")}`:""}${t.metrics?`<pre class="evidence">${evidence(t.metrics)}</pre>`:""}${t.components?`<pre class="evidence">${evidence(t.components)}</pre>`:""}</li>`).join("");
  const audioURL=previewURL??f["original WAV"];
  const media=audioURL?`<div class="loop-player"><p class="kv"><b>${previewURL?"Loop excerpt (lossless)":"Original canonical audio; scored loop excerpt unavailable"}</b></p><audio controls preload="none" src="${esc(audioURL)}"></audio>${previewURL?`<p class="kv">An excerpt of the scored continuous FT2 capture, not a stitched restart. It begins at runtime ${esc(fmt(preview.start_seconds,6))} s and lasts ${esc(fmt(preview.duration_seconds,6))} s. Buttons start up to 3 s before each marked transition.</p><div class="loop-controls">${loopControls(loop)}</div><p class="kv playback-status" role="status" aria-live="polite"></p>`:""}</div>`:"";
  return `<div class="det"><div>${media}${f.video?`<p class="kv"><b>Original video</b></p><video controls preload="none" src="${esc(f.video)}"></video>`:""}</div><div>
  <p class="kv"><b>files</b> ${links.join("")}</p>
  ${scripts?`<p class="kv"><b>submission</b> ${scripts}</p>`:""}
  <p class="kv"><b>score</b> ${esc(d.score_version)}, ${esc(d.craft??"unavailable")}${d.craft!=null?"/100":""}${d.uncapped!=null?`, uncapped ${esc(d.uncapped)}`:""}</p>
  <p class="kv"><b>content points</b> ${esc(fmt(d.content_score,2))}/100; <span class="parts">${parts||"none"}</span></p>
  
  <p class="kv"><b>multiplicative factors</b> <span class="parts">${factors||"none"}</span></p>
  <p class="kv"><b>duration diagnostic evidence</b> ${esc(fmt(loop.first_pass_audible_seconds,3))} audible seconds in the ${esc(fmt(loop.analysis_duration_seconds,3))} s first pass. Duration is not a task-compliance or musical-quality judgment.</p>
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
  <p class="kv"><b>condition</b> ${esc(d.cohort.label)}; ${esc(d.tier)}; ${esc(d.kind)}; cohort ${esc(d.cohort_fingerprint)}; route ${evidence(d.route)}; raw effective settings ${evidence(d.effective_settings)}</p>
  <p class="kv"><b>attempt ordinal</b> ${esc(d.repetition??"unknown")}; ${d.predeclared?"predetermined campaign slot":"extra attempt"}; retry of ${esc(d.retry_of??"none")}</p>
  <p class="kv"><b>selection</b> ${esc(selection(d))}${d.status==="SKIPPED_AFTER_SUCCESS"?`; skipped after ${esc(d.selected_attempt_id??"unknown success")}; link ${d.skip_link_valid?"verified":"unverified"}`:""}</p>
  <p class="kv"><b>evaluation eligibility</b> ${d.eligible?"eligible":"ineligible / unevaluated"}; model failure ${esc(d.model_failure??"unknown")}; run failure ${esc(d.failure_category??"none recorded")}; evaluation failure ${esc(d.evaluation_error_category??"none recorded")}; evaluator fingerprint ${esc(d.evaluation_fingerprint??"unavailable")}</p>
  <p class="kv"><b>cost</b> ${!d.attempted?"not attempted / null":d.cost_unknown?"unknown or incomplete":esc(d.cost)}; usage ${!d.attempted?"not attempted / null":d.usage_unknown?"unknown or incomplete":"recorded"}</p>
  <p class="kv"><b>artifact availability</b> ${esc(d.artifact_note)} ${d.archived_artifacts.length?`Archived-only files: ${esc(d.archived_artifacts.join(", "))}`:""}</p>
  <p class="kv"><b>dir</b> ${esc(d.run_dir)}</p></div></div>`;
}
let playbackRequest=null;
function render(){
  playbackRequest?.abort();
  const q=document.getElementById("q").value.toLowerCase();
  let rows=DATA.filter(d=>String(d.model??"unknown").toLowerCase().includes(q));
  rows.sort((a,b)=>{let x=a[sortK],y=b[sortK];if(NUM.has(sortK)){if(x==null||y==null)return x==null?(y==null?0:1):-1;return sortAsc?x-y:y-x}x=String(x);y=String(y);return sortAsc?x.localeCompare(y):y.localeCompare(x)});
  document.getElementById("count").textContent=`${rows.length} of ${DATA.length} attempt slots; ${DATA.filter(d=>d.attempted).length} attempted; ${DATA.filter(d=>d.selected).length} first successes; ${COHORTS.length} cohort table(s)`;
  const head=COLS.map(([k,label])=>k?`<th data-k="${k}" class="${k===sortK?"on":""}"><button class="sort" type="button" data-sort="${k}">${esc(label)}</button></th>`:`<th>${esc(label)}</th>`).join("");
  // One table per cohort: rows from different experimental conditions are never sorted or ranked together.
  const tables=[];
  for(const cohort of COHORTS){
    const h=[];
    for(const d of rows.filter(d=>d.cohort.key===cohort.key)){
      h.push(`<tr class="r" data-m="${esc(d.id)}"><td><button class="row-toggle" type="button" data-id="${esc(d.id)}" aria-expanded="${open.has(d.id)}">${esc(d.model??"unknown")}</button></td><td>${esc(d.attempt_id)} / ${esc(d.kind)} / ${esc(d.cohort_fingerprint.slice(0,12))}</td><td>${esc(d.tier)}</td><td class="${cls(d)}">${esc(short(d.status))}</td><td>${esc(selection(d))}</td><td class="num">${esc(d.craft??"null")}</td><td class="num">${esc(d.dur??"")}</td><td class="num">${esc(d.lufs??"")}</td><td class="num">${esc(d.chans??"")}</td><td class="num">${esc(d.patterns??"")}</td><td class="num">${esc(d.instr??"")}</td><td class="num">${esc(d.steps??"")}</td><td class="num">${esc(d.min??"")}</td><td>${esc([...d.flags,...(!d.eligible?["ineligible/null"]:[]),...(d.cost_unknown?["cost unknown"]:[])].join(" "))||"-"}</td></tr>`);
      if(open.has(d.id)) h.push(`<tr class="d"><td colspan="${COLS.length}">${detail(d)}</td></tr>`);
    }
    if(h.length) tables.push(`<section><h2>${esc(cohort.label)}</h2><table><thead><tr>${head}</tr></thead><tbody>${h.join("")}</tbody></table></section>`);
  }
  document.getElementById("tables").innerHTML=tables.join("");
}
document.getElementById("tables").addEventListener("click",e=>{
  const sort=e.target.closest("button.sort");
  if(sort){
    const k=sort.dataset.sort;if(sortK===k)sortAsc=!sortAsc;else{sortK=k;sortAsc=!NUM.has(k)}render();
    document.querySelector(`button.sort[data-sort="${k}"]`)?.focus();return;
  }
  const button=e.target.closest("button.row-toggle");if(!button)return;
  const id=button.dataset.id;open.has(id)?open.delete(id):open.add(id);render();
  [...document.querySelectorAll("button.row-toggle")].find(control=>control.dataset.id===id)?.focus();
});
document.getElementById("tables").addEventListener("click",async e=>{
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
  document.getElementById("tables").addEventListener(event,e=>{
    if(!e.target.matches(".loop-player audio"))return;
    const status=e.target.closest(".loop-player").querySelector(".playback-status");
    if(status)status.textContent=event==="ended"?"Playback ended.":event==="pause"?"Playback paused.":"Playing audio.";
  },true);
}
document.getElementById("q").addEventListener("input",render);
render();
</script></body></html>
"""
