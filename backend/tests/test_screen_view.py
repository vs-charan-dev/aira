import asyncio
import base64
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app.services import screen_view_service as svc
from app.agents.recall_agent import RecallAgent
from app.agents.capture_agent import CaptureAgent
from app.agents.tools.tools import RECALL_LIVE_TOOLS, CAPTURE_LIVE_TOOLS

JPEG = b'\xff\xd8synthetic-frame\xff\xd9'

class ScreenViews(unittest.IsolatedAsyncioTestCase):
    async def test_correlates_connection_and_request_and_rejects_invalid_images(self):
        connection = object()
        with patch.object(svc.manager, 'get_connection', return_value=connection), patch.object(svc.manager, 'send', new_callable=AsyncMock, return_value=True) as send:
            task = asyncio.create_task(svc.request_screen_view('local', source='recall'))
            await asyncio.sleep(0)
            request = send.await_args.args[1]['requestId']
            for data in ['bad', base64.b64encode(b'not jpeg').decode(), 'A' * 3_000_001]:
                self.assertFalse(svc.resolve_screen_view('local', {'requestId': request, 'data': data}, connection))
            message = {'requestId': request, 'data': base64.b64encode(JPEG).decode()}
            self.assertFalse(svc.resolve_screen_view('local', message, object()))
            self.assertFalse(svc.resolve_screen_view('local', {**message, 'requestId': 'other'}, connection))
            self.assertTrue(svc.resolve_screen_view('local', message, connection))
            self.assertEqual((await task)[0], JPEG)
            self.assertNotIn('local', svc._pending)

    async def test_cancel_removes_pending_and_failure_does_not_claim_screen_seen(self):
        connection = object()
        with patch.object(svc.manager, 'get_connection', return_value=connection), patch.object(svc.manager, 'send', new_callable=AsyncMock, return_value=True):
            task = asyncio.create_task(svc.request_screen_view('local', source='recall'))
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
            self.assertNotIn('local', svc._pending)
        agent = RecallAgent()
        with patch.object(svc, 'request_screen_view', new_callable=AsyncMock, return_value=(None, 'No screen received.')):
            self.assertEqual(await agent._execute_tool('local', 'look_at_screen', {}, None), 'No screen received.')

    async def test_both_modes_receive_frame_without_switching_or_saving(self):
        for tools in (RECALL_LIVE_TOOLS, CAPTURE_LIVE_TOOLS):
            self.assertEqual(sum(t['name'] == 'look_at_screen' for t in tools), 1)
        session = SimpleNamespace(send_realtime_input=AsyncMock())
        recall = RecallAgent()
        recall._sessions['local'] = SimpleNamespace(session=session, _closed=False)
        capture = CaptureAgent('local', 'capture-1', AsyncMock())
        capture._session = session
        capture._user_has_spoken = True
        with patch.object(svc, 'request_screen_view', new_callable=AsyncMock, return_value=(JPEG, 'Received')):
            await recall._execute_tool('local', 'look_at_screen', {}, None)
            await capture._execute_tool('look_at_screen', {})
        self.assertEqual(session.send_realtime_input.await_count, 2)
        self.assertEqual(session.send_realtime_input.await_args.kwargs['video'].data, JPEG)

    async def test_replacement_session_cannot_receive_old_screen(self):
        session = SimpleNamespace(send_realtime_input=AsyncMock())
        agent = RecallAgent()
        agent._sessions['local'] = SimpleNamespace(session=session, _closed=False)
        async def replacement(*args, **kwargs):
            agent._sessions['local'] = SimpleNamespace(session=session, _closed=False)
            return JPEG, 'Received'
        with patch.object(svc, 'request_screen_view', side_effect=replacement):
            self.assertIn('not delivered', await agent._execute_tool('local', 'look_at_screen', {}, None))
        session.send_realtime_input.assert_not_awaited()
