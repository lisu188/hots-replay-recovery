"""Check exact historical reference fixtures; write sanitized evidence only.

The 41810 fixtures are exact-build controls. 42273 is a separate nearby control.
Admitted 41810 MapInfo framing and inverses run in RAM. No network request,
replay conversion, payload write, client launch or player data export.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

UPSTREAM_COMMIT = '9af3ea7150f1a8acb53464c92519a9bbcc7a3594'
CANONICAL_SCHEMA_SHA256 = '879d228d9d8acd21d63563538dd15841aaf49259ee0bb468b8a46b6a4ef866fd'
# These are exact raw-byte alternatives, not an arbitrary newline exemption.
SCHEMA_RAW_PINS = {
    (25890, CANONICAL_SCHEMA_SHA256): 'canonical-LF',
    (26364, 'a970f10719f29787c7ea25359a908a1f8d99e7f9a721ec91cd8c1dcb38fd112c'): 'deterministic-CRLF',
}
PROFILES = {
    '41810': {
        'id': 'public-exact41810-apr12', 'build': 41810, 'exact_original_build': True,
        'bytes': 774134, 'sha256': '3a33d012a9d47dc1e66595398c2f3dd75cbc9240762996cf52c9c6ad8337e869',
        'streams': {
            'game': (134617, '6176d2c8921b7539345cd705186818c6888e26046547509b2daa7623ec6632f9'),
            'message': (160, '67b7bfab59825a05b88c656e780b50980cff25332bc7fa2e4a064be3ab1b8fce'),
            'tracker': (4405, '3c57b652983d31fbbe352b1ef52e8d8779b00458bae8bd986c1bd8969210e5d8'),
        },
        'lobby_bytes': 43534, 'lobby_sha256': '9536a8f9204fa141ae71a8a25a5f207030165611328579a1daefb747f326cb56',
        'mod_count': 7, 'metadata_end': 227810, 'handles_end': 230056,
    },
    '42273': {
        'id': 'public-nearby42273-apr20', 'build': 42273, 'exact_original_build': False,
        'bytes': 342878, 'sha256': '8281a5ab262e8060719a8b3f56f79bff5a103eab0d8ed26f760d17175ae85066',
        'streams': {
            'game': (50614, '4ddf21cdc25c449828a949af0cdb95a483d9c73e9111c27e9659297c4d2b9ad9'),
            'message': (281, 'e5961a86230fd82cd7a25f66df3aba1edcf1331ce770cfdefdb4c37fe298a340'),
            'tracker': (3370, '0e611ce97e5ca5688e0f20dfe73538f176031b409a443b678b5faccfa429c5ea'),
        },
        'lobby_bytes': 42402, 'lobby_sha256': 'd7c1ad4451d73fb03aa720aac37b75bd1a852e8c57ded06dbe1bbc9e0cab74c4',
        'mod_count': 5, 'metadata_end': 215673, 'handles_end': 217280,
    },
    '41810-local3': {
        'id': 'local-exact41810-dragon-3', 'build': 41810, 'exact_original_build': True,
        'bytes': 850813, 'sha256': '7efa1c335816eebe802747ae4b16252ed22fcd8387b09d24b115b2917542b52a',
        'streams': {
            'game': (140494, '6267487f589c4db643ff4d3b7abc061af0b61552c7a2de9e86c8508406ca4daf'),
            'message': (177, '8f99e8986d20a7ea87996513bb49f5b1450467f81429f702e5cfa3cc0cc72a17'),
            'tracker': (8089, 'efcd51f24f37612199a8ebce2872bdf72144a82a3a8c15552a164deb5e27d139'),
        },
        'lobby_bytes': 41728, 'lobby_sha256': '4a1aacc7dcca7211a8cbedb876376dd2212a8f7e6f4625a233a5d7365f71920b',
        'mod_count': 5, 'metadata_end': 214289, 'handles_end': 215896,
    },
    '41810-local4': {
        'id': 'local-exact41810-dragon-4', 'build': 41810, 'exact_original_build': True,
        'bytes': 688705, 'sha256': '2fca3c78d0e459d4452e3fb1f41ff3fce22b9c1f8f113019389195ff171bf618',
        'streams': {
            'game': (112108, '55d2cbddda60b683d07ed9a21ffe84ca55422ef9a8aa724969f9a359a6d65f28'),
            'message': (107, '55dbb0cc3ad4807cd17460acfd6fe06744a043b78742d066c9d3444f9b7f8bdc'),
            'tracker': (5858, '8d01d6f734e9fea8d038a94d28f6dd0fdac22f4a5d1011caee7165beb7dd13af'),
        },
        'lobby_bytes': 41743, 'lobby_sha256': '7d6cbfad8e5cc3fe86df083a41dc2ad5b3a0be4c8db977e3d512562c4eaf6419',
        'mod_count': 5, 'metadata_end': 214289, 'handles_end': 215896,
    },
    '41810-local5': {
        'id': 'local-exact41810-dragon-5', 'build': 41810, 'exact_original_build': True,
        'bytes': 488833, 'sha256': '8c4fb83989b528ea3227f6c97758293d1f650e33caa3d38c6a2a84d27ab0850d',
        'streams': {
            'game': (78880, '541239128ab928fa794b083f997966fb2d56fe8e5972a88a0a9039ad501e4afb'),
            'message': (135, 'b501cc5c30a47204b4f08ca392676f8f5af8102ef5f5362f5a27bc2cc822c65e'),
            'tracker': (4953, 'fa44344a45d5d1b91b1c196810a81b2144d4992bdb12ed5a1854efbee95a01d1'),
        },
        'lobby_bytes': 41697, 'lobby_sha256': 'd11e15c3ab40f7ffbdf0b8078c5d212dbefe7f98f2a50ebb291c48166e7b67ee',
        'mod_count': 5, 'metadata_end': 214289, 'handles_end': 215896,
    },
}

# Framing admission is an exact-member policy, separate from build identity.
# Preserve the original public control's pins when admitting other fixtures.
MAPINFO_PROFILES = {
    '41810': {
        'source_id': 'public41810control',
        'all_native_field_comparisons': 1816,
        'converted_sha256': '2c770fb59f7a64734752b10858de4746af270a63b1ebfa1b02e6094c493a9e6f',
    },
    '41810-local3': {
        'source_id': 'local41810control3',
        'all_native_field_comparisons': 1191,
        'converted_sha256': '49a5fd5b0f952038d86980489ef42d150fa4f2b2b591707ea5ba21701e98f29c',
    },
    '41810-local4': {
        'source_id': 'local41810control4',
        'all_native_field_comparisons': 1191,
        'converted_sha256': 'd5f3549d40d18dadcbec4b37d79c5ab016b0a587a097c30251f5b66d895f0a81',
    },
    '41810-local5': {
        'source_id': 'local41810control5',
        'all_native_field_comparisons': 1191,
        'converted_sha256': '4ac6dd9b9d4554896971a5b62157d53380957b8342148e5757e9bcd156fc3ff5',
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def read_bound_file(path, size, expected_digest, label):
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size == size,
            label + ' regular-file size differs before parsing')
    with path.open('rb') as stream:
        require(signature(os.fstat(stream.fileno())) == signature(before), label + ' open identity differs')
        raw = stream.read(size + 1)
        after_handle = signature(os.fstat(stream.fileno()))
    require(len(raw) == size and digest(raw) == expected_digest,
            label + ' SHA-256 differs before parsing')
    require(after_handle == signature(before) == signature(path.stat()), label + ' changed during reading')
    return signature(before)


def report_preflight(replay, report):
    require(report.suffix.lower() == '.json', 'Report must have a .json suffix')
    require(report.parent.is_dir(), 'Report parent must already exist')
    require(not os.path.lexists(report), 'Existing report must be preserved')
    require(report.resolve() != replay.resolve(), 'Input and report paths must differ')


def _load_pinned_protocol(build):
    # Verify the exact raw source before the existing loader executes the module.
    package = importlib.import_module('heroprotocol')
    candidates = [Path(root) / 'versions' / f'protocol{build}.py' for root in package.__path__]
    paths = [path.resolve() for path in candidates if path.is_file()]
    require(len(paths) == 1, 'Exactly one official schema source is required')
    path = paths[0]
    raw = path.read_bytes()
    raw_digest = digest(raw)
    variant = SCHEMA_RAW_PINS.get((len(raw), raw_digest))
    require(variant is not None, 'Official schema raw size/SHA-256 differs')
    canonical = raw.replace(b'\r\n', b'\n')
    require(b'\r' not in canonical and digest(canonical) == CANONICAL_SCHEMA_SHA256,
            'Official schema canonical LF SHA-256 differs')
    from protocol_loader import load_protocol
    protocol = load_protocol(build)
    require(protocol.recovery_schema_build == build and protocol.recovery_schema_sha256 == raw_digest,
            'Loaded official schema differs from the prechecked raw source')
    require(digest(path.read_bytes()) == raw_digest, 'Schema source changed during loading')
    return {'build': build, 'upstream_commit': UPSTREAM_COMMIT, 'raw_bytes': len(raw),
            'raw_sha256': raw_digest, 'raw_variant': variant,
            'canonical_LF_bytes': len(canonical), 'canonical_LF_sha256': digest(canonical),
            'dependency_file_rewritten': False}


def verify_mapinfo(lobby, expected, framing):
    """Verify one separately admitted source in RAM; never return its bytes."""
    from legacy_mapinfo_framing import PROFILE, convert_mapinfo_framing, inverse_mapinfo_framing
    require(PROFILE == 'legacy-empty-mapinfo-count7-to-native31-v1', 'MapInfo profile differs')
    value = convert_mapinfo_framing(lobby, PROFILE)
    facts = value.summary()
    count = expected['mod_count']
    added = 3 * count
    require(facts['source_id'] == framing['source_id']
            and facts['source_member_sha256'] == expected['lobby_sha256']
            and facts['source_member_bytes'] == len(lobby), 'MapInfo source admission differs')
    require(facts['MapInfo_records'] == count and facts['added_bytes'] == added
            and facts['named_root_field_comparisons'] == 32 * count
            and facts['all_native_field_comparisons'] == framing['all_native_field_comparisons'],
            'MapInfo comparison counts differ')
    converted_digest = framing['converted_sha256']
    require(type(value.converted) is bytes and len(value.converted) == len(lobby) + added
            and digest(value.converted) == facts['converted_member_sha256'] == converted_digest,
            'MapInfo converted-member pin differs')
    require(facts['unchanged_current_native_32_field_destination_values_and_bounds_exact'] is True
            and facts['all_non_count_tokens_and_outside_bits_exact'] is True
            and facts['inverse_whole_member_bytes_exact'] is True,
            'MapInfo current-field/outside-bit/inverse checks differ')
    require(facts['nonempty_permissions_supported'] is False
            and facts['whole_replay_upgrade_or_historical_schema_authenticated'] is False,
            'MapInfo proof scope differs')
    require(inverse_mapinfo_framing(value, PROFILE) == lobby, 'MapInfo inverse API differs from source')
    return {
        'status': 'admitted-and-verified-in-RAM', 'conversion_attempted': True,
        'profile': PROFILE, 'source_id': facts['source_id'], 'records': count, 'added_bytes': added,
        'named_root_field_comparisons': 32 * count,
        'all_native_field_comparisons': framing['all_native_field_comparisons'],
        'converted_member_bytes': len(value.converted), 'converted_member_sha256': converted_digest,
        'current_32_field_values_and_bounds_exact': True,
        'non_count_tokens_and_outside_bits_exact': True,
        'inverse_whole_source_bytes_exact': True, 'inverse_API_equals_original_member': True,
        'payload_written': False, 'whole_replay_conversion_proven': False,
    }


def verify_reference(replay, profile_name):
    expected = PROFILES[profile_name]
    initial_identity = read_bound_file(replay, expected['bytes'], expected['sha256'], 'Reference fixture')
    # Published scripts/ entry points find project modules without requiring
    # the caller to put the repository root on PYTHONPATH. Keep this after the
    # fixture fingerprint guard and before loading any project decoder.
    sys.path.insert(0, str(ROOT))
    schema = _load_pinned_protocol(expected['build'])
    # No decoder imports or archive parsing occur until the fixture and schema pins pass.
    from reference_replay import checked_archive, inspect_reference
    from audit_battlelobby_mod_metadata import audit_member
    profile = inspect_reference(replay, expected['build'], expected['build'])
    require(profile['file_bytes'] == expected['bytes'] and profile['file_sha256'] == expected['sha256'],
            'Core profile fixture pin differs')
    require(profile['schema_build'] == expected['build']
            and profile['schema_file_sha256'] == schema['raw_sha256'], 'Core profile schema pin differs')
    version = profile['target']['m_version']
    require(version['m_build'] == version['m_baseBuild'] == profile['target']['m_dataBuildNum'] == expected['build'],
            'Historical build declarations differ')
    require(profile['declared_base_matches_schema'] is True and profile['observed_payload_roundtrip'] is True,
            'Historical core round-trip failed')
    require(set(profile['streams']) == set(expected['streams']), 'Core stream inventory differs')
    streams = {}
    for kind, (count, checksum) in expected['streams'].items():
        observed = profile['streams'][kind]
        require(observed['count'] == count and observed['sha256'] == checksum
                and observed['binary_roundtrip'] is True, 'Historical event stream pin/round-trip differs')
        streams[kind] = {'count': count, 'sha256': checksum, 'binary_roundtrip_exact': True}
    archive = checked_archive(replay)
    try:
        lobby = archive.read_file('replay.server.battlelobby')
    finally:
        archive.close()
    require(type(lobby) is bytes and len(lobby) == expected['lobby_bytes']
            and digest(lobby) == expected['lobby_sha256'], 'Historical lobby member pin differs')
    audit = audit_member(lobby, 'legacy-10', 'historical-fixed')
    require(audit['profile'] == 'historical-fixed' and audit['attribute_profile'] == 'legacy-10',
            'Historical audit profiles differ')
    require(audit['member_bytes'] == len(lobby) and audit['member_sha256'] == digest(lobby)
            and audit['same_profile_full_member_roundtrip_exact'] is True, 'Historical member reconstruction differs')
    count = expected['mod_count']
    require(audit['used_mod_count'] == audit['mod_metadata_count'] == audit['terminal_s2mh_count']
            == len(audit['entries']) == count, 'Historical mod/handle counts differ')
    require(all(entry['cafebabe_valid'] is True for entry in audit['entries'])
            and audit['repeated_mod_identities_valid'] is True, 'Historical mod structure differs')
    require(audit['mod_metadata_end_bit'] == expected['metadata_end']
            and audit['terminal_handles_end_bit'] == expected['handles_end'], 'Historical metadata boundaries differ')
    require(audit['after_section_bytes'] == len(lobby) - expected['handles_end'] // 8,
            'Historical opaque suffix extent differs')
    if profile_name in MAPINFO_PROFILES:
        mapinfo = verify_mapinfo(lobby, expected, MAPINFO_PROFILES[profile_name])
    else:
        require(profile_name == '42273', 'Reference has no explicit MapInfo admission policy')
        mapinfo = {
            'status': 'not-admitted', 'conversion_attempted': False,
            'reason': 'The separate nearby42273 member is not admitted by this strict MapInfo profile.',
            'payload_written': False,
        }
    require(read_bound_file(replay, expected['bytes'], expected['sha256'], 'Reference fixture') == initial_identity,
            'Reference fixture identity changed during verification')
    return {
        'format': 'historical-reference-strict-gate-v2', 'status': 'passed',
        'profile': expected['id'], 'declared_build': expected['build'],
        'exact_original_41810_build_control': expected['exact_original_build'],
        'fixture': {'bytes': expected['bytes'], 'sha256': expected['sha256'], 'preserved': True},
        'official_schema': schema, 'streams': streams,
        'header_details_initData_and_observed_event_roundtrips_exact': True,
        'MapInfo_framing': mapinfo,
        'battlelobby': {
            'bytes': len(lobby), 'sha256': digest(lobby), 'attribute_profile': 'legacy-10',
            'metadata_profile': 'historical-fixed', 'used_mod_count': count, 'metadata_count': count,
            'terminal_handle_count': count, 'mod_metadata_end_bit': expected['metadata_end'],
            'terminal_handles_end_bit': expected['handles_end'], 'member_bits': len(lobby) * 8,
            'opaque_suffix_bytes': audit['after_section_bytes'],
            'opaque_suffix_sha256': audit['after_section_sha256'],
            'same_profile_full_source_roundtrip_exact': True,
        },
        'scope': [
            'Core streams cover only event types present in this fixed reference.',
            'The legacy audit reaches the terminal-handle boundary; its later member suffix remains opaque.',
            'Exact whole-source reconstruction preserves that suffix; it is not complete suffix semantic/EOF validation.',
            'Admitted MapInfo member framing is checked in RAM; it does not convert the whole replay or supply missing player values.',
            'The nearby42273 profile is separate from the exact41810 control.',
        ],
        'player_or_raw_payload_emitted': False, 'local_source_path_or_host_identifiers_emitted': False,
        'network_or_client_used': False, 'replay_or_member_written': False,
        'whole_replay_conversion_performed': False, 'native_playback_or_simulation_proven': False,
        'full_upgrade_complete': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=tuple(PROFILES), default='41810')
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report_preflight(args.replay, args.report)
        result = verify_reference(args.replay, args.profile)
        payload = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode('utf-8')
        require(len(payload) <= 16384, 'Sanitized report exceeds its output cap')
        with args.report.open('xb') as stream:
            require(stream.write(payload) == len(payload), 'Report write was short')
    except Exception as error:
        # Dependency errors must not accidentally print decoded player data or local paths.
        print(f'Historical reference gate rejected ({type(error).__name__}); no success report.', file=sys.stderr)
        return 1
    print(json.dumps({'profile': result['profile'], 'status': 'passed', 'player_payload_emitted': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
