"""Build the existing FT2 website from explicitly selected public campaign snapshots.

Use collect_public.py on each trusted controller, then pass its sanitized output
with --snapshot. The old embedded HTML report is available only via --legacy.
"""
from datetime import datetime, timezone
import hashlib
import gzip
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmark.report import INDEPENDENT_SELECTION, QUEUE_SELECTION, SAMPLE_NOTE, TIER_NOTE, campaign_cohort, read_cohort, tier_label

RUNS = ROOT / "legacy/previous-work-20260930/benchmark/runs"
HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
MEDIA = DIST / "media"
# Tables are ordered by condition; a cohort is never ranked together with another one.
CONDITION_ORDER = ("highest-declared-tier", "declared-tier", "provider-default")
LEGACY_COHORT = {"key": "historical-prototype-20260929", "condition": "historical-prototype", "prompt_version": "prompt-v1",
                 "label": "historical prototype 2026-09-29, effort as recorded per model, prompt-v1"}
# Frozen campaigns retain their original stopping policies; publication ranks the available ordinal samples.
ATTEMPT_NOTE = ("Ranking uses the best eligible score among three predetermined ordinals under the same frozen condition. "
                "Ties use the lowest ordinal. Every eligible ordinal remains playable. Failed and unstarted slots have "
                "no score. Infrastructure reruns replace their ordinal's failed sample, not add another repetition.")
# Public wording for the campaign an attempt ran in; campaign identities stay private.
SOURCE_LABELS = {"main": "main campaign", INDEPENDENT_SELECTION: "independent repeats campaign", QUEUE_SELECTION: "rerun queue"}

FLAG_RULES = {
    "PHRASE_SAMPLE": "A used sample plays over 8 s at its root note, or over 25% of the song.",
    "SAMPLE_HEAVY": "Used sample seconds at root notes exceed 50% of the song length.",
    "ONE_INSTRUMENT": "Only one instrument is ever triggered.",
    "SPARSE": "Fewer than 64 note-ons, or fewer than 2 channels ever triggered.",
    "SILENCE": "Over 20% of 100 ms blocks below -60 dBFS, or a silent run over 4 s.",
    "TAIL_SILENCE": "Over 1 s of silence before the end of the render.",
    "CLIPPING": "Over 0.1% of samples at full scale.",
    "QUIET": "Integrated loudness below -30 LUFS.",
    "FLAT": "95th-to-10th percentile block RMS range under 2 dB.",
    "SEAM": "Worst measured FT2 loop transition below 50%, or no restart observed.",
    "MASKED": "Lead melody masked in over 35% of its bands (diagnostic only).",
    "SUSTAINED_NOISE": "Sustained-noise integrity below 0.8.",
    "RAW_XM": "tune.xm was written without module_save (allowed; recorded).",
}

# Access routes (proxies, subscriptions, relays) are private: nothing below may reach data.json.
PROVIDER_PREFIX = r"^(devin/|go-|vercel-[a-z]+/)"
PUBLIC_PRICE_HOSTS = (  # maker-published pricing pages only; third-party/proxy tables are not shown
    "developers.openai.com", "openai.com", "platform.claude.com", "ai.google.dev", "docs.x.ai", "api-docs.deepseek.com",
    "docs.z.ai", "platform.kimi.ai", "alibabacloud.com", "mimo.mi.com", "platform.minimax.io",
    "dev.meta.ai", "docs.mistral.ai",
)


def price_id(model: str) -> str:
    m = re.sub(r"\s*\(.*\)$", "", model)
    return re.sub(PROVIDER_PREFIX, "", m)


def public_maker(model: str, price: dict) -> str:
    if price.get("maker"):
        return price["maker"]
    names = {"google": "Google", "openai": "OpenAI", "anthropic": "Anthropic",
             "inception": "Inception", "thinkingmachines": "Thinking Machines Lab",
             "meta": "Meta", "mistral": "Mistral", "cohere": "Cohere"}
    namespace, separator, product = price_id(model).lower().partition("/")
    if separator and namespace in names:
        return names[namespace]
    product = product if separator else namespace
    prefixes = (("gpt", "OpenAI"), ("claude", "Anthropic"), ("gemini", "Google"),
                ("gemma", "Google"), ("grok", "xAI"), ("qwen", "Alibaba (Qwen)"),
                ("deepseek", "DeepSeek"), ("glm", "Zhipu (Z.ai)"), ("kimi", "Moonshot AI"),
                ("minimax", "MiniMax"), ("mimo", "Xiaomi"), ("hy", "Tencent"),
                ("longcat", "Meituan"), ("llama", "Meta"), ("mercury", "Inception"),
                ("inkling", "Thinking Machines Lab"), ("muse", "Meta"))
    return next((maker for prefix, maker in prefixes if product.startswith(prefix)), "Other")


def public_price(price: dict) -> dict:
    """Maker list price, or all-null when the only source is a proxy/aggregator."""
    keys = ("input_usd_per_m", "cached_input_usd_per_m", "output_usd_per_m")
    url = price.get("source_url") or ""
    if not any(host in url for host in PUBLIC_PRICE_HOSTS):
        return {**{k: None for k in keys}, "source_url": None}
    return {**{k: price[k] for k in keys}, "source_url": url}


