"""Select the current native S2MapInfo closure; never execute the client."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'native-embedded-schema-98348'))
from inspect_bsn_schema import analyze,load_current_PE,EXPECTED,BLOB_SHA
sha=lambda raw:hashlib.sha256(raw).hexdigest()
ROOT=5852

def project():
    _,protocol=analyze(load_current_PE())
    selected=set()
    def walk(i):
        if i in selected:return
        selected.add(i)
        if len(selected)>1000:raise ValueError('Selected MapInfo closure budget exceeded')
        rec=protocol.records[i]
        for child in rec.get('field_types',[])+([rec['element_type']] if 'element_type' in rec else []):walk(child)
    walk(ROOT)
    root=protocol.records[ROOT]
    if root['name']!='Battlenet::Event::S2Maps::S2MapInfo' or root['count']!=32:raise ValueError('Current root differs')
    return {'format':'hots-authenticated-native-MapInfo-selected-closure-v1',
            'profile':'mapinfo-98348','root_type_id':ROOT,
            'source_PE_sha256':EXPECTED,'source_embedded_bytecode_sha256':BLOB_SHA,
            'selected_type_count':len(selected),'ordered_root_fields':root['field_names'],
            'records':[protocol.records[i] for i in sorted(selected)],
            'raw_PE_or_full_BSN_blob_included':False,'private_author_or_player_values_included':False}

if __name__=='__main__':
    folder=WORK/'native-mapinfo-ready';folder.mkdir(exist_ok=False)
    data=(json.dumps(project(),indent=2,sort_keys=True)+'\n').encode()
    if len(data)>256*1024:raise ValueError('Selected schema size cap exceeded')
    path=folder/'native_mapinfo_schema_98348.json'
    with path.open('xb') as stream:stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data),'selected_types':json.loads(data)['selected_type_count']}))
