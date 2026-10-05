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

## Review fixes, 2026-09-24

Applied from docs/11-adversarial-review-2026-09-24.md: `RENDERED_UNSCORED` replaces
`PLAYABLE_UNSCORED`; `status.json` carries `collection`, `render`, and `module`
beside `status` and `termination`; failed requests get a transport line with
their error and elapsed time and totals count them; the prompt says steps, not
commands, and states that raw XM writing is allowed but the module must be a real
tracker module; sandbox output keeps head and tail with a byte-count marker.
Checked on the host: re-rendering both astra tunes gives PCM hashes identical to
the stored ones (the render is deterministic for a fixed image); `module_info`
reports 12 channels, 142 BPM, 24 and 32 order entries for them; a 40 KB command
output arrives as 10 KB + marker + 10 KB with the final line intact. 30 tests pass.

## Profiles and packets, 2026-09-24

Historical result. The order-table-rewriting packet path below was removed in
craft-v3 because it did not faithfully represent every runtime restart. Current
loop previews use unchanged-module continuous FT2 capture.

`score.py profile` over the three demo attempts: astra-low flags TAIL_SILENCE, SEAM,
RAW_XM (2.8 s tail silence, 12 channels, 24 distinct patterns, 1570 note-ons);
astra-low-v2 flags SEAM (11 channels, 32 patterns, 1706 note-ons, -21.4 LUFS);
luna flags FLAT (6 channels, 4 patterns, 240 note-ons, -17.9 LUFS). Loudness checked
against a 997 Hz reference tone at -20 dBFS in both channels: -20.0 LKFS within 0.3.
`score.py packets` built all three: extended renders reproduce the canonical prefix
byte for byte; tails 10.1 to 13.2 s; gains +4.5, +3.4, -0.1 dB; no loudness shortfall.

## Continuous reference playback and craft-v3, 2026-09-28

Executed on the Linux arm64 benchmark host with the native analysis build from
`mova77/fast-tracker2` commit `6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d` and
`benchmark/ft2_capture.patch`. The scorer uses continuous, unchanged-module
playback for runtime loop transitions and mixer-isolated channel stems.

```text
env TMPDIR=/dev/shm benchmark/.venv/bin/python -m unittest discover -s benchmark/tests
Ran 93 tests. OK.

ruff check --select E9,F63,F7,F82 benchmark scripts/build-ft2-analysis.py \
  /home/ubuntu/cliproxyapi-keygen/tools/aggregate.py \
  /home/ubuntu/cliproxyapi-keygen/tools/build-results-page.py
All checks passed.
```

Native integration coverage includes speed-one row timing, nonzero restart
orders, carried voices, Bxx/Dxx jumps, finite and endless E6 loops, delayed rows,
empty-pattern normalization, channel isolation, and exact capture budgets.
Separate DSP tests cover clicks, silence gaps, level resets, rhythmic
discontinuities, stereo polarity, and inaudible context.

A controlled native-render experiment produced loop qualities of 0.983461 for
the continuous fixture, zero after adding a 0.952834-second boundary gap, and
zero after an 18.07877 dB boundary level reset. Canonical-prefix comparisons
were exact for all three fixtures.

The published table contains 61 model entries, including 60 rendered artifacts.
Every rendered artifact has a measured runtime transition. Across the complete
overlapping PCM prefixes, the largest difference from the original canonical
WAV is one 16-bit quantization step. Twelve submissions receive zero loop
points; one receives the full 25. All 61 cached profiles pass source, artifact,
renderer, preview, and trace provenance checks. Recomputing the MiniMax M3
profile produces an identical profile, including preview and trace hashes.
The 116 pre-existing XM/WAV checksums remain unchanged.

Recovered the completed `go-minimax-m3` and `go-mimo-v2.6-pro` attempts from the
stopped benchmark sandbox, without rerunning either model. Their craft-v3
scores are 70.0 and 89.5 respectively. The four recovered XM/WAV checksums match
the sandbox copies, and both video checksums match their status records.
Earlier local rate-limit failures remain in their original attempt directory.
The sandbox is stopped again.

Checked the live results page in Chromium: craft-v3 weights, both recovered
rows, filtering, artifact links, lossless loop playback through the recorded
marker, playback completion, and competing playback requests. Delaying the
first player's metadata while starting the second leaves only the second
playing; cancelled requests no longer leave a loading message.
This Chromium build has no H.264 support, so the recovered MP4s were decoded
with FFmpeg rather than verified through browser video playback.

