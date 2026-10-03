#!/usr/bin/env python3
"""Rewrite the contrib-positive fixture's frozen contract after an intentional harness change.

The community contract pins harness source hashes, so any edit to a pinned source invalidates
the fixture by design. This updates manifest.json's environment.contract, copies it into each
attempt's environment.json and refreshes those files' SHA-256 entries. Nothing else changes.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "contrib"), str(HERE.parent)]
import validate_bundle  # noqa: E402

ROOT = HERE / "fixtures/contrib-positive"


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    manifest["environment"]["contract"] = validate_bundle.contract()
    for attempt in validate_bundle.ATTEMPTS:
        path = ROOT / attempt / "environment.json"
        newline = "\n" if path.read_text().endswith("\n") else ""
        path.write_text(json.dumps(manifest["environment"], indent=2) + newline)
        manifest["files"][f"{attempt}/environment.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
