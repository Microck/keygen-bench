#!/usr/bin/env python3
"""Opt-in acceptance check for the pinned FT2 MCP fork, not a music generator.

Uses only Python's standard library. Nothing is downloaded or uploaded.
A native success means the fixture survived author/edit/save/reload/render;
it is not proof of musical quality, all effects, or a seamless song loop.
"""
from __future__ import annotations

import argparse
from array import array
import base64
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import shutil
import struct
import subprocess
import sys
import threading
import time
import wave

PIN = "6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d"
PROTOCOL = "2024-11-05"
# Leave space below the upstream 256-KiB line buffer.
MAX_LINE = 240 * 1024
REQUIRED = {
    "module_new", "module_load", "module_info", "pattern_set_cell",
    "pattern_get_cell", "sample_create_from_pcm", "module_save",
    "module_render", "song_set", "order_set", "pattern_set_length",
}


class CheckError(RuntimeError):
    """A protocol, file, or acceptance check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


def tool_text(result: dict) -> str:
    text = "\n".join(item.get("text", "") for item in result.get("content", [])
                     if item.get("type") == "text")
    require(not result.get("isError", False), text or "MCP tool failed")
    return text


class StdioMCP:
    """Sequential JSON-RPC client with integer IDs and bounded waiting.

    This is a narrow test client, not a general MCP SDK. A queue and separate
    stderr reader avoid deadlocks and keep diagnostics out of JSON parsing.
    """

    def __init__(self, command: list[str], cwd: Path, timeout: float = 30):
        require(timeout > 0 and math.isfinite(timeout), "timeout must be positive")
        self.timeout = timeout
        self.ident = 0
        self.replies: queue.Queue = queue.Queue()
        self.errors = deque(maxlen=100)
        env = os.environ.copy()
        env.setdefault("SDL_AUDIODRIVER", "dummy")
        # Isolate tracker configuration from the user's normal installation.
        home = cwd / "isolated-home"
        home.mkdir(exist_ok=True)
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"))
        self.proc = subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="strict", bufsize=1,
        )
        self.threads = [
            threading.Thread(target=self._read, args=(self.proc.stdout, True), daemon=True),
            threading.Thread(target=self._read, args=(self.proc.stderr, False), daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def _read(self, stream, stdout: bool) -> None:
        try:
            while True:
                line = stream.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line.encode("utf-8")) > MAX_LINE:
                    raise CheckError("oversized output line")
                if stdout:
                    self.replies.put(json.loads(line))
                else:
                    self.errors.append(line.rstrip())
        except (ValueError, UnicodeError, CheckError) as exc:
            self.replies.put(CheckError(f"invalid server output: {exc}"))
        finally:
            if stdout:
                self.replies.put(None)

    def _send(self, message: dict) -> None:
        line = json.dumps(message, ensure_ascii=True, separators=(",", ":")) + "\n"
        require(len(line.encode("utf-8")) <= MAX_LINE, "request exceeds line limit")
        try:
            self.proc.stdin.write(line)
            self.proc.stdin.flush()
        except (OSError, ValueError) as exc:
            raise CheckError(f"cannot write to MCP process: {exc}") from exc

    def request(self, method: str, params: dict) -> dict:
        self.ident += 1
        ident = self.ident
        self._send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                reply = self.replies.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise CheckError(f"timeout awaiting {method}") from exc
            if isinstance(reply, Exception):
                raise reply
            require(reply is not None, "server exited: " + " | ".join(self.errors))
            require(isinstance(reply, dict), "response must be an object")
            require(reply.get("jsonrpc") == "2.0", "invalid JSON-RPC version")
            if "id" not in reply and "method" in reply:
                continue
            require(reply.get("id") == ident, "unexpected response ID")
            require("error" not in reply, f"RPC error: {reply.get('error')}")
            require(isinstance(reply.get("result"), dict), "missing result object")
            return reply["result"]

    def initialize(self) -> dict:
        result = self.request("initialize", {
            "protocolVersion": PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "keygen-research-smoke", "version": "1.0"},
        })
        require(result.get("protocolVersion") == PROTOCOL, "protocol version mismatch")
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def call(self, tool: str, **arguments) -> str:
        # The tool name is positional as `tool`, not `name`: module_new and sample_load
        # take their own `name` argument, which must reach the tool untouched.
        return tool_text(self.request("tools/call", {"name": tool, "arguments": arguments}))

    def close(self) -> None:
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=2)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            self.proc.kill()
            self.proc.wait(timeout=2)
        for thread in self.threads:
            thread.join(timeout=2)
        self.proc.stdout.close()
        self.proc.stderr.close()


def wav_metrics(path: Path) -> dict:
    """Measure bounded 16-bit PCM; endpoints are diagnostics, not a loop verdict."""
    require(path.is_file(), f"missing WAV: {path}")
    with wave.open(str(path), "rb") as handle:
        channels, width, rate, frames, compression, _ = handle.getparams()
        require(compression == "NONE" and width == 2, "expected 16-bit PCM WAV")
        require(1 <= channels <= 32 and rate > 0, "invalid WAV format")
        require(0 < frames <= rate * 60, "fixture WAV is empty or longer than 60 seconds")
        count = clipped = peak = 0
        squared = total = 0
        first = last = None
        while True:
            raw = handle.readframes(8192)
            if not raw:
                break
            values = array("h")
            values.frombytes(raw)
            if sys.byteorder != "little":
                values.byteswap()
            if first is None:
                first = list(values[:channels])
            last = list(values[-channels:])
            for value in values:
                count += 1
                peak = max(peak, abs(value))
                clipped += value in (-32768, 32767)
                total += value
                squared += value * value
        require(count == frames * channels, "truncated WAV data")
        require(peak > 0, "render is silent")
        require(clipped == 0, "fixture contains full-scale samples")
    return {
        "frames": frames, "rate": rate, "channels": channels,
        "duration_seconds": frames / rate, "peak": peak / 32768,
        "rms": math.sqrt(squared / count) / 32768,
        "dc_offset": total / count / 32768, "full_scale_samples": clipped,
        "first_frame": first, "last_frame": last,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def pcm_fixture() -> str:
    # A short original decaying tone; deliberately not a creative template.
    count = 1024
    values = [int(8000 * math.sin(2 * math.pi * i / 32)
                  * math.sin(math.pi * i / (count - 1)) ** 2) for i in range(count)]
    return base64.b64encode(struct.pack("<" + "h" * count, *values)).decode("ascii")


def smoke(command: list[str], out: Path, timeout: float, milky: str | None = None) -> dict:
    require(not out.exists(), "output directory must not exist; refusing to overwrite")
    out.mkdir(parents=True)
    report = {"status": "failed", "upstream_reference_commit": PIN,
              "binary_matches_pin": "not verified by this test",
              "command": command, "native_acceptance": False,
              "listening_review": "not performed", "loop_seam_review": "not performed",
              "independent_renderer": "not run"}
    client = None
    try:
        client = StdioMCP(command, out, timeout)
        report["server"] = client.initialize()
        tools = client.request("tools/list", {})["tools"]
        names = {item["name"] for item in tools}
        require(REQUIRED <= names, "missing tools: " + ", ".join(sorted(REQUIRED - names)))
        report["advertised_tools"] = sorted(names)
        (out / "tools-list.json").write_text(json.dumps(tools, indent=2) + "\n")
        client.call("module_new", channels=4, name="acceptance fixture")
        client.call("song_set", bpm=125, speed=6, length=1, loop_start=0)
        client.call("pattern_set_length", pattern=0, rows=16)
        client.call("order_set", position=0, pattern=0)
        client.call("sample_create_from_pcm", instrument=1, sample=0,
                    pcm=pcm_fixture(), encoding="int16", name="original test tone")
        for row, note in ((0, "C-4"), (4, "E-4"), (8, "G-4"), (12, "C-5")):
            client.call("pattern_set_cell", pattern=0, row=row, channel=0,
                        note=note, instrument=1, volume=48)
        # Make and inspect a real revision, then verify it persists through disk.
        client.call("pattern_set_cell", pattern=0, row=4, channel=0, note="D-4")
        cell = json.loads(client.call("pattern_get_cell", pattern=0, row=4, channel=0))
        require(cell.get("note") == 51 and cell.get("instrument") == 1, "edit readback failed")
        xm = out / "fixture.xm"
        client.call("module_save", path=xm.as_posix(), format="xm")
        data = xm.read_bytes()
        require(len(data) > 336 and data.startswith(b"Extended Module: "), "invalid XM artifact")
        require(struct.unpack_from("<H", data, 68)[0] == 4, "wrong XM channel count")
        client.call("module_new", channels=4, name="reset before reload")
        client.call("module_load", path=xm.as_posix())
        reloaded = json.loads(client.call("pattern_get_cell", pattern=0, row=4, channel=0))
        require(reloaded.get("note") == 51 and reloaded.get("instrument") == 1,
                "saved edit did not survive reload")
        wav = out / "fixture.wav"
        client.call("module_render", path=wav.as_posix(), rate=44100,
                    bits=16, amp=8, loops=1, start=0, stop=0)
        report["wav"] = wav_metrics(wav)
        report["xm"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        report["native_acceptance"] = True
        if milky:
            other = out / "independent.wav"
            result = subprocess.run(
                [milky, "-sample-rate", "44100", "-output", other.as_posix(), xm.as_posix()],
                cwd=out, capture_output=True, text=True, timeout=timeout,
            )
            (out / "milkycli.log").write_text(result.stdout + "\n" + result.stderr)
            require(result.returncode == 0, "milkycli returned an error")
            report["independent_renderer"] = wav_metrics(other)
        report["status"] = "passed"
        return report
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if client is not None:
            client.close()
            (out / "stderr.log").write_text("\n".join(client.errors) + "\n")
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ft2", required=True, help="path to this fork's executable")
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--milkycli", help="optional independent renderer executable")
    parser.add_argument("--timeout", type=float, default=30, help="seconds per operation")
    args = parser.parse_args()
    try:
        binary = shutil.which(args.ft2)
        require(binary is not None, f"FT2 executable not found: {args.ft2}")
        milky = shutil.which(args.milkycli) if args.milkycli else None
        require(not args.milkycli or milky is not None, "milkycli executable not found")
        report = smoke([str(Path(binary).resolve()), "--mcp"],
                       args.out.resolve(), args.timeout, milky)
        print(json.dumps(report, indent=2))
        return 0
    except (OSError, ValueError, CheckError, subprocess.TimeoutExpired, wave.Error) as exc:
        print(f"acceptance check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