These checks establish playback fidelity and deterministic signal measurements.
They do not establish human agreement on musical resolution, composition
quality, or whether an intentional rest deserves a loop penalty. The scoring
formulas and limitations are documented in `benchmark/README.md`.

## Uniform craft-v4 corrections, 2026-09-28

Applied one policy to all published submissions, without model identities,
manual channel assignments, or per-run overrides. Mix analysis now requires
corroborated fixed-delay note and sample-sound relationships before giving an
echo lower priority during its original's activity. Exact foreground ties
receive separate, equally weighted masking assessments. Spectral continuity
can cost at most 3.75 total points; masking and loop estimates no longer impose
additional whole-score caps. Artifact silence/inaudibility and sparse baked-song
gates remain.

Verification on the benchmark host:

- `env TMPDIR=/dev/shm benchmark/.venv/bin/python -m unittest discover -s benchmark/tests`:
  100 tests passed.
- Ruff fatal-error checks over benchmark code, the native build script, and both
  publication scripts passed.
- Regression coverage includes native quiet echoes with shared and duplicate
  instruments, channel permutations, distinct-timbre negatives, independent quiet
  melodies, dry-source gaps, ambiguous ties, bounded spectrum-only penalties,
  and preserved technical discontinuity penalties.
- All 60 rendered artifacts were rescored. All 61 published profiles, including
  the failed artifact, use craft-v4. Two full-corpus passes produced identical
  audio, structure, mix, loop, and craft results before and after behavior-preserving
  index/allocation simplifications.
- All 120 original XM/WAV checksums remained unchanged.
- Chromium showed the published craft-v4 score breakdown and played a lossless
  loop excerpt through its recorded marker to completion without a media error.

The generic copy detector found supported relationships in five published runs.
It remains conservative: differently encoded or altered sounds, variable delays,
and some musical-role ambiguities remain unresolved. No manual correction was
applied where the detector declined a relationship. These results establish
regression behavior and consistent corpus-wide application, not validated
listener agreement or a model-capability ranking.

## Tonal-development evidence and craft-v5, 2026-09-28

Removed additive credit for signal hygiene, duration and selected-lead masking.
The content subtotal now uses audio-derived tonal organization, channel-local
retained-motif development and dynamics. Signal integrity, sustained-noise
integrity and bounded runtime-loop continuity multiply that subtotal.
`benchmark/README.md` documents the complete formula and its style assumptions.

The rules were fixed using identity-free synthetic signals before the corpus
rescore. No model name, desired ordering, authoring command, or per-run override
enters the score. Proper 8-bit quantization is not a defect; the controls
distinguish it from interpreting int16 bytes as int8 samples.

A direct PCM probe used 44,100 Hz audio, peak-normalized every signal to 0.3,
and supplied deliberately perfect structural evidence. Every case had a signal
integrity multiplier of 1 and loop quality of 1. The white-noise loop quality
was measured across the repeated block; the other loop values were controlled
inputs. These are component/aggregate controls, not complete XM submissions:

| Control | Tonal organization | Noise integrity | Aggregate with perfect structure |
| --- | ---: | ---: | ---: |
| Harmonic melody | 0.957810 | 1.000000 | 88.0 |
| Correctly quantized 8-bit melody | 0.957791 | 1.000000 | 88.0 |
| int16 bytes reinterpreted as int8 | 0.175938 | 0.577904 | 28.3 |
| Melody with short noise percussion | 0.846664 | 1.000000 | 85.1 |
| Melody with sustained equal-power noise | 0.473667 | 0.476111 | 30.6 |
| Repeated white noise | 0.000000 | 0.000017 | 0.0 |

The four-second melody/percussion controls match total noise power rather than
peak burst amplitude. The byte-reinterpreted control has twice as many frames
because each int16 sample becomes two int8 samples. It demonstrates one concrete
corruption mechanism, not universal detection of incorrect sample encodings.

A separate sequence probe produced arrangement scores of zero for exact
repetition, one for retained-motif transpositions, and zero for an arbitrary
lead over repeating drums. The last case retained 0.666667 motif recurrence,
showing that accompaniment recurrence no longer certifies unrelated changes.

A native FT2 smoke probe retained 27 frequency bands through 22,050 Hz. A
9,000 Hz target scored clarity 1.0 against a quiet same-band masker and
0.111111 against a strong masker. Native source reconstruction differed by at
most two PCM LSBs against the fixture's eight-LSB tolerance, with identical
row traces.
An endpoint-energy probe caught an excluded Nyquist FFT bin before publication.
Including the final bin changed the Nyquist-to-nearby-tone diagnostic power ratio
from 1.333496 to 2.666504. A regression now guards that endpoint.

