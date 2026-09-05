# Validation record

Prepared 2026-09-05 against repository main commit
`a58ec8ef1166ddd4f774f796635c590c740502b4`.

Executed locally with Python 3.13.5:

```text
python -m unittest discover -s benchmark/tests -v
Ran 23 tests: 22 passed, 1 skipped.

python -m py_compile benchmark/run.py benchmark/proxy.py benchmark/bridge.py
Passed.
```

The skipped test imports the actual pinned mini-swe-agent package in an isolated
subprocess. That package was unavailable in this environment, and direct external
network access from the execution container failed DNS resolution. The test's
passing assertions must not be inferred from source inspection.

The transport tests use a local synthetic HTTP server, not CLIProxyAPI or a real
provider. The container-command tests inspect mocked Docker calls. WAV and archive
inputs are synthetic. None consumes subscription quota or contacts a model.

Not executed here:

- Docker image build and its native FT2 acceptance gate: Docker unavailable.
- End-to-end mini-swe-agent + real CLIProxyAPI + provider inference.
- Actual subscription authentication or provider authorization checks.
- Provider-facing payload audit or per-credential proxy override audit.
- Native canonical rendering of a model-generated tune.
- Musical quality evaluation or any ranking.

The Dockerfile makes the existing native FT2 smoke test a required build step.
Run the complete test suite and build on the intended benchmark host before an
official attempt. No model results or musical scores are claimed by this PR.
