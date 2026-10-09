"""Fixed local transcript CLI, launched without a shell; no Gemini key required."""
import json
import re
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def main():
    ident=sys.argv[1] if len(sys.argv)>1 else ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident): raise ValueError('INVALID_VIDEO')
    data=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'data'
    if not data.is_relative_to(ROOT): raise ValueError('INVALID_PATH')
    from requests import Session
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
    class BoundedSession(Session):
        def request(self,*args,**kwargs):
            kwargs['timeout']=(5,20)
            return super().request(*args,**kwargs)
    with BoundedSession() as session:
        tracks=YouTubeTranscriptApi(http_client=session).list(ident)
        try: selected=tracks.find_transcript(['en','en-US','en-GB'])
        except NoTranscriptFound:
            available=list(tracks)
            if not available: raise ValueError('NO_CAPTIONS')
            selected=next((t for t in available if not t.is_generated),available[0])
        transcript=selected.fetch()
        snippets=[{'text':s.text,'start':s.start,'duration':s.duration} for s in transcript if s.text.strip()]
        if not snippets: raise ValueError('NO_CAPTIONS')
        if sum(len(s['text']) for s in snippets)>300000: raise ValueError('TOO_LONG')
        body={'version':1,'videoId':ident,'language':transcript.language,
              'languageCode':transcript.language_code,'isGenerated':transcript.is_generated,
              'fetchedAt':time.time(),'snippets':snippets}
    target=data/'media'/'youtube'/'transcripts'/ident/'transcript.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
    temporary.replace(target)
    print(json.dumps({'ok':True}))


if __name__=='__main__':
    try: main()
    except Exception as error:
        # Named errors only: provider exceptions can contain arbitrary page text.
        known={'TranscriptsDisabled':'NO_CAPTIONS','NoTranscriptFound':'NO_CAPTIONS',
               'VideoUnavailable':'UNAVAILABLE','VideoUnplayable':'UNAVAILABLE',
               'AgeRestricted':'UNAVAILABLE','RequestBlocked':'BLOCKED','IpBlocked':'BLOCKED'}
        code=known.get(type(error).__name__,'FETCH_FAILED')
        if isinstance(error,ValueError) and str(error) in ('NO_CAPTIONS','TOO_LONG','INVALID_PATH','INVALID_VIDEO'): code=str(error)
        print(json.dumps({'ok':False,'code':code}))
        sys.exit(1)
