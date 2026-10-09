"""One desktop lane, one coding lane; explicit jobs survive speech interruption.

Disconnect, stop-all and shutdown cancel work. Restart never replays it.
"""
import asyncio
import json
import time
import uuid
import re
from app.websocket.manager import manager
from app.services.task_store import TaskStore
from app.services.coding_worker import validate_project, run_coding
from app.services.desktop_action_service import validate_action, request_desktop_action

ACTIVE = {'queued', 'running'}
DESKTOP_JOBS = {'desktop_task', 'create_notion_note', 'open_app', 'open_folder', 'close_app', 'type_in_app', 'calculate_in_app','open_browser','open_maps','search_maps','search_youtube','open_youtube_video'}


def instruction(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000 or '\x00' in value:
        raise ValueError('Provide instructions of 1–2000 characters.')
    return value.strip()


class TaskSupervisor:
    def __init__(self, store=None, desktop=None, coding=None, invoice_coding=None):
        self.store = store or TaskStore()
        self.desktop = desktop or request_desktop_action
        self.coding = coding or run_coding
        self.invoice_coding = invoice_coding
        self.tasks, self.connections, self.locks, self.owners = {}, {}, {}, {}

    def lock(self, user, lane):
        return self.locks.setdefault((user, lane), asyncio.Lock())

    def save(self, row, **changes):
        row.update(changes, updatedAt=time.time())
        self.store.save(row)

    def get(self, user, ident):
        row = self.store.get(user, ident)
        if row is None: raise ValueError('That task was not found. List tasks and use its ID.')
        return row

    async def read_current_video(self, user):
        # Share the desktop lane with navigation so this read cannot race a click.
        async with self.lock(user, 'desktop'):
            # Use the existing connection-scoped worker source in both voice
            # modes. This read has no persistent job ID or progress row.
            return await self.desktop(user, 'current_youtube_video', {}, source='job', detailed=True)

    async def submit(self, user, tool, args, request_key=None):
        if not isinstance(args, dict): raise ValueError('Supply task arguments as an object.')
        mode = args.get('mode', 'investigate')
        if mode not in ('investigate', 'fix'): raise ValueError('Choose investigate or fix mode.')
        if request_key:
            for row in self.store.list(user):
                if row.get('requestKey') == request_key: return row
        connection = manager.get_connection(user)
        if connection is None: raise ValueError('Open AIRA before starting a task.')
        if sum(r['status'] in ACTIVE for r in self.store.list(user)) >= 8:
            raise ValueError('Eight tasks are already active. Finish or cancel one first.')
        if tool == 'repair_invoice_app':
            from app.services.invoice_demo import prepare
            info = prepare()
            project = validate_project(path=info['path'], runner='node')
            problem = instruction(args.get('problem'))
            task = ('Investigate and fix the user-reported issue in this invoice application. '
                    'Inspect the source and independent test output to discover the cause; do not assume a fix. '
                    'Preserve tests, configuration and the demo marker. Explain the cause and your source change briefly. '
                    'User observation: ' + problem)
            action, lane, title, mode = None, 'coding', 'Repair invoice · ' + problem[:60], 'fix'
        elif tool == 'coding_task':
            task = instruction(args.get('task'))
            project = validate_project(**self.store.config(user))
            action, lane, title = None, 'coding', task[:80]
        elif tool=='youtube_study':
            from app.services.youtube_study import validate_study
            action=validate_study(args)
            # Freeze selected models at submission; later settings affect new jobs.
            action['models']=self.store.video_config(user)
            project,lane,task=None,'study',''
            title='YouTube · '+action['output']
        elif tool in ('export_summary_to_notion', 'notebooklm_mindmap'):
            from app.services.study_destinations import export_summary, mindmap_action
            action = export_summary(self.store, user, args) if tool == 'export_summary_to_notion' else mindmap_action(args)
            project, lane, task = None, 'desktop', ''
            title = 'Notion · Export summary' if tool == 'export_summary_to_notion' else 'NotebookLM · Video mind map'
        elif tool == 'show_coding_project':
            project = validate_project(**self.store.config(user))
            action, lane, title, task = {'kind': 'show_project', 'path': project['path']}, 'desktop', 'Show project in VS Code', ''
        elif tool == 'show_invoice_demo':
            from app.services.invoice_demo import prepare
            info = prepare()  # Never resets an existing demo.
            if not any(r['lane']=='coding' and r['status'] in ACTIVE for r in self.store.list(user)):
                self.store.set_config(user, {'path': info['path'], 'runner': 'node'})
            project, lane, task = None, 'desktop', ''
            action, title = {'kind': 'show_invoice_demo'}, 'Show invoice demo'
        elif tool in DESKTOP_JOBS:
            action = validate_action(tool, args)
            tool = action['kind']
            project, lane = None, 'desktop'
            task = action.get('task', '')
            title = 'Notion · ' + action['title'] if tool == 'create_notion_note' else ('Calculator · '+action['expression'] if tool=='calculate_in_app' else (action.get('appName') or 'File Explorer') + ' · ' + (task or tool.replace('_',' '))[:60])
            if tool=='open_browser': title='Chrome · AIRA browser'
            elif tool=='open_maps': title='Google Maps · Open map'
            elif tool=='search_maps': title='Google Maps · '+action['query'][:60]
            elif tool=='search_youtube': title='YouTube · '+action['query'][:60]
            elif tool=='open_youtube_video': title='YouTube · Open video'
        else: raise ValueError('Unsupported task type.')
        row = {'id': uuid.uuid4().hex[:10], 'user': user, 'lane': lane, 'tool': tool, 'action': action, 'project': project,
               'instruction': task, 'title': title, 'status': 'queued', 'progress': 'Waiting for ' + lane + ' worker',
               'createdAt': time.time(), 'updatedAt': time.time(), 'revisions': [], 'completedRuns': 0, 'requestKey': request_key, 'report': None, 'mode': mode}
        if lane == 'coding':
            from app.services.invoice_demo import generation_for
            row.update(events=[], demoGeneration=generation_for(project))
            if row['demoGeneration'] and mode=='fix':
                from app.config import settings
                row['invoiceRepairMode'] = settings.aira_invoice_repair_mode
                if settings.aira_invoice_repair_mode=='deterministic' and tool=='coding_task':
                    row['tool'] = 'repair_invoice_app'
        self.store.save(row)
        self.connections[row['id']] = connection
        self.schedule(row)
        return row

    def schedule(self, row):
        ident = row['id']
        task = asyncio.create_task(self.run(row['user'], ident))
        self.tasks[ident] = task
        self.owners[ident] = row['user']
        def done(finished):
            if self.tasks.get(ident) is finished:
                self.tasks.pop(ident, None)
                self.connections.pop(ident, None)
                self.owners.pop(ident, None)
        task.add_done_callback(done)

    async def run(self, user, ident):
        row = self.get(user, ident)
        try:
            async with self.lock(user, row['lane']):
                row = self.get(user, ident)
                if row['status'] != 'queued': return
                if manager.get_connection(user) is not self.connections.get(ident):
                    raise ValueError('Original AIRA connection closed. Inspect partial work before resuming.')
                self.save(row, status='running', progress='Starting ' + row['lane'] + ' worker')
                # Updates arriving during a native action are picked up only after it exits.
                while True:
                    row = self.get(user, ident)
                    revision = row['revisions'][0] if row['revisions'] and (row['completedRuns'] or row.get('partial') or row['lane'] == 'coding') else None
                    if row['completedRuns'] and not revision:
                        self.save(row, status=row.get('lastStatus', 'succeeded'), progress=row.get('lastMessage', 'Completed'))
                        break
                    if row['lane']=='study':
                        from app.services.youtube_study import run_study
                        if not row['action'].get('videoUrl'):
                            observed=await self.read_current_video(user)
                            if observed['status']!='succeeded' or not observed.get('data',{}).get('videoUrl'):
                                raise ValueError(observed['message'])
                            row['action'].update(observed['data'])
                            self.save(row)
                        result=await run_study(row,lambda label:self.progress(user,ident,label),self.store)
                    elif row['lane'] == 'coding':
                        if revision: row['instruction'] = revision
                        if row['tool'] == 'repair_invoice_app':
                            await self.progress(user, ident, 'Opening the invoice source in VS Code')
                            async with self.lock(user, 'desktop'):
                                shown = await self.desktop(user, 'show_coding_project', {'path':row['project']['path'],'file':'invoice.js'}, source='job', session_id=ident)
                            if not shown.startswith('Desktop action succeeded:'):
                                raise ValueError('VS Code could not show the invoice project. No repair started. ' + shown[:200])
                        if row['tool']=='repair_invoice_app' and row.get('invoiceRepairMode')=='deterministic' and row['mode']=='fix':
                            from app.services.invoice_faults import run_deterministic_repair
                            result = await (self.invoice_coding or run_deterministic_repair)(row, lambda label:self.progress(user,ident,label))
                        else:
                            result = await self.coding(row, lambda label: self.progress(user, ident, label))
                        if result.get('report',{}).get('terminalRunId') and result.get('report',{}).get('verified'):
                            self.save(row,report=result['report'])
                            from app.config import ROOT
                            from app.core.invoice_presentation import read_result
                            from app.services.invoice_demo import version
                            await self.progress(user,ident,'Showing the generated test file and running all eight checks in the VS Code terminal')
                            async with self.lock(user,'desktop'):
                                terminal=await self.desktop(user,'run_invoice_tests',{'runId':result['report']['terminalRunId']},source='job',session_id=ident)
                            if not terminal.startswith('Desktop action succeeded:'):
                                raise ValueError('Local tests passed, but visible terminal verification did not finish. ' + terminal[:200])
                            result['report']['terminalVerification']=read_result(ROOT,result['report']['terminalRunId'],result['report']['demoVersion'])
                            if version()!=result['report']['demoVersion']: raise ValueError('Invoice source changed after terminal verification. Inspect and rerun.')
                        if row['tool'] == 'repair_invoice_app' and result['status']=='succeeded' and result.get('report',{}).get('verified'):
                            await self.progress(user, ident, 'All tests passed; returning to the localhost Chrome invoice tab')
                            async with self.lock(user, 'desktop'):
                                shown = await self.desktop(user, 'show_invoice_demo', {}, source='job', session_id=ident)
                            result['report']['presentationReturned'] = shown.startswith('Desktop action succeeded:')
                            if not result['report']['presentationReturned']:
                                result.update(status='needs_attention', message='Selected tests passed, but the invoice window could not be brought forward. Open it manually.')
                    elif row['tool'] in ('export_summary_to_notion', 'notebooklm_mindmap'):
                        action = row['action']
                        if row['tool'] == 'notebooklm_mindmap' and not action.get('videoUrl'):
                            # Already holding the desktop lock: read directly, not recursively.
                            observed = await self.desktop(user, 'current_youtube_video', {}, source='job', detailed=True)
                            if observed['status'] != 'succeeded' or not observed.get('data', {}).get('videoUrl'):
                                raise ValueError(observed['message'])
                            action.update(observed['data']); self.save(row)
                        observed = await self.desktop(user, row['tool'], action, source='job', session_id=ident, detailed=True)
                        result = {'status': 'succeeded' if observed['status'] == 'succeeded' else 'needs_attention', 'message': observed['message'],
                                  'report': {'kind': 'destination', 'summary': observed['message'], 'verified': observed['status'] == 'succeeded',
                                             'changedFiles': [], 'sourceUrl': action.get('videoUrl'), 'studyTaskId': action.get('studyTaskId'), **observed.get('data', {})}}
                    else:
                        action = row['action']
                        if (row['completedRuns'] or row.get('partial')) and row['tool'] in ('desktop_task','create_notion_note'):
                            app = 'Notion' if row['tool'] == 'create_notion_note' else action.get('appName')
                            if not app: raise ValueError('This display task cannot be resumed. Submit a new display request.')
                            follow_up = revision or row['instruction']
                            prefix = 'Continue the existing task. Do not create a duplicate note or repeat committed work. Inspect current state first. Exact follow-up: ' + follow_up + '\nOriginal context: '
                            if len(prefix) > 1900: raise ValueError('Shorten this follow-up to 1700 characters so the target context can be retained.')
                            context = {k: v for k,v in action.items() if k != 'content'}
                            tool, args = 'desktop_task', {'app_name': app, 'task': prefix + json.dumps(context, ensure_ascii=False)[:2000-len(prefix)]}
                        else:
                            tool = row['tool']
                            args = {'app_name': action.get('appName'), 'task': action.get('task'), 'title': action.get('title'), 'content': action.get('content'), 'path': action.get('path'), 'text': action.get('text'), 'expression':action.get('expression'),'query':action.get('query'),'video_url':action.get('videoUrl'),'result_number':action.get('resultNumber')}
                        if tool in ('open_browser','open_maps','search_maps','search_youtube','open_youtube_video'):
                            observed=await self.desktop(user,tool,args,source='job',session_id=ident,detailed=True)
                            result={'status':'succeeded' if observed['status']=='succeeded' else 'needs_attention','message':observed['message'],
                                    'report':{'kind':'browser','summary':observed['message'],'changedFiles':[],'verified':observed['status']=='succeeded',**observed.get('data',{})}}
                        else:
                            message = await self.desktop(user, tool, args, source='job', session_id=ident)
                            status = 'succeeded' if message.startswith('Desktop action succeeded:') else 'needs_attention'
                            result = {'status': status, 'message': message}
                    # Read latest row; a follow-up may have arrived during the await.
                    if row['lane'] == 'coding': await self.progress(user, ident, result['message'])
                    latest = self.get(user, ident)
                    if latest['status'] != 'running': return
                    if revision and latest['revisions'] and latest['revisions'][0] == revision: latest['revisions'].pop(0)
                    changes = {'completedRuns': latest['completedRuns'] + 1, 'partial': result['status'] != 'succeeded', 'lastStatus': result['status'], 'lastMessage': result['message']}
                    if result.get('report'):
                        changes.update(report=result['report'], workerSession=result['report'].get('workerSession'))
                    self.save(latest, **changes)
                    if result['status'] != 'succeeded':
                        self.save(latest, status='needs_attention', progress=result['message'])
                        break
            completed = self.get(user, ident)
            if completed['tool']=='repair_invoice_app' and completed['status']=='succeeded':
                from app.services.repair_notification import announce_repair
                await announce_repair(user, completed['report'])
            if completed['lane']=='coding' and completed['status']=='succeeded':
                from app.services.telegram_notification import notify_fix
                try: await notify_fix(self.store,user,ident)
                except Exception: pass  # Notification transport/storage cannot undo a verified repair.
        except asyncio.CancelledError:
            row = self.get(user, ident)
            if row['status'] in ACTIVE:
                self.save(row, status='cancelled', partial=True, progress='Stopped. Partial changes may remain.')
            raise
        except Exception as error:
            row = self.get(user, ident)
            message = str(error) if isinstance(error, ValueError) else 'Worker could not finish. Inspect partial changes before resuming.'
            self.save(row, status='needs_attention', partial=True, progress=message[:400])

    async def progress(self, user, ident, label):
        row = self.get(user, ident)
        if row['status'] == 'running':
            label = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', str(label))
            label = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', label)[:600]
            if row['lane'] == 'coding' and label.strip():
                row['events'] = (row.get('events', []) + [{'at': time.time(), 'text': label}])[-160:]
            self.save(row, progress=label[:160] or row['progress'])

    async def control(self, user, ident, action, text=None, mode=None):
        row = self.get(user, ident)
        if action == 'update':
            if row['tool'] in ('export_summary_to_notion','notebooklm_mindmap','open_app','open_folder','close_app','show_coding_project','show_invoice_demo','type_in_app','calculate_in_app','open_browser','open_maps','search_maps','search_youtube','open_youtube_video','youtube_study'):
                raise ValueError('This action has a fixed target. Submit a new app/folder/display request to change it.')
            text = instruction(text)
            if mode is not None:
                if row['lane'] != 'coding' or mode not in ('investigate', 'fix'): raise ValueError('Coding mode must be investigate or fix.')
                row['mode'] = mode
            if row['status'] == 'cancelled': raise ValueError('That task is cancelled. Start a new task explicitly.')
            if len(row['revisions']) >= 4: raise ValueError('Four follow-ups are pending. Let them finish first.')
            if row['status'] == 'queued' and not row['completedRuns'] and row['lane'] == 'coding':
                self.save(row, instruction=text, title=text[:80])
            else:
                row['revisions'].append(text)
                self.save(row)
            if row['status'] in ('succeeded', 'needs_attention'):
                await self.control(user, ident, 'resume')
            return self.get(user, ident)
        if action in ('pause', 'cancel'):
            if row['status'] == 'succeeded' and action == 'pause': raise ValueError('That task has finished.')
            partial = row['status'] == 'running' or row.get('partial', False)
            self.save(row, status='paused' if action == 'pause' else 'cancelled', partial=partial,
                      progress='Paused; inspect partial changes before resume.' if action == 'pause' else 'Cancelled. Partial changes may remain.')
            task = self.tasks.get(ident)
            if task:
                task.cancel(); await asyncio.gather(task, return_exceptions=True)
            return self.get(user, ident)
        if action == 'resume':
            if row['tool'] in ('export_summary_to_notion','notebooklm_mindmap') and (row.get('partial') or row['completedRuns']):
                raise ValueError('Inspect the destination for partial changes, then make a new explicit request. This workflow never automatically repeats a write or generation.')
            if row['tool']=='youtube_study' and (row.get('partial') or row['completedRuns']):
                raise ValueError('Start a new YouTube request explicitly. Existing captions and summaries are cached; generation is not automatically repeated.')
            if row['tool']=='type_in_app' and (row.get('partial') or row['completedRuns']):
                raise ValueError('Inspect the Notion page before issuing a new append request. Resuming could duplicate text already entered.')
            if row['status'] not in ('paused', 'needs_attention', 'succeeded'): raise ValueError('Only paused/finished tasks can resume with a follow-up.')
            if row['status'] == 'succeeded' and not row['revisions']: raise ValueError('Provide a follow-up instruction for a completed task.')
            connection = manager.get_connection(user)
            if connection is None: raise ValueError('Open AIRA before resuming.')
            if ident in self.tasks:
                await asyncio.gather(self.tasks[ident], return_exceptions=True)
            self.connections[ident] = connection
            if row['completedRuns'] and not row['revisions']:
                row['revisions'].append('Continue the original request after inspecting current state. Do not repeat completed work. ' + row['instruction'])
            self.save(row, status='queued', progress='Waiting for ' + row['lane'] + ' worker')
            self.schedule(row)
            return row
        raise ValueError('Choose update, pause, resume or cancel.')

    async def cancel_all(self, user):
        for row in self.store.list(user):
            if row['status'] in ACTIVE: await self.control(user, row['id'], 'cancel')

    async def close(self):
        for user in set(self.owners.values()): await self.cancel_all(user)
        # A ledger recovery can mark a still-live task needs_attention. Shutdown
        # must also drain those runtime tasks, without replaying or changing history.
        pending = list(self.tasks.values())
        for task in pending:
            if not task.done(): task.cancel()
        if pending: await asyncio.gather(*pending, return_exceptions=True)

    def get_user(self, ident):
        # Runtime jobs are bound to their original user, even if a connection was replaced.
        return next((key for key, _lane in self.locks if self.store.get(key, ident)), None)


_supervisor = None
def get_supervisor():
    global _supervisor
    from app.config import settings
    expected = settings.aira_data_dir / 'db' / 'tasks.sqlite3'
    if _supervisor is None or (not _supervisor.tasks and _supervisor.store.path != expected):
        _supervisor = TaskSupervisor()
    return _supervisor


TASK_TOOLS = [
    {'name':'repair_invoice_app','description':'On an explicit request to fix the registered Invoice Studio/VS Code demo, accept the user-observed problem. Visibly open its real source in VS Code, apply the configured known-bug repair, run independent tests and bring back the corrected localhost application. Default demo mode is deterministic with a fixed percentage-discount repair; agent mode uses OpenCode. Never claim this demonstrates arbitrary-project autonomous diagnosis. Do not require a manual project selector or reveal the solution before running. Returns a background job; success requires real verification.', 'parameters':{'type':'OBJECT','properties':{'problem':{'type':'STRING'}},'required':['problem']}},
    {'name':'show_invoice_demo','description':'On a direct request, open the ordinary localhost Invoice Studio application. Preserves existing code, never resets it. Registers its known project for coding when no coding job is active. Opening alone does not repair code. For a request to fix its observed behavior use repair_invoice_app.', 'parameters':{'type':'OBJECT','properties':{}}},
    {'name':'export_summary_to_notion','description':'On an explicit request to put a video summary in Notion, export the COMPLETE saved Markdown summary, including source, key points and caveats. No regeneration or invented content. Optional study_task_id selects an actual youtube_study job; omit for the latest summary. destination=new creates a page in the selected desktop workspace (title defaults to the saved video title); destination=existing appends without replacing content. Optional page_name is an EXACT existing page title; omit to use the selected Notion page. Private, workspace and shared pages are supported when editable. AIRA cannot grant missing permissions. Returns a tracked job; check actual completion before claiming success. Never retry a failed/partial export automatically.', 'parameters':{'type':'OBJECT','properties':{'study_task_id':{'type':'STRING'},'destination':{'type':'STRING','enum':['new','existing']},'title':{'type':'STRING'},'page_name':{'type':'STRING'}},'required':['destination']}},
    {'name':'notebooklm_mindmap','description':'On a direct request, add a public captioned YouTube video link to NotebookLM and generate/open a mind map using visible source and Mind Map controls. Creates a NEW notebook by default; for an existing notebook supply its observed/user-provided notebook_url or new_notebook=false for the already open AIRA Chrome notebook. Supply an observed/user-provided video_url; omit to read the selected AIRA YouTube tab. For a previously summarised video obtain sourceUrl from list_tasks. Uses the manually signed-in AIRA Chrome profile, no extra API key. Login, read-only notebooks and changed/ambiguous controls stop with an actionable result. Background tracked job; never claim generation finished until verified, and never repeat failed creation automatically.', 'parameters':{'type':'OBJECT','properties':{'video_url':{'type':'STRING'},'notebook_url':{'type':'STRING'},'new_notebook':{'type':'BOOLEAN'}}}},
    {'name':'youtube_study','description':'On explicit request, get captions, summarise a YouTube video, create an infographic, or both. Use output=transcript, summary, infographic or both. video_url must be user-provided or observed; omit it to automatically read the selected YouTube video tab in AIRA Chrome, including while the AIRA overlay has focus. No screenshot or pasted link is needed first. Fetches captions via a local Python worker, caches on E:, and uses the saved Gemini key and selected task-board models only for requested generation. No captions means no invented summary; does not watch visual frames. After completion use export_summary_to_notion only on an explicit export request. Returns a background job ID; results and downloads appear on the task board.','parameters':{'type':'OBJECT','properties':{'video_url':{'type':'STRING'},'output':{'type':'STRING','enum':['transcript','summary','infographic','both']}},'required':['output']}},
    {'name': 'coding_task', 'description': 'On a direct request, investigate or fix a problem in the selected E-drive coding project using OpenCode. Include the exact error and instructions. Set mode=fix only when the person explicitly requests code changes; investigate denies edits. Returns a job ID immediately; code/tests run independently of desktop tasks. The user selects project/test runner on the task board.', 'parameters': {'type': 'OBJECT', 'properties': {'task': {'type': 'STRING'}, 'mode': {'type': 'STRING', 'enum': ['investigate','fix']}}, 'required': ['task','mode']}},
    {'name': 'list_tasks', 'description': 'List current/recent jobs and actual results. Use before identifying a job from an app name. Never invent job IDs or claim completion from a queued acknowledgement.', 'parameters': {'type': 'OBJECT', 'properties': {}}},
    {'name': 'control_task', 'description': 'On a direct request, update, pause, resume or cancel a specific job. Obtain its exact ID from list_tasks. Ask which job when ambiguous. Updates wait for the current action to finish. For a follow-up explicitly asking to fix code, set mode=fix; investigate denies edits. Pause/cancel does not undo committed work.', 'parameters': {'type': 'OBJECT', 'properties': {'task_id': {'type': 'STRING'}, 'action': {'type': 'STRING', 'enum': ['update','pause','resume','cancel']}, 'instruction': {'type': 'STRING'}, 'mode': {'type': 'STRING', 'enum': ['investigate','fix']}}, 'required': ['task_id','action']}},
    {'name': 'show_coding_project', 'description': 'On a direct request, show the selected coding project in VS Code. Queued behind any current desktop action. Does not diagnose or fix by itself.', 'parameters': {'type': 'OBJECT', 'properties': {}}},
    {'name': 'stop_all_tasks', 'description': 'On an explicit stop-all-work request, cancel active and queued jobs in both lanes. Partial changes remain. Conversation stays available unless the person also asks to stop listening.', 'parameters': {'type': 'OBJECT', 'properties': {}}},
]
TASK_NAMES = {t['name'] for t in TASK_TOOLS} | DESKTOP_JOBS | {'current_youtube_video'}
TASK_PROMPT = '''
CONCURRENT JOBS:
- Browser workflow: use open_browser for Chrome, search_youtube for a query and open_youtube_video for an observed result or user-provided link. For "search and open the first video", enqueue search_youtube then open_youtube_video(result_number=1) in order. Do not claim the result is relevant until inspecting the observed title. For a URL/link question call current_youtube_video, which returns observed data directly. For "summarise this video", "get its transcript" or "make an infographic of this video", use youtube_study with the respective output and omit the URL to automatically read the selected AIRA Chrome tab, even while the AIRA overlay has focus. Do not use a preliminary screenshot or deny access to the URL. Never invent a video ID from a topic. Say one short acknowledgement, then keep listening; study runs separately from desktop control. Do not speak a whole long summary unless requested. The saved result is based on captions, not visual inspection. For putting a video summary in Notion use export_summary_to_notion, never type_in_app or create_notion_note with a paraphrase. Use destination=existing only when requested; a named destination uses page_name, otherwise the selected page. For NotebookLM mind maps use notebooklm_mindmap; create a new notebook by default. Read the known video sourceUrl from list_tasks when referring to a prior summary; never guess it. These workflows are tracked desktop jobs and must not automatically repeat partial writes.
- All Windows tools now start tracked background jobs and return IDs immediately. Say briefly that the task started/queued; never say it completed until list_tasks shows the result. Keep listening for another command. App/folder/close/display requests join the same desktop queue.
- For a single simple command, acknowledge in at most one short sentence. Use search_maps for a place search in Google Maps, including a combined Chrome/Maps/search request; open_maps opens Maps without a query. Prefer open_app/open_folder/close_app/type_in_app/calculate_in_app over desktop_task for supported common actions. For "open Notion and append X", enqueue open_app then type_in_app with the person's exact X. Direct typing appends to the current editable Notion page and verifies readback. Another editor or replacing existing text uses desktop_task. Notepad is not installed. Use calculate_in_app for arithmetic in Calculator, e.g. 78*87; do not send basic arithmetic through the generic GUI agent.
- Always accept a new spoken command while jobs run. A separate desktop command queues behind the active desktop job; acknowledge that briefly. Never wait for an earlier job's completion to answer. If the person explicitly says "instead", "stop that and" or asks to switch away from the current task, list tasks, cancel the matching active desktop job, then enqueue the replacement. A normal extra command does not silently cancel work.
- Do not repeatedly poll list_tasks while a job is pending. Progress appears on the task board; return to listening. Use list_tasks when the person asks for status or gives a task-specific follow-up.
- coding_task investigates/fixes the project selected on the task board, independently of desktop work. Do not use desktop_task to edit code or run shell commands. Include explicit fix authority only when the person requests a fix; investigation alone must not edit files.
- For "open/show the invoice app/demo", call show_invoice_demo. It opens the ordinary application in its dedicated Chrome localhost tab, preserving the separate YouTube tab. For "this invoice total is wrong; go to VS Code and fix it", or "the application in my VS Code has an error; fix it" when the registered demo is in use, call repair_invoice_app with the observation. The configured demo defaults to a deterministic known-bug repair: real file edits, a new regression-test file, all eight checks in the visible VS Code integrated terminal and return to the invoice tab, with no coding inference. This is one automatic workflow; no separate terminal/type/Enter request is needed. Do not describe that mode as general autonomous diagnosis. Keep the initial acknowledgement short; do not dictate the solution before execution. Never reset automatically. Other projects still use the selected coding project and OpenCode; do not guess an arbitrary workspace path from a title.
- list_tasks gives real job statuses and results. For "change the Notion task title", "pause the coding task", or other follow-ups, list tasks, select the unambiguous matching job ID, then control_task. Ask if several jobs match. A title/content correction is a follow-up to the existing note, never another create_notion_note call.
- Desktop jobs take turns; never claim simultaneous keyboard/mouse control. Updates to running jobs apply after the current action exits, not immediately mid-keystroke. Pausing stops future input and can leave partial work. Resume inspects existing state, never blindly repeats note creation.
 - Replies use explicit-stop mode by default. Ordinary speech must not cancel accepted background jobs. If optional speech interruption is enabled, it only interrupts the reply. "Cancel the Notion task" cancels only that job; "stop all tasks" cancels both lanes; "Stop AIRA" or "Hey AIRA, stop doing the work that you are doing" ends conversation and all active jobs.
 - Standalone fillers or background fragments such as "the", "he", "hello" or "leave" are not cancellation instructions. Never infer a desktop action or a stop from those fragments; wait for a meaningful complete request.
- show_coding_project displays the selected folder in VS Code via the desktop queue. Screen visibility is separate from coding investigation. Check the report's actual test result; worker prose is not verification. A diagnosis with no test runner is not a tested fix.
'''

async def execute_task_tool(user, name, args):
    supervisor = get_supervisor()
    try:
        if name == 'current_youtube_video':
            # A URL question needs the observation in this turn, not a job ID.
            if supervisor.lock(user, 'desktop').locked():
                return json.dumps({'status':'busy','message':'A browser/desktop action is still running. Ask for the selected video URL once it finishes.'})
            return json.dumps(await supervisor.read_current_video(user), ensure_ascii=False)
        if name == 'list_tasks':
            rows = supervisor.store.list(user)[:12]
            return json.dumps([{'id': r['id'], 'title': r['title'], 'lane': r['lane'], 'status': r['status'], 'progress': r['progress'], 'pendingUpdates': len(r['revisions']), 'result': {k: r['report'].get(k) for k in ('kind','summary','changedFiles','verified','videos','videoUrl','sourceUrl','notebookUrl','notionPageId','destinationTitle','sourceTitle','mindMapTitle','studyTaskId','assets')} if r.get('report') else None} for r in rows], ensure_ascii=False)[:16000]
        if name == 'control_task':
            row = await supervisor.control(user, args.get('task_id'), args.get('action'), args.get('instruction'), args.get('mode'))
        elif name == 'stop_all_tasks':
            await supervisor.cancel_all(user); return 'All active jobs cancelled. Partial changes may remain.'
        else: row = await supervisor.submit(user, name, args)
        return json.dumps({'id': row['id'], 'status': row['status'], 'title': row['title'], 'pendingUpdates': len(row['revisions']), 'message': 'Tracked job; check list_tasks for actual completion. Updates wait for the current action to exit.'})
    except (ValueError, OSError) as error:
        return str(error)[:400]
