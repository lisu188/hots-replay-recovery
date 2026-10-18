"""Select online/offline start-message metadata; never load/execute PE code."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(WORK/'native-embedded-schema-98348'))
from inspect_bsn_schema import analyze,load_current_PE,EXPECTED,BLOB_SHA
output=WORK/'native-lobby-parent-study/native_startgame_schema_98348.json'
assert not output.exists()
_,p=analyze(load_current_PE())
selected=set()
def visit(i):
    if i in selected:return
    selected.add(i)
    if len(selected)>2000:raise ValueError('Start message selected closure budget exceeded')
    record=p.records[i]
    for child in record.get('field_types',[])+([record['element_type']] if 'element_type' in record else []):visit(child)
for root in (5917,5962):visit(root)
data={'format':'hots-authenticated-native-startgame-selected-closure-v1','profile':'startgame-98348',
    'online_root_type_id':5917,'offline_root_type_id':5962,'selected_type_count':len(selected),
    'source_PE_sha256':EXPECTED,'source_embedded_bytecode_sha256':BLOB_SHA,
    'PE_read_passes':1,'PE_read_bytes':53573840,'records':[p.records[i] for i in sorted(selected)],
    'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'raw_PE_full_BSN_blob_or_private_replay_values_included':False,'game_client_or_DLL_executed':False}
raw=(json.dumps(data,sort_keys=True,indent=2)+'\n').encode();assert len(raw)<1024*1024
with output.open('xb') as stream:stream.write(raw)
print(json.dumps({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'selected_types':len(selected),
    'StartRequest_first_and_last_fields':[(i,p.records[i]) for i in (5835,5836,5839)],
    'ClientInfo_fields':p.records[1768]['field_names']}),flush=True)
