# Changelog

## Unreleased

### Added

- Community-run guide, three-attempt runner, bundle validator, submission templates and trusted-base validation workflow.
- FT2-style results site with per-model routes, attempt selection, loop playback, scoring explanations and generated Open Graph cards.
- Public-launch checklist covering Git history, personal data, credentials, licenses and release verification.
- Repository agent instructions linking the maintained guides and defining local execution, privacy, provenance and verification boundaries.
- Guided contributor CLI for setup, private configuration, offline preflight, bounded model smoke runs and spending-authorized official submissions.
- Direct OpenAI and Anthropic API-key routes and public HTTPS custom endpoints for supported native protocols.

### Changed

- Keep one local Docker execution path and one website implementation. Publication tools take explicit local inputs rather than contacting private machines.
- Keep runtime outputs and private configuration out of source control. Export only reviewed, nonidentifying community provenance.
- Replace operator-specific setup documentation with contributor, runner and website guides.

### Fixed

- Omit absent attempt panels and download links instead of rendering literal `null` text.

### Removed

- Remote sandbox provisioning, private deployment and account inventories, campaign launch records, duplicate source trees and generated publication evidence.
- Historical operator notes and unrelated research drafts that are not required to run or evaluate the benchmark.

The cleanup changes the current source tree only. Earlier commits and pull requests still require review before the repository becomes public.
