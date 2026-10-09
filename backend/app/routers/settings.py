from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import verify_token
from app.services.user_settings_service import get_user_gemini_key, set_user_gemini_key, get_user_voice, set_user_voice
from app.core.voices import VOICES, validate_voice, PREVIEW_TEXT
from app.core.tracked_gemini import LiveSessionBusy
from app.services.voice_preview_service import preview_voice, SAMPLE_RATE
import base64
import asyncio
from app.core.gemini import get_genai_client, LIVE_MODEL, STANDARD_MODEL, EMBEDDING_MODEL, IMAGE_MODEL
from google.genai import types
from app.core.secrets import read_key

router = APIRouter(prefix="/api/v1", tags=["settings"])


@router.get("/settings")
async def get_settings(user: dict = Depends(verify_token)):
    api_key = await get_user_gemini_key(user["user_id"])
    return {
        "hasGeminiKey": bool(api_key),
        "geminiApiKeyPreview": f"{api_key[:8]}..." if api_key else None,
        "keyStorageError": await _storage_error(),
        "voiceName": await get_user_voice(user['user_id']),
        "voices": VOICES,
    }

async def _storage_error():
    try:
        await asyncio.to_thread(read_key)
        return None
    except OSError:
        return 'The saved key belongs to a different Windows account. Save your key again in this launch.'


@router.put("/settings")
async def update_settings(body: dict, user: dict = Depends(verify_token)):
    if 'voiceName' in body:
        try:
            validate_voice(body['voiceName'])
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
    if 'geminiApiKey' in body:
        api_key = body.get("geminiApiKey") or None
        await set_user_gemini_key(user["user_id"], api_key)
    if 'voiceName' in body:
        await set_user_voice(user['user_id'], body['voiceName'])
    return {"ok": True}

@router.post('/settings/voice-preview')
async def get_voice_preview(body: dict, user: dict = Depends(verify_token)):
    try:
        voice = validate_voice(body.get('voiceName'))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    key = await get_user_gemini_key(user['user_id'])
    try:
        audio, cached = await preview_voice(user['user_id'], voice, key)
    except LiveSessionBusy:
        raise HTTPException(409, 'Stop conversation or capture before previewing a voice.') from None
    except Exception:
        # Do not expose SDK messages, URLs, or credentials.
        raise HTTPException(502, 'Could not generate the short voice preview. Check your Gemini key, model access, quota and connection, then retry.') from None
    return {'voiceName': voice, 'text': PREVIEW_TEXT, 'audio': base64.b64encode(audio).decode(), 'sampleRate': SAMPLE_RATE, 'durationSeconds': len(audio) / (SAMPLE_RATE * 2), 'cached': cached}


@router.post('/settings/test')
async def test_gemini(user: dict = Depends(verify_token)):
    from app.core.tracked_gemini import has_live_for_user
    if has_live_for_user(user['user_id']):
        raise HTTPException(409, 'Stop capture or voice before running the connection test.')
    key = await get_user_gemini_key(user['user_id'])
    if not key:
        return {'results': [{'feature': 'API key', 'ok': False, 'message': 'Save your key first.'}]}
    client = get_genai_client(key)
    results = []
    async def check(label, operation):
        try:
            await asyncio.wait_for(operation(), timeout=30)
            results.append({'feature': label, 'ok': True, 'message': 'Passed'})
        except Exception as exc:
            # Never return raw SDK errors: they may include URLs or credentials.
            code = getattr(exc, 'code', None)
            results.append({'feature': label, 'ok': False, 'message':
                f'Failed ({code or type(exc).__name__}). Check model access, quota, internet, and .env model selection.'})
    async def text():
        result = await client.aio.models.generate_content(model=STANDARD_MODEL, contents='Reply with OK.',
            config=types.GenerateContentConfig(max_output_tokens=64))
        if not result.text:
            raise ValueError('No text response')
    async def embedding():
        result = await client.aio.models.embed_content(model=EMBEDDING_MODEL, contents='AIRA memory test',
            config=types.EmbedContentConfig(output_dimensionality=768))
        if len(result.embeddings[0].values) != 768:
            raise ValueError('Wrong embedding dimension')
    async def live():
        async with client.aio.live.connect(model=LIVE_MODEL, config=types.LiveConnectConfig(
            response_modalities=['AUDIO'],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=await get_user_voice(user['user_id'])))),
        )) as session:
            await session.send_realtime_input(text='Say hello briefly.')
            async for result in session.receive():
                if result.data:
                    return
            raise ValueError('Live returned no audio')
    await check('Text inference', text)
    await check('768-dimensional embeddings', embedding)
    await check('Live audio generation', live)
    results.append({'feature': 'Image generation', 'ok': None,
                    'message': f'Test separately with a diagram or room synthesis ({IMAGE_MODEL}); no image generated by this check.'})
    return {'results': results}
