"""Cross-bind static battlelobby arcade arrays to exact content-addressed s2mh.

Only a new sanitized JSON report is written. Missing depot headers leave an
explicit acquisition gap; observed current-array round-trips remain separate
from authenticated package-header binding. No replay/member/header is written.
"""
import argparse
import hashlib
import json
from pathlib import Path

from audit_battlelobby_mod_metadata import audit_member
from battlelobby_arcade_sections import from_depot_subtree, read_section, verify_binding
from battlelobby_attribute_layer import LayerError, _Reader, _read, decode_layer
from depot_s2mh_wire import decode_verified_header


def _section_start(entry):
    if 'how_to_play_section_start_bit' in entry:
        return entry['how_to_play_section_start_bit']
    # Compatibility with the preserved initial diagnostic, whose fixed447+7
    # field spans were later identified using authenticated package headers.
    if 'historical_fixed_fields' in entry:
        return entry['historical_fixed_fields']['start_bit'] + 8
    return entry['current_choice']['bit']


def inspect_case(label, attribute_profile, metadata_profile, member_path, header_directory):
    member_path, header_directory = Path(member_path), Path(header_directory)
    raw = _read(member_path)
    digest = hashlib.sha256(raw).hexdigest()
    audit = audit_member(raw, attribute_profile, metadata_profile)
    layer = decode_layer(raw, attribute_profile)
    prefix_handles = tuple(token.value for token in layer.tokens
                           if token.path.startswith('/dependencies/handles/'))
    reader = _Reader(raw)
    reader.position = audit['mod_metadata_end_bit']
    terminal = tuple(reader.blob(40) for _ in range(reader.bits(6)))
    if len(terminal) != len(audit['entries']) or reader.position != audit['terminal_handles_end_bit']:
        raise LayerError('Terminal header boundaries differ')
    results = []
    for entry, handle in zip(audit['entries'], terminal):
        if handle[:4] != b's2mh':
            raise LayerError('Expected an exact s2mh terminal handle')
        header_digest = handle[8:].hex()
        header_path = header_directory / (header_digest + '.s2mh')
        has_arcade = entry.get('has_static_arcade_info', entry.get('has_hero_metadata', False))
        result = dict(index=entry['index'], header_sha256=header_digest,
            header_file_available=header_path.is_file(),
            has_static_arcade_info=has_arcade,
            header_authenticated=False, numeric_subtree_bound=False,
            raw_publisher_or_localized_text_projected=False)
        if has_arcade:
            start = _section_start(entry)
            reader = _Reader(raw)
            reader.position = start
            observed = read_section(reader.bits)
            result['observed_array'] = verify_binding(raw, start, observed)
            result['observed_array']['authenticated_header_binding'] = False
        if header_path.is_file():
            header_raw = _read(header_path, 2 * 1024 * 1024)
            header = decode_verified_header(header_raw, header_digest)[0]
            package_identity = header[0]
            if type(package_identity) is not dict or set(package_identity) != {0, 1}:
                raise LayerError('Exact package identity is unavailable')
            reader = _Reader(raw)
            reader.position = entry['start_bit']
            if (reader.bits(32), reader.bits(32)) != (package_identity[0], package_identity[1]):
                raise LayerError('Depot package identity differs from metadata')
            if (header.get(19) is not None) != has_arcade:
                raise LayerError('Depot arcade presence differs from metadata')
            reader.position = entry['end_bit'] - entry['final_unknown_filler_bits'] - 64 * entry['dependency_count'] - 6
            count = reader.bits(6)
            dependencies = tuple((reader.bits(32), reader.bits(32)) for _ in range(count))
            expected_dependencies = tuple((item[0], item[1]) for item in header.get(14, ()))
            if dependencies != expected_dependencies:
                raise LayerError('Depot extra-dependency versions differ from metadata')
            result.update(header_authenticated=True, header_bytes=len(header_raw),
                package_identity_matches=True,
                package_pair_names='id,version',
                dependency_version_pairs_match_header=True,
                archive_handle_matches_dependency_prefix=header[2] in prefix_handles,
                endpoint_region=handle[4:8].strip(b'\0 ').decode('ascii').lower())
            if has_arcade:
                expected = from_depot_subtree(header[19][4])
                result['authenticated_array'] = verify_binding(raw, start, expected)
                result['numeric_subtree_bound'] = True
                result['authenticated_array']['authenticated_header_binding'] = True
        results.append(result)
    if _read(member_path) != raw:
        raise LayerError('Source member changed during verification')
    return dict(id=label, member_sha256=digest, attribute_profile=attribute_profile,
        metadata_profile=metadata_profile, entries=results,
        source_member_unchanged=True, client_launched=False,
        authenticated_header_count=sum(row['header_authenticated'] for row in results),
        authenticated_arcade_section_count=sum(row['numeric_subtree_bound'] for row in results),
        observed_arcade_section_count=sum(row['has_static_arcade_info'] for row in results),
        all_metadata_is_current_or_coherent_claimed=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', nargs=5, action='append', required=True,
        metavar=('LABEL', 'ATTRIBUTE_PROFILE', 'METADATA_PROFILE', 'MEMBER', 'HEADER_DIRECTORY'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.suffix.lower() != '.json':
        parser.error('Output must be a new .json report')
    if len(args.case) > 8 or len({row[0] for row in args.case}) != len(args.case):
        parser.error('At most eight uniquely labelled cases are supported')
    if any(Path(row[3]).resolve() == args.output.resolve() for row in args.case):
        parser.error('Input and output paths must differ')
    results = [inspect_case(*row) for row in args.case]
    report = dict(format='hots-authenticated-arcade-section-binding-v1', results=results,
        primary_named_schema_commit='b48c60a697b12ae1dc8681a2d42ce313958ce94a',
        primary_named_schema_url='https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L571-L610',
        primary_localization_key_url='https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L188-L206',
        primary_arcade_info_url='https://github.com/sc2-arcade-watcher/s2mdec/blob/b48c60a697b12ae1dc8681a2d42ce313958ce94a/s2m.go#L686-L716',
        primary_depot_endpoint_url='https://github.com/ggtracker/sc2reader/blob/e10fc9344417d0aa9649e4ed8d6423e38f6af4c9/sc2reader/utils.py',
        conclusions=[
            'howToPlaySections consist of a4-bit section-header count and7-bit localized-item count; colors are represented explicitly.',
            'Authenticated numeric subtree binding and exact member reconstruction are reported separately for each declared case.',
            'Observed-array roundtrips remain separate from authentication when exact headers are unavailable.',
            'The unchanged third-party C# baseline incorrectly treats observed3headers as an empty choice3.',
            'No header/player/sync substitution, replay creation or client execution is performed.'],
        replay_or_member_or_header_written=False, full_parser_or_playback_success_claimed=False)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(cases=len(results),
        authenticated_headers=sum(row['authenticated_header_count'] for row in results),
        authenticated_arcade_sections=sum(row['authenticated_arcade_section_count'] for row in results),
        report_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
