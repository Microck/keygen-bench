# FT2 website

This is the canonical frontend. It keeps the FT2 tracker, audio playback and looping, rankings with best/first/all-attempt views, scoring explanation, and support page. There is no JavaScript build step and no checked-in result dataset.

## Design and historical results

The hosted FT2 interface is the main design. Maintain it here; updating campaign data does not authorize a redesign. Legacy and current results should use this same frontend with distinct cohort labels and provenance.

An archived `dist/` directory holds a generated dataset and media, not the frontend implementation. Older frontend revisions belong in a separate private archive or retained history, not a second active source tree. Preserve their associated run evidence before removing an operational checkout. Neither this source repository nor a published results snapshot is a complete backup of all attempts.

All commands below run from the repository root. Use your own local campaign and dedicated output directories. The tools do not contact a private host, discover campaigns, or fetch results from remote storage.

## Requirements

- Python 3.11 or newer.
- A completed local campaign with its frozen `campaign.lock.json`, statuses, profiles, original XM files, canonical WAV files, and any playback traces pinned by the profiles. Export verifies these files against their hashes; missing or changed files stop the export.
- `ffmpeg` with the `libmp3lame` encoder for `collect_public.py`. MP3 is a listening derivative, not an evaluation input.
- For Open Graph images or font regeneration, install the optional Python dependencies:

  ```sh
  python3 -m pip install -r web/classic/requirements.txt
  ```

`build.py`, `build_spend.py`, and `serve.py` use the Python standard library and repository modules. The browser fonts and bitmap assets are already included. `build_og.py` requires Pillow and FontTools with WOFF2 support. It decodes the bundled WOFF2 fonts before rendering them with Pillow; it does not rely on installed system fonts.

## Export, build, and serve

Choose paths outside the campaign directory. The publication path must be new or empty.

```sh
python3 web/classic/collect_public.py \
  --campaign-root /absolute/campaign \
  --output /absolute/public-snapshot

python3 web/classic/build.py \
  --snapshot /absolute/public-snapshot \
  --publish-root /absolute/publication

python3 web/classic/build_og.py --dist /absolute/publication/dist

python3 web/classic/serve.py \
  --root /absolute/publication --bind 127.0.0.1 --port 8780
```

Open <http://127.0.0.1:8780/>. The publication contains only the frontend, its fonts/icons, sanitized `dist/data.json`, verified media, and per-run evaluation summaries. Support links to `CONTRIBUTING-RUNS.md` on the GitHub repository's `main` branch. It does not contain campaign configurations, trajectories, credentials, source code for the Python tools, or the input pricing/usage files.

The exporter uses `benchmark.report` to select eligible results without rescoring. The default `--scope main` exports the campaign's first eligible success per model. For a campaign configured with independent repetitions or an infrastructure rerun queue, use `--scope repetitions`. If it links other campaigns, supply each root and frozen lock explicitly:

```sh
python3 web/classic/collect_public.py \
  --campaign-root /absolute/repetitions \
  --scope repetitions \
  --linked /absolute/campaign /absolute/campaign/campaign.lock.json \
  --output /absolute/repetitions-snapshot

python3 web/classic/build.py \
  --snapshot /absolute/public-snapshot \
  --snapshot /absolute/repetitions-snapshot \
  --publish-root /absolute/new-publication
```

Repeat `--linked ROOT COHORT` for every required linked campaign and `--snapshot` for every snapshot you intend to publish. `--cohort` selects a frozen lock when it is not at the default path. `--scope pilot` labels an exhibition separately; `--scope continuation` labels a separately frozen continuation. The builder checks cohort membership, attempt links, media paths, hashes, and unique result slugs. It rejects snapshots without cohort labels rather than searching old runs to reconstruct them.

The frontend groups playable attempts by model, opens the best attempt by default, and offers first/all-attempt views. Publication metadata retains the frozen campaign selection and attempt provenance. These display choices do not alter the evaluator's scores.

