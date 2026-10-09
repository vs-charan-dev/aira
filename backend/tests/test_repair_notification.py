import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app.services.repair_notification import announce_repair


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_announces_verified_report_only_in_existing_session_without_replaying_work(self):
        send=AsyncMock()
        live=SimpleNamespace(_closed=False,session=SimpleNamespace(send_client_content=send))
        module=SimpleNamespace(recall_agent=SimpleNamespace(_sessions={'local':live}))
        with patch.dict('sys.modules',{'app.agents.recall_agent':module}):
            self.assertFalse(await announce_repair('local',{'verified':False}))
            self.assertFalse(await announce_repair('local',{'verified':True,'presentationReturned':False}))
            self.assertFalse(await announce_repair('other',{'verified':True,'presentationReturned':True}))
            self.assertTrue(await announce_repair('local',{'verified':True,'presentationReturned':True,'summary':'Flat subtraction was used for a percentage.'}))
            send.assert_awaited_once()
            content=send.call_args.kwargs['turns'][0].parts[0].text
            self.assertIn('Flat subtraction',content);self.assertIn('Do not call tools',content)
            send.side_effect=RuntimeError('connection lost')
            self.assertFalse(await announce_repair('local',{'verified':True,'presentationReturned':True}))
