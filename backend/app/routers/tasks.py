from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import verify_token
from app.services.task_supervisor import get_supervisor
from app.services.coding_worker import validate_project, BINARY
from app.services import invoice_demo

router = APIRouter(prefix='/api/v1/tasks', tags=['local tasks'])

@router.get('')
async def list_tasks(user=Depends(verify_token)):
    s = get_supervisor()
    rows = s.store.list(user['user_id'])[:30]
    # Diff bodies and test logs are fetched on demand, not on every poll.
    return {'jobs': [{**{k: v for k,v in r.items() if k not in ('user','requestKey','report','action','events')}, 'report': {k:r['report'].get(k) for k in ('kind','summary','changedFiles','verified','videos','videoUrl','title','sourceUrl','videoTitle','notebookUrl','notionPageId','destinationTitle','sourceTitle','mindMapTitle','studyTaskId','assets')} if r.get('report') else None} for r in rows], 'project': s.store.config(user['user_id']), 'workerInstalled': BINARY.is_file(), 'videoModels':s.store.video_config(user['user_id'])}

@router.get('/invoice-demo')
async def demo_status(user=Depends(verify_token)):
    try: return invoice_demo.status()
    except (ValueError, OSError) as error: raise HTTPException(400, str(error)) from None

@router.post('/invoice-demo/prepare')
async def demo_prepare(body: dict, user=Depends(verify_token)):
    s = get_supervisor(); uid = user['user_id']
    try:
        reset = body.get('reset', False)
        if not isinstance(reset, bool): raise ValueError('Reset must be true or false.')
        if any(r['lane'] == 'coding' and r['status'] in ('queued','running') for r in s.store.list(uid)):
            raise ValueError('Finish or cancel coding jobs before selecting or resetting the demo.')
        # No await during file mutation/config selection; a submit cannot race it.
        value = invoice_demo.prepare(reset)
        s.store.set_config(uid, {'path': value['path'], 'runner': 'node'})
        return value
    except (ValueError, OSError) as error: raise HTTPException(400, str(error)) from None

@router.post('/invoice-demo/evaluate')
async def demo_evaluate(body: dict, user=Depends(verify_token)):
    s = get_supervisor()
    async with s.lock(user['user_id'], 'preview'):
        try: return await invoice_demo.evaluate(body.get('price'), body.get('discount'), body.get('version'))
        except (ValueError, OSError) as error: raise HTTPException(400, str(error)) from None

@router.post('/invoice-demo/fix')
async def demo_fix(body: dict, user=Depends(verify_token)):
    s = get_supervisor(); uid = user['user_id']
    try:
        key = body.get('requestId')
        if not isinstance(key, str) or not 1 <= len(key) <= 64: raise ValueError('Supply a request ID.')
        for row in s.store.list(uid):
            if row.get('requestKey') == key: return row
        info = invoice_demo.status()
        config = s.store.config(uid)
        if not info['ready'] or invoice_demo.generation_for(config) != body.get('generation') or config['runner'] != 'node':
            raise ValueError('Select the current invoice demo project with Node tests before fixing it.')
        if any(r['lane'] == 'coding' and r['status'] in ('queued','running') for r in s.store.list(uid)):
            raise ValueError('A coding job is already active. Finish or cancel it first.')
        return await s.submit(uid, 'repair_invoice_app', {'problem':
            body.get('problem') or 'The invoice total is wrong when I apply a discount. Investigate and fix it.'}, key)
    except (ValueError, OSError) as error: raise HTTPException(400, str(error)) from None

@router.get('/{ident}/events')
async def events(ident: str, user=Depends(verify_token)):
    try:
        row = get_supervisor().get(user['user_id'], ident)
        return {'events': row.get('events', []), 'status': row['status'], 'progress': row['progress']}
    except ValueError as error: raise HTTPException(404, str(error)) from None

@router.put('/video-models')
async def video_models(body:dict,user=Depends(verify_token)):
    try: get_supervisor().store.set_video_config(user['user_id'],body)
    except ValueError as error: raise HTTPException(400,str(error)) from None
    return get_supervisor().store.video_config(user['user_id'])

@router.put('/project')
async def project(body: dict, user=Depends(verify_token)):
    try: config = validate_project(body.get('path'), body.get('runner'))
    except (ValueError, OSError) as error: raise HTTPException(400, str(error)) from None
    get_supervisor().store.set_config(user['user_id'], config)
    return config

@router.post('')
async def start(body: dict, user=Depends(verify_token)):
    try:
        key = body.get('requestId')
        if not isinstance(key, str) or not 1 <= len(key) <= 64: raise ValueError('Supply a request ID.')
        return await get_supervisor().submit(user['user_id'], body.get('tool'), body.get('args') or {}, key)
    except (ValueError, OSError) as error: raise HTTPException(400, str(error)) from None

@router.post('/stop-all')
async def stop_all(user=Depends(verify_token)):
    await get_supervisor().cancel_all(user['user_id'])
    return {'ok': True}

@router.post('/{ident}/control')
async def control(ident: str, body: dict, user=Depends(verify_token)):
    try: return await get_supervisor().control(user['user_id'], ident, body.get('action'), body.get('instruction'), body.get('mode'))
    except ValueError as error: raise HTTPException(400, str(error)) from None

@router.get('/{ident}/report')
async def report(ident: str, user=Depends(verify_token)):
    try:
        row=get_supervisor().get(user['user_id'], ident)
        value=row.get('report')
        return {**value,'studyTaskId':row['id']} if value and value.get('kind')=='youtube' else value
    except ValueError as error: raise HTTPException(404, str(error)) from None
