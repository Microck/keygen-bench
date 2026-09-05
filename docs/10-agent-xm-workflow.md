# Agent-generated keygen tunes: verified tooling and setup

Investigation date: 2026-09-05. Scope: music only, delivered as editable XM and WAV. No licensing utilities, key generators, visual demos, Renoise projects, or hosted song-generation services are part of this setup.

## Decision

The relevant historical lineage is FastTracker II -> modern FT2-compatible editors. MilkyTracker is a later recreation, not the original DOS tracker. This does not make FT2 the sole historical keygen tool; the earlier chapters also cover ProTracker, Scream Tracker, and Impulse Tracker. [A1][A2]

For headless composition, the closest concrete candidate found is the third-party `mova77/fast-tracker2` fork. Pin it to `6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d`, the revision inspected here. It adds a stateful MCP authoring interface to FT2 clone. Use MilkyTracker's `milkycli` only as an independent module renderer, not as the composer. [A3][A4][A5]

This is a conditional recommendation, not a certified turnkey installation. Source inspection verifies that the authoring handlers exist. The fork does not expose the entire tracker, and its native build/render cycle was not run in this environment. An opt-in acceptance checker is included so the missing runtime evidence can be collected rather than assumed.

## What was established

| Question | Finding | Evidence level |
|---|---|---|
| Is MilkyTracker the original? | No. Its project describes recreating FT2's workflow and replay. | Official project description [A1] |
| Does `milkycli` exist? | Yes. Debian's `1.06+dfsg-2` manual documents it and its conversion flags. | Package-maintainer documentation [A5] |
| Does `milkycli` compose? | No composition interface is documented there; its CLI is conversion-only. | Package-maintainer documentation [A5] |
| Does the FT2 fork actually contain authoring code? | Yes. Seventeen tools are registered and dispatched, including cell edits, sample creation, save, and render. | Pinned source inspection [A4] |
| Is `--mcp` part of stock FT2 clone? | It is a feature of this fork; do not infer it from the stock project's name or download links. | Project distinction [A2][A3] |
| Is the agent given complete tracker control? | No. Envelopes and note-to-sample mapping are notable missing setters. | Pinned handler/schema inspection [A4] |
| Did native authoring/rendering pass here? | Not run: neither tracker binary nor required native development libraries was present; direct GitHub cloning failed on DNS resolution. | Environment observation |
| What tests did pass? | 17 checker tests and 5 existing module-header tests; build-script syntax validation. | Local execution, 22 tests total |

The Python tests use synthetic data and a fake JSON-RPC process. They do not test the FT2 mixer. Neither audio listening nor independent-renderer comparison was performed.

## The fork's real interface

The source pin, file paths, and status are also recorded in [the verification record](../data/agent-tooling-verification.json).

| Tool group | Registered tools | Practical use |
|---|---|---|
| Project | `module_new`, `module_load`, `module_info`, `module_save` | Create, reopen, inspect basic metadata, save XM/MOD |
| Arrangement | `song_set`, `order_set` | Tempo, speed, length, restart order, channel count, order entries |
| Patterns | `pattern_set_cell`, `pattern_get_cell`, `pattern_clear`, `pattern_set_length`, `cell_clear` | Notes, instruments, raw volume/effect bytes, pattern lengths |
| Sound material | `sample_load`, `sample_save`, `sample_set`, `sample_create_from_pcm` | Import or synthesize sample data; adjust tuning, volume, panning and loop metadata |
| Instrument | `instrument_set` | Instrument naming only at this revision |
| Output | `module_render` | Render the in-memory project to WAV, with rate, bit depth and order-range options |

The handlers live in `src/ft2_mcp.c`. `instrument_set` is narrower than its name suggests: it accepts an instrument number and a name. It does not expose volume/panning envelope points, sustain/loop controls, multisample keymaps, fadeout, or automatic-vibrato parameters. No bulk pattern-edit or full project-dump tool appears in the registered list. [A4]

### Consequences for creative freedom

The agent can create custom sounds through externally generated WAV files or PCM payloads, then sequence them with tracker commands. That is substantially more flexible than a fixed preset-based tune generator. It still has artificial limitations compared with the GUI.

