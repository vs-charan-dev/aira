from fastapi import APIRouter, Depends, HTTPException

from app.middleware.auth import verify_token
from app.services.call_reminders import get_reminders
from app.services.twilio_voice import public_settings, save_credentials, credentials_path

router = APIRouter(prefix='/api/v1/call-reminders', tags=['phone reminders'])


@router.get('/settings')
async def get_settings(user=Depends(verify_token)):
    return public_settings()


@router.put('/settings')
async def save_settings(body: dict, user=Depends(verify_token)):
    try:
        save_credentials(body)
        return public_settings()
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    except OSError:
        raise HTTPException(500, 'Could not encrypt and save Twilio settings for this Windows account.') from None


@router.delete('/settings')
async def remove_settings(user=Depends(verify_token)):
    service = get_reminders()
    credentials_path().unlink(missing_ok=True)
    for row in service.store.rows(user['user_id']):
        if row['status'] == 'pending':
            service.store.cancel(user['user_id'], row['id'], service.clock())
    return public_settings()


@router.get('')
async def list_reminders(user=Depends(verify_token)):
    service = get_reminders()
    return {'context': service.context(), 'reminders': [service.store.public(row) for row in service.store.rows(user['user_id'])[:30]]}


@router.post('')
async def schedule(body: dict, user=Depends(verify_token)):
    try:
        return get_reminders().schedule(user['user_id'], body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post('/{ident}/cancel')
async def cancel(ident: str, user=Depends(verify_token)):
    service = get_reminders()
    try:
        return service.store.public(service.store.cancel(user['user_id'], ident, service.clock()))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
