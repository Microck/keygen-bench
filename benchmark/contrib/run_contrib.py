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
import time

from validate_bundle import (ATTEMPTS, BRIDGE_PROVIDERS, LIMITS, contract,
                             public_documentation_url, public_model, public_status,
                             required_packages, seal, sha, validate, write_json)

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import campaign
import run
from artifacts import ArtifactStore
from native_models import PROVIDERS, PROTOCOLS, declared_reasoning, check_tier, validate_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Exact upstream model identifier")
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--bridge-binary", type=Path, help="OAuth bridge executable; only its SHA-256 is published")
    parser.add_argument("--api", choices=["chat", "responses", "messages"], required=True)
    parser.add_argument("--reasoning-tier", required=True)
    parser.add_argument("--tier-source", required=True, help="HTTPS documentation of highest available tier")
    parser.add_argument("--generation", required=True, type=json.loads, help="Native generation JSON including output cap and reasoning control")
    parser.add_argument("--attempts", type=int, choices=[3], default=3)
    parser.add_argument("--handle", required=True)
    parser.add_argument("--out", required=True, type=Path, help="New submission bundle directory")
    parser.add_argument("--work", required=True, type=Path, help="New private working directory, never commit")
    parser.add_argument("--agent-image", default="keygen-ft2-benchmark:local")
    parser.add_argument("--visualizer-image", default="keygen-ft2-visualizer:local")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", args.handle):
        parser.error("Use a GitHub handle without personal information")
    try:
        public_documentation_url(args.tier_source)
    except ValueError as exc:
        parser.error(str(exc))
    validate_url(args.base_url, args.provider, args.api)
    if args.api not in PROTOCOLS[args.provider]:
        parser.error("Protocol is not supported by this route")
    bridge_sha256 = None
    if args.provider in BRIDGE_PROVIDERS:
        if args.bridge_binary is None or not args.bridge_binary.is_file():
            parser.error("OAuth routes require --bridge-binary pointing to the bridge executable")
        bridge_sha256 = sha(args.bridge_binary)
    elif args.bridge_binary is not None:
        parser.error("--bridge-binary is only for OAuth routes")
    try:
        if importlib.metadata.version("mini-swe-agent") != "2.4.6":
            parser.error("Install benchmark/requirements.txt in a fresh virtual environment")
    except importlib.metadata.PackageNotFoundError:
        parser.error("Install benchmark/requirements.txt in a fresh virtual environment")
    if not os.environ.get("KEYGEN_CONTRIB_API_KEY"):
        parser.error("Set KEYGEN_CONTRIB_API_KEY in the controller environment")
    output, work = args.out.resolve(), args.work.resolve()
    if output == work or output.exists() or work.exists() or output in work.parents or work in output.parents:
        parser.error("Use separate new bundle and private work directories")
    model = {"id": "community-model", "model": args.model, "response_model": args.model,
             "provider": args.provider, "base_url": args.base_url, "api": args.api,
             "api_key_env": "KEYGEN_CONTRIB_API_KEY", "generation": args.generation}
    tier_spec = {"source": args.tier_source, "level": args.reasoning_tier, "generation": args.generation}
    model["tier"] = {"level": args.reasoning_tier, "reasoning": declared_reasoning(model),
                     "spec_sha256": campaign.digest(tier_spec)}
    check_tier(model)
    from score_playback import renderer_identity
    renderer_identity()  # Do not spend on inference if trusted scoring cannot run.
    docker = run.docker_command()
    images = {}
    image_details = {}
    base = json.loads(run.shell(docker + ["image", "inspect", contract()["base_image"]]).stdout)[0]
    base_layers = base["RootFS"]["Layers"]
    for key, name in (("agent", args.agent_image), ("visualizer", args.visualizer_image)):
        details = json.loads(run.shell(docker + ["image", "inspect", name]).stdout)[0]
        if details["RootFS"]["Layers"][:len(base_layers)] != base_layers:
            parser.error("Build images from the pinned Debian base in benchmark/Dockerfile")
        images[key] = details["Id"]
        image_details[key] = {"architecture": details["Architecture"],
                              "os": details["Os"], "layers": details["RootFS"]["Layers"]}
    config = {"limits": dict(LIMITS), "native": contract()["native"],
              "prompts": campaign.prompt_manifest(LIMITS), "transport": {"backend": "local"},
              "concurrency": {"workers": 1, "render": 1, "video": 1, "key_pools": {},
                              "providers": {provider: 1 for provider in PROVIDERS}},
              "storage": {"reserve_bytes": 1024**3, "peak_bytes_per_attempt": 2 * 1024**3}}
    model["effective_settings"] = campaign.normalize_native(config, [model])[0]
    config.update(image=images["agent"], visualizer_image=images["visualizer"],
                  max_attempts=3, policies={"attempt_selection": campaign.INDEPENDENT})
    environment = {"contract": contract(), "images": images, "image_details": image_details,
                   "base_layers": base_layers,
                   "model": public_model(model, bridge_sha256),
                   "tier_source": args.tier_source, "handle": args.handle,
                   "runtime": {"system": platform.system(), "architecture": platform.machine(),
                               "python": platform.python_version(),
                               "docker": run.shell(docker + ["version", "--format", "{{.Server.Version}}"]).stdout.decode().strip()},
                   "packages": [[name, importlib.metadata.version(name)] for name in required_packages()]}
    work.mkdir(parents=True, mode=0o700)
    output.mkdir(parents=True, mode=0o700)
    write_json(work / "community-config.json", {"config": config, "environment": environment})
    store = ArtifactStore(config["storage"])
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


if __name__ == "__main__":
    main()
