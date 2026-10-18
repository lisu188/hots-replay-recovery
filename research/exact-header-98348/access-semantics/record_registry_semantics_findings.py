"""Allowlisted static registry/API receipt; raw game texts remain private."""
import hashlib
import json
import re
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
WORK=BASE.parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO),str(WORK/'header-reconstruction')]
from collection_license_audit import _read,write_new_report
from depot_s2mh_wire import decode_verified_header
sha=lambda b:hashlib.sha256(b).hexdigest()
gitblob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
ROOT='c3b3c8bc82e3a5a62e550fdde9a40c28'
OBS='0fa8a041fa8d6b9ba22ba6ff8be10d4f42beccc7d9577d0b6ead2d8e0fa909c9'
COMMIT='e3e57cb640f18002a4feebe3872cefe04072d814'
PUB='https://github.com/jamiephan/HeroesOfTheStorm_Gamedata/blob/'+COMMIT+'/mods/heroesdata.stormmod/base.stormdata/'

def function(text,name):
    lines=text.splitlines()
    start=next(i for i,l in enumerate(lines) if re.match(r'bool '+re.escape(name)+r'\s*\(',l))
    end=next(i for i in range(start+1,len(lines)) if lines[i]=='}')
    return start+1,end+1,'\n'.join(lines[start:end+1])

