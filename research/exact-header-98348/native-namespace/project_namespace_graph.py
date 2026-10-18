"""Selected formal namespace paths, ordinary-byte PE read, no target execution."""
import hashlib,json,os,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;WORK=HERE.parent
PARSER_SHA='0c8021fdcb761a27ca9860f72161110e1156f518678430b9570a49fc20f85f06'
PE_SHA='efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
BLOB_SHA='ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
sha=lambda b:hashlib.sha256(b).hexdigest()
def require(value):
    if not value:raise ValueError('Pinned selected namespace projection failed')
def analyze():
    source=WORK/'native-embedded-schema-98348/parse_bsn_metadata.py';require(sha(source.read_bytes())==PARSER_SHA)
    sys.path.insert(0,str(source.parent));from parse_bsn_metadata import Protocol
    path=Path('C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe')
    require(not path.is_symlink())
    with path.open('rb') as f:
        before=os.fstat(f.fileno());require(before.st_size==53573840)
        raw=f.read(53573841);after=os.fstat(f.fileno())
    require(len(raw)==53573840 and sha(raw)==PE_SHA and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns))
    blob=raw[43169040:43560673];require(sha(blob)==BLOB_SHA);p=Protocol(blob)
    def children(r):return r.get('field_types',[])+([r['element_type']] if 'element_type'in r else [])
    reverse={i:[] for i in range(len(p.records))}
    for r in p.records:
        for child in children(r):reverse[child].append(r['id'])
    relevant={145};pending=[145]
    while pending:
        for parent in reverse[pending.pop()]:
            if parent not in relevant:relevant.add(parent);pending.append(parent)
    def summary(i,filter_namespace=False):
        r=p.records[i];out={k:r[k]for k in('id','kind','name','bounds','offset','bytes')if k in r}
        if 'element_type'in r:out['element_type']=r['element_type']
        if 'field_types'in r:
            out['members']=[{'name':name,'tag':tag,'type_id':child,'type_name':p.records[child]['name'],'type_kind':p.records[child]['kind']}
                for name,tag,child in zip(r['field_names'],r['tags'],r['field_types'])if not filter_namespace or child in relevant]
        return out
    def chain(i):
        result=[];seen=set()
        while i not in seen:
            seen.add(i);result.append(summary(i))
            r=p.records[i]
            if r['kind']not in('ARRAY','USER','OPTIONAL'):break
            i=r['element_type']
        return result
    start=p.records[5842];require(start['name']=='Battlenet::Event::S2GameEngine::StartGameRequest')
    map_i=start['field_names'].index('m_mapInfoList');map_type=start['field_types'][map_i]
    matches={name:ids for name,ids in p.by_name.items()if 'ModParams'in name or 'WorkingSet'in name or 'DefinitionList'in name or 'DefinitionHandle'in name}
    final=path.stat();require((final.st_size,final.st_mtime_ns)==(before.st_size,before.st_mtime_ns))
    return {'format':'hots-native-formal-namespace-selected-graph-v1','producer_sha256':sha(Path(__file__).read_bytes()),
        'PE_sha256':PE_SHA,'PE_read_bytes':len(raw),'PE_read_passes':1,'embedded_blob_sha256':BLOB_SHA,'parser_sha256':PARSER_SHA,
        'namespace_alias_chain':chain(145),'direct_namespace_parent_records':[summary(i)for i in sorted(set(reverse[145]))],
        'namespace_ancestor_record_count':len(relevant),'namespace_ancestor_graph':[summary(i,True)for i in sorted(relevant)],
        'startgame_direct_record':summary(5842),'startgame_reaches_formal_namespace':5842 in relevant,
        'map_info_list_chain':chain(map_type),'map_info_list_reaches_formal_namespace':map_type in relevant,
        'named_definition_workingset_modparams_records':[summary(i)for ids in matches.values()for i in ids],
        'header_record':summary(4448),'no_namespace_account_creator_or_player_values_emitted':True,
        'no_candidate_header_or_raw_body_written':True,'no_network_or_game_execution':True}
if __name__=='__main__':
    out=HERE/'native-formal-namespace-selected-graph.json';require(not out.exists())
    data=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode();require(len(data)<=128*1024)
    with out.open('xb')as f:f.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
