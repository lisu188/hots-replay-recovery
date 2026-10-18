"""Offline independent saved-response/root review; never run the network fetcher."""
import datetime
import hashlib
import json
import math
import runpy
import socket
import sys
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
WORK=HERE.parent
SOURCE=WORK/'legacy-build-root-research'
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from collection_license_audit import _read,write_new_report
from protocol_loader import load_protocol
from mpq_reader import MPQArchive
from encoders import encode_header

sha=lambda b:hashlib.sha256(b).hexdigest()
FROZEN='5ec4b9d2526156e0102734802caac4ed7266f77356b70a6ae4a8987a99736ccd'
ORIGINAL_SHA='e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
ROOT='83d43a8647bb5ca5caa6f2f09064da55'
FIXED='c585f3548fb8f9776fa1fba4dfec2b9a'
EXPECTED={
 'history-newest':('df5071abe7aed29b93a1429241ef973f8e0365431ae185f735905c9b88369c64',{'file':['versions'],'page':['1'],'limit':['1']}),
 'history-reported-last-page':('5dfc3c236cfc45b2792294b92ab1332054952d604819a1797018ed9de461c902',{'file':['versions'],'page':['20'],'limit':['1']}),
 'history-arithmetic-last-page':('4b32078d72dbf6412f307b06474ec4a307f3e139c250bb57a223d0043e4bd3f6',{'file':['versions'],'page':['21'],'limit':['1']}),
 'earliest-observed-versions':('394313bfd683966a085d0e5e3d3ae9c907a2fc4fc8a1f8c948ae1a05d61bebd0',{'seqn':['1070978']})}

