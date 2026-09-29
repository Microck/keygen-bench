# Adversarial review of the benchmark, 2026-09-24

Reviewer: gpt-6-astra, reasoning_effort medium, through the dedicated proxy. Input: benchmark/README.md, prompts, run.py, proxy.py, bridge.py, visualize.sh, Dockerfile, campaign.example.json, VALIDATION.md, docs/10-agent-xm-workflow.md at main 4880dabc. Prompt asked for critical, major, minor, gaming vectors, missing measurements, evaluator needs, tracker-scene objections, ordered minimal fixes. Output unedited below the line; usage 19k prompt / 4.3k completion tokens.

---

# Critical

**Scope:** This is a source review of the supplied files, not a runtime or sandbox-escape audit. References use file names and exact source-line excerpts or named functions; the supplied snapshot has no line numbers. Tests, upstream implementations, the build script, and proxy YAML were not supplied.

### C1 — No music-quality conclusion follows from the implemented outcome
**Severity: Critical if used for musical rankings; otherwise a limitation of scope.**

**Evidence:** `run.py::wav_info` rejects a render only when its PCM structure is unacceptable, its length is inconsistent, or `not peak`. It returns `"quality_score": None`. `run_one` then assigns `"PLAYABLE_UNSCORED"`. `prompts/task.txt` asks for an **“original keygen tune.”**

**Failure scenario:** A nearly silent impulse, constant DC, unrelated noise, or a single sustained tone can pass the implemented audio gate. Originality, musical content, genre fit, and clean looping have no bearing on that status. Even “playable” means accepted by this particular renderer, not portable XM playback.

The README disclaims aesthetic scoring, but repeatedly calls `canonical.wav` the “graded artifact.” Collection success must not become an implicit leaderboard.

**Minimal fix:** Name the outcome `RENDERED_NONZERO_UNSCORED`, or publish an equally explicit definition beside every result. Prohibit quality ordering from this status. **Cost:** Reporting changes only; actual music evaluation is separate work.

### C2 — The provider-facing experimental treatment is not controlled
**Severity: Critical for claims of a model-only, same-prompt comparison.**

**Evidence:** `proxy.py::query` hashes the request sent to the local proxy, not the provider. `run.py::proxy_policy` returns `"upstream_payload_verified": False`. `VALIDATION.md`, “Protocol change and first playable attempt,” says:

> “The proxy places the benchmark system prompt as a `developer` message under its own system framing for codex models.”

**Failure scenario:** Different models receive different authority levels, provider framing, translated tools, or hidden instructions. Checking `response_model` only verifies a gateway-provided string. Hashing an on-disk YAML does not prove the running proxy used it.

**Minimal fix:** Label results as **model × provider route × proxy translation × scaffold**. Freeze and privately audit effective upstream payloads and route settings. Publish redacted differences. **Cost:** Per-route integration work; true model-weight identity remains unverifiable.

# Major

### M1 — The advertised command budget is not implemented as a command counter
**Severity: Major.**

**Evidence:** `prompts/system.txt` says “Budget: `<<STEPS>>` commands.” `run.py::worker` supplies `step_limit=...` to `DefaultAgent`; `Sandbox.execute` has no command-budget counter. `proxy.py::query` accepts a list of tool calls without imposing a one-call limit. `VALIDATION.md` records Kimi returning two calls. `bridge.py` executes an arbitrary list in `batch`.

**Failure scenario:** Agent steps, bash invocations, FT2 calls, and total computational work are different quantities. A model batching aggressively can do far more work per step. Exact multi-action scheduling depends on the pinned mini implementation, which is not included here.

**Minimal fix:** Call the limit **agent steps**, document multi-call behavior, and count bash invocations and FT2 operations separately. If commands truly are the intended bound, enforce that counter in `Sandbox.execute`. **Cost:** Small implementation and contract-test changes.

### M2 — Uniform settings do not create equal effective resources
**Severity: Major.**

**Evidence:** `campaign.example.json` sets `max_tokens: 32768`; `run.py::worker` sets a common wall limit; `run_one` independently kills the worker after that duration. `proxy.py` uses non-streaming requests and provider-reported usage.

**Failure scenario:**
- Reasoning tokens consume completion allowance differently across providers.
- Latency, queueing, and transient failures consume the creative window.
- A long non-streaming response can be killed before any tool action becomes available.
- Context limits and unsupported parameters can end some trajectories earlier.
- Fixed `--cpus 2` is a quota, not equal throughput across different hosts or contention levels.

This measures performance under a particular service-and-budget regime, not isolated compositional ability.

**Minimal fix:** State that estimand explicitly; record host conditions and route latency; run every model under the same frozen regime without describing it as compute parity. **Cost:** Metadata and narrower claims. A second budget regime costs additional attempts.

