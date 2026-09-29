#!/usr/bin/env python3
"""Run a roster selection as one campaign per thinking tier, then tabulate every attempt.

    python -I benchmark/drive.py plan --selection benchmark/config/selection.local.json --out benchmark/runs/official
    python -I benchmark/drive.py run  --selection ... --out ...      # plan, then run every campaign in order
    python -I benchmark/drive.py summary --out benchmark/runs/official

`generation` is campaign-wide, so each tier value becomes its own campaign file and output
directory. Tiers that are not a reasoning_effort value (default, thinking, thinking-on) run with
no parameter. A failed attempt never stops the driver; it lands in status.json like any other.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
NO_PARAM = {"default", "thinking", "thinking-on"}
VERCEL_LINK = Path("/home/ubuntu/cliproxyapi-keygen/vercel-link")  # a `vercel link`ed dir for `vercel env pull`
SERVICE = "cliproxyapi-keygen.service"


def plan(selection: Path, base: Path, out: Path) -> list[tuple[str, Path]]:
    """Write campaign-<tier>.local.json beside the base campaign; returns (tier, campaign path) pairs."""
    rows = json.loads(selection.read_text(encoding="utf-8"))
    campaign = json.loads(base.read_text(encoding="utf-8"))
    campaigns = []
    for tier in sorted({r["tier"] for r in rows}):
        models = [{"id": r["model"].replace("/", "-"), "model": r["model"], "response_model": r["response_model"]}
                  for r in rows if r["tier"] == tier]
        generation = {k: v for k, v in campaign["generation"].items() if k != "reasoning_effort"}
        if tier not in NO_PARAM:
            generation["reasoning_effort"] = tier
        path = base.with_name(f"campaign-{tier}.local.json")
        path.write_text(json.dumps({**campaign, "generation": generation, "models": models}, indent=2) + "\n", encoding="utf-8")
        campaigns.append((tier, path))
    return campaigns


def vercel_token_hours_left(config_path: Path) -> float | None:
    """Hours until the Vercel OIDC token in the proxy config expires, or None when no Vercel route exists."""
    import yaml
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    provider = next((p for p in config.get("openai-compatibility", []) if p["name"] == "vercel-ai-gateway"), None)
    if not provider:
        return None
    token = provider["api-key-entries"][0]["api-key"]
    claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
    return (claims["exp"] - time.time()) / 3600


def refresh_vercel_token(config_path: Path) -> None:
    """Pull a fresh OIDC token, write it into the proxy config, restart the proxy, wait for it."""
    import yaml
    subprocess.run(["vercel", "env", "pull", "--yes", ".env.pulled"], cwd=VERCEL_LINK, check=True, capture_output=True, timeout=120)
    token = next(line.split("=", 1)[1].strip().strip('"') for line in (VERCEL_LINK / ".env.pulled").read_text().splitlines()
                 if line.startswith("VERCEL_OIDC_TOKEN="))
    text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(text)
    provider = next(p for p in config["openai-compatibility"] if p["name"] == "vercel-ai-gateway")
    provider["api-key-entries"] = [{"api-key": token}]
    header = "".join(line + "\n" for line in text.splitlines() if line.startswith("#"))
    with open(os.open(config_path, os.O_WRONLY | os.O_TRUNC, 0o600), "w", encoding="utf-8") as handle:
        handle.write(header + yaml.safe_dump(config, sort_keys=False, default_flow_style=False))
    subprocess.run(["sudo", "systemctl", "restart", SERVICE], check=True, timeout=60)
    time.sleep(8)


def run(selection: Path, base: Path, out: Path) -> None:
    config_path = (base.parent / json.loads(base.read_text())["proxy_config"]).resolve()
    for tier, campaign in plan(selection, base, out):
        hours = vercel_token_hours_left(config_path)
        if hours is not None and hours < 6:
            print(f"Vercel token has {hours:.1f} h left; refreshing", flush=True)
            refresh_vercel_token(config_path)
        print(f"== campaign {tier}: {campaign.name}", flush=True)
        with (out / f"{tier}.log").open("ab") as log:
            subprocess.run([sys.executable, "-I", str(HERE / "run.py"), "run", "--campaign", str(campaign), "--out", str(out / tier)],
                           stdout=log, stderr=subprocess.STDOUT)
    summary(out)


def summary(out: Path) -> None:
    """results.json and results.md across every <tier>/<model>/status.json under out."""
    rows = []
    for status_path in sorted(out.glob("*/*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        audio, totals = status.get("audio") or {}, status.get("totals") or {}
        rows.append({"tier": status_path.parent.parent.name, "model": status["model"]["model"], "status": status["status"],
                     "duration_s": round(audio.get("duration_seconds", 0), 1), "peak": round(audio.get("peak", 0), 3),
                     "rms": round(audio.get("rms", 0), 3), "requests": totals.get("requests", 0),
                     "prompt_tokens": totals.get("prompt_tokens", 0), "completion_tokens": totals.get("completion_tokens", 0),
                     "reasoning_tokens": totals.get("reasoning_tokens", 0), "wall_s": round(status.get("wall_seconds", 0)),
                     "video": bool((status.get("video") or {}).get("sha256")), "error": status.get("error") or ""})
    (out / "results.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    keys = ["tier", "model", "status", "duration_s", "peak", "rms", "requests", "prompt_tokens", "completion_tokens", "reasoning_tokens", "wall_s", "video", "error"]
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    lines += ["| " + " | ".join(str(r[k]) for k in keys) + " |" for r in rows]
    (out / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} attempts summarized in {out / 'results.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "run", "summary"])
    parser.add_argument("--selection", type=Path, default=HERE / "config/selection.local.json")
    parser.add_argument("--campaign", type=Path, default=HERE / "config/campaign.local.json", help="base campaign whose models are replaced per tier")
    parser.add_argument("--out", type=Path, default=HERE / "runs/official")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.command == "plan":
        for tier, path in plan(args.selection.resolve(), args.campaign.resolve(), args.out.resolve()):
            print(f"{tier:12} {path.name}: {len(json.loads(path.read_text())['models'])} models")
    elif args.command == "run":
        run(args.selection.resolve(), args.campaign.resolve(), args.out.resolve())
    else:
        summary(args.out.resolve())


if __name__ == "__main__":
    main()
