"""One bounded Windows-Use task per process. JSON stdin/stdout, no renderer secrets."""
import contextlib
import json
import logging
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
PROTOCOL = sys.stdout

def emit(**value):
    print(json.dumps(value, ensure_ascii=False), file=PROTOCOL, flush=True)

def configure_environment():
    home = ROOT / 'data' / 'windows-use'
    cache = ROOT / '.cache' / 'windows-use'
    home.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    # Path.home() is used at package import for memory and logging paths.
    os.environ.update(USERPROFILE=str(home), HOME=str(home), APPDATA=str(home / 'AppData' / 'Roaming'),
                      LOCALAPPDATA=str(cache), ANONYMIZED_TELEMETRY='false',
                      TEMP=str(ROOT / '.cache' / 'tmp'), TMP=str(ROOT / '.cache' / 'tmp'),
                      PYTHONPYCACHEPREFIX=str(ROOT / '.cache' / 'pycache'))
    os.environ.pop('GOOGLE_BASE_URL', None)

def dependencies():
    configure_environment()
    # Provider/package chatter never enters the protocol or persistent app log.
    import comtypes.client
    comtypes.client.gen_dir = None
    from windows_use import Agent
    from windows_use.agent.desktop.service import Desktop
    from windows_use.agent.registry.service import Registry
    from windows_use.agent.tools import BUILTIN_TOOLS
    from windows_use.providers.google import ChatGoogle
    import windows_control as native
    from ctypes import wintypes
    native.user32.IsWindow.argtypes = (wintypes.HWND,)
    native.user32.IsWindow.restype = wintypes.BOOL
    return Agent, Desktop, Registry, BUILTIN_TOOLS, ChatGoogle, native

def atomic_shortcut(native, shortcut):
    """Each shortcut injects its complete down/up sequence in one Windows call."""
    from windows_use_policy import ALLOWED_SHORTCUTS, PolicyError
    key = shortcut.lower().replace('control','ctrl').replace(' ', '')
    if key not in ALLOWED_SHORTCUTS:
        raise PolicyError('Keyboard shortcut blocked.')
    names = {'alt':0x12,'ctrl':0x11,'shift':0x10,'win':0x5b,'f4':0x73,'enter':0x0d,'escape':0x1b,'esc':0x1b,'tab':0x09,'home':0x24,'end':0x23,'up':0x26,'down':0x28,'left':0x25,'right':0x27,'backspace':0x08}
    keys = [ord(part.upper()) if len(part)==1 else names[part] for part in key.split('+')]
    native.inject(*([native.key(vk) for vk in keys]+[native.key(vk,flags=2) for vk in reversed(keys)]))

def close_app(action, desktop, native):
    name = action['appName']
    expected = native.EXPECTED.get(name.lower())
    import psutil
    windows, _ = desktop.get_windows()
    matches = []
    for window in windows:
        try:
            process = psutil.Process(window.process_id).name().lower()
        except psutil.Error:
            continue
        if (expected and process == expected) or (not expected and (process == name.lower()+'.exe' or window.name.lower() == name.lower())):
            matches.append(window)
    if not matches:
        return 'failed', f'No open {name} window was found. No process was force-terminated.'
    if len(matches) != 1:
        return 'failed', f'{name} has multiple windows. Close the extra windows or specify the intended window before retrying.'
    window = matches[0]
    native.u.ControlFromHandle(window.handle).SetFocus()
    if not native.wait(lambda: native.foreground() == window.handle, 3):
        return 'failed', 'The requested window did not receive focus. Nothing was closed.'
    emit(type='progress', label='Closing '+name+' with Windows-Use')
    atomic_shortcut(native, 'alt+f4')
    if not native.wait(lambda: not native.user32.IsWindow(window.handle), 5):
        return 'failed', f'{name} is still open or awaiting a save/confirmation prompt. AIRA did not discard work.'
    remaining = False
    try:
        remaining = psutil.Process(window.process_id).is_running()
    except psutil.Error:
        pass
    return 'succeeded', f'{name} window closed; '+('a background process is still running. Full exit was not verified.' if remaining else 'its window process exited.')

