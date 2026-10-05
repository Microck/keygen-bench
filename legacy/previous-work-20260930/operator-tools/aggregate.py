"""Final per-model table across every official campaign: one row per model, its latest attempt.

Every later campaign was a retry of an infra-caused outcome, so the newest attempt (by start time)
is the record. Proxy 401/402/429 terminations are reported as BLOCKED unless the model had already
written a module that renders. Writes <out>.md and a machine-readable <out>.json (consumed by
build-results-page.py). Profiles are cached in each attempt dir as profile.json.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "/home/ubuntu/workspace/keygen-benchmark/benchmark")
import score

RUNS = Path("/home/ubuntu/workspace/keygen-benchmark/benchmark/runs")
CAMPAIGNS = ["official-top", "official-top-go-retry", "official-top-timeout-retry", "official-top-unlimited", "second-chance", "exhibition"]
# opus-4-8 and the second-chance Claude runs went through the Anthropic account after Devin's quota ran out
# or its max-thinking runs stalled: same model row as the Devin route
ALIASES = {m: f"devin/{m}" for m in ("claude-opus-4-8", "claude-opus-5", "claude-sonnet-5", "claude-fable-5-1", "claude-opus-5-5")}

history = {}
for camp in CAMPAIGNS:
    for tier_dir in sorted((RUNS / camp).glob("*/")):
        for run_dir in sorted(tier_dir.glob("*/")):
            if not (run_dir / "status.json").exists():
                continue
            st = json.loads((run_dir / "status.json").read_text())
            if "model" not in st:
                continue  # RESERVED: still running
            model = st["model"]["model"]
            if st.get("exhibition"):
                model += " (exhibition)"
            key = ALIASES.get(model, model)
            history.setdefault(key, []).append((st.get("started_at") or 0, camp, run_dir, st))

# Select by status metadata first: discarded retries must not trigger audio analysis.
# Reverse traversal preserves the old stable-sort policy when timestamps tie.
final = {}
for model, attempts in history.items():
    _, camp, run_dir, st = max(reversed(attempts), key=lambda attempt: attempt[0])
    prof = run_dir / "profile.json"
    p = None
    if prof.exists():
        try:
            cached = json.loads(prof.read_text())
        except json.JSONDecodeError:
            cached = None
        if isinstance(cached, dict) and cached.get("score_version") == score.SCORE_VERSION and score.profile_is_current(run_dir, cached):
            p = cached
    if p is None:
        p = score.profile_attempt(run_dir)
    if not p:
        continue  # RESERVED: status changed during aggregation
    if p.get("score_version") != score.SCORE_VERSION:
        raise ValueError(f"{run_dir}: profile does not use {score.SCORE_VERSION}")
    spec = run_dir / "spec.json"  # exhibition attempts (rendered by hand) have none
    cfg = json.loads(spec.read_text())["config"] if spec.exists() else {"generation": {}, "limits": {"wall_seconds": 7200, "steps": 0}}
    p["tier"] = cfg["generation"].get("reasoning_effort") or run_dir.parent.name
    p["budget"] = f'{cfg["limits"]["wall_seconds"] // 60}m/{cfg["limits"].get("steps", 100) or "inf"}'
    p["max_tokens"] = cfg["generation"].get("max_tokens")
    p["campaign"], p["error"] = camp, (st.get("error") or "")[:90]
    p["started_at"] = st.get("started_at") or 0
    p["run_dir"] = str(run_dir.relative_to(RUNS))
    term = st.get("termination")
    if isinstance(term, dict) and "Proxy" in str(term.get("error", "")):
        code = term["error"].replace("Proxy HTTP ", "").split(";")[0]
        if st.get("render") == "ok":
            p["error"] = f"cut by proxy {code} at {round((p.get('wall_seconds') or 0) / 60)} min; tune already written"
        else:
            p["status"] = "BLOCKED " + code
            p["error"] = term["error"]
    if st.get("exhibition"):
        # not comparable: relayed by hand through a chat UI, no tool calls, other output caps
        p["model"] += " (exhibition)"
        p["error"] = st.get("note") or "exhibition"
        p["tier"] = "web"
    if model != p["model"]:
        p["model"] = f'{p["model"]} (anthropic acct)'
    p["attempts"] = len(attempts)
    final[model] = p

rows = sorted(final.values(), key=lambda p: (-((p.get("craft") or {}).get("craft_score") or 0.0), p["model"]))
cols = ["model", "tier", "budget", "campaign", "status", "score_version", "craft", "flags", "dur_s", "requests", "wall_min", "attempts", "error"]
lines = [
    f"Deterministic {score.SCORE_VERSION}, 0-100. No human or LLM judges; no process points.",
    "Content points: " + " + ".join(f"{name.replace('_', ' ')} {weight:g}" for name, weight in score.CRAFT_WEIGHTS.items()) + f". Multiply by signal integrity, sustained-noise integrity, bounded loop continuity and min(1, first-pass audible seconds / {score.DURATION_SUFFICIENT_SECONDS:g}); artifact caps apply. Later playback and silence add no duration credit. No duration bonus above sufficiency; selected-lead masking is diagnostic.",
    "Full-band canonical audio supplies tonal and sustained-noise evidence. Tonal, noise, DC and restart level/timbre bounds give full credit at the level of typical archived keygen music; clean-loop click, gap and rhythm bounds are unchanged. Mix masking remains diagnostic. Loop previews play actual continuous FT2 transitions. Original artifacts are unchanged. This is a provisional tonal-development indicator, not a validated musical-quality rating. Latest attempt per model; exhibitions remain separate.",
    "",
    "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols),
]
for p in rows:
    au, tot = p.get("audio") or {}, p.get("totals") or {}
    lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in [
        p["model"], p["tier"], p["budget"], p["campaign"].replace("official-top", "top"), p["status"], p["score_version"],
        (p.get("craft") or {}).get("craft_score", 0.0), " ".join(p.get("flags", [])) or "-",
        au.get("duration_seconds", ""), tot.get("requests", ""), round((p.get("wall_seconds") or 0) / 60),
        p["attempts"], p["error"]]) + " |")
n = len(rows); r = sum(p["status"] == "RENDERED_UNSCORED" for p in rows); f = sum(p["status"] == "FAILED" for p in rows)
b = sum(p["status"].startswith("BLOCKED") for p in rows)
lines += ["", f"{n} models: {r} rendered, {f} failed on their own, {b} blocked by provider auth or quota, {n-r-f-b} other."]
out = Path(sys.argv[1] if len(sys.argv) > 1 else "/dev/stdout")
out.write_text("\n".join(lines) + "\n")
if str(out) != "/dev/stdout":
    out.with_suffix(".json").write_text(json.dumps(rows, indent=1, allow_nan=False) + "\n")
    print(f"{n} models -> {out}")
