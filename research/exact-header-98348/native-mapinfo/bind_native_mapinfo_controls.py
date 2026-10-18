"""Bind the pinned portable native MapInfo reader to all 21 existing controls.

No acquisition, replay creation or client execution. Private values stay in RAM.
Counted MPQ/cohort reads and explicit native pin reads share a bounded budget.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parent
REPO = Path('C:/Users/andrz/git/hots-replay-recovery')
sys.path[:0] = [str(HERE), str(REPO), str(WORK/'heroprotocol'), str(WORK/'python-deps'),
    str(WORK/'availability-vector-expanded-ready'), str(WORK/'availability-vector-ready'),
    str(WORK/'availability-representation-ready')]
import native_mapinfo as native
import audit_expanded_account_vectors as cohort
from audit_battlelobby_mod_metadata import audit_member
from battlelobby_tail import crosscheck, decode_tail
from protocol_loader import load_protocol

sha = lambda raw: hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def analyze():
    budget = cohort.Budget()
    runtime = {}
    for name in ('native_mapinfo', 'native_clientinfo', 'audit_expanded_account_vectors',
                 'audit_repeated_account_vectors', 'audit_availability_representation',
                 'battlelobby_tail', 'battlelobby_attribute_layer', 'audit_battlelobby_mod_metadata',
                 'protocol_loader', 'mpq_reader', 'collection_license_audit'):
        path = Path(sys.modules[name].__file__)
        runtime[name] = (path, sha(budget.read(path, 1024*1024, 'runtime_source_guards')))
    require(runtime['audit_expanded_account_vectors'][1] == '2f020152115324ef7e309807a9d988bc65b62eb8dcf6e8077988b29cdd2dd9ca', 'Cohort loader differs')
    require(runtime['audit_repeated_account_vectors'][1] == cohort.PRIOR_SHA, 'Prior cohort helper differs')
    require(runtime['audit_availability_representation'][1] == cohort.prior.BASE_HELPER_SHA, 'Baseline helper differs')
    require(runtime['native_clientinfo'][1] == native.SHARED_DECODER_SHA256, 'Shared decoder differs')
    specs, legacy, sources = cohort.load_specs(budget)
    protocol = load_protocol(96477)
    require(protocol.recovery_schema_sha256 == cohort.previous.SCHEMA_CURRENT, 'Official identity schema differs')
    guards = []
    for _, path, expected, _ in legacy:
        raw = budget.read(path, cohort.previous.REPLAY_LIMIT, 'guard_rehash_reads')
        budget.register(path, len(raw))
        require(sha(raw) == expected, 'Original/R8 source differs')
        guards.append((path, expected))
    # Instrument file reads only: delegate every validation and decode unchanged.
    pinned_file = native._pinned_file
    def counted_pin(path, limit, expected):
        budget.reserve(limit + 1)
        raw = pinned_file(path, limit, expected)
        budget.add('native_schema_and_shared_source_pin_reads', len(raw))
        return raw
    native._pinned_file = counted_pin
    cases = []
    widths = Counter()
    permissions = Counter()
    record_total = 0
    selected_bytes = 0
    try:
        for spec in specs:
            source = budget.read(spec['path'], cohort.previous.REPLAY_LIMIT, 'guard_rehash_reads')
            budget.register(spec['path'], len(source))
            require(sha(source) == spec['sha'], 'Current source differs')
            guards.append((spec['path'], spec['sha']))
            profile_raw, _ = cohort.profile_checked(spec['profile'], spec['profile_sha'], spec['sha'], budget)
            archive = cohort.CountedArchive(spec['path'], budget)
            try:
                header = protocol.decode_replay_header(archive.header['user_data_header']['content'])
                require(header['m_version']['m_build'] == 98348 and header['m_version']['m_baseBuild'] == 98348
                    and header['m_dataBuildNum'] == 98348
                    and header['m_ngdpRootKey']['m_data'].hex() == cohort.ROOT, 'Actual header target differs')
                raw = cohort.previous.bounded_member(archive, 'replay.server.battlelobby')
                details_raw = cohort.previous.bounded_member(archive, 'replay.details')
                init_raw = cohort.previous.bounded_member(archive, 'replay.initData')
                mods = audit_member(raw, 'observed-11', 'current-observed')
                tail = decode_tail(raw, mods['terminal_handles_end_bit'], 'current-tail')
                checks = crosscheck(tail, protocol.decode_replay_details(details_raw), protocol.decode_replay_initdata(init_raw))
                require(checks['all_details_participants_match_tail_by_slot'] and checks['initdata_identity_multiset_equal']
                    and checks['initdata_identity_and_slot_matches'] == checks['players_checked']
                    and checks['seed_matches_lobby'] and checks['seed_matches_game_description']
                    and checks['disabled_hero_list_equal'] is not False, 'Private identity/seed crosschecks differ')
                binding = native.audit_current_map_infos(raw, mods)
                record_total += binding['records_checked']
                for row in binding['last_two_field_width_histogram']:
                    widths[tuple(row['widths'])] += row['records']
                for count, occurrences in binding['required_permission_count_histogram'].items():
                    permissions[count] += occurrences
                selected_bytes += len(raw) + len(details_raw) + len(init_raw)
                cases.append({'id': spec['id'], 'replay_sha256': spec['sha'], 'profile_sha256': sha(profile_raw),
                    'member_sha256': sha(raw), 'actual_build_base_data': 98348, 'actual_root': cohort.ROOT,
                    'prior_core_roundtrip_profile_hash_bound': True, 'fresh_core_event_decode_performed': False,
                    'full_current_mod_tail_EOF_and_private_crosschecks_passed': True, 'native_map_info': binding})
            finally:
                archive.close()
    finally:
        native._pinned_file = pinned_file
    require(len(cases) == 21, 'Complete 21-case cohort required')
    for path, expected in guards:
        require(sha(budget.read(path, cohort.previous.REPLAY_LIMIT, 'guard_rehash_reads')) == expected, 'Source changed after audit')
    for path, expected in runtime.values():
        require(sha(budget.read(path, 1024*1024, 'runtime_source_guards')) == expected, 'Runtime source changed')
    producer_sha = sha(budget.read(Path(__file__), 64*1024, 'producer_source_guard'))
    return {'format': 'hots-native-mapinfo-21case-binding-v1', 'producer_sha256': producer_sha,
        'portable_module_sha256': runtime['native_mapinfo'][1], 'schema_sha256': native.SCHEMA_SHA256,
        'shared_decoder_sha256': native.SHARED_DECODER_SHA256, 'source_PE_sha256': native.SOURCE_PE_SHA256,
        'source_embedded_bytecode_sha256': native.SOURCE_BYTECODE_SHA256,
        'source_manifests': sources, 'canonical_identity_schema_sha256': cohort.previous.SCHEMA_CURRENT,
        'runtime_source_sha256s': {name: value[1] for name, value in sorted(runtime.items())},
        'current_cases': len(cases), 'source_or_decode_failures': 0, 'new_acquisition_attempts': 0, 'cases': cases,
        'aggregate': {'native_MapInfo_records': record_total, 'named_root_fields_per_record': 32,
            'all_native_ends_identities_and_consumed_spans_exact': True,
            'last_two_field_width_histogram': [{'widths': list(width), 'records': count} for width, count in sorted(widths.items())],
            'required_permission_count_histogram': dict(sorted(permissions.items()))},
        'actual_reads': {'distinct_replay_bytes_including_original_R8': sum(budget.distinct.values()),
            'distinct_replay_files': len(budget.distinct), 'explicit_analysis_input_bytes': sum(budget.counts.values()),
            'read_categories': dict(budget.counts), 'selected_decoded_member_bytes': selected_bytes,
            'accounting_scope': 'Explicit provenance/profile/guard/runtime source/native pin reads and MPQ reads; implicit interpreter/import reads excluded.',
            'PE_reads_in_this_stage': 0},
        'all_current_and_original_R8_source_hashes_unchanged': True,
        'private_author_address_player_or_header_values_emitted': False,
        'client_launched': False, 'network_used': False, 'replay_or_header_written': False,
        'full_replay_upgrade_complete': False,
        'limits': ['The selected current native graph binds 32 MapInfo fields to consumed spans in genuine current controls.',
            'Source-bound observed mod parsing and independent current tail EOF/private crosschecks passed; prior core profiles were hash-bound without re-decoding core events.',
            'No missing namespace, package reconstruction, legacy MapInfo conversion or deterministic simulation compatibility follows.']}


if __name__ == '__main__':
    target = HERE/'native-mapinfo-21case-binding.json'
    require(not target.exists(), 'Refuse replacing an existing observation')
    raw = (json.dumps(analyze(), sort_keys=True, indent=2) + '\n').encode()
    require(len(raw) <= 128*1024, 'Observation exceeds cap')
    with target.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'bytes': len(raw), 'sha256': sha(raw)}))
