#!/usr/bin/env python3
"""Recompute spectral and structural evidence without mutating historical runs.

    python benchmark/rescore.py runs --root runs --output /tmp/craft-v9-runs.json
    python benchmark/rescore.py references --modules /tmp/reference-xms --output /tmp/craft-v9-reference.json

Reference files are named <git_blob_sha>.xm from the pinned duration manifest.
Reference PCM is rendered locally; ranked-run PCM is verified and reused.
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
from score_audio import spectral_metrics

ROOT = Path(__file__).resolve().parent.parent
UNCHANGED_MEASUREMENTS = ("score_mix.py", "score_loop.py", "score_playback.py")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def provenance():
    return {"score_version": score.SCORE_VERSION, "development_method": DEVELOPMENT_METHOD,
            "scorer_sha256": {name: digest(ROOT / "benchmark" / name)
                              for name in ("score.py", "score_audio.py", "score_structure.py", "rescore.py")},
            "python": platform.python_version(), "numpy": np.__version__,
            "scope": "Recomputed spectral/structural evidence and total; retained signal, dynamics, mix and loop measurements with source hashes.",
            "listener_validated": False}


def spectral_wav(path, end_frame=None):
    """Memory-map PCM so the spectral worker keeps its bounded window storage."""
    from scipy.io import wavfile
    rate, pcm = wavfile.read(path, mmap=True)
    try:
        if pcm.dtype != np.dtype("int16") or pcm.ndim not in (1, 2) or (pcm.ndim == 2 and pcm.shape[1] not in (1, 2)):
            raise ValueError("Expected signed-16 mono/stereo canonical PCM")
        if end_frame is not None and not 0 < end_frame <= len(pcm):
            raise ValueError("First-pass boundary lies outside captured PCM")
        return spectral_metrics(pcm[:end_frame], rate)
    finally:
        pcm._mmap.close()


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
    with tempfile.TemporaryDirectory(prefix="keygen-rescore-") as temporary:
        measured_path = wav_path
        if not wav_path.exists():
            measured_path = Path(temporary) / "canonical.wav"
            subprocess.run(["flac", "--decode", "--silent", "--keep-foreign-metadata",
                            "--output-name=" + str(measured_path), str(wav_path.with_suffix(".wav.flac"))],
                           check=True, capture_output=True, timeout=120)
        if digest(measured_path) != inputs["artifacts"]["canonical/canonical.wav"]:
            raise ValueError(f"{directory.parent.name}/{directory.name}: canonical WAV does not match the source profile")
        spectral = spectral_wav(measured_path)
    old = profile["craft"]
    xm = score.parse_xm(xm_path.read_bytes())
    structure = structure_metrics(xm, set(profile["mix"]["audible_channels"]))
    if not structure["sequence_complete"]:
        raise ValueError(f"{directory.parent.name}/{directory.name}: incomplete sequence")
    audio = dict(profile["audio"], spectral=spectral)
    new = score.craft_score(structure, audio, profile["loop"])
    return {**record, "xm_sha256": xm_hash,
            "canonical_wav_sha256": inputs["artifacts"]["canonical/canonical.wav"],
            "retained_measurement_sha256": {name: inputs["scorer"][name] for name in UNCHANGED_MEASUREMENTS},
            "old_score": old["craft_score"], "new_score": new["craft_score"],
            "old_parts": old["parts"], "new_parts": new["parts"], "factors": new["factors"],
            "caps": new["caps"], "craft": new, "spectral": spectral,
            "arrangement_score": structure["arrangement_score"],
            "development_scales": structure["development_scales"]}


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
    return {"schema": "keygen-fairness-rescore-1", **provenance(),
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
        from score_playback import capture, renderer_identity
        from score_loop import runtime_returns
        # Use the native first return or F00 stop, not the static duration,
        # as the boundary. Both looping and finite compositions are valid.
        seconds = max(entry["first_subsong_seconds"], structure["sequence_seconds"]) + 10
        with tempfile.TemporaryDirectory(prefix="keygen-reference-") as temporary:
            captured = capture(path, Path(temporary), seconds)
            returns = runtime_returns(captured["rows"])
            boundaries = [row["frame"] for row in returns]
            boundaries.extend(row["frame"] for row in captured["rows"] if row["speed"] == 0)
            if not boundaries:
                raise ValueError(f"Reference has no captured return or stop: {entry['git_blob_sha']}")
            end_frame = min(boundaries)
            spectral = spectral_wav(Path(captured["wav_path"]), end_frame)
        records.append({"git_blob_sha": entry["git_blob_sha"], "xm_sha256": entry["sha256"],
                        "first_pass_frames": end_frame,
                        "first_pass_end": "return" if returns and returns[0]["frame"] == end_frame else "stop",
                        "split": previous["split"], "old_development": previous["v7_parts"]["development"],
                        "new_development": round(40 * structure["arrangement_score"], 2),
                        "old_tonal": previous["v7_parts"]["tonal_organization"],
                        "new_tonal": round(50 * spectral["tonal_organization"], 2),
                        "spectral": spectral, "development_scales": structure["development_scales"]})
    summaries = {}
    for split in ("all", "calibration", "held_out", "unscored_in_v6"):
        selected = [r for r in records if split == "all" or r["split"] == split]
        summaries[split] = {"count": len(selected)}
        for component in ("tonal", "development"):
            summaries[split][component] = {}
            for version in ("old", "new"):
                values = np.array([r[f"{version}_{component}"] for r in selected])
                summaries[split][component][version] = {key: round(float(v), 3) for key, v in zip(
                    ("min", "median", "p75", "p90", "max"), np.quantile(values, (0, .5, .75, .9, 1)))}
    identity = renderer_identity()
    return {"schema": "keygen-fairness-reference-1", **provenance(),
            "source_manifest_sha256": digest(duration_path), "baseline_sha256": digest(baseline_path),
            "renderer": {key: identity[key] for key in ("binary_sha256", "source_commit", "patch_sha256", "architecture")},
            "scope": "Tonal/development components only; pinned XM bytes and native first-pass PCM, all sequenced channels. No invented reference totals or aesthetic evaluation.",
            "limitations": ["Convenience corpus, not listener judgments.",
                            "Archived v7 values used rendered audibility filtering; reference structure includes all sequenced channels.",
                            "No constants were fitted to the reference distribution or model rankings."],
            "summary": summaries, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="kind", required=True)
    runs = sub.add_parser("runs", help="Recompute spectrum and development for every ranked attempt")
    runs.add_argument("--root", type=Path, required=True)
    references = sub.add_parser("references", help="Render and compare tonal/development evidence on the pinned XM corpus")
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
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Rescore failed: {exc}", file=sys.stderr)
        return 1
    counts = payload["counts"] if args.kind == "runs" else {"references": len(payload["records"])}
    print(json.dumps({"output": str(args.output), "score_version": score.SCORE_VERSION, "counts": counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
