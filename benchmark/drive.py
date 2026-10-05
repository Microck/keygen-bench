#!/usr/bin/env python3
"""Compile, run and summarize one frozen native campaign without changing authentication."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import campaign


def plan(selection: Path, inventory: Path, out: Path, tier_spec: Path) -> Path:
    path = out / "campaign.json"
    campaign.compile_campaign(inventory, selection, path, tier_spec)
    return path


def run(selection: Path, inventory: Path, out: Path, tier_spec: Path, workers: int | None = None) -> int:
    frozen = plan(selection, inventory, out, tier_spec)
    config = campaign.load(frozen)
    count = config["concurrency"]["workers"] if workers is None else workers
    if count != config["concurrency"]["workers"]:
        raise ValueError("Driver workers must match the frozen campaign")
    with (out / "controller.log").open("ab") as log:
        result = subprocess.run([sys.executable, "-I", str(HERE / "run.py"), "run",
                                "--campaign", str(frozen), "--out", str(out), "--workers", str(count)],
                                stdout=log, stderr=subprocess.STDOUT)
    summary(out)
    return result.returncode


def summary(out: Path) -> list[dict]:
    manifest = out / "campaign.lock.json"
    if manifest.exists():
        from report import build_report
        from run import write_json
        report = build_report(out, manifest)
        write_json(out / "results.json", report)
        print(f"{len(report['rows'])} cohort slots/attempts summarized in {out / 'results.json'}")
        return report["rows"]
    rows = []
    for status_path in sorted(out.rglob("status.json")):
        if ("isolated-host-home" in status_path.parts or "legacy" in status_path.parts
                or any(part.startswith(".reservation-") for part in status_path.relative_to(out).parts)):
            continue
        try:
            status = json.loads(status_path.read_text())
        except json.JSONDecodeError:
            rows.append({"attempt_id": str(status_path.parent.relative_to(out)), "status": "UNREADABLE_INTERRUPTED",
                         "model": None, "eligible": False, "failure_category": "INFRA", "usage_unknown": True})
            continue
        model = status.get("model") or {}
        totals = status.get("totals") or {}
        audio = status.get("audio") or {}
        profile_path = status_path.parent / "profile.json"
        try:
            profile = json.loads(profile_path.read_text()) if profile_path.exists() else None
        except (OSError, ValueError):
            profile = None
        from run import attempt_succeeded
        selected = attempt_succeeded(status, profile,
                                     finalization_error=(status_path.parent / "finalization-error.json").exists())
        rows.append({"attempt_id": status.get("attempt_id", status_path.parent.name), "repetition": status.get("repetition"),
                     "retry_of": status.get("retry_of"), "model": model.get("model"), "provider": model.get("provider"),
                     "status": status.get("status", "UNKNOWN"), "eligible": selected,
                     "selected_attempt_id": status.get("selected_attempt_id"),
                     "failure_category": status.get("failure_category"), "model_failure": status.get("model_failure"),
                     "duration_s": audio.get("duration_seconds"), "requests": totals.get("requests"),
                     "prompt_tokens": totals.get("prompt_tokens"), "completion_tokens": totals.get("completion_tokens"),
                     "reasoning_tokens": totals.get("reasoning_tokens"),
                     "usage_unknown": None if status.get("status") == "SKIPPED_AFTER_SUCCESS" else bool(
                         totals.get("usage_unknown") or totals.get("in_flight_usage_unknown")
                         or status.get("status") in {"RESERVED", "RUNNING", "INTERRUPTED", "UNKNOWN"}),
                     "wall_s": status.get("wall_seconds"), "error": status.get("error")})
    from run import write_json
    write_json(out / "results.json", {"attempt_selection": campaign.POLICIES["attempt_selection"], "max_attempts": 3,
                                     "rows": rows,
                                     "note": "Each model stops after its first eligible success or three attempts. Interrupted and unknown outcomes remain visible; explicit retries do not replace originals."})
    print(f"{len(rows)} attempts summarized in {out / 'results.json'}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "run", "summary"])
    parser.add_argument("--selection", type=Path, default=HERE / "config/campaign.example.json")
    parser.add_argument("--inventory", type=Path, default=HERE.parent / "MODEL-TEST-PLAN.oauth-first.json")
    parser.add_argument("--tier-spec", type=Path, help="required for plan/run: per-model tier spec")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--workers", type=int)
    args = parser.parse_args()
    if not args.out.is_absolute():
        raise ValueError("Artifact root must be explicitly absolute")
    from run import artifact_root
    out = artifact_root(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.command in {"plan", "run"} and args.tier_spec is None:
        raise ValueError("Compiling a campaign requires --tier-spec; there is no default tier")
    if args.command == "plan":
        print(plan(args.selection.resolve(), args.inventory.resolve(), out, args.tier_spec.resolve()))
    elif args.command == "run":
        raise SystemExit(run(args.selection.resolve(), args.inventory.resolve(), out, args.tier_spec.resolve(), args.workers))
    else:
        summary(out)


if __name__ == "__main__":
    main()
