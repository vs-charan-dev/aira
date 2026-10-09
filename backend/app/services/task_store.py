"""Small durable local job ledger. No automatic replay after a restart."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from app.config import settings


class TaskStore:
    def __init__(self, path: Path | None = None):
        self.path = path or settings.aira_data_dir / 'db' / 'tasks.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, user TEXT NOT NULL, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS config (user TEXT PRIMARY KEY, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS video_config (user TEXT PRIMARY KEY, body TEXT NOT NULL)')
            # Persisted work is historical, never permission to retry a partial action.
            for ident, body in db.execute('SELECT id, body FROM jobs').fetchall():
                row = json.loads(body)
                if row['status'] in ('queued', 'running'):
                    row['partial']=row.get('partial',False) or row['status']=='running'
                    row.update(status='needs_attention', progress='AIRA restarted. Inspect partial changes before resuming.')
                    db.execute('UPDATE jobs SET body=? WHERE id=?', (json.dumps(row), ident))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            db.execute('PRAGMA journal_mode=WAL')
            with db: yield db
        finally: db.close()

    def save(self, job):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?)', (job['id'], job['user'], json.dumps(job)))

    def get(self, user, ident):
        with self.connect() as db:
            row = db.execute('SELECT body FROM jobs WHERE user=? AND id=?', (user, ident)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, user):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM jobs WHERE user=?', (user,)).fetchall()
        return sorted((json.loads(r[0]) for r in rows), key=lambda r: r['createdAt'], reverse=True)

    def config(self, user):
        with self.connect() as db:
            row = db.execute('SELECT body FROM config WHERE user=?', (user,)).fetchone()
        return json.loads(row[0]) if row else {'path': str(settings.aira_data_dir / 'projects' / 'aira-demo'), 'runner': 'node'}

    def set_config(self, user, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO config VALUES (?,?)', (user, json.dumps(value)))

    def video_config(self,user):
        from app.services.youtube_study import SUMMARY_MODELS,IMAGE_MODELS
        default={'summaryModel':settings.aira_youtube_summary_model,'imageModel':settings.aira_youtube_image_model}
        with self.connect() as db:
            found=db.execute('SELECT body FROM video_config WHERE user=?',(user,)).fetchone()
        value=json.loads(found[0]) if found else default
        if value['summaryModel'] not in SUMMARY_MODELS or value['imageModel'] not in IMAGE_MODELS:
            raise ValueError('Choose supported YouTube models in the task board.')
        return value

    def set_video_config(self,user,value):
        from app.services.youtube_study import SUMMARY_MODELS,IMAGE_MODELS
        if value.get('summaryModel') not in SUMMARY_MODELS or value.get('imageModel') not in IMAGE_MODELS:
            raise ValueError('Choose supported YouTube models.')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO video_config VALUES (?,?)',(user,json.dumps({k:value[k] for k in ('summaryModel','imageModel')})))
