"""Runs the terminal's real fixed command on temporary E-drive fixtures. No GUI."""
import contextlib
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from app.config import ROOT,settings
from app.core.invoice_presentation import REGRESSION_FILE,REGRESSION_SOURCE,task_payload,validate_task,read_result
from app.services.invoice_faults import FIXED_SOURCE

class TerminalVerificationTests(unittest.TestCase):
    def test_real_terminal_runner_pass_failure_stale_result_and_task_boundaries(self):
        with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as temporary:
            root=Path(temporary);project=root/'data'/'projects'/'invoice-showcase';project.mkdir(parents=True)
            (root/'scripts').mkdir();(root/'.cache'/'tmp').mkdir(parents=True)
            shutil.copyfile(ROOT/'scripts'/'invoice-terminal.cjs',root/'scripts'/'invoice-terminal.cjs')
            for name in ('invoice.test.js','package.json'): shutil.copyfile(ROOT/'demo'/'invoice-showcase'/name,project/name)
            (project/'invoice.js').write_text(FIXED_SOURCE,encoding='utf-8')
            (project/REGRESSION_FILE).write_text(REGRESSION_SOURCE,encoding='utf-8')
            run_id='a'*32
            command=[shutil.which('node'),str(root/'scripts'/'invoice-terminal.cjs'),run_id]
            run=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('All tests passed (8/8).',run.stdout);self.assertIn('# pass 8',run.stdout)
            version=hashlib.sha256((project/'invoice.js').read_bytes()).hexdigest()
            self.assertTrue(read_result(root,run_id,version)['verified'])
            with self.assertRaisesRegex(ValueError,'source version'):read_result(root,run_id,'stale')
            config=task_payload(root,shutil.which('node'),run_id)
            self.assertEqual(validate_task(root,shutil.which('node'),config),run_id)
            config['tasks'][0]['args'][0]='arbitrary.js'
            with self.assertRaisesRegex(ValueError,'preserved'):validate_task(root,shutil.which('node'),config)
            shutil.copyfile(ROOT/'demo'/'invoice-showcase'/'invoice.js',project/'invoice.js')
            command[-1]='b'*32
            failed=subprocess.run(command,capture_output=True,text=True,timeout=30)
            self.assertEqual(failed.returncode,1);self.assertNotIn('All tests passed',failed.stdout)
            bad=json.loads((root/'.cache'/'invoice-terminal'/('b'*32+'.json')).read_text())
            self.assertFalse(bad['verified'])
