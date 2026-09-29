#!/usr/bin/env python3
"""Compile an approved inventory selection into an immutable native campaign."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from native_models import MAX_TRANSPORT_RETRIES, REASONING_FIELDS, TIERS, check_tier, declared_reasoning

SCHEMA = "keygen-native-campaign-3"
# Cohort label of the frozen prompts/system.txt + prompts/task.txt pair. Campaigns compiled
# before the label existed (no prompts.version) ran prompt-v1.
PROMPT_VERSION = "prompt-v2"
PROVIDERS = {"Codex OAuth": "codex_oauth", "Anthropic OAuth": "anthropic_oauth", "OpenCode Go": "go", "Vercel AI Gateway": "vercel", "NVIDIA NIM": "nim"}
LIMIT_KEYS = {"steps", "wall_seconds", "request_seconds", "command_seconds", "render_seconds", "video_seconds", "artifact_bytes"}
POLICIES = {"attempt_selection": "first_success_up_to_three_attempts", "retry": "explicit_separate_attempt_id", "failure": "separate_infrastructure_from_model", "auth": "controller_only_no_mid_cohort_refresh", "objective": "declared_native_configurations_fixed_resources"}
KEYS = {"schema", "campaign_id", "max_attempts", "inventory", "models", "limits", "concurrency", "storage", "transport", "image", "visualizer_image", "native", "policies", "prompts", "provenance"}
MODEL_KEYS = {"id", "inventory_id", "model", "response_model", "provider", "api", "base_url", "api_key_env", "generation", "tier", "readiness", "effective_settings", "backend_provenance"}
CONCURRENCY_KEYS = {"workers", "providers", "key_pools", "render", "video"}
CREDENTIAL_ENV = r"[A-Z][A-Z0-9_]*(?:KEY|TOKEN)"
POOL_MEMBER_ENV = CREDENTIAL_ENV + r"(?:_[0-9]{1,2})?"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_provenance() -> dict:
    names = ["run.py", "drive.py", "campaign.py", "native_models.py", "boat.py", "boat_transport.py", "artifacts.py", "bridge.py", "visualize.sh", "Dockerfile", "requirements.txt"]
    return {name: file_digest(HERE / name) for name in names if (HERE / name).is_file()}


def package_provenance() -> list:
    return sorted([[d.metadata["Name"], d.version] for d in importlib.metadata.distributions()])


def upstream_provenance(api: str) -> dict:
    package = importlib.metadata.distribution("mini-swe-agent")
    model = "LitellmResponseModel" if api == "responses" else "LitellmModel"
    filename = "litellm_response_model.py" if api == "responses" else "litellm_model.py"
    return {"DefaultAgent": file_digest(Path(package.locate_file("minisweagent/agents/default.py"))),
            model: file_digest(Path(package.locate_file("minisweagent/models/" + filename)))}


def validate_readiness(model: dict, effective: dict) -> None:
    from native_models import audit_messages, transmitted_reasoning
    evidence = model["readiness"]["evidence"]
    if not isinstance(evidence, dict) or not re.fullmatch(r"[a-f0-9]{64}", evidence.get("artifact_sha256", "")):
        raise ValueError("Native readiness requires a hashed evidence artifact")
    payload = evidence.get("payload")
    if not isinstance(payload, dict) or evidence.get("payload_sha256") != digest(payload):
        raise ValueError("Native readiness requires the actual immutable recorded proof payload")
    if (not isinstance(effective, dict) or effective.get("model_class") not in {"LitellmModel", "LitellmResponseModel"}
            or not isinstance(effective.get("expected_transmitted_generation"), dict)):
        raise ValueError("Native readiness must declare valid effective SDK settings")
    route = {key: model[key] for key in ("provider", "api", "base_url", "model", "response_model", "backend_provenance")}
    if (payload.get("schema") != "keygen-native-readiness-1" or payload.get("route") != route
            or payload.get("effective_settings") != effective
            or payload.get("native_source_sha256") != file_digest(HERE / "native_models.py")
            or payload.get("upstream_source_sha256") != upstream_provenance(model["api"])
            or type(evidence.get("provider_received_settings_verified")) is not bool):
        raise ValueError("Native readiness does not verify this route, settings, backend and original executable source")
    trajectory = payload.get("trajectory") or {}
    info = trajectory.get("info", {}).get("config", {})
    module = "litellm_response_model" if model["api"] == "responses" else "litellm_model"
    if (info.get("agent_type") != "minisweagent.agents.default.DefaultAgent"
            or info.get("model_type") != f"minisweagent.models.{module}.{effective['model_class']}"):
        raise ValueError("Readiness trace was not produced by the original native model and DefaultAgent")
    messages = trajectory.get("messages", [])
    turns = audit_messages(messages, model)
    if len(turns) < 2 or any(turn.get("identity_status") != "identity_match" for turn in turns):
        raise ValueError("Readiness requires at least two successful exact-identity native turns")
    first, second = turns[0]["message_index"], turns[1]["message_index"]
    actions = messages[first].get("extra", {}).get("actions") or []
    calls = {action.get("tool_call_id") for action in actions if action.get("tool_call_id")}
    observations = [message for message in messages[first + 1:second]
                    if message.get("role") == "tool" or message.get("type") == "function_call_output"]
    if (not calls or not observations
            or not any(message.get("tool_call_id", message.get("call_id")) in calls
                       and (message.get("extra") or {}).get("returncode") == 0 for message in observations)):
        raise ValueError("Readiness requires an executed native tool result between the two model turns")
    records = payload.get("transport") or []
    requests = [record for record in records if record.get("event") == "request"]
    responses = [record for record in records if record.get("event") == "response"]
    if (len(requests) < 2 or len(responses) < 2
            or any(record.get("identity_status") != "identity_match" for record in responses)
            or any(not re.fullmatch(r"[a-f0-9]{64}", record.get(key, ""))
                   for record in requests for key in ("input_sha256", "tools_sha256"))
            or requests[0]["input_sha256"] == requests[1]["input_sha256"]
            or any(record.get(key) == digest(None) for record in requests for key in ("input_sha256", "tools_sha256"))
            or len({record["tools_sha256"] for record in requests}) != 1
            or any(any((record.get("settings") or {}).get(key) != value
                       for key, value in effective["expected_transmitted_generation"].items()) for record in requests)):
        raise ValueError("Readiness requires two recorded native request/response exchanges with exact transmitted settings")
    # A declared tier counts only if its reasoning control was actually sent on every request.
    required = transmitted_reasoning(model)
    if (effective.get("transmitted_reasoning") != required
            or any(effective["expected_transmitted_generation"].get(key) != value for key, value in required.items())
            or any(any((record.get("settings") or {}).get(key) != value for key, value in required.items())
                   for record in requests)):
        raise ValueError("Readiness must record the declared tier's reasoning control in every transmitted request")


def prompt_manifest(limits: dict) -> dict:
    system = (HERE / "prompts/system.txt").read_text()
    task = (HERE / "prompts/task.txt").read_text()
    rendered = (system.replace("<<STEPS>>", "no limit on" if limits["steps"] == 0 else str(limits["steps"]))
                .replace("<<MINUTES>>", str(limits["wall_seconds"] // 60))
                .replace("<<COMMAND_SECONDS>>", str(limits["command_seconds"]))
                .replace("<<SUBMISSION_MIB>>", str(limits["artifact_bytes"] // (1024 * 1024))))
    return {"version": PROMPT_VERSION, "system_template_sha256": file_digest(HERE / "prompts/system.txt"),
            "task_sha256": file_digest(HERE / "prompts/task.txt"), "system": rendered, "task": task}


def positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def normalize_native(config: dict, models: list[dict]) -> list[dict]:
    """Compute native SDK metadata without retaining the SDK in the controller."""
    fields = ("model", "response_model", "provider", "api", "base_url", "api_key_env", "generation", "tier")
    metadata = {"native": config["native"], "models": [{key: model[key] for key in fields} for model in models]}
    payload = json.dumps(metadata, allow_nan=False).encode()
    maximum = 4 * 1024 * 1024
    if len(payload) > maximum:
        raise ValueError("Native metadata exceeds the normalization input bound")
    with tempfile.TemporaryDirectory(prefix="keygen-native-metadata-") as temporary:
        home = Path(temporary)
        environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
                       "XDG_CONFIG_HOME": str(home / ".config"), "MSWEA_GLOBAL_CONFIG_DIR": str(home / "mini-config"),
                       "MSWEA_SILENT_STARTUP": "1", "PYTHONNOUSERSITE": "1", "LITELLM_MODE": "PRODUCTION",
                       "LITELLM_LOCAL_MODEL_COST_MAP": "True"}
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            result = subprocess.run([sys.executable, "-I", str(HERE / "campaign.py"), "--normalize-native"],
                                    input=payload, stdout=output, stderr=errors, env=environment,
                                    cwd=home, timeout=90, check=False)
            if result.returncode:
                raise RuntimeError(f"Native metadata normalization exited with status {result.returncode}; private stderr discarded")
            output.seek(0)
            raw = output.read(maximum + 1)
            if len(raw) > maximum:
                raise RuntimeError("Native metadata normalization exceeded the output bound")
            normalized = json.loads(raw)
            if "error" in normalized:
                raise ValueError(normalized["error"])
            effective = normalized.get("effective")
            if not isinstance(effective, list) or len(effective) != len(models):
                raise RuntimeError("Native metadata normalization returned an invalid batch")
            return effective


def normalization_worker() -> None:
    import contextlib
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024 * 1024, 4 * 1024 * 1024))
    raw = sys.stdin.buffer.read(4 * 1024 * 1024 + 1)
    try:
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("Native metadata exceeds the normalization input bound")
        metadata = json.loads(raw)
        with contextlib.redirect_stdout(sys.stderr):
            from native_models import validate_model
            effective = [validate_model(metadata, model) for model in metadata["models"]]
        result = {"effective": effective}
    except Exception as exc:
        message = str(exc) if type(exc) in {ValueError, RuntimeError} else type(exc).__name__
        result = {"error": "Native metadata validation failed: " + message}
    print(json.dumps(result, allow_nan=False))


def validate(config: dict, *, check_provenance=True) -> dict:
    if not isinstance(config, dict) or set(config) != KEYS or config.get("schema") != SCHEMA:
        raise ValueError("Only the frozen native campaign schema is executable; inventory and legacy configs are not campaigns")
    digest(config)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", config["campaign_id"]):
        raise ValueError("Invalid campaign ID")
    if config["max_attempts"] != 3 or type(config["max_attempts"]) is not int:
        raise ValueError("Campaigns allow at most three sequential attempts, stopping after first success")
    if config["policies"] != POLICIES:
        raise ValueError("Campaign failure, selection and authentication policies must be explicit")
    limits = config["limits"]
    if set(limits) != LIMIT_KEYS:
        raise ValueError("Declare every resource limit")
    for key, value in limits.items():
        if key == "steps" and type(value) is int and value == 0:
            continue
        positive(value, key)
    if limits["wall_seconds"] % 60:
        raise ValueError("Wall budget must be whole minutes to match the frozen prompt")
    if limits["artifact_bytes"] % (1024 * 1024):
        raise ValueError("Artifact budget must be whole MiB to match the frozen prompt")
    native = config["native"]
    if (not isinstance(native, dict) or set(native) != {"timeout_seconds", "retries"}
            or native["timeout_seconds"] != limits["request_seconds"]
            or type(native["retries"]) is not int or not 0 <= native["retries"] <= MAX_TRANSPORT_RETRIES):
        raise ValueError(f"Native timeout must equal the frozen request budget; retries are 0..{MAX_TRANSPORT_RETRIES} SDK transport-only retries")
    if limits["command_seconds"] > limits["wall_seconds"]:
        raise ValueError("Command budget cannot exceed the attempt wall budget")
    concurrency = config["concurrency"]
    if set(concurrency) != CONCURRENCY_KEYS or set(concurrency["providers"]) != set(PROVIDERS.values()):
        raise ValueError("Declare global worker/render/video, every provider concurrency bound and key pools")
    for key in ("workers", "render", "video"):
        positive(concurrency[key], key)
    for key, value in concurrency["providers"].items():
        positive(value, key)
    pools = concurrency["key_pools"]
    if not isinstance(pools, dict):
        raise ValueError("key_pools must map a route credential name to member key caps")
    members = set()
    for pool, caps in pools.items():
        if not re.fullmatch(CREDENTIAL_ENV, pool) or not isinstance(caps, dict) or not caps:
            raise ValueError("Each key pool needs a credential name and at least one member key")
        for member, cap in caps.items():
            if not re.fullmatch(POOL_MEMBER_ENV, member) or member in members:
                raise ValueError("Pool member keys must be distinct credential environment names")
            positive(cap, member)
            members.add(member)
    storage = config["storage"]
    required_storage = {"backend", "reserve_bytes", "peak_bytes_per_attempt", "evict_after_archive"}
    if storage.get("backend") == "rclone":
        required_storage.add("remote")
    elif storage.get("backend") == "local":
        required_storage.add("directory")
    if set(storage) != required_storage or storage["backend"] not in {"local", "rclone"} or type(storage["evict_after_archive"]) is not bool:
        raise ValueError("Invalid storage policy")
    for key in ("reserve_bytes", "peak_bytes_per_attempt"):
        positive(storage[key], key)
    if storage["peak_bytes_per_attempt"] < 3 * limits["artifact_bytes"]:
        raise ValueError("Expected peak must cover submission, canonical render and preview")
    for key in ("image", "visualizer_image"):
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", config[key]):
            raise ValueError("Freeze immutable Docker image IDs, not mutable tags")
    transport = config["transport"]
    if transport.get("backend") == "boat":
        from boat import validate_config
        validate_config(transport)
        minimum_ttl = limits["wall_seconds"] + limits["render_seconds"] * 4 + limits["video_seconds"] + 600
        if transport["boat"]["ttl_seconds"] < minimum_ttl:
            raise ValueError("Boat TTL does not cover attempt, evaluation, export and cleanup budgets")
        if transport["boat"]["images"] != {"agent": config["image"], "visualizer": config["visualizer_image"]}:
            raise ValueError("Boat image identities differ from the frozen campaign")
    elif transport != {"backend": "local"}:
        raise ValueError("Only reviewed local Docker or Boat transports are allowed")
    inventory = config["inventory"]
    if set(inventory) != {"sha256", "entries"} or digest(inventory["entries"]) != inventory["sha256"]:
        raise ValueError("Frozen approved inventory digest mismatch")
    entries = {row["model"]: row for row in inventory["entries"]}
    models = config["models"]
    if not isinstance(models, list) or not models:
        raise ValueError("No ready models were selected")
    ids, identities = set(), set()
    for model in models:
        if set(model) != MODEL_KEYS:
            raise ValueError("Model must declare native route, readiness and effective settings exactly")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", model["id"]):
            raise ValueError("Invalid model ID")
        if not re.fullmatch(CREDENTIAL_ENV, model["api_key_env"]):
            raise ValueError("Credential source must be a dedicated key/token environment variable")
        if not isinstance(model["generation"], dict) or model["api"] not in REASONING_FIELDS:
            raise ValueError("Model must declare a native protocol and generation object")
        check_tier(model)
        row = entries.get(model["inventory_id"])
        if not row or PROVIDERS.get(row.get("provider")) != model["provider"] or row.get("status", "").startswith(("held", "blocked")):
            raise ValueError("Excluded, held or unmapped inventory route")
        if model["model"] != row.get("upstream_model") or model["response_model"] != row.get("upstream_model"):
            raise ValueError("Requested or response identity differs from the approved inventory mapping")
        backend = model["backend_provenance"]
        if not isinstance(backend, dict) or set(backend) != {"service_revision", "bridge"}:
            raise ValueError("Declare provider revision or unknown, plus exact OAuth bridge executable provenance")
        bridge = backend["bridge"]
        if model["provider"] in {"codex_oauth", "anthropic_oauth"}:
            if (not isinstance(bridge, dict) or set(bridge) != {"implementation", "version", "executable_sha256"}
                    or not bridge["implementation"] or not bridge["version"]
                    or not re.fullmatch(r"[a-f0-9]{64}", bridge["executable_sha256"])):
                raise ValueError("OAuth route requires frozen bridge implementation/version/executable hash")
        elif bridge is not None:
            raise ValueError("Direct provider routes must not introduce a bridge")
        readiness = model["readiness"]
        if not isinstance(readiness, dict) or readiness.get("status") != "verified" or not readiness.get("evidence") or not readiness.get("verified_at"):
            raise ValueError("Native protocol and exact settings readiness proof is required")
        validate_readiness(model, model["effective_settings"])
        identity = (model["provider"], model["model"])
        if model["id"] in ids or identity in identities:
            raise ValueError("Duplicate model identity")
        ids.add(model["id"])
        identities.add(identity)
    for pool, caps in pools.items():
        served = {model["provider"] for model in models if model["api_key_env"] == pool}
        if len(served) != 1:
            raise ValueError("Each key pool must serve selected models of exactly one provider")
        if sum(caps.values()) < concurrency["providers"][served.pop()]:
            raise ValueError("Per-key caps must cover the provider bound so no admitted attempt waits for a key")
    effective_models = normalize_native(config, models)
    for model, effective in zip(models, effective_models):
        if model["effective_settings"] != effective:
            raise ValueError("Declared effective settings do not match the native constructor")
    if config["prompts"] != prompt_manifest(limits):
        raise ValueError("Creative prompts changed or budget substitution differs")
    if check_provenance and config["provenance"] != {"sources": source_provenance(), "packages": package_provenance(), "python": sys.version}:
        raise ValueError("Executable/package provenance changed; compile a new campaign before inference")
    return config


def publish(path: Path, value: dict) -> None:
    """Publish complete JSON atomically without overwriting a concurrent publisher."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".publish-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if json.loads(path.read_text()) != value:
                raise ValueError("Immutable publication already exists with different contents")
    finally:
        temporary.unlink(missing_ok=True)


