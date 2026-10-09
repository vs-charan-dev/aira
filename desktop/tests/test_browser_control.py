"""Offline regressions: no Chrome launch, GUI input, network or Gemini calls."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_control import BrowserController, RESULT_TITLES


class ActionError(Exception):
    pass


API = SimpleNamespace(ActionError=ActionError, progress=lambda label: None)
VIDEO = 'https://www.youtube.com/watch?v=abcdefghijk'


class Link:
    def __init__(self, page):
        self.page = page
        self.clicked = False

    def get_attribute(self, name):
        return '/watch?v=abcdefghijk&feature=share'

    def evaluate(self, expression):
        return True

    def scroll_into_view_if_needed(self):
        pass

    def click(self):
        self.clicked = True
        self.page.url = 'https://www.youtube.com/watch?feature=share&v=abcdefghijk'


class Locator:
    def __init__(self, page, links=None):
        self.page = page
        self.links = links or []

    @property
    def first(self):
        return self

    def fill(self, query):
        self.page.typed = query

    def press(self, key):
        raise AssertionError('Search must not depend on a simulated keyboard event.')

    def all(self):
        return self.links


class Page:
    def __init__(self, *, stale_document=False, status=200, visible=True):
        self.url = self.document_url = 'https://www.youtube.com'
        self.stale_document = stale_document
        self.status = status
        self.visible = visible
        self.navigation = []
        self.typed = ''
        self.links = [Link(self), Link(self)]

    def goto(self, url, **kwargs):
        self.navigation.append(url)
        self.url = url
        self.document_url = 'https://www.youtube.com' if self.stale_document else url
        return SimpleNamespace(status=self.status)

    def locator(self, selector):
        return Locator(self, self.links if selector == RESULT_TITLES else [])

    def evaluate(self, expression):
        if expression == 'location.href': return self.document_url
        if expression.startswith('document.visibilityState'): return self.visible
        raise AssertionError('Unexpected page script')

    def bring_to_front(self):
        pass

    def is_closed(self):
        return False

    def wait_for_url(self, predicate, **kwargs):
        if not predicate(self.url): raise TimeoutError()

    def title(self):
        return 'Observed video - YouTube'


class Session:
    def __init__(self):
        self.commands = []
        self.detached = False

    def send(self, method, params=None):
        self.commands.append((method, params))
        return {'windowId': 42} if method == 'Browser.getWindowForTarget' else {}

    def detach(self):
        self.detached = True


class BrowserRegressions(unittest.TestCase):
    def maps_controller(self, *, fails=False, status=200):
        controller=BrowserController()
        youtube=Page(); invoice=Page()
        pages=[youtube,invoice]
        def new_page():
            page=Page(status=status);page.maps_queries=[]
            def wait_for_function(expression,**kwargs):
                self.assertIn('box.value',expression)
                page.maps_queries.append(kwargs['arg'])
                if fails: raise TimeoutError()
            page.wait_for_function=wait_for_function
            pages.append(page);return page
        controller.context=SimpleNamespace(pages=pages,new_page=new_page)
        controller.page=controller.youtube_page=youtube;controller.invoice_page=invoice
        controller.show_owned_window=lambda *args:None
        return controller

    def test_maps_submits_encoded_literal_place_and_preserves_other_tabs(self):
        controller=self.maps_controller()
        query='Café & Park, హైదరాబాద్'
        message,_=controller.run(API,{'kind':'search_maps','query':query})
        from urllib.parse import parse_qs,urlparse
        self.assertEqual(parse_qs(urlparse(controller.maps_page.url).query),{'api':['1'],'query':[query]})
        self.assertEqual(controller.maps_page.maps_queries,[query])
        self.assertIn(query,message)
        self.assertEqual(controller.youtube_page.navigation,[])
        self.assertEqual(controller.invoice_page.navigation,[])
        maps=controller.maps_page
        controller.run(API,{'kind':'open_maps'})
        self.assertIs(controller.maps_page,maps)
        self.assertEqual(len(controller.context.pages),3)

    def test_maps_consent_stale_query_or_missing_results_never_reports_success(self):
        with self.assertRaisesRegex(ActionError,'could not be verified'):
            self.maps_controller(fails=True).run(API,{'kind':'search_maps','query':'Hyderabad'})
        with self.assertRaisesRegex(ActionError,'did not load'):
            self.maps_controller(status=503).run(API,{'kind':'search_maps','query':'Hyderabad'})

    def test_invalid_maps_query_does_not_launch_browser(self):
        for query in ('',' ','x'*251,'Hyderabad\n',None):
            with self.assertRaisesRegex(ActionError,'place name'):
                BrowserController().run(API,{'kind':'search_maps','query':query})

    def test_invoice_and_youtube_use_separate_reusable_tabs(self):
        controller=BrowserController();pages=[Page()]
        pages[0].url=pages[0].document_url='about:blank'
        def new_page():
            page=Page();page.url=page.document_url='about:blank';pages.append(page);return page
        controller.context=SimpleNamespace(pages=pages,new_page=new_page)
        controller.page=pages[0]
        shown=[];controller.show_owned_window=lambda api,page:shown.append(page)
        controller.read_results=lambda *args:[]
        url='http://127.0.0.1:8000/invoice-demo'
        controller.run(API,{'kind':'show_invoice_demo','url':url})
        invoice=controller.invoice_page
        controller.run(API,{'kind':'search_youtube','query':'atomic model'})
        youtube=controller.youtube_page
        self.assertIsNot(invoice,youtube);self.assertEqual(invoice.navigation,[url])
        self.assertEqual(len(pages),2)
        self.assertIn('/results?',youtube.url)
        controller.run(API,{'kind':'show_invoice_demo','url':url})
        self.assertIs(controller.invoice_page,invoice);self.assertEqual(invoice.navigation,[url])
        self.assertIs(shown[-1],invoice);self.assertIn('/results?',youtube.url)

    def test_invoice_navigation_refuses_remote_or_unrelated_urls(self):
        for url in ('https://example.com/invoice-demo','http://127.0.0.1:8000/palace','http://localhost:8000/invoice-demo?x=1'):
            with self.assertRaisesRegex(ActionError,'local invoice URL'):
                BrowserController().run(API,{'kind':'show_invoice_demo','url':url})

    def test_search_loads_exact_encoded_query_without_keyboard_handlers(self):
        page = Page()
        BrowserController().submit_search(API, page, 'atoms & electrons + ions')
        self.assertEqual(page.typed, 'atoms & electrons + ions')
        self.assertEqual(page.navigation[-1], 'https://www.youtube.com/results?search_query=atoms+%26+electrons+%2B+ions')

    def test_matching_automation_url_with_home_document_is_not_success(self):
        with self.assertRaisesRegex(ActionError, 'did not open results'):
            BrowserController().submit_search(API, Page(stale_document=True), 'atomic model')

    def test_failed_http_response_is_not_success(self):
        with self.assertRaisesRegex(ActionError, 'search response'):
            BrowserController().submit_search(API, Page(status=503), 'atomic model')

    def test_duplicate_video_links_and_reordered_final_parameters(self):
        page = Page()
        page.url = 'https://www.youtube.com/results?search_query=atomic+model'
        data = BrowserController().open_video(API, page, VIDEO)
        self.assertTrue(page.links[0].clicked)
        self.assertFalse(page.links[1].clicked)
        self.assertEqual(data['videoUrl'], VIDEO)

    def test_restore_uses_window_id_from_owned_tab(self):
        session = Session()
        controller = BrowserController()
        controller.context = SimpleNamespace(new_cdp_session=lambda page: session)
        controller.show_owned_window(API, Page())
        self.assertEqual([params['windowId'] for method, params in session.commands if method == 'Browser.setWindowBounds'], [42, 42])
        self.assertTrue(session.detached)

    def test_hidden_owned_window_does_not_report_success(self):
        session = Session()
        controller = BrowserController()
        controller.context = SimpleNamespace(new_cdp_session=lambda page: session)
        with self.assertRaisesRegex(ActionError, 'not visible'):
            controller.show_owned_window(API, Page(visible=False))
        self.assertTrue(session.detached)

    def current_controller(self, *, focused=False, foreground='electron.exe', stale=False):
        page=Page()
        page.url=VIDEO
        page.document_url='https://www.youtube.com' if stale else VIDEO
        page.is_closed=lambda: False
        evaluate=page.evaluate
        page.evaluate=lambda expression: focused if expression=='document.hasFocus()' else evaluate(expression)
        controller=BrowserController()
        controller.page=page
        controller.context=SimpleNamespace(pages=[page])
        api=SimpleNamespace(ActionError=ActionError, foreground=lambda: 1, process_name=lambda handle: foreground)
        return controller,api

    def test_selected_video_read_survives_aira_overlay_focus(self):
        controller,api=self.current_controller()
        self.assertEqual(controller.current(api)['videoUrl'],VIDEO)

    def test_focused_owned_video_read(self):
        controller,api=self.current_controller(focused=True,foreground='chrome.exe')
        self.assertEqual(controller.current(api)['videoUrl'],VIDEO)

    def test_invoice_focus_does_not_replace_the_selected_video(self):
        controller,api=self.current_controller(foreground='chrome.exe')
        controller.youtube_page=controller.page
        invoice=Page();invoice.url=invoice.document_url='http://127.0.0.1:8000/invoice-demo'
        invoice.evaluate=lambda expression: expression=='document.hasFocus()'
        controller.context.pages.append(invoice)
        self.assertEqual(controller.current(api)['videoUrl'],VIDEO)

    def test_personal_chrome_is_not_substituted_with_last_owned_tab(self):
        controller,api=self.current_controller(foreground='chrome.exe')
        with self.assertRaisesRegex(ActionError,'not controlled by AIRA'):
            controller.current(api)

    def test_video_read_rejects_non_video_document(self):
        controller,api=self.current_controller(stale=True)
        with self.assertRaises(ActionError):
            controller.current(api)


if __name__ == '__main__':
    unittest.main()
