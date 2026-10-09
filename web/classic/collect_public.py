"""Export a frozen native campaign to public-only website data and verified media.

Read an explicitly selected local campaign. Only pinned XM, canonical WAV, derived
MP3, compact row traces and an allowlisted evaluation summary enter the public
snapshot. Missing or changed local artifacts stop the export.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.artifacts import ArtifactStore
from benchmark.report import INDEPENDENT_SELECTION, QUEUE_SELECTION, build_report, finite_json
from build import FLAG_RULES, compact_trace, estimate_cost, estimate_cost_range, price_id, public_maker, public_price, slug, worst_transition

# Publication reads the evaluator's version without loading its numerical dependencies.
SCORE_VERSION = re.search(r'^SCORE_VERSION = "([^"]+)"$', (ROOT / "benchmark/score.py").read_text(), re.M)[1]


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def public_campaign_ids(value):
    """Replace internal campaign names at the public write boundary without changing report lookups."""
    if isinstance(value, list):
        return [public_campaign_ids(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: public_campaign_ids(item) for key, item in value.items()}
    for key, fingerprint in (
        ("campaign_id", value.get("repetition_campaign_sha256") or value.get("campaign_sha256")),
        ("source_campaign_id", value.get("source_campaign_sha256") or value.get("campaign_sha256")),
    ):
        if key in value:
            if not isinstance(fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
                raise ValueError("Public campaign identifiers require a complete campaign SHA256")
            result[key] = f"campaign-{fingerprint}"
    return result


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(finite_json(public_campaign_ids(value)), ensure_ascii=True, allow_nan=False,
                               separators=(",", ":")) + "\n")
    ArtifactStore.check_secrets(path)


def verified_media(directory: Path, profile: dict, output: Path) -> dict:
    """Copy pinned local presentation inputs, rejecting missing or changed artifacts."""
    wanted = {"submission/tune.xm": output / "tune.xm",
              "canonical/canonical.wav": output / "canonical.wav"}
    expected = {name: profile["inputs"]["artifacts"][name] for name in wanted}
    trace_path = (profile.get("loop") or {}).get("trace_path")
    trace_hash = (profile.get("loop") or {}).get("trace_sha256")
    if isinstance(trace_path, str) and re.fullmatch(r"[a-f0-9]{64}", trace_hash or ""):
        path = Path(trace_path)
        if path.is_absolute() or ".." in path.parts or not trace_path.endswith("trace.jsonl.gz"):
            raise ValueError("Invalid pinned playback trace")
        wanted[trace_path] = output / "trace.jsonl.gz"
        expected[trace_path] = trace_hash
    output.mkdir(parents=True, exist_ok=True)
    for name, target in wanted.items():
        original = directory / name
        if (not original.is_file() or original.is_symlink()
                or not original.resolve().is_relative_to(directory.resolve())
                or sha256(original) != expected[name]):
            raise ValueError(f"Selected result has missing or changed local media: {name}")
        shutil.copyfile(original, target)
        if sha256(target) != expected[name]:
            raise ValueError("Presentation input checksum mismatch")
    return {"input_sha256": expected}


def public_run(row: dict, group: dict, directory: Path, output: Path, campaign: dict,
               scope: str, prices: dict, roster_addition: bool = False) -> dict:
    profile = row["profile"]
    if profile.get("score_version") != SCORE_VERSION or row.get("score_version") != SCORE_VERSION:
        raise ValueError(f"Publication requires {SCORE_VERSION} evaluations; run score.py profile --force before exporting")
    name = price_id(row["model"])
    repetition = scope == "repetitions"
    queue = campaign.get("attempt_selection") == QUEUE_SELECTION
    ordinal = row["repetition"]
    # A model added to the roster in the rerun queue is ranked by its attempt 1, named like every other ranked row.
    ranked_addition = roster_addition and ordinal == 1
    run_slug = slug(name) + (("" if ranked_addition else f"-a{ordinal}") if repetition else {"pilot": "-pilot", "continuation": "-continued"}.get(scope, ""))
    stage = output / ".verified" / run_slug
    verification = verified_media(directory, profile, stage)
    media = output / "media"
    media.mkdir(exist_ok=True)
    for filename, source in ((f"{run_slug}.xm", stage / "tune.xm"),
                             (f"{run_slug}.wav", stage / "canonical.wav")):
        shutil.copyfile(source, media / filename)
    mp3 = media / f"{run_slug}.mp3"
    receipt_path = stage / "mp3-receipt.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
    wav_hash = verification["input_sha256"]["canonical/canonical.wav"]
    if not mp3.is_file() or receipt.get("source_sha256") != wav_hash or receipt.get("mp3_sha256") != sha256(mp3):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(stage / "canonical.wav"),
                        "-codec:a", "libmp3lame", "-b:a", "160k", str(mp3)], check=True)
        write_json(receipt_path, {"source_sha256": wav_hash, "mp3_sha256": sha256(mp3)})
    status = json.loads((directory / "status.json").read_text())
    audio = profile.get("audio") or {}
    structure = profile.get("structure") or {}
    craft = profile["craft"]
    loop = profile.get("loop") or {}
    trace = compact_trace(stage / "trace.jsonl.gz", int(audio["duration_seconds"] * 44100)) if (stage / "trace.jsonl.gz").is_file() else []
    price = prices.get(name, {})
    maker = public_maker(name, price)
    pub_price = public_price(price)
    totals = row["totals"] or {}
    run = {
        "slug": run_slug, "model_key": name,
        "name": name + (("" if ranked_addition else f" (attempt {ordinal})") if repetition else
                        {"pilot": " (musical pilot)", "continuation": " (native continuation)"}.get(scope, "")),
        "maker": maker, "exhibition": scope == "pilot", "tier": row["tier"], "cohort": row["cohort"],
        "status": row["status"], "error": "", "score": row["craft"],
        "parts": {key: craft["parts"][key] for key in ("tonal_organization", "development", "dynamics")},
        "weights": {key: craft["weights"][key] for key in ("tonal_organization", "development", "dynamics")},
        "factors": {key: craft["factors"][key] for key in ("signal_integrity", "loop_continuity")},
        "uncapped": craft["uncapped"], "content": craft["content_score"], "caps": craft.get("caps") or [],
        "flags": [{"id": flag, "rule": FLAG_RULES.get(flag, "")} for flag in profile.get("flags") or []],
        "loop": {"quality": loop.get("quality_score"), "worst": worst_transition(loop),
                 "first_pass_audible_seconds": loop.get("first_pass_audible_seconds")},
        "tonal": {key: (audio.get("spectral") or {}).get(key) for key in ("tonal_evidence_fraction", "diatonic_concentration", "effective_pitch_classes", "sustained_noise_fraction")},
        "development": {key: structure.get(key) for key in ("arrangement_score", "sequence_coverage", "development_method", "development_scales")},
        "audio": {"duration": audio.get("duration_seconds"), "lufs": audio.get("lufs_integrated"), "peak": (status.get("audio") or {}).get("peak")},
        "module": {key: (status.get("module") or {}).get(key) for key in ("name", "channels", "bpm", "speed", "song_length", "loop_start")},
        "usage": {**{key: totals.get(key) for key in ("requests", "prompt_tokens", "cached_tokens", "completion_tokens", "reasoning_tokens", "commands")},
                  "wall_minutes": round(row["wall_s"] / 60, 1) if row["wall_s"] is not None else None,
                  "attempts": group["attempted_count"], "turns": None},
        "price": pub_price, "cost_usd": estimate_cost(totals, pub_price) if not row["usage_unknown"] else None,
        "media": {"xm": f"media/{run_slug}.xm", "audio": f"media/{run_slug}.mp3", "wav": f"media/{run_slug}.wav",
                  "evaluation": f"evaluations/{run_slug}.json"},
        "trace": trace, "rank": None, "failed": False,
        "provenance": {"scope": scope, "campaign_id": f"{scope}-{campaign['campaign_sha256'][:12]}",
                       "campaign_sha256": row["source_campaign_sha256"] if repetition else campaign["campaign_sha256"],
                       "cohort_fingerprint": row["cohort_fingerprint"],
                       "attempt_ordinal": row["repetition"],
                       "selected_by": ("attempt 1 of a model added to the roster in the rerun queue; ranked like every model's attempt 1" if ranked_addition else
                                       "independent predetermined repetition; the last attempt of its infrastructure rerun chain, none is selected" if queue else
                                       "independent predetermined repetition; every repetition is reported, none is selected" if repetition else
                                       "first eligible success among up to three sequential predetermined attempts"),
                       "score_version": row["score_version"], "evaluation_fingerprint": row["evaluation_fingerprint"],
                       "profile_sha256": sha256(directory / "profile.json"), **verification,
                       "public_media_sha256": {key: sha256(media / f"{run_slug}.{ext}") for key, ext in (("xm", "xm"), ("wav", "wav"), ("mp3", "mp3"))}},
    }
    if run["cost_usd"] is None and not row["usage_unknown"]:
        interval = estimate_cost_range(totals, pub_price)
        if interval is not None:
            run["cost_range_usd"] = interval
    if scope == "continuation":
        run["provenance"]["continuation_note"] = "A new frozen native continuation cohort with its own configuration and evaluator fingerprints. Original campaigns, routes and historical outcomes remain unchanged."
    if repetition:
        run["provenance"].update(source_campaign_id=row["source_campaign_id"], repetition_campaign_sha256=campaign["campaign_sha256"],
                                 condition_fingerprint=row["condition_fingerprint"])
    if roster_addition:
        started = status.get("started_at")
        day = f" on {datetime.fromtimestamp(started, timezone.utc).date().isoformat()}" if isinstance(started, (int, float)) else ""
        run["provenance"].update(roster_addition=True, queue_note=(
            f"Added to the roster after requalification under its declared condition. This attempt ran{day} in the "
            "infrastructure rerun queue, under the same frozen condition as every other model."))
    run["module"].update({"patterns": structure.get("distinct_patterns_in_order"), "instruments": structure.get("instruments_used"), "samples": structure.get("samples")})
    evaluation = {key: value for key, value in run.items() if key not in {"trace", "media", "price", "cost_usd", "cost_range_usd"}}
    write_json(output / "evaluations" / f"{run_slug}.json", evaluation)
    return run


# Public wording per failure category; error strings stay private because they can name access routes.
CATEGORY_TEXT = {"QUOTA": "provider usage limit or account funds exhausted", "CONTENT_FILTER": "blocked by the provider content filter",
                 "AUTH": "authentication failure", "INFRA": "infrastructure failure", "TRANSPORT": "transport failure",
                 "PROTOCOL": "protocol failure", "EVAL": "evaluation failure"}
# The frozen runner ends a model's sequence on these categories, leaving later slots reserved.
STOPPING_CATEGORIES = {"QUOTA", "AUTH", "CONTENT_FILTER"}


def pending_reason(group: dict, rows: dict) -> str:
    """Why a model has no eligible first success: each attempted slot's outcome, then the unstarted slots."""
    slots = sorted((rows[attempt_id] for attempt_id in group["attempt_ids"] if rows[attempt_id]["predeclared"]),
                   key=lambda row: row["repetition"])
    parts = []
    for row in slots:
        if row["attempted"]:
            category = row["failure_category"]
            detail = CATEGORY_TEXT.get(category, "no eligible evaluation" if not category else category)
            parts.append(f"attempt {row['repetition']} {row['status']} ({detail})")
    unstarted = [str(row["repetition"]) for row in slots if not row["attempted"]]
    if unstarted:
        stopped = any(row["attempted"] and row["failure_category"] in STOPPING_CATEGORIES for row in slots)
        parts.append(f"attempt{'s' if len(unstarted) > 1 else ''} {', '.join(unstarted)} never started"
                     + ("; the sequence stops on this failure category" if stopped else ""))
    return "; ".join(parts) or "no attempt recorded"


