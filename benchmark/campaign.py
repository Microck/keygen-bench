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
from report import NON_MODEL_FAILURES, QUEUE_SELECTION, condition_fingerprint, entry_links, origin_reruns, queue_chain_id

SCHEMA = "keygen-native-campaign-3"
# Cohort label of the frozen prompts/system.txt + prompts/task.txt pair. Campaigns compiled
# before the label existed (no prompts.version) ran prompt-v1.
PROMPT_VERSION = "prompt-v2"
PROVIDERS = {"Codex OAuth": "codex_oauth", "Anthropic OAuth": "anthropic_oauth", "OpenCode Go": "go", "Vercel AI Gateway": "vercel", "NVIDIA NIM": "nim", "Google AI Studio": "google"}
LIMIT_KEYS = {"steps", "wall_seconds", "request_seconds", "command_seconds", "render_seconds", "video_seconds", "artifact_bytes"}
FIRST_SUCCESS = "first_success_up_to_three_attempts"
# Every predetermined repetition runs regardless of earlier outcomes; only QUOTA/AUTH/CONTENT_FILTER stop
# a model's sequence and leave its later slots reserved. Repetitions may be split across campaigns
# that freeze one identical condition per model (report.condition_fingerprint).
INDEPENDENT = "independent_repetitions"
# Independent repetitions whose infrastructure (non-model) failures and unstarted slots are rerun.
# Every model declares each ordinal's origin: a slot of a linked campaign (kept when it holds a
# scored outcome; rerun when it failed for a non-model reason or never started) or none (run here
# first). Reruns are separate attempts `<model>-rep-<n>-retry-<k>` linked to the previous attempt
# of the same ordinal; no existing outcome is ever rewritten.
QUEUE = QUEUE_SELECTION
POLICIES = {"attempt_selection": FIRST_SUCCESS, "retry": "explicit_separate_attempt_id", "failure": "separate_infrastructure_from_model", "auth": "controller_only_no_mid_cohort_refresh", "objective": "declared_native_configurations_fixed_resources"}
REPETITION_POLICY_KEYS = set(POLICIES) | {"repetitions", "linked_condition"}
QUEUE_POLICY_KEYS = set(POLICIES) | {"repetitions", "linked_campaigns", "plan", "max_queue_attempts"}
LINK_KEYS = {"campaign_id", "config_sha256", "repetitions", "condition_fingerprints"}
QUEUE_LINK_KEYS = {"campaign_id", "config_sha256", "condition_fingerprints"}
ORIGIN_KEYS = {"campaign_id", "attempt_id", "status", "status_sha256", "outcome", "failure_category"}
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


def unblocked_exchanges(records: list) -> list:
    """Transport records without the sends a content-filter block discarded.

    run.bound_content_filter appends a ``content_filter_block`` record after each blocked send
    (its request, plus its response when the block arrived as HTTP 200); the re-send follows.
    """
    kept, start = [], None
    for record in records:
        if record.get("event") == "content_filter_block":
            if start is not None:
                del kept[start:]
            start = None
            continue
        if record.get("event") == "request":
            start = len(kept)
        kept.append(record)
    return kept


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
    # A declared history key removal runs the original model through its one named subclass.
    removal = effective.get("history_key_removal")
    model_type = removal["model_type"] if removal else f"minisweagent.models.{module}.{effective['model_class']}"
    if (info.get("agent_type") != "minisweagent.agents.default.DefaultAgent"
            or info.get("model_type") != model_type):
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
    sent = [record for record in records if record.get("event") == "request"]
    # Exchanges that reached native history; content-filter-blocked sends are dropped here only.
    kept = unblocked_exchanges(records)
    requests = [record for record in kept if record.get("event") == "request"]
    responses = [record for record in records if record.get("event") == "response"]
    if (len(requests) < 2 or sum(record.get("event") == "response" for record in kept) < 2
            or any(record.get("identity_status") != "identity_match" for record in responses)
            or any(not re.fullmatch(r"[a-f0-9]{64}", record.get(key, ""))
                   for record in sent for key in ("input_sha256", "tools_sha256"))
            or requests[0]["input_sha256"] == requests[1]["input_sha256"]
            or any(record.get(key) == digest(None) for record in sent for key in ("input_sha256", "tools_sha256"))
            or len({record["tools_sha256"] for record in sent}) != 1
            or any(any((record.get("settings") or {}).get(key) != value
                       for key, value in effective["expected_transmitted_generation"].items()) for record in sent)):
        raise ValueError("Readiness requires two recorded native request/response exchanges with exact transmitted settings")
    # A declared tier counts only if its reasoning control was actually sent on every request.
    required = transmitted_reasoning(model)
    if (effective.get("transmitted_reasoning") != required
            or any(effective["expected_transmitted_generation"].get(key) != value for key, value in required.items())
            or any(any((record.get("settings") or {}).get(key) != value for key, value in required.items())
                   for record in sent)):
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


