"""Durable call reminders, independent of tabs and Gemini Live sessions.

Claiming a reminder commits BEFORE network I/O. Interrupted/uncertain dispatches
never replay. Overdue reminders have a two-minute grace period, then expire.
"""
import asyncio
import json
import logging
import math
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.services.twilio_voice import TwilioVoice, CallRejected, read_credentials, public_settings

logger = logging.getLogger(__name__)
IST = timezone(timedelta(hours=5, minutes=30), 'IST')
GRACE_SECONDS = 120
TERMINAL_CALLS = {'completed', 'busy', 'failed', 'no-answer', 'canceled'}


def due_time(args, now):
    relative = args.get('after_seconds')
    clock = args.get('local_time')
    date = args.get('local_date')
    if (relative is None) == (clock is None):
        raise ValueError('Provide either after_seconds or local_time, never both.')
    if relative is not None:
        if date is not None or isinstance(relative, bool) or not isinstance(relative, (float, int)) or not math.isfinite(relative) or not 10 <= relative <= 7 * 86400:
            raise ValueError('Choose a delay between 10 seconds and seven days, without a date.')
        return now + relative
    if not isinstance(clock, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', clock):
        raise ValueError('Use a 24-hour local time HH:MM in IST; clarify AM/PM if ambiguous.')
    today = datetime.fromtimestamp(now, IST).date()
    try:
        day = datetime.strptime(date, '%Y-%m-%d').date() if isinstance(date, str) else today
        if date is not None and (not isinstance(date, str) or day.isoformat() != date):
            raise ValueError()
    except ValueError:
        raise ValueError('Use a local date YYYY-MM-DD.') from None
    hour, minute = map(int, clock.split(':'))
    due = datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST).timestamp()
    if not now + 1 <= due <= now + 7 * 86400:
        raise ValueError('That time must be in the future, within seven days. Do not silently move a past time to tomorrow; ask for the intended date.')
    return due


