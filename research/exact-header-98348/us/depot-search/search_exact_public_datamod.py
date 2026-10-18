"""Try only documented new endpoints for one exact missing public depot object.

No retries, redirects, credentials or archive fallback. A body is saved privately
only after the exact full SHA and complete generic package280539/version16 decode.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from collection_license_audit import _read,write_new_report
from depot_s2mh_wire import decode_verified_header

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
EXPECTED='42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a'
SOURCE_SHA='73d53ab5de28afccf651818a0801e17368678b2a4dedd11cdb58469e0aa75bae'
PER_OBJECT=512*1024
AGGREGATE=1024*1024
MAX_REQUESTS=6
PLAN=[
    ('modern-KR',f'https://kr-s2-depot.classic.blizzard.com/{EXPECTED}.s2mh','modern'),
    ('modern-CN',f'https://cn-s2-depot.necdn.leihuo.netease.com/{EXPECTED}.s2mh','modern'),
    ('legacy-US',f'http://us.depot.battle.net:1119/{EXPECTED}.s2mh','legacy'),
    ('legacy-EU',f'http://eu.depot.battle.net:1119/{EXPECTED}.s2mh','legacy'),
    ('legacy-KR',f'http://kr.depot.battle.net:1119/{EXPECTED}.s2mh','legacy'),
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def checked_url(url):
    parts=urlsplit(url)
    if url not in {row[1] for row in PLAN} or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('URL is outside exact documented plan')
    return url


def bounded_body(response,remaining):
    if type(remaining) is not int or not 0<remaining<=AGGREGATE:raise ValueError('No remaining body budget')
    cap=min(PER_OBJECT,remaining)
    declared=response.headers.get('Content-Length')
    if declared is not None:
        if not declared.isdecimal() or not 0<int(declared)<=cap:return b'','invalid_or_oversize_declared_body'
        target=int(declared)
    else:target=cap
    raw=bytearray()
    while len(raw)<target:
        part=response.read(min(32768,target-len(raw)))
        if not part:break
        raw.extend(part)
    if declared is not None and len(raw)!=target:return bytes(raw),'truncated_declared_body'
    if declared is None and len(raw)==cap:return bytes(raw),'unknown_length_reached_body_bound'
    return bytes(raw),None


def validated_body(raw):
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError('full_body_SHA_mismatch')
    decoded=decode_verified_header(raw,EXPECTED)
    if decoded[0][0]!={0:280539,1:16}:raise ValueError('decoded_package_identity_mismatch')
    return {'complete_generic_decode':True,'mod_id':280539,'version':16}


def run():
    output=HERE/'exact-datamod-alternate-endpoint-acquisition.json'
    if output.exists() or output.is_symlink():raise FileExistsError('Refuse receipt overwrite before any request')
    source_path=HERE/'endpoint-primary-source-provenance.json';source=_read(source_path,128*1024)
    if hashlib.sha256(source).hexdigest()!=SOURCE_SHA:raise ValueError('Primary endpoint source evidence differs')
    previous_path=WORK/'independent-parser/exact-current-s2mh-acquisition.json'
    previous_raw=_read(previous_path,128*1024);previous=json.loads(previous_raw)
    tried=[row for row in previous['attempts'] if row.get('expected_sha256')==EXPECTED]
    previous_urls={row['url'] for row in tried}
    if len(tried)!=2 or any(row.get('http_status')!=404 for row in tried):raise ValueError('Prior target acquisition inventory differs')
    if len(PLAN)>MAX_REQUESTS or any(url in previous_urls for _,url,_ in PLAN):raise ValueError('Request plan repeats prior attempts or exceeds cap')
    opener=urllib.request.build_opener(NoRedirect())
    attempts=[];total=0;requests=0;blocked_endpoints=set();saved=False
    for name,url,source_role in PLAN:
        checked_url(url);endpoint=urlsplit(url).netloc
        row={'id':name,'url':url,'primary_source_role':source_role,'expected_sha256':EXPECTED,'body_bytes_read':0,'body_saved':False}
        if endpoint in blocked_endpoints:
            row['status']='skipped_after_endpoint403';attempts.append(row);continue
        if total>=AGGREGATE:
            row['status']='skipped_aggregate_body_budget';attempts.append(row);continue
        requests+=1
        row['attempted_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'hots-replay-recovery/exact-public-header-search','Accept-Encoding':'identity'})
            with opener.open(request,timeout=10) as response:
                row['http_status']=response.status
                if response.status!=200 or response.url!=url:
                    row['status']='acquisition_failed';row['reason']='unexpected_status_or_URL'
                elif response.headers.get('Content-Encoding','identity')!='identity':
                    row['status']='acquisition_failed';row['reason']='nonidentity_transfer_encoding'
                else:
                    raw,reason=bounded_body(response,AGGREGATE-total)
                    total+=len(raw);row['body_bytes_read']=len(raw)
                    if reason:
                        row['status']='acquisition_failed';row['reason']=reason
                    else:
                        row['acquisition_complete']=True
                        try:
                            validation=validated_body(raw)
                        except (ValueError,KeyError,TypeError):
                            row['status']='validation_failed';row['reason']='full_SHA_complete_decode_or_package_tuple_failed'
                            row['full_expected_SHA_matches']=hashlib.sha256(raw).hexdigest()==EXPECTED
                        else:
                            folder=HERE/'verified-private';folder.mkdir(exist_ok=True)
                            dest=folder/(EXPECTED+'.s2mh')
                            with dest.open('xb') as stream:stream.write(raw)
                            row.update(status='exact_SHA_and_package_verified',bytes=len(raw),actual_sha256=EXPECTED,
                                body_saved=True,private_file='verified-private/'+dest.name,**validation)
                            saved=True
        except urllib.error.HTTPError as error:
            row.update(status='acquisition_failed',reason='HTTP_error',http_status=error.code)
            if error.code==403:
                blocked_endpoints.add(endpoint);row['endpoint_stopped_after403']=True
            error.close()
        except (urllib.error.URLError,TimeoutError,OSError) as error:
            row.update(status='acquisition_failed',reason='transport_failure',error_type=type(error).__name__)
        attempts.append(row)
        print(json.dumps({key:value for key,value in row.items() if key!='private_file'},sort_keys=True),flush=True)
        if saved:break
    report={'format':'hots-exact-missing-US-datamod-alternate-public-acquisition-v1',
        'source_producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'primary_endpoint_source_evidence_sha256':SOURCE_SHA,
        'prior_acquisition_receipt_sha256':hashlib.sha256(previous_raw).hexdigest(),
        'expected_object_sha256':EXPECTED,'expected_package':{'mod_id':280539,'version':16},
        'prior_target_attempts_not_repeated':[{'url':row['url'],'http_status':row['http_status']} for row in tried],
        'maximum_object_requests':MAX_REQUESTS,'maximum_body_bytes_per_object':PER_OBJECT,'maximum_aggregate_body_bytes':AGGREGATE,
        'actual_object_requests':requests,'actual_body_bytes_read':total,'attempts':attempts,
        'acquisition_failure_count':sum(row['status']=='acquisition_failed' for row in attempts),
        'validation_failure_count':sum(row['status']=='validation_failed' for row in attempts),
        'verified_exact_object_saved_privately':saved,'raw_body_in_publication_allowlist':False,
        'application_retries':0,'redirects_followed':0,'credentials_or_authentication_used':False,
        'client_launched':False,'game_cache_replay_repo_or_cloud_modified':False,
        'limitations':['Alternate regions are exact-digest object searches, not content or regional identity substitution.',
            'HTTP/status/transport failure is acquisition evidence only; no incompatible header interpretation is inferred.',
            'No legacy fallback, GCP/internal host, credential, redirected request or full archive request is made after an endpoint failure.',
            'Only an entire exact expected SHA and complete package280539/version16 decode permits a private body save.']}
    write_new_report(report,output)
    print(json.dumps({'report_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'requests':requests,
        'body_bytes':total,'verified':saved,'acquisition_failures':report['acquisition_failure_count'],
        'validation_failures':report['validation_failure_count']},sort_keys=True))


if __name__=='__main__':run()
