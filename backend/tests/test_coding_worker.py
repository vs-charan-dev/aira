import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import ROOT, settings
from app.services import coding_worker as worker


class CodingWorkerTests(unittest.IsolatedAsyncioTestCase):
    def test_observed_suite_counts_reject_empty_and_accept_node_variants(self):
        for text in ('# tests 3', 'ℹ tests 3', 'Ran 1 test in 0.01s'): self.assertTrue(worker.has_tests(text))
        for text in ('# tests 0', 'ℹ tests 0', 'All good', 'Ran 0 tests'): self.assertFalse(worker.has_tests(text))

    def test_worker_permissions_and_paths_do_not_inherit_other_credentials(self):
        with patch.dict('os.environ', {'OTHER_API_KEY':'synthetic-other-key','OPENCODE_CONFIG':'bad-config'}):
            env=worker.environment('synthetic-key',ROOT)
        config=json.loads(env['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(config['permission']['bash'],'deny')
        self.assertEqual(config['permission']['edit'],'deny')
        self.assertEqual(config['permission']['task'],'deny')
        self.assertEqual(config['permission']['external_directory'],'deny')
        self.assertNotIn('OTHER_API_KEY',env); self.assertNotIn('OPENCODE_CONFIG',env)
        for name in ('HOME','USERPROFILE','APPDATA','LOCALAPPDATA','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME','TEMP','TMP'):
            self.assertTrue(Path(env[name]).is_relative_to(ROOT))
        config=json.loads(worker.environment('synthetic',ROOT,True)['OPENCODE_CONFIG_CONTENT'])
        self.assertEqual(config['permission']['edit']['*.test.*'],'deny')
        self.assertEqual(config['permission']['edit']['*'],'allow')

    def test_project_rejects_drive_installation_private_data_and_non_e_paths(self):
        for path in ('E:/',str(ROOT),str(settings.aira_data_dir),'C:/Users','E:/missing-dir-for-test'):
            with self.assertRaises((ValueError,OSError)): worker.validate_project(path,'node')

    async def test_real_node_runner_reports_nonempty_and_empty_suite_without_model(self):
        with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as folder:
            project=Path(folder)
            (project/'fixture.test.cjs').write_text("require('node:test')('synthetic',()=>require('node:assert/strict').equal(1,1));",encoding='utf-8')
            labels=[]
            async def progress(label): labels.append(label)
            result=await worker.run_tests(project,'node',progress)
            self.assertEqual(result['exitCode'],0); self.assertTrue(worker.has_tests(result['output']))
            self.assertIn('$ node --test --test-reporter=tap', labels)
            self.assertTrue(any('synthetic' in label for label in labels))
            self.assertEqual(labels[-1], 'Test process exited with code 0')

    async def test_cancelled_test_runner_terminates_process_before_returning(self):
        started=asyncio.Event()
        class Process:
            returncode=None
            pid=123
            stdout=None
        process=Process()
        class Output:
            async def read(self,_): started.set(); await asyncio.Future()
        process.stdout=Output()
        async def spawn(*args,**kwargs): return process
        stopped=[]
        async def terminate(p): stopped.append(p); p.returncode=-1
        async def progress(_): pass
        with patch.object(worker.asyncio,'create_subprocess_exec',side_effect=spawn),patch.object(worker,'terminate',side_effect=terminate):
            task=asyncio.create_task(worker.run_tests(ROOT,'node',progress)); await started.wait(); task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(stopped,[process])
