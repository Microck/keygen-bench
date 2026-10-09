#!/usr/bin/env python3
"""Recompute development without mutating runs or re-rendering unchanged audio.

    python benchmark/rescore.py runs --root runs --output /tmp/craft-v8-runs.json
    python benchmark/rescore.py references --modules /tmp/reference-xms --output /tmp/craft-v8-reference.json

Reference files are named <git_blob_sha>.xm from the pinned duration manifest.
Outputs are review evidence, not replacement profile.json files or publications.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import subprocess
import tempfile

import numpy as np

import score
from score_structure import DEVELOPMENT_METHOD, structure_metrics

ROOT = Path(__file__).resolve().parent.parent
UNCHANGED_MEASUREMENTS = ("score_audio.py", "score_mix.py", "score_loop.py", "score_playback.py")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def provenance():
    return {"score_version": score.SCORE_VERSION, "development_method": DEVELOPMENT_METHOD,
            "scorer_sha256": {name: digest(ROOT / "benchmark" / name)
                              for name in ("score.py", "score_structure.py", "rescore.py")},
            "python": platform.python_version(), "numpy": np.__version__,
            "scope": "Recomputed XM development and total; unchanged audio/mix/loop measurements retained with source hashes.",
            "listener_validated": False}


def rescore_attempt(directory):
    profile_path = directory / "profile.json"
    record = {"model": directory.parent.name, "attempt": int(directory.name.split("-")[-1])}
    if not profile_path.exists():
        status = json.loads((directory / "status.json").read_text())
        return {**record, "status": status["status"], "eligible": False,
                "old_score": None, "new_score": None, "reason": "No completed source evaluation"}
    profile = json.loads(profile_path.read_text())
    record.update(source_profile_sha256=digest(profile_path), status=profile["status"],
                  eligible=bool(profile.get("eligible")), source_version=profile["score_version"])
    if not record["eligible"]:
        return {**record, "old_score": None, "new_score": None,
                "reason": (profile.get("evaluation_error") or {}).get("category", profile.get("run_failure_category"))}
    # Reusing facts is intentional, not a fallback. Reject a different measurement
    # implementation or artifact instead of silently mixing evaluator generations.
    inputs = profile["inputs"]
    if any(inputs["scorer"].get(name) != digest(ROOT / "benchmark" / name) for name in UNCHANGED_MEASUREMENTS):
        raise ValueError(f"{directory.parent.name}/{directory.name}: audio measurement implementation differs; run a full evaluation")
    xm_path = directory / "submission/tune.xm"
    xm_hash = digest(xm_path)
    if xm_hash != inputs["artifacts"]["submission/tune.xm"]:
        raise ValueError(f"{directory.parent.name}/{directory.name}: XM does not match the source profile")
    wav_path = directory / "canonical/canonical.wav"
    if wav_path.exists():
        wav_hash = digest(wav_path)
    else:
        with tempfile.TemporaryDirectory(prefix="keygen-rescore-") as temporary:
            restored = Path(temporary) / "canonical.wav"
            subprocess.run(["flac", "--decode", "--silent", "--keep-foreign-metadata",
                            "--output-name=" + str(restored), str(wav_path.with_suffix(".wav.flac"))],
                           check=True, capture_output=True, timeout=120)
            wav_hash = digest(restored)
    if wav_hash != inputs["artifacts"]["canonical/canonical.wav"]:
        raise ValueError(f"{directory.parent.name}/{directory.name}: canonical WAV does not match the source profile")
    # Check that all retained inputs still reproduce the source total. This also
    # rejects a change to any other content weight, factor, cap or rounding rule.
    old = score.craft_score(profile["structure"], profile["audio"], profile["loop"])
    for field in ("craft_score", "parts", "factors", "caps", "content_score", "uncapped"):
        if old[field] != profile["craft"][field]:
            raise ValueError(f"{directory.parent.name}/{directory.name}: retained {field} no longer reproduces the source score")
    xm = score.parse_xm(xm_path.read_bytes())
    structure = structure_metrics(xm, set(profile["mix"]["audible_channels"]))
    if not structure["sequence_complete"]:
        raise ValueError(f"{directory.parent.name}/{directory.name}: incomplete sequence")
    new = score.craft_score(structure, profile["audio"], profile["loop"])
    return {**record, "xm_sha256": xm_hash,
            "canonical_wav_sha256": inputs["artifacts"]["canonical/canonical.wav"],
            "retained_measurement_sha256": {name: inputs["scorer"][name] for name in UNCHANGED_MEASUREMENTS},
            "old_score": old["craft_score"], "new_score": new["craft_score"],
            "old_parts": old["parts"], "new_parts": new["parts"], "factors": new["factors"],
            "caps": new["caps"], "development_scales": structure["development_scales"]}


def ranked_runs(root):
    directories = sorted(root.glob("*/attempt-*"))
    if not directories:
        raise ValueError("No ranked attempt directories found; supply runs/<model>/attempt-N inputs")
    records = [rescore_attempt(directory) for directory in directories if directory.is_dir()]
    models = []
    for model in sorted({r["model"] for r in records}):
        attempts = [r for r in records if r["model"] == model]
        eligible = [r for r in attempts if r["eligible"]]
        old = max(eligible, key=lambda r: (r["old_score"], -r["attempt"]), default=None)
        new = max(eligible, key=lambda r: (r["new_score"], -r["attempt"]), default=None)
        models.append({"model": model, "slots": len(attempts), "scored": len(eligible),
                       "old_best": old["old_score"] if old else None, "new_best": new["new_score"] if new else None,
                       "old_best_attempt": old["attempt"] if old else None, "new_best_attempt": new["attempt"] if new else None})
    for version in ("old", "new"):
        ranked = sorted((m for m in models if m[f"{version}_best"] is not None),
                        key=lambda m: (-m[f"{version}_best"], m["model"]))
        for rank, model in enumerate(ranked, 1):
            model[f"{version}_rank"] = rank
    return {"schema": "keygen-development-rescore-1", **provenance(),
            "selection": "Every attempt-N directory; other/ excluded, original slots unchanged. Ties use model name for display only.",
            "counts": {"models": len(models), "attempts": len(records),
                       "scored": sum(r["eligible"] for r in records), "unscored": sum(not r["eligible"] for r in records)},
            "models": models, "attempts": records}


def reference_scores(modules):
    duration_path = ROOT / "data/keygen-duration-reference.json"
    baseline_path = ROOT / "data/keygen-scoring-reference.json"
    manifest = json.loads(duration_path.read_text())
    baseline = {r["git_blob_sha"]: r for r in json.loads(baseline_path.read_text())["records"]}
    records = []
    for entry in manifest["records"]:
        path = modules / (entry["git_blob_sha"] + ".xm")
        if digest(path) != entry["sha256"]:
            raise ValueError(f"Reference hash mismatch: {entry['git_blob_sha']}")
        structure = structure_metrics(score.parse_xm(path.read_bytes()))
        if not structure["sequence_complete"]:
            raise ValueError(f"Reference traversal incomplete: {entry['git_blob_sha']}")
        previous = baseline[entry["git_blob_sha"]]
        records.append({"git_blob_sha": entry["git_blob_sha"], "xm_sha256": entry["sha256"],
                        "split": previous["split"], "old_development": previous["v7_parts"]["development"],
                        "new_development": round(40 * structure["arrangement_score"], 2),
                        "development_scales": structure["development_scales"]})
    summaries = {}
    for split in ("all", "calibration", "held_out", "unscored_in_v6"):
        selected = [r for r in records if split == "all" or r["split"] == split]
        summaries[split] = {"count": len(selected)}
        for version in ("old", "new"):
            values = np.array([r[f"{version}_development"] for r in selected])
            summaries[split][version] = {key: round(float(v), 3) for key, v in zip(
                ("min", "median", "p75", "p90", "max"), np.quantile(values, (0, .5, .75, .9, 1)))}
    return {"schema": "keygen-development-reference-1", **provenance(),
            "source_manifest_sha256": digest(duration_path), "baseline_sha256": digest(baseline_path),
            "scope": "Development only; pinned XM bytes, all sequenced channels. No new audio or aesthetic evaluation.",
            "limitations": ["Convenience corpus, not listener judgments.",
                            "Archived v7 values used rendered audibility filtering; v8 reference diagnostics include all sequenced channels.",
                            "No constants were fitted to the reference distribution or model rankings."],
            "summary": summaries, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="kind", required=True)
    runs = sub.add_parser("runs", help="Rescore every ranked attempt using verified retained measurements")
    runs.add_argument("--root", type=Path, required=True)
    references = sub.add_parser("references", help="Compare development on the pinned reference XM corpus")
    references.add_argument("--modules", type=Path, required=True)
    for command in (runs, references):
        command.add_argument("--output", type=Path, required=True, help="New JSON file; existing paths are never overwritten")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path to preserve review evidence")
    try:
        payload = ranked_runs(args.root) if args.kind == "runs" else reference_scores(args.modules)
        with args.output.open("x") as stream:
            json.dump(payload, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"Rescore failed: {exc}", file=sys.stderr)
        return 1
    counts = payload["counts"] if args.kind == "runs" else {"references": len(payload["records"])}
    print(json.dumps({"output": str(args.output), "score_version": score.SCORE_VERSION, "counts": counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