def public_error(err: str) -> str:
    return "" if re.search(r"proxy|relay|driver|web ui|acct", err or "", re.I) else (err or "")


def slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", price_id(model).lower()).strip("-") + ("-exh" if "exhibition" in model else "")


def estimate_cost(totals: dict, price: dict) -> float | None:
    if not totals or price.get("input_usd_per_m") is None:
        return None
    cached = totals.get("cached_tokens") or 0
    fresh = max(0, (totals.get("prompt_tokens") or 0) - cached)
    cached_rate = price["cached_input_usd_per_m"]
    if cached_rate is None:
        cached_rate = price["input_usd_per_m"]
    return round((fresh * price["input_usd_per_m"] + cached * cached_rate
                  + (totals.get("completion_tokens") or 0) * price["output_usd_per_m"]) / 1e6, 4)


def compact_trace(path: Path, max_frame: int) -> list[list[int]]:
    """[frame, order, row, pattern] for every executed row up to the canonical render's end."""
    out = []
    with gzip.open(path, "rt") as fh:
        for line in fh:
            ev = json.loads(line)
            if ev.get("kind") != "row":
                continue
            if ev["frame"] > max_frame:
                break
            out.append([ev["frame"], ev["order"], ev["row"], ev["pattern"]])
    return out


def worst_transition(loop: dict) -> dict | None:
    ts = [t for t in loop.get("transitions") or [] if isinstance(t.get("quality_score"), (int, float))]
    if not ts:
        return None
    t = min(ts, key=lambda t: t["quality_score"])
    return {k: t.get(k) for k in ("seconds", "kind", "from_order", "from_row", "to_order", "to_row", "quality_score", "components")}


# Public display names where the run id differs from the product name.
DISPLAY_NAMES = {}
# Exhibition runs went through a chat web UI: no API token counts exist. Wall time, turns and shell commands
# are recovered from their session logs instead; token/cost fields stay null (not billed per token).
EXHIBITION_LOGS = {"gpt-6-pro": "gpt6pro-exhibition", "claude-3-opus-20240229": "opus3-exhibition"}


def exhibition_usage(name: str) -> dict | None:
    d = EXHIBITION_LOGS.get(name)
    if not d or not (RUNS / d / "driver-log.jsonl").exists():
        return None
    events = [json.loads(line) for line in (RUNS / d / "driver-log.jsonl").read_text().splitlines() if line.strip()]
    relay = RUNS / d / "relay-log.jsonl"
    commands = sum(1 for line in relay.read_text().splitlines() if line.strip()) if relay.exists() else None
    ats = [e["at"] for e in events if "at" in e]
    return {"turns": sum(1 for e in events if e.get("event") == "reply"), "commands": commands,
            "wall_minutes": round((max(ats) - min(ats)) / 60, 1) if ats else None}


def frozen_campaigns() -> dict:
    """Frozen campaign configs retained in this repository, by campaign sha256."""
    found = {}
    for path in sorted((ROOT / "benchmark/runs").glob("*/*campaign*.json")):
        try:
            config, config_hash, _ = read_cohort(path)
        except (OSError, ValueError, TypeError, KeyError):
            continue
        found[config_hash] = config
    return found


def label_unlabeled_snapshot(snapshot: dict, campaigns: dict) -> None:
    """Snapshots exported before cohort labels: derive them from the retained frozen campaign."""
    config = campaigns.get(snapshot["campaign_sha256"])
    if config is None:
        raise ValueError(f"{snapshot.get('campaign_id')}: snapshot has no cohort label and its frozen campaign is not "
                         "retained under benchmark/runs; re-export it with the current collect_public.py")
    snapshot["cohort"] = campaign_cohort(config)
    for run in snapshot["runs"]:
        labels = {tier_label(model, snapshot["cohort"]["condition"]) for model in config.get("models", [])
                  if price_id(model.get("model") or "") == price_id(run["name"])}
        if len(labels) != 1:
            raise ValueError(f"{run['name']}: cannot derive one tier label from the frozen campaign")
        run["tier"], run["cohort"] = labels.pop(), snapshot["cohort"]


def cohort_order(cohort: dict) -> tuple:
    condition = cohort["condition"]
    return (CONDITION_ORDER.index(condition) if condition in CONDITION_ORDER else len(CONDITION_ORDER), cohort["key"])


