"""Explicit Gemini smoke check: no microphone, screen, or personal memories.

Uses the configured key and API quota. Starts each real agent with an empty
diagnostic profile, waits for greeting audio, and closes it. Saves no memories.
"""
import asyncio
from app.services.user_settings_service import get_user_gemini_key
from app.agents.capture_agent import CaptureAgent
from app.agents.recall_agent import RecallAgent

async def main():
    key = await get_user_gemini_key('local')
    if not key:
        raise RuntimeError('Save your Gemini key in AIRA Settings first.')
    audio_event = asyncio.Event()
    async def on_audio(data):
        if data:
            audio_event.set()
    async def noop(*args):
        pass
    capture = CaptureAgent('diagnostic', 'diagnostic', noop, on_audio=on_audio,
                           on_text=noop, display_name='Tester', gemini_api_key=key)
    try:
        await capture.start()
        await asyncio.wait_for(audio_event.wait(), timeout=25)
        print('Capture agent tool configuration, startup, and greeting audio: PASS')
    finally:
        await capture.stop()
    audio_event.clear()
    recall = RecallAgent()
    try:
        await recall.start_session('diagnostic', {}, on_audio, noop, noop, noop,
                                   display_name='Tester', gemini_api_key=key)
        await asyncio.wait_for(audio_event.wait(), timeout=25)
        print('Recall agent tool configuration, startup, and greeting audio: PASS')
    finally:
        await recall.close_session('diagnostic')

if __name__ == '__main__':
    asyncio.run(main())
