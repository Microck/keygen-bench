"""Local artifact capacity checks and credential screening."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil

_SECRET_PREFIX = re.compile(rb"(?:oc_sk_|sk-ant-|sk-proj-)[A-Za-z0-9_-]{20,}")


class ArtifactStore:
    def __init__(self, config: dict):
        if set(config) != {"reserve_bytes", "peak_bytes_per_attempt"}:
            raise ValueError("Storage declares only the local reserve and per-attempt peak")
        self.reserve_bytes = config["reserve_bytes"]
        self.peak_bytes_per_attempt = config["peak_bytes_per_attempt"]
        if any(type(value) is not int or value <= 0 for value in (self.reserve_bytes, self.peak_bytes_per_attempt)):
            raise ValueError("Storage reserve and peak limits must be positive integers")

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
        return {"local_free_bytes": free, "required_local_bytes": required}

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
