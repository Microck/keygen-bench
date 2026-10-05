#!/usr/bin/env python3
"""Validate untrusted community bundles without credentials or model requests."""
import argparse
import hashlib
import json
import ipaddress
import math
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import campaign

LIMITS = {"steps": 0, "wall_seconds": 7200, "request_seconds": 3600,
          "command_seconds": 120, "render_seconds": 300, "video_seconds": 600,
          "artifact_bytes": 128 * 1024**2}
ATTEMPTS = ["attempt-1", "attempt-2", "attempt-3"]
DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
# Scan binary artifacts too: sample names can carry secrets. Chunk overlap catches splits.
SECRET = re.compile(rb"(?:(?:sk-|oc_sk_)[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|(?:authorization|x-api-key)\s*[\"']?\s*[:=]|(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[\"']?\s*[:=]\s*[\"']?(?!\[REDACTED\])[A-Za-z0-9_/-]{12,}|(?:OPENAI|ANTHROPIC|AWS|KEYGEN|OPENCODE)[A-Z0-9_]*(?:KEY|TOKEN|SECRET)\s*[\"']?\s*[:=]|(?:declare -x |os\.environ|printenv|env dump|[\"'](?:PATH|HOME|USER)[\"']\s*:))", re.I)
PRIVATE = re.compile(rb"""(?:/(?:home|Users)/[^/\s"'\\]+|[A-Z]:\\+(?:Users|Documents and Settings)\\+|["'](?:hostname|username|user_name|home_directory|repo_digests)["']\s*:)""", re.I)
BRIDGE_PROVIDERS = frozenset({"codex_oauth", "anthropic_oauth"})
MODEL_FIELDS = frozenset({"id", "model", "response_model", "provider", "api", "base_url",
                          "api_key_env", "generation", "tier", "bridge"})
STATUS_FIELDS = frozenset({"status", "attempt_id", "repetition", "model", "started_at",
                           "finished_at", "wall_seconds", "totals", "eligible",
                           "failure_category", "model_failure", "tune_present"})


def public_documentation_url(value):
    """Reject credentials, local hosts and query strings in published tier evidence."""
    url = urlsplit(value)
    host = url.hostname or ""
    if (url.scheme != "https" or url.username or url.password or url.port
            or url.query or url.fragment or "." not in host
            or host.endswith((".local", ".internal", ".localhost", ".test", ".invalid"))
            or host == "localhost"):
        raise ValueError("Use a public HTTPS documentation URL without credentials or query parameters")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return value
    raise ValueError("Documentation URL must use a public hostname, not an IP address")


def required_packages():
    return sorted(re.findall(r"^([A-Za-z0-9_.-]+)==", (HERE / "requirements.txt").read_text(), re.M))

def public_model(model, bridge_sha256=None):
    result = {key: value for key, value in model.items() if key in MODEL_FIELDS}
    if model["provider"] in BRIDGE_PROVIDERS:
        result.pop("base_url", None)
        result["bridge"] = {"transport": "loopback-http", "binary_sha256": bridge_sha256}
    else:
        from native_models import validate_url
        result["base_url"] = validate_url(model["base_url"], model["provider"], model["api"])
    return result



def public_status(status):
    result = {key: value for key, value in status.items() if key in STATUS_FIELDS}
    result["model"] = {key: value for key, value in status["model"].items() if key in MODEL_FIELDS}
    return result


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def pins():
    base = re.search(r"ARG BASE_IMAGE=(\S+)", (HERE / "Dockerfile").read_text())[1]
    commit = re.search(r"^pin=([a-f0-9]{40})$", (HERE.parent / "scripts/build-ft2-linux.sh").read_text(), re.M)[1]
    return {"base_image": base, "ft2_commit": commit}


def contract():
    if campaign.PROMPT_VERSION != "prompt-v2":
        raise ValueError("Community contract requires prompt-v2")
    return {**pins(), "harness_version": "2.4.6", "prompt": campaign.prompt_manifest(LIMITS),
            "limits": LIMITS, "submission_files": 4096, "render": {"rate": 44100, "bits": 16},
            "scorer": "craft-v7", "native": {"timeout_seconds": 3600, "retries": 2},
            "attempt_selection": "independent_repetitions",
            "sources": campaign.source_provenance(),
            "requirements_sha256": sha(HERE / "requirements.txt"),
            "build_script_sha256": sha(HERE.parent / "scripts/build-ft2-linux.sh")}


