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

## Protocol change and first playable attempt, 2026-09-24

Through the dedicated CLIProxyAPI instance (port 8417) on the benchmark host:

- Text-block protocol, three smoke runs, all `FAILED`: `gemini-3.5-flash` (star
  bridge timed out on the real prompt), `gpt-5.6-luna` and `kimi-k3-modal`
  (`RepeatedFormatError`; codex models returned a whole imagined session of
  commands per reply, Kimi exhausted its budget on reasoning then leaked
  tool-call tokens).
- Bash tool-call protocol, first-turn probes: gpt-5.5, gpt-5.6-luna,
  gpt-6-astra, gpt-5.6-sol each one tool call; kimi-k3-modal two tool calls.
- Bash tool-call protocol, smoke run `gpt-5.6-luna`, `max_tokens` 32768: 6 turns,
  `Submitted`, `PLAYABLE_UNSCORED`. Canonical render 38.4 s stereo, peak 0.27,
  RMS 0.059, no full-scale samples. The model created samples with NumPy,
  loaded them through `ft2 call`, built patterns with `ft2 batch`, saved the XM,
  and submitted. Recovered from one failed command (`python` vs `python3`).

The proxy places the benchmark system prompt as a `developer` message under its
own system framing for codex models; `upstream_payload_verified` stays false.

## Visualizer video, 2026-09-24

Smoke run `gpt-6-luna`, bash tool protocol, `max_tokens` 32768, images
`keygen-ft2-benchmark:local` and `keygen-ft2-visualizer:local` built with explicit
targets: 7 turns, `Submitted`, `PLAYABLE_UNSCORED`, canonical render 51.8 s.
`visualizer/visualizer.mp4`: 52 s, 1280x960, H.264 + AAC, 42.7 MB, window
1264x800 at +8+80, audio offset 0.747 s. Frames show the pattern editor scrolling
and scopes moving; the pointer sprite is parked off-window.

## Prompt revision, 2026-09-24

System prompt now states the step and time budget (filled from the frozen
limits), names what this FT2 build cannot do (envelopes, note-to-sample
mapping), says a keygen tune loops, and points at the render-and-inspect loop
in place of the negated "you have not heard it". Task prompt unchanged.
Smoke run `gpt-6-astra`, `reasoning_effort` low: 6 turns, `Submitted`,
`PLAYABLE_UNSCORED`, 54.1 s; the model rendered a preview and measured peak,
RMS and clipping before submitting. 26 tests pass.
