"""Opt-in completion messages. No raw logs, prompts, paths, secrets or retries."""
import asyncio
import json
import re
import time
import urllib.request
from app.config import settings

class TelegramRejected(ValueError):
    pass

def valid_token(value):
    return isinstance(value,str) and re.fullmatch(r'\d{5,20}:[A-Za-z0-9_-]{20,120}',value) is not None

def valid_chat(value):
    return isinstance(value,str) and re.fullmatch(r'-?\d{1,20}',value) is not None and 0 < abs(int(value)) < 2**63

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def bot_request(token, method, payload):
    if not valid_token(token) or method not in ('sendMessage','getMe','getUpdates'):
        raise TelegramRejected('Telegram configuration is invalid.')
    # urllib emits no URL access log; HTTPX's default INFO request log includes bot tokens.
    request=urllib.request.Request('https://api.telegram.org/bot'+token+'/'+method,
        data=json.dumps(payload).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=6) as response:
        raw=response.read(1000001)
    if len(raw)>1000000: raise TelegramRejected('Telegram response exceeded its limit.')
    value=json.loads(raw)
    if not isinstance(value,dict) or value.get('ok') is not True:
        raise TelegramRejected('Telegram did not accept this request.')
    return value.get('result')

def eligible(row):
    report=row.get('report') or {}
    tests=report.get('tests') or {}
    return (row.get('lane')=='coding' and row.get('mode')=='fix' and row.get('status')=='succeeded'
            and report.get('verified') is True and type(tests.get('exitCode')) is int and tests['exitCode']==0
            and bool(report.get('changedFiles')) and report.get('sourceChanged',True) is not False
            and (not report.get('terminalRunId') or (report.get('terminalVerification') or {}).get('verified') is True))

def message(row):
    output=str(row['report']['tests'].get('output',''))
    count=re.search(r'^# tests (\d+)\s*$',output,re.M) or re.search(r'Ran (\d+) tests?\b',output)
    tests='All '+count[1]+' selected tests passed.' if count else 'Selected local tests passed.'
    kind='Invoice error fixed and verified.' if row['tool']=='repair_invoice_app' else 'Code fix completed and verified.'
    return 'AIRA\n'+kind+'\n'+tests+'\nTask: '+row['id']+' · run '+str(row['completedRuns'])

async def notify_fix(store,user,ident):
    row=store.get(user,ident)
    if not row or not eligible(row) or not settings.aira_telegram_enabled: return
    run=row['completedRuns']
    if (row.get('telegramNotification') or {}).get('run')==run: return
    token=settings.aira_telegram_bot_token.get_secret_value().strip()
    chat=settings.aira_telegram_chat_id.strip()
    state={'run':run,'status':'sending','attemptedAt':time.time()}
    def record(status):
        latest=store.get(user,ident)
        if latest and latest.get('completedRuns')==run:
            latest['telegramNotification']={**state,'status':status}
            store.save(latest)
    if not valid_token(token) or not valid_chat(chat):
        record('configuration_required');return
    # Persist the attempt before any await. Never auto-retry an ambiguous delivery.
    record('sending')
    try:
        result=await asyncio.wait_for(asyncio.to_thread(bot_request,token,'sendMessage',{'chat_id':int(chat),'text':message(row)}),8)
        if not isinstance(result,dict) or type(result.get('message_id')) is not int or (result.get('chat') or {}).get('id')!=int(chat):
            record('unconfirmed');return
        record('sent')
    except asyncio.CancelledError:
        record('unconfirmed');raise
    except TelegramRejected:
        record('rejected')
    except Exception:
        # Do not log exception text: it can contain the token-bearing request URL.
        record('unconfirmed')
