"""Visible, bounded YouTube and Google Maps actions in an owned Chrome profile on E:.

No attachment to personal Chrome, arbitrary URLs, page scripts from a model,
downloads, credential entry or account mutations. Manual website sign-in in this
persistent profile is reused; selectors/code below are fixed.
"""
import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, urlencode, urljoin


RESULT_LINKS = 'a[href*="/watch?v="]:visible'
RESULT_TITLES = ('a#video-title[href*="/watch?v="]:visible, '
                 'a.yt-lockup-metadata-view-model__title[href*="/watch?v="]:visible, '
                 'h3 a[href*="/watch?v="]:visible')

READ_RESULTS_JS = '''() => {
    const current=new URL(location.href);
    if (current.protocol!=='https:' || !['youtube.com','www.youtube.com'].includes(current.hostname) ||
        current.pathname!=='/results' || !current.searchParams.get('search_query')) return [];
    return Array.from(document.querySelectorAll('a[href*="/watch?v="]')).filter(el => {
    const rect=el.getBoundingClientRect();
    return rect.width && rect.height && getComputedStyle(el).visibility!=='hidden';
}).slice(0,100).flatMap(el => {
    if (
        el.closest('ytd-ad-slot-renderer, ytd-promoted-video-renderer, ytd-promoted-sparkles-web-renderer, ytd-in-feed-ad-layout-renderer, ytd-masthead, yt-searchbox, ytd-searchbox, ytd-miniplayer, ytd-playlist-renderer, ytd-radio-renderer')) return [];
    let uri;
    try { uri=new URL(el.getAttribute('href') || '',location.href); } catch { return []; }
    if (uri.protocol!=='https:' || !['youtube.com','www.youtube.com','m.youtube.com'].includes(uri.hostname) ||
        uri.pathname!=='/watch' || uri.searchParams.has('list') || !/^[A-Za-z0-9_-]{11}$/.test(uri.searchParams.get('v') || '')) return [];
    const card=el.closest('ytd-video-renderer, yt-lockup-view-model, ytd-lockup-view-model');
    const heading=card?.querySelector('a#video-title, a.yt-lockup-metadata-view-model__title, h3 a');
    let sameVideo=false;
    try { sameVideo=!!heading && new URL(heading.getAttribute('href') || '',location.href).searchParams.get('v')===uri.searchParams.get('v'); } catch {}
    const text=node => [node.getAttribute('title'),node.innerText,node.getAttribute('aria-label')].map(value => (value || '').trim()).find(Boolean) || '';
    const title=((sameVideo ? text(heading) : '') || text(el)).slice(0,250);
    return title ? [{href:uri.href,title}] : [];
});
}'''


def search_location(value, query=None):
    uri=urlparse(str(value))
    terms=parse_qs(uri.query).get('search_query',[])
    return (uri.scheme=='https' and uri.hostname in ('www.youtube.com','youtube.com')
            and uri.path=='/results' and len(terms)==1
            and (query is None or terms==[query]))


def video_location(value, expected):
    try: return video_url(str(value))==expected
    except ValueError: return False


def video_url(value):
    if not isinstance(value, str) or len(value)>1000:
        raise ValueError('Provide a YouTube video link.')
    uri=urlparse(value.strip())
    if uri.scheme!='https' or uri.username or uri.password or uri.port not in (None,443):
        raise ValueError('Use an HTTPS YouTube video link.')
    host=(uri.hostname or '').lower()
    ident=None
    if host=='youtu.be': ident=uri.path.strip('/')
    elif host in ('youtube.com','www.youtube.com','m.youtube.com'):
        if uri.path=='/watch': ident=parse_qs(uri.query).get('v',[None])[0]
        elif re.fullmatch(r'/(shorts|live)/[^/]+/?',uri.path): ident=uri.path.strip('/').split('/')[1]
    if not ident or not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident):
        raise ValueError('Choose a specific YouTube video, not a channel or search page.')
    return 'https://www.youtube.com/watch?v='+ident


