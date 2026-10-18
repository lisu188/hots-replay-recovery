"""Rebuild a scoped lookup ledger from saved search metadata and cached sources.

Offline only: this records no replay, player, matrix or account values.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import stat

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
EVIDENCE = 'ee07ebe9c5e7bd1b6b7bf6347b41111f1271a462b9fa4977ac1a95837e4be504'
STATIC = 'c2c8deb0775bc35e3621dbd2567b39fd9159590263a0fd777c54ce79d5dcb7c7'
CACHED = (
    'collection-registry-ready/registry-semantics-primary-source-findings.json',
    'licensed-registry-semantics/registry-access-semantics-findings-v2.json',
    'licensed-registry-semantics/natives.galaxy',
    'licensed-registry-semantics/NativeLib_h.galaxy',
    'licensed-registry-semantics/NativeLib.galaxy',
    'licensed-registry-semantics/HeroesLib_h.galaxy',
    'licensed-registry-semantics/HeroesLib.galaxy',
    'player-block-source-research/player-block-primary-history-followup.json',
)
TERMS = ('ResourceState','ScopeResources','ResourceAccessMatrix','ResourceAccessList')

def sha(raw): return hashlib.sha256(raw).hexdigest()

def read(path, limit=1024*1024):
    if path.is_symlink(): raise ValueError('Source symlink refused')
    with path.open('rb') as stream:
        a = os.fstat(stream.fileno())
        if not stat.S_ISREG(a.st_mode) or not 0 < a.st_size <= limit:
            raise ValueError('Source size/type differs')
        raw = stream.read(limit+1)
        b = os.fstat(stream.fileno())
    if len(raw) != a.st_size or (a.st_size,a.st_mtime_ns) != (b.st_size,b.st_mtime_ns):
        raise ValueError('Source changed during read')
    return raw

def build():
    evidence_raw = read(HERE/'search-call-evidence.json',64*1024)
    if sha(evidence_raw) != EVIDENCE: raise ValueError('Search metadata pin differs')
    evidence = json.loads(evidence_raw)
    if (evidence['external_tool_calls'],evidence['search_queries'],evidence['primary_source_bodies_fetched']) != (4,6,0):
        raise ValueError('Acquisition scope differs')
    cached = []
    for name in CACHED:
        raw = read(WORK/name)
        hits = {term:len(re.findall(re.escape(term.encode()),raw)) for term in TERMS}
        if any(hits.values()): raise ValueError('Cached exact-term negative result changed')
        cached.append({'file':Path(name).name,'bytes':len(raw),'sha256':sha(raw),'exact_type_name_hits':hits})
    static_raw = read(WORK/'native-resource-matrix-ready/native-resource-matrix-static-98348.json',64*1024)
    if sha(static_raw) != STATIC: raise ValueError('Authenticated static projection differs')
    native = {r['id']:r for r in json.loads(static_raw)['selected_records']}
    if (native[2422]['name'],native[2422]['kind'],native[2422]['element_type']) != ('Battlenet::S2Map::ResourceState','USER',58):
        raise ValueError('ResourceState native alias differs')
    if native[58]['kind'] != 'INT' or native[58]['bounds']['bits'] != 16:
        raise ValueError('ResourceState scalar differs')
    if native[5832]['name'] != 'Battlenet::S2Map::ScopeResources' or native[5832]['kind'] != 'ARRAY' or native[5832]['bounds']['min'] != 16 or native[5832]['bounds']['max'] != 16:
        raise ValueError('ScopeResources native fixed-array relation differs')
    calls = []
    for row in evidence['calls']:
        calls.append({key:row[key] for key in ('id','tool','queries','query','url','result','unrelated_result','total_count','incomplete_results','returned','repositories') if key in row})
    return {
        'format':'hots-resource-state-scoped-primary-lookup-v1',
        'producer_sha256':sha(read(Path(__file__))),
        'search_call_evidence_sha256':EVIDENCE,
        'external_tool_calls':4,'search_queries':6,'primary_source_bodies_fetched':0,
        'cached_inputs':cached,'calls':calls,
        'native_static_projection_sha256':STATIC,
        'existing_native_evidence':{'ResourceState':'A named USER alias resolves to an unsigned16-bit INT, not an ENUM in this selected graph.','ScopeResources':'A fixed16-element array supplies no per-index member names in this selected graph.','scope':'This is authenticated current98348 metadata already independently bound to21 matrices; no new external semantics were discovered.'},
        'new_primary_flag_definitions_found':False,
        'new_primary_scope_index_mapping_found':False,
        'accepted_constants_or_guessed_semantic_mappings':[],
        'result':'Scoped negative. No concrete author-owned Battlenet flag constant or index definition was obtained within the four-call budget.',
        'limits':evidence['scope_limits'] + ['The API returned only first30of32ResourceAccessMatrix hits and first100of3736genericScopeResources hits; this is not an exhaustive code audit.','Repository descriptions and paths supplied context only; result bodies were not fetched or treated as semantic definitions.','Cached public Galaxy natives and prior source-research receipts contain none of the exact four type names.','The absence of an ENUM record in the selected current graph does not prove that implementation constants or flags do not exist elsewhere.'],
        'replay_or_PE_or_matrix_values_read':False,
        'account_queries_or_live_ownership_queries_used':False,
        'player_values_matrix_patterns_or_private_identifiers_emitted':False,
        'client_or_repo_or_cloud_modified':False,
    }

if __name__ == '__main__':
    output = HERE/'resource-state-scoped-primary-lookup.json'
    raw = (json.dumps(build(),indent=2,sort_keys=True)+'\n').encode()
    if len(raw)>64*1024: raise ValueError('Ledger too large')
    with output.open('xb') as stream: stream.write(raw)
    print(json.dumps({'bytes':len(raw),'sha256':sha(raw)}))