def addition_reason(attempt: dict) -> str:
    """Why a model added in the rerun queue has no ranked attempt 1, from its rerun chain."""
    failed = attempt if attempt["attempted"] and attempt["status"] != "RUNNING" else next(
        (link for link in reversed(attempt["superseded"]) if link["attempted"]), None)
    cause = f"{failed['status']} ({CATEGORY_TEXT.get(failed['failure_category'], failed['failure_category'] or 'no eligible evaluation')})" if failed else None
    if attempt["status"] == "RUNNING":
        state = "attempt 1 is running in the rerun queue" + (f" after {cause}" if cause else "")
    elif attempt["queue_pending"]:
        state = f"attempt 1 awaits a rerun after {cause}" if cause else "attempt 1 has not started in the rerun queue yet"
    elif failed is attempt:
        reruns = len(attempt["superseded"])
        state = f"attempt 1 {cause}" + (f" after {reruns} rerun{'s' if reruns > 1 else ''}" if reruns else "")
    else:
        state = "attempt 1 never started"
    return f"added to the roster after requalification; {state}"


def repetition_group(group: dict, rows: dict, slugs: dict, prices: dict, roster_addition: bool = False) -> dict:
    """One model's predetermined repetitions; only eligible ones carry a playable slug. No aggregate is exported.

    In a rerun queue each ordinal's sample is the end of its chain; the attempts it superseded stay listed without media.
    """
    name = price_id(group["model"])

    def link(row: dict) -> dict:
        return {"status": row["status"], "outcome": row["outcome"], "failure_category": row["failure_category"],
                "attempted": row["attempted"], "source_campaign_id": row["source_campaign_id"],
                "source_campaign_sha256": row["source_campaign_sha256"]}

    attempts = []
    for repetition in group["repetitions"]:
        row = rows[(repetition["source_campaign_id"], repetition["attempt_id"])]
        attempts.append({"ordinal": repetition["repetition"], "status": row["status"], "outcome": repetition["outcome"],
                         "eligible": repetition["eligible"], "attempted": row["attempted"], "failure_category": repetition["failure_category"],
                         "model_failure": repetition["model_failure"], "score": repetition["craft"],
                         "slug": slugs.get((repetition["source_campaign_id"], repetition["attempt_id"])),
                         "source_campaign_id": repetition["source_campaign_id"],
                         "source_campaign_sha256": row["source_campaign_sha256"],
                         "queue_pending": bool(repetition.get("queue_pending")),
                         "superseded": [link(rows[(item["source_campaign_id"], item["attempt_id"])])
                                        for item in repetition.get("superseded_attempts") or []]})
    # A slot the frozen runner never started after a stopping failure in its own campaign names that category.
    # Each ordinal's origin (the first link of its chain) is the slot its campaign's runner scheduled.
    origins = [(attempt["superseded"] or [attempt])[0] for attempt in attempts]
    for attempt in attempts:
        for item in attempt["superseded"] + [attempt]:
            stops = [origin["failure_category"] for earlier, origin in zip(attempts, origins) if earlier["ordinal"] < attempt["ordinal"]
                     and origin["attempted"] and origin["source_campaign_id"] == item["source_campaign_id"]
                     and origin["failure_category"] in STOPPING_CATEGORIES]
            item["stopped_by"] = stops[-1] if not item["attempted"] and stops else None
    outside = []
    for attempt in group["outside_condition_attempts"]:
        row = rows[(attempt["source_campaign_id"], attempt["attempt_id"])]
        outside.append({"ordinal": attempt["repetition"], "status": row["status"], "failure_category": attempt["failure_category"],
                        "attempted": row["attempted"], "retry": attempt["retry_of"] is not None,
                        "source_campaign_id": attempt["source_campaign_id"], "source_campaign_sha256": row["source_campaign_sha256"]})
    return {"model_key": name.rsplit("/", 1)[-1], "name": name,
            "maker": public_maker(name, prices.get(name, {})), "tier": group["tier"], "cohort": group["cohort"],
            "condition_fingerprint": group["condition_fingerprint"], "declared": group["declared_repetitions"],
            "eligible": group["eligible_repetitions"], "pending": len(group["pending_repetitions"]),
            "state": group["state"], "roster_addition": roster_addition, "attempts": attempts, "outside_condition": outside}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, help="Frozen campaign lock (default: <campaign-root>/campaign.lock.json)")
    parser.add_argument("--linked", nargs=2, action="append", type=Path, default=[], metavar=("ROOT", "COHORT"),
                        help="Repetitions only: root and frozen lock of a campaign the companion declares repetitions in, "
                             "or the rerun queue takes origins from")
    parser.add_argument("--output", type=Path, required=True, help="New dedicated public-only staging directory")
    parser.add_argument("--scope", choices=("main", "pilot", "continuation", "repetitions"), default="main")
    parser.add_argument("--prices", type=Path, help="Local JSON table of maker list prices; omitted prices remain unknown")
    args = parser.parse_args()
    if args.linked and args.scope != "repetitions":
        parser.error("--linked applies only to --scope repetitions")
    source, output = args.campaign_root.resolve(), args.output.resolve()
    for root in [source] + [pair[0].resolve() for pair in args.linked]:
        if output == root or output.is_relative_to(root) or root.is_relative_to(output):
            raise ValueError("Public staging must be separate from the original campaign")
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(source, args.cohort or source / "campaign.lock.json", [tuple(pair) for pair in args.linked])
    if (report["attempt_selection"] in (INDEPENDENT_SELECTION, QUEUE_SELECTION)) != (args.scope == "repetitions"):
        raise ValueError("--scope repetitions is required for, and only for, an independent-repetitions or rerun-queue campaign")
    metadata_captured = datetime.now(timezone.utc).isoformat()
    prices = {p["id"]: p for p in json.loads(args.prices.read_text())["models"]} if args.prices else {}
    runs, roster = [], []
    if args.scope == "repetitions":
        # Attempt IDs repeat across linked campaigns (main rep-2 is outside the condition, the companion's is a sample).
        rows = {(row["source_campaign_id"], row["attempt_id"]): row for row in report["rows"]}
        if len(rows) != len(report["rows"]):
            raise ValueError("Repetition rows need unique campaign and attempt identities")
        slugs, groups = {}, []
        for group in report["groups"]:
            # A rerun-queue model with no origin in any linked campaign is new to the cohort's roster; its attempt 1 is ranked.
            addition = report["attempt_selection"] == QUEUE_SELECTION and all(
                (repetition["superseded_attempts"] or [repetition])[0]["source_campaign_id"] == report["campaign_id"]
                for repetition in group["repetitions"])
            for repetition in group["repetitions"]:
                key = (repetition["source_campaign_id"], repetition["attempt_id"])
                row = rows[key]
                if row["role"] != "repetition":
                    raise ValueError(f"{repetition['attempt_id']}: reported repetition is outside its condition")
                if row["eligible"]:
                    runs.append(public_run(row, group, Path(row["source_root"]) / row["run_dir"], output, report, args.scope, prices, addition))
                    slugs[key] = runs[-1]["slug"]
                    print(f"Verified {len(runs)}: {runs[-1]['name']}", flush=True)
            groups.append(repetition_group(group, rows, slugs, prices, addition))
            first = groups[-1]["attempts"][0]
            roster.append({"name": price_id(group["model"]), "scope": args.scope, "state": group["state"],
                           "attempts": group["attempted_count"], "selected_attempt": None, "policy_errors": len(group["policy_errors"]),
                           **({"roster_addition": True, **({} if first["eligible"] else {"reason": addition_reason(first)})} if addition else {})})
        extra = {"attempt_selection": report["attempt_selection"], "sample_note": report["sample_note"],
                 "declared_counts": report["declared_counts"],
                 "linked_campaigns": [{"campaign_id": item["campaign_id"], "campaign_sha256": item["config_sha256"],
                                       "repetitions": item.get("repetitions")} for item in report["linked_campaigns"]],
                 "repetition_groups": groups}
    else:
        rows = {row["attempt_id"]: row for row in report["rows"]}
        for group in report["groups"]:
            roster.append({"name": price_id(group["model"]), "scope": args.scope, "state": group["state"],
                           "attempts": group["attempted_count"], "selected_attempt": group["selected_attempt_ordinal"],
                           "policy_errors": len(group["policy_errors"]),
                           **({} if group["selected_attempt_id"] else {"reason": pending_reason(group, rows)})})
            if group["selected_attempt_id"]:
                row = rows[group["selected_attempt_id"]]
                runs.append(public_run(row, group, source / row["run_dir"], output, report, args.scope, prices))
                print(f"Verified {len(runs)}: {runs[-1]['name']}", flush=True)
        extra = {}
    write_json(output / "snapshot.json", {"schema": "keygen-public-snapshot-1",
               "generated": datetime.now(timezone.utc).isoformat(), "scope": args.scope,
               "metadata_captured": metadata_captured,
               "campaign_id": report["campaign_id"], "campaign_sha256": report["campaign_sha256"],
               "cohort": report["cohort"], "counts": report["counts"], "roster": roster, "runs": runs, **extra})
    # Staging only ever holds verified public inputs, but it is not part of publication.
    shutil.rmtree(output / ".verified", ignore_errors=True)
    print(f"Public snapshot: {len(runs)} {'eligible repetition' if args.scope == 'repetitions' else 'selected ' + args.scope} results", flush=True)


if __name__ == "__main__":
    main()
