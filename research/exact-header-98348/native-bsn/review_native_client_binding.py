"""Independent native graph and replay-wire verification, aggregates only."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from independent_bsn_graph import Graph,load,require,PE_SHA,BLOB_SHA
from independent_client_bits import Wire
from collection_license_audit import _read,write_new_report
from protocol_loader import load_protocol
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import decode_tail,crosscheck
import audit_expanded_account_vectors as cohort

WORK=Path(__file__).resolve().parents[1]
RESEARCH=WORK/'native-embedded-schema-98348'
PINS={
 'native_client_layout.py':'14cd9d119b4b26a5b479f410412377e2c93c7fab6c813bc5df42e74e0e2772d9',
 'native-ClientInfo-current-21case-binding.json':'a0145b4e33ffca51f2658486f55c78a6a3b97744ad085d6026009f6d534377b5',
 'native-BSN-metadata-98348-v2.json':'cf7204cb7b26f4d1cdcf92930bee154932fa2cbe9f27f4d10daf7be6ef3f0256'}
ANCHORS={'/m_clientId':'/unknown32','/m_playerScope':'/slot','/m_toonHandle':'/toon/region',
 '/m_toonName':'/string_toon/region','/m_talkerInfo':'/name_flag','/m_talkerInfo/m_id/m_id':'/unknown2bits',
 '/m_talkerNetworkId':'/secondary/present','/m_rating':'/optional64/present',
 '/m_clientBuildVersion/value':'/community_named_build32','/m_sharedPlayerInfo':'/collection_choice',
 '/m_accountNickname':'/tag/present','/m_playerLevel':'/account_level','/m_hasActiveBoost':'/boost_flag'}
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def pin_files():
 for name,digest in PINS.items():require(sha(_read(RESEARCH/name,128*1024))==digest)

def positions(tail):
 at=len(tail.prefix)*8;result={}
 for token in tail.tokens:
  if token.width is None:at=(at+7)//8*8
  result[token.path]=at
  at+=len(token.value)*8 if token.width is None else token.width
 require(at==tail.member_bytes*8)
 return result

def check_graph(graph,static_report):
 for record in graph.records:
  if 'bounds'in record:
   b=record['bounds'];require(b['min']<=b['max'] or record['code']in(6,7,14) and record['header']&128 and b['min']==b['max']+1)
 for projection in static_report['selected_native_type_projections'].values():
  for chain in [projection['type']]+[member['type_chain'] for member in projection.get('members',[])]:
   for expected in chain:
    actual=graph.records[expected['id']]
    for key in ('id','offset','bytes','header','kind','name','bounds'):
     require(expected.get(key)==actual.get(key))
  root=graph.records[projection['type'][0]['id']]
  if 'members'in projection:
   require([(r['name'],r['tag'],r['type_chain'][0]['id']) for r in projection['members']]==list(zip(root['field_names'],root['tags'],root['field_types'])))
 closure=[{k:v for k,v in r.items() if k!='code'} for r in graph.closure()]
 schema_path=WORK/'native-client-codec-ready/native_clientinfo_schema_98348.json'
 schema_raw=_read(schema_path,128*1024)
 require(sha(schema_raw)=='6e8711939ede15505debb043ae626b5c529749557d7e824226863c92e4f6a229')
 schema=json.loads(schema_raw)
 require(schema['source_PE_sha256']==PE_SHA and schema['source_embedded_bytecode_sha256']==BLOB_SHA)
 require(schema['records']==closure and schema['selected_type_count']==104)
 return sha(json.dumps(closure,sort_keys=True,separators=(',',':')).encode()),sha(schema_raw)

def analyze():
 pin_files();producer=json.loads(_read(RESEARCH/'native-ClientInfo-current-21case-binding.json',128*1024))
 static=json.loads(_read(RESEARCH/'native-BSN-metadata-98348-v2.json',128*1024))
 blob,PEread=load(Path(r'C:\Program Files (x86)\Heroes of the Storm\Versions\Base98348\HeroesOfTheStorm_x64.exe'))
 graph=Graph(blob);closure_sha,schema_sha=check_graph(graph,static)
 budget=cohort.Budget();specs,guards,_=cohort.load_specs(budget)
 require(len(specs)==21 and sha(_read(Path(cohort.__file__),1024*1024))=='2f020152115324ef7e309807a9d988bc65b62eb8dcf6e8077988b29cdd2dd9ca')
 identity=load_protocol(96477);require(identity.recovery_schema_sha256==cohort.previous.SCHEMA_CURRENT)
 hist=Counter();first_bits=Counter();choices=Counter();permission_counts=Counter();cases=[];mutation=None
 for spec,claimed in zip(specs,producer['results']):
  require(spec['id']==claimed['id'] and spec['sha']==claimed['replay_sha256'])
  require(sha(budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))==spec['sha'])
  cohort.profile_checked(spec['profile'],spec['profile_sha'],spec['sha'],budget)
  archive=cohort.CountedArchive(spec['path'],budget)
  try:
   header=identity.decode_replay_header(archive.header['user_data_header']['content'])
   require(header['m_version']['m_build']==header['m_version']['m_baseBuild']==header['m_dataBuildNum']==98348)
   require(header['m_ngdpRootKey']['m_data'].hex()==cohort.ROOT)
   raw=cohort.previous.bounded_member(archive,'replay.server.battlelobby')
   require(sha(raw)==claimed['member_sha256'])
   mods=audit_member(raw,'observed-11','current-observed');tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
   details=identity.decode_replay_details(cohort.previous.bounded_member(archive,'replay.details'))
   initial=identity.decode_replay_initdata(cohort.previous.bounded_member(archive,'replay.initData'))
   checks=crosscheck(tail,details,initial)
   require(checks['all_details_participants_match_tail_by_slot'] and checks['initdata_identity_multiset_equal'])
   require(checks['initdata_identity_and_slot_matches']==len(tail.players) and checks['seed_matches_lobby'] and checks['seed_matches_game_description'])
   require(checks['disabled_hero_list_equal'] is not False)
   at=positions(tail);require(len(tail.players)==claimed['players'])
   for index,player in enumerate(tail.players):
    path='/players/'+str(index);start=at[path+'/unknown32']
    expected_end=at['/players/'+str(index+1)+'/unknown32'] if index+1<len(tail.players) else tail.report['boundaries_bits']['players_end']
    wire=Wire(graph,raw,start);decoded=wire.decode()
    require(wire.pos==expected_end and wire.exact_reencode())
    require(set(decoded)==set(graph.records[1768]['field_names']) and len(decoded)==18)
    require(all(wire.event(native).start==at[path+old] for native,old in ANCHORS.items()))
    toon=decoded['m_toonHandle']
    require(decoded['m_playerScope']==player.slot)
    require((toon['m_region'],toon['m_programId'].to_bytes(4,'big'),toon['m_realm'],toon['m_id'])==(player.toon.region,player.toon.program,player.toon.realm,player.toon.identifier))
    net=wire.event('/m_talkerNetworkId');voice=wire.event('/m_voiceSessionId');profile=wire.event('/m_profileAddress');permission=wire.event('/m_relevantPermissions')
    require(net.end==voice.start and voice.end==profile.start and profile.end==permission.start and permission.end==wire.event('/m_rating').start)
    widths=(net.end-net.start,voice.end-voice.start,profile.end-profile.start,permission.end-permission.start)
    require(widths==(8,64,96,31) and permission.end-net.start==199)
    opaque=at[path+'/unknown_player_block/0'];require(opaque==net.start+1 and permission.end-opaque==198)
    first=(raw[net.start//8]>>(net.start%8))&1
    hist[widths]+=1;first_bits[first]+=1;choices[wire.event('/m_talkerInfo/m_id/m_id',6).value[0]]+=1
    permission_counts[len(decoded['m_relevantPermissions'])]+=1
    if mutation is None:
     require(first==0);changed=bytearray(raw);changed[net.start//8]^=1<<(net.start%8);changed=bytes(changed)
     check=Wire(graph,changed,start);check.decode()
     require(check.pos==expected_end and check.exact_reencode() and 0<=check.event('/m_talkerNetworkId').value<=255)
     require(sum((a^b).bit_count() for a,b in zip(raw,changed))==1)
     failed=False
     try:decode_tail(changed,mods['terminal_handles_end_bit'],'current-tail')
     except ValueError:failed=True
     require(failed and sha(changed)==producer['single_bit_RAM_network_branch_negative_control']['RAM_mutated_member_sha256'])
     mutation={'exactly_one_first_network_wire_bit_flipped_in_RAM':True,'independent_native_boundary_and_reencoding_still_exact':True,
               'old_observed_tail_rejects':True,'same_mutation_as_frozen_producer_verified_privately':True,'body_saved':False,
               'synthetic_control_is_not_an_authentic_replay':True}
   cases.append({'id':spec['id'],'replay_sha256':spec['sha'],'records':len(tail.players),
                 'all18_native_fields_13_anchors_private_identity_boundaries_and_reencoding_exact':True})
  finally:archive.close()
  require(sha(budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))==spec['sha'])
 for _,path,digest,_ in guards:require(sha(budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))==digest)
 require(sum(hist.values())==producer['current_player_records']==222 and len(cases)==producer['current_cases']==21)
 require(dict(Counter(str(k) for k,v in first_bits.items() for _ in range(v)))==producer['aggregate']['first_network_field_bit_histogram'])
 require({str(k):v for k,v in choices.items()}==producer['aggregate']['TalkerId_choice_histogram'])
 require({str(k):v for k,v in permission_counts.items()}==producer['aggregate']['relevant_permission_count_histogram'])
 require(list(hist.items())==[((8,64,96,31),222)])
 pin_files()
 sources=[{'file':p.name,'sha256':sha(_read(p,128*1024))} for p in sorted(Path(__file__).parent.glob('*.py'))]
 return {'format':'hots-native-ClientInfo-independent-graph-wire-review-v1','review_sources':sources,'reviewed_producer_pins':PINS,
  'source_PE_SHA256':PE_SHA,'embedded_BSN_SHA256':BLOB_SHA,'independently_validated_native_type_records':8330,
  'independent_reachable_ClientInfo_graph_types':104,'static_closure_canonical_JSON_SHA256':closure_sha,
  'portable_schema_SHA256':schema_sha,'portable104_type_graph_equals_independent_raw_BSN_projection':True,
  'producer_decoder_or_metadata_parser_executed_by_reviewer':False,
  'cases':cases,'actual_cases':21,'actual_ClientInfo_records':222,
  'all_records_18_native_fields_13_baseline_anchors_private_Toon_and_end_boundaries_exact':True,
  'independent_operation_encoder_reproduces_every_consumed_ClientInfo_bit':True,
  'native_named_segment_widths_bits':[8,64,96,31],'named_segment_total_bits':199,
  'prior_secondary_marker_consumes_first_native_network_bit_then_skips_remaining198':True,
  'all_observed_TalkerId_choices_invalid_and_permission_arrays_empty':choices==Counter({0:222}) and permission_counts==Counter({0:222}),
  'all_observed_first_network_bits_zero':first_bits==Counter({0:222}),
  'one_bit_RAM_negative_control':mutation,
  'PE_stream_bytes_hashed':PEread,'replay_and_metadata_budget_counts':dict(budget.counts),
  'replay_and_metadata_budget_bytes':sum(budget.counts.values()),'all_reference_replay_hashes_unchanged':True,
  'raw_player_network_profile_permission_or_identity_values_emitted':False,
  'network_requests':0,'game_client_or_target_code_loaded_or_executed':False,'replay_or_member_written':False,
  'material_findings_in_actual_current_scope':[],
  'limits':['The independent reader implements the same native format grammar with separate metadata and wire code; agreement is limited to the hash-pinned actual PE and current replay controls.',
            'Current199-bit named segment is established; no174-bit historical layout or cross-version value transformation is established.',
            'The old profile names a network bit as a secondary-name marker. Observed zero first bits explain its successful current fixtures; the synthetic alternative demonstrates narrower profile coverage.',
            'All actual TalkerId branches are invalid0 and permission arrays empty; authentic other branches are not claimed.',
            'These are structural and private identity/boundary checks, not player ownership semantics, complete native runtime equivalence or playback proof.']}

if __name__=='__main__':
 result=analyze();out=Path(__file__).with_name('native-ClientInfo-independent-review.json');write_new_report(result,out)
 print(json.dumps({'actual_cases':21,'actual_records':222,'independent_graph_types':104,'report_SHA256':sha(_read(out,128*1024))}))
