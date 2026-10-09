"""Offline state-machine checks: no Notion input, network, or Gemini calls."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notion_control import NotionController, page_id, validate_note


class ActionError(Exception):
    pass


class FakeControl:
    IsOffscreen = False
    def __init__(self, api, field, index=0): self.api, self.field, self.index = api, field, index; self.focus_ok=True
    @property
    def HasKeyboardFocus(self): return self.focus_ok and self.api.focus == self.field and (self.field != 'body' or self.index == len(self.api.data['body'].split('\n'))-1)
    @HasKeyboardFocus.setter
    def HasKeyboardFocus(self,value): self.focus_ok=value
    def GetPattern(self, _): return SimpleNamespace(Value=self.api.data[self.field] if self.field == 'title' else self.api.data['body'].split('\n')[self.index])
    def SetFocus(self): self.api.focus = self.field


class FakeApi:
    ActionError = ActionError
    def __init__(self):
        self.data = {'title':'Existing note', 'body':''}
        self.phase = 'original'; self.focus = None; self.private = True
        self.new_populated = False; self.reject_focus = False; self.drop_on_reload = False; self.readonly=False;self.new_readonly=False
        self.reloads = 0; self.writes = []; self.keys = []; self.have_body = False
        self.u = SimpleNamespace(PatternId=SimpleNamespace(ValuePattern=1))
        self.title, self.body = FakeControl(self,'title'), FakeControl(self,'body')
    def assert_desktop(self): pass
    def foreground(self): return 42
    def process_name(self, _): return 'notion.exe'
    def progress(self, _): pass
    def click(self, control, _): self.focus = control.field
    def wait(self, test, seconds): return test()
    def chord(self, modifier, code):
        self.keys.append(code)
        if code == 0x4E:
            self.phase='new'; self.data['title']='Already populated' if self.new_populated else ''
            self.readonly=self.new_readonly
        if code == 0x52:
            self.reloads += 1
            if self.drop_on_reload: self.data['body']=''
    def tap(self, code):
        if code == 0x0D:
            if self.focus == 'title': self.have_body=True
            else: self.data['body'] += '\n'; self.paragraph_start=len(self.data['body'])
    def type_text(self, text, handle, **kwargs):
        if kwargs.get('check_focus') and not kwargs['check_focus'](): raise ActionError('lost focus')
        self.writes.append(text); self.data[self.focus] += text
    def document(self):
        return {'doc':object(), 'id':self.phase, 'private':self.private, 'editable':not self.readonly, 'title':self.title, 'edits':[self.body]+[FakeControl(self,'body',i) for i in range(1,len(self.data['body'].split('\n')))] if self.have_body else []}


class Harness(NotionController):
    def document(self): return self.api.document()


class NotionWorkflow(unittest.TestCase):
    def setUp(self):
        self.sleep = patch('notion_control.time.sleep'); self.sleep.start(); self.addCleanup(self.sleep.stop)
    def test_title_and_multiple_paragraphs_survive_reload(self):
        api=FakeApi(); result=Harness(api).run('Demo — Charan','First paragraph.\nSecond paragraph.')
        self.assertEqual(api.data,{'title':'Demo — Charan','body':'First paragraph.\nSecond paragraph.'})
        self.assertEqual(api.reloads,1); self.assertIn('matched after reload',result)
    def test_readonly_start_does_not_create_or_write(self):
        api=FakeApi(); api.private=False; api.readonly=True
        with self.assertRaisesRegex(ActionError,'read-only'): Harness(api).append('Body')
        self.assertEqual(api.keys,[]); self.assertEqual(api.writes,[])
    def test_readonly_original_does_not_prevent_new_editable_page_creation(self):
        api=FakeApi();api.readonly=True
        Harness(api).run('New page','Body')
        self.assertEqual(api.data['body'],'Body')
    def test_new_readonly_page_is_not_typed_into(self):
        api=FakeApi();api.new_readonly=True
        with self.assertRaisesRegex(ActionError,'new editable page'):Harness(api).run('Demo','Body')
        self.assertFalse(api.writes)
    def test_shared_editable_page_can_create_a_new_note(self):
        api=FakeApi();api.private=False
        self.assertIn('matched after reload',Harness(api).run('Demo','Body'))
    def test_existing_shared_page_preserves_content_and_reload_verifies_append(self):
        api=FakeApi();api.private=False;api.have_body=True;api.data['body']='Keep this paragraph'
        result=Harness(api).append('Source: https://youtu.be/abcdefghijk\nComplete points')
        self.assertEqual(api.data['body'],'Keep this paragraph\nSource: https://youtu.be/abcdefghijk\nComplete points')
        self.assertIn('after reload',result);self.assertEqual(api.reloads,1)
    def test_complete_long_summary_is_not_truncated_to_note_limit(self):
        api=FakeApi();controller=Harness(api);controller.limit=20000
        body='Full saved content '+('word '*600)+'\nCaveat: check accuracy'
        controller.run('Saved summary',body)
        self.assertEqual(api.data['body'],body)
    def test_populated_new_page_is_never_overwritten(self):
        api=FakeApi(); api.new_populated=True
        with self.assertRaisesRegex(ActionError,'not empty'): Harness(api).run('Demo','Body')
        self.assertEqual(api.writes,[])
    def test_unverified_focus_prevents_typing(self):
        api=FakeApi(); api.title.HasKeyboardFocus=False
        with self.assertRaisesRegex(ActionError,'focus could not be verified'): Harness(api).run('Demo','Body')
        self.assertEqual(api.writes,[])
    def test_reload_loss_cannot_report_success(self):
        api=FakeApi(); api.drop_on_reload=True
        with self.assertRaisesRegex(ActionError,'after reload.*partial'): Harness(api).run('Demo','Body')
    def test_validation_and_page_identity(self):
        self.assertEqual(validate_note(' Demo ', 'One\nTwo'),('Demo','One\nTwo'))
        for title,body in [('', 'Body'), ('T\nX','Body'), ('T','\x00x'), ('T','x'*2001)]:
            with self.assertRaises(ValueError): validate_note(title,body)
        self.assertIsNone(page_id('https://example.com/'+ 'a'*32))
        self.assertEqual(page_id('https://www.notion.so/Demo-'+ 'a'*32+'?x=1'),'a'*32)


if __name__=='__main__': unittest.main()