def inventory(root):
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Links and special files are forbidden")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path
    return files


def seal(root, metadata):
    write_json(root / "manifest.json", {**metadata, "files": {
        name: sha(path) for name, path in inventory(root).items() if name != "manifest.json"}})


def validate(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Bundle must be a regular directory")
    files = inventory(root)
    if len(files) > 4096 or sum(p.stat().st_size for p in files.values()) > 512 * 1024**2:
        raise ValueError("Bundle exceeds 4096 files or 512 MiB")
    for name, path in files.items():
        maximum = LIMITS["artifact_bytes"] if name.endswith("/tune.xm") else 16 * 1024**2
        if path.stat().st_size > maximum:
            raise ValueError("File exceeds its size limit")
        with path.open("rb") as stream:
            tail = b""
            while chunk := stream.read(65536):
                if SECRET.search(tail + chunk):
                    raise ValueError("Secret or environment dump detected; content withheld")
                if PRIVATE.search(tail + chunk):
                    raise ValueError("Private host metadata or home path detected; content withheld")
                tail = (tail + chunk)[-4096:]
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema") != "keygen-community-1" or manifest.get("attempts") != ATTEMPTS:
        raise ValueError("Declare exactly all three independent attempts")
    expected = {name: sha(path) for name, path in files.items() if name != "manifest.json"}
    if manifest.get("files") != expected:
        raise ValueError("File inventory or SHA-256 mismatch")
    environment = manifest["environment"]
    if set(manifest) != {"schema", "attempts", "environment", "files"}:
        raise ValueError("Unexpected manifest fields")
    if set(environment) != {"contract", "images", "image_details", "base_layers", "model",
                            "tier_source", "handle", "runtime", "packages"}:
        raise ValueError("Unexpected environment fields")
    if environment["contract"] != contract():
        raise ValueError("Frozen prompt, pins or limits mismatch")
    base_layers = environment["base_layers"]
    if set(environment["images"]) != {"agent", "visualizer"} or set(environment["image_details"]) != {"agent", "visualizer"}:
        raise ValueError("Unexpected image metadata")
    if not isinstance(base_layers, list) or not base_layers or any(not DIGEST.fullmatch(x) for x in base_layers):
        raise ValueError("Pinned base layer evidence required")
    for key in ("agent", "visualizer"):
        if not DIGEST.fullmatch(environment["images"][key]):
            raise ValueError("Immutable built image ID required")
        details = environment["image_details"][key]
        if set(details) != {"architecture", "os", "layers"}:
            raise ValueError("Unexpected image details")
        if (details["layers"][:len(base_layers)] != base_layers or details["os"] != "linux"
                or not details["architecture"]
                or any(not DIGEST.fullmatch(x) for x in details["layers"])):
            raise ValueError("Image does not declare the pinned base layers")
    model = environment["model"]
    from native_models import check_tier, validate_url, PROVIDERS, PROTOCOLS
    bridge = model["provider"] in BRIDGE_PROVIDERS
    fields = MODEL_FIELDS - ({"base_url"} if bridge else {"bridge"})
    if set(model) != fields or model["provider"] not in PROVIDERS:
        raise ValueError("Declared provider provenance and model fields required")
    if (model.get("api_key_env") != "KEYGEN_CONTRIB_API_KEY"
            or not isinstance(model.get("model"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", model["model"])
            or model.get("model") != model.get("response_model")):
        raise ValueError("Exact model identity and controller credential name required")
    if bridge:
        if (set(model["bridge"]) != {"transport", "binary_sha256"}
                or model["bridge"]["transport"] != "loopback-http"
                or not isinstance(model["bridge"]["binary_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", model["bridge"]["binary_sha256"])):
            raise ValueError("OAuth bridge transport and binary digest required")
    else:
        validate_url(model["base_url"], model["provider"], model["api"])
    if model["api"] not in PROTOCOLS[model["provider"]]:
        raise ValueError("Unsupported protocol")
    check_tier(model)
    public_documentation_url(environment["tier_source"])
    runtime = environment["runtime"]
    package_names = required_packages()
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", environment["handle"])
            or set(runtime) != {"system", "architecture", "python", "docker"}
            or any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,80}", value)
                   for value in runtime.values())
            or any(not isinstance(package, list) or len(package) != 2
                   or package[0] not in package_names
                   or not isinstance(package[1], str)
                   or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,80}", package[1])
                   for package in environment["packages"])
            or len({package[0] for package in environment["packages"]}) != len(environment["packages"])
            or ["mini-swe-agent", "2.4.6"] not in environment["packages"]):
        raise ValueError("Public handle, runtime versions and benchmark package versions required")
    if campaign.digest({"source": environment["tier_source"], "level": model["tier"]["level"],
                        "generation": model["generation"]}) != model["tier"]["spec_sha256"]:
        raise ValueError("Tier evidence digest mismatch")
    allowed = {"manifest.json"}
    for ordinal, attempt in enumerate(ATTEMPTS, 1):
        for filename in ("status.json", "environment.json", "trajectory.json", "transport.jsonl"):
            name = f"{attempt}/{filename}"
            if name not in files:
                raise ValueError("Missing attempt evidence")
            allowed.add(name)
        directory = root / attempt
        if json.loads((directory / "environment.json").read_text()) != environment:
            raise ValueError("Attempt environment differs")
        status = json.loads((directory / "status.json").read_text())
        if set(status) - STATUS_FIELDS:
            raise ValueError("Unexpected status fields")
        if status["attempt_id"] != attempt or status["repetition"] != ordinal or status["model"] != model:
            raise ValueError("Attempt identity differs")
        final_states = {"RENDERED_UNSCORED", "MODEL_FAILED", "INFRA_ERROR", "INTERRUPTED",
                        "EVALUATION_ERROR", "FINALIZATION_ERROR", "IDENTITY_MISMATCH",
                        "SETTINGS_MISMATCH", "IDENTITY_UNVERIFIED", "PROTOCOL_ERROR",
                        "QUOTA_ERROR", "AUTH_ERROR", "CONTENT_FILTER_ERROR", "TRANSPORT_ERROR"}
        if status["status"] not in final_states:
            raise ValueError("Attempt is not final")
        for field in ("started_at", "finished_at", "wall_seconds"):
            if type(status[field]) not in (int, float) or not math.isfinite(status[field]) or status[field] < 0:
                raise ValueError("Invalid timing")
        if (status["finished_at"] < status["started_at"]
                or not math.isclose(status["finished_at"] - status["started_at"],
                                    status["wall_seconds"], abs_tol=0.01)):
            raise ValueError("Finish precedes start")
        for field in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "usage_unknown"):
            if type(status["totals"][field]) is not int or status["totals"][field] < 0:
                raise ValueError("Missing or invalid usage totals")
        if (type(status["totals"].get("requests")) is not int or status["totals"]["requests"] < 0
                or any(type(value) not in (bool, int, float) or not math.isfinite(value) or value < 0
                       for key, value in status["totals"].items()
                       if not (key == "model_seconds" and value is None))):
            raise ValueError("Usage totals must contain nonnegative counts, timings or flags")
        trajectory = json.loads((directory / "trajectory.json").read_text())
        if set(trajectory) - {"messages", "evidence_unavailable"}:
            raise ValueError("Trajectory must not include controller configuration")
        if not isinstance(trajectory.get("messages"), list):
            raise ValueError("Trajectory messages required")
        if trajectory.get("evidence_unavailable") and (status["totals"].get("requests", 0)
                                                       or not status.get("failure_category")):
            raise ValueError("Missing trajectory allowed only for a pre-request failure")
        records = [json.loads(line) for line in (directory / "transport.jsonl").read_text().splitlines()]
        if any(not isinstance(record, dict) for record in records):
            raise ValueError("Transport records must be objects")
        if trajectory.get("evidence_unavailable") and (trajectory["messages"] or records):
            raise ValueError("Unavailable trajectory contradicts recorded evidence")
        if status["totals"]["requests"] and not trajectory["messages"]:
            raise ValueError("Requested attempts must retain their trajectory")
        if type(status.get("eligible")) is not bool:
            raise ValueError("Explicit eligibility required")
        if status.get("eligible"):
            if status["status"] != "RENDERED_UNSCORED" or status.get("failure_category"):
                raise ValueError("Failed attempts cannot be eligible")
            from native_models import transmitted_reasoning
            sent = [record for record in records if record.get("event") == "request"]
            required = transmitted_reasoning(model)
            if (not trajectory["messages"] or not sent
                    or any(any(record.get("settings", {}).get(key) != value
                               for key, value in required.items()) for record in sent)):
                raise ValueError("Eligible attempt requires trajectory and transmitted tier evidence")
        tune = f"{attempt}/tune.xm"
        if type(status.get("tune_present")) is not bool or status["tune_present"] != (tune in files):
            raise ValueError("Module presence must be explicit")
        if tune in files:
            allowed.add(tune)
            with files[tune].open("rb") as stream:
                if status["eligible"] and stream.read(17) != b"Extended Module: ":
                    raise ValueError("Invalid XM signature")
        elif status.get("eligible") or not status.get("failure_category"):
            raise ValueError("Missing module requires a recorded failure")
    if set(files) != allowed:
        raise ValueError("Unexpected bundle files")
    return manifest


