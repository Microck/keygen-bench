# Keygen benchmark: mini-swe-agent + CLIProxyAPI

This is the inference and artifact-collection foundation. It uses the actual
`minisweagent.agents.default.DefaultAgent` from mini-swe-agent 2.4.6, not a
look-alike agent loop. Every model uses mini's default action protocol (one declared
`bash` function tool), the same frozen creative prompt, resource budget, and offline
FT2 environment.

There are no Codex CLI or Claude Code backends. No skills, hooks, plugins,
AGENTS.md discovery, saved conversations, or per-model system prompts are loaded
by this runner. CLIProxyAPI is the transport, not the agent.

```text
mini-swe-agent DefaultAgent (host, clean Python worker)
    -> Chat Completions adapter (one retry on upstream 5xx)
    -> CLIProxyAPI (host, operator-configured upstream)
    -> model
    -> bash tool calls run in an offline FT2 container
    -> tool results back to the same agent
```

## What this adds, and what it does not

One reserved attempt per model. Within that single trajectory the model may
compose, render and revise. Submission, a resource limit, or a terminal error
ends the attempt. The last workspace artifact is frozen; there is no best-of-N,
second attempt, post-submission editing, or automatic task restart.

A fresh, trusted FT2 process renders the saved XM. This is independent of the
agent's process and preview WAV, not an independent replay engine. Entirely
silent or invalid output fails the validity gate. Duration, RMS, peak, DC offset,
and full-scale sample counts are reported as technical observations only.

After the canonical render, a second trusted container records the FT2 clone GUI
playing the module: Xvfb at 1280x960, the tracker's 1264x800 window stretched to
4:3 the way FT2 filled a CRT, 30 fps H.264. The audio track is what the mixer
played in real time through SDL's disk driver at 48 kHz, aligned to the frame the
grab started on. It is presentation; canonical.wav is the artifact a later evaluator would use.
Capture length is capped by `video_seconds`, and a capture failure is recorded in
`status.json` without changing the attempt's status.

There is deliberately no invented music-quality score. `RENDERED_UNSCORED`
means the trusted FT2 process rendered a non-silent WAV from the file, nothing
more. No ordering of models follows from it. The previously
claimed scoring package was not present in the reviewed repository. Domain-fit,
structural, originality, and aesthetic ranking are not implemented in this PR.
The collection records are intended for a separate frozen artifact evaluator.

## Setup

Run from the repository root on a machine with a local Docker daemon and
Python 3.10 or newer. Use a dedicated virtual environment.

```sh
python3 -m venv benchmark/.venv
. benchmark/.venv/bin/activate
python -m pip install -r benchmark/requirements.txt
python -m unittest discover -s benchmark/tests -v

docker build -f benchmark/Dockerfile --target agent -t keygen-ft2-benchmark:local .
docker build -f benchmark/Dockerfile --target visualizer -t keygen-ft2-visualizer:local .
cp benchmark/config/cliproxyapi.example.yaml benchmark/config/cliproxyapi.local.yaml
cp benchmark/config/campaign.example.json benchmark/config/campaign.local.json
```

The Docker build runs the repository's native FT2 acceptance checker and fails
if author/edit/save/reload/render does not pass. The final runtime image contains
only its transport portion, not its demonstration notes or the repository's
creative prompts. The FT2 source revision is pinned by the existing build script.
The base OS/package repositories are not bit-for-bit locked: build once and reuse
the resulting images. The runner locks both immutable image IDs, source hashes,
Python/package versions, prompts, parameters, and proxy-config digest per campaign.

The requirements pin mini itself. Transitive Python dependencies are recorded,
not a complete reproducible-install lock. Keep the same virtual environment for
the campaign; changing a dependency or image prevents a mixed-condition resume.

## Configure the proxy and models

Start a dedicated CLIProxyAPI instance with the local YAML file. Set its local
client API key to a newly generated random value. Configure only upstream access
you are authorized to use. Authentication, subscription eligibility, OAuth login,
and token extraction are outside this package. It neither launches native coding
clients nor implements subscription authentication or bypasses provider controls.

Set the same local client key in the host environment, not in the campaign JSON:

