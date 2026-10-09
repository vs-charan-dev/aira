import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.config import ROOT
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.local_store import initialize_store
from app.routers import local_session, media, usage
from app.core.usage import recover_usage, usage_scope
from app.core.tracked_gemini import close_all_live
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.routers import health, sessions, palace, rooms, search, artifacts, enrichment
from app.routers import settings as settings_router
from app.routers import tasks as tasks_router
from app.routers import personal_memories
from app.routers import call_reminders
from app.websocket.auth import authenticate_websocket
from app.websocket.handlers import route_message
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
    logging.getLogger("grpc").setLevel(logging.WARNING)
    initialize_store()
    from app.services.task_supervisor import get_supervisor
    get_supervisor()
    await recover_usage()
    from app.services.call_reminders import get_reminders
    reminders = get_reminders()
    reminders.start()
    try:
        yield
    finally:
        await reminders.close()
        await get_supervisor().close()
        await close_all_live()


app = FastAPI(
    title="AIRA Memory Palace",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]', 'testserver'])
app.include_router(local_session.router)
app.include_router(media.router)
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(palace.router)
app.include_router(rooms.router)
app.include_router(search.router)
app.include_router(artifacts.router)
app.include_router(enrichment.router)
app.include_router(settings_router.router)
app.include_router(usage.router)
app.include_router(tasks_router.router)
app.include_router(personal_memories.router)
app.include_router(call_reminders.router)


@app.middleware('http')
async def usage_context(request, call_next):
    feature = 'diagnostics' if request.url.path == '/api/v1/settings/test' else 'memory_api'
    with usage_scope('local', feature):
        return await call_next(request)



@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str) -> None:
    """Main WebSocket endpoint per websocket.md.

    Protocol:
      1. Accept connection
      2. Wait for auth handshake ({type: auth, token: ...})
      3. Route all subsequent messages through handlers.route_message()
      4. Disconnect and clean up on close or error
    """
    await websocket.accept()
    try:
        user = await authenticate_websocket(websocket, user_id)
        if user is None:
            return  # auth.py already closed the connection

        previous = manager.get_connection(user_id)
        if previous is not None and previous is not websocket:
            from app.services.task_supervisor import get_supervisor
            await get_supervisor().cancel_all(user_id)
            from app.core.tracked_gemini import close_live_for_user
            from app.agents.capture_agent import stop_user_agents
            from app.agents.recall_agent import recall_agent
            await close_live_for_user(user_id, 'tab_replaced')
            await stop_user_agents(user_id)
            await recall_agent.close_session(user_id)
            await previous.close(code=1000)
        manager.register(user_id, websocket)
        if user.get("display_name"):
            manager.set_display_name(user_id, user["display_name"])

        while True:
            raw = await websocket.receive_text()
            await route_message(user["user_id"], raw, websocket)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally: userId=%s", user_id)
    except Exception:
        logger.exception("Unexpected WebSocket error: userId=%s", user_id)
    finally:
        if manager.get_connection(user_id) is websocket:
            from app.services.task_supervisor import get_supervisor
            await get_supervisor().cancel_all(user_id)
            manager.disconnect(user_id)
            from app.agents.capture_agent import stop_user_agents
            from app.agents.recall_agent import recall_agent
            from app.core.tracked_gemini import close_live_for_user
            await close_live_for_user(user_id, 'disconnect')
            await stop_user_agents(user_id)
            await recall_agent.close_session(user_id)


# Serve the built palace through the same loopback origin as API/media/cookies.
frontend_dist = ROOT / 'frontend' / 'dist'
if (frontend_dist / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=frontend_dist / 'assets'), name='assets')

@app.get('/{path:path}', include_in_schema=False)
async def frontend(path: str):
    if path.startswith(('api/', 'media/', 'ws/', 'artifacts/')):
        raise HTTPException(404)
    target = (frontend_dist / path).resolve()
    if not target.is_relative_to(frontend_dist.resolve()):
        raise HTTPException(404)
    if target.is_file():
        return FileResponse(target)
    if '.' in path.rsplit('/', 1)[-1] or not (frontend_dist / 'index.html').exists():
        raise HTTPException(404)
    return FileResponse(frontend_dist / 'index.html', headers={'Cache-Control': 'no-cache'})
