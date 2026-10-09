"""Bounded PCM forwarding: slow provider writes never block desktop messages."""
import asyncio
from contextlib import suppress
from google.genai import types


class LiveAudioSender:
    def __init__(self, session, failed, *, capacity=6, timeout=8):
        self.session, self.failed, self.timeout = session, failed, timeout
        self.queue = asyncio.Queue(maxsize=capacity)
        self.task = None
        self.closed = False

    def offer(self, audio):
        if self.closed: return
        if self.task is None: self.task = asyncio.create_task(self.run())
        if self.queue.full(): self.queue.get_nowait()
        self.queue.put_nowait(audio)

    async def run(self):
        try:
            while not self.closed:
                audio = await self.queue.get()
                await asyncio.wait_for(self.session.send_realtime_input(
                    audio=types.Blob(data=audio, mime_type='audio/pcm;rate=16000')), self.timeout)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.closed = True
            await self.failed('audio_send_timeout' if isinstance(error, TimeoutError) else 'connection_error')

    async def close(self):
        self.closed = True
        if self.task and self.task is not asyncio.current_task():
            self.task.cancel()
            with suppress(asyncio.CancelledError): await self.task
        while not self.queue.empty(): self.queue.get_nowait()
