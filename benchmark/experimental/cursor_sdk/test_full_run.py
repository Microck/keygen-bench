"""Offline controller contracts: no paid provider, Docker or listener calls."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from . import full_run as full

IMAGE = 'sha256:' + '1' * 64


class FullRunTests(unittest.TestCase):
    def test_frozen_music_task_and_local_limits(self):
        config = full.configuration()
        self.assertEqual(config['limits'], full.LIMITS)
        self.assertEqual(config['limits']['wall_seconds'], 7200)
        self.assertEqual(config['limits']['steps'], 0)
        self.assertEqual(config['limits']['command_seconds'], 120)
        self.assertIn('original keygen tune', config['prompts']['task'])
        self.assertIn('COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT', config['prompts']['system'])
        self.assertFalse(full.experiment('model')['leaderboard_eligible'])

    def test_plan_never_preflights_or_creates_output(self):
        with tempfile.TemporaryDirectory() as root, patch.object(full, 'preflight') as preflight:
            target = Path(root) / 'new'
            with contextlib.redirect_stdout(io.StringIO()) as output:
                full.main(['--model','fixture','--agent-image',IMAGE,'--work',str(target),'--plan'])
            preflight.assert_not_called()
            self.assertFalse(target.exists())
            self.assertFalse(json.loads(output.getvalue())['experiment']['frozen_eligible'])

    def test_rejects_existing_relative_checkout_and_symlink_outputs(self):
        with tempfile.TemporaryDirectory() as root:
            for value in [root, 'relative', str(full.REPO / 'new-output')]:
                with self.assertRaises(ValueError): full.private_path(value)
            link = Path(root) / 'link'
            link.symlink_to(Path(root), target_is_directory=True)
            with self.assertRaises(ValueError): full.private_path(link / 'new')

    def test_worker_environment_does_not_inherit_credentials_or_startup_code(self):
        with patch.dict(os.environ, {'CURSOR_API_KEY':'private','OPENAI_API_KEY':'other',
                                     'NODE_OPTIONS':'--require evil','PYTHONPATH':'evil'}, clear=True):
            env=full.child_environment(Path('/tmp/synthetic'),{'KEYGEN_CURSOR_BRIDGE_TOKEN':'local-token'})
        for name in ['CURSOR_API_KEY','OPENAI_API_KEY','NODE_OPTIONS','PYTHONPATH']:
            self.assertNotIn(name,env)
        self.assertEqual(env['MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT'],'1')

    def test_scorer_results_never_claim_ranked_eligibility(self):
        import score
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root);(directory/'evaluations/one').mkdir(parents=True)
            raw={'eligible':True,'craft':{'craft_score':55.5},'evaluation_location':'evaluations/one'}
            with patch.object(score,'profile_attempt',return_value=raw) as scorer:
                profile=full.score_experiment(directory)
            scorer.assert_called_once_with(directory,force=True)
            self.assertTrue(profile['artifact_evaluation_eligible'])
            for path in [directory/'profile.json',directory/'evaluations/one/profile.json']:
                saved=json.loads(path.read_text());self.assertFalse(saved['eligible'])
                self.assertFalse(saved['leaderboard_eligible']);self.assertEqual(saved['craft']['craft_score'],55.5)

    def test_report_keeps_failures_and_unstarted_slots_without_fake_zero(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            for name,state in zip(full.ATTEMPTS,['RENDERED_UNSCORED','MODEL_FAILED','NOT_STARTED']):
                (root/name).mkdir();full.write_json(root/name/'status.json',{'status':state})
            full.write_json(root/'attempt-1/profile.json',{'craft':{'craft_score':50},'artifact_evaluation_eligible':True})
            report=full.report(root)
            self.assertEqual(len(report['attempts']),3)
            self.assertEqual([row['score'] for row in report['attempts']],[50,None,None])
            self.assertIsNone(report['mean_score']);self.assertIsNone(report['dollar_cost'])
            self.assertFalse(report['leaderboard_eligible'])

    def test_runs_three_distinct_slots_without_retries(self):
        self._sequence(None,3)

    def test_stops_spending_after_infrastructure_or_evaluator_failure(self):
        for failure in ['INFRA','EVAL']:
            self._sequence(failure,1)

    def _sequence(self,failure,count):
        with tempfile.TemporaryDirectory() as root:
            output=Path(root)/'new'
            def attempt(directory,*args):
                status={'status':'INFRA_ERROR' if failure else 'MODEL_FAILED','failure_category':failure}
                full.write_json(directory/'status.json',status)
                return status,None
            with patch.dict(os.environ,{'CURSOR_API_KEY':'synthetic-secret'}), \
                 patch.object(full,'preflight',return_value=(['docker'],{})), \
                 patch.object(full,'run_attempt',side_effect=attempt) as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                full.main(['--model','fixture','--agent-image',IMAGE,'--work',str(output),
                           '--allow-credit-usage','--accept-experimental-condition'])
            self.assertEqual(run.call_count,count)
            self.assertEqual(len(json.loads((output/'experimental-results.json').read_text())['attempts']),3)
            self.assertNotIn('synthetic-secret',(output/'experiment.json').read_text())

    def test_attempt_uses_trusted_sandbox_collection_and_render(self):
        import run
        with tempfile.TemporaryDirectory() as root:
            directory=Path(root)/'attempt-1';directory.mkdir()
            args=argparse.Namespace(model='fixture',effort=None,agent_image=IMAGE)
            def collect(*args):
                (directory/'submission').mkdir();(directory/'submission/tune.xm').write_bytes(b'synthetic')
                full.write_json(directory/'worker-result.json',{'exit_status':'Submitted'})
                return {'status':'collected'}
            process=Mock();process.poll.return_value=0
            with patch.object(run,'start_container') as start, patch.object(run,'remove_container') as remove, \
                 patch.object(run,'shell'), patch.object(run,'collect_submission',side_effect=collect) as collection, \
                 patch.object(run,'render',return_value={'duration_seconds':1}) as render, \
                 patch.object(full,'start_bridge',return_value=(process,'http://127.0.0.1:8320/v1')), \
                 patch.object(full.subprocess,'Popen',return_value=process) as popen, \
                 patch.object(full,'score_experiment',return_value=None), \
                 patch('artifacts.ArtifactStore.preflight'):
                # Worker receipt must exist before collection, as a real worker writes it.
                full.write_json(directory/'worker-result.json',{'exit_status':'Submitted'})
                status,_=full.run_attempt(directory,args,full.configuration(),['docker'],'upstream-secret')
            start.assert_called_once();collection.assert_called_once();render.assert_called_once()
            self.assertGreaterEqual(remove.call_count,1)
            self.assertNotIn('CURSOR_API_KEY',popen.call_args.kwargs['env'])
            self.assertEqual(popen.call_args.kwargs['env']['MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT'],'1')
            self.assertFalse(status['eligible']);self.assertEqual(status['render'],'ok')
            self.assertNotIn('upstream-secret',(directory/'spec.json').read_text())


if __name__ == '__main__': unittest.main()