class BrowserController:
    def __init__(self):
        self.playwright=None
        self.context=None
        self.page=None
        self.invoice_page=None
        self.youtube_page=None
        self.maps_page=None
        self.results=[]

    def ready(self, api, create=True):
        if self.context is not None:
            try:
                pages=[p for p in self.context.pages if not p.is_closed()]
                if not pages:
                    if not create: raise api.ActionError('No AIRA Chrome tab is open. Provide a video link or open AIRA Chrome.')
                    self.page=self.context.new_page()
                elif self.page is None or self.page.is_closed(): self.page=pages[-1]
                return self.page
            except Exception:
                self.context=None; self.page=None; self.results=[]
        if not create: raise api.ActionError('Open AIRA Chrome and select a YouTube video, or provide its link.')
        from playwright.sync_api import sync_playwright
        if self.playwright is None: self.playwright=sync_playwright().start()
        profile=api.ROOT/'data'/'browser'/'chrome'
        cache=api.ROOT/'.cache'/'chrome'
        profile.mkdir(parents=True,exist_ok=True); cache.mkdir(parents=True,exist_ok=True)
        api.progress('Opening AIRA Chrome')
        try:
            self.context=self.playwright.chromium.launch_persistent_context(
                str(profile),channel='chrome',headless=False,no_viewport=True,
                accept_downloads=False,timeout=15000,chromium_sandbox=True,
                args=['--no-first-run','--profile-directory=Default','--disable-sync','--disable-background-networking',
                      '--disable-component-update','--disk-cache-dir='+str(cache)])
        except Exception:
            raise api.ActionError('Chrome could not start. Install Google Chrome or close a stale AIRA Chrome window, then retry.')
        self.context.set_default_timeout(8000)
        self.context.set_default_navigation_timeout(15000)
        self.page=self.context.pages[0] if self.context.pages else self.context.new_page()
        self.results=[]
        return self.page

    def current(self,api):
        self.ready(api,False)
        focused=[]
        for page in self.context.pages:
            if not page.is_closed() and page.evaluate('document.hasFocus()'): focused.append(page)
        if len(focused)>1:
            raise api.ActionError('The active AIRA Chrome tab could not be identified. Supply the video link.')
        owned_focus=bool(focused)
        focused=[p for p in focused if urlparse(p.url).hostname in ('youtube.com','www.youtube.com','m.youtube.com')]
        if focused:
            page=focused[0]
        else:
            # Voice/overlay activation takes focus away from Chrome. Retain the
            # tab AIRA selected, but never substitute it for a personal Chrome tab.
            if not owned_focus and api.process_name(api.foreground())=='chrome.exe':
                raise api.ActionError('The foreground Chrome tab is not controlled by AIRA. Select the video in AIRA Chrome or provide its link.')
            page=self.youtube_page or self.page
            if page is None or page.is_closed():
                raise api.ActionError('No selected AIRA Chrome tab is available. Open a video in AIRA Chrome or provide its link.')
        try:
            url=video_url(page.evaluate('location.href'))
            if not video_location(page.url,url):
                raise ValueError('The selected video is still navigating. Ask again after it loads.')
        except ValueError as error: raise api.ActionError(str(error))
        self.page=page
        self.youtube_page=page
        return {'videoUrl':url,'title':page.title().removesuffix(' - YouTube')[:250]}

    def show_owned_window(self,api,page):
        """Restore the window belonging to this exact owned Playwright tab."""
        session=self.context.new_cdp_session(page)
        try:
            target=session.send('Browser.getWindowForTarget')
            session.send('Browser.setWindowBounds',{'windowId':target['windowId'],'bounds':{'windowState':'normal'}})
            session.send('Browser.setWindowBounds',{'windowId':target['windowId'],'bounds':{'windowState':'maximized'}})
            page.bring_to_front()
            visible=page.evaluate("document.visibilityState === 'visible' && innerWidth > 0 && innerHeight > 0")
            if not visible: raise api.ActionError('AIRA Chrome is not visible. Restore its window before asking for a browser action.')
        except api.ActionError: raise
        except Exception:
            raise api.ActionError('AIRA could not restore its own Chrome window. Close stale AIRA Chrome windows and restart the desktop app.')
        finally:
            try: session.detach()
            except Exception: pass

    def submit_search(self,api,page,query):
        """Type visibly, then load a fresh results document for this exact query.

        A simulated key event and a SPA URL change are not proof of submission.
        A fixed full navigation avoids depending on YouTube's Enter handlers.
        """
        page.goto('https://www.youtube.com',wait_until='domcontentloaded')
        box=page.locator('input[name="search_query"]:visible, input#search:visible, yt-searchbox input:visible').first
        try: box.fill(query)
        except Exception:
            raise api.ActionError('The YouTube search box was unavailable. Check the visible page for consent or a loading error.')
        api.progress('Submitting YouTube search')
        response=page.goto('https://www.youtube.com/results?'+urlencode({'search_query':query}),wait_until='domcontentloaded')
        if response is None or response.status>=400:
            raise api.ActionError('YouTube did not load the search response. Check the visible browser for a site or network error.')
        document_url=page.evaluate('location.href')
        if not search_location(page.url,query) or not search_location(document_url,query):
            raise api.ActionError('YouTube did not open results for the requested query. Inspect the page before retrying.')

    def read_results(self,api,page):
        if not search_location(page.url) or not search_location(page.evaluate('location.href')):
            raise api.ActionError('Open YouTube search results first, or provide a video link.')
        api.progress('Reading YouTube video results')
        try: page.wait_for_function('() => ('+READ_RESULTS_JS+')().length > 0',timeout=20000)
        except Exception:
            diagnostic=self.result_diagnostic(api,page)
            raise api.ActionError('YouTube search was submitted, but no readable video results loaded.'+diagnostic+' Check the page for consent, a site challenge or a loading error.')
        # Read fixed DOM fields in page order. New lockup cards and older renderer
        # cards both expose watch links, even when a#video-title is absent.
        observed=page.evaluate(READ_RESULTS_JS)
        results=[]; seen=set()
        for item in observed:
            try: url=video_url(urljoin('https://www.youtube.com',item['href']))
            except ValueError: continue
            title=item['title']
            if url in seen or not title: continue
            seen.add(url)
            results.append({'index':len(results)+1,'title':title,'videoUrl':url})
            if len(results)==5: break
        if not results:
            self.result_diagnostic(api,page)
            raise api.ActionError('YouTube search was submitted, but video titles could not be read. Inspect the visible results before retrying.')
        self.results=results
        return results

    def result_diagnostic(self,api,page):
        """Record layout counts only, without HTML, account data or screenshots."""
        try:
            counts=page.evaluate('''() => {
                const count=selector => Array.from(document.querySelectorAll(selector)).filter(el => {
                    const rect=el.getBoundingClientRect(); return rect.width && rect.height && getComputedStyle(el).visibility!=='hidden';
                }).length;
                return {classicCards:count('ytd-video-renderer'),modernCards:count('yt-lockup-view-model'),
                    watchLinks:count('a[href*="/watch?v="]'),searchContainers:count('ytd-search'),
                    documentHost:location.hostname,documentPath:location.pathname,
                    visibility:document.visibilityState,viewportWidth:innerWidth,viewportHeight:innerHeight};
            }''')
            directory=api.ROOT/'.cache'/'desktop'; directory.mkdir(parents=True,exist_ok=True)
            (directory/'youtube-layout.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),
                'stage':'read_search_results',**counts}),encoding='utf-8')
            return ' Visible watch links: '+str(counts['watchLinks'])+'.'
        except Exception: return ''

    def open_video(self,api,page,url):
        api.progress('Opening selected YouTube video')
        if search_location(page.url):
            # A result often has duplicate thumbnail/title links. They represent
            # the same video; choose its first visible title rather than rejecting
            # the page merely because multiple links point to that video.
            titles=page.locator(RESULT_TITLES)
            candidates=titles.all()+page.locator(RESULT_LINKS).all()
            selected=None
            for link in candidates[:200]:
                href=link.get_attribute('href') or ''
                if video_location(urljoin('https://www.youtube.com',href),url) and link.evaluate(
                    "el => !el.closest('ytd-ad-slot-renderer, ytd-promoted-video-renderer, ytd-promoted-sparkles-web-renderer, ytd-in-feed-ad-layout-renderer, ytd-masthead, yt-searchbox, ytd-searchbox, ytd-miniplayer, ytd-playlist-renderer, ytd-radio-renderer')"):
                    selected=link; break
            if selected is not None:
                selected.scroll_into_view_if_needed()
                selected.evaluate("el => { el.style.outline='4px solid #528bff'; }")
                selected.click()
            elif url in [r['videoUrl'] for r in self.results]:
                raise api.ActionError('The selected video link is no longer visible. Search again or supply its link.')
            else: page.goto(url,wait_until='domcontentloaded')
        else: page.goto(url,wait_until='domcontentloaded')
        try: page.wait_for_url(lambda target: video_location(target,url),wait_until='domcontentloaded')
        except Exception: raise api.ActionError('The selected video did not open. Inspect the browser before retrying.')
        return {'videoUrl':url,'title':page.title().removesuffix(' - YouTube')[:250]}

    def maps(self,api,request):
        query=request.get('query') if request['kind']=='search_maps' else None
        if request['kind']=='search_maps' and (not isinstance(query,str) or not query.strip() or len(query)>250 or re.search(r'[\x00-\x1f\x7f]',query)):
            raise api.ActionError('Provide a place name or address of 1–250 characters.')
        self.ready(api)
        page=self.maps_page
        if page is None or page.is_closed() or page not in self.context.pages:
            page=self.context.new_page()
            self.maps_page=page
        self.page=page
        self.show_owned_window(api,page)
        # Google's documented Maps Search URL submits the literal query without
        # depending on translated button labels or simulated Enter handlers.
        url='https://www.google.com/maps'
        if query is not None:
            query=query.strip()
            url='https://www.google.com/maps/search/?'+urlencode({'api':'1','query':query})
        api.progress('Searching Google Maps' if query is not None else 'Opening Google Maps')
        response=page.goto(url,wait_until='domcontentloaded')
        if response is None or response.status>=400:
            raise api.ActionError('Google Maps did not load. Check the visible browser for a network error.')
        try:
            page.wait_for_function('''query => {
                const uri=new URL(location.href);
                if (uri.protocol!=='https:' || uri.hostname!=='www.google.com' ||
                    !uri.pathname.startsWith('/maps')) return false;
                const visible=el => !!el && !!(el.getBoundingClientRect().width &&
                    el.getBoundingClientRect().height) && getComputedStyle(el).visibility!=='hidden';
                const boxes=Array.from(document.querySelectorAll('input#searchboxinput, input[role="combobox"], input[name="q"]'));
                const box=boxes.find(visible);
                if (!box || (query!==null && box.value.trim().toLocaleLowerCase()!==query.toLocaleLowerCase())) return false;
                return query===null || Array.from(document.querySelectorAll('h1, [role="feed"]')).some(visible);
            }''',arg=query,timeout=20000)
        except Exception:
            raise api.ActionError('Google Maps opened, but its '+('search results' if query is not None else 'map')+' could not be verified. Check the visible page for consent, a site challenge or no results.')
        self.show_owned_window(api,page)
        if query is None: return 'Google Maps is open in AIRA Chrome.',{}
        return 'Google Maps search results are displayed for '+query+'.',{}

    def run(self,api,request):
        kind=request['kind']
        if kind in ('open_maps','search_maps'): return self.maps(api,request)
        if kind=='show_invoice_demo':
            uri=urlparse(str(request.get('url','')))
            if uri.scheme!='http' or uri.hostname not in ('127.0.0.1','localhost','::1') or uri.username or uri.password or uri.path!='/invoice-demo' or uri.query or uri.fragment:
                raise api.ActionError('Use the local invoice URL.')
            self.ready(api)
            page=self.invoice_page
            if page is None or page.is_closed() or page not in self.context.pages:
                page=next((p for p in self.context.pages if not p.is_closed() and p.url==request['url']),None)
                if page is None: page=next((p for p in self.context.pages if not p.is_closed() and p.url=='about:blank' and p is not self.youtube_page),None)
                if page is None: page=self.context.new_page()
                self.invoice_page=page
            if page.url!=request['url']:
                response=page.goto(request['url'],wait_until='domcontentloaded')
                if response is None or response.status>=400: raise api.ActionError('The localhost invoice application did not load.')
            self.show_owned_window(api,page)
            return 'Invoice Studio is open in its dedicated localhost Chrome tab. YouTube tabs are preserved.',{}
        if kind=='notebooklm_mindmap':
            from notebooklm_control import execute as notebook_execute
            return notebook_execute(self,api,request)
        if kind=='current_youtube_video':
            return 'Selected YouTube video link read from the owned AIRA Chrome tab.',self.current(api)
        self.ready(api)
        page=self.youtube_page
        if page is None or page.is_closed() or page not in self.context.pages:
            page=next((p for p in self.context.pages if not p.is_closed() and urlparse(p.url).hostname in ('youtube.com','www.youtube.com','m.youtube.com')),None)
            if page is None: page=next((p for p in self.context.pages if not p.is_closed() and p.url=='about:blank' and p is not self.invoice_page),None)
            if page is None: page=self.context.new_page()
            self.youtube_page=page
        self.page=page
        self.show_owned_window(api,page)
        if kind=='open_browser':
            if page.url=='about:blank': page.goto('https://www.youtube.com',wait_until='domcontentloaded')
            return 'AIRA Chrome is open using its persistent E-drive profile and any saved manual website sign-in.',{}
        if kind=='search_youtube':
            query=request.get('query')
            if not isinstance(query,str) or not query.strip() or len(query)>250 or re.search(r'[\x00-\x1f]',query):
                raise api.ActionError('Provide a YouTube search query of 1–250 characters.')
            self.results=[]
            api.progress('Searching YouTube')
            self.submit_search(api,page,query.strip())
            self.read_results(api,page)
            return 'YouTube search completed. Choose a numbered video on the task board or ask AIRA to open one.',{'videos':self.results}
        if kind=='open_youtube_video':
            supplied=request.get('videoUrl')
            index=request.get('resultNumber')
            if supplied:
                try: url=video_url(supplied)
                except ValueError as error: raise api.ActionError(str(error))
            else:
                # A previous read may have failed while the page was still loading.
                # Re-read the current visible results when a numbered open is asked.
                if search_location(page.url): self.read_results(api,page)
                if isinstance(index,bool) or not isinstance(index,int) or not 1<=index<=len(self.results):
                    raise api.ActionError('Search YouTube first and choose an observed result number, or provide a video link.')
                url=self.results[index-1]['videoUrl']
            data=self.open_video(api,page,url)
            return 'The selected YouTube video page is open; playback may require a click.',data
        raise api.ActionError('Unsupported browser action.')


controller=BrowserController()


def execute(api,request):
    try: message,data=controller.run(api,request)
    except api.ActionError: raise
    except Exception:
        raise api.ActionError('Browser automation could not finish. Check the visible AIRA Chrome page for loading, consent or a changed layout; completion was not verified.')
    api.emit(type='result',status='succeeded',message=message,data=data)
