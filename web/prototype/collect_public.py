"""Export a frozen native campaign to public-only website data and verified media.

Run on its trusted controller. Archives are read into temporary staging, never
restored into original attempts. Only XM, canonical WAV, derived MP3, compact row
traces and an allowlisted evaluation summary leave the controller.
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
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.artifacts import ArtifactStore
from benchmark.report import build_report, finite_json
from build import FLAG_RULES, compact_trace, estimate_cost, price_id, public_maker, public_price, slug, worst_transition


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(finite_json(value), ensure_ascii=True, allow_nan=False,
                               separators=(",", ":")) + "\n")
    ArtifactStore.check_secrets(path)


def verified_media(directory: Path, profile: dict, output: Path) -> dict:
    """Copy only pinned presentation inputs, checking the complete archive if needed."""
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
    missing = []
    for name, target in wanted.items():
        if target.is_file() and sha256(target) == expected[name]:
            continue
        original = directory / name
        if original.is_file() and not original.is_symlink() and sha256(original) == expected[name]:
            shutil.copyfile(original, target)
        else:
            missing.append(name)
    archive_path = directory / "archive.json"
    metadata = json.loads(archive_path.read_text()) if archive_path.is_file() else None
    if missing:
        if not metadata or metadata.get("verified") is not True:
            raise ValueError("Selected result has no verified local media or archive")
        store = ArtifactStore(metadata["storage"])
        store._validate_metadata(metadata)
        if any((metadata["files"].get(name) or {}).get("sha256") != expected[name] for name in wanted):
            raise ValueError("Archive media differs from the selected evaluation inputs")
        with tempfile.TemporaryDirectory(prefix="keygen-public-", dir=output.parent) as tmp:
            bundle = Path(tmp) / "attempt.tar.gz"
            if store.backend == "local":
                shutil.copyfile(metadata["remote"], bundle)
            else:
                result = subprocess.run([store.binary, "copyto", metadata["remote"], str(bundle),
                                         "--immutable"], capture_output=True, timeout=1200)
                if result.returncode:
                    raise RuntimeError(f"Archive download failed with exit status {result.returncode}")
            if bundle.stat().st_size != metadata["bytes"] or sha256(bundle) != metadata["sha256"]:
                raise ValueError("Downloaded archive checksum mismatch")
            seen = set()
            with tarfile.open(bundle, "r:gz") as archive:
                for member in archive:
                    if member.name in seen or not member.isfile():
                        raise ValueError("Unexpected archive member type or duplicate")
                    seen.add(member.name)
                    stream = archive.extractfile(member)
                    if member.name == "manifest.json":
                        if member.size > 8 * 1024**2 or json.load(stream) != metadata["files"]:
                            raise ValueError("Archive manifest mismatch")
                        continue
                    record = metadata["files"].get(member.name)
                    if record is None or member.size != record["bytes"]:
                        raise ValueError("Archive member identity mismatch")
                    digest = hashlib.sha256()
                    target = Path(tmp) / Path(member.name).name if member.name in missing else None
                    handle = target.open("wb") if target else None
                    try:
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(block)
                            if handle:
                                handle.write(block)
                    finally:
                        if handle:
                            handle.close()
                    if digest.hexdigest() != record["sha256"]:
                        raise ValueError("Archive member checksum mismatch")
                if seen != set(metadata["files"]) | {"manifest.json"}:
                    raise ValueError("Archive is missing pinned members")
            for name in missing:
                shutil.copyfile(Path(tmp) / Path(name).name, wanted[name])
    for name, target in wanted.items():
        if sha256(target) != expected[name]:
            raise ValueError("Presentation input checksum mismatch")
    return {"input_sha256": expected,
            "archive_sha256": metadata.get("sha256") if metadata else None,
            "archive_generation": metadata.get("generation") if metadata else None,
            "archive_verified": bool(metadata and metadata.get("verified") is True)}


def public_run(row: dict, group: dict, directory: Path, output: Path, campaign: dict,
               scope: str, prices: dict) -> dict:
    profile = row["profile"]
    name = price_id(row["model"])
    # Cohorts are separate experiments; a max-tier result never shares a slug or name with an earlier cohort's row.
    max_tier = row["cohort"]["condition"] == "highest-declared-tier"
    repetition = scope == "repetitions"
    ordinal = row["repetition"]
    run_slug = slug(name) + ("-max-tier" if max_tier else "") + (f"-a{ordinal}" if repetition else {"pilot": "-pilot", "recovery": "-recovered", "continuation": "-continued"}.get(scope, ""))
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
        "name": name + ((f" (max-tier, attempt {ordinal})" if max_tier else f" (attempt {ordinal})") if repetition else
                        (" (max-tier)" if max_tier else "") + {"pilot": " (musical pilot)", "recovery": " (archive-only recovery)", "continuation": " (native continuation)"}.get(scope, "")),
        "maker": maker, "exhibition": scope == "pilot", "tier": row["tier"], "cohort": row["cohort"],
        "status": row["recorded_status"] if row["post_evaluation_finalization_error"] else row["status"], "error": "", "score": row["craft"],
        "parts": {key: craft["parts"][key] for key in ("tonal_organization", "development", "dynamics")},
        "weights": {key: craft["weights"][key] for key in ("tonal_organization", "development", "dynamics")},
        "factors": {key: craft["factors"][key] for key in ("signal_integrity", "noise_integrity", "loop_continuity", "duration_sufficiency")},
        "uncapped": craft["uncapped"], "content": craft["content_score"], "caps": craft.get("caps") or [],
        "flags": [{"id": flag, "rule": FLAG_RULES.get(flag, "")} for flag in profile.get("flags") or []],
        "loop": {"quality": loop.get("quality_score"), "worst": worst_transition(loop),
                 "first_pass_audible_seconds": loop.get("first_pass_audible_seconds")},
        "tonal": {key: (audio.get("spectral") or {}).get(key) for key in ("tonal_evidence_fraction", "diatonic_concentration", "effective_pitch_classes", "sustained_noise_fraction")},
        "development": {key: structure.get(key) for key in ("arrangement_score", "sequence_coverage", "motif_recurrence", "controlled_development")},
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
                       "selected_by": ("independent predetermined repetition; every repetition is reported, none is selected" if repetition else
                                       "first eligible success among up to three sequential predetermined attempts"),
                       "score_version": row["score_version"], "evaluation_fingerprint": row["evaluation_fingerprint"],
                       "profile_sha256": sha256(directory / "profile.json"), **verification,
                       "public_media_sha256": {key: sha256(media / f"{run_slug}.{ext}") for key, ext in (("xm", "xm"), ("wav", "wav"), ("mp3", "mp3"))}},
    }
    if scope == "recovery":
        run["provenance"]["recovery_note"] = "Archive-only recovered historical attempt. Staged status matches the selected profile's pinned status hash. The original finalization-error history remains unchanged. No new musical inference."
    if scope == "continuation":
        run["provenance"]["continuation_note"] = "A new frozen native continuation cohort with its own configuration and evaluator fingerprints. Original campaigns, routes and historical outcomes remain unchanged."
    if repetition:
        run["provenance"].update(source_campaign_id=row["source_campaign_id"], repetition_campaign_sha256=campaign["campaign_sha256"],
                                 condition_fingerprint=row["condition_fingerprint"])
    if row["post_evaluation_finalization_error"]:
        failure = row["post_evaluation_finalization_error"]
        cause = failure.get("error") if isinstance(failure, dict) else None
        archive = "" if (directory / "archive.json").is_file() else " No archive receipt was recorded for this attempt."
        run["provenance"]["status_note"] = (f"Recorded status {row['recorded_status']}{f' ({cause})' if cause else ''} after its evaluation "
                                            "completed. The profile pins the evaluated status hash, so the eligible evaluation and "
                                            f"its score stand; no rescoring or new inference.{archive}")
    run["module"].update({"patterns": structure.get("distinct_patterns_in_order"), "instruments": structure.get("instruments_used"), "samples": structure.get("samples")})
    evaluation = {key: value for key, value in run.items() if key not in {"trace", "media", "price", "cost_usd"}}
    write_json(output / "evaluations" / f"{run_slug}.json", evaluation)
    return run


def public_status(row: dict) -> str:
    return row["recorded_status"] if row["post_evaluation_finalization_error"] else row["status"]


def repetition_group(group: dict, rows: dict, slugs: dict, prices: dict) -> dict:
    """One model's predetermined repetitions; only eligible ones carry a playable slug."""
    name = price_id(group["model"])
    attempts = []
    for repetition in group["repetitions"]:
        row = rows[(repetition["source_campaign_id"], repetition["attempt_id"])]
        attempts.append({"ordinal": repetition["repetition"], "status": public_status(row), "outcome": repetition["outcome"],
                         "eligible": repetition["eligible"], "failure_category": repetition["failure_category"],
                         "model_failure": repetition["model_failure"], "score": repetition["craft"],
                         "slug": slugs.get((repetition["source_campaign_id"], repetition["attempt_id"])),
                         "source_campaign_id": repetition["source_campaign_id"],
                         "source_campaign_sha256": row["source_campaign_sha256"]})
    outside = []
    for attempt in group["outside_condition_attempts"]:
        row = rows[(attempt["source_campaign_id"], attempt["attempt_id"])]
        outside.append({"ordinal": attempt["repetition"], "status": public_status(row), "failure_category": attempt["failure_category"],
                        "attempted": row["attempted"], "operator_cancelled": attempt["operator_cancellation"] is not None, "retry": attempt["retry_of"] is not None,
                        "source_campaign_id": attempt["source_campaign_id"], "source_campaign_sha256": row["source_campaign_sha256"]})
    max_tier = group["cohort"]["condition"] == "highest-declared-tier"
    return {"model_key": name.rsplit("/", 1)[-1], "name": name + (" (max-tier)" if max_tier else ""),
            "maker": public_maker(name, prices.get(name, {})), "tier": group["tier"], "cohort": group["cohort"],
            "condition_fingerprint": group["condition_fingerprint"], "declared": group["declared_repetitions"],
            "eligible": group["eligible_repetitions"], "pending": len(group["pending_repetitions"]),
            "median": group["median_craft"], "min": group["min_craft"], "max": group["max_craft"], "range": group["craft_range"],
            "state": group["state"], "attempts": attempts, "outside_condition": outside}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--cohort", type=Path, help="Explicit original frozen lock for a separate archive-recovery staging root, "
                        "or the companion campaign's lock for --scope repetitions (default: <campaign-root>/campaign.lock.json)")
    parser.add_argument("--linked", nargs=2, action="append", type=Path, default=[], metavar=("ROOT", "COHORT"),
                        help="Repetitions only: root and frozen lock of a campaign the companion declares repetitions in")
    parser.add_argument("--output", type=Path, required=True, help="New dedicated public-only staging directory")
    parser.add_argument("--scope", choices=("main", "pilot", "recovery", "continuation", "repetitions"), default="main")
    args = parser.parse_args()
    if args.scope == "recovery" and args.cohort is None:
        parser.error("Recovery publication requires the original frozen --cohort lock")
    if args.linked and args.scope != "repetitions":
        parser.error("--linked applies only to --scope repetitions")
    source, output = args.campaign_root.resolve(), args.output.resolve()
    for root in [source] + [pair[0].resolve() for pair in args.linked]:
        if output == root or output.is_relative_to(root) or root.is_relative_to(output):
            raise ValueError("Public staging must be separate from the original campaign")
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(source, args.cohort or source / "campaign.lock.json", [tuple(pair) for pair in args.linked])
    if (report["attempt_selection"] == "independent_repetitions") != (args.scope == "repetitions"):
        raise ValueError("--scope repetitions is required for, and only for, an independent-repetitions campaign")
    metadata_captured = datetime.now(timezone.utc).isoformat()
    prices = {p["id"]: p for p in json.loads((HERE / "data-src/prices.json").read_text())["models"]}
    runs, roster = [], []
    if args.scope == "repetitions":
        # Attempt IDs repeat across linked campaigns (main rep-2 is outside the condition, the companion's is a sample).
        rows = {(row["source_campaign_id"], row["attempt_id"]): row for row in report["rows"]}
        if len(rows) != len(report["rows"]):
            raise ValueError("Repetition rows need unique campaign and attempt identities")
        slugs, groups = {}, []
        for group in report["groups"]:
            roster.append({"name": price_id(group["model"]), "scope": args.scope, "state": group["state"],
                           "attempts": group["attempted_count"], "selected_attempt": None, "policy_errors": len(group["policy_errors"])})
            for repetition in group["repetitions"]:
                key = (repetition["source_campaign_id"], repetition["attempt_id"])
                row = rows[key]
                if row["role"] != "repetition":
                    raise ValueError(f"{repetition['attempt_id']}: reported repetition is outside its condition")
                if row["eligible"]:
                    runs.append(public_run(row, group, Path(row["source_root"]) / row["run_dir"], output, report, args.scope, prices))
                    slugs[key] = runs[-1]["slug"]
                    print(f"Verified {len(runs)}: {runs[-1]['name']}", flush=True)
            groups.append(repetition_group(group, rows, slugs, prices))
        extra = {"attempt_selection": report["attempt_selection"], "sample_note": report["sample_note"],
                 "declared_counts": report["declared_counts"],
                 "linked_campaigns": [{"campaign_id": item["campaign_id"], "campaign_sha256": item["config_sha256"],
                                       "repetitions": item["repetitions"]} for item in report["linked_campaigns"]],
                 "repetition_groups": groups}
    else:
        rows = {row["attempt_id"]: row for row in report["rows"]}
        for group in report["groups"]:
            roster.append({"name": price_id(group["model"]), "scope": args.scope, "state": group["state"],
                           "attempts": group["attempted_count"], "selected_attempt": group["selected_attempt_ordinal"],
                           "policy_errors": len(group["policy_errors"])})
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
