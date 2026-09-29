"""Fixed-frame capture of the pinned FT2 replayer, including authored restarts.

The native patch only observes row execution and bypasses the export stop rule.
It does not edit modules, simulate timing, or reset playback between cycles.
PCM is deterministic for a given binary; floating-point mixing is not promised
bit-identical across architectures, compiler versions, or compiler flags.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import tempfile
import wave

SOURCE_REPOSITORY = "https://github.com/mova77/fast-tracker2.git"
SOURCE_COMMIT = "6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d"
SAMPLE_RATE = 44100
TRACE_SCHEMA = 1
PATCH_PATH = Path(__file__).with_name("ft2_capture.patch")
DEFAULT_BINARY = Path.home() / ".cache/keygen-benchmark/ft2-analysis"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    with xm_path.open("rb") as stream:
        header = stream.read(80)
    if len(header) < 80 or header[:17] != b"Extended Module: ":
        raise ValueError(f"capture requires an XM module: {xm_path}")
    module_channels = struct.unpack_from("<H", header, 68)[0]
    if not 1 <= module_channels <= 32:
        raise ValueError(f"unsupported XM channel count: {module_channels}")
    if solo_channel is not None and (isinstance(solo_channel, bool)
            or not isinstance(solo_channel, int)
            or not 0 <= solo_channel < module_channels):
        raise ValueError(f"solo_channel must be in 0..{module_channels - 1}")

    identity = renderer_identity()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "playback.wav"
    trace_path = out_dir / "trace.jsonl"
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith("KEYGEN_FT2_CAPTURE_"):
            del environment[name]
    environment.update({
        "SDL_AUDIODRIVER": "dummy",
        "SDL_VIDEODRIVER": "dummy",
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
            process = subprocess.run(command, cwd=out_dir, env=environment,
                                     capture_output=True, text=True,
                                     timeout=max(120, seconds * 4))
        if process.returncode:
            detail = (process.stderr + "\n" + process.stdout).strip()[-4000:]
            raise RuntimeError(f"FT2 capture exited {process.returncode}: {detail}")
        with wave.open(str(wav_path), "rb") as audio:
            observed = (audio.getnchannels(), audio.getsampwidth(),
                        audio.getframerate(), audio.getnframes())
        if observed != (2, 2, SAMPLE_RATE, frames):
            raise RuntimeError(f"FT2 capture produced unexpected WAV format/frame count: {observed}")
        if wav_path.stat().st_size != 44 + frames * 4:
            raise RuntimeError("FT2 capture WAV payload length does not match its header")
        with trace_path.open() as stream:
            trace = [json.loads(line) for line in stream if line.strip()]
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