```sh
export CLIPROXY_CLIENT_KEY='your-local-proxy-client-key'
curl --fail --silent http://127.0.0.1:8317/v1/models \
  -H "Authorization: Bearer $CLIPROXY_CLIENT_KEY"
```

Replace every `REPLACE_...` value in the campaign and proxy files. Record the
installed CLIProxyAPI version or commit. Add one object per exact model ID:

```json
{"id": "model-a", "model": "exact-request-model-id", "response_model": "exact-response-model-id"}
```

`response_model` is checked against the completion response. Some gateways use
a different canonical response name; verify that mapping in a separate transport
check before starting the official campaign. This check cannot authenticate the
true weights behind a proxy-reported name.

All models use the campaign's common `generation` object. Reasoning models spend
completion tokens on thinking before the tool call, so keep `max_tokens` generous. Unsupported parameters
cause a failure rather than silent parameter removal or fallback. Choose settings
supported by the intended models before freezing the campaign. There is no price-
based stopping rule; subscription billing is not inferable from an API response.

The adapter retries a request once, after 5 s, when the proxy answers 5xx or the
connection fails; 4xx answers (auth, quota, rate limit) end the attempt. Both requests
are audited in `transport.jsonl`, the first marked `retried`. Each step's last observation
carries a `<time_left>` tag with the minutes left on the wall clock. A submission is the exact
`echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` command, or, as in mini's stock environments, any
command whose first output line is that marker with exit status 0.

The proxy settings explicitly disable additional retry rounds, credential
failover within a round, quota-based model switches, global Claude prompt cloaking,
model-list cloaking, image-tool injection, plugins, and payload overrides. These
are a configuration check, not proof of the provider-facing payload. Per-credential
settings, aliases inside upstream definitions, proxy translation, and provider-side
instructions can still change a request. Use a dedicated, fixed route per model;
audit the upstream payload without publishing credentials. The report retains
`upstream_payload_verified: false` rather than claiming otherwise.

No rotating accounts, auto-model names, model fallbacks, or native CLI agent
scaffolds belong in a ranked campaign. This package does not configure them.

## Run

```sh
python -I benchmark/run.py doctor --campaign benchmark/config/campaign.local.json
python -I benchmark/run.py run --campaign benchmark/config/campaign.local.json \
  --out benchmark/runs/official
```

`doctor` checks configuration, installed mini version, both Docker images, and the
proxy's model list. It makes no completion request. It does not certify an active
proxy is using the supplied config file; start that instance explicitly.

To run a roster selection (one row per model and tier, as exported by the roster page)
as one campaign per tier, in order, with a results table at the end:

```sh
python -I benchmark/drive.py plan --selection benchmark/config/selection.local.json
python -I benchmark/drive.py run  --selection benchmark/config/selection.local.json --out benchmark/runs/official
```

Each tier gets `campaign-<tier>.local.json` and `runs/official/<tier>/`. Tiers that are not a
`reasoning_effort` value run with no parameter. The driver refreshes a Vercel OIDC token
between campaigns when it has under six hours left; credential values are excluded from the
proxy-config digest, so a rotated key does not count as a changed condition.

Reissuing the same `run` command skips every reserved model, including failed or
interrupted ones. A changed prompt, dependency set, generation setting, image,
proxy config, or model list is refused for that output directory. There is no
`--redo` flag. An operator can always create a new directory; publish the original
campaign rather than silently cherry-picking a later one.

The default budgets are examples, not musical requirements. `steps: 0` removes the
step limit and leaves the wall clock as the only budget. No tempo, key,
instrument palette, form, or target tune duration is prescribed. Resource bounds
still limit storage, request time, rendering time, CPU, and memory. Wall-clock
limits include provider latency. Adjust budgets before starting, not per model.

```text
benchmark/runs/official/
  campaign.lock.json
  model-a/
    spec.json
    trajectory.json
    transport.jsonl
    responses.jsonl
    worker-result.json
    status.json
    submission/tune.xm
    canonical/canonical.wav
    visualizer/visualizer.mp4
```

