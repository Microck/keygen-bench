#!/usr/bin/env python3
"""Build the benchmark-only FT2 capture binary from pinned, patched source.

Linux dependencies: C compiler, git, pkg-config, libsdl2-dev, libmicrohttpd-dev.
Default output: ~/.cache/keygen-benchmark/ft2-analysis (plus provenance JSON).
No downloaded source or binary is written into the benchmark repository.

For an existing pinned checkout:
  python scripts/build-ft2-analysis.py --source /path/to/fast-tracker2

For dependencies in a local prefix, pass --no-pkg-config and set CFLAGS and
LDFLAGS, including -lSDL2 -lmicrohttpd and any required runtime rpath. CC,
CFLAGS, LDFLAGS and TMPDIR are honored. Builds do not use fast-math or native
CPU tuning by default. A binary is reproducible only with the same toolchain,
architecture and dependency versions; its SHA-256 is part of score provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmark.score_playback import DEFAULT_BINARY, PATCH_PATH, SOURCE_COMMIT, SOURCE_REPOSITORY


def run(command: list[str], cwd: Path | None = None) -> str:
    process = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if process.returncode:
        raise RuntimeError(f"Command failed ({process.returncode}): {shlex.join(command)}\n"
                           f"{process.stderr}{process.stdout}")
    return process.stdout.strip()


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def build(source: Path, output: Path, no_pkg_config: bool) -> dict:
    pin = run(["git", "rev-parse", "HEAD"], source)
    if pin != SOURCE_COMMIT:
        raise RuntimeError(f"Source must be pinned to {SOURCE_COMMIT}, found {pin}")
    patch = str(PATCH_PATH.resolve())
    clean_patch = subprocess.run(["git", "apply", "--check", patch], cwd=source,
                                 capture_output=True, text=True)
    if clean_patch.returncode == 0:
        run(["git", "apply", patch], source)
    else:
        # Accept an already-patched checkout so a failed compiler invocation can
        # be retried without another download or another source copy.
        run(["git", "apply", "--reverse", "--check", patch], source)
    expected_diff = PATCH_PATH.read_text()
    actual_diff = run(["git", "diff", "--no-ext-diff", "--binary", "HEAD", "--", "src"], source)
    if actual_diff != expected_diff.strip():
        raise RuntimeError("Source contains changes other than the benchmark capture patch")

    compiler = shlex.split(os.environ.get("CC", "cc"))
    if not compiler or shutil.which(compiler[0]) is None:
        raise RuntimeError("C compiler unavailable; install build-essential or set CC")
    cflags = ["-DNDEBUG", "-O2", "-pthread"]
    cflags += shlex.split(os.environ.get("CFLAGS", ""))
    ldflags = shlex.split(os.environ.get("LDFLAGS", ""))
    if not no_pkg_config:
        if shutil.which("pkg-config") is None:
            raise RuntimeError("Install pkg-config, libsdl2-dev and libmicrohttpd-dev")
        cflags += shlex.split(run(["pkg-config", "--cflags", "sdl2", "libmicrohttpd"]))
        ldflags += shlex.split(run(["pkg-config", "--libs", "sdl2", "libmicrohttpd"]))
    ldflags += ["-lm"]
    sources = sorted(str(path) for directory in (
        "src/gfxdata", "src/mixer", "src/scopes", "src/modloaders", "src/smploaders", "src"
    ) for path in (source / directory).glob("*.c"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ft2-analysis-build-") as work:
        binary = Path(work) / "ft2-analysis"
        run(compiler + cflags + sources + ldflags + ["-o", str(binary)], source)
        metadata = {
            "source_repository": SOURCE_REPOSITORY,
            "source_commit": SOURCE_COMMIT,
            "patch_sha256": digest(PATCH_PATH),
            "binary_sha256": digest(binary),
            "architecture": platform.machine(),
            "system": platform.system(),
            "compiler": run(compiler + ["--version"]).splitlines()[0],
            "compile_flags": cflags,
            "link_flags": ldflags,
        }
        staged = output.with_name(output.name + ".new")
        shutil.copy2(binary, staged)
        os.replace(staged, output)
    metadata_path = output.with_name(output.name + ".json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, help="Existing checkout at the exact source pin")
    parser.add_argument("--output", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--no-pkg-config", action="store_true",
                        help="Use CFLAGS/LDFLAGS for all dependency include and link flags")
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.error("This native build recipe currently supports Linux only")
    output = args.output.expanduser().resolve()
    try:
        if args.source is not None:
            metadata = build(args.source.resolve(strict=True), output, args.no_pkg_config)
        else:
            with tempfile.TemporaryDirectory(prefix="keygen-ft2-source-") as work:
                source = Path(work)
                run(["git", "init", "--quiet"], source)
                run(["git", "remote", "add", "origin", SOURCE_REPOSITORY], source)
                run(["git", "fetch", "--depth", "1", "origin", SOURCE_COMMIT], source)
                run(["git", "checkout", "--detach", "--quiet", "FETCH_HEAD"], source)
                metadata = build(source, output, args.no_pkg_config)
    except (OSError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"binary": str(output), **metadata}, indent=2))


if __name__ == "__main__":
    main()
