#!/usr/bin/env python3
"""Write control/google-selection.json on Ashburn for the Google AI Studio max-tier campaign.

Run on the controller (no credentials read). Shared settings (limits, storage, Boat transport,
images, native timeouts) are copied from the frozen Claude queue-3 selection so Gemini runs under
the same conditions. Each model's readiness proof is copied into collected-proofs/<id>/<sha>/.
Only verified models are selected; the rest are reported and left out.
"""
import hashlib
import json
from pathlib import Path
import shutil

ASHBURN = Path("/home/ubuntu/keygen-full.OGHjBAkO")
ROOT = ASHBURN / "google-20261003"
CONTROL = ROOT / "control"
TEMPLATE = ASHBURN / "oauth-queue-3-20261002/control/oauth-queue-3-selection.json"
CAMPAIGN_ID = "next-max-tier-prompt-v2-google-20261003"
# Latest qualification output per model: 3.6 Flash requalified after a transport-retry gap,
# 3.1 Pro once the billed key replaced the free-tier one.
OUTPUTS = [ROOT / "qualification/out-3", ROOT / "qualification/out-2", ROOT / "qualification/out"]
# Shared Boat VMs: 3 attempts per default VM (4 vCPU / 8 GB, 1x burn) = 0.33x per attempt vs
# 0.5x for one small VM each. Per-attempt containers keep their 2 CPU / 2 GiB caps.
PACKING = {"type": "default", "attempts_per_vm": 3, "linger_seconds": 120, "ttl_seconds": 14400}


def main():
    template = json.loads(TEMPLATE.read_text())
    selection = {key: template[key] for key in ("limits", "storage", "transport", "image", "visualizer_image", "native")}
    selection["campaign_id"] = CAMPAIGN_ID
    selection["transport"]["boat"].update(PACKING)
    concurrency = json.loads(json.dumps(template["concurrency"]))
    # Google rate limits are per model and each model runs its repetitions in order, so one
    # worker per model never stacks two attempts on one model's limits: 6 workers fill 2 VMs.
    concurrency["providers"]["google"] = 6
    concurrency["workers"] = 6
    concurrency["key_pools"] = {}
    selection["concurrency"] = concurrency
    models, skipped = [], {}
    for spec_path in sorted((CONTROL / "specs").glob("*.json")):
        model = json.loads(spec_path.read_text())["model"]
        out = next((base / model["id"] for base in OUTPUTS if (base / model["id"] / "readiness.json").exists()), None)
        readiness = json.loads((out / "readiness.json").read_text()) if out else {"status": "missing"}
        if readiness["status"] != "verified":
            skipped[model["id"]] = readiness.get("blocker") or readiness["status"]
            continue
        raw = (out / "proof.json").read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        target = CONTROL / "collected-proofs" / model["id"] / sha / "proof.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out / "proof.json", target)
        model["readiness"] = {"status": "verified", "verified_at": readiness["verified_at"],
                              "evidence": {"evidence_path": str(target.relative_to(CONTROL)), "artifact_sha256": sha,
                                           "provider_received_settings_verified": False}}
        models.append(model)
    selection["models"] = models
    (CONTROL / "google-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"selected": [m["id"] for m in models], "skipped": skipped}))


if __name__ == "__main__":
    main()
