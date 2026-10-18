"""Authorized two-candidate RAM experiment; save ONLY on advertised full SHA match.

Unchanged65662 fields, +9 field7 shift and singleton registry merge are hypotheses
until the entire artifact matches the exact handle in the genuine EU replay.
No replay, client, network or mismatching candidate file operation is provided.
"""
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;WORK=BASE.parent;EU=WORK/'eu-replay-search-20261018';REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO),str(BASE),str(WORK/'collection-registry-ready'),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from lossless_wire import parse,clone,encode,to_generic
from depot_s2mh_wire import decode_verified_header
from battlelobby_header_attributes import project,localization_indices,localize_package
from project_attribute_nodes import project_nodes
from experimental_registry_merge import load_actual_inputs,iter_candidate_vectors,position_candidates
from battlelobby_attribute_layer import decode_layer,_read
from battlelobby_tail import decode_tail
from reference_replay import checked_archive

TARGET='f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0'
BASE_SHA='f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9'
PRIOR='29f66c9eca1844826ad55f63eb8fd32a2d6e74ddb7931a8e835fb951f58e184d'
REPLAY_SHA='a3c97e9a669e73e4c2b19a8f6c5e2de0315cbc5725be82cf1e887ed6319a01c4'
PINNED={'lossless_wire.py':'9d725f9be88c4185419a306ef995e82a774d174a93912ffd381cced2d6ebb7a7','battlelobby_header_attributes.py':'ce10b4ee3eeaacc1e6431f13291851e1f2fc2e8a8e3b3da5301a414d9749a868','project_attribute_nodes.py':'73b3d94269a12c117613edb25f3fa590c2af8947b2de9f11bc7baf4e4133f677','../collection-registry-ready/experimental_registry_merge.py':'f2d8fd373991fd7e03264f03379e29121b2e14bbbe01e01bde5e37cb2b108bfd'}
sha=lambda raw:hashlib.sha256(raw).hexdigest()
for name,expected in PINNED.items():
    if sha((BASE/name).read_bytes())!=expected:raise ValueError('Frozen helper source differs')
cache=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
def cached(h):
    data=_read(cache/h[:2]/h[2:4]/(h+'.s2mh'))
    if sha(data)!=h:raise ValueError('Source header digest differs')
    return data
base_raw,prior_raw=cached(BASE_SHA),cached(PRIOR)
source=parse(base_raw);prior=parse(prior_raw)
assert encode(source)==base_raw and encode(prior)==prior_raw
base_values,current_values,prior_values=load_actual_inputs()
assert to_generic(source.field(0).field(24))==base_values
assert to_generic(prior.field(0).field(24))==prior_values
position_metadata=position_candidates(base_values,current_values,prior_values,cap=2)
assert position_metadata['position_tuple_count']==2

replay=EU/'heroeslounge-27515-g1-20261005.StormReplay'
assert sha(_read(replay))==REPLAY_SHA
binding_path=EU/'one-eu-current-reference-binding.json';binding=json.loads(_read(binding_path))
assert binding['file_sha256']==REPLAY_SHA and binding['data_build']==98348 and binding['details_player_region_set']==[2]
assert binding['mod_package_bindings'][3]['terminal_s2mh_handle']['digest']==TARGET
assert binding['mod_package_bindings'][3]['mod_id']==169992 and binding['mod_package_bindings'][3]['version']==65663
a=checked_archive(replay)
try:raw=a.read_file('replay.server.battlelobby')
finally:a.close()
layer=decode_layer(raw,'observed-11');tokens={x.path:x.value for x in layer.tokens}
tail=decode_tail(raw,binding['mod_metadata']['terminal_handles_end_bit'],'current-tail')
eu_registry=[int.from_bytes(x.value,'big') for x in tail.tokens if x.path.startswith('/collections/') and x.path.endswith('/value')]
assert eu_registry==current_values and len(eu_registry)==5418
projection=project(raw,'observed-11');by_id={tuple(x[0][k] for k in (0,1)):x for x in projection.attributes}
old_attributes=to_generic(source.field(0).field(5))
target_attributes=localize_package([by_id[tuple(x[0][k] for k in (0,1))] for x in old_attributes],3)
assert len(target_attributes)==14 and max(localization_indices(target_attributes))==5122
target_attribute_node=project_nodes(source.field(0).field(5),target_attributes)

locale_by_name={tokens[f'/locales/{i}/fourcc'].to_bytes(4,'big'):tokens[f'/locales/{i}/handles/3'] for i in range(tokens['/locales/count'])}
assert len(locale_by_name)==12 and all(len(v)==40 and v[:4]==b's2ml' and v[4:8].strip(b'\0')==b'EU' for v in locale_by_name.values())
new_ids=position_metadata['new_ids_in_current_order']
prior_nodes={}
for n in prior.field(0).field(24).value:
    if n.value in new_ids:
        if n.value in prior_nodes:raise ValueError('Prior singleton is not unique')
        prior_nodes[n.value]=n
assert set(prior_nodes)==set(new_ids)

