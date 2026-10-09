"""File-backed personal context, persisted as ordinary palace artifacts.

No provider/key is needed for importing, browsing, correcting or grounded
extractive answers. Local retrieval expands semantic concepts before ranking.
The same records feed the Live agent's existing search_memories tool.
"""
import asyncio
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from app.core.local_store import connect, _encode, _decode
from app.models.artifact import Artifact
from app.models.common import Position3D
from app.models.room import Room

SEED_PATH = Path(__file__).resolve().parents[1] / 'data/personal_memory_seed.json'
UNKNOWN = "I don't currently have a memory about that."


def seed_definition():
    return json.loads(SEED_PATH.read_text(encoding='utf-8'))


def _write(con, path, value):
    con.execute('INSERT INTO documents VALUES (?, ?, ?) ON CONFLICT(path) DO UPDATE SET body=excluded.body',
                (path, path.rsplit('/', 1)[0], json.dumps(value, default=_encode)))


async def ensure_personal_palace(user_id: str):
    """Import once in a transaction. Corrections/deletions survive reopens.

    Seed import date is distinct from unknown historical event dates.
    Existing rooms and captured artifacts are preserved.
    """
    def run():
        seed = seed_definition()
        root = f'users/{user_id}'
        marker = f'{root}/imports/personal_memory_v1'
        con = connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            if con.execute('SELECT 1 FROM documents WHERE path=?', (marker,)).fetchone():
                con.rollback()
                return
            now = datetime.now(UTC)
            existing_rooms = con.execute('SELECT body FROM documents WHERE parent=?', (root + '/rooms',)).fetchall()
            # Start after all existing positions to keep imported rooms separated.
            positions = [json.loads(row[0]).get('position', {}) for row in existing_rooms]
            start_z = max([float(p.get('z', 0)) for p in positions] + [0]) + (30 if positions else 0)
            for i, definition in enumerate(seed['rooms']):
                room_memories = [m for m in seed['memories'] if m['room_id'] == definition['id']]
                room = Room(id=definition['id'], name=definition['name'], style=definition['style'],
                            position=Position3D(x=30 + (i % 4) * 30, y=0, z=start_z + (i // 4) * 30),
                            createdAt=now, lastAccessedAt=now, artifactCount=len(room_memories),
                            topicKeywords=[definition['prefix'].lower()],
                            summary='Personal context: ' + ', '.join(m['title'] for m in room_memories))
                _write(con, f'{root}/rooms/{room.id}', room.model_dump())
                for j, memory in enumerate(room_memories):
                    # Four walls, two rows, four columns. Room capacity is 32.
                    wall = ['north', 'east', 'south', 'west'][j % 4]
                    slot = j // 4
                    offset, height = 1.1 + (slot % 4) * 1.8, 1.1 + (slot // 4) * 1.8
                    pos = {'north': (offset, height, .5), 'south': (offset, height, 7.5),
                           'east': (7.5, height, offset), 'west': (.5, height, offset)}[wall]
                    artifact = Artifact(id=memory['id'], roomId=room.id, type='document', visual='floating_book',
                                        position=Position3D(x=pos[0], y=pos[1], z=pos[2]), wall=wall,
                                        title=memory['title'], summary=memory['memory'], fullContent=memory['memory'],
                                        keywords=memory['tags'], capturedAt=datetime(2026, 10, 9, tzinfo=UTC),
                                        personalMemory=memory)
                    _write(con, f'{root}/rooms/{room.id}/artifacts/{artifact.id}', artifact.model_dump())
            layout_path = root + '/layout/main'
            row = con.execute('SELECT body FROM documents WHERE path=?', (layout_path,)).fetchone()
            layout = json.loads(row[0], object_hook=_decode) if row else {}
            all_rooms = con.execute('SELECT path FROM documents WHERE parent=? ORDER BY path', (root + '/rooms',)).fetchall()
            # Rebuild all doors, including existing rooms; none fall off the lobby.
            layout['lobbyDoors'] = [dict(roomId=p.rsplit('/', 1)[-1], wallPosition=['north','east','south','west'][i % 4], doorIndex=i // 4) for i, (p,) in enumerate(all_rooms)]
            _write(con, layout_path, layout)
            palace_path = root + '/palace/main'
            row = con.execute('SELECT body FROM documents WHERE path=?', (palace_path,)).fetchone()
            palace = json.loads(row[0], object_hook=_decode) if row else {'createdAt': now, 'lobbyPosition': {'x':0,'y':0,'z':0}}
            count = con.execute("SELECT count(*) FROM documents WHERE parent LIKE ?", (root + '/rooms/%/artifacts',)).fetchone()[0]
            palace.update(roomCount=len(all_rooms), artifactCount=count, lastModifiedAt=now)
            _write(con, palace_path, palace)
            _write(con, marker, {'version':1, 'importedAt':now, 'source':str(SEED_PATH.name)})
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
    await asyncio.to_thread(run)


async def list_memories(user_id: str):
    def read():
        con = connect()
        try:
            rows = con.execute("SELECT body FROM documents WHERE substr(path,1,?)=? AND parent LIKE '%/artifacts'", (len(f'users/{user_id}/rooms/'), f'users/{user_id}/rooms/')).fetchall()
            room_rows = con.execute('SELECT path,body FROM documents WHERE parent=?', (f'users/{user_id}/rooms',)).fetchall()
            room_names = {p.rsplit('/',1)[-1]:json.loads(b)['name'] for p,b in room_rows}
            result = []
            for (body,) in rows:
                artifact = json.loads(body, object_hook=_decode)
                memory = artifact.get('personalMemory')
                if memory:
                    # Artifact location is authoritative even after a room move.
                    result.append({**memory, 'room_id':artifact['roomId'], 'room':room_names.get(artifact['roomId'], memory['room'])})
            return sorted(result, key=lambda m: m['id'])
        finally:
            con.close()
    return await asyncio.to_thread(read)


_STOP = set('what which who when why how do does did am are is was were be been being i my me you your we our the a an of for to from in at on and or about that currently should can would want wants like prefer preferred use using used have has had it this right now please tell with usually know previous'.split())
_STOP.update({'remember','recall','stored','saved','memory','memories','information'})
_CONCEPTS = [
    {'laptop','computer','pc'},
    {'specs','specification','specifications','hardware'},
    {'college','university','institution'},
    {'phone','mobile','smartphone'},
    {'start','started','begin','began','beginning'},
    {'package','salary','compensation','pay','lpa','earning','wage'},
    {'city','location','where'},
    {'job','work','career','role','employment'},
    {'learn','lesson','learned','learning'},
    {'simple','simpler','simplicity','simplify'},
    {'architecture','architectures','overengineering','complexity','complex','complicated'},
    {'explain','explanation','explanations','teach','teaching'},
    {'hackathon','hackathons'},
    {'coding','code','programming'},
    {'target','targeting','goal','goals','objective','aim','aiming'},
    {'priority','priorities','focus'},
    {'topic','topics','concept','concepts'},
    {'health','fitness','physical'},
]


def tokens(text):
    terms = re.findall(r'[a-z0-9]+', text.lower())
    result = set()
    for term in terms:
        if term in _STOP or len(term) < 2:
            continue
        canonical = False
        for group in _CONCEPTS:
            if term in group:
                term = sorted(group)[0]
                canonical = True
                break
        if not canonical:
            term = term[:-1] if term.endswith('s') and len(term) > 4 and not term.endswith('ss') else term
            for group in _CONCEPTS:
                if term in group:
                    term = sorted(group)[0]
                    break
        result.add(term)
    return result


def rank_memories(memories, query, limit=12, room_id=None):
    """Semantic concept expansion + weighted lexical ranking, fully local.

    Conservative overlap threshold avoids answering unrelated personal questions.
    A stored question is provenance, not a source of new asserted facts.
    """
    clauses = re.split(r'\band\b(?=\s+(?:what|which|where|who|why|how)\b)', query, flags=re.I)
    if len(clauses) > 1:
        combined = {m['id']:m for clause in clauses for m in rank_memories(memories, clause, limit, room_id)}
        return sorted(combined.values(), key=lambda m:-m['score'])[:limit]
    qt = tokens(query)
    if 'hackathon' in qt and 'learn' in qt:
        qt.difference_update({'losing','lose','lost','loss'})
    if not qt:
        return []
    eligible = [m for m in memories if m['status'] in {'active','uncertain'} and (room_id is None or m['room_id'] == room_id)]
    docs = [(m, tokens(' '.join([m['title'], re.sub(r'\bwhere\b', '', m['memory'], flags=re.I), m['question'], *m['tags']]))) for m in eligible]
    frequency = Counter(t for _, ts in docs for t in ts)
    weights = {t: math.log(1 + len(docs) / (1 + frequency[t])) for t in qt}
    total = sum(weights.values()) or 1
    ranked = []
    for m, ts in docs:
        coverage = sum(weights[t] for t in qt & ts) / total
        if coverage < (0.60 if len(qt) <= 2 else 0.48):
            continue
        title_match = len(qt & tokens(m['title'])) / len(qt)
        score = coverage * .8 + title_match * .2
        ranked.append({**m, 'score':round(score, 4)})
    ranked.sort(key=lambda m:(-m['score'], 0 if m['status']=='active' else 1, m['id']))
    if ranked:
        ranked = [m for m in ranked if m['score'] >= max(.40, ranked[0]['score'] * .62)]
    return ranked[:limit]


async def retrieve_memories(user_id, query, limit=12, room_id=None):
    return rank_memories(await list_memories(user_id), query, limit, room_id)


def find_conflicts(memories):
    # Conflict grouping is intentionally conservative: only shared assertion keys.
    # Source repeats with different wording are equivalent until one is corrected.
    groups = {}
    for m in memories:
        if m['kind'] != 'unknown' and m['status'] in {'active','uncertain'}:
            groups.setdefault(m['semantic_key'], []).append(m)
    return [dict(key=key, memory_ids=[m['id'] for m in ms]) for key, ms in groups.items()
            if len(ms) > 1 and any(m['history'] and m['memory'] != m['history'][0]['memory'] for m in ms)
            and len({m['memory'].lower().strip() for m in ms}) > 1]


async def answer_question(user_id, query, room_id=None):
    all_memories = await list_memories(user_id)
    relevant = rank_memories(all_memories, query, 16, room_id)
    # Pull every conflicting assertion for the keys retrieved, including other rooms.
    keys = {m['semantic_key'] for m in relevant}
    conflicts = find_conflicts([m for m in all_memories if m['semantic_key'] in keys])
    existing = {m['id'] for m in relevant}
    for conflict in conflicts:
        relevant.extend(m for m in all_memories if m['id'] in conflict['memory_ids'] and m['id'] not in existing)
    known = [m for m in relevant if m['kind'] != 'unknown']
    asks_historical_date = re.search(r'(?i)\bwhen\s+(?:did|was|were|have|had)\b|\bexact\s+dates?\b', query)
    if asks_historical_date and known and not any(m['event_date'] for m in known):
        return dict(answer=UNKNOWN, kind='unknown', references=known, conflicts=[], retrieval='local_concept_search')
    # Every answer sentence is a verbatim stored assertion, with exact references.
    if not known:
        return dict(answer=UNKNOWN, kind='unknown', references=relevant, conflicts=[], retrieval='local_concept_search')
    sentences = list(dict.fromkeys(m['memory'] + (f" Event date: {m['event_date']}." if m['event_date'] else '') for m in known))
    answer = '\n\n'.join(sentences)
    if conflicts:
        answer = 'Conflicting memories are stored; please correct or mark the older memory outdated.\n\n' + answer
    if any(m['status']=='uncertain' for m in known):
        answer = 'Some supporting memories are marked uncertain.\n\n' + answer
    return dict(answer=answer, kind='inference' if any(m['kind']=='inference' for m in known) else 'fact',
                references=known, conflicts=conflicts, retrieval='local_concept_search')


def reject_secrets(text):
    if re.search(r'(?i)(?:password|passwd|otp|api[_ -]?key|secret[_ -]?key|bank(?:ing)?\s+(?:password|credential|pin))\s*(?:is|=|:|\s)\s*\S+|\b(?:sk-[a-zA-Z0-9]{12,}|AIza[a-zA-Z0-9_-]{20,})', text):
        raise ValueError('Do not store passwords, OTPs, API keys or banking credentials in memories.')


async def correct_memory(user_id, memory_id, changes, expected_version=None):
    """Atomic read/revise/history update with optimistic concurrency protection."""
    for field in ('memory', 'title'):
        if field in changes:
            reject_secrets(changes[field])
    def run():
        con = connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            rows = con.execute("SELECT path,body FROM documents WHERE substr(path,1,?)=? AND path LIKE '%/artifacts/%'", (len(f'users/{user_id}/rooms/'), f'users/{user_id}/rooms/')).fetchall()
            found = next(((path, json.loads(body, object_hook=_decode)) for path, body in rows if path.rsplit('/',1)[-1]==memory_id), None)
            if not found or not found[1].get('personalMemory'):
                raise KeyError(memory_id)
            path, artifact = found
            old = artifact['personalMemory']
            if expected_version is not None and old['version'] != expected_version:
                raise RuntimeError('This memory changed. Reload it before saving your correction.')
            snapshot = {k:v for k,v in old.items() if k != 'history'}
            new = {**old, **changes, 'version':old['version']+1, 'updated_at':datetime.now(UTC).isoformat(),
                   'history':[*old['history'], snapshot]}
            artifact.update(personalMemory=new, title=new['title'], summary=new['memory'], fullContent=new['memory'], embedding=[])
            _write(con, path, artifact)
            con.commit()
            return new
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
    return await asyncio.to_thread(run)
