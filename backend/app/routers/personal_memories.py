"""Authenticated browsing, grounded queries and audited corrections."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.middleware.auth import verify_token
from app.services.personal_memory_service import (
    list_memories, seed_definition, answer_question, retrieve_memories, correct_memory,
)

router = APIRouter(prefix='/api/v1/personal-memories', tags=['personal memories'])


class Question(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    room_id: str | None = None


class Correction(BaseModel):
    expected_version: int = Field(ge=1)
    memory: str | None = Field(default=None, min_length=1, max_length=4000)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    status: Literal['active','outdated','uncertain','superseded'] | None = None
    kind: Literal['fact','inference','unknown'] | None = None
    event_date: str | None = Field(default=None, pattern=r'^\d{4}-\d{2}-\d{2}$')


@router.get('')
async def browse(user=Depends(verify_token)):
    return {'rooms':seed_definition()['rooms'], 'memories':await list_memories(user['user_id'])}


@router.get('/search')
async def search(query: str = Query(min_length=1, max_length=1000), room_id: str | None = None, user=Depends(verify_token)):
    return {'memories':await retrieve_memories(user['user_id'], query, room_id=room_id)}


@router.post('/query')
async def ask(body: Question, user=Depends(verify_token)):
    return await answer_question(user['user_id'], body.query, body.room_id)


@router.patch('/{memory_id}')
async def correct(memory_id: str, body: Correction, user=Depends(verify_token)):
    changes = body.model_dump(exclude_unset=True, exclude={'expected_version'})
    if not changes or ('memory' in changes and not (changes['memory'] or '').strip()):
        raise HTTPException(422, 'Enter a memory correction.')
    if any(value is None for key,value in changes.items() if key != 'event_date'):
        raise HTTPException(422, 'Memory fields cannot be null.')
    if body.event_date:
        from datetime import date
        try:
            date.fromisoformat(body.event_date)
        except ValueError:
            raise HTTPException(422, 'Enter a valid event date.')
    try:
        return {'memory':await correct_memory(user['user_id'], memory_id, changes, body.expected_version)}
    except KeyError:
        raise HTTPException(404, 'Memory not found.')
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
