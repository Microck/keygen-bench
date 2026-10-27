# Publication review

Use this guide each time you publish source, runs, community bundles, site builds
or deployments. It keeps the parts of the retired public-launch checklist
(`PUBLIC-LAUNCH.md`, removed in commit `9ecad47`) that still apply now that the
repository is public. The one-time launch steps, such as changing repository
visibility, are gone.

A clean checkout is not a clean history. Deleting a file does not remove it from
earlier commits, branches, tags, pull-request diffs, releases, workflow logs or
artifacts. Deployment, repository visibility changes and history rewriting need
explicit authorization; see [AGENTS.md](../AGENTS.md).

## Publication boundary

Publish source, pinned build inputs, synthetic tests, reviewed community
submissions and the maintainer's finished runs in [`runs/`](../runs/README.md).
Do not publish raw campaign spools, provider audits, credentials, account
inventories, deployment records, private hostnames, network addresses or
home-directory paths. The maintainer runs are the one stated exception for
controller paths; see [Maintainer runs](#maintainer-runs).

Public author handles and third-party copyright notices are intentional
attribution. Do not replace them with anonymous placeholders.

## Review before each publication

1. Review every commit, branch and tag you are about to publish, and the commit
   author emails separately.
2. Check pull requests, issue attachments, Actions logs and artifacts, release
   assets and repository metadata that the change adds or exposes. Deleting a
   branch does not necessarily remove a pull-request diff.
3. Run a secret scanner against the tree you publish and against its history.
   Classify findings without pasting credential values into issues or review
   comments. Rotate any exposed credential; deleting it is not revocation.
4. Review screenshots and binary artifacts by hand. Text and secret scanners do
   not establish that personal data is absent.
5. Preserve every third-party notice in [NOTICE.md](../NOTICE.md). Original code
   and documentation are MIT-licensed ([LICENSE](../LICENSE)); that license does
   not cover the FT2 bitmap fonts or other third-party material.
6. Build the pinned containers and run a full local submission, render and
   evaluation cycle on the intended host when the change affects them. Test model
   access only with an explicit spending budget. Offline tests do not verify
   provider credentials or billing.
7. Keep the contributor validator workflow running validator code from the
   trusted base commit, and keep branch protection and repository permissions
   suitable for untrusted contributions.

## Submission privacy

Keep in-progress run directories private. Review an exported bundle before
committing it, even when validation passes. Prompts, model output and tool logs
may contain personal information that a pattern scanner cannot find.

Neither the validator nor maintainer review proves which model produced a file,
that the declared route received the stated settings, or that no undisclosed
attempts happened. Nor do they establish authorship or organizational
compliance.

A merged submission under `submissions/` is retained evidence, not a published
result. Re-render and re-score submitted modules with the trusted evaluator
rather than accepting submitted scores. A reviewed result keeps its
`community-submitted` label, sits in its own cohort under
`runs/<model>/community/<YYYY-MM-DD>-<handle>/`, and never receives a comparative
rank. See [maintainer verification](../submissions/README.md#maintainer-verification)
and [reviewed community publication](../web/classic/README.md#reviewed-community-publication).

## Maintainer runs

The maintainer campaigns are published in full under `runs/`, without videos:
trajectories, provider transport logs, modules, renders and evaluations. Before
each update, scan the exported tree for credentials and personal data such as
emails, names, and account or organization identifiers. Controller paths such as
`/home/ubuntu/...` and opaque provider identifiers (response IDs, prompt-cache
keys, encrypted reasoning blobs) are expected. Check each provider's terms before
republishing transcripts of its models.
