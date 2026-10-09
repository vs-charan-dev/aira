import asyncio
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import settings
from app.services import invoice_demo as demo, invoice_faults as faults


class DeterministicInvoiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.target=Path(self.temp.name)/'invoice-showcase'
        self.folder_patch=patch.object(demo,'folder',return_value=self.target);self.folder_patch.start()
        self.busy_patch=patch.object(faults,'assert_not_busy');self.busy_patch.start()
        self.info=demo.prepare()
        self.job={'id':'synthetic','project':{'path':str(self.target),'runner':'node'},'demoGeneration':self.info['generation']}
        self.labels=[]

    async def asyncTearDown(self):
        self.busy_patch.stop();self.folder_patch.stop();self.temp.cleanup()

    async def progress(self,label): self.labels.append(label)

    async def test_actual_source_preview_tests_and_repeatable_fault_without_any_coding_model(self):
        tests=(self.target/'invoice.test.js').read_bytes()
        with patch('app.services.coding_worker.get_user_gemini_key',side_effect=AssertionError('No coding API key should be read')):
            result=await faults.run_deterministic_repair(self.job,self.progress)
        report=result['report']
        self.assertTrue(report['verified']);self.assertEqual(report['executionMethod'],'deterministic_demo')
        self.assertEqual(report['beforeTests']['exitCode'],1);self.assertIn('# fail 4',report['beforeTests']['output'])
        self.assertEqual(report['tests']['exitCode'],0);self.assertIn('# pass 8',report['tests']['output'])
        self.assertEqual(report['changedFiles'],['invoice.js','invoice.regression.test.js']);self.assertIn('price * discountPercent / 100',report['diff'])
        self.assertTrue((self.target/'invoice.regression.test.js').is_file())
        self.assertIn('regression:',report['diff']);self.assertEqual(len(report['terminalRunId']),32)
        self.assertEqual((await demo.evaluate(200,10,demo.version()))['total'],180)
        self.assertEqual(tests,(self.target/'invoice.test.js').read_bytes())
        again=await faults.run_deterministic_repair(self.job,self.progress)
        self.assertTrue(again['report']['verified']);self.assertFalse(again['report']['sourceChanged'])
        recreated=faults.create_fault()
        self.assertFalse((self.target/'invoice.regression.test.js').exists())
        self.assertFalse((self.target/'.vscode').exists())
        self.assertNotEqual(recreated['generation'],self.job['demoGeneration'])
        self.assertEqual((await demo.evaluate(200,10,recreated['version']))['total'],190)
        self.job['demoGeneration']=recreated['generation']
        result=await faults.run_deterministic_repair(self.job,self.progress)
        self.assertTrue(result['report']['verified']);self.assertEqual((await demo.evaluate(1000,10,demo.version()))['total'],900)
        self.assertFalse(any('opencode' in label.lower() for label in self.labels))

    async def test_unknown_code_changed_tests_wrong_project_and_old_generation_are_not_overwritten(self):
        path=self.target/'invoice.js';path.write_text('export const invoiceTotal=()=>123;',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'known demo fault'): await faults.run_deterministic_repair(self.job,self.progress)
        self.assertEqual(path.read_text(),'export const invoiceTotal=()=>123;')
        faults.create_fault();self.job['demoGeneration']=demo.metadata()['generation']
        (self.target/'invoice.test.js').write_text('// changed tests',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'tests or package'): await faults.run_deterministic_repair(self.job,self.progress)
        (self.target/'invoice.test.js').write_bytes((demo.TEMPLATE/'invoice.test.js').read_bytes())
        with self.assertRaisesRegex(ValueError,'registered invoice'): await faults.run_deterministic_repair({**self.job,'project':{'path':str(self.target.parent),'runner':'node'}},self.progress)
        with self.assertRaisesRegex(ValueError,'reset after'): await faults.run_deterministic_repair({**self.job,'demoGeneration':'old'},self.progress)

    def test_second_writer_is_blocked_by_the_process_lease(self):
        with faults.lease():
            with self.assertRaisesRegex(ValueError,'busy'): faults.create_fault()

    async def test_cancelled_repair_releases_the_lease_and_keeps_original_source(self):
        async def stop(label): raise asyncio.CancelledError()
        before=faults.source()
        with self.assertRaises(asyncio.CancelledError): await faults.run_deterministic_repair(self.job,stop)
        self.assertEqual(faults.source(),before)
        with faults.lease(): pass

    async def test_rehearsal_cli_uses_the_same_real_fix_and_restores_the_fault(self):
        from invoice_fault_cli import run
        with contextlib.redirect_stdout(io.StringIO()) as output:
            await run('fix')
            self.assertEqual((await demo.evaluate(200,10,demo.version()))['total'],180)
            await run('create')
            self.assertEqual((await demo.evaluate(200,10,demo.version()))['total'],190)
        self.assertIn('Fault fixed:',output.getvalue())
        self.assertIn('Fault created:',output.getvalue())

    def test_cli_busy_guard_reads_the_ledger_without_changing_running_jobs(self):
        data=Path(self.temp.name)/'ledger'; (data/'db').mkdir(parents=True)
        path=data/'db'/'tasks.sqlite3'
        original=json.dumps({'id':'real','lane':'coding','status':'running'})
        with contextlib.closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE jobs (body TEXT)')
            db.execute('INSERT INTO jobs VALUES (?)',(original,))
            db.commit()
        with patch.object(settings,'aira_data_dir',data):
            # asyncSetUp mocks the guard for disposable fixtures; exercise the real guard here.
            self.busy_patch.stop()
            try:
                with self.assertRaisesRegex(ValueError,'coding job is active'): faults.assert_not_busy()
                faults.assert_not_busy('real')
            finally: self.busy_patch.start()
        with contextlib.closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('SELECT body FROM jobs').fetchone()[0],original)
