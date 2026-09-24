#!/usr/bin/env python3
"""Run actual mini-swe-agent once per model through a local CLIProxyAPI endpoint."""
from __future__ import annotations

import argparse
from array import array
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import urllib.parse
import wave

# Explicit project import only; also works with `python -I benchmark/run.py`.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from proxy import ProxyModel, digest, request, validate_url

MINI_VERSION = "2.4.6"
FINISH = "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
LIMIT_KEYS = {"steps", "wall_seconds", "request_seconds", "command_seconds", "render_seconds", "video_seconds", "artifact_bytes"}
PARAMS = {"temperature", "top_p", "max_tokens", "max_completion_tokens", "reasoning_effort", "seed"}


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def proxy_policy(path: Path) -> dict:
    import yaml
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {"host": "127.0.0.1", "request-retry": 0, "max-retry-credentials": 1,
                "max-retry-interval": 0, "disable-claude-cloak-mode": True,
                "disable-image-generation": "passthrough"}
    if not isinstance(value, dict):
        raise ValueError("Proxy config must be a mapping")
    for key, expected in required.items():
        if type(value.get(key)) is not type(expected) or value[key] != expected:
            raise ValueError(f"Proxy policy requires {key}={expected!r}")
    if value.get("routing", {}).get("strategy") != "fill-first":
        raise ValueError("Proxy routing must be fill-first with dedicated upstream routes")
    for key in ("switch-project", "switch-preview-model", "antigravity-credits"):
        if value.get("quota-exceeded", {}).get(key) is not False:
            raise ValueError(f"Disable quota fallback: {key}")
    for key in ("payload", "oauth-model-alias", "ampcode"):
        if value.get(key):
            raise ValueError(f"Remove prompt/routing overrides: {key}")
    if value.get("plugins", {}).get("enabled", False):
        raise ValueError("Proxy plugins must be disabled")
    if value.get("claude-code", {}).get("disable-cloaking-model-list") is not True:
        raise ValueError("Disable model-list cloaking")
    # Do not read auth-dir or save any upstream/local client credentials. The digest skips
    # credential values so a rotated key (Vercel's 12 h OIDC token) is not a changed condition.
    return {"config_sha256": digest(redact(value)), "port": value.get("port"),
            "auth_overrides_audited": False, "upstream_payload_verified": False}


