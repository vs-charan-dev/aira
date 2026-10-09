"""Only the fixed invoice VS Code process task; no model-authored terminal input."""
import ctypes
import json
import shutil
import subprocess
import sys
import time

def run_tests_in_editor(api,run_id):
    sys.path.insert(0,str(api.ROOT/'backend'))
    from app.core.invoice_presentation import valid_run_id,validate_task,read_result,REGRESSION_FILE,REGRESSION_SOURCE
    if not valid_run_id(run_id): raise api.ActionError('Invalid invoice test task.')
    project=api.ROOT/'data'/'projects'/'invoice-showcase'
    from code_project import find_code
    from app.services.invoice_demo import safe_path,version
    from app.services.invoice_faults import trusted_fixture
    trusted_fixture()
    regression=safe_path(project/REGRESSION_FILE)
    if regression.stat().st_size>10000 or regression.read_text(encoding='utf-8')!=REGRESSION_SOURCE:
        raise api.ActionError('The generated regression checks changed. Inspect them before running.')
    task=safe_path(project/'.vscode'/'tasks.json')
    if task.stat().st_size>8000: raise api.ActionError('Unsupported invoice task configuration.')
    value=json.loads(task.read_text(encoding='utf-8'))
    if validate_task(api.ROOT,shutil.which('node'),value)!=run_id: raise api.ActionError('The invoice test task is stale.')
    source_version=version()
    result=safe_path(api.ROOT/'.cache'/'invoice-terminal'/(run_id+'.json'))
    if result.exists(): raise api.ActionError('This terminal test run already exists. Submit a new repair.')
    exe=find_code()
    if not exe: raise api.ActionError('VS Code could not be found.')
    subprocess.Popen([str(exe),'--reuse-window',str(project),'--goto',str(project/'invoice.regression.test.js')+':1:1'],shell=False)
    def editor():
        handle=api.foreground()
        if api.process_name(handle)!='code.exe': return False
        title=ctypes.create_unicode_buffer(2048)
        api.user32.GetWindowTextW(handle,title,len(title))
        return project.name.lower() in title.value.lower() and 'invoice.regression.test.js' in title.value.lower()
    if not api.wait(editor,seconds=12): raise api.ActionError('The generated test file could not be shown in VS Code.')
    handle=api.foreground()
    api.progress('Running the eight real checks in the VS Code terminal')
    # The recognized tasks.json defines our fixed process task as default build.
    # Ctrl+Shift+B launches it in the integrated terminal without shell input.
    if api.foreground()!=handle: raise api.ActionError('VS Code lost focus. No task was started.')
    api.inject(api.key(0x11),api.key(0x10),api.key(0x42),api.key(0x42,flags=2),api.key(0x10,flags=2),api.key(0x11,flags=2))
    if not api.wait(lambda:result.exists(),seconds=30):
        raise api.ActionError('The VS Code terminal did not report completion. Check workspace trust and the visible task output.')
    read_result(api.ROOT,run_id,source_version)
    trusted_fixture()
    time.sleep(1.5)  # Allow the actual terminal pass result to remain visible.
    return 'VS Code terminal verified all eight tests and displayed All tests passed (8/8).'
