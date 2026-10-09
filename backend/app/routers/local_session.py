from fastapi import APIRouter, Depends, Request, Response
from app.core.local_auth import COOKIE, check_origin, new_session, sessions
from app.middleware.auth import verify_token
from app.services.user_service import get_or_create_user

router = APIRouter(prefix='/api/v1/local-session', tags=['local session'])

@router.post('')
async def open_session(request: Request, response: Response):
    check_origin(request)
    old = request.cookies.get(COOKIE)
    if old:
        sessions.pop(old, None)
    token = new_session()
    await get_or_create_user('local', '', 'You')
    from app.services.personal_memory_service import ensure_personal_palace
    await ensure_personal_palace('local')
    response.set_cookie(COOKIE, token, httponly=True, samesite='strict', max_age=43200)
    response.headers['Cache-Control'] = 'no-store'
    return {'userId': 'local', 'displayName': 'You', 'token': token}

@router.delete('')
async def close_session(request: Request, response: Response, user=Depends(verify_token)):
    from app.core.tracked_gemini import close_live_for_user
    from app.agents.capture_agent import stop_user_agents
    from app.agents.recall_agent import recall_agent
    from app.websocket.manager import manager
    await close_live_for_user(user['user_id'], 'logout')
    await stop_user_agents(user['user_id'])
    await recall_agent.close_session(user['user_id'])
    ws = manager.get_connection(user['user_id'])
    if ws:
        await ws.close(code=1000)
    sessions.pop(request.cookies.get(COOKIE), None)
    response.delete_cookie(COOKIE)
    return {'ok': True}
