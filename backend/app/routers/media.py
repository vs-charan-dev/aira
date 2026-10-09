from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.core.local_media import resolve_media
from app.middleware.auth import verify_token

router = APIRouter()

@router.get('/media/{name:path}')
async def get_media(name: str, user=Depends(verify_token)):
    try:
        target = resolve_media(name)
    except ValueError:
        raise HTTPException(404)
    if not target.is_file():
        raise HTTPException(404)
    return FileResponse(target, headers={'Cache-Control': 'private, max-age=3600', 'X-Content-Type-Options': 'nosniff'})
