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
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from benchmark.report import REPETITION_NOTE, SAMPLE_NOTE, TIER_NOTE, campaign_cohort, read_cohort, tier_label

RUNS = ROOT / "legacy/previous-work-20260930/benchmark/runs"
HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
MEDIA = DIST / "media"
# Tables are ordered by condition; a cohort is never ranked together with another one.
CONDITION_ORDER = ("highest-declared-tier", "declared-tier", "provider-default")
LEGACY_COHORT = {"key": "historical-prototype-20260929", "condition": "historical-prototype", "prompt_version": "prompt-v1",
                 "label": "historical prototype 2026-09-29, effort as recorded per model, prompt-v1"}

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


def repetition_groups(snapshots: list[dict], runs: list[dict], roster: set) -> tuple[list[dict], dict]:
    """Public repetition groups and {superseded main slug: repetition-1 slug}.

    A group replaces its model's main first-success row only when that row is the group's own
    repetition 1 (same campaign, attempt ordinal 1, profile and inputs); anything else is refused.
    """
    main_cohorts = {snapshot["campaign_sha256"]: snapshot["cohort"] for snapshot in snapshots if snapshot["scope"] == "main"}
    main_runs = {(run["cohort"]["key"], run["model_key"]): run for run in runs if run["provenance"]["scope"] == "main"}
    groups, aliases, seen = [], {}, set()
    for snapshot in snapshots:
        if snapshot["scope"] != "repetitions":
            continue
        if snapshot.get("attempt_selection") != "independent_repetitions" or not isinstance(snapshot.get("repetition_groups"), list):
            raise ValueError(f"{snapshot['campaign_id']}: a repetitions snapshot needs independent repetition groups")
        public = {}
        for item in snapshot["linked_campaigns"]:
            sha = item["campaign_sha256"]
            if sha == snapshot["campaign_sha256"]:
                public[sha] = snapshot["campaign_id"]
            elif main_cohorts.get(sha) == snapshot["cohort"]:
                public[sha] = f"main-{sha[:12]}"
            else:
                raise ValueError("Every linked repetition campaign must be published as a main snapshot of the same cohort in this build")
        by_slug = {run["slug"]: run for run in snapshot["runs"]}
        claimed = set()
        for run in snapshot["runs"]:
            if run["provenance"]["campaign_sha256"] not in public:
                raise ValueError(f"{run['name']}: repetition result comes from an undeclared campaign")
            run["provenance"]["source_campaign_id"] = public[run["provenance"]["campaign_sha256"]]
        for group in snapshot["repetition_groups"]:
            model_key = price_id(group["name"]).rsplit("/", 1)[-1]
            key = (snapshot["cohort"]["key"], model_key)
            if key in seen or key not in roster or group.get("cohort") != snapshot["cohort"]:
                raise ValueError(f"{group['name']}: repetition groups need one row per model of their cohort's main roster")
            seen.add(key)
            if [attempt["ordinal"] for attempt in group["attempts"]] != list(range(1, group["declared"] + 1)):
                raise ValueError(f"{group['name']}: repetitions must list every declared ordinal once, in order")
            attempts = []
            for attempt in group["attempts"]:
                run = by_slug.get(attempt["slug"]) if attempt["slug"] else None
                if bool(attempt["eligible"]) != (run is not None) or (run and (
                        run["model_key"] != model_key or run["score"] != attempt["score"]
                        or run["provenance"]["attempt_ordinal"] != attempt["ordinal"]
                        or run["provenance"]["campaign_sha256"] != attempt["source_campaign_sha256"]
                        or run["provenance"]["condition_fingerprint"] != group["condition_fingerprint"])):
                    raise ValueError(f"{group['name']}: repetition {attempt['ordinal']} differs from its published result")
                if run:
                    claimed.add(run["slug"])
                attempts.append({**{key: attempt[key] for key in ("ordinal", "status", "outcome", "eligible", "failure_category",
                                                                  "model_failure", "score", "slug", "source_campaign_sha256")},
                                 "source_campaign_id": public[attempt["source_campaign_sha256"]]})
            scores = [attempt["score"] for attempt in attempts if attempt["eligible"]]
            if len(scores) != group["eligible"] or (scores and (group["median"], group["min"], group["max"]) != (statistics.median(scores), min(scores), max(scores))):
                raise ValueError(f"{group['name']}: repetition summary differs from its attempts")
            main = main_runs.get(key)
            if main:
                first = by_slug.get(attempts[0]["slug"]) if attempts[0]["slug"] else None
                if not (first and main["provenance"]["attempt_ordinal"] == 1 and main["score"] == first["score"]
                        and all(main["provenance"].get(field) == first["provenance"].get(field)
                                for field in ("campaign_sha256", "profile_sha256", "input_sha256", "evaluation_fingerprint"))):
                    raise ValueError(f"{main['name']}: the main first success is not repetition 1 of its repetition group; refusing to replace it")
                aliases[main["slug"]] = first["slug"]
            maker = public_maker(group["name"], {})
            groups.append({"cohort_key": key[0], "model_key": model_key, "name": group["name"],
                           "maker": group["maker"] if maker == "Other" else maker, "tier": group["tier"],
                           "campaign_id": snapshot["campaign_id"], "condition_fingerprint": group["condition_fingerprint"],
                           **{field: group[field] for field in ("declared", "eligible", "pending", "median", "min", "max", "range", "state")},
                           "attempts": attempts,
                           "outside_condition": [{**{field: attempt[field] for field in ("ordinal", "status", "failure_category", "attempted", "operator_cancelled",
                                                                                         "retry", "source_campaign_sha256")},
                                                  "source_campaign_id": public.get(attempt["source_campaign_sha256"], "unpublished campaign")}
                                                 for attempt in group["outside_condition"]],
                           "superseded_main_slug": main["slug"] if main else None})
        if claimed != set(by_slug):
            raise ValueError(f"{snapshot['campaign_id']}: every repetition result must belong to its model's group")
    return groups, aliases


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


