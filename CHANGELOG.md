# Changelog

## Unreleased

### Fixed

- Put Terra in release-date order, add official API prices, and calculate complete Responses usage from per-request cache receipts.
- Keep detailed publication disclosures in provenance rather than the score sidebar.

- Keep code-only CI checkouts free of retained run and submission artifacts, avoiding checkout timeouts before tests start.

- Keep the pinned FT2 build script in the deployment checkout so reviewed community bundle verification can run.

- Publish maintainer-verified community bundles through the canonical site pipeline, with playable attempts, source receipts and route disclosures, without comparative ranks.

- Keep Support button-link labels black and simplify the Muse Full access request.

### Added

- Opt-in Muse Code SDK/MCP transport for mini-owned Bash execution, with pinned host/catalog checks, explicit non-frozen provenance, separate Contributor consent and offline round-trip tests.

- Request Muse Wonder Full without a budget or fundraising target, with access-only support-page rendering and a documented SDK/MCP feasibility investigation.

- Copy-paste contributor-agent prompt and stepwise authentication, frozen-contract, spending and publication checkpoints.

- Add deterministic browser regression tests using synthetic local data and audio, without model calls or retained-run publication.

- MIT License for original code and documentation; third-party assets keep their own licenses.
- Community-run guide, three-attempt runner, bundle validator, submission templates and trusted-base validation workflow.
- FT2-style results site with per-model routes, attempt selection, loop playback, scoring explanations and generated Open Graph cards.
- Public-launch checklist covering Git history, personal data, credentials, licenses and release verification.
- Repository agent instructions linking the maintained guides and defining local execution, privacy, provenance and verification boundaries.
- Guided contributor CLI for setup, private configuration, offline preflight, bounded model smoke runs and spending-authorized official submissions.
- OAuth-first contributor login orchestration for Codex, Anthropic and xAI through an explicitly selected local CLIProxyAPI binary, with isolated no-cloak profiles and foreground bridge startup; never treat process completion as verified authentication.
- Explicit API-key login, local status/logout, private-storage consent and endpoint-bound credential reuse, including custom OpenAI-compatible endpoints, Gemini and other major APIs.
- Explicit subscription-OAuth qualification limits and rejection of new Anthropic/Codex bridge contributor runs that cannot preserve frozen settings; retain historical evidence and catalog diagnostics without claiming upstream equivalence.
- Same-route native readiness pilots before community smoke and full runs, with proof retained in private work directories.
- Direct OpenAI and Anthropic API-key routes and public HTTPS custom endpoints for supported native protocols.
- Every attempt of the maintainer max-tier prompt-v2 campaigns and earlier runs under `runs/<model>/`: the three ranked attempts plus all other attempts in `other/`, with trajectories, transport logs, modules, lossless FLAC audio and evaluations (no videos).
- MiniMax M3.1 Flash OpenRouter `:free` results with listener-v1 scores; keep the former Space Bunny Go attempts under `other/`.
- Google AI Studio and Devin native routes.
- xAI OAuth Responses route through OMP's loopback auth-gateway, with an authenticated pre-inference model-catalog identity check.
- Best/Average ordering toggle at the right of the ranking toolbar with shareable URL state and final-ordinal means, preserving the same columns, attempt views and sidebar.
- Native Mistral and Cohere routes; per-account request pacing for Cohere trial keys, OpenRouter `:free` endpoints and Cerebras; Cerebras history-key removal.
- Independent repetitions follow explicit `run.py retry` chains: a rerun of an unstarted slot or non-model failure becomes the ordinal's sample, and superseded attempts stay listed.
- Static export for GitHub Pages (`--host github-pages`) with media served from public GitHub Pages repositories.
- Automatic GitHub Actions site builds from ranked `runs/` inputs, dry-run static artifacts, and changed-only deployment to the site and two size-bounded media repositories with stable media URLs.
- Crypto donation page (`/crypto`) with per-network addresses, QR codes and copy buttons, linked from Support.
- Cracktro-style preloader replacing the "Loading..." text: starfield and a chrome keygen-style logo, with load progress shown as a decoding serial and a dithered raster reveal of the mounted page.
- Repository-ranked site builder with verified listener evidence, byte-exact FLAC decoding, stable published slugs, reviewed site metadata and an offline parity checker.

### Changed

- Fetch independent optional website metadata in parallel while preserving missing-file defaults and failure reporting.

