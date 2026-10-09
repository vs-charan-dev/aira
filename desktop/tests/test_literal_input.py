"""Run just the input batching function with fake injection; never load Win32."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace

class ActionError(Exception):pass

class LiteralInput(unittest.TestCase):
    def fixture(self,focus=lambda:42):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'windows_control.py').read_text(encoding='utf-8'))
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='type_text')
        calls=[];sleep=[]
        namespace={'foreground':focus,'ActionError':ActionError,'key':lambda *args,**kwargs:kwargs,
                   'inject':lambda *keys:calls.append(keys),'time':SimpleNamespace(sleep=sleep.append)}
        exec(compile(ast.Module(body=[function],type_ignores=[]),'<isolated type_text>','exec'),namespace)
        return namespace['type_text'],calls
    def test_unicode_and_shell_like_content_stays_literal(self):
        fn,calls=self.fixture();text='Hi Charan — 🧠 $(calc)'
        fn(text,42,batch_units=16,delay=0)
        units=[key['scan'] for batch in calls for key in batch if key['flags']==4]
        actual=b''.join(unit.to_bytes(2,'little') for unit in units).decode('utf-16-le')
        self.assertEqual(actual,text);self.assertEqual(len(calls),2)
    def test_lost_editor_focus_stops_before_next_batch(self):
        fn,calls=self.fixture();checks=iter((True,False))
        with self.assertRaises(ActionError):fn('x'*32,42,batch_units=16,check_focus=lambda:next(checks))
        self.assertEqual(len(calls),1)
    def test_wrong_window_stops_before_any_input(self):
        fn,calls=self.fixture(lambda:99)
        with self.assertRaises(ActionError):fn('Body',42,batch_units=16)
        self.assertFalse(calls)
    def test_oversized_batch_is_rejected(self):
        fn,calls=self.fixture()
        with self.assertRaises(ActionError):fn('Body',42,batch_units=1000)
        self.assertFalse(calls)