def repetitions(config: dict) -> list[int]:
    """Repetition ordinals this campaign runs, in order."""
    return config["policies"].get("repetitions") or list(range(1, config["max_attempts"] + 1))


def ordinal_list(values, ordinals: list[int]) -> bool:
    return (isinstance(values, list) and bool(values) and all(type(value) is int for value in values)
            and values == sorted(set(values)) and set(values) <= set(ordinals))


def check_queue_policies(config: dict) -> None:
    policies = config["policies"]
    if (set(policies) != QUEUE_POLICY_KEYS
            or {key: policies[key] for key in POLICIES} != {**POLICIES, "attempt_selection": QUEUE}):
        raise ValueError("Campaign failure, selection and authentication policies must be explicit")
    ordinals = list(range(1, config["max_attempts"] + 1))
    if policies["repetitions"] != ordinals:
        raise ValueError("A rerun queue declares every repetition through its plan")
    if type(policies["max_queue_attempts"]) is not int or not 1 <= policies["max_queue_attempts"] <= 10:
        raise ValueError("A rerun queue bounds its attempts per repetition to 1..10")
    links = policies["linked_campaigns"]
    if (not isinstance(links, list) or any(not isinstance(link, dict) or set(link) != QUEUE_LINK_KEYS for link in links)
            or len({link["campaign_id"] for link in links}) != len(links)
            or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", str(link["campaign_id"]))
                   or link["campaign_id"] == config["campaign_id"]
                   or not re.fullmatch(r"[a-f0-9]{64}", str(link["config_sha256"])) for link in links)):
        raise ValueError("Linked campaigns name other frozen campaigns by ID and configuration hash")
    linked = {link["campaign_id"]: link for link in links}
    plan = policies["plan"]
    models = {model.get("id"): model for model in config["models"]}
    if not isinstance(plan, dict) or set(plan) != set(models):
        raise ValueError("A rerun queue plans every model and only its models")
    referenced = {campaign_id: set() for campaign_id in linked}
    runs = 0
    for model_id, entries in plan.items():
        if not isinstance(entries, list) or [entry.get("repetition") if isinstance(entry, dict) else None
                                              for entry in entries] != ordinals:
            raise ValueError(f"{model_id}: plan every repetition once, in order")
        for entry in entries:
            if not {"repetition", "origin"} <= set(entry) <= {"repetition", "origin", "reruns"}:
                raise ValueError(f"{model_id}: a plan entry declares its repetition, origin and optional earlier reruns")
            origin, reruns = entry["origin"], entry.get("reruns", [])
            if not isinstance(reruns, list) or ("reruns" in entry and not reruns):
                raise ValueError(f"{model_id}: earlier reruns are a non-empty list when declared")
            start = 0 if origin is None else 1
            links = [(0, origin)] if origin is not None else []
            links += [(start + offset, link) for offset, link in enumerate(reruns)]
            for position, (index, link) in enumerate(links):
                if (not isinstance(link, dict) or set(link) != ORIGIN_KEYS or link["campaign_id"] not in linked
                        or link["attempt_id"] != queue_chain_id(model_id, entry["repetition"], index)
                        or link["outcome"] not in {"SUCCESS", "FAILURE", "UNATTEMPTED"}
                        or (link["outcome"] == "UNATTEMPTED") != (link["status"] == "RESERVED")
                        or (link["outcome"] == "FAILURE") != bool(link["failure_category"])
                        or not re.fullmatch(r"[a-f0-9]{64}", str(link["status_sha256"]))):
                    raise ValueError(f"{model_id}: an origin or rerun names its linked slot and its recorded outcome")
                if position < len(links) - 1 and not origin_reruns(link):
                    raise ValueError(f"{model_id}: a frozen rerun follows only an unstarted slot or a non-model failure")
                referenced[link["campaign_id"]].add(model_id)
            runs += origin_reruns(links[-1][1] if links else None)
    if not runs:
        raise ValueError("A rerun queue must run at least one repetition")
    for campaign_id, link in linked.items():
        fingerprints = link["condition_fingerprints"]
        if (not referenced[campaign_id] or not isinstance(fingerprints, dict) or set(fingerprints) != referenced[campaign_id]
                or any(fingerprints[model_id] != condition_fingerprint(config, models[model_id]) for model_id in fingerprints)):
            raise ValueError("Every model must freeze each linked campaign's condition fingerprint it draws on")


