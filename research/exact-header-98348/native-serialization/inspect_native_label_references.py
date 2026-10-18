"""Static pointer/reference candidates only; no target image execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct

WORK=Path(__file__).resolve().parent
HERE=WORK/'native-serialization-98348'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=HERE/'inspect_native_serialization_labels.py'
assert sha(source.read_bytes())=='4c43053e77a9ee4997ab972f6d039f31e1e92902c5e58d514aa90b0af4bdb523'
spec=importlib.util.spec_from_file_location('pinned_pe_static',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
raw=module.IMAGE.read_bytes()
assert len(raw)==53573840 and sha(raw)==module.EXPECTED_SHA
pe=module.PE(raw)
report_raw=(HERE/'native-serialization-labels-98348.json').read_bytes()
assert sha(report_raw)=='6aed9e391b79c2b3252c544c8d1b31065ef6f21380db6928123281f8ca49c2e3'
prior=json.loads(report_raw)
labels=[row for row in prior['selected_labels'] if row['label'] in (
    'm_clientLicensesList','m_licenseCatalog','m_licenseInstance','m_licenses','m_licenseIds','m_mapNamespace',
    'Battlenet::Client::S2Game::EncodedGameDataHeader','Battlenet::Client::S2Game::ClientLicensesList',
    'Battlenet::Client::S2Game::ClientLicenses','Battlenet::S2Map::BnetHeader')]
assert 5<=len(labels)<=32
rows=[]
for row in labels:
    assert raw[row['file_offset']:row['file_offset']+len(row['label'])]==row['label'].encode('ascii')
    record={'label':row['label'],'location':pe.location(row['file_offset'])}
    for name,needle in [('absolute_VA_u64',struct.pack('<Q',pe.imagebase+row['rva'])),('image_RVA_u32',struct.pack('<I',row['rva']))]:
        hits=[];start=0
        while True:
            pos=raw.find(needle,start)
            if pos<0:break
            assert len(hits)<128
            hits.append(pe.location(pos));start=pos+1
        record[name+'_byte_matches']=hits
    rows.append(record)
out={'format':'hots-native-exact-label-pointer-byte-reference-candidates-v1',
    'producer_sha256':sha(Path(__file__).read_bytes()),'PE_parser_source_sha256':sha(source.read_bytes()),
    'source_PE_sha256':module.EXPECTED_SHA,'source_PE_bytes':len(raw),'PE_image_base':pe.imagebase,
    'pinned_initial_report_sha256':sha(report_raw),'selected_labels':len(rows),'references':rows,
    'classification':'Raw integer-address byte matches only; pointer origin, relocation, instruction boundary and semantic use unproven.',
    'target_image_executed_or_loaded':False,'raw_binary_bytes_emitted_or_copied':False,
    'network_used':False,'replay_read_or_written':False,'new_header_candidate':False,
    'full_PE_input_read_passes':1,'full_PE_input_bytes':len(raw)}
dest=WORK/'native-reference-98348';dest.mkdir(exist_ok=False)
path=dest/'native-label-pointer-byte-matches.json'
with path.open('xb') as handle:handle.write((json.dumps(out,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps(out,indent=2))
