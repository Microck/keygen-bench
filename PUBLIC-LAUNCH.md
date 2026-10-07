# Before making the repository public

A clean checkout is not a clean history. Merging the launch cleanup does not erase files from earlier commits, branches, tags, pull-request diffs, releases, workflow logs or artifacts.

## Publication boundary

Keep source, pinned build inputs, synthetic tests and reviewed community submissions. Do not publish raw campaign spools, provider audits, credentials, account inventories, deployment records, private hostnames, network addresses or home-directory paths.

Public author handles and third-party copyright notices are intentional attribution. Do not replace them with anonymous placeholders.

## Required review

1. Review every branch and tag that will become public, including commits before the cleanup. Review commit author emails separately.
2. Inspect old pull requests, issue attachments, Actions logs and artifacts, release assets and repository metadata. Deleting a branch does not necessarily remove a pull-request diff.
3. Run a secret scanner against both the release tree and all history. Classify findings without pasting credential values into issues or review comments. Rotate any exposed credential; deleting it is not revocation.
4. Review screenshots and binary artifacts manually. Text and secret scanners do not establish absence of personal data.
5. Choose a publication strategy before changing visibility. A new repository initialized from the reviewed release tree avoids carrying private operational history into the public repository. Rewriting the existing repository requires coordinating all refs and clones and addressing retained pull-request diffs with the hosting provider. Neither happens automatically in this PR.
6. Original code and documentation are MIT-licensed ([LICENSE](LICENSE)). Preserve all third-party notices, including the FT2 bitmap font license, which the MIT License does not cover.
7. Build the pinned containers and exercise a full local submission/render/evaluation cycle on the intended host. Test model access only with an explicit spending budget. Offline tests do not verify provider credentials or billing.
8. Merge the contributor validator before accepting submission PRs; its CI runs trusted code from the base branch. Keep branch protection and repository permissions appropriate for untrusted contributions.

## Submission privacy

Keep in-progress run directories private. Review the exported bundle before committing it, even when validation passes. Prompts, model output and tool logs may contain personal information that a pattern scanner cannot identify. A validator cannot establish authorship, undisclosed attempts, provider identity or organizational compliance.

The maintainer campaigns are published in full under `runs/` (minus videos): trajectories, provider transport logs, modules, renders and evaluations. Before each update, scan the exported tree for credentials and personal data (emails, names, account or organization identifiers); controller paths such as `/home/ubuntu/...` and opaque provider identifiers (response IDs, prompt-cache keys, encrypted reasoning blobs) are expected. Check each provider's terms before republishing transcripts of its models.

Accepted results must keep their community provenance label. Re-render and re-score submitted modules using the trusted evaluator rather than accepting submitted scores.