class ReminderStore:
    def __init__(self, path=None):
        self.path = path or settings.aira_data_dir / 'db' / 'call-reminders.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY, user TEXT NOT NULL, request_key TEXT,
                due REAL NOT NULL, message TEXT NOT NULL, recipient TEXT NOT NULL,
                account TEXT NOT NULL, sender TEXT NOT NULL, status TEXT NOT NULL,
                created REAL NOT NULL, updated REAL NOT NULL, call_sid TEXT,
                call_status TEXT, call_mode TEXT, detail TEXT NOT NULL, last_poll REAL NOT NULL DEFAULT 0,
                UNIQUE(user, request_key))''')
            if 'call_mode' not in {row['name'] for row in db.execute('PRAGMA table_info(reminders)')}:
                db.execute('ALTER TABLE reminders ADD COLUMN call_mode TEXT')
            db.execute('CREATE INDEX IF NOT EXISTS reminders_due ON reminders(status, due)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA journal_mode=WAL')
            with db:
                yield db
        finally:
            db.close()

    def rows(self, user=None):
        with self.connect() as db:
            query = 'SELECT * FROM reminders' + (' WHERE user=?' if user else '') + ' ORDER BY created DESC LIMIT 100'
            return [dict(row) for row in db.execute(query, (user,) if user else ()).fetchall()]

    def get(self, user, ident):
        with self.connect() as db:
            row = db.execute('SELECT * FROM reminders WHERE user=? AND id=?', (user, ident)).fetchone()
        if row is None:
            raise ValueError('Reminder not found. List reminders and use its actual ID.')
        return dict(row)

    def public(self, row):
        return {'id': row['id'], 'message': row['message'], 'dueAt': datetime.fromtimestamp(row['due'], timezone.utc).isoformat(),
                'dueLocal': datetime.fromtimestamp(row['due'], IST).isoformat(), 'timezone': 'Asia/Kolkata',
                'recipientPreview': '…' + row['recipient'][-4:], 'status': row['status'],
                'callSid': row['call_sid'], 'callStatus': row['call_status'], 'callMode': row['call_mode'], 'detail': row['detail']}

    def create(self, user, args, config, now):
        if not isinstance(args, dict) or set(args) - {'message', 'after_seconds', 'local_time', 'local_date', 'requestId'}:
            raise ValueError('Reminders call only your number saved in Settings. Supply a message and time.')
        key = args.get('requestId')
        if key is not None and (not isinstance(key, str) or not 1 <= len(key) <= 100):
            raise ValueError('Invalid reminder request ID.')
        message = args.get('message')
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 500 or any(ord(c) < 32 and c not in '\n\t' for c in message):
            raise ValueError('Provide a reminder message of 1–500 characters.')
        message = message.strip()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if key:
                existing = db.execute('SELECT * FROM reminders WHERE user=? AND request_key=?', (user, key)).fetchone()
                if existing:
                    return dict(existing)
            due = due_time(args, now)
            # Repeated model acknowledgements with the same message/time reuse the pending reminder.
            existing = db.execute("SELECT * FROM reminders WHERE user=? AND status='pending' AND message=? AND recipient=? AND ABS(due-?)<=5", (user, message, config['toNumber'], due)).fetchone()
            if existing:
                return dict(existing)
            if db.execute("SELECT COUNT(*) FROM reminders WHERE user=? AND status IN ('pending','dispatching','calling')", (user,)).fetchone()[0] >= 20:
                raise ValueError('Twenty reminders are active. Cancel or finish one first.')
            ident = uuid.uuid4().hex[:12]
            db.execute('''INSERT INTO reminders (id,user,request_key,due,message,recipient,account,sender,status,created,updated,detail)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (ident, user, key, due, message, config['toNumber'], config['accountSid'], config['fromNumber'], 'pending', now, now, 'Scheduled. Keep AIRA running and the computer awake.'))
            return dict(db.execute('SELECT * FROM reminders WHERE id=?', (ident,)).fetchone())

    def cancel(self, user, ident, now):
        with self.connect() as db:
            changed = db.execute("UPDATE reminders SET status='cancelled', detail='Cancelled before calling.', updated=? WHERE user=? AND id=? AND status='pending'", (now, user, ident)).rowcount
        row = self.get(user, ident)
        if not changed and row['status'] != 'cancelled':
            raise ValueError('This reminder has already been dispatched or finished. Cancellation cannot undo a call request.')
        return row

    def update(self, ident, status, detail, now, sid=None, call_status=None, call_mode=None):
        with self.connect() as db:
            db.execute('UPDATE reminders SET status=?, detail=?, updated=?, call_sid=COALESCE(?,call_sid), call_status=COALESCE(?,call_status), call_mode=COALESCE(?,call_mode) WHERE id=?',
                       (status, detail, now, sid, call_status, call_mode, ident))

    def claim(self, now):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute("UPDATE reminders SET status='missed', detail='Time passed while AIRA was unavailable. No late call was placed; schedule a new reminder.', updated=? WHERE status='pending' AND due<?", (now, now - GRACE_SECONDS))
            row = db.execute("SELECT * FROM reminders WHERE status='pending' AND due<=? ORDER BY due LIMIT 1", (now,)).fetchone()
            if row:
                db.execute("UPDATE reminders SET status='dispatching', detail='Requesting the phone call.', updated=? WHERE id=?", (now, row['id']))
                return dict(row)
        return None

    def recover(self, now):
        with self.connect() as db:
            db.execute("UPDATE reminders SET status='uncertain', detail='AIRA stopped during call dispatch. Check Twilio Voice logs; this request will not be repeated.', updated=? WHERE status='dispatching'", (now,))


