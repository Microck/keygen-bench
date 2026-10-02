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


def controller_resource_dir() -> Path:
    """Lock and gate directory shared by every campaign root this user runs on this controller."""
    directory = Path(tempfile.gettempdir()) / f"keygen-benchmark-{os.getuid()}-resources"
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise RuntimeError("Unsafe resource-lock directory")
    return directory


@contextmanager
def slot(root: Path, name: str, count: int):
    if name in {"render", "video", "scoring"}:
        directory = controller_resource_dir()
    else:
        directory = root / ".resource-locks"
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


class KeyLease:
    """One held pool-member cap lock. release() is idempotent and may run on any thread."""

    def __init__(self, name: str, handle):
        self.name, self._handle, self._lock = name, handle, threading.Lock()

    def release(self) -> None:
        with self._lock:
            if self._handle is not None:
                fcntl.flock(self._handle, fcntl.LOCK_UN)
                self._handle.close()
                self._handle = None


def key_lock_paths(model: dict, pool: dict) -> tuple[Path, dict]:
    """Pool mutex and per-member cap locks. They are controller-wide: every campaign on this
    controller counts against the same per-key cap, so a key never serves more attempts at once."""
    directory = controller_resource_dir()
    return (directory / f"key-pool-{model['api_key_env']}.lock",
            {name: [directory / f"key-{name}-{index}.lock" for index in range(cap)] for name, cap in pool.items()})


def try_key_lease(config: dict, model: dict, name: str) -> KeyLease | None:
    """Take one free cap slot of pool member `name` without waiting; None when it is full."""
    mutex_path, paths = key_lock_paths(model, credential_pool(config, model))
    with mutex_path.open("a") as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX)
        for path in paths[name]:
            handle = path.open("a")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return KeyLease(name, handle)
            except BlockingIOError:
                handle.close()
    return None


