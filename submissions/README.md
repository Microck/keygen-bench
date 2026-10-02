# Community submissions

Store each bundle at `submissions/<model-slug>/<YYYY-MM-DD>-<github-handle>/`.
Use a safe filename slug for the model; the manifest preserves the exact ID.
See [the run guide](../CONTRIBUTING-RUNS.md).

## Bundle format: keygen-community-1

`manifest.json` declares exactly `attempt-1`, `attempt-2`, and `attempt-3`, a
shared environment, and a map of relative filenames to SHA-256. Every regular
file except the manifest itself must appear in that map. Links, special files,
extra files, unfinished slots, changed pins/prompts/limits, and detected secrets
fail validation. The manifest cannot hash itself.

Each attempt contains `status.json`, `environment.json`, `trajectory.json`,
`transport.jsonl`, and `tune.xm` if a module was collected. Missing modules require
an explicit failure category and `tune_present: false`. A failure before any
provider request has an empty trajectory with `evidence_unavailable: true` and
an empty transport log. Other attempts must retain their available evidence.
Invalid modules from failed attempts stay in the bundle for review.
Status includes attempt ordinal, final outcome, usage totals with unknown-usage
counts, and start/finish/wall times. It omits controller paths, container names,
and raw controller errors. Environment includes model ID, public provider
API/base URL, generation settings, reasoning tier/documentation, prompt hashes
and exact text, frozen limits, base image digest, final image IDs/layers, FT2
commit, harness/source hashes, benchmark package versions, OS family,
architecture, Python version, and Docker version. It excludes kernel releases,
registry names, unrelated packages, hostnames, and usernames. Trajectories
contain the original messages, not serialized controller configuration.
OAuth bridge models replace the private base URL with a `bridge` object holding
`transport: loopback-http` and `binary_sha256`. The executable path and local
address/port stay private. This is contributor-declared provenance, not proof
that the binary handled the requests or that upstream received the settings.

The bundle limit is 512 MiB and 4096 files. Each XM is at most 128 MiB; each
metadata/log file is at most 16 MiB. Ask the maintainers to review a larger log;
do not truncate it. Optional sandbox extras and submitted scores are not packaged.

## Maintainer verification

Validate with the current trusted repository code, not code supplied in the PR.
Review all three outcomes, route identity, transmitted settings, highest-tier
source, usage gaps, runtime/build provenance, and suspicious logs. Hashes detect
changes; contributor-written evidence does not prove no undisclosed attempts
occurred. Final image IDs identify builds but are not the Debian base digest.
The validator checks the declared base digest against the pinned Dockerfile;
review/rebuild image provenance separately. Different architectures are different
experimental conditions. Keep failures visible.

Validation rejects common credential patterns, environment dumps, absolute
home paths, and private host metadata fields. Public route and metadata
allowlists reduce accidental disclosure; they do not detect all personal data,
private URLs, or credentials. Review every file before publication. Keep a
rejected bundle private rather than deleting evidence to make it pass.

Build the trusted images and FT2 analysis binary as described in the run guide.
Re-render and score without provider credentials, on an isolated machine:

```sh
python benchmark/contrib/validate_bundle.py submissions/MODEL/DATE-HANDLE \
  --rescore --trusted-agent-image keygen-ft2-benchmark:local \
  --rescore-out /tmp/keygen-trusted-review
```

This uses 44.1 kHz / 16-bit FT2 rendering and the existing craft-v7 scorer. It
keeps trusted results outside the sealed bundle. Do not load contributor-selected
Docker images or trust supplied scores. Inspect the resulting profiles for
eligibility and evaluation errors. The analysis renderer has a separate bounded
64 MiB XM input limit; larger permitted submissions need explicit maintainer
review and may fail scoring.

Label accepted results `community-submitted`. Publish them in a separate cohort
with provenance and every attempt/failure visible. Never silently add them to
ranked results. CI validation alone is not acceptance or a musical-quality claim.
GitHub retains public history; handle deletion requests under the maintainer's
data policy and rotate exposed credentials even if a file is removed later.
