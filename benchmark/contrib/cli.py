#!/usr/bin/env python3
"""Set up, configure, check and run private community benchmark work.

Examples:
  python benchmark/contrib/cli.py setup
  <printed-venv-python> benchmark/contrib/cli.py configure
  <printed-venv-python> benchmark/contrib/cli.py doctor
  <printed-venv-python> benchmark/contrib/cli.py smoke --work /private/new-smoke
  <printed-venv-python> benchmark/contrib/cli.py run --work /private/new-run --out submissions/new-bundle

Model smoke and run spend money and require confirmation. Doctor never sends
provider requests. OAuth requires a separately installed, user-authorized
loopback bridge; this CLI does not log in or extract account tokens.
"""
from __future__ import annotations

import argparse
import getpass
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import uuid

CONTRIB = Path(__file__).resolve().parent
ROOT = CONTRIB.parents[1]
sys.path.insert(0, str(CONTRIB))
import run_contrib as runner
from native_models import PROVIDERS, PROTOCOLS, validate_model
from score_playback import DEFAULT_BINARY, renderer_identity

PRESETS = {
    "go": "https://opencode.ai/zen/go/v1",
    "vercel": "https://ai-gateway.vercel.sh/v1",
    "nim": "https://integrate.api.nvidia.com/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
}
CONFIG_FIELDS = {"provider", "model", "api", "base_url", "bridge_binary", "reasoning_tier",
                 "tier_source", "generation", "handle", "agent_image", "visualizer_image"}
DEFAULT_CONFIG = Path.home() / ".config/keygen-benchmark/contrib.json"
DEFAULT_HOME = Path.home() / ".local/share/keygen-benchmark/contrib"
AGENT_IMAGE = "keygen-ft2-benchmark:local"
VISUALIZER_IMAGE = "keygen-ft2-visualizer:local"
APT_GUIDANCE = "sudo apt-get update && sudo apt-get install -y python3-venv build-essential git pkg-config libsdl2-dev libmicrohttpd-dev"
CREDENTIAL_NAME = re.compile(r"(?:key|token)$|(?:^|_)(?:key|token|secret|password)(?:_|$)", re.I)


class CLIError(ValueError):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        if message.startswith("unrecognized arguments"):
            message = "Unknown argument. Credentials are accepted only through the environment or a hidden prompt; use --help."
        elif "invalid choice:" in message:
            message = message.split("invalid choice:", 1)[0] + "invalid choice; use --help for supported values"
        super().error(message)


def json_object(text):
    try:
        value = json.loads(text)
    except ValueError:
        raise argparse.ArgumentTypeError("Generation must be valid JSON; never include credentials") from None
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("Generation must be a JSON object")
    return value