def check_tier_spec(models: list, tier_spec_path: Path) -> None:
    """Every selected model must declare exactly the tier and reasoning control its spec entry requires."""
    raw = tier_spec_path.read_bytes()
    spec, spec_sha256 = json.loads(raw), hashlib.sha256(raw).hexdigest()
    entries = {}
    for entry in spec.get("entries", []) if isinstance(spec, dict) else []:
        key = (entry.get("provider"), entry.get("model"))
        if key in entries:
            raise ValueError(f"Tier spec has duplicate entries for {key[0]}/{key[1]}")
        entries[key] = entry
    for model in models:
        label = f"{model.get('provider')}/{model.get('model')}"
        entry = entries.get((model.get("provider"), model.get("model")))
        if entry is None:
            raise ValueError(f"Tier spec has no entry for {label}")
        if entry.get("tier") not in TIERS or not isinstance(entry.get("reasoning"), dict) or entry.get("api") != model.get("api"):
            raise ValueError(f"Tier spec entry for {label} is blocked, unknown or for another protocol")
        tier = model.get("tier")
        if not isinstance(tier, dict):
            raise ValueError(f"{label} must declare its tier generation; there is no default tier")
        if tier != {"level": entry["tier"], "reasoning": entry["reasoning"], "spec_sha256": spec_sha256}:
            raise ValueError(f"{label} tier differs from the tier spec entry or spec digest")
        generation = model.get("generation")
        if not isinstance(generation, dict) or model.get("api") not in REASONING_FIELDS or declared_reasoning(model) != entry["reasoning"]:
            raise ValueError(f"{label} generation lacks the reasoning control its tier spec requires")


