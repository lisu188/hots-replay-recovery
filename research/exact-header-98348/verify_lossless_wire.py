"""Hash-bound36-header research verification; no decoded field values exported."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from collection_license_audit import _read, write_new_report
from depot_s2mh_wire import decode_verified_header
from lossless_wire import Node, parse, encode, clone, to_generic

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CACHE = Path(r'C:\ProgramData\Blizzard Entertainment\Battle.net\Cache')
MAX_AGGREGATE_BYTES = 16*1024*1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def metrics(root):
    stack, counts, maximum = [(root, 0)], Counter(), 0
    while stack:
        node, depth = stack.pop()
        assert type(node) is Node
        counts[node.tag] += 1
        maximum = max(maximum, depth)
        children = []
        if node.tag == 0:
            children = node.value
        elif node.tag == 5:
            children = [value for _, value in node.value]
        elif node.tag == 3:
            children = [node.value[1]]
        elif node.tag == 4 and node.value is not None:
            children = [node.value]
        stack.extend((child, depth+1) for child in children)
    return {'nodes': sum(counts.values()), 'maximum_depth': maximum,
            'tag_node_counts': dict(sorted(counts.items()))}


def verify():
    scan_raw = _read(WORK/'cached-s2mh-identity-scan-20261018.json', 1024*1024)
    if sha(scan_raw) != '20e9af06a9fb2fe63ec06c1426ae5a79661731f0baa6145d4060f3908f5b3120':
        raise ValueError('Existing header inventory differs')
    scan = json.loads(scan_raw)
    old_paths = sorted((WORK/'depot-headers/original-eu').glob('*.s2mh'))
    cached_paths = [CACHE/row['header_sha256'][:2]/row['header_sha256'][2:4]/
                    (row['header_sha256']+'.s2mh') for row in scan['matching_archive_digest']]
    current_paths = sorted((WORK/'independent-parser/s2mh-headers').glob('*.s2mh'))
    expected_current = {'3392997d3afe27a33371b58cfaff37af5b67bda09ee9131e52bae0a0c80b2b76',
                        '82cf19ac9ceb903631db0994023efba040a1ccfbb0e920033a742d62cb65a77b',
                        '4b6fdc8eccc9eca107f7c6e5eae6c7c604e718ded019f4f4110a92300b54313f'}
    if len(old_paths) != 5 or len(cached_paths) != 28 or {p.stem for p in current_paths} != expected_current:
        raise ValueError('Expected5old+28cached+3current exact-header controls')
    cases = ([(p, 'original-eu') for p in old_paths] +
             [(p, 'cache-payload-match-candidate') for p in cached_paths] +
             [(p, 'current-us-authenticated-content-handle') for p in current_paths])
    if len({p.stem for p, _ in cases}) != 36:
        raise ValueError('Header control hashes must be36distinct')
    rows, total = [], 0
    for path, scope in cases:
        raw = _read(path, 2*1024*1024)
        total += len(raw)
        if total > MAX_AGGREGATE_BYTES:
            raise ValueError('Header verification aggregate read cap exceeded')
        generic = decode_verified_header(raw, path.stem)
        node = parse(raw)
        if encode(node) != raw or encode(clone(node)) != raw:
            raise ValueError('Lossless header roundtrip changed bytes')
        if to_generic(node) != generic:
            raise ValueError('Lossless and existing generic decoders disagree')
        if sha(_read(path, 2*1024*1024)) != path.stem:
            raise ValueError('Header changed during verification')
        rows.append({'header_sha256': path.stem, 'source_scope': scope, 'bytes': len(raw),
                     'complete_original_and_cloned_roundtrip_byte_exact': True,
                     'decoded_values_equal_existing_generic_decoder': True,
                     **metrics(node)})
    return {'format': 'hots-lossless-versioned-wire36-header-verification-v1',
            'producer_sha256': sha(_read(HERE/'lossless_wire.py', 1024*1024)),
            'verifier_sha256': sha(_read(Path(__file__), 1024*1024)),
            'cache_inventory_sha256': sha(scan_raw), 'header_count': len(rows),
            'aggregate_header_bytes': total, 'headers': rows,
            'new_network_requests': 0, 'client_launched': False,
            'raw_headers_or_decoded_private_fields_emitted': False,
            'candidate_reconstruction_or_target_digest_match_claimed': False,
            'limitations': ['Lossless codec verification proves byte preservation on these36controls only.',
                            'Cached payload-matching EU headers remain candidates, not98348bindings.',
                            'No unknown timestamp/signature/default semantics inferred, metadata replacement or replay written.']}


if __name__ == '__main__':
    report = verify()
    output = HERE/'lossless-wire36-control-verification.json'
    write_new_report(report, output)
    print(json.dumps({'header_count': report['header_count'],
                      'bytes': report['aggregate_header_bytes'],
                      'report_sha256': sha(_read(output, 1024*1024))}))
