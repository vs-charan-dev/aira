from fastapi import Request
from app.core.local_auth import COOKIE, check_origin, validate

async def verify_token(request: Request) -> dict[str, str]:
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        check_origin(request)
    bearer = request.headers.get('authorization', '').removeprefix('Bearer ')
    return validate(bearer or request.cookies.get(COOKIE))
