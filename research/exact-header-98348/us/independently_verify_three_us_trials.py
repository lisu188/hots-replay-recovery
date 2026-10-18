"""Independent read-only repeat of the three exhausted US header trials.

No wrapper entry point, save function, network operation, or header write runs.
Only the final allowlisted review receipt is created exclusively.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0] = [str(REPO), str(HERE), str(WORK/'heroprotocol'), str(WORK/'python-deps')]

from collection_license_audit import _read, write_new_report
from regional_header_controls import extract_context, candidate_from_eu, run_controls
from depot_s2mh_wire import decode_verified_header
from lossless_wire import parse, to_generic
from reference_replay import inspect_reference, checked_archive
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_attribute_layer import _Reader

sha = lambda raw: hashlib.sha256(raw).hexdigest()
PRIVATE = HERE/'recovered-headers-private'
CACHE = Path('C:/ProgramData/Blizzard Entertainment/Battle.net/Cache')
SOURCE = WORK/'reference-donors/ngs-20261016-protectors-dragon.StormReplay'
SOURCE_SHA = '882f4895651799f7cc42c6b48dd4452f33408a147e6bc9c15c142e36ad77e21c'
PINS = {
    'attempt_exact_us_headers.py': '1c00b6b3d6d0d3a9c6102dc9f3bd99db507ade62c3dd1d6aed9498e0e1085231',
    'regional_header_controls.py': '7cf886a8fdf8cbaad8c69dda116798a3e6caef1f3b90342b7d0a5eb7e422a6cd',
    'authorized-three-US-header-trials.json': '3902c1fd08d11deacba24742128412aa9135575c4a9898c9e8b9a6cd1ac9c73c',
    'three-known-regional-whole-header-controls.json': 'db95fd9e2e932c302e2eb282162d57af12f997d426b1f890213b1b948cbf9c95',
    'namespace-and-source-exposure-independent-review.json': 'dd44a08d9fcb4517c6bb50f66d9f89b1ed08d81c6255d80819c253d8e8561861',
    'recover_current_eu_heroesdata_header.py': '080615308fd50f4015b8ee0e562a79240b64dc6b0d9cc1d51923d4fc953676f9',
    'lossless_wire.py': '9d725f9be88c4185419a306ef995e82a774d174a93912ffd381cced2d6ebb7a7',
}
TRIALS = (
    ('HeroesData', 'f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0',
     '0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a',
     (243553, 65665), 222049, True),
    ('Dragon-module', '33a1c5c9cd0e3d808c2a942c392fa2b5cc7077457bdbe62adad158b86ef8a4fd',
     '42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a',
     (280539, 16), 1660, False),
    ('Dragon-map', 'f4103504b365e00dd873b171be164b9e3736c29fd3ded08c794ca4df84f44a41',
     '3c2d7d5c17b8a5351c03d7bfb40159ca158694176b81d51bbd1d12abadc2e429',
     (243571, 65624), 4057, True),
)

def snapshot():
    return {p.name: sha(_read(p, 512*1024)) for p in PRIVATE.glob('*.s2mh')}

def main():
    for filename, expected in PINS.items():
        assert sha(_read(HERE/filename, 1024*1024)) == expected
    before = snapshot()
    original_report = json.loads(_read(HERE/'authorized-three-US-header-trials.json', 1024*1024))
    assert sha(_read(SOURCE, 3*1024*1024)) == SOURCE_SHA
    # Fresh complete observed core: official/semantic agreement and exact encoding.
    profile = inspect_reference(SOURCE, 96477, 98348)
    assert profile['file_sha256'] == SOURCE_SHA and profile['observed_payload_roundtrip']
    assert profile['schema_file_sha256'] == 'e95b728028399e7ffcfd32dff5e0c5fa3077d3827837755ccf40da2efcedbc84'
    target = profile['target']
    assert target['m_version']['m_build'] == target['m_version']['m_baseBuild'] == target['m_dataBuildNum'] == 98348
    assert target['m_ngdpRootKey']['m_data'].hex() == 'c3b3c8bc82e3a5a62e550fdde9a40c28'
    context = extract_context(SOURCE, SOURCE_SHA, 'US')
    assert context.member_sha256 == 'ab03d9533081e9d69d205a6adec9df6a0aaf5ff47a05ecc8bf670b6760b0ab55'
    # Independent direct terminal reader verifies the actual package indices.
    archive = checked_archive(SOURCE)
    try:
        member = archive.read_file('replay.server.battlelobby')
    finally:
        archive.close()
    mods = audit_member(member, 'observed-11', 'current-observed')
    r = _Reader(member)
    r.position = mods['mod_metadata_end_bit']
    terminals = [r.blob(40) for _ in range(r.bits(6))]
    assert terminals == context.terminal and r.position == mods['terminal_handles_end_bit']
    actual_ids = []
    for entry in mods['entries']:
        r.position = entry['start_bit']
        actual_ids.append((r.bits(32), r.bits(32)))
    assert actual_ids == [entry['identity'] for entry in context.entries]
    controls = run_controls()
    assert controls['control_count'] == 3 and all(x['whole_known_US_header_sha256_and_bytes_exact'] for x in controls['controls'])
    offsets = set()
    known = []
    for path in (WORK/'independent-parser/s2mh-headers').glob('*.s2mh'):
        body = _read(path, 512*1024)
        h = decode_verified_header(body, path.stem)[0]
        offsets.add(h[3] - h[0][0])
        known.append(path.stem)
    assert len(known) == 3 and len(offsets) == 1
    offset = next(iter(offsets))
    rows = []
    for ordinal, (role, source_sha, expected, identity, size, matched) in enumerate(TRIALS, 1):
        source_path = PRIVATE/(source_sha+'.s2mh') if ordinal == 1 else CACHE/source_sha[:2]/source_sha[2:4]/(source_sha+'.s2mh')
        source_raw = _read(source_path, 512*1024)
        source = decode_verified_header(source_raw, source_sha)[0]
        indices = [i for i, handle in enumerate(context.prefix) if handle[8:] == source[2][8:]]
        assert len(indices) == 1
        index = indices[0]
        assert actual_ids[index] == identity and terminals[index][:8] == b's2mh\0\0US' and terminals[index][8:].hex() == expected
        body = candidate_from_eu(source_raw, context, index, offset)
        digest = sha(body)
        assert len(body) == size and (digest == expected) == matched
        previous = original_report['results'][ordinal-1]
        assert previous['candidate_sha256'] == digest and previous['matches_actual_advertised_full_SHA256'] == matched
        decoded = decode_verified_header(body, digest)
        assert decoded == to_generic(parse(body))
        h = decoded[0]
        assert h[0] == {0: identity[0], 1: identity[1]} and h[2] == context.prefix[index]
        assert h[4][7] == context.entries[index]['visuals'] and h[14] == context.entries[index]['dependencies']
        for locale_array in (h[8], h[4][8]):
            assert {row[0]: row[1][0] for row in locale_array} == context.entries[index]['locales']
        row = {'role': role, 'source_header_sha256': source_sha, 'actual_terminal_target_sha256': expected,
               'actual_package_id_version': list(identity), 'candidate_sha256': digest, 'bytes': len(body),
               'full_target_sha256_matches': matched, 'matches_frozen_trial_report': True,
               'actual_replay_terminal_and_metadata_bound': True, 'independent_complete_generic_EOF': True,
               'lossless_Node_agrees_with_independent_generic': True}
        if matched:
            saved = _read(PRIVATE/(expected+'.s2mh'), 512*1024)
            assert saved == body and sha(saved) == expected
            assert decode_verified_header(saved, expected) == decoded
            row['saved_private_file_byte_identical_and_full_SHA_verified'] = True
        else:
            assert not (PRIVATE/(expected+'.s2mh')).exists() and not (PRIVATE/(digest+'.s2mh')).exists()
            row['no_target_or_mismatching_candidate_digest_file_present'] = True
        rows.append(row)
        assert sha(_read(source_path, 512*1024)) == source_sha
        del body
    assert snapshot() == before
    for filename, expected in PINS.items():
        assert sha(_read(HERE/filename, 1024*1024)) == expected
    assert sha(_read(SOURCE, 3*1024*1024)) == SOURCE_SHA
    report = {'format': 'hots-three-US-header-trials-independent-review-v1', 'result': 'PASS',
              'reviewer_source_sha256': sha(_read(Path(__file__), 1024*1024)), 'reviewed_source_and_report_hashes': PINS,
              'source_replay_sha256': SOURCE_SHA, 'source_member_sha256': context.member_sha256,
              'fresh_core_observed_payload_roundtrip': True,
              'schema_build': 96477, 'schema_sha256': profile['schema_file_sha256'],
              'actual_build_base_data': 98348, 'actual_root': 'c3b3c8bc82e3a5a62e550fdde9a40c28',
              'core_streams': {kind: {key: values[key] for key in ('count','sha256','binary_roundtrip')} for kind, values in profile['streams'].items()},
              'fresh_whole_known_controls': 3, 'whole_known_controls_exact': True,
              'wrong_module_negative_trials': 6, 'trials_repeated_in_RAM': 3, 'results': rows,
              'exact_saved_objects_read_and_verified': 2, 'new_candidate_recipes_tried': 0,
              'wrapper_main_or_save_function_invoked_by_review': False, 'header_body_writes_by_review': 0,
              'private_header_inventory_unchanged_during_review': True,
              'source_guard_review': {'bounded_reads_and_candidates': True, 'actual_terminal_target_hard_pinned': True,
                                      'known_3_control_producer_and_report_hard_pinned': True,
                                      'later_two_conditioned_on_exact_HD_success': True,
                                      'one_recipe_per_each_of_three_targets': True,
                                      'full_SHA_and_independent_EOF_before_exclusive_private_save': True,
                                      'mismatch_not_written_by_reviewed_branch': True,
                                      'existing_output_refused': True},
              'namespace_creator_player_literals_emitted': False, 'network_requests': 0, 'client_launched': False,
              'replay_modified': False,
              'limitations': ['This verifies two specific complete static objects and one rejected hypothesis.',
                             'The Dragon-module target remains missing; its candidate body was not saved.',
                             'No general regional transformation or namespace ownership interpretation is established.',
                             'No replay conversion, simulation or playback acceptance follows from these checks.']}
    output = HERE/'three-US-header-trials-independent-review.json'
    write_new_report(report, output)
    print(json.dumps({'result': 'PASS', 'RAM_trials': 3, 'exact_objects': 2, 'negative_candidates_unwritten': 1,
                      'report_sha256': sha(_read(output, 1024*1024))}))

if __name__ == '__main__':
    main()
