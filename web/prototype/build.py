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
# Replaces SAMPLE_NOTE when later independent repetitions are published beside the ranked attempt 1.
ATTEMPT_NOTE = ("Ranking uses attempt 1 only: the same predetermined slot for every model, whatever later attempts scored. "
                "Models with independent repetitions under the same frozen condition show them as separate, unranked "
                "attempts; they are never combined into the ranked score. Quota, funds, rate-limit and auth stops are "
                "infrastructure, and the slots they leave unstarted are labeled not run.")
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


def queue_precedence(snapshots: list[dict]) -> None:
    """A rerun queue's group replaces the independent-repeats group of the same model, with that group's runs.

    The queue re-exports every chain's sample, including repeats attempts it did not rerun, so nothing is lost.
    A superseded repeats campaign must be one the queue takes origins from.
    """
    covered = {}
    for snapshot in snapshots:
        if snapshot["scope"] == "repetitions" and snapshot.get("attempt_selection") == QUEUE_SELECTION:
            linked = {item["campaign_sha256"] for item in snapshot["linked_campaigns"]}
            for group in snapshot["repetition_groups"]:
                covered.setdefault((snapshot["cohort"]["key"], price_id(group["name"]).rsplit("/", 1)[-1]), []).append(linked)
    for snapshot in snapshots:
        if snapshot["scope"] != "repetitions" or snapshot.get("attempt_selection") != INDEPENDENT_SELECTION:
            continue
        replaced = set()
        for group in snapshot["repetition_groups"]:
            model = (snapshot["cohort"]["key"], price_id(group["name"]).rsplit("/", 1)[-1])
            if model in covered:
                if any(snapshot["campaign_sha256"] not in linked for linked in covered[model]):
                    raise ValueError(f"{group['name']}: a rerun queue may replace only the repeats campaign it takes origins from")
                replaced.add(model[1])
        snapshot["repetition_groups"] = [group for group in snapshot["repetition_groups"] if price_id(group["name"]).rsplit("/", 1)[-1] not in replaced]
        snapshot["runs"] = [run for run in snapshot["runs"] if run["model_key"] not in replaced]


