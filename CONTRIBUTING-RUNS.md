# Submit a community run

Run one exact model three times and submit every outcome to
[Microck/keygen-bench](https://github.com/Microck/keygen-bench).
Community results stay separate from ranked results.


## Using an AI agent

The [README's copy-paste prompt](README.md#contribute-with-your-ai-agent) is a
starting request for your coding agent, not permission to spend or publish.
Replace the exact model, provider/base URL and authentication preference. If
you do not know a value, ask the agent to research it rather than invent one.
For an unmerged feature, read the guides from the exact PR commit, not a mixture
of main and PR files.

Ask the agent to work through these checkpoints:

1. Read `AGENTS.md`, this guide and `benchmark/README.md`; inspect the installed
   contributor CLI's `--help` and verify prerequisites. Use a dedicated local
   controller with no personal/company files mounted into the sandbox.
2. Confirm the exact model and response identity, public endpoint, native
   protocol, documented reasoning tier/output cap and requested authentication
   method. Custom OpenAI-compatible endpoints are supported when their tool
   calling and generation controls satisfy the contract; compatibility alone
   is not proof of model identity.
3. Prepare the appropriate login command, then let **you** complete the local
   browser/device-code or hidden-key prompt. Do not send passwords, API keys,
   callback URLs, device codes or tokens to the agent's chat or run artifacts.
   The bridge owns its provider tokens. Explicit API-key setup must never be
   substituted for requested subscription OAuth without your agreement.
4. Keep authentication and eligibility separate. Codex/Anthropic bridge login
   can be configured while new frozen contributor runs remain blocked because
   the inspected routes drop required controls. A model catalog, successful
   login process or no-cloak setting does not waive that block. Gemini API-key
   setup is not Antigravity OAuth. Explain unsupported paths rather than
   promising a working run or changing the frozen experiment.
5. Run offline doctor checks first. A catalog `verify` is a network/authentication
   diagnostic, not an inference test or fairness certificate. Before any
   readiness pilot, smoke or official run, describe the route, request scope and
   possible charges and obtain your explicit approval. `--yes` is spending
   authorization, not a price cap; the agent must not insert it on its own.
6. After approval, run the smoke diagnostic and, with approval for the full run,
   all three predetermined attempts. Preserve failed/interrupted outcomes.
   Do not rerun scored attempts to select better results, change prompts,
   silently remove output limits or enable identity/tool cloaking.
7. Review the private bundle for secrets, personal data and accurate provenance;
   validate it and have you review what will become public. Obtain separate
   permission before uploading, pushing or opening the submission PR. Neither
   passing validation nor having provider access authorizes publication.

The setup/login commands do not make paid model calls. `doctor` is offline;
`verify` contacts the configured bridge catalog; `smoke` and `run` include a
real paid-or-quota-consuming readiness pilot before their attempts. Never
describe a synthetic offline test as verification of a real provider login.

## Guided setup and run

Use Linux with Python 3.11 or later and a working local Docker Engine.
From the repository root:

```sh
python3 benchmark/contrib/cli.py setup --home "$HOME/.local/share/keygen-bench"
```

Setup installs the pinned controller packages in a private virtual environment,
installs the AI listener (Meta Audiobox Aesthetics, about 415 MB of weights) in
a second one, builds both Docker targets, and builds the trusted analysis
renderer. It makes no model requests. Missing compiler or system packages
produce installation instructions; setup does not run `sudo` for you.

Use the installed environments for the remaining commands:

```sh
PYTHON="$HOME/.local/share/keygen-bench/venv/bin/python"
export KEYGEN_LISTENER_PYTHON="$HOME/.local/share/keygen-bench/listener-venv/bin/python"
CONFIG="$HOME/.config/keygen-bench/model.json"
"$PYTHON" benchmark/contrib/cli.py login openai --method api-key
"$PYTHON" benchmark/contrib/cli.py configure --provider openai --config "$CONFIG"
"$PYTHON" benchmark/contrib/cli.py doctor --config "$CONFIG"
```

Doctor fails if the listener is not configured. Rating a tune takes seconds on
a fast machine and several minutes on a small 2-core one.

The configuration wizard asks for the provider, exact model, native protocol,
documented reasoning tier, generation settings and public GitHub handle.
It stores configuration with private permissions outside the checkout.
Credentials are supplied separately; they are not stored in the configuration.
Use `--no-input` and explicit configuration flags for automation; see
`configure --help`. Presets supply endpoint defaults, not guessed model settings.

### OAuth login, with API keys as an explicit alternative

This is Keygen's contributor command, not an upstream `mini-swe-agent login`
command. Upstream mini does not provide these login subcommands.

Install a reviewed [CLIProxyAPI v8 release](https://github.com/router-for-me/CLIProxyAPI/releases)
on your own trusted machine. Keygen does not download or execute an unselected
bridge automatically. Then choose one account:

```sh
"$PYTHON" benchmark/contrib/cli.py login codex --bridge-binary /absolute/path/cli-proxy-api
"$PYTHON" benchmark/contrib/cli.py login xai --bridge-binary /absolute/path/cli-proxy-api
"$PYTHON" benchmark/contrib/cli.py login anthropic --bridge-binary /absolute/path/cli-proxy-api
```

Run only the commands for the providers you intend to use. `codex`/`openai`,
`anthropic` and `xai` default to OAuth, never silently to billable API keys.
The CLI explains community-support and provider restrictions and asks before
starting login; `--accept-community-auth` records that deliberate choice.
It requires an interactive terminal. `--no-browser` suppresses automatic browser
opening, but does not make the consent/device-code flow unattended.

- Codex uses CLIProxyAPI's device login (`-codex-device-login`), avoiding a local
  callback listener. This is its community compatibility flow, not OpenAI's
  separately documented open-source-client registration integration.
- xAI uses its device login (`-xai-login`). This is an implemented community
  flow; we have not established an official third-party subscription contract.
- Anthropic uses its browser/PKCE login (`-claude-login`). Anthropic does not
  officially permit third-party Claude subscription login here. The inspected
  bridge callback listens on port 54545 and may bind beyond loopback, so use a
  trusted local machine. Do not confuse this with supported API-key access or
  Anthropic's unmodified-Claude-Code exception.
- Gemini is available via explicit API-key setup below. The inspected bridge
  exposes Antigravity, not a generic Gemini CLI login; we do not pretend they
  are interchangeable or guess unsupported flags.

The selected bridge handles its own provider-token storage and refresh. Keygen
never reads or copies those provider tokens. Generated v8 configuration lives
under `~/.config/keygen-benchmark/credentials/oauth/PROVIDER/`, with a dedicated
private token directory, loopback inference listener, random local bearer and
known prompt/tool cloaking disabled. Provider profiles are isolated and ports
default to 8317 (Codex), 8318 (Anthropic) and 8319 (xAI). `--bridge-port` changes
only the inference port, not browser OAuth callback ports. Existing profiles
are reused rather than overwritten.

Some bridge login helpers return exit code zero after reporting an error.
Keygen therefore never equates process completion or credential-file presence
with remotely verified authentication. No login makes inference requests.

After login, keep the bridge in a separate foreground terminal:

```sh
"$PYTHON" benchmark/contrib/cli.py bridge-serve xai
"$PYTHON" benchmark/contrib/cli.py auth-status xai
"$PYTHON" benchmark/contrib/cli.py configure --provider xai_oauth \
  --base-url http://127.0.0.1:8319/v1 --bridge-binary /absolute/path/cli-proxy-api --config "$CONFIG"
"$PYTHON" benchmark/contrib/cli.py verify --config "$CONFIG"
```

Run/smoke uses only the generated local bearer, and only for the matching
loopback endpoint and executable. `verify` also uses that matching local bearer automatically; it never reads
provider tokens. `auth-status` reports
configuration presence, not remote validity. Stop the bridge and revoke access
in the provider account to sign out; automatic bridge OAuth logout/revocation
is not implemented, and `logout --method oauth` says so rather than claiming
that deleting a local file revokes access.

### API keys and OpenAI-compatible endpoints

Use `--method api-key` to deliberately choose API billing instead of OAuth:

```sh
"$PYTHON" benchmark/contrib/cli.py login anthropic --method api-key
"$PYTHON" benchmark/contrib/cli.py login gemini --method api-key
"$PYTHON" benchmark/contrib/cli.py login custom --method api-key --base-url https://YOUR-PROVIDER/v1
"$PYTHON" benchmark/contrib/cli.py configure --provider custom --base-url https://YOUR-PROVIDER/v1 --config "$CONFIG"
```

Named key presets: OpenAI/Codex, Anthropic, xAI, Gemini/Google, OpenRouter,
DeepSeek, Groq, Mistral and Cohere. Custom public HTTPS endpoints support the
existing native Chat Completions, Responses or Messages transport. Choose the
exact model ID, protocol, documented reasoning tier and output cap. Compatibility
is not a guarantee of tool support, model identity or parameter preservation.
There is no model allowlist for custom endpoints, but the frozen execution
requirements still apply. Google uses its native Gemini adapter.

API-key login prints the provider console link, asks permission to save and
reads the key without echo. Keys are plaintext owner-only files (0600 under a
0700 private directory), never inside model configuration or the checkout.
A custom key is bound to its exact endpoint; keys are never automatically sent
to another host or bridge. No provider request is sent during key setup.
Use `--auth-dir` consistently for login, configure, doctor, smoke and run to
select another private directory. API `auth-status` and `logout` also require
`--method api-key` for OAuth-default providers; custom keys require the same
`--base-url`. Local logout does not revoke a provider API key.

For automation, supply the provider environment variable privately, then use
`login PROVIDER --method api-key --no-input --save` only if local storage is
intended. Custom login uses `KEYGEN_CONTRIB_API_KEY`; named profiles use their
standard variables, such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`
and `GEMINI_API_KEY`. `--replace` is required to overwrite saved keys. Never
supply secrets in command-line arguments. Without storage, smoke/run can use
these environment credentials directly at their matching destinations.

### Authentication is not benchmark qualification

A successful OAuth login is useful, but it does not establish unchanged prompts
or generation settings. At inspected CLIProxyAPI commit
`0db19025571684b198a2ef508f99b41c717337e8`, the Codex Responses translator removes
output caps, temperature and top_p; Claude normalization removes temperature
and top_p independently of no-cloak. Consequently new `codex_oauth` and
`anthropic_oauth` contributor smoke/runs fail before spending. Login remains
available separately. Do not silently remove these checks or replace frozen
settings to make a route run. Historical evidence/validator schemas are retained.

The advanced xAI route keeps its existing eligibility checks, but catalog lookup
is not final-upstream payload verification. Known xAI search-tool injection is
disabled in the generated profile. Before accepting bridge results as equivalent,
verify the exact bridge version/config and sanitized final outbound request;
client logs and model catalogs alone are insufficient. Provider-internal hidden
instructions cannot be ruled out by client inspection.

[OpenAI's official OSS OAuth](https://developers.openai.com/siwc/token-sharing-open-source)
is a possible future direct transport, but its current
[preview constraints](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
also exclude the frozen output-token caps/sampling controls. It needs its own
PKCE/client registration/token lifecycle and a disclosed compatible condition,
not a silent drop-in. [Anthropic's current rules](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use)
distinguish API keys, third-party subscription credentials and the unmodified
Claude Code binary. No wrapper setting changes those provider rules.

Before either command runs a benchmark attempt, it performs a real native
readiness pilot with the same model, provider, protocol, endpoint, tier,
generation settings and agent image. The pilot makes provider requests and may
incur cost. Each smoke or run invocation performs its own pilot, even if a prior
smoke passed. The pilot is not a benchmark attempt. Its proof and diagnostic
files stay in the private work directory, never in the public bundle. If the
pilot does not verify the native route, the CLI stops before starting a smoke
or any of the three official attempts.

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
2. From the repository root, install the pinned controller packages and the
   AI listener in its own environment:

   ```sh
   python3 -m venv .venv-contrib
   . .venv-contrib/bin/activate
   python -m pip install -r benchmark/requirements.txt
   python3 -m venv .venv-listener
   .venv-listener/bin/pip install -r benchmark/requirements-listener.txt
   export KEYGEN_LISTENER_PYTHON="$PWD/.venv-listener/bin/python"
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
   `benchmark/README.md` for route restrictions. Prefer the provider API-key
   setup above. OAuth login is available separately from frozen-route eligibility.
6. Set your API key or local bridge bearer privately. Do not put it in a command,
   config, PR, or committed file. Bash can read it without showing it or saving
   it in history:

   ```sh
   read -rsp 'Provider API key or local bridge bearer: ' KEYGEN_CONTRIB_API_KEY; echo
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
`--bridge-binary PATH` pointing to the executable that runs your bridge. Run
`verify` first to check the exact advertised model without inference. The bundle
records the provider, API protocol, exact model, loopback transport class, and
executable SHA-256. It does not publish the bridge address, port, or executable
path. The hash identifies the supplied binary; it does not prove its config,
which server handled requests, or what that server sent upstream.

Use new work and output directories. Before starting the three attempts, the
command runs a real native readiness pilot with the exact configured route and
settings. The pilot makes provider requests and may incur cost. Each invocation
runs a fresh pilot, and its proof stays in the private work directory. If the
pilot fails, no benchmark attempt starts. After qualification, the command reuses
`run.py` and native campaign settings. It freezes mini-swe-agent 2.4.6, one bash
tool, prompt-v2, 120 minutes per attempt, no step limit, 120 seconds per
command, 60 minutes per request, and a 128 MiB / 4096-file submission limit. It
runs all three attempts, including after failures. Do not rerun and choose
better outcomes. If stopped, keep the private work and report the interruption
in an issue before spending more. An incomplete bundle fails validation.

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


## Muse Wonder Full: experimental subscription transport

Wonder Full is requested without a fundraising target. It is not regular Wonder
at max effort and is not a qualified native provider. The implemented
[Muse Code SDK/MCP adapter](benchmark/experimental/muse_sdk/README.md) hands Bash
execution to mini while keeping the upstream Muse harness explicit. It requires
an entitled, privately authenticated Muse Code profile and separate usage consent.
It does not purchase access, reuse subscription credentials in a generic API
client, or imply frozen equivalence. Start with its synthetic Docker diagnostic;
keep any subsequent runs separate and non-ranked until prompt/tool and inference
provenance requirements are met. See the [access notes](docs/muse-wonder-full-access.md).