For complete XM-oriented control, extend and test the bridge's instrument-envelope, sample-mapping, fadeout/vibrato, bulk-read/write, and checkpoint operations. This PR documents those gaps; it does not implement those missing upstream features. Baking modulation into a sample is an optional musical technique, not a claim that an envelope API already exists.

Do not confine the agent to the acceptance fixture's waveform, tempo, channel count, melody, or length. That fixture tests plumbing, not composition.

### Protocol and encoding details

The inspected server uses newline-delimited JSON-RPC over stdin/stdout, advertises MCP `2024-11-05`, and keeps project state in one process. Use a client compatible with that protocol; compatibility with every current agent client is not established. Keep the process alive across edits. Run `initialize`, send `notifications/initialized`, inspect `tools/list`, then call tools. [A4]

Use integer request IDs with the included checker. Its narrow implementation is not a replacement for a general MCP SDK. Results often contain a JSON document inside an MCP text-content item; parse that inner document for readback.

Pattern/order/channel/sample-slot indices are zero-based; instruments start at one. Pattern volume is a raw XM volume-column byte, not a normalized amplitude. JSON effect values are decimal integers: for example, decimal 55 encodes the hexadecimal parameter `37`. `sample_create_from_pcm` accepts base64 `int16` or `float32` data but stores a 16-bit sample; it is not a float-sample XM extension. [A4]

There is a 256-KiB input-line buffer, a 512-token JSON parser budget, and a separate 512-KiB decoded-PCM ceiling. The line limit becomes restrictive first for large base64 inputs. Keep direct payloads small; use `sample_load` for larger files. Avoid huge bulk messages. Use simple ASCII names and forward-slash paths for this prototype: the inspected string helper copies token bytes rather than doing full JSON-string unescaping. [A4]

Headless initialization still opens an SDL audio device, although rendering goes to a file. The sample configuration uses `SDL_AUDIODRIVER=dummy`; availability depends on the installed SDL build. The checker isolates HOME/XDG configuration on Unix-like systems. It does not constitute a filesystem sandbox or guarantee Windows configuration isolation. [A6][A9]

## Build and connect

### Linux candidate recipe

The root `CMakeLists.txt` globs the REST source but does not link libmicrohttpd. `CMakeLists.txt.api` contains incomplete example source lists. The original no-MIDI shell script also lacks the new HTTP dependency. Therefore neither an unmodified CMake invocation nor the old no-MIDI script should be presented as a verified headless build recipe. [A7]

The included [Linux build script](../scripts/build-ft2-linux.sh) follows the existing no-MIDI source selection but adds explicit SDL2/libmicrohttpd flags through pkg-config, pthread support, a fixed source commit, and fail-fast handling. It is syntax-checked and source-derived, not native-build-tested.

On Debian/Ubuntu, install the prerequisites, review the source, then run:

```bash
sudo apt-get install build-essential git pkg-config libsdl2-dev libmicrohttpd-dev
bash scripts/build-ft2-linux.sh /tmp/keygen-ft2-build
python tools/ft2_smoke.py \
  --ft2 /tmp/keygen-ft2-build/release/other/ft2-clone \
  --out /tmp/keygen-ft2-acceptance
```

Both directories must be new. The checker deliberately refuses to overwrite an earlier run. It does not install dependencies or fetch code. Native compilation may expose additional issues not visible in this source review; a failed build is a failed gate, not permission to claim the integration works.

### macOS and Windows

The fork's documented macOS route uses Homebrew `sdl2-compat` and `libmicrohttpd`, then `make-simple.sh`. That script targets arm64 and writes `release/macos/ft2-clone-macos.app/Contents/MacOS/ft2-clone-macos`. It is not a universal Mac build. Its unconditional final success message is not sufficient evidence of compilation; inspect the compiler exit/output and run the acceptance checker. macOS compilation was not tested here. [A3][A8]

No Windows build is certified by this investigation. The stock project's Windows binaries should not be assumed to contain the fork's additions.

### Agent connection

The process command is the built fork executable with `--mcp`. [A3][A4]

[config/ft2-mcp.example.json](../config/ft2-mcp.example.json) shows a common `mcpServers` configuration shape. Replace its executable and scratch-directory paths and adapt the file location/schema to the chosen client. The example is not proof of client-specific integration. No HTTP server, externally reachable service, account, or API key is needed by this tracker backend.

