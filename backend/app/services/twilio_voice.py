"""One local recipient; encrypted credentials and outbound-only Twilio Voice.

Inline TwiML (paid) or demo audio (trial) needs no public local server.
Never retry a create-call request: a lost response can still mean a real call.
"""
import json
import re
from base64 import b64encode
from dataclasses import dataclass
from xml.etree.ElementTree import Element, SubElement, tostring

import httpx

from app.config import settings
from app.core.secrets import _crypt


def credentials_path():
    return settings.aira_data_dir / 'secrets' / 'twilio.dpapi'


def read_credentials():
    target = credentials_path()
    try:
        return json.loads(_crypt(target.read_bytes(), decrypt=True)) if target.exists() else None
    except (OSError, ValueError, RuntimeError):
        raise ValueError('Cannot read the saved Twilio settings. Save them again using the Windows account running AIRA.') from None


def phone(value):
    if not isinstance(value, str) or not re.fullmatch(r'\+[1-9]\d{7,14}', value.strip()):
        raise ValueError('Use a full phone number with country code, such as +919876543210.')
    return value.strip()


def save_credentials(body):
    if not isinstance(body, dict) or set(body) - {'accountSid', 'authToken', 'fromNumber', 'toNumber'}:
        raise ValueError('Supply Account SID, Auth Token, calling number and your number.')
    sid = body.get('accountSid')
    if not isinstance(sid, str) or not re.fullmatch(r'AC[0-9a-fA-F]{32}', sid.strip()):
        raise ValueError('Enter a valid Twilio Account SID (AC followed by 32 hex characters).')
    token = body.get('authToken')
    # Empty token on an edit preserves the encrypted token for the SAME account.
    if not token:
        previous = read_credentials()
        token = previous.get('authToken') if previous and previous['accountSid'] == sid.strip() else None
    if not isinstance(token, str) or not re.fullmatch(r'[0-9a-fA-F]{32}', token.strip()):
        raise ValueError('Enter the 32-character Twilio Auth Token.')
    value = {'accountSid': sid.strip(), 'authToken': token.strip(),
             'fromNumber': phone(body.get('fromNumber')), 'toNumber': phone(body.get('toNumber'))}
    if value['fromNumber'] == value['toNumber']:
        raise ValueError('The calling number and your receiving number must be different.')
    if value['toNumber'].startswith('+91') and value['fromNumber'].startswith('+91'):
        raise ValueError('Twilio calls into India need a non-Indian calling number.')
    target = credentials_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_bytes(_crypt(json.dumps(value).encode()))
    temporary.replace(target)


def public_settings():
    try:
        value = read_credentials()
        return {'configured': bool(value), 'accountSid': value['accountSid'] if value else '',
                'fromNumber': value['fromNumber'] if value else '', 'toNumber': value['toNumber'] if value else '',
                'storageError': None, 'timezone': 'Asia/Kolkata', 'timezoneLabel': 'IST (UTC+05:30)'}
    except ValueError as exc:
        return {'configured': False, 'accountSid': '', 'fromNumber': '', 'toNumber': '',
                'storageError': str(exc), 'timezone': 'Asia/Kolkata', 'timezoneLabel': 'IST (UTC+05:30)'}


class CallRejected(Exception):
    """Definite Twilio rejection, safe to show without provider request data."""


class CallUncertain(Exception):
    """Do not repeat a POST after a transport error or ambiguous response."""


@dataclass(frozen=True)
class AcceptedCall:
    sid: str
    mode: str = 'reminder'