`transport.jsonl` records, per request: outbound request hash, requested and reported
model IDs, usage, start time, latency, response size, prompt message count, and the
rate-limit headers the proxy passed through. `responses.jsonl` keeps each whole
upstream body, reasoning fields included. Tool results carry the sandbox time of
their command. `status.json` adds attempt start and end times and per-attempt totals
(requests, failed requests, requests with unknown usage, prompt/cached/completion/
reasoning tokens, model seconds, sandbox seconds, commands). A request that fails
still gets a transport line with its error and elapsed time. The trajectory preserves visible messages and executed
actions. Authentication headers and API keys are never placed in prompts or
serialized model config. Keep these local audit files private unless reviewed.
No automatic leaderboard or aesthetic ranking is emitted.

Statuses distinguish `FAILED`, `INFRA_ERROR`, `EVALUATION_ERROR`, `INTERRUPTED`,
and `RENDERED_UNSCORED`. Beside the status, `termination` says how the agent
ended, `collection` whether a submission was found, `render` whether the file
rendered (`ok`, `invalid`, `error`), and `module` what FT2 reports about it
(channels, patterns, instruments). A worker timing out may leave a renderable
final artifact; its termination reason is retained separately. A render/infrastructure error is
not silently turned into a zero musical score. None causes a second model attempt.

## Deterministic scoring and runtime-loop previews

`score.py` ranks collected artifacts with `craft-v7`, a fixed 0–100
tonal-development indicator. Its numeric scores are provisional heuristics,
not a validated musical-quality rating.
There are no human ratings, LLM judges, provider identities, or tool-use bonuses.
Every artifact receives the same policy, with no model-specific rules or per-run
adjustments. Process tags remain visible but do not change the score.

Install the Python requirements, FFmpeg, a C compiler, git, pkg-config,
`libsdl2-dev`, and `libmicrohttpd-dev`. Build the pinned reference player once:

```sh
python scripts/build-ft2-analysis.py
python -I benchmark/score.py profile --out benchmark/runs/official
```

The build installs `~/.cache/keygen-benchmark/ft2-analysis` and its provenance
JSON. `KEYGEN_FT2_ANALYSIS` can select another build of the same pinned source
and patch. `TMPDIR` controls temporary captures; allow space for a 900-second
stereo WAV and temporary band powers. No model rerun or container is required.

`profile` writes `profile.json` per attempt, `profiles.{json,md}` at the campaign
root, and `playback/loop-preview.flac` plus the playback trace. Original XM, WAV,
and video artifacts remain unchanged. The obsolete `packets` command that
rewrote the order table has been removed.

### Reference playback

Both loop and mix analysis use FT2 source commit
`6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d` with `ft2_capture.patch`.
The patch bypasses the WAV export stop condition and records executed row
positions at exact PCM frame offsets. It does not change the order table,
manually restart playback, or reset voices between cycles. Natural restarts,
nonzero restart positions, Bxx/Dxx jumps, E6 loops, delays, and carried effect
state are executed by FT2 itself. The export tool's `loops` argument is a
safety limit, not a request for that many full repeats.

Captures use deterministic defaults, 44,100 Hz signed-16 stereo, and amp 8.
The entire overlap with the existing canonical WAV must match within two PCM
LSBs or 0.5% relative RMS; platform rounding is recorded. A failed comparison
stops scoring rather than inventing a fallback. Solo captures mute mixer output,
not tracker commands. Their row traces must match the full capture, and sampled
PCM reconstruction must remain within the quantization/dither bound.

The listener preview is an unchanged excerpt around the weakest measured
runtime transition, with at least two seconds or four context beats on each
side where available. FLAC is lossless; decoding it must reproduce the
scored PCM byte for byte. Preview markers are relative to that excerpt, while
transition records retain exact full-playback frame and second positions.
The WAV endpoint is not assumed to be a loop point.

### Formula

`craft-v7` separates content evidence from delivery integrity and duration
sufficiency. Clean rendering and selected-lead masking earn no additive points.
Exact repetition alone earns no development points. Length above sufficiency
earns no bonus.

