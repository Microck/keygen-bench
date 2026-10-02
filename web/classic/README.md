# FT2 website

This is the canonical frontend. It keeps the FT2 tracker, audio playback and looping, rankings with best/first/all-attempt views, scoring explanation, and support page. There is no JavaScript build step and no checked-in result dataset.

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

Open <http://127.0.0.1:8780/>. The publication contains only the frontend, its fonts/icons, sanitized `dist/data.json`, verified media, and per-run evaluation summaries. It does not contain campaign configurations, trajectories, credentials, source code for the Python tools, or the input pricing/usage files.

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
| `source_url` | Maker's public pricing page |

Input and output rates must both be known or both be `null`. The existing maker-domain allowlist in `build.py` excludes proxy/aggregator prices from public estimates. Add a maker's pricing domain there when supporting a new maker. Keep rate dates and source notes in your input file if needed; these notes are not published. Review prices before every publication.

Without a separate ledger, the support page totals only the published attempts and labels that scope. Unknown costs show `n/a`; a partial total has a `+` and reports the number of unpriced attempts. The site never claims this is a provider bill.

To include other attempts, including failed or unpublished ones, prepare a local JSON file with a top-level `attempts` array. Each entry needs:

- `id`: a nonempty attempt ID unique across all supplied files. Use a campaign-qualified ID if ordinals repeat. Duplicate IDs are rejected rather than guessed to be copies.
- `model`: the public model ID matching the pricing table.
- `totals`: an object with nonnegative integer `prompt_tokens`, `cached_tokens`, and `completion_tokens`, or `null` when usage is unknown. Prompt tokens include cached input; completion tokens include any billed reasoning output. Cached input cannot exceed total prompt input.

```sh
python3 web/classic/build_spend.py \
  --input /absolute/attempt-usage.json \
  --prices /absolute/prices.json \
  --output /absolute/publication/dist/spend.json
```

Repeat `--input` to combine files. The tool reads only these files; it does not search logs, infer attempts from equal token counts, or use SSH. The output contains model aggregates and counts, not attempt IDs, filesystem paths, or account details. Include every attempt you want counted, even when its usage is unknown. An empty input is an empty ledger, not a substitute for missing usage evidence.

## Update a publication

1. Finish and evaluate the local runs through the benchmark workflow.
2. Export into a new snapshot directory with the desired local pricing table.
3. Build into a new empty publication directory. Do not build over a served release.
4. Generate the optional spend summary and rerun `build_og.py` against the new `dist/` directory.
5. Serve the new directory locally and check playback, seeking, looping, downloads, rankings, scoring, support, and direct model links before publishing it.

The source of support links, wanted-model estimates, and manually recorded fundraising amounts is `core/content.js`. Review them before deploying a fork or changing a fundraising goal. Those planning estimates are separate from measured attempt usage and the optional spend ledger.

Open Graph generation writes `dist/og/home.png`, one image per model, and `dist/og/meta.json`. The server uses that metadata to inject route-specific titles and preview tags. Without OG generation, the site still works but has no generated link-preview cards. Rerun OG generation whenever the results change.

The server supports `/tracker`, `/rankings`, `/scoring`, `/support`, and model/attempt URLs, plus byte ranges for audio seeking and downloads. It rejects dotfiles, symlinks, and directory listings. Serve only the dedicated publication directory, never the repository or a campaign directory. For public deployment, put this local server behind a proxy with HTTPS; configure the proxy to set trustworthy `Host` or `X-Forwarded-Host` and `X-Forwarded-Proto` headers for preview URLs. No deployment-specific service files are included.

## Regenerate fonts

Only regenerate fonts when changing their source bitmaps or metrics:

```sh
python3 web/classic/build_fonts.py
```

The command reads `core/ft2gfx/` and writes `core/fonts/ft2-font{1,2,3}.woff2`. Rebuild the publication and OG images afterward. Preserve `core/ft2gfx/LICENSE-gfx.txt` and the attribution in the repository's `NOTICE.md`; the FT2 graphics and derived fonts have their own license.
