"""Hy4 Preview: measure Go's real context limit on key 3, then apply the matching fix (user 2026-10-04).

Evidence: go-hy4-preview-rep-1-retry-1 got 58 good responses, the last at prompt 142,030 tokens with
max_tokens 64,000 (~206k total); the next request (~144.3k prompt + 64,000) was rejected with an
empty HTTP 400 after 83 min, before any tune.xm existed. The Go catalog lists a 1M context. The
harness maps that 400 to PROTOCOL (infrastructure), so every rerun would hit the same wall.

Measurement (3 requests, ~150k-token filler prompt, reasoning_effort high as the frozen tier):
  T1 max_tokens 16, T2 max_tokens 64,000, T3 max_tokens 32,768.
Decision:
  T1 rejected            -> PROMPT_LIMIT: no generation setting can help; Hy4 is not run.
  T1 ok, T2 rejected      -> TOTAL_LIMIT (prompt + max_tokens): if T3 passes, Hy4 runs a fresh,
                             separately labelled campaign with output cap 32,768 (max completion
                             ever observed 14,519), requalified at that exact setting.
  T1 and T2 ok            -> NOT_REPRODUCED: Hy4 is released unchanged in the main arm64 queue.
Only the cap changes; route, reasoning tier, prompts, limits and images stay the frozen ones.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import uuid

P = Path("/home/ubuntu/keygen-full.eALj54bh")
ROOT = P / "go-arm64-20261005"
CONTROL = ROOT / "control"
HY4 = CONTROL / "hy4"
PYTHON = str(P / "runtime/bin/python3.11")
REPO = ROOT / "repo-main"
TIER_SPEC = P / "go-parallel-20261002/control/tier-spec-c8cba354.json"
CAP = 32768
TARGET_PROMPT = 150_000
CAMPAIGN_ID = "next-max-tier-prompt-v2-go-hy4-cap32k-20261005"


def frozen_model():
    selection = json.loads((CONTROL / "go-arm64-main-selection.json").read_text())
    return selection, next(m for m in selection["models"] if m["id"] == "go-hy4-preview")


def request(model, key, prompt, max_tokens):
    body = {"model": model["model"], "max_tokens": max_tokens, "reasoning_effort": "high",
            "messages": [{"role": "user", "content": prompt + "\n\nReply with the single word OK."}]}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "User-Agent": "keygen-benchmark/hy4-limit-probe-1.0", "x-opencode-session": uuid.uuid4().hex}
    req = urllib.request.Request(model["base_url"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(), headers=headers, method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=900) as response:
            usage = json.loads(response.read()).get("usage") or {}
            return {"ok": True, "status": response.status, "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"), "seconds": round(time.time() - started, 1)}
    except urllib.error.HTTPError as exc:
        text = exc.read(4096).decode("utf-8", "replace")
        return {"ok": False, "status": exc.code, "quota": exc.code == 429 or "limit" in text.lower(),
                "body_bytes": len(text), "seconds": round(time.time() - started, 1)}
    except Exception as exc:
        return {"ok": False, "status": None, "error": type(exc).__name__, "seconds": round(time.time() - started, 1)}


def measure(env, record):
    _, model = frozen_model()
    key = env["OPENCODE_GO_API_KEY_3"]
    unit = "pattern row 00 C-4 01 .. 000 | "
    calibration = request(model, key, unit * 2000, 16)
    record["calibration"] = calibration
    if not calibration["ok"] or not calibration.get("prompt_tokens"):
        return "PROBE_FAILED"
    repeats = int(2000 * TARGET_PROMPT / calibration["prompt_tokens"])
    prompt = unit * repeats
    for name, max_tokens in (("T1", 16), ("T2", 64000), ("T3", CAP)):
        record[name] = request(model, key, prompt, max_tokens)
        if record[name].get("quota"):
            return "QUOTA"
        if name == "T1" and not record[name]["ok"]:
            return "PROMPT_LIMIT"
        if name == "T2" and record[name]["ok"]:
            return "NOT_REPRODUCED"
        if name == "T2" and record[name]["status"] is None:
            return "PROBE_FAILED"
    return "TOTAL_LIMIT" if record["T3"]["ok"] else "TOTAL_LIMIT_CAP_REJECTED"


def run(command, log, env, cwd=REPO, timeout=None):
    with (HY4 / log).open("ab") as handle:
        return subprocess.run(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT,
                              timeout=timeout).returncode


def capped_campaign(env, record):
    """Requalify Hy4 at the 32,768 cap, then compile, doctor and run its own 3 attempts. Returns pid."""
    selection, model = frozen_model()
    spec = json.loads(TIER_SPEC.read_text())
    for entry in spec["entries"]:
        if entry.get("provider") == "go" and entry.get("model") == "hy4-preview":
            entry["generation"] = {**entry.get("generation", {}), "max_tokens": CAP}
            entry.setdefault("limits", {})["run_output_cap"] = CAP
            entry["notes"] = (entry.get("notes") or []) + [
                "2026-10-05: Go enforces ~207k prompt + max_tokens for hy4-preview (measured, see hy4/record.json); "
                f"cap {CAP} keeps ~175k of history. Max completion observed: 14,519."]
    raw = (json.dumps(spec, indent=2) + "\n").encode()
    sha = hashlib.sha256(raw).hexdigest()
    tier_spec = HY4 / f"tier-spec-hy4-{sha[:8]}.json"
    tier_spec.write_bytes(raw)
    capped = {key: model[key] for key in ("id", "inventory_id", "model", "response_model", "provider", "api",
                                          "base_url", "api_key_env", "backend_provenance")}
    capped["generation"] = {**model["generation"], "max_tokens": CAP}
    capped["tier"] = {**model["tier"], "spec_sha256": sha}
    pilot = HY4 / "pilot-spec.json"
    pilot.write_text(json.dumps({"model": capped, "config": {"native": selection["native"]}, "image": selection["image"],
                                 "limits": {"steps": 5, "wall_seconds": 1800, "command_seconds": 15}}, indent=2) + "\n")
    out = HY4 / "qualification"
    qualify_env = {**env, "OPENCODE_GO_API_KEY": env["OPENCODE_GO_API_KEY_3"]}
    run([PYTHON, "-I", "benchmark/native_readiness.py", "--spec", str(pilot), "--out", str(out)],
        "qualification.private.log", qualify_env, timeout=2400)
    readiness = json.loads((out / "readiness.json").read_text())
    record["qualification"] = {"status": readiness["status"], "blocker": readiness.get("blocker")}
    if readiness["status"] != "verified":
        return None
    proof = (out / "proof.json").read_bytes()
    proof_sha = hashlib.sha256(proof).hexdigest()
    target = HY4 / "collected-proofs" / capped["id"] / proof_sha / "proof.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(proof)
    capped["readiness"] = {"status": "verified", "verified_at": readiness["verified_at"], "evidence": {
        "evidence_path": str(target.relative_to(HY4)), "artifact_sha256": proof_sha,
        "provider_received_settings_verified": False}}
    selection = {**selection, "campaign_id": CAMPAIGN_ID, "models": [capped]}
    (HY4 / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    manifest, results = HY4 / "campaign.json", ROOT / "results" / CAMPAIGN_ID
    plain = {key: env[key] for key in ("PATH", "HOME", "LANG", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE")}
    if run([PYTHON, "-I", "benchmark/campaign.py", "--inventory", str(REPO / "MODEL-TEST-PLAN.oauth-first.json"),
            "--selection", str(HY4 / "selection.json"), "--tier-spec", str(tier_spec), "--repetitions", "1,2,3",
            "--out", str(manifest)], "compile.private.log", plain, timeout=900):
        record["compile"] = "failed"
        return None
    if run([PYTHON, "-I", "benchmark/run.py", "doctor", "--campaign", str(manifest), "--out", str(results)],
           "doctor.private.log", env, timeout=900):
        record["doctor"] = "failed"
        return None
    log = (HY4 / "campaign.private.log").open("ab")
    return subprocess.Popen([PYTHON, "-I", "benchmark/run.py", "run", "--campaign", str(manifest), "--out", str(results)],
                            cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT)
