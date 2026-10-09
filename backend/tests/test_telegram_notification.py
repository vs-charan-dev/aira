import asyncio
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch
from pydantic import SecretStr
from app.config import settings
from app.services import telegram_notification as telegram
from app.services.task_store import TaskStore
from app.services.task_supervisor import TaskSupervisor
import telegram_setup

TOKEN='123456789:abcdefghijklmnopqrstuvwxyz_123456'
CHAT='12345'

def completed():
    return {'id':'verified-fix','user':'local','lane':'coding','tool':'repair_invoice_app',
            'mode':'fix','status':'succeeded','createdAt':1,'completedRuns':1,
            'report':{'verified':True,'sourceChanged':True,'changedFiles':['invoice.js'],
                      'tests':{'exitCode':0,'output':'# tests 8\n# pass 8\n# fail 0'},
                      'terminalRunId':'a'*32,'terminalVerification':{'verified':True}}}


class CompletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.store=TaskStore(Path(self.temp.name)/'jobs.sqlite3')
        self.store.save(completed())
        self.patches=ExitStack()
        for name,value in {'aira_telegram_enabled':True,'aira_telegram_bot_token':SecretStr(TOKEN),'aira_telegram_chat_id':CHAT}.items():
            self.patches.enter_context(patch.object(settings,name,value))

    async def asyncTearDown(self):
        self.patches.close();self.temp.cleanup()

    async def test_success_is_private_minimal_and_deduplicated_across_restart(self):
        original=self.store.get('local','verified-fix')
        with patch.object(telegram,'bot_request',return_value={'message_id':2,'chat':{'id':int(CHAT)}}) as send:
            await asyncio.gather(telegram.notify_fix(self.store,'local','verified-fix'),telegram.notify_fix(self.store,'local','verified-fix'))
            send.assert_called_once()
            payload=send.call_args.args[2]
            self.assertEqual(payload['chat_id'],int(CHAT))
            self.assertIn('All 8 selected tests passed.',payload['text'])
            self.assertNotIn('invoice.js',payload['text']);self.assertNotIn(TOKEN,payload['text'])
            row=self.store.get('local','verified-fix')
            self.assertEqual(row.pop('telegramNotification')['status'],'sent');self.assertEqual(row,original)
            self.store=TaskStore(self.store.path)
            await telegram.notify_fix(self.store,'local','verified-fix')
            send.assert_called_once()
            row['completedRuns']=2;self.store.save(row)
            await telegram.notify_fix(self.store,'local','verified-fix')
            self.assertEqual(send.call_count,2)

    async def test_ineligible_results_and_disabled_configuration_never_send(self):
        cases=[]
        for key,value in [('mode','investigate'),('status','needs_attention'),('status','cancelled'),('lane','study')]:
            row=completed();row[key]=value;cases.append(row)
        for key,value in [('verified',False),('sourceChanged',False),('changedFiles',[]),('tests',{'exitCode':1}),('tests',{'exitCode':False}),('terminalVerification',{})]:
            row=completed();row['report'][key]=value;cases.append(row)
        with patch.object(telegram,'bot_request') as send:
            for row in cases:
                self.store.save(row);await telegram.notify_fix(self.store,'local','verified-fix')
                self.assertNotIn('telegramNotification',self.store.get('local','verified-fix'))
            self.store.save(completed())
            with patch.object(settings,'aira_telegram_enabled',False):
                await telegram.notify_fix(self.store,'local','verified-fix')
            send.assert_not_called()

    async def test_invalid_config_records_setup_requirement_without_network(self):
        with patch.object(settings,'aira_telegram_bot_token',SecretStr('')),patch.object(telegram,'bot_request') as send:
            await telegram.notify_fix(self.store,'local','verified-fix')
            send.assert_not_called()
        row=self.store.get('local','verified-fix')
        self.assertEqual(row['telegramNotification']['status'],'configuration_required')
        self.assertEqual(row['status'],'succeeded')

    async def test_delivery_failure_preserves_fix_and_never_retries_or_leaks_error(self):
        cases=[(RuntimeError('https://api.telegram.org/bot'+TOKEN),'unconfirmed'),
               (TimeoutError('timeout'),'unconfirmed'),(telegram.TelegramRejected('rejected'),'rejected'),
               ({'message_id':2,'chat':{'id':999}},'unconfirmed')]
        for result,status in cases:
            self.store.save(completed())
            with patch.object(telegram,'bot_request',**({'side_effect':result} if isinstance(result,Exception) else {'return_value':result})) as send:
                await telegram.notify_fix(self.store,'local','verified-fix')
                await telegram.notify_fix(self.store,'local','verified-fix')
                send.assert_called_once()
            row=self.store.get('local','verified-fix')
            self.assertEqual(row['telegramNotification']['status'],status)
            self.assertEqual(row['status'],'succeeded');self.assertTrue(row['report']['verified'])
            self.assertNotIn(TOKEN,json.dumps(row))

    async def test_cancelled_delivery_stays_uncertain_with_successful_fix(self):
        with patch.object(telegram,'bot_request',side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                await telegram.notify_fix(self.store,'local','verified-fix')
        row=self.store.get('local','verified-fix')
        self.assertEqual(row['status'],'succeeded')
        self.assertEqual(row['telegramNotification']['status'],'unconfirmed')

    async def test_supervisor_calls_notification_after_persisted_success_and_ignores_failure(self):
        row=completed();row.update(status='queued',completedRuns=0,revisions=[],instruction='fix',project={},report=None)
        row['tool']='coding_task';self.store.save(row)
        async def coding(job,progress):
            return {'status':'succeeded','message':'Verified','report':completed()['report']|{'terminalRunId':None}}
        supervisor=TaskSupervisor(self.store,coding=coding)
        connection=object();supervisor.connections[row['id']]=connection
        async def notify(store,user,ident):
            self.assertEqual(store.get(user,ident)['status'],'succeeded')
            raise RuntimeError('simulated transport failure')
        with patch('app.services.task_supervisor.manager.get_connection',return_value=connection),patch.object(telegram,'notify_fix',side_effect=notify) as hook:
            await supervisor.run('local',row['id']);hook.assert_awaited_once()
        self.assertEqual(self.store.get('local',row['id'])['status'],'succeeded')


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=settings.aira_cache_dir)
        self.root=Path(self.temp.name)

    def tearDown(self): self.temp.cleanup()

    def test_env_update_preserves_other_settings_and_refuses_invalid_values_or_temp(self):
        env=self.root/'.env';env.write_text('GEMINI_API_KEY=private-example\nPORT=8000\nAIRA_TELEGRAM_ENABLED=false\n',encoding='utf-8')
        telegram_setup.save_config(env,TOKEN,CHAT)
        text=env.read_text(encoding='utf-8')
        self.assertIn('GEMINI_API_KEY=private-example\nPORT=8000',text)
        self.assertEqual(text.count('AIRA_TELEGRAM_ENABLED='),1)
        self.assertIn('AIRA_TELEGRAM_ENABLED=true',text)
        with self.assertRaises(ValueError):telegram_setup.save_config(env,'bad',CHAT)
        self.assertEqual(env.read_text(encoding='utf-8'),text)
        temporary=self.root/'.env.telegram.tmp';temporary.write_text('preserve')
        with self.assertRaises(ValueError):telegram_setup.save_config(env,TOKEN,CHAT)
        self.assertEqual(temporary.read_text(),'preserve')
        self.assertEqual(env.read_text(encoding='utf-8'),text)

    def test_setup_observes_private_chat_without_sending_messages_or_echoing_token(self):
        responses=[{'is_bot':True,'username':'AiraDemo_bot'},
                   [{'message':{'chat':{'id':int(CHAT),'type':'private'}}},
                    {'message':{'chat':{'id':-12,'type':'group'}}}]]
        output=io.StringIO()
        with patch.object(telegram_setup,'ROOT',self.root),patch.object(telegram_setup.getpass,'getpass',return_value=TOKEN),patch('builtins.input',return_value=''),patch.object(telegram_setup,'bot_request',side_effect=responses) as request,redirect_stdout(output):
            telegram_setup.main()
        self.assertEqual([c.args[1] for c in request.call_args_list],['getMe','getUpdates'])
        self.assertNotIn(TOKEN,output.getvalue())
        self.assertIn('AIRA_TELEGRAM_CHAT_ID='+CHAT,(self.root/'.env').read_text())
        self.assertEqual(request.call_args_list[1].args[2],{'limit':100,'timeout':0})

    def test_multiple_private_chats_require_observed_selection(self):
        updates=[{'message':{'chat':{'id':i,'type':'private'}}} for i in (12345,67890)]
        with patch.object(telegram_setup,'ROOT',self.root),patch.object(telegram_setup.getpass,'getpass',return_value=TOKEN),patch('builtins.input',side_effect=['','999']),patch.object(telegram_setup,'bot_request',side_effect=[{'is_bot':True,'username':'AiraDemo_bot'},updates]),redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):telegram_setup.main()
        self.assertFalse((self.root/'.env').exists())

    def test_bot_transport_is_bounded_fixed_https_and_refuses_redirects(self):
        response=MagicMock();response.__enter__.return_value=response
        response.read.return_value=b'{"ok":true,"result":{"message_id":1}}'
        opener=MagicMock();opener.open.return_value=response
        with patch.object(telegram.urllib.request,'build_opener',return_value=opener) as build:
            result=telegram.bot_request(TOKEN,'sendMessage',{'chat_id':12345,'text':'AIRA'})
            self.assertEqual(result,{'message_id':1})
            self.assertIsInstance(build.call_args.args[0],telegram.NoRedirect)
            request=opener.open.call_args.args[0]
            self.assertEqual(request.full_url,'https://api.telegram.org/bot'+TOKEN+'/sendMessage')
            self.assertEqual(request.get_method(),'POST')
            self.assertEqual(opener.open.call_args.kwargs['timeout'],6)
            response.read.assert_called_with(1000001)
            response.read.return_value=b'{"ok":false,"description":"hidden"}'
            with self.assertRaises(telegram.TelegramRejected):telegram.bot_request(TOKEN,'getMe',{})
            response.read.return_value=b'x'*1000001
            with self.assertRaises(telegram.TelegramRejected):telegram.bot_request(TOKEN,'getMe',{})
            with self.assertRaises(telegram.TelegramRejected):telegram.bot_request(TOKEN,'deleteMessage',{})
        self.assertIsNone(telegram.NoRedirect().redirect_request(None,None,None,None,None,None))
