"""Acquire one October candidate from hash-bound, saved official match metadata."""
import datetime, hashlib, json, re, urllib.request
from pathlib import Path
from inspect_lounge_page import BASE, Redirect, checked
from urllib.parse import urlsplit

LIMIT=3*1024*1024
def replay_url(url):
    checked(url); p=urlsplit(url)
    if p.query or p.fragment or not re.fullmatch(r'/storage/app/uploads/public/[a-f0-9]{3}/[a-f0-9]{3}/[a-f0-9]{3}/[a-f0-9]+\.stormreplay',p.path):
        raise ValueError('Replay URL is outside observed official public-upload path')
    return url

class ReplayRedirect(Redirect):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        replay_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

discovery_path=BASE/'dated-match-discovery.json'
discovery=json.loads(discovery_path.read_bytes())
match=next(r for r in discovery['results'] if r['match_id']==27515)
assert match['scheduled']=='05 Oct 2026 19:00 (UTC +00:00)'
html_path=BASE/'match-27515.private.html'
assert hashlib.sha256(html_path.read_bytes()).hexdigest()==match['html_sha256']
game=match['games'][0]
url=replay_url(game['replay_url'])
assert url in html_path.read_text(encoding='utf8')
dest=BASE/'heroeslounge-27515-g1-20261005.StormReplay'
if dest.exists():raise FileExistsError('refuse replay overwrite')
request=urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/offline-reference-research','Accept-Encoding':'identity'})
with urllib.request.build_opener(ReplayRedirect).open(request,timeout=30) as response:
    replay_url(response.url)
    if response.status!=200 or response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('unexpected transfer representation')
    expected=response.headers.get('Content-Length')
    if expected is not None and (not expected.isdecimal() or int(expected)>LIMIT):raise ValueError('replay exceeds transfer bound')
    raw=response.read(LIMIT+1)
    if len(raw)>LIMIT or (expected is not None and len(raw)!=int(expected)):raise ValueError('oversize/truncated replay')
    receipt={'schema_version':1,'acquired_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_match_url':match['url'],'source_match_html_sha256':match['html_sha256'],'scheduled_primary_page':match['scheduled'],'primary_page_map':game['map'],'source_discovery_file_sha256':hashlib.sha256(discovery_path.read_bytes()).hexdigest(),'requested_url':url,'final_url':response.url,'http_status':response.status,'content_length':expected,'etag':response.headers.get('ETag'),'last_modified':response.headers.get('Last-Modified'),'maximum_bytes':LIMIT,'file':dest.name,'file_bytes':len(raw),'file_sha256':hashlib.sha256(raw).hexdigest(),'download_is_compatibility_proof':False,'raw_replay_publication':False}
with dest.open('xb') as f:f.write(raw)
with (BASE/'one-eu-candidate-acquisition.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt,indent=2))
