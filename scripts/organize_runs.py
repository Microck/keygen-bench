#!/usr/bin/env python3
"""Organize a finished maintainer campaign into runs/<model>/.

    python scripts/organize_runs.py --model gpt-6.1-terra --route codex \
        --slot 1=/private/campaign/runs/MODEL-rep-1 --slot 2=... --slot 3=... \
        [--other /private/campaign/runs/MODEL-rep-2-retry-1 ...] \
        --source-prefix paris:terra-20261026/runs

This is the maintainer organizer that AGENTS.md refers to. It copies each
attempt's public projection unchanged, stores WAVs as byte-exact
`.wav.flac`, writes ATTEMPT.json and updates runs/index.json. It never
overwrites or re-slots an attempt: every target must be new. Slots are the
campaign's three predetermined ordinals, not the best attempts; failed slots
stay in their slot. Infrastructure retries and other attempts go to --other.
It makes no provider requests and does not score anything.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# The public projection of one attempt. Anything else (isolated host homes with
# private configs and credential fingerprints, visualizer videos, locks) stays private.
FILES = ("campaign.json", "spec.json", "status.json", "profile.json", "archive.json",
         "module_info.json", "module_load.json", "module_render.json",
         "trajectory.json", "transport.jsonl", "transport.json", "worker-result.json", "worker.log")
DIRS = ("submission", "canonical", "evaluations", "transport")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compress_wav(wav: Path) -> None:
    """Replace a WAV with FLAC that decodes to the identical bytes, or fail."""
    flac = wav.with_name(wav.name + ".flac")
    subprocess.run(["flac", "--silent", "--best", "--keep-foreign-metadata", "-o", str(flac), str(wav)], check=True)
    with tempfile.TemporaryDirectory() as temporary:
        decoded = Path(temporary) / "check.wav"
        subprocess.run(["flac", "-d", "--silent", "--keep-foreign-metadata", "-o", str(decoded), str(flac)], check=True)
        if sha256(decoded) != sha256(wav):
            raise ValueError(f"{wav}: FLAC does not restore the original WAV")
    wav.unlink()


def project(source: Path, target: Path, identity: dict) -> dict:
    if target.exists():
        raise ValueError(f"{target} exists; attempts are never overwritten or re-slotted")
    status = json.loads((source / "status.json").read_text())
    campaign = json.loads((source / "campaign.json").read_text())
    campaign = campaign.get("snapshot", campaign).get("campaign", campaign)
    profile = json.loads((source / "profile.json").read_text()) if (source / "profile.json").is_file() else {}
    target.mkdir(parents=True)
    for name in FILES:
        if (source / name).is_file():
            shutil.copyfile(source / name, target / name)
    for name in DIRS:
        if (source / name).is_dir():
            shutil.copytree(source / name, target / name, symlinks=False)
    for wav in sorted(target.rglob("*.wav")):
        compress_wav(wav)
    entry = {**identity, "attempt_id": status["attempt_id"], "status": status["status"],
             "failure_category": status.get("failure_category"),
             "score": (profile.get("craft") or {}).get("craft_score"),
             "route": identity["route"], "campaign_id": campaign["campaign_id"], "rescored": False}
    entry = {key: entry[key] for key in ("slot", "path", "attempt_id", "status", "failure_category",
                                         "score", "route", "campaign_id", "rescored", "source")}
    (target / "ATTEMPT.json").write_text(json.dumps(entry, indent=2) + "\n")
    return entry


def organize(runs: Path, model: str, route: str, slots: dict[int, Path], others: list[Path], source_prefix: str) -> dict:
    if sorted(slots) != [1, 2, 3]:
        raise ValueError("Give exactly the three predetermined ordinals: --slot 1=... --slot 2=... --slot 3=...")
    root = runs / model
    if any((root / f"attempt-{n}").exists() for n in slots):
        raise ValueError(f"{root} already has maintainer slots; add new attempts with --other only")
    entries = []
    for ordinal, source in sorted(slots.items()):
        slot = f"attempt-{ordinal}"
        entries.append(project(source, root / slot, {"slot": slot, "path": slot, "route": route,
                                                     "source": f"{source_prefix}/{source.name}"}))
    for source in others:
        started = json.loads((source / "status.json").read_text()).get("started_at")
        day = datetime.fromtimestamp(started, timezone.utc).date().isoformat() if isinstance(started, (int, float)) else "undated"
        path = f"other/{day}-{source.name}"
        entries.append(project(source, root / path, {"slot": "other", "path": path, "route": route,
                                                     "source": f"{source_prefix}/{source.name}"}))
    index_path = runs / "index.json"
    index = json.loads(index_path.read_text())
    previous = index["models"].get(model, {}).get("attempts", [])
    attempts = previous + entries
    scores = [a["score"] for a in attempts if a["score"] is not None]
    index["models"][model] = {"route": route, "ranked": sum(a["slot"] != "other" for a in attempts),
                              "best": max(scores) if scores else None, "attempts": attempts}
    index["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    return index["models"][model]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=Path, default=ROOT / "runs")
    parser.add_argument("--model", required=True, help="Public model directory name, e.g. gpt-6.1-terra")
    parser.add_argument("--route", required=True, help="Public route label as in runs/index.json, e.g. codex")
    parser.add_argument("--slot", action="append", default=[], metavar="N=DIR",
                        help="Private attempt directory for predetermined ordinal N (1-3)")
    parser.add_argument("--other", action="append", default=[], type=Path, metavar="DIR",
                        help="Any other attempt (retry, failure outside the slots); goes to other/")
    parser.add_argument("--source-prefix", required=True,
                        help="Nonsecret provenance label for the source, e.g. paris:terra-20261026/runs")
    args = parser.parse_args()
    slots = {}
    for value in args.slot:
        ordinal, _, path = value.partition("=")
        slots[int(ordinal)] = Path(path)
    print(json.dumps(organize(args.runs, args.model, args.route, slots, args.other, args.source_prefix), indent=2))


if __name__ == "__main__":
    main()
