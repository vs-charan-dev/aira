"""Mocked VS Code input; no GUI or account changes."""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from app.config import ROOT,settings
from app.core.invoice_presentation import REGRESSION_FILE,REGRESSION_SOURCE,task_payload
from app.services import invoice_demo
from app.services.invoice_faults import FIXED_SOURCE

sys.path.insert(0,str(ROOT/'desktop'))
from invoice_control import run_tests_in_editor

class EditorTests(unittest.TestCase):
    def test_fixed_build_shortcut_and_result_check_with_foreground_guards(self):
        with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as temporary:
            root=Path(temporary);project=root/'data'/'projects'/'invoice-showcase';project.mkdir(parents=True)
            for name in ('invoice.test.js','package.json'):shutil.copyfile(invoice_demo.TEMPLATE/name,project/name)
            (project/'invoice.js').write_text(FIXED_SOURCE,encoding='utf-8')
            (project/REGRESSION_FILE).write_text(REGRESSION_SOURCE,encoding='utf-8')
            (project/invoice_demo.MARKER).write_text(json.dumps({'schema':invoice_demo.SCHEMA,'generation':'a'*32}))
            (project/'.vscode').mkdir();run_id='b'*32
            task=project/'.vscode'/'tasks.json';task.write_text(json.dumps(task_payload(root,shutil.which('node'),run_id)))
            calls=[]
            def inject(*keys):
                calls.append(keys)
                result=root/'.cache'/'invoice-terminal'/(run_id+'.json');result.parent.mkdir(parents=True)
                result.write_text(json.dumps({'runId':run_id,'sourceVersion':hashlib.sha256((project/'invoice.js').read_bytes()).hexdigest(),'verified':True,'exitCode':0,'tests':8,'passed':8}))
            api=SimpleNamespace(ROOT=root,ActionError=ValueError,foreground=lambda:1,process_name=lambda handle:'code.exe',
                user32=SimpleNamespace(GetWindowTextW=lambda handle,title,size:setattr(title,'value','invoice.regression.test.js — invoice-showcase')),
                wait=lambda callback,seconds:callback(),progress=lambda label:None,key=lambda vk,flags=0:(vk,flags),inject=inject)
            with patch.object(invoice_demo,'folder',return_value=project),patch.dict('sys.modules',{'code_project':SimpleNamespace(find_code=lambda:root/'Code.exe')}),patch('invoice_control.subprocess.Popen') as launch,patch('invoice_control.time.sleep'):
                self.assertIn('all eight tests',run_tests_in_editor(api,run_id))
                self.assertEqual(calls[0],((0x11,0),(0x10,0),(0x42,0),(0x42,2),(0x10,2),(0x11,2)))
                self.assertFalse(launch.call_args.kwargs['shell'])
                self.assertIn('invoice.regression.test.js',launch.call_args.args[0][-1])
                task.write_text(json.dumps({'tasks':[{'args':['malicious.js',run_id]}]}))
                with self.assertRaisesRegex(ValueError,'preserved'):run_tests_in_editor(api,run_id)
                self.assertEqual(len(calls),1)
