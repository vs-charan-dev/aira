"""Discover the installed VS Code executable without running a command shell."""
import os
import shutil
from pathlib import Path

def find_code():
    candidates = [Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Microsoft VS Code/Code.exe', Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Microsoft VS Code/Code.exe']
    launcher = shutil.which('code.cmd')
    if launcher: candidates.insert(0, Path(launcher).parent.parent / 'Code.exe')
    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r'Software\Microsoft\Windows\CurrentVersion\App Paths\Code.exe') as key:
                    candidates.append(Path(winreg.QueryValueEx(key, '')[0].strip('"')))
            except OSError: pass
    except ImportError: pass
    return next((item.resolve() for item in candidates if item.name.lower() == 'code.exe' and item.is_file()), None)
