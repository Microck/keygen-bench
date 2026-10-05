#!/usr/bin/env python3
"""Find which part of the request makes Anthropic refuse claude-opus-5 before generating (0 output tokens).

Sends one small request per variant through the local CLIProxyAPI bridge (Claude OAuth); prints
stop_reason and output tokens only. Variants isolate: account/route, the readiness system prompt,
the readiness task, the benchmark (keygen) system prompt and task, tools, and adaptive thinking.
claude-opus-4-8 with the full benchmark request is the control. Run from benchmark/.
"""
import json
import sys
import urllib.error
import urllib.request

import yaml

sys.path.insert(0, ".")
import campaign  # noqa: E402
import native_readiness as nr  # noqa: E402

KEY = yaml.safe_load(open("config/cliproxyapi.local.yaml"))["api-keys"][0]
READY_SYSTEM, READY_TASK = nr.SYSTEM, nr.readiness_task("native-history-0123456789abcdef")
BENCH = campaign.prompt_manifest({"steps": 0, "wall_seconds": 7200, "command_seconds": 120,
                                  "artifact_bytes": 128 * 1024 * 1024})
TOOL = [{"name": "bash", "description": "Execute a bash command",
         "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}]


def ask(label, system, user, model="claude-opus-5", tools=None, thinking=True):
    body = {"model": model, "max_tokens": 2048, "messages": [{"role": "user", "content": user}]}
    if system:
        body["system"] = system
    if tools:
        body["tools"] = tools
    if thinking:
        body["thinking"] = {"type": "adaptive"}
    request = urllib.request.Request("http://127.0.0.1:8417/v1/messages", json.dumps(body).encode(),
                                     {"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        data = json.load(urllib.request.urlopen(request, timeout=300))
        print(f"{label:44s} stop={data.get('stop_reason')} out={data.get('usage', {}).get('output_tokens')}")
    except urllib.error.HTTPError as exc:
        print(f"{label:44s} HTTP {exc.code} {exc.read()[:160]!r}")


ask("plain hello", None, "Reply OK.")
ask("plain hello, no thinking", None, "Reply OK.", thinking=False)
ask("readiness system + hello", READY_SYSTEM, "Reply OK.")
ask("hello + readiness task", None, READY_TASK)
ask("readiness system + task + tool", READY_SYSTEM, READY_TASK, tools=TOOL)
ask("benchmark task only", None, BENCH["task"])
ask("benchmark system only + hello", BENCH["system"], "Reply OK.")
ask("benchmark system + task + tool", BENCH["system"], BENCH["task"], tools=TOOL)
ask("CONTROL opus-4-8 benchmark full", BENCH["system"], BENCH["task"], model="claude-opus-4-8", tools=TOOL)
