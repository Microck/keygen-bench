#!/usr/bin/env python3
"""Offline re-evaluation of google-gemini-3-flash-rep-1 in separate staging; historical files untouched.

The attempt rendered normally but its evaluation could not run: the campaign process lacked the
FT2 analysis binary (launcher omission, fixed for later attempts). This restores the
checksum-verified archive into staging, scores it with the same frozen scorer, archives the
rescored attempt as a new generation and verifies the round trip. No model request is made.
Usage (on Ashburn): rescore-3-flash-rep-1.py STAGING_BASE
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

A = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = A / "google-20261003"
SOURCE = ROOT / "results/next-max-tier-prompt-v2-google-20261003/google-gemini-3-flash-rep-1"
BASE = Path(sys.argv[1])


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(root):
    return {str(p.relative_to(root)): digest(p) for p in root.rglob("*") if p.is_file()}


os.environ.update(KEYGEN_FT2_ANALYSIS=str(A / "analysis/ft2-analysis"), LD_LIBRARY_PATH=str(A / "analysis/lib"),
                  RCLONE_CONFIG=str(A / ".private/rclone.conf"), TMPDIR=str(BASE / "tmp"))
(BASE / "tmp").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "repo/benchmark"))
import run  # noqa: E402
import score  # noqa: E402
from artifacts import ArtifactStore  # noqa: E402

config = json.loads((ROOT / "control/google-campaign-packed.json").read_text())["campaign"]
store = ArtifactStore(config["storage"])
original = snapshot(SOURCE)
historical_status = json.loads((SOURCE / "status.json").read_text())
historical_profile = json.loads((SOURCE / "profile.json").read_text())
metadata = json.loads((SOURCE / "archive.json").read_text())
stage = BASE / "attempt" / SOURCE.name
store.restore_attempt(metadata, stage)
started = time.time()
profile = score.profile_attempt(stage, force=True)
score_seconds = time.time() - started
new_metadata = store.archive_attempt(stage)
run.write_json(stage / "archive.json", new_metadata)
with tempfile.TemporaryDirectory(prefix="roundtrip-", dir=BASE) as temporary:
    store.restore_attempt(new_metadata, Path(temporary) / "attempt")
    restored = json.loads((Path(temporary) / "attempt/profile.json").read_text())
if original != snapshot(SOURCE):
    raise SystemExit("historical attempt changed during offline re-evaluation")
craft = lambda p: (p.get("craft") or {}).get("craft_score")
status = json.loads((stage / "status.json").read_text())
record = {
    "attempt_id": SOURCE.name, "source": str(SOURCE), "staging": str(stage),
    "cause": "campaign process lacked KEYGEN_FT2_ANALYSIS; render and status were unaffected",
    "historical_status": historical_status["status"],
    "historical_evaluation_status": historical_profile.get("evaluation_status"),
    "historical_evaluation_error": historical_profile.get("evaluation_error"),
    "historical_status_sha256": original["status.json"], "historical_profile_sha256": original["profile.json"],
    "source_archive_generation": metadata["generation"],
    "rescored_evaluation_status": profile.get("evaluation_status"), "rescored_eligible": profile.get("eligible"),
    "rescored_craft_score": craft(profile), "rescored_score_version": profile.get("score_version"),
    "eligible_success": run.attempt_succeeded(status, profile),
    "score_seconds": round(score_seconds, 1),
    "archive_generation": new_metadata["generation"], "archive": new_metadata["remote"],
    "archive_sha256": new_metadata["sha256"], "archive_bytes": new_metadata["bytes"],
    "archive_roundtrip_verified": craft(restored) == craft(profile),
    "historical_files_unchanged": True, "model_requests": 0,
}
run.write_json(BASE / "rescore-record.json", record)
print(json.dumps(record, indent=2))