class CallReminders:
    def __init__(self, store=None, voice=None, credentials=None, clock=None):
        self.store = store or ReminderStore()
        self.voice = voice or TwilioVoice()
        self.credentials = credentials or read_credentials
        self.clock = clock or time.time
        self.task = None
        self.tick_lock = asyncio.Lock()

    def schedule(self, user, args):
        config = self.credentials()
        if not config:
            raise ValueError('Save your Twilio account, calling number and your phone number in Settings → Phone reminders first.')
        return self.store.public(self.store.create(user, args, config, self.clock()))

    def context(self):
        return {'nowLocal': datetime.fromtimestamp(self.clock(), IST).isoformat(), 'timezone': 'Asia/Kolkata',
                'timezoneLabel': 'IST (UTC+05:30)', 'settings': {k: v for k, v in public_settings().items() if k in ('configured', 'storageError')},
                'message': 'Calls go only to your saved number. Trial accounts ring with Twilio demo audio; upgraded accounts speak your reminder. Backend must remain running, awake and online. Calls can ring a few seconds after the scheduled time.'}

    def start(self):
        if self.task is None or self.task.done():
            self.store.recover(self.clock())
            self.task = asyncio.create_task(self.run(), name='aira-call-reminders')

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def run(self):
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                # No provider response, message, number or credentials in logs.
                logger.warning('Call reminder scheduler could not complete its local check.')
            await asyncio.sleep(2)

    async def tick(self):
        async with self.tick_lock:
            now = self.clock()
            row = self.store.claim(now)
            if row:
                try:
                    config = self.credentials()
                    if not config or config['accountSid'] != row['account'] or config['fromNumber'] != row['sender']:
                        raise CallRejected('Twilio calling setup changed or was removed. Schedule a new reminder using the current setup.')
                    # Freeze the recipient chosen when scheduled, even after editing Settings.
                    config = {**config, 'toNumber': row['recipient']}
                    call = await self.voice.create(config, row['message'])
                    note = ' Trial account: plays Twilio demo audio, not the saved reminder text.' if call.mode == 'trial-demo' else ''
                    self.store.update(row['id'], 'calling', 'Call accepted by Twilio. Waiting for call status.' + note, self.clock(), sid=call.sid, call_status='queued', call_mode=call.mode)
                except asyncio.CancelledError:
                    self.store.update(row['id'], 'uncertain', 'AIRA stopped during dispatch. Check Twilio Voice logs; no automatic retry.', self.clock())
                    raise
                except CallRejected as exc:
                    self.store.update(row['id'], 'failed', str(exc), self.clock())
                except Exception:
                    self.store.update(row['id'], 'uncertain', 'Call outcome is unknown. Check Twilio Voice logs before scheduling another call. No automatic retry.', self.clock())
            # Poll only known calls, without exposing a public callback endpoint.
            for row in self.store.rows():
                if row['status'] != 'calling' or now - row['last_poll'] < 10:
                    continue
                with self.store.connect() as db:
                    db.execute('UPDATE reminders SET last_poll=? WHERE id=?', (now, row['id']))
                try:
                    config = self.credentials()
                    if not config or config['accountSid'] != row['account']:
                        raise ValueError('Settings unavailable')
                    status = await self.voice.status(config, row['call_sid'])
                    final = status in TERMINAL_CALLS
                    self.store.update(row['id'], 'finished' if final else 'calling',
                                      ('Call ended: ' if final else 'Call status: ') + status + ('. Call completion does not prove the message was heard.' if status == 'completed' else '.') + (' Trial account: plays Twilio demo audio, not the saved reminder text.' if row['call_mode'] == 'trial-demo' else ''),
                                      self.clock(), call_status=status)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    if now - row['due'] > 300:
                        self.store.update(row['id'], 'uncertain', 'Call was accepted, but final status is unavailable. Check Twilio Voice logs. No automatic retry.', self.clock())


_service = None


def get_reminders():
    global _service
    expected = settings.aira_data_dir / 'db' / 'call-reminders.sqlite3'
    if _service is None or (_service.task is None and _service.store.path != expected):
        _service = CallReminders()
    return _service


