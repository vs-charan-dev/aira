import asyncio
from app.config import settings
from app.core.secrets import read_key, save_key
from app.core.local_store import get_store
from app.core.voices import DEFAULT_VOICE, VOICE_NAMES, validate_voice

async def get_user_gemini_key(user_id: str) -> str | None:
    try:
        return await asyncio.to_thread(read_key) or settings.gemini_api_key or None
    except OSError:
        # A DPAPI file saved by a different Windows user cannot be decrypted.
        # Do not silently fall back to another key when a saved key is unreadable.
        return None

async def set_user_gemini_key(user_id: str, api_key: str | None):
    await asyncio.to_thread(save_key, api_key)

async def get_user_voice(user_id: str) -> str:
    snapshot = await get_store().collection('users').document(user_id).collection('settings').document('voice').get()
    name = (snapshot.to_dict() or {}).get('voiceName', DEFAULT_VOICE)
    return name if isinstance(name, str) and name in VOICE_NAMES else DEFAULT_VOICE

async def set_user_voice(user_id: str, name: str):
    await get_store().collection('users').document(user_id).collection('settings').document('voice').set({'voiceName': validate_voice(name)})
