"""Offline PCM forwarding checks; no microphone, provider or desktop actions."""
import asyncio
import unittest
from unittest.mock import AsyncMock
from app.services.live_audio import LiveAudioSender


class AudioSenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_offer_returns_while_provider_is_slow_and_discards_stale_queue(self):
        started=asyncio.Event()
        async def send(**kwargs):
            started.set()
            await asyncio.Future()
        session=AsyncMock();session.send_realtime_input.side_effect=send
        sender=LiveAudioSender(session,AsyncMock(),capacity=2)
        sender.offer(b'first')
        await asyncio.wait_for(started.wait(),1)
        for data in (b'old',b'recent',b'latest'): sender.offer(data)
        self.assertEqual(sender.queue.qsize(),2)
        self.assertEqual(sender.queue.get_nowait(),b'recent')
        self.assertEqual(sender.queue.get_nowait(),b'latest')
        await sender.close()

    async def test_timeout_reports_once_and_rejects_new_audio(self):
        async def send(**kwargs): await asyncio.Future()
        session=AsyncMock();session.send_realtime_input.side_effect=send
        failed=AsyncMock();sender=LiveAudioSender(session,failed,timeout=.01)
        sender.offer(b'pcm')
        await asyncio.wait_for(sender.task,1)
        failed.assert_awaited_once_with('audio_send_timeout')
        sender.offer(b'late')
        self.assertEqual(sender.queue.qsize(),0)
        await sender.close()

    async def test_transport_exception_has_distinct_reason(self):
        session=AsyncMock();session.send_realtime_input.side_effect=RuntimeError('synthetic')
        failed=AsyncMock();sender=LiveAudioSender(session,failed)
        sender.offer(b'pcm')
        await asyncio.wait_for(sender.task,1)
        failed.assert_awaited_once_with('connection_error')
        await sender.close()

    async def test_stop_cancels_writer_without_reporting_failure(self):
        session=AsyncMock()
        async def send(**kwargs): await asyncio.Future()
        session.send_realtime_input.side_effect=send
        failed=AsyncMock();sender=LiveAudioSender(session,failed)
        sender.offer(b'pcm')
        await asyncio.sleep(0)
        await sender.close()
        failed.assert_not_awaited()
        self.assertTrue(sender.task.done())
        self.assertEqual(sender.queue.qsize(),0)


if __name__=='__main__': unittest.main()