def rejection_detail(result, config):
    """Keep Twilio's actionable diagnosis while removing credentials and numbers."""
    try:
        value = result.json()
    except ValueError:
        value = {}
    if not isinstance(value, dict):
        value = {}
    code = value.get('code')
    label = f', code {code}' if type(code) is int and code > 0 else ''
    detail = value.get('message')
    if not isinstance(detail, str) or not detail.strip():
        detail = 'Check credentials, balance, recipient verification and Voice geographic permissions.'
    # Provider messages can echo request parameters. Never expose secrets in the
    # reminder database or UI, including an encoded HTTP Basic credential.
    basic = b64encode(f"{config['accountSid']}:{config['authToken']}".encode()).decode()
    for secret in sorted([basic, *config.values()], key=len, reverse=True):
        if secret:
            detail = detail.replace(secret, '[redacted]')
    detail = re.sub(r'[A-Za-z]{0,2}[0-9a-fA-F]{32}', '[redacted]', detail)
    detail = re.sub(r'\+?\d{8,15}', '[number]', detail)
    detail = ' '.join(detail.split())[:500]
    return f'Twilio rejected the call (HTTP {result.status_code}{label}): {detail}'


class TwilioVoice:
    def __init__(self, transport=None):
        self.transport = transport

    async def request(self, method, config, suffix='', data=None, account=False):
        sid = config['accountSid']
        resource = '' if account else '/Calls' + suffix
        url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}{resource}.json'
        async with httpx.AsyncClient(timeout=15, transport=self.transport, follow_redirects=False) as client:
            return await client.request(method, url, auth=(sid, config['authToken']), data=data)

    async def account_type(self, config):
        # Read before dispatch; never discover trial mode by retrying a POST.
        try:
            result = await self.request('GET', config, account=True)
            if 400 <= result.status_code < 500:
                raise CallRejected(rejection_detail(result, config))
            result.raise_for_status()
            value = result.json()
            if not isinstance(value, dict) or value.get('type') not in {'Trial', 'Full'}:
                raise ValueError('Unknown account type')
            if value.get('status') != 'active':
                raise CallRejected('Twilio account is not active. No call was attempted.')
            return value['type']
        except (httpx.HTTPError, ValueError, TypeError):
            raise CallRejected('Could not verify the Twilio account before calling. No call was attempted. Check your connection and account settings.') from None

    async def create(self, config, message):
        trial = await self.account_type(config) == 'Trial'
        response = Element('Response')
        SubElement(response, 'Say', {'language': 'en-US'}).text = 'Hi, this is AIRA. ' + message
        SubElement(response, 'Hangup')
        try:
            data = {'To': config['toNumber'], 'From': config['fromNumber']}
            if trial:
                # New trials allow template URLs, but reject inline Twiml and
                # extra call options (even Record=false). No custom speech here.
                data['Url'] = 'https://webhooks.twilio.com/v1/Voice/Template/voice_text_to_speech'
            else:
                data.update({
                'Twiml': tostring(response, encoding='unicode'), 'Timeout': '30',
                'TimeLimit': '60', 'Record': 'false',
                })
            result = await self.request('POST', config, data=data)
            if 400 <= result.status_code < 500:
                raise CallRejected(rejection_detail(result, config))
            result.raise_for_status()
            value = result.json()
            if not isinstance(value, dict) or not re.fullmatch(r'CA[0-9a-fA-F]{32}', value.get('sid', '')):
                raise ValueError('No valid call SID')
            return AcceptedCall(value['sid'], 'trial-demo' if trial else 'reminder')
        except CallRejected:
            raise
        except (httpx.HTTPError, ValueError, TypeError):
            raise CallUncertain('Call outcome is unknown. Check Twilio Voice logs before scheduling another call; AIRA will not retry automatically.') from None

    async def status(self, config, sid):
        if not isinstance(sid, str) or not re.fullmatch(r'CA[0-9a-fA-F]{32}', sid):
            raise ValueError('Invalid call SID.')
        result = await self.request('GET', config, '/' + sid)
        result.raise_for_status()
        value = result.json().get('status')
        if value not in {'queued', 'ringing', 'in-progress', 'completed', 'busy', 'failed', 'no-answer', 'canceled'}:
            raise ValueError('Unknown call status.')
        return value