def compile_campaign(inventory_path: Path, selection_path: Path, output: Path, tier_spec_path: Path) -> dict:
    inventory = json.loads(inventory_path.read_text())
    selection = json.loads(selection_path.read_text())
    required = KEYS - {"schema", "max_attempts", "inventory", "policies", "prompts", "provenance"}
    if not isinstance(selection, dict) or set(selection) != required:
        raise ValueError(f"Selection keys must be exactly {sorted(required)}")
    check_tier_spec(selection["models"], tier_spec_path)
    rows = [{key: row.get(key) for key in ("model", "provider", "status", "upstream_model", "proxy_request_model")} for row in inventory["models"]]
    config = {**selection, "schema": SCHEMA, "max_attempts": 3, "inventory": {"sha256": digest(rows), "entries": rows}, "policies": POLICIES, "prompts": prompt_manifest(selection["limits"]), "provenance": {"sources": source_provenance(), "packages": package_provenance(), "python": sys.version}}
    for model in config["models"]:
        model["effective_settings"] = None
        evidence = model.get("readiness", {}).get("evidence")
        if isinstance(evidence, dict) and evidence.get("evidence_path"):
            proof_path = (selection_path.parent / evidence["evidence_path"]).resolve()
            if not proof_path.is_file() or proof_path.stat().st_size > 4 * 1024 * 1024:
                raise ValueError("Readiness evidence must be an existing bounded nonsecret JSON proof artifact")
            from artifacts import ArtifactStore
            ArtifactStore.check_secrets(proof_path)
            raw = proof_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != evidence.get("artifact_sha256"):
                raise ValueError("Readiness evidence artifact hash mismatch")
            evidence["payload"] = json.loads(raw)
            evidence["payload_sha256"] = digest(evidence["payload"])
            model["effective_settings"] = evidence["payload"].get("effective_settings")
        elif model.get("readiness", {}).get("status") == "verified":
            raise ValueError("Verified selection must name an actual readiness evidence_path artifact")
    validate(config)
    publish(output, {"sha256": digest(config), "campaign": config})
    return config


def read_manifest(path: Path) -> dict:
    envelope = json.loads(path.read_text())
    if (not isinstance(envelope, dict) or set(envelope) != {"sha256", "campaign"}
            or digest(envelope["campaign"]) != envelope["sha256"]
            or envelope["campaign"].get("schema") != SCHEMA):
        raise ValueError("Expected an immutable compiled campaign, not metadata or a selection")
    return envelope["campaign"]


def load(path: Path) -> dict:
    return validate(read_manifest(path))


def main():
    if sys.argv[1:] == ["--normalize-native"]:
        normalization_worker()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=HERE.parent / "MODEL-TEST-PLAN.oauth-first.json")
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--tier-spec", required=True, type=Path, help="per-model tier spec every selected model must match")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    config = compile_campaign(args.inventory.resolve(), args.selection.resolve(), args.out.resolve(), args.tier_spec.resolve())
    print(json.dumps({"campaign_id": config["campaign_id"], "models": len(config["models"]), "reserved_slots": len(config["models"]) * config["max_attempts"], "max_attempts_per_model": config["max_attempts"], "attempt_selection": config["policies"]["attempt_selection"], "sha256": digest(config)}))


if __name__ == "__main__":
    main()
