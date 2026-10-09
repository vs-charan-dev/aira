import asyncio
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.config import settings
from app.core.local_auth import new_session
from app.routers import tasks
from app.services.task_store import TaskStore
from app.services.task_supervisor import TaskSupervisor
from app.services import invoice_demo

class TaskApiTests(unittest.TestCase):
    def test_demo_selection_reset_guards_generation_and_private_bounded_logs(self):
        with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as folder:
            async def coding(row, progress):
                for index in range(170): await progress('\x1b[32mObserved test line '+str(index)+'\x00')
                await asyncio.Future()
            async def desktop(*args,**kwargs): return 'Desktop action succeeded: synthetic editor shown'
            s=TaskSupervisor(TaskStore(Path(folder)/'jobs.sqlite3'),coding=coding,desktop=desktop,invoice_coding=coding)
            @asynccontextmanager
            async def lifespan(app):
                yield
                await s.close()
            app=FastAPI(lifespan=lifespan);app.include_router(tasks.router)
            with patch.object(tasks,'get_supervisor',return_value=s),patch.object(invoice_demo,'folder',return_value=Path(folder)/'invoice-showcase'),patch('app.services.task_supervisor.validate_project',side_effect=lambda **value:value),patch('app.services.task_supervisor.manager.get_connection',return_value=object()),TestClient(app) as client:
                base='/api/v1/tasks/invoice-demo'
                self.assertEqual(client.get(base).status_code,401)
                headers={'Authorization':'Bearer '+new_session(),'Origin':'http://testserver'}
                self.assertEqual(client.post(base+'/prepare',json={},headers={**headers,'Origin':'https://invalid.example'}).status_code,403)
                self.assertEqual(client.post(base+'/prepare',json={'reset':'yes'},headers=headers).status_code,400)
                value=client.post(base+'/prepare',json={},headers=headers).json()
                self.assertEqual(s.store.config('local')['path'],value['path'])
                self.assertEqual(client.post(base+'/fix',json={'requestId':'demo-fix','generation':'stale'},headers=headers).status_code,400)
                result=client.post(base+'/fix',json={'requestId':'demo-fix','generation':value['generation']},headers=headers)
                self.assertEqual(result.status_code,200); row=result.json()
                self.assertEqual(row['mode'],'fix');self.assertEqual(row['demoGeneration'],value['generation'])
                self.assertEqual(client.post(base+'/fix',json={'requestId':'demo-fix','generation':value['generation']},headers=headers).json()['id'],row['id'])
                self.assertEqual(client.post(base+'/prepare',json={'reset':True},headers=headers).status_code,400)
                listed=client.get('/api/v1/tasks',headers=headers).json()
                self.assertNotIn('events',listed['jobs'][0])
                observed=client.get('/api/v1/tasks/'+row['id']+'/events',headers=headers).json()['events']
                self.assertEqual(len(observed),160)
                self.assertNotIn('\x1b',observed[0]['text']);self.assertNotIn('\x00',observed[0]['text'])
                self.assertEqual(client.get('/api/v1/tasks/unknown/events',headers=headers).status_code,404)
                client.post('/api/v1/tasks/'+row['id']+'/control',json={'action':'cancel'},headers=headers)
                reset=client.post(base+'/prepare',json={'reset':True},headers=headers).json()
                self.assertNotEqual(reset['generation'],value['generation'])

    def test_auth_origin_job_controls_and_reports_without_desktop_side_effects(self):
        with tempfile.TemporaryDirectory(dir=settings.aira_cache_dir) as folder:
            async def desktop(*args,**kwargs): await asyncio.Future()
            supervisor=TaskSupervisor(TaskStore(Path(folder)/'tasks.sqlite3'),desktop=desktop)
            @asynccontextmanager
            async def lifespan(app):
                yield
                await supervisor.close()
            app=FastAPI(lifespan=lifespan);app.include_router(tasks.router)
            with patch.object(tasks,'get_supervisor',return_value=supervisor),patch('app.services.task_supervisor.manager.get_connection',return_value=object()),TestClient(app) as client:
                self.assertEqual(client.get('/api/v1/tasks').status_code,401)
                token=new_session();headers={'Authorization':'Bearer '+token,'Origin':'http://testserver'}
                self.assertEqual(client.post('/api/v1/tasks/stop-all',json={},headers={**headers,'Origin':'https://invalid.example'}).status_code,403)
                body={'requestId':'api-test','tool':'create_notion_note','args':{'title':'Synthetic','content':'Synthetic fixture; no native controller'}}
                response=client.post('/api/v1/tasks',json=body,headers=headers)
                self.assertEqual(response.status_code,200)
                ident=response.json()['id']
                self.assertEqual(client.post('/api/v1/tasks',json=body,headers=headers).json()['id'],ident)
                listed=client.get('/api/v1/tasks',headers=headers).json()
                self.assertEqual(len(listed['jobs']),1);self.assertNotIn('requestKey',listed['jobs'][0]);self.assertNotIn('user',listed['jobs'][0])
                self.assertEqual(client.get('/api/v1/tasks/unknown/report',headers=headers).status_code,404)
                response=client.post('/api/v1/tasks/'+ident+'/control',json={'action':'cancel'},headers=headers)
                self.assertEqual(response.json()['status'],'cancelled')
                self.assertTrue(client.post('/api/v1/tasks/stop-all',json={},headers=headers).json()['ok'])