@contextmanager
def credential_lease(config: dict, model: dict, held: KeyLease | None = None):
    """Assign one key for the whole attempt: the least-loaded pool member under its cap.

    The attempt never switches keys, so native history and billing provenance stay
    with one credential. Only the key name is yielded and recorded. A rerun queue passes the
    lease it already took for a key it probed (`held`) and keeps it until it has classified the
    attempt's outcome, so a key that just hit its usage limit never serves the next attempt.
    """
    if held is not None:
        yield held.name
        return
    pool = credential_pool(config, model)
    if pool == {model["api_key_env"]: None}:
        yield model["api_key_env"]
        return
    mutex_path, paths = key_lock_paths(model, pool)
    mutex = mutex_path.open("a")
    handles = {name: [path.open("a") for path in files] for name, files in paths.items()}
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
    """Serialize this controller's starts before the VM startup deadline begins.

    The lock and the last start are controller-wide, so campaigns running side by side on one
    controller share the interval; the campaign root keeps its own record of its latest start.
    """
    if not interval_seconds:
        return
    shared = controller_resource_dir()
    with (shared / "boat-allocation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        paths = (root / "boat-allocation.json", shared / "boat-allocation.json")
        last = max([json.loads(path.read_text())["last_start_at"] for path in paths if path.exists()], default=0)
        while True:
            if STOP.is_set():
                raise KeyboardInterrupt()
            delay = last + interval_seconds - time.time()
            if delay <= 0:
                break
            STOP.wait(min(delay, 0.25))
        record = {"last_start_at": time.time(), "interval_seconds": interval_seconds}
        for path in paths:
            write_json(path, record)


def run_one(root: Path, config: dict, model: dict, docker: list[str] | None, image: str, visualizer_image: str,
            repetition: int, attempt_id: str, store, retry_of=None, key_lease: KeyLease | None = None) -> None:
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
                _run_one(root, config, model, docker, image, visualizer_image, repetition, attempt_id, store, retry_of, key_lease)
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

    First success: later slots become SKIPPED_AFTER_SUCCESS after the first eligible success.
    Independent repetitions: every declared slot runs regardless of earlier outcomes.
    In both, a QUOTA or AUTH attempt is an account fault, not the model's, and a CONTENT_FILTER
    attempt is a provider block of every allowed send: the sequence stops and the later slots stay
    RESERVED for `recover` plus an explicit `retry` once the cause is fixed.
    """
    independent = config["policies"]["attempt_selection"] == campaign.INDEPENDENT
    ordinals = campaign.repetitions(config)
    slots = [f"{model['id']}-rep-{ordinal}" for ordinal in ordinals]
    for ordinal, attempt_id in zip(ordinals, slots):
        status = json.loads((root / attempt_id / "status.json").read_text())
        if (status.get("status") != "RESERVED" or status.get("model") != model
                or status.get("repetition") != ordinal or status.get("retry_of") is not None):
            raise ValueError("Model sequences require fresh matching reserved slots; never repeat existing attempts")
    selected = None
    eligible = []
    attempted = []
    errors = []
    stopped = None
    for ordinal, attempt_id in zip(ordinals, slots):
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
            eligible.append(attempt_id)
            selected = None if independent else attempt_id
        elif status.get("failure_category") in SEQUENCE_STOPPING_FAILURES:
            stopped = {"attempt_id": attempt_id, "failure_category": status["failure_category"]}
    summary = {"model_id": model["id"], "max_attempts": config["max_attempts"],
               "attempt_selection": config["policies"]["attempt_selection"], "slots": slots,
               "attempted": attempted, "selected_attempt_id": selected, "eligible": eligible,
               "skipped": slots[len(attempted):] if selected else [], "errors": errors,
               "stopped_after": stopped, "reserved": slots[len(attempted):] if stopped else []}
    write_json(root / f"{model['id']}-attempts.json", summary)
    return summary


# A probe reply naming any of these is a provider usage limit or an exhausted credential pool:
# wait and re-probe instead of starting an attempt that would only record a QUOTA failure.
PROBE_WAIT_MARKERS = ("rate limit", "rate_limit", "ratelimit", "too many requests", "quota", "usage limit",
                      "usage_limit", "auth_unavailable", "no auth available", "cooldown", "cooling down",
                      "exhausted", "insufficient account funds", "gousagelimiterror", "positive credit balance")
PROBE_TEXT = "Reply with OK."


def probe_provider(model: dict, credential: str, timeout: float = 120) -> dict:
    """Send ONE minimal request on the model's own route; return only its category and HTTP status.

    "ok": HTTP 200. "quota": HTTP 429 or a usage-limit / exhausted-credential reply. "unavailable":
    any other failure (bridge, tunnel or provider outage). Response bodies are never retained.
    """
    import urllib.error
    import urllib.request
    if model["api"] == "messages":
        path, body = "/messages", {"model": model["model"], "max_tokens": 16,
                                   "messages": [{"role": "user", "content": PROBE_TEXT}]}
    elif model["api"] == "responses":
        path, body = "/responses", {"model": model["model"], "input": PROBE_TEXT, "max_output_tokens": 16, "store": False}
    else:
        path, body = "/chat/completions", {"model": model["model"], "max_tokens": 16,
                                           "messages": [{"role": "user", "content": PROBE_TEXT}]}
    # Go rejects urllib's default User-Agent (HTTP 403) and unrouted requests without a session.
    headers = {"Authorization": f"Bearer {credential}", "Content-Type": "application/json",
               "User-Agent": "keygen-benchmark/queue-probe-1.0"}
    if model["api"] == "messages":
        headers.update({"x-api-key": credential, "anthropic-version": "2023-06-01"})
    if model["provider"] == "go":
        headers["x-opencode-session"] = uuid.uuid4().hex
    request = urllib.request.Request(model["base_url"].rstrip("/") + path, data=json.dumps(body).encode(),
                                     headers=headers, method="POST")
    started = time.time()
    result = {"model": model["model"], "provider": model["provider"], "at": started, "http_status": None}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            json.loads(response.read())
            result.update(category="ok", http_status=response.status)
    except urllib.error.HTTPError as exc:
        text = exc.read(65536).decode("utf-8", "replace").lower()
        waiting = exc.code == 429 or any(marker in text for marker in PROBE_WAIT_MARKERS)
        result.update(category="quota" if waiting else "unavailable", http_status=exc.code)
        limit = re.search(r'"limitname"\s*:\s*"([a-z0-9_-]{1,32})"', text)
        if waiting and limit:
            result["limit_name"] = limit.group(1)  # e.g. Go's "weekly" window; never the body itself
    except Exception as exc:
        result.update(category="unavailable", error=type(exc).__name__)
    result["seconds"] = round(time.time() - started, 2)
    return result


# A key gate a probe or a finished attempt verified stays open this long without fresh evidence
# (run.py queue --key-gate-fresh-seconds; 0 probes the key before every start).
KEY_GATE_FRESH_SECONDS = 3600
# A key whose provider reports its weekly usage window spent re-probes only this often.
WEEKLY_LIMIT_BACKOFF_SECONDS = 6 * 3600


def quota_wait(probe_interval: int, limit_text: str) -> int:
    """Seconds a usage-limited key waits before its next probe: longer for a weekly window."""
    return max(probe_interval, WEEKLY_LIMIT_BACKOFF_SECONDS) if "weekly" in limit_text.lower() else probe_interval


def process_start_ticks(pid: int) -> str | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (OSError, IndexError):
        return None


class KeyGates:
    """Usage gates of pooled credentials, one record per key name in a controller-wide file.

    Every rerun queue on this controller reads and writes the same records, so a key that a probe
    or an attempt found usage-limited stays closed for every campaign until its next probe, and a
    key is probed once before use rather than once per campaign. Records hold key names, probe
    categories and HTTP statuses only, never credential values or response bodies.
    """

    def __init__(self):
        directory = controller_resource_dir()
        self.path, self.lock_path = directory / "key-gates.json", directory / "key-gates.lock"

    @contextmanager
    def edit(self):
        with self.lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            gates = json.loads(self.path.read_text()) if self.path.exists() else {}
            yield gates
            write_json(self.path, gates)

    def read(self) -> dict:
        with self.edit() as gates:
            return json.loads(json.dumps(gates))

    @staticmethod
    def state(gate: dict, now: float, fresh: int = KEY_GATE_FRESH_SECONDS) -> str:
        """"open": usable without a probe; "wait": closed until next_probe_at; "probe": probe first."""
        if fresh > 0 and gate.get("open") and now - (gate.get("verified_at") or 0) <= fresh:
            return "open"
        if not gate.get("open") and now < (gate.get("next_probe_at") or 0):
            return "wait"
        return "probe"


class RerunQueue:
    """Run a rerun queue campaign (campaign.QUEUE): every planned ordinal until it holds a sample.

    An ordinal runs when its origin never started, failed for a non-model reason, or does not exist.
    Each attempt of an ordinal's chain runs only after the previous one ended rerunnable
    (report.rerunnable, the report's own classification); a scored outcome or a model failure ends
    the chain. Reruns are separate attempts with status.retry_of and a retry record.

    Every non-pooled model is gated on its own: before its work starts, and again after any of its
    attempts ends in a non-model failure, ONE minimal probe request on that model must succeed, so
    one model's usage limit (for example a separately metered model) never blocks another model of
    the same provider. A usage-limit reply re-probes after `probe_interval` seconds, any other probe
    failure after `retry_interval`; no attempt is spent while the gate is closed. Models in `holds`
    (operator deferral) are never probed or started; their ordinals stay pending ("held"), and a
    later `run.py queue` without the hold resumes them. Before each start the Boat balance must keep
    `boat_reserve` seconds after the worst case (frozen TTL) of every running attempt and the new
    one; otherwise the queue starts nothing more, lets running attempts finish and stops.

    A plan entry may carry frozen `reruns` an earlier queue campaign ran after the origin; the chain
    then continues after the last of them (report.entry_next_index).

    A pooled route (concurrency.key_pools) is gated per key instead (KeyGates): an attempt starts
    only on a pool member with a free controller-wide cap slot whose gate is open, probing that
    key with its own credential first when its last verification is older than `key_gate_fresh`
    seconds (0: before every start). An attempt that ends QUOTA closes only its key
    for `probe_interval`; any other non-model failure makes its key re-probe before its next use.

    Queues running side by side on one controller publish their waiting ordinals and running
    attempts (queue-demand-<campaign>.json beside the key gates): a queue never starts a provider's
    repetition while another live queue still waits to start a lower repetition on that provider,
    and the Boat reserve counts every live queue's running attempts.
    """

    def __init__(self, root: Path, config: dict, docker, snapshot: dict, store, *,
                 probe_interval: int, retry_interval: int, boat_reserve: int, probe=probe_provider, balance=None,
                 holds=(), key_gate_fresh: int = KEY_GATE_FRESH_SECONDS):
        import report
        self.report = report
        self.root, self.config, self.docker, self.snapshot, self.store = root, config, docker, snapshot, store
        self.probe_interval, self.retry_interval, self.boat_reserve = probe_interval, retry_interval, boat_reserve
        self.key_gate_fresh = key_gate_fresh
        self.probe = probe
        self.balance = balance or self.boat_balance
        self.policies = config["policies"]
        self.cap = self.policies["max_queue_attempts"]
        self.models = {model["id"]: model for model in config["models"]}
        order = {model["id"]: index for index, model in enumerate(config["models"])}
        self.holds = set(holds)
        if not self.holds <= set(self.models):
            raise ValueError("Held models must belong to this campaign")
        self.ordinals = sorted(((model_id, entry["repetition"], entry)
                                for model_id, entries in self.policies["plan"].items() for entry in entries
                                if report.entry_reruns(entry)),
                               key=lambda item: (item[1], order[item[0]]))
        _, self.config_hash, self.fingerprint = report.open_cohort(root, root / "campaign.lock.json")
        self.cohort = report.campaign_cohort(config)
        self.gates = {model_id: {"open": False, "next_probe_at": 0.0, "last_probe": None}
                      for model_id in {model_id for model_id, _, _ in self.ordinals}}
        self.key_gates = KeyGates()
        self.demand_path = controller_resource_dir() / f"queue-demand-{config['campaign_id']}.json"
        self.inflight = {}
        self.leases = {}
        self.stopped = None

    def pooled(self, model: dict) -> bool:
        return credential_pool(self.config, model) != {model["api_key_env"]: None}

    def event(self, **record) -> None:
        with (self.root / "queue-events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": time.time(), **record}, allow_nan=False) + "\n")

    def boat_balance(self) -> int | None:
        if self.config["transport"]["backend"] != "boat":
            return None
        from boat import doctor
        try:
            return doctor(self.config["transport"])["remaining_seconds"]
        except Exception as exc:
            self.event(event="boat_balance_error", error=type(exc).__name__)
            return 0

    def chain(self, model_id: str, repetition: int, entry: dict) -> dict:
        """Where one ordinal stands: next attempt to start, held, in flight, done or exhausted."""
        model = self.models[model_id]
        links = self.report.entry_links(entry)
        first = index = self.report.entry_next_index(entry)
        previous = links[-1]["attempt_id"] if links else None
        started = 0
        while True:
            attempt_id = self.report.queue_chain_id(model_id, repetition, index)
            if attempt_id in self.inflight:
                return {"state": "running", "attempt_id": attempt_id}
            if not (self.root / attempt_id).exists():
                if started >= self.cap:
                    return {"state": "exhausted", "attempt_id": previous}
                if model_id in self.holds:
                    return {"state": "held", "attempt_id": attempt_id}
                from_link = index == first and bool(links)
                kind = "fresh" if previous is None else (
                    "continuation" if from_link and links[-1]["outcome"] == "UNATTEMPTED" else "retry")
                return {"state": "next", "attempt_id": attempt_id, "retry_of": previous, "kind": kind,
                        "previous_campaign_id": None if previous is None else (
                            links[-1]["campaign_id"] if from_link else self.config["campaign_id"])}
            started += 1
            row = self.report.attempt_row(self.root, attempt_id, (model, repetition), self.fingerprint,
                                          self.config_hash, self.cohort, retry_of=previous)
            if row["status"] in {"RESERVED", "RUNNING"}:
                raise RuntimeError(f"{attempt_id}: recover the interrupted attempt before resuming the queue")
            if not self.report.rerunnable(row):
                return {"state": "done", "attempt_id": attempt_id, "outcome": row["outcome"],
                        "failure_category": row["failure_category"]}
            previous = attempt_id
            index += 1

    def snapshot_state(self, status: str) -> dict:
        chains = [{"model_id": model_id, "repetition": repetition, **self.chain(model_id, repetition, entry)}
                  for model_id, repetition, entry in self.ordinals]
        state = {"status": status, "updated_at": time.time(), "campaign_sha256": self.config_hash,
                 "gates": self.gates, "key_gates": self.key_gates.read(),
                 "inflight": {attempt_id: item[3] for attempt_id, item in sorted(self.inflight.items())},
                 "stopped": self.stopped, "ordinals": chains}
        write_json(self.root / "queue-state.json", state)
        return state

    def open_gate(self, model: dict) -> bool:
        gate = self.gates[model["id"]]
        if gate["open"]:
            return True
        if time.time() < gate["next_probe_at"]:
            return False
        credential = os.environ.get(model["api_key_env"], "")
        result = self.probe(model, credential)
        gate["last_probe"] = result
        self.event(event="probe", **result)
        if result["category"] == "ok":
            gate["open"] = True
        else:
            gate["next_probe_at"] = time.time() + (self.probe_interval if result["category"] == "quota" else self.retry_interval)
        return gate["open"]

    def open_key(self, model: dict) -> KeyLease | None:
        """A held cap slot of the first pool member, in declared order, whose gate is open.

        A member whose gate needs a probe is probed with ONE request on its own credential while
        its slot is held, so no other queue on this controller probes or uses it meanwhile.
        """
        for name in credential_pool(self.config, model):
            lease = try_key_lease(self.config, model, name)
            if lease is None:
                continue
            with self.key_gates.edit() as gates:
                state = KeyGates.state(gates.get(name, {}), time.time(), self.key_gate_fresh)
            if state == "open":
                return lease
            if state == "probe":
                result = {**self.probe(model, os.environ.get(name, "")), "key": name}
                self.event(event="probe", **result)
                now = time.time()
                with self.key_gates.edit() as gates:
                    if result["category"] == "ok":
                        gates[name] = {"open": True, "verified_at": now, "next_probe_at": 0.0,
                                       "last_probe": result, "campaign_id": self.config["campaign_id"]}
                    else:
                        wait = (quota_wait(self.probe_interval, str(result.get("limit_name") or ""))
                                if result["category"] == "quota" else self.retry_interval)
                        gates[name] = {"open": False, "verified_at": None, "next_probe_at": now + wait,
                                       "last_probe": result, "campaign_id": self.config["campaign_id"]}
                if result["category"] == "ok":
                    return lease
            lease.release()
        return None

    def close_key(self, name: str, attempt_id: str, category: str | None, error: str = "") -> None:
        """Record what a finished attempt showed about its key."""
        now = time.time()
        wait = quota_wait(self.probe_interval, error)
        with self.key_gates.edit() as gates:
            gate = gates.get(name, {})
            if category == "QUOTA":
                # The key's usage window is spent: it waits before its next probe (6 h for a weekly window).
                gates[name] = {**gate, "open": False, "verified_at": None, "next_probe_at": now + wait,
                               "closed_by": attempt_id, "campaign_id": self.config["campaign_id"],
                               "limit_name": "weekly" if "weekly" in error.lower() else None}
            elif category in campaign.NON_MODEL_FAILURES:
                gates[name] = {**gate, "open": False, "verified_at": None, "next_probe_at": 0.0,
                               "closed_by": attempt_id, "campaign_id": self.config["campaign_id"]}
            elif gate.get("open"):
                gates[name] = {**gate, "verified_at": now}  # the key served a whole attempt
        if category == "QUOTA":
            self.event(event="key_waiting", key=name, attempt_id=attempt_id, next_probe_in=wait)

    def others(self) -> list[dict]:
        """Demand records of the other live queues on this controller."""
        records = []
        for path in self.demand_path.parent.glob("queue-demand-*.json"):
            if path == self.demand_path:
                continue
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if record.get("pid") != os.getpid() and process_start_ticks(record.get("pid", 0)) == record.get("start_ticks"):
                records.append(record)
        return records

    def publish_demand(self, waiting: list) -> None:
        lowest = {}
        if not self.stopped:
            for model, repetition, _ in waiting:
                lowest[model["provider"]] = min(repetition, lowest.get(model["provider"], repetition))
        write_json(self.demand_path, {"pid": os.getpid(), "start_ticks": process_start_ticks(os.getpid()),
                                      "campaign_id": self.config["campaign_id"], "updated_at": time.time(),
                                      "waiting": lowest, "inflight_started": [item[2] for item in self.inflight.values()]})

    def reserve_allows_start(self, others: list[dict] = ()) -> bool:
        remaining = self.balance()
        if remaining is None:
            return True
        ttl = self.config["transport"]["boat"]["ttl_seconds"]
        now = time.time()
        started = [item[2] for item in self.inflight.values()] + [value for record in others for value in record["inflight_started"]]
        running = sum(max(0, ttl - (now - value)) for value in started)
        projected = remaining - running - ttl
        if projected < self.boat_reserve:
            self.stopped = {"reason": "boat_reserve", "remaining_seconds": remaining, "projected_seconds": projected,
                            "reserve_seconds": self.boat_reserve}
            self.event(event="stop_starting", **self.stopped)
            return False
        return True

    def start(self, pool, model: dict, repetition: int, step: dict, key_lease: KeyLease | None = None) -> None:
        attempt_id, previous = step["attempt_id"], step["retry_of"]
        try:
            if previous is not None:
                campaign.publish(self.root / f"retry-{attempt_id}.json",
                                 {"campaign_sha256": self.config_hash, "attempt_id": attempt_id, "model_id": model["id"],
                                  "repetition": repetition, "kind": step["kind"], "retry_of": previous,
                                  "retry_of_campaign_id": step["previous_campaign_id"]})
            reserve(self.root, model, repetition, attempt_id, previous)
            extra = {} if key_lease is None else {"key_lease": key_lease}
            future = pool.submit(run_one, self.root, self.config, model, self.docker, self.snapshot["image_id"],
                                 self.snapshot["visualizer_image_id"], repetition, attempt_id, self.store, previous, **extra)
        except BaseException:
            if key_lease is not None:
                key_lease.release()
            raise
        key = None if key_lease is None else key_lease.name
        if key_lease is not None:
            self.leases[attempt_id] = key_lease  # held until reap() has classified the outcome
        self.inflight[attempt_id] = (future, model["provider"], time.time(), key)
        self.event(event="start", attempt_id=attempt_id, kind=step["kind"], retry_of=previous, key=key)

    def reap(self) -> list[str]:
        errors = []
        for attempt_id, (future, provider, _, key) in list(self.inflight.items()):
            if not future.done():
                continue
            del self.inflight[attempt_id]
            if future.exception() is not None:
                errors.append(type(future.exception()).__name__)
            status = json.loads((self.root / attempt_id / "status.json").read_text())
            self.event(event="finish", attempt_id=attempt_id, status=status.get("status"),
                       failure_category=status.get("failure_category"), key=key)
            if key is not None:
                self.close_key(key, attempt_id, status.get("failure_category"), str(status.get("error") or ""))
                self.leases.pop(attempt_id).release()
            elif status.get("failure_category") in campaign.NON_MODEL_FAILURES:
                # Re-verify this model with one probe before its next start.
                self.gates[status["model"]["id"]].update(open=False, next_probe_at=0.0)
        return errors

    def run(self) -> dict:
        concurrency = self.config["concurrency"]
        for model_id, repetition, entry in self.ordinals:
            self.chain(model_id, repetition, entry)  # refuse unrecovered attempts before any request
        errors = []
        pool = ThreadPoolExecutor(max_workers=concurrency["workers"])
        try:
            while True:
                if STOP.is_set():
                    raise KeyboardInterrupt()
                errors.extend(self.reap())
                waiting = []
                for model_id, repetition, entry in self.ordinals:
                    step = self.chain(model_id, repetition, entry)
                    if step["state"] == "next":
                        waiting.append((self.models[model_id], repetition, step))
                if (not waiting or self.stopped) and not self.inflight:
                    break
                self.publish_demand(waiting)
                others = self.others()
                closed = set()  # one gate decision per provider or model per pass keeps admission in ordinal order
                for model, repetition, step in waiting:
                    if self.stopped or len(self.inflight) >= concurrency["workers"]:
                        break
                    provider = model["provider"]
                    if (provider in closed or model["id"] in closed
                            or sum(item[1] == provider for item in self.inflight.values()) >= concurrency["providers"][provider]):
                        continue
                    if any(record["waiting"].get(provider, repetition) < repetition for record in others):
                        closed.add(provider)  # another queue here still waits to start a lower repetition
                        continue
                    key_lease = None
                    if self.pooled(model):
                        key_lease = self.open_key(model)
                        if key_lease is None:
                            closed.add(provider)
                            continue
                    elif not self.open_gate(model):
                        closed.add(model["id"])  # a closed model gate never blocks another model
                        continue
                    if not self.reserve_allows_start(others):
                        if key_lease is not None:
                            key_lease.release()
                        break
                    self.start(pool, model, repetition, step, key_lease)
                self.publish_demand(waiting)
                self.snapshot_state("RUNNING")
                STOP.wait(5)
        except KeyboardInterrupt:
            STOP.set()
            raise
        finally:
            pool.shutdown(wait=True)
            self.demand_path.unlink(missing_ok=True)
            for lease in self.leases.values():
                lease.release()  # only interrupted or failed runs leave leases here
        errors.extend(self.reap())
        final = self.snapshot_state("STOPPED_BOAT_RESERVE" if self.stopped else "COMPLETED")
        if not self.stopped and any(item["state"] == "held" for item in final["ordinals"]):
            final = self.snapshot_state("COMPLETED_WITH_HOLDS")
        return {**final, "errors": errors}



def _run_one(root: Path, config: dict, model: dict, docker: list[str], image: str, visualizer_image: str,
             repetition: int, attempt_id: str, store, retry_of=None, key_lease: KeyLease | None = None) -> None:
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
            result["credential_env"] = lease.enter_context(credential_lease(config, model, key_lease))
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
    except BaseException as exc:
        interrupted = isinstance(exc, (KeyboardInterrupt, SystemExit))
        error = {"failure_category": "INFRA" if interrupted else "EVAL", "error": type(exc).__name__}
        write_json(run_dir / "finalization-error.json", error)
        status = json.loads((run_dir / "status.json").read_text())
        status.update(status="INTERRUPTED" if interrupted else "FINALIZATION_ERROR",
                      failure_category=error["failure_category"], eligible=False, finalization_error=error)
        write_json(run_dir / "status.json", status)
        raise
    export_attempt(run_dir, store)


def export_attempt(run_dir: Path, store) -> bool:
    """Export an evaluated attempt; an export failure never changes the attempt's outcome.

    status.json and profile.json stay as evaluated, local files are kept, and the failure is
    recorded in archive-error.json so `export_deferred` can retry the export later.
    """
    try:
        metadata = store.archive_attempt(run_dir)
        write_json(run_dir / "archive.json", metadata)
        if store.evict_after_archive:
            store.evict(run_dir, metadata)
    except BaseException as exc:
        write_json(run_dir / "archive-error.json", {"error": type(exc).__name__, "local_files_retained": True,
                                                    "recorded_at": time.time()})
        if not isinstance(exc, Exception):
            raise
        return False
    return True


def export_deferred(root: Path, store) -> list[str]:
    """Retry every export that failed after evaluation; return the attempts still unarchived."""
    return [path.parent.name for path in sorted(root.glob("*/archive-error.json"))
            if not (path.parent / "archive.json").exists() and not export_attempt(path.parent, store)]


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
    parser.add_argument("command", choices=["doctor", "run", "recover", "retry", "queue"])
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="absolute local artifact root; never a cloud/FUSE mount")
    parser.add_argument("--workers", type=int, help="must match the frozen worker bound")
    parser.add_argument("--retry-of")
    parser.add_argument("--retry-id")
    parser.add_argument("--probe-interval", type=int, default=1800,
                        help="queue: seconds before re-probing a provider whose probe hit a usage limit")
    parser.add_argument("--retry-interval", type=int, default=300,
                        help="queue: seconds before re-probing after any other probe failure")
    parser.add_argument("--boat-reserve-seconds", type=int, default=36000,
                        help="queue: Boat balance every start must leave after all running attempts' worst case")
    parser.add_argument("--hold", action="append", default=[], metavar="MODEL_ID",
                        help="queue: operator deferral; never probe or start this model's ordinals (they stay pending)")
    parser.add_argument("--key-gate-fresh-seconds", type=int, default=KEY_GATE_FRESH_SECONDS,
                        help="queue: seconds a verified pooled key starts attempts without a new probe; 0 probes before every start")
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
    queue = config["policies"].get("attempt_selection") == campaign.QUEUE
    if args.command in {"run", "retry", "queue"} and queue != (args.command == "queue"):
        raise ValueError("A rerun queue campaign runs only with the queue command, and the queue command only runs one")
    if args.command == "recover":
        with controller_lock(root):
            frozen = json.loads((root / "campaign.lock.json").read_text())
            if (digest(frozen["snapshot"]) != frozen["sha256"]
                    or frozen["snapshot"]["config_sha256"] != digest(config)):
                raise ValueError("Recovery campaign does not match the immutable original cohort")
            docker = docker_command() if config["transport"]["backend"] == "local" else None
            from artifacts import ArtifactStore
            print(json.dumps({"interrupted_attempts": recover_attempts(root, config, docker), "rerun": False,
                              "unarchived_attempts": export_deferred(root, ArtifactStore(config["storage"]))}))
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
        if args.command == "queue":
            if (min(args.probe_interval, args.retry_interval) < 60 or args.boat_reserve_seconds < 0
                    or args.key_gate_fresh_seconds < 0):
                raise ValueError("Probe intervals are at least 60 s; the Boat reserve and key gate freshness are non-negative")
            summary = RerunQueue(root, config, docker, snapshot, store, probe_interval=args.probe_interval,
                                 retry_interval=args.retry_interval, boat_reserve=args.boat_reserve_seconds,
                                 holds=args.hold, key_gate_fresh=args.key_gate_fresh_seconds).run()
            unarchived = export_deferred(root, store)
            print(json.dumps({"status": summary["status"], "stopped": summary["stopped"], "errors": summary["errors"],
                              "unarchived_attempts": unarchived,
                              "ordinals": [{key: item.get(key) for key in ("model_id", "repetition", "state", "attempt_id")}
                                           for item in summary["ordinals"]]}))
            return
        attempts = [(model, ordinal, f"{model['id']}-rep-{ordinal}", None)
                    for model in config["models"] for ordinal in campaign.repetitions(config)]
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
        unarchived = export_deferred(root, store)
        if unarchived:
            print(json.dumps({"unarchived_attempts": unarchived,
                              "note": "Evaluated outcomes stand and local files are retained; run `recover` to retry the export."}))
        if errors:
            raise RuntimeError("Campaign finalization failed: " + ", ".join(errors))
        if config["policies"]["attempt_selection"] == campaign.INDEPENDENT:
            print("Model sequences completed: every declared independent repetition ran unless an account or content-filter stop left it RESERVED. Scores are auxiliary diagnostics, not aesthetic rankings.")
        else:
            print("Model sequences completed, stopping after first eligible success or three attempts. Unused slots are SKIPPED_AFTER_SUCCESS. Scores are auxiliary diagnostics, not aesthetic rankings.")
        if stopped:
            print(json.dumps({"stopped_on_account_failure": stopped,
                              "note": "QUOTA/AUTH/CONTENT_FILTER are infrastructure faults; RESERVED slots are unused. Fix the cause, then recover and retry explicitly."}))


if __name__ == "__main__":
    main()