`core/intro.js` is the preloader. It is a classic script, so it paints before
the module graph loads, and it draws with its own 5x7 font rather than waiting
for the FT2 fonts. `app.js` reports the results and font loads through
`bootIntro.track()`, then calls `done()` after mounting the site underneath, or
`fail()` to reveal the error message. Locked serial characters show completed
steps only: each settled load, and the mount, locks its share of the serial,
staggered over a fraction of a second. The first load in a browser session plays for at
least 1.3 seconds; a click or key press ends that minimum, and later loads in
the session last only as long as loading. With reduced motion, the scene holds
still and fades out in 200 ms.

The Rankings **Best / Average** buttons sit at the right of the toolbar,
replacing the ranked count. They change ranking order without changing the
columns, attempt-view filter, selected attempt or sidebar layout. Displayed
scores, output tokens and duration remain the individual attempt's values in
both modes. Ranking Cost and podium costs total the model's ordinal attempts.
Known failed-attempt costs are included. Bounded costs display their upper
estimate, rounded up to cents, and Cost sorts by that estimate. Missing costs
are excluded and described in tooltips, not marked with a visible `+`.
The sidebar remains the selected attempt's cost, with no cost-range paragraph.
Average uses the arithmetic mean of scored, predetermined ordinal slots;
infrastructure reruns replace their original slot rather than adding a sample.
Failed and unscored slots do not become zero scores. Incomplete models sort
after complete models and do not receive average ranks or podium places.
Share `/rankings?mode=average` to open Average directly.

The `Attempt` column shows the individual attempt score in both modes.
Its tooltip and podium tooltips explain the ordering metric; Average tooltips
include the mean and scored-slot coverage. Sidebar `Best rank` is the model's
best-attempt rank, not its Average position. Tab reaches model and podium
selection buttons; Enter or Space selects a result without starting playback.

Below 600 CSS pixels, Tracker, Rankings and Support stack their panels and
scroll vertically. Rankings keeps a minimum-width Model column and horizontal
table scrolling. Tracker download and channel controls remain above its sidebar.
Support donation controls wrap and spend rows keep names and amounts separate.

The playback slider supports Home, End and all four arrow keys. Arrows seek
five seconds, clamped to the track bounds; paused seeking stays paused.
Accessible slider values follow playback, seeking and Stop. Scoring and Support
retain the selected model and ordinal in browser history, including reloads
and Back/Forward navigation.

Tracker instrument and order entries are native buttons. Tab reaches each
entry; Enter or Space selects an instrument or seeks to an order without
starting paused playback. The highlighted order and its pressed state follow
the playback trace, including media-clock rounding at sample boundaries.

Scoring distribution markers are also native buttons. Focus names the model
and measure in the readout; Enter or Space opens its Tracker result.
Example names and controls wrap into content-sized rows on narrow screens.

Tracker dropdown labels and score-card headings show only the model name.
The Model popup keeps its original width. Company counts are distinct models,
not attempt counts. The picker lists each model once, opening its best attempt
by default and retaining the current attempt when another ordinal was opened
from Rankings.

To order the picker by model release, put reviewed public release metadata in
`dist/model-metadata.json`. It is an object keyed by the exact public `model_key`;
each entry contains `release_date` as `YYYY-MM-DD` and `source_url` pointing to
the maker's release announcement. Models sort newest first within their company.
Unknown dates sort last, with model-name ties deterministic. Campaign and
attempt timestamps are not model release dates.

The Rankings `Cons.` column sorts by best score minus worst score across at
least two scored attempts. Its first activation puts the smallest spread first;
activate it again for the largest spread first. Models with fewer than two
scored attempts stay last in both directions. The visible sort note and marker
tooltips explain the metric. A consistently low-scoring model can have a small
spread; marker colors indicate individual scores, not consistency ranks.

## Pricing and spend

No price catalog or historical spend ledger is bundled. Omit `--prices` during export to leave cost estimates unknown. To publish estimates, pass a local pricing JSON file to `collect_public.py --prices /absolute/prices.json`.

The pricing file has a top-level `models` array. Each entry contains:

| Field | Meaning |
| --- | --- |
| `id` | Exact public model ID used by the export |
| `maker` | Display name of the model's maker |
| `input_usd_per_m` | USD per million input tokens, or `null` |
| `cached_input_usd_per_m` | USD per million cached input tokens, or `null` to use the input rate |
| `output_usd_per_m` | USD per million output tokens, or `null` |
| `cache_write_usd_per_m` | Optional USD per million default/5-minute cache-write tokens |
| `cache_write_1h_usd_per_m` | Optional USD per million 1-hour cache-write tokens |
| `tiers` | Optional rate rows with an inclusive `min_prompt_tokens` threshold |
| `source_url` | Maker's public pricing page |

