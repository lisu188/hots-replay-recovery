"""Static named-tail constraints from the pinned513-type current native graph.

No replay/PE reads, native execution or migration. Width calculations require
explicit presence/count choices for variable fields and reject byte-aligned
strings/blobs rather than pretending that their width is context-free.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
SCHEMA_SHA = '0fd61c8ef3b0aeef647912fd9e35308e70c39da9e2980004d06b1b92e0c96640'


def schema(raw):
    if type(raw) is not bytes or len(raw) > 256*1024 or hashlib.sha256(raw).hexdigest() != SCHEMA_SHA:
        raise ValueError('Pinned513-type native graph required')
    data = json.loads(raw)
    if data['selected_type_count'] != 513 or data['online_root_type_id'] != 5917:
        raise ValueError('Native graph root differs')
    return {record['id']: record for record in data['records']}


def width(records, identifier, *, counts=None, present=None, depth=0):
    """Derive local scalar/struct width without materializing array elements."""
    counts, present = counts or {}, present or {}
    if depth > 64:
        raise ValueError('Width traversal depth exceeded')
    record = records[identifier]
    kind = record['kind']
    def child(at):
        return width(records, at, counts=counts, present=present, depth=depth+1)
    if kind == 'USER':
        return child(record['element_type'])
    if kind == 'STRUCT':
        return sum(child(at) for at in record['field_types'])
    if kind in ('INT', 'ENUM'):
        return record['bounds']['bits']
    if kind in ('BOOL', 'FOURCC', 'REAL32', 'REAL64'):
        return {'BOOL': 1, 'FOURCC': 32, 'REAL32': 32, 'REAL64': 64}[kind]
    if kind == 'OPTIONAL':
        if identifier not in present or type(present[identifier]) is not bool:
            raise ValueError('Explicit optional presence required')
        return 1 + (child(record['element_type']) if present[identifier] else 0)
    if kind == 'ARRAY':
        bound = record['bounds']
        if bound['min'] == bound['max']:
            count = bound['min']
        elif identifier in counts:
            count = counts[identifier]
        else:
            raise ValueError('Explicit array count required')
        if type(count) is not int or not bound['min'] <= count <= bound['max']:
            raise ValueError('Array count outside authenticated bounds')
        return bound['bits'] + (count*child(record['element_type']) if count else 0)
    raise ValueError('Context-dependent/nonselected width kind refused')


def resolve(records, identifier):
    chain = []
    for _ in range(64):
        record = records[identifier]
        chain.append({'id': identifier, 'kind': record['kind'], 'name': record['name']})
        if record['kind'] != 'USER':
            return chain
        identifier = record['element_type']
    raise ValueError('Alias depth exceeded')


def analyze():
    raw = (HERE/'native_startgame_schema_98348.json').read_bytes()
    records = schema(raw)
    probe_path = HERE/'native-online-USDragon-probe.json'
    probe_raw = probe_path.read_bytes()
    if len(probe_raw) > 64*1024:
        raise ValueError('Probe report exceeds cap')
    probe = json.loads(probe_raw)
    if (probe['schema_sha256'] != SCHEMA_SHA or probe['native_root_type'] != 5917
            or not probe['whole_member_reencoding_exact'] or not probe['source_unchanged']):
        raise ValueError('Source-bound current probe differs')
    spans = {row['name']: row for row in probe['root_field_spans']}
    root = records[5917]
    position = 0
    for name in root['field_names']:
        field = spans[name]
        if field['start_bit'] != position:
            raise ValueError('Native root coverage is not contiguous')
        position = field['end_bit']
    if position != probe['member_end_bit']:
        raise ValueError('Native root does not reach EOF')
    shapes = {
        'voice_session_bits': width(records, 983), 'AMM_optional_absent_bits': width(records, 5923, present={5923: False}),
        'AMM_optional_present_bits': width(records, 5923, present={5923: True}),
        'instance_handle_bits': width(records, 1749),
        'ladder_item_without_season_rating_bits': width(records, 1815, present={1840: False}),
        'ladder_item_with_season_rating_bits': width(records, 1815, present={1840: True}),
        'client_license_record_empty_list_bits': width(records, 2510, counts={908: 0}),
        'client_license_record_two_IDs_bits': width(records, 2510, counts={908: 2}),
        'mastery_record_sixteen_player_tiers_bits': width(records, 1857, counts={1871: 16}),
        'mastery_record_zero_player_tiers_bits': width(records, 1857, counts={1871: 0}),
        'global_resource_identifier_bits': width(records, 2509),
        'suffix_license_identifier_bits': width(records, 866)}
    groups = [
        {'observed': '/init/random_seed32 and /init/unknown32', 'native': ['m_randomSeed(fixed4-byte blob)', 'm_clientId(u32)'], 'relationship': 'Root spans bind the two32-bit extents; blob representation remains distinct.'},
        {'observed': '/players/count5 and player records', 'native': ['m_clientInfoList1702 count5/max16', 'ClientInfo1768 eighteenfields'], 'relationship': 'Current native ClientInfo already independently bound; frozensecondary flag/198 grouping is not its correct field split.'},
        {'observed': '/end/unknown64', 'native': ['m_voiceSessionId983 {label32,instance32}'], 'relationship': 'Exact64-bit root span.'},
        {'observed': '/end/mode_toon_choice + present136 / absent-filler16', 'native': ['m_ammHandle5923 OPTIONAL MatchMaker::Handle1772 {region8,program32,realm32,id32,version16}'], 'relationship': 'Native payload is120bits when present and zero when absent. BOTH observed branches consume sixteenextra bits: the following sixBOOLs plus tenbits of instanceHandle.'},
        {'observed': '/end/unknown87', 'native': ['remaining86bits of m_instanceHandle after observedmode16-bitoverrun', 'm_ladderStats optionalpresence1'], 'relationship': '16+87 equals sixflags6+instance96+ladderpresence1 in BOTH AMM branches; not one87-bit nativefield.'},
        {'observed': '/end/a38_count_minus1 and fixed38-bit items', 'native': ['m_ladderStats optional LadderStatsList1752 count4/min1', 'LadderStats1815 {scope5,mmrREAL32,seasonRatingOPTIONAL REAL32}'], 'relationship': 'A38 is exactly the absent-seasonRating38-bit branch; nonempty seasonRating requires32morebits per affected item.'},
        {'observed': '/end/unknown_bool + /end/neut_count_minus1 + FourCCs', 'native': ['m_races5932 OPTIONAL ARRAYcount4/min1 of FourCC'], 'relationship': 'Frozen codec always reads the array after its presencebit; nativeabsence is a distinct valid branch.'},
        {'observed': '/end/hero_tables count5; unknown32; icons count11; triples; unknown11', 'native': ['m_clientUnlockableInfoList1826 count5/max16', 'ClientUnlockableInfo1856 {clientId32,HandleList1876,OverrideList1672}', 'Unlockable::Handle1884 {programFourCC32,tagFourCC32,index32}'], 'relationship': 'These are generic unlockables rather than a hero/icon-specific table; unknown11 is overrideARRAYcount, whose payload is omitted by the observed profile.'},
        {'observed': '/end/cstm/count6 and FourCCs', 'native': ['m_achievementTags5934 ARRAYcount6/max63 of FourCC'], 'relationship': 'Generic native name identifies the field; no achievement semantics/values inferred.'},
        {'observed': '/end/a41_or_a48 count5; eachunknown32+16 current / +9 historical', 'native': ['m_clientLicensesList2503 count5/max16', 'ClientLicenses2510 {clientId32,License::IdList908 count16/max32768 ofu32}'], 'relationship': 'Current fixed48-bit observed item is only the EMPTYlicense-list branch. Historical9-bit count candidate is a separate unproven oldtype hypothesis; no licenses are dropped/defaulted.'},
        {'observed': '/end/unknown23 + unknown32a + unknown10 + unknown32b', 'native': ['m_currentTurn32', 'm_turnIntervalMS32', 'm_currentSyncEventNumber32', 'm_tournamentInfo OPTIONAL flag1'], 'relationship': 'Observed97-bit grouping crosses native scalar boundaries; exact match only for absent tournament payload.'},
        {'observed': '/end/allheroes count10; FourCC32 + unknown5 + unknown128', 'native': ['m_heroMasteryTiers1827 count10/max512', 'HeroMasteryTier1857 {heroFourCC32,playerTiers ARRAYcount5/max16 ofu8}'], 'relationship': 'Opaque128 is the16-tier case. Native tier array can be0..16 and requires count×8bits.'},
        {'observed': '/end/unknown2', 'native': ['m_rejoinSaveCacheHandle OPTIONAL40-byteblob', 'm_rejoinSaveElapsedGameLoops OPTIONALu32'], 'relationship': 'Two absent optional flags; presence adds a bounded payload and cachehandle bytealignment.'}]
    return {'format': 'hots-current-native-tail-layout-and-observed-profile-constraints-v1',
        'schema_sha256': SCHEMA_SHA, 'probe_sha256': hashlib.sha256(probe_raw).hexdigest(),
        'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_member_sha256': probe['member_sha256'], 'source_replay_sha256': probe['source_replay_sha256'],
        'whole_current_native_root_control_passed': True, 'native_root_type': 5917,
        'root_fields': [{'name': name, 'type_chain': resolve(records, identifier), **spans[name]}
                        for name, identifier in zip(root['field_names'], root['field_types'])],
        'derived_static_width_checks': shapes, 'native_to_observed_groups': groups,
        'resource_and_license_namespaces': {'global_resourceMap_type_chain': resolve(records, 2509),
            'suffix_per_client_license_type_chain': resolve(records, 866),
            'same_identifier_type_claimed': False, 'ownership_or_resourceState_bit_semantics_inferred': False},
        'historical_conversion_constraints': [
            'Current native graph authenticates current field names and bounds only.',
            'Old observed resource names versus current u64 resourceMap require independent static registry binding; this graph does not assign ownership.',
            'Old source profiles omit current override count11 per unlockable-client record and current playerlevel32/boost1; additions need separately audited historical absence/value provenance.',
            'The old observed client-license count9 versus current nativecount16 is a structural candidate, not authenticated historical native type908.',
            'Keep complete per-client license IDs, unlockable overrides, optional payloads, tier counts, session and sync fields; an observed empty branch is not a defaulting rule.'],
        'PE_replay_header_fragment_or_network_reads_in_this_stage': 0,
        'private_field_values_written': False, 'production_codec_or_schema_changed': False,
        'old_to_current_conversion_implemented': False}


if __name__ == '__main__':
    output = HERE/'current-native-tail-layout-and-observed-profile-constraints-v2.json'
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refuse existing report')
    data = (json.dumps(analyze(), indent=2, sort_keys=True)+'\n').encode()
    if len(data) > 64*1024:
        raise ValueError('Report exceeds cap')
    with output.open('xb') as stream:
        stream.write(data)
    print(json.dumps({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}))
