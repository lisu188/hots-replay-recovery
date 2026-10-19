"""Bounded new primary EU Dragon route; raw pages remain task-private.

One request per invocation, no redirects, no retries. URL must occur literally
in one previously saved Heroes Lounge primary page. Report contains no names,
Toons, chat or response bodies. Separate header acquisition requires exact206.
"""
import argparse, datetime, hashlib, html, json, re, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urljoin

BASE=Path(__file__).resolve().parent
OLD=BASE.parent/'eu-replay-search-20261018'
MAX_OPS=8
MAX_HTML=1024*1024
LEDGER=BASE/'route-ledger.json'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):
        raise ValueError('Redirect refused before body read')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def checked(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in ('heroeslounge.gg','www.heroeslounge.gg') or p.username or p.password or p.port not in (None,443) or p.fragment:
        raise ValueError('Unexpected primary URL')
    return url

def inspect(raw):
    text=raw.decode('utf-8')
    clean=' '.join(html.unescape(re.sub('<[^>]*>',' ',text)).split())
    links=sorted(set(checked(html.unescape(v)) for v in re.findall(r'href=["\x27](https://heroeslounge\.gg/(?:match/view/\d+|season/archive|[^"\x27]*playoff[^"\x27]*|tournament/[^"\x27]*))["\x27]',text,re.I)))
    matches=sorted(set(int(v) for v in re.findall(r'match/view/(\d+)',text)))
    games=[]
    parts=re.split(r'<div class="tab-pane[^\"]*" id="game(\d+)" role="tabpanel">',text)
    for i in range(1,len(parts),2):
        body=parts[i+1]
        link=re.search(r'href="([^\"]+\.stormreplay)"',body,re.I)
        name=re.search(r'<span class="badge badge-info">([^<]+)</span>',body)
        games.append({'game_id':int(parts[i]),'map':html.unescape(name.group(1)) if name else None,'replay_url':checked(html.unescape(link.group(1))) if link else None})
    return {'match_ids':matches,'links':links,'games':games,'scheduled':next(iter(re.findall(r'Scheduled for (\d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{2} \(UTC [^)]*\))',clean)),None),'has_dragon_shire_text':bool(re.search(r'Dragon\s+Shire',clean,re.I))}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('url');ap.add_argument('--label',required=True);a=ap.parse_args()
    if not re.fullmatch('[a-z0-9-]{1,60}',a.label):raise ValueError('Unsafe label')
    url=checked(a.url)
    ledger=json.loads(LEDGER.read_bytes())
    if len(ledger['external_operations'])>=MAX_OPS:raise ValueError('External operation cap exhausted')
    if any(x.get('url')==url and x.get('transport')=='urllib' for x in ledger['external_operations']):raise ValueError('Refuse repeated urllib route')
    refs=[]
    for folder in (OLD,BASE):
        for path in folder.glob('*.private.html'):
            if path.is_symlink() or path.stat().st_size>MAX_HTML:continue
            raw=path.read_bytes()
            if url in {urljoin('https://heroeslounge.gg/', html.unescape(v)) for v in re.findall(r'href=[\"\x27]([^\"\x27]+)[\"\x27]', raw.decode('utf8'), re.I)}:refs.append({'file':path.name,'sha256':sha(raw)})
    if not refs and url==ledger.get('next_candidate',{}).get('url')=='https://www.heroeslounge.gg/en/match/view/27490':
        refs=[{'source':'primary indexed page from sixth bounded operation','ledger_sha256':sha(LEDGER.read_bytes()),'indexed_source_url':url}]
    if not refs:raise ValueError('URL not observed on saved primary page or exact approved indexed candidate')
    out=BASE/(a.label+'.private.html')
    if out.exists():raise FileExistsError('Refuse HTML overwrite')
    row={'url':url,'transport':'urllib','acquired_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'observed_link_sources':refs,'max_body_bytes':MAX_HTML,'request_attempts':1,'hidden_retries':0}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/bounded-public-EU-Dragon-metadata','Accept-Encoding':'identity'})
        with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as response:
            row['http_status']=response.status
            if response.status!=200 or response.url!=url or response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('Unexpected HTTP response')
            length=response.headers.get('Content-Length')
            if length is not None and (not length.isdecimal() or int(length)>MAX_HTML):raise ValueError('Invalid or excessive Content-Length')
            raw=response.read(MAX_HTML+1)
            if len(raw)>MAX_HTML or (length is not None and len(raw)!=int(length)):raise ValueError('Oversize or truncated page')
        row.update(body_bytes=len(raw),sha256=sha(raw),parsed=inspect(raw),outcome='acquired-and-parsed')
        with out.open('xb') as stream:stream.write(raw)
    except urllib.error.HTTPError as exc:
        row.update(outcome='HTTP-unavailable',http_status=exc.code,body_bytes_read=0)
        exc.close()
    except urllib.error.URLError as exc:
        row.update(outcome='transport-unavailable',exception_type=type(exc.reason).__name__,body_bytes_read=0)
    except Exception as exc:
        row.update(outcome='rejected',exception_type=type(exc).__name__)
    ledger['external_operations'].append(row)
    LEDGER.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf8')
    print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
