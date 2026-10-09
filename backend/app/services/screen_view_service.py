"""On-request, transient screen frames tied to the requesting connection."""
import asyncio
import base64
import uuid
from app.websocket.manager import manager

_pending: dict[str, tuple[str, asyncio.Future, object]] = {}

async def request_screen_view(user_id: str, *, source: str, session_id: str | None = None) -> tuple[bytes | None, str]:
    connection = manager.get_connection(user_id)
    if connection is None or user_id in _pending:
        return None, 'Screen view unavailable or already pending.'
    request_id = str(uuid.uuid4())
    future = asyncio.get_running_loop().create_future()
    _pending[user_id] = (request_id, future, connection)
    try:
        sent = await manager.send(user_id, {'type': 'screen_view_request', 'requestId': request_id, 'source': source, 'sessionId': session_id})
        if not sent:
            return None, 'Desktop disconnected; no screen received.'
        return await asyncio.wait_for(future, 15)
    except TimeoutError:
        return None, 'Screen view timed out; do not claim to see it.'
    finally:
        _pending.pop(user_id, None)

def resolve_screen_view(user_id: str, msg: dict, connection: object) -> bool:
    pending = _pending.get(user_id)
    if not pending or pending[0] != msg.get('requestId') or pending[2] is not connection or pending[1].done():
        return False
    data = msg.get('data')
    if not data:
        pending[1].set_result((None, 'No screen received. Launch the AIRA desktop app and keep the requested page visible.'))
        return True
    if not isinstance(data, str) or len(data) > 3_000_000:
        return False
    try:
        jpeg = base64.b64decode(data, validate=True)
        if not jpeg.startswith(b'\xff\xd8') or len(jpeg) > 2_000_000:
            return False
    except (ValueError, TypeError):
        return False
    pending[1].set_result((jpeg, 'Screen frame received.'))
    return True
