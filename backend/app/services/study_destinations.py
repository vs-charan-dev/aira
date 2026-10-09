"""Resolve explicit export requests from owned, complete local study artifacts."""
import re
from urllib.parse import urlparse
from app.core.local_media import resolve_media
from app.core.youtube import canonical_video


def notebook_url(value):
    if not isinstance(value, str) or len(value) > 1000:
        raise ValueError('Provide a NotebookLM notebook URL.')
    uri = urlparse(value.strip())
    if (uri.scheme != 'https' or uri.hostname not in ('notebooklm.google.com', 'notebook.google.com')
            or uri.username or uri.password or uri.port not in (None, 443)
            or not re.fullmatch(r'/notebook/[a-zA-Z0-9_-]{1,100}/?', uri.path)):
        raise ValueError('Use an HTTPS NotebookLM notebook link, not an account or unrelated page.')
    return f'https://{uri.hostname}{uri.path}'


def export_summary(store, user, args):
    ident = args.get('study_task_id')
    if ident:
        row = store.get(user, ident)
    else:
        # Do not fall back to an older summary while the latest one is pending.
        row = next((r for r in store.list(user) if r['tool'] == 'youtube_study'
                    and r.get('action', {}).get('output') in ('summary', 'both')), None)
    if not row or row['tool'] != 'youtube_study':
        raise ValueError('Create a video summary first, or select its study task ID.')
    report = row.get('report') or {}
    if row['status'] != 'succeeded' or not report.get('assets', {}).get('summary'):
        raise ValueError('That video summary is not ready. Check its task result before exporting.')
    if not re.fullmatch(r'[a-f0-9]{10}', row['id']):
        raise ValueError('Invalid study task ID.')
    path = resolve_media('youtube/jobs/' + row['id'] + '/summary.md')
    if not path.is_file() or path.stat().st_size > 100000:
        raise ValueError('The saved summary is missing or too large. Nothing was exported.')
    content = path.read_text(encoding='utf-8')
    if not content.strip() or len(content) > 20000 or re.search(r'[\x00-\x08\x0b-\x1f\x7f]', content):
        raise ValueError('The complete summary must contain 1–20000 plain-text characters. It was not truncated.')
    # Keep every paragraph, URL and caveat, removing presentation syntax only.
    # Literal Markdown typed into Notion can invoke its editor shortcuts.
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.M)
    content = re.sub(r'^[-*]\s+', '• ', content, flags=re.M)
    content = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 (\2)', content)
    content = re.sub(r'\*\*([^\n]+?)\*\*', r'\1', content)
    destination = args.get('destination', 'new')
    if destination not in ('new', 'existing'):
        raise ValueError('Choose a new or existing Notion page.')
    title = args.get('title') or (report.get('videoTitle') or 'YouTube summary')[:160]
    page_name = args.get('page_name', '')
    if not isinstance(title, str) or not title.strip() or len(title) > 160 or re.search(r'[\x00-\x1f\x7f]', title):
        raise ValueError('Use a one-line Notion title of 1–160 characters.')
    if not isinstance(page_name, str) or len(page_name) > 160 or re.search(r'[\x00-\x1f\x7f]', page_name):
        raise ValueError('Use an exact existing page title, or leave it empty for the selected page.')
    if destination == 'new' and page_name:
        raise ValueError('A target page name is for existing-page exports only.')
    _, source = canonical_video(report.get('sourceUrl'))
    return {'kind': 'export_summary_to_notion', 'destination': destination, 'title': title.strip(),
            'pageName': page_name.strip(), 'content': content, 'studyTaskId': row['id'], 'videoUrl': source}


def mindmap_action(args):
    uri = notebook_url(args['notebook_url']) if args.get('notebook_url') else None
    new = args.get('new_notebook', not bool(uri))
    if not isinstance(new, bool) or (new and uri):
        raise ValueError('Choose either a new notebook or an existing notebook link.')
    action = {'kind': 'notebooklm_mindmap', 'newNotebook': new}
    if uri: action['notebookUrl'] = uri
    if args.get('video_url'):
        _, action['videoUrl'] = canonical_video(args['video_url'])
    return action