### M3 — Prior model-dependent tuning contaminates “one attempt” rhetoric
**Severity: Major.**

**Evidence:** `VALIDATION.md` documents three text-protocol smoke runs, model-specific first-turn probes, several playable tool-protocol runs, and a later prompt revision. `run.py::reserve` only reserves a directory locally.

**Failure scenario:** Protocol and prompts are selected after observing named models’ failures. Final runs may be one-shot, but the benchmark design was not model-blind. An operator can also repeat campaigns in new directories or register aliases of the same underlying model.

**Minimal fix:** Publish the development-run ledger, distinguish pilots from official attempts, and preregister the final campaign hash and model roster. **Cost:** Disclosure; externally timestamping a manifest is inexpensive.

### M4 — Audit totals omit precisely the failed requests that matter
**Severity: Major.**

**Evidence:** In `proxy.py::query`, `reply = request(...)` occurs **before** either audit file is written. `request` raises on HTTP errors, transport failures, oversized bodies, and invalid JSON. `run.py::summarize` sums only recorded replies and converts missing usage to zero.

**Failure scenario:** A failed request can consume substantial time or upstream computation yet contribute zero requests and zero model seconds. Unknown token usage appears indistinguishable from actual zero usage. Abrupt termination can also leave trajectory-based command totals incomplete.

**Minimal fix:** Write a request-start event before I/O and a completion/error event afterward; preserve missing usage as unknown and report coverage. **Cost:** Small logging/schema change; do not retain credential-bearing error bodies.

### M5 — Termination cause and artifact outcome are conflated
**Severity: Major.**

**Evidence:** `run.py::worker` catches all exceptions into `worker-result.json`. `run_one` then collects and renders regardless of that result. A usable last XM becomes `PLAYABLE_UNSCORED`; missing submission becomes `FAILED`. Subprocess failures during rendering become `EVALUATION_ERROR`.

**Failure scenario:** A provider failure with an earlier XM looks playable; the same failure before a save looks like model failure. Conversely, an artifact that stalls the renderer can look like evaluator infrastructure failure. Consumers grouping only by top-level status will misattribute outcomes.

**Minimal fix:** Emit independent fields for **agent termination**, **transport outcome**, **collection outcome**, and **render validity**. Keep unknown render-failure attribution explicit. **Cost:** Small schema and reporting changes.

### M6 — Fresh rendering is not independent validation
**Severity: Major.**

**Evidence:** `run.py::render` loads and renders using the same agent image and FT2 implementation, with `loops: 1`, 44.1 kHz, 16-bit output, and `amp: 8`. `docs/10-agent-xm-workflow.md` describes an optional independent renderer, but the benchmark does not call it.

**Failure scenario:** The same loader/mixer bug can affect composition previews and canonical output. A clean first traversal says nothing about restart-state behavior, sustained voices, effect memory, or later loop cycles.

**Minimal fix:** Keep the canonical engine but add a separately versioned compatibility render and capture at least two restart transitions. Treat discrepancies as flags rather than demanding identical PCM. **Cost:** Another dependency and additional render time.

### M7 — “Editable XM” and restricted tracker tooling leave an undefined submission boundary
**Severity: Major.**

**Evidence:** `prompts/system.txt` permits Python for “editing files” while saying envelopes and note-to-sample mapping are unavailable. `run.py::render` checks the XM magic and renderability, not authoring method or musical structure.

**Failure scenario:** A model knowledgeable about XM serialization can use features unavailable through MCP. Another can embed an effectively finished audio piece in a long sample with minimal pattern sequencing. Both satisfy the current file boundary, but neither measures the same tracker-authoring task as building instrument parts and patterns.

**Minimal fix:** Explicitly choose an **artifact-open** or **tool-constrained** track. For artifact-open evaluation, disclose that raw XM editing is allowed and measure practical editability separately. **Cost:** A rule clarification; structural inspection adds modest tooling.

### M8 — Frozen records are not a reproducible execution environment
**Severity: Major.**

**Evidence:** `run.py::fingerprint` records package names/versions, image IDs, architecture, and selected source hashes. `Dockerfile` uses mutable Debian tags and package repositories. `proxy_version` is operator-entered. `VALIDATION.md` describes successive source changes without identifying a fresh full revision for each follow-up.

**Failure scenario:** Another researcher cannot recover an image from its local ID alone. Package version strings do not establish package contents; proxy version text does not establish the running executable. Provider updates and randomness prevent exact inference replay even with identical local artifacts.

**Minimal fix:** Separate **recorded conditions**, **artifact replay**, and **inference reproducibility**. Archive images or publish retrievable immutable digests, dependency locks, full source revision/dirty diff, and the proxy binary digest. **Cost:** Storage and build provenance work.

# Minor

### m1 — Command observations silently lose the end of output
**Severity: Minor.**

