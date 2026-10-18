"""Read one pinned PE as ordinary bytes; retain only selected static BSN types."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
PE_SHA='efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
BSN_SHA='ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
PARSER_SHA='0c8021fdcb761a27ca9860f72161110e1156f518678430b9570a49fc20f85f06'
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def require(value):
    if not value:raise ValueError('Pinned static header graph differs')

def project():
    source=WORK/'native-embedded-schema-98348/parse_bsn_metadata.py'
    require(source.stat().st_size<=128*1024 and sha(source.read_bytes())==PARSER_SHA)
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('_pinned_header_graph_parser',source)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    path=Path('C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe')
    require(not path.is_symlink())
    hasher=hashlib.sha256();position=0;selected=bytearray()
    with path.open('rb') as stream:
        before=os.fstat(stream.fileno());require(before.st_size==53573840)
        while position<before.st_size:
            raw=stream.read(min(512*1024,before.st_size-position));require(raw)
            hasher.update(raw)
            a=max(position,43169040);b=min(position+len(raw),43560673)
            if a<b:selected.extend(raw[a-position:b-position])
            position+=len(raw)
        after=os.fstat(stream.fileno())
    require(position==53573840 and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns) and hasher.hexdigest()==PE_SHA)
    require(len(selected)==391633 and sha(selected)==BSN_SHA)
    protocol=module.Protocol(bytes(selected))
    roots=(4376,4448,5852);closure=set()
    def visit(index):
        if index in closure:return
        closure.add(index);require(len(closure)<=2048)
        record=protocol.records[index]
        for child in record.get('field_types',[])+([record['element_type']] if 'element_type'in record else []):visit(child)
    for root in roots:visit(root)
    require(sha(source.read_bytes())==PARSER_SHA)
    return {'format':'hots-native-header-mapinfo-selected-graph-v1','producer_sha256':sha(Path(__file__).read_bytes()),
            'PE_sha256':PE_SHA,'PE_bytes_read':position,'PE_read_passes':1,'embedded_BSN_sha256':BSN_SHA,
            'metadata_parser_sha256':PARSER_SHA,'root_type_ids':list(roots),'selected_type_count':len(closure),
            'records':[protocol.records[index] for index in sorted(closure)],
            'private_values_binary_body_or_game_code_emitted':False,'client_or_network_used':False}

if __name__=='__main__':
    output=HERE/'native-header-mapinfo-selected-graph.json'
    raw=(json.dumps(project(),indent=2,sort_keys=True)+'\n').encode()
    require(len(raw)<=256*1024)
    with output.open('xb') as stream:stream.write(raw)
    data=json.loads(raw);records={r['id']:r for r in data['records']}
    print(json.dumps({'bytes':len(raw),'sha256':sha(raw),'selected_types':data['selected_type_count'],
                      'roots':[{k:records[i][k] for k in ('id','name','kind','field_names','field_types','tags')} for i in data['root_type_ids']]}))
