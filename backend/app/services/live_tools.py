"""Keep the Live reader free while executing ordered, cancellable tool calls."""
import asyncio
import logging
import uuid
from google.genai import types

logger = logging.getLogger(__name__)

class LiveToolRunner:
    def __init__(self, session, execute):
        self.session, self.execute = session, execute
        self.pending = {}
        self.seen = set()
        self.lock = asyncio.Lock()
        self.closed = False

    def submit(self, calls):
        for call in calls:
            key = call.id or uuid.uuid4().hex
            if self.closed or key in self.seen:
                continue
            self.seen.add(key)
            task = asyncio.create_task(self._run(key, call))
            self.pending[key] = task

    async def _run(self, key, call):
        try:
            async with self.lock:
                if self.closed:
                    return
                try:
                    args = dict(call.args or {})
                    if call.name == 'schedule_call_reminder':
                        # Bind idempotency to the actual provider call, not model arguments.
                        args['requestId'] = key
                    result = await self.execute(call.name, args)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.warning('Live tool failed: %s', call.name)
                    result = 'Tool failed; completion was not verified. Do not retry a write automatically.'
                if not self.closed:
                    await self.session.send_tool_response(function_responses=[types.FunctionResponse(id=call.id, name=call.name, response={'result': result})])
        except asyncio.CancelledError:
            # Provider-cancelled calls must not send late completion responses.
            pass
        except Exception:
            logger.warning('Live tool response could not be delivered')
        finally:
            self.pending.pop(key, None)

    async def cancel(self, ids=None):
        if ids is not None:
            self.seen.update(ids)
        tasks = [task for key, task in list(self.pending.items()) if ids is None or key in ids]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        self.closed = True
        await self.cancel()