def main():
    frozen_raw=_read(SOURCE/'legacy41810-research-frozen-receipt.json',1024*1024)
    assert sha(frozen_raw)==FROZEN
    frozen=json.loads(frozen_raw)
    files=frozen['allowlisted_files']
    assert len(files)==11 and len({row['relative_to_work'] for row in files})==11
    before={}
    for row in files:
        path=(WORK/row['relative_to_work']).resolve()
        assert path.is_relative_to(SOURCE.resolve()) and not path.is_symlink()
        raw=_read(path,1024*1024)
        assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
        before[path]=sha(raw)
    producer=SOURCE/'record_legacy_build_research.py'
    assert before[producer.resolve()]=='fb04c50dfaa1f0e5f75fe672442634b3adb242c1bc6b7940c88f2602b671897e'
    bodies={};request_rows=[]
    for label,(digest,query) in EXPECTED.items():
        raw=_read(SOURCE/(label+'.body.json'),131072)
        receipt_raw=_read(SOURCE/(label+'.request.json'),8192)
        request=json.loads(receipt_raw);body=json.loads(raw)
        assert sha(raw)==digest==request['sha256'] and len(raw)==request['bytes']<=131072
        assert request['http_status']==200 and request['redirects_followed']==0 and request['maximum_bytes']==131072
        url=urlsplit(request['url'])
        assert url.scheme=='https' and url.netloc=='blizztrack.com' and not url.fragment
        assert parse_qs(url.query,keep_blank_values=True,strict_parsing=True)==query
        assert url.path=='/api/manifest/hero/'+('versions' if label=='earliest-observed-versions' else 'seqn')
        assert datetime.datetime.fromisoformat(request['requested_at_utc']).utcoffset()==datetime.timedelta(0)
        assert body['success'] is True
        bodies[label]=body['result']
        request_rows.append({'label':label,'body_bytes':len(raw),'body_sha256':digest,
                             'request_receipt_sha256':sha(receipt_raw),'exact_URL_query_verified':True})
    pages=[bodies[x] for x in ('history-newest','history-reported-last-page','history-arithmetic-last-page')]
    assert [p['page'] for p in pages]==[1,20,21]
    assert all((p['per_page'],p['total'],p['total_pages'])==(10,202,20) for p in pages)
    assert [len(p['results']) for p in pages]==[10,10,2]
    assert math.ceil(202/10)==21
    history=[row for page in pages for row in page['results']]
    assert len(history)==len({row['seqn'] for row in history})==22
    assert [row['seqn'] for row in history]==sorted([row['seqn'] for row in history],reverse=True)
    assert all(row['tact']=='hero' and row['type']=='versions' and row['refs']['versions']=='/api/manifest/hero/versions?seqn='+str(row['seqn']) for row in history)
    oldest=history[-1]
    manifest=bodies['earliest-observed-versions']
    assert oldest['seqn']==manifest['seqn']==1070978 and oldest['created_at']==manifest['created_at']=='2022-06-10T22:11:07.975919Z'
    versions=manifest['data']
    assert len(versions)==6 and sorted(row['region'] for row in versions)==['cn','eu','kr','sg','tw','us']
    assert all((row['build_id'],row['version_name'],row['build_config'])==(88122,'2.55.2.88122','dbf59f1c7f77eff9fc4ece5e6b0f87d7') for row in versions)
    original=WORK/'TEN_GREYMANE_source_41810.StormReplay'
    assert sha(_read(original,5*1024*1024))==ORIGINAL_SHA
    protocol=load_protocol(41810)
    assert protocol.recovery_schema_sha256=='879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd'
    archive=MPQArchive(original)
    try:
        header_raw=archive.header['user_data_header']['content']
        header=protocol.decode_replay_header(header_raw)
    finally:archive.close()
    assert encode_header(header,protocol)==header_raw
    v=header['m_version']
    assert (v['m_major'],v['m_minor'],v['m_revision'],v['m_build'],v['m_baseBuild'],header['m_dataBuildNum'])==(0,17,0,41810,41810,41810)
    assert header['m_ngdpRootKey']['m_data'].hex()==ROOT and header['m_fixedFileHash']['m_data'].hex()==FIXED
    # Fail closed on any unexpected network call or producer report-write call.
    counters={'network_attempts':0,'producer_report_write_attempts':0}
    def block_network(*args,**kwargs):
        counters['network_attempts']+=1
        raise RuntimeError('Independent offline review disallows network')
    def block_write(*args,**kwargs):
        counters['producer_report_write_attempts']+=1
        raise RuntimeError('Independent review disallows producer report writes')
    patches=[(socket,'create_connection',socket.create_connection),(socket,'getaddrinfo',socket.getaddrinfo),
             (socket.socket,'connect',socket.socket.connect),(socket.socket,'connect_ex',socket.socket.connect_ex)]
    try:
        for obj,key,_ in patches:setattr(obj,key,block_network)
        namespace=runpy.run_path(str(producer),run_name='independent_offline_review_import')
        namespace['analyze'].__globals__['write_new_report']=block_write
        fresh=namespace['analyze']()
    finally:
        for obj,key,old in patches:setattr(obj,key,old)
    assert counters=={'network_attempts':0,'producer_report_write_attempts':0}
    published_raw=_read(SOURCE/'legacy41810-primary-research-outcome.json',1024*1024)
    assert fresh==json.loads(published_raw)
    rendered=(json.dumps(fresh,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode()
    assert rendered==published_raw and sha(rendered)=='e01531a006f0205853e78086fa6b71e89f1efb8a60af0f0f7716abf5b04c7284'
    assert len(fresh['operation_ledger'])==fresh['actual_primary_fetch_or_search_operations']==12
    assert [row['number'] for row in fresh['operation_ledger']]==list(range(1,13))
    assert len(fresh['direct_primary_response_evidence'])==4 and fresh['direct_API_body_bytes']==5592
    assert fresh['observed_history_boundary']['fetched_history_records']==22 and not fresh['observed_history_boundary']['all202_version_manifests_fetched_or_searched']
    for key in ('exact41810_BuildConfig_found','exact41810_encoding_key_found','authenticated41810_raw_catalog_or_license_rule_source_obtained',
                'old_string_to_current_license_identity_mapping_proven','root_or_fixed_hash_reinterpreted_as_BuildConfig_or_EKey',
                'client_launched','repo_modified','player_names_account_IDs_or_ownership_data_emitted'):
        assert fresh[key] is False
    assert fresh['CDN_object_requests']==fresh['full_client_SDK_archive_downloads']==0
    for path,digest in before.items():assert sha(_read(path,1024*1024))==digest
    assert sha(_read(SOURCE/'legacy41810-research-frozen-receipt.json',1024*1024))==FROZEN
    assert sha(_read(original,5*1024*1024))==ORIGINAL_SHA
    report={'format':'hots-legacy-build-root-independent-review-v1','result':'PASS','material_findings':[],
        'review_source_sha256':sha(_read(Path(__file__),1024*1024)),
        'reviewed_frozen_receipt_sha256':FROZEN,'allowlisted_file_count':11,'all_allowlisted_bytes_and_hashes_verified':True,
        'fresh_report_JSON_matches_frozen':True,'fresh_report_serialized_bytes_match_frozen':True,
        'fresh_report_sha256':sha(rendered),'producer_analyze_only_called_in_RAM':True,'producer_main_or_fetcher_called':False,
        'unexpected_network_attempts':0,'producer_report_write_attempts':0,
        'four_direct_API_evidence_records':request_rows,'direct_API_body_bytes':5592,
        'history_pagination':{'API_reported_total':202,'API_observed_per_page':10,'API_reported_pages':20,'arithmetic_pages':21,
             'fetched_pages':[1,20,21],'fetched_record_counts':[10,10,2],'unique_records_fetched':22,
             'page20_demonstrably_not_final':True,'all202_manifests_fetched':False},
        'oldest_observed_manifest':{'seqn':1070978,'created_at':oldest['created_at'],'build':88122,
             'version':'2.55.2.88122','build_config':'dbf59f1c7f77eff9fc4ece5e6b0f87d7','regions':sorted(x['region'] for x in versions)},
        'fresh_original_header':{'replay_sha256':ORIGINAL_SHA,'canonical_schema_sha256':protocol.recovery_schema_sha256,
             'version':'0.17.0.41810','build_base_data':41810,'root':ROOT,'fixed_file_hash':FIXED,
             'header_binary_roundtrip_exact':True,'no_details_player_chat_or_availability_read':True},
        'source_review':{'four_fetches_are_small_API_routes_not_CDN_objects':True,
             'fetcher_https_host_route_redirect_and_size_guards_reviewed':True,
             'replay_root_or_fixedhash_not_reinterpreted_as_BuildConfig_or_EKey':True,
             'no_exact41810_BuildConfig_or_original_catalog_claim':True,
             'middle_pages_and_other_monitor_generations_explicitly_unsearched':True},
        'all_reviewed_inputs_unchanged':True,'new_network_requests':0,'client_launched':False,'repo_modified':False,
        'limitations':['Review validates saved primary responses and local source/header evidence; it makes no fresh server-state claim.',
             'The first eight descriptive discovery/page/tool ledger entries were inspected for consistency, not independently rerun.',
             'Observed22history entries and one88122manifest do not establish global absence of41810metadata.',
             'No raw original replay/player data is included in this receipt.']}
    output=HERE/'legacy-build-root-independent-review.json'
    write_new_report(report,output)
    print(json.dumps({'result':'PASS','allowlisted_files':11,'RAM_report_exact':True,'report_sha256':sha(_read(output,1024*1024))}))

if __name__=='__main__':main()
