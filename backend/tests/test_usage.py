"""Simulated SDK usage and lifecycle tests; no network or actual credentials."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.core.usage import UsageRun, usage_scope, usage_summary, normalize_usage, estimate, recover_usage
from app.core.tracked_gemini import TrackedClient, close_live_for_user, has_live_for_user


def usage(prompt=100, output=20, **extra):
    return NS(prompt_token_count=prompt, response_token_count=output, total_token_count=prompt + output,
              prompt_tokens_details=[NS(modality='TEXT', token_count=prompt)],
              response_tokens_details=[NS(modality='AUDIO', token_count=output)], **extra)


def message(meta=None, *, text=None, ended=False):
    content = NS(input_transcription=NS(text=text) if text else None, model_turn=None, turn_complete=ended)
    return NS(usage_metadata=meta, server_content=content, tool_call=None)


class FakeSession:
    def __init__(self):
        self.messages = asyncio.Queue()
        self.closed = False
        self.send_client_content = AsyncMock()

    async def receive(self):
        while not self.closed:
            value = await self.messages.get()
            if value is None:
                return
            yield value
            if value.server_content.turn_complete:
                return

    async def close(self):
        self.closed = True
        await self.messages.put(None)


class FakeSDK:
    def __init__(self):
        self.sessions = []
        self.fail_connect = False
        self.aio = NS(models=NS(generate_content=AsyncMock(return_value=NS(usage_metadata=None)),
                                embed_content=AsyncMock(return_value=NS(embeddings=[]))),
                      live=NS(connect=self.connect))

    @asynccontextmanager
    async def connect(self, **kwargs):
        if self.fail_connect:
            raise RuntimeError('simulated unavailable model')
        session = FakeSession()
        self.sessions.append(session)
        try:
            yield session
        finally:
            await session.close()


class UsageIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_data = settings.aira_data_dir
        self.tmp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir / 'tmp')
        settings.aira_data_dir = Path(self.tmp.name)
        self.limits = (settings.aira_live_idle_seconds, settings.aira_live_max_seconds,
                       settings.aira_live_max_estimated_usd, settings.aira_live_usage_mode)
        settings.aira_live_idle_seconds = settings.aira_live_max_seconds = settings.aira_live_max_estimated_usd = 0
        settings.aira_live_usage_mode = 'per_turn'
        self.sdk = FakeSDK()
        self.client = TrackedClient(self.sdk)
        self.send_patch = patch('app.websocket.manager.manager.send', new_callable=AsyncMock)
        self.send = self.send_patch.start()

    async def asyncTearDown(self):
        await close_live_for_user('local')
        self.send_patch.stop()
        settings.aira_data_dir = self.original_data
        (settings.aira_live_idle_seconds, settings.aira_live_max_seconds,
         settings.aira_live_max_estimated_usd, settings.aira_live_usage_mode) = self.limits
        self.tmp.cleanup()

    async def test_live_per_turn_snapshots_replace_but_history_is_rebilled(self):
        with usage_scope('local', 'recall', 'test-session'):
            async with self.client.aio.live.connect(model='gemini-3.8-live') as session:
                raw = self.sdk.sessions[-1]
                for msg in (message(usage(100, 5), text='fake private text'), message(usage(100, 20), ended=True)):
                    await raw.messages.put(msg)
                async for _ in session.receive():
                    pass
                # Late/repeated metadata is still part of the preceding turn.
                for msg in (message(usage(100, 20)), message(usage(200, 30), text='next'), message(usage(200, 30), ended=True)):
                    await raw.messages.put(msg)
                async for _ in session.receive():
                    pass
        result = await usage_summary('local')
        row = result['records'][0]
        self.assertEqual(row['breakdown']['input']['TEXT'], 300)
        self.assertEqual(row['breakdown']['output']['AUDIO'], 50)
        self.assertAlmostEqual(row['estimatedUsd'], .000825)
        self.assertNotIn('fake private text', json.dumps(result))
        self.assertFalse(has_live_for_user('local'))

    async def test_explicit_cumulative_mode_and_restart_recovery(self):
        settings.aira_live_usage_mode = 'session_cumulative'
        with usage_scope('local', 'recall'):
            run = UsageRun('gemini-3.8-live', 'live')
            await run.save()
            async with self.client.aio.live.connect(model='gemini-3.8-live') as session:
                raw = self.sdk.sessions[-1]
                for msg in (message(usage(100, 20), text='one'), message(ended=True)):
                    await raw.messages.put(msg)
                async for _ in session.receive(): pass
                for msg in (message(usage(200, 40), text='two'), message(ended=True)):
                    await raw.messages.put(msg)
                async for _ in session.receive(): pass
        await recover_usage()
        records = (await usage_summary('local'))['records']
        cumulative = next(r for r in records if r['id'] != run.id)
        self.assertEqual(cumulative['breakdown']['input']['TEXT'], 200)
        self.assertEqual(cumulative['breakdown']['output']['AUDIO'], 40)
        self.assertEqual(next(r for r in records if r['id'] == run.id)['status'], 'interrupted')

    async def test_one_live_connection_mode_switch_logout_and_failed_start(self):
        with usage_scope('local', 'recall'):
            async with self.client.aio.live.connect(model='gemini-3.8-live') as old:
                with usage_scope('local', 'capture', 'capture-test'):
                    async with self.client.aio.live.connect(model='gemini-3.8-live') as new:
                        self.assertTrue(old.closed)
                        self.assertTrue(self.sdk.sessions[0].closed)
                        self.assertTrue(has_live_for_user('local'))
                        await close_live_for_user('local', 'logout')
                        self.assertTrue(new.closed)
                        self.assertFalse(has_live_for_user('local'))
                self.sdk.fail_connect = True
                with self.assertRaises(RuntimeError):
                    async with self.client.aio.live.connect(model='unavailable'):
                        self.fail('connection should fail')
        reasons = {r['stopReason'] for r in (await usage_summary('local'))['records']}
        self.assertIn('mode_switch', reasons)
        self.assertIn('logout', reasons)
        self.assertTrue(all(s.closed for s in self.sdk.sessions))

    async def test_idle_duration_and_soft_cost_guards_close_sdk_connection(self):
        for reason in ('idle_limit', 'duration_limit', 'estimated_cost_limit'):
            settings.aira_live_idle_seconds = .01 if reason == 'idle_limit' else 0
            settings.aira_live_max_seconds = .01 if reason == 'duration_limit' else 0
            settings.aira_live_max_estimated_usd = .00001 if reason == 'estimated_cost_limit' else 0
            with usage_scope('local', 'recall'):
                async with self.client.aio.live.connect(model='gemini-3.8-live') as session:
                    if reason == 'estimated_cost_limit':
                        await session.run.observe(usage())
                    async def drain():
                        async for _ in session.receive(): pass
                    await asyncio.wait_for(drain(), 2)
                    self.assertTrue(session.closed)
                    self.assertEqual(session.run.stop_reason, reason)
            self.assertTrue(self.sdk.sessions[-1].closed)
        self.assertEqual((await usage_summary('local'))['activeCalls'], 0)

    async def test_text_stream_final_snapshot_and_missing_embedding_usage(self):
        async def raw_stream():
            yield NS(usage_metadata=NS(prompt_token_count=100, candidates_token_count=5, total_token_count=105))
            yield NS(usage_metadata=NS(prompt_token_count=100, candidates_token_count=20, total_token_count=120))
        self.sdk.aio.models.generate_content_stream = AsyncMock(return_value=raw_stream())
        with usage_scope('local', 'narration'):
            async for _ in await self.client.aio.models.generate_content_stream(model='gemini-3.8-flash'): pass
            await self.client.aio.models.embed_content(model='gemini-embedding-001', contents='fake')
        summary = await usage_summary('local')
        stream = next(r for r in summary['records'] if r['kind'] == 'generate_content_stream')
        embedding = next(r for r in summary['records'] if r['kind'] == 'embed_content')
        self.assertEqual(stream['tokens'], 120)
        self.assertEqual(stream['breakdown']['output']['TEXT'], 20)
        self.assertIsNone(embedding['estimatedUsd'])
        self.assertFalse(embedding['usageAvailable'])
        self.assertEqual(summary['incompleteCalls'], 1)

    async def test_pricing_modalities_thoughts_cache_unknown_and_failure(self):
        sample = normalize_usage(NS(prompt_token_count=1000, candidates_token_count=100, total_token_count=1150,
                                    thoughts_token_count=50, cached_content_token_count=800), text_only=True)
        priced = estimate('gemini-3.8-flash', [sample])
        self.assertAlmostEqual(priced['estimatedUsd'], .0007725)
        unknown = estimate('unknown-model', [sample])
        self.assertFalse(unknown['estimateComplete'])
        self.assertGreater(unknown['unpricedTokens'], 0)
        self.sdk.aio.models.generate_content.side_effect = RuntimeError('private-error-must-not-be-stored')
        with self.assertRaises(RuntimeError):
            await self.client.aio.models.generate_content(model='gemini-3.8-flash')
        summary = await usage_summary('local')
        self.assertEqual(summary['records'][0]['status'], 'failed')
        self.assertIsNone(summary['records'][0]['estimatedUsd'])
        self.assertNotIn('private-error', json.dumps(summary))

    async def test_capture_limit_finalizes_session_and_releases_agent_registry(self):
        from app.agents.capture_agent import CaptureAgent, register_agent, get_agent
        from app.services.capture_service import start_session, get_session
        settings.aira_live_idle_seconds = .01
        await start_session('local', 'capture-limit-test', 'voice')
        with usage_scope('local', 'capture', 'capture-limit-test'), patch('app.agents.capture_agent.get_genai_client', return_value=self.client), patch.object(CaptureAgent, '_build_room_directory', new_callable=AsyncMock, return_value='(empty)'):
            agent = CaptureAgent('local', 'capture-limit-test', AsyncMock(), gemini_api_key='fake')
            await agent.start()
            register_agent('capture-limit-test', agent)
            await asyncio.wait_for(agent._task, 2)
        self.assertIsNone(get_agent('capture-limit-test'))
        self.assertEqual((await get_session('local', 'capture-limit-test')).status.value, 'completed')

    async def test_recall_limit_releases_agent_without_busy_receive_loop(self):
        from app.agents.recall_agent import RecallAgent
        settings.aira_live_idle_seconds = .01
        agent = RecallAgent()
        with usage_scope('local', 'recall'), patch('app.agents.recall_agent.get_genai_client', return_value=self.client), patch('app.agents.recall_agent._retrieve_context', new_callable=AsyncMock, return_value=[]), patch('app.agents.recall_agent._build_room_directory', new_callable=AsyncMock, return_value='(empty)'), patch.object(agent, '_greet_after_context', new_callable=AsyncMock):
            await agent.start_session('local', {}, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), gemini_api_key='fake')
            task = agent._sessions['local'].task
            await asyncio.wait_for(task, 2)
        self.assertFalse(agent.has_session('local'))
