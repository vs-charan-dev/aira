"""A disposable E-drive showcase; fixed Node preview, never model-authored shell."""
import asyncio
import hashlib
import json
import math
import secrets
import shutil
import stat
from app.core.invoice_presentation import REGRESSION_FILE, REGRESSION_SOURCE, validate_task
from pathlib import Path
from app.config import ROOT, settings
from app.services.coding_worker import environment, terminate

FILES = ('invoice.js', 'invoice.test.js', 'package.json', 'README.md')
MARKER = '.aira-invoice-demo.json'
SCHEMA = 'aira-invoice-demo-v1'
TEMPLATE = ROOT / 'demo' / 'invoice-showcase'
# The worker edits invoice.js. Only this fixed program evaluates its exported
# function. No project JS runs in the browser or Electron renderer.
PREVIEW = """import {pathToFileURL} from 'node:url';
let input=''; for await (const chunk of process.stdin) input+=chunk;
const {path,price,discount}=JSON.parse(input);
const {invoiceTotal}=await import(pathToFileURL(path).href);
const total=await invoiceTotal(price,discount);
if(typeof total!=='number' || !Number.isFinite(total)) throw Error('Expected a finite numeric total');
console.log('AIRA_PREVIEW_RESULT:'+JSON.stringify({total}));
"""


def folder():
    return settings.aira_data_dir / 'projects' / 'invoice-showcase'


def safe_path(path):
    # resolve() alone would hide junctions. Reject every existing reparse point.
    for part in (path, *path.parents):
        if part.exists() and (part.is_symlink() or getattr(part.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError('The invoice demo cannot use linked files or folders.')
    return path


def metadata():
    target = safe_path(folder())
    marker = safe_path(target / MARKER)
    try:
        if marker.stat().st_size > 1024: raise ValueError('Invalid invoice demo marker.')
        value = json.loads(marker.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None
    except (ValueError, OSError):
        raise ValueError('Invoice demo marker is invalid. Existing files were preserved.') from None
    if value.get('schema') != SCHEMA or not isinstance(value.get('generation'), str) or len(value['generation']) != 32:
        raise ValueError('Invoice demo marker is invalid. Existing files were preserved.')
    return value


def version():
    target = safe_path(folder() / 'invoice.js')
    if not target.is_file() or target.stat().st_size > 100000:
        raise ValueError('The invoice module is missing or exceeds 100 KB.')
    return hashlib.sha256(target.read_bytes()).hexdigest()


def status():
    info = metadata()
    return {'ready': info is not None, 'path': str(folder()), 'generation': info['generation'] if info else None,
            'version': version() if info else None, 'nodeInstalled': shutil.which('node') is not None,
            'repairMode':settings.aira_invoice_repair_mode}


def prepare(reset=False):
    target = safe_path(folder())
    info = metadata()
    if target.exists() and not info:
        raise ValueError('The invoice-showcase folder is not managed by AIRA. Existing files were preserved.')
    if info and not reset:
        return status()
    # Reset only a recognized, dedicated fixture. Unexpected files are preserved
    # and cause refusal rather than deleting or overwriting somebody's project.
    if target.exists() and set(p.name for p in target.iterdir()) - set(FILES) - {MARKER, REGRESSION_FILE, '.vscode'}:
        raise ValueError('The demo contains extra files. Preserve them elsewhere before resetting.')
    for name in FILES:
        safe_path(target / name)
    sources = {name: (TEMPLATE / name).read_bytes() for name in FILES}
    clear_presentation()
    target.mkdir(parents=True, exist_ok=True)
    for name, content in sources.items():
        (target / name).write_bytes(content)
    (target / MARKER).write_text(json.dumps({'schema': SCHEMA, 'generation': secrets.token_hex(16)}), encoding='utf-8')
    return status()


def clear_presentation():
    """Remove only recognized generated artifacts, so each rehearsal writes fresh tests."""
    test = safe_path(folder() / REGRESSION_FILE)
    directory = safe_path(folder() / '.vscode')
    task = safe_path(directory / 'tasks.json')
    if test.exists() and (test.stat().st_size > 10000 or test.read_text(encoding='utf-8') != REGRESSION_SOURCE):
        raise ValueError('The generated regression file changed. Existing files were preserved.')
    if directory.exists():
        if not directory.is_dir() or {p.name for p in directory.iterdir()} != {'tasks.json'} or task.stat().st_size > 8000:
            raise ValueError('Existing VS Code configuration was preserved.')
        validate_task(ROOT, shutil.which('node'), json.loads(task.read_text(encoding='utf-8')))
    if test.exists(): test.unlink()
    if task.exists(): task.unlink(); directory.rmdir()


def generation_for(project):
    if Path(project['path']).resolve() != folder().resolve(): return None
    info = metadata()
    return info['generation'] if info else None


async def evaluate(price, discount, expected_version):
    for value in (price, discount):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Use finite numbers for the price and discount.')
    if not 0 <= price <= 1000000 or not 0 <= discount <= 100:
        raise ValueError('Use price 0–1000000 and discount 0–100.')
    if not metadata(): raise ValueError('Prepare the invoice demo first.')
    current = version()
    if current != expected_version: raise ValueError('The source changed. Refresh the preview.')
    node = shutil.which('node')
    if not node: raise ValueError('Node.js is not installed. Use the AIRA setup runtime.')
    env = environment('', folder()); env.pop('GOOGLE_GENERATIVE_AI_API_KEY', None)
    process = await asyncio.create_subprocess_exec(node, '--input-type=module', '-e', PREVIEW, cwd=folder(), env=env,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    async def read():
        process.stdin.write(json.dumps({'path': str(folder() / 'invoice.js'), 'price': price, 'discount': discount}).encode())
        await process.stdin.drain(); process.stdin.close()
        output = bytearray()
        while chunk := await process.stdout.read(4096):
            output.extend(chunk)
            if len(output) > 20000: raise ValueError('Invoice preview exceeded its output limit.')
        await process.wait()
        return output.decode('utf-8', errors='replace')
    try:
        output = await asyncio.wait_for(read(), 5)
    except asyncio.TimeoutError:
        raise ValueError('Invoice preview timed out. Inspect the module.') from None
    finally:
        if process.returncode is None: await terminate(process)
    if current != version(): raise ValueError('The source changed. Refresh the preview.')
    if process.returncode != 0: raise ValueError('Invoice preview failed: ' + output[-1500:])
    try:
        line = next(line for line in reversed(output.splitlines()) if line.startswith('AIRA_PREVIEW_RESULT:'))
        total = json.loads(line.removeprefix('AIRA_PREVIEW_RESULT:'))['total']
        if isinstance(total, bool) or not isinstance(total, (int, float)) or not math.isfinite(total): raise ValueError()
    except (StopIteration, KeyError, ValueError):
        raise ValueError('The invoice module did not return a numeric total.') from None
    expected = price * (1 - discount / 100)
    return {'version': current, 'total': total, 'expected': expected, 'matches': math.isclose(total, expected, abs_tol=1e-8),
            'command': 'node --input-type=module · invoice.js preview'}
