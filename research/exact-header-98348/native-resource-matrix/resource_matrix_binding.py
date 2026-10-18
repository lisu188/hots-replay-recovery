"""Current resource-map/matrix representation audit. Private values stay in RAM."""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
STATIC_SHA = 'c2c8deb0775bc35e3621dbd2567b39fd9159590263a0fd777c54ce79d5dcb7c7'
MAX_ROWS = 65535
MAX_MEMBER = 8*1024*1024
sha = lambda b: hashlib.sha256(b).hexdigest()

def require(value, message):
    if not value: raise ValueError(message)

@dataclass(frozen=True, repr=False)
class ResourceBlock:
    identifiers: tuple = field(repr=False)
    rows: tuple = field(repr=False)
    disabled: tuple = field(repr=False)

class ByteReader:
    def __init__(self, raw, start, end):
        require(type(raw) is bytes and len(raw) <= MAX_MEMBER, 'bounded bytes required')
        require(type(start) is int and type(end) is int and 0 <= start <= end <= len(raw), 'invalid byte extent')
        self.raw, self.position, self.end = raw, start, end
    def take(self, n):
        require(type(n) is int and 0 <= n <= self.end-self.position, 'truncated resource block')
        value = self.raw[self.position:self.position+n]
        self.position += n
        return value
    def number(self, bits):
        require(bits in (8,16,32,64), 'unsupported aligned scalar')
        return int.from_bytes(self.take(bits//8), 'big')

class ByteWriter:
    def __init__(self): self.data = bytearray()
    def number(self, value, bits):
        require(bits in (8,16,32,64) and type(value) is int and 0 <= value < 1<<bits, 'scalar cannot be represented')
        self.data.extend(value.to_bytes(bits//8, 'big'))
    def raw(self, value, size):
        require(type(value) is bytes and len(value) == size, 'fixed bytes required')
        self.data.extend(value)

def decode_block(raw, start, end):
    """Aligned native shape only; no meanings are assigned to scalar cell bits."""
    reader = ByteReader(raw,start,end)
    identifiers = tuple(reader.number(64) for _ in range(reader.number(16)))
    matrix_start = reader.position
    count = reader.number(32)
    require(count <= MAX_ROWS and count*32 <= reader.end-reader.position, 'matrix count exceeds bound or input')
    rows = tuple(tuple(reader.number(16) for _ in range(16)) for _ in range(count))
    matrix_end = reader.position
    disabled_count = reader.number(8)
    require(disabled_count <= 128, 'disabled hero count exceeds native bound')
    disabled = tuple(reader.take(4) for _ in range(disabled_count))
    require(reader.position == end, 'resource block end differs')
    return ResourceBlock(identifiers,rows,disabled), {'resource_map_start':start,'resource_map_end':matrix_start,
            'matrix_start':matrix_start,'matrix_end':matrix_end,'disabled_start':matrix_end,'disabled_end':end}

def encode_block(block):
    require(type(block) is ResourceBlock, 'private resource block required')
    require(type(block.identifiers) is tuple and len(block.identifiers)<=MAX_ROWS, 'identifier array bound')
    require(type(block.rows) is tuple and len(block.rows)<=MAX_ROWS, 'matrix array bound')
    require(type(block.disabled) is tuple and len(block.disabled)<=128, 'disabled hero array bound')
    writer=ByteWriter()
    writer.number(len(block.identifiers),16)
    for value in block.identifiers: writer.number(value,64)
    writer.number(len(block.rows),32)
    for row in block.rows:
        require(type(row) is tuple and len(row)==16, 'matrix row must have16cells')
        for value in row: writer.number(value,16)
    writer.number(len(block.disabled),8)
    for value in block.disabled: writer.raw(value,4)
    require(len(writer.data)<=MAX_MEMBER,'encoded resource block exceeds bound')
    return bytes(writer.data)

def check_static(path=HERE/'native-resource-matrix-static-98348.json'):
    raw=path.read_bytes()
    require(sha(raw)==STATIC_SHA,'static projection pin differs')
    report=json.loads(raw)
    records={r['id']:r for r in report['selected_records']}
    def resolve(i):
        seen=set()
        while records[i]['kind']=='USER':
            require(i not in seen and len(seen)<32,'alias cycle/limit')
            seen.add(i);i=records[i]['element_type']
        return records[i]
    def bounds(r,bits,minimum,maximum):
        require(r['bounds']['bits']==bits and r['bounds']['min']==minimum and r['bounds']['max']==maximum,'native scalar/array bounds differ')
    matrix=resolve(5830)
    require(matrix['kind']=='ARRAY' and matrix['name']=='Battlenet::Event::S2GameEngine::ResourceAccessMatrix','matrix type differs')
    bounds(matrix,32,0,4294967295)
    row=resolve(matrix['element_type'])
    require(row['kind']=='ARRAY' and row['name']=='Battlenet::S2Map::ScopeResources','scope row type differs')
    bounds(row,0,16,16)
    scalar=resolve(row['element_type'])
    require(scalar['id']==58 and scalar['kind']=='INT','resource-state scalar differs')
    bounds(scalar,16,0,65535)
    direct=resolve(7981)
    require(direct['kind']=='ARRAY' and direct['name']=='Battlenet::S2Map::ResourceAccessList','direct list differs')
    bounds(direct,32,0,4294967295)
    require(resolve(direct['element_type'])['id']==scalar['id'],'direct list element differs')
    members=report['selected_parent_members']
    require([m['name'] for m in members]==['m_resourceMap','m_accessMatrix','m_disabledHeroList'] and [m['member_index'] for m in members]==[4,5,6],'parent adjacency differs')
    require(resolve(members[1]['type_id'])['id']==matrix['id'],'parent matrix reference differs')
    identifier=resolve(members[0]['type_id'])
    require(identifier['kind']=='ARRAY','resource identifier map differs')
    bounds(identifier,16,0,65535)
    identifier_scalar=resolve(identifier['element_type'])
    require(identifier_scalar['kind']=='INT','resource identifier scalar differs')
    bounds(identifier_scalar,64,0,18446744073709551615)
    disabled=resolve(members[2]['type_id'])
    require(disabled['kind']=='ARRAY' and resolve(disabled['element_type'])['kind']=='FOURCC','disabled hero type differs')
    bounds(disabled,8,0,128)
    return report

def token_positions(tail):
    position=len(tail.prefix)*8;positions={}
    for token in tail.tokens:
        if token.width is None: position+=(-position)%8
        positions[token.path]=position
        position+=len(token.value)*8 if token.width is None else token.width
    require(position==tail.member_bytes*8,'tail token extent differs')
    return positions

def analyze():
    static=check_static()
    code_read_bytes=0
    def code_digest(path):
        nonlocal code_read_bytes
        require(path.stat().st_size<=1024*1024,'runtime source exceeds bound')
        data=path.read_bytes();code_read_bytes+=len(data)
        return sha(data)
    sys.path[:0]=[str(REPO),str(WORK/'heroprotocol'),str(WORK/'python-deps'),str(WORK/'availability-vector-expanded-ready'),str(WORK/'availability-vector-ready'),str(WORK/'availability-representation-ready')]
    import audit_expanded_account_vectors as cohort
    from audit_battlelobby_mod_metadata import audit_member
    from battlelobby_tail import crosscheck,decode_tail
    from protocol_loader import load_protocol
    require(code_digest(Path(cohort.__file__))=='2f020152115324ef7e309807a9d988bc65b62eb8dcf6e8077988b29cdd2dd9ca','cohort loader differs')
    require(code_digest(Path(cohort.prior.__file__))==cohort.PRIOR_SHA,'prior cohort helper differs')
    require(code_digest(Path(cohort.previous.__file__))==cohort.prior.BASE_HELPER_SHA,'baseline helper differs')
    budget=cohort.Budget();specs,legacy,sources=cohort.load_specs(budget)
    budget.add('static_projection_provenance',(HERE/'native-resource-matrix-static-98348.json').stat().st_size)
    protocol=load_protocol(96477)
    require(protocol.recovery_schema_sha256==cohort.previous.SCHEMA_CURRENT,'identity schema differs')
    guards=[]
    for _,path,expected,_ in legacy:
        guard=budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads');budget.register(path,len(guard))
        require(sha(guard)==expected,'legacy source guard differs');guards.append((path,expected))
    runtime={}
    for name in ('audit_expanded_account_vectors','audit_repeated_account_vectors','audit_availability_representation','battlelobby_tail','battlelobby_attribute_layer','audit_battlelobby_mod_metadata','protocol_loader','mpq_reader','collection_license_audit'):
        module=sys.modules[name];path=Path(module.__file__);runtime[name]={'path':path,'sha256':code_digest(path)}
    cases=[];registry=None;row_total=0;cell_total=0;selected_total=0
    for spec in specs:
        source=budget.read(spec['path'],cohort.previous.REPLAY_LIMIT,'guard_rehash_reads');budget.register(spec['path'],len(source))
        require(sha(source)==spec['sha'],'current source digest differs');guards.append((spec['path'],spec['sha']))
        profile_raw,_=cohort.profile_checked(spec['profile'],spec['profile_sha'],spec['sha'],budget)
        archive=cohort.CountedArchive(spec['path'],budget)
        try:
            header=protocol.decode_replay_header(archive.header['user_data_header']['content'])
            require(header['m_version']['m_build']==98348 and header['m_version']['m_baseBuild']==98348 and header['m_dataBuildNum']==98348 and header['m_ngdpRootKey']['m_data'].hex()==cohort.ROOT,'actual build/root differs')
            raw=cohort.previous.bounded_member(archive,'replay.server.battlelobby')
            details_raw=cohort.previous.bounded_member(archive,'replay.details');init_raw=cohort.previous.bounded_member(archive,'replay.initData')
            mods=audit_member(raw,'observed-11','current-observed');tail=decode_tail(raw,mods['terminal_handles_end_bit'],'current-tail')
            checks=crosscheck(tail,protocol.decode_replay_details(details_raw),protocol.decode_replay_initdata(init_raw))
            require(checks['all_details_participants_match_tail_by_slot'] and checks['initdata_identity_multiset_equal'] and checks['initdata_identity_and_slot_matches']==checks['players_checked'] and checks['seed_matches_lobby'] and checks['seed_matches_game_description'] and checks['disabled_hero_list_equal'] is not False,'private crosschecks differ')
            positions=token_positions(tail)
            start=positions['/collections/count'];end=positions['/init/random_seed']
            require(start%8==end%8==positions['/availability/count']%8==0,'aligned matrix context required')
            block,bounds=decode_block(raw,start//8,end//8)
            keys=tuple(t.value for t in tail.tokens if t.path.startswith('/collections/') and t.path.endswith('/value'))
            rows=tuple(t.value for t in tail.tokens if t.path.startswith('/availability/') and t.width is None)
            require(len(keys)==len(rows)==len(block.rows)==len(block.identifiers)==5418,'resource/matrix counts differ')
            require(registry is None or keys==registry,'current registry order differs');registry=keys
            require(all(value==int.from_bytes(key,'big') for value,key in zip(block.identifiers,keys)),'identifier values differ')
            require(all(b''.join(value.to_bytes(2,'big') for value in row)==original for row,original in zip(block.rows,rows)),'u16 matrix values differ')
            require(block.disabled==tail.disabled_heroes,'disabled hero values differ')
            require(bounds['matrix_start']*8==positions['/availability/count'] and bounds['matrix_end']*8==tail.report['boundaries_bits']['collections_end']==positions['/disabled_heroes/count'],'native matrix boundaries differ')
            require(encode_block(block)==raw[start//8:end//8],'independent resource block reencoding differs')
            budget.add_availability(len(rows)*32);row_total+=len(rows);cell_total+=len(rows)*16
            selected_total+=len(raw)+len(details_raw)+len(init_raw)
            cases.append({'id':spec['id'],'replay_sha256':spec['sha'],'profile_sha256':sha(profile_raw),'member_sha256':sha(raw),
                          'build_base_data':98348,'root':cohort.ROOT,'resource_identifiers':len(block.identifiers),'matrix_rows':len(block.rows),
                          'matrix_cells':len(block.rows)*16,'matrix_bytes_including_count':32*len(block.rows)+4,
                          'full_mod_tail_EOF_roundtrip_and_private_crosschecks_passed':True,
                          'native_resourceMap_matrix_disabled_boundaries_exact':True,'all_native_u16_values_equal_prior_row_bytes':True,
                          'independent_resource_block_encode_decode_exact':True})
        finally: archive.close()
    require(len(cases)==21,'complete21-case cohort required')
    for path,expected in guards: require(sha(budget.read(path,cohort.previous.REPLAY_LIMIT,'guard_rehash_reads'))==expected,'source changed after audit')
    for row in runtime.values(): require(code_digest(row['path'])==row['sha256'],'runtime source changed')
    require(sha(budget.read(HERE/'native-resource-matrix-static-98348.json',64*1024,'static_projection_provenance'))==STATIC_SHA,'static projection changed')
    producer_sha=code_digest(Path(__file__));tests_sha=code_digest(HERE/'test_resource_matrix_binding.py')
    require(sum(budget.counts.values())+code_read_bytes<=cohort.MAX_READS,'combined explicit read budget exceeded')
    return {'format':'hots-native-resource-matrix-21case-binding-v1','producer_sha256':producer_sha,'test_source_sha256':tests_sha,
            'static_projection_sha256':STATIC_SHA,'source_PE_sha256':static['source_PE_sha256'],'embedded_blob_sha256':static['embedded_blob_sha256'],
            'runtime_source_SHA256s':{name:row['sha256'] for name,row in sorted(runtime.items())},'source_manifests':sources,
            'canonical_identity_schema_sha256':cohort.previous.SCHEMA_CURRENT,'current_cases':len(cases),'cases':cases,
            'attempted_existing_current_cases':len(specs),'source_or_decode_failures':0,'new_acquisition_attempts':0,
            'aggregate':{'matrix_rows':row_total,'u16_cells':cell_total,'bytes_per_matrix_row':32,'u16_cells_per_row':16,
                         'all_native_resource_matrix_counts_boundaries_and_values_match':True,'all21_resource_identifier_orders_exactly_equal':True},
            'actual_reads':{'distinct_replay_bytes_including_original_R8':sum(budget.distinct.values()),'distinct_replay_files':len(budget.distinct),
                            'explicit_analysis_read_bytes':sum(budget.counts.values())+code_read_bytes,
                            'source_code_verification_read_bytes':code_read_bytes,'read_categories':dict(budget.counts),
                            'decoded_matrix_row_bytes':budget.availability,'selected_decoded_member_bytes':selected_total,
                            'PE_reads_in_this_binding_stage':0,'PE_read_bytes_in_separate_static_projection_stage':static['PE_bytes_read'],
                            'accounting_scope':'All explicit provenance/profile/guard/source-verification reads and inherited MPQ reads; implicit import/runtime filesystem reads excluded.'},
            'all_current_and_original_R8_source_hashes_unchanged':True,
            'private_cell_values_patterns_vector_hashes_positions_accounts_or_masks_emitted':False,'matrix_ownership_or_bit_index_meaning_inferred':False,
            'replay_member_header_or_private_resource_block_written':False,'client_launched':False,'network_used':False,'repo_or_cloud_modified':False,
            'limits':['The selected current native graph names the32-byte row representation as ScopeResources of16ResourceState/u16 cells in ResourceAccessMatrix.',
                      'The distinct ResourceAccessList type has one u16 per element and is not substituted for the matrix.',
                      'Current resourceMap/matrix/disabled-list adjacency and exact boundaries/values are bound to21real controls; the full StartGameRequest has other fields.',
                      'No ownership/entitlement/bit-index meaning, missing/new-license filling, old263-name mapping or old174-bit conversion follows.',
                      'Prior core profiles are hash-bound; this audit freshly verifies build/root, full mod/tail EOF and private identity/seed guards, without rerunning core events.']}

if __name__=='__main__':
    output=HERE/'native-resource-matrix-21case-binding-v2.json'
    require(not output.exists(),'refuse existing matrix binding report')
    data=(json.dumps(analyze(),indent=2,sort_keys=True)+'\n').encode()
    require(len(data)<=64*1024,'report too large')
    with output.open('xb') as stream: stream.write(data)
    print(json.dumps({'bytes':len(data),'sha256':sha(data)}))
