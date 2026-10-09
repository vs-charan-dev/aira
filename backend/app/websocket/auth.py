import asyncio
import json
from fastapi import WebSocket
from app.core.local_auth import allowed_origin, validate

async def authenticate_websocket(websocket: WebSocket, url_user_id: str):
    try:
        if not allowed_origin(websocket.headers.get('origin'), websocket.headers.get('host')):
            raise ValueError('Invalid origin')
        msg = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout=10))
        if msg.get('type') != 'auth':
            raise ValueError('Auth handshake required')
        user = validate(msg.get('token'))
        if user['user_id'] != url_user_id:
            raise ValueError('Wrong local profile')
        await websocket.send_json({'type': 'auth_success', 'userId': url_user_id})
        return user
    except Exception:
        await websocket.send_json({'type': 'error', 'code': 'UNAUTHORIZED', 'message': 'Local session required', 'retryable': False})
        await websocket.close(code=4001)
        return None
