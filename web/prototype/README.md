# FT2-styled results preview

A FastTracker II-styled results site. The native preview has Tracker, Results, Scoring and Support pages; historical mode retains the Rankings label. The original layout and page transition are unchanged.

## Published snapshot

[Inspect the results](https://ubuntu-paris.tailc896c6.ts.net/?page=ranking).

The current snapshot, `keygen-public-20261001-v4`, publishes two cohorts in separate tables chosen with the Results page's **Cohort** selector. Results from different cohorts are never listed or ranked together.

- **Max-tier, prompt v2 (highest declared tier per exact route)** has 19 of 34 models with an eligible result from `next-max-tier-prompt-v2-ashburn-20261001`, captured at 21:16:07 UTC while that campaign was still running. Each row shows its declared tier and output cap, for example `highest declared tier: xhigh, 128k output`. Claude Fable 5.1's attempt 1 keeps its recorded `FINALIZATION_ERROR` label: the artifact-archive upload timed out after its eligible evaluation (craft 65.0) completed. Media for 18 evicted attempts were restored from checksum-verified gdrive2 archives; Fable 5.1's media were hash-verified locally.
- **Provider default effort, prompt-v1** keeps the earlier 38 playable rows unchanged: 30 original main first successes, six native continuation results, one archive-only recovered GPT-5.4 result and one retained Qwen3.8 Flash musical pilot. Its availability count is **37 of the original 57 models**; the pilot stays outside that numerator. The continuation metadata cutoffs are 11:08:25 UTC for Ashburn and 11:08:27 UTC for Paris.

This is a fixed snapshot, not a live campaign monitor. Later completions need an explicit refresh. Scores are auxiliary craft-v7 diagnostics, not musical-quality ranks. Original outcomes and selections remain unchanged, including Astra's original second-attempt selection.

Deployment paths, hashes and verification are in [`publication-20261001-v4.json`](publication-20261001-v4.json); the earlier single-cohort release is recorded in [`publication-20261001.json`](publication-20261001.json). HTTPS uses the controller's existing Tailscale Funnel capability and a dedicated persistent `keygen-preview.service`. Only HTTPS port 443 was added; the existing port-10000 forwarding and stopped Minecraft service were left alone. No Cloudflare service or purchase is involved.

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

The four scopes remain separate:

- `main` retains the original first eligible successes.
- `continuation` identifies actual new results from separately frozen native cohorts.
- `recovery` identifies archive-only recovered historical attempts, including their reconstructed-status provenance.
- `pilot` retains the separately labeled musical pilot outside main counts.

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
