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

## Follow-up on the benchmark host, 2026-09-14

Executed on Linux arm64 with Python 3.11.14, Docker server 29.2.0, and
mini-swe-agent 2.4.6 installed in a fresh virtual environment:

- `python -m unittest benchmark.tests.test_benchmark -v`: 23 tests passed, none
  skipped. The real DefaultAgent contract test ran.
- `python -m unittest tests.test_ft2_smoke`: 17 tests passed.
- `docker build -f benchmark/Dockerfile .` succeeded, including the native FT2
  acceptance gate. The first build failed because `StdioMCP.call` in
  `tools/ft2_smoke.py` used `name` for the tool, which collided with the `name`
  argument of `module_new` and `sample_load`. That parameter is now `tool`.
- A scripted round trip through `run.py` primitives without a model:
  `start_container`, `ft2 list` and `ft2 batch` through `Sandbox.execute`,
  `Submitted` on the finish command, `docker pause`, `collect` through the
  read-only export helper, `render` in a fresh container, `wav_info` on the
  canonical WAV, and removal of every container and volume.
- The container-command tests use a hand-written recording stand-in for
  `run.shell`, not `unittest.mock`.

Still not executed:

- End-to-end mini-swe-agent + real CLIProxyAPI + provider inference.
- Actual subscription authentication or provider authorization checks.
- Provider-facing payload audit or per-credential proxy override audit.
- Musical quality evaluation or any ranking.

Run the complete test suite and build on the intended benchmark host before an
official attempt. No model results or musical scores are claimed.
