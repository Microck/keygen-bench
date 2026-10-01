#!/usr/bin/env python3
"""Run frozen native mini-swe-agent campaigns in credential-free offline workspaces."""
from __future__ import annotations

import argparse
from array import array
import fcntl
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, ExitStack
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import selectors
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid
import wave

# Explicit project import only; also works with `python -I benchmark/run.py`.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from native_models import build_model, audit_messages, redact_credentials, classify_error, validate_url, _native, PROVIDERS, PROTOCOLS
import campaign

MINI_VERSION = "2.4.6"
FINISH = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
digest = campaign.digest
STOP = threading.Event()


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_config(path: Path) -> dict:
    return campaign.load(path)


def shell(cmd: list[str], timeout=30, check=True, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, timeout=timeout, check=check, capture_output=True, **kwargs)


def docker_command() -> list[str]:
    binary = shutil.which("docker")
    if not binary:
        raise RuntimeError("Docker is required")
    context = json.loads(shell([binary, "context", "inspect"]).stdout)[0]
    host = os.environ.get("DOCKER_HOST", context["Endpoints"]["docker"]["Host"])
    if not host.startswith(("unix://", "npipe://")):
        raise ValueError("Use a local Docker daemon; remote runners need a separate reviewed transport")
    return [binary, "--host", host]


def start_container(docker: list[str], image: str, name: str) -> str:
    # A private tmpfs-backed Docker volume is held by a read-only export helper.
    # docker cp cannot reliably read tmpfs; this also permits export while the agent is paused.
    volume = name + "-work"
    shell(docker + ["volume", "create", "--driver", "local", "--opt", "type=tmpfs",
                    "--opt", "device=tmpfs", "--opt", "o=size=512m,uid=10001,gid=10001", volume])
    mount = f"type=volume,source={volume},target=/export,readonly,volume-nocopy"
    shell(docker + ["create", "--name", name + "-files", "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "10001:10001",
                    "--memory", "256m", "--pids-limit", "32", "--mount", mount,
                    "--entrypoint", "/bin/sleep", image, "infinity"])
    shell(docker + ["start", name + "-files"])
    cmd = docker + ["create", "--name", name, "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "256",
                    "--cpus", "2", "--memory", "2g", "--memory-swap", "2g", "--user", "10001:10001"]
    cmd += ["--mount", f"type=volume,source={volume},target=/workspace,volume-nocopy"]
    for path, size in (("/tmp", "256m"), ("/home/agent", "16m")):
        cmd += ["--tmpfs", f"{path}:rw,nosuid,nodev,size={size},uid=10001,gid=10001"]
    shell(cmd + [image])
    shell(docker + ["start", name])
    for _ in range(50):
        result = shell(docker + ["exec", name, "test", "-S", "/tmp/keygen-ft2.sock"], check=False)
        if result.returncode == 0:
            return name
        time.sleep(0.2)
    raise RuntimeError("FT2 bridge did not become ready; inspect the native build/acceptance log")


def remove_container(docker: list[str], name: str) -> None:
    shell(docker + ["rm", "-f", name, name + "-files"], check=False)
    shell(docker + ["volume", "rm", name + "-work"], check=False)
    for kind, identity in (("container", name), ("container", name + "-files"), ("volume", name + "-work")):
        assert_removed(docker, kind, identity)


def assert_removed(docker: list[str], kind: str, identity: str) -> None:
    inspected = shell(docker + [kind, "inspect", identity], check=False)
    if inspected.returncode == 0:
        raise RuntimeError("Sandbox cleanup left a Docker resource allocated")
    if inspected.returncode != 1 or b"no such" not in inspected.stderr.lower():
        raise RuntimeError("Sandbox cleanup could not be confirmed")


class Sandbox:
    """mini-swe-agent Environment protocol, without profile or host mounts."""
    def __init__(self, docker: list[str], name: str, timeout: int):
        self.docker, self.name, self.timeout = docker, name, timeout
        self.config = {"image_container": name, "network": "none", "skills": False}

    def execute(self, action: dict, cwd="") -> dict:
        command = action["command"]
        if command.strip() == FINISH:
            self.submit()
        # Output is bounded by the container tmpfs; the host sees the first and last 10 KB with a
        # marker in between, so a long batch never hides its final error or save result.
        wrapper = (f"timeout --kill-after=2s {self.timeout}s /bin/bash --noprofile --norc -c "
                   + shlex.quote(command) + " > /tmp/keygen-action.log 2>&1; r=$?; "
                   + "n=$(stat -c %s /tmp/keygen-action.log); if [ \"$n\" -le 20000 ]; then cat /tmp/keygen-action.log; "
                   + "else head -c 10000 /tmp/keygen-action.log; printf '\\n[output truncated: %s bytes total]\\n' \"$n\"; "
                   + "tail -c 10000 /tmp/keygen-action.log; fi; exit $r")
        started = time.monotonic()
        result = shell(self.docker + ["exec", "-w", "/workspace", "-e", "BASH_ENV=/dev/null",
                       "-e", "ENV=/dev/null", self.name, "/bin/bash", "--noprofile", "--norc", "-c", wrapper],
                       timeout=self.timeout + 10, check=False)
        output = result.stdout.decode("utf-8", "replace")
        # mini's stock environments also treat a command whose first output line is the marker (exit 0)
        # as the submission, e.g. `cd /workspace && echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`. Nine
        # campaign attempts sent that form and were ignored; keep the two rules identical to mini's.
        lines = output.lstrip().splitlines()
        if result.returncode == 0 and lines and lines[0].strip() == FINISH.split(" ", 1)[1]:
            self.submit()
        # mini copies `extra` onto the tool message, so the sandbox time lands in the trajectory.
        return {"returncode": result.returncode, "output": output,
                "extra": {"duration_seconds": time.monotonic() - started}}

    @staticmethod
    def submit():
        from minisweagent.exceptions import Submitted
        raise Submitted({"role": "exit", "content": "Submitted",
                         "extra": {"exit_status": "Submitted", "submission": "submission/tune.xm"}})

    def get_template_vars(self, **kwargs) -> dict:
        return {}

    def serialize(self) -> dict:
        return {"info": {"sandbox": self.config}}


def safe_unpack(archive: Path, destination: Path, max_bytes: int) -> None:
    """Accept regular files/directories only; never restore untrusted modes or links."""
    total = 0
    seen = set()
    with tarfile.open(archive, "r:") as tf:
        for member in tf:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe archive path")
            if member.isdir():
                continue
            if not member.isfile() or not path.parts or str(path) in seen:
                raise ValueError("Only unique regular artifact files are accepted")
            seen.add(str(path))
            total += member.size
            if total > max_bytes or len(seen) > 4096:
                raise ValueError("Artifact limit exceeded")
            out = destination.joinpath(*path.parts)
            out.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(member) as source, out.open("xb") as target:
                shutil.copyfileobj(source, target)


