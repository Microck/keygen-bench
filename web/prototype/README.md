# FT2-styled results preview

A FastTracker II-styled results site. The native preview has Tracker, Results, Scoring and Support pages; historical mode retains the Rankings label. The original layout and page transition are unchanged.

## Published snapshot

[Inspect the results](https://ubuntu-paris.tailc896c6.ts.net/?page=ranking).

The current snapshot, `keygen-public-20261002-v6`, publishes one cohort: **Max-tier, prompt v2 (highest declared tier per exact route)** from the finished campaign `next-max-tier-prompt-v2-ashburn-20261001`, plus the later attempts of its OAuth independent-repeats campaign `next-max-tier-prompt-v2-oauth-repeats-20261001`. It has no Cohort selector, so every page opens this cohort.

- Ranking uses attempt 1 only, the same predetermined slot for every model. The Results table is identical to v5: 22 of the campaign's 34 models, each with its attempt-1 score. Each row shows its declared tier and output cap, for example `highest declared tier: xhigh, 128k output`, the score breakdown with its noise factor, wall minutes and the XM, WAV, MP3 and JSON downloads. Claude Fable 5.1's attempt 1 keeps its recorded `FINALIZATION_ERROR` label with a note: the artifact-archive upload timed out after its eligible evaluation (craft 65.0) completed.
- 17 ranked models also ran repetitions 2 and 3. Their attempt switcher (Tracker, and the Attempts panel in the Results detail) lists `Attempt 1 (ranked)`, then each later attempt. The 18 eligible later attempts of 10 models (claude-fable-5, claude-fable-5-1, claude-opus-4-5-20251101, gpt-5.5, gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra, gpt-6-astra, gpt-6-luna and gpt-6.1-sol) are playable with their own XM, WAV, MP3, JSON and score breakdown, marked `not ranked`. Failed and unstarted attempts are labels without media, for example `Attempt 2: failed (quota)` or `Attempt 3: not run (quota)`. No median, range or other aggregate is shown.
- Media for evicted attempts were restored from checksum-verified gdrive2 archives.
- The Support page's **Pending: no eligible result** list gives each missing model's reason: 12 routes stopped at attempt 1 by a provider usage limit or exhausted account funds, so attempts 2 and 3 never started, and `claude-opus-5` was excluded before launch because of its content filter.

Earlier cohorts (provider-default main, pilot, recovery and continuation) are not published in v6. The v5 and v4 roots stay on disk.

This is a fixed snapshot, not a live campaign monitor. Scores are auxiliary craft-v7 diagnostics, not musical-quality ranks.

Deployment paths, hashes and verification are in [`publication-20261002-v6.json`](publication-20261002-v6.json); earlier releases are recorded in [`publication-20261002-v5.json`](publication-20261002-v5.json), [`publication-20261001-v4.json`](publication-20261001-v4.json) and [`publication-20261001.json`](publication-20261001.json). HTTPS uses the controller's existing Tailscale Funnel capability and a dedicated persistent `keygen-preview.service`. Only HTTPS port 443 is used; the existing port-10000 forwarding and stopped Minecraft service were left alone. No Cloudflare service or purchase is involved.

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

Repeat `--snapshot` to combine controller exports. Export separate cohorts with `--scope pilot`, `--scope continuation`, or `--scope recovery`. Recovery requires `--cohort /absolute/original/campaign.lock.json` and a separate recovery staging root. The builder rejects duplicate non-pilot model rows and a recovery that would replace an existing original selection.

A model withheld from a cohort's frozen roster before launch has no attempt to export. List it on the Support page with `--excluded-model COHORT_KEY MODEL REASON`, for example `--excluded-model highest-declared-tier/prompt-v2 claude-opus-5 "provider content filter blocked its qualification pilots"`. The cohort must be published and the model must be outside its roster. Roster models without a first success carry a reason derived from their recorded attempt statuses and failure categories; provider error strings stay private.

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

Every eligible repetition is verified from its own attempt directory (local media or the checksum-verified archive). Its provenance records the attempt ordinal, the source campaign hash, the condition fingerprint and "independent predetermined repetition" instead of a first-success selection. The snapshot's `repetition_groups` list every declared attempt per model, including failed and unstarted ones, which have no playable run, plus attempts outside the condition, such as an operator-cancelled main slot. An unstarted slot names the stopping failure category of an earlier attempt in its campaign (`stopped_by`). The build needs the linked main snapshot in the same invocation. A group attaches to its model's ranked main row only if that row is the group's repetition 1, matching campaign, ordinal 1, profile, inputs and evaluation; otherwise the build fails. Repetition 1 is then published once, under the main slug; each later eligible repetition becomes an unranked run `<model>-max-tier-a<ordinal>` with `ranked: false` and `attempt_of: <main slug>`. Roster, ranking and availability counts stay those of the main snapshot; no median, range or other aggregate is exported.

A rerun-queue campaign (policy `independent_repetitions_infrastructure_reruns`) uses the same `--scope repetitions`. Pass the queue's root and lock, and `--linked` for every campaign it takes origins from (main and repeats):

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

Each ordinal's sample is the last attempt of its rerun chain, wherever it ran; it is verified and exported from its own attempt directory, so an ordinal the queue did not rerun keeps its origin's result. Each attempt lists the attempts it superseded (`superseded`, status and failure category only, no media) and whether it still awaits a rerun (`queue_pending`). In the build, a queue group replaces the repeats group of the same model, together with that group's runs; models outside the queue keep their repeats groups. The replaced repeats campaign must be one the queue links to, and every linked campaign must be published as a main or repetitions snapshot in the same build. A queue model without an origin in any linked campaign is a roster addition (`roster_addition`): it joins its cohort's roster, its eligible attempt 1 is a ranked row named and slugged like a main row, with a note on when it ran, and its later attempts attach to that row. A roster addition without an eligible attempt 1 is listed as pending with its chain's state; if it has eligible later attempts but no eligible attempt 1, the build fails, because those attempts have no ranked row to attach to. Superseded attempts show as labels such as `first run failed (quota), rerun`; reruns label their attempt, for example `Attempt 2 (rerun after quota, not ranked)` or `Attempt 3: pending rerun (quota)`.

Keep frozen controller source unchanged. When copying the publication tools outside that repository, copy `collect_public.py`, `build.py` and `data-src/prices.json` together, and set `PYTHONPATH` to the original controller repository. Set `RCLONE_CONFIG` to its private configuration when archive downloads are needed; never copy that configuration into public output.

Each publication root must be a new, empty directory. The server requires an explicit root, binds to loopback by default, denies directory listings and hidden or symlink paths, and supports byte ranges for audio seeking. Never serve the repository, a controller root or an archive staging root. The supplied service unit records this deployment's actual paths; point it at a successfully built new release before restarting only the preview service.

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

- `main` retains the original first eligible successes.
- `continuation` identifies actual new results from separately frozen native cohorts.
- `recovery` identifies archive-only recovered historical attempts, including their reconstructed-status provenance.
- `pilot` retains the separately labeled musical pilot outside main counts.
- `repetitions` adds the later predetermined independent repetitions of one frozen condition, across the companion and linked campaigns, and the reruns of a later infrastructure rerun queue. Ranking stays on attempt 1: the Results table lists the main rows, unchanged, plus the attempt-1 row of any model the queue added after requalification. A repeated model's attempt switcher, in the Tracker and in the Results detail, lists `Attempt 1 (ranked)` and each later attempt; eligible ones play with their own media and score breakdown and are marked `not ranked`, the others are labels such as `Attempt 3: not run (quota)`. A rerun attempt says so (`rerun after quota`) and its superseded runs are labels without media. The Support page lists every attempt with its status. Attempts are never aggregated.

Scopes apply within a cohort. Each frozen campaign's experimental condition (provider default effort, declared tier or max-tier, plus prompt version) is its own cohort with its own table, roster and counts. Max-tier rows carry a `-max-tier` slug and a `(max-tier)` name suffix so they never collide with an earlier cohort's row for the same model. A selected attempt whose finalization failed only after its evaluation completed keeps its recorded status, such as `FINALIZATION_ERROR`, with an explanatory note.

Public output contains original XM and canonical WAV files, MP3 listening derivatives, compact row traces and allowlisted evaluation summaries. Cohort, evaluator, profile and artifact hashes remain available. Full profiles, status files, trajectories, worker logs, provider routes, private configuration and credentials are not published.

Maker list-price estimates use the prices retrieved on 2026-09-29, not actual bills or whole-campaign expenditure. Unknown prices stay `n/a`. The native Support page lists each cohort's unfinished states separately, removes published continuation identities from that list, and marks the retained pilot without requesting another attempt. Unconfirmed donation links and historical fundraising estimates are not presented as current.

`build.py --legacy` explicitly targets the frozen historical report under `legacy/previous-work-20260930/benchmark/runs` and labels its output historical. It cannot be combined with current snapshots. Generated `dist/` and `dist-public/` directories are gitignored.

## Fonts and logos

- **Fonts.** These are the original FT2 bitmap fonts from ft2-clone, by Vogue and 8bitbubsy, licensed CC BY-NC-SA 4.0 (see `core/ft2gfx/LICENSE-gfx.txt`). `build_fonts.py` converts them to web fonts.
- **Logos.** `core/logos.js` holds 16x16 pixel art redrawn from the maker logos Artificial Analysis uses.

## Preview limits

The row trace drives the tracker position. Scopes are visual emulations from XM pattern/sample data, not live native PCM scopes. The player uses the derived MP3; the `.WAV` link provides the untouched canonical evaluation audio, and `.JSON` provides the sanitized evaluation and provenance summary.

No historical prototype rows are mixed into this snapshot. Models without an eligible published output have no fabricated zero score. Native continuation cohorts retain their own configuration and evaluator fingerprints rather than implying that historical inference was rerouted.
