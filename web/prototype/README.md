# FT2-styled results preview

A FastTracker II-styled results site. The native preview has Tracker, Results, Scoring and Support pages; historical mode retains the Rankings label. The original layout and page transition are unchanged.

## Published snapshot

`keygen-public-20261003-v7` is the verified local release at `web/prototype/releases/keygen-public-20261003-v7/`. It is not deployed. The [existing live v6 site](https://ubuntu-paris.tailc896c6.ts.net/?page=ranking), its service, port-10000 forwarding and stopped Minecraft service were not changed.

V7 publishes one cohort, **Max-tier, prompt v2, highest declared tier per exact route**, from all 12 captured Ashburn and Paris campaign roots. There is no Cohort selector. The still-running Go parallel queue contributes only finished eligible results from the captured metadata; collection did not stop or alter it.

- The Results table ranks 36 of 44 roster models by their best eligible score among three predetermined ordinals, labeled `Best of 3`. Ties within a model select the lowest ordinal. Each row shows the selected ordinal and scored count. Of the ranked models, 29 have 3/3 scored, four have 2/3 and three have 1/3. No mean or median is shown.
- All 98 eligible attempts are playable in the Tracker and Results attempt switcher, with separate XM, canonical WAV, MP3, JSON and score breakdowns. The 62 alternatives are labeled `not ranked`. The 34 unscored slots have labels and reasons without media or fabricated scores. Infrastructure reruns fill an ordinal rather than add an attempt.
- The Support page lists eight roster models with no eligible result: seven blocked by quota and `hy4-preview` blocked by a provider protocol failure. It also lists `claude-opus-5`, excluded before launch because the provider content filter blocked its qualification pilots.
- All 18 Gemini attempts are published. Their provider is Google AI Studio, their highest declared tier is `high`, and their output cap is 65,536 tokens. Each attempt retains its shared-VM provenance, including three attempts per VM, slot and 2-CPU pin. These fields do not affect ranking.
- Gemini 3 Flash attempt 1 uses its offline rescored profile, craft 75.4, with a visible note. The original ineligible profile, status and archive remain unchanged. Claude Fable 5.1 attempt 1 retains its `FINALIZATION_ERROR` note and eligible score of 65.0.
- Presentation inputs for 95 published attempts came from checksum-verified gdrive2 archives. Three used retained media verified against their profiles' pinned hashes.

The 418-file release is 1,424,041,456 bytes. Every file matched its source or generated-summary manifest and its full local HTTP response hash. All 392 artifact byte-range checks passed. A real Chromium session parsed all 98 XM files, decoded all 98 MP3 files, checked the ranking order, played and switched Gemini and Go attempts, and checked Pending and Scoring. The consistency marker remains pending in [issue #21](https://github.com/Microck/keygen-bench/issues/21).

Serve only the release directory:

```sh
python3 web/prototype/serve.py \
  --root web/prototype/releases/keygen-public-20261003-v7 --port 8797
```

This is a fixed snapshot, not a live campaign monitor. Scores are auxiliary craft-v7 diagnostics, not musical-quality ranks. Provider-default, pilot, recovery and continuation cohorts are not included.

Counts, campaign roots, rescore provenance, hashes, screenshots and verification are in [`publication-20261003-v7.json`](publication-20261003-v7.json). The live deployment is still recorded in [`publication-20261002-v6.json`](publication-20261002-v6.json); earlier releases retain their own records.

## Build and serve a new snapshot

Run the exporter on the trusted controller holding the frozen campaign and its archive credentials:

```sh
python3 web/prototype/collect_public.py \
  --campaign-root /absolute/native-campaign-root \
  --scope main --output /tmp/public-main-snapshot

python3 web/prototype/build.py \
  --snapshot /tmp/public-main-snapshot \
  --publish-root /tmp/keygen-site-release

python3 web/prototype/serve.py \
  --root /tmp/keygen-site-release --port 8780
```

Repeat `--snapshot` to combine controller exports. Export separate cohorts with `--scope pilot`, `--scope continuation`, or `--scope recovery`. Recovery requires `--cohort /absolute/original/campaign.lock.json` and a separate recovery staging root. Duplicate exports of the same ordinal must have identical pinned evaluation and input hashes; contradictory eligible samples or a recovery replacing an existing original selection are rejected.

A model withheld from a cohort's frozen roster before launch has no attempt to export. List it on the Support page with `--excluded-model COHORT_KEY MODEL REASON`, for example `--excluded-model highest-declared-tier/prompt-v2 claude-opus-5 "provider content filter blocked its qualification pilots"`. The cohort must be published and the model must be outside its roster. Roster models without an eligible ordinal carry reasons derived from their recorded statuses and failure categories; provider error strings stay private.

An independent-repetitions companion campaign (policy `independent_repetitions`, declaring repetitions 2-3 of a main campaign's condition) is exported with `--scope repetitions`. Pass the companion's root, its lock with `--cohort` (default `<campaign-root>/campaign.lock.json`), and each linked campaign's root and lock with `--linked ROOT COHORT`:

```sh
python3 web/prototype/collect_public.py \
  --campaign-root /absolute/companion-repeats-root \
  --cohort /absolute/companion-repeats-root/campaign.lock.json \
  --linked /absolute/main-campaign-root /absolute/main-campaign-root/campaign.lock.json \
  --scope repetitions --output /tmp/public-repetitions-snapshot

python3 web/prototype/build.py \
  --snapshot /tmp/public-main-snapshot \
  --snapshot /tmp/public-repetitions-snapshot \
  --publish-root /tmp/keygen-site-release
```

Every eligible repetition is verified from its own attempt directory, using retained media or its checksum-verified archive. The snapshot's `repetition_groups` list all three predetermined ordinals, including failed and unstarted slots without playable runs, plus attempts outside the condition. The build needs every linked snapshot in the same invocation. It merges samples by cohort, model, condition and ordinal, verifies duplicate evaluations and inputs, and publishes each eligible sample once. Each group's best eligible sample has `ranked: true`; every other eligible sample has `ranked: false` and `attempt_of` pointing to the group's best slug. Ordinals remain separate; no mean or median is exported.

An unlinked standalone independent campaign declaring repetitions 1-3 uses the same `--scope repetitions`, with no `--linked` arguments. Its models join the cohort's original roster. An immutable offline rescore can be selected with `--attempt-override ATTEMPT_ID STAGED_DIR --attempt-override-record RECORD_JSON`. The staged directory must end in the attempt ID and preserve the original campaign, model, ordinal, status and pinned XM/WAV inputs. The audit record verifies historical hashes and the new archive generation; the public summary includes a visible offline-rescoring note. Historical files are never rewritten.

A rerun-queue campaign (policy `independent_repetitions_infrastructure_reruns`) uses the same `--scope repetitions`. Pass the queue's root and lock, and `--linked` for every campaign declared in its frozen policy, including prior queues:

```sh
python3 web/prototype/collect_public.py \
  --campaign-root /absolute/queue-root \
  --cohort /absolute/queue-root/campaign.lock.json \
  --linked /absolute/main-campaign-root /absolute/main-campaign-root/campaign.lock.json \
  --linked /absolute/companion-repeats-root /absolute/companion-repeats-root/campaign.lock.json \
  --scope repetitions --output /tmp/public-queue-snapshot

python3 web/prototype/build.py \
  --snapshot /tmp/public-main-snapshot \
  --snapshot /tmp/public-repetitions-snapshot \
  --snapshot /tmp/public-queue-snapshot \
  --publish-root /tmp/keygen-site-release
```

Each ordinal's sample is the last attempt of its frozen rerun chain, wherever it ran. The collector verifies that sample from its own attempt directory; an ordinal not rerun keeps its origin's result. Each attempt lists superseded infrastructure runs as labels without media and records whether it still awaits a rerun (`queue_pending`). The builder follows source identities and frozen chain precedence rather than snapshot order. Empty queue branches cannot hide a finished sample. Attempts outside the declared condition, including an operator-cancelled main slot replaced by a companion's predetermined repetition, stay listed separately. Every linked campaign must be published in the same build. A queue model without a linked origin joins its cohort's roster after requalification, and its best eligible ordinal is ranked even when attempt 1 has no eligible result. A model with no eligible ordinal is Pending. Scored results and model failures are never rerun or replaced.

Keep frozen controller source unchanged. When copying the publication tools outside that repository, copy `collect_public.py`, `build.py` and `data-src/prices.json` together, and set `PYTHONPATH` to the original controller repository. Set `RCLONE_CONFIG` to its private configuration when archive downloads are needed; never copy that configuration into public output.

Each publication root must be a new, empty directory. The server requires an explicit root, binds to loopback by default, denies directory listings and hidden or symlink paths, and supports byte ranges for audio seeking. Never serve the repository, a controller root or an archive staging root. The supplied service unit describes the existing live deployment; v7 is local-only and does not change it.

The URL parameters are `page=viewer|ranking|scoring|support` and `run=<slug>`.

## Files

- `site.js` is the whole UI.
- `core/transitions.js` holds the page transition.
- `core/content.js` holds the page copy, including the scoring explanation and the disclaimer.
- `core/pattern.js` and `core/fb.js` draw the pattern editor and scopes using the original FT2 fonts.
- `core/player.js` syncs audio to the FT2 row trace.
- `collect_public.py` exports selected cached evaluations and verifies presentation inputs without musical inference or rescoring.
- `build.py` combines sanitized snapshots and copies an explicit public asset allowlist.
- `serve.py` serves only the chosen publication directory with byte-range support.

The UI uses ft2-clone's "Why colors" palette, preset 10, for the classic blue FT2 look. `core/ft2.css` and `core/fb.js` share its panel, bevel and pattern colours. Existing benchmark videos retain the palette used during recording.

## Public data

`collect_public.py` uses the frozen-cohort selection and eligibility checks in `benchmark.report`. Local XM, canonical WAV and row-trace inputs must match the selected profile's pinned hashes. If those inputs were evicted, it verifies the archive checksum, manifest and every member before extracting only presentation inputs into temporary staging.

The five scopes remain separate:

- `main` retains historical first-success provenance and exports every eligible predetermined ordinal with its three-slot group.
- `continuation` identifies actual new results from separately frozen native cohorts.
- `recovery` identifies archive-only recovered historical attempts, including their reconstructed-status provenance.
- `pilot` retains the separately labeled musical pilot outside main counts.
- `repetitions` exports predetermined independent repetitions from standalone campaigns, linked companions and infrastructure rerun queues. The Results table ranks each model by its best eligible ordinal. The Tracker and Results switchers make every eligible ordinal playable with its own media and score breakdown; failed and unstarted slots have labels and reasons without media. Reruns fill their ordinal, with superseded infrastructure runs listed separately. The Support page lists every ordinal and models without eligible results. No mean or median is computed.

Scopes apply within a cohort. Each frozen campaign's experimental condition, including reasoning tier and prompt version, has its own table, roster and counts. Max-tier attempt slugs contain `-max-tier`, their ordinal and an exporting-campaign hash suffix, so linked exports cannot collide. Model labels omit the attempt suffix; each attempt's ordinal is explicit in its switcher and provenance. A result whose finalization failed after its evaluation completed keeps its recorded status, such as `FINALIZATION_ERROR`, with an explanatory note.

Public output contains original XM and canonical WAV files, MP3 listening derivatives, compact row traces and allowlisted evaluation summaries. Cohort, evaluator, profile and artifact hashes remain available. Full profiles, status files, trajectories, worker logs, provider routes, private configuration and credentials are not published.

Maker list-price estimates use the prices retrieved on 2026-09-29, not actual bills or whole-campaign expenditure. Unknown prices stay `n/a`. The native Support page lists each cohort's unfinished states separately, removes published continuation identities from that list, and marks the retained pilot without requesting another attempt. Unconfirmed donation links and historical fundraising estimates are not presented as current.

`build.py --legacy` explicitly targets the frozen historical report under `legacy/previous-work-20260930/benchmark/runs` and labels its output historical. It cannot be combined with current snapshots. Generated `dist/` and `dist-public/` directories are gitignored.

## Fonts and logos

- **Fonts.** These are the original FT2 bitmap fonts from ft2-clone, by Vogue and 8bitbubsy, licensed CC BY-NC-SA 4.0 (see `core/ft2gfx/LICENSE-gfx.txt`). `build_fonts.py` converts them to web fonts.
- **Logos.** `core/logos.js` holds 16x16 pixel art redrawn from the maker logos Artificial Analysis uses.

## Preview limits

The row trace drives the tracker position. Scopes are visual emulations from XM pattern/sample data, not live native PCM scopes. The player uses the derived MP3; the `.WAV` link provides the untouched canonical evaluation audio, and `.JSON` provides the sanitized evaluation and provenance summary.

No historical prototype rows are mixed into this snapshot. Models without an eligible published output have no fabricated zero score. Native continuation cohorts retain their own configuration and evaluator fingerprints rather than implying that historical inference was rerouted.