def run_agent(action, history, parts):
    from windows_use_policy import GUI_TOOLS, INSTRUCTIONS, PolicyError, check_tool
    Agent, _, Registry, tools, ChatGoogle, native = parts
    sys.path.insert(0, str(ROOT / 'backend'))
    from app.config import settings
    from app.core.secrets import read_key
    key = read_key() or settings.gemini_api_key
    if not key:
        return 'failed', 'Add the Gemini key in AIRA Settings before using Windows-Use.', 0, 0
    model = os.environ.get('AIRA_DESKTOP_MODEL','').strip() or settings.gemini_standard_model
    totals = {'input':0, 'output':0, 'calls':0}

    class BudgetedGoogle(ChatGoogle):
        def invoke(self, *args, **kwargs):
            if totals['calls'] >= 16 or totals['input']+totals['output'] >= 60000:
                raise PolicyError('Desktop task inference budget reached.')
            totals['calls'] += 1
            result = super().invoke(*args, **kwargs)
            usage = getattr(result, 'usage', None)
            totals['input'] += int(getattr(usage,'prompt_tokens',0) or 0)
            totals['output'] += int(getattr(usage,'completion_tokens',0) or 0) + int(getattr(usage,'thinking_tokens',0) or 0)
            return result

    blocked = []
    class GuardedRegistry(Registry):
        def execute(self, tool_name, tool_params, desktop=None):
            if blocked:
                raise PolicyError(blocked[0])
            handle = native.foreground()
            title = native.u.ControlFromHandle(handle).Name if handle else ''
            try:
                native.assert_desktop()
                observed = getattr(desktop, 'desktop_state', None)
                active = getattr(observed, 'active_window', None)
                if active and active.handle != handle and tool_name != 'done_tool':
                    raise PolicyError('Another window took focus after observation. Desktop input stopped.')
                check_tool(tool_name, tool_params, native.process_name(handle), title)
                target = native.ALIASES.get(action['appName'].lower(), action['appName']).lower()
                if tool_name == 'app_tool' and tool_params.get('mode','launch') == 'launch':
                    requested = native.ALIASES.get(str(tool_params.get('name','')).lower(), str(tool_params.get('name',''))).lower()
                    if requested != target:
                        raise PolicyError('Launching another application is outside this task.')
                elif tool_name not in ('app_tool','done_tool','wait_tool'):
                    expected_process = native.EXPECTED.get(target, target.replace(' ','')+'.exe')
                    from calculator_control import result_control
                    calculator_matches = target == 'calculator' and bool(result_control(native,handle))
                    if not calculator_matches and native.process_name(handle).lower() != expected_process:
                        raise PolicyError('The target application is not active. Input stopped.')
            except (PolicyError, native.ActionError) as error:
                blocked.append(str(error))
                raise PolicyError(str(error))
            # Visible launcher reuses AIRA's exact installed-app resolution.
            # The model never supplies PowerShell code, paths or launch arguments.
            if tool_name == 'app_tool' and tool_params.get('mode','launch') == 'launch':
                from windows_use.agent.registry.views import ToolResult
                return ToolResult(is_success=True, content=native.open_app(tool_params['name']))
            return super().execute(tool_name, tool_params, desktop)

    labels = {'app_tool':'Opening or switching application', 'click_tool':'Clicking an application control',
              'type_tool':'Typing requested text', 'scroll_tool':'Scrolling', 'move_tool':'Moving pointer',
              'shortcut_tool':'Using a keyboard shortcut', 'wait_tool':'Waiting for the application'}
    def event(value):
        kind = getattr(value.type,'value',value.type)
        if kind in ('tool_call','tool_result'):
            name = value.data.get('tool_name','')
            status = 'running' if kind == 'tool_call' else 'succeeded' if value.data.get('is_success') else 'failed'
            history.step(name, status)
            if kind == 'tool_call':
                emit(type='progress', label=f"Windows-Use · step {value.data.get('step',0)+1}: {labels.get(name,'Working')}")

    llm = BudgetedGoogle(model=model, api_key=key, temperature=.1, max_output_tokens=2048)
    agent = Agent(llm=llm, mode='flash', use_vision=False, use_accessibility=True, max_steps=12,
                  max_consecutive_failures=2, instructions=INSTRUCTIONS, experimental=False,
                  log_to_console=False, log_to_file=False, event_subscriber=event)
    agent.registry = GuardedRegistry([tool for tool in tools if tool.name in GUI_TOOLS])
    agent.desktop.shortcut = lambda shortcut: atomic_shortcut(native, shortcut)
    original_click = agent.desktop.click
    def literal_type(loc, text, caret_position='idle', clear='false', press_enter='false'):
        expected = native.foreground()
        original_click(loc)
        if native.foreground() != expected:
            raise PolicyError('Typing target changed. Input stopped.')
        if caret_position in ('start','end'):
            atomic_shortcut(native, 'home' if caret_position=='start' else 'end')
        if clear == 'true':
            atomic_shortcut(native, 'ctrl+a')
            atomic_shortcut(native, 'backspace')
        native.type_text(text, expected, delay=.005)
        if press_enter == 'true':
            atomic_shortcut(native, 'enter')
    agent.desktop.type = literal_type
    # Block all arbitrary command execution, including calls outside the registry.
    original_command = agent.desktop.execute_command
    def known_command(command, *args, **kwargs):
        if command.strip() != 'Get-StartApps | ConvertTo-Csv -NoTypeInformation':
            raise PolicyError('Shell execution is disabled.')
        return original_command(command, *args, **kwargs)
    agent.desktop.execute_command = known_command
    emit(type='progress', label='Windows-Use · reading the application interface')
    try:
        result = agent.invoke(task=f"Target application: {action['appName']}\nDirect user task: {action['task']}")
        if blocked:
            return 'failed', blocked[0], totals['input'], totals['output']
        if not result or not result.is_done:
            return 'failed', 'Windows-Use did not complete this task within its limits. Inspect the app before retrying.', totals['input'], totals['output']
        # General GUI outcomes are agent-reported, unlike the independent close check.
        message = 'Windows-Use reports: '+str(result.content or 'Task complete.')[:300]+' Final state is agent-reported; persistence/sync was not independently verified.'
        return 'succeeded', message[:400], totals['input'], totals['output']
    finally:
        llm.client.close()

