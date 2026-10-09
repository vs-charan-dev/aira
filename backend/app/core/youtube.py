"""Canonical video links at every network boundary; no arbitrary URL fetching."""
import re
from urllib.parse import urlparse,parse_qs


def canonical_video(value):
    if not isinstance(value,str) or len(value)>1000: raise ValueError('Provide a YouTube video link.')
    uri=urlparse(value.strip())
    if uri.scheme!='https' or uri.username or uri.password or uri.port not in (None,443):
        raise ValueError('Use an HTTPS YouTube video link.')
    host=(uri.hostname or '').lower(); ident=None
    if host=='youtu.be': ident=uri.path.strip('/')
    elif host in ('youtube.com','www.youtube.com','m.youtube.com'):
        if uri.path=='/watch': ident=parse_qs(uri.query).get('v',[None])[0]
        elif re.fullmatch(r'/(shorts|live)/[^/]+/?',uri.path): ident=uri.path.strip('/').split('/')[1]
    if not ident or not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident):
        raise ValueError('Choose a specific YouTube video, not a search or channel page.')
    return ident,'https://www.youtube.com/watch?v='+ident