| Content component | Maximum points | Measurement |
| --- | ---: | --- |
| Tonal organization | 50 | Audio-derived, tuning-aligned pitch-class evidence in four-second contexts |
| Development | 40 | Covered recurring material transformed within the same part |
| Dynamics | 10 | 25% active 100 ms level range, 75% three-second level range |

```text
content = 50 * tonal_organization + 40 * arrangement_score + 10 * dynamics
duration_sufficiency = min(1, first_pass_audible_seconds / 30)
score = content * signal_integrity * noise_integrity * (0.75 + 0.25 * loop_quality) * duration_sufficiency
```

The existing silence and sparse-baked-audio caps apply afterward. Each multiplier
is bounded to 0–1 and can only reduce content points. Calculations use unrounded
values until the final score rounds to 0.1. Displayed content parts round to
0.01. Profiles expose both the content subtotal and every multiplier.

The content weights were fixed against identity-free synthetic controls before
rescoring submissions. In `craft-v7`, thresholds that were first set a priori
were checked against real keygen music and recalibrated where they penalized
typical genuine tracks. They remain heuristic policy choices, not weights fitted
to listener ratings or a validated musical-quality scale.

**Reference calibration.** The duration sample's 256 archived XMs were scored
with the complete v6 pipeline, using the pinned FT2 renderer. Twenty files
initially failed analysis because the parser was stricter than FT2 itself; the
parser now follows the pinned FT2 loader. Scored as submissions, the references
had a median v6 score of 25.8, near the submissions' 21.7. Genuine tracks lost
most of their points to thresholds, not to missing musical content:

| v6 rule | References penalized | Evidence |
| --- | ---: | --- |
| DC offset full credit ≤0.002 | 89% | Reference median 0.013; tracker samples commonly carry bias |
| Tonal power fraction full credit at 1.0 | Nearly all | Reference median 0.51; percussion and noise channels hold the rest |
| Diatonic concentration full credit at 1.0 | Nearly all | Reference median 0.955 |
| Any sustained noise reduces integrity | 95% | Reference median sustained-noise fraction 0.24; noise drums and hats are genre-typical |
| Restart level change full credit ≤1 dB | Most restarts | Gapless reference restarts: median 2.3 dB, upper quartile 3.5 dB |
| Restart spectral distance full credit ≤0.10 | 100% of held-out restarts | Gapless reference restarts: median 0.42, upper quartile 0.60 |

A reference-anchor rule replaced those bounds. The references were split by the
first hex digit of their Git blob hash: 113 calibration tracks and 108 held-out
tracks with complete profiles. Full credit starts at the calibration median for
content-like measurements and the calibration upper quartile for defect-like
measurements; bounds are rounded. A typical genuine keygen track therefore
earns full credit, while stronger departures still lose credit continuously.
Percentile tails such as the 5th/95th were tried first and rejected before any
submission rescore: they gave full sustained-noise credit to byte-reinterpreted
PCM and to a melody buried in equal-power white noise.

| Bound | Old full credit | `craft-v7` full credit | Zero point |
| --- | --- | --- | --- |
| Tonal power fraction | 1.0 | ≥0.50 (median) | 0 |
| Diatonic concentration | 1.0 | ≥0.95 (median) | 7/12, chance |
| Sustained-noise fraction | 0 | ≤0.25 (median) | 1.0 |
| DC offset | ≤0.002 | ≤0.03 (upper quartile) | 0.15 |
| Restart level change | ≤1 dB | ≤3.5 dB (upper quartile) | 12 dB |
| Restart spectral distance | ≤0.10 | ≤0.60 (upper quartile) | 0.90 |

Unchanged on purpose: click, gap and rhythm loop bounds, clipping, true peak,
silence and dynamics. The task explicitly requires a clean loop, and 24% of
references end in over a second of silence before restarting; historical
prevalence does not make an audible restart gap correct for this prompt.
Development, the content weights, duration sufficiency and artifact caps are
also unchanged. Development measures structure rather than a genre signature;
the references' median, 0.169, is close to the submissions' 0.204.

On the held-out half, the median tonal-organization value rose from 0.394 to
0.782 and median noise integrity from 0.754 to 1.0. Held-out references were
not used to choose any bound. [The calibration data](../data/keygen-scoring-reference.json)
lists the split, every bound's calibration and held-out distribution, and the
per-reference v6 and v7 scores.