REMINDER_TOOLS = [
    {'name': 'get_call_reminder_context', 'description': 'Get the actual current date/time in IST and whether phone reminders are configured. Call before interpreting a clock time; do not use the session-start time.', 'parameters': {'type': 'OBJECT', 'properties': {}}},
    {'name': 'schedule_call_reminder', 'description': 'On a direct request for a timed phone reminder, persist one call to the saved personal number. Return actual scheduled time before confirming. Use after_seconds for relative delays (5 minutes=300; 34 minutes=2040), OR local_time in 24-hour HH:MM IST and optional local_date YYYY-MM-DD. Never invent AM/PM or a date. No call is made until due; ending the conversation does not cancel it.', 'parameters': {'type': 'OBJECT', 'properties': {'message': {'type': 'STRING'}, 'after_seconds': {'type': 'NUMBER'}, 'local_time': {'type': 'STRING'}, 'local_date': {'type': 'STRING'}}, 'required': ['message']}},
    {'name': 'list_call_reminders', 'description': 'List actual phone reminders and call outcomes. Use to identify a reminder before cancellation; never invent an ID or claim the person heard a message just because the call completed.', 'parameters': {'type': 'OBJECT', 'properties': {}}},
    {'name': 'cancel_call_reminder', 'description': 'On a direct request, cancel a specific pending phone reminder using its exact ID from list_call_reminders. Ask which one if ambiguous. Dispatched calls cannot be undone with this tool.', 'parameters': {'type': 'OBJECT', 'properties': {'reminder_id': {'type': 'STRING'}}, 'required': ['reminder_id']}},
]
REMINDER_NAMES = {tool['name'] for tool in REMINDER_TOOLS}
REMINDER_PROMPT = '''
PHONE REMINDERS:
- For "call me in five minutes to head out", call schedule_call_reminder(message="Time to head out.", after_seconds=300). For 34 minutes use 2040 seconds. Calls go only to the one number saved in Phone reminders settings.
- Before a clock-time request, use get_call_reminder_context to get the real current date/time in IST (Asia/Kolkata). Resolve the user's time from that fresh clock, never the session-start date or an invented clock. Ask one short clarification if AM/PM or date is ambiguous. local_time uses 24-hour HH:MM; local_date is optional and defaults to today. Never silently move a past time to tomorrow.
- A statement of plans alone is not permission to call: ask whether they want a phone reminder. A direct timed reminder request can use the saved phone reminder setup.
- Confirm a reminder only after schedule_call_reminder returns its actual pending record and dueLocal. Keep it short: "I'll call you at 9:05 PM." If setup is missing, direct them to Settings → Phone reminders; never claim it was saved or request credentials in conversation.
- Twilio trial accounts ring with demo audio; upgraded accounts speak the saved reminder. Never promise custom speech on a trial account. Call outcomes report callMode="trial-demo" when applicable.
- Reminders persist after voice stops, tab closes or backend restarts. They require the local backend running, computer awake and internet. AIRA attempts calls within two minutes of the due time; older overdue reminders are marked missed. Never guarantee ringing at the exact second or automatic retries. Use list_call_reminders for status and cancel_call_reminder for an explicit cancellation.
'''


async def execute_reminder_tool(user, name, args):
    service = get_reminders()
    try:
        if name == 'get_call_reminder_context':
            value = service.context()
        elif name == 'schedule_call_reminder':
            value = service.schedule(user, args)
        elif name == 'list_call_reminders':
            value = [service.store.public(row) for row in service.store.rows(user)[:20]]
        elif name == 'cancel_call_reminder':
            value = service.store.public(service.store.cancel(user, args.get('reminder_id'), service.clock()))
        else:
            raise ValueError('Unknown reminder tool.')
        return json.dumps(value, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({'error': str(exc)})
