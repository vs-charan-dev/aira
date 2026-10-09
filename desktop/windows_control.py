"""Bounded Windows workflows; JSON stdin only, no arbitrary code or shell arguments."""
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT / '.cache' / 'tmp')
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
# Generate COM interfaces in memory, never in a C-drive profile cache.
import comtypes.client
comtypes.client.gen_dir = None
import uiautomation as u
u.Logger.SetLogFile('')
u.SetGlobalSearchTimeout(1)

DENIED = re.compile(r'powershell|command prompt|terminal|registry|regedit|task scheduler|disk management|computer management|wsl|security|run command', re.I)
ALIASES = {'explorer': 'File Explorer', 'windows explorer': 'File Explorer', 'windows settings': 'Settings', 'chrome': 'Google Chrome', 'googlechrome': 'Google Chrome', 'chrome browser': 'Google Chrome', 'google chrome browser': 'Google Chrome', 'edge': 'Microsoft Edge', 'vs code': 'Visual Studio Code', 'vscode': 'Visual Studio Code', 'code': 'Visual Studio Code'}
EXPECTED = {'notion': 'notion.exe', 'calculator': 'calculatorapp.exe', 'google chrome': 'chrome.exe', 'microsoft edge': 'msedge.exe', 'file explorer': 'explorer.exe', 'settings': 'systemsettings.exe', 'notepad': 'notepad.exe', 'visual studio code': 'code.exe'}
_catalog_cache = None
_catalog_until = 0
_input_started = False

class ActionError(Exception):
    pass

def emit(**value):
    print(json.dumps(value, ensure_ascii=False), flush=True)

def progress(label):
    emit(type='progress', label=label)

def wait(test, seconds=8):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = test()
        if value:
            return value
        time.sleep(.1)
    return None

user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
user32.GetForegroundWindow.restype = w.HWND
user32.IsWindow.argtypes = (w.HWND,)
user32.IsWindow.restype = w.BOOL
user32.IsWindowVisible.argtypes = (w.HWND,)
user32.IsWindowVisible.restype = w.BOOL
user32.PostMessageW.argtypes = (w.HWND, w.UINT, w.WPARAM, w.LPARAM)
user32.PostMessageW.restype = w.BOOL
user32.GetWindowThreadProcessId.argtypes = (w.HWND, ctypes.POINTER(w.DWORD))
user32.OpenInputDesktop.argtypes = (w.DWORD, w.BOOL, w.DWORD)
user32.OpenInputDesktop.restype = w.HANDLE
user32.CloseDesktop.argtypes = (w.HANDLE,)
kernel32.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
kernel32.OpenProcess.restype = w.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD))
kernel32.CloseHandle.argtypes = (w.HANDLE,)

