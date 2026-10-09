import asyncio
import unittest
import tempfile
from pathlib import Path
from app.config import settings
from app.services.task_store import TaskStore
from app.services.task_supervisor import TaskSupervisor
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, patch
from app.agents.recall_agent import RecallAgent, LiveSession
from app.agents.capture_agent import CaptureAgent
from app.services.live_tools import LiveToolRunner
from app.services import desktop_action_service as desktop

def call(id, name='open_app'):
    return NS(id=id, name=name, args={'app_name': 'Notepad', 'task': 'Type synthetic test'})

class Session:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.closed = False
        self.send_tool_response = AsyncMock()
    async def receive(self):
        while not self.closed:
            message = await self.queue.get()
            if message is None:
                self.closed = True
                return
            yield message

class Interruptions(unittest.IsolatedAsyncioTestCase):
    async def test_runner_serializes_calls_cancelled_ids_never_run_or_reply(self):
        session = Session()
        started = asyncio.Event()
        cancelled = asyncio.Event()
        async def execute(name, args):
            started.set()
            try: await asyncio.Future()
            finally: cancelled.set()
        runner = LiveToolRunner(session, execute)
        runner.submit([call('one'), call('two')])
        await started.wait()
        await runner.cancel({'one', 'two', 'not-yet-delivered'})
        self.assertTrue(cancelled.is_set())
        runner.submit([call('one'), call('not-yet-delivered')])
        await asyncio.sleep(0)
        self.assertFalse(runner.pending)
        session.send_tool_response.assert_not_awaited()
        await runner.close()

    async def test_receive_loops_cancel_awaited_voice_owned_tools_while_reading(self):
        for mode in ['recall', 'capture']:
            session = Session()
            connection = object()
            issued = asyncio.Event()
            messages = []
            async def send(user, message):
                messages.append(message)
                if message['type'] == 'desktop_action': issued.set()
                return True
            interrupted, user_text = AsyncMock(), AsyncMock()
            agent = RecallAgent() if mode == 'recall' else CaptureAgent('local', 'capture-1', AsyncMock(), on_user_text=user_text)
            if mode == 'recall':
                live = LiveSession('local', session, None, asyncio.Event(), asyncio.Event())
                async def execute(user, name, args, activity):
                    return await desktop.request_desktop_action(user, name, args, source='recall')
                agent._execute_tool = execute
                loop = agent._receive_loop(live, session, AsyncMock(), AsyncMock(), interrupted, AsyncMock(), user_text)
            else:
                agent._user_has_spoken = True
                async def execute(name, args):
                    return await desktop.request_desktop_action('local', name, args, source='capture', session_id='capture-1')
                agent._execute_tool = execute
                loop = agent._receive_loop(session)
            with patch.object(desktop.manager, 'get_connection', return_value=connection), patch.object(desktop.manager, 'send', side_effect=send):
                reader = asyncio.create_task(loop)
                await session.queue.put(NS(tool_call=NS(function_calls=[call('old')]), server_content=None))
                await asyncio.wait_for(issued.wait(), 1)
                request_id = messages[-1]['requestId']
                await session.queue.put(NS(tool_call=None, server_content=NS(interrupted=True, input_transcription=NS(text='Stop doing that'))))
                for _ in range(30):
                    if any(m['type'] == 'desktop_action_cancel' for m in messages): break
                    await asyncio.sleep(.01)
                self.assertTrue(any(m['type'] == 'desktop_action_cancel' and m['requestId'] == request_id for m in messages))
                self.assertNotIn('local', desktop._pending)
                self.assertFalse(desktop.resolve_desktop_action('local', {'requestId': request_id, 'status': 'succeeded', 'message': 'late'}, connection))
                await asyncio.sleep(.01)
                user_text.assert_awaited_once_with('Stop doing that')
                session.send_tool_response.assert_not_awaited()
                await session.queue.put(None)
                await asyncio.wait_for(reader, 1)
                if mode == 'recall': interrupted.assert_awaited_once()
                else: self.assertTrue(any(m['type'] == 'capture_interrupted' for m in messages))

    async def test_both_actual_agents_keep_accepted_jobs_running_after_speech_interruption(self):
        for mode in ('recall','capture'):
            with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as folder:
                started=asyncio.Event()
                async def worker(*args,**kwargs): started.set(); await asyncio.Future()
                supervisor=TaskSupervisor(TaskStore(Path(folder)/'jobs.sqlite3'),desktop=worker)
                session=Session();connection=object()
                agent=RecallAgent() if mode=='recall' else CaptureAgent('local','capture-1',AsyncMock(),on_user_text=AsyncMock())
                if mode=='recall':
                    live=LiveSession('local',session,None,asyncio.Event(),asyncio.Event())
                    loop=agent._receive_loop(live,session,AsyncMock(),AsyncMock(),AsyncMock(),AsyncMock(),AsyncMock())
                else:
                    agent._user_has_spoken=True;loop=agent._receive_loop(session)
                with patch('app.services.task_supervisor.get_supervisor',return_value=supervisor),patch.object(desktop.manager,'get_connection',return_value=connection),patch.object(desktop.manager,'send',new_callable=AsyncMock,return_value=True):
                    reader=asyncio.create_task(loop)
                    await session.queue.put(NS(tool_call=NS(function_calls=[call('start-job')]),server_content=None))
                    await asyncio.wait_for(started.wait(),1)
                    for _ in range(30):
                        if session.send_tool_response.await_count: break
                        await asyncio.sleep(.01)
                    self.assertEqual(session.send_tool_response.await_count,1)
                    ident=supervisor.store.list('local')[0]['id']
                    await session.queue.put(NS(tool_call=None,server_content=NS(interrupted=True,input_transcription=NS(text='Also fix my project'))))
                    await asyncio.sleep(.03)
                    self.assertEqual(supervisor.get('local',ident)['status'],'running')
                    await supervisor.control('local',ident,'cancel')
                    self.assertEqual(supervisor.get('local',ident)['status'],'cancelled')
                    await session.queue.put(None);await asyncio.wait_for(reader,1)
                    await supervisor.close()

    async def test_success_after_interruption_uses_fresh_call_and_keeps_receive_alive(self):
        session = Session()
        execute = AsyncMock(return_value='verified')
        runner = LiveToolRunner(session, execute)
        await runner.cancel({'old'})
        runner.submit([call('old'), call('new', 'open_app')])
        for _ in range(10):
            if session.send_tool_response.await_count: break
            await asyncio.sleep(0)
        execute.assert_awaited_once()
        response = session.send_tool_response.await_args.kwargs['function_responses'][0]
        self.assertEqual(response.id, 'new')
        await runner.close()

    async def test_disconnect_cancels_tool_and_suppresses_late_reply(self):
        async def execute(*_):
            await asyncio.Future()
        runner = LiveToolRunner(Session(), execute)
        runner.submit([call('one')])
        await asyncio.sleep(0)
        await runner.close()
        self.assertFalse(runner.pending)
        runner.session.send_tool_response.assert_not_awaited()
