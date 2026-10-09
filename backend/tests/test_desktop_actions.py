import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from app.services import desktop_action_service as service
from app.agents.recall_agent import RecallAgent, _BASE_SYSTEM_PROMPT
from app.agents.capture_agent import CaptureAgent, _SYSTEM_PROMPT_TEMPLATE
from app.agents.tools.tools import RECALL_LIVE_TOOLS, CAPTURE_LIVE_TOOLS

class DesktopActions(unittest.IsolatedAsyncioTestCase):
    async def test_maps_validation_prompt_and_both_voice_mode_dispatch(self):
        for tools in (CAPTURE_LIVE_TOOLS, RECALL_LIVE_TOOLS):
            for name in ('open_maps','search_maps'):
                self.assertEqual(sum(t['name']==name for t in tools),1)
        self.assertIn('search_maps(query=X)',service.DESKTOP_PROMPT)
        self.assertEqual(service.validate_action('search_maps',{'query':' Café & Park '}),{'kind':'search_maps','query':'Café & Park'})
        for task in ('Search Google Maps for Hyderabad','Search for Hyderabad on Maps','Go to Google Chrome, go to Maps and search for Hyderabad'):
            self.assertEqual(service.validate_action('desktop_task',{'app_name':'Chrome','task':task}),{'kind':'search_maps','query':'Hyderabad'})
        self.assertEqual(service.validate_action('desktop_task',{'app_name':'Chrome','task':'Go to Maps'}),{'kind':'open_maps'})
        for query in ('',' ','x'*251,'Hyderabad\n',None):
            with self.assertRaises(ValueError):service.validate_action('search_maps',{'query':query})
        with patch('app.agents.recall_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as recall:
            await RecallAgent()._execute_tool('local','search_maps',{'query':'Hyderabad'},None)
            self.assertEqual(recall.await_args.args[1:3],('search_maps',{'query':'Hyderabad'}))
        agent=CaptureAgent('local','capture-maps',AsyncMock());agent._user_has_spoken=True
        with patch('app.agents.capture_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as capture:
            await agent._execute_tool('search_maps',{'query':'Hyderabad'})
            self.assertEqual(capture.await_args.args[1:3],('search_maps',{'query':'Hyderabad'}))

    async def test_validates_actions_and_publishes_no_invalid_request(self):
        with patch.object(service.manager, 'send', new_callable=AsyncMock) as send:
            for name,args in [('open_app',{'app_name':'Notion;calc'}),('open_folder',{'path':'\\\\host\\share'}),('open_folder',{'path':'E:\\x:stream'}),('shell',{})]:
                await service.request_desktop_action('local',name,args,source='recall')
            send.assert_not_awaited()
        self.assertEqual(service.validate_action('open_folder',{'path':'E:\\Havetobuild\\AIRA'})['kind'],'open_folder')

    async def test_only_origin_connection_and_matching_id_can_resolve(self):
        connection = object()
        with patch.object(service.manager,'get_connection',return_value=connection), patch.object(service.manager,'send',new_callable=AsyncMock,return_value=True) as send:
            pending = asyncio.create_task(service.request_desktop_action('local','open_app',{'app_name':'Notion'},source='recall'))
            await asyncio.sleep(0)
            message = send.await_args.args[1]
            ack={'requestId':message['requestId'],'status':'succeeded','message':'Notion verified.'}
            self.assertFalse(service.resolve_desktop_action('local',ack,object()))
            self.assertFalse(service.resolve_desktop_action('other',ack,connection))
            self.assertFalse(service.resolve_desktop_action('local',{**ack,'requestId':'stale'},connection))
            self.assertFalse(pending.done())
            self.assertTrue(service.resolve_desktop_action('local',ack,connection))
            self.assertIn('succeeded',await pending)
            self.assertFalse(service._pending)

    async def test_cancelled_live_task_cancels_native_request_and_rejects_overlap(self):
        connection=object()
        with patch.object(service.manager,'get_connection',return_value=connection), patch.object(service.manager,'send',new_callable=AsyncMock,return_value=True) as send:
            pending=asyncio.create_task(service.request_desktop_action('local','open_app',{'app_name':'Notion'},source='recall'))
            await asyncio.sleep(0)
            self.assertIn('Another',await service.request_desktop_action('local','open_app',{'app_name':'Calculator'},source='recall'))
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError): await pending
            self.assertEqual(send.await_args.args[1]['type'],'desktop_action_cancel')
            self.assertFalse(service._pending)

    async def test_both_live_agents_dispatch_tools_and_receive_prompt(self):
        with patch('app.agents.recall_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as recall:
            self.assertEqual(await RecallAgent()._execute_tool('local','open_app',{'app_name':'Notion'},None),'queued')
            recall.assert_awaited_once()
        agent=CaptureAgent('local','capture-1',AsyncMock()); agent._user_has_spoken=True
        with patch('app.agents.capture_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as capture:
            await agent._execute_tool('open_folder',{'path':'E:\\Havetobuild\\AIRA'})
            self.assertEqual(capture.await_args.args[0],'local')
        for tools,prompt in [(RECALL_LIVE_TOOLS,_BASE_SYSTEM_PROMPT),(CAPTURE_LIVE_TOOLS,_SYSTEM_PROMPT_TEMPLATE)]:
            for name in ('open_app','open_folder','create_notion_note','close_app','desktop_task'): self.assertEqual(sum(t['name']==name for t in tools),1)
            self.assertIn('Report success only',prompt)

    async def test_notion_payload_limits_and_dispatch(self):
        action = service.validate_action('create_notion_note', {'title':' Demo ', 'content':'Hello\nCharan'})
        self.assertEqual(action, {'kind':'create_notion_note','title':'Demo','content':'Hello\nCharan'})
        for args in [{'title':'', 'content':'Body'}, {'title':'x\nTitle', 'content':'Body'}, {'title':'T','content':'x'*2001}, {'title':'T','content':'\x00bad'}, {'title':None,'content':'Body'}]:
            with self.assertRaises(ValueError): service.validate_action('create_notion_note',args)
        with patch('app.agents.recall_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as recall:
            await RecallAgent()._execute_tool('local','create_notion_note',{'title':'Demo','content':'Body'},None)
            self.assertEqual(recall.await_args.args[1], 'create_notion_note')
        agent=CaptureAgent('local','capture-1',AsyncMock()); agent._user_has_spoken=True
        with patch('app.agents.capture_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as capture:
            await agent._execute_tool('create_notion_note',{'title':'Demo','content':'Body'})
            self.assertEqual(capture.await_args.args[1], 'create_notion_note')

    async def test_windows_use_validation_and_both_agent_dispatches(self):
        self.assertEqual(service.validate_action('close_app',{'app_name':'Notion'}),{'kind':'close_app','appName':'Notion'})
        action=service.validate_action('desktop_task',{'app_name':'Notepad','task':'Type Hi Charan'})
        self.assertEqual(action['task'],'Type Hi Charan')
        for args in [{'app_name':'Notepad','task':''},{'app_name':'Notepad','task':'x'*2001}]:
            with self.assertRaises(ValueError): service.validate_action('desktop_task',args)
        with patch('app.agents.recall_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued'):
            self.assertEqual(await RecallAgent()._execute_tool('local','close_app',{'app_name':'Notion'},None),'queued')
        agent=CaptureAgent('local','capture-1',AsyncMock());agent._user_has_spoken=True
        with patch('app.agents.capture_agent.execute_task_tool',new_callable=AsyncMock,return_value='queued') as capture:
            self.assertEqual(await agent._execute_tool('desktop_task',{'app_name':'Notepad','task':'Type Hi Charan'}),'queued')
            self.assertEqual(capture.await_args.args[0],'local')