def parser():
    result = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = result.add_subparsers(dest="command", required=True, parser_class=Parser)
    setup = commands.add_parser("setup", help="Install pinned packages and build both Docker targets and trusted renderer")
    setup.add_argument("--home", type=Path, default=DEFAULT_HOME, help="Private directory outside checkout for the virtual environment")
    setup.add_argument("--no-input", action="store_true", help="Never prompt; setup already needs no input")
    configure = commands.add_parser("configure", help="Save owner-only nonsecret model settings outside checkout")
    configure.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    configure.add_argument("--no-input", action="store_true")
    configure.add_argument("--replace", action="store_true", help="Replace an existing private configuration")
    configure.add_argument("--provider", choices=sorted(PROVIDERS))
    configure.add_argument("--model", help="Exact model identifier, never an inferred default")
    configure.add_argument("--api", choices=["chat", "responses", "messages"])
    configure.add_argument("--base-url", help="Preset endpoint, reviewed custom HTTPS URL, or authorized loopback bridge /v1")
    configure.add_argument("--bridge-binary", type=Path, help="Executable for your separately installed, user-authorized OAuth bridge")
    configure.add_argument("--reasoning-tier", help="Highest documented tier, or none-available if documented")
    configure.add_argument("--tier-source", help="Public HTTPS documentation URL for the declared tier")
    configure.add_argument("--generation", type=json_object, help="Explicit native output and reasoning settings as JSON, no credentials")
    configure.add_argument("--handle", help="Public GitHub handle")
    configure.add_argument("--agent-image", default=AGENT_IMAGE)
    configure.add_argument("--visualizer-image", default=VISUALIZER_IMAGE)
    doctor = commands.add_parser("doctor", help="Check prerequisites offline, without model or HTTP requests")
    doctor.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    doctor.add_argument("--infrastructure-only", action="store_true", help="Check runtime/images/renderer without provider configuration or credential")
    doctor.add_argument("--sandbox", action="store_true", help="Collect, render and score an explicit synthetic XM in offline Docker; never submission eligible")
    doctor.add_argument("--xm", type=Path, help="Explicit synthetic XM for --sandbox")
    doctor.add_argument("--work", type=Path, help="New absolute private directory for --sandbox evidence")
    doctor.add_argument("--no-input", action="store_true", help="Doctor never prompts")
    for name, description in (("smoke", "Spend on one bounded model attempt, never eligible for submission"),
                              ("run", "Spend on all three frozen attempts and package every outcome")):
        command = commands.add_parser(name, help=description)
        command.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
        command.add_argument("--work", type=Path, required=True, help="New absolute private working directory outside checkout")
        if name == "run":
            command.add_argument("--out", type=Path, required=True, help="New bundle directory; review before publishing")
        command.add_argument("--yes", action="store_true", help="Explicitly authorize model spending")
        command.add_argument("--no-input", action="store_true", help="Never prompt; requires --yes and credential in environment")
    return result


def interactive(args):
    return not args.no_input and sys.stdin.isatty() and sys.stderr.isatty()


def outside_path(path):
    if not path.is_absolute():
        raise CLIError("Use an absolute private path outside the checkout")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise CLIError("Private paths must not contain symlinks")
    path = path.resolve()
    if path == ROOT or ROOT in path.parents:
        raise CLIError("Keep private configuration, environments and work outside the checkout")
    return path


def check_owner(path, *, directory=False):
    details = path.lstat()
    valid_type = stat.S_ISDIR(details.st_mode) if directory else stat.S_ISREG(details.st_mode)
    if not valid_type or details.st_uid != os.getuid() or details.st_mode & 0o077:
        raise CLIError("Private configuration and its directory must be owned by you with modes 0600 and 0700; symlinks are forbidden")


def private_directory(path):
    path = outside_path(path)
    missing = []
    ancestor = path
    while not ancestor.exists():
        missing.append(ancestor)
        ancestor = ancestor.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
    check_owner(path, directory=True)
    return path