def build_snapshots(sources: list[Path], publish_root: Path) -> None:
    """Assemble only explicitly allowlisted assets from sanitized public snapshots."""
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
    if not runs or len({run["slug"] for run in runs}) != len(runs):
        raise ValueError("Public snapshots need results with unique slugs")
    # Uniqueness and roster membership hold within one cohort; cohorts are separate experiments.
    original_hashes = {snapshot["campaign_sha256"] for snapshot in snapshots if snapshot["scope"] == "main"}
    original_models = {(run["cohort"]["key"], run["model_key"]) for run in runs if run["provenance"]["scope"] == "main"}
    for run in runs:
        if run["provenance"]["scope"] == "recovery":
            if run["provenance"]["campaign_sha256"] not in original_hashes or (run["cohort"]["key"], run["model_key"]) in original_models:
                raise ValueError("A recovery must belong to an original main cohort and cannot replace its selected success")
    original_roster = {(model["cohort_key"], model["model_key"]) for snapshot in snapshots if snapshot["scope"] == "main" for model in snapshot["roster"]}
    selected_models = [(run["cohort"]["key"], run["model_key"]) for run in runs if run["provenance"]["scope"] not in ("pilot", "repetitions")]
    repeated_models = [(run["cohort"]["key"], run["model_key"]) for run in runs if run["provenance"]["scope"] == "repetitions"]
    if len(set(selected_models)) != len(selected_models) or any(model not in original_roster for model in selected_models + repeated_models):
        raise ValueError("Current selections must belong to their cohort's original roster without duplicate model rows")
    # Repetition groups replace their models' main rows; roster and availability counts stay the main snapshot's.
    groups, aliases = repetition_groups(snapshots, runs, original_roster)
    cohorts = sorted(({**snapshot["cohort"]} for snapshot in snapshots), key=cohort_order)
    cohorts = list({cohort["key"]: cohort for cohort in cohorts}.values())
    for cohort in cohorts:
        members = [run for run in runs if run["cohort"]["key"] == cohort["key"]]
        cohort["results"] = sum(run["provenance"]["scope"] not in ("pilot", "repetitions") for run in members)
        cohort["main_model_roster"] = sum(key == cohort["key"] for key, _ in original_roster)
        cohort["selection_counts"] = {name: sum(run["provenance"]["scope"] == scope for run in members) for name, scope in (
            ("main_first_successes", "main"), ("archive_only_recoveries", "recovery"),
            ("native_continuation_successes", "continuation"), ("musical_pilots", "pilot"))}
        repeated = [group for group in groups if group["cohort_key"] == cohort["key"]]
        if repeated:
            cohort["repetitions"] = {"models": len(repeated), "declared_attempts": sum(group["declared"] for group in repeated),
                                     "eligible_attempts": sum(group["eligible"] for group in repeated),
                                     "pending_attempts": sum(group["pending"] for group in repeated),
                                     "superseded_main_first_successes": sum(group["superseded_main_slug"] is not None for group in repeated)}
    publish_root.mkdir(parents=True, exist_ok=True)
    dist = publish_root / "dist"
    dist.mkdir()
    for source, snapshot in zip(sources, snapshots):
        for run in snapshot["runs"]:
            if run["slug"] in aliases:
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
    main_snapshots = [snapshot for snapshot in snapshots if snapshot["scope"] == "main"]
    main_count = sum(run["provenance"]["scope"] == "main" for run in runs)
    recovery_count = sum(run["provenance"]["scope"] == "recovery" for run in runs)
    continuation_count = sum(run["provenance"]["scope"] == "continuation" for run in runs)
    pilot_count = sum(run["provenance"]["scope"] == "pilot" for run in runs)
    native_count = main_count + recovery_count + continuation_count
    model_count = sum(len(snapshot["roster"]) for snapshot in main_snapshots)
    generated = datetime.now(timezone.utc).isoformat()
    availability = (f"{native_count}/{model_count} available" if len(cohorts) == 1 else
                    " | ".join(f"{cohort['label']}: {cohort['results']}/{cohort['main_model_roster']}" for cohort in cohorts))
    out = {
        "generated": generated, "dataset_kind": "native-first-success",
        "publication_note": f"Main snapshot {generated[:10]} | {availability}",
        "selection_counts": {"main_first_successes": main_count, "archive_only_recoveries": recovery_count, "native_continuation_successes": continuation_count, "musical_pilots": pilot_count, "main_model_roster": model_count},
        "cohorts": cohorts,
        "limitations": [
            "This is an immutable snapshot, not a live campaign monitor.",
            "Scores are craft-v7 auxiliary tonal-development diagnostics, not musical-quality ranks.",
            SAMPLE_NOTE,
            TIER_NOTE,
            "The musical pilot is labeled separately and is excluded from the main-campaign counts.",
            "Archive-only recovered historical attempts are labeled separately. Original finalization-error histories and existing selections remain unchanged.",
            f"{continuation_count} native continuation successes use separately frozen cohorts. Their own cohort and evaluator fingerprints apply; original histories are not rewritten.",
            "MP3 is a listening derivative. WAV is the original canonical evaluation audio; XM is the original module.",
            "List-price estimates use maker prices retrieved 2026-09-29, not actual provider bills.",
            "The historical 2026-09-29 prototype dataset is not mixed into this snapshot.",
        ],
        "campaigns": [{**{key: snapshot[key] for key in ("campaign_id", "campaign_sha256", "scope", "generated", "counts", "roster")}, "metadata_captured": snapshot.get("metadata_captured"),
                       **({"attempt_selection": snapshot["attempt_selection"],
                           "linked_campaigns": [{"campaign_id": snapshot["campaign_id"] if item["campaign_sha256"] == snapshot["campaign_sha256"] else f"main-{item['campaign_sha256'][:12]}",
                                                 "campaign_sha256": item["campaign_sha256"], "repetitions": item["repetitions"]} for item in snapshot["linked_campaigns"]]}
                          if snapshot["scope"] == "repetitions" else {})} for snapshot in snapshots],
        "flag_rules": FLAG_RULES, "runs": [run for run in runs if run["slug"] not in aliases],
    }
    if groups:
        repeated_cohorts = [cohort for cohort in cohorts if "repetitions" in cohort]
        out["limitations"] += [REPETITION_NOTE] + [
            f"{cohort['label']}: {cohort['repetitions']['models']} models report every predetermined independent repetition; their row shows "
            "the median and range of the eligible repetitions next to the eligible count, and each attempt is playable. Repetition 1 is the "
            "main campaign's original attempt; attempts outside the frozen condition, such as an operator-cancelled slot, are listed but never "
            "count as repetitions. The cohort's other models keep one first-success sample each." for cohort in repeated_cohorts]
        out["repetition_groups"] = sorted(groups, key=lambda group: (cohort_order(next(c for c in cohorts if c["key"] == group["cohort_key"])), group["name"].lower()))
        out["run_aliases"] = aliases
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
    print(f"{main_count} original main first successes, {recovery_count} labeled recoveries, {continuation_count} native continuations, {pilot_count} labeled pilots -> {publish_root}")
    if groups:
        print(f"{len(groups)} repetition groups with {sum(group['eligible'] for group in groups)} eligible repetitions; {len(aliases)} main rows shown as repetition 1")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build the existing FT2 website from explicit sanitized snapshots.")
    parser.add_argument("--snapshot", type=Path, action="append", help="Public-only output of collect_public.py; repeat for controllers/pilot")
    parser.add_argument("--publish-root", type=Path, default=HERE / "dist-public")
    parser.add_argument("--legacy", action="store_true", help="Explicitly build the historical prototype, not current campaign results")
    args = parser.parse_args()
    if args.legacy:
        if args.snapshot:
            parser.error("--legacy cannot be mixed with current snapshots")
        build_legacy()
    elif args.snapshot:
        build_snapshots(args.snapshot, args.publish_root)
    else:
        parser.error("Specify --snapshot directories from collect_public.py, or --legacy for the historical prototype")
