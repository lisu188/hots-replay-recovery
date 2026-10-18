"""Reproduce a sanitized, scoped legacy-build research receipt without network."""
from pathlib import Path
import hashlib,json,math

from collection_license_audit import _read,write_new_report
from mpq_reader import MPQArchive
from protocol_loader import load_protocol

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
ORIGINAL_SHA='e8f167cbb163f178c3f01c0eaf6eba393d9f010c2eec533e3ca82c35e7f4c824'
ROOT='83d43a8647bb5ca5caa6f2f09064da55'
FIXED='c585f3548fb8f9776fa1fba4dfec2b9a'
PINS={
    'history-newest':'df5071abe7aed29b93a1429241ef973f8e0365431ae185f735905c9b88369c64',
    'history-reported-last-page':'5dfc3c236cfc45b2792294b92ab1332054952d604819a1797018ed9de461c902',
    'history-arithmetic-last-page':'4b32078d72dbf6412f307b06474ec4a307f3e139c250bb57a223d0043e4bd3f6',
    'earliest-observed-versions':'394313bfd683966a085d0e5e3d3ae9c907a2fc4fc8a1f8c948ae1a05d61bebd0',
}
OPERATIONS=[
    {'number':1,'kind':'primary_repository_discovery_search','query':'site:github.com "ngdp-builds" "hero"','outcome':'no_results'},
    {'number':2,'kind':'primary_repository_discovery_search','query':'site:github.com "BlizzTrack" "hero" "versions"','outcome':'no_results'},
    {'number':3,'kind':'primary_source_discovery_search','query':'NGDP build archive Heroes Storm GitHub buildconfig','outcome':'combined_batch_identified_primary_monitor_and_library_sources_no_41810_config'},
    {'number':4,'kind':'primary_monitor_discovery_search','query':'"hero" "builds" "BlizzTrack"','outcome':'combined_batch_identified_primary_monitor_and_library_sources_no_41810_config'},
    {'number':5,'kind':'primary_monitor_page','url':'https://www.blizztrack.com/en','outcome':'homepage_read_and_documented_API_link_observed'},
    {'number':6,'kind':'primary_monitor_exact_build_search','query':'site:blizztrack.com/config/hero "B41810"','outcome':'no_results'},
    {'number':7,'kind':'primary_API_documentation','url':'https://www.blizztrack.com/docs','outcome':'documented_hero_seqn_and_versions_routes_with_page_limit_and_seqn_parameters'},
    {'number':8,'kind':'primary_history_API_web_tool_attempt','url':'https://www.blizztrack.com/api/manifest/hero/seqn?file=versions&page=1&limit=1','outcome':'web_tool_could_not_access_URL_no_server_status_established'},
    {'number':9,'kind':'primary_history_API_direct','evidence_label':'history-newest'},
    {'number':10,'kind':'primary_history_API_direct','evidence_label':'history-reported-last-page'},
    {'number':11,'kind':'primary_history_API_direct','evidence_label':'history-arithmetic-last-page'},
    {'number':12,'kind':'primary_version_manifest_direct','evidence_label':'earliest-observed-versions'},
]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def analyze():
    path=WORK/'TEN_GREYMANE_source_41810.StormReplay'
    if sha(_read(path,5*1024*1024))!=ORIGINAL_SHA:raise ValueError('Original source digest differs')
    protocol=load_protocol(41810)
    if protocol.recovery_schema_sha256!='879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd':
        raise ValueError('Canonical41810 schema differs')
    archive=MPQArchive(path)
    try:header=protocol.decode_replay_header(archive.header['user_data_header']['content'])
    finally:archive.close()
    version=header['m_version']
    if (version['m_major'],version['m_minor'],version['m_revision'],version['m_build'],version['m_baseBuild'],header['m_dataBuildNum'])!=(0,17,0,41810,41810,41810):
        raise ValueError('Source version differs')
    if header['m_ngdpRootKey']['m_data'].hex()!=ROOT or header['m_fixedFileHash']['m_data'].hex()!=FIXED:
        raise ValueError('Source header identities differ')
    evidence=[];data={}
    for label,expected in PINS.items():
        body_path=HERE/(label+'.body.json');raw=_read(body_path,131072)
        request_path=HERE/(label+'.request.json');request_raw=_read(request_path,8192);request=json.loads(request_raw)
        if sha(raw)!=expected or request['sha256']!=expected or request['bytes']!=len(raw) or request['http_status']!=200:
            raise ValueError('Pinned primary response evidence differs')
        parsed=json.loads(raw)
        if parsed['success'] is not True:raise ValueError('Primary API did not report success')
        data[label]=parsed['result']
        evidence.append({'label':label,'url':request['url'],'http_status':200,'acquired_at_utc':request['requested_at_utc'],
            'body_bytes':len(raw),'body_sha256':expected,'request_receipt_sha256':sha(request_raw),
            'body_file':body_path.name,'request_receipt_file':request_path.name})
    first=data['history-newest'];last=data['history-arithmetic-last-page'];reported=data['history-reported-last-page']
    if (first['page'],first['per_page'],first['total'],first['total_pages'])!=(1,10,202,20):raise ValueError('History pagination evidence differs')
    if last['page']!=21 or len(last['results'])!=2 or reported['page']!=20 or len(reported['results'])!=10:
        raise ValueError('Last-page control differs')
    oldest=last['results'][-1];manifest=data['earliest-observed-versions']
    if oldest['seqn']!=1070978 or manifest['seqn']!=1070978 or manifest['created_at']!=oldest['created_at']:
        raise ValueError('Oldest observed history link differs')
    versions=manifest['data']
    if len(versions)!=6 or any(row['build_id']!=88122 or row['version_name']!='2.55.2.88122'
        or row['build_config']!='dbf59f1c7f77eff9fc4ece5e6b0f87d7' for row in versions):
        raise ValueError('Earliest observed manifest version differs')
    if sha(_read(path,5*1024*1024))!=ORIGINAL_SHA:raise ValueError('Source changed during verification')
    return {
        'format':'hots-legacy41810-build-root-bounded-primary-research-v1',
        'source_producer_sha256':sha(Path(__file__).read_bytes()),
        'original_replay_sha256':ORIGINAL_SHA,'canonical_header_schema_sha256':protocol.recovery_schema_sha256,
        'source_header_projection':{'version':'0.17.0.41810','build':41810,'base_build':41810,'data_build':41810,
            'm_ngdpRootKey_m_data':ROOT,'m_fixedFileHash_m_data':FIXED},
        'maximum_primary_fetch_or_search_operations':12,'actual_primary_fetch_or_search_operations':len(OPERATIONS),
        'operation_ledger':OPERATIONS,'direct_primary_response_evidence':evidence,
        'direct_API_body_bytes':sum(row['body_bytes'] for row in evidence),
        'web_tool_search_or_page_transfer_bytes_measured':False,
        'primary_history_route_documentation':'https://www.blizztrack.com/docs',
        'observed_history_boundary':{
            'API_reported_records':first['total'],'API_reported_per_page':first['per_page'],
            'API_reported_total_pages':first['total_pages'],'arithmetic_page_count':math.ceil(first['total']/first['per_page']),
            'requested_limit_was_1_but_observed_per_page_was_10':True,
            'API_reported_last_page_20_was_not_actually_final':True,
            'observed_page21_record_count':2,'fetched_history_pages':[1,20,21],
            'fetched_history_records':sum(len(data[label]['results']) for label in ('history-newest','history-reported-last-page','history-arithmetic-last-page')),
            'oldest_returned_seqn':oldest['seqn'],'oldest_returned_created_at':oldest['created_at'],
            'oldest_returned_manifest_version':'2.55.2.88122','oldest_returned_manifest_build':88122,
            'oldest_returned_manifest_build_config':'dbf59f1c7f77eff9fc4ece5e6b0f87d7',
            'oldest_manifest_regions':sorted(row['region'] for row in versions),
            'all202_version_manifests_fetched_or_searched':False,
        },
        'exact41810_BuildConfig_found':False,'exact41810_encoding_key_found':False,
        'authenticated41810_raw_catalog_or_license_rule_source_obtained':False,
        'old_string_to_current_license_identity_mapping_proven':False,
        'CDN_object_requests':0,'root_or_fixed_hash_reinterpreted_as_BuildConfig_or_EKey':False,
        'full_client_SDK_archive_downloads':0,'client_launched':False,'repo_modified':False,
        'player_names_account_IDs_or_ownership_data_emitted':False,'original_source_digest_unchanged':True,
        'remaining_authoritative_inputs_needed':[
            'An archived41810 BuildConfig bound to the exact replay root and fixed-file hash, with its actual encoding metadata keys.',
            'Authenticated original catalog/reward definitions or original collection/license rules; later88122 or current data cannot substitute.',
        ],
        'limitations':[
            'This is a twelve-operation bounded negative lookup, not proof that the original build metadata is unavailable everywhere.',
            'Only observed history pages1/20/21 and the oldest returned version manifest were retrieved. Middle pages and other monitor generations were not exhausted.',
            'The current documented history tail returns a2022 manifest for88122. No old41810 BuildConfig was inferred from that different build.',
            'The replay root field and fixed-file hash were preserved as observed identities; no unknown content-key/encoding-key conversion or CDN filename was guessed.',
            'Primary monitor records are provenance observations rather than cryptographic publisher signatures.',
        ],
    }


if __name__=='__main__':
    report=analyze();output=HERE/'legacy41810-primary-research-outcome.json'
    write_new_report(report,output)
    print(json.dumps({'operations':report['actual_primary_fetch_or_search_operations'],'direct_API_body_bytes':report['direct_API_body_bytes'],
        'oldest_returned_build':report['observed_history_boundary']['oldest_returned_manifest_build'],
        'exact41810_config_found':False,'report_sha256':sha(output.read_bytes())},sort_keys=True))