def check_policies(config: dict) -> None:
    """First success over all ordinals (POLICIES), or declared ordinals with an optional linked campaign.

    Independent repetitions may run every ordinal unlinked, or some of them linked to a campaign
    holding the others. A first-success continuation runs the remaining ordinals of a linked
    first-success campaign whose other ordinals were consumed without an eligible success.
    A rerun queue (QUEUE) plans each model's ordinals across linked campaigns.
    """
    policies = config["policies"]
    if policies == POLICIES:
        return
    selection = policies.get("attempt_selection") if isinstance(policies, dict) else None
    if selection == QUEUE:
        return check_queue_policies(config)
    if (selection not in (FIRST_SUCCESS, INDEPENDENT) or set(policies) != REPETITION_POLICY_KEYS
            or {key: policies[key] for key in POLICIES} != {**POLICIES, "attempt_selection": selection}):
        raise ValueError("Campaign failure, selection and authentication policies must be explicit")
    ordinals = list(range(1, config["max_attempts"] + 1))
    own = policies["repetitions"]
    if not ordinal_list(own, ordinals):
        raise ValueError("Declared repetitions must be distinct ascending ordinals within the attempt bound")
    link = policies["linked_condition"]
    if link is None:
        if selection == FIRST_SUCCESS or own != ordinals:
            raise ValueError("Only an unlinked independent campaign may declare ordinals, and it must run every repetition")
        return
    if (not isinstance(link, dict) or set(link) != LINK_KEYS
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", str(link["campaign_id"]))
            or link["campaign_id"] == config["campaign_id"]
            or not re.fullmatch(r"[a-f0-9]{64}", str(link["config_sha256"]))):
        raise ValueError("A linked condition names another frozen campaign by ID and configuration hash")
    if not ordinal_list(link["repetitions"], ordinals) or sorted(own + link["repetitions"]) != ordinals:
        raise ValueError("Linked campaigns must declare every repetition exactly once")
    if selection == FIRST_SUCCESS and link["repetitions"] != ordinals[:len(link["repetitions"])]:
        raise ValueError("A first-success continuation runs only the ordinals after the linked campaign's consumed ones")
    fingerprints = link["condition_fingerprints"]
    if (not isinstance(fingerprints, dict) or set(fingerprints) != {model.get("id") for model in config["models"]}
            or any(fingerprints[model["id"]] != condition_fingerprint(config, model) for model in config["models"])):
        raise ValueError("Every model must freeze the linked campaign's condition fingerprint")


