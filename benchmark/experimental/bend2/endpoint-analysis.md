# Endpoint standardization: investigation

This is a design investigation, not a new runner or a claim of provider parity.
Python remains authoritative. No provider requests were made for this analysis.

## What has actually gone wrong

* [PR 93](https://github.com/Microck/keygen-bench/pull/93) records OpenCode Go
  responding to a temporary per-model outage with 429/502. Treating that as
  quota ended attempts; the fix waits for that specific body, with a bounded
  retry and transport audit. [PR 95](https://github.com/Microck/keygen-bench/pull/95)
  records 117, 25 and 98 such waits in three later attempts. Other 429s must
  not become blanket retries.
* [PR 33](https://github.com/Microck/keygen-bench/pull/33) documents Cohere's
  rejection of undeclared generated tools and its route-specific strict-tools
  setting, plus rate pacing. These are wire and scheduling differences, not
  just a new URL.
* [PR 32](https://github.com/Microck/keygen-bench/pull/32) explains why
  Mistral's structured thinking required the native SDK adapter instead of the
  generic compatible path. [PR 115](https://github.com/Microck/keygen-bench/pull/115)
  records bridge control stripping and explicitly blocks unsupported routes.
* [PR 25](https://github.com/Microck/keygen-bench/pull/25) already added a
  generic custom endpoint route. It supports common protocols, but still
  requires explicit endpoint, model, controls and security validation.

## Where coupling exists

`native_models.py` mixes provider allowlists and protocol/URL validation with
SDK selection, request transformations, pacing, and settings evidence.
`run.py` additionally contains provider-specific content-filter and outage
handling beside generic attempt and scheduling logic. The generic custom route
helps ordinary compatible endpoints; it cannot safely make every endpoint
equivalent when tools, reasoning, model identity, retry semantics or OAuth
bridges differ.

## Proposed migration

1. Define a small explicit route adapter contract for validation, construction,
   request policy and auditable effective settings. Keep protocol, endpoint,
   exact model ID and credential source declared, and reject unknown controls.
2. Move each existing exception into a named, independently tested adapter or
   policy. The runner should consume the resolved policy, not inspect provider
   names. Preserve existing SDK versions, wire payloads, retry counts, audit
   records, stop behavior, sandbox boundaries and frozen campaign fingerprints.
3. Lock current behavior down with synthetic request/response fixtures and
   differential tests first, including negative cases: quota vs outage,
   strict tool calls, streaming, exact identity, credential isolation and
   unsupported generation controls. Replay retained sanitized examples where
   appropriate; retain historical artifacts unchanged.
4. Migrate one route at a time and test the trusted synthetic Docker submission,
   render and score pipeline required by the repository. Offline tests cannot
   establish live-provider behavior or pricing; paid readiness requires separate
   explicit authorization. Only describe a new endpoint as configured after its
   specific capabilities and security assumptions have been verified.

## Bend 2 assessment

Bend 2 does not remove endpoint-specific protocol, identity or safety work.
Its pure decision logic could be explored separately, but replacing the
controller adds a second implementation and process-lifecycle parity work.
The current experiment is incomplete and does not launch a campaign. A Python
adapter cleanup is the more direct first step for the stated goal; this is an
engineering judgment, not a measured performance comparison.