def repetition_groups(snapshots: list[dict], runs: list[dict], roster: set, additions: set) -> tuple[list[dict], set]:
    """Public attempt groups and the repetition-1 slugs that duplicate their ranked main row.

    Ranking uses attempt 1 only. A group attaches to its model's main row only when that row is the
    group's own repetition 1 (same campaign, attempt ordinal 1, profile and inputs); anything else is
    refused. Later eligible repetitions become unranked runs linked to that row; no aggregate is built.
    A model added to the roster in a rerun queue (`additions`) has no main row: its eligible attempt 1
    is its ranked row. Rerun-queue attempts list the attempts their chain superseded, without media.
    """
    # Every campaign an attempt comes from must be published in this build, within the same cohort.
    published = {snapshot["campaign_sha256"]: (snapshot["campaign_id"], snapshot["cohort"],
                                               SOURCE_LABELS["main" if snapshot["scope"] == "main" else snapshot.get("attempt_selection")])
                 for snapshot in snapshots if snapshot["scope"] == "main" or (snapshot["scope"] == "repetitions" and snapshot.get("attempt_selection") in SOURCE_LABELS)}
    main_runs = {(run["cohort"]["key"], run["model_key"]): run for run in runs if run["provenance"]["scope"] == "main"}
    groups, duplicates, seen = [], set(), set()
    for snapshot in snapshots:
        if snapshot["scope"] != "repetitions":
            continue
        queue = snapshot.get("attempt_selection") == QUEUE_SELECTION
        if snapshot.get("attempt_selection") not in (INDEPENDENT_SELECTION, QUEUE_SELECTION) or not isinstance(snapshot.get("repetition_groups"), list):
            raise ValueError(f"{snapshot['campaign_id']}: a repetitions snapshot needs independent repetition groups")
        public = {}
        for item in snapshot["linked_campaigns"]:
            sha = item["campaign_sha256"]
            if sha not in published or published[sha][1] != snapshot["cohort"]:
                raise ValueError("Every linked repetition campaign must be published as a main or repetitions snapshot of the same cohort in this build")
            public[sha] = published[sha]
        by_slug = {run["slug"]: run for run in snapshot["runs"]}
        claimed = set()
        for run in snapshot["runs"]:
            if run["provenance"]["campaign_sha256"] not in public:
                raise ValueError(f"{run['name']}: repetition result comes from an undeclared campaign")
            run["provenance"]["source_campaign_id"] = public[run["provenance"]["campaign_sha256"]][0]

        def source(attempt: dict) -> dict:
            campaign_id, _, label = public[attempt["source_campaign_sha256"]]
            return {"source_campaign_id": campaign_id, "source": label}

        for group in snapshot["repetition_groups"]:
            model_key = price_id(group["name"]).rsplit("/", 1)[-1]
            key = (snapshot["cohort"]["key"], model_key)
            addition = bool(group.get("roster_addition"))
            if (key in seen or key not in (additions if addition else roster) or group.get("cohort") != snapshot["cohort"]
                    or (addition and not queue)):
                raise ValueError(f"{group['name']}: repetition groups need one row per model of their cohort's main roster or rerun-queue additions")
            seen.add(key)
            if [attempt["ordinal"] for attempt in group["attempts"]] != list(range(1, group["declared"] + 1)):
                raise ValueError(f"{group['name']}: repetitions must list every declared ordinal once, in order")
            if sum(bool(attempt["eligible"]) for attempt in group["attempts"]) != group["eligible"]:
                raise ValueError(f"{group['name']}: repetition eligible count differs from its attempts")
            first = by_slug.get(group["attempts"][0]["slug"]) if group["attempts"][0]["slug"] else None
            if addition:
                # Its eligible attempt 1 is the ranked row; later attempts need that row to attach to.
                main = first if first and first["provenance"].get("roster_addition") and first["provenance"]["attempt_ordinal"] == 1 else None
                if main is None and group["eligible"]:
                    raise ValueError(f"{group['name']}: a roster addition without an eligible attempt 1 has no ranked row for its later attempts")
            else:
                main = main_runs.get(key)
                if not (main and first and main["provenance"]["attempt_ordinal"] == 1 and main["score"] == first["score"]
                        and all(main["provenance"].get(field) == first["provenance"].get(field)
                                for field in ("campaign_sha256", "profile_sha256", "input_sha256", "evaluation_fingerprint"))):
                    raise ValueError(f"{group['name']}: repetition 1 is not the cohort's ranked main attempt 1; refusing to attach later attempts")
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
                    if attempt["ordinal"] == 1 and not addition:
                        duplicates.add(run["slug"])
                    elif attempt["ordinal"] != 1:
                        run.update(ranked=False, attempt_of=main["slug"])
                attempts.append({**{key: attempt[key] for key in ("ordinal", "status", "outcome", "eligible", "attempted", "stopped_by",
                                                                  "failure_category", "model_failure", "score", "source_campaign_sha256")},
                                 "slug": main["slug"] if attempt["ordinal"] == 1 and main else attempt["slug"], "ranked": attempt["ordinal"] == 1 and main is not None,
                                 **source(attempt),
                                 **({"queue_pending": attempt["queue_pending"],
                                     "superseded": [{**{field: link[field] for field in ("status", "outcome", "failure_category", "attempted", "stopped_by",
                                                                                         "source_campaign_sha256")}, **source(link)}
                                                    for link in attempt["superseded"]]} if queue else {})})
            maker = public_maker(group["name"], {})
            groups.append({"cohort_key": key[0], "model_key": model_key, "name": group["name"],
                           "maker": group["maker"] if maker == "Other" else maker, "tier": group["tier"],
                           "campaign_id": snapshot["campaign_id"], "condition_fingerprint": group["condition_fingerprint"],
                           **{field: group[field] for field in ("declared", "eligible", "pending", "state")},
                           **({"rerun_queue": True, "reruns": sum(len(attempt["superseded"]) for attempt in group["attempts"]),
                               "roster_addition": addition} if queue else {}),
                           "attempts": attempts,
                           "outside_condition": [{**{field: attempt[field] for field in ("ordinal", "status", "failure_category", "attempted", "operator_cancelled",
                                                                                         "retry", "source_campaign_sha256")},
                                                  "source_campaign_id": public[attempt["source_campaign_sha256"]][0] if attempt["source_campaign_sha256"] in public else "unpublished campaign",
                                                  "source": public[attempt["source_campaign_sha256"]][2] if attempt["source_campaign_sha256"] in public else "unpublished campaign"}
                                                 for attempt in group["outside_condition"]],
                           "ranked_slug": main["slug"] if main else None})
        if claimed != set(by_slug):
            raise ValueError(f"{snapshot['campaign_id']}: every repetition result must belong to its model's group")
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
    queue_precedence(snapshots)
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
    # Models a rerun queue added after requalification join their cohort's roster; they were never in the main campaign.
    additions = {(model["cohort_key"], model["model_key"]) for snapshot in snapshots if snapshot.get("attempt_selection") == QUEUE_SELECTION
                 for model in snapshot["roster"] if model.get("roster_addition")}
    if additions & original_roster:
        raise ValueError("A rerun-queue roster addition must be outside its cohort's main roster")
    selected_models = [(run["cohort"]["key"], run["model_key"]) for run in runs if run["provenance"]["scope"] not in ("pilot", "repetitions")]
    repeated_models = [(run["cohort"]["key"], run["model_key"]) for run in runs if run["provenance"]["scope"] == "repetitions"]
    if len(set(selected_models)) != len(selected_models) or any(model not in original_roster | additions for model in selected_models + repeated_models):
        raise ValueError("Current selections must belong to their cohort's original roster without duplicate model rows")
    # Ranking stays on attempt 1; later repetitions are unranked runs linked to it. Roster and availability counts stay the main snapshot's.
    groups, duplicates = repetition_groups(snapshots, runs, original_roster, additions)
    runs = [run for run in runs if run["slug"] not in duplicates]

    def added_ranked(run: dict) -> bool:
        return bool(run["provenance"].get("roster_addition")) and not run.get("attempt_of")

    cohort_keys = {snapshot["cohort"]["key"] for snapshot in snapshots}
    excluded_models = [{"cohort_key": key, "name": name, "model_key": price_id(name).rsplit("/", 1)[-1], "reason": reason} for key, name, reason in excluded]
    for model in excluded_models:
        if model["cohort_key"] not in cohort_keys or (model["cohort_key"], model["model_key"]) in original_roster | additions or not model["reason"].strip():
            raise ValueError("A launch exclusion needs a published cohort, a model outside its frozen roster and a reason")
    cohorts = sorted(({**snapshot["cohort"]} for snapshot in snapshots), key=cohort_order)
    cohorts = list({cohort["key"]: cohort for cohort in cohorts}.values())
    for cohort in cohorts:
        members = [run for run in runs if run["cohort"]["key"] == cohort["key"]]
        cohort["results"] = sum(run["provenance"]["scope"] not in ("pilot", "repetitions") or added_ranked(run) for run in members)
        cohort["main_model_roster"] = sum(key == cohort["key"] for key, _ in original_roster)
        cohort["selection_counts"] = {name: sum(run["provenance"]["scope"] == scope for run in members) for name, scope in (
            ("main_first_successes", "main"), ("archive_only_recoveries", "recovery"),
            ("native_continuation_successes", "continuation"), ("musical_pilots", "pilot"))}
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
    main_snapshots = [snapshot for snapshot in snapshots if snapshot["scope"] == "main"]
    main_count = sum(run["provenance"]["scope"] == "main" for run in runs)
    recovery_count = sum(run["provenance"]["scope"] == "recovery" for run in runs)
    continuation_count = sum(run["provenance"]["scope"] == "continuation" for run in runs)
    pilot_count = sum(run["provenance"]["scope"] == "pilot" for run in runs)
    addition_count = sum(added_ranked(run) for run in runs)
    native_count = main_count + recovery_count + continuation_count + addition_count
    model_count = sum(len(snapshot["roster"]) for snapshot in main_snapshots) + len(additions)
    generated = datetime.now(timezone.utc).isoformat()
    public_ids = {snapshot["campaign_sha256"]: snapshot["campaign_id"] for snapshot in snapshots}
    availability = (f"{native_count}/{model_count} available" if len(cohorts) == 1 else
                    " | ".join(f"{cohort['label']}: {cohort['results']}/{cohort['main_model_roster'] + cohort.get('roster_additions', 0)}" for cohort in cohorts))
    out = {
        "generated": generated, "dataset_kind": "native-first-success",
        "publication_note": f"Main snapshot {generated[:10]} | {availability}",
        "selection_counts": {"main_first_successes": main_count, "archive_only_recoveries": recovery_count, "native_continuation_successes": continuation_count, "musical_pilots": pilot_count, "main_model_roster": model_count,
                             **({"rerun_queue_additions": addition_count} if additions else {})},
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
            f"{cohort['label']}: {cohort['repetitions']['models']} models also ran later predetermined independent repetitions under the "
            "same frozen condition. Each eligible later attempt is playable from its model's attempt switcher and labeled not ranked; "
            "failed and unstarted attempts are listed without media. Attempts outside the frozen condition, such as an operator-cancelled "
            "slot, are listed but never count as repetitions." for cohort in repeated_cohorts]
        out["limitations"] += [
            f"{cohort['label']}: a later rerun queue covers {cohort['repetitions']['rerun_queue']['models']} models. Their provider-limit, "
            "infrastructure and unstarted attempts were rerun as separate attempts under the same frozen condition. Each attempt shows "
            "the last run of its chain; the runs it superseded are listed without media. Scored attempts and model failures are never rerun."
            for cohort in repeated_cohorts if "rerun_queue" in cohort["repetitions"]]
        out["limitations"] += [
            f"{group['name']} joined the roster after requalification and ran in the rerun queue under the same frozen condition. "
            "Only its attempt 1 can be ranked, like every other model's; its later attempts are not ranked." for group in groups if group.get("roster_addition")]
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
    print(f"{main_count} original main first successes, {recovery_count} labeled recoveries, {continuation_count} native continuations, {pilot_count} labeled pilots"
          f"{f', {addition_count} ranked rerun-queue roster additions of {len(additions)}' if additions else ''} -> {publish_root}")
    if groups:
        print(f"{len(groups)} attempt groups: {sum(attempt['eligible'] and not attempt['ranked'] for group in groups for attempt in group['attempts'])} unranked playable attempts beside {len(duplicates) + addition_count} ranked attempt-1 rows")


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
