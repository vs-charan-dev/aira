"""SQLite repositories retaining upstream records/relationships in JSON.

Connections run in worker threads. Atomic updates use BEGIN IMMEDIATE.
Only the upstream-used document operations are supported; no cloud SDK.
"""
import asyncio
import copy
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from app.config import settings

@dataclass
class Increment:
    value: int

@dataclass
class ArrayUnion:
    values: list

def _encode(value):
    if isinstance(value, datetime):
        return {'__aira_datetime__': value.isoformat()}
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f'Unsupported stored value: {type(value)}')

def _decode(value):
    if set(value) == {'__aira_datetime__'}:
        return datetime.fromisoformat(value['__aira_datetime__'])
    return value

def connect():
    db_path = settings.aira_data_dir / 'db' / 'aira.sqlite3'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, timeout=10)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')
    con.execute('CREATE TABLE IF NOT EXISTS documents (path TEXT PRIMARY KEY, parent TEXT NOT NULL, body TEXT NOT NULL)')
    con.execute('CREATE INDEX IF NOT EXISTS documents_parent ON documents(parent)')
    con.execute('PRAGMA user_version=1')
    return con

def initialize_store():
    con = connect()
    con.close()

def _segment(value):
    if not value or '/' in value or value in ('.', '..'):
        raise ValueError('Invalid record ID')
    return value

class Snapshot:
    def __init__(self, path, data):
        self.id = path.rsplit('/', 1)[-1]
        self.path = path
        self.exists = data is not None
        self._data = data

    def to_dict(self):
        return copy.deepcopy(self._data)

class Document:
    def __init__(self, path):
        self.path = path

    def collection(self, name):
        return Collection(f'{self.path}/{_segment(name)}')

    async def get(self):
        def read():
            con = connect()
            try:
                row = con.execute('SELECT body FROM documents WHERE path=?', (self.path,)).fetchone()
                return Snapshot(self.path, json.loads(row[0], object_hook=_decode) if row else None)
            finally:
                con.close()
        return await asyncio.to_thread(read)

    async def set(self, data, merge=False):
        await asyncio.to_thread(self._write, data, merge, False)

    async def update(self, data):
        await asyncio.to_thread(self._write, data, True, True)

    def _write(self, data, merge, must_exist):
        con = connect()
        try:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('SELECT body FROM documents WHERE path=?', (self.path,)).fetchone()
            if must_exist and not row:
                raise KeyError(f'Record missing: {self.path}')
            body = json.loads(row[0], object_hook=_decode) if row and merge else {}
            for field, value in data.items():
                if isinstance(value, Increment):
                    body[field] = body.get(field, 0) + value.value
                elif isinstance(value, ArrayUnion):
                    values = list(body.get(field, []))
                    for item in value.values:
                        if item not in values:
                            values.append(item)
                    body[field] = values
                else:
                    body[field] = value
            con.execute('INSERT INTO documents VALUES (?, ?, ?) ON CONFLICT(path) DO UPDATE SET body=excluded.body',
                        (self.path, self.path.rsplit('/', 1)[0], json.dumps(body, default=_encode)))
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    async def delete(self):
        def remove():
            con = connect()
            try:
                with con:
                    con.execute('DELETE FROM documents WHERE path=? OR substr(path,1,?)=?',
                                (self.path, len(self.path) + 1, self.path + '/'))
            finally:
                con.close()
        await asyncio.to_thread(remove)

class Collection:
    def __init__(self, path, filters=(), ordering=None, cap=None, cursor=None, fields=None):
        self.path, self.filters, self.ordering = path, filters, ordering
        self.cap, self.cursor, self.fields = cap, cursor, fields

    def document(self, name):
        return Document(f'{self.path}/{_segment(name)}')

    def _clone(self, **kwargs):
        args = dict(path=self.path, filters=self.filters, ordering=self.ordering,
                    cap=self.cap, cursor=self.cursor, fields=self.fields)
        return Collection(**(args | kwargs))

    def where(self, field, op, value):
        if op != '==':
            raise ValueError('Only equality filters supported')
        return self._clone(filters=(*self.filters, (field, value)))

    def order_by(self, field, direction='ASCENDING'):
        return self._clone(ordering=(field, direction == 'DESCENDING'))

    def limit(self, value):
        return self._clone(cap=value)

    def start_after(self, snap):
        return self._clone(cursor=snap.id)

    def select(self, fields):
        return self._clone(fields=fields)

    async def get(self):
        def read():
            con = connect()
            try:
                rows = con.execute('SELECT path, body FROM documents WHERE parent=? ORDER BY path', (self.path,)).fetchall()
            finally:
                con.close()
            docs = [Snapshot(path, json.loads(body, object_hook=_decode)) for path, body in rows]
            docs = [d for d in docs if all(d._data.get(k) == v for k, v in self.filters)]
            if self.ordering:
                key, reverse = self.ordering
                docs = [d for d in docs if d._data.get(key) is not None]
                docs.sort(key=lambda d: (d._data[key], d.id), reverse=reverse)
            if self.cursor:
                idx = next((i for i, d in enumerate(docs) if d.id == self.cursor), None)
                if idx is not None:
                    docs = docs[idx + 1:]
            if self.cap is not None:
                docs = docs[:self.cap]
            if self.fields is not None:
                for d in docs:
                    d._data = {k: v for k, v in d._data.items() if k in self.fields}
            return docs
        return await asyncio.to_thread(read)

class Store:
    def collection(self, name):
        return Collection(_segment(name))

def get_store():
    return Store()
