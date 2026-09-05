"""Offline tests for our checker. These do NOT run FT2 or validate its mixer."""
from __future__ import annotations
import base64
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

from tools.ft2_smoke import CheckError, MAX_LINE, PROTOCOL, StdioMCP, pcm_fixture, tool_text, wav_metrics


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def client(self, program: str, timeout: float = 2) -> StdioMCP:
        client = StdioMCP([sys.executable, "-u", "-c", program], self.root, timeout)
        self.addCleanup(client.close)
        return client

    def wav(self, values, channels=1):
        path = self.root / "test.wav"
        with wave.open(str(path), "wb") as h:
            h.setparams((channels, 2, 8000, 0, "NONE", "not compressed"))
            h.writeframes(struct.pack("<" + "h" * len(values), *values))
        return path

    def test_initialize_and_notifications(self):
        c = self.client('''import json, sys
for line in sys.stdin:
    m=json.loads(line)
    if "id" not in m: continue
    r={"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"fake"}}
    print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":r}), flush=True)
''')
        self.assertEqual(c.initialize()["protocolVersion"], PROTOCOL)

    def test_diagnostics_are_not_json(self):
        c = self.client('''import json, sys
for line in sys.stdin:
    m=json.loads(line)
    print("diagnostic", file=sys.stderr, flush=True)
    print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":{}}), flush=True)
''')
        self.assertEqual(c.request("ping", {}), {})

    def test_wrong_id_rejected(self):
        c = self.client('import sys; sys.stdin.readline(); print(\'{"jsonrpc":"2.0","id":99,"result":{}}\',flush=True)')
        with self.assertRaisesRegex(CheckError, "response ID"):
            c.request("ping", {})

    def test_rpc_error_rejected(self):
        c = self.client('import sys; sys.stdin.readline(); print(\'{"jsonrpc":"2.0","id":1,"error":{"code":-1}}\',flush=True)')
        with self.assertRaisesRegex(CheckError, "RPC error"):
            c.request("ping", {})

    def test_malformed_stdout_rejected(self):
        c = self.client('import sys; sys.stdin.readline(); print("not JSON",flush=True)')
        with self.assertRaisesRegex(CheckError, "invalid server output"):
            c.request("ping", {})

    def test_timeout_rejected(self):
        c = self.client('import sys,time; sys.stdin.readline(); time.sleep(10)', timeout=0.15)
        with self.assertRaisesRegex(CheckError, "timeout"):
            c.request("ping", {})

    def test_oversized_request_rejected(self):
        c = self.client('import sys; sys.stdin.read()')
        with self.assertRaisesRegex(CheckError, "line limit"):
            c.request("ping", {})

    def test_normal_tool_text(self):
        self.assertEqual(tool_text({"content": [{"type": "text", "text": "saved"}]}), "saved")

    def test_tool_failure_rejected(self):
        with self.assertRaisesRegex(CheckError, "failed to save"):
            tool_text({"isError": True, "content": [{"type": "text", "text": "failed to save"}]})

    def test_tone_metrics(self):
        m = wav_metrics(self.wav([0, 1000, -1000, 0] * 100, channels=2))
        self.assertEqual(m["frames"], 200)
        self.assertEqual(m["channels"], 2)
        self.assertEqual(m["dc_offset"], 0)
        self.assertGreater(m["rms"], 0)
        self.assertEqual(len(m["sha256"]), 64)

    def test_silence_rejected(self):
        with self.assertRaisesRegex(CheckError, "silent"):
            wav_metrics(self.wav([0] * 100))

    def test_empty_wav_rejected(self):
        with self.assertRaisesRegex(CheckError, "empty"):
            wav_metrics(self.wav([]))

    def test_full_scale_rejected(self):
        with self.assertRaisesRegex(CheckError, "full-scale"):
            wav_metrics(self.wav([0, 32767, -32768, 0]))

    def test_missing_wav_rejected(self):
        with self.assertRaisesRegex(CheckError, "missing WAV"):
            wav_metrics(self.root / "missing.wav")

    def test_truncated_wav_rejected(self):
        path = self.wav([1000, -1000] * 100)
        path.write_bytes(path.read_bytes()[:-4])
        with self.assertRaisesRegex(CheckError, "truncated"):
            wav_metrics(path)

    def test_pcm_fixture_deterministic(self):
        raw = base64.b64decode(pcm_fixture())
        self.assertEqual(len(raw), 2048)
        self.assertEqual(raw, base64.b64decode(pcm_fixture()))
        self.assertNotEqual(raw, bytes(len(raw)))

    def test_missing_native_binary_fails(self):
        script = Path(__file__).parents[1] / "tools" / "ft2_smoke.py"
        r = subprocess.run([sys.executable, str(script), "--ft2", str(self.root / "missing"),
                            "--out", str(self.root / "out")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("executable not found", r.stderr)
        self.assertFalse((self.root / "out").exists())


if __name__ == "__main__":
    unittest.main()
