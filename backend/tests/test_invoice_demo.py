import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import settings
from app.services import invoice_demo as demo
from app.services.coding_worker import run_tests, has_tests
from app.services import coding_worker as worker


class InvoiceDemoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.target = Path(self.temp.name) / 'invoice-showcase'
        self.folder_patch = patch.object(demo, 'folder', return_value=self.target)
        self.folder_patch.start()

    async def asyncTearDown(self):
        self.folder_patch.stop(); self.temp.cleanup()

    async def test_real_preview_and_independent_tests_follow_source_fix_then_reset(self):
        original = demo.prepare()
        value = await demo.evaluate(200, 10, original['version'])
        self.assertEqual(value['total'], 190); self.assertFalse(value['matches'])
        labels=[]
        async def progress(value): labels.append(value)
        before = await run_tests(self.target, 'node', progress)
        self.assertEqual(before['exitCode'], 1); self.assertIn('# fail 4', before['output'])
        (self.target/'invoice.js').write_text('export function invoiceTotal(p,d){return p*(1-d/100);}',encoding='utf-8')
        fixed = demo.status()
        value = await demo.evaluate(200, 10, fixed['version'])
        self.assertEqual(value['total'], 180); self.assertTrue(value['matches'])
        after = await run_tests(self.target, 'node', progress)
        self.assertEqual(after['exitCode'],0); self.assertTrue(has_tests(after['output'])); self.assertIn('# pass 5',after['output'])
        self.assertEqual(demo.prepare()['version'], fixed['version'])  # Open/select never resets.
        reset = demo.prepare(True)
        self.assertNotEqual(reset['generation'],original['generation'])
        self.assertEqual(reset['version'], original['version'])
        self.assertFalse((await demo.evaluate(200,10,reset['version']))['matches'])

    async def test_invalid_input_stale_source_and_syntax_errors_never_report_success(self):
        info=demo.prepare()
        for price,discount in ((True,10),(200,float('nan')),(-1,10),(100,101)):
            with self.assertRaises(ValueError): await demo.evaluate(price,discount,info['version'])
        with self.assertRaisesRegex(ValueError,'source changed'): await demo.evaluate(200,10,'outdated')
        (self.target/'invoice.js').write_text('broken syntax !',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'preview failed'): await demo.evaluate(200,10,demo.version())

    def test_reset_refuses_unmanaged_folder_extra_files_and_links(self):
        self.target.mkdir(); (self.target/'invoice.js').write_text('preserve me')
        with self.assertRaisesRegex(ValueError,'not managed'): demo.prepare(True)
        self.assertEqual((self.target/'invoice.js').read_text(),'preserve me')
        (self.target/'invoice.js').unlink(); self.target.rmdir()
        demo.prepare(); (self.target/'extra.txt').write_text('preserve me')
        with self.assertRaisesRegex(ValueError,'extra files'): demo.prepare(True)
        self.assertEqual((self.target/'extra.txt').read_text(),'preserve me')
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaisesRegex(ValueError,'linked'): demo.status()

    async def test_cancellation_terminates_preview_process(self):
        demo.prepare(); started=asyncio.Event(); stopped=[]
        class Input:
            def write(self,value): pass
            async def drain(self): pass
            def close(self): pass
        class Output:
            async def read(self,size): started.set(); await asyncio.Future()
        class Process:
            stdin=Input(); stdout=Output(); returncode=None
        process=Process()
        async def terminate(value): stopped.append(value); value.returncode=-1
        with patch.object(demo.asyncio,'create_subprocess_exec',return_value=process),patch.object(demo,'terminate',side_effect=terminate):
            task=asyncio.create_task(demo.evaluate(200,10,demo.version()))
            await started.wait(); task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual(stopped,[process])

    async def test_worker_reports_real_before_after_tests_diff_and_source_fingerprint(self):
        info=demo.prepare(); original_spawn=asyncio.create_subprocess_exec
        lines=[json.dumps({'type':'tool_use','part':{'tool':'edit'}}).encode()+b'\n',
               json.dumps({'type':'text','sessionID':'ses_fixture','part':{'text':'Corrected the percentage calculation; AIRA must verify tests.'}}).encode()+b'\n']
        class Input:
            def write(self,value): pass
            async def drain(self): pass
            def close(self): pass
        class Output:
            async def readline(self): return lines.pop(0) if lines else b''
        class Process:
            stdin=Input();stdout=Output();returncode=0
            async def wait(self): return 0
        async def spawn(*args,**kwargs):
            if str(args[0])==str(worker.BINARY):
                (self.target/'invoice.js').write_text('export function invoiceTotal(p,d){return p-p*d/100;}',encoding='utf-8')
                return Process()
            return await original_spawn(*args,**kwargs)
        labels=[]
        async def progress(value): labels.append(value)
        job={'id':'offline-demo','user':'local','instruction':'Fix the percentage calculation','mode':'fix',
             'project':{'path':str(self.target),'runner':'node'},'demoGeneration':info['generation']}
        with patch.object(worker,'validate_project',side_effect=lambda path,runner:{'path':path,'runner':runner}),patch.object(worker,'get_user_gemini_key',return_value='synthetic-never-sent'),patch.object(worker.asyncio,'create_subprocess_exec',side_effect=spawn):
            result=await worker.run_coding(job,progress)
        report=result['report']
        self.assertEqual(result['status'],'succeeded');self.assertTrue(report['verified'])
        self.assertEqual(report['beforeTests']['exitCode'],1);self.assertEqual(report['tests']['exitCode'],0)
        self.assertEqual(report['changedFiles'],['invoice.js']);self.assertIn('before/invoice.js',report['diff'])
        self.assertEqual(report['demoVersion'],demo.version())
        self.assertTrue(any(label.startswith('$ opencode run') for label in labels))
        self.assertIn('AFTER · verifying source changes',labels)
