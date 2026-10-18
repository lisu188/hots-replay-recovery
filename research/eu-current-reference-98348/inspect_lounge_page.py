"""Bounded primary Heroes Lounge page lookup; private HTML stays in task work."""
import argparse, hashlib, html, json, re, urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urljoin

BASE = Path(__file__).resolve().parent
LIMIT = 2 * 1024 * 1024

def checked(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname not in ('heroeslounge.gg','www.heroeslounge.gg') or p.username or p.password or p.port not in (None,443) or p.fragment:
        raise ValueError('URL outside primary Heroes Lounge boundary')
    return url

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked(urljoin(req.full_url,newurl))
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('url'); ap.add_argument('--label',required=True); a=ap.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,70}',a.label): raise ValueError('bad label')
    url=checked(a.url)
    with urllib.request.build_opener(Redirect).open(urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/offline-reference-research'}),timeout=30) as r:
        if int(r.headers.get('Content-Length','0'))>LIMIT: raise ValueError('page too large')
        raw=r.read(LIMIT+1)
        if len(raw)>LIMIT: raise ValueError('page too large')
        meta={'url':url,'final_url':checked(r.url),'status':r.status,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    text=raw.decode('utf-8')
    (BASE/(a.label+'.private.html')).write_bytes(raw)
    links=[]
    for href,body in re.findall(r'<a\b[^>]*href=[\"\x27]([^\"\x27]+)[\"\x27][^>]*>(.*?)</a>',text,re.I|re.S):
        href=html.unescape(href); label=' '.join(html.unescape(re.sub('<[^>]*>',' ',body)).split())
        if re.search(r'match/view|tournament|cup|master|season|playoff|storage/app/uploads/public|api/',href,re.I):
            links.append({'href':urljoin(meta['final_url'],href),'label':label[:160]})
    clean=' '.join(html.unescape(re.sub('<[^>]*>',' ',text)).split())
    dates=[m.group(0) for m in re.finditer(r'Scheduled for \d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{2} \(UTC [^)]*\)|\d{1,2} Oct 2026|2026-10-\d\d',clean)]
    scripts=re.findall(r'<script[^>]*src=[\"\x27]([^\"\x27]+)',text,re.I)
    meta.update(links=links,date_contexts=dates[:50],scripts=scripts)
    out=BASE/(a.label+'.page-observation.json')
    if out.exists(): raise FileExistsError(out)
    out.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf8')
    print(json.dumps(meta,indent=2))

if __name__=='__main__':main()
