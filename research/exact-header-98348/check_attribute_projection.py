"""Small authenticated header controls and target field5 projection coverage."""
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;WORK=BASE.parent;EU=WORK/'eu-replay-search-20261018';REPO=Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0]=[str(REPO),str(BASE),str(WORK/'heroprotocol'),str(WORK/'python-deps')]
from battlelobby_header_attributes import project,localization_indices,localize_package
from reference_replay import checked_archive
from depot_s2mh_wire import decode_verified_header
from battlelobby_attribute_layer import LayerError
cache=Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=checked_archive(EU/'heroeslounge-27515-g1-20261005.StormReplay')
try:raw=a.read_file('replay.server.battlelobby')
finally:a.close()
projection=project(raw,'observed-11');by_id={tuple(x[0][k] for k in (0,1)):x for x in projection.attributes}
def mismatch(a,b,path=''):
    if a==b:return []
    if type(a) is dict and type(b) is dict and set(a)==set(b):return sum((mismatch(a[k],b[k],path+'/'+str(k)) for k in a),[])
    if type(a) is list and type(b) is list and len(a)==len(b):return sum((mismatch(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
    return [path]
rows=[]
for source in json.loads((EU/'four-eu-base-header-acquisition.json').read_bytes())['results'][:3]:
    header=decode_verified_header((EU/source['local_file']).read_bytes(),source['sha256'])[0]
    groups=[]
    for item in header[5]:
        identity=tuple(item[0][k] for k in (0,1));target=by_id.get(identity)
        if target is None:raise LayerError('Missing authenticated header identity')
        target=localize_package([target],source['index'])[0]
        paths=mismatch(item,target)
        groups.append({'identity':identity,'exact':not paths,'mismatch_paths':paths[:20],'mismatch_path_count':len(paths)})
    rows.append({'header_sha256':source['sha256'],'package_identity':header[0],'attribute_count':len(groups),'exact_attributes':sum(x['exact'] for x in groups),'details':groups,'max_attribute_localization_index':max(localization_indices(header[5]),default=0),'field7_record_count':len(header.get(7,[]))})
headers=[]
for version,h in [(65661,'29f66c9eca1844826ad55f63eb8fd32a2d6e74ddb7931a8e835fb951f58e184d'),(65662,'f115def2b9adbc67cfdd8bb4255cff1a8b44a8c921e98f56eebe20708660a7c9')]:
    tree=decode_verified_header((cache/h[:2]/h[2:4]/(h+'.s2mh')).read_bytes(),h)[0]
    ids=[tuple(x[0][k] for k in (0,1)) for x in tree[5]]
    target=[by_id[k] for k in ids]
    loc=localization_indices(tree[5]);score=[]
    for item in tree[7]:
        for key in (item[2][0],item[2][1]):
            if key is not None and key[2]:score.append(key[2])
    headers.append({'version':version,'header_sha256':h,'max_attribute_localization_index':max(loc),'field7_nonzero_localization_indices':len(score),'field7_min_index':min(score),'field7_max_index':max(score),'field7_starts_immediately_after_attributes':min(score)==max(loc)+1,'current_projected_max_attribute_localization_index':max(localization_indices(target)),'target_attribute_count':len(target),'target_value_count':sum(len(x[1]) for x in target),'target_missing_values_vs_cached':[{'identity':list(k),'prior_values':len(old[1]),'target_values':len(new[1])} for k,old,new in zip(ids,tree[5],target) if len(old[1])!=len(new[1])]})
report={'format':'hots-header-attribute-projection-control-v1','current_member_sha256':hashlib.sha256(raw).hexdigest(),'projected_attribute_count':len(projection.attributes),'complete_attribute_region_boundary_verified':True,'base_controls':rows,'heroesdata_index_controls':headers,'header_candidates_generated':False,'client_launched':False,'raw_player_fields_emitted':False}
out=BASE/'attribute-projection-localized-controls.json'
with out.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'report':out.name,'sha256':sha(out),'base_controls':[{k:x[k] for k in ('package_identity','attribute_count','exact_attributes','max_attribute_localization_index','field7_record_count')} for x in rows],'heroesdata_controls':headers},indent=2))
