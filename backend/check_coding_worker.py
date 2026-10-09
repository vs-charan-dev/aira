"""Explicit CLI acceptance on an isolated, dependency-free demo. No Notion writes."""
import asyncio
import json
import shutil
import sys
import uuid
from pathlib import Path
from app.config import ROOT, settings
from app.services.coding_worker import BINARY, environment, run_coding, run_tests, has_tests

async def main():
    if '--verify' in sys.argv:
        project = Path(sys.argv[sys.argv.index('--verify') + 1]).resolve(strict=True)
        if project.parent != settings.aira_data_dir / 'projects' or not project.name.startswith('coding-acceptance-'):
            raise SystemExit('Only an existing isolated acceptance project can be verified.')
        report_path = project / 'aira-acceptance-report.json'
        report = json.loads(report_path.read_text(encoding='utf-8'))
        async def progress(label): print(label, flush=True)
        report['tests'] = await run_tests(project, 'node', progress)
        report['verified'] = report['tests']['exitCode'] == 0 and has_tests(report['tests']['output'])
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'verified':report['verified'],'beforeExit':report['beforeTests']['exitCode'],'afterExit':report['tests']['exitCode'],'changedFiles':report['changedFiles']}))
        if not report['verified']: raise SystemExit(1)
        return
    if '--probe' in sys.argv:
        process = await asyncio.create_subprocess_exec(str(BINARY), '--version', env=environment('', ROOT), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        output, _ = await asyncio.wait_for(process.communicate(), 30)
        print(json.dumps({'version': output.decode().strip() if process.returncode == 0 else None, 'runtimeOnE': str(BINARY).startswith(str(ROOT)), 'exitCode': process.returncode}))
        return
    if '--acceptance' not in sys.argv: raise SystemExit('Use --probe or --acceptance (Gemini inference on synthetic files).')
    project = settings.aira_data_dir / 'projects' / ('coding-acceptance-' + uuid.uuid4().hex[:8])
    shutil.copytree(ROOT / 'demo/coding-fixture', project)
    job = {'id':'acceptance','user':'local','mode':'fix','project':{'path':str(project),'runner':'node'},
           'instruction':'Fix the discount calculation in invoice.js so the existing tests pass. Do not modify tests, README or package.json. Read invoice.js and invoice.test.js, edit only invoice.js, then summarize the source change briefly.'}
    async def progress(label): print(label, flush=True)
    result = await run_coding(job, progress)
    report = result['report']
    (project / 'aira-acceptance-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status':result['status'],'project':str(project),'beforeExit':report['beforeTests']['exitCode'],'afterExit':report['tests']['exitCode'],'verified':report['verified'],'changedFiles':report['changedFiles'],'tokens':report['tokens']}))
    if not report['verified'] or report['changedFiles'] != ['invoice.js'] or report['beforeTests']['exitCode'] == 0: raise SystemExit(1)

if __name__ == '__main__': asyncio.run(main())
