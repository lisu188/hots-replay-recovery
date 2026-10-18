"""Read-only independent review runner for the two frozen vector audits.

Producer reports are read and compared as JSON; neither report is overwritten.
The only output is a new aggregate review receipt, never a vector or account.
"""
from pathlib import Path
import hashlib
import json
from math import factorial, prod
import time
import unittest

import audit_repeated_account_vectors as thirteen
import audit_expanded_account_vectors as twenty_one
from collection_license_audit import _read, write_new_report

WORK = Path(__file__).resolve().parents[1]
PINS = {
    'availability-vector-ready/audit_repeated_account_vectors.py': '66fdf4a017ddaf0a8a2b816572a8bdaae6993e0f041632a7d19e3647cbada6ac',
    'availability-vector-ready/test_audit_repeated_account_vectors.py': '14802fa1ad76f8fc3edafe6ff893fcf2d6100abacec240cb1a8e0c4f0130a309',
    'availability-vector-ready/repeated-account-vector-comparison-13-cases-v2.json': '1b0203fe36da7e42e72d4de6062e0ae8cc8dbd745e6af1119d188b1546a83d75',
    'availability-vector-ready/repeated-account-vector-frozen-receipt.json': '2ae95af61a34ecee3f83d61962f2c7a6c0e4559ed0568d7cb1094698ecff6c05',
    'availability-vector-expanded-ready/audit_expanded_account_vectors.py': '2f020152115324ef7e309807a9d988bc65b62eb8dcf6e8077988b29cdd2dd9ca',
    'availability-vector-expanded-ready/test_audit_expanded_account_vectors.py': '1c232c528290812117fa215ccc3f061c5b1b973b25198e7e74eaaed6aa3bb3ca',
    'availability-vector-expanded-ready/expanded-vector-comparison-up-to21-cases.json': '647ce289f873e145fad72329ace453b56a52cc9f42ff1e35ae12c47c9fd9937f',
    'availability-vector-expanded-ready/expanded-vector-frozen-receipt.json': 'cfc588f7d607501120dd4ed5088d01dc3d1288327f5be3807418c05632ae559b',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition):
    if not condition:
        raise ValueError('Frozen vector audit independent verification failed')


def verify_pins():
    for relative, expected in PINS.items():
        require(sha(_read(WORK/relative, 1024*1024)) == expected)


def summary(comparison):
    presence = comparison['presence_constraint_aggregate']
    consistency = comparison['arrangement_consistency_aggregate']
    direct = comparison['direct_working_set_position_alignment']
    active = presence['distinct_active_arrangements_enumerated']
    never = presence['never_participant_permutations_not_enumerated']
    total = presence['all_compatible_position_bijections']
    require(active * never == total)
    require(prod(factorial(size) for size in presence['signature_group_sizes']) == total)
    require(sum(row['active_arrangement_count'] for row in consistency['histogram']) == active)
    require(presence['identity_active_arrangement_checked'])
    same = direct['same_account_across_replays']
    different = direct['different_accounts_across_replays']
    require(same['vector_pairs'] + different['vector_pairs'] == comparison['cross_replay_pairs_considered'])
    require(same['exact_vector_pairs'] + same['different_vector_pairs'] == same['vector_pairs'])
    require(different['exact_vector_pairs'] + different['different_vector_pairs'] == different['vector_pairs'])
    return {'cases': comparison['control_cases'], 'presence_bijections': total,
            'active_arrangements_exhaustively_checked': active,
            'never_participant_permutations_counted_separately': never,
            'same_account_pairs': same['vector_pairs'], 'same_account_exact_pairs': same['exact_vector_pairs'],
            'different_account_pairs': different['vector_pairs'], 'different_account_exact_pairs': different['exact_vector_pairs'],
            'maximum_same_account_exact_pairs': consistency['same_account_exact_vector_pairs_max'],
            'active_arrangements_attaining_maximum': consistency['active_arrangements_attaining_maximum_same_account_exact_pairs'],
            'identity_reaches_statistical_maximum': same['exact_vector_pairs'] == consistency['same_account_exact_vector_pairs_max']}


