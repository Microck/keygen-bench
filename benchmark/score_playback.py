"""Fixed-frame capture of the pinned FT2 replayer, including authored restarts.

The native patch only observes row execution and bypasses the export stop rule.
It does not edit modules, simulate timing, or reset playback between cycles.
PCM is deterministic for a given binary; floating-point mixing is not promised
bit-identical across architectures, compiler versions, or compiler flags.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import resource
import shutil
import tempfile
import time
import wave

SOURCE_REPOSITORY = "https://github.com/mova77/fast-tracker2.git"
SOURCE_COMMIT = "6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d"
SAMPLE_RATE = 44100
TRACE_SCHEMA = 1
PATCH_PATH = Path(__file__).with_name("ft2_capture.patch")
DEFAULT_BINARY = Path.home() / ".cache/keygen-benchmark/ft2-analysis"
MAX_WORKER_MEMORY = 2 * 1024 ** 3
MAX_RENDERER_MEMORY = 512 * 1024 ** 2
MAX_TRACE_BYTES = 64 * 1024 ** 2
MAX_TRACE_ROWS = 200_000
NATIVE_MEMORY_BASELINE = 64 * 1024 ** 2
_DEADLINE = ContextVar("scoring_deadline", default=None)
_HASH_CACHE = {}
_DEPENDENCY_CACHE = {}


class AnalysisDeadlineError(RuntimeError):
    """Evaluation did not finish within its declared wall-clock budget."""


@contextmanager
def analysis_budget(seconds: float):
    deadline = time.monotonic() + seconds
    current = _DEADLINE.get()
    token = _DEADLINE.set(min(current, deadline) if current is not None else deadline)
    try:
        yield
    finally:
        _DEADLINE.reset(token)


def bounded_timeout(seconds: float, phase: str = "analysis") -> float:
    deadline = _DEADLINE.get()
    if deadline is None:
        return seconds
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise AnalysisDeadlineError(f"{phase} exceeded the evaluation wall-clock budget")
    return min(seconds, remaining)


def check_deadline(phase: str = "analysis") -> None:
    bounded_timeout(1, phase)


def _file_identity(path: Path) -> tuple:
    check_deadline("provenance")
    resolved = Path(path).resolve(strict=True)
    stat = resolved.stat()
    return str(resolved), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def validate_xm_header(xm_path: Path) -> int:
    """Reject a plainly invalid artifact before renderer or RAM admission."""
    with Path(xm_path).open("rb") as stream:
        header = stream.read(80)
    if len(header) < 80 or header[:17] != b"Extended Module: ":
        raise ValueError(f"capture requires an XM module: {xm_path}")
    channels = struct.unpack_from("<H", header, 68)[0]
    if not 1 <= channels <= 32:
        raise ValueError(f"unsupported XM channel count: {channels}")
    return channels


def capture_memory_budget(xm_path: Path, seconds: float) -> int:
    """Admission estimate, distinct from the child's hard address-space cap.

    The pinned native renderer measured 10 MiB peak RSS for a 20-second tiny
    looping XM on aarch64. Reserve a 64 MiB native baseline, four input copies
    for loading/sample conversion, and 4 KiB per possible decoded trace row.
    Header BPM may exceed normal tracker tempo; include it in the row bound.
    """
    validate_xm_header(xm_path)
    size = Path(xm_path).stat().st_size
    if size > 64 * 1024 ** 2:
        raise RuntimeError("XM exceeds the bounded 64 MiB renderer input limit")
    with Path(xm_path).open("rb") as stream:
        stream.seek(78)
        bpm = int.from_bytes(stream.read(2), "little")
    rows = min(MAX_TRACE_ROWS + 2, math.ceil(seconds * max(255, bpm) / 2.5) + 2)
    return NATIVE_MEMORY_BASELINE + size * 4 + rows * 4096


def renderer_environment() -> dict[str, str]:
    """Never pass provider credentials, proxy settings or loader overrides."""
    return {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
            "SDL_AUDIODRIVER": "dummy", "SDL_VIDEODRIVER": "dummy"}


def available_memory() -> int:
    return _available_memory(Path("/proc/meminfo"), Path("/sys/fs/cgroup"))


def _available_memory(meminfo: Path, cgroup: Path) -> int:
    available = os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    # Linux's MemAvailable includes reclaimable page cache. MemFree and
    # SC_AVPHYS_PAGES alone incorrectly reject work on a warm-cache host.
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemAvailable:"):
                available = max(0, int(line.split()[1])) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass  # Non-Linux or unavailable procfs retains the sysconf fallback.
    # Host availability can still exceed this process's cgroup allowance.
    for root, limit_name, used_name in (
            (cgroup, "memory.max", "memory.current"),
            (cgroup / "memory", "memory.limit_in_bytes", "memory.usage_in_bytes")):
        try:
            limit = int((root / limit_name).read_text())
            used = int((root / used_name).read_text())
        except (OSError, ValueError):
            continue
        available = min(available, max(0, limit - used))
    return available


def require_resources(memory_bytes: int = 0, disk_bytes: int = 0,
                      directory: Path | None = None) -> None:
    """Reject bounded-work requests before array or temporary-file allocation."""
    check_deadline("resource admission")
    if memory_bytes > MAX_WORKER_MEMORY:
        raise RuntimeError(f"evaluation needs {memory_bytes} RAM bytes; per-worker limit is {MAX_WORKER_MEMORY}")
    if memory_bytes and available_memory() < memory_bytes + 256 * 1024 ** 2:
        raise RuntimeError(f"insufficient evaluation RAM for {memory_bytes} bytes plus reserve")
    if disk_bytes:
        directory = Path(directory or tempfile.gettempdir())
        while not directory.exists():
            directory = directory.parent
        free = shutil.disk_usage(directory).free
        if free < disk_bytes + 256 * 1024 ** 2:
            raise RuntimeError(f"insufficient evaluation disk at {directory}: need {disk_bytes} bytes plus reserve, have {free}")


def _child_limits() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (MAX_RENDERER_MEMORY, MAX_RENDERER_MEMORY))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024 ** 2, 256 * 1024 ** 2))


def binary_dependencies(binary: Path) -> dict:
    """Cache resolved libraries only while binary, loader and library identities match."""
    loader = Path("/etc/ld.so.cache")
    key = (_file_identity(binary), _file_identity(loader) if loader.exists() else None)
    cached = _DEPENDENCY_CACHE.get(str(binary))
    if cached is not None and cached["key"] == key:
        try:
            valid = all(_file_identity(Path(name)) == identity
                        for name, identity in cached["identities"].items())
        except OSError:
            valid = False
        if valid:
            return cached["hashes"].copy()
    process = subprocess.run(["/usr/bin/ldd", str(binary)], env=renderer_environment(),
                             capture_output=True, text=True,
                             timeout=bounded_timeout(30, "library provenance"))
    if process.returncode:
        raise RuntimeError(f"cannot fingerprint runtime libraries for {binary}")
    libraries, identities = {}, {}
    for line in process.stdout.splitlines():
        check_deadline("library provenance")
        for token in line.split():
            if token.startswith("/"):
                source = Path(token)
                identity = _file_identity(source)
                path = Path(identity[0])
                identities[str(source)] = identity
                libraries[str(path)] = _sha256(path)
                break
        if "not found" in line:
            raise RuntimeError(f"missing runtime library for {binary}")
    _DEPENDENCY_CACHE[str(binary)] = {"key": key, "identities": identities, "hashes": libraries.copy()}
    return libraries


def _sha256(path: Path) -> str:
    identity = _file_identity(path)
    key = str(Path(path))
    cached = _HASH_CACHE.get(key)
    if cached is not None and cached[0] == identity:
        return cached[1]
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            check_deadline("file provenance")
            digest.update(block)
    if _file_identity(path) != identity:
        raise RuntimeError(f"file changed while fingerprinting: {path}")
    value = digest.hexdigest()
    _HASH_CACHE[key] = identity, value
    return value


def renderer_identity() -> dict:
    """Return verified binary/source/patch provenance used in scoring caches."""
    binary = Path(os.environ.get("KEYGEN_FT2_ANALYSIS", str(DEFAULT_BINARY))).expanduser().resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise FileNotFoundError(
            f"FT2 analysis binary unavailable: {binary}. Build it with "
            "python scripts/build-ft2-analysis.py, or set KEYGEN_FT2_ANALYSIS."
        )
    metadata_path = binary.with_name(binary.name + ".json")
    if not metadata_path.is_file():
        raise RuntimeError(f"FT2 analysis provenance missing: {metadata_path}; rebuild the binary")
    metadata = json.loads(metadata_path.read_text())
    binary_digest = _sha256(binary)
    patch_digest = _sha256(PATCH_PATH)
    if (metadata.get("source_commit") != SOURCE_COMMIT
            or metadata.get("patch_sha256") != patch_digest
            or metadata.get("binary_sha256") != binary_digest):
        raise RuntimeError("FT2 analysis binary/source/patch provenance mismatch; rebuild the binary")
    return {
        "name": "ft2-runtime-capture-v1",
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": SOURCE_COMMIT,
        "patch_sha256": patch_digest,
        "binary_sha256": binary_digest,
        "binary_path": str(binary),
        "runtime_libraries": binary_dependencies(binary),
        "host_architecture": platform.machine(),
        "provenance_sha256": _sha256(metadata_path),
        "architecture": metadata.get("architecture", platform.machine()),
        "compiler": metadata.get("compiler"),
        "compile_flags": metadata.get("compile_flags"),
        "sample_rate": SAMPLE_RATE,
        "bit_depth": 16,
        "amplification": 8,
        "trace_schema": TRACE_SCHEMA,
        "cross_architecture_bit_exact": False,
    }


def capture(xm_path: Path, out_dir: Path, seconds: float,
            solo_channel: int | None = None) -> dict:
    """Capture continuous FT2 playback and exact executed-row timestamps.

    ``rows`` are JSONL kind=``row`` records, emitted when FT2 reads a new row.
    ``frame`` is the first PCM frame of that row's first tick. Pattern-delay
    repeats do not read new rows. Speed/BPM reflect effects on the entered row.
    Transition flags describe the incoming edge, not commands on the new row.
    The first row has from_order/from_row=-1 and transition=``start``.

    The caller owns playback.wav and trace.jsonl and must remove temporary
    captures after extracting its metrics or preview. No persistent process is
    started. Solos mute mixer output only; all channels' effects still execute.
    """
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError("capture seconds must be a finite number greater than 0 and at most 900")
    if not math.isfinite(seconds) or not 0 < seconds <= 900:
        raise ValueError("capture seconds must be greater than 0 and at most 900")
    frames = round(seconds * SAMPLE_RATE)
    if frames < 1:
        raise ValueError("capture duration must round to at least one PCM frame")
    xm_path = Path(xm_path).resolve(strict=True)
    module_channels = validate_xm_header(xm_path)
    if solo_channel is not None and (isinstance(solo_channel, bool)
            or not isinstance(solo_channel, int)
            or not 0 <= solo_channel < module_channels):
        raise ValueError(f"solo_channel must be in 0..{module_channels - 1}")

    identity = renderer_identity()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "playback.wav"
    trace_path = out_dir / "trace.jsonl"
    require_resources(capture_memory_budget(xm_path, seconds), frames * 4 + MAX_TRACE_BYTES, out_dir)
    environment = renderer_environment()
    environment.update({
        "KEYGEN_FT2_CAPTURE_FRAMES": str(frames),
        "KEYGEN_FT2_CAPTURE_TRACE": str(trace_path),
    })
    if solo_channel is not None:
        environment["KEYGEN_FT2_CAPTURE_SOLO"] = str(solo_channel)
    command = [identity["binary_path"], "--cli", "render", str(xm_path), str(wav_path),
               "--rate", str(SAMPLE_RATE), "--bits", "16", "--amp", "8", "--loops", "0"]
    try:
        # Fresh HOME also isolates SDL/config side effects outside the patched
        # configuration loader. It contains no input or durable output files.
        with tempfile.TemporaryDirectory(prefix="ft2-capture-home-") as home:
            environment["HOME"] = home
            environment["XDG_CONFIG_HOME"] = home
            with (out_dir / "renderer.log").open("w+") as log:
                process = subprocess.run(command, cwd=out_dir, env=environment,
                                         stdout=log, stderr=log, preexec_fn=_child_limits,
                                         timeout=bounded_timeout(max(120, seconds * 4), "native playback"))
                if process.returncode:
                    log.seek(max(0, log.tell() - 4000))
                    detail = log.read()
                    raise RuntimeError(f"FT2 capture exited {process.returncode}: {detail}")
        with wave.open(str(wav_path), "rb") as audio:
            observed = (audio.getnchannels(), audio.getsampwidth(),
                        audio.getframerate(), audio.getnframes())
        if observed != (2, 2, SAMPLE_RATE, frames):
            raise RuntimeError(f"FT2 capture produced unexpected WAV format/frame count: {observed}")
        if wav_path.stat().st_size != 44 + frames * 4:
            raise RuntimeError("FT2 capture WAV payload length does not match its header")
        if trace_path.stat().st_size > MAX_TRACE_BYTES:
            raise RuntimeError(f"FT2 capture trace exceeds {MAX_TRACE_BYTES} bytes")
        trace = []
        with trace_path.open() as stream:
            for line in stream:
                check_deadline("native trace decoding")
                if len(trace) > MAX_TRACE_ROWS:
                    raise RuntimeError(f"FT2 capture exceeds {MAX_TRACE_ROWS} trace rows")
                if line.strip():
                    trace.append(json.loads(line))
        if (not trace or trace[0].get("kind") != "header"
                or trace[0].get("schema") != TRACE_SCHEMA
                or trace[0].get("frame_budget") != frames
                or trace[-1] != {"kind": "end", "frames": frames}):
            raise RuntimeError("FT2 capture trace is incomplete or has an unsupported schema")
        rows = trace[1:-1]
        if not rows or rows[0].get("frame") != 0:
            raise RuntimeError("FT2 capture trace has no initial row at frame zero")
        previous = -1
        for row in rows:
            if row.get("kind") != "row" or not previous < row["frame"] < frames:
                raise RuntimeError("FT2 capture trace row frames are not strictly increasing")
            previous = row["frame"]
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, wave.Error) as exc:
        wav_path.unlink(missing_ok=True)
        trace_path.unlink(missing_ok=True)
        raise RuntimeError(f"FT2 capture failed for {xm_path}: {exc}") from exc
    return {
        "wav_path": str(wav_path),
        "trace_path": str(trace_path),
        "rows": rows,
        "frames": frames,
        "sample_rate": SAMPLE_RATE,
        "duration_seconds": frames / SAMPLE_RATE,
        "solo_channel": solo_channel,
        "module_channels": module_channels,
        "renderer": identity,
    }
