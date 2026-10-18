"""Only four exact advertised EU base header handles; bounded SHA/EOF-verified reads."""
import datetime,hashlib,json,re,sys,urllib.error,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
BASE=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/andrz/git/hots-replay-recovery')
from depot_s2mh_wire import decode_verified_header

ONE_LIMIT=512*1024;TOTAL_LIMIT=1024*1024
binding_path=BASE/'one-eu-current-reference-binding.json'
binding=json.loads(binding_path.read_bytes())
assert binding['file_sha256']=='a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4'
assert binding['data_build']==98348 and binding['details_player_region_set']==[2]
entries=binding['mod_package_bindings'][:4]
assert len(entries)==4 and all(x['terminal_s2mh_handle']['region']=='EU' for x in entries)
HOST='eu-s2-depot.classic.blizzard.com'
def check(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname!=HOST or p.port not in (None,443) or p.username or p.password or p.query or p.fragment or not re.fullmatch(r'/[0-9a-f]{64}\.s2mh',p.path):raise ValueError('outside exact public EU depot boundary')
    return url
class Guard(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check(newurl)
        if urlsplit(newurl).path!=urlsplit(req.full_url).path:raise ValueError('digest path changed')
        return super().redirect_request(req,fp,code,msg,headers,newurl)
out=BASE/'base-headers-private';out.mkdir(exist_ok=True)
opener=urllib.request.build_opener(Guard)
rows=[];total=0
for entry in entries:
    sha=entry['terminal_s2mh_handle']['digest'];url=check(f'https://{HOST}/{sha}.s2mh')
    row={'index':entry['index'],'mod_id':entry['mod_id'],'version':entry['version'],'url':url,'expected_sha256':sha}
    try:
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/offline-exact-header','Accept-Encoding':'identity'}),timeout=20) as response:
            check(response.url)
            if response.status!=200 or response.headers.get('Content-Encoding','identity')!='identity':raise ValueError('unexpected transfer representation')
            expected=response.headers.get('Content-Length')
            if expected is not None and (not expected.isdecimal() or int(expected)>min(ONE_LIMIT,TOTAL_LIMIT-total)):raise ValueError('declared response exceeds bound')
            raw=response.read(min(ONE_LIMIT,TOTAL_LIMIT-total)+1);total+=len(raw)
            if len(raw)>ONE_LIMIT or total>TOTAL_LIMIT or (expected is not None and len(raw)!=int(expected)):raise ValueError('oversize/truncated response')
            tree=decode_verified_header(raw,sha)
            path=out/(sha+'.s2mh')
            with path.open('xb') as f:f.write(raw)
            row.update(status='sha256-and-complete-versioned-wire-verified',http_status=response.status,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),local_file='base-headers-private/'+path.name,versioned_outer_tags=sorted(tree),complete_wire_eof=True,etag=response.headers.get('ETag'),last_modified=response.headers.get('Last-Modified'))
    except urllib.error.HTTPError as error:row.update(status='acquisition-failed',http_status=error.code,error_type=type(error).__name__)
    rows.append(row);print(json.dumps(row),flush=True)
report={'format':'hots-exact-current-eu-base-header-acquisition-v1','acquired_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_replay_sha256':binding['file_sha256'],'source_binding_sha256':hashlib.sha256(binding_path.read_bytes()).hexdigest(),'maximum_objects':4,'maximum_per_header_bytes':ONE_LIMIT,'maximum_aggregate_bytes':TOTAL_LIMIT,'downloaded_body_bytes':total,'endpoint_primary_url':'https://github.com/ggtracker/sc2reader/blob/e10fc9344417d0aa9649e4ed8d6423e38f6af4c9/sc2reader/utils.py','decoder_source_file_sha256':hashlib.sha256(Path('C:/Users/andrz/git/hots-replay-recovery/depot_s2mh_wire.py').read_bytes()).hexdigest(),'results':rows,'raw_headers_publishable':False,'client_launched':False,'replay_modified':False}
with (BASE/'four-eu-base-header-acquisition.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