- Score tunes with an AI listener (listener-v1): 10 x the content-enjoyment rating of Meta Audiobox Aesthetics on the canonical render, with the silent and baked-sample caps. The listener runs in its own pinned environment (`benchmark/requirements-listener.txt`, `KEYGEN_LISTENER_PYTHON`) on the CPU with verified weights; contributor setup installs it and doctor checks it. Pitched clarity, development, dynamics, signal integrity and loop continuity remain as craft diagnostics; a voice with one onset in a passage no longer counts as development there. The site shows the four listener ratings (enjoyment scored, the other three marked unscored), explains how the listener model works on the Scoring page, and no longer shows or exports the old craft measurements.
- Add a read-only, hash-verified rescorer for ranked attempts and the pinned reference corpus, with separate evaluation evidence and native reference return/stop boundaries.
- Derive the contributor contract's scorer identity from the evaluator and reject mismatched campaign evaluations at publication export.
- Include the donation page and its QR images in fresh website publications, and preserve existing external playback traces during static export.
- Keep one local Docker execution path and one website implementation. Publication tools take explicit local inputs rather than contacting private machines.
- Keep runtime outputs and private configuration out of source control. Export only reviewed, nonidentifying community provenance.
- Replace operator-specific setup documentation with contributor, runner and website guides.
- Show funding options beside a contributor-run guide in the Support tab, retaining the wanted-model list and spending ledger below.
- Show only model names in tracker dropdowns and score-card headings, keep the original popup width, order models by reviewed release dates, and count distinct models in company menus.
- Explain Rankings consistency as score spread, sort unknown spreads last in either direction, and remove the sidebar pricing-source link.
- Total ordinal attempt costs in model rankings and show single upper estimates in Support, rankings and attempt sidebars, keeping ranges and missing-cost coverage in tooltips instead of visible `+` suffixes or warning paragraphs.
- Use MiniMax's published API rates for the M3.1 Flash list-price estimate even when the recorded OpenRouter `:free` route reports zero cost.

### Fixed

- Render bootstrap errors as literal text rather than HTML.

- Move verified site inputs across filesystems when the temporary directory and publication output use different mounts.
- Record listener operating system, CPU architecture and Python version; distinguish its 120-second rating window from whole-render artifact caps, and reject pre-listener public snapshots with the version-2 schema.
- Preserve full listener-rating precision so serialized evidence reproduces its score; allow read-only rescores of listener-v1 profiles as well as the historical craft profiles, and describe the listener score in campaign reports.
- Match model release metadata across dot/dash keys and the public names without `-contributor`, so the model dropdown sorts by release date; keep dropdown logos inside their border.
- Restore the original page slide transition and the original spend tooltip wording.
- Show `$0` for models that are free on their maker's API instead of `<$0.01`.
- Price supported records per response with context tiers, cached reads and cache writes; preserve unknown amounts and count known portions of incomplete attempts without token-count deduplication.
- Show bounded cost estimates when recorded usage and documented pricing cannot establish an exact context tier or cache-write split.
- Keep mobile ranking identities, tracker downloads/channel controls and Support funding/spend rows readable through stacked layouts and scrolling.
- Add keyboard playback seeking and model/podium selection, with current slider values and visible keyboard focus.
- Distinguish attempt scores and best-attempt ranks from Average ordering; preserve the selected attempt through Scoring, Support and browser history.
- Link the contributor guide to its GitHub `main` page instead of an unavailable pinned commit.
- Make Scoring distribution markers and Tracker instrument/order entries keyboard-accessible native buttons with visible focus and selection state.
- Wrap narrow Scoring example rows without overlapping model names, values or Listen controls.
- Align tracker trace lookup to captured samples so rounded media-clock seeks highlight the requested order and row.
- Keep the spending tooltip compact, with attempt counts and short coverage caveats instead of raw ledger metadata.
- Switch the Tracker's Company and Model pickers, info and score card at once. While a module downloads the pattern editor shows the run's empty channels instead of a "Loading module..." message, and modules one click away (hovered picker entries, neighbouring models, the model's other attempts, the run selected in Rankings) are prefetched at low priority so they usually open already parsed.
- Serve JSON, JavaScript, CSS and XM files gzip-compressed when the browser accepts it, with `If-Modified-Since` revalidation; audio stays uncompressed for byte-range seeking.

- Omit absent attempt panels and download links instead of rendering literal `null` text.

### Removed

- Remote sandbox provisioning, private deployment and account inventories, campaign launch records, duplicate source trees and generated publication evidence.
- Historical operator notes and unrelated research drafts that are not required to run or evaluate the benchmark.

The cleanup changes the current source tree only. Earlier commits and pull requests still require review before the repository becomes public.