Input and output rates must both be known or both be `null`. The existing maker-domain allowlist in `build.py` excludes proxy/aggregator prices from public estimates. Add a maker's pricing domain there when supporting a new maker. Keep rate dates and source notes in your input file if needed; these notes are not published. Review prices before every publication.

For tiered pricing, supply per-response usage so each request selects its own
context tier before costs are summed. A large cumulative input-token total does
not establish the size of any one request. Positive cache-write prices require
an explicit token breakdown for an exact cost, including zero counts when no
writes occurred. Where recorded usage and documented prices support finite
bounds but not an exact amount, `cost_range_usd` contains `min`, `max`, and a
readable `reason`. The website displays that range, not a guessed exact price.
The narrow documented `space-bunny-free` exception permits its public zero-price
route; it does not permit arbitrary proxy catalogs or guessed free pricing.

Without a separate ledger, the support page totals only the published attempts and labels that scope. Missing usage or prices remain unknown; a partial total has a `+` and reports incomplete coverage. The site never claims this is a provider bill.

To include other attempts, including failed or unpublished ones, prepare a local JSON file with a top-level `attempts` array. Each entry needs:

- `id`: a nonempty attempt ID unique across all supplied files. Use a campaign-qualified ID if ordinals repeat. Duplicate IDs are rejected rather than guessed to be copies.
- `model`: the public model ID matching the pricing table.
- `totals`: an object with nonnegative integer `prompt_tokens`, `cached_tokens`, and `completion_tokens`, or `null` when usage is unknown. Prompt tokens include fresh input, cached reads and cache writes; completion tokens include billed reasoning output. Optional `cache_write_tokens` and `cache_write_1h_tokens` distinguish write durations. Cached reads and writes together cannot exceed prompt tokens.
- `requests`: an optional nonempty array of per-response usage objects or `null` entries for responses with missing usage. Its recorded counts must sum exactly to `totals`.
- `usage_complete`: an optional boolean. Set it to `false` if the totals describe only the observed portion of an attempt; missing response usage also makes the attempt incomplete.

```sh
python3 web/classic/build_spend.py \
  --input /absolute/attempt-usage.json \
  --prices /absolute/prices.json \
  --output /absolute/publication/dist/spend.json
```

Repeat `--input` to combine files. The tool reads only these files; it does not search logs, infer attempts from equal token counts, or use SSH. The output contains model aggregates and counts, not attempt IDs, filesystem paths, or account details. Include every attempt you want counted, even when its usage is unknown. An empty input is an empty ledger, not a substitute for missing usage evidence.

Deduplicate observations by exact physical attempt identity before supplying the
ledger. Equal token totals are not evidence that two attempts are the same.
Include started qualification checks, failed requests, superseded runs, pilots
and older experiments when their records are available; do not count unstarted
planned ordinal slots as paid attempts.

The known total includes recorded, priceable portions of incomplete attempts.
Such attempts remain in `unpriced_runs`, and `partial_priced_runs` counts those
with known contributions. `unknown_usage_runs` counts incomplete usage records.
Unknown costs are not zero. The Support tooltip states the attempt scope and
missing-cost coverage; missing historical records prevent a claim that every
past request or the actual provider bill is represented.

The ledger can also include `recorded_usage_cost_range_usd`, bounded over the
recorded usage only. It includes supported exact contributions and supported
intervals once each. It is not an upper bound on lifetime spending: unknown
usage and unavailable prices remain outside it. Support displays one
recorded-usage estimate in its heading and model rows, using the upper value
rounded up to cents where a range exists. The compact tooltip lists attempt
counts, missing-cost coverage and the list-price caveat without raw ledger
field names or a visible cost-range warning.

## Update a publication

1. Finish and evaluate the local runs through the benchmark workflow.
2. Export into a new snapshot directory with the desired local pricing table.
3. Build into a new empty publication directory. Do not build over a served release.
4. Generate the optional spend summary and rerun `build_og.py` against the new `dist/` directory.
5. Serve the new directory locally and check playback, seeking, looping, downloads, rankings, scoring, support, and direct model links before publishing it.

