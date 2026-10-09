"""Short Gemini Live previews, cached locally by model/voice/phrase/version."""
import asyncio
import hashlib
import re
import uuid
import weakref
from google.genai import types
from app.config import settings
from app.core.gemini import LIVE_MODEL, get_genai_client
from app.core.voices import PREVIEW_TEXT, validate_voice
from app.core.tracked_gemini import has_live_for_user, LiveSessionBusy
from app.core.usage import usage_scope

SAMPLE_RATE = 24000
MAX_BYTES = SAMPLE_RATE * 2 * 8
_locks = weakref.WeakKeyDictionary()

def _lock(user_id):
    return _locks.setdefault(asyncio.get_running_loop(), {}).setdefault(user_id, asyncio.Lock())

def _cache_path(voice):
    digest = hashlib.sha256(f'v1|{LIVE_MODEL}|{voice}|{PREVIEW_TEXT}'.encode()).hexdigest()
    return settings.aira_data_dir / 'media' / 'voice-previews' / f'{digest}.pcm'

def _read_cache(path):
    try:
        data = path.read_bytes()
        return data if 0 < len(data) <= MAX_BYTES and len(data) % 2 == 0 else None
    except FileNotFoundError:
        return None

def _write_cache(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f'.{uuid.uuid4().hex}.tmp')
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)

async def _generate(voice, api_key):
    client = get_genai_client(api_key)
    config = types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction='Speak in English. Say exactly "Hi Charan." once, with no other words or sound effects.',
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True)),
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
    )
    audio = bytearray(); transcript = ''; complete = False
    async with client.aio.live.connect(model=LIVE_MODEL, config=config, replace_existing=False) as session:
        await session.send_client_content(turns=types.Content(role='user', parts=[types.Part(text=f'Say exactly: {PREVIEW_TEXT}')]), turn_complete=True)
        async for response in session.receive():
            content = getattr(response, 'server_content', None)
            turn = getattr(content, 'model_turn', None)
            parts = getattr(turn, 'parts', None) or []
            chunks = [part.inline_data.data for part in parts if getattr(part, 'inline_data', None) and part.inline_data.data and (part.inline_data.mime_type or '').startswith('audio/pcm')]
            if not parts and getattr(response, 'data', None):
                chunks = [response.data]
            for chunk in chunks:
                audio.extend(chunk)
            if len(audio) > MAX_BYTES:
                raise ValueError('Preview was longer than the short greeting.')
            output = getattr(content, 'output_transcription', None)
            transcript += getattr(output, 'text', None) or ''
            if getattr(content, 'turn_complete', False):
                complete = True
                break
    if not complete or not audio or len(audio) % 2:
        raise ValueError('Preview ended without complete audio.')
    if re.sub('[^a-z]', '', transcript.lower()) != 'hicharan':
        raise ValueError('Preview did not match the requested greeting.')
    return bytes(audio)

async def preview_voice(user_id, voice, api_key):
    validate_voice(voice)
    async with _lock(user_id):
        if has_live_for_user(user_id):
            raise LiveSessionBusy('Stop conversation or capture before previewing a voice.')
        path = _cache_path(voice)
        cached = await asyncio.to_thread(_read_cache, path)
        if cached:
            return cached, True
        with usage_scope(user_id, 'voice_preview', voice):
            audio = await asyncio.wait_for(_generate(voice, api_key), timeout=20)
        await asyncio.to_thread(_write_cache, path, audio)
        return audio, False