def validate(config: dict, *, check_provenance=True) -> dict:
    if not isinstance(config, dict) or set(config) != KEYS or config.get("schema") != SCHEMA:
        raise ValueError("Only the frozen native campaign schema is executable; inventory and legacy configs are not campaigns")
    digest(config)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", config["campaign_id"]):
        raise ValueError("Invalid campaign ID")
    if config["max_attempts"] != 3 or type(config["max_attempts"]) is not int:
        raise ValueError("Campaigns allow at most three sequential attempts, stopping after first success")
    check_policies(config)
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


def repetition_policies(ordinals: list[int] | None, linked_path: Path | None,
                        selection: str = INDEPENDENT) -> tuple[dict, dict | None]:
    """Policies for first success over every ordinal (no ordinals), or for declared ordinals.

    Declared independent repetitions may link to the campaign holding the other ordinals. A
    first-success continuation must link to the first-success campaign whose earlier ordinals it
    continues.
    """
    if ordinals is None:
        if linked_path is not None:
            raise ValueError("A linked campaign requires declared repetition ordinals")
        return POLICIES, None
    policies = {**POLICIES, "attempt_selection": selection, "repetitions": sorted(ordinals), "linked_condition": None}
    if linked_path is None:
        return policies, None
    linked = read_manifest(linked_path)
    linked_selection = (linked.get("policies") or {}).get("attempt_selection")
    if selection == FIRST_SUCCESS:
        if linked_selection != FIRST_SUCCESS:
            raise ValueError("A first-success continuation links only to a first-success campaign")
        linked_ordinals = [ordinal for ordinal in range(1, linked["max_attempts"] + 1) if ordinal not in ordinals]
    elif linked_selection == FIRST_SUCCESS:
        # Only a first-success campaign's first slot runs unconditionally; later slots ran only after failure.
        linked_ordinals = [1]
    elif linked_selection == INDEPENDENT:
        linked_ordinals = linked["policies"]["repetitions"]
    else:
        raise ValueError("Linked campaign has no supported attempt selection")
    policies["linked_condition"] = {"campaign_id": linked["campaign_id"], "config_sha256": digest(linked),
                                    "repetitions": linked_ordinals, "condition_fingerprints": {}}
    return policies, linked


def queue_policies(plan_path: Path, linked_paths: list[Path]) -> tuple[dict, dict]:
    """Policies of a rerun queue from its plan ({"max_queue_attempts", "models": {id: entries}})."""
    plan = json.loads(plan_path.read_text())
    if not isinstance(plan, dict) or set(plan) != {"max_queue_attempts", "models"}:
        raise ValueError("A queue plan declares max_queue_attempts and every model's ordinal origins")
    linked = {}
    for path in linked_paths:
        manifest = read_manifest(path)
        linked[manifest["campaign_id"]] = manifest
    used = {link["campaign_id"] for entries in plan["models"].values() for entry in entries
            if isinstance(entry, dict) for link in entry_links(entry) if isinstance(link, dict)}
    if set(linked) != used:
        raise ValueError("Pass exactly the linked campaigns the queue plan's origins name")
    policies = {**POLICIES, "attempt_selection": QUEUE, "repetitions": [1, 2, 3], "plan": plan["models"],
                "max_queue_attempts": plan["max_queue_attempts"],
                "linked_campaigns": [{"campaign_id": campaign_id, "config_sha256": digest(manifest),
                                      "condition_fingerprints": {}} for campaign_id, manifest in sorted(linked.items())]}
    return policies, linked


