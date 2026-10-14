#!/usr/bin/env python3
"""Offline stand-in for the listener environment's Python.

score.py runs `$KEYGEN_LISTENER_PYTHON score_listener.py identity|predict WAV`.
Pointing KEYGEN_LISTENER_PYTHON here answers with fixed ratings, so tests
exercise the real subprocess contract without PyTorch or model weights.
"""
import json
import sys
import wave

IDENTITY = {"model": "fake", "revision": "fake", "weights_sha256": "0" * 64, "device": "cpu", "max_seconds": 120}
RATINGS = {"content_enjoyment": 6.54, "content_usefulness": 7.0,
           "production_complexity": 4.0, "production_quality": 7.5}

command = sys.argv[2:]
if command == ["identity"]:
    print(json.dumps(IDENTITY))
elif len(command) == 2 and command[0] == "predict":
    with wave.open(command[1]) as audio:
        seconds = min(audio.getnframes() / audio.getframerate(), 120)
    print(json.dumps({"ratings": RATINGS, "analyzed_seconds": seconds, "identity": IDENTITY}))
else:
    sys.exit(f"unexpected arguments: {command}")
