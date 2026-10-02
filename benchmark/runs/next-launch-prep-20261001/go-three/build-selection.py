#!/usr/bin/env python3
"""Build the go-three main-route selection from the frozen Ashburn main-campaign selection.

Keeps all 17 launch-ready Go routes exactly as frozen (route, generation, tier, readiness proof),
with the main campaign's limits, native settings, images, transport and storage. Only
operational fields change: campaign ID, worker count, the Go provider bound, the key pool (all
four Go keys, one attempt each) and the controller path of the identical image bundle on Paris.
Writes go-three-selection.json and copies the frozen proofs into collected-proofs/ beside it.
"""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
LAUNCH = HERE.parent / "launch"
MAIN_SELECTION_SHA256 = "0388531a3980fb208bb8b81fa44c4b6b6c388dd74172f14945ea3a96260f66eb"
CAMPAIGN_ID = "next-max-tier-prompt-v2-go-three-20261002"
PARIS_BUNDLE = "/home/ubuntu/keygen-full.eALj54bh/native-images.tar"
# User rule: at most one attempt per Go key at a time (leases are controller-wide on Paris).
GO_POOL = {"OPENCODE_GO_API_KEY": 1, "OPENCODE_GO_API_KEY_1": 1, "OPENCODE_GO_API_KEY_2": 1, "OPENCODE_GO_API_KEY_3": 1}
WORKERS = 4


def main():
    raw = (LAUNCH / "ashburn-selection.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MAIN_SELECTION_SHA256:
        raise SystemExit("main selection changed")
    selection = json.loads(raw)
    models = [model for model in selection["models"] if model["provider"] == "go"]
    if len(models) != 17:
        raise SystemExit("expected the 17 launch-ready Go routes")
    selection["models"] = models
    selection["campaign_id"] = CAMPAIGN_ID
    selection["concurrency"] = {**selection["concurrency"], "workers": WORKERS,
                                "key_pools": {"OPENCODE_GO_API_KEY": dict(GO_POOL)}}
    selection["concurrency"]["providers"]["go"] = WORKERS
    selection["transport"]["boat"]["image_bundle"]["controller_path"] = PARIS_BUNDLE
    proofs = HERE / "collected-proofs"
    for model in models:
        relative = model["readiness"]["evidence"]["evidence_path"]
        source = LAUNCH / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != model["readiness"]["evidence"]["artifact_sha256"]:
            raise SystemExit(f"{model['id']}: proof hash mismatch")
        target = HERE / relative
        if not target.resolve().is_relative_to(proofs):
            raise SystemExit("proof path escapes collected-proofs")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (HERE / "go-three-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"campaign_id": CAMPAIGN_ID, "workers": WORKERS, "key_pool": GO_POOL,
                      "models": [model["id"] for model in models]}))


if __name__ == "__main__":
    main()
