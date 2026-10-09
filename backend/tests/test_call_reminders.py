"""Phone reminders with fake time and fake Twilio; never places real calls."""
import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs
from xml.etree.ElementTree import fromstring
from base64 import b64encode

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.core.local_auth import new_session
from app.routers import call_reminders as routes
from app.services.call_reminders import CallReminders, ReminderStore, due_time, IST
from app.services.twilio_voice import TwilioVoice, AcceptedCall, CallRejected, CallUncertain, save_credentials, read_credentials, public_settings, credentials_path

CONFIG = {'accountSid': 'AC' + '1' * 32, 'authToken': '2' * 32,
          'fromNumber': '+14155550100', 'toNumber': '+919876543210'}
SID = 'CA' + '3' * 32


class FakeVoice:
    def __init__(self):
        self.calls = []
        self.statuses = []
        self.failure = None

    async def create(self, config, message):
        self.calls.append((dict(config), message))
        if self.failure:
            raise self.failure
        return AcceptedCall(SID)

    async def status(self, config, sid):
        self.statuses.append(sid)
        return 'completed'


class ReminderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.store = ReminderStore(Path(self.tmp.name) / 'reminders.sqlite3')
        self.now = datetime(2026, 10, 9, 9, 0, tzinfo=IST).timestamp()
        self.voice = FakeVoice()
        self.config = dict(CONFIG)
        self.service = CallReminders(self.store, self.voice, lambda: self.config, lambda: self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def schedule(self, **args):
        return self.service.schedule('local', {'message': 'Time to head out.', 'after_seconds': 60, **args})

    async def test_no_early_call_then_one_dispatch_even_with_two_workers(self):
        row = self.schedule()
        await self.service.tick()
        self.assertEqual(self.voice.calls, [])
        # A distinct service instance contends for the same SQLite claim.
        other = CallReminders(ReminderStore(self.store.path), self.voice, lambda: CONFIG, lambda: self.now)
        self.now += 60
        await asyncio.gather(self.service.tick(), other.tick())
        await self.service.tick()
        self.assertEqual(len(self.voice.calls), 1)
        saved = self.store.get('local', row['id'])
        self.assertEqual(saved['call_sid'], SID)
        self.assertEqual(saved['call_status'], 'completed')
        self.assertEqual(saved['status'], 'finished')

    async def test_cancel_prevents_dispatch_and_unknown_id_does_not_cancel_others(self):
        row = self.schedule()
        with self.assertRaises(ValueError):
            self.store.cancel('local', 'invented-id', self.now)
        with self.assertRaises(ValueError):
            self.store.cancel('another-user', row['id'], self.now)
        self.store.cancel('local', row['id'], self.now)
        self.now += 70
        await self.service.tick()
        self.assertEqual(self.voice.calls, [])
        self.assertEqual(self.store.get('local', row['id'])['status'], 'cancelled')

    async def test_relative_clock_time_and_validation(self):
        self.assertEqual(due_time({'after_seconds': 2040}, self.now), self.now + 2040)
        self.assertEqual(due_time({'local_time': '09:05'}, self.now), self.now + 300)
        tomorrow = due_time({'local_time': '09:05', 'local_date': '2026-10-10'}, self.now)
        self.assertEqual(tomorrow, self.now + 86700)
        for args in ({}, {'after_seconds': True}, {'after_seconds': float('nan')},
                     {'after_seconds': 0}, {'after_seconds': 8 * 86400},
                     {'after_seconds': 60, 'local_time': '09:05'},
                     {'local_time': '9:05'}, {'local_time': '24:00'}, {'local_time': '08:59'},
                     {'local_time': '09:05', 'local_date': '2026-02-30'},
                     {'local_time': '09:05', 'local_date': 20261009},
                     {'after_seconds': 60, 'local_date': '2026-10-09'}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                due_time(args, self.now)
        row = self.service.schedule('local', {'message': 'Head out.', 'local_time': '09:05'})
        self.assertEqual(row['dueLocal'], '2026-10-09T09:05:00+05:30')

    async def test_idempotency_survives_lost_ack_restart_and_cancel(self):
        first = self.schedule(requestId='voice-call-id')
        self.now += 15
        service = CallReminders(ReminderStore(self.store.path), self.voice, lambda: CONFIG, lambda: self.now)
        again = service.schedule('local', {'message': 'Time to head out.', 'after_seconds': 60, 'requestId': 'voice-call-id'})
        self.assertEqual(first['id'], again['id'])
        self.store.cancel('local', first['id'], self.now)
        again = service.schedule('local', {'message': 'Time to head out.', 'after_seconds': 60, 'requestId': 'voice-call-id'})
        self.assertEqual(again['status'], 'cancelled')
        self.assertEqual(len(self.store.rows('local')), 1)

    async def test_pending_survives_restart_recent_due_fires_old_due_is_missed(self):
        recent = self.schedule()
        old = self.schedule(message='Another reminder.', after_seconds=10)
        self.now += 150
        restarted = CallReminders(ReminderStore(self.store.path), self.voice, lambda: CONFIG, lambda: self.now)
        restarted.store.recover(self.now)
        await restarted.tick()
        self.assertEqual(len(self.voice.calls), 1)
        self.assertEqual(self.store.get('local', recent['id'])['status'], 'finished')
        self.assertEqual(self.store.get('local', old['id'])['status'], 'missed')

    async def test_dispatch_crash_and_network_uncertainty_never_retry(self):
        crashed = self.schedule()
        self.now += 60
        self.store.claim(self.now)
        self.store.recover(self.now)
        await self.service.tick()
        self.assertEqual(self.store.get('local', crashed['id'])['status'], 'uncertain')
        self.assertEqual(self.voice.calls, [])
        timed_out = self.schedule(message='Network test.')
        self.voice.failure = CallUncertain('Fake lost response')
        self.now += 60
        await self.service.tick()
        await self.service.tick()
        self.assertEqual(len(self.voice.calls), 1)
        self.assertEqual(self.store.get('local', timed_out['id'])['status'], 'uncertain')

    async def test_backend_shutdown_during_post_records_uncertainty(self):
        entered = asyncio.Event()
        async def slow(config, message):
            entered.set()
            await asyncio.Future()
        self.voice.create = slow
        row = self.schedule()
        self.now += 60
        task = asyncio.create_task(self.service.tick())
        await entered.wait()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(self.store.get('local', row['id'])['status'], 'uncertain')

    async def test_recipient_frozen_and_changed_account_or_missing_setup_fails(self):
        first = self.schedule()
        self.config['toNumber'] = '+919876543211'
        self.now += 60
        await self.service.tick()
        self.assertEqual(self.voice.calls[0][0]['toNumber'], CONFIG['toNumber'])
        self.assertEqual(self.store.get('local', first['id'])['status'], 'finished')
        second = self.schedule(message='Account changed.')
        self.config['accountSid'] = 'AC' + '4' * 32
        self.now += 60
        await self.service.tick()
        self.assertEqual(self.store.get('local', second['id'])['status'], 'failed')
        self.assertEqual(len(self.voice.calls), 1)
        self.config = None
        with self.assertRaises(ValueError):
            self.schedule()

    async def test_provider_rejection_and_pending_only_cancellation(self):
        self.voice.failure = CallRejected('Fake insufficient credit')
        row = self.schedule()
        self.now += 60
        await self.service.tick()
        self.assertEqual(self.store.get('local', row['id'])['status'], 'failed')
        with self.assertRaises(ValueError):
            self.store.cancel('local', row['id'], self.now)
        await self.service.tick()
        self.assertEqual(len(self.voice.calls), 1)

    async def test_trial_audio_mode_remains_visible_after_call_finishes(self):
        async def trial(config, message):
            return AcceptedCall(SID, 'trial-demo')
        self.voice.create = trial
        row = self.schedule()
        self.now += 60
        await self.service.tick()
        saved = self.store.public(self.store.get('local', row['id']))
        self.assertEqual(saved['callMode'], 'trial-demo')
        self.assertEqual(saved['status'], 'finished')
        self.assertIn('not the saved reminder text', saved['detail'])

    async def test_existing_database_migration_keeps_saved_reminders(self):
        row = self.schedule()
        with self.store.connect() as db:
            db.execute('ALTER TABLE reminders DROP COLUMN call_mode')
        migrated = ReminderStore(self.store.path)
        saved = migrated.public(migrated.get('local', row['id']))
        self.assertEqual(saved['status'], 'pending')
        self.assertEqual(saved['message'], row['message'])
        self.assertIsNone(saved['callMode'])

    async def test_single_recipient_guard_private_list_and_pending_limit(self):
        with self.assertRaises(ValueError):
            self.schedule(toNumber='+14155550200')
        with self.assertRaises(ValueError):
            self.schedule(message='x' * 501)
        row = self.schedule()
        value = json.dumps(row)
        for secret in (CONFIG['authToken'], CONFIG['accountSid'], CONFIG['toNumber']):
            self.assertNotIn(secret, value)
        for i in range(19):
            self.schedule(message='Reminder ' + str(i))
        with self.assertRaises(ValueError):
            self.schedule(message='Limit exceeded')

    async def test_both_voice_modes_dispatch_reminder_tools(self):
        from app.agents.capture_agent import CaptureAgent
        from app.agents.recall_agent import RecallAgent
        from app.agents.tools.tools import CAPTURE_LIVE_TOOLS, RECALL_LIVE_TOOLS
        from app.services.call_reminders import REMINDER_NAMES
        for declarations in (CAPTURE_LIVE_TOOLS, RECALL_LIVE_TOOLS):
            self.assertTrue(REMINDER_NAMES <= {tool['name'] for tool in declarations})
        capture = CaptureAgent('local', 'fixture', lambda event: None)
        capture._user_has_spoken = True
        recall = RecallAgent()
        with patch('app.services.call_reminders.get_reminders', return_value=self.service):
            first = json.loads(await capture._execute_tool('schedule_call_reminder', {'message': 'Capture reminder.', 'after_seconds': 300}))
            second = json.loads(await recall._execute_tool('local', 'schedule_call_reminder', {'message': 'Recall reminder.', 'local_time': '09:05'}, None))
            self.assertEqual(first['status'], 'pending')
            self.assertEqual(second['dueLocal'], '2026-10-09T09:05:00+05:30')
            listed = json.loads(await recall._execute_tool('local', 'list_call_reminders', {}, None))
            self.assertEqual(len(listed), 2)
            cancelled = json.loads(await capture._execute_tool('cancel_call_reminder', {'reminder_id': first['id']}))
            self.assertEqual(cancelled['status'], 'cancelled')
        self.assertEqual(self.voice.calls, [])


class TwilioAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_http_contract_escaped_twiml_and_status_without_webhook(self):
        observed = []
        def handler(request):
            observed.append(request)
            if '/Calls' not in request.url.path:
                return httpx.Response(200, json={'type': 'Full', 'status': 'active'})
            if request.method == 'POST':
                return httpx.Response(201, json={'sid': SID, 'status': 'queued'})
            return httpx.Response(200, json={'status': 'completed'})
        adapter = TwilioVoice(httpx.MockTransport(handler))
        message = 'Head out <now> & bring "keys".'
        self.assertEqual(await adapter.create(CONFIG, message), AcceptedCall(SID))
        self.assertEqual(await adapter.status(CONFIG, SID), 'completed')
        form = parse_qs(observed[1].content.decode())
        self.assertEqual(form['To'], [CONFIG['toNumber']])
        self.assertEqual(form['From'], [CONFIG['fromNumber']])
        xml = fromstring(form['Twiml'][0])
        self.assertEqual(xml.find('Say').text, 'Hi, this is AIRA. ' + message)
        self.assertIsNotNone(xml.find('Hangup'))
        self.assertEqual(form['Record'], ['false'])
        self.assertNotIn('Url', form)
        self.assertNotIn('StatusCallback', form)
        self.assertIn('/Calls/' + SID + '.json', str(observed[2].url))
        self.assertTrue(observed[1].headers['authorization'].startswith('Basic '))

    async def test_trial_uses_supported_template_with_one_post(self):
        observed = []
        def handler(request):
            observed.append(request)
            if request.method == 'GET':
                return httpx.Response(200, json={'type': 'Trial', 'status': 'active'})
            form = parse_qs(request.content.decode())
            self.assertEqual(set(form), {'To', 'From', 'Url'})
            self.assertEqual(form['Url'], ['https://webhooks.twilio.com/v1/Voice/Template/voice_text_to_speech'])
            return httpx.Response(201, json={'sid': SID})
        result = await TwilioVoice(httpx.MockTransport(handler)).create(CONFIG, 'Head out.')
        self.assertEqual(result, AcceptedCall(SID, 'trial-demo'))
        self.assertEqual([request.method for request in observed], ['GET', 'POST'])

    async def test_trial_parameter_error_is_actionable_and_redacts_echoed_secrets(self):
        observed = []
        basic = b64encode((CONFIG['accountSid'] + ':' + CONFIG['authToken']).encode()).decode()
        detail = 'Invalid or disallowed parameters provided - trial accounts have limited parameter access, upgrade your account to unlock full functionality'
        def handler(request):
            observed.append(request)
            if request.method == 'GET':
                return httpx.Response(200, json={'type': 'Trial', 'status': 'active'})
            return httpx.Response(400, json={'code': 0, 'message': detail + ' ' + ' '.join(CONFIG.values()) + ' ' + basic})
        with self.assertRaises(CallRejected) as caught:
            await TwilioVoice(httpx.MockTransport(handler)).create(CONFIG, 'Fixture')
        self.assertIn('HTTP 400', str(caught.exception))
        self.assertIn(detail, str(caught.exception))
        self.assertNotIn('code 0', str(caught.exception))
        for secret in [basic, *CONFIG.values()]:
            self.assertNotIn(secret, str(caught.exception))
        self.assertEqual(sum(request.method == 'POST' for request in observed), 1)

    async def test_account_lookup_failure_does_not_attempt_a_call(self):
        for payload in ({'type': 'Full', 'status': 'suspended'}, {'type': 'unknown'}, []):
            observed = []
            def handler(request):
                observed.append(request)
                return httpx.Response(200, json=payload)
            with self.assertRaises(CallRejected):
                await TwilioVoice(httpx.MockTransport(handler)).create(CONFIG, 'Fixture')
            self.assertEqual([request.method for request in observed], ['GET'])

    async def test_safe_errors_and_no_transport_retries(self):
        for code in (401, 500):
            calls = []
            def handler(request):
                if request.method == 'GET':
                    return httpx.Response(200, json={'type': 'Full', 'status': 'active'})
                calls.append(request)
                return httpx.Response(code, json={'message': 'SECRET ' + CONFIG['authToken'], 'code': 21215})
            adapter = TwilioVoice(httpx.MockTransport(handler))
            error = CallRejected if code == 401 else CallUncertain
            with self.assertRaises(error) as caught:
                await adapter.create(CONFIG, 'Fixture')
            self.assertNotIn(CONFIG['authToken'], str(caught.exception))
            self.assertEqual(len(calls), 1)
        calls = []
        def timeout(request):
            if request.method == 'GET':
                return httpx.Response(200, json={'type': 'Full', 'status': 'active'})
            calls.append(request)
            raise httpx.ReadTimeout('Fixture')
        with self.assertRaises(CallUncertain):
            await TwilioVoice(httpx.MockTransport(timeout)).create(CONFIG, 'Fixture')
        self.assertEqual(len(calls), 1)


class ReminderApiTests(unittest.TestCase):
    def test_auth_origin_encrypted_settings_schedule_list_cancel_and_remove(self):
        with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as folder, patch.object(settings, 'aira_data_dir', Path(folder)):
            voice = FakeVoice()
            service = CallReminders(voice=voice)
            app = FastAPI()
            app.include_router(routes.router)
            with patch.object(routes, 'get_reminders', return_value=service), TestClient(app) as client:
                base = '/api/v1/call-reminders'
                self.assertEqual(client.get(base).status_code, 401)
                headers = {'Authorization': 'Bearer ' + new_session(), 'Origin': 'http://testserver'}
                invalid = {**headers, 'Origin': 'https://invalid.example'}
                self.assertEqual(client.put(base + '/settings', json=CONFIG, headers=invalid).status_code, 403)
                self.assertFalse(client.get(base + '/settings', headers=headers).json()['configured'])
                self.assertEqual(client.post(base, json={'message': 'Fixture', 'after_seconds': 60}, headers=headers).status_code, 400)
                response = client.put(base + '/settings', json=CONFIG, headers=headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn('authToken', response.json())
                self.assertNotIn(CONFIG['authToken'].encode(), credentials_path().read_bytes())
                self.assertEqual(read_credentials(), CONFIG)
                # Editing same account can keep a token, account switches cannot.
                self.assertEqual(client.put(base + '/settings', json={**CONFIG, 'authToken': ''}, headers=headers).status_code, 200)
                self.assertEqual(client.put(base + '/settings', json={**CONFIG, 'accountSid': 'AC' + '4' * 32, 'authToken': ''}, headers=headers).status_code, 400)
                self.assertEqual(client.put(base + '/settings', json={**CONFIG, 'fromNumber': '+919876543211'}, headers=headers).status_code, 400)
                body = {'message': 'Fixture', 'after_seconds': 60, 'requestId': 'browser-id'}
                response = client.post(base, json=body, headers=headers)
                self.assertEqual(response.status_code, 200)
                ident = response.json()['id']
                self.assertEqual(client.post(base, json=body, headers=headers).json()['id'], ident)
                self.assertEqual(client.post(base, json={**body, 'toNumber': '+14155550200'}, headers=headers).status_code, 400)
                self.assertEqual(len(client.get(base, headers=headers).json()['reminders']), 1)
                self.assertEqual(client.post(base + '/' + ident + '/cancel', json={}, headers=invalid).status_code, 403)
                self.assertEqual(client.post(base + '/' + ident + '/cancel', json={}, headers=headers).json()['status'], 'cancelled')
                second = client.post(base, json={**body, 'requestId': 'second-id'}, headers=headers).json()
                self.assertEqual(client.delete(base + '/settings', headers=headers).status_code, 200)
                self.assertEqual(service.store.get('local', second['id'])['status'], 'cancelled')
                self.assertFalse(credentials_path().exists())
                self.assertEqual(voice.calls, [])

    def test_unreadable_secrets_report_actionable_error_without_token(self):
        with patch('app.services.twilio_voice.read_credentials', side_effect=ValueError('Save settings again.')):
            value = public_settings()
        self.assertFalse(value['configured'])
        self.assertEqual(value['storageError'], 'Save settings again.')


if __name__ == '__main__':
    unittest.main()