def repetition_groups(snapshots: list[dict], runs: list[dict], roster: set, additions: set) -> tuple[list[dict], set]:
    """Merge frozen ordinal samples, following explicit rerun chains rather than publication order."""
    published = {snapshot["campaign_sha256"]: snapshot for snapshot in snapshots}
    links = {sha: {item["campaign_sha256"] for item in snapshot.get("linked_campaigns", [])
                   if item["campaign_sha256"] != sha} for sha, snapshot in published.items()}
    for sha, linked in links.items():
        if any(item not in published or published[item]["cohort"] != published[sha]["cohort"] for item in linked):
            raise ValueError("Every linked campaign must be published in the same cohort")

    def ancestors(sha: str, trail: frozenset = frozenset()) -> set:
        if sha in trail:
            raise ValueError("Linked campaigns must not contain a cycle")
        return links[sha] | {item for parent in links[sha] for item in ancestors(parent, trail | {sha})}

    dependencies = {sha: ancestors(sha) for sha in published}

    def identity(attempt: dict) -> tuple:
        return attempt["source_campaign_sha256"], attempt.get("source_attempt_id", attempt.get("ordinal"))

    def public_attempt(attempt: dict) -> dict:
        sha = attempt["source_campaign_sha256"]
        if sha not in published:
            raise ValueError("An attempt comes from an unpublished campaign")
        source = published[sha]
        label = SOURCE_LABELS["main" if source["scope"] == "main" else source.get("attempt_selection")]
        return {**attempt, "source_campaign_id": source["campaign_id"], "source": label,
                "queue_pending": bool(attempt.get("queue_pending")),
                "superseded": [public_attempt(link) for link in attempt.get("superseded", [])]}

    models, claimed, duplicates = {}, set(), set()
    for snapshot in snapshots:
        if snapshot["scope"] not in ("main", "repetitions"):
            continue
        if not isinstance(snapshot.get("repetition_groups"), list):
            raise ValueError("Main and repetitions snapshots must retain all predetermined slots; re-export with collect_public.py")
        by_slug = {run["slug"]: run for run in snapshot["runs"]}
        for group in snapshot["repetition_groups"]:
            key = (snapshot["cohort"]["key"], price_id(group["name"]).rsplit("/", 1)[-1])
            if key not in roster | additions or group["cohort"] != snapshot["cohort"]:
                raise ValueError(f"{group['name']}: attempt group is outside its cohort's roster")
            if group["declared"] != 3 or [attempt["ordinal"] for attempt in group["attempts"]] != [1, 2, 3]:
                raise ValueError(f"{group['name']}: all three predetermined ordinals must be listed once")
            if group["eligible"] != sum(bool(attempt["eligible"]) for attempt in group["attempts"]):
                raise ValueError(f"{group['name']}: eligible count differs from the ordinal samples")
            entry = models.setdefault(key, {"group": group, "samples": {1: [], 2: [], 3: []},
                                           "outside": [], "campaigns": set(), "queued": False})
            if entry["group"]["condition_fingerprint"] != group["condition_fingerprint"]:
                raise ValueError(f"{group['name']}: overlapping product identities have contradictory frozen conditions")
            entry["campaigns"].add(snapshot["campaign_id"])
            entry["queued"] |= snapshot.get("attempt_selection") == QUEUE_SELECTION
            for outside in group["outside_condition"]:
                item = public_attempt(outside)
                if item not in entry["outside"]:
                    entry["outside"].append(item)
            for attempt in group["attempts"]:
                run = by_slug.get(attempt["slug"]) if attempt["slug"] else None
                if bool(attempt["eligible"]) != (run is not None) or (run and (
                        run["model_key"] != key[1] or run["score"] != attempt["score"]
                        or run["provenance"]["attempt_ordinal"] != attempt["ordinal"]
                        or run["provenance"]["campaign_sha256"] != attempt["source_campaign_sha256"]
                        or run["provenance"]["condition_fingerprint"] != group["condition_fingerprint"])):
                    raise ValueError(f"{group['name']}: ordinal differs from its published result")
                if attempt["source_campaign_sha256"] not in {snapshot["campaign_sha256"]} | dependencies[snapshot["campaign_sha256"]]:
                    raise ValueError(f"{group['name']}: attempt comes from an undeclared source campaign")
                if run:
                    claimed.add(run["slug"])
                    run["provenance"]["source_campaign_id"] = published[attempt["source_campaign_sha256"]]["campaign_id"]
                entry["samples"][attempt["ordinal"]].append((snapshot, public_attempt(attempt), run))
        if {run["slug"] for run in snapshot["runs"]} - claimed:
            raise ValueError("Every published result must belong to its model's attempt group")

    def supersedes(new: tuple, old: tuple) -> bool:
        _, new_attempt, _ = new
        old_snapshot, old_attempt, _ = old
        old_id = identity(old_attempt)
        explicit = old_id in {identity(link) for link in new_attempt["superseded"]}
        # Ownership follows the sample's source, even when a later queue re-exports it.
        sources = {item["source_campaign_sha256"] for item in [*new_attempt["superseded"], new_attempt]}
        companion = (old_snapshot["scope"] == "main" and any(
            published[sha].get("attempt_selection") == INDEPENDENT_SELECTION
            and old_snapshot["campaign_sha256"] in dependencies[sha] for sha in sources))
        if explicit or companion:
            if old_attempt["eligible"]:
                raise ValueError("A rerun or companion cannot replace a scored eligible ordinal")
            return True
        return False

    groups = []
    for key, entry in models.items():
        group = entry["group"]
        attempts, eligible_runs = [], []
        for ordinal, candidates in entry["samples"].items():
            unique = {}
            for candidate in candidates:
                snapshot, attempt, run = candidate
                attempt_id = identity(attempt)
                previous = unique.get(attempt_id)
                if previous:
                    previous_snapshot, old, old_run = previous
                    if old["eligible"] != attempt["eligible"] or old["score"] != attempt["score"]:
                        raise ValueError(f"{group['name']}: contradictory evaluations for the same ordinal source")
                    if run and any(run["provenance"].get(field) != old_run["provenance"].get(field)
                                   for field in ("profile_sha256", "input_sha256", "evaluation_fingerprint")):
                        raise ValueError(f"{group['name']}: duplicate ordinal has different pinned evaluation inputs")
                    replace = (previous_snapshot["campaign_sha256"] in dependencies[snapshot["campaign_sha256"]]
                               or len(attempt["superseded"]) > len(old["superseded"]))
                    discarded = old_run if replace else run
                    kept = run if replace else old_run
                    if discarded and discarded["slug"] != kept["slug"]:
                        duplicates.add(discarded["slug"])
                    if replace:
                        unique[attempt_id] = candidate
                else:
                    unique[attempt_id] = candidate
            samples = list(unique.values())
            # Empty queue branches reserve the same slots but contribute no replacement outcome.
            attempted = [candidate for candidate in samples if candidate[1]["attempted"]]
            active = attempted or samples
            survivors = [candidate for candidate in active
                         if not any(other is not candidate and supersedes(other, candidate) for other in active)]
            if not attempted:
                survivors = [max(survivors, key=lambda candidate: (
                    len(candidate[1]["superseded"]), len(dependencies[candidate[0]["campaign_sha256"]]),
                    candidate[0]["campaign_sha256"]))]
            if len(survivors) != 1:
                raise ValueError(f"{group['name']}: contradictory ordinal {ordinal} without frozen rerun precedence")
            _, attempt, run = survivors[0]
            for _, replaced, replaced_run in samples:
                if replaced_run and replaced is not attempt:
                    raise ValueError(f"{group['name']}: eligible media would be lost by ordinal replacement")
            attempt["ranked"] = False
            attempts.append(attempt)
            if run:
                eligible_runs.append((attempt, run))
        best = min(eligible_runs, key=lambda item: (-item[1]["score"], item[0]["ordinal"])) if eligible_runs else None
        ranked_slug = best[1]["slug"] if best else None
        best_ordinal = best[0]["ordinal"] if best else None
        for attempt, run in eligible_runs:
            attempt["ranked"] = run is best[1]
            run.update(ranked=attempt["ranked"], ranking_policy="best of 3",
                       eligible_attempts=len(eligible_runs), best_ordinal=best_ordinal)
            run["provenance"]["selected_by"] = "best eligible score among three predetermined ordinals; ties use the lowest ordinal"
            if attempt["ranked"]:
                run.pop("attempt_of", None)
            else:
                run["attempt_of"] = ranked_slug
        maker = public_maker(group["name"], {})
        pending = sum(attempt["queue_pending"] or not attempt["attempted"]
                      or attempt["status"] in {"RUNNING", "RESERVED", "MISSING"} for attempt in attempts)
        state = "complete" if len(eligible_runs) == 3 else "complete_with_failures" if eligible_runs else "pending"
        groups.append({"cohort_key": key[0], "model_key": key[1], "name": group["name"],
                       "maker": group["maker"] if maker == "Other" else maker, "tier": group["tier"],
                       "campaign_id": sorted(entry["campaigns"])[0], "campaign_ids": sorted(entry["campaigns"]),
                       "condition_fingerprint": group["condition_fingerprint"], "declared": 3,
                       "eligible": len(eligible_runs), "eligible_attempts": len(eligible_runs), "pending": pending,
                       "state": state, "ranking_policy": "best of 3", "best_ordinal": best_ordinal,
                       "ranked_slug": ranked_slug, "attempts": attempts, "outside_condition": entry["outside"],
                       "reason": "; ".join(f"attempt {attempt['ordinal']}: {attempt['status'].lower().replace('_', ' ')}"
                                           for attempt in attempts if not attempt["eligible"]),
                       **({"roster_addition": True} if key in additions else {}),
                       **({"rerun_queue": True, "reruns": sum(len(attempt["superseded"]) for attempt in attempts)}
                          if entry["queued"] else {})})
    return groups, duplicates