def verify():
    verify_pins()
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_audit_repeated_account_vectors', 'test_audit_expanded_account_vectors'])
    results = unittest.TextTestRunner(verbosity=1).run(suite)
    require(results.testsRun == 28 and results.wasSuccessful() and not results.skipped)
    recomputed = []
    for producer, name in (
        (thirteen, 'availability-vector-ready/repeated-account-vector-comparison-13-cases-v2.json'),
        (twenty_one, 'availability-vector-expanded-ready/expanded-vector-comparison-up-to21-cases.json')):
        saved = json.loads(_read(WORK/name, 1024*1024))
        started = time.monotonic()
        fresh = producer.analyze()
        require(fresh == saved)
        aggregate = summary(fresh['comparison'])
        aggregate.update(fresh_JSON_values_exactly_match_frozen_report=True,
                         elapsed_seconds=round(time.monotonic()-started, 3))
        if producer is twenty_one:
            require(fresh['admitted_current_controls'] == 21 and fresh['admitted_additional_controls'] == 8)
            require(fresh['existing_source_or_decode_failure_count'] == 0)
            require(fresh['frozen13_case_comparison_reproduced_exactly'])
            aggregate['input_read_accounting'] = fresh['actual_reads']
        recomputed.append(aggregate)
        print(json.dumps({'completed_cases': aggregate['cases'], 'JSON_exact': True,
                          'active_arrangements': aggregate['active_arrangements_exhaustively_checked']}), flush=True)
    require(recomputed[0]['presence_bijections'] == 5760)
    require(recomputed[0]['active_arrangements_exhaustively_checked'] == 2880)
    require(recomputed[0]['never_participant_permutations_counted_separately'] == 2)
    require(recomputed[1]['active_arrangements_exhaustively_checked'] == 240)
    require(recomputed[1]['active_arrangements_attaining_maximum'] == 1)
    require(recomputed[1]['identity_reaches_statistical_maximum'])
    verify_pins()
    return {'format': 'hots-frozen-vector-audits-independent-review-v1',
            'review_source_sha256': sha(_read(Path(__file__), 1024*1024)),
            'reviewed_input_pins': PINS, 'focused_tests_run': 28,
            'focused_test_failures_errors_or_skips': 0,
            'fresh_hash_bound_aggregate_recomputations': recomputed,
            'source_review': {
                'full_tail_EOF_and_same_profile_roundtrip_gates': True,
                'private_details_initdata_tail_identity_position_and_seed_gates': True,
                'same_ordered_5418_registry_required': True,
                'canonical_protocol_SHA_required': True,
                'thirteen_case_context_uses_existing_hash_pinned_provenance': True,
                'twenty_one_case_fresh_build_base_data_root_and_bound_core_profile_gates': True,
                'all_active_presence_arrangements_exhaustively_checked_without_truncation': True,
                'exact_bytes_used_for_private_vector_equality': True,
                'no_private_vector_values_hashes_account_keys_slots_signatures_or_permutations_emitted': True,
                'no_semantic_mapping_or_ownership_adopted': True,
                'no_material_findings_in_reviewed_actual_input_scope': True},
            'frozen_sources_and_reports_unchanged': True,
            'network_requests': 0, 'client_launched': False,
            'replay_header_or_member_written': False, 'repo_modified': False,
            'limits': [
                'Fresh computations reproduce the reviewed producers; they are not an independent ownership model.',
                'The 13-case producer binds existing current context through pinned replay/manifests; the 21-case extension additionally checks fresh actual header build/base/data/root and bound prior core profiles.',
                'Unique statistical maximum at identity is an observed correlation; no participant-to-cell semantic mapping, entitlement or migration rule is selected.',
                'Runtime executable/import filesystem reads are outside the declared explicit analysis-input accounting scope.']}


if __name__ == '__main__':
    report = verify()
    output = Path(__file__).with_name('availability-vector-independent-review.json')
    write_new_report(report, output)
    print(json.dumps({'review_receipt_sha256': sha(_read(output, 1024*1024)),
                      'focused_tests': report['focused_tests_run'], 'fresh_actual_cases': [13, 21]}))