def collect_submission(docker: list[str], name: str, run_dir: Path, max_bytes: int) -> dict:
    """Collect tune.xm on its own; optional extras follow only if the whole directory fits.

    A missing or irregular tune.xm raises ValueError (the model's fault). Extras that break
    the byte/file/regular-file limits or the copy deadline are dropped with a recorded note.
    """
    collect(docker, name, "/workspace/submission/tune.xm", run_dir / "submission", max_bytes)
    staging = run_dir / ".submission-extras"
    try:
        try:
            collect(docker, name, "/workspace/submission/.", staging, max_bytes)
        except (ValueError, TimeoutError) as exc:
            return {"status": "dropped", "reason": str(exc),
                    "note": "Optional submission extras broke the submission limits; tune.xm was collected alone"}
        moved = 0
        for path in sorted(staging.rglob("*")):
            relative = path.relative_to(staging)
            if path.is_file() and relative != Path("tune.xm"):
                target = run_dir / "submission" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                path.rename(target)
                moved += 1
        return {"status": "collected", "files": moved}
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def collect(docker: list[str], name: str, source: str, destination: Path, max_bytes: int) -> None:
    destination.mkdir(parents=True)
    with tempfile.TemporaryFile() as errors, tempfile.NamedTemporaryFile() as archive:
        # Stream with an explicit cap rather than trusting a tar's advertised size.
        from boat import workspace_export_command
        proc = subprocess.Popen(workspace_export_command(docker, name, source),
                                stdout=subprocess.PIPE, stderr=errors)
        total = 0
        try:
            deadline = time.monotonic() + 120
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise TimeoutError("Artifact copy timed out")
                    chunk = os.read(proc.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes + 4 * 1024 * 1024:
                        raise ValueError("Artifact archive exceeded byte limit")
                    archive.write(chunk)
            code = proc.wait(timeout=30)
            if code:
                errors.seek(0)
                if code in {1, 2} and b"No such file or directory" in errors.read(8192):
                    raise ValueError("Submission not found")
                raise RuntimeError("Artifact transport failed")
            archive.flush()
            safe_unpack(Path(archive.name), destination, max_bytes)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            proc.stdout.close()


def wav_info(path: Path) -> dict:
    count = square = full_scale = 0
    total = 0
    peak = 0
    h = hashlib.sha256()
    with wave.open(str(path), "rb") as wav:
        channels, width, rate, frames, compression, _ = wav.getparams()
        if width != 2 or channels not in (1, 2) or rate <= 0 or not frames or compression != "NONE":
            raise ValueError("Expected a nonempty mono/stereo 16-bit PCM render")
        while raw := wav.readframes(65536):
            h.update(raw)
            values = array("h", raw)
            if sys.byteorder != "little":
                values.byteswap()
            for v in values:
                count += 1
                square += v * v
                total += v
                peak = max(peak, abs(v))
                full_scale += v in (-32768, 32767)
        if count != frames * channels or not peak:
            raise ValueError("Truncated or entirely silent render")
    return {"duration_seconds": frames / rate, "rate": rate, "channels": channels,
            "pcm_sha256": h.hexdigest(), "peak": peak / 32768,
            "rms": math.sqrt(square / count) / 32768,
            "dc_offset": total / count / 32768, "full_scale_samples": full_scale,
            "quality_score": None, "note": "Technical observations, not aesthetic scores"}


def render(docker: list[str], image: str, run_dir: Path, config: dict) -> dict:
    xm = run_dir / "submission/tune.xm"
    if not xm.is_file() or not xm.read_bytes()[:17] == b"Extended Module: ":
        raise ValueError("Missing or unrecognized final tune.xm")
    name = "keygen-grade-" + uuid.uuid4().hex[:16]
    try:
        start_container(docker, image, name)
        shell(docker + ["exec", "-i", name, "python3", "-c",
                        "import sys;open('/workspace/input.xm','wb').write(sys.stdin.buffer.read())"], input=xm.read_bytes())
        for tool, arguments in (
                ("module_load", {"path": "/workspace/input.xm"}),
                ("module_info", {}),
                ("module_render", {"path": "/workspace/canonical.wav", "rate": 44100, "bits": 16, "amp": 8, "loops": 1})):
            result = shell(docker + ["exec", name, "ft2", "call", tool, json.dumps(arguments)],
                           timeout=config["limits"]["render_seconds"], check=False)
            (run_dir / (tool + ".json")).write_bytes(result.stdout)
            if result.returncode:
                # The bridge exits 1 when FT2 reports isError (e.g. a hand-written XM it cannot load):
                # that is the artifact's fault, so it is FAILED / render invalid, not an evaluation error.
                raise ValueError(f"FT2 {tool} rejected the module: " + result.stdout.decode("utf-8", "replace")[:200].strip())
        collect(docker, name, "/workspace/canonical.wav", run_dir / "canonical", config["limits"]["artifact_bytes"])
        return wav_info(run_dir / "canonical/canonical.wav")
    finally:
        remove_container(docker, name)


def module_facts(run_dir: Path) -> dict | str:
    """What FT2 reports about the loaded module (channels, patterns, instruments...), as saved by render()."""
    raw = json.loads((run_dir / "module_info.json").read_bytes())
    text = "".join(part.get("text", "") for part in raw.get("content", []))
    try:
        return json.loads(text)
    except ValueError:
        return text


def visualize(docker: list[str], image: str, run_dir: Path, config: dict, duration: float) -> dict:
    """Record the trusted FT2 GUI playing the collected module as a 4:3 video with its live audio.

    Presentation only: the graded audio stays canonical.wav. The video is capped by video_seconds.
    """
    seconds = min(math.ceil(duration), config["limits"]["video_seconds"])
    name = "keygen-video-" + uuid.uuid4().hex[:16]
    try:
        shell(docker + ["run", "-d", "--name", name, "--network", "none", "--read-only", "--cap-drop", "ALL",
                        "--security-opt", "no-new-privileges", "--user", "10001:10001", "--cpus", "2", "--memory", "2g",
                        "--pids-limit", "256", "--tmpfs", "/tmp:rw,nosuid,nodev,size=1g,uid=10001,gid=10001", image])
        shell(docker + ["exec", "-i", name, "sh", "-c", "cat > /tmp/input.xm"],
              input=(run_dir / "submission/tune.xm").read_bytes())
        capture = shell(docker + ["exec", name, "/bin/bash", "/opt/keygen/visualize.sh", "/tmp/input.xm", str(seconds), "/tmp/visualizer.mp4"],
                        timeout=seconds + config["limits"]["render_seconds"])
        (run_dir / "visualizer").mkdir()
        output = run_dir / "visualizer/visualizer.mp4"
        bounded_stream(docker + ["exec", name, "cat", "/tmp/visualizer.mp4"], output,
                       config["limits"]["artifact_bytes"], 120)
        return {"seconds": seconds, "bytes": output.stat().st_size, "sha256": campaign.file_digest(output),
                "capture": capture.stdout.decode("utf-8", "replace").strip()}
    finally:
        shell(docker + ["rm", "-f", name], check=False)
        assert_removed(docker, "container", name)


def bounded_stream(command: list[str], destination: Path, max_bytes: int, timeout: int) -> None:
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    total = 0
    try:
        deadline = time.monotonic() + timeout
        with destination.open("xb") as output, selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError("Binary export timed out")
                block = os.read(proc.stdout.fileno(), 65536)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    raise ValueError("Binary export exceeded byte limit")
                output.write(block)
        if proc.wait(timeout=10):
            raise RuntimeError("Binary transport failed")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()


def isolated_env(home: Path, credentials: dict) -> dict:
    reserved = {"PATH", "HOME", "XDG_CONFIG_HOME", "MSWEA_GLOBAL_CONFIG_DIR", "PYTHONNOUSERSITE"}
    if reserved.intersection(credentials):
        raise ValueError("Provider credentials cannot override worker identity/configuration")
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"), "MSWEA_GLOBAL_CONFIG_DIR": str(home / "mini-config"),
            "MSWEA_SILENT_STARTUP": "1", "PYTHONNOUSERSITE": "1", **credentials}


