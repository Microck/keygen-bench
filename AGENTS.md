# Current frontend

The current frontend is the FT2 website in [`../keygen-easy-runs/web/classic/`](../keygen-easy-runs/web/classic/). Make frontend changes there; preview publication directories are generated outputs, not source.

Before editing it, read the [repository instructions](../keygen-easy-runs/AGENTS.md) and [frontend guide](../keygen-easy-runs/web/classic/README.md).

# Run storage

All benchmark runs live under `~/keygen-data/runs/` on the laptop, one folder per model, using its plain name (no service or machine suffix):

```
runs/<model>/
  attempt-1/ attempt-2/ attempt-3/   # the 3 attempts the leaderboard ranks (best of 3)
  other/                             # everything else: failed, retried, quota, older/legacy runs, other services
```

Never delete attempts; anything not ranked goes in `other/`. Where an attempt ran (Ashburn, Paris, x86, ARM) is noted only inside its own files.

`benchmark/runs/organize/organize.py` builds it (mirror with SHA-256 checks, restore evicted gdrive2 bundles, rebuild `runs/`); `--export DIR` hard-links it into a checkout's `runs/`. `runs/` has no videos and stores WAV as lossless `<name>.wav.flac` (`flac -d --keep-foreign-metadata` restores the exact bytes). The public repo commits it on branch `data/runs` (PR #28), in commits under 2 GB each.
