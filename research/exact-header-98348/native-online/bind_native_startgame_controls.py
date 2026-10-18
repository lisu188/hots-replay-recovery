"""Whole native OnlineStartGameRequest binding; no replay or client created."""
from collections import Counter
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;WORK=HERE.parent
REPO=Path(r'C:\Users\andrz\git\hots-replay-recovery')
sys.path[:0]=[str(HERE),str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps'),
    str(WORK/'availability-vector-expanded-ready'),str(WORK/'availability-vector-ready'),
    str(WORK/'availability-representation-ready')]
import native_startgame as native
import audit_expanded_account_vectors as cohort
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import decode_tail,crosscheck
from protocol_loader import load_protocol
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def positions(tail):
    position=len(tail.prefix)*8;result={}
    for token in tail.tokens:
        if token.width is None:position+=(-position)%8
        result[token.path]=position
        position+=len(token.value)*8 if token.width is None else token.width
    require(position==tail.member_bytes*8,'Observed tail extent differs')
    return result

def bind_anchors(info,mods,tail):
    observed=positions(tail)
    wanted={'/StartGameRequest/m_mapInfoList','/StartGameRequest/m_headerCacheHandles',
        '/StartGameRequest/m_resourceMap','/StartGameRequest/m_accessMatrix','/StartGameRequest/m_disabledHeroList',
        '/m_clientInfoList','/m_clientUnlockableInfoList','/m_achievementTags','/m_clientLicensesList','/m_heroMasteryTiers'}
    for i in range(len(mods['entries'])):wanted.add('/StartGameRequest/m_mapInfoList/'+str(i))
    for i in range(len(tail.players)):wanted.add('/m_clientInfoList/'+str(i))
    fields={f.path:f for f in info.fields if f.kind!='USER' and f.path in wanted}
    for index,entry in enumerate(mods['entries']):
        f=fields['/StartGameRequest/m_mapInfoList/'+str(index)]
        require((f.start_bit,f.end_bit)==(entry['start_bit'],entry['end_bit']),'Native MapInfo record boundary differs')
    for index in range(len(tail.players)):
        f=fields['/m_clientInfoList/'+str(index)]
        start=observed[f'/players/{index}/unknown32']
        end=observed[f'/players/{index+1}/unknown32'] if index+1<len(tail.players) else tail.report['boundaries_bits']['players_end']
        require((f.start_bit,f.end_bit)==(start,end),'Native ClientInfo record boundary differs')
    checks=[
        ('MapInfoList_end',fields['/StartGameRequest/m_mapInfoList'].end_bit,mods['mod_metadata_end_bit']),
        ('HeaderCacheHandles_end',fields['/StartGameRequest/m_headerCacheHandles'].end_bit,mods['terminal_handles_end_bit']),
        ('ResourceMap_start',fields['/StartGameRequest/m_resourceMap'].start_bit,observed['/collections/count']),
        ('ResourceMatrix_start',fields['/StartGameRequest/m_accessMatrix'].start_bit,observed['/availability/count']),
        ('DisabledHeroList_start',fields['/StartGameRequest/m_disabledHeroList'].start_bit,observed['/disabled_heroes/count']),
        ('ClientInfoList_end',fields['/m_clientInfoList'].end_bit,tail.report['boundaries_bits']['players_end']),
        ('ClientUnlockables_start',fields['/m_clientUnlockableInfoList'].start_bit,observed['/end/hero_tables/count']),
        ('ClientUnlockables_end',fields['/m_clientUnlockableInfoList'].end_bit,observed['/end/cstm/count']),
        ('AchievementTags_end',fields['/m_achievementTags'].end_bit,observed['/end/a41_or_a48/count']),
        ('ClientLicenses_end',fields['/m_clientLicensesList'].end_bit,observed['/end/unknown23/0']),
        ('HeroMasteryTiers_start',fields['/m_heroMasteryTiers'].start_bit,observed['/end/allheroes/count']),
        ('HeroMasteryTiers_end',fields['/m_heroMasteryTiers'].end_bit,observed['/end/unknown2/0'])]
    require(all(actual==expected for _,actual,expected in checks),'Native whole-message/observed selected anchor differs')
    return {'named_surrounding_anchors_checked':len(checks),'all_named_surrounding_anchors_match':True,
        'all_MapInfo_record_boundaries_match':True,'all_ClientInfo_record_boundaries_match':True,
        'MapInfo_records':len(mods['entries']),'ClientInfo_records':len(tail.players)}