def credential_pool(config: dict, model: dict) -> dict:
    """Frozen member keys and per-key caps for a route, or just its single declared key."""
    name = model.get("api_key_env")
    pool = config.get("concurrency", {}).get("key_pools", {}).get(name)
    return dict(pool) if pool else {name: None}


def worker_credentials(config: dict, model: dict, key_name: str | None = None) -> dict:
    """Resolve credentials from SDK-validated frozen metadata without loading the SDK.

    A pooled route resolves only the one member key assigned to this attempt.
    """
    _native(config)  # retries are bounded LiteLLM transport retries; mini never retries
    provider, api = model.get("provider"), model.get("api")
    if provider not in PROVIDERS or api not in PROTOCOLS[provider]:
        raise ValueError("Credential resolution requires an approved native provider/protocol")
    validate_url(model.get("base_url"), provider, api)
    name = model.get("api_key_env")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*(?:KEY|TOKEN)", name):
        raise ValueError("Credential source must be a dedicated key/token environment variable")
    pool = credential_pool(config, model)
    if key_name is None and pool == {name: None}:
        key_name = name
    if key_name not in pool:
        raise ValueError("Pooled credential requires one assigned member key of the frozen pool")
    effective = model.get("effective_settings")
    if not isinstance(effective, dict) or not isinstance(effective.get("model_name"), str):
        raise ValueError("Credential resolution requires validated native constructor metadata")
    native_name = effective["model_name"]
    prefix = native_name.split("/", 1)[0]
    expected = "anthropic" if api == "messages" else "openai"
    if prefix != expected or native_name != f"{prefix}/{model.get('model')}":
        raise ValueError("Credential target differs from the validated native constructor")
    value = os.environ.get(key_name)
    if not value:
        raise ValueError(f"Missing credential environment variable {key_name}")
    return {f"{prefix.upper()}_API_KEY": value,
            "MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT": "1",
            "LITELLM_MODE": "PRODUCTION", "LITELLM_LOCAL_MODEL_COST_MAP": "True"}


# A sequence stops after these: later slots stay RESERVED instead of burning on a dead account
# or on a provider content filter that blocked every allowed send of one request.
SEQUENCE_STOPPING_FAILURES = {"QUOTA", "AUTH", "CONTENT_FILTER"}
# Anthropic's output content filter blocks a whole reply: HTTP 200 with stop_reason refusal
# (LiteLLM finish_reason "content_filter") and neither text nor tool call, or HTTP 400
# "Output blocked by content filtering policy". A blocked reply never enters native history,
# so the identical request is re-sent, at most CONTENT_FILTER_SENDS sends in total.
CONTENT_FILTER_SENDS = 3
CONTENT_FILTER_PROVIDERS = {"anthropic_oauth"}
CONTENT_FILTER_MARKER = "output blocked by content filtering policy"


class ContentFilterBlocked(RuntimeError):
    """The provider's content filter blocked every allowed send of one request."""


def content_filter_form(response=None, error=None) -> str | None:
    """"error" or "stop_reason" when a send was blocked outright by the content filter."""
    if error is not None:
        blocked = type(error).__name__ == "ContentPolicyViolationError" or CONTENT_FILTER_MARKER in str(error).lower()
        return "error" if blocked else None
    choices = getattr(response, "choices", None) or []
    if not choices or getattr(choices[0], "finish_reason", None) != "content_filter":
        return None
    message = choices[0].message
    return None if message.tool_calls or message.content else "stop_reason"


