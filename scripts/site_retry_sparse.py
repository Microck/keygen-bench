"""Select retained retry artifacts for the deployment sparse checkout.

The first checkout includes only retry proofs and other/*/status.json. Only
other entries with a matching explicit retry proof need their larger artifacts.
The publication builder performs the full campaign and identity verification.
"""
import json
import re
from pathlib import Path

SAFE_COMPONENT = re.compile(r"[A-Za-z0-9_.-]+\Z")
SAFE_ID = re.compile(r"[A-Za-z0-9_.:-]+\Z")
ARTIFACTS = (
    "ATTEMPT.json", "spec.json", "campaign.json", "profile.json", "transport.jsonl",
    "trajectory.json", "submission/tune.xm", "canonical/canonical.wav.flac",
    "evaluations/*/profile.json", "evaluations/*/playback/trace.jsonl.gz",
    "evaluations/*/playback/loop-preview.flac",
)


def retry_patterns(runs: Path):
    matched_proofs = set()
    for status_path in sorted(runs.glob("*/other/*/status.json")):
        model_dir = status_path.parent.parent.parent
        directory = status_path.parent
        if not SAFE_COMPONENT.fullmatch(model_dir.name) or not SAFE_COMPONENT.fullmatch(directory.name):
            raise ValueError(f"Unsafe retry path: {status_path}")
        if status_path.is_symlink() or directory.is_symlink() or model_dir.is_symlink():
            raise ValueError(f"Symlinked retry path: {status_path}")
        status = json.loads(status_path.read_text())
        attempt_id = status.get("attempt_id")
        if not isinstance(attempt_id, str) or not SAFE_ID.fullmatch(attempt_id):
            continue  # Historical other entries without a valid attempt cannot have a proof.
        proof_path = model_dir / f"retry-{attempt_id}.json"
        if not proof_path.exists():
            continue
        if proof_path.is_symlink():
            raise ValueError(f"Symlinked retry proof: {proof_path}")
        proof = json.loads(proof_path.read_text())
        if proof.get("attempt_id") != attempt_id or proof.get("retry_of") != status.get("retry_of"):
            raise ValueError(f"Retry proof disagrees with status: {directory}")
        matched_proofs.add(proof_path)
        prefix = f"/runs/{model_dir.name}/other/{directory.name}"
        for artifact in ARTIFACTS:
            yield f"{prefix}/{artifact}"
    missing = set(runs.glob("*/retry-*.json")) - matched_proofs
    if missing:
        raise ValueError(f"Retry proof has no matching retained status: {sorted(missing)[0]}")


if __name__ == "__main__":
    for pattern in retry_patterns(Path("runs")):
        print(pattern)