The source of support links, wanted-model estimates, and manually recorded fundraising amounts is `core/content.js`. Review them before deploying a fork or changing a fundraising goal. Those planning estimates are separate from measured attempt usage and the optional spend ledger.

The Support page pairs a combined funding panel with a contributor-run panel.
Keep provider and cost caveats in `SUPPORT.contribution`, and the guide URL in
`SITE.contributorGuide`. The guide currently points to the contributor-workflow
commit so it works before that PR merges. A private repository requires GitHub
access to open it; do not advertise the link as public until the repository is
public.

Open Graph generation writes `dist/og/home.png`, one image per model, and `dist/og/meta.json`. The server uses that metadata to inject route-specific titles and preview tags. Without OG generation, the site still works but has no generated link-preview cards. Rerun OG generation whenever the results change.

The server supports `/tracker`, `/rankings`, `/scoring`, `/support`, and model/attempt URLs, plus byte ranges for audio seeking and downloads. JSON, JavaScript, CSS and XM files are sent gzip-compressed to browsers that accept it (a pretty-printed 6.3 MB `data.json` becomes about 0.76 MB); range requests and audio are always sent uncompressed. It rejects dotfiles, symlinks, and directory listings. Serve only the dedicated publication directory, never the repository or a campaign directory. For public deployment, put this local server behind a proxy with HTTPS; configure the proxy to set trustworthy `Host` or `X-Forwarded-Host` and `X-Forwarded-Proto` headers for preview URLs. No deployment-specific service files are included.

### Static hosting (GitHub Pages or Netlify)

`export_static.py` turns a publication into a static site for a CDN host, without `dist/media/`:

```sh
python3 web/classic/export_static.py --publication /absolute/publication --out /absolute/static \
  --site-url https://keygen.micr.dev --media-map /absolute/media-map.json \
  --redirect-from keygen-bench.netlify.app
netlify deploy --prod --dir /absolute/static
```

The live site is published with `--host github-pages` to the public repository `Microck/keygen-bench-site` (GitHub Pages, custom domain `keygen.micr.dev`, HTTPS enforced): the exporter writes `404.html` (the app shell, so unlisted app routes such as attempt URLs still render), `CNAME` and `.nojekyll` instead of `netlify.toml`. GitHub Pages has no deploy credits or bandwidth meter (soft limits: 1 GB per site, about 100 GB a month), but response headers cannot be configured. Push the output as the repository's `main` branch to deploy.

`--media-map` maps every media file name to its absolute URL. The live site serves MP3 renders, XM modules and one lossless FLAC loop source per WAV (`ffmpeg -c:a flac`, same name with `.flac`) from public GitHub Pages repositories (`Microck/keygen-bench-media`, `Microck/keygen-bench-media-2`; each published site must stay under 1 GB, so the files are split by size). GitHub Pages sends `Access-Control-Allow-Origin: *` and honours byte ranges, which the player's `fetch` of modules and loop sources and MP3 seeking need. The exporter rewrites `data.json` media paths to those URLs (the frontend's `mediaUrl` accepts absolute URLs), writes one HTML file per route in `dist/og/meta.json` with that route's preview tags (a static host cannot inject them per request), writes `netlify.toml` falling back to `index.html` for other app routes and redirecting `--redirect-from` hosts to the site URL, drops `dist/evaluations/` (not read by the site) and moves each run's playback trace to `dist/traces/<slug>.json`, which the tracker loads when it opens the run (`data.json` drops from 2.8 MB to 0.95 MB, about 130 kB with Brotli). Cross-origin `.XM`/`.MP3` buttons open the file instead of forcing a download, because browsers ignore `download` across origins.

## Regenerate fonts

Only regenerate fonts when changing their source bitmaps or metrics:

```sh
python3 web/classic/build_fonts.py
```

The command reads `core/ft2gfx/` and writes `core/fonts/ft2-font{1,2,3}.woff2`. Rebuild the publication and OG images afterward. Preserve `core/ft2gfx/LICENSE-gfx.txt` and the attribution in the repository's `NOTICE.md`; the FT2 graphics and derived fonts have their own license.