def redact(value):
    """Copy of a config tree with every key/secret/token value replaced by a marker."""
    if isinstance(value, dict):
        return {k: "<redacted>" if re.search(r"key|secret|token", k, re.I) and isinstance(v, (str, list)) else redact(v)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def load_config(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {"base_url", "api_key_env", "proxy_config", "proxy_version", "image", "visualizer_image", "generation", "limits", "models"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"Campaign keys must be exactly: {sorted(required)}")
    value["base_url"] = validate_url(value["base_url"])
    if not re.fullmatch(r"CLIPROXY_[A-Z0-9_]*KEY", value["api_key_env"]):
        raise ValueError("Invalid API key environment variable name")
    if not value["proxy_version"] or "REPLACE" in value["proxy_version"]:
        raise ValueError("Record the installed proxy version or commit")
    if set(value["limits"]) != LIMIT_KEYS or any(
            type(n) is not int or n <= 0 for n in value["limits"].values()):
        raise ValueError("All resource limits must be positive integers")
    if not isinstance(value["generation"], dict) or set(value["generation"]) - PARAMS:
        raise ValueError("Unsupported generation parameters; no prompt, tools, or routing overrides")
    digest(value)  # Also rejects NaN/Infinity, which Python's JSON decoder accepts.
    seen_ids, seen_models = set(), set()
    if not isinstance(value["models"], list) or not value["models"]:
        raise ValueError("Specify at least one exact model")
    for model in value["models"]:
        if set(model) != {"id", "model", "response_model"}:
            raise ValueError("Each model needs id, model, response_model only")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}", model["id"]):
            raise ValueError("Invalid model run ID")
        for key in ("model", "response_model"):
            name = model[key]
            if not isinstance(name, str) or not name or "REPLACE" in name or name == "auto" or "*" in name:
                raise ValueError("Use exact model IDs; no auto-routing or placeholders")
        if model["id"] in seen_ids or model["model"] in seen_models:
            raise ValueError("Duplicate model: one attempt per configured model")
        seen_ids.add(model["id"])
        seen_models.add(model["model"])
    proxy_path = (path.parent / value["proxy_config"]).resolve()
    value["proxy_policy"] = proxy_policy(proxy_path)
    if value["proxy_policy"]["port"] != urllib.parse.urlsplit(value["base_url"]).port:
        raise ValueError("Proxy config and endpoint ports differ")
    # The prompt states the budget so models can plan; the numbers come from the frozen limits.
    value["system"] = ((HERE / "prompts/system.txt").read_text(encoding="utf-8")
                       .replace("<<STEPS>>", str(value["limits"]["steps"]))
                       .replace("<<MINUTES>>", str(value["limits"]["wall_seconds"] // 60)))
    value["task"] = (HERE / "prompts/task.txt").read_text(encoding="utf-8")
    value.pop("proxy_config")
    return value


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


class Sandbox:
    """mini-swe-agent Environment protocol, without profile or host mounts."""
    def __init__(self, docker: list[str], name: str, timeout: int):
        self.docker, self.name, self.timeout = docker, name, timeout
        self.config = {"image_container": name, "network": "none", "skills": False}

    def execute(self, action: dict, cwd="") -> dict:
        command = action["command"]
        if command.strip() == FINISH:
            from minisweagent.exceptions import Submitted
            raise Submitted({"role": "exit", "content": "Submitted",
                             "extra": {"exit_status": "Submitted", "submission": "submission/tune.xm"}})
        # Output is bounded by the container tmpfs and only 20 KB reaches the host.
        wrapper = (f"timeout --kill-after=2s {self.timeout}s /bin/bash --noprofile --norc -c "
                   + shlex.quote(command) + " > /tmp/keygen-action.log 2>&1; "
                   + "r=$?; head -c 20000 /tmp/keygen-action.log; exit $r")
        started = time.monotonic()
        result = shell(self.docker + ["exec", "-w", "/workspace", "-e", "BASH_ENV=/dev/null",
                       "-e", "ENV=/dev/null", self.name, "/bin/bash", "--noprofile", "--norc", "-c", wrapper],
                       timeout=self.timeout + 10, check=False)
        # mini copies `extra` onto the tool message, so the sandbox time lands in the trajectory.
        return {"returncode": result.returncode, "output": result.stdout.decode("utf-8", "replace"),
                "extra": {"duration_seconds": time.monotonic() - started}}

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


def collect(docker: list[str], name: str, source: str, destination: Path, max_bytes: int) -> None:
    destination.mkdir(parents=True)
    with tempfile.TemporaryFile() as errors, tempfile.NamedTemporaryFile() as archive:
        # Stream with an explicit cap rather than trusting a tar's advertised size.
        if not source.startswith("/workspace/") or ".." in PurePosixPath(source).parts:
            raise ValueError("Export source must be inside /workspace")
        relative = PurePosixPath(source).relative_to("/workspace")
        parent, leaf = (relative, ".") if source.endswith("/.") else (relative.parent, relative.name)
        proc = subprocess.Popen(docker + ["exec", name + "-files", "/bin/tar", "-C",
                                str(PurePosixPath("/export") / parent), "-cf", "-", leaf],
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
            if proc.wait(timeout=30) != 0:
                raise ValueError("Submission not found or could not be copied")
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
        with xm.open("rb") as source:
            result = subprocess.run(docker + ["exec", "-i", name, "python3", "-c",
                    "import sys;open('/workspace/input.xm','wb').write(sys.stdin.buffer.read())"],
                    stdin=source, capture_output=True, timeout=30, check=True)
        for tool, arguments in (
                ("module_load", {"path": "/workspace/input.xm"}),
                ("module_render", {"path": "/workspace/canonical.wav", "rate": 44100, "bits": 16, "amp": 8, "loops": 1})):
            result = shell(docker + ["exec", name, "ft2", "call", tool, json.dumps(arguments)],
                           timeout=config["limits"]["render_seconds"])
            (run_dir / (tool + ".json")).write_bytes(result.stdout)
        collect(docker, name, "/workspace/canonical.wav", run_dir / "canonical", config["limits"]["artifact_bytes"])
        return wav_info(run_dir / "canonical/canonical.wav")
    finally:
        remove_container(docker, name)


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
        video = shell(docker + ["exec", name, "cat", "/tmp/visualizer.mp4"], timeout=120).stdout
        if len(video) > config["limits"]["artifact_bytes"]:
            raise ValueError("Video exceeded byte limit")
        (run_dir / "visualizer").mkdir()
        (run_dir / "visualizer/visualizer.mp4").write_bytes(video)
        return {"seconds": seconds, "bytes": len(video), "sha256": hashlib.sha256(video).hexdigest(),
                "capture": capture.stdout.decode("utf-8", "replace").strip()}
    finally:
        shell(docker + ["rm", "-f", name], check=False)


def isolated_env(home: Path, key_name: str) -> dict:
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"), "MSWEA_GLOBAL_CONFIG_DIR": str(home / "mini-config"),
            "MSWEA_SILENT_STARTUP": "1", "PYTHONNOUSERSITE": "1", key_name: os.environ[key_name]}


def worker(spec_path: Path) -> None:
    # The parent creates this directory empty and starts Python with -I.
    spec = json.loads(spec_path.read_text())
    config = spec["config"]
    run_dir = spec_path.parent
    from minisweagent import __version__
    from minisweagent.agents.default import DefaultAgent
    if __version__ != MINI_VERSION:
        raise RuntimeError("mini-swe-agent version mismatch")
    agent = DefaultAgent(ProxyModel(config, spec["model"], run_dir / "transport.jsonl"),
                         Sandbox(spec["docker"], spec["container"], config["limits"]["command_seconds"]),
                         system_template="{{ frozen_system }}", instance_template="{{ task }}",
                         step_limit=config["limits"]["steps"], cost_limit=0,
                         wall_time_limit_seconds=config["limits"]["wall_seconds"],
                         output_path=run_dir / "trajectory.json")
    try:
        result = agent.run(task=config["task"], frozen_system=config["system"])
    except Exception as exc:
        result = {"exit_status": type(exc).__name__, "error": str(exc)}
    write_json(run_dir / "worker-result.json", result)


def summarize(run_dir: Path) -> dict:
    """Per-attempt totals from the audit files, so nobody has to re-sum transport.jsonl later."""
    totals = {"requests": 0, "prompt_tokens": 0, "cached_tokens": 0, "completion_tokens": 0,
              "reasoning_tokens": 0, "model_seconds": 0.0, "sandbox_seconds": 0.0, "commands": 0}
    transport = run_dir / "transport.jsonl"
    if transport.exists():
        for line in transport.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            usage = record.get("usage") or {}
            totals["requests"] += 1
            totals["prompt_tokens"] += usage.get("prompt_tokens") or 0
            totals["completion_tokens"] += usage.get("completion_tokens") or 0
            totals["cached_tokens"] += (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
            totals["reasoning_tokens"] += ((usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
                                           or usage.get("reasoning_tokens") or 0)
            totals["model_seconds"] += record.get("latency_seconds") or 0.0
    trajectory = run_dir / "trajectory.json"
    if trajectory.exists():
        for message in json.loads(trajectory.read_text(encoding="utf-8")).get("messages", []):
            duration = message.get("extra", {}).get("duration_seconds")
            if message.get("role") == "tool" and duration is not None:
                totals["commands"] += 1
                totals["sandbox_seconds"] += duration
    return totals


def reserve(root: Path, model_id: str) -> Path:
    directory = root / model_id
    directory.mkdir()  # Atomic one-attempt reservation. No overwrite/redo option.
    write_json(directory / "status.json", {"status": "RESERVED"})
    return directory


def run_one(root: Path, config: dict, model: dict, docker: list[str], image: str, visualizer_image: str) -> None:
    run_dir = reserve(root, model["id"])
    name = "keygen-create-" + uuid.uuid4().hex[:16]
    started = time.time()
    result = {"status": "INFRA_ERROR", "model": model, "quality_score": None, "started_at": started}
    try:
        start_container(docker, image, name)
        spec = {"config": config, "model": model, "docker": docker, "container": name}
        write_json(run_dir / "spec.json", spec)
        home = run_dir / "isolated-host-home"
        mini_config = home / "mini-config"
        mini_config.mkdir(parents=True)
        # Do not inherit MSWEA_*, PYTHONPATH, BASH_ENV, .env, native CLI config, or skills.
        env = isolated_env(home, config["api_key_env"])
        with (run_dir / "worker.log").open("wb") as log:
            proc = subprocess.Popen([sys.executable, "-I", str(HERE / "run.py"), "--worker", str(run_dir / "spec.json")],
                                    cwd=home, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                proc.wait(timeout=config["limits"]["wall_seconds"])
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                result["termination"] = "WallTimeExceeded"
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
        worker_result = run_dir / "worker-result.json"
        if worker_result.exists():
            result["termination"] = json.loads(worker_result.read_text())
        else:
            result.setdefault("termination", "WorkerExitedWithoutResult")
        # Freeze all child processes before collecting the last artifact, even on timeout.
        shell(docker + ["pause", name])
        try:
            collect(docker, name, "/workspace/submission/.", run_dir / "submission", config["limits"]["artifact_bytes"])
        except ValueError as exc:
            result.update(status="FAILED", error=str(exc))
            return
        remove_container(docker, name)
        try:
            result["audio"] = render(docker, image, run_dir, config)
            result["artifact_sha256"] = hashlib.sha256((run_dir / "submission/tune.xm").read_bytes()).hexdigest()
            result["status"] = "PLAYABLE_UNSCORED"
            # The video is presentation, not evaluation: a capture failure is recorded, not a status change.
            try:
                result["video"] = visualize(docker, visualizer_image, run_dir, config, result["audio"]["duration_seconds"])
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                result["video"] = {"error": type(exc).__name__ + ": " + str(exc)[:500]}
        except (ValueError, wave.Error, EOFError) as exc:
            result.update(status="FAILED", error=str(exc))
        except (subprocess.SubprocessError, RuntimeError) as exc:
            result.update(status="EVALUATION_ERROR", error=type(exc).__name__)
    except KeyboardInterrupt:
        result["status"] = "INTERRUPTED"
        raise
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        try:
            remove_container(docker, name)
        finally:
            result["finished_at"] = time.time()
            result["wall_seconds"] = result["finished_at"] - started
            result["totals"] = summarize(run_dir)
            write_json(run_dir / "status.json", result)


def fingerprint(config: dict, docker: list[str]) -> dict:
    if importlib.metadata.version("mini-swe-agent") != MINI_VERSION:
        raise ValueError(f"Install mini-swe-agent=={MINI_VERSION}")
    image, visualizer = (json.loads(shell(docker + ["image", "inspect", config[key]]).stdout)[0]
                         for key in ("image", "visualizer_image"))
    sources = {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in [HERE / "run.py", HERE / "proxy.py", HERE / "bridge.py", HERE / "visualize.sh",
                         HERE / "Dockerfile", HERE / "requirements.txt"]}
    packages = sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())
    return {"config": config, "source_sha256": sources, "image_id": image["Id"], "visualizer_image_id": visualizer["Id"],
            "architecture": image["Architecture"], "packages": packages, "python": sys.version,
            "docker_server": shell(docker + ["version", "--format", "{{.Server.Version}}"]).stdout.decode().strip()}


def lock_campaign(path: Path, snapshot: dict) -> None:
    frozen = {"sha256": digest(snapshot), "snapshot": snapshot}
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(frozen, handle, indent=2)
    except FileExistsError:
        if json.loads(path.read_text())["sha256"] != frozen["sha256"]:
            raise ValueError("Campaign inputs changed; refusing mixed-condition resume")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]))
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["doctor", "run"])
    parser.add_argument("--campaign", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=HERE / "runs/official")
    args = parser.parse_args()
    config = load_config(args.campaign.resolve())
    key = os.environ.get(config["api_key_env"])
    if not key:
        raise ValueError("Set the local proxy client-key environment variable")
    models = request(config["base_url"], key, "/models", timeout=30).json
    available = {m["id"] for m in models.get("data", [])}
    if any(m["model"] not in available for m in config["models"]):
        raise ValueError("A configured model is missing from the proxy /v1/models list")
    docker = docker_command()
    snapshot = fingerprint(config, docker)
    if args.command == "doctor":
        print(json.dumps({"status": "configuration_checked", "image_id": snapshot["image_id"],
                          "visualizer_image_id": snapshot["visualizer_image_id"],
                          "mini_version": MINI_VERSION, "models": config["models"],
                          "proxy_policy": config["proxy_policy"],
                          "note": "No completion sent. Upstream payload and native rendering not tested by doctor."}, indent=2))
        return
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_campaign(root / "campaign.lock.json", snapshot)
    for model in config["models"]:
        if (root / model["id"]).exists():
            print(f"Skipping reserved attempt: {model['id']}", flush=True)
            continue
        run_one(root, config, model, docker, snapshot["image_id"], snapshot["visualizer_image_id"])
        print(f"Finished: {model['id']}", flush=True)
    print("Artifacts and audit records saved. No aesthetic ranking has been calculated.")


if __name__ == "__main__":
    main()
