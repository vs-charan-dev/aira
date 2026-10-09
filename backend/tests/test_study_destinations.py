"""Offline exports, ownership, queueing and cancellation; no GUI/provider calls."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.config import settings
from app.services.task_store import TaskStore
from app.services.task_supervisor import TaskSupervisor, TASK_NAMES
from app.services.study_destinations import export_summary, mindmap_action
from app.services.desktop_action_service import validate_action

VIDEO='https://www.youtube.com/watch?v=abcdefghijk'
NOTEBOOK='https://notebook.google.com/notebook/abc-123'


class Destinations(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.folder=Path(self.temp.name)
        self.store=TaskStore(self.folder/'tasks.sqlite3')
        self.summary=self.folder/'summary.md'
        self.summary.write_text('# All points\n\nOverview.\n\n- First point\n- Second point\n\nSource: '+VIDEO+'\n\nCaveat: uncertain.\n',encoding='utf-8')
        self.media=patch('app.services.study_destinations.resolve_media',return_value=self.summary);self.media.start()
        self.connection=object()
        self.conn=patch('app.services.task_supervisor.manager.get_connection',return_value=self.connection);self.conn.start()
        self.calls=[]
        async def desktop(user,tool,args,**kwargs):
            self.calls.append((tool,args,kwargs))
            if tool=='current_youtube_video':return {'status':'succeeded','message':'Observed','data':{'videoUrl':VIDEO,'title':'Video'}}
            return {'status':'succeeded','message':'Verified fixture','data':{'notebookUrl':NOTEBOOK} if tool=='notebooklm_mindmap' else {'notionPageId':'a'*32,'destinationTitle':'All points'}}
        self.s=TaskSupervisor(self.store,desktop)
        self.seed()

    def seed(self,ident='a'*10,status='succeeded',created=1):
        row={'id':ident,'user':'local','tool':'youtube_study','status':status,'createdAt':created,'action':{'output':'summary'},
             'report':{'kind':'youtube','videoTitle':'All points','sourceUrl':VIDEO,'summary':'Only overview',
                       'assets':{'summary':'/media/youtube/jobs/'+ident+'/summary.md'}}}
        self.store.save(row);return row

    async def asyncTearDown(self):
        await self.s.close();self.conn.stop();self.media.stop();self.temp.cleanup()

    async def done(self,row):
        task=self.s.tasks.get(row['id'])
        if task: await asyncio.wait_for(task,2)
        return self.s.get('local',row['id'])

    async def test_full_file_is_exported_instead_of_model_overview(self):
        row=await self.s.submit('local','export_summary_to_notion',{'destination':'existing','content':'Invented overview'})
        finished=await self.done(row)
        self.assertEqual(finished['status'],'succeeded')
        content=self.calls[0][1]['content']
        for expected in ('First point','Second point','Caveat: uncertain.',VIDEO):self.assertIn(expected,content)
        self.assertNotIn('Invented',content);self.assertNotIn('Only overview',content)
        self.assertTrue(finished['report']['verified']);self.assertEqual(finished['report']['studyTaskId'],'a'*10)

    async def test_incomplete_latest_summary_does_not_export_an_older_one(self):
        self.seed('b'*10,'running',2)
        with self.assertRaisesRegex(ValueError,'not ready'): export_summary(self.store,'local',{'destination':'new'})
        selected=export_summary(self.store,'local',{'destination':'new','study_task_id':'a'*10})
        self.assertEqual(selected['studyTaskId'],'a'*10)
        with self.assertRaises(ValueError): export_summary(self.store,'other',{'study_task_id':'a'*10})

    async def test_overlong_file_rejected_without_truncation(self):
        self.summary.write_text('x'*20001)
        with self.assertRaisesRegex(ValueError,'not truncated'): export_summary(self.store,'local',{})

    async def test_missing_video_is_observed_inside_desktop_lane_without_deadlock(self):
        row=await self.s.submit('local','notebooklm_mindmap',{})
        finished=await self.done(row)
        self.assertEqual(finished['status'],'succeeded')
        self.assertEqual([c[0] for c in self.calls],['current_youtube_video','notebooklm_mindmap'])
        self.assertEqual(self.calls[-1][1]['videoUrl'],VIDEO)
        self.assertTrue(self.calls[-1][1]['newNotebook'])
        self.assertEqual(finished['report']['notebookUrl'],NOTEBOOK)

    async def test_partial_destination_cannot_be_resumed_or_updated(self):
        row=await self.s.submit('local','notebooklm_mindmap',{'video_url':VIDEO})
        await self.done(row)
        self.s.save(row,status='needs_attention',partial=True)
        with self.assertRaisesRegex(ValueError,'never automatically repeats'):await self.s.control('local',row['id'],'resume')
        with self.assertRaisesRegex(ValueError,'fixed target'):await self.s.control('local',row['id'],'update','Again')
        self.assertEqual(len(self.calls),1)

    async def test_boundaries_reject_unrelated_urls_and_targets(self):
        for uri in ('http://notebooklm.google.com/notebook/abc','https://accounts.google.com/','https://notebooklm.google.com.evil.test/notebook/a','https://notebook.google.com/notebook/a/../../bad'):
            with self.assertRaises(ValueError):mindmap_action({'notebook_url':uri})
        with self.assertRaises(ValueError):mindmap_action({'notebook_url':NOTEBOOK,'new_notebook':True})
        value=export_summary(self.store,'local',{'destination':'existing','page_name':'Project Docs'})
        self.assertEqual(validate_action('export_summary_to_notion',value)['pageName'],'Project Docs')
        self.assertIn('notebooklm_mindmap',TASK_NAMES);self.assertIn('export_summary_to_notion',TASK_NAMES)


if __name__=='__main__':unittest.main()
