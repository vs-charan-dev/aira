"""Exercise target selection and graceful close with no real Windows input."""
import ast
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class ActionError(Exception): pass


class CloseAppTests(unittest.TestCase):
    def fixture(self, windows, *, remains=False, blocked=False):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'windows_control.py').read_text(encoding='utf-8'))
        body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='close_app' or
              isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ALIASES','EXPECTED','DENIED') for t in n.targets)]
        native=SimpleNamespace(IsWindowVisible=lambda handle:True, IsWindow=lambda handle:remains,
                               PostMessageW=Mock(return_value=not blocked))
        ns={'re':re,'sys':sys,'__name__':__name__,'ActionError':ActionError,
            'u':SimpleNamespace(GetRootControl=lambda:SimpleNamespace(GetChildren=lambda:windows)),
            'user32':native,'process_name':lambda handle:next(w.process for w in windows if w.NativeWindowHandle==handle),
            'wait':lambda test,seconds:test(),'progress':Mock(),'assert_desktop':Mock(),'emit':Mock()}
        exec(compile(ast.Module(body=body,type_ignores=[]),'<close_app>','exec'),ns)
        return ns['close_app'],native

    def window(self,handle,process,title):
        return SimpleNamespace(NativeWindowHandle=handle,process=process,Name=title,IsOffscreen=True,ClassName='AppWindow')

    def test_named_minimized_window_is_closed_without_foreground_keyboard_input(self):
        close,native=self.fixture([self.window(42,'code.exe','Project — Visual Studio Code'),self.window(99,'notion.exe','Notion')])
        self.assertIn('closed',close('VS Code'))
        native.PostMessageW.assert_called_once_with(42,0x0010,0,0)

    def test_unknown_app_matches_document_title_suffix(self):
        close,native=self.fixture([self.window(42,'writer.exe','Draft - LibreOffice Writer')])
        close('LibreOffice Writer');native.PostMessageW.assert_called_once()

    def test_multiple_windows_including_minimized_window_are_not_closed(self):
        close,native=self.fixture([self.window(42,'chrome.exe','One'),self.window(43,'chrome.exe','Two')])
        with self.assertRaisesRegex(ActionError,'No unique'): close('Google Chrome')
        native.PostMessageW.assert_not_called()

    def test_missing_window_is_not_closed(self):
        close,native=self.fixture([])
        with self.assertRaises(ActionError): close('Notion')
        native.PostMessageW.assert_not_called()

    def test_save_prompt_or_blocked_close_is_not_success(self):
        for flags in ({'remains':True},{'blocked':True}):
            close,native=self.fixture([self.window(42,'notion.exe','Notion')],**flags)
            with self.assertRaises(ActionError): close('Notion')
            native.PostMessageW.assert_called_once()

    def test_minimized_calculator_identity_is_checked(self):
        close,native=self.fixture([self.window(42,'applicationframehost.exe','Calculator')])
        control=Mock(return_value=True)
        with patch.dict(sys.modules,{'calculator_control':SimpleNamespace(result_control=control)}): close('Calculator')
        self.assertTrue(control.call_args.kwargs['include_offscreen'])
        native.PostMessageW.assert_called_once_with(42,0x0010,0,0)

    def test_invalid_app_name_has_no_input(self):
        close,native=self.fixture([])
        for name in ('Notion;calc','PowerShell',''):
            with self.assertRaises(ActionError): close(name)
        native.PostMessageW.assert_not_called()
