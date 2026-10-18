"""Allowlisted source/provenance summary, excluding all raw private artifacts."""
import datetime,hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery');sys.path.insert(0,str(REPO))
from depot_s2mh_wire import decode_verified_header
from dependency_audit import cache_handle

load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
binding=load(BASE/'one-eu-current-reference-binding.json')
profile=load(BASE/binding['profile_file'])
acq=load(BASE/'four-eu-base-header-acquisition.json')
graph_path=BASE.parent/'cached-eu-package-graph-observation-20261018.json'
graph=load(graph_path)
rows=[]
for entry,receipt in zip(binding['mod_package_bindings'][:4],acq['results'],strict=True):
    handle=entry['terminal_s2mh_handle'];prefix=binding['prefix_handles'][entry['index']]
    group=next(x for x in graph['archive_groups'] if x['archive_digest']==prefix['digest'])
    exact=[x for x in group['candidates'] if x['package_id']==entry['mod_id'] and x['package_version']==entry['version'] and x['header_sha256']==handle['digest']]
    row={'index':entry['index'],'mod_id':entry['mod_id'],'version':entry['version'],'terminal_handle':handle,'prefix_archive_handle':prefix,'cached_previous_candidate_count':len(group['candidates']),'exact_current_tuple_previously_cached':len(exact)==1,'header_acquisition_status':receipt['status'],'header_http_status':receipt['http_status']}
    if receipt['status']=='sha256-and-complete-versioned-wire-verified':
        raw=(BASE/receipt['local_file']).read_bytes()
        tree=decode_verified_header(raw,handle['digest'])[0]
        assert tree[0]=={0:entry['mod_id'],1:entry['version']}
        archive=cache_handle(tree[2]);assert archive==prefix
        cache=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')/handle['relative_path']
        assert cache.read_bytes()==raw
        row.update(header_identity_equals_replay_tuple=True,header_archive_equals_replay_prefix=True,cached_header_bytes_equal_download=True,complete_wire_eof=True)
    rows.append(row)
assert [x['exact_current_tuple_previously_cached'] for x in rows]==[True,True,True,False]
files=['one-eu-candidate-acquisition.json','heroeslounge-27515-g1-20261005.profile.json','one-eu-current-reference-binding.json','four-eu-base-header-acquisition.json','inspect_lounge_page.py','find_dated_candidate.py','acquire_one_lounge.py','inspect_eu_binding.py','fetch_four_eu_base_headers.py','finalize_eu_reference_receipt.py']
report={'format':'hots-one-genuine-current-eu-reference-receipt-v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_match_url':'https://heroeslounge.gg/match/view/27515','source_replay_url':load(BASE/'one-eu-candidate-acquisition.json')['requested_url'],'replay_file_sha256':binding['file_sha256'],'replay_file_bytes':binding['file_bytes'],'raw_replay_or_header_in_publication_allowlist':False,'declared_build_base_data':98348,'root_md5':binding['root_md5'],'verified_core_events':{kind:value['count'] for kind,value in profile['streams'].items()},'official_and_semantic_full_observed_core_roundtrips':True,'schema_build':profile['schema_build'],'schema_file_sha256':profile['schema_file_sha256'],'details_player_region_set':binding['details_player_region_set'],'all_mod_creator_regions':sorted({x['creator_toon_region'] for x in binding['mod_package_bindings']}),'all_terminal_handle_regions':sorted({x['terminal_s2mh_handle']['region'] for x in binding['mod_package_bindings']}),'tail_identity_slot_seed_crosscheck_passed':all(binding['tail_crosscheck'][x] for x in ('details_identity_multiset_equal','all_details_participants_match_tail_by_slot','initdata_identity_multiset_equal','seed_matches_lobby','seed_matches_game_description','disabled_hero_list_equal')),'mod_and_tail_same_profile_full_member_roundtrips':True,'base_package_bindings':rows,'previous_cache_graph_sha256':sha(graph_path),'missing_exact_current_heroesdata_header':True,'cached_936_combinations_are_now_currently_eligible':False,'downloaded_successful_header_body_bytes':acq['downloaded_body_bytes'],'allowlist':[{'file':name,'bytes':(BASE/name).stat().st_size,'sha256':sha(BASE/name)} for name in files],'limitations':['Lost Cavern is an ARAM map; this replay binds shared EU base metadata, not the Dragon Shire final map package.','The exact currently advertised HeroesData EU header returned404 and is absent at its exact conventional cache path; none of13oldercached candidates is substituted.','The previous936relaxed cached combinations are not current choices: all lack the observed exact HeroesData tuple/header.','S2MH package metadata has no verified client-build field; replay provenance supplies the98348 context.','A public tournament origin and content hashes are provenance, not a publisher authenticity signature.','No player names, account identifiers, ownership masks or chat contents are projected.','Whole-target schema coverage, simulation/playback and old-to-current conversion remain unproven.'],'replay_modified':False,'client_launched':False}
out=BASE/'one-eu-current-reference-final-receipt.json'
with out.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'report':out.name,'sha256':sha(out),'base_package_bindings':rows,'allowlisted_files':len(files)},indent=2))
