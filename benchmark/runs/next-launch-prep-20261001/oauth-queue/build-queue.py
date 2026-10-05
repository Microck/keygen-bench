#!/usr/bin/env python3
"""Build the OAuth rerun-queue selection and plan (campaign policy independent_repetitions_infrastructure_reruns).

Models: every launch-ready Claude/GPT route whose three max-tier repetitions are not all scored
(main campaign attempt 1 + OAuth repeats attempts 2-3), plus claude-opus-5-5, requalified at its
max tier on 2026-10-02 (oauth-queue/requalify, proof copied into collected-proofs/). Every frozen
route field, proof, limit, native setting, image and Boat resource class is copied from the main
selection; only campaign ID, concurrency (codex 4, anthropic 2) and key pools change.

Each ordinal's origin is classified by benchmark.report.attempt_row on read-only metadata copies of
the two results roots (argv[1] = main root copy, argv[2] = repeats root copy) and frozen with its
status.json sha256. Writes oauth-queue-selection.json and oauth-queue-plan.json beside this file.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
PREP = HERE.parent
sys.path.insert(0, str(PREP.parents[2] / "benchmark"))
import report  # noqa: E402

MAIN_SELECTION_SHA256 = "0388531a3980fb208bb8b81fa44c4b6b6c388dd74172f14945ea3a96260f66eb"
MAIN_ID = "next-max-tier-prompt-v2-ashburn-20261001"
REPEATS_ID = "next-max-tier-prompt-v2-oauth-repeats-20261001"
CAMPAIGN_ID = "next-max-tier-prompt-v2-oauth-queue-20261002"
MAX_QUEUE_ATTEMPTS = 4
OAUTH = {"codex_oauth", "anthropic_oauth"}
NEW = "anthropic_oauth-claude-opus-5-5"
REQUALIFY = HERE / "requalify/out/requalify-1" / NEW


def classify(root: Path, attempt_id: str, repetition: int) -> dict:
    config, config_hash, fingerprint = report.open_cohort(root, root / "campaign.lock.json")
    model_id = attempt_id.rsplit("-rep-", 1)[0]
    model = next(model for model in config["models"] if model["id"] == model_id)
    row = report.attempt_row(root, attempt_id, (model, repetition), fingerprint, config_hash, report.campaign_cohort(config))
    if row["status"] == "RESERVED":
        outcome = "UNATTEMPTED"
    elif row["outcome"] in {"SUCCESS", "FAILURE"}:
        outcome = row["outcome"]
    else:
        raise SystemExit(f"{attempt_id}: outcome {row['outcome']} needs review before it can be an origin")
    return {"campaign_id": config["campaign_id"], "attempt_id": attempt_id, "status": row["status"],
            "status_sha256": hashlib.sha256((root / attempt_id / "status.json").read_bytes()).hexdigest(),
            "outcome": outcome, "failure_category": row["failure_category"] if outcome == "FAILURE" else None}


def main():
    main_root, repeats_root = Path(sys.argv[1]), Path(sys.argv[2])
    raw = (PREP / "launch/ashburn-selection.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != MAIN_SELECTION_SHA256:
        raise SystemExit("main selection changed")
    selection = json.loads(raw)
    oauth = [model for model in selection["models"] if model["provider"] in OAUTH]
    plan, models = {}, []
    for model in oauth:
        origins = [classify(main_root, f"{model['id']}-rep-1", 1)] + [
            classify(repeats_root, f"{model['id']}-rep-{n}", n) for n in (2, 3)]
        if any(report.origin_reruns(origin) for origin in origins):
            models.append(model)
            plan[model["id"]] = [{"repetition": n, "origin": origin} for n, origin in enumerate(origins, 1)]
    template = next(model for model in oauth if model["id"] == "anthropic_oauth-claude-sonnet-5-5")
    readiness = json.loads((REQUALIFY / "readiness.json").read_text())
    proof = (REQUALIFY / "proof.json").read_bytes()
    proof_sha256 = hashlib.sha256(proof).hexdigest()
    if readiness["status"] != "verified" or readiness["evidence"]["artifact_sha256"] != proof_sha256:
        raise SystemExit("opus-5-5 requalification is not a verified proof")
    new = json.loads(json.dumps(template))
    new.update(id=NEW, inventory_id="claude-opus-5-5", model="claude-opus-5-5", response_model="claude-opus-5-5")
    new["readiness"] = {"status": "verified", "verified_at": readiness["verified_at"], "evidence": {
        "evidence_path": f"collected-proofs/{NEW}/{proof_sha256}/proof.json", "artifact_sha256": proof_sha256,
        "provider_received_settings_verified": readiness["evidence"]["provider_received_settings_verified"]}}
    models.append(new)
    plan[NEW] = [{"repetition": n, "origin": None} for n in (1, 2, 3)]
    for model in models:
        relative = model["readiness"]["evidence"]["evidence_path"]
        source = REQUALIFY / "proof.json" if model["id"] == NEW else PREP / "launch" / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != model["readiness"]["evidence"]["artifact_sha256"]:
            raise SystemExit(f"{model['id']}: proof hash mismatch")
        target = HERE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    selection["models"] = models
    selection["campaign_id"] = CAMPAIGN_ID
    selection["concurrency"] = {**selection["concurrency"], "workers": 6, "key_pools": {}}
    selection["concurrency"]["providers"].update(codex_oauth=4, anthropic_oauth=2)
    (HERE / "oauth-queue-selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    (HERE / "oauth-queue-plan.json").write_text(json.dumps({"max_queue_attempts": MAX_QUEUE_ATTEMPTS, "models": plan}, indent=2) + "\n")
    for model_id, entries in plan.items():
        print(model_id, [(entry["repetition"], (entry["origin"] or {}).get("outcome", "NEW"),
                          (entry["origin"] or {}).get("failure_category"), report.origin_reruns(entry["origin"]))
                         for entry in entries])


if __name__ == "__main__":
    main()
