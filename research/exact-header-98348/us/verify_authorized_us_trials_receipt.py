"""Read-only verification of the frozen, already completed three US trials.

This verifier does not construct any candidate or write any header body.
"""
from pathlib import Path
import hashlib
import json

from collection_license_audit import _read, write_new_report
from depot_s2mh_wire import decode_verified_header
from lossless_wire import parse, encode, to_generic
from regional_header_controls import extract_context, US_SOURCE, HEADER_LIMIT

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
PINS = {
    'attempt_exact_us_headers.py': '1c00b6b3d6d0d3a9c6102dc9f3bd99db507ade62c3dd1d6aed9498e0e1085231',
    'regional_header_controls.py': '7cf886a8fdf8cbaad8c69dda116798a3e6caef1f3b90342b7d0a5eb7e422a6cd',
    'three-known-regional-whole-header-controls.json': 'db95fd9e2e932c302e2eb282162d57af12f997d426b1f890213b1b948cbf9c95',
    'authorized-three-US-header-trials.json': '3902c1fd08d11deacba24742128412aa9135575c4a9898c9e8b9a6cd1ac9c73c',
}
EXPECTED = (
    ('0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a', 222049, (243553, 65665)),
    ('42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a', 1660, (280539, 16)),
    ('3c2d7d5c17b8a5351c03d7bfb40159ca158694176b81d51bbd1d12abadc2e429', 4057, (243571, 65624)),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('Frozen trial verification failed')


def verify():
    for name, digest in PINS.items():
        require(sha(_read(HERE/name, 1024*1024)) == digest)
    report = json.loads(_read(HERE/'authorized-three-US-header-trials.json', 1024*1024))
    manifest = json.loads(_read(WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json', 4*1024*1024))
    refs = [row for row in manifest['references'] if row['replay_sha256'] == US_SOURCE]
    require(len(refs) == 1)
    replay = (WORK/refs[0]['replay_file']).resolve()
    require(replay.is_relative_to(WORK.resolve()))
    context = extract_context(replay, US_SOURCE, 'US')
    require(report['actual_US_replay_sha256'] == context.replay_sha256)
    require(report['actual_US_member_sha256'] == context.member_sha256)
    require(report['actual_trials'] == 3 and report['exact_missing_objects_recovered'] == 2)
    require(len(report['results']) == 3)
    rows = []
    for index, ((target, size, identity), entry) in enumerate(zip(EXPECTED, report['results'])):
        require(entry['trial'] == index+1 and entry['target_sha256'] == target and entry['bytes'] == size)
        package_indices = [i for i, handle in enumerate(context.terminal) if handle[8:].hex() == target]
        require(len(package_indices) == 1)
        package_index = package_indices[0]
        actual_handle = context.terminal[package_index]
        require(actual_handle[:4] == b's2mh' and actual_handle[4:8].strip(b'\0 ') == b'US')
        require(context.entries[package_index]['identity'] == identity)
        if index == 1:
            require(entry['candidate_sha256'] == 'bcbacce6174dac21f9c289f4dd6a7e6b40873c15cc96c3624a37204c4793aa67')
            require(not entry['candidate_body_saved'] and not entry['matches_actual_advertised_full_SHA256'])
            require(not (HERE/'recovered-headers-private'/(target+'.s2mh')).exists())
            require(not (HERE/'recovered-headers-private'/(entry['candidate_sha256']+'.s2mh')).exists())
            rows.append({'target_sha256': target, 'actual_package_id_version': list(identity),
                         'status': 'mismatch recorded; no target or candidate file present'})
            continue
        raw = _read(HERE/'recovered-headers-private'/(target+'.s2mh'), HEADER_LIMIT)
        require(len(raw) == size and sha(raw) == target)
        generic = decode_verified_header(raw, target)
        node = parse(raw)
        require(encode(node) == raw and to_generic(node) == generic)
        require(generic[0][0] == {0: identity[0], 1: identity[1]})
        require(generic[0][2] == context.prefix[package_index])
        require(entry['candidate_body_saved'] and entry['matches_actual_advertised_full_SHA256'])
        rows.append({'target_sha256': target, 'bytes': len(raw), 'actual_package_id_version': list(identity),
                     'full_SHA256_and_EOF_verified': True, 'lossless_reencoding_exact': True,
                     'actual_replay_terminal_and_payload_binding': True})
    for name, digest in PINS.items():
        require(sha(_read(HERE/name, 1024*1024)) == digest)
    require(sha(_read(replay, 5*1024*1024)) == US_SOURCE)
    return {'format': 'hots-authorized-three-US-trials-frozen-receipt-v1',
            'reviewer_source_sha256': sha(_read(Path(__file__), 1024*1024)), 'frozen_inputs': PINS,
            'actual_US_replay_sha256': US_SOURCE, 'fresh_actual_US_build_base_data': [98348]*3,
            'fresh_actual_US_region': 'US', 'rows': rows, 'accepted_header_count': 2,
            'producer_or_source_inputs_changed': False, 'new_candidates_constructed_by_verifier': 0,
            'header_bodies_written_by_verifier': 0, 'network_requests': 0, 'client_launched': False,
            'private_player_namespace_or_creator_literals_emitted': False,
            'limit': 'Exact static package objects; no replay conversion or playback claim.'}


if __name__ == '__main__':
    result = verify()
    output = HERE/'authorized-three-US-trials-frozen-verification.json'
    write_new_report(result, output)
    print(json.dumps({'accepted_headers': result['accepted_header_count'], 'report_sha256': sha(_read(output, 1024*1024))}))
