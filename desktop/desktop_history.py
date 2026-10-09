"""Local task/action metadata; never store provider keys, screen trees or reasoning."""
import json
from contextlib import contextmanager
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

class History:
    def __init__(self, request_id, action, root=ROOT):
        self.request_id = request_id
        db = root / 'data' / 'db' / 'desktop-actions.sqlite3'
        db.parent.mkdir(parents=True, exist_ok=True)
        self.db = db
        with self.connect() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, started REAL, finished REAL, action TEXT, status TEXT, message TEXT, input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0)')
            con.execute('CREATE TABLE IF NOT EXISTS steps (task_id TEXT, seq INTEGER, at REAL, tool TEXT, status TEXT, PRIMARY KEY(task_id,seq))')
            columns = {row[1] for row in con.execute('PRAGMA table_info(tasks)')}
            if 'timings' not in columns:
                try: con.execute('ALTER TABLE tasks ADD COLUMN timings TEXT')
                except sqlite3.OperationalError:
                    if 'timings' not in {row[1] for row in con.execute('PRAGMA table_info(tasks)')}:
                        raise
            con.execute('INSERT OR IGNORE INTO tasks(id,started,action,status) VALUES(?,?,?,?)', (request_id, time.time(), json.dumps(action, ensure_ascii=False), 'running'))
    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.db, timeout=5)
        try:
            with con:
                yield con
        finally:
            con.close()
    def step(self, tool, status):
        with self.connect() as con:
            seq = con.execute('SELECT COALESCE(MAX(seq),0)+1 FROM steps WHERE task_id=?', (self.request_id,)).fetchone()[0]
            con.execute('INSERT INTO steps VALUES(?,?,?,?,?)', (self.request_id, seq, time.time(), str(tool)[:50], str(status)[:30]))
    def finish(self, status, message, input_tokens=0, output_tokens=0, timings=None):
        with self.connect() as con:
            con.execute('UPDATE tasks SET finished=COALESCE(finished,?),status=?,message=?,input_tokens=MAX(input_tokens,?),output_tokens=MAX(output_tokens,?),timings=COALESCE(?,timings) WHERE id=?',
                        (time.time(), status, str(message)[:400], input_tokens, output_tokens, json.dumps(timings) if timings else None, self.request_id))

if __name__ == '__main__':
    import sys
    value = json.loads(sys.stdin.readline(20000))
    if value.get('status') not in ('succeeded', 'failed', 'cancelled'):
        raise ValueError('Invalid result')
    History(value['requestId'], value['action']).finish(value['status'], value['message'],timings=value.get('timings'))