def analyze():
    budget=cohort.Budget();runtime={}
    for name in ('native_startgame','native_clientinfo','audit_expanded_account_vectors','audit_repeated_account_vectors',
        'audit_availability_representation','battlelobby_tail','battlelobby_attribute_layer','audit_battlelobby_mod_metadata',
        'protocol_loader','mpq_reader','collection_license_audit'):
        path=Path(sys.modules[name].__file__);runtime[name]=(path,sha(budget.read(path,1024*1024,'runtime_source_guards')))
    require(runtime['audit_expanded_account_vectors'][1]=='2f020152115324ef7e309807a9d988bc65b62eb8dcf6e8077988b29cdd2dd9ca','Cohort loader differs')
    require(runtime['audit_repeated_account_vectors'][1]==cohort.PRIOR_SHA,'Prior cohort helper differs')
    require(runtime['audit_availability_representation'][1]==cohort.prior.BASE_HELPER_SHA,'Baseline helper differs')
    require(runtime['native_clientinfo'][1]==native.SHARED_TYPES_SHA256,'Shared native types differ')
    specs,legacy,sources=cohort.load_specs(budget)
    protocol=load_protocol(96477)
    require(protocol.recovery_schema_sha256==cohort.previous.SCHEMA_CURRENT,'Official identity schema differs')
    guards=[]
    for _,path,expected,_ in legacy:
        raw=budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads');budget.register(path,len(raw))
        require(sha(raw)==expected,'Original/R8 source differs');guards.append((path,expected))
    original_pin=native._pinned_file
    def counted_pin(path,limit,expected):
        budget.reserve(limit+1);raw=original_pin(path,limit,expected)
        budget.add('native_schema_and_shared_types_pin_reads',len(raw));return raw
    native._pinned_file=counted_pin
    cases=[];padding=Counter();map_count=client_count=field_count=token_count=selected_bytes=0
    try:
        for spec in specs:
            source=budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads');budget.register(spec['path'],len(source))
            require(sha(source)==spec['sha'],'Current source digest differs');guards.append((spec['path'],spec['sha']))
            profile_raw,_=cohort.profile_checked(spec['profile'],spec['profile_sha'],spec['sha'],budget)
            archive=cohort.CountedArchive(spec['path'],budget)
            try:
                header=protocol.decode_replay_header(archive.header['user_data_header']['content'])
                require(header['m_version']['m_build']==98348 and header['m_version']['m_baseBuild']==98348
                    and header['m_dataBuildNum']==98348 and header['m_ngdpRootKey']['m_data'].hex()==cohort.ROOT,'Actual build/root differs')
                raw=cohort.previous.bounded_member(archive,'replay.server.battlelobby')
                details_raw=cohort.previous.bounded_member(archive,'replay.details');init_raw=cohort.previous.bounded_member(archive,'replay.initData')
                mods=audit_member(raw,'observed-11','current-observed');tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
                checks=crosscheck(tail,protocol.decode_replay_details(details_raw),protocol.decode_replay_initdata(init_raw))
                require(checks['all_details_participants_match_tail_by_slot'] and checks['initdata_identity_multiset_equal']
                    and checks['initdata_identity_and_slot_matches']==checks['players_checked'] and checks['seed_matches_lobby']
                    and checks['seed_matches_game_description'] and checks['disabled_hero_list_equal'] is not False,'Private gates differ')
                info=native.decode_startgame(raw,native.PROFILE);summary=info.summary();anchors=bind_anchors(info,mods,tail)
                require(summary['complete_EOF_and_readonly_whole_member_reencoding_exact'],'Native whole-member reencoding differs')
                map_count+=anchors['MapInfo_records'];client_count+=anchors['ClientInfo_records']
                field_count+=len(info.fields);token_count+=len(info.tokens);padding[info.padding_bits]+=1
                selected_bytes+=len(raw)+len(details_raw)+len(init_raw)
                cases.append({'id':spec['id'],'replay_sha256':spec['sha'],'profile_sha256':sha(profile_raw),
                    'actual_build_base_data':98348,'actual_root':cohort.ROOT,'prior_core_profile_bound':True,
                    'fresh_core_event_decode_performed':False,'fresh_observed_full_mod_tail_EOF_and_private_gates':True,
                    'native_OnlineStartGameRequest':summary,'crossbinding':anchors})
                print(json.dumps({'case':spec['id'],'whole_native_root_EOF_exact':True,'fields':len(info.fields),'tokens':len(info.tokens)}),flush=True)
                del info
            finally:archive.close()
    finally:native._pinned_file=original_pin
    require(len(cases)==21,'Complete current cohort required')
    for path,expected in guards:require(sha(budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))==expected,'Source changed after audit')
    for path,expected in runtime.values():require(sha(budget.read(path,1024*1024,'runtime_source_guards'))==expected,'Runtime source changed')
    producer_sha=sha(budget.read(Path(__file__),64*1024,'producer_source_guard'))
    return {'format':'hots-native-whole-OnlineStartGameRequest-21case-binding-v1','producer_sha256':producer_sha,
        'portable_module_sha256':runtime['native_startgame'][1],'schema_sha256':native.SCHEMA_SHA256,
        'source_PE_sha256':native.SOURCE_PE_SHA256,'source_embedded_bytecode_sha256':native.SOURCE_BYTECODE_SHA256,
        'runtime_source_sha256s':{name:row[1] for name,row in sorted(runtime.items())},'source_manifests':sources,
        'canonical_identity_schema_sha256':cohort.previous.SCHEMA_CURRENT,'current_cases':len(cases),'cases':cases,
        'aggregate':{'native_root_type':5917,'named_root_fields_per_message':25,'selected_schema_types':513,
            'all_whole_members_decode_to_EOF_and_reencode_exact':True,'all12_named_anchors_per_message_match':True,
            'MapInfo_records':map_count,'ClientInfo_records':client_count,'decoded_native_fields':field_count,
            'wire_tokens':token_count,'EOF_zero_padding_bit_histogram':dict(sorted(padding.items()))},
        'actual_reads':{'distinct_replay_bytes_including_original_R8':sum(budget.distinct.values()),
            'distinct_replay_files':len(budget.distinct),'explicit_analysis_input_bytes':sum(budget.counts.values()),
            'read_categories':dict(budget.counts),'selected_decoded_member_bytes':selected_bytes,
            'PE_reads_in_this_stage':0,'scope':'Explicit metadata/profile/source guards, native pins and MPQ reads; implicit imports/interpreter reads excluded.'},
        'all_current_original_and_R8_source_hashes_unchanged':True,'network_used':False,'game_client_or_DLL_executed':False,
        'prior_local_attempts':[{'failure':'Validator used aggregate opaque path instead of its actual /0 token path',
            'exception_class':'KeyError','cases_decoded_before_failure':1,'format_failure_claimed':False,
            'prior_attempt_input_reads_in_successful_final_run_ledger':False}],
        'private_author_player_license_or_network_values_emitted':False,'replay_or_header_written':False,
        'historical_conversion_or_deterministic_compatibility_proven':False,'full_upgrade_complete':False}

if __name__=='__main__':
    output=HERE/'native-online-startgame-21case-binding.json';require(not output.exists(),'Refuse existing observation')
    data=(json.dumps(analyze(),sort_keys=True,indent=2)+'\n').encode();require(len(data)<=256*1024,'Report cap exceeded')
    with output.open('xb') as stream:stream.write(data)
    print(json.dumps({'observation_bytes':len(data),'observation_sha256':sha(data)}),flush=True)
