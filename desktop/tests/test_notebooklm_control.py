"""Execute the actual workflow against a rendered-control fixture; no Chrome/API."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from notebooklm_control import NotebookLMController, notebook_url

VIDEO='https://www.youtube.com/watch?v=abcdefghijk'

class ActionError(Exception):pass

class Group:
    def __init__(self,items=()):self.items=list(items)
    def all(self):return self.items
    def count(self):return len(self.items)
    def filter(self,**kwargs):return self
    def is_checked(self):return self.first.is_checked()
    def set_checked(self,value,**kwargs):return self.first.set_checked(value,**kwargs)
    @property
    def first(self):return self.items[0]

class Element:
    def __init__(self,page,name):self.page=page;self.name=name;self.checked=False
    def is_visible(self):return True
    def is_enabled(self):return self.name!='generate' or not self.page.disabled
    def is_editable(self):return True
    def inner_text(self):return {'source':'Atoms video','artifact':'account_tree Atoms Mind Map'}.get(self.name,self.name)
    def get_attribute(self,name):return 'YouTube URL' if name=='placeholder' and self.name=='input' else None
    def scroll_into_view_if_needed(self):pass
    def evaluate(self,_):pass
    def fill(self,text):self.page.entered=text
    def input_value(self):return self.page.entered
    def is_checked(self):return self.checked
    def set_checked(self,value,**kwargs):self.checked=value
    def bounding_box(self):return {'width':400,'height':300}
    def locator(self,selector):return Group([object(),object(),object()]) if self.name=='diagram' else Group()
    def get_by_role(self,role,**kwargs):
        if role=='checkbox':return Group([self.page.check])
        if self.name=='dialog':
            if role=='button':
                expr=kwargs['name']
                return Group([self.page.elements['insert']]) if expr.search('Insert') else Group([self.page.elements['website']])
        if self.name=='Studio' and role=='button':return Group([self.page.elements['generate']])
        return Group()
    def click(self,**kwargs):
        self.page.events.append(self.name)
        if self.name=='create':self.page.url='https://notebook.google.com/notebook/new-id';self.page.dialog=True
        elif self.name=='website':self.page.url_dialog=True
        elif self.name=='insert':self.page.dialog=False;self.page.imported=True
        elif self.name=='generate':self.page.generated=True
        elif self.name=='artifact':self.page.opened=True

class Dialog(Element):
    def locator(self,selector):return Group([self.page.elements['input']]) if self.page.url_dialog else Group()

class Page:
    def __init__(self):
        self.url='https://notebooklm.google.com/';self.dialog=False;self.url_dialog=False
        self.imported=False;self.generated=False;self.opened=False;self.entered='';self.events=[];self.disabled=False
        self.elements={name:Element(self,name) for name in ('create','website','input','insert','source','generate','artifact','diagram')}
        self.elements['dialog']=Dialog(self,'dialog');self.check=Element(self,'check')
    def goto(self,url,**kwargs):self.url=url
    def wait_for_timeout(self,_):pass
    def get_by_role(self,role,**kwargs):
        if role=='alert':return Group()
        if role=='heading':return Group([Element(self,'Sources')])
        if role=='dialog':return Group([self.elements['dialog']]) if self.dialog else Group()
        if role=='button':return Group([self.elements['create']])
        return Group()
    def locator(self,selector):return Group([self.elements['diagram']]) if selector=='svg' and self.opened else Group()

class Harness(NotebookLMController):
    def panel(self,label):return Element(self.page,label)
    def source_rows(self):return [self.page.elements['source']] if self.page.imported else []
    def artifacts(self):return [self.page.elements['artifact']] if self.page.generated else []

class NotebookTests(unittest.TestCase):
    def fixture(self):
        page=Page()
        browser=SimpleNamespace(ready=lambda _:page,context=SimpleNamespace(new_page=lambda:page),show_owned_window=lambda *args:None)
        api=SimpleNamespace(ActionError=ActionError,progress=lambda _:None,wait=lambda test,seconds:test())
        return page,Harness(browser,api)
    def test_new_notebook_import_select_generate_and_open_sequence(self):
        page,controller=self.fixture()
        message,data=controller.run({'videoUrl':VIDEO,'newNotebook':True})
        self.assertEqual(page.events,['create','website','insert','generate','artifact'])
        self.assertEqual(page.entered,VIDEO);self.assertTrue(page.check.checked)
        self.assertTrue(page.opened);self.assertIn('diagram is open',message)
        self.assertEqual(data['notebookUrl'],'https://notebook.google.com/notebook/new-id')
    def test_disabled_generation_retains_partial_link_without_claiming_success(self):
        page,controller=self.fixture();page.disabled=True
        with self.assertRaisesRegex(ActionError,'disabled') as result:controller.run({'videoUrl':VIDEO})
        self.assertTrue(page.imported);self.assertFalse(page.generated)
        self.assertEqual(result.exception.data['notebookUrl'],'https://notebook.google.com/notebook/new-id')
        self.assertNotIn('generate',page.events)
    def test_invalid_input_prevents_creation(self):
        page,controller=self.fixture()
        with self.assertRaises(ActionError):controller.run({'videoUrl':'https://evil.test'})
        self.assertEqual(page.events,[])
    def test_only_explicit_notebook_hosts_and_paths_are_allowed(self):
        for uri in ('http://notebook.google.com/notebook/a','https://notebook.google.com.evil.test/notebook/a','https://notebooklm.google.com/notebook/a/../b','https://user@notebook.google.com/notebook/a'):
            with self.assertRaises(ValueError):notebook_url(uri)

if __name__=='__main__':unittest.main()
