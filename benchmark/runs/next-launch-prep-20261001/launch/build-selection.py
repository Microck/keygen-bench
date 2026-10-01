#!/usr/bin/env python3
"""Build the launch selection: the 34 launch-ready routes with their frozen readiness proofs.

Reads the Ashburn selection draft, qualification-results.json and the collected proofs; never
reads credentials. Each proof is copied to collected-proofs/<model>/<sha256>/proof.json only if
its bytes hash to the qualification-recorded proof_sha256 and its readiness.json agrees.
"""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
CAMPAIGN_ID = "next-max-tier-prompt-v2-ashburn-20261001"
EXCLUDED_PROVIDERS = {"nim", "vercel"}
EXCLUDED_MODELS = {"anthropic_oauth-claude-opus-5"}  # content filter blocks every send
PROVIDER_ORDER = ("codex_oauth", "anthropic_oauth", "go")
EXPECTED_COUNTS = {"anthropic_oauth": 9, "codex_oauth": 8, "go": 17}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    draft = json.loads((PREP / "ashburn-selection-draft.json").read_text())
    results = json.loads((PREP / "qualification-results.json").read_text())
    ready = results["summary"]["launch_ready"]
    if len(ready) != results["summary"]["launch_ready_count"] or len(set(ready)) != len(ready):
        raise ValueError("Launch-ready list is inconsistent")
    models = {model["id"]: model for model in draft["models"]}
    chosen = []
    for model_id in ready:
        model = json.loads(json.dumps(models[model_id]))
        if model["provider"] in EXCLUDED_PROVIDERS or model_id in EXCLUDED_MODELS:
            raise ValueError(f"Excluded route in launch-ready list: {model_id}")
        attempts = [a for a in results["pilots"][model_id]["attempts"] if a["status"] == "pass"]
        if len(attempts) != 1:
            raise ValueError(f"{model_id} needs exactly one passing pilot")
        attempt = attempts[0]
        source = PREP / attempt["proof"]
        digest = sha256(source)
        if digest != attempt["proof_sha256"]:
            raise ValueError(f"{model_id} proof bytes differ from the qualification record")
        readiness = json.loads((source.parent / "readiness.json").read_text())
        evidence = readiness["evidence"]
        if readiness["status"] != "verified" or evidence["artifact_sha256"] != digest:
            raise ValueError(f"{model_id} readiness record does not verify its proof")
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
                         "provider_received_settings_verified": evidence["provider_received_settings_verified"]}}
        model.pop("effective_settings", None)
        chosen.append(model)
    counts = {provider: sum(m["provider"] == provider for m in chosen) for provider in PROVIDER_ORDER}
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"Unexpected provider counts {counts}")
    # run.py submits model sequences FIFO to a pool of `workers` threads, and a thread whose
    # provider bound is full waits holding its worker. Round-robin by provider so the first
    # wave starts 4 codex, 4 anthropic and 4 go sequences instead of parking go behind OAuth.
    queues = {provider: [m for m in chosen if m["provider"] == provider] for provider in PROVIDER_ORDER}
    ordered = []
    while any(queues.values()):
        for provider in PROVIDER_ORDER:
            if queues[provider]:
                ordered.append(queues[provider].pop(0))
    selection = {key: draft[key] for key in draft if key != "models"}
    selection["campaign_id"] = CAMPAIGN_ID
    selection["models"] = ordered
    expected = {"steps": 0, "wall_seconds": 7200, "request_seconds": 3600, "command_seconds": 120}
    if any(selection["limits"][key] != value for key, value in expected.items()):
        raise ValueError("Limits differ from the authorized launch")
    if selection["native"] != {"timeout_seconds": 3600, "retries": 2}:
        raise ValueError("Native settings differ from the authorized launch")
    concurrency = selection["concurrency"]
    pool = concurrency["key_pools"]["OPENCODE_GO_API_KEY"]
    if (concurrency["providers"]["codex_oauth"], concurrency["providers"]["anthropic_oauth"],
            concurrency["providers"]["go"]) != (4, 4, 12) or len(pool) != 4 or set(pool.values()) != {3}:
        raise ValueError("Concurrency differs from the authorized launch")
    if selection["transport"]["backend"] != "boat":
        raise ValueError("Boat transport required")
    (HERE / "ashburn-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"campaign_id": CAMPAIGN_ID, "models": len(ordered), "counts": counts,
                      "first_wave": [m["id"] for m in ordered[:concurrency["workers"]]]}, indent=1))


if __name__ == "__main__":
    main()
