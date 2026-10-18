"""Read one exact4096-byte public immutable prefix per unique HTC fixture.

Raw prefixes exist only in RAM. No ignored-Range fallback, redirect or retry is
permitted. A whole fixture is not acquired by this header-only producer.
"""
from pathlib import Path, PurePosixPath
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import stat
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
COMMIT = 'd381dd9c273205c0fd7ac402c75eef98c6fa6c78'
TREE = '0a913bb21a505392dc8a7eb265203654f03196b1'
BINDING_SHA = '841e5f0ccdb00ada0d6fbdfb80282f649f14da8f6c8d8d6e1a2bc0dcdd20e2da'
CACHED_SHA = 'eb8dc2a87ad8cc6411b6a30ce87a754357e6e7c0214e6e48f0c9c80cbbcb0675'
SCHEMA_SHA = 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
DECODER_SHA = 'c5e4e7c588ebc2ef722ab9fd9def2e67e309c45d451639cfdee3126b0f616a42'
UPSTREAM = '9af3ea7150f1a8acb53464c92519a9bbcc7a3594'
HOST = 'raw.githubusercontent.com'
PREFIX = 'https://raw.githubusercontent.com/HeroesToolChest/Heroes.StormReplayParser/'
CAP = 4096
MAX_UNIQUE = 20
MAX_BODY = MAX_UNIQUE*CAP
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def require(condition,message):
    if not condition: raise ValueError(message)

def read(path,limit=256*1024):
    require(not path.is_symlink(),'Metadata/source symlink refused')
    with path.open('rb') as stream:
        a=os.fstat(stream.fileno())
        require(stat.S_ISREG(a.st_mode) and 0<a.st_size<=limit,'Metadata/source size or type refused')
        raw=stream.read(limit+1);b=os.fstat(stream.fileno())
    require(len(raw)==a.st_size and (a.st_size,a.st_mtime_ns)==(b.st_size,b.st_mtime_ns),'Metadata/source changed')
    return raw

def canonical_trees(rows,root):
    """Recompute every listed Git tree from its immediate immutable children."""
    require(len({r['path'] for r in rows})==len(rows),'Repeated tree path')
    directories={'':root}|{r['path']:r['sha'] for r in rows if r['type']=='tree'}
    for directory,expected in directories.items():
        children=[r for r in rows if str(PurePosixPath(r['path']).parent)==(directory or '.')]
        encoded=[]
        for r in children:
            name=PurePosixPath(r['path']).name.encode('utf-8')
            require(r['type'] in ('tree','blob') and re.fullmatch('[0-9a-f]{40}',r['sha']) is not None,'Invalid tree object')
            require(r['mode'] in ('040000','100644'),'Unexpected source tree mode')
            mode=format(int(r['mode'],8),'o').encode()
            encoded.append((name+(b'/' if r['type']=='tree' else b''),mode+b' '+name+b'\0'+bytes.fromhex(r['sha'])))
        body=b''.join(value for _,value in sorted(encoded))
        require(hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest()==expected,'Canonical Git tree differs')
    return len(directories)

def fixtures():
    binding_raw=read(HERE/'source-binding.json');cached_raw=read(WORK/'legacy-replay-controls-search/htc-tree.body.json')
    require(sha(binding_raw)==BINDING_SHA and sha(cached_raw)==CACHED_SHA,'Pinned tree metadata differs')
    binding=json.loads(binding_raw);cached=json.loads(cached_raw)
    require(binding['commit_sha']==COMMIT and binding['commit_tree_sha']==binding['tree_sha']==TREE and not binding['truncated'],'Immutable commit/tree binding differs')
    fields=('path','mode','type','sha','size')
    project=lambda rows:sorted(tuple(r.get(k) for k in fields) for r in rows)
    require(cached['sha']==COMMIT and not cached['truncated'] and len(binding['tree'])==len(cached['tree'])==183 and project(binding['tree'])==project(cached['tree']),'Fresh canonical tree and cached entries differ')
    tree_count=canonical_trees(binding['tree'],TREE)
    rows=[r for r in binding['tree'] if re.search(r'\.StormR(?:eplay)?$',r['path'],re.I)]
    require(len(rows)==22 and all(r['type']=='blob' and r['mode']=='100644' and CAP<=r['size']<=3*1024*1024 for r in rows),'Fixture listing differs')
    groups={}
    for row in rows: groups.setdefault(row['sha'],[]).append(row)
    require(len(groups)==MAX_UNIQUE,'Expected20unique fixtures')
    result=[]
    for blob,items in groups.items():
        require(len({r['size'] for r in items})==1,'Duplicate object size differs')
        preferred=sorted(items,key=lambda r:(not r['path'].startswith('Tests/'),r['path']))[0]
        path=preferred['path']
        require(not path.startswith('/') and '..' not in PurePosixPath(path).parts,'Unsafe public source path')
        result.append({'path':path,'duplicate_paths':sorted(r['path'] for r in items if r['path']!=path),'git_blob_sha1':blob,'listed_bytes':preferred['size'],'url':PREFIX+COMMIT+'/'+urllib.parse.quote(path,safe='/')})
    return sorted(result,key=lambda r:r['path']),tree_count

