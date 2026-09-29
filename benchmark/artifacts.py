"""Immutable, verified result export; credentials and worker homes never leave the controller."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

_FILES = {"status.json", "trajectory.json", "transport.json", "transport.jsonl", "responses.jsonl", "worker-result.json", "worker.log", "profile.json", "module-info.json", "campaign.json", "readiness.json"}
_DIRS = {"submission", "canonical", "visualizer", "playback", "evaluations", "transport"}
_SECRET_PREFIX = re.compile(rb"(?:oc_sk_|sk-ant-|sk-proj-)[A-Za-z0-9_-]{20,}")


def _hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ArtifactStore:
    def __init__(self, config: dict):
        self.backend = config.get("backend")
        if self.backend not in {"rclone", "local"}:
            raise ValueError("Artifact storage backend must be rclone or local")
        self.config = dict(config)
        if self.backend == "local":
            directory = Path(config.get("directory", ""))
            if not directory.is_absolute():
                raise ValueError("Local archive directory must be absolute")
            self.remote = str(directory.resolve())
        else:
            self.remote = config.get("remote", "")
            if (not isinstance(self.remote, str) or not re.fullmatch(r"[A-Za-z0-9_-]+:[A-Za-z0-9_./-]+", self.remote)
                    or ".." in self.remote.partition(":")[2].split("/")):
                raise ValueError("Use an explicit dedicated remote artifact path")
        self.reserve_bytes = config.get("reserve_bytes", 1024**3)
        self.peak_bytes_per_attempt = config.get("peak_bytes_per_attempt", 1024**3)
        if any(type(value) is not int or value <= 0 for value in (self.reserve_bytes, self.peak_bytes_per_attempt)):
            raise ValueError("Storage reserve and peak limits must be positive integers")
        self.evict_after_archive = config.get("evict_after_archive", False)
        if type(self.evict_after_archive) is not bool:
            raise ValueError("Artifact eviction flag must be boolean")
        self.binary = shutil.which("rclone") if self.backend == "rclone" else None
        if self.backend == "rclone" and self.binary is None:
            raise RuntimeError("rclone is required for persistent artifact export")
        self._remote_free_bytes: int | None = None

    def _command(self, *args: str, timeout: int = 600) -> str:
        result = subprocess.run([self.binary, *args], capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            # Provider errors may contain credentials; preserve only stage and exit status.
            raise RuntimeError(f"Artifact storage {args[0]} failed with exit status {result.returncode}")
        return result.stdout

    def preflight(self, local_root: Path, parallelism: int, peak_per_attempt: int | None = None) -> dict:
        if type(parallelism) is not int or parallelism <= 0:
            raise ValueError("Storage parallelism must be a positive integer")
        peak = self.peak_bytes_per_attempt if peak_per_attempt is None else peak_per_attempt
        if type(peak) is not int or peak <= 0:
            raise ValueError("Storage peak estimate must be positive")
        ancestor = local_root.resolve()
        while not ancestor.exists():
            ancestor = ancestor.parent
        free = shutil.disk_usage(ancestor).free
        required = self.reserve_bytes + parallelism * peak
        if free < required:
            raise RuntimeError(f"Insufficient local artifact space: {free} bytes available, {required} required")
        if self.backend == "rclone":
            if self._remote_free_bytes is None:
                quota = json.loads(self._command("about", self.remote.split(":", 1)[0] + ":", "--json", timeout=60))
                self._remote_free_bytes = quota.get("free")
            remote_free = self._remote_free_bytes
        else:
            archive_root = Path(self.remote)
            while not archive_root.exists():
                archive_root = archive_root.parent
            remote_free = shutil.disk_usage(archive_root).free
        if not isinstance(remote_free, int) or remote_free < required:
            raise RuntimeError("Dedicated archive storage cannot demonstrate sufficient available capacity")
        return {"remote": self.remote, "local_free_bytes": free, "remote_free_bytes": remote_free, "required_local_bytes": required}

    @staticmethod
    def _files(run_dir: Path) -> list[Path]:
        files = []
        for path in sorted(run_dir.rglob("*")):
            relative = path.relative_to(run_dir)
            if relative.parts[0] not in _DIRS and str(relative) not in _FILES:
                continue
            if path.is_symlink():
                raise ValueError("Do not archive symlinks from an attempt")
            if path.is_file():
                files.append(path)
        if not (run_dir / "status.json").is_file():
            raise ValueError("Only terminal, identified attempts can be exported")
        status = json.loads((run_dir / "status.json").read_text())
        if not status.get("model") or status.get("status") in {"RESERVED", "RUNNING"}:
            raise ValueError("Attempt is not terminal and identified")
        return files

    @staticmethod
    def check_secrets(path: Path) -> None:
        if path.suffix not in {".json", ".jsonl", ".log", ".txt"}:
            return
        secrets = [value.encode() for key, value in os.environ.items()
                   if re.search(r"(?:key|token)$|(?:^|_)(?:key|token|secret)(?:_|$)", key, re.I) and len(value) >= 16]
        overlap = max([256, *(len(value) for value in secrets)])
        tail = b""
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                window = tail + block
                if _SECRET_PREFIX.search(window) or any(value in window for value in secrets):
                    raise ValueError(f"Sensitive credential material prevents export of {path.name}")
                tail = window[-overlap:]

    def archive_attempt(self, run_dir: Path) -> dict:
        run_dir = run_dir.resolve()
        files = self._files(run_dir)
        self.preflight(run_dir, 1)
        for path in files:
            self.check_secrets(path)
        manifest = {str(path.relative_to(run_dir)): {"bytes": path.stat().st_size, "sha256": _hash(path)} for path in files}
        expanded_bytes = sum(record["bytes"] for record in manifest.values())
        self.preflight(run_dir, 1, max(self.peak_bytes_per_attempt, expanded_bytes))
        manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        generation = hashlib.sha256(manifest_bytes).hexdigest()
        with tempfile.TemporaryDirectory(prefix="keygen-export-", dir=run_dir.parent) as temporary:
            bundle = Path(temporary) / "attempt.tar.gz"
            manifest_path = Path(temporary) / "manifest.json"
            manifest_path.write_bytes(manifest_bytes + b"\n")
            with bundle.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    for name, path in [("manifest.json", manifest_path), *((str(path.relative_to(run_dir)), path) for path in files)]:
                        member = tarfile.TarInfo(name)
                        member.size = path.stat().st_size
                        member.mode = 0o600
                        with path.open("rb") as stream:
                            archive.addfile(member, stream)
            if any(_hash(path) != manifest[str(path.relative_to(run_dir))]["sha256"] for path in files):
                raise RuntimeError("Attempt changed during artifact export; no archive uploaded")
            destination = self.remote.rstrip("/") + "/" + generation + "/attempt.tar.gz"
            expected_md5 = _hash(bundle, "md5")
            if self.backend == "rclone":
                self._command("copyto", str(bundle), destination, "--immutable", "--checksum")
                checksum = self._command("md5sum", destination).strip().split()
                verified = len(checksum) >= 2 and checksum[0] == expected_md5
            else:
                target = Path(destination)
                if target.exists():
                    if _hash(target) != _hash(bundle):
                        raise RuntimeError("Immutable local archive generation has changed")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("xb") as stream, bundle.open("rb") as source:
                        shutil.copyfileobj(source, stream)
                verified = _hash(target) == _hash(bundle)
            if not verified:
                raise RuntimeError("Archive checksum verification failed; local files retained")
            if self._remote_free_bytes is not None:
                self._remote_free_bytes -= bundle.stat().st_size
            return {"remote": destination, "generation": generation, "bytes": bundle.stat().st_size,
                    "sha256": _hash(bundle), "md5": expected_md5, "files": manifest, "verified": True,
                    "storage": self.config}

    def verify_archive(self, metadata: dict) -> bool:
        self._validate_metadata(metadata)
        if self.backend == "local":
            return Path(metadata["remote"]).is_file() and _hash(Path(metadata["remote"])) == metadata.get("sha256")
        checksum = self._command("md5sum", metadata["remote"]).strip().split()
        return len(checksum) >= 2 and checksum[0] == metadata.get("md5")

    def _validate_metadata(self, metadata: dict) -> None:
        generation = metadata.get("generation", "")
        if not re.fullmatch(r"[a-f0-9]{64}", generation):
            raise ValueError("Invalid artifact generation")
        if metadata.get("remote") != self.remote.rstrip("/") + "/" + generation + "/attempt.tar.gz":
            raise ValueError("Archive does not belong to the configured storage root")
        if type(metadata.get("bytes")) is not int or metadata["bytes"] <= 0:
            raise ValueError("Invalid archive byte count")
        if not isinstance(metadata.get("files"), dict) or not metadata["files"]:
            raise ValueError("Missing archive file manifest")
        for name, record in metadata["files"].items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("Invalid archive member path")
            if path.parts[0] not in _DIRS and name not in _FILES:
                raise ValueError("Archive contains non-result controller data")
            if type(record.get("bytes")) is not int or record["bytes"] < 0 or not re.fullmatch(r"[a-f0-9]{64}", record.get("sha256", "")):
                raise ValueError("Invalid archive member identity")

    def restore_attempt(self, metadata: dict, run_dir: Path) -> Path:
        self._validate_metadata(metadata)
        run_dir = run_dir.resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        expanded_bytes = sum(record["bytes"] for record in metadata["files"].values())
        self.preflight(run_dir, 1, metadata["bytes"] + expanded_bytes)
        with tempfile.TemporaryDirectory(prefix="keygen-restore-", dir=run_dir.parent) as temporary:
            bundle = Path(temporary) / "attempt.tar.gz"
            if self.backend == "rclone":
                remote_stat = json.loads(self._command("lsjson", metadata["remote"], "--stat", timeout=60))
                if remote_stat.get("Size") != metadata["bytes"]:
                    raise RuntimeError("Remote artifact size changed; refusing download")
                self._command("copyto", metadata["remote"], str(bundle), "--immutable")
            else:
                source = Path(metadata["remote"])
                if source.stat().st_size != metadata["bytes"]:
                    raise RuntimeError("Local archive size changed")
                shutil.copyfile(source, bundle)
            if bundle.stat().st_size != metadata["bytes"] or _hash(bundle) != metadata["sha256"]:
                raise RuntimeError("Downloaded artifact identity verification failed")
            staging = Path(temporary) / "verified"
            staging.mkdir()
            seen = set()
            with tarfile.open(bundle, "r:gz") as archive:
                for member in archive:
                    if member.name in seen or not member.isfile():
                        raise ValueError("Unexpected archive member type or duplicate")
                    seen.add(member.name)
                    if member.name == "manifest.json":
                        if member.size > 8 * 1024**2:
                            raise ValueError("Archive manifest exceeds limit")
                        stream = archive.extractfile(member)
                        if json.load(stream) != metadata["files"]:
                            raise ValueError("Archive manifest changed")
                        continue
                    expected = metadata["files"].get(member.name)
                    if expected is None or member.size != expected["bytes"]:
                        raise ValueError("Archive content differs from pinned manifest")
                    target = staging / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(member) as source, target.open("xb") as output:
                        shutil.copyfileobj(source, output)
                    if _hash(target) != expected["sha256"]:
                        raise ValueError("Archive member identity verification failed")
            if seen != set(metadata["files"]) | {"manifest.json"}:
                raise ValueError("Archive is missing pinned files")
            for name in metadata["files"]:
                target = run_dir / name
                if target.is_symlink():
                    raise ValueError("Restore destination contains a symlink")
                parent = target.parent
                while parent != run_dir:
                    if parent.is_symlink():
                        raise ValueError("Restore destination parent contains a symlink")
                    parent = parent.parent
                if target.exists():
                    if name != "profile.json" and _hash(target) != metadata["files"][name]["sha256"]:
                        raise ValueError("Restore would overwrite changed attempt data")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staging / name, target)
        return run_dir

    def evict(self, run_dir: Path, metadata: dict) -> int:
        if not self.evict_after_archive:
            raise ValueError("Artifact eviction is not enabled")
        run_dir = run_dir.resolve()
        if (Path(__file__).resolve().parents[1] / "legacy") in run_dir.parents:
            raise ValueError("Legacy results must never be evicted")
        if not (run_dir / "profile.json").is_file():
            raise ValueError("Evaluate an attempt before evicting its artifacts")
        if not self.verify_archive(metadata):
            raise RuntimeError("Archive verification failed; local artifacts retained")
        keep = _FILES
        removable = []
        for name, record in metadata["files"].items():
            path = run_dir / name
            if path.is_symlink() or not path.is_file() or _hash(path) != record["sha256"]:
                raise RuntimeError("Attempt data changed; refusing partial eviction")
            if name not in keep:
                removable.append(path)
        reclaimed = sum(path.stat().st_size for path in removable)
        for path in removable:
            path.unlink()
        return reclaimed
