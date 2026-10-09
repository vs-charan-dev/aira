import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from windows_use_policy import PolicyError, check_tool, validate_action
from desktop_history import History

class WindowsUsePolicy(unittest.TestCase):
    def test_task_validation(self):
        self.assertEqual(validate_action({'kind':'desktop_task','appName':' Notepad ','task':'Type Hi Charan'})['appName'],'Notepad')
        for value in [{'kind':'shell','appName':'Notepad'}, {'kind':'close_app','appName':'Windows Security'}, {'kind':'desktop_task','appName':'Notepad','task':'delete files'}, {'kind':'desktop_task','appName':'Notepad','task':'x'*2001}]:
            with self.assertRaises(PolicyError): validate_action(value)
    def test_runtime_boundaries(self):
        for name,args in [('shell_tool',{'command':'calc'}),('file_tool',{'mode':'delete'}),('memory_tool',{}),('desktop_tool',{}),('shortcut_tool',{'shortcut':'win+r'}),('app_tool',{'name':'PowerShell'}),('move_tool',{'drag':True}),('wait_tool',{'duration':100})]:
            with self.assertRaises(PolicyError): check_tool(name,args)
        with self.assertRaises(PolicyError): check_tool('click_tool',{},'consent.exe','Administrator password')
        check_tool('shortcut_tool',{'shortcut':'alt+f4'},'notepad.exe','Untitled - Notepad')
        check_tool('type_tool',{'text':'Hi Charan'},'notepad.exe','Untitled - Notepad')
    def test_history_completion_cancellation_and_metadata_only(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.cache'/'tmp') as tmp:
            root=Path(tmp); action={'kind':'desktop_task','appName':'Notepad','task':'Type synthetic text'}
            history=History('one',action,root); history.step('type_tool','running'); history.finish('succeeded','Agent-reported',12,3)
            History('one',action,root).finish('cancelled','Stopped')
            with closing(sqlite3.connect(history.db)) as con:
                row=con.execute('SELECT action,status,input_tokens,output_tokens FROM tasks').fetchone()
                self.assertEqual(json.loads(row[0]),action); self.assertEqual(row[1:],('cancelled',12,3))
                self.assertEqual(con.execute('SELECT tool,status FROM steps').fetchone(),('type_tool','running'))

if __name__ == '__main__': unittest.main()
