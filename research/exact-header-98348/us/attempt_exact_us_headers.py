"""At most three expressly authorized RAM trials; save only full advertised SHA.

The latter two trials are permitted only after exact US HeroesData success.
There is no recipe retry, brute force, network request, replay edit or cloud I/O.
"""
from pathlib import Path
import hashlib
import json

from collection_license_audit import _read, write_new_report
from lossless_wire import parse, to_generic
from depot_s2mh_wire import decode_verified_header
from recover_current_eu_heroesdata_header import save_exact_header
from regional_header_controls import (extract_context, candidate_from_eu,
                                      US_SOURCE, ROLES, HEADER_LIMIT)

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
CACHE = Path(r'C:\ProgramData\Blizzard Entertainment\Battle.net\Cache')
CONTROL_SHA = 'db95fd9e2e932c302e2eb282162d57af12f997d426b1f890213b1b948cbf9c95'
PRODUCER_SHA = '7cf886a8fdf8cbaad8c69dda116798a3e6caef1f3b90342b7d0a5eb7e422a6cd'
TRIALS = (
    ('HeroesData', 'f644ce88b9d1a1c15af40be380be285f3d2ffcaf901dc9c15da367e763ee75c0',
     '0633db0bcff394a95e6d3e62a54190c2c33ee6c39af555a5d6268ac6e26c936a', True),
    ('Dragon-module', '33a1c5c9cd0e3d808c2a942c392fa2b5cc7077457bdbe62adad158b86ef8a4fd',
     '42afeaf8be79bff738e3387c15261b2c71474a63618ecfe8d38f5beb2985b57a', False),
    ('Dragon-map', 'f4103504b365e00dd873b171be164b9e3736c29fd3ded08c794ca4df84f44a41',
     '3c2d7d5c17b8a5351c03d7bfb40159ca158694176b81d51bbd1d12abadc2e429', False),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def execute():
    producer_raw = _read(HERE/'regional_header_controls.py', 1024*1024)
    control_raw = _read(HERE/'three-known-regional-whole-header-controls.json', 1024*1024)
    require(sha(producer_raw) == PRODUCER_SHA and sha(control_raw) == CONTROL_SHA,
            'Frozen whole-header control producer/report differs')
    controls = json.loads(control_raw)
    require(controls['control_count'] == 3 and controls['all3_whole_known_US_objects_reproduced_exactly'] and
            all(row['whole_known_US_header_sha256_and_bytes_exact'] and
                row['namespace_offset_derived_from_other_two_US_modules_only']
                for row in controls['controls']), 'Three exact whole controls are required')
    manifest = json.loads(_read(WORK/'reference-donors/ngs-expanded-reference-catalog-comparison-20261018.json', 4*1024*1024))
    refs = [row for row in manifest['references'] if row['replay_sha256'] == US_SOURCE]
    require(len(refs) == 1, 'Pinned actualUSreference is not unique')
    reference = (WORK/refs[0]['replay_file']).resolve()
    require(reference.is_relative_to(WORK.resolve()), 'Replay path escapes taskwork')
    context = extract_context(reference, US_SOURCE, 'US')
    offsets, control_inputs = set(), []
    for path in (WORK/'independent-parser/s2mh-headers').glob('*.s2mh'):
        data = _read(path, HEADER_LIMIT)
        h = decode_verified_header(data, path.stem)[0]
        require(h[1] in ROLES and h[2][4:8].strip(b'\0 ') == b'US', 'KnownUSrole source differs')
        offsets.add(h[3]-h[0][0])
        control_inputs.append({'sha256': path.stem, 'bytes': len(data), 'role': h[1].decode('utf8')})
    require(len(control_inputs) == 3 and len(offsets) == 1, 'Three observed namespace witnesses disagree')
    offset = next(iter(offsets))
    inputs, results = [], []
    for ordinal, (role, source_sha, target_sha, recovered) in enumerate(TRIALS, 1):
        if ordinal > 1 and not results[0]['matches_actual_advertised_full_SHA256']:
            break
        source_path = (HERE/'recovered-headers-private'/(source_sha+'.s2mh') if recovered else
                       CACHE/source_sha[:2]/source_sha[2:4]/(source_sha+'.s2mh'))
        source_raw = _read(source_path, HEADER_LIMIT)
        source_header = decode_verified_header(source_raw, source_sha)[0]
        indices = [i for i, handle in enumerate(context.prefix) if handle[8:] == source_header[2][8:]]
        require(len(indices) == 1, 'EU payload does not identify one actualUSpackage')
        index = indices[0]
        actual_handle = context.terminal[index]
        require(actual_handle[:4] == b's2mh' and actual_handle[4:8].strip(b'\0 ') == b'US' and
                actual_handle[8:].hex() == target_sha, 'Actual advertisedUStarget differs')
        if ordinal == 1:
            require(context.entries[index]['identity'] == (243553, 65665), 'ExpectedUSHDpackage differs')
        inputs.append({'role': role, 'source_header_sha256': source_sha, 'source_bytes': len(source_raw),
                       'actual_target_handle_sha256': target_sha,
                       'actual_target_package_id_version': list(context.entries[index]['identity'])})
        row = {'trial': ordinal, 'role': role, 'target_sha256': target_sha,
               'source_header_sha256': source_sha, 'maximum_recipe_attempts': 1,
               'candidate_body_saved': False, 'candidate_body_emitted': False,
               'matches_actual_advertised_full_SHA256': False}
        try:
            body = candidate_from_eu(source_raw, context, index, offset)
        except ValueError as error:
            row.update(status='strict-source-shape-or-payload-guard-refusal', error_type=type(error).__name__)
            results.append(row)
            break
        digest = sha(body)
        matched = digest == target_sha
        row.update(status='exact-target-recovered' if matched else 'whole-target-hash-mismatch',
                   bytes=len(body), candidate_sha256=digest,
                   matches_actual_advertised_full_SHA256=matched)
        if matched:
            decoded = decode_verified_header(body, target_sha)
            identity = context.entries[index]['identity']
            require(decoded[0][0] == {0: identity[0], 1: identity[1]} and
                    decoded[0][2] == context.prefix[index] and
                    decoded == to_generic(parse(body)), 'Independent complete-header postcondition failed')
            output = HERE/'recovered-headers-private'/(target_sha+'.s2mh')
            require(save_exact_header(body, output, target_sha), 'Exact-only exclusive save failed')
            require(_read(output, HEADER_LIMIT) == body, 'Saved exact body differs')
            row.update(candidate_body_saved=True, accepted_private_file='recovered-headers-private/'+output.name,
                       independent_generic_complete_EOF=True, independent_package_identity_verified=True)
        results.append(row)
        require(sha(_read(source_path, HEADER_LIMIT)) == source_sha, 'Source header changed')
        print(json.dumps({k: row.get(k) for k in ('trial', 'role', 'status', 'bytes', 'candidate_sha256',
                                                'matches_actual_advertised_full_SHA256')}), flush=True)
        del body
    require(sha(_read(reference, 5*1024*1024)) == US_SOURCE and
            sha(_read(HERE/'regional_header_controls.py', 1024*1024)) == PRODUCER_SHA,
            'Source replay or producer changed')
    return {'format': 'hots-authorized-at-most-three-exact-US-header-trials-v1',
            'producer_sha256': sha(_read(Path(__file__), 1024*1024)),
            'regional_recipe_source_sha256': PRODUCER_SHA,
            'three_full_control_report_sha256': CONTROL_SHA,
            'actual_US_replay_sha256': context.replay_sha256,
            'actual_US_member_sha256': context.member_sha256,
            'namespace_control_inputs': control_inputs, 'trial_source_and_actual_target_inputs': inputs,
            'maximum_trials': 3, 'trials_per_target': 1,
            'latter_two_conditioned_on_exact_US_HD_success': True,
            'actual_trials': len(results), 'results': results,
            'exact_missing_objects_recovered': sum(row['matches_actual_advertised_full_SHA256'] for row in results),
            'all_source_inputs_unchanged': True,
            'mismatching_bodies_saved': False, 'raw_bodies_publishable': False,
            'namespace_creator_or_player_literals_emitted': False,
            'new_network_requests': 0, 'client_launched': False, 'replay_modified': False,
            'limits': ['OnlycompleteactualadvertisedfullSHA256acceptsanobject; mismatchesarenotsaved.',
                       'Rawheadersremainprivate; noclouduploadispartofthisexperiment.',
                       'Exactstaticobjectrecoveryisnotareplayconversionorplaybackproof.']}


if __name__ == '__main__':
    report = execute()
    output = HERE/'authorized-three-US-header-trials.json'
    write_new_report(report, output)
    print(json.dumps({'report_sha256': sha(_read(output, 1024*1024)),
                      'actual_trials': report['actual_trials'],
                      'exact_recovered': report['exact_missing_objects_recovered']}))