Give the agent a persistent stdio connection, a project-local Python/shell workspace for custom sample generation, and file access to its output directory. Run the tracker without elevated privileges in a disposable workspace. The fork is source you are choosing to execute; this review is not a security audit.

## Acceptance checks

Run the checker only with a locally reviewed build:

```bash
python tools/ft2_smoke.py --ft2 /absolute/path/to/ft2-clone \
  --out /tmp/ft2-check-001

# Optional, when this version of milkycli is actually installed:
python tools/ft2_smoke.py --ft2 /absolute/path/to/ft2-clone \
  --milkycli /absolute/path/to/milkycli --out /tmp/ft2-check-002

# Offline tests of the checker itself:
python -m unittest discover -s tests -v
```

The native check initializes/discovers tools, creates an original short tone, writes notes, revises and reads back a note, saves an XM, verifies its header, resets the project, reloads the file, verifies the revision persisted, renders 16-bit PCM, and checks duration, silence, full-scale samples, RMS and DC offset. It saves the tool list, diagnostics, artifact hashes and an explicit result report.

The optional MilkyTracker path renders that saved XM with a second implementation. It does not require byte-identical WAVs: mixing choices can differ. It only checks the second output's basic integrity. The checker records the inspected source reference, but does not certify that an arbitrary supplied binary was built from that commit. Record the actual checkout/build separately.

The four-note fixture does not test every tracker command, envelopes, multisampling, long arrangements, concurrent calls, arbitrary third-party files, or authentic musical quality. It also does not certify a song's loop seam. These are deliberate limits, not hidden green checks.

## Independent rendering and listening

The Debian 1.06 manual documents these commands: [A5]

```bash
milkycli -help
milkycli -sample-rate 44100 -output tune.wav tune.xm
milkycli -multi-track -output stems.wav tune.xm
# Alternative with a supporting GUI executable:
milkytracker -headless -output tune.wav tune.xm
```

Availability is package/build-specific. Do not assert that every MilkyTracker installer bundles `milkycli`; check the installed executable. The documented multitrack export numbers its files and omits silent tracks.

Rendering is not listening. An autonomous musical review stage needs either an agent that genuinely accepts the rendered audio or a separately connected audio-review tool. This repository provides neither an audio-capable model nor that integration. A proposed contract is `review_audio(path, question, comparison_path=None)`, returning timestamped observations and an explicit statement of what audio was received. It is a design requirement, not an existing FT2 tool.

For production tunes, inspect full arrangements, individual parts, and the actual repeated restart transition. An endpoint jump metric or `loops` option alone does not prove a musical seam is clean. Review sustained notes, effect memory, tails and transitions. Preserve previous revisions and compare at matched levels. Technical checks can reject broken output; they cannot establish that a tune is good.

Use [the creative prompt](../prompts/keygen-composer.md) only after the actual machine passes the acceptance checks. It leaves musical decisions open and requires honest reporting when listening or a requested editing capability is unavailable.

## Readiness verdict

Music-only XM authoring: plausible and source-backed with this fork, pending native acceptance on the target machine.

Full GUI-equivalent creative control: not present in the inspected API. Add and verify the missing controls rather than silently reducing the brief.

Autonomous render/listen/revise loop: tracker render handlers exist, but actual audio review needs a separately verified capability. No listening success is claimed here.

## Sources

[A1]: https://milkytracker.org/about/
[A2]: https://github.com/8bitbubsy/ft2-clone
[A3]: https://github.com/mova77/fast-tracker2/blob/6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d/README.md
[A4]: https://github.com/mova77/fast-tracker2/blob/6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d/src/ft2_mcp.c
[A5]: https://manpages.debian.org/testing/milkytracker/milkytracker.1.en.html
[A6]: https://github.com/mova77/fast-tracker2/blob/6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d/src/ft2_renderer.c
[A7]: https://github.com/mova77/fast-tracker2/tree/6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d
[A8]: https://github.com/mova77/fast-tracker2/blob/6c2ffc0778d02a42286b4a87e4dc28793ccbdf4d/make-simple.sh
[A9]: https://wiki.libsdl.org/SDL2/FAQUsingSDL

A7 refers specifically to `CMakeLists.txt`, `CMakeLists.txt.api`, and `make-linux-nomidi.sh` at the pinned revision. The supplementary verification record lists their exact paths and file hashes. Sources were inspected on 2026-09-05; native execution limits are stated above.