class Mouse(ctypes.Structure):
    _fields_ = [('dx',w.LONG),('dy',w.LONG),('data',w.DWORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
class Key(ctypes.Structure):
    _fields_ = [('vk',w.WORD),('scan',w.WORD),('flags',w.DWORD),('time',w.DWORD),('extra',ctypes.c_size_t)]
class Union(ctypes.Union):
    _fields_ = [('mouse',Mouse),('key',Key)]
class Input(ctypes.Structure):
    _fields_ = [('type',w.DWORD),('data',Union)]
user32.SendInput.argtypes = (w.UINT, ctypes.POINTER(Input), ctypes.c_int)
user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
user32.VkKeyScanW.argtypes = (w.WCHAR,)
user32.VkKeyScanW.restype = ctypes.c_short

def foreground():
    return user32.GetForegroundWindow()

def process_name(handle):
    pid = w.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
    proc = kernel32.OpenProcess(0x1000, False, pid.value)
    if not proc:
        return ''
    try:
        size = w.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(proc, 0, buffer, ctypes.byref(size)):
            return Path(buffer.value).name.lower()
        return ''
    finally:
        kernel32.CloseHandle(proc)

def assert_desktop():
    handle = user32.OpenInputDesktop(0, False, 1)
    if not handle:
        raise ActionError('Unlock Windows and dismiss administrator prompts first.')
    user32.CloseDesktop(handle)

def inject(*inputs):
    global _input_started
    assert_desktop()
    sequence = (Input * len(inputs))(*inputs)
    if user32.SendInput(len(sequence), sequence, ctypes.sizeof(Input)) != len(sequence):
        raise ActionError('Windows blocked input. Completion was not verified.')
    if not _input_started:
        _input_started = True
        emit(type='action_started')

def key(vk=0, scan=0, flags=0):
    if vk and not scan:
        scan = user32.MapVirtualKeyW(vk,0)
        if vk in (0x5B,0x5C,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x2D,0x2E):
            flags |= 1
    return Input(type=1, data=Union(key=Key(vk,scan,flags,0,0)))

def tap(vk):
    inject(key(vk), key(vk,flags=2))

def chord(modifier, vk):
    inject(key(modifier), key(vk), key(vk,flags=2), key(modifier,flags=2))

def type_text(text, expected, physical=False, delay=.03, check_focus=None, batch_units=1):
    # Literal UTF-16 input; braces, spaces etc. never become hotkey expressions.
    data = text.encode('utf-16-le')
    if not isinstance(batch_units,int) or isinstance(batch_units,bool) or not 1<=batch_units<=16 or (physical and batch_units!=1):
        raise ActionError('Text input batches must contain 1–16 UTF-16 units; physical keys use one unit.')
    for offset in range(0,len(data),batch_units*2):
        if foreground() != expected:
            raise ActionError('Another window took focus. AIRA stopped typing.')
        if check_focus is not None and not check_focus():
            raise ActionError('The editor lost focus. Typing stopped; inspect the partial Notion note before retrying.')
        chunk=data[offset:offset+batch_units*2]
        inputs=[]
        for index in range(0,len(chunk),2):
            scan = int.from_bytes(chunk[index:index+2], 'little')
            mapped = user32.VkKeyScanW(chr(scan)) if physical else -1
            if mapped != -1:
                vk, modifiers = mapped & 0xff, (mapped >> 8) & 0xff
                keys = [code for bit,code in ((1,0x10),(2,0x11),(4,0x12)) if modifiers & bit]
                inputs.extend([key(code) for code in keys] + [key(vk),key(vk,flags=2)] + [key(code,flags=2) for code in reversed(keys)])
            else:
                inputs.extend([key(scan=scan,flags=4),key(scan=scan,flags=6)])
        inject(*inputs)
        time.sleep(delay*len(chunk)/2)

def click(control, expected=None):
    assert_desktop()
    rect = control.BoundingRectangle
    if control.IsOffscreen or rect.width() < 1 or rect.height() < 1:
        raise ActionError('The requested control is not visible.')
    x,y = int((rect.left+rect.right)/2), int((rect.top+rect.bottom)/2)
    point = w.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    for step in range(1,13):
        user32.SetCursorPos(point.x + (x-point.x)*step//12, point.y+(y-point.y)*step//12)
        time.sleep(.015)
    current = control.BoundingRectangle
    if control.IsOffscreen or abs((current.left+current.right)/2-x)>4 or abs((current.top+current.bottom)/2-y)>4:
        raise ActionError('The requested control moved. Please retry.')
    if expected and foreground()!=expected:
        raise ActionError('Another window took focus. AIRA stopped before clicking.')
    inject(Input(type=0,data=Union(mouse=Mouse(flags=2))), Input(type=0,data=Union(mouse=Mouse(flags=4))))

def catalog(refresh=False):
    global _catalog_cache, _catalog_until
    if not refresh and _catalog_cache is not None and time.monotonic() < _catalog_until:
        return _catalog_cache
    # Fixed read-only command: no app name/path is interpolated into PowerShell.
    powershell = Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = "[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false); @(Get-StartApps | Select-Object Name,AppID) | ConvertTo-Json -Compress"
    result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise ActionError('Installed app inventory unavailable. Please retry.')
    values = json.loads(result.stdout.decode('utf-8-sig'))
    _catalog_cache = [item for item in values if not DENIED.search(item['Name'])]
    _catalog_until = time.monotonic() + 300
    return _catalog_cache

def search_result(name):
    handle = foreground()
    if process_name(handle) not in ('searchhost.exe','searchapp.exe'):
        return None
    root = u.ControlFromHandle(handle)
    for index,(control,depth) in enumerate(u.WalkControl(root,maxDepth=18)):
        if index > 1500:
            break
        if control.ControlTypeName not in ('ListItemControl','ButtonControl','DataItemControl') or control.IsOffscreen:
            continue
        label = control.Name.lower()
        if label == name.lower() or label.startswith(name.lower()+', app') or label.startswith(name.lower()+', desktop app'):
            return control
    return None

def verify_app(name):
    handle = foreground()
    if name.lower()=='calculator':
        from calculator_control import result_control
        return bool(result_control(sys.modules[__name__],handle))
    actual = process_name(handle)
    if actual in ('searchhost.exe','searchapp.exe','startmenuexperiencehost.exe','electron.exe','explorer.exe') and name.lower() != 'file explorer':
        return False
    expected = EXPECTED.get(name.lower())
    control = u.ControlFromHandle(handle)
    if expected and actual == expected:
        if name.lower() == 'file explorer':
            return control.ClassName in ('CabinetWClass','ExploreWClass')
        return True
    if expected:
        return False
    title = control.Name.lower()
    return title == name.lower() or title.endswith(' - '+name.lower()) or title.endswith(' — '+name.lower())

def open_app(name):
    if not isinstance(name,str) or not re.fullmatch(r'[\w .()&+\-]{1,80}',name.strip()) or DENIED.search(name):
        raise ActionError('Provide an ordinary installed app display name, without commands.')
    name = ALIASES.get(name.strip().lower(),name.strip())
    if verify_app(name):
        return name+' is already in the foreground; its window was verified.'
    matches = [item for item in catalog() if item['Name'].lower()==name.lower()]
    if not matches:
        matches = [item for item in catalog(refresh=True) if item['Name'].lower()==name.lower()]
    if len(matches)!=1:
        raise ActionError('App not found or ambiguous. Choose its exact name from Desktop actions.')
    name = matches[0]['Name']
    progress('Opening Start for '+name)
    taskbar = u.PaneControl(searchDepth=1,ClassName='Shell_TrayWnd')
    start = taskbar.ButtonControl(searchDepth=5,AutomationId='StartButton')
    if not start.Exists(.5):
        start = taskbar.ButtonControl(searchDepth=5,Name='Start')
    if not start.Exists(.5):
        raise ActionError('Windows Start button was not found.')
    click(start)
    active = wait(lambda: foreground() if process_name(foreground()) in ('startmenuexperiencehost.exe','searchhost.exe','searchapp.exe') else None)
    if not active:
        raise ActionError('Start did not become active. No app was launched.')
    progress('Searching for '+name)
    # Physical first letter triggers Start's search; Unicode input alone does not.
    physical = bool(re.match(r'[a-zA-Z0-9]',name))
    if physical:
        tap(ord(name[0].upper()))
    else:
        chord(0x5B,0x53)
    search = wait(lambda: foreground() if process_name(foreground()) in ('searchhost.exe','searchapp.exe') else None)
    if not search:
        raise ActionError('Windows Search did not become active.')
    def search_box():
        if foreground() != search:
            raise ActionError('Another window took focus. Search stopped.')
        control = u.ControlFromHandle(search).EditControl(searchDepth=5,AutomationId='SearchTextBox')
        return control if control.Exists(.05) and not control.IsOffscreen and control.IsEnabled else None
    box = wait(search_box, 3)
    if not box:
        raise ActionError('Windows Search input was not found.')
    box.SetFocus()
    if not wait(lambda: box.HasKeyboardFocus, 2):
        raise ActionError('Windows Search input did not receive focus.')
    search = foreground()
    if process_name(search) not in ('searchhost.exe','searchapp.exe'):
        if os.environ.get('AIRA_CONTROL_DIAGNOSTICS')=='1':
            print('Unexpected focused process: '+process_name(search),file=sys.stderr)
        raise ActionError('Another window took focus. Search stopped.')
    focused = u.GetFocusedControl()
    if focused.ControlTypeName!='EditControl' or focused.ProcessId!=box.ProcessId:
        raise ActionError('Windows Search input did not receive focus.')
    chord(0x11,0x41)
    type_text(name,search,physical=True,delay=.005)
    # Search updates asynchronously. Never click an unrelated best match if input
    # is dropped; the exact installed AppID remains a safe launch target.
    def query_matches():
        if foreground()!=search:
            raise ActionError('Another window took focus. Launch stopped.')
        try: return box.GetValuePattern().Value.lower()==name.lower()
        except comtypes.COMError: return False
    query_received = wait(query_matches,1)
    result = wait(lambda: search_result(name),1.5) if query_received else None
    if foreground()!=search:
        raise ActionError('Another window took focus. Launch stopped.')
    if result:
        progress('Opening '+name)
        click(result,search)
    else:
        # Some Windows Search builds expose the textbox but not their result pane.
        # Launch only the exact entry already matched against Windows' app inventory.
        # Never click guessed positions or press Enter on an unknown best match.
        progress('Opening installed '+name)
        tap(0x1B)
        shell = comtypes.client.CreateObject('Shell.Application',dynamic=True)
        item = shell.NameSpace('shell:AppsFolder').ParseName(matches[0]['AppID'])
        if not item:
            raise ActionError('The installed app shortcut could not be resolved.')
        item.InvokeVerb('open')
    if not wait(lambda: verify_app(name),12):
        raise ActionError('App was clicked, but its foreground window could not be verified. It may still be loading.')
    return name+' is open and its foreground window was verified.'

def open_folder(path):
    if isinstance(path,str) and path.lower() in ('desktop','documents','downloads'):
        from known_folders import resolve
        try: path=resolve(path)
        except ValueError as error: raise ActionError(str(error))
    if not isinstance(path,str) or len(path)>500 or not re.match(r'^[a-zA-Z]:[\\/]',path) or re.search(r'[\x00-\x1f<>"|?*]',path) or ':' in path[2:]:
        raise ActionError('Provide an absolute local folder path.')
    folder = Path(path)
    if not folder.is_dir():
        raise ActionError('That local folder does not exist. No navigation was performed.')
    folder = str(folder.resolve())
    if not re.match(r'^[a-zA-Z]:[\\/]',folder):
        raise ActionError('The folder resolves to a network or device path. Choose a local folder.')
    progress('Opening File Explorer')
    chord(0x5B,0x45)
    def explorer_window():
        handle = foreground()
        return handle if process_name(handle)=='explorer.exe' and u.ControlFromHandle(handle).ClassName in ('CabinetWClass','ExploreWClass') else None
    explorer = wait(explorer_window)
    if not explorer:
        raise ActionError('File Explorer did not become active.')
    shell = comtypes.client.CreateObject('Shell.Application',dynamic=True)
    def target_window():
        if foreground()!=explorer:
            raise ActionError('Another window took focus. Navigation stopped.')
        windows = shell.Windows()
        matches=[]
        for index in range(windows.Count):
            window = windows.Item(index)
            try:
                if int(window.HWND)==int(explorer): matches.append(window)
            except (AttributeError,comtypes.COMError):
                continue
        if len(matches)>1:
            raise ActionError('Explorer exposed multiple tabs for this window. Open a single-tab Explorer window and retry; AIRA did not choose a hidden tab.')
        return matches[0] if matches else None
    target = wait(target_window,5)
    if not target:
        raise ActionError('Explorer window was visible but its navigation interface was not ready. No folder navigation was sent.')
    progress('Navigating to '+folder)
    # Navigate the observed Explorer window through its fixed Shell interface.
    # Windows 11 address input can drop Unicode keystrokes; no guessed typing.
    target.Navigate2(folder)
    def verified():
        from urllib.parse import unquote, urlparse
        window = target_window()
        if window is None: return False
        try:
            # Folder.Self also covers a canonical filesystem folder displayed
            # through Explorer's namespace rather than a file:// LocationURL.
            location = str(window.Document.Folder.Self.Path)
            if os.path.normcase(location.rstrip('\\'))==os.path.normcase(folder.rstrip('\\')): return True
            uri = urlparse(window.LocationURL)
            if uri.scheme=='file' and not uri.netloc:
                location = unquote(uri.path).lstrip('/').replace('/','\\')
                return os.path.normcase(location.rstrip('\\'))==os.path.normcase(folder.rstrip('\\'))
        except (AttributeError,comtypes.COMError):
            return False
        return False
    if not wait(verified):
        raise ActionError('Explorer navigation was sent, but the requested folder could not be verified.')
    return 'File Explorer is open at '+folder+'; the folder was verified.'

def close_app(name):
    if not isinstance(name,str) or not re.fullmatch(r'[\w .()&+\-]{1,80}',name.strip()) or DENIED.search(name):
        raise ActionError('Provide an ordinary application display name.')
    name = ALIASES.get(name.strip().lower(),name.strip())
    expected = EXPECTED.get(name.lower())
    matches = []
    for window in u.GetRootControl().GetChildren():
        handle = window.NativeWindowHandle
        # Minimized application windows are offscreen in UIA, but remain
        # visible Win32 windows. Include them when deciding uniqueness.
        if not handle or not user32.IsWindowVisible(handle):
            continue
        process = process_name(handle)
        calculator=False
        if name.lower()=='calculator':
            from calculator_control import result_control
            calculator=bool(result_control(sys.modules[__name__],handle,include_offscreen=True))
        title=window.Name.lower()
        title_matches=title == name.lower() or title.endswith(' - '+name.lower()) or title.endswith(' — '+name.lower())
        if calculator or (name.lower()!='calculator' and ((expected and process == expected) or (not expected and (process == name.lower().replace(' ','')+'.exe' or title_matches)))):
            if name.lower() == 'file explorer' and window.ClassName not in ('CabinetWClass','ExploreWClass'):
                continue
            matches.append(window)
    if len(matches) != 1:
        raise ActionError('No unique '+name+' window was found. Specify the intended window; nothing was closed.')
    window = matches[0]
    handle = window.NativeWindowHandle
    progress('Closing '+name)
    # Address the verified window directly. Alt+F4 can close a different app
    # if focus changes between verification and input; WM_CLOSE cannot.
    assert_desktop()
    if not user32.PostMessageW(handle, 0x0010, 0, 0):
        raise ActionError('Windows blocked closing the requested window. Nothing was force-closed.')
    emit(type='action_started')
    if not wait(lambda: not user32.IsWindow(handle), 5):
        raise ActionError(name+' remains open or is awaiting confirmation. AIRA did not discard work.')
    return name+' window closed; a background process may remain.'


def type_in_app(name, text):
    if not isinstance(name,str) or name.strip().lower() != 'notion':
        raise ActionError('Direct text entry supports the current Notion page. Use a Windows-Use task for another application.')
    if not isinstance(text,str) or not text or len(text)>2000 or re.search(r'[\x00-\x08\x0b-\x1f\x7f]',text):
        raise ActionError('Provide literal text of 1–2000 characters.')
    if not verify_app('Notion'):
        windows = [window for window in u.GetRootControl().GetChildren()
                   if window.NativeWindowHandle and not window.IsOffscreen and process_name(window.NativeWindowHandle)=='notion.exe']
        if len(windows)!=1:
            raise ActionError('Bring the intended Notion page to the foreground first. No unique visible Notion window was found; no text was typed.')
        windows[0].SetFocus()
        if not wait(lambda: verify_app('Notion'), 2):
            raise ActionError('Notion did not receive focus. No text was typed.')
    from notion_control import NotionController
    return NotionController(sys.modules[__name__]).append(text)


def execute(request):
    global _input_started
    _input_started = False
    assert_desktop()
    # UI Automation rectangles are physical pixels; align the helper's Win32 coordinates.
    user32.SetProcessDPIAware()
    if request.get('kind')=='open_app' and isinstance(request.get('appName'),str) and request['appName'].strip().lower() in ('chrome','google chrome','googlechrome','chrome browser','google chrome browser'):
        request={'kind':'open_browser'}
    if request.get('kind') in ('open_browser','open_maps','search_maps','search_youtube','open_youtube_video','current_youtube_video','notebooklm_mindmap','show_invoice_demo'):
        from browser_control import execute as browser_execute
        browser_execute(sys.modules[__name__],request)
        return
    if request.get('kind') == 'export_summary_to_notion':
        from notion_control import NotionController
        controller = NotionController(sys.modules[__name__])
        try:
            message, data = controller.export(request)
        except ActionError: raise
        except Exception:
            controller.fail('Notion accessibility changed. Completion was not verified; inspect partial changes before retrying.')
        emit(type='result', status='succeeded', message=message, data=data)
        return
    if request.get('kind')=='list_apps':
        emit(type='result',status='succeeded',message='Installed apps loaded.',apps=sorted(set(item['Name'] for item in catalog(refresh=True))))
        return
    if request.get('kind')=='inspect_notion':
        # Developer-only read-only readiness diagnostic; never exposed in IPC.
        from notion_control import NotionController
        controller = NotionController(sys.modules[__name__])
        controller.handle = foreground()
        if process_name(controller.handle) != 'notion.exe':
            raise ActionError('Bring Notion to the foreground for the readiness check.')
        doc = controller.document()
        if doc and os.environ.get('AIRA_CONTROL_DIAGNOSTICS')=='1':
            for button in controller.nodes(doc['doc']):
                if button.ControlTypeName=='ButtonControl' and button.Name=='Private':
                    ancestors=[]
                    control=button.GetParentControl()
                    for _ in range(6):
                        if control is None:
                            break
                        ancestors.append({'type': control.ControlTypeName, 'role': control.AriaRole, 'localizedType': control.LocalizedControlType})
                        control=control.GetParentControl()
                    emit(type='diagnostic', privateAncestors=ancestors)
        emit(type='result', status='succeeded', message='Read-only Notion readiness check.', ready=bool(doc), private=bool(doc and doc['private']), titleLength=len(controller.value(doc['title'])) if doc else None, paragraphs=len(doc['edits']) if doc else None, emptyBody=all(not controller.value(c).strip() for c in doc['edits']) if doc else None, pageId=doc['id'] if doc else None)
        return
    if request.get('kind')=='run_invoice_tests':
        from invoice_control import run_tests_in_editor
        message = run_tests_in_editor(sys.modules[__name__],request.get('runId'))
    elif request.get('kind')=='show_project':
        project = Path(request.get('path', '')).resolve(strict=True)
        if not project.is_dir() or project.drive.lower() != 'e:':
            raise ActionError('Choose an existing E-drive coding project.')
        from code_project import find_code
        exe = find_code()
        if not exe: raise ActionError('Visual Studio Code could not be found in PATH, registered app paths or standard folders.')
        source = None
        if request.get('file') is not None:
            if request['file'] != 'invoice.js': raise ActionError('Unsupported source file.')
            source = (project / 'invoice.js').resolve(strict=True)
            if not source.is_file() or not source.is_relative_to(project): raise ActionError('The invoice source is not inside the project.')
        progress('Showing selected project in VS Code')
        args = [str(exe), '--reuse-window', str(project)]
        if source: args += ['--goto', str(source) + ':1:1']
        subprocess.Popen(args, shell=False)
        def visible():
            handle = foreground()
            if process_name(handle) != 'code.exe': return False
            buffer = ctypes.create_unicode_buffer(2048)
            user32.GetWindowTextW(handle, buffer, len(buffer))
            return project.name.lower() in buffer.value.lower() and (not source or source.name.lower() in buffer.value.lower())
        if not wait(visible, seconds=12): raise ActionError('VS Code launch requested, but the selected project could not be verified in the foreground.')
        message = 'VS Code is showing the selected project; its window title was verified. Inspect the task report for tests and changes.'
    elif request.get('kind')=='open_app':
        message = open_app(request.get('appName'))
    elif request.get('kind')=='open_folder':
        message = open_folder(request.get('path'))
    elif request.get('kind')=='close_app':
        message = close_app(request.get('appName'))
    elif request.get('kind')=='type_in_app':
        message = type_in_app(request.get('appName'), request.get('text'))
    elif request.get('kind')=='calculate_in_app':
        from calculator_control import run
        message = run(sys.modules[__name__],request.get('expression'))+'; Calculator display matched the computed result.'
    elif request.get('kind')=='create_notion_note':
        from notion_control import NotionController
        controller = NotionController(sys.modules[__name__])
        try:
            message = controller.run(request.get('title'), request.get('content'))
        except ActionError:
            raise
        except Exception as error:
            if os.environ.get('AIRA_CONTROL_DIAGNOSTICS')=='1':
                import traceback
                for frame in traceback.extract_tb(error.__traceback__)[-5:]:
                    print(Path(frame.filename).name+':'+str(frame.lineno)+' '+frame.name, file=sys.stderr)
                print(type(error).__name__, file=sys.stderr)
            controller.fail('Notion accessibility changed or became unavailable. Completion was not verified.')
    else:
        raise ActionError('Unsupported desktop action.')
    emit(type='result',status='succeeded',message=message)


def main():
    execute(json.loads(sys.stdin.readline()))

if __name__=='__main__':
    try:
        main()
    except ActionError as error:
        emit(type='result',status='failed',message=str(error))
        sys.exit(1)
    except Exception as error:
        # Never return raw provider details, which can include other window content.
        if os.environ.get('AIRA_CONTROL_DIAGNOSTICS')=='1':
            print(type(error).__name__+': '+str(error),file=sys.stderr)
        emit(type='result',status='failed',message='Windows could not complete this action. Stop and try again.')
        sys.exit(1)
