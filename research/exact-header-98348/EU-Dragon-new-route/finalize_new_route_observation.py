"""Offline deterministic summary of this bounded research acquisition only.

Does not repeat requests or reread player data. Prefix raw bytes were RAM-only;
this verifier checks saved acquisition metadata, source pins and private HTML
hashes, not a second independent replay-header decode.
"""
from pathlib import Path
import hashlib, json, re
BASE=Path(__file__).resolve().parent
WORK=BASE.parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
FILES=('probe_primary_route_first_batch.py','probe_new_primary_route.py','probe_observed_replay_header.py','probe_27490_dragon_header.py')
def read(path,limit=1024*1024):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:raise ValueError('Input type/size differs')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Growing input exceeds cap')
    return raw

def verify():
    raw=read(BASE/'route-ledger.json',128*1024);ledger=json.loads(raw);ops=ledger['external_operations']
    if len(ops)!=8 or ledger['maximum_external_operations']!=8:raise ValueError('Bounded operation ledger differs')
    direct=[x for x in ops if x['transport'].startswith('urllib')]
    headers=[x for x in ops if x['transport']=='urllib-range']
    if len(direct)!=5 or len(headers)!=2 or ledger['full_replays_acquired']!=0:raise ValueError('Acquisition counts differ')
    for row in direct:
        if row['request_attempts']!=1 or row['hidden_retries']!=0 or sha(read(BASE/row['producer_file']))!=row['producer_sha256']:raise ValueError('Executed source/request pin differs')
    for label,row in [('nexus-rumble',ops[1]),('match-27430',ops[2]),('match-27490',ops[6])]:
        page=read(BASE/(label+'.private.html'))
        if len(page)!=row['body_bytes'] or sha(page)!=row['sha256'] or row['http_status']!=200:raise ValueError('Saved primary page differs')
    builds=[]
    for row,expected in zip(headers,(97771,98025)):
        if row['http_status']!=206 or row['body_bytes_read']!=4096 or row['content_length']!='4096' or not re.fullmatch(r'bytes 0-4095/\d+',row['content_range']):raise ValueError('Strict prefix acquisition differs')
        h=row['decoded_header'];v=h['version']
        if v['m_build']!=v['m_baseBuild'] or v['m_build']!=h['data_build'] or h['data_build']!=expected or row['current98348'] is not False:raise ValueError('Actual rejection version differs')
        if row['header_decode_outcome']!='success' or row['schema_sha256']!='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84' or row['official_decoder_sha256']!='c5e4e7c588ebc2ef722ab9fd9def2e67e309c45d451639cfdee3126b0f616a42':raise ValueError('Official decode pin differs')
        builds.append({'source_match_url':row['source_match_url'],'source_replay_url':row['url'],'primary_page_map':'DragonShire','actual_executable_base_data_build':expected,'actual_NGDP_root':h['NGDP_root'],'strict206_prefix_bytes':4096,'prefix_sha256':row['prefix_sha256'],'replay_total_bytes_from_Content_Range':row['total_replay_bytes'],'full_replay_acquired':False,'actual_replay_region_decoded':False,'admitted_as_currentEUDragon':False})
    sources={name:sha(read(BASE/name)) for name in FILES+(Path(__file__).name,)}
    if sha(read(BASE/'route-ledger.json',128*1024))!=sha(raw):raise ValueError('Ledger changed')
    return {'format':'bounded-new-current-EU-Dragon-route-observation-v1','ledger_sha256':sha(raw),'producer_source_sha256':sources,'scope':{'original_external_operation_cap':6,'specific_followup_page_prefix_extension':2,'logical_external_operations':8,'directly_instrumented_HTTP_requests':5,'web_tool_operations':3,'web_tool_underlying_HTTP_requests_and_body_bytes':'not exposed; not included in instrumented byte count','instrumented_application_body_bytes':sum(x.get('body_bytes',x.get('body_bytes_read',0)) for x in direct),'instrumented_HTML_bytes':sum(x.get('body_bytes',0) for x in direct),'strict_prefix_bytes':sum(x['body_bytes_read'] for x in headers),'full_replay_downloads':0,'client_launches':0,'no_redirects_or_hidden_retries_in_instrumented_requests':True},'header_screenings':builds,'result':{'new_actual98348EUDragon_reference':False,'currentEUDragon_package_tuple_established':False,'currentEUDragon_s2mh_handle_established':False,'index_date_and_EU_league_labels_not_used_as_actual_build_or_region_proof':True},'new_primary_route_evidence':{'season30_division3_cup_match':'https://www.heroeslounge.gg/en/match/view/27490','official_scheduled_page_date':'25Sep2026 17:00UTC','actual_header_build':98025,'season31_official_round1_date':'19Oct2026','season31_date_source':'https://www.heroeslounge.gg/blog/post/signups-open-season-31'},'limits':['A first web.open could not access the NexusRumble table; its acquisition failure was not labeled replay/schema incompatibility.','Two genuine DragonShire primary page links were tested using pinned official header decoding; both were rejected before whole-file acquisition.','EU labels are primary competition metadata only; no replay.details/initData/lobby region or package graph was decoded from these older prefixes.','No broad absence claim, latest-version inference, payload-based version substitution or playable-migration claim follows.','Raw prefixes were retained only in RAM. This offline summary validates saved metadata and source/page hashes; it is not a second independent decoding of prefix bytes.','No player, account, chat, availability or author data is emitted; private HTML remains excluded from the publication allowlist.']}

if __name__=='__main__':
    result=verify();out=BASE/'current-EU-Dragon-new-route-observation.json'
    with out.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'file':out.name,'sha256':sha(out.read_bytes()),'instrumented_body_bytes':result['scope']['instrumented_application_body_bytes'],'full_replay_downloads':0},sort_keys=True))
