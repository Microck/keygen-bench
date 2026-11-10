"""Opt-in real offline Docker/FT2/scorer path with synthetic SDK and fake listener.

No Cursor login/inference and no neural listener weights. This proves orchestration,
not real-provider access, musical quality, fairness or model identity.
"""
import argparse
import copy
import base64
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from . import full_run as full


@unittest.skipUnless(os.environ.get('KEYGEN_CURSOR_NATIVE_TEST_IMAGE'), 'requires explicit local pinned FT2 image')
class NativeFullRunTests(unittest.TestCase):
    def test_three_real_offline_sandboxes_render_and_score(self):
        import run
        from benchmark.tests.test_score import build_xm
        image=os.environ['KEYGEN_CURSOR_NATIVE_TEST_IMAGE']
        docker=run.docker_command()
        sample_frames=2048
        module=bytearray(build_xm(sample_frames=sample_frames))
        previous=0;encoded=[]
        for i in range(sample_frames):
            value=round(48*math.sin(2*math.pi*i/32))
            encoded.append((value-previous)&255);previous=value
        module[-sample_frames:]=bytes(encoded)
        payload=base64.b64encode(module).decode()
        commands=[f"mkdir -p submission && python3 -c \"import base64;open('submission/tune.xm','wb').write(base64.b64decode('{payload}'))\"",
                  'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT']
        def start_fixture(directory, model, effort, token, cursor_key):
            home=directory/'bridge-home';home.mkdir()
            env=full.child_environment(home,{'KEYGEN_CURSOR_BRIDGE_TOKEN':token,'KEYGEN_TEST_COMMANDS_JSON':json.dumps(commands)})
            process=subprocess.Popen(['node',str(full.HERE/'fixtures/server.mjs')],env=env,cwd=home,
                                     stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True)
            try:
                port=process.stdout.readline().strip()
                if not port.isdigit():raise RuntimeError('Fixture did not start')
                process.stdout.close()
                return process,f'http://127.0.0.1:{port}/v1'
            except BaseException:
                full.stop_process(process);raise
        with tempfile.TemporaryDirectory(prefix='keygen-cursor-native-') as temporary:
            root=Path(temporary);config=full.configuration()
            args=argparse.Namespace(model='fixture',effort=None,agent_image=image)
            prior=signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Native fixture deadline')))
            try:
                for name in full.ATTEMPTS:
                    directory=root/name;directory.mkdir()
                    signal.alarm(180)
                    import score
                    snapshots=[]
                    original=score.profile_inputs
                    def observe_inputs(*args,**kwargs):
                        value=original(*args,**kwargs);snapshots.append(copy.deepcopy(value));return value
                    with patch.object(full,'start_bridge',side_effect=start_fixture), patch.object(score,'profile_inputs',side_effect=observe_inputs):
                        status,profile=full.run_attempt(directory,args,config,docker,'unused-synthetic-key')
                    if status.get('failure_category') == 'EVAL' and len(snapshots) >= 2:
                        def changed(a,b,prefix=''):
                            if isinstance(a,dict) and isinstance(b,dict):
                                return [item for key in set(a)|set(b) for item in changed(a.get(key),b.get(key),prefix+'/'+str(key))]
                            return [prefix] if a != b else []
                        print('Evaluator provenance changes:',changed(snapshots[0],snapshots[-1])[:30])
                    signal.alarm(0)
                    self.assertIsNone(status['failure_category'],{'status':status,'evaluation_error':profile.get('evaluation_error') if profile else None})
                    self.assertEqual(status['render'],'ok',status)
                    self.assertTrue((directory/'canonical/canonical.wav').is_file())
                    self.assertTrue((directory/'trajectory.json').is_file())
                    self.assertTrue(profile['artifact_evaluation_eligible'],profile)
                    self.assertFalse(profile['eligible'])
                    self.assertFalse(profile['leaderboard_eligible'])
                    self.assertIsInstance(profile['craft']['craft_score'],(int,float))
                    self.assertEqual(profile['inputs']['listener']['model'],'fake')
                report=full.report(root)
                self.assertEqual(report['scored_attempts'],3)
                self.assertFalse(report['leaderboard_eligible'])
                print('PASS: three actual mini/Docker/FT2/scorer attempts; mocked SDK and fake listener only')
            finally:
                signal.alarm(0);signal.signal(signal.SIGALRM,prior)


if __name__ == '__main__': unittest.main()
