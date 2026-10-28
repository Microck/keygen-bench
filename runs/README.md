# Benchmark runs

Every attempt of every maintainer model, one folder per model, plus reviewed community publications:

```text
<model>/attempt-1/ attempt-2/ attempt-3/   the maintainer's three attempts the leaderboard ranks (best of 3)
<model>/other/<date>-<attempt>/             everything else: failed, retried, quota, older runs, other services
<model>/community/<date>-<handle>/attempt-N one reviewed community submission, published unranked
index.json                                  maintainer attempts: slot, status, score, route, source
```

Maintainer slots are the highest-declared-tier condition, written from the private campaign by
`scripts/organize_runs.py`. A community directory is written by
`validate_bundle.py --publication-out` after review, sits beside the maintainer slots and never
replaces them; see [maintainer verification](../submissions/README.md#maintainer-verification).

Each attempt folder holds what the harness recorded: `status.json`, `trajectory.json` and `transport.jsonl`
(the full model conversation), `submission/` (the model's `tune.xm` and files), `canonical/` (the trusted
render), `evaluations/` (scores) and `ATTEMPT.json` (where it came from and why it is in this slot).

Visualizer videos are not included. Audio is stored as lossless FLAC: `<name>.wav.flac` decodes to the
exact original WAV, byte for byte, with `flac -d --keep-foreign-metadata <name>.wav.flac`; the original
WAV SHA-256 is in the attempt's `archive.json` or its evaluation records.