def main():
    from desktop_history import History
    from windows_use_policy import validate_action
    value = json.loads(sys.stdin.readline(12000))
    action = validate_action(value)
    request_id = value.get('requestId','')
    if not isinstance(request_id,str) or not request_id or len(request_id)>80 or not all(c.isalnum() or c=='-' for c in request_id):
        raise ValueError('Invalid desktop task ID.')
    history = History(request_id, action)
    emit(type='progress', label='Starting Windows-Use')
    try:
        parts = dependencies()
        native = parts[-1]
        native.assert_desktop()
        native.user32.SetProcessDPIAware()
        if action['kind'] == 'close_app':
            status, message = close_app(action, parts[1](use_vision=False, use_accessibility=True), native)
            tokens = (0,0)
        else:
            status, message, *tokens = run_agent(action, history, parts)
        history.finish(status, message, *tokens)
        emit(type='result', status=status, message=message)
    except Exception as error:
        from windows_use_policy import PolicyError
        message = str(error) if isinstance(error,PolicyError) else 'Windows-Use could not complete this task. Check the Gemini model/key, app focus and controller installation; inspect partial changes before retrying.'
        history.finish('failed', message)
        emit(type='result', status='failed', message=message)

if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    with contextlib.redirect_stdout(sys.stderr):
        try:
            if '--probe' in sys.argv:
                parts = dependencies()
                from importlib.metadata import version
                emit(type='probe', version=version('windows-use'), home=str(Path.home()), telemetry=os.environ['ANONYMIZED_TELEMETRY'], gui_tools_only=True)
            else:
                main()
        except Exception:
            emit(type='result', status='failed', message='Invalid or unavailable Windows-Use task. No completion was verified.')
            sys.exit(1)
