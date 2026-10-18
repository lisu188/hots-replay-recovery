"""Formal namespace carrier audit; numeric namespaces/offsets never leave RAM."""
from __future__ import annotations
from dataclasses import dataclass,field
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;WORK=HERE.parent;REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
GRAPH_SHA='2db88802fec04e587e7203c32ab16d25578e56a6f377e04f5d933938f0246baf'
REPLAY_SHA='882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'
MISSING='42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a'
EU_DATA='33a1c5c9cd0e3d808c2a942c392fa2b5cc7077457bdbe62adad158b86ef8a4fd'
US_HASHES=(('US-Core','3392997d3afe27a33371b58cfaff37af5b67bda09ee9131e52bae0a0c80b2b76'),
 ('US-Teams10','82cf19ac9ceb903631db0994023efba040a1ccfbb0e920033a742d62cb65a77b'),
 ('US-Heroes','4b6fdc8eccc9eca107f7c6e5eae6c7c604e718ded019f4f4110a92300b54313f'),
 ('US-HeroesData','0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a'),
 ('US-Dragon','3c2d7d5c17b8a5351c03d7bfb40159ca158694176b81d51bbd1d12abadc2e429'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def require(value,message='Bounded formal namespace audit failed'):
    if not value:raise ValueError(message)

@dataclass(frozen=True,repr=False)
class Carrier:
    path:tuple=field(repr=False)
    value:int=field(repr=False)
    through_definition_handle:bool=field(repr=False)

def namespace_carriers(graph,root_type,value):
    """Walk ONLY namespace-relevant native type edges in decoded versioned data."""
    nodes={r['id']:r for r in graph};out=[];count=0
    def walk(i,v,path,depth,via_handle):
        nonlocal count
        count+=1;require(count<=200000 and depth<=64,'carrier traversal bound')
        if i==145:
            require(type(v)is int and 0<=v<1<<32,'formal namespace exceeds native u32')
            out.append(Carrier(path,v,via_handle));return
        require(i in nodes,'missing selected type')
        r=nodes[i];kind=r['kind'];via_handle=via_handle or i==159
        if kind=='USER':walk(r['element_type'],v,path,depth+1,via_handle)
        elif kind=='OPTIONAL':
            if v is not None:walk(r['element_type'],v,path,depth+1,via_handle)
        elif kind=='ARRAY':
            require(type(v)is list,'native array wire shape')
            if 'bounds'in r:require(r['bounds']['min']<=len(v)<=r['bounds']['max'],'native array count')
            for index,item in enumerate(v):walk(r['element_type'],item,path+(index,),depth+1,via_handle)
        elif kind=='STRUCT':
            require(type(v)is dict,'native struct wire shape')
            for m in r.get('members',[]):
                if m['tag']in v:walk(m['type_id'],v[m['tag']],path+(m['name'],),depth+1,via_handle)
        elif kind=='CHOICE':
            require(hasattr(v,'tag')and hasattr(v,'value'),'native choice wire shape')
            matches=[m for m in r.get('members',[])if m['tag']==v.tag]
            require(len(matches)<=1)
            if matches:walk(matches[0]['type_id'],v.value,path+(matches[0]['name'],),depth+1,via_handle)
        else:raise ValueError('Unexpected leaf on namespace path')
    walk(root_type,value,(),0,False)
    return out

def analyze():
    sys.path[:0]=[str(REPO),str(WORK/'header-reconstruction'),str(WORK/'mod-metadata-publish-ready'),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
    from regional_header_controls import extract_context
    from depot_s2mh_wire import decode_verified_header
    from reference_replay import checked_archive
    from battlelobby_attribute_layer import decode_layer
    from audit_battlelobby_mod_metadata import audit_member
    from battlelobby_header_attributes import project
    graph_raw=(HERE/'native-formal-namespace-selected-graph.json').read_bytes();require(sha(graph_raw)==GRAPH_SHA)
    graph=json.loads(graph_raw);require(graph['map_info_list_reaches_formal_namespace']is False)
    ns_nodes=graph['namespace_ancestor_graph']
    replay=WORK/'reference-donors/ngs-20261016-protectors-dragon.StormReplay'
    context=extract_context(replay,REPLAY_SHA,'US')
    archive=checked_archive(replay)
    try:raw=archive.read_file('replay.server.battlelobby')
    finally:archive.close()
    layer=decode_layer(raw,'observed-11');mods=audit_member(raw,'observed-11','current-observed')
    projection=project(raw,'observed-11')
    require(sha(raw)==context.member_sha256,'context member differs')
    # Explicit observed pair fields only. No scalar/haystack scan is performed.
    observed=[t.value for t in layer.tokens if t.path.endswith('/namespace')]
    definition_pairs={(a.namespace,a.identifier)for a in layer.attributes}
    require(len(definition_pairs)==len(layer.attributes))
    headers=[];guards=[];header_bytes=0;known_definition_pairs=set()
    for index,(role,expected)in enumerate(US_HASHES):
        folder=WORK/'independent-parser/s2mh-headers'if index<3 else WORK/'header-reconstruction/recovered-headers-private'
        path=folder/(expected+'.s2mh');data=path.read_bytes();header_bytes+=len(data)
        require(len(data)<=512*1024 and sha(data)==expected)
        header=decode_verified_header(data,expected)[0];guards.append((path,expected))
        require(header[2][:8]==b's2ma\0\0US')
        matches=[i for i,e in enumerate(context.entries)if e['identity']==(header[0][0],header[0][1])]
        require(len(matches)==1);module_index=matches[0]
        require(context.prefix[module_index]==header[2] and context.terminal[module_index][8:].hex()==expected)
        require(type(header[3])is int and 0<=header[3]<1<<32)
        carriers=namespace_carriers(ns_nodes,4448,header)
        direct=[c for c in carriers if c.path==('m_mapNamespace',)]
        require(len(direct)==1 and direct[0].value==header[3])
        handles=[c for c in carriers if c.through_definition_handle]
        pairs=[(item[0][0],item[0][1])for item in header[5]]
        require(all(pair in definition_pairs for pair in pairs),'header definition pair missing from observed prefix')
        known_definition_pairs.update(pairs)
        headers.append({'role':role,'header_sha256':expected,'bytes':len(data),'full_header_digest_and_actual_US_package_binding_passed':True,
            'native_named_namespace_carriers':len(carriers),'native_DefinitionHandle_namespace_carriers':len(handles),
            'mapNamespace_is_native_tag3_u32':True,'mapNamespace_equal_to_any_observed_prefix_handle_namespace':header[3]in observed,
            'header_definitions':len(header[5]),'all_header_definition_pairs_present_in_observed_prefix':True,
            'definitionHandle_carriers_equal_own_mapNamespace':sum(c.value==header[3]for c in handles)})
    cache=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache');eu_path=cache/EU_DATA[:2]/EU_DATA[2:4]/(EU_DATA+'.s2mh')
    eu_raw=eu_path.read_bytes();require(len(eu_raw)==1660 and sha(eu_raw)==EU_DATA);header_bytes+=len(eu_raw);guards.append((eu_path,EU_DATA))
    eu=decode_verified_header(eu_raw,EU_DATA)[0]
    require(eu[0]=={0:196228,1:16}and eu[2][:8]==b's2ma\0\0EU'and not eu[5]and eu[19]is None)
    target=[i for i,value in enumerate(context.prefix)if value[8:]==eu[2][8:]];require(len(target)==1);target=target[0]
    require(context.entries[target]['identity']==(280539,16)and context.terminal[target][8:].hex()==MISSING and not mods['entries'][target]['has_static_arcade_info'])
    eu_carriers=namespace_carriers(ns_nodes,4448,eu)
    eu_handles=[c for c in eu_carriers if c.through_definition_handle]
    # Do not assign a package from a coincident scalar or localization index.
    # Compare only explicit namespace/id pairs against actual known definitions.
    unmatched_pairs=definition_pairs-known_definition_pairs
    for path,expected in guards:require(sha(path.read_bytes())==expected,'header changed')
    require(sha(replay.read_bytes())==REPLAY_SHA,'replay changed')
    runtime={name:sha(Path(sys.modules[name].__file__).read_bytes())for name in('regional_header_controls','depot_s2mh_wire','battlelobby_attribute_layer','audit_battlelobby_mod_metadata','battlelobby_header_attributes')}
    return {'format':'hots-native-formal-namespace-exposure-assessment-v1','producer_sha256':sha(Path(__file__).read_bytes()),
        'native_graph_sha256':GRAPH_SHA,'source_PE_sha256':graph['PE_sha256'],'source_embedded_blob_sha256':graph['embedded_blob_sha256'],
        'runtime_source_sha256s':runtime,'actual_US_replay_sha256':REPLAY_SHA,'actual_member_sha256':context.member_sha256,
        'actual_build_base_data':98348,'actual_root':'c3b3c8bc82e3a5a62e550fdde9a40c28','explicit_US_participant_region_guard_passed':True,
        'known_exact_US_header_positive_controls':headers,'known_header_bytes_per_pass':header_bytes,'known_headers_guard_passes':2,
        'observed_prefix':{'definition_count':len(layer.attributes),'selected_handle_count':len(layer.selections),
            'namespace_pair_field_occurrences_checked':len(observed),'distinct_namespace_values_count':len(set(observed)),
            'unique_definition_pairs_in_five_exact_headers':len(known_definition_pairs),
            'definition_pairs_not_in_five_exact_headers':len(unmatched_pairs),
            'DefinitionList_count_width':9,'native_DefinitionList_count_width':9,'observed_profile_index_width':11,
            'whole_native_prefix_decoder_applied':False,'raw_4byte_haystack_search_performed':False},
        'DataMod':{'source_EU_header_sha256':EU_DATA,'actual_missing_US_header_sha256':MISSING,'source_and_target_package_identity_archive_payload_binding_passed':True,
            'source_EU_attribute_definitions':len(eu[5]),'actual_US_definition_rows_attributed_to_DataMod':None,
            'actual_US_definition_package_ownership_independently_established':False,
            'source_EU_native_namespace_carriers':len(eu_carriers),'source_EU_native_DefinitionHandle_namespace_carriers':len(eu_handles),
            'source_and_target_static_arcade_absent':True,'native_S2MapInfo_subtree_has_formal_namespace_path':False,
            'actual_US_DataMod_namespace_directly_bound':False},
        'conclusion':'No formally attributed US DataMod namespace is exposed by the checked named carriers; root/0/3 remains an unobserved target value.',
        'namespace_account_creator_values_digests_or_additive_offsets_emitted':False,'candidate_header_created_or_scalar_chosen':False,
        'game_network_repo_or_cloud_used':False,'all_input_header_and_replay_digests_unchanged':True,
        'limits':['MapInfo graph has no path to named NameSpace145. Root independently reviews its complete actual replay binding.',
            'DefinitionHandle native u32/u32 fields are compared only through explicit observed prefix pairs and known header positive controls.',
            'DefinitionList count9 matches the prefix; observed-11 denotes index width11. This does not authorize unchanged whole-prefix native decoding.',
            'A numeric coincidence in unrelated u32 fields would not establish a DataMod namespace. No such scan, brute force or candidate assembly is done.',
            'The EU source namespace is not transferred to the US target, and no module offset is selected or inferred.']}

if __name__=='__main__':
    out=HERE/'native-formal-namespace-exposure-assessment.json';require(not out.exists())
    data=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode();require(len(data)<=64*1024)
    with out.open('xb')as f:f.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