class TransportRefused(Exception): pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self,req,fp,code,msg,headers):
        fp.close();raise TransportRefused('redirect_refused')
    http_error_301=http_error_303=http_error_307=http_error_308=http_error_302

def valid_url(url,path):
    parsed=urllib.parse.urlsplit(url)
    require(parsed.scheme=='https' and parsed.hostname==HOST and parsed.port is None and parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment,'Only the exact public raw HTTPS host is allowed')
    require(url==PREFIX+COMMIT+'/'+urllib.parse.quote(path,safe='/'),'Immutable public path differs')

def response_header(response,name,maximum):
    value=response.headers.get(name)
    if value is not None and len(value)>maximum: raise TransportRefused('oversized_response_header')
    return value

def fetch_prefix(opener,spec):
    """One request, at most one4096-byte read; bad transports get zero reads."""
    valid_url(spec['url'],spec['path'])
    request=urllib.request.Request(spec['url'],headers={'Range':'bytes=0-4095','Accept-Encoding':'identity','User-Agent':'HotS-offline-public-fixture-header-probe/1'})
    metadata={'request_attempted':True,'application_body_bytes_read':0,'body_read_calls':0,'response_closed':False}
    try:
        with opener.open(request,timeout=20) as response:
            metadata['status']=response.status
            if response.geturl()!=spec['url']: raise TransportRefused('changed_url_refused')
            if response.status!=206: raise TransportRefused('non206_refused_before_body')
            cr=response_header(response,'Content-Range',128);cl=response_header(response,'Content-Length',32);ce=response_header(response,'Content-Encoding',32)
            metadata.update(content_range=cr,content_length=cl,content_encoding=ce,etag=response_header(response,'ETag',256))
            if ce not in (None,'identity'): raise TransportRefused('nonidentity_encoding_refused')
            if cr!=f"bytes 0-4095/{spec['listed_bytes']}" or cl!='4096': raise TransportRefused('range_or_total_size_mismatch')
            metadata['body_read_calls']=1
            raw=response.read(CAP)
            metadata['application_body_bytes_read']=len(raw)
            require(len(raw)<=CAP,'Response read exceeded fixed cap')
            if len(raw)!=CAP: raise TransportRefused('short_prefix_body')
        metadata['response_closed']=True
        return raw,metadata,None
    except urllib.error.HTTPError as error:
        metadata['status']=error.code;error.close();metadata['response_closed']=True
        return None,metadata,'http_error'
    except TransportRefused as error:
        metadata['response_closed']=True
        return None,metadata,str(error)
    except urllib.error.URLError as error:
        metadata['network_error_class']=type(error.reason).__name__;metadata['response_closed']=True
        return None,metadata,'network_error'
    except http.client.IncompleteRead as error:
        require(len(error.partial)<=CAP,'Partial read exceeded fixed cap')
        metadata['application_body_bytes_read']=len(error.partial)
        metadata['network_error_class']=type(error).__name__;metadata['response_closed']=True
        return None,metadata,'incomplete_HTTP_body'
    except http.client.HTTPException as error:
        metadata['network_error_class']=type(error).__name__;metadata['response_closed']=True
        return None,metadata,'HTTP_protocol_error'
    except (OSError,TimeoutError) as error:
        metadata['network_error_class']=type(error).__name__;metadata['response_closed']=True
        return None,metadata,'network_error'

def decode_header(raw,protocol):
    require(type(raw) is bytes and len(raw)==CAP,'Exact bounded prefix required')
    magic,size,offset,length=struct.unpack_from('<4s3I',raw)
    require(magic==b'MPQ\x1b' and 1<=length<=CAP-16 and offset>=16+length,'MPQ user header extent differs')
    decoded=protocol.decode_replay_header(raw[16:16+length])
    version={key:decoded['m_version'][key] for key in ('m_flags','m_major','m_minor','m_revision','m_build','m_baseBuild')}
    require(all(type(v) is int and 0<=v<2**32 for v in version.values()),'Header version scalars invalid')
    data=decoded.get('m_dataBuildNum');require(data is None or type(data) is int and 0<=data<2**32,'Header data build invalid')
    root=decoded.get('m_ngdpRootKey')
    if root is not None:
        require(type(root) is dict and type(root.get('m_data')) is bytes and len(root['m_data'])==16,'Header root shape invalid')
        root=root['m_data'].hex()
    return {'version':version,'data_build':data,'NGDP_root':root,'MPQ_user_header_bytes':length,'MPQ_user_data_size':size,'MPQ_archive_offset':offset}

