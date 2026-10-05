# Benchmark runs

Every attempt of every model, one folder per model:

```text
<model>/attempt-1/ attempt-2/ attempt-3/   the three attempts the leaderboard ranks (best of 3)
<model>/other/<date>-<attempt>/             everything else: failed, retried, quota, older runs, other services
index.json                                  every attempt: slot, status, score, route, source
```

Each attempt folder holds what the harness recorded: `status.json`, `trajectory.json` and `transport.jsonl`
(the full model conversation), `submission/` (the model's `tune.xm` and files), `canonical/` (the trusted
render), `evaluations/` (scores) and `ATTEMPT.json` (where it came from and why it is in this slot).

Visualizer videos are not included. Audio is stored as lossless FLAC: `<name>.wav.flac` decodes to the
exact original WAV, byte for byte, with `flac -d --keep-foreign-metadata <name>.wav.flac`; the original
WAV SHA-256 is in the attempt's `archive.json` or its evaluation records.
