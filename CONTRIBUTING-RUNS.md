# Submit a community run

Run one exact model three times and submit every outcome to
[Microck/keygen-bench](https://github.com/Microck/keygen-bench).
Community results stay separate from ranked results.

## Guided setup and run

Use Linux with Python 3.11 or later and a working local Docker Engine.
From the repository root:

```sh
python3 benchmark/contrib/cli.py setup --home "$HOME/.local/share/keygen-bench"
```

Setup installs the pinned controller packages in a private virtual environment,
builds both Docker targets, and builds the trusted analysis renderer. It makes
no model requests. Missing compiler or system packages produce installation
instructions; setup does not run `sudo` for you.

Use the installed environment for the remaining commands:

```sh
PYTHON="$HOME/.local/share/keygen-bench/venv/bin/python"
CONFIG="$HOME/.config/keygen-bench/model.json"
"$PYTHON" benchmark/contrib/cli.py configure --config "$CONFIG"
"$PYTHON" benchmark/contrib/cli.py doctor --config "$CONFIG"
```

The configuration wizard asks for the provider, exact model, native protocol,
documented reasoning tier, generation settings and public GitHub handle.
It stores configuration with private permissions outside the checkout.
Credentials are supplied separately; they are not stored in the configuration.
Use `--no-input` and explicit configuration flags for automation; see
`configure --help`. Presets supply endpoint defaults, not guessed model settings.

For API-key routes, set `KEYGEN_CONTRIB_API_KEY` privately as shown below.
For `anthropic_oauth` or `codex_oauth`, first install and sign in to your own
authorized bridge, start its loopback server, and provide its URL and executable
path to the wizard. The CLI does not implement an OAuth login or extract tokens
from another application's credential store. The bridge credential goes in
`KEYGEN_CONTRIB_API_KEY`; only its executable digest is exported.
Doctor checks a bridge listener without sending an inference request.

Try a short paid model smoke run before committing to three full attempts:

```sh
"$PYTHON" benchmark/contrib/cli.py smoke --config "$CONFIG" \
  --work "$HOME/.local/share/keygen-bench/smoke-01"
```

Smoke outputs are private diagnostics, not eligible submission bundles.
Smoke and official runs require interactive spending consent or `--yes`.
Consent authorizes requests; it is not a dollar cap or a guarantee of model access.
Doctor makes no provider requests and does not verify authentication or billing.

When ready, run all three official attempts:

```sh
"$PYTHON" benchmark/contrib/cli.py run --config "$CONFIG" \
  --work "$HOME/.local/share/keygen-bench/run-01" \
  --out submissions/MODEL/DATE-YOUR-HANDLE
```

Use new work and bundle directories each time. Review and validate the bundle,
then follow the PR instructions below. The guided command uses the same frozen
runner and submission contract as the explicit invocation.

## Manual setup

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

4. Scoring needs the trusted analysis build too. Follow the prerequisites and
   build instructions in `scripts/build-ft2-analysis.py`. It verifies the same
   FT2 commit and the capture patch. Install the script's stated SDL2 and
   libmicrohttpd development packages, then run:

   ```sh
   python scripts/build-ft2-analysis.py
   ```

5. Read your provider's model documentation. Use the exact model ID, highest
   documented reasoning tier for that route, and documented output cap. Keep
   the documentation URL. No alias, checkpoint substitution, or provider
   fallback is allowed. API-key routes include `openai`, `anthropic`, `go`,
   `nim`, `vercel`, and `custom` for a public HTTPS service implementing
   Chat Completions, Responses, or Messages. Protocol compatibility does not
   establish model identity or equivalent reasoning behavior. See
   `benchmark/README.md` for route restrictions. `codex_oauth` and
   `anthropic_oauth` require your own authorized loopback bridge.
6. Set your credential privately. Do not put it in a command, config, PR, or
   committed file. Bash can read it without showing it or saving it in history:

   ```sh
   read -rsp 'Provider credential: ' KEYGEN_CONTRIB_API_KEY; echo
   export KEYGEN_CONTRIB_API_KEY
   ```

## Run and package

This is one run command. Replace the model, tier, documentation URL, generation
JSON, handle, and private work path with your values. Keep the work directory
outside the checkout. This example shows the Go Messages route; confirm model
availability, reasoning support, and pricing before spending money.

```sh
python benchmark/contrib/run_contrib.py \
  --model qwen3.8-flash --provider go \
  --base-url https://opencode.ai/zen/go/v1 --api messages \
  --reasoning-tier xhigh --tier-source https://opencode.ai/docs/go/ \
  --generation '{"max_tokens":32768,"thinking":{"type":"adaptive"},"output_config":{"effort":"xhigh"}}' \
  --attempts 3 --handle YOUR-HANDLE \
  --work /absolute/private/community-run \
  --out submissions/qwen3.8-flash/$(date -u +%F)-YOUR-HANDLE
unset KEYGEN_CONTRIB_API_KEY
```

For an OAuth route, pass its private loopback `--base-url` and
`--bridge-binary PATH` pointing to the executable that runs your bridge. The
bundle records the provider, API protocol, exact model, loopback transport
class, and executable SHA-256. It does not publish the bridge address, port,
or executable path. The hash identifies the supplied binary; it does not prove
which server handled requests or what that server sent upstream.

Use new work and output directories. The command reuses `run.py` and native
campaign settings. It freezes mini-swe-agent 2.4.6, one bash tool, prompt-v2,
120 minutes per attempt, no step limit, 120 seconds per command, 60 minutes per
request, and a 128 MiB / 4096-file submission limit. It runs all three attempts,
including after failures. Do not rerun and choose better outcomes. If stopped,
keep the private work and report the interruption in an issue before spending
more. An incomplete bundle fails validation.

The output directory is the package. Do not copy the private work directory.
It contains controller files that are not for publication. The output starts
with owner-only directory permissions too. Inspect every packaged file for
credentials and personal data, then validate it:

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
Git size limit, ask the maintainers for an agreed artifact transfer before opening
the PR. Do not silently omit it or replace it with a Git LFS pointer.

## What becomes public

The API provider receives the benchmark prompt, model replies, and tool output.
The offline sandbox receives no controller credentials. Use a dedicated
controller with no personal or company files mounted. Obtain any required
approval for provider use and public disclosure. These checks are not a
compliance assessment or certification.

GitHub publishes the XM, model conversations, tool output, token/timing totals,
model provider/tier and public route or bridge digest, image IDs and layers,
source hashes, benchmark package
versions, operating system family, architecture, Python version, and Docker
version. The exporter excludes controller configuration, container names, raw
controller error details, kernel releases, image registry names, and unrelated
installed packages. Attempt states, failure categories, timings, and usage
remain available for all three attempts. Model conversations and transport
evidence are not silently rewritten to remove sensitive text.

Never submit credentials, names, emails, internal URLs, customer data, or other
personal/company data. Use only your public GitHub handle. The validator scans
all files, including binary samples, for common key patterns, credential headers,
environment dumps, private host metadata fields, and absolute home paths.
It checks direct provider routes and requires nonidentifying OAuth bridge
provenance instead of a private endpoint. Tier documentation must use a
public HTTPS URL without credentials, query parameters, or a custom port.
Pattern scanning cannot detect every secret, identifying detail, or private URL.
Review the contents yourself. If a log contains sensitive material, do not
publish it or silently edit its evidence. Contact the maintainers privately
and rotate any exposed credential. A rejected output directory is still private
data; passing validation does not mean it is safe to publish without review.

The PR workflow uses read-only permissions, no provider credentials, and
validator code from the trusted base commit. Maintainers check provenance and
re-render `tune.xm` with a separately selected trusted image. Submitted scores
never establish a trusted result. See `submissions/README.md`.
