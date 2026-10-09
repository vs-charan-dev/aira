import json
import unittest
from unittest.mock import AsyncMock, patch
from app.agents.recall_agent import RecallAgent, _BASE_SYSTEM_PROMPT
from app.agents.capture_agent import CaptureAgent, _SYSTEM_PROMPT_TEMPLATE
from app.agents.tools.tools import CAPTURE_LIVE_TOOLS, RECALL_LIVE_TOOLS
from app.services.companion_service import request_companion_action

class CompanionTools(unittest.IsolatedAsyncioTestCase):
    async def test_recall_dispatches_screen_request_without_claiming_activation(self):
        with patch('app.services.companion_service.manager.send', new_callable=AsyncMock) as send:
            result = await RecallAgent()._execute_tool('local', 'switch_mode', {'mode': 'capture_screen'}, None)
            message = send.await_args.args[1]
            self.assertEqual(message['mode'], 'capture_screen')
            self.assertEqual(message['source'], 'recall')
            self.assertIn('pending', result)

    async def test_capture_dispatches_recall_and_keeps_origin_session(self):
        agent = CaptureAgent('local', 'capture-1', AsyncMock())
        agent._user_has_spoken = True
        with patch('app.services.companion_service.manager.send', new_callable=AsyncMock) as send:
            await agent._execute_tool('switch_mode', {'mode': 'recall'})
            self.assertEqual(send.await_args.args[1]['sessionId'], 'capture-1')

    async def test_invalid_modes_durations_and_greeting_cannot_trigger_devices(self):
        with patch('app.services.companion_service.manager.send', new_callable=AsyncMock) as send:
            for tool, args in [('switch_mode', {'mode': 'shell'}), ('hide_companion', {'seconds': -1}), ('hide_companion', {'seconds': True})]:
                await request_companion_action('local', tool, args, source='recall')
            agent = CaptureAgent('local', 'capture-1', AsyncMock())
            await agent._execute_tool('switch_mode', {'mode': 'recall'})
            send.assert_not_awaited()

    async def test_both_models_receive_device_tools_and_truthful_instructions(self):
        for tools, prompt in [(CAPTURE_LIVE_TOOLS, _SYSTEM_PROMPT_TEMPLATE), (RECALL_LIVE_TOOLS, _BASE_SYSTEM_PROMPT)]:
            names = [t['name'] for t in tools]
            self.assertEqual(names.count('switch_mode'), 1)
            self.assertEqual(names.count('hide_companion'), 1)
            json.dumps(tools)
            self.assertIn('never just acknowledge', prompt)

    async def test_hide_request_is_bounded_and_unique(self):
        with patch('app.services.companion_service.manager.send', new_callable=AsyncMock) as send:
            await request_companion_action('local', 'hide_companion', {'seconds': 10}, source='recall')
            first = send.await_args.args[1]
            await request_companion_action('local', 'hide_companion', {'seconds': 10}, source='recall')
            self.assertEqual(first['seconds'], 10)
            self.assertNotEqual(first['requestId'], send.await_args.args[1]['requestId'])
