"""Conservative Notion workflow, independent of model-written coordinates/code.

English Notion desktop UI only. ValuePattern.SetValue is deliberately avoided:
Chromium contenteditable values can change visually without updating Notion's
editor state. Physical text input and reopening the page verify the real state.
"""
import re
import os
import time
from urllib.parse import urlparse


def validate_note(title, content, limit=2000):
    if not isinstance(title, str) or not title.strip() or len(title) > 160 or re.search(r'[\x00-\x1f\x7f]', title):
        raise ValueError('Provide a note title of 1–160 characters on one line.')
    if not isinstance(content, str) or not content.strip() or len(content) > limit or re.search(r'[\x00-\x08\x0b-\x1f\x7f]', content):
        raise ValueError(f'Provide plain-text note content of 1–{limit} characters.')
    return title.strip(), content.replace('\r\n', '\n')


def page_id(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('www.notion.so', 'notion.so'):
        return None
    match = re.search(r'([0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})$', parsed.path, re.I)
    return match.group(1).replace('-', '').lower() if match else None


class NotionController:
    def __init__(self, api):
        self.api = api
        self.handle = None
        self.created = False
        self.limit = 2000

    def fail(self, message):
        suffix = ' A blank or partial note may remain; inspect Notion before retrying.' if self.created else ''
        raise self.api.ActionError(message + suffix)

    def guard(self):
        self.api.assert_desktop()
        if self.api.foreground() != self.handle or self.api.process_name(self.handle) != 'notion.exe':
            self.fail('Another window took focus. AIRA stopped the Notion action.')

    def nodes(self, root):
        # Let UI Automation filter visibility in one native query rather than
        # walking thousands of Chromium parents/siblings across COM round trips.
        from uiautomation.uiautomation import _AutomationClient
        automation=_AutomationClient.instance().IUIAutomation
        elements=root.Element.FindAll(4,automation.CreatePropertyCondition(30022,False))
        if elements.Length>2500:
            self.fail('Notion accessibility tree is too large to verify safely.')
        output=[] if root.IsOffscreen else [root]
        for index in range(elements.Length):
            output.append(self.api.u.Control.CreateControlFromElement(elements.GetElement(index)))
        return output

    def value(self, control):
        try:
            value = control.GetPattern(self.api.u.PatternId.ValuePattern).Value
            return '' if value is None else value
        except Exception:
            self.fail('Notion did not expose a readable editor value.')

    def writable(self, control):
        try:
            return control.IsEnabled and not control.GetPattern(self.api.u.PatternId.ValuePattern).IsReadOnly
        except Exception:
            return False

    def editable(self, doc):
        if not doc.get('editable', False):
            self.fail('The selected Notion page is read-only, locked, or its edit permission could not be verified. No text was typed. Open an editable page; AIRA cannot grant permissions.')

    def document(self):
        import comtypes
        try:
            return self._document()
        except comtypes.COMError:
            # Chromium replaces its accessibility elements when opening a tab
            # or reloading. Retry observation, never retry the creation action.
            return None

    def _document(self):
        self.guard()
        root = self.api.u.ControlFromHandle(self.handle)
        matches = []
        # Hidden tabs can remain in Chromium's accessibility tree. The active
        # document must match the current window title and contain a main region.
        from uiautomation.uiautomation import _AutomationClient
        automation = _AutomationClient.instance().IUIAutomation
        condition = automation.CreateAndCondition(
            automation.CreatePropertyCondition(30003, 50030),  # Document type.
            automation.CreatePropertyCondition(30005, root.Name))
        elements = root.Element.FindAll(4, condition)
        if not elements.Length:
            # Current Chromium builds can expose a page document name without the
            # window's Notion suffix. Still require a real page URL and disambiguate
            # by focus/visible main editor below; never choose an arbitrary document.
            elements = root.Element.FindAll(4, automation.CreatePropertyCondition(30003,50030))
        if os.environ.get('AIRA_CONTROL_DIAGNOSTICS') == '1':
            self.api.emit(type='diagnostic', matchedDocuments=elements.Length)
        if elements.Length > 20:
            self.fail('Notion exposes too many matching tabs to identify the active page.')
        for index in range(elements.Length):
            control = self.api.u.Control.CreateControlFromElement(elements.GetElement(index))
            try:
                url = control.GetValuePattern().Value
                if os.environ.get('AIRA_CONTROL_DIAGNOSTICS') == '1':
                    parsed = urlparse(url)
                    self.api.emit(type='diagnostic', offscreen=control.IsOffscreen, hasPageId=bool(page_id(url)), notionHost=parsed.hostname in ('notion.so', 'www.notion.so'), pathLength=len(parsed.path))
                if not control.IsOffscreen and page_id(url):
                    matches.append(control)
            except Exception as error:
                if os.environ.get('AIRA_CONTROL_DIAGNOSTICS') == '1':
                    self.api.emit(type='diagnostic', documentError=type(error).__name__)
        # Several untitled tabs can share the same name. Chromium sometimes
        # reports hidden tab documents as onscreen, so use the focused control's
        # document ancestry to disambiguate instead of choosing the first match.
        focused = self.api.u.GetFocusedControl()
        for _ in range(40):
            if focused is None:
                break
            active = [c for c in matches if c.GetRuntimeId() == focused.GetRuntimeId()]
            if len(active) == 1:
                matches = active
                break
            focused = focused.GetParentControl()
        if len(matches) != 1:
            return None
        doc = matches[0]
        nodes = self.nodes(doc)
        if any(c.ControlTypeName=='TextControl' and re.fullmatch(r'Loading(?:\.{3}|…)?',c.Name,re.I) for c in nodes):
            return None
        mains = [c for c in nodes if c.AutomationId == 'main']
        if os.environ.get('AIRA_CONTROL_DIAGNOSTICS') == '1':
            self.api.emit(type='diagnostic', validDocuments=len(matches), mainRegions=len(mains))
        if len(mains) != 1:
            return None
        main_nodes = self.nodes(mains[0])
        titles = [c for c in main_nodes if c.LocalizedControlType.lower() == 'page title']
        if os.environ.get('AIRA_CONTROL_DIAGNOSTICS') == '1':
            self.api.emit(type='diagnostic', titleControls=len(titles))
        if len(titles) != 1:
            return None
        headers = [c for c in nodes if c.AriaRole == 'banner' or c.LocalizedControlType.lower() == 'header']
        private = any(c.ControlTypeName == 'ButtonControl' and c.Name == 'Private'
                      for header in headers for c in self.nodes(header))
        edits = [c for c in main_nodes if c.ControlTypeName == 'EditControl' and c.LocalizedControlType.lower() != 'page title']
        locked = any(re.fullmatch(r'(?:Page )?Locked|Unlock page|View only|Can view|Request access', c.Name, re.I)
                     for c in nodes if c.ControlTypeName in ('ButtonControl','TextControl'))
        return {'doc': doc, 'id': page_id(self.value(doc)), 'title': titles[0], 'edits': edits, 'private': private,
                'editable': not locked and self.writable(titles[0]) and all(self.writable(c) for c in edits)}

    def require(self, predicate, message, seconds=12):
        value = self.api.wait(predicate, seconds)
        if not value:
            self.fail(message)
        return value

    def page(self, expected_id):
        return self.require(lambda: (doc if (doc := self.document()) and doc['id'] == expected_id and doc.get('editable') else None), 'The intended editable Notion page could not be verified.', 3)

    def focus(self, control):
        self.guard()
        self.api.click(control, self.handle)
        control.SetFocus()
        self.guard()
        # Chromium can report document focus instead of its contenteditable.
        # Require the actual editable control's keyboard-focus property too.
        if not self.api.wait(lambda: control.HasKeyboardFocus, 2):
            self.fail('Notion editor focus could not be verified. No text was typed.')

    def run(self, title, content):
        try:
            title, content = validate_note(title, content, self.limit)
        except ValueError as error:
            self.fail(str(error))
        if self.api.process_name(self.api.foreground()) != 'notion.exe':
            self.api.open_app('Notion')
        self.handle = self.api.foreground()
        original = self.require(self.document, 'Open a normal Notion page in your signed-in workspace first. Login, Home-only and unexpected dialogs are not automated.')
        self.api.progress('Creating a Notion page in the selected workspace')
        self.guard()
        self.api.chord(0x11, 0x4E)  # Notion's documented Ctrl+N shortcut.
        self.created = True  # A page can exist even if the subsequent observation fails.
        # Current Notion opens a Create new menu, older versions open the page
        # directly. Only select the ordinary Page entry inside that named menu.
        def creation_state():
            doc = self.document()
            if doc and doc['id'] != original['id']:
                return ('page', doc)
            # Re-observe the window instead of traversing the old page's stale COM tree.
            control=self.api.u.ControlFromHandle(self.handle).WindowControl(searchDepth=16,Name='Create new')
            if control.Exists(.05) and not control.IsOffscreen:
                items = [c for c in self.nodes(control) if c.ControlTypeName == 'MenuItemControl' and re.fullmatch(r'Page(?: Press 1)?', c.Name)]
                if len(items) == 1:
                    return ('menu', items[0])
            return None
        kind, value = self.require(creation_state, 'Notion did not expose its Create new page control.')
        if kind == 'menu':
            self.guard()
            self.api.click(value, self.handle)
        self.created = True
        new = self.require(lambda: (d if (d := self.document()) and d['id'] != original['id'] and d.get('editable') else None), 'Notion did not expose a new editable page.', 25)
        note_id = new['id']
        return self.finish(note_id, title, content)

    def append(self, content):
        validate_note('Append', content, self.limit)
        self.handle=self.api.foreground()
        original=self.require(self.document,'Open the intended Notion page first. Its current editor could not be identified.',5)
        self.editable(original)
        note_id=original['id']
        title=self.value(original['title'])
        baseline='\n'.join(self.value(c).replace('\r\n','\n') for c in original['edits'])
        if len(baseline)>200000: self.fail('This page is too large for direct readback. Use a Windows-Use task.')
        if not original['edits']:
            self.focus(original['title'])
            self.api.chord(0x11,0x23)
            self.api.tap(0x0D)
        def same_page():
            doc=self.document()
            return doc if doc and doc['id']==note_id and doc.get('editable') and self.value(doc['title'])==title else None
        current=self.require(lambda: (doc if (doc:=same_page()) and doc['edits'] else None),'The intended Notion body editor is not available.',3)
        paragraph=current['edits'][-1]
        self.focus(paragraph)
        self.api.chord(0x11,0x23)
        self.guard()
        if not paragraph.HasKeyboardFocus: self.fail('Notion body focus changed. No text was typed.')
        expected=baseline
        self.api.progress('Appending requested text to the current Notion page')
        def next_paragraph():
            doc=same_page()
            if not doc: return None
            candidates=[c for c in doc['edits'] if c.HasKeyboardFocus and not self.value(c)]
            return candidates[0] if len(candidates)==1 else None
        if baseline:
            self.api.tap(0x0D)
            expected+='\n'
            paragraph=self.require(next_paragraph,'The new Notion paragraph could not be identified. Inspect the page before retrying.',3)
        for index,line in enumerate(content.replace('\r\n','\n').split('\n')):
            if index:
                self.guard();self.api.tap(0x0D)
                paragraph=self.require(next_paragraph,'The next Notion paragraph did not become ready. Inspect partial text before retrying.',3)
            self.api.type_text(line,self.handle,delay=.002,check_focus=lambda:paragraph.HasKeyboardFocus,batch_units=16 if self.limit>2000 else 1)
            self.guard();self.api.tap(0x1B)
        expected+=content.replace('\r\n','\n')
        self.require(lambda:self.matches(note_id,title,expected),'Notion text readback did not match the expected page. Inspect partial changes before retrying.',4)
        self.api.progress('Reopening the page to verify the appended text')
        self.guard(); self.api.chord(0x11,0x52)
        time.sleep(1)
        self.require(lambda:self.matches(note_id,title,expected),'The appended text could not be verified after reload. Inspect partial changes before retrying.',15)
        return 'Requested text was appended to the selected Notion page and matched after reload. Notion server sync was not independently verified.'

    def finish(self, note_id, title, content, *, resume_title=False):
        # Shared with an explicit developer diagnostic that can finish only an
        # identified blank test page. The application IPC never exposes resume.
        title, content = validate_note(title, content, self.limit)
        new = self.page(note_id)
        existing_title = self.value(new['title'])
        if (existing_title.strip() and not (resume_title and existing_title == title)) or any(self.value(c).strip() for c in new['edits']):
            self.fail('The new note is not empty. Existing content was not overwritten.')
        if not existing_title:
            self.api.progress('Writing the note title')
            self.focus(new['title'])
            self.api.type_text(title, self.handle, check_focus=lambda: new['title'].HasKeyboardFocus)
        self.require(lambda: self.value(self.page(note_id)['title']) == title, 'The requested title was not received.')
        # End prevents Enter from splitting the title at its click position.
        if not self.page(note_id)['edits']:
            self.focus(self.page(note_id)['title'])
            self.guard()
            self.api.chord(0x11, 0x23)  # Ctrl+End inside the verified title.
            self.api.tap(0x0D)
        new = self.require(lambda: (d if (d := self.page(note_id))['edits'] else None), 'Notion did not expose a body editor.')
        if self.value(new['title']) != title or len(new['edits']) != 1 or self.value(new['edits'][0]).strip():
            self.fail('Notion did not provide one empty paragraph. Body entry stopped.')
        self.api.progress('Writing the note content')
        self.focus(new['edits'][0])
        paragraph = new['edits'][0]
        # Literal input, not clipboard paste or UIA SetValue. Newlines create
        # paragraphs. Fresh focus is checked before each character by the host.
        for index, line in enumerate(content.split('\n')):
            if index:
                self.guard()
                self.api.tap(0x0D)
                time.sleep(.15)
                current = self.page(note_id)
                candidates = [c for c in current['edits'] if c.HasKeyboardFocus and not self.value(c).strip()]
                if len(candidates) != 1:
                    self.fail('The next empty paragraph did not receive focus. Body entry stopped.')
                paragraph = candidates[0]
            self.api.type_text(line, self.handle, delay=.002, check_focus=lambda: paragraph.HasKeyboardFocus,batch_units=16 if self.limit>2000 else 1)
            # Close slash/mention suggestions rather than allowing the next
            # Enter to choose an unintended command or mention.
            self.guard()
            self.api.tap(0x1B)
        self.guard()
        self.api.tap(0x1B)
        time.sleep(.5)
        self.require(lambda: self.matches(note_id, title, content), 'The entered title/content did not match. This version supports plain text paragraphs only.')
        self.api.progress('Reopening the note to verify it')
        self.guard()
        self.api.chord(0x11, 0x52)  # Reload current page; no URL or command typed.
        time.sleep(1)
        self.require(lambda: self.matches(note_id, title, content), 'The note could not be verified after reload. Server sync is not confirmed.', 15)
        return 'Notion note created in the selected workspace. Title and content matched after reload; server sync is not independently verified.'

    def matches(self, note_id, title, content):
        doc = self.document()
        if not doc or doc['id'] != note_id or not doc.get('editable') or self.value(doc['title']) != title:
            return False
        actual = '\n'.join(self.value(c).replace('\r\n', '\n') for c in doc['edits'])
        return actual.strip() == content.strip()

    def select_page(self, name):
        """Use Notion search only for an exact, unambiguous requested title."""
        current = self.document()
        if current and self.value(current['title']) == name:
            return
        self.guard(); self.api.chord(0x11, 0x50)
        def search_dialog():
            root = self.api.u.ControlFromHandle(self.handle)
            dialogs = [c for c in self.nodes(root) if c.AriaRole == 'dialog' or
                       (c.ControlTypeName == 'WindowControl' and re.search(r'search', c.Name, re.I))]
            matches = [(d, [c for c in self.nodes(d) if c.ControlTypeName == 'EditControl']) for d in dialogs]
            matches = [(d, e[0]) for d, e in matches if len(e) == 1]
            return matches[0] if len(matches) == 1 else None
        dialog, field = self.require(search_dialog, 'Notion search is not identifiable. Open the intended page manually, then export to the selected page.', 4)
        self.focus(field); self.api.chord(0x11, 0x41)
        self.api.type_text(name, self.handle, delay=.002, check_focus=lambda:field.HasKeyboardFocus)
        def exact_result():
            state = search_dialog()
            if not state: return None
            candidates = [c for c in self.nodes(state[0]) if c.ControlTypeName in ('ListItemControl','ButtonControl')
                          and c.Name.strip().split('\n')[0] == name]
            return candidates[0] if len(candidates) == 1 else None
        result = self.require(exact_result, 'No unique exact Notion page title was found. Open the intended page manually; nothing was appended.', 8)
        self.guard(); self.api.click(result, self.handle)
        self.require(lambda: (d if (d:=self.document()) and self.value(d['title'])==name else None),
                     'The requested Notion page did not open. Nothing was appended.', 10)

    def export(self, request):
        self.limit = 20000
        title, content = validate_note(request.get('title'), request.get('content'), self.limit)
        destination = request.get('destination')
        name = request.get('pageName', '')
        if destination not in ('new', 'existing') or not isinstance(name,str) or len(name)>160 or re.search(r'[\x00-\x1f\x7f]',name) or (destination=='new' and name):
            self.fail('Choose a new page or an exact existing page title; leave the existing title empty for the selected page.')
        if self.api.process_name(self.api.foreground()) != 'notion.exe':
            self.api.open_app('Notion')
        self.handle = self.api.foreground()
        if destination == 'existing':
            if name: self.select_page(name)
            message = self.append(content)
        else:
            message = self.run(title, content)
        doc = self.require(self.document, 'The destination page could not be read after export.')
        return message, {'notionPageId':doc['id'], 'destinationTitle':self.value(doc['title'])}