def rescore(root, trusted_image, output):
    """Use a maintainer-selected image, never execute a contributor-selected image."""
    import run
    import score
    from score_playback import renderer_identity
    renderer_identity()  # Fail before rendering if the trusted analysis build is missing.
    docker = run.docker_command()
    image = json.loads(run.shell(docker + ["image", "inspect", trusted_image]).stdout)[0]["Id"]
    output = output.resolve()
    if output == root.resolve() or root.resolve() in output.parents:
        raise ValueError("Rescore output must be outside the sealed bundle")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "verification.json", {"bundle_sha256": sha(root / "manifest.json"),
               "trusted_agent_image": image, "contract": contract()})
    for attempt in ATTEMPTS:
        source = root / attempt
        target = output / attempt
        (target / "submission").mkdir(parents=True)
        shutil.copyfile(source / "trajectory.json", target / "trajectory.json")
        status = json.loads((source / "status.json").read_text())
        if (source / "tune.xm").exists():
            shutil.copyfile(source / "tune.xm", target / "submission/tune.xm")
            try:
                status["audio"] = run.render(docker, image, target, {"limits": LIMITS})
                status["module"] = run.module_facts(target)
            except ValueError:
                # Preserve invalid artifacts as failed outcomes, then evaluate later slots.
                status.update(status="MODEL_FAILED", eligible=False, render="invalid",
                              failure_category=status.get("failure_category") or "MODEL")
        write_json(target / "status.json", status)
        profile = score.profile_attempt(target, force=True)
        if (profile.get("evaluation_error") or {}).get("category") == "EVAL":
            raise ValueError("Trusted scoring failed; inspect rescore output")
        print(json.dumps(profile))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", type=Path, nargs="+")
    parser.add_argument("--rescore", action="store_true")
    parser.add_argument("--trusted-agent-image", help="Maintainer-built image required for rescore")
    parser.add_argument("--rescore-out", type=Path, help="New directory for trusted evaluation")
    args = parser.parse_args()
    if args.rescore and (len(args.bundles) != 1 or not args.trusted_agent_image or not args.rescore_out):
        parser.error("Rescore requires one bundle, --trusted-agent-image and --rescore-out")
    if not args.rescore and (args.trusted_agent_image or args.rescore_out):
        parser.error("Trusted evaluation options require --rescore")
    try:
        for root in args.bundles:
            validate(root)
            if args.rescore:
                rescore(root, args.trusted_agent_image, args.rescore_out)
            print(f"Valid community bundle: {root}")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Bundle rejected ({type(exc).__name__}); check format and secret scan locally.\n")


if __name__ == "__main__":
    main()
