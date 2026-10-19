"""Screen exactly the Dragon game linked by the newly acquired public match.

Exact4096-byte206 required; no redirect/retry/ignored-Range fallback. Only the
pinned official Blizzard header decoder runs; prefix bytes remain in RAM.
"""
from pathlib import Path
import datetime, hashlib, importlib.util, json, re, struct, sys, urllib.error, urllib.request
BASE=Path(__file__).resolve().parent
WORK=BASE.parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
LEDGER=BASE/'route-ledger.json'
SCHEMA='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
DECODER='c5e4e7c588ebc2ef722ab9fd9def2e67e309c45d451639cfdee3126b0f616a42'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):raise ValueError('Redirect refused')
def main():
    ledger=json.loads(LEDGER.read_bytes())
    require(len(ledger['external_operations'])<6,'Operation cap exhausted')
    match=next(x for x in ledger['external_operations'] if x.get('url')=='https://heroeslounge.gg/match/view/27430')
    page=(BASE/'match-27430.private.html').read_bytes()
    require(sha(page)==match['sha256'],'Match source changed')
    games=[x for x in match['parsed']['games'] if x['map']=='Dragon Shire']
    require(len(games)==1,'Unique observed Dragon game required')
    url=games[0]['replay_url']
    require(re.fullmatch(r'https://heroeslounge\.gg/storage/app/uploads/public/[a-f0-9]{3}/[a-f0-9]{3}/[a-f0-9]{3}/[a-f0-9]+\.stormreplay',url) and url in page.decode('utf8'),'Observed public path differs')
    require(not any(x.get('url')==url for x in ledger['external_operations']),'No replay retries')
    require(sha((WORK/'heroprotocol/heroprotocol/versions/protocol96477.py').read_bytes())==SCHEMA,'Canonical schema differs')
    require(sha((WORK/'heroprotocol/heroprotocol/decoders.py').read_bytes())==DECODER,'Official decoder differs')
    sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
    from protocol_loader import load_protocol
    protocol=load_protocol(96477)
    require(protocol.recovery_schema_sha256==SCHEMA,'Loaded schema differs')
    row={'url':url,'transport':'urllib-range','source_match_url':match['url'],'source_match_page_sha256':sha(page),'primary_map':games[0]['map'],'acquired_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request_attempts':1,'hidden_retries':0,'range':'bytes=0-4095','maximum_body_bytes':4096,'header_decode_outcome':'not-attempted','schema_build':96477,'schema_sha256':SCHEMA,'official_decoder_sha256':DECODER,'body_bytes_read':0}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/bounded-current-EU-Dragon-header','Accept-Encoding':'identity','Range':'bytes=0-4095'})
        with urllib.request.build_opener(NoRedirect).open(req,timeout=30) as response:
            row.update(http_status=response.status,content_range=response.headers.get('Content-Range'),content_length=response.headers.get('Content-Length'),etag=response.headers.get('ETag'))
            require(response.status==206 and response.url==url and response.headers.get('Content-Encoding','identity')=='identity','Strict206 required before read')
            m=re.fullmatch(r'bytes 0-4095/(\d+)',row['content_range'] or '')
            require(m and 4096<=int(m[1])<=3*1024*1024 and row['content_length']=='4096','Range extent/length differs')
            row['total_replay_bytes']=int(m[1]);raw=response.read(4096);row['body_bytes_read']=len(raw)
            require(len(raw)==4096,'Truncated prefix')
        row.update(acquisition_outcome='strict206-prefix-acquired',prefix_sha256=sha(raw))
        magic,size,offset,length=struct.unpack_from('<4s3I',raw)
        require(magic==b'MPQ\x1b' and 1<=length<=4080 and offset>=16+length,'MPQ header extent differs')
        decoded=protocol.decode_replay_header(raw[16:16+length])
        version={key:decoded['m_version'][key] for key in ('m_flags','m_major','m_minor','m_revision','m_build','m_baseBuild')}
        require(all(type(v) is int and 0<=v<2**32 for v in version.values()),'Version scalar differs')
        root=decoded.get('m_ngdpRootKey',{}).get('m_data')
        require(type(root) is bytes and len(root)==16,'Root differs')
        row.update(header_decode_outcome='success',decoded_header={'version':version,'data_build':decoded.get('m_dataBuildNum'),'NGDP_root':root.hex()},current98348=version['m_build']==version['m_baseBuild']==decoded.get('m_dataBuildNum')==98348)
    except urllib.error.HTTPError as exc:
        row.update(acquisition_outcome='HTTP-unavailable',http_status=exc.code);exc.close()
    except urllib.error.URLError as exc:
        row.update(acquisition_outcome='transport-unavailable',exception_type=type(exc.reason).__name__)
    except Exception as exc:
        row.update(acquisition_outcome=row.get('acquisition_outcome','rejected-before-prefix'),exception_type=type(exc).__name__)
        if row.get('prefix_sha256'):row['header_decode_outcome']='rejected'
    ledger['external_operations'].append(row)
    LEDGER.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf8')
    print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
