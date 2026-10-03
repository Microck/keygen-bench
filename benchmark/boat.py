"""Trusted Boat lifecycle, immutable image bundles, and bounded raw SSH exports.

Provider calls and credentials stay on the controller. Fresh credential-free VMs
load SHA256-verified controller Docker-save bundles. Boat API is control-plane
only; Docker data uses stock, noninteractive SSH to the local VM daemon.
"""
from __future__ import annotations

from contextlib import contextmanager
import argparse
from datetime import datetime
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import stat
import signal
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.parse
import uuid

try:
    from .boat_transport import ssh_command
except ImportError:
    from boat_transport import ssh_command

HERE = Path(__file__).resolve().parent
SOURCE_ALLOWLIST = (
    "benchmark/Dockerfile", "benchmark/bridge.py", "benchmark/visualize.sh",
    "scripts/build-ft2-linux.sh", "tools/ft2_smoke.py",
)
IMAGE_ID = re.compile(r"sha256:[a-f0-9]{64}\Z")
BOAT_ID = re.compile(r"bx_[a-z0-9]{8}\Z")
# small 2 vCPU/4 GB (0.5x), default 4 vCPU/8 GB (1x), large 8 vCPU/16 GB (2x burn rate).
MAX_ATTEMPTS_PER_VM = {"small": 1, "default": 3, "large": 6}
BASE_IMAGE = "debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251"
API_BASES = {"https://boat.dev/api/v1", "https://ascii.dev/api/boat"}
BUNDLE_MAX_BYTES = 2 * 1024 * 1024 * 1024
BUNDLE_RESERVE_BYTES = 256 * 1024 * 1024


class BoatError(RuntimeError):
    """Errors contain codes, never secret-bearing Boat error/dashboard URLs."""
    def __init__(self, message: str, *, code: str = "", status: int = 0, exit_code: int | None = None):
        super().__init__(message)
        self.code, self.status, self.exit_code = code, status, exit_code


class BoatAPI:
    def __init__(self):
        # CLI-compatible auth resolution. This file is read internally, never
        # printed, copied to Boat, included in audits, or given to the model.
        config = {}
        if not os.environ.get("BOAT_API_KEY"):
            path = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "ascii/boat/config.json"
            try:
                config = json.loads(path.read_text())
            except (OSError, ValueError):
                raise BoatError("Boat authentication unavailable; authenticate the controller first") from None
        self.token = os.environ.get("BOAT_API_KEY") or config.get("token")
        if not isinstance(self.token, str) or not self.token:
            raise BoatError("Boat authentication unavailable; authenticate the controller first")
        base = os.environ.get("BOAT_API_URL") or config.get("api_url", "https://boat.dev")
        self.base = {"https://boat.dev": "https://boat.dev/api/v1", "https://ascii.dev": "https://ascii.dev/api/boat"}.get(base.rstrip("/"), base.rstrip("/"))
        if self.base not in API_BASES:
            raise BoatError("Boat API origin must be the trusted production Boat service")

    def call(self, method: str, path: str, body: dict | None = None, *, key: str | None = None, timeout: float = 30) -> dict:
        if timeout <= 0:
            raise BoatError("Boat API deadline exhausted", code="connection_error")
        payload = {"url": self.base + path, "method": method, "body": body,
                   "key": key, "token": self.token, "timeout": timeout}
        try:
            # A socket timeout is not a whole-request deadline. The finite
            # metadata worker is killed at the controller's exact remaining
            # stage budget, including DNS, TLS, headers and body.
            result = subprocess.run([sys.executable, "-I", str(HERE / "boat_api.py")],
                                    input=json.dumps(payload).encode(), capture_output=True,
                                    timeout=timeout, check=True)
            response = json.loads(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError, ValueError):
            raise BoatError("Boat API connection or response deadline failed", code="connection_error") from None
        if "error" in response:
            code = response["error"]["code"]
            status = response["error"]["status"]
            raise BoatError(f"Boat API {method} failed: {code} (HTTP {status})", code=code, status=status)
        return response["result"]


def _bundle_spec(bundle: dict, images: dict) -> dict:
    if not isinstance(bundle, dict):
        raise ValueError("Boat image_bundle must be an object")
    path = Path(bundle.get("controller_path", ""))
    if not path.is_absolute():
        raise ValueError("image_bundle controller_path must be absolute")
    digest = bundle.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("image_bundle sha256 must be 64 lowercase hexadecimal digits")
    size = bundle.get("bytes")
    if type(size) is not int or size <= 0:
        raise ValueError("image_bundle bytes must be an explicit positive integer")
    if set(images) != {"agent", "visualizer"}:
        raise ValueError("image_bundle requires both exact agent and visualizer image IDs")
    if "images" in bundle and bundle["images"] != images:
        raise ValueError("image_bundle image IDs do not match configured images")
    return {"controller_path": str(path), "sha256": digest, "bytes": size, "images": dict(images)}


