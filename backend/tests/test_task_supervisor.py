import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.config import settings
from app.services.task_store import TaskStore
from app.services.task_supervisor import TaskSupervisor


class SupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def test_maps_jobs_run_in_desktop_lane_with_verified_browser_report(self):
        self.s.desktop=AsyncMock(return_value={'status':'succeeded','message':'Maps page verified.','data':{}})
        for tool,args in [('open_maps',{}),('search_maps',{'query':'Hyderabad'})]:
            row=await self.s.submit('local',tool,args)
            await self.wait_done(row)
            result=self.store.get('local',row['id'])
            self.assertEqual(result['lane'],'desktop')
            self.assertIn('Google Maps',result['title'])
            self.assertEqual(result['status'],'succeeded')
            self.assertTrue(result['report']['verified'])
        self.assertEqual([call.args[1] for call in self.s.desktop.await_args_list],['open_maps','search_maps'])

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.store = TaskStore(Path(self.temp.name) / 'jobs.sqlite3')
        self.connection = object()
        self.connection_patch = patch('app.services.task_supervisor.manager.get_connection', return_value=self.connection)
        self.connection_patch.start()
        self.project_patch = patch('app.services.task_supervisor.validate_project', side_effect=lambda **kwargs: kwargs)
        self.project_patch.start()
        self.release, self.code_release = asyncio.Event(), asyncio.Event()
        self.desktop_started, self.code_started = asyncio.Event(), asyncio.Event()
        self.calls = []
        async def desktop(user, tool, args, **kwargs):
            self.calls.append((tool,args)); self.desktop_started.set()
            await self.release.wait()
            return 'Desktop action succeeded: synthetic verified result'
        async def coding(row, progress):
            self.code_started.set(); await progress('Synthetic coding progress')
            await self.code_release.wait()
            return {'status':'succeeded','message':'Synthetic tests passed','report':{'workerSession':'ses_test','verified':True}}
        self.s = TaskSupervisor(self.store, desktop, coding)

    async def asyncTearDown(self):
        await self.s.close()
        self.project_patch.stop(); self.connection_patch.stop(); self.temp.cleanup()

    async def wait_done(self, row):
        task = self.s.tasks.get(row['id'])
        if task: await asyncio.wait_for(task, 1)
        return self.s.get('local', row['id'])

    async def note(self, title='Demo'):
        return await self.s.submit('local','create_notion_note',{'title':title,'content':'Literal test content'})

    async def test_two_lanes_overlap_but_desktop_jobs_serialize(self):
        first = await self.note()
        await self.desktop_started.wait()
        second = await self.note('Second')
        code = await self.s.submit('local','coding_task',{'task':'Investigate a failure'})
        await self.code_started.wait()
        self.assertEqual(self.s.get('local',first['id'])['status'],'running')
        self.assertEqual(self.s.get('local',code['id'])['status'],'running')
        self.assertEqual(self.s.get('local',second['id'])['status'],'queued')
        self.assertEqual(len(self.calls),1)
        self.release.set(); self.code_release.set()
        for row in (first,second,code): self.assertEqual((await self.wait_done(row))['status'],'succeeded')
        self.assertEqual(len(self.calls),2)

    async def test_running_note_update_is_follow_up_never_second_creation(self):
        row = await self.note()
        await self.desktop_started.wait()
        await self.s.control('local',row['id'],'update','Change the existing note title to Demo Plan')
        self.assertEqual(len(self.calls),1)
        self.release.set()
        result = await self.wait_done(row)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual([c[0] for c in self.calls],['create_notion_note','desktop_task'])
        self.assertIn('Do not create a duplicate',self.calls[1][1]['task'])
        self.assertIn('Demo Plan',self.calls[1][1]['task'])
        self.assertFalse(result['revisions'])

    async def test_pause_resume_partial_note_inspects_instead_of_recreating(self):
        row=await self.note(); await self.desktop_started.wait()
        paused=await self.s.control('local',row['id'],'pause')
        self.assertEqual(paused['status'],'paused'); self.assertTrue(paused['partial'])
        await self.s.control('local',row['id'],'resume'); self.release.set()
        self.assertEqual((await self.wait_done(row))['status'],'succeeded')
        self.assertEqual([c[0] for c in self.calls],['create_notion_note','desktop_task'])

    async def test_cancelling_one_job_does_not_stop_other_lane_and_stop_all_cancels_queue(self):
        row=await self.note(); await self.desktop_started.wait()
        code=await self.s.submit('local','coding_task',{'task':'Fix explicitly requested error'}); await self.code_started.wait()
        await self.s.control('local',code['id'],'cancel')
        self.assertEqual(self.s.get('local',row['id'])['status'],'running')
        queued=await self.note('Queued')
        await self.s.cancel_all('local')
        for r in (row,code,queued): self.assertEqual(self.s.get('local',r['id'])['status'],'cancelled')
        self.assertEqual(len(self.calls),1)

    async def test_queued_update_is_not_lost_and_request_id_is_idempotent(self):
        first=await self.note(); await self.desktop_started.wait()
        args={'title':'Second','content':'body'}
        row=await self.s.submit('local','create_notion_note',args,'same-request')
        duplicate=await self.s.submit('local','create_notion_note',args,'same-request')
        self.assertEqual(row['id'],duplicate['id'])
        await self.s.control('local',row['id'],'update','Retitle existing note to Updated')
        self.release.set(); await self.wait_done(first); result=await self.wait_done(row)
        self.assertEqual(len(self.calls),3); self.assertEqual(result['completedRuns'],2)
        self.assertIn('Updated',self.calls[-1][1]['task'])

    async def test_replaced_connection_never_starts_queued_work_and_other_user_cannot_control(self):
        first=await self.note(); await self.desktop_started.wait()
        queued=await self.note('Queued')
        with self.assertRaises(ValueError): await self.s.control('other',first['id'],'cancel')
        with patch('app.services.task_supervisor.manager.get_connection',return_value=object()):
            self.release.set(); await self.wait_done(first); result=await self.wait_done(queued)
        self.assertEqual(result['status'],'needs_attention'); self.assertEqual(len(self.calls),1)

    async def test_restart_marks_unfinished_work_without_replay(self):
        row=await self.note(); await self.desktop_started.wait()
        reloaded=TaskStore(self.store.path)
        self.assertEqual(reloaded.get('local',row['id'])['status'],'needs_attention')
        self.assertEqual(len(self.calls),1)

    async def test_completed_task_update_runs_follow_up_and_cancel_is_final(self):
        self.release.set(); row=await self.note(); await self.wait_done(row)
        await self.s.control('local',row['id'],'update','Retitle existing note')
        await self.wait_done(row)
        self.assertEqual(self.calls[-1][0],'desktop_task')
        await self.s.control('local',row['id'],'cancel')
        with self.assertRaises(ValueError): await self.s.control('local',row['id'],'resume')

    async def test_coding_follow_up_reuses_worker_session(self):
        sessions=[]
        async def worker(row,progress):
            sessions.append(row.get('workerSession'))
            return {'status':'succeeded','message':'Checked','report':{'workerSession':'ses_known','verified':True}}
        self.s.coding=worker
        row=await self.s.submit('local','coding_task',{'task':'Investigate'})
        await self.wait_done(row)
        await self.s.control('local',row['id'],'update','Now fix the identified bug')
        await self.wait_done(row)
        self.assertEqual(sessions,[None,'ses_known'])

    async def test_quick_app_and_folder_requests_queue_behind_note_and_have_fixed_targets(self):
        note=await self.note();await self.desktop_started.wait()
        app=await self.s.submit('local','open_app',{'app_name':'Notion'})
        folder=await self.s.submit('local','open_folder',{'path':'E:/example'})
        self.assertEqual(self.s.get('local',app['id'])['status'],'queued')
        with self.assertRaises(ValueError): await self.s.control('local',app['id'],'update','Open another app')
        self.release.set()
        for row in (note,app,folder): self.assertEqual((await self.wait_done(row))['status'],'succeeded')
        self.assertEqual([c[0] for c in self.calls],['create_notion_note','open_app','open_folder'])

    async def test_shutdown_cancels_running_and_not_yet_started_jobs_and_releases_owner(self):
        first=await self.note();await self.desktop_started.wait()
        second=await self.note('Queued at shutdown')
        await self.s.close()
        for row in (first,second): self.assertEqual(self.s.get('local',row['id'])['status'],'cancelled')
        await asyncio.sleep(0)
        self.assertFalse(self.s.tasks);self.assertFalse(self.s.connections);self.assertFalse(self.s.owners)

    async def test_invoice_repair_opens_source_before_editing_then_returns_only_after_verification(self):
        order=[]
        async def desktop(user,tool,args,**kwargs):
            order.append((tool,args)); return 'Desktop action succeeded: observed window'
        async def coding(row,progress):
            order.append(('coding',row['instruction']))
            self.assertEqual(row['mode'],'fix')
            return {'status':'succeeded','message':'Selected tests passed.','report':{'verified':True,'summary':'The source used a flat discount.'}}
        self.s.desktop=desktop;self.s.coding=coding;self.s.invoice_coding=coding
        from app.services import invoice_demo,repair_notification
        with patch.object(invoice_demo,'prepare',return_value={'path':str(Path(self.temp.name)/'invoice-showcase')}),patch.object(invoice_demo,'generation_for',return_value='synthetic-generation'),patch.object(repair_notification,'announce_repair',return_value=True) as notification:
            row=await self.s.submit('local','repair_invoice_app',{'problem':'Ten percent off gives the wrong total. Please fix it.'})
            result=await self.wait_done(row)
        self.assertEqual([item[0] for item in order],['show_coding_project','coding','show_invoice_demo'])
        self.assertEqual(order[0][1]['file'],'invoice.js')
        self.assertIn('Ten percent off gives the wrong total',order[1][1])
        self.assertNotIn('price *',order[1][1])
        self.assertEqual(result['status'],'succeeded');self.assertTrue(result['report']['presentationReturned'])
        notification.assert_awaited_once()

    async def test_invoice_editor_failure_prevents_edits_and_failed_tests_do_not_return_success(self):
        from app.services import invoice_demo,repair_notification
        calls=[]
        async def desktop(user,tool,args,**kwargs):
            calls.append(tool);return 'Desktop action failed: editor unavailable'
        async def coding(row,progress): calls.append('coding');return {'status':'needs_attention','message':'Tests failed','report':{'verified':False}}
        self.s.desktop=desktop;self.s.coding=coding;self.s.invoice_coding=coding
        with patch.object(invoice_demo,'prepare',return_value={'path':str(Path(self.temp.name)/'invoice-showcase')}),patch.object(invoice_demo,'generation_for',return_value='synthetic-generation'),patch.object(repair_notification,'announce_repair',return_value=True) as notification:
            row=await self.s.submit('local','repair_invoice_app',{'problem':'Wrong invoice total'})
            self.assertEqual((await self.wait_done(row))['status'],'needs_attention')
            self.assertEqual(calls,['show_coding_project'])
            async def shown(*args,**kwargs): calls.append('show_coding_project');return 'Desktop action succeeded: editor shown'
            self.s.desktop=shown
            row=await self.s.submit('local','repair_invoice_app',{'problem':'Wrong invoice total'})
            self.assertEqual((await self.wait_done(row))['status'],'needs_attention')
            self.assertEqual(calls[-2:],['show_coding_project','coding'])
            notification.assert_not_awaited()

    async def test_generic_fix_for_registered_demo_routes_to_deterministic_runner_and_freezes_mode(self):
        from app.services import invoice_demo,repair_notification
        chosen=[]
        async def agent(row,progress): raise AssertionError('OpenCode should not run in demo mode')
        async def deterministic(row,progress):
            chosen.append(row['invoiceRepairMode'])
            return {'status':'succeeded','message':'Five tests passed','report':{'verified':True}}
        async def desktop(*args,**kwargs): return 'Desktop action succeeded: synthetic window'
        self.s.coding=agent;self.s.invoice_coding=deterministic;self.s.desktop=desktop
        with patch.object(invoice_demo,'generation_for',return_value='known-generation'),patch.object(settings,'aira_invoice_repair_mode','deterministic'),patch.object(repair_notification,'announce_repair',return_value=True):
            row=await self.s.submit('local','coding_task',{'mode':'fix','task':'The application in VS Code has an error; fix it.'})
            self.assertEqual(row['tool'],'repair_invoice_app')
            with patch.object(settings,'aira_invoice_repair_mode','agent'):
                self.assertEqual((await self.wait_done(row))['status'],'succeeded')
        self.assertEqual(chosen,['deterministic'])

    async def test_changing_queued_demo_to_investigation_does_not_apply_scripted_fix(self):
        from app.services import invoice_demo
        modes=[]
        async def agent(row,progress):
            modes.append(row['mode'])
            return {'status':'succeeded','message':'Inspection only','report':{'verified':False}}
        async def deterministic(*args): raise AssertionError('Investigation cannot apply a scripted edit')
        async def desktop(*args,**kwargs): return 'Desktop action succeeded: synthetic window'
        self.s.coding=agent;self.s.invoice_coding=deterministic;self.s.desktop=desktop
        with patch.object(invoice_demo,'generation_for',return_value='known-generation'),patch.object(settings,'aira_invoice_repair_mode','deterministic'):
            row=await self.s.submit('local','coding_task',{'mode':'fix','task':'Fix the invoice'})
            await self.s.control('local',row['id'],'update','Inspect only; do not edit',mode='investigate')
            self.assertEqual((await self.wait_done(row))['status'],'succeeded')
        self.assertEqual(modes,['investigate'])

    async def test_generated_tests_require_visible_terminal_success_before_browser_return(self):
        from app.services import invoice_demo,repair_notification
        from app.core import invoice_presentation
        steps=[]
        terminal_ok=True
        async def desktop(user,tool,args,**kwargs):
            steps.append(tool)
            return 'Desktop action succeeded: synthetic result' if tool!='run_invoice_tests' or terminal_ok else 'Desktop action failed: terminal unavailable'
        async def deterministic(row,progress):
            steps.append('write_regression_and_fix')
            return {'status':'succeeded','message':'Local tests passed','report':{'verified':True,'demoVersion':'v','terminalRunId':'a'*32,'generatedTestFiles':['invoice.regression.test.js']}}
        self.s.desktop=desktop;self.s.invoice_coding=deterministic
        with patch.object(invoice_demo,'generation_for',return_value='known'),patch.object(settings,'aira_invoice_repair_mode','deterministic'),patch.object(invoice_demo,'version',return_value='v'),patch.object(invoice_presentation,'read_result',return_value={'verified':True,'passed':8}),patch.object(repair_notification,'announce_repair',return_value=True):
            row=await self.s.submit('local','coding_task',{'mode':'fix','task':'Fix invoice'})
            done=await self.wait_done(row)
            self.assertEqual(done['status'],'succeeded')
            self.assertEqual(steps,['show_coding_project','write_regression_and_fix','run_invoice_tests','show_invoice_demo'])
            self.assertEqual(done['report']['terminalVerification']['passed'],8)
            steps.clear();terminal_ok=False
            row=await self.s.submit('local','coding_task',{'mode':'fix','task':'Fix invoice again'})
            done=await self.wait_done(row)
            self.assertEqual(done['status'],'needs_attention');self.assertNotIn('show_invoice_demo',steps)
            self.assertEqual(done['report']['generatedTestFiles'],['invoice.regression.test.js'])
