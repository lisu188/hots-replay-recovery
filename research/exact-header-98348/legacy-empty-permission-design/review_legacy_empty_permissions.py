"""Saved-evidence-only design assessment; no replay/header/PE/client I/O."""
from pathlib import Path
import hashlib,json,os,stat
HERE=Path(__file__).resolve().parent
WORKSPACE=HERE.parent.parent
PIN_SHA='cd76e092ad6df3fbc4b10eacf4d3e7d22b56f3cada71fc7074081cfbdbeb9341'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def require(v):
    if not v:raise ValueError('Saved evidence design gate failed')
def read(path,limit=128*1024):
    require(not path.is_symlink())
    with path.open('rb')as stream:
        a=os.fstat(stream.fileno());require(stat.S_ISREG(a.st_mode)and 0<a.st_size<=limit)
        raw=stream.read(limit+1);b=os.fstat(stream.fileno())
    require(len(raw)==a.st_size==b.st_size and a.st_mtime_ns==b.st_mtime_ns);return raw

def width(records,i,depth=0):
    require(depth<=32);r=records[i];kind=r['kind']
    if kind=='USER':return width(records,r['element_type'],depth+1)
    if kind=='STRUCT':return sum(width(records,c,depth+1)for c in r['field_types'])
    if kind in ('INT','ENUM'):return r['bounds']['bits']
    if kind=='BOOL':return 1
    if kind=='FOURCC':return 32
    raise ValueError('Not a fixed scalar/struct span')

