import asyncio
from urllib.parse import quote
from app.config import settings

def resolve_media(name):
    root = (settings.aira_data_dir / 'media').resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError('Invalid media path')
    return target

async def save_media(data: bytes, name: str):
    target = resolve_media(name)
    def write():
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + '.tmp')
        temp.write_bytes(data)
        temp.replace(target)
    await asyncio.to_thread(write)
    return '/media/' + quote(name, safe='/')
