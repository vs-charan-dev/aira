"""Offline voice-to-browser wiring; no GUI, caption fetch or Gemini request."""
import asyncio
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.agents.tools.tools import CAPTURE_LIVE_TOOLS, RECALL_LIVE_TOOLS
from app.services.task_supervisor import TASK_NAMES, TaskSupervisor, execute_task_tool

URL='https://www.youtube.com/watch?v=abcdefghijk'
OBSERVED={'status':'succeeded','message':'Selected owned video read.',
          'data':{'videoUrl':URL,'title':'Observed title'}}


class YoutubeVoiceTests(unittest.IsolatedAsyncioTestCase):
    def supervisor(self):
        store=SimpleNamespace(save=Mock())
        return TaskSupervisor(store, desktop=AsyncMock(return_value=OBSERVED))

    async def test_url_reader_is_exposed_to_both_voice_modes(self):
        for tools in (CAPTURE_LIVE_TOOLS,RECALL_LIVE_TOOLS):
            names=[tool['name'] for tool in tools]
            self.assertEqual(names.count('current_youtube_video'),1)
            self.assertIn('youtube_study',names)
        self.assertIn('current_youtube_video',TASK_NAMES)

    async def test_url_question_returns_observed_data_without_creating_job(self):
        supervisor=self.supervisor()
        with patch('app.services.task_supervisor.get_supervisor',return_value=supervisor):
            result=json.loads(await execute_task_tool('local','current_youtube_video',{}))
        self.assertEqual(result,OBSERVED)
        supervisor.desktop.assert_awaited_once_with('local','current_youtube_video',{},source='job',detailed=True)
        supervisor.store.save.assert_not_called()

    async def test_url_read_during_navigation_is_busy_without_racing(self):
        supervisor=self.supervisor()
        async with supervisor.lock('local','desktop'):
            with patch('app.services.task_supervisor.get_supervisor',return_value=supervisor):
                result=json.loads(await execute_task_tool('local','current_youtube_video',{}))
        self.assertEqual(result['status'],'busy')
        supervisor.desktop.assert_not_awaited()

    async def test_summary_without_url_reads_selected_tab_before_generation(self):
        supervisor=self.supervisor()
        row={'id':'offline-study','user':'local','lane':'study','status':'queued',
             'tool':'youtube_study','action':{'videoUrl':None,'output':'summary'},
             'revisions':[],'completedRuns':0}
        supervisor.store.get=lambda user,ident: row
        connection=object()
        supervisor.connections[row['id']]=connection
        async def study(actual,progress,store):
            self.assertEqual(actual['action']['videoUrl'],URL)
            self.assertEqual(actual['action']['title'],'Observed title')
            self.assertFalse(supervisor.lock('local','desktop').locked())
            return {'status':'succeeded','message':'Offline summary finished.'}
        # Isolate wiring from the provider SDK and caption-worker implementation.
        with patch('app.services.task_supervisor.manager.get_connection',return_value=connection), \
             patch.dict(sys.modules,{'app.services.youtube_study':SimpleNamespace(run_study=study)}):
            await asyncio.wait_for(supervisor.run('local',row['id']),2)
        supervisor.desktop.assert_awaited_once()
        self.assertEqual(row['status'],'succeeded')


if __name__=='__main__':
    unittest.main()