def solve_count_width(span,prefix,element):
    require(type(span)is int and type(prefix)is int and type(element)is int and span>=prefix and element>0)
    out=[]
    for w in range(32):
        remaining=span-prefix-w
        if remaining>=0 and remaining%element==0:out.append({'width':w,'elements':remaining//element})
    return out

def review():
    raw=read(HERE/'input-pins.v2.json');require(sha(raw)==PIN_SHA);pins=json.loads(raw);require(len(pins)==17)
    locate=lambda p:Path('C:/Users/andrz/git/hots-replay-recovery')/p[5:]if p.startswith('repo/')else WORKSPACE/p
    bodies={p['path']:read(locate(p['path']))for p in pins}
    for p in pins:require(len(bodies[p['path']])==p['bytes']and sha(bodies[p['path']])==p['sha256'])
    get=lambda p:json.loads(bodies['work/'+p])
    h=get('legacy-header-mapinfo-evidence/original41810-cached-header-MapInfo-evidence.json')
    old=get('legacy-client-layout-constraints.json');s1=get('legacy-39445-control/39445-schema1-player-diagnostic-v2.json')
    mapold=get('legacy-mapinfo-hypothesis/legacy-MapInfo-count-width-hypothesis.json')
    native=get('native-client-codec-ready/native_clientinfo_schema_98348.json');records={r['id']:r for r in native['records']};root=records[1768]
    i=lambda n:root['field_types'][root['field_names'].index(n)]
    prefix=sum(width(records,i(n))for n in ('m_talkerNetworkId','m_voiceSessionId','m_profileAddress'))
    element=width(records,181);require((prefix,element)==(168,96)and records[1828]['bounds']['bits']==31)
    require(h['aggregate']['exact_shared_field_matches']==75 and h['aggregate']['exact_shared_field_mismatches']==0)
    for x in h['headers']:
        p=next(r for r in x['shared_current_named_fields']if r['candidate_MapInfo_field']=='m_requiredPermissions')
        require(p['explicit_tag_present']and p['versioned_ARRAY_wire_tag']and p['header_array_empty']and p['candidate_array_empty']and p['wire_path']=='root/0/17')
    require(len(h['headers'])==5)
    for r in old['results']:
        require(r['players']==10 and r['candidate7_count_histogram']=={'0':10}and r['candidate7_all_175bit_boundaries_exact']and r['current_native_first5_named_fields_prefix_complete_match']and r['candidate7_rating_flags_and_build_anchors_exact']and r['candidate31_permission_payload_exceeds_remaining_member_records']==10)
    require(old['original_R8_candidate_slices_identical_in_order'])
    r=s1['result'];require(r['players']==10 and r['candidate7_count_histogram']=={'0':10}and r['candidate7_175bit_boundary_matches']==10 and r['native_current_first5_prefix_matches']==10 and r['candidate31_permission_payload_physically_impossible_records']==10 and r['full_schema1_EOF_and_member_reencoding_exact'])
    require(sum(len(c['entries'])for c in mapold['cases'])==16)
    for c in mapold['cases']:
        for e in c['entries']:require(e['derived_7bit_count_graph']['permission_count']==0 and e['derived_7bit_count_graph']['final_two_widths']==[1,7])
    missing=width(records,i('m_playerLevel'))+width(records,i('m_hasActiveBoost'));require(missing==33)
    full=get('native-lobby-parent-study/native_startgame_schema_98348.json');fullrecords={r['id']:r for r in full['records']}
    hero=fullrecords[1852];newflags=('m_isLobbyVoiceSilenced','m_isTeamVoiceSilenced','m_isBlizzardStaff')
    require(all(width(fullrecords,hero['field_types'][hero['field_names'].index(n)])==1 for n in newflags))
    require('m_combinedRaceLevels'in fullrecords[1851]['field_names']and 'm_playerLevel'not in fullrecords[1851]['field_names'])
    primary=bodies['work/current-parser-research/ReplayInitData.cs'];tree=get('htc-fixture-headers-ready/source-binding.json')
    blob=hashlib.sha1(b'blob '+str(len(primary)).encode()+b'\0'+primary).hexdigest();require(blob=='d2c163a73c92515ab18e90ef857785c20a646e23')
    require(any(r['path']=='Heroes.StormReplayParser/MpqFiles/ReplayInitData.cs'and r['sha']==blob for r in tree['tree']))
    oldprotocol=bodies['work/heroprotocol/heroprotocol/versions/protocol41810.py'].decode();modernprotocol=bodies['work/heroprotocol/heroprotocol/versions/protocol96477.py'].decode()
    require('m_combinedRaceLevels'in oldprotocol and 'm_hasActiveBoost'not in oldprotocol and 'm_hasActiveBoost'in modernprotocol)
    tail=bodies['repo/battlelobby_tail.py'].decode();require("if modern:\n            scalar(path+'/unknown_bool', 1)"in tail and "scalar(path+'/account_level', 32)"in tail)
    solution=solve_count_width(175,prefix,element);require(solution==[{'width':7,'elements':0}])
    out={'format':'legacy-empty-permission-conversion-design-review-v2','producer_sha256':sha(read(Path(__file__))),'input_pins_sha256':PIN_SHA,'source_pins':pins,'saved_client_record_observations':30,'independently_acquired_replay_record_observations':20,'R8_is_duplicate_source_evidence_not_independent_replication':True,'unique_accounts_or_people_count_inferred':False,'saved_MapInfo_record_observations':16,'old_original_exact_header_controls':5,'old_original_header_common_positive_comparisons':75,'old_original_explicit_empty_ARRAY17_controls':5,'current_shared_native_permission_type':1828,'current_count_bits':31,'permission_handle_bits':element,'client_pre_count_fixed_span_bits':prefix,'source_client_candidate_span_bits':175,'conditional_width_solution':solution,'conditional_proof_scope':'Given unchanged168-bit scalar prefix, one variable permission array of fixed96-bit elements, no unmodeled padding/fields and independently anchored175-bit source span, exactly7count bits and0elements fit. This does not prove those historical modeling premises.','isolated_MapInfo_empty_list_framing_conversion_recommended_for_exact_original_profile':True,'isolated_ClientInfo_empty_segment_conversion_recommended_as_strict_observed_profile':True,'complete_ClientInfo_count_only_conversion_admissible':False,'current_required_tail_fields_absent_from_historical_profile':[{'name':'m_playerLevel','bits':32},{'name':'m_hasActiveBoost','bits':1}],'missing_current_tail_bits_per_record':missing,'additional_current_only_Hero_flags':[{'name':n,'bits':1}for n in newflags],'current_Hero_extra_field_bits_beyond_historical_profile':missing+3,'old_saved_reports_expose_shared_player_branch_histogram':False,'TalkerId_choice2_histogram_is_not_shared_player_branch_evidence':True,'source_combinedRaceLevels_optional_u32_alias_to_playerLevel_established':False,'source_old_initData_contains_named_boost_field':False,'primary_HTC_boost_read_minimum_build':69947,'primary_HTC_voice_silence_read_minimum_build':61718,'primary_HTC_staff_read_minimum_build':66977,'primary_HTC_InitData_combinedRaceLevels_read_is_discarded':True,'nonempty_legacy_permission_counts_supported':False,'old_native_names_or_general_schema_authenticated':False,'new_current_tail_field_defaults_authorized':False,'replay_header_PE_or_network_inputs_opened':False,'repo_profiles_replays_or_private_values_written':False}
    for p in pins:require(sha(read(locate(p['path'])))==p['sha256'])
    out['all_saved_evidence_source_guards_unchanged']=True
    return out
if __name__=='__main__':
    target=HERE/'legacy-empty-permission-conversion-design-review-v2.json';require(not target.exists()and not target.is_symlink())
    data=(json.dumps(review(),indent=2,sort_keys=True)+'\n').encode();require(len(data)<=32*1024)
    with target.open('xb')as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