def save_config(path, values, *, replace=False):
    path = outside_path(path)
    private_directory(path.parent)
    if path.exists():
        check_owner(path)
        if not replace:
            raise CLIError("Configuration already exists; use --replace to deliberately overwrite it")
    descriptor, pending = tempfile.mkstemp(prefix=".contrib-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            json.dump({"schema": "keygen-contrib-config-1", **values}, target, indent=2, allow_nan=False)
            target.write("\n")
        if replace:
            os.replace(pending, path)
        else:
            # Atomic no-clobber publication, even if another configure races us.
            os.link(pending, path, follow_symlinks=False)
    finally:
        Path(pending).unlink(missing_ok=True)


def load_config(path):
    path = outside_path(path)
    if not path.exists():
        raise CLIError("No saved configuration. Run configure first, or select --config with an existing private file")
    check_owner(path.parent, directory=True)
    check_owner(path)
    if path.stat().st_size > 64 * 1024:
        raise CLIError("Configuration exceeds the 64 KiB limit")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise CLIError("Configuration is not valid JSON. Run configure again") from None
    if (not isinstance(value, dict) or value.get("schema") != "keygen-contrib-config-1"
            or set(value) != CONFIG_FIELDS | {"schema"}):
        raise CLIError("Unsupported configuration fields; credentials must never be stored in configuration")
    values = {key: value[key] for key in CONFIG_FIELDS}
    for key in CONFIG_FIELDS - {"generation", "bridge_binary"}:
        if not isinstance(values[key], str) or not values[key]:
            raise CLIError("Configuration has invalid nonsecret settings. Run configure again")
    if values["bridge_binary"] is not None:
        if not isinstance(values["bridge_binary"], str):
            raise CLIError("Configuration has an invalid bridge executable path")
        values["bridge_binary"] = Path(values["bridge_binary"])
    if values["provider"] not in PROVIDERS or values["api"] not in {"chat", "responses", "messages"}:
        raise CLIError("Configuration has an unsupported provider or protocol")
    args = argparse.Namespace(**values)
    validate_configuration(args)
    return args


def validate_configuration(args):
    if args.provider not in PROVIDERS or args.api not in PROTOCOLS[args.provider]:
        raise CLIError("Choose a native protocol supported by the selected provider")
    if not isinstance(args.generation, dict):
        raise CLIError("Generation must be a JSON object")
    raw = json.dumps({key: str(getattr(args, key)) for key in CONFIG_FIELDS}, allow_nan=False)
    if re.search(r"(?:sk-|oc_sk_)[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}", raw):
        raise CLIError("Credential-like material is forbidden in model settings")
    for key, value in os.environ.items():
        if len(value) >= 8 and CREDENTIAL_NAME.search(key) and value in raw:
            raise CLIError("A credential appeared in model settings; keep secrets only in the environment or hidden prompt")
    output_fields = {"max_tokens", "max_completion_tokens", "max_output_tokens"}
    if not output_fields.intersection(args.generation):
        raise CLIError("Declare your model's documented output limit explicitly in --generation")
    model, _ = runner.validate_inputs(args)
    validate_model(runner.frozen_configuration(), model)
    return model


def configure(args):
    fields = (("provider", "Provider (" + ", ".join(sorted(PROVIDERS)) + ")"),
              ("model", "Exact model identifier"), ("api", "Native API protocol (chat/responses/messages)"),
              ("reasoning_tier", "Highest documented reasoning tier (or none-available)"),
              ("tier_source", "Public HTTPS tier documentation URL"),
              ("generation", "Native generation JSON including documented output cap and reasoning"),
              ("handle", "Public GitHub handle"))
    for field, label in fields:
        if getattr(args, field) is None:
            if not interactive(args):
                raise CLIError(f"Missing --{field.replace('_', '-')}; supply it with --no-input, or configure in a terminal")
            text = input(label + ": ").strip()
            setattr(args, field, json_object(text) if field == "generation" else text)
    if args.provider not in PROVIDERS:
        raise CLIError("Choose a supported provider; see configure --help")
    if args.base_url is None:
        args.base_url = PRESETS.get(args.provider)
        if args.base_url is None:
            if not interactive(args):
                raise CLIError("This provider requires an explicit --base-url; OAuth uses your own authorized http://127.0.0.1:PORT/v1 bridge")
            args.base_url = input("Reviewed public HTTPS endpoint or authorized loopback bridge URL: ").strip()
    if args.provider in runner.BRIDGE_PROVIDERS:
        print("OAuth uses your separately installed, authorized bridge. Complete its documented login yourself and start its loopback listener; no account tokens are extracted here.", file=sys.stderr)
        if args.bridge_binary is None and interactive(args):
            args.bridge_binary = Path(input("Authorized bridge executable path: ").strip())
    validate_configuration(args)
    values = {key: getattr(args, key) for key in CONFIG_FIELDS}
    if values["bridge_binary"] is not None:
        values["bridge_binary"] = str(values["bridge_binary"].resolve())
    # Never serialize any environment value or hidden-prompt credential.
    save_config(args.config, values, replace=args.replace)
    print(f"Saved private configuration to {args.config}. No credential was saved.")
    print("Set KEYGEN_CONTRIB_API_KEY privately in your controller environment, then run doctor. Run/smoke can also ask for it without echo in a terminal.")


def prerequisite_errors(*, build=True):
    errors = []
    if platform.system() != "Linux":
        errors.append("Use Linux with a local Docker Engine")
    if sys.version_info < (3, 11):
        errors.append("Use Python 3.11 or later")
    if build:
        compiler = shlex.split(os.environ.get("CC", "cc"))
        missing = [name for name in ("git", "pkg-config", compiler[0] if compiler else "cc") if not shutil.which(name)]
        if missing:
            errors.append("Missing build tools. On Debian/Ubuntu run: " + APT_GUIDANCE)
        elif subprocess.run(["pkg-config", "--exists", "sdl2", "libmicrohttpd"], capture_output=True).returncode:
            errors.append("Missing SDL2/libmicrohttpd development packages. On Debian/Ubuntu run: " + APT_GUIDANCE)
    return errors


def package_errors():
    errors = []
    for line in (ROOT / "benchmark/requirements.txt").read_text().splitlines():
        pin = line.split("#", 1)[0].strip()
        if not pin:
            continue
        name, version = pin.split("==", 1)
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != version:
            errors.append(f"Install pinned {name}=={version} using the setup virtual environment")
    return errors


def setup(args):
    errors = prerequisite_errors()
    try:
        import venv
        import ensurepip
        docker = runner.run.docker_command()
        runner.run.shell(docker + ["info"])
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        errors.append("Install Python venv support and Docker Engine, start its local daemon, and grant your user access. On Debian/Ubuntu for Python/build dependencies run: " + APT_GUIDANCE)
    home = outside_path(args.home)
    ancestor = home
    while not ancestor.exists():
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < 20 * 1024**3:
        errors.append("Free at least 20 GiB on the setup filesystem before building")
    if errors:
        raise CLIError("\n".join(errors))
    home = private_directory(home)
    environment = {key: value for key, value in os.environ.items()
                   if not CREDENTIAL_NAME.search(key)}
    python = home / "venv/bin/python"
    if (home / "venv").exists():
        check_owner(home / "venv", directory=True)
        if python.is_symlink():
            # A venv interpreter normally points to the base Python; the enclosing
            # owner-only directory is the trust boundary, not that normal symlink.
            if not python.resolve().is_file():
                raise CLIError("The existing virtual environment has a broken interpreter; choose a new --home")
    renderer_output = outside_path(Path(os.environ.get("KEYGEN_FT2_ANALYSIS", str(DEFAULT_BINARY))).expanduser())
    commands = [
        ("Creating the private virtual environment", [sys.executable, "-m", "venv", str(home / "venv")]),
        ("Installing pinned controller packages", [str(python), "-m", "pip", "install", "-r", str(ROOT / "benchmark/requirements.txt")]),
        ("Pulling the pinned Debian base", docker + ["pull", runner.contract()["base_image"]]),
        ("Building the pinned agent target", docker + ["build", "-f", str(ROOT / "benchmark/Dockerfile"), "--target", "agent", "-t", AGENT_IMAGE, str(ROOT)]),
        ("Building the pinned visualizer target", docker + ["build", "-f", str(ROOT / "benchmark/Dockerfile"), "--target", "visualizer", "-t", VISUALIZER_IMAGE, str(ROOT)]),
        ("Building the trusted analysis renderer", [str(python), str(ROOT / "scripts/build-ft2-analysis.py"), "--output", str(renderer_output)]),
    ]
    for description, command in commands:
        print(description + "...", flush=True)
        process = subprocess.run(command, env=environment, capture_output=True)
        if process.returncode:
            raise CLIError(description + " failed. Check network access and the stated prerequisites; rerun setup after correcting them. Provider credentials were not passed to the build.")
        if description.startswith("Creating"):
            os.chmod(home / "venv", 0o700)
    runner.inspect_images(docker, AGENT_IMAGE, VISUALIZER_IMAGE)
    renderer_identity()
    print(f"Setup complete. Next: {shlex.quote(str(python))} benchmark/contrib/cli.py configure")


def bridge_check(config):
    if config.provider not in runner.BRIDGE_PROVIDERS:
        return None
    endpoint = urlsplit(config.base_url)
    try:
        with socket.create_connection((endpoint.hostname, endpoint.port), timeout=2):
            pass
    except OSError:
        raise CLIError("Authorized OAuth bridge is not listening. Complete its documented login and start it at your configured loopback address. Doctor does not authenticate or send provider requests") from None
    return runner.sha(config.bridge_binary)


def admit_artifact_disk(directory, synthetic_xm=None):
    if synthetic_xm is None:
        runner.ArtifactStore(runner.frozen_configuration()["storage"]).preflight(directory, 1)
    else:
        from score_playback import require_resources
        # Synthetic verification has no model worker or three-attempt archive.
        # Reserve the bounded canonical artifact plus input copies initially;
        # trusted scoring separately admits every actual trace/capture.
        require_resources(disk_bytes=128 * 1024**2 + synthetic_xm.stat().st_size * 2,
                          directory=directory)


def doctor(args):
    errors = prerequisite_errors(build=False) + package_errors()
    for warning in prerequisite_errors():
        if warning not in errors:
            print("Build prerequisite warning: " + warning, file=sys.stderr)
    from score_playback import available_memory, capture_memory_budget, require_resources
    try:
        if args.sandbox and args.xm is not None:
            # Admit the minimum loop-analysis window for this explicit fixture.
            # The trusted scorer still gates every actual capture/array allocation
            # after canonical rendering reveals the real duration.
            memory_bytes = capture_memory_budget(args.xm, 20) + 32 * 1024**2
        else:
            memory_bytes = 2 * 1024**3
        require_resources(memory_bytes=memory_bytes)
    except (RuntimeError, ValueError) as exc:
        errors.append(f"Evaluation memory/module admission failed: {str(exc)}. Available RAM: {available_memory()} bytes")
    except Exception as exc:
        errors.append("Evaluation memory/module admission failed: " + safe_error(exc))
    try:
        ancestor = args.work if args.work else args.config.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        admit_artifact_disk(ancestor, args.xm if args.sandbox else None)
    except RuntimeError as exc:
        errors.append("Local artifact disk admission failed: " + str(exc))
    except Exception as exc:
        errors.append("Local artifact disk admission failed: " + safe_error(exc))
    config = None
    if not args.infrastructure_only:
        try:
            config = load_config(args.config)
            bridge_digest = bridge_check(config)
            if bridge_digest:
                print(f"Authorized bridge executable SHA-256: {bridge_digest}; TCP listener is reachable. Upstream authentication is unverified.")
            if not os.environ.get("KEYGEN_CONTRIB_API_KEY"):
                errors.append("KEYGEN_CONTRIB_API_KEY is not set; set it privately before a funded run")
        except Exception as exc:
            errors.append(safe_error(exc))
    docker = None
    try:
        docker = runner.run.docker_command()
        runner.run.shell(docker + ["info"])
    except ValueError as exc:
        errors.append("Docker transport check failed: " + safe_error(exc))
        docker = None
    except Exception:
        errors.append("Local Docker daemon is unavailable or access is denied. Start Docker Engine and grant your user access to its local socket")
        docker = None
    if docker is not None:
        try:
            images, _, _ = runner.inspect_images(docker, config.agent_image if config else AGENT_IMAGE,
                                                 config.visualizer_image if config else VISUALIZER_IMAGE)
            print("Pinned Docker image ancestry verified for agent and visualizer.")
        except Exception as exc:
            errors.append("Pinned Docker image check failed: " + safe_error(exc))
    try:
        renderer_identity()
        print("Trusted analysis renderer provenance verified.")
    except Exception:
        errors.append("Trusted analysis renderer missing or unverified. Run setup, or scripts/build-ft2-analysis.py with the documented build prerequisites")
    if args.sandbox and (args.xm is None or args.work is None):
        errors.append("doctor --sandbox requires --xm with an explicit synthetic module and --work with a new absolute private directory")
    if not args.sandbox and (args.xm is not None or args.work is not None):
        errors.append("--xm and --work are only used with doctor --sandbox")
    if errors:
        for error in errors:
            print("FAIL: " + error, file=sys.stderr)
        return 1
    if args.sandbox:
        sandbox_smoke(args, docker, images)
    print("Doctor passed offline checks. No provider request was sent; model availability, authentication, pricing and endpoint delivery remain unverified.")
    return 0


def new_work(path):
    path = runner.private_work_path(path)
    if path.exists():
        raise CLIError("Use a new private work directory; never reuse or replace earlier attempts")
    return private_directory(path)


def sandbox_smoke(args, docker, images):
    source = args.xm.resolve(strict=True)
    if not source.is_file() or source.stat().st_size > runner.LIMITS["artifact_bytes"]:
        raise CLIError("Provide a regular synthetic XM within the frozen artifact size limit")
    from score_playback import validate_xm_header
    validate_xm_header(source)
    work = new_work(args.work)
    runner.write_json(work / "smoke.json", {"kind": "offline-synthetic", "submission_eligible": False,
                                           "provider_requests": 0})
    attempt = work / "sandbox-smoke"
    attempt.mkdir(mode=0o700)
    config = runner.frozen_configuration()
    name = "keygen-cli-smoke-" + uuid.uuid4().hex[:16]
    try:
        runner.run.start_container(docker, images["agent"], name)
        runner.run.shell(docker + ["exec", "-i", name, "python3", "-c",
                         "import sys,os;os.makedirs('/workspace/submission',exist_ok=True);open('/workspace/submission/tune.xm','wb').write(sys.stdin.buffer.read())"], input=source.read_bytes())
        runner.run.collect_submission(docker, name, attempt, config["limits"]["artifact_bytes"])
    finally:
        runner.run.remove_container(docker, name)
    audio = runner.run.render(docker, images["agent"], attempt, config)
    runner.write_json(attempt / "status.json", {"status": "RENDERED_UNSCORED", "model": {"model": "offline-synthetic"},
                     "eligible": True, "render": "ok", "audio": audio, "submission_eligible": False})
    from score import profile_attempt
    profile = profile_attempt(attempt)
    if not profile or profile.get("evaluation_status") != "evaluated":
        raise CLIError("Synthetic collection/rendering finished but trusted scoring failed; inspect the private profile evidence")
    print(f"Offline sandbox collection, trusted rendering and scoring passed. Private evidence: {work}. Not eligible for submission.")


def consent(args, config):
    count = "three frozen independent attempts" if args.command == "run" else "one smoke attempt (180-second wall limit, 4 steps, 60-second model request limit)"
    print(f"This will spend on {count} for exact model {config.model} using {config.provider}/{config.api}. Documented generation/output settings stay unchanged. Pricing and token cost are not verified.", file=sys.stderr)
    if args.yes:
        return
    if not interactive(args):
        raise CLIError("Spending is not authorized. Supply --yes explicitly, or confirm in a terminal")
    if input("Authorize model spending? Type yes: ").strip().lower() != "yes":
        raise CLIError("Spending was not authorized; no provider request was sent")


def obtain_credential(args):
    if os.environ.get("KEYGEN_CONTRIB_API_KEY"):
        return
    if not interactive(args):
        raise CLIError("Set KEYGEN_CONTRIB_API_KEY privately in the environment; --no-input cannot ask for a credential")
    credential = getpass.getpass("Controller provider/bridge credential (never saved): ")
    if not credential:
        raise CLIError("A controller credential is required; no provider request was sent")
    os.environ["KEYGEN_CONTRIB_API_KEY"] = credential


def model_smoke(args, settings):
    config, model, docker, images, environment = runner.prepare_run(settings)
    bridge_check(settings)
    config["limits"].update(wall_seconds=180, steps=4, request_seconds=60, command_seconds=30,
                            render_seconds=90, video_seconds=90)
    config["native"]["timeout_seconds"] = 60
    config["prompts"] = runner.campaign.prompt_manifest(config["limits"])
    config["max_attempts"] = 1
    model["effective_settings"] = runner.campaign.normalize_native(config, [model])[0]
    environment["contract"].update(limits=dict(config["limits"]), native=dict(config["native"]),
                                   prompt=config["prompts"])
    work = new_work(args.work)
    runner.write_json(work / "smoke.json", {"kind": "single-model-smoke", "submission_eligible": False,
                     "config": config, "environment": environment, "model": model})
    runner.run.reserve(work, model, 1, "smoke-attempt")
    failure = False
    try:
        runner.run.run_one(work, config, model, docker, images["agent"], images["visualizer"],
                           1, "smoke-attempt", runner.ArtifactStore(config["storage"]))
    except Exception:
        failure = True
    directory = work / "smoke-attempt"
    status = json.loads((directory / "status.json").read_text())
    status["submission_eligible"] = False
    runner.write_json(directory / "status.json", status)
    profile_path = directory / "profile.json"
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else None
    print(f"Smoke outcome: {status['status']}. Private evidence: {work}. This short-limit attempt is not eligible for submission and no bundle was produced.")
    if failure or not runner.run.attempt_succeeded(status, profile):
        raise CLIError("Model smoke did not complete a verified, scored submission. Inspect private status/profile evidence; do not treat this as a successful provider check")


def safe_error(exc):
    if isinstance(exc, (CLIError, ValueError, argparse.ArgumentTypeError)):
        message = str(exc)
    elif isinstance(exc, (ImportError, importlib.metadata.PackageNotFoundError)):
        message = "Pinned controller dependencies are missing. Run setup and use its printed virtual-environment Python"
    elif isinstance(exc, FileNotFoundError):
        message = "A required local file or executable is missing; check the configured paths and run setup"
    elif isinstance(exc, PermissionError):
        message = "Permission denied. Use owner-only private paths and a local Docker daemon your user can access"
    else:
        message = f"{type(exc).__name__}. Check local prerequisites and private attempt evidence; no provider response or credential is printed"
    for key, value in os.environ.items():
        if value and CREDENTIAL_NAME.search(key):
            message = message.replace(value, "[redacted]")
    return message


def main(argv=None):
    args = parser().parse_args(argv)
    previous_key = os.environ.get("KEYGEN_CONTRIB_API_KEY")
    previous_umask = os.umask(0o077)
    try:
        if args.command == "setup":
            setup(args)
        elif args.command == "configure":
            configure(args)
        elif args.command == "doctor":
            return doctor(args)
        else:
            settings = load_config(args.config)
            work = runner.private_work_path(args.work)
            if work.exists():
                raise CLIError("Use a new work directory; existing attempt evidence must not be overwritten")
            consent(args, settings)
            obtain_credential(args)
            bridge_check(settings)
            if args.command == "run":
                settings.work, settings.out = work, args.out
                runner.execute(settings)
            else:
                model_smoke(args, settings)
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Interrupted. No new spending is authorized. Keep any private attempt evidence; do not rerun and select outcomes.", file=sys.stderr)
        return 130
    except Exception as exc:
        print("error: " + safe_error(exc), file=sys.stderr)
        return 1
    finally:
        os.umask(previous_umask)
        if previous_key is None:
            os.environ.pop("KEYGEN_CONTRIB_API_KEY", None)
        else:
            os.environ["KEYGEN_CONTRIB_API_KEY"] = previous_key


if __name__ == "__main__":
    sys.exit(main())
