import secrets
import time
from fastapi import HTTPException, Request
from app.config import settings

USER_ID = 'local'
COOKIE = 'aira_session'
sessions: dict[str, float] = {}

def allowed_origin(origin: str | None, host: str | None) -> bool:
    return bool(origin and (origin in settings.cors_origins or origin == f'http://{host}'))

def check_origin(request: Request):
    if not allowed_origin(request.headers.get('origin'), request.headers.get('host')):
        raise HTTPException(403, 'Open AIRA from its local launch URL')

def new_session():
    token = secrets.token_urlsafe(32)
    now = time.time()
    for old in list(sessions):
        if sessions[old] < now:
            sessions.pop(old, None)
    sessions[token] = now + 12 * 3600
    return token

def validate(token):
    if not isinstance(token, str) or sessions.get(token, 0) < time.time():
        raise HTTPException(401, 'Local session expired. Open AIRA again.')
    return {'user_id': USER_ID, 'email': '', 'display_name': 'You'}
