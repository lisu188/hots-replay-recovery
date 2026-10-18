"""Private RAM-only observed header attribute projection controls."""
import copy,dataclasses,hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;WORK=BASE.parent;EU=WORK/'eu-replay-search-20261018';REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO),str(BASE),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from battlelobby_header_attributes import project,localization_indices,localize_package
from project_attribute_nodes import project_nodes
from lossless_wire import parse,encode,to_generic,WireError
from reference_replay import checked_archive
from battlelobby_attribute_layer import LayerError,decode_layer,encode_layer,Token
cache=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache');sha=lambda b:hashlib.sha256(b).hexdigest()
replay=EU/'heroeslounge-27515-g1-20261005.StormReplay'
assert sha(replay.read_bytes())=='a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4'
a=checked_archive(replay)
try:raw=a.read_file('replay.server.battlelobby')
finally:a.close()
projection=project(raw,'observed-11');by_id={tuple(x[0][k] for k in (0,1)):x for x in projection.attributes}
controls=[];core_template=None;core_target=None
for source in json.loads((EU/'four-eu-base-header-acquisition.json').read_bytes())['results'][:3]:
    data=(EU/source['local_file']).read_bytes();assert sha(data)==source['sha256']
    root=parse(data);template=root.field(0).field(5);generic=to_generic(template)
    desired=localize_package([by_id[tuple(x[0][k] for k in (0,1))] for x in generic],source['index'])
    out=project_nodes(template,desired)
    assert to_generic(out)==generic and encode(out)==encode(template) and encode(root)==data
    controls.append({'header_sha256':source['sha256'],'attribute_count':len(generic),'field5_wire_bytes':len(encode(template)),'field5_wire_sha256':sha(encode(template)),'projection_generic_equal':True,'projection_wire_bytes_equal':True,'source_whole_header_unchanged':True})
    if source['index']==0:core_template,core_target=template,desired

negative=[]
def refuses(label,fn,error):
    try:fn()
    except error:negative.append({'case':label,'rejected':True})
    else:raise AssertionError('Negative control was accepted: '+label)
swapped=copy.deepcopy(core_target);swapped[0],swapped[1]=swapped[1],swapped[0]
refuses('swapped_attribute_identities',lambda:project_nodes(core_template,swapped),WireError)
bad=copy.deepcopy(core_target);bad[0][4]=1.25
refuses('floating_point_in_integer_wire_field',lambda:project_nodes(core_template,bad),WireError)
bad=copy.deepcopy(core_target);bad[0][1][0][1][1]={0:None,1:0,2:123}
refuses('new_optional_shape_without_authenticated_template',lambda:project_nodes(core_template,bad),WireError)
refuses('wrong_global_localization_table_index',lambda:localize_package(core_target,1),LayerError)
layer=decode_layer(raw,'observed-11');changed=[];did=False
for t in layer.tokens:
    if not did and t.path.endswith('/values/0/flags'):
        t=dataclasses.replace(t,value=1);did=True
    changed.append(t)
assert did
invalid=encode_layer(dataclasses.replace(layer,tokens=tuple(changed)),'observed-11')
refuses('unsupported_nonempty_value_requirement_bits',lambda:project(invalid,'observed-11'),LayerError)

h='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9';data=(cache/h[:2]/h[2:4]/(h+'.s2mh')).read_bytes();assert sha(data)==h
root=parse(data);template=root.field(0).field(5);old=to_generic(template)
desired=localize_package([by_id[tuple(x[0][k] for k in (0,1))] for x in old],3)
target=project_nodes(template,desired)
assert encode(root)==data
assert len(desired)==14 and sum(len(x[1]) for x in desired)==5165
old_names={v[0] for item in old for v in item[1]}
new_names={v[0] for item in desired for v in item[1]}
assert len(new_names-old_names)==9 and not old_names-new_names
report={'format':'hots-observed-attribute-wire-projection-controls-v1','source_replay_sha256':sha(replay.read_bytes()),'source_member_sha256':sha(raw),'authenticated_controls':controls,'total_authenticated_definitions':sum(x['attribute_count'] for x in controls),'all_authenticated_field5_subtrees_wire_exact':True,'negative_controls':negative,'current_heroesdata_projection':{'source_template_header_sha256':h,'attribute_count':len(desired),'value_count':5165,'new_fourcc_values_vs_template':9,'removed_fourcc_values_vs_template':0,'maximum_localization_index':max(localization_indices(desired)),'field5_wire_bytes':len(encode(target)),'field5_wire_sha256':sha(encode(target)),'all_generic_target_fields_equal_observed_replay_projection':True,'all_wire_tags_taken_from_compatible_authenticated_templates':True,'source_template_whole_header_unchanged':True,'is_accepted_current_header':False},'conditional_field7_hypothesis':{'historical65661_max_attr_index':5099,'historical65661_score_index_range':[5100,5198],'historical65662_max_attr_index':5113,'historical65662_score_index_range':[5114,5212],'current_observed_max_attr_index':5122,'candidate_current_field7_range_if_same_rule':[5123,5221],'candidate_delta_from65662':9,'current_exact_localization_entries_available':False,'hypothesis_verified_by_target_full_SHA256':False},'source_helpers':[{'file':p.name,'sha256':sha(p.read_bytes())} for p in (BASE/'battlelobby_header_attributes.py',BASE/'project_attribute_nodes.py',Path(__file__),BASE/'lossless_wire.py')],'header_assembled_or_written':False,'no_target_or_playback_acceptance_claim':True,'network_used':False,'client_launched':False,'raw_player_fields_emitted':False}
out=BASE/'attribute-wire-projection-controls.json'
with out.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'report':out.name,'sha256':sha(out.read_bytes()),'authenticated_definitions':report['total_authenticated_definitions'],'negative_controls':len(negative),'current_projection':report['current_heroesdata_projection']},indent=2))
