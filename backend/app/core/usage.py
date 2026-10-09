"""Local usage ledger. Stores counters only, never API keys or request content.

Rates are a dated Standard paid-tier estimate, not the user's Google bill.
Live snapshots replace earlier snapshots within a turn; retained input context
is counted again on subsequent turns. Streaming text uses the final snapshot.
"""
import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
import logging
import time
import uuid

from app.config import settings
from app.core.local_store import get_store

logger = logging.getLogger(__name__)
RATE_DATE = '2026-10-06'
RATE_SOURCE = 'https://ai.google.dev/gemini-api/docs/pricing'
scope = ContextVar('aira_usage_scope', default=('local', 'other', None))


@contextmanager
def usage_scope(user_id='local', feature='other', group_id=None):
    token = scope.set((user_id, feature, group_id))
    try:
        yield
    finally:
        scope.reset(token)


def _field(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


def _count(obj, name):
    value = _field(obj, name)
    return max(0, value) if isinstance(value, int) else 0


def _details(obj, name):
    result = {}
    for item in _field(obj, name, None) or []:
        modality = _field(item, 'modality', 'UNKNOWN')
        modality = str(getattr(modality, 'value', modality)).upper()
        result[modality] = result.get(modality, 0) + _count(item, 'token_count')
    return result


def normalize_usage(meta, *, text_only=False):
    """Whitelist SDK fields; ignore arbitrary/raw response contents."""
    if meta is None:
        return None
    output_field = 'response_token_count' if _field(meta, 'response_token_count') is not None else 'candidates_token_count'
    input_details = _details(meta, 'prompt_tokens_details')
    output_details = _details(meta, 'response_tokens_details') or _details(meta, 'candidates_tokens_details')
    tool_details = _details(meta, 'tool_use_prompt_tokens_details')
    for details, total in ((input_details, _count(meta, 'prompt_token_count')),
                           (output_details, _count(meta, output_field)),
                           (tool_details, _count(meta, 'tool_use_prompt_token_count'))):
        remainder = max(0, total - sum(details.values()))
        if remainder:
            key = 'TEXT' if text_only else 'UNKNOWN'
            details[key] = details.get(key, 0) + remainder
    return {'input': input_details, 'output': output_details, 'tool': tool_details,
            'cached': _details(meta, 'cache_tokens_details'),
            'cachedCount': _count(meta, 'cached_content_token_count'),
            'thoughts': _count(meta, 'thoughts_token_count'),
            'total': _count(meta, 'total_token_count')}


def estimate(model, snapshots):
    """Unknown models/modalities are explicitly unpriced, never silently zero."""
    if model == 'gemini-3.8-live':
        inputs, outputs, cache_rate = {'TEXT': .75, 'AUDIO': 3., 'IMAGE': 1., 'VIDEO': 1.}, {'TEXT': 4.5, 'AUDIO': 12.}, None
    elif model == 'gemini-3.8-flash':
        # This promotional Standard rate expires on 2026-12-31.
        multiplier = 1 if datetime.now(UTC).date().isoformat() <= '2026-12-31' else 2
        inputs, outputs, cache_rate = {'TEXT': .75 * multiplier}, {'TEXT': 3.75 * multiplier}, .075 * multiplier
    elif model == 'gemini-2.5-flash-image':
        inputs, outputs, cache_rate = {'TEXT': .3, 'IMAGE': .3}, {'TEXT': 2.5, 'IMAGE': 30.}, None
    elif model == 'gemini-embedding-001':
        # Historical model's published rate; response may omit usage entirely.
        inputs, outputs, cache_rate = {'TEXT': .15}, {}, None
    else:
        inputs, outputs, cache_rate = {}, {}, None
    cost, unpriced, tokens = 0., 0, 0
    breakdown = {'input': {}, 'output': {}, 'tool': {}, 'thoughts': 0, 'cached': 0}
    for sample in snapshots:
        tokens += sample['total']
        for direction, prices in (('input', inputs), ('tool', inputs), ('output', outputs)):
            for modality, count in sample[direction].items():
                breakdown[direction][modality] = breakdown[direction].get(modality, 0) + count
                if modality not in prices:
                    unpriced += count
                else:
                    cost += count * prices[modality] / 1_000_000
        thoughts = sample['thoughts']
        breakdown['thoughts'] += thoughts
        if 'TEXT' in outputs:
            cost += thoughts * outputs['TEXT'] / 1_000_000
        else:
            unpriced += thoughts
        cached = min(sample['cachedCount'], sample['input'].get('TEXT', 0))
        breakdown['cached'] += sample['cachedCount']
        if cache_rate is not None:
            cost -= cached * (inputs['TEXT'] - cache_rate) / 1_000_000
        elif sample['cachedCount']:
            # Live cached-input discount is not assumed.
            unpriced += sample['cachedCount']
    return {'estimatedUsd': round(max(0., cost), 8) if snapshots else None,
            'unpricedTokens': unpriced, 'tokens': tokens, 'breakdown': breakdown,
            'estimateComplete': bool(snapshots) and unpriced == 0 and bool(inputs)}


def usage_collection(user_id):
    return get_store().collection('users').document(user_id).collection('apiUsage')


class UsageRun:
    def __init__(self, model, kind):
        self.user_id, self.feature, self.group_id = scope.get()
        self.id = uuid.uuid4().hex
        self.model, self.kind = model.removeprefix('models/'), kind
        self.started = time.monotonic()
        self.samples = {}
        self.events = 0
        self.status = 'active'
        self.stop_reason = None
        self.lock = asyncio.Lock()
        self.body = {'id': self.id, 'feature': self.feature, 'groupId': self.group_id,
                     'model': self.model, 'kind': kind, 'startedAt': datetime.now(UTC).isoformat(),
                     'rateDate': RATE_DATE, 'liveUsageMode': settings.aira_live_usage_mode if kind == 'live' else None}

    async def save(self):
        async with self.lock:
            self.body.update(estimate(self.model, list(self.samples.values())))
            if self.body.get('possibleExtraCharges'):
                self.body['estimateComplete'] = False
            self.body.update(status=self.status, stopReason=self.stop_reason,
                             elapsedSeconds=round(time.monotonic() - self.started, 1),
                             usageEvents=self.events, usageAvailable=bool(self.samples),
                             snapshots=list(self.samples.values()))
            try:
                await usage_collection(self.user_id).document(self.id).set(self.body)
            except Exception:
                # Meter failure must not lose the user's memory/voice session.
                logger.error('Could not persist usage counters for run %s', self.id)

    async def observe(self, meta, slot=0, *, text_only=False):
        sample = normalize_usage(meta, text_only=text_only)
        if sample is None:
            return
        self.samples[slot] = sample
        self.events += 1
        await self.save()

    async def finish(self, status='completed'):
        self.status = status
        self.body['endedAt'] = datetime.now(UTC).isoformat()
        await self.save()


async def recover_usage():
    # A terminated process cannot report final provider usage. Preserve counters.
    for snap in await usage_collection('local').where('status', '==', 'active').get():
        await usage_collection('local').document(snap.id).update({'status': 'interrupted', 'stopReason': 'backend_restart'})


async def usage_summary(user_id):
    records = [s.to_dict() for s in await usage_collection(user_id).order_by('startedAt', direction='DESCENDING').get()]
    return {'estimatedUsd': round(sum(r.get('estimatedUsd') or 0 for r in records), 8),
            'calls': len(records), 'incompleteCalls': sum(not r.get('estimateComplete', False) for r in records),
            'activeCalls': sum(r['status'] == 'active' for r in records),
            'records': [{k: v for k, v in r.items() if k != 'snapshots'} for r in records[:30]],
            'rateDate': RATE_DATE, 'rateSource': RATE_SOURCE,
            'liveUsageMode': settings.aira_live_usage_mode,
            'limits': {'idleSeconds': settings.aira_live_idle_seconds, 'maxSeconds': settings.aira_live_max_seconds,
                       'maxEstimatedUsd': settings.aira_live_max_estimated_usd}}
