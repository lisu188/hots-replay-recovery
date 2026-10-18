"""One pinned PE read; export only a narrowly selected static metadata graph."""
import hashlib
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / 'native-embedded-schema-98348'
PARSER_SHA = '0c8021fdcb761a27ca9860f72161110e1156f518678430b9570a49fc20f85f06'
PE_SHA = 'efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
BLOB_SHA = 'ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
sha = lambda b: hashlib.sha256(b).hexdigest()

def check(value, message):
    if not value: raise ValueError(message)

def project():
    source = NATIVE / 'parse_bsn_metadata.py'
    check(sha(source.read_bytes()) == PARSER_SHA, 'reviewed metadata parser differs')
    sys.path.insert(0, str(NATIVE))
    from parse_bsn_metadata import Protocol
    path = Path('C:/Program Files (x86)/Heroes of the Storm/Versions/Base98348/HeroesOfTheStorm_x64.exe')
    check(not path.is_symlink(), 'PE symlink refused')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        check(before.st_size == 53573840, 'PE size differs')
        raw = stream.read(53573841)
        after = os.fstat(stream.fileno())
    check(len(raw) == 53573840 and sha(raw) == PE_SHA, 'full PE pin differs')
    check((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'PE changed')
    blob = raw[43169040:43560673]
    check(sha(blob) == BLOB_SHA, 'blob pin differs')
    p = Protocol(blob)
    parent = p.records[5842]
    wanted = ('m_resourceMap', 'm_accessMatrix', 'm_disabledHeroList')
    selected = []
    for name in wanted:
        check(parent['field_names'].count(name) == 1, 'selected parent member absent/nonunique')
        i = parent['field_names'].index(name)
        selected.append({'name': name, 'member_index': i, 'tag': parent['tags'][i], 'type_id': parent['field_types'][i]})
    roots = {5830, 7981} | {m['type_id'] for m in selected}
    closure = set()
    def visit(i):
        if i in closure: return
        closure.add(i)
        check(len(closure) <= 64, 'selected graph too large')
        rec = p.records[i]
        for child in rec.get('field_types', []) + ([rec['element_type']] if 'element_type' in rec else []): visit(child)
    for i in roots: visit(i)
    check(sha(source.read_bytes()) == PARSER_SHA, 'parser changed')
    final = path.stat()
    check((final.st_size, final.st_mtime_ns) == (before.st_size, before.st_mtime_ns), 'PE metadata changed')
    return {'format': 'hots-native-resource-matrix-static-projection-v1', 'producer_sha256': sha(Path(__file__).read_bytes()),
            'source_PE_sha256': PE_SHA, 'source_PE_bytes': len(raw), 'PE_read_passes': 1, 'PE_bytes_read': len(raw),
            'embedded_blob_sha256': BLOB_SHA, 'metadata_parser_sha256': PARSER_SHA,
            'independent_metadata_review_sha256': '9d378748169662bf862f9c947448b986f66463a1fee1949ba524023f8804eb3b',
            'parent': {k: parent[k] for k in ('id', 'kind', 'name', 'offset', 'bytes')},
            'selected_parent_members': selected, 'selected_records': [p.records[i] for i in sorted(closure)],
            'private_player_values_or_raw_binary_body_emitted': False, 'game_code_loaded_or_executed': False,
            'limits': ['Selected static metadata only; no ownership, bit-index or old-version meaning inferred.',
                       'Parent contains other members; this export is explicitly a selected graph, not its complete schema.']}

if __name__ == '__main__':
    out = HERE / 'native-resource-matrix-static-98348.json'
    check(not out.exists(), 'refuse existing projection')
    data = (json.dumps(project(), indent=2, sort_keys=True) + '\n').encode()
    check(len(data) <= 64*1024, 'projection too large')
    with out.open('xb') as stream: stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': sha(data)}))