**Evidence:** `run.py::Sandbox.execute` uses `head -c 20000 /tmp/keygen-action.log`. The later head-and-tail truncation in `proxy.py` cannot recover discarded bytes.

**Failure scenario:** Long batch output hides the final error or save result without a truncation notice.

**Minimal fix:** Return marked head-and-tail output with total byte count. **Cost:** Small wrapper change.

### m2 — Video synchronization is asserted more precisely than it is established
**Severity: Minor; Major if video audio is used for judging.**

**Evidence:** `visualize.sh` samples `offset_bytes` before starting ffmpeg, assumes 48 kHz stereo PCM, and uses `-shortest`. Playback has already started before capture. `run.py::visualize` reports the requested `seconds`, not a probed encoded duration.

**Failure scenario:** Process startup latency and audio buffering exceed the claimed one-buffer alignment; the opening is omitted, and the video may end early. Video also uses different playback conditions and lossy AAC rather than canonical PCM.

**Minimal fix:** Describe alignment as approximate, probe actual streams/duration, and exclude video audio from judging. **Cost:** Small metadata change; precise synchronization requires more work.

### m3 — Isolation claims exceed the persistence actually provided
**Severity: Minor.**

**Evidence:** README says “Only the FT2 session and workspace persist.” Container `/tmp`, `/home/agent`, and arbitrary background processes also persist until teardown. `Sandbox.execute` provides a command timeout but no explicit per-action process census or cleanup.

**Failure scenario:** Later commands inherit residual processes or temporary state. Detached work can continue between tool calls; a bash timeout is not necessarily an attempt-wide computation boundary.

**Minimal fix:** Document whole-container persistence and test descendant-process timeout behavior. **Cost:** Documentation and a targeted test.

### m4 — Optional companions can invalidate the required submission
**Severity: Minor.**

**Evidence:** The system prompt permits WAV previews and scripts alongside the XM. `run_one` collects the entire submission directory under one byte/file limit.

**Failure scenario:** A valid tune fails collection because optional previews consume the quota or an unrelated entry violates archive policy.

**Minimal fix:** Collect and validate `tune.xm` first, then companions under a separate allowance. **Cost:** Small collection change.

### m5 — Prompt and resource disclosure are incomplete
**Severity: Minor.**

**Evidence:** `load_config` displays minutes using integer division. The prompt omits request, command, render, storage, and context constraints.

**Failure scenario:** Models plan around an inaccurately rounded time budget and discover important ceilings only through failures.

**Minimal fix:** State exact seconds and relevant limits in a compact budget block. **Cost:** A few prompt tokens.

# Gaming vectors

These are benchmark-integrity scenarios, not claims of demonstrated sandbox exploits.

| Actor | Vector and evidence | Consequence |
|---|---|---|
| Model | Satisfy only the nonzero-PCM gate (`run.py::wav_info`). | Technical pass without a tune. |
| Model | Package whole musical passages as samples; structure is unchecked (`render`). | Apparent XM composition without meaningful part-level editability. |
| Model | Batch many operations or exploit multi-call turns (`bridge.py::main`, `ProxyModel.query`). | More work per nominal “command” budget. |
| Model | Use raw XM editing despite missing MCP setters (`system.txt`). | API limitations burden models unequally. |
| Model | Put claims or judging instructions in module metadata or companion files. | A future language-model evaluator may follow artifact-supplied instructions unless these are treated strictly as data. |
| Operator | Create new output roots, omit pilots, or register route aliases (`reserve`, `load_config`). | Hidden best-of-N or duplicate underlying models. |
| Operator | Change the active proxy independently of the hashed config (`proxy_policy`). | Undisclosed changes in model route or framing. |
| Operator | Edit local artifacts and logs after collection; hashes are stored locally without external attestation. | No independently verifiable chain of custody. |
| Operator | Publish only playable attempts, or judge capped videos instead of full audio. | Survivorship and presentation bias. |

# Missing measurements

- **Musical:** Motif quality, development, harmony, rhythm, groove, arrangement, timbral coherence, transitions, fatigue, genre fit.
- **Looping:** Restart correctness, audible seams, rhythmic continuity, note tails, persistent effect state across repeated cycles.
- **Originality:** Melody resemblance, recognizable copied phrases, sample provenance; offline generation is not proof of originality.
- **Tracker structure:** Active channels, meaningful patterns, order reuse, effects, sample sizes, musical-part separation, practical editability.
- **Audio:** Integrated/short-term loudness, true peak, per-channel DC, silence distribution, stereo correlation, discontinuities. Full-scale sample counts alone are not a clipping diagnosis.
- **Reliability:** Variance across attempts, route failure rates, context exhaustion, missing-usage coverage, uncertainty in model comparisons.
- **Resource use:** Complete failed-request accounting, actual CPU/memory consumption, operation counts, effective context and reasoning budgets.
- **Reproducibility:** Independent playback compatibility, repeated-render stability, retrievable build provenance.
- **Human evaluation:** Rater agreement, listener expertise, blinding effectiveness, sample-size justification.

