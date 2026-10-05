# Changelog

## Unreleased

### Added

- Community-run guide, three-attempt runner, bundle validator, submission templates and trusted-base validation workflow.
- FT2-style results site with per-model routes, attempt selection, loop playback, scoring explanations and generated Open Graph cards.
- Public-launch checklist covering Git history, personal data, credentials, licenses and release verification.
- Repository agent instructions linking the maintained guides and defining local execution, privacy, provenance and verification boundaries.
- Guided contributor CLI for setup, private configuration, offline preflight, bounded model smoke runs and spending-authorized official submissions.
- Direct OpenAI and Anthropic API-key routes and public HTTPS custom endpoints for supported native protocols.
- Best/Average ordering toggle at the right of the ranking toolbar with shareable URL state and final-ordinal means, preserving the same columns, attempt views and sidebar.
- Cracktro-style preloader replacing the "Loading..." text: starfield and a chrome keygen-style logo, with load progress shown as a decoding serial and a dithered raster reveal of the mounted page.

### Changed

- Keep one local Docker execution path and one website implementation. Publication tools take explicit local inputs rather than contacting private machines.
- Keep runtime outputs and private configuration out of source control. Export only reviewed, nonidentifying community provenance.
- Replace operator-specific setup documentation with contributor, runner and website guides.
- Show funding options beside a contributor-run guide in the Support tab, retaining the wanted-model list and spending ledger below.
- Show only model names in tracker dropdowns and score-card headings, keep the original popup width, order models by reviewed release dates, and count distinct models in company menus.
- Explain Rankings consistency as score spread, sort unknown spreads last in either direction, and remove the sidebar pricing-source link.
- Total ordinal attempt costs in model rankings and show single upper estimates in Support, rankings and attempt sidebars, keeping ranges and missing-cost coverage in tooltips instead of visible `+` suffixes or warning paragraphs.

### Fixed

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
- Switch the Tracker's Company and Model pickers, info and score card at once, showing "Loading module..." while the module downloads alongside its MP3, instead of keeping the previous model until the module arrives.
- Serve JSON, JavaScript, CSS and XM files gzip-compressed when the browser accepts it, with `If-Modified-Since` revalidation; audio stays uncompressed for byte-range seeking.

- Omit absent attempt panels and download links instead of rendering literal `null` text.

### Removed

- Remote sandbox provisioning, private deployment and account inventories, campaign launch records, duplicate source trees and generated publication evidence.
- Historical operator notes and unrelated research drafts that are not required to run or evaluate the benchmark.

The cleanup changes the current source tree only. Earlier commits and pull requests still require review before the repository becomes public.