def analyze():
    specs,tree_count=fixtures()
    protocol_path=WORK/'heroprotocol/heroprotocol/versions/protocol96477.py'
    decoder_path=WORK/'heroprotocol/heroprotocol/decoders.py'
    require(sha(read(protocol_path))==SCHEMA_SHA and sha(read(decoder_path))==DECODER_SHA,'Pinned official source differs')
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
    from protocol_loader import load_protocol
    protocol=load_protocol(96477)
    require(protocol.recovery_schema_sha256==SCHEMA_SHA,'Official loaded header schema differs')
    addresses=socket.getaddrinfo(HOST,443,type=socket.SOCK_STREAM)
    require(addresses and all(ipaddress.ip_address(r[4][0]).is_global for r in addresses),'Public hostname resolved outside public global addresses')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    results=[];body_bytes=0;requests=0
    for spec in specs:
        require(requests<MAX_UNIQUE and body_bytes+CAP<=MAX_BODY,'Global request/body allowance exceeded')
        requests+=1
        raw,metadata,error=fetch_prefix(opener,spec)
        body_bytes+=metadata['application_body_bytes_read']
        row=dict(spec,response=metadata,acquisition_outcome='failed' if error else 'strict206_prefix_acquired',acquisition_failure=error,header_decode_outcome='not_attempted',decoded_header=None,exact41810=False)
        if raw is not None:
            row['header_prefix_sha256']=sha(raw)
            try:
                row['decoded_header']=decode_header(raw,protocol);row['header_decode_outcome']='success';row['exact41810']=row['decoded_header']['version']['m_build']==41810
            except Exception as failure:
                row['header_decode_outcome']='header_decode_error';row['header_decoder_error_class']=type(failure).__name__
        results.append(row)
        print(json.dumps({'number':requests,'outcome':row['acquisition_outcome'],'transport_error':error,'actual_build':row['decoded_header']['version']['m_build'] if row['decoded_header'] else None,'body_read':metadata['application_body_bytes_read']}),flush=True)
    require(requests==20 and body_bytes<=MAX_BODY,'Final prefix budget differs')
    require(sha(read(protocol_path))==SCHEMA_SHA and sha(read(decoder_path))==DECODER_SHA,'Official source changed')
    fixtures()
    versions={}
    for row in results:
        if row['decoded_header'] is not None:
            build=str(row['decoded_header']['version']['m_build']);versions[build]=versions.get(build,0)+1
    return {'format':'htc-public-unique-fixture-header-observation-v1','producer_sha256':sha(read(Path(__file__))),
        'immutable_source':{'repository':'HeroesToolChest/Heroes.StormReplayParser','commit_sha':COMMIT,'actual_root_tree_sha':TREE,'source_binding_sha256':BINDING_SHA,'cached_tree_sha256':CACHED_SHA,'all183entry_tuples_equal_primary_canonical_tree':True,'canonical_Git_trees_recomputed':tree_count,'cached_top_level_sha_was_commit_label_not_canonical_tree_sha':True},
        'official_header_decoder':{'schema_build':96477,'schema_sha256':SCHEMA_SHA,'decoder_source_sha256':DECODER_SHA,'Blizzard_upstream_commit':UPSTREAM},
        'request_policy':{'unique_fixture_cap':20,'Range':'bytes=0-4095','body_read_cap_per_request':CAP,'global_prefix_body_cap':MAX_BODY,'identity_encoding_only':True,'exact206_and_ContentRange_total_required':True,'redirects_proxies_and_retries_allowed':False,'whole200_fallback_allowed':False,'public_host_only':HOST},
        'results':results,'aggregate':{'replay_paths':22,'unique_replay_blobs':20,'benchmark_duplicate_paths_skipped':2,'HTTP_attempts':requests,'application_body_bytes_read':body_bytes,'strict206_prefixes_acquired':sum(r['acquisition_outcome']=='strict206_prefix_acquired' for r in results),'header_decode_successes':sum(r['header_decode_outcome']=='success' for r in results),'acquisition_failures':sum(r['acquisition_outcome']=='failed' for r in results),'header_decode_failures':sum(r['header_decode_outcome']=='header_decode_error' for r in results),'actual_build_histogram':dict(sorted(versions.items(),key=lambda x:int(x[0]))),'exact41810_candidates':sum(r['exact41810'] for r in results)},
        'full_replay_acquisitions':0,'prefixes_retained_only_in_RAM':True,'raw_prefixes_or_players_or_messages_saved':False,'client_launched':False,'repo_or_cloud_modified':False,
        'limits':['Only prefix header versions are decoded; immutable URL/tree provenance is not a whole-file Git-blob/SHA256 validation.','Transport failures are recorded as acquisition outcomes and never relabeled schema failures.','The body allowance counts application bytes returned by the one capped read; underlying socket/TLS buffering is not measured.','Filename build/date labels were not used to classify eligibility.','No whole replay is fetched by this producer; an exact41810 result alone qualifies for the separately authorized≤3MiB full Git-blob/SHA256+parse stage.']}

if __name__=='__main__':
    output=HERE/'htc-20-unique-fixture-header-observation.json'
    require(not output.exists() and not output.is_symlink(),'Refuse existing report')
    report=analyze();raw=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    require(len(raw)<=128*1024,'Header ledger exceeds bound')
    with output.open('xb') as stream: stream.write(raw)
    print(json.dumps({'report_bytes':len(raw),'report_sha256':sha(raw),'aggregate':report['aggregate']}),flush=True)
