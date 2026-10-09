"""Meaningful local integration tests. No network, real keys, or demo memories.

All temporary data lives under the configured E-drive cache.
"""
import asyncio
import os
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.config import settings, ROOT
from app.core.local_store import get_store, Increment, ArrayUnion
from app.core.local_media import save_media
from app.core.secrets import _crypt
from app.main import app
from app.services import room_service, artifact_service, capture_service, enrichment_service

class LocalIntegration(unittest.TestCase):
    def setUp(self):
        self.original_data = settings.aira_data_dir
        self.tmp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir / 'tmp')
        settings.aira_data_dir = Path(self.tmp.name)
        self.client = TestClient(app)
        self.client.__enter__()
        self.client.headers['Origin'] = 'http://testserver'

    def tearDown(self):
        self.client.__exit__(None, None, None)
        settings.aira_data_dir = self.original_data
        self.tmp.cleanup()

    def sign_in(self):
        response = self.client.post('/api/v1/local-session')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['token']

    def test_auth_origin_media_and_websocket(self):
        self.assertEqual(self.client.get('/api/v1/settings').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/local-session', headers={'Origin':'https://attacker.invalid'}).status_code, 403)
        self.assertEqual(self.client.get('/health', headers={'Host':'attacker.invalid'}).status_code, 400)
        token = self.sign_in()
        self.assertEqual(self.client.get('/api/v1/settings').status_code, 200)
        self.assertEqual(self.client.put('/api/v1/settings', json={}, headers={'Origin':'https://attacker.invalid'}).status_code, 403)
        url = asyncio.run(save_media(b'local-test', 'screenshots/test.jpg'))
        self.assertEqual(self.client.get(url).content, b'local-test')
        unauth = TestClient(app)
        self.assertEqual(unauth.get(url).status_code, 401)
        unauth.close()
        with self.client.websocket_connect('/ws/local', headers={'Origin':'http://testserver'}) as ws:
            ws.send_json({'type':'auth', 'token':token})
            self.assertEqual(ws.receive_json()['type'], 'auth_success')
            # Rejected sockets must not replace the authenticated connection.
            with self.client.websocket_connect('/ws/local', headers={'Origin':'https://attacker.invalid'}) as bad:
                bad.send_json({'type':'auth','token':token})
                self.assertEqual(bad.receive_json()['code'], 'UNAUTHORIZED')
            ws.send_json({'type':'ping'})
            self.assertEqual(ws.receive_json()['type'], 'pong')
        self.assertEqual(self.client.delete('/api/v1/local-session').status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 401)
        with self.assertRaises(ValueError):
            asyncio.run(save_media(b'x', '../outside.jpg'))

    def test_atomic_store_queries_and_restart(self):
        async def run():
            col = get_store().collection('counter')
            doc = col.document('one')
            await doc.set({'count':0, 'values':[], 'at':datetime.now(UTC)})
            await asyncio.gather(*[doc.update({'count':Increment(1), 'values':ArrayUnion([n % 3])}) for n in range(30)])
            body = (await doc.get()).to_dict()
            self.assertEqual(body['count'], 30)
            self.assertEqual(len(body['values']), 3)
            self.assertIsInstance(body['at'], datetime)
            for n in range(4):
                await col.document(f'item{n}').set({'order':n, 'status':'active'})
            query = col.where('status','==','active').order_by('order', direction='DESCENDING')
            first = await query.limit(2).get()
            second = await query.start_after(first[-1]).get()
            self.assertEqual([d.id for d in first + second], ['item3','item2','item1','item0'])
            await doc.collection('children').document('child').set({'x':True})
            await doc.delete()
            self.assertFalse((await doc.get()).exists)
            self.assertEqual(await doc.collection('children').get(), [])
        asyncio.run(run())
        env = dict(os.environ, AIRA_DATA_DIR=str(settings.aira_data_dir))
        child = subprocess.run([str(ROOT / '.venv/Scripts/python.exe'), '-c',
            "import asyncio; from app.core.local_store import get_store; print(len(asyncio.run(get_store().collection('counter').get())))"],
            cwd=ROOT/'backend', env=env, capture_output=True, text=True)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout.strip(), '4')

    def test_palace_memory_session_restart_records(self):
        self.sign_in()
        self.assertEqual(self.client.post('/api/v1/palace').status_code, 409)
        self.assertEqual(len(self.client.get('/api/v1/palace').json()['rooms']), 15)
        async def records():
            with patch.object(room_service, 'get_embedding', return_value=[1.,0.]), patch.object(artifact_service, 'get_embedding', return_value=[1.,0.]):
                room = await room_service.create_room('local', 'Test topic', ['test'])
                await room_service.add_lobby_door('local', room.id)
                await capture_service.start_session('local','session_test','voice')
                artifact = await artifact_service.create_artifact(user_id='local', room_id=room.id,
                    artifact_type='insight', title='Test fact', summary='A saved test fact',
                    full_content='Evidence content', capture_session_id='session_test')
                await capture_service.add_artifact_to_session('local','session_test',artifact.id)
                await room_service.increment_artifact_count('local',room.id)
                await capture_service.end_session('local','session_test')
                enrichment = await enrichment_service.create_enrichment(user_id='local',room_id=room.id,artifact_id=artifact.id,
                    source_url='https://example.com/reference', source_name='Test source', extracted_content='Test reference')
                self.assertEqual((await enrichment_service.get_enrichments_for_artifact(user_id='local',room_id=room.id,artifact_id=artifact.id))[0].id, enrichment.id)
                return room.id, artifact.id
        room_id, art_id = asyncio.run(records())
        palace = self.client.get('/api/v1/palace').json()
        self.assertEqual(next(r for r in palace['rooms'] if r['id'] == room_id)['artifactCount'],1)
        self.assertEqual(palace['artifacts'][room_id][0]['fullContent'],'Evidence content')
        self.assertEqual(self.client.get('/api/v1/sessions/session_test').json()['session']['conceptCount'],1)
        self.assertEqual(self.client.get(f'/artifacts/{art_id}').status_code,200)
        self.assertEqual(self.client.patch('/api/v1/palace/layout',json={'lastRoomId':room_id}).status_code,200)
        self.assertEqual(self.client.get('/api/v1/palace').json()['layout']['lastRoomId'],room_id)
        self.assertEqual(self.client.delete(f'/api/v1/rooms/{room_id}').status_code,200)
        self.assertEqual(len(self.client.get('/api/v1/palace').json()['rooms']),15)

    def test_windows_encryption(self):
        value = b'fake-test-value-not-a-key'
        encrypted = _crypt(value)
        self.assertNotIn(value, encrypted)
        self.assertEqual(_crypt(encrypted, decrypt=True), value)

    def test_usage_endpoint_is_local_protected_and_diagnostics_do_not_overlap_live(self):
        self.assertEqual(self.client.get('/api/v1/usage').status_code, 401)
        self.sign_in()
        response = self.client.get('/api/v1/usage')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['calls'], 0)
        with patch('app.core.tracked_gemini.has_live_for_user', return_value=True), patch('app.routers.settings.get_genai_client') as gemini:
            self.assertEqual(self.client.post('/api/v1/settings/test').status_code, 409)
            gemini.assert_not_called()

    def test_settings_secret_persistence_and_account_mismatch(self):
        self.sign_in()
        fake = 'fake-test-value-not-a-real-api-key'
        response = self.client.put('/api/v1/settings', json={'geminiApiKey':fake})
        self.assertEqual(response.status_code,200)
        encrypted_path = settings.aira_data_dir / 'secrets/gemini.dpapi'
        self.assertTrue(encrypted_path.exists())
        self.assertNotIn(fake.encode(),encrypted_path.read_bytes())
        self.assertNotIn(fake.encode(),(settings.aira_data_dir/'db/aira.sqlite3').read_bytes())
        from app.services.user_settings_service import get_user_gemini_key
        self.assertEqual(asyncio.run(get_user_gemini_key('local')),fake)
        with patch('app.services.user_settings_service.read_key', side_effect=OSError('wrong Windows account')):
            self.assertIsNone(asyncio.run(get_user_gemini_key('local')))
        self.assertEqual(self.client.put('/api/v1/settings', json={'geminiApiKey':None}).status_code,200)
        self.assertFalse(encrypted_path.exists())

if __name__ == '__main__':
    unittest.main()
