"""Offline only: real pinned mini drives this PR's bridge with a synthetic SDK."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

# Imports belong after isolated mini configuration is established.
ROOT = Path(__file__).resolve().parent


class CursorMiniTests(unittest.TestCase):
    def test_real_mini_handoff_and_redaction(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=home,
                       MSWEA_GLOBAL_CONFIG_DIR=home, MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT="1",
                       LITELLM_LOCAL_MODEL_COST_MAP="True", LITELLM_MODE="PRODUCTION",
                       KEYGEN_CURSOR_BRIDGE_TOKEN="synthetic-local-token-123456789",
                       NO_PROXY="127.0.0.1,localhost")
            env.pop('CURSOR_API_KEY', None)
            # This child contacts only the synthetic loopback server.
            for key in list(env):
                if key.lower() in {'http_proxy', 'https_proxy', 'all_proxy'}:
                    env.pop(key)
            script = r'''
import json, os
from pathlib import Path
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from benchmark.experimental.cursor_sdk.model import CursorMiniModel
m=CursorMiniModel(model_name='fixture',bridge_url=os.environ['BRIDGE_URL'],allow_credit_usage=True,accept_experimental_condition=True)
try:
 a=DefaultAgent(m,LocalEnvironment(cwd=os.environ['HOME']),system_template='EXACT SYSTEM',instance_template='EXACT TASK',step_limit=3,cost_limit=0)
 result=a.run()
 assert result['exit_status']=='Submitted', result
 assert Path(os.environ['HOME'],'proof.txt').read_text()=='mini-owned'
 output=json.dumps(a.serialize())
 assert os.environ['KEYGEN_CURSOR_BRIDGE_TOKEN'] not in output
 assert a.serialize()['info']['cursor_experiment']['frozen_eligible'] is False
 assert a.serialize()['info']['cursor_experiment']['cost_known'] is False
 print('PASS: real mini -> actual bridge -> mocked SDK callback -> mini Bash -> callback continuation')
finally:
 m.close()
'''
            server = subprocess.Popen(["node", str(ROOT / "fixtures/server.mjs")], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True, env=env)
            try:
                port = server.stdout.readline().strip()
                self.assertTrue(port.isdigit(), port)
                env['BRIDGE_URL'] = f'http://127.0.0.1:{port}/v1'
                completed = subprocess.run([os.sys.executable, '-c', script], env=env,
                                           capture_output=True, text=True, timeout=30, cwd=ROOT.parents[2])
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            finally:
                server.terminate()
                try:
                    server.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.communicate()


if __name__ == '__main__':
    unittest.main()