def build_legacy() -> None:
    html = (RUNS / "index.html").read_text(encoding="utf-8")
    report = json.loads(re.search(r"const DATA=(\[.*?\]);\n", html, re.S).group(1))
    prices = {p["id"]: p for p in json.loads((HERE / "data-src/prices.json").read_text())["models"]}
    MEDIA.mkdir(parents=True, exist_ok=True)
    runs = []
    for d in report:
        run_dir = RUNS / d["run_dir"]
        status = json.loads((run_dir / "status.json").read_text())
        profile = json.loads((run_dir / "profile.json").read_text()) if (run_dir / "profile.json").exists() else {}
        price = prices[price_id(d["model"])]
        s = slug(d["model"])
        media = {}
        xm = run_dir / "submission/tune.xm"
        if d["files"].get("xm") and (RUNS / d["files"]["xm"]).exists():
            xm = RUNS / d["files"]["xm"]
        if xm.exists():
            shutil.copyfile(xm, MEDIA / f"{s}.xm")
            media["xm"] = f"media/{s}.xm"
        wav = run_dir / "canonical/canonical.wav"
        if wav.exists():
            mp3 = MEDIA / f"{s}.mp3"
            if not mp3.exists() or mp3.stat().st_mtime < wav.stat().st_mtime:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "160k", str(mp3)], check=True)
            media["audio"] = f"media/{s}.mp3"
        audio = status.get("audio") or {}
        trace = []
        if (run_dir / "playback/trace.jsonl.gz").exists() and audio.get("duration_seconds"):
            trace = compact_trace(run_dir / "playback/trace.jsonl.gz", int(audio["duration_seconds"] * 44100))
        totals = status.get("totals") or {}
        structure = profile.get("structure") or {}
        pub_price = public_price(price)
        runs.append({
            "slug": s,
            "name": DISPLAY_NAMES.get(price_id(d["model"]), price_id(d["model"])),
            "maker": price["maker"],
            "exhibition": "(exhibition)" in d["model"],
            "tier": f"recorded effort: {d['tier']}",
            "cohort": LEGACY_COHORT,
            "status": d["status"],
            "error": public_error(d["error"]),
            "score": d["craft"],
            "parts": {k: (d["parts"] or {}).get(k, 0.0) for k in ("tonal_organization", "development", "dynamics")},
            "weights": d["weights"],
            "factors": {k: (d["factors"] or {}).get(k, 0.0) for k in ("signal_integrity", "noise_integrity", "loop_continuity", "duration_sufficiency")},
            "uncapped": d["uncapped"],
            "content": d["content_score"],
            "caps": d["caps"],
            "flags": [{"id": f, "rule": FLAG_RULES.get(f, "")} for f in d["flags"]],
            "loop": {"quality": (d["loop"] or {}).get("quality_score"), "worst": worst_transition(d["loop"] or {})},
            "tonal": {k: (d["spectral"] or {}).get(k) for k in ("tonal_evidence_fraction", "diatonic_concentration", "effective_pitch_classes", "sustained_noise_fraction")},
            "development": {k: structure.get(k) for k in ("arrangement_score", "sequence_coverage", "motif_recurrence", "controlled_development")},
            "audio": {"duration": audio.get("duration_seconds"), "lufs": d["lufs"], "peak": audio.get("peak")},
            "module": {**(status.get("module") or {}), "patterns": d["patterns"], "instruments": d["instr"], "samples": d["samples"]},
            "usage": {
                "requests": totals.get("requests"), "prompt_tokens": totals.get("prompt_tokens"),
                "cached_tokens": totals.get("cached_tokens"), "completion_tokens": totals.get("completion_tokens"),
                "reasoning_tokens": totals.get("reasoning_tokens"), "commands": totals.get("commands"),
                "wall_minutes": round((status.get("wall_seconds") or 0) / 60, 1), "attempts": d["attempts"],
                "turns": None,
                **({k: v for k, v in (exhibition_usage(price_id(d["model"])) or {}).items()} if "(exhibition)" in d["model"] else {}),
            },
            "price": pub_price,
            "cost_usd": estimate_cost(totals, pub_price),
            "media": media,
            "trace": trace,
        })
    runs.sort(key=lambda r: (r["exhibition"], r["status"] != "RENDERED_UNSCORED", -r["score"]))
    rank = 0
    for r in runs:
        r["failed"] = r["status"] != "RENDERED_UNSCORED"
        r["rank"] = None if r["exhibition"] or r["failed"] else (rank := rank + 1)
    out = {
        "generated": "2026-09-29",
        "dataset_kind": "historical",
        "publication_note": "Historical prototype dataset, 2026-09-29. Not the current native campaign.",
        "formula": {
            "content": "50 x tonal organization + 40 x development + 10 x dynamics",
            "score": "content x signal integrity x noise integrity x (0.75 + 0.25 x loop quality) x duration sufficiency, then caps; rounded to 0.1",
            "duration": "min(1, first-pass audible seconds / 30)",
        },
        "flag_rules": FLAG_RULES,
        "cohorts": [LEGACY_COHORT],
        "runs": runs,
    }
    (DIST / "data.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"{len(runs)} runs -> {DIST / 'data.json'} ({(DIST / 'data.json').stat().st_size // 1024} KB)")


def build_snapshots(sources: list[Path], publish_root: Path, excluded: list[tuple[str, str, str]] = ()) -> None:
    """Assemble only explicitly allowlisted assets from sanitized public snapshots.

    `excluded` lists (cohort key, model, public reason) for models withheld from a cohort's frozen roster before launch.
    """
    publish_root = publish_root.resolve()
    if publish_root == ROOT or ROOT.is_relative_to(publish_root) or publish_root == HERE:
        raise ValueError("Publication needs a dedicated directory, never the repository or prototype root")
    if publish_root.exists() and any(publish_root.iterdir()):
        raise ValueError("Use a new empty publication directory for each immutable snapshot")
    snapshots = [json.loads((source / "snapshot.json").read_text()) for source in sources]
    if any(snapshot.get("schema") != "keygen-public-snapshot-1" for snapshot in snapshots):
        raise ValueError("Unsupported public snapshot")
    campaigns = None
    for snapshot in snapshots:
        if "cohort" not in snapshot:
            campaigns = frozen_campaigns() if campaigns is None else campaigns
            label_unlabeled_snapshot(snapshot, campaigns)
        elif any(run.get("cohort") != snapshot["cohort"] or not isinstance(run.get("tier"), str) for run in snapshot["runs"]):
            raise ValueError("Every public result needs its snapshot's cohort and a readable tier label")
        public_id = f"{snapshot['scope']}-{snapshot['campaign_sha256'][:12]}"
        snapshot["campaign_id"] = public_id
        for model in snapshot["roster"]:
            model["model_key"] = price_id(model["name"]).rsplit("/", 1)[-1]
            model["cohort_key"] = snapshot["cohort"]["key"]
        for run in snapshot["runs"]:
            run["provenance"].pop("attempt_id", None)
            run["provenance"]["campaign_id"] = public_id
            maker = public_maker(run["name"], {})
            if maker != "Other":
                run["maker"] = maker
            run["model_key"] = price_id(run["name"]).rsplit("/", 1)[-1]
    runs = [run for snapshot in snapshots for run in snapshot["runs"]]
    if len({run["slug"] for run in runs}) != len(runs):
        raise ValueError("Public snapshots need unique exported result slugs")
    # Uniqueness and roster membership hold within one cohort; cohorts are separate experiments.
    original_hashes = {snapshot["campaign_sha256"] for snapshot in snapshots if snapshot["scope"] == "main"}
    original_models = {(run["cohort"]["key"], run["model_key"]) for run in runs if run["provenance"]["scope"] == "main"}
    for run in runs:
        if run["provenance"]["scope"] == "recovery":
            if run["provenance"]["campaign_sha256"] not in original_hashes or (run["cohort"]["key"], run["model_key"]) in original_models:
                raise ValueError("A recovery must belong to an original main cohort and cannot replace its selected success")
    def standalone(snapshot: dict) -> bool:
        return (snapshot.get("attempt_selection") == INDEPENDENT_SELECTION
                and all(item["campaign_sha256"] == snapshot["campaign_sha256"] for item in snapshot.get("linked_campaigns", [])))

    original_roster = {(model["cohort_key"], model["model_key"]) for snapshot in snapshots
                       if snapshot["scope"] == "main" or standalone(snapshot) for model in snapshot["roster"]}
    # New queue rosters join the same cohort; recursive queues may re-export them.
    additions = {(model["cohort_key"], model["model_key"]) for snapshot in snapshots if snapshot.get("attempt_selection") == QUEUE_SELECTION
                 for model in snapshot["roster"] if model.get("roster_addition")} - original_roster
    if any((run["cohort"]["key"], run["model_key"]) not in original_roster | additions
           for run in runs if run["provenance"]["scope"] != "pilot"):
        raise ValueError("Current results must belong to their cohort's frozen roster")
    groups, duplicates = repetition_groups(snapshots, runs, original_roster, additions)
    runs = [run for run in runs if run["slug"] not in duplicates]

    def added_ranked(run: dict) -> bool:
        return (run["cohort"]["key"], run["model_key"]) in additions and run.get("ranked", False)

    cohort_keys = {snapshot["cohort"]["key"] for snapshot in snapshots}
    excluded_models = [{"cohort_key": key, "name": name, "model_key": price_id(name).rsplit("/", 1)[-1], "reason": reason} for key, name, reason in excluded]
    for model in excluded_models:
        if model["cohort_key"] not in cohort_keys or (model["cohort_key"], model["model_key"]) in original_roster | additions or not model["reason"].strip():
            raise ValueError("A launch exclusion needs a published cohort, a model outside its frozen roster and a reason")
    cohorts = sorted(({**snapshot["cohort"]} for snapshot in snapshots), key=cohort_order)
    cohorts = list({cohort["key"]: cohort for cohort in cohorts}.values())
    for cohort in cohorts:
        members = [run for run in runs if run["cohort"]["key"] == cohort["key"]]
        ranked_members = sorted((run for run in members if run.get("ranked")), key=lambda run: (-run["score"], run["model_key"]))
        for rank, run in enumerate(ranked_members, 1):
            run["rank"] = rank
        cohort["results"] = sum(run.get("ranked", run["provenance"]["scope"] not in ("pilot", "repetitions")) for run in members)
        cohort["main_model_roster"] = sum(key == cohort["key"] for key, _ in original_roster)
        cohort["selection_counts"] = {name: sum(run["provenance"]["scope"] == scope for run in members) for name, scope in (
            ("archive_only_recoveries", "recovery"),
            ("native_continuation_successes", "continuation"), ("musical_pilots", "pilot"))}
        cohort["selection_counts"]["main_first_successes"] = sum(
            model.get("selected_attempt") is not None for snapshot in snapshots
            if snapshot["scope"] == "main" and snapshot["cohort"]["key"] == cohort["key"] for model in snapshot["roster"])
        cohort["ranking_policy"] = "best of 3"
        cohort["selection_counts"]["ranked_best_of_three"] = sum(run.get("ranked", False) for run in members)
        cohort["selection_counts"]["eligible_attempts"] = sum(run.get("ranking_policy") == "best of 3" for run in members)
        if any(key == cohort["key"] for key, _ in additions):
            cohort["roster_additions"] = sum(key == cohort["key"] for key, _ in additions)
            cohort["selection_counts"]["rerun_queue_additions"] = sum(added_ranked(run) for run in members)
        repeated = [group for group in groups if group["cohort_key"] == cohort["key"]]
        if repeated:
            cohort["repetitions"] = {"models": len(repeated), "declared_attempts": sum(group["declared"] for group in repeated),
                                     "eligible_attempts": sum(group["eligible"] for group in repeated),
                                     "pending_attempts": sum(group["pending"] for group in repeated),
                                     "unranked_playable_attempts": sum(attempt["eligible"] and not attempt["ranked"] for group in repeated for attempt in group["attempts"])}
            queued = [group for group in repeated if group.get("rerun_queue")]
            if queued:
                cohort["repetitions"]["rerun_queue"] = {"models": len(queued), "reruns": sum(group["reruns"] for group in queued),
                                                        "rerun_attempts": sum(bool(attempt["superseded"]) for group in queued for attempt in group["attempts"]),
                                                        "pending_reruns": sum(attempt["queue_pending"] for group in queued for attempt in group["attempts"])}
    publish_root.mkdir(parents=True, exist_ok=True)
    dist = publish_root / "dist"
    dist.mkdir()
    for source, snapshot in zip(sources, snapshots):
        for run in snapshot["runs"]:
            if run["slug"] in duplicates:
                continue
            for key, relative in run["media"].items():
                path = Path(relative)
                if path.is_absolute() or ".." in path.parts or key not in {"xm", "wav", "audio", "evaluation"}:
                    raise ValueError("Unsupported public media path")
                extension = {"xm": ".xm", "wav": ".wav", "audio": ".mp3", "evaluation": ".json"}[key]
                expected = Path("evaluations" if key == "evaluation" else "media") / (run["slug"] + extension)
                if path != expected or (source / path).is_symlink():
                    raise ValueError("Public media path differs from its allowlist")
                target = dist / path
                target.parent.mkdir(parents=True, exist_ok=True)
                if key == "evaluation":
                    evaluation = {key: value for key, value in run.items() if key not in {"trace", "media", "price", "cost_usd"}}
                    target.write_text(json.dumps(evaluation, separators=(",", ":"), allow_nan=False) + "\n")
                else:
                    shutil.copyfile(source / path, target)
                    digest = hashlib.sha256()
                    with target.open("rb") as stream:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                    if digest.hexdigest() != run["provenance"]["public_media_sha256"]["mp3" if key == "audio" else key]:
                        raise ValueError("Copied public media checksum mismatch")
    runs.sort(key=lambda run: (run["exhibition"], run["name"].lower()))
    main_count = sum(cohort["selection_counts"]["main_first_successes"] for cohort in cohorts)
    recovery_count = sum(run["provenance"]["scope"] == "recovery" for run in runs)
    continuation_count = sum(run["provenance"]["scope"] == "continuation" for run in runs)
    pilot_count = sum(run["provenance"]["scope"] == "pilot" for run in runs)
    addition_count = sum(added_ranked(run) for run in runs)
    native_count = sum(run.get("ranked", False) for run in runs) + recovery_count + continuation_count
    model_count = len(original_roster | additions)
    generated = datetime.now(timezone.utc).isoformat()
    public_ids = {snapshot["campaign_sha256"]: snapshot["campaign_id"] for snapshot in snapshots}
    availability = (f"{native_count}/{model_count} available" if len(cohorts) == 1 else
                    " | ".join(f"{cohort['label']}: {cohort['results']}/{cohort['main_model_roster'] + cohort.get('roster_additions', 0)}" for cohort in cohorts))
    out = {
        "generated": generated, "dataset_kind": "native-best-of-three", "ranking_policy": "best of 3",
        "publication_note": f"Best-of-3 snapshot {generated[:10]} | {availability}",
        "selection_counts": {"main_first_successes": main_count, "ranked_best_of_three": sum(run.get("ranked", False) for run in runs),
                             "eligible_attempts": sum(group["eligible"] for group in groups),
                             "archive_only_recoveries": recovery_count, "native_continuation_successes": continuation_count,
                             "musical_pilots": pilot_count, "main_model_roster": model_count,
                             **({"rerun_queue_additions": addition_count} if additions else {})},
        "ranked_results": sum(run.get("ranked", False) for run in runs),
        "eligible_attempts": sum(group["eligible"] for group in groups),
        "pending_models": sum(not group["eligible"] for group in groups),
        "cohorts": cohorts,
        "limitations": [
            "This is an immutable snapshot, not a live campaign monitor.",
            "Scores are craft-v7 auxiliary tonal-development diagnostics, not musical-quality ranks.",
            ATTEMPT_NOTE if groups else SAMPLE_NOTE,
            TIER_NOTE,
            *(["The musical pilot is labeled separately and is excluded from the main-campaign counts."] if pilot_count else []),
            *(["Archive-only recovered historical attempts are labeled separately. Original finalization-error histories and existing selections remain unchanged."] if recovery_count else []),
            *([f"{continuation_count} native continuation successes use separately frozen cohorts. Their own cohort and evaluator fingerprints apply; original histories are not rewritten."] if continuation_count else []),
            "MP3 is a listening derivative. WAV is the original canonical evaluation audio; XM is the original module.",
            "List-price estimates use maker prices retrieved 2026-09-29, not actual provider bills.",
            "The historical 2026-09-29 prototype dataset is not mixed into this snapshot.",
        ],
        "campaigns": [{**{key: snapshot[key] for key in ("campaign_id", "campaign_sha256", "scope", "generated", "counts", "roster")}, "metadata_captured": snapshot.get("metadata_captured"),
                       **({"attempt_selection": snapshot["attempt_selection"],
                           "linked_campaigns": [{"campaign_id": public_ids[item["campaign_sha256"]], "campaign_sha256": item["campaign_sha256"],
                                                 "repetitions": item.get("repetitions")} for item in snapshot["linked_campaigns"]]}
                          if snapshot["scope"] == "repetitions" else {})} for snapshot in snapshots],
        "flag_rules": FLAG_RULES, "runs": runs,
        **({"excluded_models": excluded_models} if excluded_models else {}),
    }
    if groups:
        repeated_cohorts = [cohort for cohort in cohorts if "repetitions" in cohort]
        out["limitations"] += [
            f"{cohort['label']}: all {cohort['repetitions']['models']} models retain three predetermined ordinal slots. "
            "The best eligible score is ranked and every eligible sample remains playable. Failed and unstarted slots "
            "are listed without media or invented scores. Attempts outside the frozen condition never count as repetitions."
            for cohort in repeated_cohorts]
        out["limitations"] += [
            f"{cohort['label']}: a later rerun queue covers {cohort['repetitions']['rerun_queue']['models']} models. Their provider-limit, "
            "infrastructure and unstarted attempts were rerun as separate attempts under the same frozen condition. Each attempt shows "
            "the last run of its chain; the runs it superseded are listed without media. Scored attempts and model failures are never rerun."
            for cohort in repeated_cohorts if "rerun_queue" in cohort["repetitions"]]
        out["repetition_groups"] = sorted(groups, key=lambda group: (cohort_order(next(c for c in cohorts if c["key"] == group["cohort_key"])), group["name"].lower()))
    (dist / "data.json").write_text(json.dumps(out, separators=(",", ":"), allow_nan=False) + "\n")
    assets = ["index.html", "app.js", "site.js"]
    assets += [str(path.relative_to(HERE)) for path in (HERE / "core").glob("*.js")]
    assets += ["core/ft2.css", "core/ft2gfx/tables.json", "core/ft2gfx/LICENSE-gfx.txt"]
    assets += [str(path.relative_to(HERE)) for path in (HERE / "core/fonts").glob("*.woff2")]
    assets += [str(path.relative_to(HERE)) for path in (HERE / "core/ft2gfx").glob("*.png")]
    for relative in assets:
        source, target = HERE / relative, publish_root / relative
        if source.is_symlink():
            raise ValueError("Public assets must not be symlinks")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"{native_count} ranked results, {sum(group['eligible'] for group in groups)} eligible ordinal samples -> {publish_root}")
    if groups:
        print(f"{len(groups)} best-of-3 groups, {sum(not group['eligible'] for group in groups)} pending models")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build the existing FT2 website from explicit sanitized snapshots.")
    parser.add_argument("--snapshot", type=Path, action="append", help="Public-only output of collect_public.py; repeat for controllers/pilot")
    parser.add_argument("--publish-root", type=Path, default=HERE / "dist-public")
    parser.add_argument("--excluded-model", nargs=3, action="append", default=[], metavar=("COHORT_KEY", "MODEL", "REASON"),
                        help="List a model withheld from a cohort's frozen roster before launch, with its public reason")
    parser.add_argument("--legacy", action="store_true", help="Explicitly build the historical prototype, not current campaign results")
    args = parser.parse_args()
    if args.legacy:
        if args.snapshot or args.excluded_model:
            parser.error("--legacy cannot be mixed with current snapshots")
        build_legacy()
    elif args.snapshot:
        build_snapshots(args.snapshot, args.publish_root, [tuple(item) for item in args.excluded_model])
    else:
        parser.error("Specify --snapshot directories from collect_public.py, or --legacy for the historical prototype")
