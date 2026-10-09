"""Visible NotebookLM workflow in the owned AIRA Chrome context.

Fixed code observes rendered controls and verifies new source/artifact state.
No model-authored scripts, personal-profile access, login or sharing changes.
"""
import re
from urllib.parse import urlparse
from browser_control import video_url

HOSTS = ('notebooklm.google.com', 'notebook.google.com')


def notebook_url(value):
    if not isinstance(value, str) or len(value) > 1000:
        raise ValueError('Provide a NotebookLM notebook URL.')
    uri = urlparse(value.strip())
    if (uri.scheme != 'https' or uri.hostname not in HOSTS or uri.username or uri.password
            or uri.port not in (None,443) or not re.fullmatch(r'/notebook/[a-zA-Z0-9_-]{1,100}/?',uri.path)):
        raise ValueError('Use an HTTPS NotebookLM notebook link.')
    return f'https://{uri.hostname}{uri.path}'


class NotebookLMController:
    def __init__(self, browser, api):
        self.browser, self.api = browser, api
        self.page = None
        self.changed = False
        self.video = None

    def fail(self, message):
        suffix = ' A notebook, source or generation may already exist; inspect NotebookLM before making a new request.' if self.changed else ''
        error=self.api.ActionError(message + suffix)
        if self.page and self.video:
            try: error.data={'notebookUrl':notebook_url(self.page.url),'videoUrl':self.video}
            except ValueError: pass
        raise error

    def guard(self):
        uri = urlparse(self.page.url)
        if uri.scheme != 'https' or uri.hostname not in HOSTS:
            self.fail('Sign in to Google manually in AIRA Chrome using Sign-In-AIRA-Chrome.cmd, then restart AIRA. The NotebookLM page is not available.')
        alert = self.page.get_by_role('alert').filter(has_text=re.compile(r'permission|access denied|failed|unable|limit|error',re.I))
        if alert.count() and alert.first.is_visible():
            self.fail('NotebookLM reported an access, import or usage-limit error. Check the visible page.')

    def unique(self, locator, purpose):
        visible = [c for c in locator.all() if c.is_visible()]
        if len(visible) != 1:
            self.fail(f'The {purpose} control is missing or ambiguous. Check the visible NotebookLM page; no guessed click was made.')
        return visible[0]

    def click(self, control):
        self.guard()
        if not control.is_enabled():
            self.fail('The requested NotebookLM control is disabled. The notebook may be read-only or the source is still processing.')
        control.scroll_into_view_if_needed()
        control.evaluate("el => { el.style.outline='3px solid #528bff'; }")
        control.click(timeout=10000)

    def panel(self, label):
        self.guard()
        heading=self.page.get_by_role('heading',name=label,exact=True)
        navigation=self.page.get_by_role('navigation').filter(has=heading)
        candidates=[c for c in navigation.all() if c.is_visible()]
        if len(candidates)==1: return candidates[0]
        tags = 'sources-panel, source-panel, .sources-panel' if label=='Sources' else 'studio-panel, .studio-panel'
        candidates = [c for c in self.page.locator(tags).all() if c.is_visible()]
        if len(candidates)==1: return candidates[0]
        # Locate the rendered three-column panel from its observed label and
        # geometry, rather than hardcoding screen coordinates from a screenshot.
        node = self.unique(self.page.get_by_text(label, exact=True), label + ' panel heading')
        width = self.page.evaluate('() => innerWidth')
        for _ in range(9):
            node = node.locator('xpath=..')
            rect = node.bounding_box()
            if rect and 150 <= rect['width'] < width*.6 and rect['height'] >= 200:
                return node
        self.fail(f'The {label} panel could not be identified in this layout.')

    def wait(self, predicate, message, seconds=20):
        result = self.api.wait(predicate, seconds)
        if not result: self.fail(message)
        return result

    def source_rows(self):
        panel = self.panel('Sources')
        for selector in ('source-item', '.single-source-container', '[data-source-id]'):
            visible=[r for r in panel.locator(selector).all() if r.is_visible()]
            if visible: return visible
        # Source checkboxes have their own rendered row; exclude Select all.
        checks = [c for c in panel.get_by_role('checkbox',name=re.compile(r'^(?!Select all)',re.I)).all() if c.is_visible()]
        result=[]
        for check in checks:
            row=check.locator('xpath=..')
            for _ in range(4):
                text=(row.inner_text() or '').strip()
                if text and row.get_by_role('button').count()>0 and row.get_by_role('checkbox').count()==1:
                    result.append(row); break
                row=row.locator('xpath=..')
        return result

    def artifacts(self):
        studio = self.panel('Studio')
        result=[]
        for selector in ('artifact-library-item','artifact-item','.artifact-item','[data-artifact-id]'):
            result=[r for r in studio.locator(selector).all() if r.is_visible()]
            if result: break
        if not result:
            # Existing artifact rows expose either an accessible mind-map name
            # or a fixed Material icon. Never treat the Generate button as an artifact.
            result = [r for r in studio.locator('[role="button"], button, .artifact-row').all()
                      if r.is_visible() and re.search(r'account_tree|mind.?map',r.inner_text()+' '+(r.get_attribute('aria-label') or ''),re.I)
                      and not re.fullmatch(r'(?:account_tree\s*)?Mind Map',r.inner_text().strip(),re.I)]
        return result

    @staticmethod
    def fingerprint(row):
        return (row.get_attribute('data-artifact-id') or row.get_attribute('data-source-id') or '', row.inner_text().strip())

    def run(self, request):
        try:
            video = video_url(request.get('videoUrl'))
            self.video = video
            new = request.get('newNotebook', True)
            if not isinstance(new,bool): raise ValueError('Choose a new or existing notebook.')
            target = notebook_url(request['notebookUrl']) if request.get('notebookUrl') else None
            if new and target: raise ValueError('Choose a new notebook or an existing link, not both.')
        except ValueError as error: self.fail(str(error))
        self.browser.ready(self.api)
        if not new and not target:
            pages = [p for p in self.browser.context.pages if not p.is_closed() and
                     urlparse(p.url).hostname in HOSTS and '/notebook/' in urlparse(p.url).path]
            if len(pages)!=1: self.fail('Open exactly one intended notebook in AIRA Chrome, or provide its notebook URL.')
            self.page=pages[0]
        else:
            self.page=self.browser.context.new_page()
            self.browser.page=self.page
            self.page.goto(target or 'https://notebooklm.google.com/',wait_until='domcontentloaded',timeout=30000)
        self.browser.page=self.page
        self.browser.show_owned_window(self.api,self.page)
        self.page.wait_for_timeout(1000)
        self.guard()
        if new:
            self.api.progress('Creating a NotebookLM notebook')
            create = self.page.get_by_role('button',name=re.compile(r'(?:add\s+)?(?:Create (?:a )?(?:new )?notebook|New notebook|Create new)$',re.I))
            self.wait(lambda: create.count() and create.first.is_visible(), 'NotebookLM did not show Create notebook. Check sign-in and loading.', 15)
            button=self.unique(create,'Create notebook')
            self.changed=True; self.click(button)
            self.wait(lambda:'/notebook/' in urlparse(self.page.url).path,'The new notebook did not open.',20)
        try: destination=notebook_url(self.page.url)
        except ValueError: self.fail('NotebookLM did not open a notebook.')
        self.wait(lambda:self.page.get_by_role('heading',name='Sources',exact=True).count()>0,
                  'The notebook Sources panel did not finish loading.',20)
        # New notebooks may already show Add sources. Existing ones require its button.
        before=[self.fingerprint(r) for r in self.source_rows()]
        dialogs=self.page.get_by_role('dialog')
        visible_dialogs=[d for d in dialogs.all() if d.is_visible()]
        if not visible_dialogs:
            add=self.panel('Sources').get_by_role('button',name=re.compile(r'(?:add\s+)?Add sources?$',re.I))
            self.click(self.unique(add,'Add sources'))
        dialog=self.unique(self.page.get_by_role('dialog'),'Add sources dialog')
        self.api.progress('Adding the YouTube link as a NotebookLM source')
        inputs=dialog.locator('input:not([type="file"]):visible, textarea:visible')
        # The sources chooser contains Website / YouTube, not a URL input yet.
        if not any(re.search(r'url|link|website|youtube', ' '.join(str(c.get_attribute(a) or '') for a in ('placeholder','aria-label')),re.I) for c in inputs.all()):
            choice=dialog.get_by_role('button',name=re.compile(r'YouTube|Websites?|Links?',re.I))
            options=[c for c in choice.all() if c.is_visible()]
            youtube=[c for c in options if re.search('youtube',c.inner_text()+' '+(c.get_attribute('aria-label') or ''),re.I)]
            self.click(youtube[0] if len(youtube)==1 else self.unique(choice,'Website / YouTube link'))
            dialog=self.unique(self.page.get_by_role('dialog'),'link dialog')
        field=self.unique(dialog.locator('input:not([type="file"]):visible, textarea:visible'),'source URL input')
        if not field.is_editable(): self.fail('The source URL input is read-only.')
        field.fill(video)
        if field.input_value().strip()!=video: self.fail('The video link was not received by NotebookLM.')
        insert=self.unique(dialog.get_by_role('button',name=re.compile(r'^(?:Insert(?: links?| sources?)?|Add(?: links?| sources?)?|Import(?: sources?)?)$',re.I)),'Insert source')
        self.changed=True; self.click(insert)
        self.api.progress('Waiting for NotebookLM to import captions')
        def imported():
            self.guard()
            if any(d.is_visible() for d in self.page.get_by_role('dialog').all()): return None
            added=[r for r in self.source_rows() if self.fingerprint(r) not in before]
            if len(added)!=1: return None
            text=added[0].inner_text().strip()
            if re.search(r'processing|loading|uploading|importing',text,re.I): return None
            if re.search(r'failed|error|unsupported',text,re.I): self.fail('NotebookLM could not import the video. It needs a public video with captions.')
            return added[0] if added[0].get_by_role('checkbox').count()==1 else None
        source=self.wait(imported,'The source import was not verified. Check video captions, access and the Sources panel.',100)
        source_title=source.inner_text().strip()[:250]
        # Generate from the requested video only, even in an existing notebook.
        target_check=source.get_by_role('checkbox')
        for row in self.source_rows():
            check=row.get_by_role('checkbox')
            if check.count()!=1: self.fail('Source selection is ambiguous. Select the intended video manually.')
            selected=self.fingerprint(row)==self.fingerprint(source)
            if check.is_checked()!=selected:
                self.guard(); check.set_checked(selected,timeout=5000)
        if not target_check.is_checked(): self.fail('The imported video source was not selected.')
        old_artifacts={self.fingerprint(r) for r in self.artifacts()}
        self.api.progress('Generating a NotebookLM mind map')
        studio=self.panel('Studio')
        generate=studio.get_by_role('button',name=re.compile(r'^(?:account_tree\s+)?(?:(?:Generate|Create) )?Mind Map$',re.I))
        options=[c for c in generate.all() if c.is_visible()]
        if len(options)!=1:
            # Official older layouts use a Mind Map chip in the centre chat.
            generate=self.page.get_by_role('button',name=re.compile(r'^(?:account_tree\s+)?(?:(?:Generate|Create) )?Mind Map$',re.I))
        self.click(self.unique(generate,'Generate Mind Map'))
        def generated():
            self.guard()
            added=[r for r in self.artifacts() if self.fingerprint(r) not in old_artifacts]
            maps=[r for r in added if re.search(r'account_tree|mind.?map',r.inner_text()+' '+(r.get_attribute('aria-label') or ''),re.I)]
            ready=[r for r in maps if not re.search(r'generating|loading|creating|pending',r.inner_text(),re.I)]
            return ready[0] if len(ready)==1 else None
        artifact=self.wait(generated,'Mind map generation has not been verified. Check Studio; do not regenerate automatically.',120)
        title=artifact.inner_text().strip()[:250]
        self.click(artifact)
        def opened_diagram():
            for diagram in self.page.locator('svg').all():
                rect=diagram.bounding_box()
                if diagram.is_visible() and rect and rect['width']>150 and rect['height']>150 and diagram.locator('text, foreignObject').count()>=3:
                    return True
            return False
        self.wait(opened_diagram,
                  'A new mind map appeared in Studio, but its opened diagram was not verified.',15)
        return ('NotebookLM imported the video source and generated a new mind map; the diagram is open.',
                {'notebookUrl':destination,'videoUrl':video,'sourceTitle':source_title,'mindMapTitle':title})


def execute(browser,api,request):
    controller=NotebookLMController(browser,api)
    try: return controller.run(request)
    except api.ActionError: raise
    except Exception:
        controller.fail('NotebookLM automation stopped because the page, account or controls changed. Completion was not verified. Check the visible page.')
