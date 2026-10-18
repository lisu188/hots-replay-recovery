"""Formal named-field exposure comparisons; no candidate is built or saved.

Author, namespace, creator and player values are private RAM objects only.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import os
import stat
import sys

HERE=Path(__file__).resolve().parent;WORK=HERE.parent
REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
GRAPH_SHA='56fa4fedd97e63737c2c575e63c728d9389d015243ff6acd25020c4d62834147'
NATIVE_SHA='14cd9d119b4b26a5b479f410412377e2c93c7fab6c813bc5df42e74e0e2772d9'
US_REPLAY_SHA='882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'
US_MEMBER_SHA='ab03d9533081e9d69d205a6adec9df6a0aaf5ff47a05ecc8bf670b6760b0ab55'
EU_DATAMOD='33a1c5c9cd0e3d808c2a942c392fa2b5cc7077457bdbe62adad158b86ef8a4fd'
TARGET='42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a'
SCHEMA='e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
MAPINFO_SCHEMA='3900a63c0799474becd2ecfb03eece4f8c523a965b38e539264867d5cdf2075c'
MAPINFO_PROOF='2188684e79939cdd2c08929de0e9ca798def21b7865d65d1567abd6591713154'
ROOT='c3b3c8bc82e3a5a62e550fdde9a40c28'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def require(value,message='Formal header field-exposure guard differs'):
    if not value:raise ValueError(message)

def read(path,limit=512*1024):
    require(not path.is_symlink())
    with path.open('rb') as stream:
        a=os.fstat(stream.fileno());require(stat.S_ISREG(a.st_mode) and 0<a.st_size<=limit)
        raw=stream.read(limit+1);b=os.fstat(stream.fileno())
    require(len(raw)==a.st_size and (a.st_size,a.st_mtime_ns)==(b.st_size,b.st_mtime_ns))
    return raw

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

class NamedVersioned:
    """Strict actual versioned nodes named solely by authenticated native tags."""
    def __init__(self,records):self.records=records;self.nodes=0
    def bind(self,node,index,path='',depth=0):
        self.nodes+=1;require(self.nodes<=200000 and depth<=64)
        record=self.records[index];kind=record['kind'];bounds=record.get('bounds')
        child=lambda n,i,p:self.bind(n,i,p,depth+1)
        def tag(expected):require(node.tag==expected,'Versioned wire tag differs at '+path)
        if kind=='USER':return child(node,record['element_type'],path)
        if kind=='STRUCT':
            tag(5);actual=dict(node.value)
            require(len(actual)==len(node.value) and set(actual)==set(record['tags']),'Versioned struct fields differ at '+path)
            return {name:child(actual[key],i,path+'/'+name) for name,i,key in zip(record['field_names'],record['field_types'],record['tags'])}
        if kind=='OPTIONAL':
            tag(4);return None if node.value is None else child(node.value,record['element_type'],path+'/value')
        if kind=='ARRAY':
            tag(0);require(bounds['min']<=len(node.value)<=min(bounds['max'],65535))
            return [child(n,record['element_type'],path+'/'+str(j)) for j,n in enumerate(node.value)]
        if kind=='CHOICE':
            tag(3);choice,value=node.value;require(choice in record['tags'])
            at=record['tags'].index(choice)
            return choice,child(value,record['field_types'][at],path+'/'+record['field_names'][at])
        if kind in ('ASCII_STRING','STRING','BLOB'):
            tag(2);value=node.value;require(type(value) is bytes)
            if kind=='STRING':require(bounds['min']<=len(value.decode('utf-8'))<=bounds['max'])
            else:
                require(bounds['min']<=len(value)<=bounds['max'])
                if kind=='ASCII_STRING':value.decode('ascii')
            return value
        if kind in ('INT','ENUM'):
            tag(9);require(type(node.value) is int and bounds['min']<=node.value<=bounds['max'])
            if kind=='ENUM':require(node.value in record['tags'])
            return node.value
        if kind=='BOOL':
            tag(6);require(node.value in (0,1));return node.value
        if kind in ('FOURCC','REAL32','REAL64'):
            tag(8 if kind=='REAL64' else 7);return int.from_bytes(node.value,'big')
        if kind=='BIT_ARRAY':
            tag(1);require(bounds['min']<=node.value[0]<=bounds['max']);return node.value
        raise ValueError('Unsupported versioned native kind at '+path)

def native_value(decoder,records,index,path='',depth=0):
    require(depth<=64)
    r=records[index];kind=r['kind']
    if kind=='USER':return native_value(decoder,records,r['element_type'],path,depth+1)
    field=decoder.field(path,kind)
    if kind=='STRUCT':return {name:native_value(decoder,records,i,path+'/'+name,depth+1) for name,i in zip(r['field_names'],r['field_types'])}
    if kind=='ARRAY':return [native_value(decoder,records,r['element_type'],path+'/'+str(j),depth+1) for j in range(field.value)]
    if kind=='OPTIONAL':return None if not field.value else native_value(decoder,records,r['element_type'],path+'/value',depth+1)
    if kind=='CHOICE':
        at=r['tags'].index(field.value)
        return field.value,native_value(decoder,records,r['field_types'][at],path+'/'+r['field_names'][at],depth+1)
    require(kind!='BIT_ARRAY','Bit-array value is not projected by this comparison')
    return field.value

def locale_map(locales,global_locales):
    local={r['m_locale']:r['m_stringFileTable'] for r in locales}
    require(len(local)==len(locales)==12 and set(local)==set(global_locales))
    count={len(v) for v in local.values()};require(len(count)==1)
    result={}
    for local_index in range(next(iter(count))):
        matches=[global_index for global_index in range(6) if all(local[name][local_index]==global_locales[name][global_index] for name in local)]
        require(len(matches)==1,'Locale column binding is not unique')
        result[matches[0]]=local_index
    return result

def equivalent_localized(header,metadata,rebase):
    """Exact values first; different file indices require all12 locale handles."""
    if header==metadata:return True,0
    if type(header) is not type(metadata):return False,0
    if type(header) is dict:
        if set(header)!=set(metadata):return False,0
        if set(header)=={'m_colorHint','m_fileIndex','m_id'}:
            if header['m_colorHint']!=metadata['m_colorHint'] or header['m_id']!=metadata['m_id']:return False,0
            return rebase.get(metadata['m_fileIndex'])==header['m_fileIndex'],1
        answers=[equivalent_localized(header[k],metadata[k],rebase) for k in header]
    elif type(header) in (list,tuple):
        if len(header)!=len(metadata):return False,0
        answers=[equivalent_localized(a,b,rebase) for a,b in zip(header,metadata)]
    else:return False,0
    return all(a for a,_ in answers),sum(n for _,n in answers)

def value_at(data,path):
    for key in path:data=data[key]
    return data

def resolve(records,index):
    seen=set()
    while records[index]['kind']=='USER':
        require(index not in seen);seen.add(index);index=records[index]['element_type']
    return records[index]

def wire_path(records,names):
    current=4376;path=['root']
    for name in names:
        r=resolve(records,current);require(r['kind']=='STRUCT' and name in r['field_names'])
        index=r['field_names'].index(name);path.append(str(r['tags'][index]));current=r['field_types'][index]
    return '/'.join(path),current

def compatible_named_types(records,left,right,depth=0):
    require(depth<=64)
    a=resolve(records,left);b=resolve(records,right)
    if a['id']==b['id']:return True
    if a['kind']!=b['kind']:return False
    if a['kind'] in ('ARRAY','OPTIONAL'):
        return compatible_named_types(records,a['element_type'],b['element_type'],depth+1)
    # These scalar records have separate native type IDs per member. This
    # checks compatibility of the already named mapping, never infers a pair.
    return a['kind'] in ('BOOL','FOURCC','REAL32','REAL64')

def field_schema_links(records):
    rows=[];meta=records[5852]
    for label,path,name in DIRECT:
        numeric,left=wire_path(records,('m_bnet',)+path)
        right=meta['field_types'][meta['field_names'].index(name)]
        require(compatible_named_types(records,left,right))
        a=resolve(records,left);b=resolve(records,right)
        rows.append({'field':label,'header_wire_path':numeric,'header_resolved_type_id':a['id'],
                     'header_resolved_type_name':a['name'],'MapInfo_named_field':name,'MapInfo_resolved_type_id':b['id'],
                     'MapInfo_resolved_type_name':b['name'],'named_value_types_compatible':True,
                     'physical_container_type_ids_identical':a['id']==b['id'],
                     'scope':'Shared value/member semantics only; array/optional count or presence prefix widths are validated in their own wire profiles.'})
    return rows

def private_shape(value):
    if type(value) in (list,tuple):return {'kind':'array','elements':len(value)}
    if type(value) is dict:return {'kind':'struct','members':len(value)}
    if value is None:return {'kind':'absent optional'}
    return {'kind':type(value).__name__,'value_emitted':False}

DIRECT=(
    ('header identity',('m_handle',),'m_handle'),
    ('display name',('m_workingSet','m_name'),'m_mapName'),
    ('display description',('m_workingSet','m_description'),'m_mapDescription'),
    ('thumbnail',('m_workingSet','m_thumbnail'),'m_mapThumbnail'),
    ('big map',('m_workingSet','m_bigMap'),'m_bigMap'),
    ('maximum players',('m_workingSet','m_maxPlayers'),'m_maxPlayers'),
    ('visual files',('m_workingSet','m_visualFiles'),'m_visualFiles'),
    ('map size',('m_size',),'m_mapSize'),
    ('tileset',('m_tileset',),'m_tileset'),
    ('labels',('m_labels',),'m_labels'),
    ('default variant index',('m_defaultVariantIndex',),'m_defaultVariantIndex'),
    ('arcade info',('m_arcadeData',),'m_arcadeGameInfo'),
    ('extra dependencies',('m_extraDependencies',),'m_extraDependencies'),
    ('add multiple mods',('m_addMultiMod',),'m_addMultiMod'),
    ('required permissions',('m_requiredPermissions',),'m_requiredPermissions'),
)
VARIANT_FIELDS=('m_variantId','m_categoryName','m_modeName','m_categoryDescription','m_modeDescription','m_visual','m_maxTeamSize','m_maxHumanPlayers','m_maxOpenSlots')

def compare(header,info,rebase):
    result=[]
    for label,path,name in DIRECT:
        ok,n=equivalent_localized(value_at(header,path),info[name],rebase)
        result.append({'field':label,'header_named_path':'Header/m_bnet/'+ '/'.join(path),'MapInfo_field':name,'equal':ok,'locale_indices_rebased_by_12_exact_handles':n})
    variants=[]
    for item in info['m_variants']:
        index=item['m_variantIndex'];require(type(index) is int and 0<=index<len(header['m_variants']))
        require(item['m_mapHandle']==info['m_handle'])
        known=header['m_variants'][index]
        answers={name:equivalent_localized(known[name],item[name],rebase)[0] for name in VARIANT_FIELDS}
        variants.append({'native_variant_index_in_bounds_and_map_handle_matches':True,'nine_common_named_fields_equal':all(answers.values()),'field_equalities':answers})
    return result,variants

def analyze():
    graph_raw=read(HERE/'native-header-mapinfo-selected-graph.json');require(sha(graph_raw)==GRAPH_SHA)
    graph=json.loads(graph_raw);records={r['id']:r for r in graph['records']};protocol=SimpleNamespace(records=records)
    schema_raw=read(WORK/'native-mapinfo-ready/native_mapinfo_schema_98348.json');require(sha(schema_raw)==MAPINFO_SCHEMA)
    selected=json.loads(schema_raw)
    require(len(selected['records'])==selected['selected_type_count']==191 and all(r==records.get(r['id']) for r in selected['records']) and selected['ordered_root_fields']==records[5852]['field_names'])
    proof_raw=read(WORK/'native-mapinfo-ready/native-mapinfo-21case-binding.json');require(sha(proof_raw)==MAPINFO_PROOF)
    proof=json.loads(proof_raw)
    require(proof['schema_sha256']==MAPINFO_SCHEMA and proof['aggregate']['native_MapInfo_records']==136 and proof['current_cases']==21)
    source=WORK/'native-embedded-schema-98348/native_client_layout.py';require(sha(read(source))==NATIVE_SHA)
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
    native=load('_verified_field_exposure_native_decoder',source)
    nodes=load('_verified_field_exposure_wire',WORK/'header-reconstruction/lossless_wire.py')
    from audit_battlelobby_mod_metadata import audit_member
    from battlelobby_attribute_layer import _Reader,decode_layer
    from depot_s2mh_wire import decode_verified_header
    from mod_data_audit import dependency_prefix
    from protocol_loader import load_protocol
    from reference_replay import checked_archive
    replay=WORK/'reference-donors/ngs-20261016-protectors-dragon.StormReplay'
    require(sha(read(replay,3*1024*1024))==US_REPLAY_SHA)
    official=load_protocol(96477);require(official.recovery_schema_sha256==SCHEMA)
    archive=checked_archive(replay)
    try:
        hdr=official.decode_replay_header(archive.header['user_data_header']['content'])
        require(hdr['m_version']['m_build']==hdr['m_version']['m_baseBuild']==hdr['m_dataBuildNum']==98348 and hdr['m_ngdpRootKey']['m_data'].hex()==ROOT)
        raw=archive.read_file('replay.server.battlelobby')
    finally:archive.close()
    require(len(raw)<=8*1024*1024 and sha(raw)==US_MEMBER_SHA)
    mods=audit_member(raw,'observed-11','current-observed');require(len(mods['entries'])==6)
    reader=_Reader(raw);reader.position=mods['mod_metadata_end_bit']
    terminals=[reader.blob(40) for _ in range(reader.bits(6))]
    require(len(terminals)==6 and reader.position==mods['terminal_handles_end_bit'])
    prefix=[bytes.fromhex(s) for s in dependency_prefix(raw)['handles']];require(len(prefix)==6)
    layer=decode_layer(raw,'observed-11');tokens={t.path:t.value for t in layer.tokens}
    global_locales={tokens[f'/locales/{i}/fourcc']:[tokens[f'/locales/{i}/handles/{j}'] for j in range(6)] for i in range(tokens['/locales/count'])}
    info=[]
    for entry in mods['entries']:
        d=native.NativeDecoder(protocol,raw,entry['start_bit']);d.decode(5852)
        require(d.reader.position==entry['end_bit'] and d.exact_consumed_bits())
        value=native_value(d,records,5852)
        require((value['m_mapVersion']['m_major']<<16)|value['m_mapVersion']['m_minor']==value['m_handle']['m_version'])
        info.append(value)
    paths=list((WORK/'independent-parser/s2mh-headers').glob('*.s2mh'))
    paths += [WORK/'header-reconstruction/recovered-headers-private'/(s+'.s2mh') for s in ('0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a','3c2d7d5c17b8a5351c03d7bfb40159ca158694176b81d51bbd1d12abadc2e429')]
    require(len(paths)==5)
    headers=[];output=[];source_guards=[]
    for path in paths:
        body=read(path);require(sha(body)==path.stem)
        source_guards.append((path,path.stem))
        wire=nodes.parse(body);require(nodes.encode(wire)==body and nodes.to_generic(wire)==decode_verified_header(body,path.stem))
        typed=NamedVersioned(records).bind(wire,4376);bnet=typed['m_bnet']
        matches=[j for j,value in enumerate(terminals) if value[8:].hex()==path.stem]
        require(len(matches)==1);index=matches[0]
        require(bnet['m_archiveCacheHandle']==prefix[index] and bnet['m_handle']==info[index]['m_handle'])
        rebase=locale_map(bnet['m_locales'],global_locales)
        comparisons,variants=compare(bnet,info[index],rebase)
        require(all(c['equal'] and c['locale_indices_rebased_by_12_exact_handles']==0 for c in comparisons) and all(v['nine_common_named_fields_equal'] for v in variants))
        headers.append((typed,index))
        output.append({'header_sha256':path.stem,'strict_full_versioned_native_graph_binding':True,'common_fields':comparisons,'variants':variants,'variant_counts_equal':len(bnet['m_variants'])==len(info[index]['m_variants'])})
    eu_path=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')/EU_DATAMOD[:2]/EU_DATAMOD[2:4]/(EU_DATAMOD+'.s2mh')
    eu_raw=read(eu_path);require(sha(eu_raw)==EU_DATAMOD and len(eu_raw)==1660)
    source_guards.append((eu_path,EU_DATAMOD))
    eu_node=nodes.parse(eu_raw);require(nodes.encode(eu_node)==eu_raw and nodes.to_generic(eu_node)==decode_verified_header(eu_raw,EU_DATAMOD))
    eu=NamedVersioned(records).bind(eu_node,4376)
    matches=[j for j,h in enumerate(prefix) if h[8:]==eu['m_bnet']['m_archiveCacheHandle'][8:]];require(len(matches)==1)
    index=matches[0];require(terminals[index][8:].hex()==TARGET)
    # No EU-to-US cache-handle rewrite is made. Missing-header locale rebasing
    # stays unavailable unless all12 exact authenticated handles already match.
    try:eu_rebase=locale_map(eu['m_bnet']['m_locales'],global_locales)
    except ValueError:eu_rebase={}
    comparisons,variants=compare(eu['m_bnet'],info[index],eu_rebase)
    mismatches=[r['MapInfo_field'] for r in comparisons if not r['equal']]
    require(mismatches==['m_handle','m_visualFiles','m_extraDependencies'])
    require(all(v['nine_common_named_fields_equal'] for v in variants))
    wrong_module=sum(typed['m_bnet']['m_handle']!=value['m_handle'] for typed,own in headers for other,value in enumerate(info) if other!=own)
    require(wrong_module==25)
    unexposed_paths=[('m_bnet','m_name'),('m_bnet','m_mapNamespace'),
        *[('m_bnet','m_workingSet',name) for name in ('m_specialScope','m_instances','m_visibilityOverrides','m_indexRestrictions','m_permissionRestrictions')],
        *[('m_bnet',name) for name in ('m_definitions','m_resultDefinitions','m_addDefaultPermissions','m_relevantPermissions','m_resourceList')],
        ('m_game','m_dummy')]
    unexposed=[]
    for path in unexposed_paths:
        numeric,_=wire_path(records,path)
        unexposed.append({'header_named_path':'Header/'+'/'.join(path),'wire_path':numeric,'source_shape':private_shape(value_at(eu,path)),
                          'status':'No corresponding field in the32-member S2MapInfo; retained target value is not authenticated by this lane.'})
    for variant in eu['m_bnet']['m_variants']:
        for name in ('m_instances','m_lockedAttributes','m_visibilityOverrides','m_instanceRestrictions','m_achievementTags'):
            unexposed.append({'header_named_path':'Header/m_bnet/m_variants[]/'+name,'source_shape':private_shape(variant[name]),
                'status':'Omitted from S2MapVariantInfo; retained target value is not authenticated by this lane.'})
    require(len(unexposed)==18)
    for path,expected in source_guards:require(sha(read(path))==expected)
    require(sha(read(replay,3*1024*1024))==US_REPLAY_SHA and sha(read(source))==NATIVE_SHA and sha(read(HERE/'native-header-mapinfo-selected-graph.json'))==GRAPH_SHA)
    require(sha(read(WORK/'native-mapinfo-ready/native_mapinfo_schema_98348.json'))==MAPINFO_SCHEMA)
    require(not (WORK/'header-reconstruction/recovered-headers-private'/(TARGET+'.s2mh')).exists())
    primary=WORK/'independent-parser/s2m-primary/s2m.go'
    return {'format':'hots-native-MapInfo-header-field-exposure-v1','producer_sha256':sha(read(Path(__file__))),
            'native_selected_graph_sha256':GRAPH_SHA,'source_PE_sha256':graph['PE_sha256'],'source_embedded_BSN_sha256':graph['embedded_BSN_sha256'],
            'selected_graph_types':382,'PE_reads_in_this_comparison_stage':0,
            'separate_graph_projection_PE_read_bytes':graph['PE_bytes_read'],
            'selected_MapInfo_schema_comparison':{'schema_sha256':MAPINFO_SCHEMA,'all191_complete_record_dictionaries_exact':True,'ordered32_root_fields_exact':True,'comparison_source':'Separately projected382-type closure from the same hash-pinnedPE, using the shared reviewed metadata grammar parser.'},
            'root21case_binding_receipt_sha256':MAPINFO_PROOF,'root21case136record_binding_not_rerun_in_this_lane':True,
            'shared_native_research_decoder_sha256':NATIVE_SHA,
            'source_US_replay_sha256':US_REPLAY_SHA,'source_US_member_sha256':US_MEMBER_SHA,
            'controls':output,'aggregate':{'known_US_headers':5,'exact_common_named_field_comparisons':75,'exact_common_variant_field_comparisons':45,'wrong_module_handle_negative_comparisons':25,'all_direct_comparisons_required_no_index_rebasing':True},
            'named_native_field_schema_links':field_schema_links(records),
            'EU_DataMod_source_sha256':EU_DATAMOD,'actual_missing_US_DataMod_terminal_sha256':TARGET,
            'EU_DataMod_comparisons':comparisons,'EU_DataMod_variants':variants,
            'EU_DataMod_exposed_retained_fields_exact':12,'EU_DataMod_exposed_common_variant_fields_exact':9,
            'EU_source_mismatches_already_replaced_by_prior_recipe':mismatches,
            'new_contradiction_among_exposed_retained_fields':False,
            'unexposed_retained_field_groups':unexposed,
            'unexposed_retained_field_group_count_including_namespace':len(unexposed),
            'old_recipe_fully_authenticated_except_namespace':False,
            'authors_and_server_flags_are_not_outer_root1':True,
            'formal_outer_root1_definition':{'Header_type_id':4376,'field_tag':1,'field_name':'m_game','resolved_type_id':4449,'resolved_type_name':'Battlenet::S2Map::GameHeader','members':[{'tag':0,'name':'m_dummy','kind':'BOOL'}]},
            'author_field_names_not_in_actual_s2mh_Header_schema':['m_authorRealName','m_authorToonName','m_authorToonHandle'],
            'primary_crossgame_reader':{'repository':'sc2-arcade-watcher/s2mdec','commit':'b48c60a697b12ae1dc8681a2d42ce313958ce94a','path':'s2m.go','local_sha256':sha(read(primary)),'ReadS2MH_line':719,'scope':'SC2 reader names the same BnetHeader paths and explicitly descends outerfield0; it does not name outerfield1. CurrentHotS native graph plus actual bytes name root1.'},
            'outer_root1_single_dummy_BOOL_shape_all6':True,
            'outer_root1_US_control_value_cardinality':len({t['m_game']['m_dummy'] for t,_ in headers}),
            'outer_root1_EU_DataMod_equals_all5_US_controls':all(eu['m_game']==t['m_game'] for t,_ in headers),
            'exact_current_native_MapInfo_entries':len(info),'all6_exact_record_ends_and_consumed_bit_reencoding':True,
            'namespace_author_creator_player_values_or_private_digests_emitted':False,
            'header_candidates_bodies_or_replays_created':0,'client_network_repo_or_cloud_used':False,
            'limits':['This lane compares32named currentMapInfo fields with five known exact wholeUSheaders and the authenticatedEUDataMod template; it does not authenticate an unknown wholeUSDataMod header.',
                      'Shared native type/field names supply the mapping. Constant-valued equalities alone are not used to infer a new semantic relationship.',
                      'All75direct known-header comparisons matched without localization rebasing; no EU-to-US locale-handle rewrite or regional hash substitution was used.',
                      'Authors, profile addresses and private/locked/mod cluster flags in MapInfo are not a Header.root1 author structure. No author or namespace value is emitted or transferred.',
                      'Eighteen retained field groups, including namespace, remain unexposed by MapInfo. Empty arrays or the common dummy BOOL do not prove their unknown target values.',
                      'No newcandidate is assembled; the complete advertised42afeSHA remains the only acceptance criterion for any separately authorized reconstruction.']}

if __name__=='__main__':
    output=HERE/'native-mapinfo-header-field-exposure-v2.json'
    raw=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    require(len(raw)<=64*1024)
    with output.open('xb') as stream:stream.write(raw)
    data=json.loads(raw)
    print(json.dumps({'bytes':len(raw),'sha256':sha(raw),'aggregate':data['aggregate'],'unexposed_groups':data['unexposed_retained_field_group_count_including_namespace']}))
