from fastapi import APIRouter, Depends
from app.middleware.auth import verify_token
from app.core.usage import usage_summary

router = APIRouter(prefix='/api/v1/usage', tags=['usage'])


@router.get('')
async def get_usage(user=Depends(verify_token)):
    return await usage_summary(user['user_id'])
