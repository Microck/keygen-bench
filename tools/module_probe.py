#!/usr/bin/env python3
"""Read basic metadata from XM, IT, S3M, and common MOD headers.

This tool does not render audio, extract executable resources, or determine
authorship. A tracker-name field identifies the writer recorded in that saved
file, which may be a converter or a later editor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any


class ProbeError(Exception):
    """Raised when a file cannot be inspected safely."""


def _text(raw: bytes) -> str:
    raw = raw.split(b"\x00", 1)[0].rstrip(b" ")
    return raw.decode("cp437", errors="replace")


def _u16(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        raise ProbeError(f"header is too short for uint16 at offset {offset}")
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        raise ProbeError(f"header is too short for uint32 at offset {offset}")
    return struct.unpack_from("<I", data, offset)[0]


def _mod_channels(signature: bytes) -> int | None:
    fixed = {
        b"M.K.": 4,
        b"M!K!": 4,
        b"M&K!": 4,
        b"N.T.": 4,
        b"FLT4": 4,
        b"FLT8": 8,
        b"CD81": 8,
        b"OKTA": 8,
        b"OCTA": 8,
    }
    if signature in fixed:
        return fixed[signature]

    text = signature.decode("ascii", errors="ignore")
    for pattern in (r"^(\d)CHN$", r"^(\d{2})CH$", r"^(\d{2})CN$"):
        match = re.match(pattern, text)
        if match:
            return int(match.group(1))
    return None


def _probe_xm(data: bytes) -> dict[str, Any]:
    if len(data) < 80:
        raise ProbeError("XM header is shorter than 80 bytes")
    return {
        "format": "XM",
        "title": _text(data[17:37]),
        "tracker_or_exporter": _text(data[38:58]),
        "format_version": f"{data[59]}.{data[58]:02x}",
        "header_size": _u32(data, 60),
        "song_length_orders": _u16(data, 64),
        "restart_position": _u16(data, 66),
        "channels": _u16(data, 68),
        "patterns": _u16(data, 70),
        "instruments": _u16(data, 72),
        "frequency_table": "linear" if (_u16(data, 74) & 1) else "Amiga",
        "default_speed": _u16(data, 76),
        "default_tempo": _u16(data, 78),
        "provenance_warning": (
            "The tracker/exporter field may identify a converter or the last "
            "program that saved the file, not the original composition setup."
        ),
    }


def _probe_it(data: bytes) -> dict[str, Any]:
    if len(data) < 64:
        raise ProbeError("IT header is shorter than 64 bytes")
    created = _u16(data, 40)
    compatible = _u16(data, 42)
    return {
        "format": "IT",
        "title": _text(data[4:30]),
        "orders": _u16(data, 32),
        "instruments": _u16(data, 34),
        "samples": _u16(data, 36),
        "patterns": _u16(data, 38),
        "created_with_raw": f"0x{created:04x}",
        "compatible_with_raw": f"0x{compatible:04x}",
        "initial_speed": data[50],
        "initial_tempo": data[51],
        "message_length": _u16(data, 54),
        "message_offset": _u32(data, 56),
        "provenance_warning": (
            "Creation-version fields can be rewritten or imitated by other "
            "trackers and are not conclusive authorship evidence."
        ),
    }


def _probe_s3m(data: bytes) -> dict[str, Any]:
    if len(data) < 64:
        raise ProbeError("S3M header is shorter than 64 bytes")
    return {
        "format": "S3M",
        "title": _text(data[0:28]),
        "orders": _u16(data, 32),
        "instruments": _u16(data, 34),
        "patterns": _u16(data, 36),
        "flags_raw": f"0x{_u16(data, 38):04x}",
        "created_with_raw": f"0x{_u16(data, 40):04x}",
        "sample_format_version_raw": f"0x{_u16(data, 42):04x}",
        "initial_speed": data[49],
        "initial_tempo": data[50],
        "provenance_warning": (
            "Version fields identify file-writing metadata, not necessarily "
            "the complete original production chain."
        ),
    }


def _probe_mod(data: bytes) -> dict[str, Any] | None:
    if len(data) < 1084:
        return None
    signature = data[1080:1084]
    channels = _mod_channels(signature)
    if channels is None:
        return None
    return {
        "format": "MOD",
        "title": _text(data[0:20]),
        "signature": signature.decode("ascii", errors="replace"),
        "channels_inferred_from_signature": channels,
        "song_length_orders": data[950],
        "restart_byte": data[951],
        "provenance_warning": (
            "A MOD signature identifies a format variant and channel layout; "
            "it does not prove which tracker originally composed the song."
        ),
    }


def probe(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ProbeError(str(exc)) from exc

    if not path.is_file():
        raise ProbeError("path is not a regular file")

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        first = handle.read(4096)
        digest.update(first)
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)

    result: dict[str, Any]
    if first.startswith(b"Extended Module: "):
        result = _probe_xm(first)
    elif first.startswith(b"IMPM"):
        result = _probe_it(first)
    elif len(first) >= 48 and first[44:48] == b"SCRM":
        result = _probe_s3m(first)
    else:
        mod = _probe_mod(first)
        if mod is None:
            result = {
                "format": "unknown",
                "provenance_warning": (
                    "No supported XM, IT, S3M, or common MOD signature was found."
                ),
            }
        else:
            result = mod

    result["path"] = str(path)
    result["size_bytes"] = size
    result["sha256"] = digest.hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect basic XM, IT, S3M, or MOD header metadata."
    )
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--compact", action="store_true", help="emit one-line JSON instead of indented JSON"
    )
    args = parser.parse_args()

    try:
        result = probe(args.file)
    except ProbeError as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
