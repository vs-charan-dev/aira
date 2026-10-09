"""Instrument the existing async SDK surface without changing agent prompts."""
import asyncio
from contextlib import asynccontextmanager, suppress
import time
from types import SimpleNamespace
import weakref

from app.config import settings
from app.core.usage import UsageRun

_live = {}
_locks = weakref.WeakKeyDictionary()

class LiveSessionBusy(RuntimeError):
    """A preview must not replace an existing conversation or capture."""


def has_live_for_user(user_id):
    session = _live.get(user_id)
    return bool(session and not session.closed)


def _lock(user_id):
    per_loop = _locks.setdefault(asyncio.get_running_loop(), {})
    return per_loop.setdefault(user_id, asyncio.Lock())


async def close_live_for_user(user_id, reason='stopped'):
    async with _lock(user_id):
        session = _live.get(user_id)
        if session:
            await session.close(reason)


async def close_all_live(reason='backend_shutdown'):
    for user_id in list(_live):
        await close_live_for_user(user_id, reason)


class TrackedModels:
    def __init__(self, raw):
        self.raw = raw

    async def _request(self, operation, **kwargs):
        run = UsageRun(kwargs['model'], operation)
        config = kwargs.get('config')
        tools = config.get('tools', []) if isinstance(config, dict) else getattr(config, 'tools', []) or []
        if any((isinstance(tool, dict) and 'google_search' in tool) or getattr(tool, 'google_search', None) is not None for tool in tools):
            run.body['possibleExtraCharges'] = 'Google Search charges/free allowance are not included.'
        await run.save()
        try:
            response = await getattr(self.raw, operation)(**kwargs)
            await run.observe(getattr(response, 'usage_metadata', None), text_only=operation != 'embed_content' and 'image' not in run.model)
            await run.finish()
            return response
        except BaseException:
            await run.finish('failed')
            raise

    async def generate_content(self, **kwargs):
        return await self._request('generate_content', **kwargs)

    async def embed_content(self, **kwargs):
        return await self._request('embed_content', **kwargs)

    async def generate_content_stream(self, **kwargs):
        run = UsageRun(kwargs['model'], 'generate_content_stream')
        await run.save()
        async def stream():
            status = 'interrupted'
            try:
                async for chunk in await self.raw.generate_content_stream(**kwargs):
                    # Stream metadata is cumulative within this request. Replace.
                    await run.observe(getattr(chunk, 'usage_metadata', None), text_only=True)
                    yield chunk
                status = 'completed'
            except Exception:
                status = 'failed'
                raise
            finally:
                await run.finish(status)
        return stream()


class TrackedSession:
    def __init__(self, raw, run):
        self.raw, self.run = raw, run
        self.closed = False
        self.turn = 0
        self.turn_ended = False
        self.last_activity = time.monotonic()

    def __getattr__(self, name):
        return getattr(self.raw, name)

    async def close(self, reason='stopped'):
        if self.closed:
            return
        self.closed = True
        self.run.stop_reason = reason
        if self.run.feature in ('capture', 'recall'):
            from app.websocket.manager import manager
            with suppress(Exception):
                await manager.send(self.run.user_id, {'type': 'live_mode_stopped', 'mode': self.run.feature,
                    'reason': reason, 'sessionId': self.run.group_id})
        # Announce the intended reason before socket shutdown can emit a generic
        # inactive-session notice on the other lifecycle task.
        with suppress(Exception):
            await self.raw.close()

    async def receive(self):
        try:
            async for message in self.raw.receive():
                content = getattr(message, 'server_content', None)
                transcript = getattr(content, 'input_transcription', None)
                turn = getattr(content, 'model_turn', None)
                tool_call = getattr(message, 'tool_call', None)
                new_content = bool((getattr(transcript, 'text', None) or '').strip() or
                    getattr(turn, 'parts', None) or getattr(tool_call, 'function_calls', None))
                if new_content:
                    self.last_activity = time.monotonic()
                    if self.turn_ended:
                        self.turn += 1
                        self.turn_ended = False
                slot = self.turn if settings.aira_live_usage_mode == 'per_turn' else 0
                await self.run.observe(getattr(message, 'usage_metadata', None), slot)
                if content and getattr(content, 'turn_complete', False):
                    self.turn_ended = True
                if not self.closed:
                    yield message
        except Exception:
            if not self.closed:
                await self.close('connection_error')
                raise

    async def watch_limits(self):
        while not self.closed:
            await asyncio.sleep(.5)
            elapsed = time.monotonic() - self.run.started
            idle = time.monotonic() - self.last_activity
            cost = self.run.body.get('estimatedUsd') or 0
            reason = None
            if settings.aira_live_max_seconds and elapsed >= settings.aira_live_max_seconds:
                reason = 'duration_limit'
            elif settings.aira_live_idle_seconds and idle >= settings.aira_live_idle_seconds:
                reason = 'idle_limit'
            elif settings.aira_live_max_estimated_usd and cost >= settings.aira_live_max_estimated_usd:
                reason = 'estimated_cost_limit'
            if reason:
                await self.close(reason)
                return


class TrackedLive:
    def __init__(self, raw):
        self.raw = raw

    @asynccontextmanager
    async def connect(self, **kwargs):
        replace_existing = kwargs.pop('replace_existing', True)
        run = UsageRun(kwargs['model'], 'live')
        await run.save()
        wrapper, guard = None, None
        status = 'completed'
        try:
            # Keep the SDK context open beyond the lock, but reserve connection
            # creation so simultaneous requests cannot leave two paid sessions.
            async with _lock(run.user_id):
                previous = _live.get(run.user_id)
                if previous and not previous.closed:
                    if not replace_existing:
                        raise LiveSessionBusy('Stop conversation or capture before previewing a voice.')
                    await previous.close('mode_switch')
                context = self.raw.connect(**kwargs)
                raw = await context.__aenter__()
                wrapper = TrackedSession(raw, run)
                _live[run.user_id] = wrapper
            guard = asyncio.create_task(wrapper.watch_limits())
            try:
                yield wrapper
            finally:
                guard.cancel()
                with suppress(asyncio.CancelledError):
                    await guard
                if _live.get(run.user_id) is wrapper:
                    _live.pop(run.user_id, None)
                await context.__aexit__(None, None, None)
        except asyncio.CancelledError:
            status = 'stopped'
            raise
        except Exception:
            status = 'failed'
            if wrapper and not wrapper.closed:
                await wrapper.close('connection_error')
            raise
        finally:
            if run.stop_reason:
                status = 'stopped'
            await run.finish(status)


class TrackedClient:
    def __init__(self, raw):
        self.aio = SimpleNamespace(models=TrackedModels(raw.aio.models), live=TrackedLive(raw.aio.live))