# What an evaluator needs

1. **A frozen rubric before official outputs are judged.** Separate validity, tracker craft, domain fit, originality, and aesthetic preference. Do not invent one composite score afterward.
2. **Full, blinded audio listening.** Randomized anonymous identifiers; no provider names, trajectories, generation costs, or tracker video in the primary listening round.
3. **Level-controlled comparisons.** Preserve originals for engineering review; use a declared loudness-matching policy for preference tests to reduce louder-is-better bias.
4. **Actual loop evaluation.** Include restart transitions and repeated playback, not just a first-pass render or endpoint jump statistic.
5. **Qualified, multiple raters.** Include tracker practitioners and listeners familiar with keygen music. Report agreement, confidence intervals, and disagreements.
6. **Separate artifact inspection.** Examine patterns, instruments, effects, sample provenance, and ease of editing individual parts after blinded listening.
7. **A defensible originality procedure.** Similarity tools can flag candidates; human adjudication must distinguish stock idioms from substantial copying. No procedure proves universal novelty.
8. **Validation of automated judges.** Demonstrate agreement with held-out expert judgments and robustness to loudness, metadata, silence padding, and superficial complexity. Numerical WAV analysis is not a music judge.
9. **Honest uncertainty.** One artifact per model supports a comparison of those artifacts—not a reliable estimate of each model’s general musical ability.

# Tracker-scene objections

- **“Keygen” is not a single genre.** The open task leaves chiptune, demoscene, dance, jazz-inflected, and other traditions unresolved. A narrow evaluator could punish legitimate stylistic choices.
- **FT2 is not the whole lineage.** `docs/10-agent-xm-workflow.md` itself names ProTracker, Scream Tracker, and Impulse Tracker. Frame this as an XM/FT2-conditioned task.
- **The fork’s MCP interface is not full FT2 proficiency.** Missing envelopes, keymaps, fadeout, and automatic vibrato alter instrument design substantially.
- **Baking envelopes into samples is not equivalent.** Transposition changes time behavior; reusable instrument articulation and note-off behavior are affected.
- **Small size and economical reuse matter historically.** A 128 MiB artifact allowance permits constructions far removed from compact keygen modules. Efficiency should be a disclosed dimension, not an unstated universal rule.
- **Pattern count is not musical development.** Repeated patterns can be elegant; many unique patterns can be incoherent. Structural metrics are evidence, not automatic quality scores.
- **A module container does not establish tracker craft.** Long prerendered phrases can obscure the very sequencing skill the benchmark appears to test.
- **Loop cleanliness is musical, not merely numerical.** Cadence, groove, sustained notes, and effect memory matter alongside waveform discontinuity.
- **A scrolling tracker video proves little.** Scopes and pattern motion do not establish authorship, originality, portability, or compositional quality.
- **No listening means a restricted compositional task.** This chiefly tests text-mediated planning, synthesis coding, and symbolic sequencing without auditory feedback—not the normal tracker compose/listen/revise workflow.

# Recommended changes (ordered, minimal)

1. **Constrain claims now:** collection/renderability only; no musical ranking from status. **Cost:** Documentation.
2. **Preregister the final campaign and disclose all pilots.** Use an externally timestamped manifest and publish every reserved outcome. **Cost:** Administrative.
3. **Audit and freeze effective provider routes/payloads.** Report comparisons as complete systems where equivalence is impossible. **Cost:** Per-route inspection.
4. **Correct budget terminology and test multi-call behavior.** Expose exact limits; count commands separately from agent steps. **Cost:** Small code/test change.
5. **Log request starts, failures, and unknown usage.** Split termination from artifact validity. **Cost:** Small schema change.
6. **Define the submission boundary.** State whether raw XM editing and long phrase samples are allowed; separate optional companion collection. **Cost:** Rules and minor code.
7. **Archive reproducible local infrastructure.** Full source revision, image retrieval, dependency lock, proxy binary digest. **Cost:** Storage and provenance.
8. **Add repeated-loop and independent-render checks.** Keep compatibility separate from aesthetics. **Cost:** Extra render dependency/time.
9. **Freeze a blinded human evaluation protocol before ranking.** Include musical and tracker-structural assessments as distinct outcomes. **Cost:** Expert time.
10. **If generalizing beyond these artifacts, run a new repeated-attempt study.** Do not retrofit retries into the claimed one-attempt campaign. **Cost:** Additional inference and judging.


<!-- usage: {"completion_tokens": 4252, "total_tokens": 23256, "prompt_tokens": 19004, "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0, "cached_creation_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 113}} model: gpt-6-astra -->
