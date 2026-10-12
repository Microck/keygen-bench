#!/usr/bin/env python3
"""Run three frozen independent attempts using the existing native runner."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import subprocess
import time

from validate_bundle import (ATTEMPTS, BRIDGE_PROVIDERS, LIMITS, contract,
                             public_documentation_url, public_model, public_status,
                             required_packages, seal, sha, validate, write_json)

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import campaign
import native_readiness
import run
from artifacts import ArtifactStore
from native_models import PROVIDERS, PROTOCOLS, declared_reasoning, check_tier, validate_url

def generation_json(text):
    try:
        value = json.loads(text)
    except ValueError:
        raise argparse.ArgumentTypeError("Generation must be valid JSON without credentials") from None
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("Generation must be a JSON object")
    return value



def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Exact upstream model identifier")
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--bridge-binary", type=Path, help="OAuth bridge executable; only its SHA-256 is published")
    parser.add_argument("--api", choices=["chat", "responses", "messages"], required=True)
    parser.add_argument("--reasoning-tier", required=True)
    parser.add_argument("--tier-source", required=True, help="HTTPS documentation of highest available tier")
    parser.add_argument("--generation", required=True, type=generation_json, help="Native generation JSON including output cap and reasoning control")
    parser.add_argument("--attempts", type=int, choices=[3], default=3)
    parser.add_argument("--handle", required=True)
    parser.add_argument("--out", required=True, type=Path, help="New submission bundle directory")
    parser.add_argument("--work", required=True, type=Path, help="New private working directory, never commit")
    parser.add_argument("--agent-image", default="keygen-ft2-benchmark:local")
    parser.add_argument("--visualizer-image", default="keygen-ft2-visualizer:local")
    return parser


def validate_inputs(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", args.handle):
        raise ValueError("Use a GitHub handle without personal information")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", args.model):
        raise ValueError("Declare an exact upstream model identifier")
    try:
        public_documentation_url(args.tier_source)
    except ValueError:
        raise ValueError("Use a public HTTPS tier-documentation URL without credentials, queries or custom ports") from None
    validate_url(args.base_url, args.provider, args.api)
    if args.api not in PROTOCOLS[args.provider]:
        raise ValueError("Protocol is not supported by this route")
    bridge_sha256 = None
    bridge_provenance = None
    if args.provider in BRIDGE_PROVIDERS:
        if (args.bridge_binary is None or not args.bridge_binary.is_file()
                or not os.access(args.bridge_binary, os.X_OK)):
            raise ValueError("OAuth requires --bridge-binary for your own authorized executable bridge")
        bridge_sha256 = sha(args.bridge_binary)
        bridge_provenance = {"implementation": "user-provided authorized executable",
                             "version": "unknown", "executable_sha256": bridge_sha256}
    elif args.bridge_binary is not None:
        raise ValueError("--bridge-binary is only for OAuth routes")
    model = {"id": "community-model", "model": args.model, "response_model": args.model,
             "provider": args.provider, "base_url": args.base_url, "api": args.api,
             "api_key_env": "KEYGEN_CONTRIB_API_KEY", "generation": args.generation,
             "backend_provenance": {"service_revision": None, "bridge": bridge_provenance}}
    tier_spec = {"source": args.tier_source, "level": args.reasoning_tier, "generation": args.generation}
    model["tier"] = {"level": args.reasoning_tier, "reasoning": declared_reasoning(model),
                     "spec_sha256": campaign.digest(tier_spec)}
    check_tier(model)
    return model, bridge_sha256


def frozen_configuration():
    return {"limits": dict(LIMITS), "native": contract()["native"],
            "prompts": campaign.prompt_manifest(LIMITS), "transport": {"backend": "local"},
            "concurrency": {"workers": 1, "render": 1, "video": 1, "key_pools": {},
                            "providers": {provider: 1 for provider in PROVIDERS}},
            "storage": {"reserve_bytes": 1024**3, "peak_bytes_per_attempt": 2 * 1024**3},
            "max_attempts": 3, "policies": {"attempt_selection": campaign.INDEPENDENT}}


def readiness_spec(config, model, agent_image):
    """Build the same-route, same-settings input for the native qualification pilot."""
    fields = ("id", "model", "response_model", "provider", "api", "base_url", "api_key_env",
              "generation", "tier", "backend_provenance")
    return {"model": {key: model[key] for key in fields},
            "config": {"native": config["native"]}, "image": agent_image,
            "limits": dict(native_readiness.DEFAULT_LIMITS)}


def qualify_model(work, config, model, agent_image, bridge_executable=None):
    """Record a real readiness proof before allowing a community attempt."""
    spec_path = work / "native-readiness-spec.json"
    write_json(spec_path, readiness_spec(config, model, agent_image))
    readiness = native_readiness.qualify(spec_path, work / "native-readiness", bridge_executable)
    if readiness["status"] != "verified":
        raise ValueError("Native readiness pilot did not verify; no benchmark attempt started. Inspect private readiness evidence")
    model["readiness"] = readiness
    return readiness


def inspect_images(docker, agent_image, visualizer_image):
    images, image_details = {}, {}
    base_name = contract()["base_image"]
    try:
        base = json.loads(run.shell(docker + ["image", "inspect", base_name]).stdout)[0]
    except subprocess.CalledProcessError as exc:
        if b"no such image" in (exc.stderr or b"").lower():
            raise ValueError(f"Pinned Debian base image is missing; ancestry cannot be verified. Run: docker pull {base_name}") from None
        raise ValueError("Docker could not inspect the pinned Debian base; check local daemon access") from None
    base_layers = base["RootFS"]["Layers"]
    for key, name in (("agent", agent_image), ("visualizer", visualizer_image)):
        try:
            details = json.loads(run.shell(docker + ["image", "inspect", name]).stdout)[0]
        except subprocess.CalledProcessError as exc:
            if b"no such image" in (exc.stderr or b"").lower():
                raise ValueError(f"Configured {key} image is missing. Run setup or build its target from benchmark/Dockerfile") from None
            raise ValueError(f"Docker could not inspect the configured {key} image; check local daemon access") from None
        if details["RootFS"]["Layers"][:len(base_layers)] != base_layers:
            raise ValueError(f"Configured {key} image does not descend from the pinned Debian base. Rebuild its target from benchmark/Dockerfile")
        images[key] = details["Id"]
        image_details[key] = {"architecture": details["Architecture"],
                              "os": details["Os"], "layers": details["RootFS"]["Layers"]}
    return images, image_details, base_layers


def prepare_run(args, *, require_key=True):
    model, bridge_sha256 = validate_inputs(args)
    try:
        if importlib.metadata.version("mini-swe-agent") != "2.4.6":
            raise ValueError("Install benchmark/requirements.txt in a fresh virtual environment")
    except importlib.metadata.PackageNotFoundError:
        raise ValueError("Install benchmark/requirements.txt in a fresh virtual environment") from None
    if require_key and not os.environ.get("KEYGEN_CONTRIB_API_KEY"):
        raise ValueError("Set KEYGEN_CONTRIB_API_KEY in the controller environment")
    config = frozen_configuration()
    model["effective_settings"] = campaign.normalize_native(config, [model])[0]
    from score_playback import renderer_identity
    renderer_identity()  # Never spend if trusted scoring cannot run.
    docker = run.docker_command()
    images, image_details, base_layers = inspect_images(docker, args.agent_image, args.visualizer_image)
    config.update(image=images["agent"], visualizer_image=images["visualizer"])
    environment = {"contract": contract(), "images": images, "image_details": image_details,
                   "base_layers": base_layers, "model": public_model(model, bridge_sha256),
                   "tier_source": args.tier_source, "handle": args.handle,
                   "runtime": {"system": platform.system(), "architecture": platform.machine(),
                               "python": platform.python_version(),
                               "docker": run.shell(docker + ["version", "--format", "{{.Server.Version}}"]).stdout.decode().strip()},
                   "packages": [[name, importlib.metadata.version(name)] for name in required_packages()]}
    return config, model, docker, images, environment


def private_work_path(path):
    if not path.is_absolute():
        raise ValueError("Use an absolute private work directory outside the checkout")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Private work directories must not contain symlinks")
    resolved = run.artifact_root(path)
    if HERE.parent == resolved or HERE.parent in resolved.parents:
        raise ValueError("Keep private work outside the checkout")
    return resolved


def execute(args):
    output, work = args.out.resolve(), private_work_path(args.work)
    if output == work or output.exists() or work.exists() or output in work.parents or work in output.parents:
        raise ValueError("Use separate new bundle and private work directories")
    if any(parent.is_symlink() for parent in (args.out, *args.out.parents)):
        raise ValueError("Bundle directories must not contain symlinks")
    config, model, docker, images, environment = prepare_run(args)
    work.mkdir(parents=True, mode=0o700)
    os.chmod(work, 0o700)
    store = ArtifactStore(config["storage"])
    store.preflight(work, len(ATTEMPTS))
    qualify_model(work, config, model, images["agent"], args.bridge_binary)
    write_json(work / "community-config.json", {"config": config, "environment": environment,
                                                 "readiness": model["readiness"]})
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    # Reserve every slot before inference. No best-of selection or retry path.
    for ordinal, attempt in enumerate(ATTEMPTS, 1):
        run.reserve(work, model, ordinal, attempt)
    for ordinal, attempt in enumerate(ATTEMPTS, 1):
        print(f"Running {attempt} of 3", flush=True)
        started = time.time()
        try:
            run.run_one(work, config, model, docker, images["agent"], images["visualizer"], ordinal, attempt, store)
        except Exception:
            # Keep early infrastructure/finalization failures and continue the declared slots.
            status_path = work / attempt / "status.json"
            status = json.loads(status_path.read_text())
            status.setdefault("started_at", started)
            status.setdefault("finished_at", time.time())
            status.setdefault("wall_seconds", status["finished_at"] - status["started_at"])
            status.setdefault("totals", {})
            if "prompt_tokens" not in status["totals"]:
                status["totals"] = run.summarize(work / attempt, model)
            write_json(status_path, status)
    for attempt in ATTEMPTS:
        source, target = work / attempt, output / attempt
        target.mkdir()
        status = json.loads((source / "status.json").read_text())
        tune = source / "submission/tune.xm"
        status["tune_present"] = tune.is_file()
        if status["tune_present"]:
            shutil.copyfile(tune, target / "tune.xm")
        status["model"] = environment["model"]
        write_json(target / "status.json", public_status(status))
        write_json(target / "environment.json", environment)
        # Keep messages intact, but never export the agent's controller configuration.
        trajectory_path = source / "trajectory.json"
        trajectory = ({"messages": json.loads(trajectory_path.read_text())["messages"]}
                      if trajectory_path.exists()
                      else {"messages": [], "evidence_unavailable": True})
        write_json(target / "trajectory.json", trajectory)
        if (source / "transport.jsonl").exists():
            shutil.copyfile(source / "transport.jsonl", target / "transport.jsonl")
        else:
            (target / "transport.jsonl").write_text("")
    seal(output, {"schema": "keygen-community-1", "attempts": ATTEMPTS, "environment": environment})
    validate(output)
    print(f"Bundle ready: {output}. Keep {work} private.")


def main(argv=None):
    parser = argument_parser()
    args = parser.parse_args(argv)
    try:
        execute(args)
    except KeyboardInterrupt:
        print("Interrupted. Keep the private work and report the interruption before spending again.", file=sys.stderr)
        return 130
    except Exception as exc:
        # Provider/controller exceptions can include credentials or response bodies.
        message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        secret = os.environ.get("KEYGEN_CONTRIB_API_KEY")
        if secret:
            message = message.replace(secret, "[redacted]")
        print(f"error: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
