#!/usr/bin/env python3
"""Qualify one exact native route through an isolated worker and offline Docker."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import campaign
import run
from native_models import MAX_TRANSPORT_RETRIES, build_probe_model, digest, redact_credentials

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
DEFAULT_LIMITS = {"steps": 5, "wall_seconds": 180, "command_seconds": 15}
SYSTEM = (
    "You are a native protocol readiness agent. Use only the declared bash function tool "
    "inside the offline workspace. A reply may contain one or several bash tool calls; every "
    "tool call in a reply runs in order. Never access credentials, host paths, or network. "
    "Follow the task's turns in order and wait for each turn's executed tool results before "
    "the next turn."
)
# M3: one long non-streaming generation on the production settings. It decides only
# whether the route's transport survives a long request; it is never readiness evidence.
PROBE_LONG_GENERATION = "long-generation"
PROBE_SCHEMA = "keygen-long-generation-probe-1"
PROBE_SYSTEM = (
    "You are a native protocol probe agent. Use only the declared bash function tool inside "
    "the offline workspace. A reply may contain several bash tool calls; every tool call in a "
    "reply runs in order. Never access credentials, host paths, or network. Follow the task exactly."
)
PROBE_LIMITS = {"steps": 3, "wall_seconds": 3600, "command_seconds": 60}
PROBE_THRESHOLDS = {"output_tokens_gt": 32768, "latency_seconds_gt": 600}
PROBE_POLICY = ("routes failing this probe get run_output_cap reduced to 64000 (Anthropic long-request "
                "guidance) before launch; streaming is not available because mini-swe-agent 2.4.6 "
                "LitellmModel/LitellmResponseModel call the SDK without stream")
# A connection that dropped (and was resent by a transport retry), a gateway error body,
# an SDK timeout/connection error, or a request still open at the outer deadline.
PROBE_FAIL_CATEGORIES = {"transport_error", "gateway_error", "transport_retry", "request_timeout"}
PROBE_INFRASTRUCTURE_CATEGORIES = {"quota_or_rate_limit", "authentication_error", "content_filter"}
PROBE_CHUNK_LINES = 2000  # Keeps each heredoc argument below Linux's 128 KiB MAX_ARG_STRLEN.
PROBE_LINES = 12000


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("Readiness artifact exceeds its byte bound")
    return json.loads(path.read_text())


def normalize_spec(spec: dict, bridge_executable: Path | None) -> dict:
    if not isinstance(spec, dict) or set(spec) - {"model", "config", "image", "limits"}:
        raise ValueError("Expected a sanitized model/config/image pilot spec")
    config, model = spec["config"], spec["model"]
    if not isinstance(config, dict) or set(config) != {"native"}:
        raise ValueError("Pilot config requires only native settings")
    if not isinstance(model, dict):
        raise ValueError("Pilot model must be an object")
    required = {"id", "model", "response_model", "provider", "api", "base_url", "api_key_env",
                "generation", "tier", "backend_provenance"}
    if not required <= set(model) or set(model) - required - {"inventory_id", "readiness", "effective_settings"}:
        raise ValueError("Pilot model must declare its exact native identity and backend")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", model["id"]):
        raise ValueError("Invalid pilot model ID")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", spec["image"]):
        raise ValueError("Pilot requires an immutable Docker image ID")
    limits = spec.get("limits", DEFAULT_LIMITS)
    if not isinstance(limits, dict) or set(limits) != set(DEFAULT_LIMITS):
        raise ValueError("Pilot requires explicit step, wall and command bounds")
    for key, maximum in (("steps", 10), ("wall_seconds", 3600), ("command_seconds", 60)):
        if type(limits[key]) is not int or not 1 <= limits[key] <= maximum:
            raise ValueError("Invalid pilot resource bound")
    if limits["steps"] < 3 or limits["command_seconds"] > limits["wall_seconds"]:
        raise ValueError("Pilot must permit the three-turn task inside its wall bound")
    native = run._native(config)
    if not 0 <= native["retries"] <= MAX_TRANSPORT_RETRIES:
        raise ValueError("Qualification permits only bounded transport retries")
    # Preserve the production request timeout even when it exceeds this tiny
    # pilot's wall budget. The controller kills the worker at the outer deadline.
    backend = model["backend_provenance"]
    if not isinstance(backend, dict) or set(backend) != {"service_revision", "bridge"}:
        raise ValueError("Pilot requires explicit backend provenance")
    revision = backend["service_revision"]
    if revision is not None and (not isinstance(revision, str) or len(revision) > 200):
        raise ValueError("Invalid provider revision")
    bridge = backend["bridge"]
    if model["provider"] in {"codex_oauth", "anthropic_oauth"}:
        if (not isinstance(bridge, dict) or set(bridge) != {"implementation", "version", "executable_sha256"}
                or not isinstance(bridge["implementation"], str) or not bridge["implementation"]
                or not isinstance(bridge["version"], str) or not bridge["version"]
                or not re.fullmatch(r"[a-f0-9]{64}", bridge["executable_sha256"])):
            raise ValueError("OAuth qualification requires exact executable provenance")
        if bridge_executable is None or campaign.file_digest(bridge_executable) != bridge["executable_sha256"]:
            raise ValueError("Actual OAuth bridge executable does not match declared provenance")
    elif bridge is not None or bridge_executable is not None:
        raise ValueError("Direct routes must not introduce a bridge")
    # Do not carry a previous proof or a pretend verified flag into the bootstrap.
    model = {key: value for key, value in model.items() if key not in {"readiness", "effective_settings"}}
    model["readiness"] = {"status": "qualification", "evidence": None, "verified_at": None}
    effective = campaign.normalize_native(config, [model])[0]
    model["effective_settings"] = effective
    return {"model": model, "config": config, "image": spec["image"], "limits": dict(limits)}


def worker(spec_path: Path) -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES))
    spec = load_json(spec_path)
    root, model = spec_path.parent, spec["model"]
    target = "ANTHROPIC_API_KEY" if model["api"] == "messages" else "OPENAI_API_KEY"
    secrets = [os.environ.get(target, "")]
    agent = None
    result = {"exit_status": "NotStarted", "failure_category": "infrastructure_error"}
    try:
        from minisweagent import __version__
        from minisweagent.agents.default import DefaultAgent
        if __version__ != run.MINI_VERSION:
            raise RuntimeError("mini-swe-agent version mismatch")
        provenance = {
            "captured_at": timestamp(), "native_source_sha256": campaign.file_digest(HERE / "native_models.py"),
            "readiness_source_sha256": campaign.file_digest(Path(__file__)),
            "sandbox_source_sha256": campaign.file_digest(HERE / "run.py"),
            "upstream_source_sha256": campaign.upstream_provenance(model["api"]),
            "packages": campaign.package_provenance(), "python": sys.version,
            "backend_provenance": model["backend_provenance"],
        }
        run.write_json(root / "runtime-provenance.json", provenance)
        native = run.bound_content_filter(build_probe_model(spec["config"], model, root), model, root)
        agent = DefaultAgent(
            native, run.Sandbox(spec["docker"], spec["container"], spec["limits"]["command_seconds"]),
            system_template="{{ frozen_system }}", instance_template="{{ task }}",
            step_limit=spec["limits"]["steps"], cost_limit=0,
            wall_time_limit_seconds=spec["limits"]["wall_seconds"],
            output_path=root / "isolated-host-home/trajectory.private.json",
        )
        result = agent.run(task=spec["task"], frozen_system=spec["system"])
    except Exception as exc:
        result = {"exit_status": type(exc).__name__, "failure_category": run.native_failure_category(exc, root)}
    finally:
        if agent is not None:
            run.write_json(root / "trajectory.json", redact_credentials(agent.serialize(), secrets))
        run.write_json(root / "worker-result.json", redact_credentials(result, secrets))


def start_pilot_container(docker: list[str], image: str, name: str) -> None:
    """A tiny credential-free protocol workspace, not an FT2 acceptance run."""
    volume = name + "-work"
    run.shell(docker + ["volume", "create", "--driver", "local", "--opt", "type=tmpfs",
                       "--opt", "device=tmpfs", "--opt", "o=size=16m,uid=10001,gid=10001", volume])
    common = ["--network", "none", "--read-only", "--cap-drop", "ALL",
              "--security-opt", "no-new-privileges", "--user", "10001:10001",
              "--pids-limit", "32", "--entrypoint", "/bin/sleep"]
    run.shell(docker + ["create", "--name", name + "-files", *common, "--memory", "32m",
                       "--memory-swap", "32m", "--mount",
                       f"type=volume,source={volume},target=/export,readonly,volume-nocopy", image, "infinity"])
    run.shell(docker + ["start", name + "-files"])
    run.shell(docker + ["create", "--name", name, *common, "--memory", "128m",
                       "--memory-swap", "128m", "--cpus", "1", "--mount",
                       f"type=volume,source={volume},target=/workspace,volume-nocopy",
                       "--tmpfs", "/tmp:rw,nosuid,nodev,size=8m,uid=10001,gid=10001",
                       image, "infinity"])
    run.shell(docker + ["start", name])


def sandbox_preflight(docker: list[str], name: str, image: str) -> dict:
    state = json.loads(run.shell(docker + ["inspect", name]).stdout)[0]
    config, host = state["Config"], state["HostConfig"]
    if (state["Image"] != image or host["NetworkMode"] != "none" or not host["ReadonlyRootfs"]
            or config["User"] != "10001:10001" or host["Memory"] != 128 * 1024 * 1024
            or any(re.search(r"(?:KEY|TOKEN|SECRET|PASSWORD)", value.partition("=")[0], re.I)
                   for value in config.get("Env") or [] if not value.startswith("GPG_KEY="))
            or any(mount["Type"] == "bind" for mount in state.get("Mounts", []))):
        raise RuntimeError("Pilot sandbox failed credential-free offline isolation")
    return {"image": state["Image"], "network": host["NetworkMode"], "read_only": True,
            "user": config["User"], "memory_bytes": host["Memory"],
            "credential_environment_present": False, "host_bind_mounts": False,
            "public_image_gpg_key": any(value.startswith("GPG_KEY=") for value in config.get("Env") or []),
            "ft2_acceptance_claim": False}


def transport_records(root: Path) -> list:
    path = root / "transport.jsonl"
    if not path.exists():
        return []
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("Transport audit exceeds its byte bound")
    return [json.loads(line) for line in path.read_text().splitlines()]


def executed_calls(messages: list) -> list[str]:
    """Tool call IDs of model replies whose every tool call executed with exit code 0.

    A reply may carry one call (Codex) or several; either counts. mini 2.4.6 records each
    call's ID in the reply's ``extra.actions`` and answers it with a chat ``tool`` message
    (``tool_call_id``) or a Responses ``function_call_output`` (``call_id``).
    """
    replies = [index for index, message in enumerate(messages)
               if isinstance((message.get("extra") or {}).get("actions"), list) and message["extra"]["actions"]]
    verified = []
    for position, index in enumerate(replies):
        calls = [action.get("tool_call_id") for action in messages[index]["extra"]["actions"]]
        if not all(calls) or len(set(calls)) != len(calls):
            continue
        end = replies[position + 1] if position + 1 < len(replies) else len(messages)
        results = {}
        for message in messages[index + 1:end]:
            if message.get("role") == "tool" or message.get("type") == "function_call_output":
                results[message.get("tool_call_id", message.get("call_id"))] = (message.get("extra") or {}).get("returncode")
        if all(call in results and results[call] == 0 for call in calls):
            verified.extend(calls)
    return verified


def verify_pilot(spec: dict, root: Path, marker: str) -> dict:
    model = spec["model"]
    result = load_json(root / "worker-result.json")
    if result.get("exit_status") != "Submitted" or result.get("failure_category"):
        raise ValueError("Native pilot did not finish the tool-result task successfully")
    trajectory = load_json(root / "trajectory.json")
    messages = trajectory.get("messages", [])
    observations = [message for message in messages
                    if message.get("role") == "tool" or message.get("type") == "function_call_output"]
    if (len(observations) < 3
            or any((message.get("extra") or {}).get("returncode") != 0 for message in observations)):
        raise ValueError("Pilot did not observe a successful native read-back tool result")
    # Write, read back and test: three answered calls, in one-call or multi-call replies.
    if len(executed_calls(messages)) < 3:
        raise ValueError("Pilot did not observe three native tool calls answered by their executed results")
    artifact = root / "submission/readiness.txt"
    if artifact.read_text() != marker + "\n":
        raise ValueError("Offline pilot artifact did not match the requested tool task")
    provenance = load_json(root / "runtime-provenance.json")
    if (provenance["native_source_sha256"] != campaign.file_digest(HERE / "native_models.py")
            or provenance["sandbox_source_sha256"] != campaign.file_digest(HERE / "run.py")
            or provenance["readiness_source_sha256"] != campaign.file_digest(Path(__file__))
            or provenance["upstream_source_sha256"] != campaign.upstream_provenance(model["api"])
            or provenance["packages"] != campaign.package_provenance()
            or provenance["backend_provenance"] != model["backend_provenance"]):
        raise ValueError("Pilot executable/package/backend provenance changed during qualification")
    records = transport_records(root)
    # A content-filter-blocked send never reached native history (run.bound_content_filter).
    events = [record.get("event") for record in campaign.unblocked_exchanges(records)]
    if len(events) < 4 or len(events) % 2 or events != ["request", "response"] * (len(events) // 2):
        raise ValueError("Pilot audit does not contain complete sequential wire exchanges")
    payload = {
        "schema": "keygen-native-readiness-1", "verified_at": timestamp(),
        "route": {key: model[key] for key in ("provider", "api", "base_url", "model", "response_model", "backend_provenance")},
        "effective_settings": model["effective_settings"],
        "native_source_sha256": provenance["native_source_sha256"],
        "upstream_source_sha256": provenance["upstream_source_sha256"],
        "runtime_provenance": provenance, "trajectory": trajectory, "transport": records,
        "sandbox": load_json(root / "sandbox-preflight.json"),
        "cleanup": load_json(root / "cleanup.json"),
        "tool_artifact_sha256": campaign.file_digest(artifact),
        "payload_scope": "controller_to_endpoint", "provider_received_settings_verified": False,
    }
    # The compiler checks actual identity, original model history, executed tool call
    # IDs, wire exchanges and exact settings. A qualification label is not evidence.
    candidate = {**model, "readiness": {"status": "qualification", "evidence": {
        "artifact_sha256": digest(payload), "payload": payload, "payload_sha256": digest(payload),
        "provider_received_settings_verified": False,
    }}}
    campaign.validate_readiness(candidate, model["effective_settings"])
    return payload


def readiness_task(marker: str) -> str:
    return (
        "Work in successive turns. Turn 1, one bash tool call: mkdir -p submission and "
        f"write the single line {marker} to submission/readiness.txt; print created. Wait for its "
        "executed tool result. Turn 2, two bash tool calls, preferably both in one reply, "
        "otherwise one per reply: the first runs cat submission/readiness.txt; the second tests "
        f"that the file content equals {marker}, for example test \"$(cat submission/readiness.txt)\" "
        f"= {marker}. Wait for both executed tool results. Final turn, one bash tool call: "
        f"{run.FINISH}. Do not submit before both turn-2 results."
    )


def long_generation_task() -> str:
    calls = PROBE_LINES // PROBE_CHUNK_LINES
    return (
        f"In one single reply, write submission/long.txt containing the integers 1 through {PROBE_LINES} "
        "spelled out in English words, one per line, in increasing order (one, two, three, ..., "
        "twenty-one, ..., twelve thousand). Type every line literally; never generate the text with a "
        f"program, loop, seq, or other tool. Use {calls} bash tool calls in that same reply, in order; "
        f"each appends the next {PROBE_CHUNK_LINES} lines with its own quoted heredoc "
        "(cat >> submission/long.txt <<'EOF' ... EOF), and the first also starts with mkdir -p submission. "
        f"As tool call {calls + 1} of the same reply, run {run.FINISH}."
    )


def execute_pilot(spec_path: Path, root: Path, bridge_executable: Path | None, probe: str | None):
    """Run one isolated worker against one sandbox; return (spec, failure, secrets, marker).

    Readiness and probes share credentials, sandbox, worker, deadline, recovery and cleanup.
    """
    root = root.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    docker = None
    name = "keygen-readiness-" + uuid.uuid4().hex[:20]
    proc = None
    secrets = []
    spec = None
    failure = None
    marker = "native-history-" + uuid.uuid4().hex
    home = root / "isolated-host-home"
    stage = "configuration"
    try:
        spec = normalize_spec(load_json(spec_path), bridge_executable)
        if probe is not None and (probe != PROBE_LONG_GENERATION or spec["limits"] != PROBE_LIMITS):
            raise ValueError("Long-generation probe requires its exact step, wall and command bounds")
        stage = "credentials"
        credentials = run.worker_credentials(spec["config"], spec["model"])
        secrets = [value for key, value in credentials.items() if "KEY" in key or "TOKEN" in key]
        stage = "sandbox_setup"
        docker = run.docker_command()
        # Record intended ownership before allocation so partial setup also cleans up.
        run.write_json(root / "sandbox.json", {"container": name, "export_helper": name + "-files", "volume": name + "-work"})
        start_pilot_container(docker, spec["image"], name)
        run.write_json(root / "sandbox-preflight.json", sandbox_preflight(docker, name, spec["image"]))
        (home / "mini-config").mkdir(parents=True, mode=0o700)
        if probe is None:
            spec.update(docker=docker, container=name, system=SYSTEM, task=readiness_task(marker))
        else:
            spec.update(docker=docker, container=name, system=PROBE_SYSTEM, task=long_generation_task())
        stage = "native_worker"
        run.write_json(root / "pilot-spec.json", spec)
        with (home / "worker.private.log").open("wb") as log:
            proc = subprocess.Popen(
                [sys.executable, "-I", str(Path(__file__).resolve()), "--worker", str(root / "pilot-spec.json")],
                cwd=home, env=run.isolated_env(home, credentials), stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                code = proc.wait(timeout=spec["limits"]["wall_seconds"])
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
            if code:
                raise RuntimeError("Readiness worker exited unsuccessfully")
        if probe is None:
            stage = "artifact_export"
            run.shell(docker + ["pause", name])
            run.collect(docker, name, "/workspace/submission/.", root / "submission", 1024 * 1024)
    except BaseException as exc:
        # Error bodies can echo credentials or private controller paths. Category and
        # exception type are sufficient here; sanitized native traces retain evidence.
        failure = {"exception_type": type(exc).__name__, "category": stage + "_error"}
        if isinstance(exc, subprocess.TimeoutExpired):
            failure["category"] = "wall_time_exceeded"
        result_path = root / "worker-result.json"
        if result_path.exists():
            try:
                failure["worker_result"] = redact_credentials(load_json(result_path), secrets)
            except (OSError, ValueError):
                pass
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        cleanup = {"status": "not_allocated"}
        if docker is not None:
            try:
                run.remove_container(docker, name)
                cleanup = {"status": "removed", "container": name, "export_helper": name + "-files", "volume": name + "-work"}
            except Exception as exc:
                cleanup = {"status": "unconfirmed", "exception_type": type(exc).__name__}
                failure = {"category": "sandbox_cleanup_error", "exception_type": type(exc).__name__}
        run.write_json(root / "cleanup.json", cleanup)
        # Recover partial upstream history after a killed worker, then delete private
        # SDK logs/history. Neither artifact is ever exported without redaction.
        if home.exists():
            try:
                private = home / "trajectory.private.json"
                if private.exists():
                    run.write_json(root / "trajectory.json", redact_credentials(load_json(private), secrets))
                log = home / "worker.private.log"
                if log.exists():
                    with log.open("rb") as stream:
                        text = stream.read(MAX_ARTIFACT_BYTES).decode("utf-8", "replace")
                    (root / "worker.log").write_text(redact_credentials(text, secrets))
            except (OSError, ValueError) as exc:
                failure = failure or {"category": "trajectory_recovery_error", "exception_type": type(exc).__name__}
            finally:
                try:
                    shutil.rmtree(home)
                except OSError as exc:
                    failure = {"category": "private_artifact_cleanup_error", "exception_type": type(exc).__name__}
    return spec, failure, secrets, marker


def qualify(spec_path: Path, root: Path, bridge_executable: Path | None = None) -> dict:
    """Run one real pilot. Never overwrite an earlier outcome or use another route."""
    root = root.resolve()
    spec, failure, secrets, marker = execute_pilot(spec_path, root, bridge_executable, None)
    try:
        if failure is not None or spec is None:
            raise ValueError("Readiness pilot failed")
        if bridge_executable is not None and campaign.file_digest(bridge_executable) != spec["model"]["backend_provenance"]["bridge"]["executable_sha256"]:
            raise ValueError("OAuth bridge executable changed during qualification")
        payload = verify_pilot(spec, root, marker)
    except Exception as exc:
        failure = failure or {"category": "native_proof_rejected", "exception_type": type(exc).__name__}
        if (root / "worker-result.json").exists():
            try:
                failure["worker_result"] = redact_credentials(load_json(root / "worker-result.json"), secrets)
                category = failure["worker_result"].get("failure_category")
                if category:
                    failure["native_failure_category"] = category
            except (OSError, ValueError):
                pass
        try:
            trajectory = load_json(root / "trajectory.json") if (root / "trajectory.json").exists() else {"messages": []}
            records = transport_records(root)
        except (OSError, ValueError):
            trajectory, records = {"messages": []}, []
        payload = {"schema": "keygen-native-readiness-1", "status": "blocked", "recorded_at": timestamp(),
                   "blocker": failure, "trajectory": redact_credentials(trajectory, secrets),
                   "transport": redact_credentials(records, secrets), "cleanup": load_json(root / "cleanup.json")}
        if (root / "runtime-provenance.json").exists():
            try:
                payload["runtime_provenance"] = redact_credentials(load_json(root / "runtime-provenance.json"), secrets)
            except (OSError, ValueError):
                pass
        run.write_json(root / "blocker.json", payload)
        readiness = {"status": "blocked", "verified_at": None, "evidence": None, "blocker": failure}
    else:
        readiness = {"status": "verified", "verified_at": payload["verified_at"], "evidence": {
            "artifact_sha256": None, "payload": payload, "payload_sha256": digest(payload),
            "provider_received_settings_verified": False,
        }}
    run.write_json(root / "proof.json", redact_credentials(payload, secrets))
    if readiness["status"] == "verified":
        readiness["evidence"]["artifact_sha256"] = campaign.file_digest(root / "proof.json")
    run.write_json(root / "readiness.json", redact_credentials(readiness, secrets))
    return readiness


def _output_tokens(usage) -> int | None:
    # OpenAI completion/output tokens and Anthropic output tokens include reasoning/thinking.
    if isinstance(usage, dict):
        for key in ("output_tokens", "completion_tokens"):
            if type(usage.get(key)) is int:
                return usage[key]
    return None


def _reasoning_tokens(usage) -> int | None:
    if isinstance(usage, dict):
        for key in ("output_tokens_details", "completion_tokens_details"):
            details = usage.get(key)
            if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int:
                return details["reasoning_tokens"]
    return None


def classify_long_generation(records: list, worker_category: str | None = None,
                             controller_category: str | None = None,
                             expected_settings: dict | None = None) -> dict:
    """Decide the probe only from recorded wire exchanges and error categories, never file content.

    Every LiteLLM transport retry records a new request, so a request resent before any
    response means the earlier connection dropped even when the retry later succeeded. A
    content-filter block answers its send; the bounded re-send is not a transport retry.
    """
    exchanges, requests, anomaly, pending = [], [], None, False
    for record in records:
        if record.get("event") == "request":
            if pending:
                anomaly = anomaly or "transport_retry"
            pending = True
            requests.append(record)
        elif record.get("event") == "content_filter_block":
            pending = False
        elif record.get("event") == "response":
            pending = False
            if record.get("identity_status") == "gateway_error":
                anomaly = anomaly or "gateway_error"
                continue
            latency = record.get("latency_seconds")
            exchanges.append({
                "output_tokens": _output_tokens(record.get("usage")),
                "reasoning_tokens": _reasoning_tokens(record.get("usage")),
                "latency_seconds": latency if type(latency) in {int, float} else None,
                "identity_status": record.get("identity_status"),
            })
    if anomaly:
        category = anomaly
    elif pending:
        # The last request never answered: the worker's SDK error, or the outer deadline.
        category = worker_category or ("request_timeout" if controller_category == "wall_time_exceeded"
                                       else controller_category or "unanswered_request")
    else:
        category = worker_category or controller_category
    tokens = [exchange["output_tokens"] for exchange in exchanges if exchange["output_tokens"] is not None]
    latencies = [exchange["latency_seconds"] for exchange in exchanges if exchange["latency_seconds"] is not None]
    settings_match = bool(requests) and isinstance(expected_settings, dict) and all(
        all((record.get("settings") or {}).get(key) == value for key, value in expected_settings.items())
        for record in requests)
    long = any((exchange["output_tokens"] or 0) > PROBE_THRESHOLDS["output_tokens_gt"]
               or (exchange["latency_seconds"] or 0) > PROBE_THRESHOLDS["latency_seconds_gt"]
               for exchange in exchanges)
    if category in PROBE_FAIL_CATEGORIES:
        outcome = "fail"
    elif category in PROBE_INFRASTRUCTURE_CATEGORIES:
        outcome = "inconclusive"
    elif long and settings_match:
        outcome = "pass"
    else:
        outcome = "inconclusive"
        if long and category is None:
            category = "settings_mismatch"
    return {"outcome": outcome, "failure_category": category,
            "max_output_tokens_observed": max(tokens, default=None),
            "max_latency_seconds": max(latencies, default=None),
            "settings_match": settings_match, "exchanges": exchanges}


def long_generation_probe(spec_path: Path, root: Path, bridge_executable: Path | None = None) -> dict:
    """Run one long non-streaming generation probe. Writes probe.json, never readiness evidence."""
    root = root.resolve()
    spec, failure, secrets, _ = execute_pilot(spec_path, root, bridge_executable, PROBE_LONG_GENERATION)
    worker_result, records, provenance = None, [], None
    try:
        if (root / "worker-result.json").exists():
            worker_result = redact_credentials(load_json(root / "worker-result.json"), secrets)
        records = transport_records(root)
        if (root / "runtime-provenance.json").exists():
            provenance = load_json(root / "runtime-provenance.json")
        if (failure is None and bridge_executable is not None and campaign.file_digest(bridge_executable)
                != spec["model"]["backend_provenance"]["bridge"]["executable_sha256"]):
            failure = {"category": "bridge_provenance_changed"}
    except (OSError, ValueError) as exc:
        failure = failure or {"category": "probe_record_error", "exception_type": type(exc).__name__}
    model = spec["model"] if spec is not None else None
    worker_category = worker_result.get("failure_category") if isinstance(worker_result, dict) else None
    result = classify_long_generation(
        records, worker_category, failure["category"] if failure else None,
        model["effective_settings"]["expected_transmitted_generation"] if model else None)
    trajectory = root / "trajectory.json"
    payload = {
        "schema": PROBE_SCHEMA, "probe": PROBE_LONG_GENERATION, "recorded_at": timestamp(),
        "route": {key: model[key] for key in ("provider", "api", "base_url", "model", "response_model",
                                              "backend_provenance")} if model else None,
        "effective_settings": model["effective_settings"] if model else None,
        "limits": spec["limits"] if spec is not None else None,
        "outcome": result["outcome"],
        "max_output_tokens_observed": result["max_output_tokens_observed"],
        "max_latency_seconds": result["max_latency_seconds"],
        "failure_category": result["failure_category"],
        "thresholds": PROBE_THRESHOLDS, "policy": PROBE_POLICY,
        "settings_match": result["settings_match"], "exchanges": result["exchanges"],
        "readiness_evidence": False, "blocker": failure, "worker_result": worker_result,
        "transport": records, "runtime_provenance": provenance,
        "trajectory_sha256": campaign.file_digest(trajectory) if trajectory.exists() else None,
        "cleanup": load_json(root / "cleanup.json"),
        "payload_scope": "controller_to_endpoint",
    }
    run.write_json(root / "probe.json", redact_credentials(payload, secrets))
    return payload



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, help="Sanitized model/config/image pilot JSON")
    parser.add_argument("--out", type=Path, help="New proof output directory; never overwritten")
    parser.add_argument("--bridge-executable", type=Path, help="Actual OAuth bridge executable to hash")
    parser.add_argument("--probe", choices=[PROBE_LONG_GENERATION],
                        help="Run a transport probe instead of readiness; writes probe.json, never readiness.json")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        worker(args.worker)
        return 0
    if args.spec is None or args.out is None:
        parser.error("--spec and --out are required")
    if args.probe is not None:
        probe = long_generation_probe(args.spec.resolve(), args.out, args.bridge_executable)
        print(json.dumps({"outcome": probe["outcome"], "probe": str(args.out.resolve() / "probe.json")}))
        return 0 if probe["outcome"] == "pass" else 1
    readiness = qualify(args.spec.resolve(), args.out, args.bridge_executable)
    print(json.dumps({"status": readiness["status"], "proof": str(args.out.resolve() / "proof.json")}))
    return 0 if readiness["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
