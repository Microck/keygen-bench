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
from secrets import choice as secure_choice
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import campaign
import run
from native_models import BRIDGE_PROVIDERS, MAX_TRANSPORT_RETRIES, build_probe_model, credential_target, digest, redact_credentials

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
DEFAULT_LIMITS = {"steps": 5, "wall_seconds": 180, "command_seconds": 15}
# The read-back marker the pilot must write and test. Random words, not hex: at effort "max",
# Anthropic's input classifier refused claude-opus-5 6/6 when the task carried a random 32-hex
# string (it resembles a secret) and accepted six random words 24/24 (2026-10-05).
MARKER_WORDS = (
    "amber", "anchor", "aspen", "banjo", "beacon", "birch", "bramble", "breeze", "brook", "cactus",
    "canyon", "cedar", "cello", "cinder", "clover", "comet", "copper", "coral", "cricket", "dahlia",
    "delta", "ember", "fable", "falcon", "fern", "fjord", "garnet", "glacier", "harbor", "hazel",
    "heron", "indigo", "island", "jasper", "juniper", "kelp", "lantern", "lemon", "lilac", "lotus",
    "maple", "marble", "meadow", "mesa", "nectar", "nutmeg", "oasis", "olive", "orchid", "otter",
    "pebble", "pepper", "pine", "plum", "quartz", "quill", "raven", "river", "saffron", "summit",
    "thistle", "tulip", "velvet", "willow",
)


def readiness_marker() -> str:
    """A fresh unguessable marker (64^6, ~36 bits) made of plain words."""
    return "native-history-" + "-".join(secure_choice(MARKER_WORDS) for _ in range(6))

# Neutral wording (2026-10-05): at effort "max", Anthropic's input classifier refused claude-opus-5
# 5/5 on the former "native protocol readiness agent ... Never access credentials, host paths, or
# network" wording before generating any token, and accepted this wording 10/10. The sandbox
# (offline container, no credentials, no host mounts) enforces the same limits regardless of text.
SYSTEM = (
    "You are a careful shell assistant completing a short file task. Use only the declared bash function "
    "tool inside the workspace. A reply may contain one or several bash tool calls; every tool call in a "
    "reply runs in order. Work only inside the workspace directory. Follow the task's turns in order and "
    "wait for each turn's executed tool results before the next turn."
)


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
    if model["provider"] in BRIDGE_PROVIDERS:
        if (not isinstance(bridge, dict) or set(bridge) != {"implementation", "version", "executable_sha256"}
                or not isinstance(bridge["implementation"], str) or not bridge["implementation"]
                or not isinstance(bridge["version"], str) or not bridge["version"]
                or not re.fullmatch(r"[a-f0-9]{64}", bridge["executable_sha256"])):
            raise ValueError("Bridge qualification requires exact executable provenance")
        if bridge_executable is None or campaign.file_digest(bridge_executable) != bridge["executable_sha256"]:
            raise ValueError("Actual credential bridge executable does not match declared provenance")
    elif bridge is not None or bridge_executable is not None:
        raise ValueError("Direct routes must not introduce a bridge")
    # Do not carry a previous proof or a pretend verified flag into the bootstrap.
    model = {key: value for key, value in model.items() if key not in {"readiness", "effective_settings"}}
    model["readiness"] = {"status": "qualification", "evidence": None, "verified_at": None}
    effective = campaign.normalize_native(config, [model])[0]
    model["effective_settings"] = effective
    return {"model": model, "config": config, "image": spec["image"], "limits": dict(limits)}


def worker_failure_record(exc: Exception, run_dir: Path, secrets: list[str] | tuple[str, ...] = ()) -> dict:
    """Keep actionable HTTP metadata without saving provider response bodies."""
    result = {"exit_status": type(exc).__name__, "failure_category": run.native_failure_category(exc, run_dir)}
    status = getattr(exc, "status_code", None)
    if type(status) is int and 100 <= status <= 599:
        result["http_status"] = status
    code = getattr(exc, "code", None)
    if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", code):
        safe_code = redact_credentials(code, secrets)
        if safe_code == code:
            result["provider_error_code"] = code
    return result


def worker(spec_path: Path) -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_ARTIFACT_BYTES, MAX_ARTIFACT_BYTES))
    spec = load_json(spec_path)
    root, model = spec_path.parent, spec["model"]
    target = credential_target(model)
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
        result = worker_failure_record(exc, root, secrets)
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


def execute_pilot(spec_path: Path, root: Path, bridge_executable: Path | None):
    """Run one isolated worker and return its spec, failure, secrets and marker."""
    root = root.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    docker = None
    name = "keygen-readiness-" + uuid.uuid4().hex[:20]
    proc = None
    secrets = []
    spec = None
    failure = None
    marker = readiness_marker()
    home = root / "isolated-host-home"
    stage = "configuration"
    try:
        spec = normalize_spec(load_json(spec_path), bridge_executable)
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
        spec.update(docker=docker, container=name, system=SYSTEM, task=readiness_task(marker))
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
        stage = "artifact_export"
        run.shell(docker + ["pause", name])
        run.collect(docker, name, "/workspace/submission/.", root / "submission", 1024 * 1024)
    except BaseException as exc:
        # Provider bodies can echo credentials or private paths. Keep only the redacted
        # status/code summary and failure category in the private evidence.
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
    spec, failure, secrets, marker = execute_pilot(spec_path, root, bridge_executable)
    try:
        if failure is not None or spec is None:
            raise ValueError("Readiness pilot failed")
        if bridge_executable is not None and campaign.file_digest(bridge_executable) != spec["model"]["backend_provenance"]["bridge"]["executable_sha256"]:
            raise ValueError("Credential bridge executable changed during qualification")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, help="Sanitized model/config/image pilot JSON")
    parser.add_argument("--out", type=Path, help="New proof output directory; never overwritten")
    parser.add_argument("--bridge-executable", type=Path, help="Actual credential bridge executable to hash")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        worker(args.worker)
        return 0
    if args.spec is None or args.out is None:
        parser.error("--spec and --out are required")
    readiness = qualify(args.spec.resolve(), args.out, args.bridge_executable)
    print(json.dumps({"status": readiness["status"], "proof": str(args.out.resolve() / "proof.json")}))
    return 0 if readiness["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