def bound_content_filter(native, model: dict, run_dir: Path):
    """Re-send a content-filter-blocked request on this native model instance, within bound.

    Each block is audited as a transport.jsonl ``content_filter_block`` record after its send.
    The instance keeps its original class, history handling and serialization.
    """
    if model["provider"] not in CONTENT_FILTER_PROVIDERS:
        return native
    send = native._query

    def query(messages, **kwargs):
        for attempt in range(1, CONTENT_FILTER_SENDS + 1):
            try:
                response = send(messages, **kwargs)
            except Exception as exc:
                form = content_filter_form(error=exc)
                if form is None:
                    raise
            else:
                form = content_filter_form(response)
                if form is None:
                    return response
            with (run_dir / "transport.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"event": "content_filter_block", "send": attempt, "form": form}) + "\n")
        raise ContentFilterBlocked(f"Content filter blocked all {CONTENT_FILTER_SENDS} sends of one request")

    native._query = query
    return native


def native_failure_category(exc, run_dir=None) -> str:
    return "content_filter" if isinstance(exc, ContentFilterBlocked) else classify_error(exc, run_dir)


def failure_category(exc, run_dir=None) -> str:
    category = native_failure_category(exc, run_dir)
    return {"authentication_error": "AUTH", "quota_or_rate_limit": "QUOTA", "content_filter": "CONTENT_FILTER",
            "transport_error": "TRANSPORT", "gateway_error": "PROTOCOL",
            "provider_request_error": "PROTOCOL", "native_model_error": "PROTOCOL"}.get(category, "INFRA")


def worker(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text())
    config, model, run_dir = spec["config"], spec["model"], spec_path.parent
    from minisweagent import __version__
    from minisweagent.agents.default import DefaultAgent
    if __version__ != MINI_VERSION:
        raise RuntimeError("mini-swe-agent version mismatch")
    target = "ANTHROPIC_API_KEY" if model["api"] == "messages" else "OPENAI_API_KEY"
    secrets = [os.environ[target]]
    agent = None
    try:
        agent = DefaultAgent(bound_content_filter(build_model(config, model, run_dir), model, run_dir),
                             Sandbox(spec["docker"], spec["container"], config["limits"]["command_seconds"]),
                             system_template="{{ frozen_system }}", instance_template="{{ task }}",
                             step_limit=config["limits"]["steps"], cost_limit=0,
                             wall_time_limit_seconds=config["limits"]["wall_seconds"],
                             output_path=run_dir / "isolated-host-home/trajectory.private.json")
        result = agent.run(task=config["prompts"]["task"], frozen_system=config["prompts"]["system"])
    except Exception as exc:
        result = {"exit_status": type(exc).__name__, "failure_category": failure_category(exc, run_dir),
                  "error": redact_credentials(str(exc), secrets)}
    finally:
        if agent is not None:
            write_json(run_dir / "trajectory.json", redact_credentials(agent.serialize(), secrets))
    write_json(run_dir / "worker-result.json", result)


def recover_trajectory(run_dir: Path, config: dict, model: dict, key_name: str | None = None) -> None:
    home = run_dir / "isolated-host-home"
    try:
        credentials = worker_credentials(config, model, key_name)
    except ValueError:
        return
    secrets = [v for k, v in credentials.items() if "KEY" in k or "TOKEN" in k]
    fingerprint = home / "credential-fingerprint.json"
    if not fingerprint.exists() or json.loads(fingerprint.read_text()) != [hashlib.sha256(value.encode()).hexdigest() for value in secrets]:
        return  # Never export private SDK history using a different or unavailable redaction credential.
    private = home / "trajectory.private.json"
    if private.exists():
        try:
            value = json.loads(private.read_text())
        except json.JSONDecodeError:
            pass
        else:
            write_json(run_dir / "trajectory.json", redact_credentials(value, secrets))
    log = home / "worker.private.log"
    if log.exists():
        with log.open("rb") as source:
            raw = source.read(16 * 1024 * 1024 + 1)
        text = (raw.decode("utf-8", "replace") if len(raw) <= 16 * 1024 * 1024
                else "[Worker log exceeded the 16 MiB export bound; full private log retained.]")
        (run_dir / "worker.log").write_text(redact_credentials(text, secrets))


def summarize(run_dir: Path, model: dict | None = None, *, interrupted=False) -> dict:
    totals = {"requests": 0, "failed_requests": 0, "usage_unknown": 0, "prompt_tokens": 0,
              "cached_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0,
              "model_seconds": 0.0, "sandbox_seconds": 0.0, "commands": 0,
              "in_flight_usage_unknown": bool(interrupted), "identity_mismatch": False,
              "transport_retries": 0, "content_filter_blocks": 0}
    path = run_dir / "trajectory.json"
    trajectory = {}
    if path.exists():
        try:
            trajectory = json.loads(path.read_text())
        except json.JSONDecodeError:
            totals["in_flight_usage_unknown"] = True
    messages = trajectory.get("messages", [])
    for message in messages:
        duration = (message.get("extra") or {}).get("duration_seconds")
        if message.get("role") == "tool" and duration is not None:
            totals["commands"] += 1
            totals["sandbox_seconds"] += duration
    records = audit_messages(messages, model) if model else []
    transport = run_dir / "transport.jsonl"
    requested = 0
    timed = 0
    totals["settings_mismatch"] = False
    expected_settings = (model or {}).get("effective_settings", {}).get("expected_transmitted_generation", {})
    if transport.exists():
        callbacks = []
        # mini never retries, so a request that follows an unanswered request is the SDK's
        # transport retry; each one fires the SDK's pre-call hook again.
        unanswered = False
        for line in transport.read_text().splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                totals["in_flight_usage_unknown"] = True
                continue
            requested += record.get("event") == "request"
            if record.get("event") == "request":
                totals["transport_retries"] += unanswered
                unanswered = True
                settings = record.get("settings") or {}
                totals["settings_mismatch"] |= any(settings.get(key) != value for key, value in expected_settings.items())
            if record.get("event") == "content_filter_block":
                # The block answered its send; the bounded re-send is not a transport retry.
                unanswered = False
                totals["content_filter_blocks"] += 1
            if record.get("event") == "response":
                unanswered = False
                callbacks.append(record)
                if record.get("latency_seconds") is not None:
                    totals["model_seconds"] += record["latency_seconds"]
                    timed += 1
        if len(callbacks) > len(records):
            records = callbacks
    totals["requests"] = max(len(records), requested, trajectory.get("info", {}).get("model_stats", {}).get("api_calls", 0))
    totals["settings_verified"] = requested > 0 and not totals["settings_mismatch"]
    if timed < totals["requests"] or interrupted:
        totals["model_seconds"] = None
    totals["identity_unverified"] = not records
    for record in records:
        usage = record.get("usage") or {}
        status = record.get("identity_status")
        totals["gateway_error"] = totals.get("gateway_error", False) or status == "gateway_error"
        totals["usage_unknown"] += not bool(usage)
        totals["failed_requests"] += status == "gateway_error"
        totals["identity_mismatch"] |= status == "identity_mismatch"
        totals["identity_unverified"] |= status == "identity_unverified"
        totals["prompt_tokens"] += usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        totals["completion_tokens"] += usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        totals["cached_tokens"] += (usage.get("prompt_tokens_details") or {}).get("cached_tokens", usage.get("cache_read_input_tokens", 0)) or 0
        totals["reasoning_tokens"] += (usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0) or 0
    totals["usage_unknown"] += max(0, totals["requests"] - len(records))
    if interrupted:
        totals["usage_unknown"] += 1
    return totals


def reserve(root: Path, model: dict, repetition: int, attempt_id: str, retry_of=None) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", attempt_id):
        raise ValueError("Invalid attempt ID")
    directory = root / attempt_id
    stage = root / (".reservation-" + uuid.uuid4().hex)
    stage.mkdir()
    try:
        write_json(stage / "status.json", {"status": "RESERVED", "attempt_id": attempt_id,
                   "model": model, "repetition": repetition, "retry_of": retry_of,
                   "reserved_at": time.time(), "eligible": False, "quality_score": None,
                   "totals": {"in_flight_usage_unknown": False}})
        lock = root / "campaign.lock.json"
        if lock.exists():
            campaign.publish(stage / "campaign.json", json.loads(lock.read_text()))
        with (root / ".reservation.lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            if directory.exists():
                raise FileExistsError(str(directory))
            stage.rename(directory)
        return directory
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def artifact_root(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("Artifact root must be explicitly absolute")
    root = path.resolve()
    legacy = (HERE.parent / "legacy").resolve()
    if root == legacy or legacy in root.parents:
        raise ValueError("Preserved legacy directories are never writable artifact roots")
    selected = ("", "")
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        left, right = line.split(" - ", 1)
        mount = left.split()[4].replace("\\040", " ")
        filesystem = right.split()[0]
        if (str(root) == mount or str(root).startswith(mount.rstrip("/") + "/")) and len(mount) > len(selected[0]):
            selected = (mount, filesystem)
    if not selected[0] or selected[1].startswith("fuse") or selected[1] in {"nfs", "nfs4", "cifs", "9p", "ceph", "glusterfs"}:
        raise ValueError("Live artifact reservations require a verified local filesystem, not cloud/FUSE/network storage")
    return root


@contextmanager
def slot(root: Path, name: str, count: int):
    directory = (Path(tempfile.gettempdir()) / f"keygen-benchmark-{os.getuid()}-resources"
                 if name in {"render", "video", "scoring"} else root / ".resource-locks")
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise RuntimeError("Unsafe resource-lock directory")
    handles = [(directory / f"{name}-{index}.lock").open("a") for index in range(count)]
    acquired = None
    try:
        while acquired is None:
            for handle in handles:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = handle
                    break
                except BlockingIOError:
                    pass
            if acquired is None:
                time.sleep(0.1)
        yield
    finally:
        if acquired is not None:
            fcntl.flock(acquired, fcntl.LOCK_UN)
        for handle in handles:
            handle.close()


@contextmanager
def credential_lease(root: Path, config: dict, model: dict):
    """Assign one key for the whole attempt: the least-loaded pool member under its cap.

    The attempt never switches keys, so native history and billing provenance stay
    with one credential. Only the key name is yielded and recorded.
    """
    pool = credential_pool(config, model)
    if pool == {model["api_key_env"]: None}:
        yield model["api_key_env"]
        return
    directory = root / ".resource-locks"
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise RuntimeError("Unsafe resource-lock directory")
    mutex = (directory / f"key-pool-{model['api_key_env']}.lock").open("a")
    handles = {name: [(directory / f"key-{name}-{index}.lock").open("a") for index in range(cap)]
               for name, cap in pool.items()}
    acquired = None
    try:
        while acquired is None:
            if STOP.is_set():
                raise KeyboardInterrupt()
            # All assignments probe under one pool mutex, so the load count is consistent.
            fcntl.flock(mutex, fcntl.LOCK_EX)
            try:
                free = {}
                for name, files in handles.items():
                    free[name] = []
                    for handle in files:
                        try:
                            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            free[name].append(handle)
                        except BlockingIOError:
                            pass
                available = [name for name in pool if free[name]]
                if available:
                    # Fewest active attempts first, then most headroom, then declared order.
                    name = min(available, key=lambda key: (pool[key] - len(free[key]), -len(free[key])))
                    acquired = (name, free[name][0])
                for files in free.values():
                    for handle in files:
                        if acquired is None or handle is not acquired[1]:
                            fcntl.flock(handle, fcntl.LOCK_UN)
            finally:
                fcntl.flock(mutex, fcntl.LOCK_UN)
            if acquired is None:
                time.sleep(0.1)
        yield acquired[0]
    finally:
        if acquired is not None:
            fcntl.flock(acquired[1], fcntl.LOCK_UN)
        for files in handles.values():
            for handle in files:
                handle.close()
        mutex.close()



def pace_boat_allocation(root: Path, interval_seconds: int) -> None:
    """Serialize this controller's starts before the VM startup deadline begins."""
    if not interval_seconds:
        return
    with (root / ".boat-allocation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = root / "boat-allocation.json"
        last = json.loads(path.read_text())["last_start_at"] if path.exists() else 0
        while True:
            if STOP.is_set():
                raise KeyboardInterrupt()
            delay = last + interval_seconds - time.time()
            if delay <= 0:
                break
            STOP.wait(min(delay, 0.25))
        write_json(path, {"last_start_at": time.time(), "interval_seconds": interval_seconds})


def run_one(root: Path, config: dict, model: dict, docker: list[str] | None, image: str, visualizer_image: str,
            repetition: int, attempt_id: str, store, retry_of=None) -> None:
    run_dir = root / attempt_id
    try:
        with slot(root, model["provider"], config["concurrency"]["providers"][model["provider"]]):
            if STOP.is_set():
                raise KeyboardInterrupt()
            with ExitStack() as stack:
                if config["transport"]["backend"] == "boat":
                    from boat import BoatSession
                    pace_boat_allocation(root, config["transport"]["boat"].get("allocation_interval_seconds", 0))
                    session = stack.enter_context(BoatSession(config["transport"], audit_dir=run_dir / "transport"))
                    docker = session.docker_prefix
                    if session.image_id("agent") != image or session.image_id("visualizer") != visualizer_image:
                        raise ValueError("Boat images differ from frozen campaign")
                    write_json(run_dir / "transport.json", {"boat_id": session.id, "images": {"agent": image, "visualizer": visualizer_image}})
                    required = config["limits"]["wall_seconds"] + 4 * config["limits"]["render_seconds"] + config["limits"]["video_seconds"] + 600
                    if session.archive_deadline - time.time() < required:
                        raise RuntimeError("Boat delivered TTL cannot cover the frozen runtime and export budgets")
                _run_one(root, config, model, docker, image, visualizer_image, repetition, attempt_id, store, retry_of)
    except BaseException as exc:
        status = json.loads((run_dir / "status.json").read_text())
        status.update(status="INTERRUPTED" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "INFRA_ERROR",
                      failure_category="INFRA", model_failure=False, eligible=False,
                      finished_at=time.time(), error=type(exc).__name__)
        write_json(run_dir / "status.json", status)
        raise
    finally:
        finalize_attempt(run_dir, store)


def attempt_succeeded(status: dict, profile: dict | None, *, finalization_error=False) -> bool:
    """Select only a rendered, eligible attempt with a completed eligible evaluation."""
    if (status.get("status") != "RENDERED_UNSCORED" or status.get("render") != "ok"
            or status.get("eligible") is not True or status.get("failure_category")
            or status.get("model_failure") or status.get("error") or finalization_error
            or status.get("finalization_error") or status.get("cleanup_error")
            or status.get("trajectory_recovery_error")):
        return False
    termination = status.get("termination") or {}
    if isinstance(termination, dict) and (termination.get("failure_category") or termination.get("error")):
        return False
    totals = status.get("totals") or {}
    if any(totals.get(key) for key in ("identity_mismatch", "identity_unverified", "settings_mismatch", "gateway_error")):
        return False
    return bool(isinstance(profile, dict) and profile.get("eligible") is True
                and profile.get("evaluation_status") == "evaluated"
                and profile.get("cacheable") is True
                and profile.get("status") == status.get("status")
                and profile.get("model") == (status.get("model") or {}).get("model")
                and not any(profile.get(key) for key in
                            ("evaluation_error", "run_failure_category", "model_failure", "provenance_error", "structure_error")))


def run_model_sequence(root: Path, config: dict, model: dict, docker: list[str] | None,
                       image: str, visualizer_image: str, store) -> dict:
    """Run fresh reserved slots in ordinal order; leave interrupted slots for explicit recovery.

    A QUOTA or AUTH attempt is an account fault, not the model's, and a CONTENT_FILTER attempt
    is a provider block of every allowed send: the sequence stops and the later slots stay
    RESERVED for `recover` plus an explicit `retry` once the cause is fixed.
    """
    slots = [f"{model['id']}-rep-{ordinal}" for ordinal in range(1, config["max_attempts"] + 1)]
    for ordinal, attempt_id in enumerate(slots, 1):
        status = json.loads((root / attempt_id / "status.json").read_text())
        if (status.get("status") != "RESERVED" or status.get("model") != model
                or status.get("repetition") != ordinal or status.get("retry_of") is not None):
            raise ValueError("Model sequences require fresh matching reserved slots; never repeat existing attempts")
    selected = None
    attempted = []
    errors = []
    stopped = None
    for ordinal, attempt_id in enumerate(slots, 1):
        directory = root / attempt_id
        if stopped is not None:
            break
        if selected is not None:
            status = json.loads((directory / "status.json").read_text())
            status.update(status="SKIPPED_AFTER_SUCCESS", selected_attempt_id=selected,
                          eligible=False, quality_score=None, totals=None, finished_at=time.time())
            write_json(directory / "status.json", status)
            continue
        if STOP.is_set():
            raise KeyboardInterrupt()
        attempted.append(attempt_id)
        invocation_error = False
        try:
            run_one(root, config, model, docker, image, visualizer_image, ordinal, attempt_id, store)
        except Exception as exc:
            errors.append({"attempt_id": attempt_id, "error": type(exc).__name__})
            invocation_error = True
        status = json.loads((directory / "status.json").read_text())
        profile_path = directory / "profile.json"
        try:
            profile = json.loads(profile_path.read_text()) if profile_path.exists() else None
        except (OSError, ValueError):
            profile = None
        if not invocation_error and attempt_succeeded(
                status, profile, finalization_error=(directory / "finalization-error.json").exists()):
            selected = attempt_id
        elif status.get("failure_category") in SEQUENCE_STOPPING_FAILURES:
            stopped = {"attempt_id": attempt_id, "failure_category": status["failure_category"]}
    summary = {"model_id": model["id"], "max_attempts": config["max_attempts"],
               "attempt_selection": config["policies"]["attempt_selection"], "slots": slots,
               "attempted": attempted, "selected_attempt_id": selected,
               "skipped": slots[len(attempted):] if selected else [], "errors": errors,
               "stopped_after": stopped, "reserved": slots[len(attempted):] if stopped else []}
    write_json(root / f"{model['id']}-attempts.json", summary)
    return summary


def _run_one(root: Path, config: dict, model: dict, docker: list[str], image: str, visualizer_image: str,
             repetition: int, attempt_id: str, store, retry_of=None) -> None:
    with slot(root, "worker", config["concurrency"]["workers"]):
        run_dir = root / attempt_id
        name = "keygen-create-" + uuid.uuid4().hex[:16]
        started = time.time()
        result = {"status": "INFRA_ERROR", "attempt_id": attempt_id, "repetition": repetition,
                  "retry_of": retry_of, "model": model, "eligible": False, "quality_score": None,
                  "started_at": started, "collection": "not_attempted", "render": "not_attempted",
                  "failure_category": "INFRA", "model_failure": False, "container": name}
        proc = None
        interrupted = False
        lease = ExitStack()
        try:
            if STOP.is_set():
                raise KeyboardInterrupt()
            memory_admission(config)
            store.preflight(root, parallelism=config["concurrency"]["workers"],
                            peak_per_attempt=config["storage"]["peak_bytes_per_attempt"])
            # One key for the whole model attempt; released once the worker has exited.
            result["credential_env"] = lease.enter_context(credential_lease(root, config, model))
            start_container(docker, image, name)
            home = run_dir / "isolated-host-home"
            (home / "mini-config").mkdir(parents=True)
            spec = {"config": config, "model": model, "docker": docker, "container": name}
            write_json(run_dir / "spec.json", spec)
            result["status"] = "RUNNING"
            write_json(run_dir / "status.json", result)
            credentials = worker_credentials(config, model, result["credential_env"])
            write_json(home / "credential-fingerprint.json",
                       [hashlib.sha256(value.encode()).hexdigest() for key, value in credentials.items() if "KEY" in key or "TOKEN" in key])
            env = isolated_env(home, credentials)
            with (home / "worker.private.log").open("wb") as log:
                proc = subprocess.Popen([sys.executable, "-I", str(HERE / "run.py"), "--worker", str(run_dir / "spec.json")],
                                        cwd=home, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    deadline = time.monotonic() + config["limits"]["wall_seconds"]
                    while proc.poll() is None:
                        if STOP.is_set():
                            raise KeyboardInterrupt()
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(proc.args, config["limits"]["wall_seconds"])
                        try:
                            proc.wait(timeout=min(0.5, remaining))
                        except subprocess.TimeoutExpired:
                            pass
                except subprocess.TimeoutExpired:
                    interrupted = True
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    result["termination"] = {"exit_status": "WallTimeExceeded"}
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            result["worker_exit_code"] = proc.returncode
            recover_trajectory(run_dir, config, model, result["credential_env"])
            lease.close()
            worker_result = run_dir / "worker-result.json"
            if worker_result.exists():
                result["termination"] = json.loads(worker_result.read_text())
            else:
                interrupted = True
                result.setdefault("termination", {"exit_status": "WorkerExitedWithoutResult"})
            termination = result["termination"]
            fault = termination.get("failure_category")
            if interrupted and termination.get("exit_status") != "WallTimeExceeded":
                fault = fault or "INFRA"
            if fault:
                result.update(status=f"{fault}_ERROR", failure_category=fault, error=termination.get("error"))
            elif proc.returncode and not interrupted:
                result.update(status="INFRA_ERROR", error="Worker exited without a successful result")
                fault = "INFRA"
            shell(docker + ["pause", name])
            try:
                result["submission_extras"] = collect_submission(docker, name, run_dir, config["limits"]["artifact_bytes"])
                result["collection"] = "ok"
            except ValueError as exc:
                result["collection"] = "missing"
                if not fault:
                    result.update(status="MODEL_FAILED", failure_category="MODEL", model_failure=True, error=str(exc))
                return
            remove_container(docker, name)
            try:
                with slot(root, "render", config["concurrency"]["render"]):
                    result["audio"] = render(docker, image, run_dir, config)
                result["module"] = module_facts(run_dir)
                result["artifact_sha256"] = hashlib.sha256((run_dir / "submission/tune.xm").read_bytes()).hexdigest()
                result["render"] = "ok"
                if not fault:
                    result.update(status="RENDERED_UNSCORED", failure_category=None, eligible=True)
                try:
                    with slot(root, "video", config["concurrency"]["video"]):
                        result["video"] = visualize(docker, visualizer_image, run_dir, config, result["audio"]["duration_seconds"])
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    result["video"] = {"error": type(exc).__name__}
            except (ValueError, wave.Error, EOFError) as exc:
                result.update(status="MODEL_FAILED" if not fault else result["status"], render="invalid",
                              failure_category=fault or "MODEL", model_failure=not bool(fault), error=str(exc))
            except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
                result.update(status="EVALUATION_ERROR", render="error", failure_category="EVAL", eligible=False, error=type(exc).__name__)
        except BaseException as exc:
            interrupted |= isinstance(exc, (KeyboardInterrupt, SystemExit))
            result.update(status="INTERRUPTED" if interrupted else "INFRA_ERROR",
                          failure_category="INFRA", eligible=False, error=type(exc).__name__)
            if interrupted:
                raise
        finally:
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            lease.close()
            try:
                remove_container(docker, name)
            except Exception as exc:
                result["cleanup_error"] = type(exc).__name__
                result.update(status="INFRA_ERROR", failure_category="INFRA", eligible=False)
            try:
                recover_trajectory(run_dir, config, model, result.get("credential_env"))
            except Exception as exc:
                result["trajectory_recovery_error"] = type(exc).__name__
            result["finished_at"] = time.time()
            result["wall_seconds"] = result["finished_at"] - started
            result["totals"] = summarize(run_dir, model, interrupted=interrupted)
            if result["totals"]["identity_mismatch"]:
                result.update(status="IDENTITY_MISMATCH", failure_category="PROTOCOL", eligible=False,
                              model_failure=False, identity_verified=False)
            elif result["totals"]["settings_mismatch"]:
                result.update(status="SETTINGS_MISMATCH", failure_category="PROTOCOL", eligible=False,
                              model_failure=False, settings_verified=False)
            elif result["totals"].get("gateway_error") and result["failure_category"] not in SEQUENCE_STOPPING_FAILURES:
                result.update(status="PROTOCOL_ERROR", failure_category="PROTOCOL", eligible=False, model_failure=False)
            elif result["totals"].get("identity_unverified") and result["eligible"]:
                result.update(status="IDENTITY_UNVERIFIED", failure_category="PROTOCOL", eligible=False,
                              identity_verified=False, model_failure=False)
            write_json(run_dir / "status.json", result)


def finalize_attempt(run_dir: Path, store) -> None:
    from score import profile_attempt
    try:
        with slot(run_dir.parent, "scoring", 1):
            profile_attempt(run_dir)
        metadata = store.archive_attempt(run_dir)
        write_json(run_dir / "archive.json", metadata)
        if store.evict_after_archive:
            store.evict(run_dir, metadata)
    except BaseException as exc:
        interrupted = isinstance(exc, (KeyboardInterrupt, SystemExit))
        error = {"failure_category": "INFRA" if interrupted else "EVAL", "error": type(exc).__name__}
        write_json(run_dir / "finalization-error.json", error)
        status = json.loads((run_dir / "status.json").read_text())
        status.update(status="INTERRUPTED" if interrupted else "FINALIZATION_ERROR",
                      failure_category=error["failure_category"], eligible=False, finalization_error=error)
        write_json(run_dir / "status.json", status)
        raise


def fingerprint(config: dict, docker: list[str]) -> dict:
    if importlib.metadata.version("mini-swe-agent") != MINI_VERSION:
        raise ValueError(f"Install mini-swe-agent=={MINI_VERSION}")
    image, visualizer = (json.loads(shell(docker + ["image", "inspect", config[key]]).stdout)[0]
                         for key in ("image", "visualizer_image"))
    if image["Id"] != config["image"] or visualizer["Id"] != config["visualizer_image"]:
        raise ValueError("Execution image differs from the frozen image ID")
    return {"config_sha256": digest(config), "campaign": config, "image_id": image["Id"], "visualizer_image_id": visualizer["Id"],
            "architecture": image["Architecture"], "docker_server": shell(docker + ["version", "--format", "{{.Server.Version}}"]).stdout.decode().strip()}


def lock_campaign(path: Path, snapshot: dict) -> None:
    campaign.publish(path, {"sha256": digest(snapshot), "snapshot": snapshot})


@contextmanager
def controller_lock(root: Path):
    with (root / ".controller.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Campaign controller is already running; no concurrent restart")
        yield


def recover_attempts(root: Path, config: dict, docker: list[str]) -> list[str]:
    recovered = []
    for path in sorted(root.glob("*/status.json")):
        if path.parent.name.startswith("."):
            continue
        status = json.loads(path.read_text())
        if status.get("status") not in {"RESERVED", "RUNNING"}:
            continue
        model = status.get("model")
        if model:
            recover_trajectory(path.parent, config, model, status.get("credential_env"))
        if status.get("container"):
            if config["transport"]["backend"] == "boat":
                from boat import BoatSession
                metadata_path = path.parent / "transport.json"
                if not metadata_path.exists():
                    raise RuntimeError("Boat recovery requires the original recorded VM identity")
                metadata = json.loads(metadata_path.read_text())
                transport = json.loads(json.dumps(config["transport"]))
                transport["boat"].update(mode="resume", id=metadata["boat_id"])
                transport["boat"].pop("image_bundle", None)
                transport["boat"].pop("snapshot", None)
                with BoatSession(transport, audit_dir=path.parent / "recovery-transport") as session:
                    remove_container(session.docker_prefix, status["container"])
            else:
                remove_container(docker, status["container"])
        status.update(status="INTERRUPTED", eligible=False, failure_category="INFRA", model_failure=False,
                      finished_at=time.time(), totals=summarize(path.parent, model, interrupted=True))
        write_json(path, status)
        recovered.append(path.parent.name)
    return recovered


def memory_admission(config: dict) -> dict:
    """Require the full frozen pool reserve both at launch and before each attempt.

    MemAvailable excludes swap. Local workers reserve 512 MiB controller plus
    a 2 GiB sandbox cap each; Boat workers reserve only 512 MiB controller each.
    Render, video and scoring allocations are not included in this admission gate.
    """
    available = None
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            available = int(line.split()[1]) * 1024
            break
    workers = config["concurrency"]["workers"]
    controller = workers * 512 * 1024 * 1024
    sandbox = workers * 2 * 1024**3 if config["transport"]["backend"] == "local" else 0
    required = controller + sandbox
    diagnostic = {"available_bytes": available, "required_bytes": required, "controller_reserve_bytes": controller,
                  "local_sandbox_caps_bytes": sandbox, "swap_counted": False, "workers": workers}
    if available is None or available < required:
        raise RuntimeError("Insufficient controller RAM for frozen concurrency: " + json.dumps(diagnostic, sort_keys=True))
    return diagnostic


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "run", "recover", "retry"])
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="absolute local artifact root; never a cloud/FUSE mount")
    parser.add_argument("--workers", type=int, help="must match the frozen worker bound")
    parser.add_argument("--retry-of")
    parser.add_argument("--retry-id")
    args = parser.parse_args()
    def terminate(signum, frame):
        STOP.set()
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, terminate)
    config = (campaign.read_manifest(args.campaign.resolve()) if args.command == "recover"
              else load_config(args.campaign.resolve()))
    root = artifact_root(args.out)
    if args.workers is not None and args.workers != config["concurrency"]["workers"]:
        raise ValueError("Worker count differs from the frozen campaign")
    root.mkdir(parents=True, exist_ok=True)
    if args.command == "recover":
        with controller_lock(root):
            frozen = json.loads((root / "campaign.lock.json").read_text())
            if (digest(frozen["snapshot"]) != frozen["sha256"]
                    or frozen["snapshot"]["config_sha256"] != digest(config)):
                raise ValueError("Recovery campaign does not match the immutable original cohort")
            docker = docker_command() if config["transport"]["backend"] == "local" else None
            print(json.dumps({"interrupted_attempts": recover_attempts(root, config, docker), "rerun": False}))
        return
    memory = memory_admission(config)
    from artifacts import ArtifactStore
    store = ArtifactStore(config["storage"])
    store.preflight(root, parallelism=config["concurrency"]["workers"],
                    peak_per_attempt=config["storage"]["peak_bytes_per_attempt"])
    for model in config["models"]:
        # Fail all readiness/auth configuration gates, for every pooled key, before any request.
        for key_name in credential_pool(config, model):
            worker_credentials(config, model, key_name)
    with controller_lock(root):
        transport_status = None
        if config["transport"]["backend"] == "boat":
            from boat import doctor
            transport_status = doctor(config["transport"])
            docker = None
            snapshot = {"config_sha256": digest(config), "campaign": config,
                        "image_id": config["image"], "visualizer_image_id": config["visualizer_image"],
                        "runtime_images_verified": "per_attempt"}
        else:
            docker = docker_command()
            snapshot = fingerprint(config, docker)
        if args.command == "doctor":
            print(json.dumps({"status": "configuration_checked", **snapshot,
                              "effective_models": [model["effective_settings"] for model in config["models"]],
                              "memory": memory, "transport": transport_status,
                              "note": "No model request sent. Native protocol readiness evidence is a separate launch gate."}, indent=2))
            return
        lock_campaign(root / "campaign.lock.json", snapshot)
        attempts = [(model, ordinal, f"{model['id']}-rep-{ordinal}", None)
                    for model in config["models"] for ordinal in range(1, config["max_attempts"] + 1)]
        if args.command == "retry":
            if not args.retry_of or not args.retry_id or args.retry_of == args.retry_id:
                raise ValueError("Retry requires an original terminal attempt and an explicit distinct retry ID")
            if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", value) for value in (args.retry_of, args.retry_id)):
                raise ValueError("Retry identities must be safe explicit attempt IDs")
            original = json.loads((root / args.retry_of / "status.json").read_text())
            if original["status"] in {"RESERVED", "RUNNING"}:
                raise ValueError("Recover the interrupted attempt before requesting a separate retry")
            if original["status"] == "SKIPPED_AFTER_SUCCESS":
                raise ValueError("Unused slots after success are not retryable attempts")
            if original.get("model") not in config["models"]:
                raise ValueError("Retry model does not belong to this immutable campaign")
            attempts = [(original["model"], original["repetition"], args.retry_id, args.retry_of)]
            campaign.publish(root / f"retry-{args.retry_id}.json", {"campaign_sha256": digest(config),
                             "retry_of": args.retry_of, "attempt_id": args.retry_id})
        else:
            existing = [attempt_id for _, _, attempt_id, _ in attempts if (root / attempt_id).exists()]
            if existing:
                raise ValueError("Attempts already reserved; never silently skip/rerun. Use recover or an explicit separate retry: " + ", ".join(existing))
        for model, repetition, attempt_id, retry_of in attempts:
            reserve(root, model, repetition, attempt_id, retry_of)
        errors = []
        pool = ThreadPoolExecutor(max_workers=config["concurrency"]["workers"])
        if args.command == "retry":
            futures = [pool.submit(run_one, root, config, model, docker, snapshot["image_id"],
                       snapshot["visualizer_image_id"], repetition, attempt_id, store, retry_of)
                       for model, repetition, attempt_id, retry_of in attempts]
        else:
            futures = [pool.submit(run_model_sequence, root, config, model, docker, snapshot["image_id"],
                       snapshot["visualizer_image_id"], store) for model in config["models"]]
        stopped = []
        try:
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if isinstance(result, dict):
                        errors.extend(error["error"] for error in result["errors"])
                        if result.get("stopped_after"):
                            stopped.append({"model_id": result["model_id"], **result["stopped_after"],
                                            "reserved": result["reserved"]})
                except Exception as exc:
                    errors.append(type(exc).__name__)
        except KeyboardInterrupt:
            STOP.set()
            raise
        finally:
            pool.shutdown(wait=True)
        if errors:
            raise RuntimeError("Campaign finalization failed: " + ", ".join(errors))
        print("Model sequences completed, stopping after first eligible success or three attempts. Unused slots are SKIPPED_AFTER_SUCCESS. Scores are auxiliary diagnostics, not aesthetic rankings.")
        if stopped:
            print(json.dumps({"stopped_on_account_failure": stopped,
                              "note": "QUOTA/AUTH/CONTENT_FILTER are infrastructure faults; RESERVED slots are unused. Fix the cause, then recover and retry explicitly."}))


if __name__ == "__main__":
    main()