Verification:

- The focused audio, structure, aggregate and mix suites passed 71 tests.
- `env TMPDIR=/dev/shm OPENBLAS_NUM_THREADS=1 benchmark/.venv/bin/python -m unittest discover -s benchmark/tests`
  passed 123 tests.
- `ruff check --select E9,F63,F7,F82 benchmark /home/ubuntu/cliproxyapi-keygen/tools/aggregate.py /home/ubuntu/cliproxyapi-keygen/tools/build-results-page.py`
  passed.
- All six direct PCM control outputs remained identical after replacing a
  per-band scalar NumPy clamp with an equivalent Python clamp and removing an
  unnecessary structural motif set.
- Rescored the same 61 published entries, including 60 rendered artifacts and
  one failed artifact. Every profile passes current source, renderer, artifact,
  preview and trace provenance checks. Recomputing aggregates from the stored
  measurements reproduces every published score.
- All 120 original XM/WAV checksums remain unchanged. Across all 60 rendered
  artifacts, canonical-prefix differences are at most one PCM LSB. Every
  native stem reconstruction remains within its channel-count-dependent
  quantization tolerance.
- Chromium displayed all 61 v5 values matching the aggregate, ascending and
  descending sorting, model filtering, the new multipliers and expanded
  spectral evidence. The Qwen lossless excerpt played across its recorded
  loop marker and reached the end without a media error. Profile, XM, original
  WAV, lossless excerpt and trace links returned HTTP 200.

For the five runs raised during diagnosis, corpus-wide application produced:

| Run | craft-v4 | craft-v5 |
| --- | ---: | ---: |
| Inkling | 90.0 | 26.7 |
| Nemotron 3 Ultra | 88.0 | 23.8 |
| Qwen 3.7 Plus | 87.3 | 6.6 |
| Opus 5.5 | 86.1 | 49.7 |
| Fable 5.1 | 81.0 | 40.3 |

The scale changed; these are not before/after listener quality percentages.
The resulting order was observed after the rules were fixed, not used to fit
the rules. Other submissions received exactly the same analysis.

These controls establish specific discrimination and invariance properties.
They do not establish listener agreement. Intentional sustained noise and
non-diatonic writing can lose credit; static chords, reordered in-key notes,
and periodic corruption can still receive misleading credit. Sparse or
longer-form development can fall outside the four-note/sixteen-row model.

## Historical duration reference and craft-v6, 2026-09-28

The v5 removal of duration also removed any distinction between an eleven-second
sketch and a longer submission with the same local content measurements.
The original prompt permitted models to choose length, so v6 adds an explicit
evaluation policy rather than treating short output as a task failure.

