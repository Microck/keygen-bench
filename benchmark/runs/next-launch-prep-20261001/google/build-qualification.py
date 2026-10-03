#!/usr/bin/env python3
"""Write the Google AI Studio tier spec, readiness pilot specs and qualification plan (no credentials).

Six Gemini models at Google's top thinkingLevel ("high"; Gemini 3.x has no higher level) with the
documented 65,536-token output cap. Readiness mirrors the Ashburn OAuth requalification: same Boat
image, 5 steps, 1,800 s, native timeout 3,600 s and 2 transport retries.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASHBURN = "/home/ubuntu/keygen-full.OGHjBAkO"
ROOT = ASHBURN + "/google-20261003"
IMAGE = "sha256:c0837265585378b1b4ca4fc96a2a0c4d8c3249f8e3376f6ff4efa6c37560a59e"
BASE = "https://generativelanguage.googleapis.com/v1beta"
# inventory id -> Google API model id (also the returned modelVersion, checked live 2026-10-03)
MODELS = {"gemini-3-flash": "gemini-3-flash-preview", "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
          "gemini-3.5-flash": "gemini-3.5-flash", "gemini-3.6-flash": "gemini-3.6-flash",
          "gemini-3.7-flash": "gemini-3.7-flash", "gemini-3.8-flash": "gemini-3.8-flash"}
REASONING = {"reasoning_effort": "high"}
OUTPUT_CAP = 65536


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    spec = {"schema": "keygen-tier-spec-1", "scope": "Google AI Studio native routes, 2026-10-03",
            "tier_semantics": "Gemini 3.x thinkingLevel: minimal/low/medium/high; high is the top level",
            "entries": [{"identity": inventory, "model": api, "response_model": api, "provider": "google",
                         "api": "chat", "base_url": BASE, "tier": "high", "reasoning": REASONING,
                         "generation": {"max_tokens": OUTPUT_CAP, **REASONING},
                         "limits": {"model_max_output_tokens": OUTPUT_CAP, "run_output_cap": OUTPUT_CAP}}
                        for inventory, api in MODELS.items()]}
    write(HERE / "tier-spec-google.json", spec)
    spec_sha256 = hashlib.sha256((HERE / "tier-spec-google.json").read_bytes()).hexdigest()
    items = []
    for inventory, api in MODELS.items():
        model_id = "google-" + inventory
        model = {"id": model_id, "inventory_id": inventory, "model": api, "response_model": api,
                 "provider": "google", "api": "chat", "base_url": BASE, "api_key_env": "GEMINI_API_KEY",
                 "generation": {"max_tokens": OUTPUT_CAP, **REASONING},
                 "tier": {"level": "high", "reasoning": REASONING, "spec_sha256": spec_sha256},
                 "backend_provenance": {"service_revision": None, "bridge": None}}
        write(HERE / "specs" / (model_id + ".json"),
              {"model": model, "config": {"native": {"timeout_seconds": 3600, "retries": 2}}, "image": IMAGE,
               "limits": {"steps": 5, "wall_seconds": 1800, "command_seconds": 15}})
        items.append({"id": model_id, "provider": "google", "spec": f"{ROOT}/control/specs/{model_id}.json",
                      "out": f"{ROOT}/qualification/out/{model_id}", "timeout": 2400})
    write(HERE / "qualification-plan.json",
          {"control": ROOT + "/qualification", "env_file": ASHBURN + "/.private/controller.env.json",
           "python": ASHBURN + "/runtime/bin/python3.11",
           "readiness": ROOT + "/repo/benchmark/native_readiness.py",
           "concurrency": {"google": 2}, "go_pool": [], "go_per_key": 0, "label": "google-qualify-1",
           "items": items})
    print(json.dumps({"tier_spec_sha256": spec_sha256, "models": len(items)}))


if __name__ == "__main__":
    main()