@contextmanager
def _verified_bundle(bundle: dict, images: dict, *, deadline: float | None = None):
    spec = _bundle_spec(bundle, images)
    try:
        descriptor = os.open(spec["controller_path"], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        raise BoatError("Controller image bundle is missing or unreadable", code="image_bundle_missing") from None
    with os.fdopen(descriptor, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != spec["bytes"]:
            raise BoatError("Controller image bundle size/type mismatch", code="image_bundle_size_mismatch")
        digest = hashlib.sha256()
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                raise BoatError("Image bundle verification exceeded setup deadline", code="lifecycle_deadline")
            block = source.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
        after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or digest.hexdigest() != spec["sha256"]:
            raise BoatError("Controller image bundle SHA256 mismatch or file changed", code="image_bundle_hash_mismatch")
        source.seek(0)
        yield source, spec
        delivered = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns) != (delivered.st_size, delivered.st_mtime_ns):
            raise BoatError("Controller image bundle changed during delivery", code="image_bundle_hash_mismatch")


def verify_image_bundle(bundle: dict, images: dict, *, deadline: float | None = None) -> dict:
    with _verified_bundle(bundle, images, deadline=deadline) as (_, spec):
        return spec


def _diagnostic(text) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    text = (text or "")[:32768]
    text = re.sub(r"https?://\S+", "[redacted-url]", text)
    return re.sub(r"\b(?:boat|sk|ghp|gho)_[A-Za-z0-9_-]+", "[redacted-token]", text)


def _docker_error(returncode: int, stderr: str) -> str:
    lowered = stderr.lower()
    if returncode == 255:
        return "ssh_transport_failure"
    if "permission denied" in lowered:
        return "docker_permission_denied"
    if "cannot connect to the docker daemon" in lowered or "is the docker daemon running" in lowered:
        return "docker_daemon_unavailable"
    if "no such image" in lowered:
        return "docker_image_missing"
    return "docker_command_failed"

def _bundle_export_preflight(destination: Path, max_bytes: int, reserve_bytes: int):
    destination = Path(destination)
    if not destination.is_absolute() or max_bytes <= 0 or reserve_bytes < 0:
        raise ValueError("image bundle export needs an absolute path and positive bounds")
    if destination.resolve().is_relative_to((HERE.parent / "legacy").resolve()):
        raise ValueError("image bundle export cannot write into legacy")
    metadata_path = destination.with_name(destination.name + ".json")
    if destination.exists() or destination.is_symlink() or metadata_path.exists() or metadata_path.is_symlink():
        raise FileExistsError("refusing to overwrite an existing image bundle or metadata")
    destination.parent.mkdir(parents=True, exist_ok=True)
    available = shutil.disk_usage(destination.parent).free
    if available < max_bytes + reserve_bytes:
        raise BoatError("Controller lacks image-export peak-space reserve", code="image_bundle_space")
    return destination, metadata_path, available



def validate_config(config: dict) -> dict:
    if config.get("backend") != "boat" or not isinstance(config.get("boat"), dict):
        raise ValueError("transport requires backend=boat and a boat configuration object")
    boat = config["boat"]
    mode = boat.get("mode", "new")
    if mode not in {"new", "resume", "fork"}:
        raise ValueError("Boat mode must be new, resume, or fork")
    if mode != "new" and not BOAT_ID.fullmatch(str(boat.get("id", ""))):
        raise ValueError("resume/fork requires an explicit Boat id")
    ttl = boat.get("ttl_seconds")
    if type(ttl) is not int or not 1 <= ttl <= 2592000:
        raise ValueError("Boat ttl_seconds must be an explicit integer from 1 to 2592000")
    interval = boat.get("allocation_interval_seconds", 0)
    if type(interval) is not int or not 0 <= interval <= 86400:
        raise ValueError("Boat allocation_interval_seconds must be an integer from 0 to 86400")
    # Shared VMs: attempts per machine type, bounded so the sum of per-attempt container caps
    # (agent 2 GiB + helper 256 MiB + 512 MiB workspace tmpfs) stays within ~5% of VM memory.
    tenants = boat.get("attempts_per_vm", 1)
    if type(tenants) is not int or not 1 <= tenants <= MAX_ATTEMPTS_PER_VM.get(boat.get("type", "small"), 1):
        raise ValueError("Boat attempts_per_vm must be an integer from 1 to the machine type's bound "
                         + json.dumps(MAX_ATTEMPTS_PER_VM))
    linger = boat.get("linger_seconds", 0)
    if type(linger) is not int or not 0 <= linger <= 600:
        raise ValueError("Boat linger_seconds must be an integer from 0 to 600")
    if (tenants > 1 or linger) and mode != "new":
        raise ValueError("Shared or lingering VMs require fresh new machines")
    for option, default in (("startup_seconds", 120), ("stop_seconds", 120)):
        value = boat.get(option, default)
        if type(value) is not int or not 10 <= value <= 600:
            raise ValueError(f"Boat {option} must be an integer from 10 to 600")
    if boat.get("type", "small") not in {"small", "default", "large"}:
        raise ValueError("unsupported Boat machine type")
    if not isinstance(boat.get("images", {}), dict):
        raise ValueError("Boat images must be a role-to-immutable-ID object")
    for role, image in boat.get("images", {}).items():
        if role not in {"agent", "visualizer"} or not IMAGE_ID.fullmatch(str(image)):
            raise ValueError("Boat images require immutable sha256 IDs for agent/visualizer")
    if boat.get("snapshot") and (mode != "new" or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", boat["snapshot"])):
        raise ValueError("named snapshot requires new mode and a valid snapshot name")
    if boat.get("image_bundle") is not None:
        if mode != "new" or boat.get("snapshot"):
            raise ValueError("image_bundle loading requires a fresh new VM without a snapshot")
        _bundle_spec(boat["image_bundle"], boat.get("images", {}))
    return boat


def doctor(config: dict, *, timeout: float = 30) -> dict:
    """Read-only readiness: never creates, resumes, or forks a machine."""
    deadline = time.monotonic() + timeout
    boat = validate_config(config)
    bundle = verify_image_bundle(boat["image_bundle"], boat["images"], deadline=deadline) if boat.get("image_bundle") is not None else None
    missing = [name for name in ("ssh", "ssh-keygen") if shutil.which(name) is None]
    if missing:
        raise BoatError("Required controller programs missing: " + ", ".join(missing))
    api = BoatAPI()
    limits = api.call("GET", "/limits", timeout=deadline - time.monotonic())
    nested = limits.get("limits", limits)
    if nested.get("canStart") is not True:
        raise BoatError("Boat cannot start machines: " + str(nested.get("startBlockedReason") or nested.get("blockedReason") or "quota/auth unavailable"))
    starts = nested.get("starts", {})
    for window, value in starts.items():
        if isinstance(value, dict) and value.get("remaining", 1) <= 0:
            raise BoatError(f"Boat {window} start budget exhausted")
    remaining = nested.get("creditBalanceSeconds")
    if remaining is None:
        remaining = (nested.get("subscriptionRemainingSeconds") or 0) + (nested.get("packBalanceSeconds") or 0)
    if remaining <= 0:
        raise BoatError("Boat machine-time quota exhausted")
    result = {"backend": "boat", "can_start": True, "remaining_seconds": remaining,
              "mode": boat.get("mode", "new"), "ttl_seconds": boat["ttl_seconds"],
              "images": boat.get("images", {}), "transport": "pinned-host-key raw SSH"}
    if bundle is not None:
        result["image_bundle"] = bundle
    if boat.get("id"):
        data = api.call("GET", f"/sandboxes/{boat['id']}", timeout=deadline - time.monotonic())
        result["source_state"] = data.get("sandbox", data).get("state")
    return result


def stream_command(argv: list[str], destination: Path, *, timeout: float, max_bytes: int, stdin=None) -> dict:
    """Stream stdout to disk; bound both streams and preserve exit status.

    No retry is made, even on a dropped SSH connection or timeout. The remote
    process may still exist; the controller must clean its container/VM.
    """
    if timeout <= 0 or max_bytes <= 0:
        raise ValueError("stream deadline and byte limit must be positive")
    start = time.monotonic()
    destination.parent.mkdir(parents=True, exist_ok=True)
    stderr_path = destination.with_name(destination.name + ".stderr")
    proc = subprocess.Popen(argv, stdin=stdin if stdin is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    counts = {"stdout": 0, "stderr": 0}
    digest = hashlib.sha256()
    try:
        with destination.open("wb") as stdout, stderr_path.open("wb") as stderr, selectors.DefaultSelector() as selector:
            for pipe, name, target in ((proc.stdout, "stdout", stdout), (proc.stderr, "stderr", stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, (name, target))
            while selector.get_map():
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, timeout)
                for entry, _ in selector.select(min(remaining, 0.25)):
                    chunk = os.read(entry.fd, 64 * 1024)
                    if not chunk:
                        selector.unregister(entry.fileobj)
                        continue
                    name, target = entry.data
                    counts[name] += len(chunk)
                    limit = max_bytes if name == "stdout" else min(max_bytes, 1024 * 1024)
                    if counts[name] > limit:
                        raise BoatError(f"SSH {name} exceeded its {limit}-byte bound")
                    target.write(chunk)
                    if name == "stdout":
                        digest.update(chunk)
            remaining = timeout - (time.monotonic() - start)
            returncode = proc.wait(timeout=max(0.001, remaining))
            if returncode:
                raise subprocess.CalledProcessError(returncode, argv)
        return {"path": str(destination), "bytes": counts["stdout"], "sha256": digest.hexdigest(), "exit_code": returncode}
    except BaseException:
        proc.kill()
        proc.wait()
        destination.unlink(missing_ok=True)
        raise
    finally:
        proc.stdout.close()
        proc.stderr.close()
        if counts["stderr"] == 0:
            stderr_path.unlink(missing_ok=True)


def validate_tar(path: Path, *, max_bytes: int) -> None:
    total = 0
    seen = set()
    with tarfile.open(path, "r:") as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts or (not member.isfile() and not member.isdir()):
                raise BoatError("Unsafe artifact archive member")
            normalized = str(name)
            if normalized in seen:
                raise BoatError("Duplicate artifact archive member")
            seen.add(normalized)
            total += member.size
            if total > max_bytes:
                raise BoatError("Artifact archive exceeds expanded-byte limit")


def workspace_tar_command(source_absolute: str, *, mount_root: str = "/export") -> list[str]:
    """Read workspace artifacts through the helper's live, read-only volume mount."""
    source = PurePosixPath(source_absolute)
    if not source.is_absolute() or ".." in source.parts or not source.is_relative_to("/workspace"):
        raise ValueError("collection source must be under /workspace")
    relative = source.relative_to("/workspace")
    parent, leaf = (relative, ".") if source_absolute.endswith("/.") or not relative.parts else (relative.parent, relative.name)
    return ["/bin/tar", "-C", str(PurePosixPath(mount_root) / parent), "-cf", "-", "--", leaf]


def workspace_export_command(docker: list[str], container: str, source_absolute: str) -> list[str]:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", container):
        raise ValueError("invalid container identifier")
    return [*docker, "exec", container + "-files", *workspace_tar_command(source_absolute)]


def source_context(repo_root: Path, destination: Path) -> dict:
    """Upload five explicitly named regular source files; never a repository tree."""
    root = repo_root.resolve(strict=True)
    hashes = {}
    with tarfile.open(destination, "w") as archive:
        for relative in SOURCE_ALLOWLIST:
            source = root / relative
            if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
                raise BoatError(f"Image source must be a regular allowlisted file: {relative}")
            if source.stat().st_size > 2 * 1024 * 1024:
                raise BoatError(f"Image source exceeds context bound: {relative}")
            content = source.read_bytes()
            hashes[relative] = hashlib.sha256(content).hexdigest()
            member = tarfile.TarInfo(relative)
            member.size = len(content)
            member.mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
            archive.addfile(member, io.BytesIO(content))
    return hashes


class BoatSession:
    def __init__(self, config: dict, *, audit_dir: Path | None = None):
        self.options = validate_config(config)
        self.config = config
        self.audit_dir = audit_dir
        self.id = None
        self.api = None
        self.connection = None
        self._private = None
        self._closed = False
        self._closing = False
        self._previous_sigterm = None
        self._pending_provision = None
        self._images = dict(self.options.get("images", {}))
        self.stop_record = None
        self._startup_deadline = None
        self._cleanup_deadline = None
        self._stage_name = "not-started"

    def _timeout(self, cap: float = 30, deadline: float | None = None) -> float:
        active = self._cleanup_deadline if self._closing else self._startup_deadline
        if active is not None:
            deadline = min(deadline, active) if deadline is not None else active
        if deadline is None:
            return cap
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BoatError(f"Boat lifecycle deadline exceeded during {self._stage_name}", code="lifecycle_deadline")
        return min(cap, remaining)

    def _request(self, method, path, body=None, *, key=None, deadline=None):
        return self.api.call(method, path, body, key=key, timeout=self._timeout(deadline=deadline))

    def _stage(self, name: str, **details):
        self._stage_name = name
        if not self._closing:
            self._audit("lifecycle.json", {"stage": name, "id": self.id, **details})

    def _terminate(self, signum, frame):
        if not self._closing:
            raise SystemExit(128 + signum)

    def _audit(self, name: str, data: dict) -> None:
        if self.audit_dir is not None:
            self.audit_dir.mkdir(parents=True, exist_ok=True)
            (self.audit_dir / name).write_text(json.dumps(data, indent=2) + "\n")

    def _safe_provision(self, path: str, body: dict, key: str) -> dict:
        # Only idempotency-key protected provisioning retries. Never retry exec.
        self._pending_provision = (path, dict(body), key)
        active = self._cleanup_deadline if self._closing else self._startup_deadline
        deadline = min(time.monotonic() + 180, active) if active is not None else time.monotonic() + 180
        while True:
            try:
                result = self._request("POST", path, body, key=key, deadline=deadline)
                identity = result.get("id") or result.get("sandbox", {}).get("id")
                if not BOAT_ID.fullmatch(str(identity)):
                    raise BoatError("Boat provisioning did not return a valid machine id", code="connection_error")
                self.id = identity
                self._pending_provision = None
                return result
            except BoatError as exc:
                ambiguous = exc.code in {"connection_error", "idempotency_in_progress", "lifecycle_deadline"} or exc.status >= 500
                if not ambiguous:
                    self._pending_provision = None
                if time.monotonic() >= deadline or not ambiguous:
                    raise
                time.sleep(min(2, self._timeout(2, deadline)))

    def _wait(self, states: set[str], *, timeout: float = 120) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            data = self._request("GET", f"/sandboxes/{self.id}", deadline=deadline)
            info = data.get("sandbox", data)
            state = info.get("state")
            self._stage("waiting-state", state=state, expected_states=sorted(states))
            if not self._closing and info.get("error"):
                error = info["error"]
                code = "restore_incomplete" if isinstance(error, str) and error.lower().startswith("restore incomplete") else "provider_boot_error"
                self._audit("provider-error.json", {"id": self.id, "state": state, "health": info.get("health"), "code": code})
                raise BoatError("Boat provider did not produce a complete runnable machine", code=code)
            if not self._closing and info.get("archiveAfter"):
                expiry = datetime.fromisoformat(info["archiveAfter"].replace("Z", "+00:00")).timestamp()
                reserve = min(self.options.get("stop_seconds", 120), self.options["ttl_seconds"] / 2)
                expiry_deadline = time.monotonic() + expiry - time.time() - reserve
                deadline = min(deadline, expiry_deadline)
                if self._startup_deadline is not None:
                    self._startup_deadline = min(self._startup_deadline, expiry_deadline)
            self._timeout(deadline=deadline)
            if state in states:
                return info
            if state == "error":
                raise BoatError("Boat entered error state")
            time.sleep(min(2, self._timeout(2, deadline)))

    def _authorize_ssh(self, public_key: str) -> dict:
        """Wait through the no-env scrub gate; retry only the same public key."""
        attempts = 0
        while True:
            self._stage("ssh-authorization")
            try:
                return self._request("POST", f"/sandboxes/{self.id}/sshkey", {"key": public_key})
            except BoatError as exc:
                if exc.status != 409 or exc.code not in {"sandbox_securing", "boat_securing"}:
                    raise
                attempts += 1
                self._audit("ssh-securing.json", {"id": self.id, "code": exc.code, "attempts": attempts, "public_key_reused": True})
                self._stage("waiting-securing", code=exc.code)
                # provisioned is not sufficient when the separate no-env
                # security gate is still scrubbing a restored snapshot.
                time.sleep(self._timeout(2))
                self._wait({"ready", "provisioned", "idle", "running"}, timeout=self._timeout(self.options.get("startup_seconds", 120)))

    def __enter__(self):
        try:
            self._startup_deadline = time.monotonic() + self.options.get("startup_seconds", 120)
            self._stage("preflight")
            if threading.current_thread() is threading.main_thread():
                self._previous_sigterm = signal.signal(signal.SIGTERM, self._terminate)
            doctor(self.config, timeout=self._timeout())
            self.api = BoatAPI()
            mode = self.options.get("mode", "new")
            provision_started = time.time()
            body = {"type": self.options.get("type", "small"), "ttlSeconds": self.options["ttl_seconds"], "noEnv": True, "env": {}}
            key = str(uuid.uuid4())
            if self.options.get("snapshot"):
                body["from"] = self.options["snapshot"]
            self._audit("provision-request.json", {"mode": mode, "idempotency_key": key, "body": body, "source": self.options.get("id") or self.options.get("snapshot")})
            self._stage("provision")
            if mode == "resume":
                self.id = self.options["id"]
                self._request("POST", f"/sandboxes/{self.id}/resume", body)
            else:
                path = "/sandboxes" if mode == "new" else f"/sandboxes/{self.options['id']}/fork"
                self._safe_provision(path, body, key)
            self._audit("machine.json", {"id": self.id, "no_env": True, "ttl_seconds": self.options["ttl_seconds"]})
            info = self._wait({"ready", "provisioned", "idle", "running"})
            archive_after = info.get("archiveAfter")
            if not archive_after:
                raise BoatError("Boat did not enable the required deadman TTL")
            try:
                expires = datetime.fromisoformat(archive_after.replace("Z", "+00:00"))
                if expires.tzinfo is None:
                    raise ValueError("timezone missing")
                self.archive_deadline = expires.timestamp()
            except (TypeError, ValueError, AttributeError):
                raise BoatError("Boat returned an invalid deadman expiry") from None
            if self.archive_deadline < provision_started + self.options["ttl_seconds"] - 5:
                raise BoatError("Boat shortened the requested TTL; frozen budgets cannot be delivered")
            self._private = tempfile.TemporaryDirectory(prefix="keygen-boat-ssh-")
            private = Path(self._private.name)
            identity = private / "identity"
            self._stage("local-ssh-key")
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(identity)], check=True, timeout=self._timeout(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            authorized = self._authorize_ssh(identity.with_suffix(".pub").read_text().strip())
            endpoint = authorized.get("sshEndpoint")
            if endpoint:
                host, port = endpoint.rsplit(":", 1)
                port = int(port)
            else:
                host, port = authorized.get("machineIp") or info.get("ip"), 22
            ipaddress.ip_address(host)
            if not 1 <= port <= 65535 or authorized.get("sshUser", "user") != "user":
                raise BoatError("Boat returned unsupported SSH coordinates")
            host_key = authorized.get("hostKey", "")
            if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]+)?", host_key):
                raise BoatError("Boat did not return a pin-able SSH server host key")
            known_hosts = private / "known_hosts"
            known_hosts.write_text(f"[{host}]:{port} {host_key}\n" if port != 22 else f"{host} {host_key}\n")
            self.connection = {"host": host, "port": port, "user": "user", "identity": str(identity), "known_hosts": str(known_hosts)}
            self.connection_path = private / "connection.json"
            self.connection_path.write_text(json.dumps(self.connection))
            self.connection_path.chmod(0o600)
            self._wait_docker_ready()
            if self.options.get("image_bundle") is not None:
                self._load_image_bundle()
            self._stage("image-verification")
            verified_images = {role: self.image_id(role) for role in self._images}
            if self.options.get("image_bundle") is not None:
                self._audit("image-bundle-identities.json", {"images": verified_images, "identities_verified": True})
            self._audit("ready.json", {"id": self.id, "archive_after": archive_after, "remaining_ttl_seconds": int(self.archive_deadline - time.time()), "transport": "raw SSH", "images": verified_images, "docker": self._docker_info, "host_key_sha256": hashlib.sha256(host_key.encode()).hexdigest()})
            self._startup_deadline = None
            self._stage("ready")
            return self
        except BaseException as exc:
            try:
                self._audit("entry-error.json", {"id": self.id, "stage": self._stage_name, "error_type": type(exc).__name__, "code": getattr(exc, "code", None)})
            finally:
                self.close()
            raise

    @property
    def docker_prefix(self) -> list[str]:
        if not self.connection or self._closed:
            raise BoatError("Boat transport is not active")
        return [sys.executable, str(HERE / "boat_transport.py"), "--ssh-config", str(self.connection_path), "--"]

    def command(self, argv: list[str]) -> list[str]:
        if not self.connection or self._closed:
            raise BoatError("Boat transport is not active")
        return ssh_command(self.connection, argv)

    def _wait_docker_ready(self) -> None:
        while True:
            # A restore failure can appear after SSH becomes available.
            self._wait({"ready", "provisioned", "idle", "running"}, timeout=self._timeout())
            self._stage("docker-readiness")
            result = subprocess.run([*self.docker_prefix, "info", "--format",
                                     '{"server_version":{{json .ServerVersion}},"root_dir":{{json .DockerRootDir}}}'],
                                    capture_output=True, text=True, timeout=self._timeout(15), check=False)
            if not result.returncode:
                details = json.loads(result.stdout)
                if not Path(details["root_dir"]).is_absolute():
                    raise BoatError("Docker reported an invalid storage root", code="docker_protocol_error")
                self._docker_info = details
                self._audit("docker-ready.json", details)
                return
            code = _docker_error(result.returncode, result.stderr)
            self._audit("docker-readiness-error.json", {"exit_code": result.returncode, "code": code, "stderr": _diagnostic(result.stderr)})
            if code != "docker_daemon_unavailable":
                raise BoatError(f"Remote Docker readiness failed: {code}", code=code, exit_code=result.returncode)
            # Only the observed local-daemon-unavailable condition is polled.
            # A missing image, permission error, or SSH failure is not retried.
            time.sleep(self._timeout(2))

    def _load_image_bundle(self) -> None:
        self._stage("image-bundle-verification")
        with _verified_bundle(self.options["image_bundle"], self._images, deadline=self._startup_deadline) as (source, spec):
            root = self._docker_info["root_dir"]
            space = subprocess.run(self.command(["df", "-B1", "--output=avail", root]), capture_output=True, text=True, timeout=self._timeout(), check=True)
            available = int(space.stdout.split()[-1])
            peak = spec["bytes"] * 4 + BUNDLE_RESERVE_BYTES
            self._audit("image-bundle-space.json", {"docker_root": root, "available_bytes": available, "peak_estimate_bytes": peak, "reserve_bytes": BUNDLE_RESERVE_BYTES})
            if available < peak:
                raise BoatError("Fresh VM lacks image-load peak-space reserve", code="image_bundle_space")
            self._stage("image-bundle-load")
            directory = self.audit_dir or Path(self._private.name)
            log = directory / "image-bundle-load.log"
            try:
                result = stream_command([*self.docker_prefix, "load"], log,
                                        stdin=source, timeout=self._timeout(300), max_bytes=1024 * 1024)
            except BaseException as exc:
                error_path = log.with_name(log.name + ".stderr")
                with (error_path.open("rb") if error_path.exists() else io.BytesIO()) as error:
                    diagnostic = _diagnostic(error.read(32768))
                self._audit("image-bundle-load-error.json", {"code": "image_bundle_load_failed", "exit_code": getattr(exc, "returncode", None), "stderr": diagnostic, "error_type": type(exc).__name__})
                raise
            self._audit("image-bundle-loaded.json", {**spec, "load_exit_code": result["exit_code"], "identities_verified": False})

    def export_image_bundle(self, destination: Path, *, max_bytes: int = BUNDLE_MAX_BYTES,
                            timeout: int = 300, reserve_bytes: int = BUNDLE_RESERVE_BYTES) -> dict:
        """Stream both exact images to a controller Docker-save tar and SHA metadata."""
        if timeout <= 0:
            raise ValueError("image bundle export timeout must be positive")
        destination, metadata_path, available = _bundle_export_preflight(destination, max_bytes, reserve_bytes)
        images = {role: self.image_id(role) for role in ("agent", "visualizer")}
        remaining_ttl = self.archive_deadline - time.time() - self.options.get("stop_seconds", 120)
        if remaining_ttl <= 0:
            raise BoatError("VM TTL cannot cover image export and stop reserve", code="lifecycle_deadline")
        partial = destination.with_name("." + destination.name + "." + uuid.uuid4().hex + ".partial")
        try:
            streamed = stream_command([*self.docker_prefix, "save", images["agent"], images["visualizer"]], partial,
                                      timeout=min(timeout, remaining_ttl), max_bytes=max_bytes)
            os.link(partial, destination)
            metadata = {"controller_path": str(destination), "sha256": streamed["sha256"],
                        "bytes": streamed["bytes"], "images": images, "format": "docker-save",
                        "controller_free_bytes_before": available, "export_bound_bytes": max_bytes,
                        "reserve_bytes": reserve_bytes}
            with metadata_path.open("x") as output:
                output.write(json.dumps(metadata, indent=2) + "\n")
            self._audit("image-bundle-export.json", metadata)
            return metadata
        except BaseException as exc:
            error_path = partial.with_name(partial.name + ".stderr")
            with (error_path.open("rb") if error_path.exists() else io.BytesIO()) as error:
                diagnostic = _diagnostic(error.read(32768))
            self._audit("image-bundle-export-error.json", {"code": "image_bundle_export_failed", "exit_code": getattr(exc, "returncode", None), "stderr": diagnostic, "error_type": type(exc).__name__})
            raise
        finally:
            partial.unlink(missing_ok=True)
            partial.with_name(partial.name + ".stderr").unlink(missing_ok=True)

    def image_id(self, role: str) -> str:
        identity = self._images.get(role)
        if not identity or not IMAGE_ID.fullmatch(identity):
            raise BoatError(f"Missing immutable Boat image identity for {role}")
        command = [*self.docker_prefix, "image", "inspect", identity, "--format", "{{.Id}} {{.Os}}/{{.Architecture}}"]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=self._timeout(45), check=False)
        except subprocess.TimeoutExpired as exc:
            self._audit(f"image-inspect-{role}.json", {"image": identity, "code": "image_inspect_timeout", "stderr": _diagnostic(exc.stderr)})
            raise BoatError(f"Remote {role} image inspection timed out", code="image_inspect_timeout") from None
        if result.returncode:
            code = _docker_error(result.returncode, result.stderr)
            self._audit(f"image-inspect-{role}.json", {"image": identity, "exit_code": result.returncode, "code": code, "stderr": _diagnostic(result.stderr), "stdout": _diagnostic(result.stdout)})
            self._wait({"ready", "provisioned", "idle", "running"}, timeout=self._timeout())
            raise BoatError(f"Remote {role} image inspection failed: {code}", code=code, exit_code=result.returncode)
        fields = result.stdout.strip().split()
        if fields != [identity, "linux/amd64"]:
            raise BoatError(f"Remote {role} image identity/architecture mismatch")
        return identity

    def collect_tar(self, container: str, source_absolute: str, destination: Path, *, timeout: int, max_bytes: int) -> dict:
        command = workspace_export_command(self.docker_prefix, container, source_absolute)
        result = stream_command(command, destination, timeout=timeout, max_bytes=max_bytes)
        try:
            validate_tar(destination, max_bytes=max_bytes)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return result

    def prepare(self, repo_root: Path) -> dict:
        """Build native amd64 images from a bounded source-only context, freezing IDs."""
        containers = subprocess.run([*self.docker_prefix, "ps", "-aq"], capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        if containers:
            raise BoatError("Image preparation requires a clean VM without existing containers")
        with tempfile.TemporaryDirectory(prefix="keygen-boat-context-") as directory:
            context = Path(directory) / "context.tar"
            sources = source_context(repo_root, context)
            architecture = subprocess.run(self.command(["uname", "-m"]), capture_output=True, text=True, timeout=30, check=True).stdout.strip()
            if architecture != "x86_64":
                raise BoatError("Pinned Boat preparation requires native x86_64")
            images = {}
            for target in ("agent", "visualizer"):
                tag = f"keygen-ft2-{target}:boat-prepared"
                log = (self.audit_dir or Path(directory)) / f"build-{target}.log"
                with context.open("rb") as input_file:
                    stream_command([*self.docker_prefix, "build", "--platform", "linux/amd64", "--build-arg", f"BASE_IMAGE={BASE_IMAGE}", "-f", "benchmark/Dockerfile", "--target", target, "-t", tag, "-"], log, stdin=input_file, timeout=1200, max_bytes=16 * 1024 * 1024)
                result = subprocess.run([*self.docker_prefix, "image", "inspect", tag, "--format", "{{.Id}}"], capture_output=True, text=True, timeout=45, check=True)
                images[target] = result.stdout.strip()
                if not IMAGE_ID.fullmatch(images[target]):
                    raise BoatError("Docker build did not produce an immutable image ID")
            self._images = images
            for role in images:
                self.image_id(role)
            provenance = {}
            for role, identity in images.items():
                output = Path(directory) / f"{role}-provenance.txt"
                stream_command([*self.docker_prefix, "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--pids-limit", "32", "--memory", "128m", "--cpus", "0.5", "--entrypoint", "/bin/sh", identity, "-c", "cat /opt/keygen/binary.sha256; sha256sum /opt/keygen/packages.txt; cat /opt/keygen/native-acceptance.json"], output, timeout=45, max_bytes=512 * 1024)
                provenance[role] = output.read_text()
            manifest = {"boat_id": self.id, "architecture": "linux/amd64", "base_image": BASE_IMAGE, "source_sha256": sources, "images": images, "native_provenance": provenance, "context_bytes": context.stat().st_size, "allowlist": list(SOURCE_ALLOWLIST)}
            self._audit("images.json", manifest)
            return manifest

    def smoke(self, destination: Path) -> dict:
        """No-inference acceptance: offline FT2, raw bytes, pause/export, cleanup."""
        destination.mkdir(parents=True, exist_ok=True)
        name = "keygen-boat-smoke-" + uuid.uuid4().hex[:12]
        image = self.image_id("agent")
        volume = name + "-work"
        docker = self.docker_prefix
        def checked(args, timeout=45):
            return subprocess.run([*docker, *args], capture_output=True, timeout=timeout, check=True)
        try:
            checked(["volume", "create", "--driver", "local", "--opt", "type=tmpfs",
                     "--opt", "device=tmpfs", "--opt", "o=size=256m,uid=10001,gid=10001", volume])
            checked(["create", "--name", name + "-files", "--network", "none", "--read-only",
                     "--user", "10001:10001", "--cap-drop", "ALL",
                     "--security-opt", "no-new-privileges:true", "--pids-limit", "32",
                     "--memory", "256m", "--cpus", "0.5",
                     "--mount", f"type=volume,source={volume},target=/export,readonly,volume-nocopy",
                     "--entrypoint", "/bin/sleep", image, "infinity"])
            checked(["start", name + "-files"])
            checked(["create", "--name", name, "--network", "none", "--read-only",
                     "--user", "10001:10001", "--cap-drop", "ALL",
                     "--security-opt", "no-new-privileges:true", "--pids-limit", "64",
                     "--memory", "512m", "--cpus", "1",
                     "--mount", f"type=volume,source={volume},target=/workspace,volume-nocopy",
                     "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m,uid=10001,gid=10001", image])
            inspection = json.loads(checked(["inspect", name]).stdout)[0]
            host_config = inspection["HostConfig"]
            if host_config["NetworkMode"] != "none" or not host_config["ReadonlyRootfs"] or inspection["Config"]["User"] != "10001:10001" or host_config.get("Binds"):
                raise BoatError("Remote offline container isolation was not delivered")
            (destination / "container.json").write_text(json.dumps(inspection, indent=2) + "\n")
            helper = json.loads(checked(["inspect", name + "-files"]).stdout)[0]
            mounts = {item["Destination"]: item for item in inspection["Mounts"]}
            helper_mounts = {item["Destination"]: item for item in helper["Mounts"]}
            writable, readonly = mounts["/workspace"], helper_mounts["/export"]
            helper_config = helper["HostConfig"]
            if writable["Type"] != "volume" or writable["Name"] != volume or not writable["RW"] or readonly["Name"] != volume or readonly["RW"] or helper_config["NetworkMode"] != "none" or not helper_config["ReadonlyRootfs"] or helper["Config"]["User"] != "10001:10001":
                raise BoatError("Remote shared-volume export isolation was not delivered")
            (destination / "export-helper.json").write_text(json.dumps(helper, indent=2) + "\n")
            checked(["start", name])
            deadline = time.monotonic() + 30
            while True:
                try:
                    checked(["exec", name, "ft2", "list"])
                    break
                except subprocess.CalledProcessError:
                    # Reading the tool catalogue is idempotent; writes aren't retried.
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.5)
            checked(["exec", name, "ft2", "call", "module_new", '{"channels":4,"name":"transport acceptance"}'])
            checked(["exec", name, "ft2", "call", "module_save", '{"path":"/workspace/fixture.xm","format":"xm"}'])
            checked(["exec", name, "python3", "-c", "from pathlib import Path; Path('/workspace/raw.bin').write_bytes(bytes(range(256))*4096)"])
            try:
                checked(["exec", name, "bash", "-lc", "touch /workspace/timeout-started; sleep 30"], timeout=3)
            except subprocess.TimeoutExpired:
                pass
            else:
                raise BoatError("SSH deadline smoke unexpectedly completed")
            checked(["pause", name])
            result = self.collect_tar(name, "/workspace/.", destination / "workspace.tar", timeout=45, max_bytes=8 * 1024 * 1024)
            with tarfile.open(destination / "workspace.tar", "r:") as archive:
                files = {PurePosixPath(item.name).name: item for item in archive if item.isfile()}
                raw = archive.extractfile(files["raw.bin"]).read()
                xm = archive.extractfile(files["fixture.xm"]).read()
                if raw != bytes(range(256)) * 4096 or not xm.startswith(b"Extended Module: ") or "timeout-started" not in files:
                    raise BoatError("Remote binary/XM/deadline acceptance failed")
            result.update({"image": image, "native_ft2": True, "paused_export": True, "deadline_observed": True})
            (destination / "smoke.json").write_text(json.dumps(result, indent=2) + "\n")
            return result
        finally:
            # Removing a paused container also terminates any exec left behind
            # after SSH timeout. No attempt command was killed/retried by API.
            removal = subprocess.run([*docker, "rm", "-f", name, name + "-files"], capture_output=True, timeout=45)
            volume_removal = subprocess.run([*docker, "volume", "rm", volume], capture_output=True, timeout=45)
            if removal.returncode or volume_removal.returncode:
                raise BoatError("Smoke container/volume cleanup failed; session must still stop the VM")

    def save_template(self, name: str) -> dict:
        """Stop first, then name the completed clean filesystem snapshot."""
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", name):
            raise ValueError("invalid template name")
        containers = subprocess.run([*self.docker_prefix, "ps", "-aq"], capture_output=True, text=True, timeout=30, check=True).stdout.strip()
        if containers:
            raise BoatError("A warm template cannot contain attempt containers")
        # Flush committed Docker layers before the provider captures its stopped
        # filesystem. This cannot repair a provider's incomplete restore.
        subprocess.run(self.command(["sync"]), capture_output=True, timeout=30, check=True)
        self._audit("template-prestop.json", {"id": self.id, "containers": [], "filesystem_synced": True, "images": self._images})
        self.close()
        if self.stop_record.get("forced") or not self.stop_record.get("snapshot_available") or not self.stop_record.get("snapshot_completed_at"):
            raise BoatError("Cannot template a machine without a completed stopped snapshot")
        self.api.call("POST", "/named-snapshots", {"sandboxId": self.id, "name": name})
        deadline = time.monotonic() + 600
        while True:
            data = self.api.call("GET", "/named-snapshots/" + urllib.parse.quote(name, safe=""))
            snapshot = data.get("snapshot", data)
            if snapshot.get("status") == "ready":
                record = {key: snapshot[key] for key in ("id", "name", "status", "sandboxId", "snapshotId", "createdAt") if key in snapshot}
                self._audit("template.json", record)
                return record
            if snapshot.get("status") == "failed" or time.monotonic() >= deadline:
                raise BoatError("Warm template snapshot did not become ready")
            time.sleep(2)

    def close(self) -> None:
        if self._closed:
            return
        self._closing = True
        self._cleanup_deadline = time.monotonic() + self.options.get("stop_seconds", 120)
        try:
            if self._pending_provision and self.api and not self.id:
                # Recover the SAME idempotent create/fork after an interrupted or
                # lost response, then stop that machine rather than leaking it.
                self._safe_provision(*self._pending_provision)
            if self.id and self.api:
                forced = False
                self._stage("checking-stop-state")
                current = self._request("GET", f"/sandboxes/{self.id}")
                info = current.get("sandbox", current)
                if info.get("state") not in {"stopped", "archived"}:
                    try:
                        self._stage("stopping")
                        self._request("POST", f"/sandboxes/{self.id}/stop", {})
                        normal_budget = self._timeout(self.options.get("stop_seconds", 120)) * 2 / 3
                        info = self._wait({"stopped", "archived"}, timeout=normal_budget)
                    except (BoatError, KeyboardInterrupt):
                        # A dropped stop response can already have completed.
                        # Inspect state before a destructive force request.
                        current = self._request("GET", f"/sandboxes/{self.id}")
                        info = current.get("sandbox", current)
                        if info.get("state") not in {"stopped", "archived"}:
                            forced = True
                            self._stage("force-stopping")
                            self._request("POST", f"/sandboxes/{self.id}/stop", {"force": True})
                            info = self._wait({"stopped", "archived"}, timeout=self._timeout(self.options.get("stop_seconds", 120)))
                self.stop_record = {"id": self.id, "state": info["state"], "forced": forced, "snapshot_completed_at": info.get("snapshotCompletedAt"), "snapshot_available": info.get("snapshotAvailable")}
                self._audit("stopped.json", self.stop_record)
                self._stage("stopped", state=info["state"], forced=forced)
            self._closed = True
        except BaseException as exc:
            self._audit("stop-error.json", {"id": self.id, "stage": self._stage_name, "error_type": type(exc).__name__, "code": getattr(exc, "code", None), "ttl_deadman_retained": True})
            raise
        finally:
            self._closing = False
            if self._previous_sigterm is not None:
                signal.signal(signal.SIGTERM, self._previous_sigterm)
                self._previous_sigterm = None
            if self._private:
                self._private.cleanup()
                self._private = None

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("doctor", "prepare", "smoke"))
    parser.add_argument("--config", type=Path, required=True, help="JSON transport config or campaign containing transport")
    parser.add_argument("--audit-dir", type=Path)
    parser.add_argument("--repo-root", type=Path, default=HERE.parent)
    parser.add_argument("--snapshot", help="prepare: stopped, clean named warm template")
    parser.add_argument("--verify", action="store_true", help="prepare: exercise offline native FT2 and binary export before stopping")
    parser.add_argument("--image-bundle-out", type=Path, help="prepare: exclusive absolute controller path for both exact images")
    parser.add_argument("--image-bundle-max-bytes", type=int, default=BUNDLE_MAX_BYTES)
    parser.add_argument("--image-bundle-timeout", type=int, default=300)
    parser.add_argument("--image-bundle-reserve-bytes", type=int, default=BUNDLE_RESERVE_BYTES)
    args = parser.parse_args()
    if (args.snapshot or args.verify or args.image_bundle_out) and args.command != "prepare":
        parser.error("--snapshot, --verify, and --image-bundle-out are only supported for prepare")
    if args.image_bundle_out is not None and not args.image_bundle_out.is_absolute():
        parser.error("--image-bundle-out must be an absolute controller path")
    if args.image_bundle_out is not None:
        if args.image_bundle_timeout <= 0:
            parser.error("--image-bundle-timeout must be positive")
        _bundle_export_preflight(args.image_bundle_out, args.image_bundle_max_bytes, args.image_bundle_reserve_bytes)
    config = json.loads(args.config.read_text())
    config = config.get("transport", config)
    if args.command == "doctor":
        print(json.dumps(doctor(config), indent=2))
    else:
        if not args.audit_dir:
            parser.error("prepare/smoke requires --audit-dir for provenance")
        with BoatSession(config, audit_dir=args.audit_dir) as session:
            manifest = session.prepare(args.repo_root) if args.command == "prepare" else session.smoke(args.audit_dir / "smoke")
            if args.image_bundle_out is not None:
                manifest["image_bundle"] = session.export_image_bundle(
                    args.image_bundle_out, max_bytes=args.image_bundle_max_bytes,
                    timeout=args.image_bundle_timeout, reserve_bytes=args.image_bundle_reserve_bytes)
            if args.verify:
                manifest["smoke"] = session.smoke(args.audit_dir / "smoke")
            if args.snapshot:
                session.save_template(args.snapshot)
            print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
