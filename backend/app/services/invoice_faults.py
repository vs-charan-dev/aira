"""Repeatable known-bug demo. No inference; actual source edits and Node checks."""
import difflib
import json
import os
import secrets
import sqlite3
import shutil
from contextlib import closing, contextmanager
from pathlib import Path
from app.config import ROOT, settings
from app.core.invoice_presentation import REGRESSION_FILE, REGRESSION_SOURCE, task_payload
from app.services import invoice_demo as demo
from app.services.coding_worker import run_tests

FIXED_SOURCE = ('// discountPercent is a percentage: 10 means a ten percent discount.\n'
                'export function invoiceTotal(price, discountPercent) {\n'
                '  return price - (price * discountPercent / 100);\n'
                '}\n')


@contextmanager
def lease():
    import msvcrt
    path = demo.safe_path(settings.aira_cache_dir / 'invoice-showcase.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size == 0: stream.write(b'0'); stream.flush()
        stream.seek(0)
        try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError: raise ValueError('The invoice demo is busy. Finish or cancel the running repair first.') from None
        try: yield
        finally:
            stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def assert_not_busy(except_id=None):
    path = settings.aira_data_dir / 'db' / 'tasks.sqlite3'
    if not path.exists(): return
    # Do not construct TaskStore: its restart recovery would alter live jobs.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
        rows = db.execute('SELECT body FROM jobs').fetchall()
    blocked = ('queued','running') if except_id is None else ('running',)
    if any(row.get('id') != except_id and row.get('lane') == 'coding' and row.get('status') in blocked
           for row in (json.loads(value[0]) for value in rows)):
        raise ValueError('A coding job is active. Finish or cancel it before changing the demo fault.')


def trusted_fixture():
    if not demo.metadata(): raise ValueError('Prepare the recognized invoice showcase first.')
    for name in ('invoice.test.js', 'package.json'):
        path = demo.safe_path(demo.folder() / name)
        if path.read_bytes() != (demo.TEMPLATE / name).read_bytes():
            raise ValueError('The independent demo tests or package configuration changed. No scripted fix applied.')
    regression = demo.safe_path(demo.folder() / REGRESSION_FILE)
    if regression.exists() and (regression.stat().st_size > 10000 or regression.read_text(encoding='utf-8') != REGRESSION_SOURCE):
        raise ValueError('The generated regression checks changed. Existing files were preserved.')


def source():
    path = demo.safe_path(demo.folder() / 'invoice.js')
    if path.stat().st_size > 100000: raise ValueError('The invoice source is too large.')
    return path.read_text(encoding='utf-8')


def write_source(value):
    target = demo.safe_path(demo.folder() / 'invoice.js')
    temporary = demo.safe_path(demo.folder() / '.invoice-repair.tmp')
    if temporary.exists(): raise ValueError('A previous temporary invoice file exists. Inspect it before retrying.')
    try:
        temporary.write_text(value, encoding='utf-8', newline='\n')
        os.replace(temporary, target)
    finally:
        if temporary.exists(): temporary.unlink()


def create_fault():
    with lease():
        assert_not_busy()
        demo.prepare()
        trusted_fixture()
        demo.clear_presentation()
        write_source((demo.TEMPLATE / 'invoice.js').read_text(encoding='utf-8'))
        marker = demo.metadata()
        marker['generation'] = secrets.token_hex(16)
        demo.safe_path(demo.folder() / demo.MARKER).write_text(json.dumps(marker), encoding='utf-8')
        return demo.status()


async def run_deterministic_repair(job, progress, check_busy=True):
    if Path(job['project']['path']).resolve() != demo.folder().resolve():
        raise ValueError('The deterministic repair supports only the registered invoice showcase.')
    with lease():
        if check_busy: assert_not_busy(job.get('id'))
        trusted_fixture()
        if job.get('demoGeneration') != demo.metadata()['generation']:
            raise ValueError('The demo was reset after this request. Submit a new repair.')
        before = source()
        faulty = (demo.TEMPLATE / 'invoice.js').read_text(encoding='utf-8')
        if before not in (faulty, FIXED_SOURCE):
            raise ValueError('This source is not the known demo fault. Use the agent mode for another bug; no scripted change applied.')
        demo.clear_presentation()
        initial_version = demo.version()
        await progress('Deterministic demo · checking the actual invoice source and unchanged tests')
        await progress('BEFORE · independent Node verification')
        baseline = await run_tests(demo.folder(), 'node', progress)
        if demo.version() != initial_version: raise ValueError('Source changed during inspection. No scripted overwrite applied.')
        trusted_fixture()
        if before == faulty and (baseline['exitCode'] != 1 or '# tests 5' not in baseline['output'] or '# fail 4' not in baseline['output']):
            raise ValueError('The observed failures do not match the configured demo. No scripted fix applied.')
        if before == FIXED_SOURCE and (baseline['exitCode'] != 0 or '# pass 5' not in baseline['output']):
            raise ValueError('The already-fixed source did not pass its expected checks. No scripted change applied.')
        changed = before != FIXED_SOURCE
        if changed:
            await progress('Applying the configured percentage-discount repair to invoice.js')
            write_source(FIXED_SOURCE)
        await progress('Writing invoice.regression.test.js with three new regression checks')
        demo.safe_path(demo.folder() / REGRESSION_FILE).write_text(REGRESSION_SOURCE,encoding='utf-8',newline='\n')
        fixed_version = demo.version()
        await progress('AFTER · independent Node verification')
        after = await run_tests(demo.folder(), 'node', progress)
        trusted_fixture()
        verified = after['exitCode'] == 0 and '# tests 8' in after['output'] and '# pass 8' in after['output'] and demo.version() == fixed_version
        run_id = secrets.token_hex(16)
        if verified:
            directory = demo.safe_path(demo.folder() / '.vscode')
            directory.mkdir(exist_ok=True)
            demo.safe_path(directory / 'tasks.json').write_text(json.dumps(task_payload(ROOT,shutil.which('node'),run_id),indent=2),encoding='utf-8')
        report = {'summary': 'The code subtracted the discount as a flat amount instead of a percentage. The repair applies the percentage to the price.' if changed else 'The invoice source was already correct. All eight checks passed.',
                  'changedFiles':(['invoice.js'] if changed else [])+[REGRESSION_FILE], 'sourceChanged':changed,'generatedTestFiles':[REGRESSION_FILE],
                  'diff': ''.join(difflib.unified_diff(before.splitlines(True),FIXED_SOURCE.splitlines(True),fromfile='before/invoice.js',tofile='after/invoice.js')) + ''.join(difflib.unified_diff([],REGRESSION_SOURCE.splitlines(True),fromfile='/dev/null',tofile='after/'+REGRESSION_FILE)),
                  'beforeTests':baseline,'tests':after,'verified':verified,'demoVersion':fixed_version,
                  'executionMethod':'deterministic_demo','terminalRunId':run_id if verified else None,'workerSession':None,'tokens':{},'providerEstimatedCost':0}
        return {'status':'succeeded' if verified else 'needs_attention',
                'message':'Known invoice repair verified: eight tests passed, including three new regression checks.' if verified else 'Verification failed. Inspect the source and test output.', 'report':report}