The [music-only Keygenmusic mirror](https://github.com/6512345/keygenmusic)
supplied a deterministic 256-file sample from 1,310 keygen-labeled XM blobs.
The pinned tree, hash-based selection, individual source URLs and file hashes
are retained in [the reference dataset](../data/keygen-duration-reference.json).
No keygen executable was downloaded or run; no archived music is redistributed.
libopenmpt `0.6.1+r16764.pkg` measured the first subsong with playback repetition
disabled. Every file loaded successfully.

| First-subsong duration statistic | Seconds |
| --- | ---: |
| Minimum | 7.92 |
| Fifth percentile | 30.72 |
| Lower quartile | 61.44 |
| Median | 106.03 |
| Upper quartile | 159.77 |
| Maximum | 562.36 |

Eleven of 256 first passes were below 30 seconds, including three below 15.
These are convenience-corpus duration estimates, not listener quality labels.
An XM-only, filename-filtered archive omits other formats and can contain
multiple versions of the same composition. Three files had additional subsongs;
only subsong zero contributed. Audible time was not measured for all historical
references, so 245/256 is not an exact pass rate for the new scoring policy.

The independently curated [Essential Keygen Music](https://archive.org/details/essential-keygen-music)
collection has 100 FLAC exports with median length 171.85 seconds. Its curator
explicitly describes a loop plus a four-second fade. These export lengths did
not set the threshold.

Native FT2 cross-checks reproduced the following libopenmpt estimates:

| Archived XM | libopenmpt seconds | FT2 first return seconds |
| --- | ---: | ---: |
| Mr. Teo / 3D Text Commander 3.0.3 | 7.92 | 7.92 |
| Lz0 / Johannes Wallroth All Products | 30.72 | 30.72 |
| R2R / IK Multimedia 1.0 | 105.28 | 105.28 |

The resulting uniform factor is `min(1, first_pass_audible_seconds / 30)`.
Thirty seconds rounds down the sample's fifth percentile; linear scaling and
the use of audible time remain policy choices. There is no hard minimum and
no bonus for longer songs. The v5 tonal, development, dynamics, noise and loop
weights remain unchanged. This study does not validate those musical proxies.

Verification before publication:

- All 126 existing and updated benchmark tests passed with
  `env TMPDIR=/dev/shm OPENBLAS_NUM_THREADS=1 benchmark/.venv/bin/python -m unittest discover -s benchmark/tests`.
- Aggregate boundary cases produce 0, 50, 99.7, 100 and 100 points for otherwise
  perfect content at 0, 15, 29.9, 30 and 60 audible seconds.
- The native-duration test excludes leading/internal silence and later cycles,
  includes the final partial block and preserves opposite-polarity stereo.
- A real-submission smoke probe extended MiniMax M3's original 10.906122-second
  WAV to four copies, 43.624490 seconds. Both exports measured the same first
  FT2 return at 10.906122449 seconds, with 10.9 audible seconds, duration factor
  0.3633333333 and aggregate score 21.6. The original artifacts were not edited.
- The native historical checks and padding probe were throwaway experiments;
  the lasting boundary and PCM invariants live in `test_score.py` and
  `test_score_loop.py`.

Publication checks:

- Rescored the same 61 entries, including 60 rendered submissions. All profiles
  pass current source, artifact, renderer, preview and trace provenance checks.
  Recalculating their aggregates reproduces every published score.
- Audio, structure, mix, content parts and the three pre-existing multipliers
  are exactly unchanged from v5. Only the duration factor changes scoring.
  All 120 original XM/WAV hashes match the pre-rescore baseline.
- MiniMax M3 changed from 59.5, second place, to 21.6, 31st place. Terra remains
  first at 63.6 because its first pass exceeds the sufficiency threshold.
  This is not evidence that listeners prefer Terra's composition.
- Chromium displayed all 61 scores matching the aggregate. Model filtering and
  keyboard clearing worked. The MiniMax detail exposed 10.9 audible seconds
  and the 0.363333 duration factor. Its lossless excerpt played across the
  recorded marker and ended without a media error. The reference dataset and
  current profile links returned HTTP 200 with the expected contents.
- `ruff check --select E9,F63,F7,F82 benchmark /home/ubuntu/cliproxyapi-keygen/tools/aggregate.py /home/ubuntu/cliproxyapi-keygen/tools/build-results-page.py`
  passed.
- Read-only agents were unavailable because their provider returned HTTP 403.
  Source analysis and code review ran locally; there was no independent-agent
  corroboration. The review found no worthwhile behavior-preserving
  simplification of the bounded first-pass measurement.

## Reference-calibrated thresholds and craft-v7, 2026-09-28

Question: does the scorer, applied unchanged, treat genuine keygen music as
competent? The 256 archived references from the duration study were rendered
with the pinned FT2 analysis build and profiled by the complete v6 pipeline.

Twenty references initially failed analysis. Sixteen declared instruments past
the end of the file and four had order entries naming patterns absent from the
file. The pinned FT2 loader
(`src/modloaders/ft2_load_xm.c` at `6c2ffc07`) accepts both: short instrument
reads leave zeroed, empty instruments, and every pattern slot starts as an empty
64-row pattern. `parse_xm` now follows it. Truncated pattern and sample headers
remain errors, as they are in FT2. After the fix all 256 references scored.

The v6 median reference score was 25.8, against the submissions' 21.7. A
per-term decomposition showed the loss came from thresholds set a priori, not
missing content:

- DC full credit ended at 0.002, but the reference median is 0.013. 89% of
  references were penalized; a rerendered 32-file subset put the median DC
  integrity term at 0.28.
- Tonal organization multiplied by raw tonal-power fraction with full credit
  at 1.0. The reference median is 0.51 because drum and noise channels hold
  the rest. The tonal-fraction term was the largest log-loss for references,
  0.72, versus 0.16 for diatonic concentration and 0.06 for variety.
- Any sustained noise reduced integrity. 95% of references lost credit; the
  median sustained-noise fraction is 0.24, typical noise percussion.
- Loop level and timbre full credit ended at 1 dB and 0.10 spectral distance.
  Gapless reference restarts have a median level change of 2.3 dB and median
  spectral distance 0.42; every held-out restart exceeded the old 0.10 bound.

Method. References with complete profiles were split by the first hex digit of
their Git blob hash: 0–7 calibration (113), 8–f held out (108). Bounds were
chosen on calibration data only. The first rule tried, 5th/95th percentile
tails, was rejected before any submission rescore. It gave full noise credit to
int16 bytes reinterpreted as int8 (sustained-noise fraction 0.51) and to a
melody under equal-power white noise (0.525), both above the 0.528 tail bound.
The adopted rule anchors full credit at the calibration median for content-like
measurements and the calibration upper quartile for defect-like ones, rounded:

| Bound | Calibration anchor | v6 full credit | v7 full credit |
| --- | --- | --- | --- |
| Tonal power fraction | median 0.506 | 1.0 | 0.50 |
| Diatonic concentration | median 0.956 | 1.0 | 0.95 |
| Sustained-noise fraction | median 0.246 | 0 | 0.25 |
| DC offset | upper quartile 0.033 | 0.002 | 0.03 |
| Restart level change | upper quartile 3.54 dB | 1 dB | 3.5 dB |
| Restart spectral distance | upper quartile 0.598 | 0.10 | 0.60 |

Kept unchanged, with reasons recorded in the scoring reference: content weights,
development, dynamics, duration, clipping, true peak, silence, loop click/gap/
rhythm, and the artifact caps. The prompt requires a clean loop. 24% of
references end with over a second of silence before restarting, so their
restart gaps are real and still lose loop credit.

Synthetic controls, peak-normalized to 0.3 with perfect structure and delivery
inputs, under v7:

| Control | Tonal organization | Noise integrity | Aggregate |
| --- | ---: | ---: | ---: |
| Harmonic melody | 1.000000 | 1.000000 | 100.0 |
| Correctly quantized 8-bit melody | 1.000000 | 1.000000 | 100.0 |
| int16 bytes reinterpreted as int8 | 0.357626 | 0.770539 | 52.3 |
| Melody with short noise percussion | 1.000000 | 1.000000 | 100.0 |
| Melody with sustained equal-power noise | 0.960216 | 0.636689 | 62.4 |
| Repeated white noise | 0.000000 | 0.000023 | 0.0 |

The byte-reinterpretation and sustained-noise controls lose credit less steeply
than in v5. That is the direct cost of accepting genre-typical noise percussion;
repeated noise still scores zero, and correct 8-bit material is unaffected.

Reference scores, v6 then v7, complete profiles only:

| Split | v6 p25 / median / p75 | v7 p25 / median / p75 |
| --- | --- | --- |
| Calibration (113) | 17.6 / 24.4 / 31.3 | 34.0 / 45.8 / 54.9 |
| Held out (108) | 16.8 / 26.9 / 34.2 | 37.2 / 48.3 / 61.6 |

The held-out half improved at least as much as the calibration half, so the
bounds are not fitted to one half of the archive. References still span a
wide range; the recalibration does not declare every archived tune excellent.
Per-reference scores, factors, both halves' distributions and every bound are
in [the scoring reference](../data/keygen-scoring-reference.json).

Verification:

- All 127 benchmark tests passed, including new FT2-loader parser cases and
  the revised restart-level boundary.
- Rescored the same 61 entries. All profiles pass provenance checks, and
  recomputing each aggregate reproduces the published score. All 120 original
  XM/WAV hashes match the pre-rescore baseline. Development and first-pass
  duration evidence are identical to v6 for every rendered submission.
- Terra remains first, 63.6 to 78.9. Larger rank moves follow the recalibrated
  terms: Gemini 3.8 Flash rose from 15th to 3rd because v6 penalized its 0.28
  sustained-noise fraction and 0.038 DC offset, both near the reference
  median and upper quartile; MiMo v2.6 Pro fell from 3rd to 14th because it had
  no noise or DC penalty to recover. These orderings were observed after the
  bounds were fixed from reference data, not used to choose them.
- Chromium displayed all 61 v7 scores matching the aggregate. The Gemini 3.8
  Flash detail showed its v7 score, parts and factors. The scoring reference
  returned HTTP 200 with 256 records.
- `ruff check --select E9,F63,F7,F82` over the scorer and publication tools
  passed.

Limits: a median anchor leaves half of the calibration references below full
credit on that measure by design. The bounds describe one archive of one
genre; they do not validate the tonal or noise proxies as musical-quality
measures, or show transfer to other scenes.
