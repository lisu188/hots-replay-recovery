"""Cached-only native lobby parent/anchor study; no PE or replay reads."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
sha = lambda value: hashlib.sha256(value).hexdigest()


def read(path, limit=512*1024):
    if path.is_symlink():
        raise ValueError('Symlink source refused')
    with path.open('rb') as stream:
        raw = stream.read(limit+1)
    if len(raw) > limit:
        raise ValueError('Cached-source bound exceeded')
    return raw


def analyze():
    inputs = {
        'cached_namespace_graph': WORK/'native-namespace-exposure/native-formal-namespace-selected-graph.json',
        'cached_resource_matrix_graph': WORK/'native-resource-matrix-ready/native-resource-matrix-static-98348.json',
        'cached_native_metadata': WORK/'native-embedded-schema-98348/native-BSN-metadata-98348-v2.json',
        'current_native_ClientInfo_closure': WORK/'native-client-codec-ready/native_clientinfo_schema_98348.json',
        'current_native_MapInfo_closure': WORK/'native-mapinfo-ready/native_mapinfo_schema_98348.json',
        'observed_tail_source': REPO/'battlelobby_tail.py',
        'observed_attribute_source': REPO/'battlelobby_attribute_layer.py',
        'observed_mod_metadata_source': REPO/'audit_battlelobby_mod_metadata.py',
        'historical_source_2': WORK/'independent-parser/historical-schemas/2.txt',
        'historical_source_5': WORK/'independent-parser/historical-schemas/5.txt',
        'pinned_independent_Csharp': WORK/'independent-parser/historical-schemas/ReplayServerBattlelobby.pinned.cs',
        'producer': Path(__file__)}
    bodies = {name: read(path) for name, path in inputs.items()}
    namespace = json.loads(bodies['cached_namespace_graph'])
    matrix = json.loads(bodies['cached_resource_matrix_graph'])
    client = json.loads(bodies['current_native_ClientInfo_closure'])
    mapping = json.loads(bodies['current_native_MapInfo_closure'])
    if (namespace['PE_sha256'] != 'efdf5a2f13dfe4f66a63f525f4d4ae3c953064232c60da74b4e6540aa534dca9'
            or namespace['embedded_blob_sha256'] != 'ce3b1f764575730f2c08c89eed73ea843ec4cc702b727c9577ca071ce610e741'
            or sha(bodies['current_native_MapInfo_closure']) != '3900a63c0799474becd2ecfb03eece4f8c523a965b38e539264867d5cdf2075c'
            or sha(bodies['current_native_ClientInfo_closure']) != '6e8711939ede15505debb043ae626b5c529749557d7e824226863c92e4f6a229'):
        raise ValueError('Cached native source binding differs')
    records = {record['id']: record for record in namespace['namespace_ancestor_graph']}
    def children(record):
        return [member['type_id'] for member in record.get('members', [])] + (
            [record['element_type']] if 'element_type' in record else [])
    frontier, seen, chains = [5842], {5842}, []
    for depth in range(8):
        next_ids = []
        for record in records.values():
            for child in children(record):
                if child in frontier and record['id'] not in seen:
                    seen.add(record['id'])
                    next_ids.append(record['id'])
                    chains.append({'depth': depth+1, 'parent_id': record['id'], 'parent_name': record['name'],
                        'kind': record['kind'], 'child_id': child,
                        'member_name': next((m['name'] for m in record.get('members', []) if m['type_id'] == child), None)})
        frontier = next_ids
        if not frontier:
            break
    selected = []
    for identifier in (5834, 5842, 5917, 5962, 5951, 1767, 6062, 6060):
        record = records[identifier]
        bounds = record.get('bounds', {})
        selected.append({'id': identifier, 'name': record['name'], 'kind': record['kind'],
            'native_record_bytes': record['bytes'], 'native_bounds': bounds,
            'dense_count_when_struct': bounds.get('max', 0)-bounds.get('min', 0)+1
                if record['kind'] == 'STRUCT' else None,
            'cached_retained_members_only': record.get('members', [])})
    tail = ast.parse(bodies['observed_tail_source'].decode())
    remaining = []
    for node in ast.walk(tail):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in ('scalar', 'opaque') and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                and (node.args[0].value.startswith('/end/') or node.args[0].value in
                     ('/init/random_seed', '/init/unknown32', '/players/count'))):
            remaining.append({'observed_path': node.args[0].value, 'width_expression': ast.unparse(node.args[1]),
                              'source_line': node.lineno, 'source_function': node.func.id})
    return {'format': 'hots-cached-native-lobby-parent-and-anchor-study-v1',
        'source_files': {name: {'bytes': len(bodies[name]), 'sha256': sha(bodies[name]),
            'path': path.relative_to(WORK).as_posix() if path.is_relative_to(WORK) else path.name}
            for name, path in inputs.items()},
        'cached_source_bytes_read': sum(map(len, bodies.values())),
        'new_PE_replay_header_fragment_network_reads': 0,
        'candidate_native_body_root': {'id': 5917, 'name': records[5917]['name'],
            'reason': 'It contains StartGameRequest, which contains the independently bound MapInfo/resource-map/matrix/disabled-list sequence.',
            'proposed_start_bit': 0, 'whole_member_fit_not_yet_tested_here': True},
        'alternative_native_roots': [5962, 5951], 'cached_native_parent_edges': chains,
        'selected_partial_cached_records': selected,
        'complete_cached_StartGameRequest': namespace['startgame_direct_record'],
        'cached_parent_members_for_resource_matrix': matrix['selected_parent_members'],
        'existing_bound_child_roots': {'ClientInfo': {'id': client['root_type_id'], 'closure_types': len(client['records'])},
                                      'MapInfo': {'id': mapping['root_type_id'], 'closure_types': len(mapping['records'])}},
        'exact_anchor_tests_for_new_complete_projection': [
            {'candidate': 'StartRequest5834 child0/1', 'observed': 'dependency paths count6/length10/byte-aligned strings, then cache-handles count6/fixed40B', 'status': 'hypothesis: missing cached child names'},
            {'candidate': 'StartRequest5834 m_definitionList child2', 'observed': 'attribute table count9; value-count12/index11 under observed-11 profile', 'status': 'count9 matches cached native294; names/complete definition closure still needed'},
            {'candidate': 'StartRequest5834 m_workingSet child3', 'observed': 'working-set127bit prefix, selected count9, visual-file count6 and locale-table count5', 'status': 'candidate grouping; full fieldwise verification needed'},
            {'candidate': 'StartRequest5834 child4', 'observed': '128bits immediately after locale_handles_end', 'status': 'hypothesis: missing cached child name'},
            {'candidate': 'StartGameRequest5842 m_mapLink', 'observed': 'used-mod list count5 with id32/version32/linktype4', 'status': 'test named link closure'},
            {'candidate': 'StartGameRequest5842 m_mapInfoList', 'observed': 'count7 followed by exact current32field MapInfo spans', 'status': '191child closure and spans already bound'},
            {'candidate': 'StartGameRequest5842 m_headerCacheHandles', 'observed': 'count6 then aligned40B s2mh handles ending at tail_start', 'status': 'test full cached-handle list closure'},
            {'candidate': 'StartGameRequest5842 m_resourceMap/m_accessMatrix/m_disabledHeroList', 'observed': 'collections count16×u64; matrix count32×fixed16×u16; disabled count8×FourCC', 'status': 'selected native graph and current21-case binding already exist'},
            {'candidate': 'OnlineStartGameRequest5917 remaining24fields', 'observed': 'tail init32+32, player-list count5/ClientInfo1768, post-player fields through EOF', 'status': 'complete parent graph needed; no guessed names assigned'}],
        'remaining_observed_tail_scalar_source_anchors': sorted(remaining, key=lambda item:item['source_line']),
        'generic_current_decoder_capacity_warning': {'MAX_TOKENS_also_caps_fields': 100000,
            'known_current_matrix_cells': 5418*16, 'minimum_fields_for_three_node_scalar_chain': 5418*16*3,
            'meaning': 'A current full-root probe may hit the existing field budget even with valid syntax; do not silently relax a production pin or treat that limit as a schema contradiction.'},
        'needed_new_projection': {'complete_roots': [5834, 5842, 5917, 5962, 5951],
            'reverse_ancestors_of': [1768, 5830], 'all_8330_type_names_required_here': False},
        'community_sources': {'historical_schema_2': 'https://github.com/EugenPolyakov/HOTS_battlelobby/blob/85625327fd5623368410e5270a7eeb4869b40af9/lobby/2.txt',
            'historical_schema_5': 'https://github.com/EugenPolyakov/HOTS_battlelobby/blob/85625327fd5623368410e5270a7eeb4869b40af9/lobby/5.txt',
            'independent_current_Csharp': 'https://github.com/HeroesToolChest/Heroes.StormReplayParser/blob/d381dd9c273205c0fd7ac402c75eef98c6fa6c78/Heroes.StormReplayParser/MpqFiles/ReplayServerBattlelobby.cs'},
        'limits': ['The namespace ancestor graph intentionally omits members not reaching namespace145; its retained member lists are not complete decoder schemas.',
            'The fixed9 definition/selection count is separate from observed-11 index capacity11/value-count12; these are not a native count mismatch.',
            'This study proposes bounded anchors only and establishes no whole-root parse, old schema or conversion.'],
        'production_profile_replay_or_header_modified': False, 'private_data_written': False}


if __name__ == '__main__':
    output = HERE/'cached-native-lobby-parent-and-anchor-study.json'
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refuse existing study report')
    data = (json.dumps(analyze(), indent=2, sort_keys=True)+'\n').encode()
    if len(data) > 64*1024:
        raise ValueError('Study report exceeds cap')
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': sha(data)}))