def main():
    operational=[]
    reports={}
    for name in ('installed-native-filename-inventory.json','installed-heroes-library-filename-inventory.json',
                 'installed-native-three-members.json','installed-heroes-three-members.json'):
        raw=_read(BASE/name,1024*1024);d=json.loads(raw);reports[name]=d
        assert d['root']==d['actual_root_content_md5']==ROOT and d['version']=='2.57.0.98348'
        assert d['blocked_http_attempts_during_casc']==0 and d['denying_http_handler_canary_passed']
        assert d['installed_config_hashes_unchanged'] and not d['cache_enabled'] and not d['online_fallback_flag']
        assert not d['game_client_launched'] and not d['game_storage_modified']
        assert d['config_parsed_from_scratch_copies'] and d['load_flags']=='None'
        assert d['library_clear_succeeded'] is False and d['library_clear_exception_type']=='System.NullReferenceException'
        operational.append({'name':name,'sha256':sha(raw),'bytes':len(raw)})
    bodies={};members=[]
    for name in ('installed-native-three-members.json','installed-heroes-three-members.json'):
        for m in reports[name]['members']:
            assert m['read'] and m['full_casc_content_md5_verified']
            raw=_read(BASE/m['saved_name'],1024*1024)
            assert len(raw)==m['bytes'] and sha(raw)==m['sha256'] and hashlib.md5(raw).hexdigest()==m['casc_content_md5']
            bodies[m['saved_name']]=raw
            members.append({k:m[k] for k in ('casc_path','bytes','casc_content_md5','encoded_key','sha256')})
    assert len(members)==6 and sum(m['bytes'] for m in members)==779428<2*1024*1024
    assert gitblob(bodies['HeroesLib.galaxy'])=='0cf700ed3ae8e5b6dff5c812d2de9bddd7899b0b'
    assert gitblob(bodies['ConfigData.xml'])=='f63298d1a04a7148ca6b32cc161a2eed82da5152'
    heroes=bodies['HeroesLib.galaxy'].decode('utf-8')
    functions=[]
    cases=[
        ('libCore_gf_MetagameIsHeroInRotationForPlayer',('PlayerHasReward','FreeToPlayRewardArray','lv_heroRotationSlotsAvailable += 1'),
         'Required free-rotation reward checks increase the permitted rotation-slot count before a hero-list comparison.'),
        ('libCore_gf_MetagameDoesPlayerHaveAccessToHero',('PlayerHasReward','RequiredRewardArray','GameIsPractice()','GameIsCooperative()','GameModes_TryMe','IsHeroInRotationForPlayer'),
         'Hero access checks required rewards, with explicit AI/human-selection rules and rotation, practice, freebie, TryMe and offline branches.'),
        ('libCore_gf_MetagameDoesPlayerHaveAccessToSkin',('PlayerHasReward','RequiredRewardArray','lp_skinIndex == 1','GameModes_TryMe'),
         'Skin access checks all required rewards, with first-skin, TryMe and offline branches.'),
        ('libCore_gf_MetagameDoesPlayerHaveAccessToMount',('PlayerHasReward','RequiredRewardArray','Flags[FreePlay]','lp_mountIndex == 1'),
         'Mount access checks all required rewards, with free-play, first-mount, TryMe and offline branches.')]
    for name,tokens,meaning in cases:
        first,last,body=function(heroes,name)
        assert all(token in body for token in tokens)
        functions.append({'function':name,'line_start':first,'line_end':last,'source_sha256':sha(bodies['HeroesLib.galaxy']),
                          'url':PUB+'triggerlibs/heroeslib.galaxy#L'+str(first),
                          'static_source_observation':meaning})
    config=bodies['ConfigData.xml'].decode('utf-8')
    rewards=['UnlockExtraFreeToPlayHero'+str(i) for i in range(1,5)]
    assert all('<FreeToPlayRewardArray value="'+r+'" />' in config for r in rewards)
    native_negative={term:sum(len(re.findall(re.escape(term),bodies[n].decode('utf-8'),re.I)) for n in ('natives.galaxy','NativeLib_h.galaxy','NativeLib.galaxy'))
                     for term in ('license','reward','entitle','collection','HyperlinkId')}
    assert all(count==0 for count in native_negative.values())
    whole_six={term:sum(len(re.findall(re.escape(term),raw.decode('utf-8'),re.I)) for raw in bodies.values())
               for term in ('CUnitLicense','UnitLicense','PlayerHasLicense','PlayerHasAccessTo','PlayerHasReward')}
    observed_raw=_read(REPO/'observations/collection-identities-2026-10-18.json',1024*1024)
    assert sha(observed_raw)==OBS
    observed=json.loads(observed_raw)
    assert observed['contains_player_ownership_or_identity_data'] is False
    cases_by_id={row['id']:row for row in observed['cases']}
    old=[]
    for p in (WORK/'depot-headers/original-eu').glob('*.s2mh'):
        raw=_read(p,512*1024);h=decode_verified_header(raw,p.stem)[0]
        if h.get(23):old.append((p.stem,h[23]))
    assert len(old)==1
    oldsha,oldvalues=old[0]
    assert all(type(x) is bytes for x in oldvalues)
    oldnames=[x.decode('ascii') for x in oldvalues]
    assert len(oldnames)==264 and len(set(oldnames))==263
    assert list(dict.fromkeys(oldnames))==cases_by_id['original']['items']==cases_by_id['r8']['items']
    examples=('NovaHoloCloneCloaked','AbathurEvolvedMonstrosity','TownCannonTower')
    example_membership={x:x in oldnames for x in examples}
    assert not any(example_membership.values())
    unique_old=list(dict.fromkeys(oldnames))
    lexical_groups=[('case-sensitive-name-contains-Skin',[x for x in unique_old if 'Skin' in x]),
                    ('remaining-name-contains-Mount',[x for x in unique_old if 'Skin' not in x and 'Mount' in x]),
                    ('remaining-names',[x for x in unique_old if 'Skin' not in x and 'Mount' not in x])]
    assert sum(len(values) for _,values in lexical_groups)==263
    current_sha='0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a'
    current=decode_verified_header(_read(WORK/'header-reconstruction/recovered-headers-private'/(current_sha+'.s2mh'),512*1024),current_sha)[0]
    assert 23 not in current and len(current[24])==5497 and len(set(current[24]))==5418
    assert list(dict.fromkeys(current[24]))==cases_by_id['protectors']['items']==cases_by_id['stormblessed']['items']
    sources=[]
    for n in ('inventory_installed_native_filenames.ps1','read_three_installed_native_members.ps1',
              'inventory_installed_heroes_library_filenames.ps1','read_three_installed_heroes_members.ps1',
              'prepare_native_read_helper.py',Path(__file__).name):
        raw=_read(BASE/n,1024*1024);sources.append({'name':n,'bytes':len(raw),'sha256':sha(raw)})
    report={'format':'hots-static-registry-current-access-API-semantics-v1',
        'status':'current-access-API-authenticated-historical-transition-unresolved',
        'producer_sha256':sha(_read(Path(__file__),1024*1024)),
        'installed_version':'2.57.0.98348','actual_decoded_root_md5':ROOT,
        'operation_reports':operational,'research_sources':sources,
        'native_and_text_file_count':6,'total_native_and_text_bytes':779428,'maximum_files':8,'maximum_total_bytes':2097152,
        'private_static_text_inputs':members,'raw_text_publishable':False,
        'actual_CASC_and_public_source_binding':[
            {'file':'HeroesLib.galaxy','git_blob_sha1':gitblob(bodies['HeroesLib.galaxy']),
             'public_commit':COMMIT,'GitHub_returned_blob_equals_current_CASC_blob':True,
             'url':PUB+'triggerlibs/heroeslib.galaxy'},
            {'file':'ConfigData.xml','git_blob_sha1':gitblob(bodies['ConfigData.xml']),
             'public_commit':COMMIT,'GitHub_returned_blob_equals_current_CASC_blob':True,
             'url':PUB+'gamedata/configdata.xml#L1065'}],
        'current_authenticated_functions':functions,
        'current_Config_FreeToPlayRewardArray':{'catalog_names':rewards,'line_start':1065,'line_end':1068,
                                                 'source_sha256':sha(bodies['ConfigData.xml'])},
        'bounded_lexical_negatives':{'three_Core_native_texts':native_negative,'six_read_texts':whole_six,
                                    'absence_from_complete_engine_API_not_claimed':True},
        'fresh_static_registry_crosscheck':{'catalog_observation_sha256':OBS,'old_header_sha256':oldsha,
            'old_field':23,'old_type':'array-of-ASCII-byte-blobs','old_raw_count':264,'old_first_dedup_count':263,
            'old_first_dedup_equals_original_and_R8':True,'checked_named_unit_membership':example_membership,
            'claimed_three_named_units_are_not_in_old263_registry':True,
            'old_lexical_groups_only_not_catalog_types':[{'rule':rule,'count':len(values),'first_source_order_samples':values[:5]} for rule,values in lexical_groups],
            'current_header_sha256':current_sha,'current_field':24,'current_type':'array-of-wire-integers',
            'current_field23_absent':True,'current_raw_count':5497,'current_first_dedup_count':5418,
            'current_first_dedup_equals_two_current_catalog_observations':True,
            'registry_is_package_bound_not_a_per_player_list':True,
            'this_alone_does_not_assign_32byte_record_semantics':True},
        'separate_SC2_primary_declaration_evidence':{
            'url':'https://github.com/SC2Mapster/SC2GameData/blob/6dd323aae4209a01f110719a00b4e8f7a88389bc/mods/core.sc2mod/base.sc2data/TriggerLibs/natives.galaxy',
            'declarations':['PlayerHasLicense(int,int)','PlayerHasAccessTo(int,string)','PlayerHasReward(int,string)'],
            'scope':'SC2 public game-data source only; not authenticated HotS41810 or98348 native declaration proof.'},
        'historical_search':{'qualifying_HotS41810_native_or_CUnitLicense_source_found':False,
            'exact_negative_terms':['CUnitLicense','UnitHasLicense','UnitHasReward','LicensedUnit'],
            'negative_scope':'Bounded GitHub/web exact-symbol searches and the six named current text files; no global absence claim.'},
        'conclusions':{
            'current_reward_dependent_access_helpers_and_free_access_branches_proven':True,
            'legacy_field23_to_current_field24_semantic_conversion_proven':False,
            'legacy_personal_ownership_meaning_proven':False,
            'PlayerHasReward_calls_bound_to_availability32byte_record_bits':False,
            'account_ownership_or_slot_pattern_meaning_proven':False,
            'legacy_alias_or_207_name_mappings_added':0},
        'guards':{'original_CASC_guard_provenance':str('research/installed-casc-98348/primary-source-guard-provenance.json'),
            'unchanged_managed_DLL_SHA256':'8be4b72776a3a4eca6708cc204860c51592c8f886224dd6ccbdec03b6fa82a11',
            'actual_MNDX_names_confirmed_before_selective_reads':True,
            'four_operations_HTTP_handler_canary_passed':True,'four_operations_HTTP_transport_attempts':0,
            'cache_enabled':False,'online_fallback_enabled':False,'installed_config_hashes_unchanged':True,
            'configuration_loader_ReadWrite_access_limited_to_existing_task_copies':True,
            'installed_index_data_streams_explicit_read_only':True,
            'partial_private_path_Clear_NullReferenceException_retained':True},
        'raw_player_or_account_data_read_or_emitted':False,'replay_or_availability_bytes_read':False,
        'client_launched':False,'replay_modified':False,'new_header_trials':0,
        'limitations':[
            'Native helper files do not contain the complete engine-native declaration set.',
            'The current functions show access checks and their branches, not the implementation of PlayerHasReward.',
            'No primary41810 declaration or code binds the old name registry to a licensed-unit API.',
            'The two wire arrays are static registry universes; per-entry availability interpretation remains a distinct problem.',
            'No ownership projection, alias guess, default value, new replay or conversion is produced.']}
    output=BASE/'registry-access-semantics-findings-v2.json'
    write_new_report(report,output)
    print(json.dumps({'report_sha256':sha(_read(output,1024*1024)), 'files':6,'text_bytes':779428,
                      'current_functions':len(functions),'historical_conversion_proven':False}))

if __name__=='__main__':main()
