#!/usr/bin/env python3
"""Build the Paris add-on selection from the add-on pilots' verified readiness proofs.

`build-selection.py PASSED_ID [PASSED_ID ...]`. Reads the Paris selection draft (transport,
storage, limits, native), the regenerated pilot specs and the proofs fetched from Paris into
pilots/<id>/; never reads credentials. Each proof is copied to collected-proofs/<id>/<sha256>/
only if its readiness.json is verified and names exactly those proof bytes.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
CAMPAIGN_ID = "next-max-tier-prompt-v2-paris-addon-20261001"
CANDIDATES = ("go-glm-5.2-chat", "go-glm-5.3-chat", "go-minimax-m2.7-messages")
# All four Go keys, one attempt each. Go-three runs this campaign beside the main-route Go campaign
# on Paris; key leases are controller-wide, so each key still serves one attempt at a time overall.
GO_POOL = {"OPENCODE_GO_API_KEY": 1, "OPENCODE_GO_API_KEY_1": 1, "OPENCODE_GO_API_KEY_2": 1, "OPENCODE_GO_API_KEY_3": 1}
WORKERS = 3
LIMITS = {"steps": 0, "wall_seconds": 7200, "request_seconds": 3600, "command_seconds": 120}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    passed = sys.argv[1:]
    if not passed or set(passed) - set(CANDIDATES) or len(set(passed)) != len(passed):
        raise SystemExit(f"usage: build-selection.py ID [ID ...] with IDs from {CANDIDATES}")
    draft = json.loads((PREP / "paris-selection-draft.json").read_text())
    models = []
    for model_id in passed:
        spec = json.loads((PREP / "pilot-specs" / f"{model_id}.json").read_text())
        model = spec["model"]
        source = HERE / "pilots" / model_id / "proof.json"
        digest = sha256(source)
        readiness = json.loads((source.parent / "readiness.json").read_text())
        if readiness["status"] != "verified" or readiness["evidence"]["artifact_sha256"] != digest:
            raise ValueError(f"{model_id} readiness record does not verify its proof")
        if json.loads(source.read_text())["route"]["model"] != model["model"]:
            raise ValueError(f"{model_id} proof is for another route")
        target = HERE / "collected-proofs" / model_id / digest / "proof.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256(target) != digest:
                raise ValueError(f"{model_id} collected proof differs")
        else:
            shutil.copyfile(source, target)
        model["readiness"] = {
            "status": "verified", "verified_at": readiness["verified_at"],
            "evidence": {"evidence_path": str(target.relative_to(HERE)), "artifact_sha256": digest,
                         "provider_received_settings_verified": readiness["evidence"]["provider_received_settings_verified"]}}
        models.append(model)
    selection = {key: draft[key] for key in draft if key != "models"}
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = models
    if any(selection["limits"][key] != value for key, value in LIMITS.items()):
        raise ValueError("Limits differ from the authorized launch")
    if selection["native"] != {"timeout_seconds": 3600, "retries": 2}:
        raise ValueError("Native settings differ from the authorized launch")
    if selection["transport"]["backend"] != "boat":
        raise ValueError("Boat transport required")
    concurrency = selection["concurrency"]
    concurrency["workers"] = WORKERS
    concurrency["providers"]["go"] = WORKERS
    concurrency["key_pools"] = {"OPENCODE_GO_API_KEY": dict(GO_POOL)}
    (HERE / "paris-addon-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"campaign_id": CAMPAIGN_ID, "models": [m["id"] for m in models],
                      "concurrency": concurrency}, indent=1))


if __name__ == "__main__":
    main()
