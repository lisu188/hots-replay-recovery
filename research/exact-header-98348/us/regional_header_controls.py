"""Private RAM-only regional metadata controls; no candidate-body file writes.

The additive namespace relation is a hypothesis until the complete known object
hash matches. No module namespace, creator identity or account value is emitted.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from collection_license_audit import _read, write_new_report
from lossless_wire import parse, clone, encode, to_generic
from depot_s2mh_wire import decode_verified_header
from protocol_loader import load_protocol
from reference_replay import checked_archive
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_attribute_layer import decode_layer, _Reader
from mod_data_audit import dependency_prefix

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
HEADER_LIMIT = 512*1024
SCHEMA = 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
ROOT = 'c3b3c8bc82e3a5a62e550fdde9a40c28'
ROLES = (b'Core.StormMod', b'Teams10.StormMod', b'Heroes.StormMod')
US_SOURCE = '882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


@dataclass(repr=False)
class Context:
    region: str
    replay_sha256: str
    member_sha256: str
    entries: list
    terminal: list
    prefix: list


def extract_context(path, expected_sha256, region):
    """Read actual, pinned replay metadata; keep private values only in RAM."""
    require(region in ('US', 'EU'), 'An explicit supported region is required')
    replay = _read(path, 5*1024*1024)
    require(sha(replay) == expected_sha256, 'Pinned source replay differs')
    protocol = load_protocol(96477)
    require(protocol.recovery_schema_sha256 == SCHEMA, 'Pinned official schema differs')
    archive = checked_archive(path)
    try:
        raw = archive.read_file('replay.server.battlelobby')
        header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
        details = protocol.decode_replay_details(archive.read_file('replay.details'))
    finally:
        archive.close()
    require(header['m_version']['m_build'] == header['m_version']['m_baseBuild'] ==
            header['m_dataBuildNum'] == 98348 and
            header['m_ngdpRootKey']['m_data'].hex() == ROOT, 'Exact build/root context differs')
    require({x['m_toon']['m_region'] for x in details['m_playerList']} ==
            {1 if region == 'US' else 2}, 'Explicit participant regions differ')
    mods = audit_member(raw, 'observed-11', 'current-observed')
    layer = decode_layer(raw, 'observed-11')
    tokens = {token.path: token.value for token in layer.tokens}
    reader = _Reader(raw)
    reader.position = mods['mod_metadata_end_bit']
    terminal = [reader.blob(40) for _ in range(reader.bits(6))]
    require(reader.position == mods['terminal_handles_end_bit'], 'Terminal end differs')
    prefix = [bytes.fromhex(value) for value in dependency_prefix(raw)['handles']]
    require(len(prefix) == len(terminal) == len(mods['entries']), 'Package counts differ')
    entries = []
    for index, entry in enumerate(mods['entries']):
        reader.position = entry['start_bit']
        identity = (reader.bits(32), reader.bits(32))
        # Explicit current profile:16+16+24+7+15+2+74unknown bits.
        reader.position += 154
        visuals = [reader.blob(40) for _ in range(reader.bits(6))]
        # Six-bit count, count*(id32,version32), final32 bits.
        reader.position = entry['end_bit']-32-entry['dependency_count']*64-6
        count = reader.bits(6)
        require(count == entry['dependency_count'], 'Dependency boundary differs')
        dependencies = [{0: reader.bits(32), 1: reader.bits(32)} for _ in range(count)]
        locales = {tokens[f'/locales/{i}/fourcc'].to_bytes(4, 'big'):
                   tokens[f'/locales/{i}/handles/{index}']
                   for i in range(tokens['/locales/count'])}
        require(len(locales) == tokens['/locales/count'] == 12, 'Expected12distinct locale records')
        entries.append({'identity': identity, 'visuals': visuals,
                        'dependencies': dependencies, 'locales': locales})
    require(sha(_read(path, 5*1024*1024)) == expected_sha256, 'Replay changed during metadata extraction')
    return Context(region, expected_sha256, sha(raw), entries, terminal, prefix)


def _handles(array, values, magic, region):
    require(array.tag == 0 and len(array.value) == len(values), 'Authenticated handle-array shape differs')
    for node, value in zip(array.value, values):
        require(node.tag == 2 and type(node.value) is bytes and len(node.value) == 40,
                'Authenticated handle type differs')
        require(type(value) is bytes and len(value) == 40 and value[:4] == magic and
                value[4:8].strip(b'\0 ') == region.encode('ascii'), 'Observed handle region/type differs')
        node.value = value


def candidate_from_eu(eu_raw, context, package_index, namespace_offset):
    """Return one candidate in RAM; caller must require its complete advertised SHA.

    namespace_offset must be supplied from separately controlled known US
    headers. This function never obtains it from the target header or chooses
    a default. It never saves bytes or declares a candidate accepted.
    """
    require(type(eu_raw) is bytes and 0 < len(eu_raw) <= HEADER_LIMIT, 'Source header exceeds bound')
    require(type(context) is Context and context.region == 'US', 'ObservedUScontext is required')
    require(type(package_index) is int and 0 <= package_index < len(context.entries), 'Invalid package index')
    require(type(namespace_offset) is int, 'Explicit namespace hypothesis is required')
    source = parse(eu_raw)
    generic = decode_verified_header(eu_raw, sha(eu_raw))[0]
    require(generic[2][4:8].strip(b'\0 ') == b'EU', 'Source header is not an EU template')
    require(generic[2][8:] == context.prefix[package_index][8:], 'Source and target archive payloads differ')
    candidate = clone(source)
    header = candidate.field(0)
    entry = context.entries[package_index]
    ident, version = entry['identity']
    require(0 <= ident+namespace_offset < 2**32, 'Namespace hypothesis exceeds32bits')
    for key, value in ((0, ident), (1, version)):
        require(header.field(0).field(key).tag == 9, 'Identity wire type differs')
        header.field(0).field(key).value = value
    require(header.field(3).tag == 9, 'Namespace wire type differs')
    header.field(3).value = ident+namespace_offset
    require(header.field(2).tag == 2 and len(header.field(2).value) == 40, 'Archive wire shape differs')
    require(context.prefix[package_index][:8] == b's2ma\0\0US', 'ActualUSarchive handle differs')
    header.field(2).value = context.prefix[package_index]
    _handles(header.field(4).field(7), entry['visuals'], b's2mv', 'US')
    for array in (header.field(4).field(8), header.field(8)):
        require(array.tag == 0 and len(array.value) == len(entry['locales']), 'Locale-array shape differs')
        names = [item.field(0).value for item in array.value]
        require(len(names) == len(set(names)) and set(names) == set(entry['locales']), 'Locale identities differ')
        for node in array.value:
            _handles(node.field(1), [entry['locales'][node.field(0).value]], b's2ml', 'US')
    dependencies = header.field(14)
    require(dependencies.tag == 0 and len(dependencies.value) == len(entry['dependencies']), 'Dependency-array shape differs')
    for node, observed in zip(dependencies.value, entry['dependencies']):
        require(set(to_generic(node)) == {0, 1}, 'Dependency field shape differs')
        for key in (0, 1):
            require(node.field(key).tag == 9, 'Dependency integer wire type differs')
            node.field(key).value = observed[key]
    body = encode(candidate)
    require(0 < len(body) <= HEADER_LIMIT and encode(source) == eu_raw,
            'Candidate size or source-preservation guard failed')
    return body


def run_controls():
    manifest = json.loads(_read(WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json', 4*1024*1024))
    matches = [row for row in manifest['references'] if row['replay_sha256'] == US_SOURCE]
    require(len(matches) == 1, 'PinnedUScontrol not uniquely identified')
    path = (WORK/matches[0]['replay_file']).resolve()
    require(path.is_relative_to(WORK.resolve()), 'Reference path escapes taskwork')
    context = extract_context(path, US_SOURCE, 'US')
    pairs = {}
    for region, folder in (('US', WORK/'independent-parser/s2mh-headers'),
                           ('EU', WORK/'eu-replay-search-20261018/base-headers-private')):
        for path in folder.glob('*.s2mh'):
            raw = _read(path, HEADER_LIMIT)
            header = decode_verified_header(raw, path.stem)[0]
            key = (header[1], header[2][8:])
            require(region not in pairs.setdefault(key, {}), 'Duplicate role/payload header')
            pairs[key][region] = (path.stem, raw, header)
    require(len(pairs) == 3 and {key[0] for key in pairs} == set(ROLES) and
            all(set(pair) == {'EU', 'US'} for pair in pairs.values()), 'Expected3exactrole/payload pairs')
    rows = []
    for (role, payload), pair in sorted(pairs.items()):
        target_sha, known_us_raw, known_us = pair['US']
        other_us = [p['US'][2] for key, p in pairs.items() if key != (role, payload)]
        offsets = {h[3]-h[0][0] for h in other_us}
        require(len(other_us) == 2 and len(offsets) == 1, 'Twoheldout namespace witnesses disagree')
        namespace_offset = next(iter(offsets))
        indices = [i for i, handle in enumerate(context.prefix) if handle[8:] == payload]
        require(len(indices) == 1, 'ObservedUSpayload not unique')
        index = indices[0]
        body = candidate_from_eu(pair['EU'][1], context, index, namespace_offset)
        require(sha(body) == target_sha and body == known_us_raw, 'WholeknownUSheader control failed')
        decoded = decode_verified_header(body, target_sha)
        require(decoded[0][0] == {0: context.entries[index]['identity'][0],
                                 1: context.entries[index]['identity'][1]}, 'Acceptedcontrol identity differs')
        wrong_trials = sum(h[0][0]+namespace_offset != known_us[3] for h in other_us)
        require(wrong_trials == 2, 'Wrongmodule namespace control failed')
        rows.append({'role': role.decode('utf8'), 'EU_source_sha256': pair['EU'][0],
                     'US_target_sha256': target_sha, 'bytes': len(body),
                     'namespace_offset_derived_from_other_two_US_modules_only': True,
                     'target_namespace_not_used_in_candidate_construction': True,
                     'whole_known_US_header_sha256_and_bytes_exact': True,
                     'complete_independent_generic_decode': True,
                     'wrong_module_negative_trials': wrong_trials})
    return {'format': 'hots-known-three-EU-to-US-whole-header-controls-v1',
            'producer_sha256': sha(_read(Path(__file__), 1024*1024)),
            'source_US_replay_sha256': context.replay_sha256,
            'source_US_member_sha256': context.member_sha256,
            'control_count': len(rows), 'all3_whole_known_US_objects_reproduced_exactly': True,
            'controls': rows, 'missing_US_HeroesData_attempted': False,
            'candidate_bodies_written_or_emitted': False,
            'namespace_or_publisher_literals_emitted': False,
            'new_network_requests': 0, 'client_launched': False, 'replay_modified': False,
            'limits': ['Threewholeobjects validate this specific observedregionalrecipe on knowncontrols only.',
                       'OnlythefullactualadvertisedUStargetSHAcanauthenticateanyseparatelyreviewedmissingheaderattempt.',
                       'No timestamp, creator, signature or availability semantics inferred.']}


if __name__ == '__main__':
    report = run_controls()
    output = HERE/'three-known-regional-whole-header-controls.json'
    write_new_report(report, output)
    print(json.dumps({'controls': report['control_count'],
                      'report_sha256': sha(_read(output, 1024*1024))}))