results=[];accepted=[]
for number,(gaps,registry) in enumerate(iter_candidate_vectors(base_values,current_values,prior_values,cap=2),1):
    candidate=clone(source);header=candidate.field(0)
    version=header.field(0).field(1)
    assert version.value==65662;version.value=65663
    header.set_field(5,clone(target_attribute_node))
    locale_paths=[]
    for array_path,array in [('root/0/4/8',header.field(4).field(8)),('root/0/8',header.field(8))]:
        assert len(array.value)==12
        for i,node in enumerate(array.value):
            name=node.field(0).value;handles=node.field(1)
            assert name in locale_by_name and handles.tag==0 and len(handles.value)==1
            item=handles.value[0]
            assert item.tag==2 and len(item.value)==40
            item.value=locale_by_name[name];locale_paths.append(f'{array_path}/{i}/1/0')
    score_paths=[];score_old=[]
    for i,record in enumerate(header.field(7).value):
        for k in (0,1):
            key=record.field(2).field(k)
            assert key.tag==4
            if key.value is not None:
                index=key.value.field(2)
                if index.value:
                    score_old.append(index.value);index.value+=9;score_paths.append(f'root/0/7/{i}/2/{k}/2')
    assert sorted(score_old)==list(range(5114,5213)) and len(score_paths)==99
    insertions={}
    for gap,value in zip(gaps,new_ids):insertions.setdefault(gap,[]).append(value)
    source_registry=source.field(0).field(24).value;new_registry=[]
    for gap in range(len(source_registry)+1):
        new_registry.extend(clone(prior_nodes[value]) for value in insertions.get(gap,()))
        if gap<len(source_registry):new_registry.append(clone(source_registry[gap]))
    header.field(24).value=new_registry
    assert tuple(to_generic(header.field(24)))==registry and len(registry)==5497
    data=encode(candidate)
    if not 0<len(data)<=512*1024:raise ValueError('Candidate exceeds header bound')
    actual=sha(data);matched=actual==TARGET
    row={'candidate':number,'registry_original_array_insertion_gaps':list(gaps),'registry_count_hypothesis':len(registry),'bytes':len(data),'sha256':actual,'matches_exact_advertised_target':matched,'mismatching_body_saved_or_emitted':False,'changed_path_groups':['root/0/0/1','root/0/4/8/*/1/0','root/0/5','root/0/7/*/2/{0,1}/2','root/0/8/*/1/0','root/0/24'],'locale_changed_paths':locale_paths,'field7_changed_paths':score_paths,'unmodified_other_source_fields_preserved':True}
    if matched:
        generic=decode_verified_header(data,TARGET)
        assert generic[0][0]=={0:169992,1:65663}
        assert generic[0][5]==target_attributes and generic[0][24]==list(registry)
        assert to_generic(candidate)==generic
        outdir=BASE/'recovered-headers-private';outdir.mkdir(exist_ok=True)
        out=outdir/(TARGET+'.s2mh')
        with out.open('xb') as f:f.write(data)
        assert sha(_read(out))==TARGET
        row.update(independent_depot_decoder_complete_EOF=True,independent_generic_values_equal=True,accepted_private_file='recovered-headers-private/'+out.name)
        accepted.append({'file':row['accepted_private_file'],'sha256':actual,'bytes':len(data),'candidate':number})
    results.append(row)
    print(json.dumps({k:row[k] for k in ('candidate','registry_original_array_insertion_gaps','bytes','sha256','matches_exact_advertised_target')}),flush=True)
    del data,candidate
assert len(results)==2 and len(accepted)<=1
assert encode(source)==base_raw and encode(prior)==prior_raw and sha(_read(replay))==REPLAY_SHA
report={'format':'hots-exact-current-EU-heroesdata-header-RAM-experiment-v1','source_header_sha256':BASE_SHA,'historical_singleton_witness_header_sha256':PRIOR,'genuine_current_EU_replay_sha256':REPLAY_SHA,'binding_report_sha256':sha(_read(binding_path)),'exact_advertised_target_sha256':TARGET,'maximum_candidates':2,'maximum_candidate_header_bytes':512*1024,'accepted_only_if_full_advertised_SHA_matches':True,'experiments':['Version65663and12localehandlesobserved in currentEUreplay.','14completeattribute definitions projected fromcurrentEUreplay and controlled73authenticateddefinitions.','Field7+9shift is an explicitly experimental continuation of the observed final99indices rule.','Registry preservesall5488sourcepositions/multiplicities and inserts9historicallywitnessedsingletons; bothadmissibleorders tried.','Everyother65662field andwiretype preserved.'],'results':results,'accepted':accepted,'actual_exact_target_header_recovered':bool(accepted),'source_inputs_unchanged':True,'source_helpers':[{'file':name,'sha256':expected} for name,expected in PINNED.items()]+[{'file':Path(__file__).name,'sha256':sha(Path(__file__).read_bytes())}],'raw_header_bodies_publication':False,'player_values_emitted':False,'replay_modified':False,'client_launched':False,'network_used':False,'playback_or_simulation_proven':False,'acceptance_limit':'A successful fullSHA recovers the exact static object advertised by this EU replay; it does not prove replay conversion, account semantics or deterministic playback.'}
out=BASE/'exact-current-eu-heroesdata-reconstruction-experiment.json'
with out.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'report':out.name,'sha256':sha(out.read_bytes()),'accepted':accepted},indent=2))
