# Submit a community run

Run one exact model three times and submit every outcome to Microck at
[Microck/keygen-bench](https://github.com/Microck/keygen-bench).
Community results stay separate from ranked results.

## Prepare

1. Fork and clone the repository. Use Linux, Python 3.11 or later, Git,
   Docker Engine, and a funded provider account. Allow at least 8 GiB RAM,
   20 GiB free disk, and six hours plus rendering time. Your controller needs
   network access. Model commands run in an offline Docker container.
2. From the repository root, install the pinned controller packages:

   ```sh
   python3 -m venv .venv-contrib
   . .venv-contrib/bin/activate
   python -m pip install -r benchmark/requirements.txt
   ```

3. Pull the pinned base and build both targets. The Dockerfile pins Debian;
   `scripts/build-ft2-linux.sh` pins the FT2 source commit. There is no published
   canonical final image to pull. Builds may differ by architecture and package
   mirror state. The runner records each final image's immutable SHA-256 ID.

   ```sh
   docker pull debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251
   docker build -f benchmark/Dockerfile --target agent -t keygen-ft2-benchmark:local .
   docker build -f benchmark/Dockerfile --target visualizer -t keygen-ft2-visualizer:local .
   ```

4. Craft-v7 needs the trusted analysis build too. Follow the prerequisites and
   build instructions in `scripts/build-ft2-analysis.py`. It verifies the same
   FT2 commit and the capture patch. Install the script's stated SDL2 and
   libmicrohttpd development packages, then run:

   ```sh
   python scripts/build-ft2-analysis.py
   ```

5. Read your provider's model documentation. Use the exact model ID, highest
   documented reasoning tier for that route, and documented output cap. Keep
   the documentation URL. No alias, checkpoint substitution, or provider
   fallback is allowed. Supported providers are `go`, `nim`, `vercel`,
   `codex_oauth`, and `anthropic_oauth`. See `benchmark/README.md` for route
   restrictions. OAuth routes need your own authorized loopback bridge.
6. Set your credential privately. Do not put it in a command, config, PR, or
   committed file. Bash can read it without showing it or saving it in history:

   ```sh
   read -rsp 'Provider credential: ' KEYGEN_CONTRIB_API_KEY; echo
   export KEYGEN_CONTRIB_API_KEY
   ```

## Run and package

This is one run command. Replace the model, tier, documentation URL, generation
JSON, and handle with your values. This example shows the Go Messages route;
confirm its current model documentation before spending money.

```sh
python benchmark/contrib/run_contrib.py \
  --model qwen3.8-flash --provider go \
  --base-url https://opencode.ai/zen/go/v1 --api messages \
  --reasoning-tier xhigh --tier-source https://opencode.ai/docs/go/ \
  --generation '{"max_tokens":32768,"thinking":{"type":"adaptive"},"output_config":{"effort":"xhigh"}}' \
  --attempts 3 --handle YOUR-HANDLE \
  --work /tmp/keygen-private-run \
  --out submissions/qwen3.8-flash/$(date -u +%F)-YOUR-HANDLE
unset KEYGEN_CONTRIB_API_KEY
```

Use new work and output directories. The command reuses `run.py` and native
campaign settings. It freezes mini-swe-agent 2.4.6, one bash tool, prompt-v2,
120 minutes per attempt, no step limit, 120 seconds per command, 60 minutes per
request, and a 128 MiB / 4096-file submission limit. It runs all three attempts,
including after failures. Do not rerun and choose better outcomes. If stopped,
keep the private work and report the interruption in an issue before spending
more. An incomplete bundle fails validation.

The output directory is the package. Do not copy the private work directory.
It contains controller files that are not for publication. Inspect the package
for credentials and personal data, then validate it:

```sh
python benchmark/contrib/validate_bundle.py submissions/qwen3.8-flash/DATE-YOUR-HANDLE
```

## Open the PR

Create a branch in your fork. Add only your submission directory, commit it,
push it to your fork, and open a ready-for-review PR against Microck/keygen-bench.
Choose the run-submission template. For GitHub CLI:

```sh
git switch -c run/qwen3.8-flash
git add submissions/qwen3.8-flash/DATE-YOUR-HANDLE
git commit -m 'Add community qwen3.8-flash run'
git push -u origin run/qwen3.8-flash
gh pr create --repo Microck/keygen-bench --base main \
  --title 'Community run: qwen3.8-flash' \
  --body-file .github/PULL_REQUEST_TEMPLATE/run-submission.md
```

Fill in the PR body before requesting review. If a file exceeds GitHub's regular
Git size limit, ask Microck for an agreed artifact transfer before opening the
PR. Do not silently omit it or replace it with a Git LFS pointer.

## Public data and company runs

The API provider receives the benchmark prompt, model replies, and tool output.
The offline sandbox receives no controller credentials. Run on a dedicated
controller with no company files mounted. Obtain your company's approval for
provider use and public disclosure under its SOC 2 / ISO 27001 controls.
This workflow is not a certification.

GitHub publishes the XM, model conversations, tool output, token/timing totals,
model route/tier, image IDs, source/package hashes, and coarse host details.
Never submit credentials, names, emails, internal URLs, customer data, or other
personal/company data. Use only your public GitHub handle. The validator scans
all files, including binary samples, for key patterns, credential headers, and
environment dumps. Pattern scanning cannot detect every secret or personal
record. Review the contents yourself. If a log contains sensitive material,
do not publish it or silently edit its evidence. Report the problem privately
and rotate any exposed credential.

The PR workflow uses read-only permissions and no provider credentials. Microck
checks provenance and re-renders `tune.xm` with the trusted pipeline. Submitted
scores never establish a trusted result. See `submissions/README.md`.