**Duration reference.** A deterministic sample of 256 keygen-labeled XM modules
from the [music-only Keygenmusic archive](https://github.com/6512345/keygenmusic)
had a median first-subsong duration of 106.03 seconds, an interquartile range of
61.44–159.77 seconds, and a fifth percentile of 30.72 seconds.
Eleven files, 4.3%, were below 30 seconds. The shortest was 7.92 seconds.
Short loops therefore occur in the reference material; there is no historical
30-second eligibility rule.

The policy uses 30 seconds as a conservative rounded lower-tail sufficiency
threshold. A 15-second audible first pass receives a 0.5 multiplier; 30 seconds
or more receives 1.0. The linear curve is a benchmark policy choice, not an
estimated listener preference. The original prompt explicitly let models choose
length. This new evaluation criterion is not a task-compliance failure.

[The reference data](../data/keygen-duration-reference.json) records all 256
paths, source URLs, hashes, measurements, sampling rules and limitations.
The sampling frame was 1,310 XM blobs explicitly labeled `kg`, at repository
tree `8b57692adc78fc5a3ff702d6f151ef10c0cad175`.
Selection sorted `SHA256("keygen-duration-study-v1" + NUL + git_blob_sha)`
and took the first 256. Every selected download matched its Git blob hash.
The [libopenmpt duration API](https://lib.openmpt.org/doc/group__libopenmpt__c.html#ga3d243ff23a128ac52e8148343c52618f),
version `0.6.1+r16764.pkg`, measured subsong zero with repeat count zero.
All selected modules loaded; three exposed additional subsongs that were not
included. These are approximate first-pass durations, not unique musical
material or audible-duration measurements. This XM-only convenience archive
is not a census of the scene, and different files can contain related music.
The percentage above 30 seconds is not an exact pass rate for the audible-time
policy below.

Rendered album lengths are not interchangeable with module first passes.
The curator of [Essential Keygen Music](https://archive.org/details/essential-keygen-music)
states that looped tracks loop once and then fade for four seconds.
Its 100 FLAC exports have a median duration of 171.85 seconds, but neither that
median nor compilation-video lengths set the threshold.

**Duration measurement.** The pinned FT2 capture supplies the first runtime
return's exact frame boundary. Count only 100 ms blocks before it with stereo
mean-square power at least −60 dBFS, using the actual duration of the final
partial block. This matches the existing silence threshold and does not cancel
opposite-polarity stereo. Without an observed return, use the bounded available
capture up to the canonical duration and disclose the missing return.
Later playback cycles, exported copies and silent blocks add no duration credit.
Authored repetitions inside the first pass still count; this does not measure
unique composition length or defeat every possible padding strategy.
The existing development measure separately gives exact repetition zero credit.

**Loop.** Capture `min(900, max(20, 3 * canonical_seconds + 12))` seconds
continuously. Evaluate natural restarts and backward/self Bxx returns;
finite E6 pattern loops and forward arrangement jumps are not song restarts.
An E6 edge with a repeated native sequencer state is a genuine cycle and is
included. State includes loop counters, markers, and pending position/delay
controls, so a finite pattern repetition is not mistaken for an endless loop.
Take the worst measured return, including later returns with carried state.
If no measurable runtime return is observed, loop quality is zero.

Each transition first combines click, gap, level, and rhythm as a normalized
weighted geometric mean. Spectrum then supplies a bounded timbral-continuity
factor:

```text
technical = click**(.20/.85) * gap**(.25/.85) * level**(.20/.85) * rhythm**(.20/.85)
loop_quality = technical * (.85 + .15 * spectrum)
```

| Check | Formula weight | Full credit | Zero credit |
| --- | ---: | --- | --- |
| Click | .20 / .85 in technical mean | Sample jump ≤1× nearby 99th-percentile ordinary steps | ≥8× |
| Gap | .25 / .85 in technical mean | Boundary silence ≤0.05 beat | ≥0.75 beat |
| Level | .20 / .85 in technical mean | Change ≤3.5 dB | ≥12 dB |
| Rhythm | .20 / .85 in technical mean | Crossing attack interval differs ≤0.10 octaves from nearby ordinary intervals | ≥0.75 octaves |
| Spectrum | .15 in bounded factor | Normalized broad-band distance ≤0.60 | ≥0.90 |

Scores interpolate linearly between each pair of thresholds. A zero technical
component gives zero loop quality and a 0.75 whole-score multiplier. A zero
spectrum score with otherwise perfect continuity gives 0.85 loop quality and
a 0.9625 multiplier. Thus spectral continuity alone can cost at most 3.75
points before other integrity factors. There are no additive loop points.

Gap detection uses 5 ms RMS blocks and the larger of −60 dBFS or 40 dB below
local RMS. Level compares both one-beat and four-beat windows; spectrum compares
one-beat windows. Four tracker rows set the context beat duration, bounded to
0.15–2 seconds. Rhythm uses actual envelope attacks rather than imposing a
downbeat. Without enough attacks, rhythm uses the weaker of gap and level
continuity. Inaudible context earns zero.

**Signal integrity.** Clipping contributes 35%, DC 15%, true peak 10%, silent fraction 25%,
and longest silent run 15%. Full/zero thresholds are respectively 0/0.1% clipped
samples, 0.03/0.15 DC amplitude, 0/+3 dBTP, 1/25% silent audio, and 0.5/4
seconds of silence. Silence uses 100 ms blocks below −60 dBFS. The multiplier
ramps from zero at −60 LUFS to full at −30 LUFS; louder audio gets no extra
credit. Stereo energy is measured without cancelling opposite-polarity channels.

**Sustained noise.** Native-rate Hann windows of approximately 96 ms cover the
entire non-DC spectrum through Nyquist. Separate channel powers prevent stereo
polarity cancellation. Disjoint 32 ms duration cells include partial endings.
Third-octave bands merge until each contains at least six FFT bins. Active
audio has mean power at least one millionth of the recording peak squared.

Band flatness maps linearly from zero noise evidence at 0.10 to full evidence
at 0.50. Bands below 0.0001 of frame power contribute nothing. Power-weighted
evidence must reach 0.10 continuously for at least 0.25 seconds; the whole
qualifying run then counts. The sustained-noise fraction is the active-duration
mean of that sustained evidence. It is not simply the proportion of time
containing noise. Brief noise percussion does not qualify by itself.
`noise_integrity` is 1 up to a sustained-noise fraction of 0.25, the reference
median, then falls linearly to 0 at 1.0. `SUSTAINED_NOISE` flags integrity
below 0.8 without imposing a second penalty.

The scorer never penalizes a sample merely for being 8-bit, bright, or authored
with a particular API. It does not inspect construction commands to infer a
sample-format error. Intentional sustained noise can lose credit, while some
periodic corruption can escape. Profiles report these limitations and per-band
power, flatness, exposure, and high-frequency evidence.

**Tonal organization.** Audio peaks at 65–5,000 Hz need three-bin power at
least 1% of frame power and height at least 12 times a fifteen-bin median
floor. Log-parabolic interpolation estimates frequency. Up to 32 peaks are
grouped under lower roots at harmonics 2–12 within 35 cents when the root's
own peak has at least one tenth of the overtone's power.

Four-second contexts align fractional-semitone tuning and collect 10-cent
pitch-class evidence. Each context multiplies `min(1, tonal_power_fraction / 0.50)`
by `clip((best_diatonic_concentration - 7/12)/(0.95 - 7/12), 0, 1)` and
`clip((exp(chroma_entropy) - 1)/3, 0, 1)`. Active-duration weighting combines
contexts. A single stationary pitch has no variety. Harmonic power above
5,000 Hz remains in the full-band noise and total-power measurements, but is
not used to identify pitch roots.

This favors diatonic material and is not a harmony, melody, or taste judge.
Chromatic and microtonal music may score lower without being defective.
Static chords and reordered in-key notes can resemble melodic variety.
Integer-related simultaneous notes can merge during harmonic suppression.

**Mix diagnostics.** Native 44,100 Hz stems supply 27 bands from 50 to 22,050 Hz
using 4,096-frame windows. No decimation discards high-frequency interference.
A fixed note-contour/harmonicity rule selects melodic candidates, handles
octave doubles, and allows handoffs. It does not rank by volume or discard a
candidate merely because accompaniment is louder. Stems at or below two PCM
LSBs are dither-only. Selected-lead clarity and masking do not affect `craft`.

Delayed copies yield to their original only when the same reached pitches and
sample sound match at a fixed positive lag of at most two seconds. Sample
fingerprints include PCM, loop settings, and tuning, but exclude instrument
numbers, names, volume, and panning. Matching requires at least four events and
three pitches, 80% of copy events, 50% of source events, and overlapping
activity covering 50% of the shorter part. Lag-aligned spectra must have median
cosine similarity at least 0.98, a median copy/source power ratio at most 0.8,
and 80% of ratios within 6 dB of that median. Equally supported lags remain
unresolved. Copies remain eligible during gaps in their original.

Independent candidates are not demoted merely for being quiet. Exactly tied
foreground alternatives are measured separately against their accompaniment,
then averaged, rather than selected by channel number or pooled into one
artificially clear target. Profiles disclose copy evidence, suppression, and
ambiguous foreground duration. These conservative rules can miss altered
echoes and cannot distinguish every intentional canon from an effect copy;
they are not a validated musical-role classifier.

Masker energy spreads 25% into adjacent bands. Target-to-masker ratios map
linearly from zero at −12 dB to full clarity at +6 dB. The better ear qualifies
only if it has at least 10% of target energy. Target bands below 1% of the
strongest target band are ignored; each active frame has equal weight.
Active-only clarity is multiplied by the fraction of audible program time
with an active selected melody. A brief clear phrase cannot earn full-song mix
credit. No qualifying melodic source means zero clarity. `masking_fraction`
is the target-weighted band fraction below 0 dB during active melody frames,
not the fraction of whole-song time. `MASKED` flags values above 0.35.

**Development.** Sixteen traversed rows form a phrase. Repeated four-note motifs
and transposition-normalized phrases establish recurrence. Development requires
the changed channel itself to retain shared motifs covering at least half of
its events in each adjacent phrase. Unchanged accompaniment cannot certify
unrelated melody changes. Each transition weights supported channels by event
count against all active channel events, including unchanged parts and entries
or exits. The mean transition fraction is `controlled_development`.

Both note commands and audible row/pitch content must change. Instrument-index
and volume-only changes do not establish development. Exact duplicate complete
channel trajectories count once for scoring, but remain in raw diagnostics.
Copies with different instrument/sample identities remain distinct.

The formula is `coverage * sqrt(recurrence * development)`. Exact repetition
alone receives zero development points, while its recurrence remains visible.
Unused assets and inaudible channels earn none. Four-note motifs and sixteen-row
boundaries can miss sparse, longer-form, timbral, or envelope-only development.
The reference loader normalizes entirely empty patterns to 64 rows.

**Dynamics.** Active-block RMS percentile range p95−p10 receives full
credit at 3–18 dB and zero at 0/36 dB. Three-second RMS range p90−p10 receives
full credit at 1–10 dB and zero at 0/24 dB.

At least 99% silence caps the score at zero. A used sample over eight seconds
with sequence coverage below 0.25 caps at 40; a long pad alone does not.
Quiet playback already reduces the signal-integrity multiplier.

### Evidence and limits

Profiles record source/artifact hashes, scorer version, reference binary and
patch hashes, content parts, multipliers, gate reasons, spectral measurements,
and loop trace/preview evidence. Changed inputs invalidate the cache;
publication requires current profiles. `craft-v5` includes `score_audio.py`
in scorer provenance and invalidates older profiles. It changes no original
XM, canonical WAV, or video and uses no model identity or trajectory input
in the score.

The synthetic controls in `tests/test_score_audio.py` distinguish sustained
white/filtered noise, byte-reinterpreted PCM, short percussion, legitimate
8-bit synthesis, diatonic material, chromatic dispersion, and stationary tones.
`VALIDATION.md` records measured results. These establish specific
discrimination and invariance properties, not listener agreement.

Intentional noise, chromatic writing, sparse motifs, unusual meters, and
irregular rhythms can lose credit. Static chords, in-key random ordering and
periodic corruption can still receive misleading credit. Mix diagnostics can
prefer an echo or accompaniment to the intended lead; they no longer determine
aggregate ordering. Phase cancellation and binaural effects are not modeled.
Native audio includes tick effects, but static note labels do not fully model
delayed onsets, envelopes, or pitch slides. Unsupported or inconsistent
analysis fails explicitly.

## Isolation details

The worker runs Python with `-I` and an allowlisted environment. Its HOME, XDG
config and `MSWEA_GLOBAL_CONFIG_DIR` are new directories. This matters because
mini's package initializer loads a global `.env` even when using its Python API.
We instantiate DefaultAgent directly with two explicit templates; no mini CLI
configuration merging or native-client configuration occurs.

The model executes commands only inside a non-root, network-disabled, read-only
container with bounded writable tmpfs storage. The workspace is a private,
tmpfs-backed Docker-managed volume, not a host directory. A non-agent, read-only
export helper keeps it mounted and reads files while the agent is paused; ordinary
`docker cp` cannot reliably copy tmpfs data. Helpers and volumes are removed after
collection. No repository, host home,
Docker socket, API keys, proxy auth directory, evaluator, reference music, or
skill folder is bind-mounted. Bash runs with `--noprofile --norc` and disabled
BASH_ENV/ENV startup files. Only the FT2 session and workspace persist within one
attempt. Files from another model never enter that workspace.

The adapter is small because it implements mini's Model protocol directly using
one HTTP request per turn, two when the first fails transiently. It does not import LiteLLM routing or its retry layer.
It sends the conversation unchanged and declares exactly one tool, mini's stock
`bash` function, the protocol the shipped SWE-bench configs use. No other tools or
auxiliary prompts. A reply with no tool call or an unknown tool gets mini's standard
format-error message back; three in a row end the attempt as `RepeatedFormatError`.
An HTTP error terminates the worker. The legacy single-code-block text protocol was
tried first: current codex-backend models answer it with a whole imagined session of
commands in one reply, and Kimi K3 leaks tool-call tokens into the text.
Rendering supplies files and numerical observations, not audio listening.

Containers share the host kernel. For hostile workloads use a dedicated VM or
stronger sandbox, and treat a custom image as trusted infrastructure that requires
review. Isolation is not a claim that upstream model/provider internals are visible.

## Tests and verification

```sh
python -m unittest discover -s benchmark/tests -v
python -m py_compile benchmark/run.py benchmark/proxy.py benchmark/bridge.py
```

Offline tests cover outbound message and tool preservation, authentication separation,
HTTP retries/redirects, response-model mismatch, contaminated environment removal,
container flags, duplicate model rejection, one-attempt reservation, campaign
locking, archive validation, and technical audio observations. The real DefaultAgent
contract test runs only when mini-swe-agent is installed; a skip is not a pass.
See [VALIDATION.md](VALIDATION.md) for what was actually run during preparation.

## Primary implementation references

Source inspection date: 2026-09-05. These are implementation references, not
endorsements of subscription credential reuse.

- [mini DefaultAgent 2.4.6](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/agents/default.py)
- [mini initialization and Model/Environment protocols](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/__init__.py)
- [mini tool-call model and bash tool](https://github.com/SWE-agent/mini-swe-agent/blob/v2.4.6/src/minisweagent/models/litellm_model.py)
- [CLIProxyAPI configuration inspected at a fixed revision](https://github.com/router-for-me/CLIProxyAPI/blob/5208aec703b5ce7e3445f6e9d91cc13b3e78003a/config.example.yaml)
- [Existing FT2 workflow and limitations](../docs/10-agent-xm-workflow.md)
- [Existing native acceptance checker](../tools/ft2_smoke.py)
- [Docker copy limitations](https://docs.docker.com/reference/cli/docker/container/cp/)
- [Docker-managed volumes](https://docs.docker.com/engine/storage/volumes/)
