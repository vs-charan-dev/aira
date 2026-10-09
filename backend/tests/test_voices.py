"""Voice preference, preview cache and Live exclusivity; no real API or audio device."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.core.voices import VOICES, VOICE_NAMES
from app.core.tracked_gemini import TrackedClient, LiveSessionBusy
from app.core.usage import usage_scope
from app.services.user_settings_service import get_user_voice, set_user_voice
from app.services.voice_preview_service import preview_voice

class FakeSDK:
    def __init__(self, *, transcript='Hi, Charan.', complete=True, data=b'\0\0' * 4800):
        self.calls = []; self.sessions = []
        self.transcript = transcript; self.complete = complete; self.data = data
        self.aio = NS(models=NS(), live=NS(connect=self.connect))
    @asynccontextmanager
    async def connect(self, **kwargs):
        self.calls.append(kwargs)
        session = NS(closed=False, send_client_content=AsyncMock())
        async def close(): session.closed = True
        async def receive():
            yield NS(server_content=NS(
                model_turn=NS(parts=[NS(inline_data=NS(data=self.data[:4800], mime_type='audio/pcm;rate=24000')), NS(inline_data=NS(data=self.data[4800:], mime_type='audio/pcm;rate=24000'))]),
                output_transcription=NS(text=self.transcript), turn_complete=self.complete,
                input_transcription=None), tool_call=None, usage_metadata=None)
        session.close = close; session.receive = receive; self.sessions.append(session)
        try: yield session
        finally: await close()

class VoicePreferences(unittest.TestCase):
    def setUp(self):
        self.original = settings.aira_data_dir
        self.tmp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir / 'tmp')
        settings.aira_data_dir = Path(self.tmp.name)
        self.client = TestClient(app); self.client.__enter__()
        self.client.headers['Origin'] = 'http://testserver'
        self.client.post('/api/v1/local-session')
    def tearDown(self):
        self.client.__exit__(None, None, None); settings.aira_data_dir = self.original; self.tmp.cleanup()
    def test_voice_only_updates_preserve_key_and_survive_new_client(self):
        with patch('app.routers.settings.set_user_gemini_key', new_callable=AsyncMock) as key_save, patch('app.routers.settings.get_user_gemini_key', new_callable=AsyncMock, return_value=None):
            self.assertEqual(self.client.get('/api/v1/settings').json()['voiceName'], 'Aoede')
            self.assertEqual(self.client.put('/api/v1/settings', json={'voiceName':'Kore'}).status_code, 200)
            key_save.assert_not_awaited()
            with TestClient(app) as other:
                other.headers['Origin'] = 'http://testserver'; other.post('/api/v1/local-session')
                result = other.get('/api/v1/settings').json()
                self.assertEqual(result['voiceName'], 'Kore'); self.assertEqual(len(result['voices']), 30)
            self.assertEqual(self.client.put('/api/v1/settings', json={'voiceName':'../../bad','geminiApiKey':'fake'}).status_code, 400)
            key_save.assert_not_awaited()
            self.assertEqual(self.client.get('/api/v1/settings').json()['voiceName'], 'Kore')
            self.client.put('/api/v1/settings', json={'geminiApiKey':None})
            key_save.assert_awaited_once_with('local', None)
            self.assertEqual(self.client.get('/api/v1/settings').json()['voiceName'], 'Kore')
    def test_preview_is_authenticated_validated_and_sdk_errors_are_redacted(self):
        with TestClient(app) as other:
            other.headers['Origin'] = 'http://testserver'
            self.assertEqual(other.post('/api/v1/settings/voice-preview', json={'voiceName':'Kore'}).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/settings/voice-preview', json={'voiceName':'unknown'}).status_code, 400)
        with patch('app.routers.settings.get_user_gemini_key', new_callable=AsyncMock, return_value='fake'), patch('app.routers.settings.preview_voice', new_callable=AsyncMock, side_effect=RuntimeError('private-api-key')):
            result = self.client.post('/api/v1/settings/voice-preview', json={'voiceName':'Kore'})
            self.assertEqual(result.status_code, 502); self.assertNotIn('private-api-key', result.text)

class VoicePreviews(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original = settings.aira_data_dir
        self.tmp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir / 'tmp')
        settings.aira_data_dir = Path(self.tmp.name)
        self.sdk = FakeSDK(); self.client = TrackedClient(self.sdk)
        self.patch = patch('app.services.voice_preview_service.get_genai_client', return_value=self.client); self.patch.start()
    async def asyncTearDown(self):
        self.patch.stop(); settings.aira_data_dir = self.original; self.tmp.cleanup()
    async def test_all_30_voices_generate_and_replay_from_local_cache(self):
        self.assertEqual(len(VOICE_NAMES), 30)
        for voice in VOICES:
            name = voice['name']
            await set_user_voice('local', name)
            self.assertEqual(await get_user_voice('local'), name)
            audio, cached = await preview_voice('local', name, 'fake')
            self.assertFalse(cached); self.assertEqual(audio, self.sdk.data)
            config = self.sdk.calls[-1]['config']
            self.assertEqual(config.speech_config.voice_config.prebuilt_voice_config.voice_name, name)
            self.assertTrue(config.realtime_input_config.automatic_activity_detection.disabled)
            self.assertNotIn('replace_existing', self.sdk.calls[-1])
            self.assertIn('Hi Charan.', self.sdk.sessions[-1].send_client_content.await_args.kwargs['turns'].parts[0].text)
            replay, cached = await preview_voice('local', name, None)
            self.assertTrue(cached); self.assertEqual(replay, audio)
        self.assertEqual(len(self.sdk.calls), 30)
        self.assertEqual(len(list((settings.aira_data_dir / 'media' / 'voice-previews').glob('*.pcm'))), 30)
    async def test_duplicate_preview_requests_make_only_one_generation(self):
        results = await asyncio.gather(*(preview_voice('local', 'Kore', 'fake') for _ in range(3)))
        self.assertEqual(len(self.sdk.calls), 1); self.assertEqual([cached for _, cached in results], [False, True, True])
    async def test_preview_never_replaces_live_even_after_a_racing_busy_check(self):
        with usage_scope('local', 'recall'):
            async with self.client.aio.live.connect(model='fake-live', config={}) as active:
                with self.assertRaises(LiveSessionBusy): await preview_voice('local', 'Kore', 'fake')
                with patch('app.services.voice_preview_service.has_live_for_user', return_value=False):
                    with self.assertRaises(LiveSessionBusy): await preview_voice('local', 'Kore', 'fake')
                self.assertFalse(active.closed); self.assertFalse(self.sdk.sessions[0].closed)
                self.assertEqual(len(self.sdk.calls), 1)
    async def test_wrong_greeting_and_incomplete_audio_are_not_cached(self):
        for kwargs in ({'transcript':'Welcome to the palace.'}, {'complete':False}, {'data':b'\0'}, {'data':b'\0\0' * (24000 * 9)}):
            sdk = FakeSDK(**kwargs)
            with patch('app.services.voice_preview_service.get_genai_client', return_value=TrackedClient(sdk)):
                with self.assertRaises(ValueError): await preview_voice('local', 'Kore', 'fake')
        self.assertFalse(list((settings.aira_data_dir / 'media' / 'voice-previews').glob('*.pcm')))
    async def test_saved_voice_reaches_recall_and_capture_session_configs(self):
        from tests.test_usage import FakeSDK as SessionSDK
        from app.agents.recall_agent import RecallAgent
        from app.agents.capture_agent import CaptureAgent
        class RecordingSDK(SessionSDK):
            def __init__(self): super().__init__(); self.configs = []
            @asynccontextmanager
            async def connect(self, **kwargs):
                self.configs.append(kwargs['config'])
                async with super().connect(**kwargs) as session: yield session
        sdk = RecordingSDK(); client = TrackedClient(sdk)
        await set_user_voice('local', 'Sulafat')
        agent = RecallAgent()
        with patch('app.agents.recall_agent.get_genai_client', return_value=client), patch('app.agents.recall_agent._build_room_directory', new_callable=AsyncMock, return_value='(empty)'), patch.object(agent, '_greet_after_context', new_callable=AsyncMock):
            with usage_scope('local', 'recall'):
                await agent.start_session('local', {}, AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), gemini_api_key='fake')
                self.assertEqual(sdk.configs[-1].speech_config.voice_config.prebuilt_voice_config.voice_name, 'Sulafat')
                await agent.close_session('local')
        with patch('app.agents.capture_agent.get_genai_client', return_value=client), patch.object(CaptureAgent, '_build_room_directory', new_callable=AsyncMock, return_value='(empty)'):
            with usage_scope('local', 'capture'):
                capture = CaptureAgent('local', 'voice-setting-test', AsyncMock(), gemini_api_key='fake')
                await capture.start()
                self.assertEqual(sdk.configs[-1].speech_config.voice_config.prebuilt_voice_config.voice_name, 'Sulafat')
                await capture.stop()
