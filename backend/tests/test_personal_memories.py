"""Offline integration coverage of personal context; no provider calls."""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.services.personal_memory_service import (
    seed_definition, ensure_personal_palace, list_memories, rank_memories, UNKNOWN,
)
from app.agents.recall_agent import RecallAgent
from app.services import artifact_service
from app.core.local_store import get_store
from app.services.search_service import semantic_search


class PersonalMemories(unittest.TestCase):
    def setUp(self):
        self.original = settings.aira_data_dir
        settings.aira_cache_dir.joinpath('tmp').mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=settings.aira_cache_dir / 'tmp')
        settings.aira_data_dir = Path(self.tmp.name)
        self.client = TestClient(app)
        self.client.__enter__()
        self.client.headers['Origin'] = 'http://testserver'
        self.client.post('/api/v1/local-session')

    def tearDown(self):
        self.client.__exit__(None, None, None)
        settings.aira_data_dir = self.original
        self.tmp.cleanup()

    def query(self, text):
        result = self.client.post('/api/v1/personal-memories/query', json={'query':text})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def correction(self, id, **changes):
        return self.client.patch('/api/v1/personal-memories/' + id, json={'expected_version':1, **changes})

    def test_all_rooms_are_actual_artifacts_with_source_provenance(self):
        seed = seed_definition()
        data = self.client.get('/api/v1/personal-memories').json()
        palace = self.client.get('/api/v1/palace').json()
        self.assertEqual(len(data['rooms']), 15)
        self.assertEqual(len(data['memories']), 181)
        self.assertEqual(len(palace['rooms']), 15)
        self.assertEqual(len(palace['layout']['lobbyDoors']), 15)
        self.assertEqual(palace['palace']['artifactCount'], 181)
        self.assertEqual(len({m['id'] for m in seed['memories']}), 181)
        for memory in data['memories']:
            self.assertGreater(memory['source_line'], 0)
            self.assertEqual(memory['created_at'], '2026-10-09')
            self.assertIsNone(memory['event_date'])
            artifact = next(a for a in palace['artifacts'][memory['room_id']] if a['id']==memory['id'])
            self.assertEqual(artifact['personalMemory']['memory'], memory['memory'])

    def test_salary_and_city_question_cites_both_facets(self):
        response = self.query('Where do I want to work and what package am I targeting?')
        self.assertIn('Hyderabad', response['answer'])
        self.assertIn('24 LPA', response['answer'])
        ids = {m['id'] for m in response['references']}
        self.assertIn('CAREER-002', ids)
        self.assertIn('CAREER-003', ids)
        self.assertNotIn('CAREER-011', ids)  # salary reasons aren't a salary target

    def test_hackathon_lessons_and_explanation_preferences(self):
        response = self.query('What did I learn from previous hackathons?')
        self.assertIn('presentation', response['answer'])
        self.assertIn('DECISION-003', [m['id'] for m in response['references']])
        self.assertIn('DECISION-004', [m['id'] for m in response['references']])
        response = self.query('How should you explain technical topics to me?')
        self.assertIn('PREFERENCE-003', [m['id'] for m in response['references']])
        self.assertTrue(any(m['id'].startswith('LEARNING') for m in response['references']))
        self.assertEqual(response['kind'], 'fact')

    def test_unknown_is_not_invented(self):
        for query in ['What is my mother name?', 'What is my favourite food?', 'Which programming languages and frameworks do I use?', 'When did I start B.Tech?']:
            response = self.query(query)
            self.assertEqual(response['answer'], UNKNOWN)
            self.assertEqual(response['kind'], 'unknown')

    def test_correction_history_conflict_and_outdated_exclusion(self):
        response = self.correction('CAREER-003', memory='My target minimum package is approximately ₹30 LPA.')
        self.assertEqual(response.status_code, 200, response.text)
        corrected = response.json()['memory']
        self.assertEqual(corrected['version'], 2)
        self.assertIn('24 LPA', corrected['history'][0]['memory'])
        answer = self.query('What package am I targeting?')
        self.assertTrue(answer['conflicts'])
        self.assertIn('Conflicting', answer['answer'])
        self.assertEqual(self.correction('CAREER-003', status='outdated').status_code, 409)
        result = self.client.patch('/api/v1/personal-memories/CAREER-003', json={'expected_version':2, 'status':'outdated'})
        self.assertEqual(result.status_code, 200)
        answer = self.query('What package am I targeting?')
        self.assertNotIn('CAREER-003', [m['id'] for m in answer['references']])
        self.assertFalse(answer['conflicts'])

    def test_reimport_preserves_corrections_and_event_dates(self):
        result = self.correction('TIMELINE-001', event_date='2022-08-15', status='uncertain')
        self.assertEqual(result.status_code, 200, result.text)
        asyncio.run(ensure_personal_palace('local'))
        data = asyncio.run(list_memories('local'))
        memory = next(m for m in data if m['id']=='TIMELINE-001')
        self.assertEqual(memory['event_date'], '2022-08-15')
        self.assertEqual(memory['version'], 2)
        self.assertEqual(len(data),181)
        self.assertIn('2022-08-15', self.query('When did I start B.Tech?')['answer'])
        self.assertEqual(self.correction('TIMELINE-002', event_date='2026-02-30').status_code, 422)

    def test_secrets_and_unauthenticated_access_are_rejected(self):
        for secret in ['My password is example-secret', 'API key: AIza' + 'a'*25, 'Banking pin: 1234', 'OTP: 543210']:
            self.assertEqual(self.correction('CAREER-003', memory=secret).status_code, 422)
        # A second request client needs no second app lifespan/event loop.
        other = TestClient(app)
        self.assertEqual(other.get('/api/v1/personal-memories').status_code,401)
        other.close()
        self.assertEqual(self.correction('CAREER-003', memory='  ').status_code,422)

    def test_agent_tool_reads_the_same_corrected_context_without_embedding(self):
        self.correction('PERSON-006', memory='Vinay leads testing on AIRA.')
        async def run():
            notify = AsyncMock()
            result = await RecallAgent()._execute_tool('local','search_memories',{'query':'Who is Vinay?'},notify)
            answer = json.loads(result)
            self.assertIn('Vinay leads testing',answer['answer'])
            self.assertEqual(answer['references'][0]['id'],'PERSON-006')
            self.assertTrue(any('memoryAnswer' in call.args[1] for call in notify.await_args_list))
            await artifact_service.update_artifact('local','PERSON-006',summary='Vinay is an AIRA teammate.')
            records = await list_memories('local')
            self.assertEqual(next(m for m in records if m['id']=='PERSON-006')['version'],3)
            with patch('app.services.search_service.get_embedding', side_effect=ValueError('No key')):
                results = await semantic_search('local','Who is Vinay?')
                self.assertIn('Vinay is an AIRA teammate',results[0].summary)
        asyncio.run(run())

    def test_inference_and_uncertain_records_keep_their_labels(self):
        self.correction('PERSON-006', memory='Vinay may be available to help with AIRA.', kind='inference',status='uncertain')
        answer = self.query('Who is Vinay?')
        self.assertEqual(answer['kind'],'inference')
        self.assertIn('uncertain',answer['answer'])
        self.correction('CAREER-003',status='uncertain')
        self.assertFalse(self.query('What package am I targeting?')['conflicts'])

    def test_concurrent_import_is_idempotent(self):
        async def run():
            await asyncio.gather(*(ensure_personal_palace('other') for _ in range(3)))
            self.assertEqual(len(await list_memories('other')), 181)
            self.assertEqual(len(await list_memories('local')),181)
        asyncio.run(run())

    def test_import_preserves_existing_rooms_and_counts_only_artifacts(self):
        async def run():
            from app.services import room_service
            with patch.object(room_service, 'get_embedding', return_value=[1.,0.]), patch.object(artifact_service, 'get_embedding', return_value=[1.,0.]):
                room = await room_service.create_room('existing', 'Existing captured room', ['captured'])
                artifact = await artifact_service.create_artifact('existing', room.id, 'document', 'A real captured fact')
                await room_service.increment_artifact_count('existing',room.id)
            ref = get_store().collection('users').document('existing').collection('rooms').document(room.id).collection('artifacts').document(artifact.id)
            await ref.collection('enrichments').document('reference').set({'source':'Existing reference'})
            await ensure_personal_palace('existing')
            self.assertEqual((await ref.get()).to_dict()['summary'],'A real captured fact')
            palace = await get_store().collection('users').document('existing').collection('palace').document('main').get()
            self.assertEqual(palace.to_dict()['artifactCount'],182)
            self.assertEqual(palace.to_dict()['roomCount'],16)
            self.assertEqual(len(await list_memories('existing')),181)
        asyncio.run(run())