def compile_campaign(inventory_path: Path, selection_path: Path, output: Path, tier_spec_path: Path,
                     ordinals: list[int] | None = None, linked_path: Path | None = None,
                     attempt_selection: str = INDEPENDENT, queue_plan: Path | None = None,
                     queue_links: list[Path] = ()) -> dict:
    inventory = json.loads(inventory_path.read_text())
    selection = json.loads(selection_path.read_text())
    required = KEYS - {"schema", "max_attempts", "inventory", "policies", "prompts", "provenance"}
    if not isinstance(selection, dict) or set(selection) != required:
        raise ValueError(f"Selection keys must be exactly {sorted(required)}")
    check_tier_spec(selection["models"], tier_spec_path)
    rows = [{key: row.get(key) for key in ("model", "provider", "status", "upstream_model", "proxy_request_model")} for row in inventory["models"]]
    if queue_plan is not None:
        if ordinals is not None or linked_path is not None:
            raise ValueError("A rerun queue takes its ordinals and links from its plan")
        policies, queue_linked = queue_policies(queue_plan, list(queue_links))
        linked = None
    else:
        policies, linked = repetition_policies(ordinals, linked_path, attempt_selection)
    config = {**selection, "schema": SCHEMA, "max_attempts": 3, "inventory": {"sha256": digest(rows), "entries": rows}, "policies": policies, "prompts": prompt_manifest(selection["limits"]), "provenance": {"sources": source_provenance(), "packages": package_provenance(), "python": sys.version}}
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
    if linked is not None:
        frozen = {model.get("id"): model for model in linked.get("models", [])}
        for model in config["models"]:
            fingerprint = condition_fingerprint(config, model)
            if model["id"] not in frozen or condition_fingerprint(linked, frozen[model["id"]]) != fingerprint:
                raise ValueError(f"{model['id']}: condition differs from the linked campaign's frozen model")
            policies["linked_condition"]["condition_fingerprints"][model["id"]] = fingerprint
    if queue_plan is not None:
        links = {link["campaign_id"]: link for link in policies["linked_campaigns"]}
        for model in config["models"]:
            fingerprint = condition_fingerprint(config, model)
            for entry in policies["plan"].get(model["id"], []):
                for link in entry_links(entry) if isinstance(entry, dict) else []:
                    frozen = {item.get("id"): item for item in queue_linked[link["campaign_id"]].get("models", [])}
                    if (model["id"] not in frozen
                            or condition_fingerprint(queue_linked[link["campaign_id"]], frozen[model["id"]]) != fingerprint):
                        raise ValueError(f"{model['id']}: condition differs from the linked campaign's frozen model")
                    links[link["campaign_id"]]["condition_fingerprints"][model["id"]] = fingerprint
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
    parser.add_argument("--repetitions", help="ordinals this campaign runs, e.g. 2,3; omit for first success over every ordinal")
    parser.add_argument("--attempt-selection", choices=[INDEPENDENT, FIRST_SUCCESS], default=INDEPENDENT,
                        help=f"policy for declared --repetitions: {INDEPENDENT}, or {FIRST_SUCCESS} to continue a linked first-success campaign's remaining ordinals")
    parser.add_argument("--linked-campaign", type=Path, action="append", default=[],
                        help="frozen campaign holding the other ordinals of the same condition; repeat for a --queue-plan")
    parser.add_argument("--queue-plan", type=Path, help=f"{QUEUE}: per-model ordinal origins across the linked campaigns")
    args = parser.parse_args()
    ordinals = [int(value) for value in args.repetitions.split(",")] if args.repetitions else None
    if args.queue_plan is None and len(args.linked_campaign) > 1:
        raise SystemExit("Only a --queue-plan links more than one campaign")
    config = compile_campaign(args.inventory.resolve(), args.selection.resolve(), args.out.resolve(), args.tier_spec.resolve(),
                              ordinals, args.linked_campaign[0].resolve() if args.linked_campaign and args.queue_plan is None else None,
                              args.attempt_selection, args.queue_plan.resolve() if args.queue_plan else None,
                              [path.resolve() for path in args.linked_campaign] if args.queue_plan else [])
    summary = {"campaign_id": config["campaign_id"], "models": len(config["models"]), "reserved_slots": len(config["models"]) * len(repetitions(config)), "repetitions": repetitions(config), "max_attempts_per_model": config["max_attempts"], "attempt_selection": config["policies"]["attempt_selection"], "sha256": digest(config)}
    if config["policies"]["attempt_selection"] == QUEUE:
        summary["reserved_slots"] = None
        summary["queued_repetitions"] = sum(origin_reruns(entry["origin"]) for entries in config["policies"]["plan"].values() for entry in entries)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
