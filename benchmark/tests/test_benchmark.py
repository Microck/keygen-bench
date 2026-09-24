"""Offline contract tests. They do not use subscriptions, Docker, or the FT2 mixer."""
from __future__ import annotations

from contextlib import contextmanager
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tarfile
import tempfile
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from benchmark import run
from benchmark.proxy import ProxyModel, request, validate_url
from minisweagent.exceptions import FormatError
from minisweagent.models.utils.actions_toolcall import BASH_TOOL


@contextmanager
def environ(**values):
    """Set process environment variables for one block, then restore the originals."""
    saved = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def bash_call(command, call_id="call_1"):
    return {"id": call_id, "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": command})}}


@contextmanager
def endpoint(code=200, returned_model="exact-model", redirect=False, tool_calls=(bash_call("echo ready"),)):
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.do_POST()
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            seen.append({"path": self.path, "body": json.loads(raw) if raw else None,
                         "authorization": self.headers.get("Authorization")})
            self.send_response(302 if redirect else code)
            if redirect:
                self.send_header("Location", "/v1/should-not-follow")
            self.end_headers()
            response = {"model": returned_model, "choices": [{"message": {"content": "", "tool_calls": list(tool_calls)},
                "finish_reason": "tool_calls"}],
                "usage": {"total_tokens": 10}}
            self.wfile.write(json.dumps(response).encode())
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", seen
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = json.loads((run.HERE / "config/campaign.example.json").read_text())
        self.config["proxy_version"] = "test-version"
        self.config["models"] = [{"id": "test-model", "model": "exact-model", "response_model": "exact-model"}]
        self.path = self.root / "campaign.json"
        self.proxy_file = self.root / "cliproxyapi.local.yaml"
        self.proxy_file.write_text((run.HERE / "config/cliproxyapi.example.yaml").read_text())

    def load(self):
        self.path.write_text(json.dumps(self.config))
        return run.load_config(self.path)

    def fake_shell(self, stdout=b""):
        """Replace run.shell with a recorder so no Docker command runs; returns the recorded argv list."""
        commands = []
        def shell(cmd, **kwargs):
            commands.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout, b"")
        self.addCleanup(setattr, run, "shell", run.shell)
        run.shell = shell
        return commands

    def test_campaign_configuration(self):
        c = self.load()
        self.assertIn("Choose the sound", c["task"])
        self.assertIn("Budget: 100 commands and 30 minutes.", c["system"])
        self.assertNotIn("<<", c["system"])
        self.assertFalse(c["proxy_policy"]["upstream_payload_verified"])
        self.assertNotIn("api-keys", json.dumps(c))

    def test_duplicate_models_rejected(self):
        self.config["models"].append({**self.config["models"][0], "id": "other"})
        with self.assertRaisesRegex(ValueError, "Duplicate model"):
            self.load()

    def test_model_prompt_overrides_rejected(self):
        self.config["models"][0]["system"] = "skill instructions"
        with self.assertRaises(ValueError):
            self.load()

    def test_tools_and_router_parameters_rejected(self):
        for parameter in ["messages", "tools", "api_base", "fallbacks", "n", "num_retries"]:
            with self.subTest(parameter=parameter):
                self.config["generation"] = {parameter: []}
                with self.assertRaises(ValueError):
                    self.load()

    def test_bad_resource_budgets_rejected(self):
        for value in [0, -1, True, 1.5]:
            self.config["limits"]["steps"] = value
            with self.assertRaises(ValueError):
                self.load()

    def test_reserved_environment_names_rejected(self):
        self.config["api_key_env"] = "HOME"
        with self.assertRaises(ValueError):
            self.load()

    def test_nan_rejected(self):
        self.config["generation"]["temperature"] = float("nan")
        with self.assertRaises(ValueError):
            self.load()

    def test_proxy_retries_and_prompt_rewrite_rejected(self):
        original = self.proxy_file.read_text()
        for old, new in [("request-retry: 0", "request-retry: 1"),
                         ("disable-claude-cloak-mode: true", "disable-claude-cloak-mode: false"),
                         ("switch-preview-model: false", "switch-preview-model: true"),
                         ("payload: {}", "payload: {override: something}")]:
            self.proxy_file.write_text(original.replace(old, new))
            with self.assertRaises(ValueError):
                self.load()

    def test_local_endpoint_only(self):
        for url in ["https://example.com/v1", "http://user:secret@127.0.0.1:8317/v1",
                    "http://127.0.0.1:8317/v1?x=1", "http://localhost:8317/v1"]:
            with self.assertRaises(ValueError):
                validate_url(url)
        self.assertEqual(validate_url("http://127.0.0.1:8317/v1/"), "http://127.0.0.1:8317/v1")

    def test_no_ambient_configuration_forwarded(self):
        with environ(CLIPROXY_CLIENT_KEY="secret", BASH_ENV="/tmp/skills", MSWEA_DEFAULT_MODEL="other",
                     ANTHROPIC_API_KEY="private", PYTHONPATH="/tmp/injected"):
            env = run.isolated_env(self.root, "CLIPROXY_CLIENT_KEY")
        for key in ["BASH_ENV", "MSWEA_DEFAULT_MODEL", "ANTHROPIC_API_KEY", "PYTHONPATH"]:
            self.assertNotIn(key, env)
        self.assertEqual(env["HOME"], str(self.root))
        self.assertEqual(env["MSWEA_GLOBAL_CONFIG_DIR"], str(self.root / "mini-config"))

    def test_lock_and_one_attempt(self):
        run.lock_campaign(self.root / "lock.json", {"prompt": "original"})
        run.lock_campaign(self.root / "lock.json", {"prompt": "original"})
        with self.assertRaises(ValueError):
            run.lock_campaign(self.root / "lock.json", {"prompt": "changed"})
        run.reserve(self.root, "model")
        with self.assertRaises(FileExistsError):
            run.reserve(self.root, "model")

    def test_outbound_messages_and_single_bash_tool(self):
        c = self.load()
        history = [{"role": "system", "content": "Exact original {{ text }}", "extra": {"private": 1}},
                   {"role": "user", "content": "task"},
                   {"role": "assistant", "content": "", "tool_calls": [bash_call("ls", "call_0")], "extra": {"actions": []}},
                   {"role": "tool", "content": "<returncode>0</returncode>", "tool_call_id": "call_0", "extra": {"raw_output": "x"}}]
        with endpoint() as (url, seen), environ(CLIPROXY_CLIENT_KEY="local-secret", HTTP_PROXY="http://unreachable:1"):
            c["base_url"] = url
            model = ProxyModel(c, c["models"][0], self.root / "audit.jsonl")
            answer = model.query(history)
        self.assertEqual(len(seen), 1)
        body = seen[0]["body"]
        self.assertEqual(body["messages"], [{"role": "system", "content": "Exact original {{ text }}"},
                                            {"role": "user", "content": "task"},
                                            {"role": "assistant", "content": "", "tool_calls": [bash_call("ls", "call_0")]},
                                            {"role": "tool", "content": "<returncode>0</returncode>", "tool_call_id": "call_0"}])
        self.assertEqual(body["tools"], [BASH_TOOL])  # mini's one bash tool, nothing else
        self.assertNotIn("tool_choice", body)
        self.assertEqual(body["n"], 1)
        self.assertEqual(answer["extra"]["actions"], [{"command": "echo ready", "tool_call_id": "call_1"}])
        self.assertEqual(answer["tool_calls"], [bash_call("echo ready")])
        self.assertNotIn("local-secret", json.dumps(model.serialize()))
        self.assertNotIn("local-secret", (self.root / "audit.jsonl").read_text())

    def test_missing_or_unknown_tool_call_raises_mini_format_error(self):
        c = self.load()
        unknown = {"id": "call_9", "type": "function", "function": {"name": "python", "arguments": "{}"}}
        for calls, expected in [((), "No tool calls found"), ((unknown,), "Unknown tool 'python'")]:
            with endpoint(tool_calls=calls) as (url, _), environ(CLIPROXY_CLIENT_KEY="secret"):
                c["base_url"] = url
                with self.assertRaises(FormatError) as caught:
                    ProxyModel(c, c["models"][0], self.root / "audit.jsonl").query([])
            feedback = caught.exception.messages[0]
            self.assertEqual(feedback["role"], "user")
            self.assertIn(expected, feedback["content"])
        self.assertEqual(len((self.root / "audit.jsonl").read_text().splitlines()), 2)  # both turns audited

    def test_observations_are_tool_results(self):
        c = self.load()
        with environ(CLIPROXY_CLIENT_KEY="secret"):
            model = ProxyModel(c, c["models"][0], self.root / "audit.jsonl")
        turn = {"role": "assistant", "extra": {"actions": [{"command": "ls", "tool_call_id": "call_0"}]}}
        [observation] = model.format_observation_messages(turn, [{"returncode": 0, "output": "a" * 30000}])
        self.assertEqual((observation["role"], observation["tool_call_id"]), ("tool", "call_0"))
        self.assertIn("<returncode>0</returncode>", observation["content"])
        self.assertIn("[observation truncated]", observation["content"])
        self.assertLess(len(observation["content"]), 21000)

    def test_error_not_retried(self):
        with endpoint(code=429) as (url, seen):
            with self.assertRaisesRegex(RuntimeError, "429"):
                request(url, "secret", "/chat/completions", {})
        self.assertEqual(len(seen), 1)

    def test_redirect_not_followed(self):
        with endpoint(redirect=True) as (url, seen):
            with self.assertRaisesRegex(RuntimeError, "redirect"):
                request(url, "secret", "/chat/completions", {})
        self.assertEqual(len(seen), 1)

    def test_model_switch_fails(self):
        c = self.load()
        with endpoint(returned_model="unexpected") as (url, _), environ(CLIPROXY_CLIENT_KEY="secret"):
            c["base_url"] = url
            with self.assertRaisesRegex(ValueError, "Unexpected response model"):
                ProxyModel(c, c["models"][0], self.root / "audit").query([])

    def test_sandbox_flags_no_host_mounts(self):
        commands = self.fake_shell()
        run.start_container(["/usr/bin/docker"], "sha256:test", "test")
        cmd = next(c for c in commands if "--name" in c and c[c.index("--name") + 1] == "test")
        for value in ["--read-only", "--cap-drop", "--network", "none", "--user", "10001:10001"]:
            self.assertIn(value, cmd)
        self.assertIn("type=volume,source=test-work,target=/workspace,volume-nocopy", cmd)
        self.assertNotIn("type=bind", " ".join(cmd))
        for value in ["-v", "--volume", "--env-file", "--privileged"]:
            self.assertNotIn(value, cmd)

    def test_visualizer_container_is_isolated_and_capped(self):
        c = self.load()
        (self.root / "submission").mkdir(); (self.root / "submission/tune.xm").write_bytes(b"Extended Module: x")
        commands = self.fake_shell(b"")
        video = run.visualize(["docker"], "sha256:vis", self.root, c, duration=100000.0)
        start = next(cmd for cmd in commands if cmd[1] == "run")
        for value in ["--network", "none", "--read-only", "--cap-drop", "--user", "10001:10001"]:
            self.assertIn(value, start)
        self.assertNotIn("type=bind", " ".join(start))
        capture = next(cmd for cmd in commands if "/opt/keygen/visualize.sh" in cmd)
        self.assertEqual(capture[-2], str(c["limits"]["video_seconds"]))  # duration capped by the campaign limit
        self.assertEqual(video["seconds"], c["limits"]["video_seconds"])
        self.assertTrue((self.root / "visualizer/visualizer.mp4").exists())
        self.assertEqual(commands[-1][1:3], ["rm", "-f"])

    def test_shell_skips_profiles(self):
        commands = self.fake_shell(b"ok")
        result = run.Sandbox(["docker"], "container", 10).execute({"command": "echo ok"})
        command = " ".join(commands[-1])
        self.assertIn("--noprofile --norc", command)
        self.assertIn("BASH_ENV=/dev/null", command)
        self.assertEqual(result["output"], "ok")

    def archive(self, name, size=4, kind=tarfile.REGTYPE):
        path = self.root / "artifact.tar"
        with tarfile.open(path, "w") as tf:
            item = tarfile.TarInfo(name)
            item.type, item.size = kind, size if kind == tarfile.REGTYPE else 0
            tf.addfile(item, io.BytesIO(b"a" * size) if kind == tarfile.REGTYPE else None)
        return path

    def test_artifact_paths_and_links_rejected(self):
        for name, kind in [("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)]:
            with self.assertRaises(ValueError):
                run.safe_unpack(self.archive(name, kind=kind), self.root / "out", 100)

    def test_artifact_byte_limit(self):
        with self.assertRaises(ValueError):
            run.safe_unpack(self.archive("tune.xm", 100), self.root / "out", 20)

    def test_regular_artifact_extracted(self):
        run.safe_unpack(self.archive("tune.xm"), self.root / "out", 100)
        self.assertEqual((self.root / "out/tune.xm").read_bytes(), b"aaaa")

    def wav(self, values):
        path = self.root / "audio.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            wav.writeframes(struct.pack("<" + "h" * len(values), *values))
        return path

    def test_audio_is_not_an_aesthetic_judge(self):
        result = run.wav_info(self.wav([32767, -32768, 1000, -1000] * 50))
        self.assertIsNone(result["quality_score"])
        self.assertEqual(result["full_scale_samples"], 100)

    def test_silent_audio_fails(self):
        with self.assertRaisesRegex(ValueError, "silent"):
            run.wav_info(self.wav([0] * 100))

    @unittest.skipUnless(importlib.util.find_spec("minisweagent"), "Pinned mini-swe-agent not installed")
    def test_real_mini_agent_worker_contract(self):
        # Run in a subprocess so real mini cannot read the test host's global .env.
        program = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from proxy import ProxyModel
from minisweagent.agents.default import DefaultAgent
from minisweagent.exceptions import Submitted
class Model(ProxyModel):
    def query(self, messages, **kwargs):
        assert messages[0]['content'] == 'Exact {{ untouched }}'
        return {'role':'assistant','content':'','tool_calls':[],'extra':{'actions':[{'command':'submit','tool_call_id':'c1'}]}}
class Env:
    def get_template_vars(self, **kw): return {}
    def serialize(self): return {}
    def execute(self, action):
        raise Submitted({'role':'exit','content':'done','extra':{'exit_status':'Submitted'}})
m=object.__new__(Model);m.config={'generation':{}};m.model={'model':'fake'}
a=DefaultAgent(m,Env(),system_template='{{ frozen }}',instance_template='{{ task }}',cost_limit=0,step_limit=1)
assert a.run('Create music',frozen='Exact {{ untouched }}')['exit_status']=='Submitted'
'''
        env = {"PATH": os.environ["PATH"], "HOME": str(self.root),
               "MSWEA_GLOBAL_CONFIG_DIR": str(self.root / "empty-mini"), "MSWEA_SILENT_STARTUP": "1"}
        run.shell([__import__("sys").executable, "-I", "-c", program, str(run.HERE)], env=env)


if __name__ == "__main__":
    unittest.main()
